"""The calls the shared UI makes on Windows: window.StNative (st_bridge.py) and window.CameraNative, answered as
CameraBridge.java answers them on Android. open_sony and CameraBridge are Benro-Polaris-Controller's (D12)."""
import json

from . import gallery
from .paths import pictures_dir
from .sony import SonyCamera
from .st_bridge import StBridge


def _err(e):
    return str(e) or e.__class__.__name__


def open_sony():
    """Opens the first Sony camera Windows sees (PC Remote mode)."""
    from .ptp_win import WpdTransport, list_devices
    devices = list_devices()
    for dev_id, name, maker in devices:
        if "sony" in maker.lower() or name.upper().startswith(("ILCE", "ILME", "DSC-", "ZV-")):
            return WpdTransport(dev_id), name
    raise IOError("No Sony camera found. Check the cable and set USB Connection Mode to Remote Shooting.")


class CameraBridge:
    def __init__(self, camera: SonyCamera):
        self.c = camera

    def connect(self):
        if self.c.is_connected():
            return "ok"
        try:
            from .ptp_win import list_devices
            if not any("sony" in m.lower() or n.upper().startswith(("ILCE", "ILME", "DSC-", "ZV-"))
                       for _, n, m in list_devices()):
                return "none"
        except OSError:
            return "none"
        return self.c.connect()

    def disconnect(self):
        self.c.disconnect()

    def status(self):
        return self.c.status()

    def refresh(self):
        self.c.refresh()

    def step(self, code, direction):
        self.c.step(int(code), int(direction))

    def set(self, code, value):
        self.c.set(int(code), int(value))

    def shoot(self, o):
        return self.c.shoot_once(json.loads(o or "{}"))

    def startInterval(self, o):
        return self.c.start_interval(json.loads(o or "{}"))

    def startPanorama(self, o):
        return self.c.start_panorama(json.loads(o or "{}"))

    def startHdr(self, o):
        return self.c.start_hdr(json.loads(o or "{}"))

    def startFocusStack(self, o):
        return self.c.start_focus_stack(json.loads(o or "{}"))

    def startPathLapse(self, o):
        return self.c.start_path_lapse(json.loads(o or "{}"))

    def startScheduled(self, o):
        return self.c.start_scheduled(json.loads(o or "{}"))

    def startPeopleRemover(self, o):
        return self.c.start_people_remover(json.loads(o or "{}"))

    def startSolve(self, o):
        return self.c.start_solve(json.loads(o or "{}"))

    def lastSolve(self):
        return self.c.last_solve()

    def startTrails(self, o):
        return self.c.start_trails(json.loads(o or "{}"))

    def trailsFrame(self, since):
        return self.c.trails_frame(int(since))

    def startAstro(self, o):
        return self.c.start_astro(json.loads(o or "{}"))

    def startDarks(self, o):
        return self.c.start_darks(json.loads(o or "{}"))

    def startVideo(self, o):
        return self.c.start_video(json.loads(o or "{}"))

    def startHolyGrail(self, o):
        return self.c.start_holy_grail(json.loads(o or "{}"))

    def startSphere(self, o):
        return self.c.start_sphere(json.loads(o or "{}"))

    def startMixedPanorama(self, o):
        return self.c.start_mixed_panorama(json.loads(o or "{}"))

    def liveStart(self):
        self.c.live_start()

    def liveStop(self):
        self.c.live_stop()

    def liveFrame(self, since):
        return self.c.live_frame(int(since))

    def focus(self, steps):
        self.c.focus(int(steps))

    def autofocus(self):
        self.c.autofocus()

    def stopJob(self):
        self.c.stop()

    def diagnostics(self):
        return self.c.diagnostics()

    def gallery(self):
        return gallery.listing()

    def galleryThumb(self, name):
        return gallery.thumb(name)

    def startHeadJob(self, o):
        """Star Tracker: a head job shot by this camera (D73): the head moves and waits, this side shoots and acks."""
        return self.camera.start_head_job(o)

    def galleryOpen(self, name, mime=None):
        return gallery.open_file(name)


def make_bridges():
    return {"st": StBridge(), "camera": CameraBridge(SonyCamera(open_sony, pictures_dir))}
