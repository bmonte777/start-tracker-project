"""One CSV line per photo in Documents\\Canopus\\
shot-log-YYYY-MM-DD.csv (time, job, file, shutter, aperture, ISO, where the
Polaris pointed), as ShotLog.java writes on Android."""
import csv
import io
import os
import threading
from datetime import datetime
from pathlib import Path

HEADER = ["time", "job", "step", "file", "shutter", "aperture", "iso", "polaris_azimuth", "polaris_altitude"]
_lock = threading.Lock()


def documents_dir():
    docs = None
    if os.name == "nt":
        try:
            import ctypes
            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            fid = (ctypes.c_byte * 16)(*bytes.fromhex("d09ad3fd8f23af46adb46c85480369c7"))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(fid, 0, None, ctypes.byref(p)) == 0:
                docs = Path(p.value)
                ctypes.windll.ole32.CoTaskMemFree(p)
        except Exception:      # noqa: BLE001
            docs = None
    d = (docs or Path.home() / "Documents") / "Canopus"
    d.mkdir(parents=True, exist_ok=True)
    return d


def add(job, step, file, shutter, aperture, iso, az, alt):
    """Never raises: the log is a convenience and must not stop the shooting."""
    try:
        now = datetime.now()
        f = documents_dir() / ("shot-log-%s.csv" % now.strftime("%Y-%m-%d"))
        num = lambda v: "" if v is None or v != v else "%.2f" % v       # noqa: E731
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        with _lock:
            fresh = not f.exists()
            if fresh:
                w.writerow(HEADER)
            w.writerow([now.strftime("%Y-%m-%dT%H:%M:%S"), job, step, file, shutter, aperture, iso, num(az), num(alt)])
            with open(f, "a", encoding="utf-8", newline="") as out:
                out.write(buf.getvalue())
    except Exception:      # noqa: BLE001
        pass
