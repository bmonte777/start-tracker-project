"""window.StNative on Windows (app/shared/native.js calls POST /bridge/st/<method> with a JSON object):
setTheme, setHead, discoverAlpaca, discoverMdns, bleScan, bleConnect, bleWrite, bleRead, bleDisconnect, keepAwake,
notify, openSettings, location."""
import asyncio
import json
import os
import socket
import threading
import time

from . import head_client

SERVICE = "5354524b-0100-4d2a-9b1e-000000000001"


class _Loop:
    """One asyncio loop in a thread for bleak (BLE)."""
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True, name="ble").start()

    def run(self, coro, timeout=60):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)


class StBridge:
    def __init__(self):
        self._ble = None
        self._clients = {}

    def setTheme(self, a):
        return None

    def setHead(self, a):
        head_client.set_base(a.get("http"))

    def discoverAlpaca(self, a):
        ms = int(a.get("timeoutMs", 2000))
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.3)
        for target in ("255.255.255.255", "127.0.0.1"):           # the simulator on this PC answers on localhost
            try:
                s.sendto(b"alpacadiscovery1", (target, 32227))
            except OSError:
                pass
        found, end = {}, time.monotonic() + ms / 1000
        while time.monotonic() < end:
            try:
                data, (host, _) = s.recvfrom(512)
                port = json.loads(data).get("AlpacaPort")
                if port:
                    found[host] = port
            except (socket.timeout, ValueError):
                continue
        s.close()
        return [{"host": h, "port": p} for h, p in found.items()]

    def discoverMdns(self, a):
        try:
            from zeroconf import ServiceBrowser, Zeroconf
        except ImportError:
            return []
        found = []

        class L:
            def add_service(self, zc, t, name):
                info = zc.get_service_info(t, name, 1500)
                if info and info.parsed_addresses():
                    found.append({"host": info.parsed_addresses()[0], "port": info.port})

            def update_service(self, *x):
                pass

            def remove_service(self, *x):
                pass

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, "_startracker._tcp.local.", L())
            time.sleep(int(a.get("timeoutMs", 2000)) / 1000)
        finally:
            zc.close()
        return found

    # BLE first set-up (bleak). Windows asks for the pairing code in its own dialog when the head requests it.
    def _loop(self):
        if self._ble is None:
            self._ble = _Loop()
        return self._ble

    def bleScan(self, a):
        from bleak import BleakScanner

        async def scan():
            devs = await BleakScanner.discover(timeout=int(a.get("ms", 6000)) / 1000, return_adv=True)
            out = []
            for d, adv in devs.values():
                name = adv.local_name or d.name or ""
                if name.startswith("StarTracker-") or SERVICE in [u.lower() for u in adv.service_uuids]:
                    out.append({"id": d.address, "name": name or d.address, "rssi": adv.rssi, "uuids": adv.service_uuids})
            return out
        return self._loop().run(scan(), 30)

    def bleConnect(self, a):
        from bleak import BleakClient

        async def conn():
            c = BleakClient(a["id"])
            await c.connect(timeout=20)
            try:
                await c.pair()                       # Windows shows its pairing dialog: type the code on the head's screen
            except Exception:  # noqa: BLE001  (already paired, or pairing happens on the first encrypted write)
                pass
            self._clients[a["id"]] = c
        self._loop().run(conn(), 90)

    def bleWrite(self, a):
        c = self._clients.get(a["id"])
        if c is None:
            raise RuntimeError("not paired: press Pair first")
        self._loop().run(c.write_gatt_char(a["ch"], a["text"].encode("utf-8"), response=True), 30)

    def bleRead(self, a):
        c = self._clients.get(a["id"])
        if c is None:
            raise RuntimeError("not paired")
        return bytes(self._loop().run(c.read_gatt_char(a["ch"]), 15)).decode("utf-8", "replace")

    def bleDisconnect(self, a):
        c = self._clients.pop(a["id"], None)
        if c is not None:
            self._loop().run(c.disconnect(), 10)

    def keepAwake(self, a):
        # Windows: ask the system not to sleep while a job runs (ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if a.get("on") else 0))
        return None

    def notify(self, a):
        return None

    def openSettings(self, a):
        target = {"bluetooth": "ms-settings:bluetooth", "location": "ms-settings:privacy-location"}.get(a.get("what"), "ms-settings:network-wifi")
        if hasattr(os, "startfile"):
            os.startfile(target)  # noqa: S606
        return None

    def location(self, a):
        raise RuntimeError("this PC has no location: type it in Settings, or send it from the phone app")
