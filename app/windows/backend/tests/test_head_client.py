"""The reused camera code's head client against the running simulator (skipped when no simulator answers)."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from startracker_desktop import head_client  # noqa: E402

SIM = os.environ.get("ST_SIM") or str(Path(__file__).resolve().parents[4] / "firmware/sim/build/startracker-sim")


@pytest.fixture(scope="module")
def sim():
    if not Path(SIM).exists():
        pytest.skip("simulator not built")
    p = subprocess.Popen([SIM, "--speed", "50", "--http-port", "8091"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:8091/startracker/v1/info", timeout=0.5)
            break
        except OSError:
            time.sleep(0.1)
    time.sleep(1.0)   # a go-to in the simulator's first moments can be lost (noted in docs/06-apps.md section 10)
    head_client.set_base("http://127.0.0.1:8091")
    yield
    p.kill()


def test_slew_and_position(sim):
    h = head_client.HeadClient()
    h.slew_altaz(123.0, 35.0)
    for _ in range(100):                      # a freshly started simulator needs a moment before the slew shows
        az, alt = h.position()
        if abs(az - 123.0) < 0.05 and not h.slewing():
            break
        time.sleep(0.1)
    assert abs(az - 123.0) < 0.05 and abs(alt - 35.0) < 0.05


def test_head_job_ack_loop(sim):
    h = head_client.HeadClient()
    r = h.op("job.start", {"type": "poses", "shutter": "app", "poses": [{"az_d": 100, "alt_d": 20}, {"az_d": 110, "alt_d": 20}], "settle_s": 0.5})
    acked = 0
    for _ in range(400):
        st = h.op("job.status")
        if st["state"] == "waiting_ack":
            h.op("job.ack", {"job_id": r["job_id"], "frame": st["frame"]})
            acked += 1
        if st["state"] == "done":
            break
        time.sleep(0.02)
    assert acked == 2 and h.op("job.status")["state"] == "done"


def test_errors_come_back_readable(sim):
    with pytest.raises(head_client.HeadError, match="limit"):
        head_client.HeadClient().op("goto", {"az_d": 0, "alt_d": -50})
