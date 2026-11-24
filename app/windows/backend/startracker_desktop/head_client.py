"""The Star Tracker head for the reused camera code (port of app/android/.../HeadClient.java): the method names the
camera jobs used with the Polaris driver, answered by the head's one-shot HTTP transport POST /startracker/v1/op
(API 1.1). The UI sets the head's address when it connects (StBridge.setHead)."""
import json
import threading
import time
import urllib.request

_base = None
_lock = threading.Lock()
_id = 0


def set_base(http_base):
    global _base
    _base = http_base.rstrip("/") if http_base else None


class HeadError(Exception):
    pass


class HeadClient:
    def __init__(self):
        self._guide_until = 0.0
        self._panels = []

    def op(self, op, args=None):
        global _id
        if not _base:
            raise HeadError("No head connected")
        with _lock:
            _id += 1
            req = {"v": 1, "id": _id, "op": op, "args": args or {}}
        r = urllib.request.Request(_base + "/startracker/v1/op", data=json.dumps(req).encode(), method="POST",
                                   headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=15) as resp:
            rep = json.loads(resp.read().decode("utf-8"))
        if "ev" in rep:
            return rep
        if not rep.get("ok"):
            e = rep.get("err") or {}
            raise HeadError(f"Head: {e.get('msg', 'error')} ({e.get('code', '')})")
        return rep.get("result") or {}

    def state(self):
        return self.op("state")

    status = state

    def position(self):
        a = self.state().get("altaz", {})
        return a.get("az_d", float("nan")), a.get("alt_d", float("nan"))

    def slew_altaz(self, az, alt):
        self.op("goto", {"az_d": az % 360, "alt_d": alt})

    def ra_dec(self):
        r = self.state().get("radec", {})
        return r.get("ra_now_h", float("nan")), r.get("dec_now_d", float("nan"))

    def j2000_sync(self, ra_hours, dec_deg):
        self.op("sync", {"ra_h": ra_hours, "dec_d": dec_deg, "epoch": "J2000"})

    def j2000_goto(self, name, ra_hours, dec_deg):
        self.op("goto", {"ra_h": ra_hours, "dec_d": dec_deg, "epoch": "J2000"})

    def tracking(self):
        return bool(self.state().get("tracking"))

    def set_tracking(self, on):
        self.op("track", {"on": bool(on)})

    def pulse_guide(self, direction, ms):
        ms = max(1, min(10000, int(ms)))
        self.op("guide", {"dir": "nsew"[max(0, min(3, int(direction)))], "ms": ms})
        self._guide_until = time.monotonic() + ms / 1000

    def pulse_guiding(self):
        return time.monotonic() < self._guide_until + 0.1

    def track_orbital(self, name):
        n = name.lower()
        if n not in ("sun", "moon"):
            raise HeadError(f"Pick {name} on the Sky screen: the app computes planets")
        self.op("goto", {"body": n})

    def slewing(self):
        return self.state().get("mode") in ("slewing", "moving", "parking")

    def abort_slew(self):
        try:
            self.op("stop")
        except Exception:  # noqa: BLE001
            pass

    def wait_while_slewing(self, stop, timeout):
        time.sleep(0.5)
        deadline = time.monotonic() + timeout
        while self.slewing():
            if stop():
                self.abort_slew()
                return False
            if time.monotonic() > deadline:
                raise HeadError("The head did not finish moving")
            time.sleep(0.3)
        return not stop()

    def move(self, axis, dps):
        self.op("jog", {"axis": int(axis), "dps": float(dps)})

    def home(self):
        self.op("park")

    def pano_grid(self, grid):
        g = json.loads(grid) if isinstance(grid, str) else grid
        poses = g.get("poses")
        if not poses:
            raise HeadError("Use the Canopus panorama planner (Camera & jobs)")
        self._panels = [(p["az_d"], p["alt_d"]) for p in poses]

    def panel_count(self):
        return max(1, len(self._panels))

    def slew_to_panel(self, panel):
        if not self._panels:
            raise HeadError("No panorama planned")
        az, alt = self._panels[max(0, min(len(self._panels) - 1, panel - 1))]
        self.slew_altaz(az, alt)
