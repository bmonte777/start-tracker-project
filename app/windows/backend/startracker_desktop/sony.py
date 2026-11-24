"""Controls a Sony camera (A7R V and other recent Alphas) in PC Remote mode:
Sony's SDIO extensions to PTP, as used by libgphoto2. Port of
SonyCamera.java: same jobs, same status JSON for the Camera screen."""
import base64
import json
import math
import os
import struct
import threading
import time
from collections import deque
from datetime import datetime

import random

from . import alerts, astap, exposure, median, path as pathlapse, plate_solver, shot_log
from . import holy_grail as hg
from . import sony_props as sp
from .paths import catalog_file, pictures_dir
from .head_client import HeadClient
from .sony_props import SonyProps

ASTAP_FIRST_BELOW_DEG = 7.5        # frame width in degrees: about 275 mm and longer on full frame (D74)

OP_OPEN_SESSION = 0x1002
OP_CLOSE_SESSION = 0x1003
OP_GET_STORAGE_IDS = 0x1004
OP_GET_STORAGE_INFO = 0x1005
OP_GET_OBJECT_INFO = 0x1008
OP_GET_OBJECT = 0x1009
OP_SDIO_CONNECT = 0x9201
OP_SDIO_GET_EXT_DEVICE_INFO = 0x9202
OP_SDIO_SET_VALUE = 0x9205
OP_SDIO_CONTROL = 0x9207
OP_SDIO_GET_ALL_PROPS = 0x9209
SHOT_IN_MEMORY = 0xFFFFC001
LIVE_VIEW = 0xFFFFC002


def encode(t, v):
    """Little-endian bytes of v for PTP data type t (negatives as two's complement)."""
    size = {1: 1, 2: 1, 3: 2, 4: 2, 7: 8, 8: 8}.get(t, 4)
    return (int(v) & ((1 << (8 * size)) - 1)).to_bytes(size, "little")


def live_jpeg(d):
    """The JPEG inside Sony live-view data: header offset/size, else markers."""
    if len(d) >= 8:
        off, ln = struct.unpack_from("<II", d, 0)
        if off >= 8 and ln > 2 and off + ln <= len(d) and d[off] == 0xFF and d[off + 1] == 0xD8:
            return bytes(d[off:off + ln])
    start = d.find(b"\xff\xd8")
    if start < 0:
        return None
    end = d.rfind(b"\xff\xd9")
    return bytes(d[start:end + 2]) if end > start else None


MOVIE_BUTTON = 0xD2C8


def _hms(hours):
    h = (hours % 24 + 24) % 24
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = ((h - hh) * 60 - mm) * 60
    return "%02dh%02dm%04.1fs" % (hh, mm, ss)


def _dms(deg):
    a = abs(deg)
    d = int(a)
    m = int((a - d) * 60)
    sec = ((a - d) * 60 - m) * 60
    return "%s%02d°%02d′%02.0f″" % ("−" if deg < 0 else "+", d, m, sec)


class Stop(Exception):
    pass


class ShotSettings:
    def __init__(self, o=None):
        o = o or {}
        self.bulb_seconds = max(0.1, float(o.get("bulbSeconds", 30)))
        self.autofocus = bool(o.get("autofocus", False))


class SonyCamera:
    def __init__(self, open_transport=None, out_dir=None):
        """open_transport() -> (Transport, model name); out_dir: where photos go."""
        self.open_transport = open_transport
        self.out_dir = out_dir
        self.ptp = None
        self.model = ""
        self.props = SonyProps()
        self.state = "disconnected"
        self.error = ""
        self.card = ""
        self.shots = 0
        self.last_file = ""
        self.log_lines = deque(maxlen=200)
        self.last_info = b""
        self.last_props = b""
        self.job = None
        self.job_name = ""
        self.job_step = ""
        self.stop_job = False
        self.job_jpegs = []
        self.live_wanted = False
        self.live_thread = None
        self.live_jpeg = None
        self.live_seq = 0
        self.live_error = ""
        self.last_path = None
        self.trails_jpeg = None
        self.trails_seq = 0
        self.last_solve_json = ""
        self.star_catalog = None
        self.iso_dial_dir = 1
        self.lock = threading.RLock()
        self.worker_lock = threading.Lock()

    # ------------------------------------------------------------- helpers
    def log(self, line):
        self.log_lines.append(time.strftime("%H:%M:%S") + " " + line)

    def fail(self, what, e):
        self.error = "%s: %s" % (what, e)
        self.log(self.error)

    def _bg(self, fn):
        def run():
            with self.worker_lock:
                try:
                    fn()
                except Exception as e:      # noqa: BLE001 - reported to the page
                    self.fail("Camera", e)
        threading.Thread(target=run, daemon=True).start()

    def _t(self, op, params=(), data_out=None, want_data=False):
        p = self.ptp
        if p is None:
            raise IOError("Camera not connected")
        return p.transact(op, params, data_out, want_data)

    # ---------------------------------------------------------- connection
    def is_connected(self):
        return self.ptp is not None

    def connect(self):
        if self.ptp is not None:
            return "ok"

        def go():
            self.state = "connecting"
            self.error = ""
            try:
                self.ptp, self.model = self.open_transport()
                self.log("Camera opened: " + self.model)
                self.handshake()
                self.state = "connected"
                self.refresh_now()
                self.read_card()
            except Exception as e:      # noqa: BLE001
                self.fail("Connect failed", e)
                self._close()
                self.state = "disconnected"
        self._bg(go)
        return "ok"

    def handshake(self):
        if not self.ptp.manages_session:
            r = self._t(OP_OPEN_SESSION, [1])
            if not r.ok() and r.code != 0x201E:
                raise IOError("OpenSession refused (0x%04x)" % r.code)
        self._sdio(OP_SDIO_CONNECT, [1, 0, 0])
        self._sdio(OP_SDIO_CONNECT, [2, 0, 0])
        r = self._t(OP_SDIO_GET_EXT_DEVICE_INFO, [0xC8], want_data=True)
        self.last_info = r.data
        if len(r.data) >= 2:
            v = r.data[0] | (r.data[1] << 8)
            self.log("Sony remote protocol %d.%02d" % (v // 100, v % 100))
        self._sdio(OP_SDIO_CONNECT, [3, 0, 0])
        self.log("Remote control mode on")

    def _sdio(self, op, params):
        # SDIO Connect answers with a short data phase (libgphoto2 reads it
        # too). Windows' MTP driver rejects a data packet it was not told
        # to expect ("invalid data", 0x8007065D), so always ask for it.
        r = self._t(op, params, want_data=True)
        if not r.ok():
            raise IOError("Camera refused 0x%04x (0x%04x)" % (op, r.code))

    def disconnect(self):
        self.stop_job = True

        def go():
            if self.ptp is not None and not self.ptp.manages_session:
                try:
                    self._t(OP_CLOSE_SESSION)
                except Exception:      # noqa: BLE001
                    pass
            self._close()
            self.state = "disconnected"
            self.log("Disconnected")
        self._bg(go)

    def _close(self):
        p, self.ptp = self.ptp, None
        if p is not None:
            try:
                p.close()
            except Exception:      # noqa: BLE001
                pass

    # ---------------------------------------------------------- properties
    def refresh(self):
        if self.ptp is not None and self.job is None:
            self._bg(self.refresh_now)

    def refresh_now(self):
        r = self._t(OP_SDIO_GET_ALL_PROPS, want_data=True)
        if not r.ok():
            raise IOError("Camera refused settings read (0x%04x)" % r.code)
        self.last_props = r.data
        p = SonyProps.parse(r.data)
        if p.parse_problem and not self.props.parse_problem:
            self.log("Settings list: " + p.parse_problem)
        self.props = p

    def step(self, code, direction):
        def go():
            r = self._t(OP_SDIO_CONTROL, [code], bytes([0x01 if direction > 0 else 0xFF]))
            if not r.ok():
                self.log("Step 0x%04x refused (0x%04x)" % (code, r.code))
            time.sleep(0.15)
            self.refresh_now()
        self._bg(go)

    def set(self, code, value):
        def go():
            self.set_now(code, int(value))
            time.sleep(0.15)
            self.refresh_now()
        self._bg(go)

    def set_now(self, code, value):
        p = self.props.props.get(code)
        r = self._t(OP_SDIO_SET_VALUE, [code], encode(p.type if p else 4, value))
        if not r.ok():
            self.log("Set 0x%04x refused (0x%04x)" % (code, r.code))

    def button(self, code, value):
        r = self._t(OP_SDIO_CONTROL, [code], encode(4, value))
        if not r.ok():
            raise IOError("Button 0x%04x refused (0x%04x)" % (code, r.code))

    def read_card(self):
        if self.ptp is None:
            return
        try:
            ids = self._t(OP_GET_STORAGE_IDS, want_data=True)
            if not ids.ok() or len(ids.data) < 4:
                return
            n = struct.unpack_from("<I", ids.data, 0)[0]
            parts = []
            for i in range(n):
                if 4 + 4 * (i + 1) > len(ids.data):
                    break
                sid = struct.unpack_from("<I", ids.data, 4 + 4 * i)[0]
                if sid & 0xFFFF == 0:
                    continue
                r = self._t(OP_GET_STORAGE_INFO, [sid], want_data=True)
                if not r.ok() or len(r.data) < 26:
                    continue
                cap, free = struct.unpack_from("<QQ", r.data, 6)
                left = struct.unpack_from("<I", r.data, 22)[0]
                if cap <= 0:
                    continue
                t = "Card %d: %.1f of %.0f GB free" % ((sid >> 16) & 0xFFFF, free / 1e9, cap / 1e9)
                if 0 < left != 0xFFFFFFFF:
                    t += ", %d shots" % left
                parts.append(t)
            self.card = " · ".join(parts)
        except Exception as e:      # noqa: BLE001
            self.log("Card info not available: %s" % e)

    # ------------------------------------------------------------ shooting
    def _sleep(self, seconds, what=None):
        """Waits, checking for Stop. False when stopped."""
        until = time.monotonic() + seconds
        while not self.stop_job:
            left = until - time.monotonic()
            if left <= 0:
                return True
            if what:
                self.job_step = "%s %d s" % (what, math.ceil(left))
            time.sleep(min(0.25, left))
        return False

    def exposure_seconds(self):
        sec = exposure.seconds(self.props.get(sp.SHUTTER, 0))
        return 0.0 if math.isnan(sec) else sec

    def shoot(self, s):
        self.refresh_now()
        bulb = sp.is_bulb(self.props.get(sp.SHUTTER, -1))
        dest = self.props.get(sp.SAVE_DESTINATION, sp.DEST_CARD)
        if s.autofocus:
            self.button(sp.AUTOFOCUS_BUTTON, 2)
            time.sleep(0.7)
        self.button(sp.SHUTTER_BUTTON, 2)
        if bulb:
            until = time.monotonic() + s.bulb_seconds
            while time.monotonic() < until and not self.stop_job:
                self.job_step = "Exposing… %d s left" % max(0, until - time.monotonic())
                time.sleep(min(0.25, max(0.001, until - time.monotonic())))
        else:
            time.sleep(0.2)
        self.button(sp.SHUTTER_BUTTON, 1)
        if s.autofocus:
            self.button(sp.AUTOFOCUS_BUTTON, 1)
        self.shots += 1
        self.log("Shot %d%s" % (self.shots, " (bulb %.1f s)" % s.bulb_seconds if bulb else ""))
        step_now, file_before = self.job_step, self.last_file
        if dest in (sp.DEST_TABLET, sp.DEST_BOTH):
            self.download_waiting(30 if bulb else 15 + self.exposure_seconds())
        else:
            self.job_step = "Camera saving to card…"
            time.sleep(1.0 if bulb else 0.6 + self.exposure_seconds())
        self._log_shot(step_now, "on camera card" if self.last_file == file_before else self.last_file,
                       "bulb %.1f s" % s.bulb_seconds if bulb else sp.shutter(self.props.get(sp.SHUTTER, 0)))

    def _log_shot(self, step, file, shutter):
        """One line in the day's shot log (Documents\\Canopus)."""
        az = alt = float("nan")
        try:
            az, alt = HeadClient().position()
        except Exception:      # noqa: BLE001 - driver not running: logged without the pointing
            pass
        shot_log.add(self.job_name or "Single shot", step, file, shutter,
                     sp.fmt(sp.F_NUMBER, self.props.get(sp.F_NUMBER, 0)), sp.iso(self.props.get(sp.ISO, 0)), az, alt)

    @staticmethod
    def _start_position(polaris):
        """Where the Polaris points now, to come back to after a job (None if unknown)."""
        try:
            p = polaris.position()
            return None if any(math.isnan(v) for v in p) else p
        except Exception:      # noqa: BLE001
            return None

    def _return_to(self, polaris, start):
        """Moves the Polaris back to where the job started (also after Stop)."""
        if start is None:
            return
        try:
            self.job_step = "Returning to the start position"
            polaris.set_tracking(False)
            polaris.slew_altaz(start[0], start[1])
            polaris.wait_while_slewing(lambda: False, 180)
            self.log("Back at the start position (%.1f° / %.1f°)" % (start[0], start[1]))
        except Exception as e:      # noqa: BLE001
            self.log("Could not return to the start position: %s" % e)

    def download_waiting(self, wait):
        deadline = time.monotonic() + wait
        got = 0
        while time.monotonic() < deadline:
            self.refresh_now()
            pending = self.props.get(sp.OBJECT_IN_MEMORY, 0)
            if pending & 0x8000:
                self.download()
                got += 1
                deadline = time.monotonic() + 3
                continue
            if got > 0 and pending == 0:
                return
            if got == 0:
                self.job_step = "Waiting for the camera…"
            time.sleep(0.2)
        if got == 0:
            self.log("No image arrived from the camera (check Save to)")

    def download(self):
        info = self._t(OP_GET_OBJECT_INFO, [SHOT_IN_MEMORY], want_data=True)
        if not info.ok():
            raise IOError("GetObjectInfo refused (0x%04x)" % info.code)
        size = struct.unpack_from("<I", info.data, 8)[0] if len(info.data) >= 12 else 0
        name = ""
        if len(info.data) > 52:
            r = sp.Reader(info.data)
            r.p = 52
            try:
                name = sp.read_string(r)
            except ValueError:
                name = ""
        name = datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + (name or "DSC%d.JPG" % int(time.time()))
        self.job_step = "Downloading %s (%.1f MB)" % (name, size / 1e6)
        r = self._t(OP_GET_OBJECT, [SHOT_IN_MEMORY], want_data=True)
        if not r.ok():
            raise IOError("GetObject refused (0x%04x)" % r.code)
        target = os.path.join(self.out_dir(), name)
        tmp = target + ".part"
        with open(tmp, "wb") as f:
            f.write(r.data)
        os.replace(tmp, target)
        self.last_path = target
        if name.lower().endswith((".jpg", ".jpeg")):
            self.job_jpegs.append(target)
        self.last_file = name
        self.log("Saved " + target)

    # ----------------------------------------------------------- live view
    def live_start(self):
        with self.lock:
            self.live_wanted = True
            self.live_error = ""
            if self.live_thread and self.live_thread.is_alive():
                return
            self.live_thread = threading.Thread(target=self._live_loop, name="live", daemon=True)
            self.live_thread.start()

    def live_stop(self):
        self.live_wanted = False

    def live_frame(self, since):
        j, seq = self.live_jpeg, self.live_seq
        if j is None or seq == int(since):
            return ""
        return "%d,%s" % (seq, base64.b64encode(j).decode("ascii"))

    def _live_loop(self):
        failures = 0
        while self.live_wanted:
            if self.ptp is None:
                self.live_error = "Camera not connected"
                break
            if self.job is not None:
                time.sleep(0.3)
                continue
            t0 = time.monotonic()
            try:
                with self.worker_lock:
                    r = self._t(OP_GET_OBJECT, [LIVE_VIEW], want_data=True)
                jpeg = live_jpeg(r.data) if r.ok() else None
                if jpeg:
                    self.live_jpeg, self.live_seq = jpeg, self.live_seq + 1
                    failures, self.live_error = 0, ""
                else:
                    failures += 1
                    self.live_error = "No picture in the live-view data" if r.ok() \
                        else "Camera refused live view (0x%04x)" % r.code
                    time.sleep(0.2)
            except Exception as e:      # noqa: BLE001
                failures += 1
                self.live_error = "Live view: %s" % e
                time.sleep(0.3)
            if failures >= 25:
                self.log("Live view stopped: " + self.live_error)
                self.live_wanted = False
                break
            spent = time.monotonic() - t0
            if spent < 0.1:
                time.sleep(0.1 - spent)

    # --------------------------------------------------------------- focus
    def focus_now(self, v):
        r = self._t(OP_SDIO_CONTROL, [sp.NEAR_FAR], encode(3, v))
        if not r.ok():
            raise IOError("Focus refused (0x%04x): set the lens to MF or DMF" % r.code)

    def focus(self, steps):
        v = max(-7, min(7, int(steps)))
        if v:
            self._bg(lambda: self.focus_now(v))

    def autofocus(self):
        def go():
            self.button(sp.AUTOFOCUS_BUTTON, 2)
            time.sleep(1.0)
            self.button(sp.AUTOFOCUS_BUTTON, 1)
        self._bg(go)

    # ------------------------------------------------------------- brackets
    def bracket(self, s, shots, ev):
        self.refresh_now()
        original = self.props.get(sp.SHUTTER, -1)
        base = s.bulb_seconds if sp.is_bulb(original) else exposure.seconds(original)
        if math.isnan(base):
            raise IOError("Unknown shutter speed: set it on the camera first")
        try:
            offs = exposure.offsets(shots, ev)
            for i, off in enumerate(offs):
                if self.stop_job:
                    break
                step = "Bracket %d of %d (%+.1f EV)" % (i + 1, len(offs), off)
                self.job_step = step + ": setting shutter"
                shot = self.set_exposure(base * 2 ** off, s)
                self.job_step = step
                self.shoot(shot)
        finally:
            stopped, self.stop_job = self.stop_job, False
            try:
                if original >= 0:
                    self.seek_shutter(original)
            except Exception as e:      # noqa: BLE001
                self.log("Could not restore the shutter speed: %s" % e)
            finally:
                self.stop_job = stopped

    def set_exposure(self, target, s):
        shot = ShotSettings()
        shot.autofocus, shot.bulb_seconds = s.autofocus, s.bulb_seconds
        if target > exposure.LONGEST_TIMED + 0.5:
            shot.bulb_seconds = target
            self.seek_shutter(0)
            if not sp.is_bulb(self.props.get(sp.SHUTTER, -1)):
                raise IOError("Could not set BULB for a %d s exposure" % round(target))
            return shot
        p = self.props.props.get(sp.SHUTTER)
        want = exposure.nearest(p.choices, target) if p else -1
        if want >= 0:
            self.seek_shutter(want)
        else:
            self.seek_by_steps(target)
        got = exposure.seconds(self.props.get(sp.SHUTTER, 0))
        if not math.isnan(got) and abs(exposure.stops(target, got)) > 0.4:
            self.log("Bracket: wanted %.4g s, camera is at %s" % (target, sp.shutter(self.props.get(sp.SHUTTER, 0))))
        return shot

    def seek_shutter(self, value):
        if self.props.get(sp.SHUTTER, -1) == value:
            return
        self.set_now(sp.SHUTTER, value)
        time.sleep(0.15)
        self.refresh_now()
        if self.props.get(sp.SHUTTER, -1) == value:
            return
        self.seek_by_steps(float("inf") if value == 0 else exposure.seconds(value))

    def _secs(self, v):
        return float("inf") if sp.is_bulb(v) else exposure.seconds(v)

    def seek_by_steps(self, target):
        direction, learned = 1, False
        for _ in range(60):
            if self.stop_job:
                return
            now = self.props.get(sp.SHUTTER, -1)
            cur = self._secs(now)
            if math.isinf(target) and math.isinf(cur):
                return
            if not math.isinf(target) and not math.isnan(cur) and not math.isinf(cur) \
                    and abs(exposure.stops(cur, target)) < 0.17:
                return
            longer = math.isinf(target) or (not math.isinf(cur) and target > cur)
            r = self._t(OP_SDIO_CONTROL, [sp.SHUTTER], bytes([0x01 if (direction if longer else -direction) > 0 else 0xFF]))
            if not r.ok():
                raise IOError("Shutter step refused (0x%04x)" % r.code)
            time.sleep(0.12)
            self.refresh_now()
            if not learned:
                after = self.props.get(sp.SHUTTER, -1)
                if after == now:
                    return
                if (self._secs(after) > cur) != longer:
                    direction = -direction
                learned = True

    # ----------------------------------------------------------------- jobs
    def run_job(self, name, work):
        with self.lock:
            if self.ptp is None:
                self.error = "Camera not connected"
                return False
            if self.job is not None:
                self.error = "Already running: " + self.job_name
                return False
            self.stop_job, self.job_name, self.job_step, self.error = False, name, "", ""

            def run():
                try:
                    with self.worker_lock:
                        work()
                    self.log(name + (" stopped" if self.stop_job else " done"))
                    if not self.stop_job:           # stopped on purpose: no alert
                        alerts.done(name, self.error)
                except Exception as e:      # noqa: BLE001
                    self.fail(name + " failed", e)
                    alerts.failed(name, self.error)
                finally:
                    try:
                        with self.worker_lock:
                            self.read_card()
                    finally:
                        with self.lock:
                            self.job, self.job_name, self.job_step = None, "", ""
            self.job = threading.Thread(target=run, name="camera-job", daemon=True)
            self.job.start()
            return True

    def stop(self):
        self.stop_job = True

    def shoot_once(self, o):
        s = ShotSettings(o)
        return self.run_job("Single shot", lambda: self.shoot(s))

    def start_interval(self, o):
        s = ShotSettings(o)
        count, interval = max(0, int(o.get("count", 10))), max(0.0, float(o.get("intervalSeconds", 5)))

        def work():
            i = 1
            while (count == 0 or i <= count) and not self.stop_job:
                t0 = time.monotonic()
                self.job_step = "Shot %d" % i if count == 0 else "Shot %d of %d" % (i, count)
                self.shoot(s)
                if count and i == count:
                    break
                wait = interval - (time.monotonic() - t0)
                if wait > 0 and not self._sleep(wait, "Next shot in"):
                    break
                i += 1
        return self.run_job("Interval", work)

    def start_head_job(self, o):
        """Star Tracker head job with this camera (D73): the head moves and waits at each frame ("waiting_ack"); this
        side shoots and downloads, then answers job.ack. If this side goes quiet the head pauses, still tracking."""
        job = o.get("job") or {}
        s = ShotSettings(o.get("shot") or job)

        def work():
            head = HeadClient()
            start = head.op("job.start", job)
            jid, frames = start.get("job_id"), start.get("frames", 0)
            self.log("Head job %s: %s frames" % (jid, frames))
            while not self.stop_job:
                st = head.op("job.status")
                state = st.get("state")
                if state in ("done", "stopped", "failed"):
                    self.log("Head job %s%s" % (state, ": " + st["reason"] if st.get("reason") else ""))
                    break
                if state == "waiting_ack":
                    frame = st.get("frame")
                    self.job_step = "Frame %s of %s" % (frame, frames)
                    self.shoot(s)
                    head.op("job.ack", {"job_id": jid, "frame": frame})
                else:
                    time.sleep(0.25)
            if self.stop_job:
                try:
                    head.op("job.stop")
                except Exception:  # noqa: BLE001
                    pass
        return self.run_job("Head job", work)

    def start_hdr(self, o):
        s = ShotSettings(o)
        shots, ev = max(1, int(o.get("hdrShots", 3))), max(0.3, float(o.get("hdrEv", 1)))
        return self.run_job("HDR", lambda: self.bracket(s, shots, ev))

    def start_panorama(self, o):
        """For each panel of the driver's grid (Alpaca Pilot → Settings →
        Panorama): move, settle, shoot. Panel numbers follow the grid's First
        Panel and Panel Order settings, so the driver decides the path."""
        s = ShotSettings(o)
        per = max(1, int(o.get("shotsPerPanel", 1)))
        settle, gap = max(0.0, float(o.get("settleSeconds", 3))), max(0.0, float(o.get("gapSeconds", 1)))
        first, last = max(1, int(o.get("firstPanel", 1))), max(0, int(o.get("lastPanel", 0)))
        hdr_shots, hdr_ev = max(1, int(o.get("hdrShots", 1))), max(0.3, float(o.get("hdrEv", 1)))
        back = bool(o.get("returnToStart", False))
        polaris = HeadClient()

        def work():
            start = self._start_position(polaris) if back else None
            try:
                self._panorama(polaris, s, first, last, per, settle, gap, hdr_shots, hdr_ev)
            finally:
                self._return_to(polaris, start)
        return self.run_job("Panorama", work)

    def start_sphere(self, o):
        """720° sphere: moves through the azimuth/altitude points planned on
        the Camera page (fewer frames towards the zenith, zenith last) and
        shoots at each, tracking off; HDR brackets per point if asked."""
        s = ShotSettings(o)
        settle = max(0.0, float(o.get("settleSeconds", 2)))
        hdr_shots, hdr_ev = max(1, int(o.get("hdrShots", 1))), max(0.3, float(o.get("hdrEv", 1)))
        back = bool(o.get("returnToStart", True))
        pts = [(float(p[0]), float(p[1])) for p in (o.get("points") or []) if isinstance(p, (list, tuple)) and len(p) >= 2]
        if not pts:
            self.error = "Plan the sphere first"
            return False
        polaris = HeadClient()

        def work():
            start = self._start_position(polaris) if back else None
            try:
                polaris.set_tracking(False)
                for i, (az, alt) in enumerate(pts):
                    if self.stop_job:
                        break
                    self.job_step = "Frame %d of %d: moving to %.0f° / %.0f°" % (i + 1, len(pts), az, alt)
                    polaris.slew_altaz(az, alt)
                    if not polaris.wait_while_slewing(lambda: self.stop_job, 180) or not self._sleep(settle, "Settling"):
                        break
                    self.job_step = "Frame %d of %d" % (i + 1, len(pts))
                    if hdr_shots > 1:
                        self.bracket(s, hdr_shots, hdr_ev)
                    else:
                        self.shoot(s)
            finally:
                self._return_to(polaris, start)
        return self.run_job("Sphere panorama", work)

    def start_mixed_panorama(self, o):
        """Two passes on the same anchored grid: foreground untracked (grid
        tracking 0), then the sky tracked (1 horizon-locked, 2 celestial),
        straight after or at skyAt (epoch ms). Only the grid's tracking
        changes between passes, so its position stays."""
        s = ShotSettings(o)
        per = max(1, int(o.get("shotsPerPanel", 1)))
        settle, gap = max(0.0, float(o.get("settleSeconds", 3))), max(0.0, float(o.get("gapSeconds", 1)))
        hdr_shots, hdr_ev = max(1, int(o.get("hdrShots", 1))), max(0.3, float(o.get("hdrEv", 1)))
        fg_first, fg_last = max(1, int(o.get("fgFirst", 1))), max(0, int(o.get("fgLast", 0)))
        sky_first, sky_last = max(1, int(o.get("skyFirst", 1))), max(0, int(o.get("skyLast", 0)))
        sky_track = 2 if int(o.get("skyTrack", 1)) == 2 else 1
        sky_at = float(o.get("skyAt", 0)) / 1000.0
        back = bool(o.get("returnToStart", False))
        polaris = HeadClient()

        def work():
            start = self._start_position(polaris) if back else None
            try:
                self.log("Pass 1: foreground, untracked")
                polaris.pano_grid({"track": 0})
                self._panorama(polaris, s, fg_first, fg_last, per, settle, gap, hdr_shots, hdr_ev)
                if self.stop_job:
                    return
                wait = sky_at - time.time()
                if wait > 0:
                    at = datetime.fromtimestamp(sky_at).strftime("%H:%M")
                    self.log("Sky pass at " + at)
                    if not self._sleep(wait, "Sky pass at %s ·" % at):
                        return
                self.log("Pass 2: sky, %s tracking" % ("celestial" if sky_track == 2 else "horizon-locked"))
                polaris.pano_grid({"track": sky_track})
                self._panorama(polaris, s, sky_first, sky_last, per, settle, gap, hdr_shots, hdr_ev)
            finally:
                self._return_to(polaris, start)
        return self.run_job("Two-pass panorama", work)

    def _panorama(self, polaris, s, first, last_wanted, per, settle, gap, hdr_shots, hdr_ev):
        panels = polaris.panel_count()
        last = panels if last_wanted == 0 else min(panels, last_wanted)
        if first > last:
            raise IOError("Start panel %d is after the stop panel %d" % (first, last))
        self.log("Panorama: panels %d–%d of %d, %d shot(s) each" % (first, last, panels, per))
        for panel in range(first, last + 1):
            if self.stop_job:
                break
            self.job_step = "Moving to panel %d of %d" % (panel, panels)
            polaris.slew_to_panel(panel)
            if not polaris.wait_while_slewing(lambda: self.stop_job, 180):
                break
            if not self._sleep(settle, "Panel %d: settling" % panel):
                break
            for k in range(1, per + 1):
                if self.stop_job:
                    break
                self.job_step = "Panel %d of %d: shot %d of %d" % (panel, panels, k, per)
                if hdr_shots > 1:
                    self.bracket(s, hdr_shots, hdr_ev)
                else:
                    self.shoot(s)
                if k < per and not self._sleep(gap, "Next shot in"):
                    break
            self.log("Panel %d done" % panel)

    def start_focus_stack(self, o):
        s = ShotSettings(o)
        shots, size = max(2, int(o.get("shots", 10))), max(1, min(7, int(o.get("size", 1))))
        pulses, direction = max(1, int(o.get("pulses", 2))), (-1 if int(o.get("direction", 1)) < 0 else 1)
        back, settle = bool(o.get("returnToStart", True)), max(0.0, float(o.get("settleSeconds", 0.5)))

        def work():
            moved = 0
            try:
                for i in range(1, shots + 1):
                    if self.stop_job:
                        break
                    self.job_step = "Focus stack: shot %d of %d" % (i, shots)
                    self.shoot(s)
                    if i == shots:
                        break
                    self.job_step = "Focus stack: moving focus"
                    for _ in range(pulses):
                        if self.stop_job:
                            break
                        self.focus_now(direction * size)
                        moved += 1
                        time.sleep(0.12)
                    time.sleep(settle)
            finally:
                if back and moved and self.ptp is not None:
                    self.job_step = "Returning focus"
                    try:
                        for _ in range(moved):
                            self.focus_now(-direction * size)
                            time.sleep(0.12)
                    except IOError as e:
                        self.log("Could not return the focus: %s" % e)
        return self.run_job("Focus stack", work)

    def start_path_lapse(self, o):
        s = ShotSettings(o)
        shots, interval = max(2, int(o.get("shots", 60))), max(0.0, float(o.get("intervalSeconds", 5)))
        settle = max(0.0, float(o.get("settleSeconds", 1)))
        keys = [[float(p[0]), float(p[1])] for p in (o.get("points") or []) if len(p) >= 2]
        if len(keys) < 2:
            self.error = "Add at least two positions for a path-lapse"
            return False
        route = pathlapse.positions(keys, shots)
        polaris = HeadClient()

        def work():
            polaris.set_tracking(False)
            for i, p in enumerate(route):
                if self.stop_job:
                    break
                t0 = time.monotonic()
                self.job_step = "Shot %d of %d: moving to %.1f° / %.1f°" % (i + 1, len(route), p[0], p[1])
                polaris.slew_altaz(p[0], p[1])
                if not polaris.wait_while_slewing(lambda: self.stop_job, 120) or not self._sleep(settle):
                    break
                self.job_step = "Shot %d of %d" % (i + 1, len(route))
                self.shoot(s)
                wait = interval - (time.monotonic() - t0)
                if i + 1 < len(route) and wait > 0 and not self._sleep(wait, "Next shot in"):
                    break
        return self.run_job("Path-lapse", work)

    def start_scheduled(self, o):
        s = ShotSettings(o)
        start_at = float(o.get("startAt", time.time() * 1000)) / 1000
        end_at = float(o.get("endAt", (start_at + 3600) * 1000)) / 1000
        interval, track = max(1.0, float(o.get("intervalSeconds", 10))), bool(o.get("trackSun", False))
        az, alt = o.get("az"), o.get("alt")
        if end_at <= start_at:
            self.error = "The end time must be after the start time"
            return False
        polaris = HeadClient()

        def clock(sec):
            sec = max(0, int(sec))
            return "%d:%02d:%02d" % (sec // 3600, sec // 60 % 60, sec % 60)

        def work():
            if az is not None and alt is not None and not track:
                self.job_step = "Moving into position"
                polaris.set_tracking(False)
                polaris.slew_altaz(float(az), float(alt))
                if not polaris.wait_while_slewing(lambda: self.stop_job, 180):
                    return
            while not self.stop_job and time.time() < start_at:
                self.job_step = "Starts in " + clock(start_at - time.time())
                time.sleep(min(1.0, max(0.001, start_at - time.time())))
            if self.stop_job:
                return
            if track:
                self.job_step = "Moving to the Sun"
                polaris.track_orbital("Sun")
                time.sleep(1)
                polaris.wait_while_slewing(lambda: self.stop_job, 180)
            i = 0
            while not self.stop_job and time.time() < end_at:
                t0 = time.monotonic()
                i += 1
                self.job_step = "Shot %d · ends in %s" % (i, clock(end_at - time.time()))
                self.shoot(s)
                wait = min(interval - (time.monotonic() - t0), max(0.0, end_at - time.time()))
                if wait > 0 and not self._sleep(wait, "Next shot in"):
                    break
        return self.run_job("Sun timelapse", work)

    def start_people_remover(self, o):
        s = ShotSettings(o)
        shots, interval = max(3, min(30, int(o.get("shots", 10)))), max(0.0, float(o.get("intervalSeconds", 3)))
        sample = 1 if int(o.get("sample", 2)) == 1 else 2
        merge = bool(o.get("merge", True))
        if merge and self.props.get(sp.SAVE_DESTINATION, sp.DEST_CARD) not in (sp.DEST_TABLET, sp.DEST_BOTH):
            self.error = "People Remover merges on the computer: set Save to “Card + computer” first"
            return False

        def work():
            self.job_jpegs = []
            for i in range(1, shots + 1):
                if self.stop_job:
                    break
                t0 = time.monotonic()
                self.job_step = "Shot %d of %d · keep the camera still" % (i, shots)
                self.shoot(s)
                wait = interval - (time.monotonic() - t0)
                if i < shots and wait > 0 and not self._sleep(wait, "Next shot in"):
                    break
            if not merge or self.stop_job:
                return
            jpegs = list(self.job_jpegs)
            if len(jpegs) < 3:
                raise IOError("Only %d JPEGs arrived: set the camera to JPEG or RAW+JPEG" % len(jpegs))
            self.job_step = "Merging %d shots…" % len(jpegs)

            def progress(pct):
                self.job_step = "Merging %d shots… %d%%" % (len(jpegs), pct)
            img = median.merge(jpegs, sample, progress)
            name = datetime.now().strftime("%Y%m%d-%H%M%S") + "_PEOPLE-REMOVED.JPG"
            img.save(os.path.join(self.out_dir(), name), quality=95)
            self.last_file = name
            self.log("People Remover: saved %s (%d × %d)" % (name, img.size[0], img.size[1]))
        return self.run_job("People Remover", work)

    # ------------------------------------------------- Holy Grail timelapse
    def start_holy_grail(self, o):
        """Interval shooting that keeps the exposure right through sunset or
        sunrise: after each frame its brightness is measured (from the file
        on the computer, else from live view) and the shutter or ISO moves by
        1/3-stop notches. The night is made nightDarker stops darker than the
        day (by the Sun's altitude). Aperture is never touched."""
        s = ShotSettings(o)
        count = max(0, int(o.get("count", 0)))
        interval = max(1.0, float(o.get("intervalSeconds", 10)))
        max_shutter = max(0.01, min(exposure.LONGEST_TIMED, float(o.get("maxShutter", 15))))
        min_iso = max(50.0, float(o.get("minIso", 100)))
        max_iso = max(min_iso, float(o.get("maxIso", 3200)))
        night_darker = float(o.get("nightDarker", 2))
        lat, lon = o.get("lat"), o.get("lon")
        has_loc = isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and not (math.isnan(lat) or math.isnan(lon))

        def work():
            self.refresh_now()
            if sp.is_bulb(self.props.get(sp.SHUTTER, -1)):
                raise IOError("Set a shutter speed (not BULB) and ISO in the camera's M mode first")
            if self._iso_now() <= 0:
                raise IOError("Set ISO to a number (not AUTO) in the camera's M mode first")
            from_files = self.props.get(sp.SAVE_DESTINATION, sp.DEST_CARD) in (sp.DEST_TABLET, sp.DEST_BOTH)
            self.log("Holy Grail: measuring brightness from " + ("each downloaded picture" if from_files else
                     "live view (less exact at night: set Save to Card + computer)")
                     + ("" if has_loc else "; no location, so the night is not darkened"))
            ramp = hg.HolyGrail(night_darker if has_loc else 0)
            i = 1
            while (count == 0 or i <= count) and not self.stop_job:
                t0 = time.monotonic()
                self.job_step = ("Frame %d" % i if count == 0 else "Frame %d of %d" % (i, count)) + " · " + self._settings_text()
                seconds = exposure.seconds(self.props.get(sp.SHUTTER, 0))
                iso = self._iso_now()
                self.last_path = None
                self.shoot(s)
                ev = self._measure_file(self.last_path) if from_files else float("nan")
                if math.isnan(ev):
                    ev = self._measure_live_view()
                if math.isnan(ev):
                    self.log("Frame %d: brightness not measured, exposure unchanged" % i)
                else:
                    alt = hg.sun_altitude(lat, lon, time.time()) if has_loc else float("nan")
                    st = ramp.frame(ev, seconds, iso, alt)
                    moved = self._move_exposure(st.notches, max_shutter, min_iso, max_iso) if st.notches else ""
                    self.log("Frame %d: %s, error %+.2f EV%s%s" % (i, self._settings_text(), st.error,
                             "" if math.isnan(alt) else ", Sun %.1f°" % alt, moved))
                if count and i == count:
                    break
                wait = interval - (time.monotonic() - t0)
                if wait > 0 and not self._sleep(wait, "Next frame in"):
                    break
                i += 1
        return self.run_job("Holy Grail", work)

    def _iso_now(self):
        v = self.props.get(sp.ISO, 0)
        return -1 if v == 0xFFFFFF or v <= 0 else v

    def _settings_text(self):
        return sp.shutter(self.props.get(sp.SHUTTER, 0)) + " " + sp.iso(self.props.get(sp.ISO, 0))

    def _move_exposure(self, notches, max_shutter, min_iso, max_iso):
        """Moves the exposure by 1/3-stop notches (+ brighter). Brighter:
        shutter first, then ISO. Darker: ISO first, then shutter."""
        note = ""
        third = 2 ** (1 / 3.0)
        for _ in range(abs(notches)):
            if self.stop_job:
                break
            brighter = notches > 0
            self.refresh_now()
            sec, iso = exposure.seconds(self.props.get(sp.SHUTTER, 0)), self._iso_now()
            if brighter:
                done = sec * third <= max_shutter * 1.05 and self._nudge_shutter(True)
                if not done:
                    done = iso * third <= max_iso * 1.05 and self._nudge_iso(True)
            else:
                done = iso / third >= min_iso * 0.95 and self._nudge_iso(False)
                if not done:
                    done = self._nudge_shutter(False)
            if not done:
                note = "; at the limit (max shutter and ISO)" if brighter else "; at the limit (shortest shutter, lowest ISO)"
                break
        self.refresh_now()
        return note or " -> " + self._settings_text()

    def _nudge_shutter(self, longer):
        """Shutter to the next listed speed longer or shorter (else one dial
        step towards 1/3 stop away). False when it could not move."""
        now = self.props.get(sp.SHUTTER, -1)
        cur = exposure.seconds(now)
        if math.isnan(cur):
            return False
        target = cur * 2 ** ((1 if longer else -1) / 3.0)
        if target > exposure.LONGEST_TIMED + 0.5:
            return False
        p = self.props.props.get(sp.SHUTTER)
        speeds = [(exposure.seconds(c), c) for c in (p.choices if p else []) if not sp.is_bulb(c)]
        speeds = [(sec, c) for sec, c in speeds if not math.isnan(sec)]
        if longer:
            nxt = min((x for x in speeds if x[0] > cur * 1.02), default=None)
        else:
            nxt = max((x for x in speeds if x[0] < cur / 1.02), default=None)
        if nxt is not None:
            if nxt[0] > exposure.LONGEST_TIMED + 0.5:
                return False
            self.seek_shutter(nxt[1])
        else:
            self.seek_by_steps(target)
        return self.props.get(sp.SHUTTER, -1) != now

    def _nudge_iso(self, higher):
        now = self.props.get(sp.ISO, -1)
        p = self.props.props.get(sp.ISO)
        if p is not None and p.choices:
            best = -1
            for c in p.choices:
                if c == 0xFFFFFF or c <= 0:
                    continue
                if (c > now and (best < 0 or c < best)) if higher else (c < now and (best < 0 or c > best)):
                    best = c
            if best < 0:
                return False
            self.set_now(sp.ISO, best)
            time.sleep(0.15)
            self.refresh_now()
            if self.props.get(sp.ISO, -1) != now:
                return True
        orig = now                 # no list or not accepted: turn the ISO dial, learning its direction
        for _ in range(3):
            up = (self.iso_dial_dir if higher else -self.iso_dial_dir) > 0
            r = self._t(OP_SDIO_CONTROL, [sp.ISO], bytes([0x01 if up else 0xFF]))
            if not r.ok():
                return False
            time.sleep(0.15)
            self.refresh_now()
            after = self.props.get(sp.ISO, -1)
            if after == now:
                return False
            if after != 0xFFFFFF and (after > orig if higher else after < orig):
                return True
            if (after > now) != higher:
                self.iso_dial_dir = -self.iso_dial_dir
            now = after
        return False

    @staticmethod
    def _open_image(path, max_side=None):
        """A JPEG (or the largest JPEG preview inside a RAW file) as a PIL image, or None."""
        from PIL import Image
        if not path:
            return None
        try:
            if path.lower().endswith((".jpg", ".jpeg")):
                img = Image.open(path)
            else:
                with open(path, "rb") as f:
                    data = f.read()
                best, start = None, data.find(b"\xff\xd8\xff")
                while start >= 0:
                    end = data.find(b"\xff\xd9", start)
                    if end < 0:
                        break
                    if best is None or end - start > best[1] - best[0]:
                        best = (start, end + 2)
                    start = data.find(b"\xff\xd8\xff", end)
                if best is None:
                    return None
                import io
                img = Image.open(io.BytesIO(data[best[0]:best[1]]))
            if max_side:
                img.draft("RGB", (max_side, max_side))
                img = img.convert("RGB")
                if max(img.size) > max_side:
                    img.thumbnail((max_side, max_side))
            return img.convert("RGB")
        except Exception:      # noqa: BLE001
            return None

    def _measure_file(self, path):
        img = self._open_image(path, 480)
        if img is None:
            if path:
                self.log("Brightness from file failed: %s" % os.path.basename(path))
            return float("nan")
        return hg.picture_ev(img)

    def _measure_live_view(self):
        try:
            from PIL import Image
            import io
            r = self._t(OP_GET_OBJECT, [LIVE_VIEW], want_data=True)
            jpeg = live_jpeg(r.data) if r.ok() else None
            return hg.picture_ev(Image.open(io.BytesIO(jpeg))) if jpeg else float("nan")
        except Exception:      # noqa: BLE001
            return float("nan")

    # ------------------------------------------------------- video, astro
    def start_video(self, o):
        """Starts the camera's movie recording, keeps it running for minutes
        (0 = until Stop), then stops it. The clip stays on the camera's card."""
        minutes = max(0.0, float(o.get("minutes", 0)))

        def work():
            self.button(MOVIE_BUTTON, 2)
            self.log("Recording started" + (" for %.1f min" % minutes if minutes else ""))
            t0 = time.monotonic()
            until = t0 + minutes * 60 if minutes else float("inf")
            try:
                while not self.stop_job and time.monotonic() < until:
                    sec = int(time.monotonic() - t0)
                    self.job_step = "Recording %d:%02d" % (sec // 60, sec % 60)
                    time.sleep(0.5)
            finally:
                self.button(MOVIE_BUTTON, 1)
                sec = int(time.monotonic() - t0)
                self.log("Recording stopped after %d:%02d (clip on the camera's card)" % (sec // 60, sec % 60))
        return self.run_job("Video", work)

    def start_astro(self, o):
        """count exposures of a tracked target; every ditherEvery frames the
        Polaris is nudged a few arcseconds in a random direction (pulse
        guiding) so noise and hot pixels stack away, then it settles."""
        s = ShotSettings(o)
        count = max(1, int(o.get("count", 30)))
        gap = max(0.0, float(o.get("gapSeconds", 2)))
        dither_every = max(0, int(o.get("ditherEvery", 3)))
        dither_ms = max(200, min(8000, int(o.get("ditherMs", 2000))))
        settle = max(0.0, float(o.get("settleSeconds", 5)))
        polaris = HeadClient()
        rnd = random.Random()

        def work():
            can_dither = dither_every > 0
            if can_dither:
                try:
                    if not polaris.tracking():
                        self.log("The Polaris is not tracking: no dithering (and stars will trail). Go to the target first.")
                        can_dither = False
                except Exception:      # noqa: BLE001
                    self.log("Polaris driver not reachable: no dithering")
                    can_dither = False
            for i in range(1, count + 1):
                if self.stop_job:
                    break
                self.job_step = "Frame %d of %d" % (i, count)
                self.shoot(s)
                if i == count:
                    break
                if can_dither and i % dither_every == 0:
                    self.job_step = "Dithering"
                    try:
                        ra, dec = int(dither_ms * (0.5 + rnd.random())), int(dither_ms * (0.5 + rnd.random()))
                        polaris.pulse_guide(2 if rnd.random() < 0.5 else 3, ra)
                        self._wait_pulse(polaris, ra)
                        polaris.pulse_guide(0 if rnd.random() < 0.5 else 1, dec)
                        self._wait_pulse(polaris, dec)
                        if not self._sleep(settle, "Settling after dither"):
                            break
                    except Exception as e:      # noqa: BLE001
                        self.log("Dither failed: %s" % e)
                if gap > 0 and not self._sleep(gap, "Next frame in"):
                    break
        return self.run_job("Astro sequence", work)

    def _wait_pulse(self, polaris, ms):
        until = time.monotonic() + ms / 1000.0 + 15
        time.sleep(ms / 1000.0)
        while polaris.pulse_guiding() and time.monotonic() < until and not self.stop_job:
            time.sleep(0.1)

    def start_darks(self, o):
        """Dark frames: the same exposure with the lens covered, no Polaris movement."""
        s = ShotSettings(o)
        count, gap = max(1, int(o.get("count", 20))), max(0.0, float(o.get("gapSeconds", 2)))

        def work():
            for i in range(1, count + 1):
                if self.stop_job:
                    break
                self.job_step = "Dark %d of %d" % (i, count)
                self.shoot(s)
                if i < count and gap > 0 and not self._sleep(gap, "Next dark in"):
                    break
        return self.run_job("Dark frames", work)

    # --------------------------------------------------------- star trails
    def start_trails(self, o):
        """Interval shots blended as they arrive, keeping the brightest value
        of every pixel (lighten), so the trails grow on screen. Needs JPEGs on
        the computer. The blend is saved at the end; single frames stay too."""
        s = ShotSettings(o)
        count = max(2, int(o.get("count", 120)))
        interval = max(0.0, float(o.get("intervalSeconds", 0)))

        def work():
            from PIL import ImageChops
            blend, used = None, 0
            self.trails_jpeg = None
            self.job_jpegs = []
            try:
                for i in range(1, count + 1):
                    if self.stop_job:
                        break
                    t0 = time.monotonic()
                    self.job_step = "Frame %d of %d%s" % (i, count, " · %d blended" % used if used else "")
                    before = len(self.job_jpegs)
                    self.shoot(s)
                    img = self._open_image(self.job_jpegs[-1], 2000) if len(self.job_jpegs) > before else None
                    if img is None:
                        if i == 1:
                            self.log("Star trails: no JPEG reached the computer, nothing to blend "
                                     "(set Save to Card + computer, with JPEG)")
                    else:
                        if blend is None:
                            blend = img
                            used = 1
                        elif img.size == blend.size:
                            blend = ImageChops.lighter(blend, img)
                            used += 1
                        if used % 3 == 1 or i == count:
                            self._publish_trails(blend)
                    if i == count:
                        break
                    wait = interval - (time.monotonic() - t0)
                    if wait > 0 and not self._sleep(wait, "Next frame in"):
                        break
            finally:
                if blend is not None and used > 1:
                    name = datetime.now().strftime("%Y%m%d-%H%M%S") + "_StarTrails_%d.jpg" % used
                    blend.save(os.path.join(self.out_dir(), name), quality=95)
                    self.last_file = name
                    self.log("Saved %s (%d frames blended)" % (name, used))
        return self.run_job("Star trails", work)

    def _publish_trails(self, blend):
        import io
        small = blend.copy()
        small.thumbnail((900, 900))
        buf = io.BytesIO()
        small.save(buf, "JPEG", quality=80)
        self.trails_jpeg, self.trails_seq = buf.getvalue(), self.trails_seq + 1

    def trails_frame(self, since):
        j, seq = self.trails_jpeg, self.trails_seq
        if j is None or seq == int(since):
            return ""
        return "%d,%s" % (seq, base64.b64encode(j).decode("ascii"))

    # ------------------------------------------------------- plate solving
    def last_solve(self):
        return self.last_solve_json

    def _catalog(self):
        if self.star_catalog is None:
            self.star_catalog = plate_solver.Catalog.read(catalog_file())
        return self.star_catalog

    def start_solve(self, o):
        """action: "solve" (shoot a frame and find where it points), "sync"
        (and tell the driver), "goto" (sync, then go to targetRa hours /
        targetDec degrees J2000, or back to where the Polaris thought it
        pointed), "align" (solve and sync at three sky positions). Needs a
        JPEG on the computer and the lens focal length."""
        s = ShotSettings(o)
        action = str(o.get("action", "solve"))
        focal, sensor_w = float(o.get("focal", 0) or 0), float(o.get("sensorWidth", 36) or 36)
        radius = max(3.0, min(25.0, float(o.get("searchRadius", 8))))
        target_ra, target_dec = o.get("targetRa"), o.get("targetDec")
        if not focal > 0:
            self.error = "Set the lens focal length (Live view → Lens) first"
            return False
        plane_w = math.degrees(sensor_w / focal)
        polaris = HeadClient()

        def work():
            if action == "align":
                self._auto_align(polaris, s, plane_w, radius)
                return
            hint = self._hint_j2000(polaris)
            sol = self._shoot_and_solve(s, hint, plane_w, radius)
            if sol is None or action not in ("sync", "goto"):
                return
            polaris.j2000_sync(sol.ra / 15, sol.dec)
            self.log("Synced the Polaris to the solved position")
            if action == "goto":
                ra = hint[0] / 15 if not isinstance(target_ra, (int, float)) else float(target_ra)
                dec = hint[1] if not isinstance(target_dec, (int, float)) else float(target_dec)
                self.job_step = "Going to the target"
                polaris.set_tracking(True)
                polaris.j2000_goto("target", ra, dec)
                time.sleep(1)
                polaris.wait_while_slewing(lambda: self.stop_job, 180)
                self.log("Re-centred on RA %.4fh Dec %+.3f°" % (ra, dec))
        return self.run_job("Auto-align" if action == "align" else "Plate solve", work)

    @staticmethod
    def _hint_j2000(polaris):
        ra, dec = polaris.ra_dec()
        if math.isnan(ra) or math.isnan(dec):
            raise IOError("The Polaris position is not known (driver connected?)")
        return plate_solver.to_j2000(ra * 15, dec, time.time())

    def _shoot_and_solve(self, s, hint, plane_w, radius):
        import numpy as np
        before = len(self.job_jpegs)
        self.job_step = "Plate solve: taking the picture"
        self.shoot(s)
        if len(self.job_jpegs) <= before:
            raise IOError("No JPEG reached the computer: set Save to Card + computer, with JPEG or RAW+JPEG")
        self.job_step = "Plate solve: finding stars"
        img = self._open_image(self.job_jpegs[-1], 3000)
        if img is None:
            raise IOError("Could not read the picture")
        px = np.asarray(img, dtype=np.float32)
        lum = 0.2126 * px[:, :, 0] + 0.7152 * px[:, :, 1] + 0.0722 * px[:, :, 2]
        stars = plate_solver.detect(lum, 60)
        self.log("Plate solve: %d stars found in the picture" % len(stars))
        if len(stars) < 8:
            self.log("Too few stars: expose longer or raise ISO (and check focus and clouds)")
            return None
        self.job_step = "Plate solve: matching the catalogue"
        cat = self._catalog()
        h, w = lum.shape
        long_lens = plane_w <= ASTAP_FIRST_BELOW_DEG
        sol = None
        if long_lens and astap.ASTAP.available():         # D74: ASTAP first for 300-600 mm
            sol = self._astap_solve(self.job_jpegs[-1], hint, plane_w, w, h, radius)
        if sol is None:
            sol = plate_solver.solve(cat, stars, w, h, hint[0], hint[1], radius, plane_w, 0.25)
        if sol is None and radius < 15:
            self.job_step = "Plate solve: searching wider"
            sol = plate_solver.solve(cat, stars, w, h, hint[0], hint[1], 15, plane_w, 0.3)
        if sol is None and not long_lens and astap.ASTAP.available():
            sol = self._astap_solve(self.job_jpegs[-1], hint, plane_w, w, h, max(radius, 15))
        if sol is None:
            self.log("Not solved. Check the lens focal length, that the Polaris is roughly aligned (within ~10°), "
                     "and that stars are sharp")
            self.last_solve_json = json.dumps({"ok": False, "time": int(time.time() * 1000)})
            return None
        off = plate_solver.project(sol.ra, sol.dec, hint[0], hint[1])
        off_deg = math.hypot(*off) if off else float("nan")
        self.log("Solved: RA %s Dec %s, field %.2f°×%.2f°, %d stars matched, %.1f\" rms; the Polaris was %.2f° off" % (
            _hms(sol.ra / 15), _dms(sol.dec), sol.fovW, sol.fovH, sol.matched, sol.rmsArcsec, off_deg))
        self.last_solve_json = json.dumps({
            "ok": True, "time": int(time.time() * 1000), "ra": sol.ra / 15, "dec": sol.dec,
            "raText": _hms(sol.ra / 15), "decText": _dms(sol.dec), "roll": sol.roll, "fovW": sol.fovW,
            "fovH": sol.fovH, "matched": sol.matched, "stars": len(stars), "rms": sol.rmsArcsec,
            "offset": None if math.isnan(off_deg) else off_deg, "ms": sol.millis})
        return sol

    def _astap_solve(self, jpeg, hint, plane_w, w, h, radius):
        """ASTAP's command-line solver with D05 (Windows, long lenses). Returns a plate_solver.Solution or None."""
        self.job_step = "Plate solve: ASTAP"
        try:
            r = astap.ASTAP.solve(jpeg, hint[0], hint[1], plane_w * h / w, radius)
        except Exception as e:                        # noqa: BLE001
            self.log("ASTAP did not run: %s" % e)
            return None
        if r is None:
            self.log("ASTAP: not solved")
            return None
        self.log("ASTAP solved in %.1f s" % (r["millis"] / 1000))
        # ASTAP reads the full-size JPEG, star detection a reduced copy: report the field from the lens, not pixels
        return plate_solver.Solution(ra=r["ra"], dec=r["dec"], roll=r["roll"], scale=plane_w / w,
                                     fovW=plane_w, fovH=plane_w * h / w, matched=0, rmsArcsec=0.0, millis=r["millis"])

    def _auto_align(self, polaris, s, plane_w, radius):
        """Solve and sync at three positions (here, then 60° either side in
        azimuth at a safe altitude): a multi-point alignment. Then back to
        the start, tracking."""
        start = self._start_position(polaris)
        if start is None:
            raise IOError("The Polaris position is not known (driver connected?)")
        alt = max(30.0, min(65.0, start[1]))
        points = [(start[0], start[1]), (start[0] + 60, alt), (start[0] - 60, alt)]
        synced = 0
        for i, (az, al) in enumerate(points):
            if self.stop_job:
                break
            if i > 0:
                self.job_step = "Auto-align %d of 3: moving" % (i + 1)
                polaris.set_tracking(False)
                polaris.slew_altaz(az, al)
                time.sleep(0.8)
                if not polaris.wait_while_slewing(lambda: self.stop_job, 180):
                    break
            polaris.set_tracking(True)
            if not self._sleep(3, "Settling"):
                break
            sol = self._shoot_and_solve(s, self._hint_j2000(polaris), plane_w, radius)
            if sol is None:
                self.log("Auto-align point %d not solved: skipped" % (i + 1))
                continue
            polaris.j2000_sync(sol.ra / 15, sol.dec)
            synced += 1
            self.log("Auto-align point %d synced" % (i + 1))
        self.log("Auto-align: %d of 3 points synced%s" % (synced, " (multi-point alignment)" if synced >= 2 else ""))
        if not self.stop_job:
            polaris.set_tracking(False)
            polaris.slew_altaz(start[0], start[1])
            time.sleep(0.8)
            polaris.wait_while_slewing(lambda: self.stop_job, 180)
            polaris.set_tracking(True)

    # -------------------------------------------------------------- status
    def status(self):
        o = {"state": self.state, "model": self.model, "error": self.error, "job": self.job_name,
             "step": self.job_step, "shots": self.shots, "lastFile": self.last_file, "card": self.card,
             "live": self.live_wanted, "liveError": self.live_error}
        settings = {}
        for code in (sp.EXPOSURE_PROGRAM, sp.SHUTTER, sp.F_NUMBER, sp.ISO, sp.FOCUS_MODE, sp.EXPOSURE_COMP,
                     sp.WHITE_BALANCE, sp.COLOR_TEMP, sp.BATTERY, sp.SAVE_DESTINATION):
            p = self.props.props.get(code)
            if p is None:
                continue
            settings[str(code)] = {"code": code, "value": p.value, "text": sp.fmt(code, p.value),
                                   "writable": p.writable,
                                   "choices": [[c, sp.fmt(code, c)] for c in p.choices]}
        o["settings"] = settings
        o["bulb"] = sp.is_bulb(self.props.get(sp.SHUTTER, -1))
        o["log"] = list(self.log_lines)
        return json.dumps(o)

    def diagnostics(self):
        lines = ["Canopus (Windows) camera diagnostics", "Model: " + self.model,
                 "Settings parse: " + (self.props.parse_problem or "ok"), "Properties:"]
        for p in self.props.props.values():
            lines.append("  %04x type %04x %s%s = %s (%s) choices %d" % (
                p.code, p.type, "rw" if p.writable else "r-", "" if p.enabled else " disabled",
                p.text if p.text is not None else p.value, sp.fmt(p.code, p.value), len(p.choices)))
        lines.append("Log:")
        lines += ["  " + l for l in self.log_lines]

        def hexdump(d, mx):
            out = []
            for i in range(0, min(len(d), mx), 32):
                out.append("  %05x %s" % (i, " ".join("%02x" % b for b in d[i:i + 32])))
            if len(d) > mx:
                out.append("  …")
            return out
        lines.append("ExtDeviceInfo (%d bytes):" % len(self.last_info))
        lines += hexdump(self.last_info, 512)
        lines.append("AllProps (%d bytes):" % len(self.last_props))
        lines += hexdump(self.last_props, 8192)
        return "\n".join(lines)
