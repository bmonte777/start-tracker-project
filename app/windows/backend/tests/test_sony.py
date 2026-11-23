import json
import os
import sys
import tempfile
import time
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from startracker_desktop import sony_props as sp  # noqa: E402
from startracker_desktop.sony import SonyCamera  # noqa: E402
from fake_sony import FakeSony, jpeg  # noqa: E402


def wait(cond, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


class SonyTest(unittest.TestCase):
    def make(self, **kw):
        self.out = tempfile.mkdtemp()
        self.fake = FakeSony(**kw)
        cam = SonyCamera(lambda: (self.fake, "ILCE-7RM5 (fake)"), lambda: self.out)
        cam.connect()
        self.assertTrue(wait(lambda: cam.state == "connected"), cam.error)
        wait(lambda: cam.card != "")
        return cam

    def run_job(self, cam, started, timeout=30):
        self.assertTrue(started, cam.error)
        self.assertTrue(wait(lambda: cam.job is None, timeout), "job did not finish")
        self.assertEqual(cam.error, "", cam.error)

    def test_connect_and_status(self):
        cam = self.make()
        st = json.loads(cam.status())
        self.assertEqual(st["state"], "connected")
        self.assertEqual(st["settings"][str(sp.SHUTTER)]["text"], "1/125")
        self.assertEqual(st["settings"][str(sp.SAVE_DESTINATION)]["text"], "Card + computer")
        self.assertIn("128 GB", st["card"])
        self.assertIn("Sony remote protocol 3.00", "\n".join(st["log"]))

    def test_single_shot_downloads_raw_and_jpeg(self):
        cam = self.make()
        self.run_job(cam, cam.shoot_once({}))
        self.assertEqual(sorted(f.split("_", 1)[1] for f in os.listdir(self.out)), ["DSC00001.ARW", "DSC00001.JPG"])

    def test_card_only_downloads_nothing(self):
        cam = self.make()
        self.fake.dest = 0x10
        self.run_job(cam, cam.shoot_once({}))
        self.assertEqual(os.listdir(self.out), [])
        self.assertEqual(len(self.fake.shots), 1)

    def check_hdr(self, cam):
        self.run_job(cam, cam.start_hdr({"hdrShots": 3, "hdrEv": 1}))
        got = [sp.shutter(v) for v in self.fake.shots]
        self.assertEqual(got, ["1/125", "1/250", "1/60"])
        self.assertEqual(sp.shutter(cam.props.get(sp.SHUTTER, -1)), "1/125")   # restored

    def test_hdr_with_listed_speeds(self):
        self.check_hdr(self.make())

    def test_hdr_by_dial_steps_either_direction(self):
        self.check_hdr(self.make(list_choices=False))
        self.check_hdr(self.make(list_choices=False, step_reversed=True))

    def test_hdr_goes_to_bulb_beyond_30s(self):
        import types
        from startracker_desktop import sony
        clock = {"t": 0.0}
        fast = types.SimpleNamespace(
            monotonic=lambda: clock["t"], time=lambda: clock["t"], strftime=time.strftime,
            sleep=lambda x: clock.__setitem__("t", clock["t"] + max(0.0, x)))
        cam = self.make()
        self.fake.shutter = 18    # 30"
        self.fake.dest = 0x10
        cam.refresh_now()
        sony.time = fast          # exposures take simulated time
        try:
            self.run_job(cam, cam.start_hdr({"hdrShots": 3, "hdrEv": 1}))
        finally:
            sony.time = time
        self.assertEqual([sp.shutter(v) for v in self.fake.shots], ['30"', '15"', "BULB"])
        self.assertIn("bulb 60.0 s", "\n".join(cam.log_lines))

    def test_focus_stack_returns_focus(self):
        cam = self.make()
        self.fake.dest = 0x10
        self.run_job(cam, cam.start_focus_stack({"shots": 4, "size": 3, "pulses": 2, "settleSeconds": 0}))
        self.assertEqual(len(self.fake.shots), 4)
        self.assertEqual(self.fake.focus_pos, 0)

    def test_live_view(self):
        cam = self.make()
        cam.live_start()
        self.assertTrue(wait(lambda: cam.live_frame(0) != ""))
        seq, b64 = cam.live_frame(0).split(",", 1)
        self.assertTrue(int(seq) >= 1)
        cam.live_stop()

    def test_people_remover_removes_moving_block(self):
        frames = []
        for i in range(5):
            a = np.full((60, 90, 3), 120, np.uint8)
            a[10:30, 10 + i * 15:25 + i * 15] = 255      # someone walking
            frames.append(jpeg(Image.fromarray(a)))
        cam = self.make(frames=frames)
        self.run_job(cam, cam.start_people_remover({"shots": 5, "intervalSeconds": 0, "sample": 1}), 60)
        merged = [f for f in os.listdir(self.out) if f.endswith("_PEOPLE-REMOVED.JPG")]
        self.assertEqual(len(merged), 1)
        m = np.asarray(Image.open(os.path.join(self.out, merged[0])))
        self.assertLess(abs(int(m[20:30].mean()) - 120), 6)   # the walker is gone

    def test_people_remover_needs_computer_destination(self):
        cam = self.make()
        self.fake.dest = 0x10
        cam.refresh_now()
        self.assertFalse(cam.start_people_remover({"shots": 3}))
        self.assertIn("Card + computer", cam.error)

    def test_interval_and_diagnostics(self):
        cam = self.make()
        self.fake.dest = 0x10
        self.run_job(cam, cam.start_interval({"count": 3, "intervalSeconds": 0}))
        self.assertEqual(len(self.fake.shots), 3)
        self.assertIn("AllProps", cam.diagnostics())


class FakePolaris:
    """Stands in for HeadClient: records what the jobs ask the driver."""
    def __init__(self, panels=2):
        self.log, self.panels, self.pos = [], panels, [100.0, 40.0]

    def position(self):
        return list(self.pos)

    def slew_altaz(self, az, alt):
        self.log.append(("slew", round(az, 1), round(alt, 1)))

    def set_tracking(self, on):
        self.log.append(("tracking", on))

    def tracking(self):
        return True

    def wait_while_slewing(self, stop, timeout):
        return not stop()

    def panel_count(self):
        return self.panels

    def slew_to_panel(self, panel):
        self.log.append(("panel", panel))

    def pano_grid(self, grid):
        self.log.append(("grid", grid.get("track")))

    def pulse_guide(self, direction, ms):
        self.log.append(("pulse", direction))

    def pulse_guiding(self):
        return False


class SuiteJobsTest(SonyTest):
    """The jobs Polaris Suite added on Android, ported to Windows."""

    def setUp(self):
        from startracker_desktop import shot_log, sony
        self.sony = sony
        self.polaris = FakePolaris()
        self._orig = sony.HeadClient
        sony.HeadClient = lambda: self.polaris
        self.docs = tempfile.mkdtemp()
        self._docs = shot_log.documents_dir
        shot_log.documents_dir = lambda: __import__("pathlib").Path(self.docs)
        self.alerts = []
        self._alerts = (sony.alerts.done, sony.alerts.failed)
        sony.alerts.done = lambda job, w="": self.alerts.append(("done", job))
        sony.alerts.failed = lambda job, e="": self.alerts.append(("failed", job))

    def tearDown(self):
        from startracker_desktop import shot_log
        self.sony.HeadClient = self._orig
        shot_log.documents_dir = self._docs
        self.sony.alerts.done, self.sony.alerts.failed = self._alerts

    def test_shot_log_and_alert(self):
        cam = self.make()
        self.run_job(cam, cam.start_darks({"count": 2, "gapSeconds": 0}))
        logs = os.listdir(self.docs)
        self.assertEqual(len(logs), 1)
        lines = open(os.path.join(self.docs, logs[0])).read().strip().split("\n")
        self.assertEqual(lines[0].split(",")[:3], ["time", "job", "step"])
        self.assertEqual(len(lines), 3)
        self.assertIn("Dark frames", lines[1])
        self.assertIn("100.00", lines[1])                     # the Polaris azimuth
        self.assertEqual(self.alerts, [("done", "Dark frames")])

    def test_astro_dithers_between_frames(self):
        cam = self.make()
        self.fake.dest = 0x10
        self.run_job(cam, cam.start_astro({"count": 5, "gapSeconds": 0, "ditherEvery": 2, "ditherMs": 200,
                                           "settleSeconds": 0}))
        self.assertEqual(len(self.fake.shots), 5)
        pulses = [d for k, d in [e[:2] for e in self.polaris.log] if k == "pulse"]
        self.assertEqual(len(pulses), 4)                      # two dithers, RA then Dec each
        self.assertIn(pulses[0], (2, 3))
        self.assertIn(pulses[1], (0, 1))

    def test_video_presses_and_releases_record(self):
        cam = self.make()
        self.run_job(cam, cam.start_video({"minutes": 0.005}))
        self.assertEqual(self.fake.recording, [2, 1])

    def test_sphere_visits_points_and_returns(self):
        cam = self.make()
        self.fake.dest = 0x10
        pts = [[0, 0], [90, 0], [180, 45], [0, 90]]
        self.run_job(cam, cam.start_sphere({"points": pts, "settleSeconds": 0}))
        slews = [e[1:] for e in self.polaris.log if e[0] == "slew"]
        self.assertEqual(slews, [(0, 0), (90, 0), (180, 45), (0, 90), (100.0, 40.0)])
        self.assertEqual(len(self.fake.shots), 4)

    def test_two_pass_panorama_changes_only_tracking(self):
        cam = self.make()
        self.fake.dest = 0x10
        self.run_job(cam, cam.start_mixed_panorama({"settleSeconds": 0, "gapSeconds": 0, "skyTrack": 2}))
        seq = [e for e in self.polaris.log if e[0] in ("grid", "panel")]
        self.assertEqual(seq, [("grid", 0), ("panel", 1), ("panel", 2), ("grid", 2), ("panel", 1), ("panel", 2)])
        self.assertEqual(len(self.fake.shots), 4)

    def test_star_trails_blend(self):
        frames = []
        for i in range(4):
            a = np.full((60, 90, 3), 10, np.uint8)
            a[20:24, 10 + i * 20:14 + i * 20] = 250       # a star moving across
            frames.append(jpeg(Image.fromarray(a)))
        cam = self.make(frames=frames)
        self.run_job(cam, cam.start_trails({"count": 4, "intervalSeconds": 0}), 60)
        out = [f for f in os.listdir(self.out) if "_StarTrails_4" in f]
        self.assertEqual(len(out), 1, os.listdir(self.out))
        m = np.asarray(Image.open(os.path.join(self.out, out[0])).convert("L"))
        self.assertGreater(m[21:23, 11:13].mean(), 180)    # first position kept
        self.assertGreater(m[21:23, 71:73].mean(), 180)    # last position too
        self.assertNotEqual(cam.trails_frame(0), "")

    def test_holy_grail_lengthens_shutter_as_it_darkens(self):
        bright = jpeg(Image.fromarray(np.full((60, 90, 3), 160, np.uint8)))
        dark = jpeg(Image.fromarray(np.full((60, 90, 3), 40, np.uint8)))
        cam = self.make(frames=[bright, dark, dark])
        self.run_job(cam, cam.start_holy_grail({"count": 3, "intervalSeconds": 1}), 60)
        got = [sp.shutter(v) for v in self.fake.shots]
        self.assertEqual(got[0], "1/125")
        self.assertEqual(got[1], "1/125")
        # brighter after the dark frame: this fake body lists only full stops, so two notches are 1/60 then 1/30
        self.assertIn(got[2], ("1/60", "1/30"))


if __name__ == "__main__":
    unittest.main()
