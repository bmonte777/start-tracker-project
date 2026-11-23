#!/usr/bin/env python3
"""Protocol tests against a running simulator (firmware/sim): Alpaca over HTTP, Alpaca discovery over UDP, LX200 over
TCP the way Stellarium talks to it, and the WebSocket JSON API. Standard library only.

Start the simulator first (the workflow does this): startracker-sim --speed 10
Exit code = number of failed checks. Writes a Markdown report to proto_report.md.
"""
import base64
import http.client
import json
import os
import socket
import struct
import sys
import time
import urllib.parse

HOST = os.environ.get("SIM_HOST", "127.0.0.1")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""))


def alpaca(method, path, **params):
    c = http.client.HTTPConnection(HOST, 32323, timeout=60)
    params.setdefault("ClientID", "7")
    params.setdefault("ClientTransactionID", "42")
    q = urllib.parse.urlencode(params)
    if method == "GET":
        c.request("GET", f"/api/v1/{path}?{q}")
    else:
        c.request("PUT", f"/api/v1/{path}", body=q, headers={"Content-Type": "application/x-www-form-urlencoded"})
    r = c.getresponse()
    body = r.read().decode()
    return r.status, (json.loads(body) if r.status == 200 else body)


def test_alpaca():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(b"alpacadiscovery1", (HOST, 32227))
    try:
        data, _ = s.recvfrom(256)
        check("alpaca discovery answers with the port", json.loads(data).get("AlpacaPort") == 32323, data.decode())
    except socket.timeout:
        check("alpaca discovery answers with the port", False, "no reply")
    st, j = alpaca("PUT", "telescope/0/connected", Connected="True")
    check("telescope connect", st == 200 and j["ErrorNumber"] == 0)
    st, j = alpaca("GET", "telescope/0/rightascension")
    check("rightascension readable, transaction id echoed", st == 200 and j["ClientTransactionID"] == 42 and 0 <= j["Value"] < 24)
    alpaca("PUT", "telescope/0/tracking", Tracking="True")
    t0 = time.time()
    st, j = alpaca("PUT", "telescope/0/slewtocoordinates", RightAscension="5.27815", Declination="45.99799")   # synchronous
    st2, sl = alpaca("GET", "telescope/0/slewing")
    check("synchronous slew returns when finished", st == 200 and j["ErrorNumber"] == 0 and sl["Value"] is False, f"{time.time() - t0:.1f} s real")
    time.sleep(1)
    _, ra = alpaca("GET", "telescope/0/rightascension")
    _, de = alpaca("GET", "telescope/0/declination")
    err = ((ra["Value"] - 5.27815) * 15 * 3600 * 0.695) ** 2 + ((de["Value"] - 45.99799) * 3600) ** 2
    check("pointing after the slew within 2 arcsec (JNow)", err ** 0.5 < 2.0, f"{err ** 0.5:.2f}\"")
    st, j = alpaca("PUT", "telescope/0/slewtocoordinatesasync", RightAscension="25", Declination="0")
    check("invalid RA -> error 0x401", j["ErrorNumber"] == 0x401)
    st, j = alpaca("GET", "telescope/0/axisrates", Axis="0")
    check("axis rates 0..8 deg/s (D42)", j["Value"][0]["Maximum"] == 8)
    st, j = alpaca("PUT", "rotator/0/connected", Connected="True")
    st, j = alpaca("GET", "rotator/0/position")
    check("rotator position readable", j["ErrorNumber"] == 0 and 0 <= j["Value"] < 360)
    st, body = alpaca("GET", "telescope/0/bogus")
    check("unknown member -> HTTP 400", st == 400)


def lx(sock, cmd, expect_reply=True):
    sock.sendall(cmd.encode())
    if not expect_reply:
        return ""
    time.sleep(0.2)
    return sock.recv(256).decode(errors="replace")


def test_lx200():
    s = socket.create_connection((HOST, 4030), timeout=5)
    r = lx(s, ":GR#")
    check("LX200 :GR# high precision HH:MM:SS#", len(r) == 9 and r[2] == ":" and r[5] == ":" and r.endswith("#"), r)
    r = lx(s, ":GD#")
    check("LX200 :GD# sDD*MM:SS#", len(r) == 10 and r[0] in "+-" and r[3] == "*", r)
    # Stellarium "Meade LX200" goto: set target, slew, poll position
    check("LX200 :Sr accepted", lx(s, ":Sr 06:45:09#") == "1")
    check("LX200 :Sd accepted", lx(s, ":Sd -16*42:58#") == "1")
    r = lx(s, ":MS#")
    check("LX200 :MS# to Sirius (below the horizon or slewing)", r[:1] in ("0", "1"), repr(r))
    lx(s, ":Q#", False)
    check("LX200 ACK -> A (alt-az)", lx(s, "\x06") == "A")
    s.close()


def ws_connect():
    s = socket.create_connection((HOST, 8080), timeout=5)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall(f"GET /ws/v1 HTTP/1.1\r\nHost: {HOST}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
    resp = s.recv(1024).decode()
    return s, resp


def ws_send(s, text):
    data = text.encode()
    mask = os.urandom(4)
    hdr = bytes([0x81, 0x80 | len(data)]) if len(data) < 126 else bytes([0x81, 0x80 | 126]) + struct.pack(">H", len(data))
    s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def ws_recv(s):
    h = s.recv(2)
    n = h[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", s.recv(2))[0]
    buf = b""
    while len(buf) < n:
        buf += s.recv(n - len(buf))
    return buf.decode()


def test_ws():
    s, resp = ws_connect()
    check("WebSocket upgrade (101)", "101" in resp.split("\r\n")[0])
    ws_send(s, json.dumps({"v": 1, "id": 5, "op": "config.get"}))
    got_reply, got_state = False, False
    for _ in range(20):
        m = json.loads(ws_recv(s))
        if m.get("id") == 5:
            got_reply = m["ok"] and "lat" in m["result"]
        if m.get("ev") == "state":
            got_state = "axes" in m and "batt" in m
        if got_reply and got_state:
            break
    check("WebSocket config.get reply", got_reply)
    check("WebSocket state events", got_state)
    s.close()


if __name__ == "__main__":
    for t in (test_alpaca, test_lx200, test_ws):
        try:
            t()
        except Exception as e:  # noqa: BLE001
            check(t.__name__ + " ran", False, repr(e))
    failed = sum(1 for r in results if not r[1])
    with open("proto_report.md", "w") as f:
        f.write("| Check | Result | Detail |\n|---|---|---|\n")
        for n, ok, d in results:
            f.write(f"| {n} | {'pass' if ok else 'FAIL'} | {d} |\n")
    print(f"\n{len(results) - failed} passed, {failed} failed")
    sys.exit(failed)
