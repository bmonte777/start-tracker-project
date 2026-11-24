"""ASTAP for long lenses on Windows (decision D74).

The hinted solver (plate_solver.py) handles wide fields; with 300-600 mm lenses a frame holds few stars brighter
than its catalogue, so on Windows the app can also use ASTAP's command-line solver with its D05 star database.
Both are downloaded once from Settings (hnsky.org links, hosted on SourceForge) into the app's own folder:

    %LOCALAPPDATA%\\Star Tracker\\astap\\astap_cli.exe
    %LOCALAPPDATA%\\Star Tracker\\astap\\d05\\*.1476   (the D05 installer is run silently with /DIR= here;
                                                      if it insists on its own folder, C:\\Program Files\\astap
                                                      is searched too)

Solving: astap_cli -f image -ra <hours> -spd <dec+90> -fov <image height deg> -r <radius deg> -z 0 -d <db> -D d05
ASTAP writes <image>.ini next to the image: PLTSOLVD=T, CRVAL1/CRVAL2 (J2000 degrees of the image centre),
CDELT1/CDELT2 (degrees per pixel), CROTA2 (degrees). Source: https://www.hnsky.org/astap.htm (command line).
"""
import glob
import json
import os
import subprocess
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

CLI_URL = "https://sourceforge.net/projects/astap-program/files/windows_installer/astap_command-line_version_win64.zip/download"
D05_URL = "https://sourceforge.net/projects/astap-program/files/star_databases/d05_star_database.exe/download"
# SourceForge sends a plain redirect to a mirror for non-browser clients; a browser agent gets a countdown page.
UA = "Wget/1.21.4"


def base_dir():
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(root) / "Star Tracker" / "astap"


def _find_cli():
    for p in (base_dir() / "astap_cli.exe", base_dir() / "astap_cli", Path(r"C:\Program Files\astap\astap_cli.exe")):
        if p.is_file():
            return p
    return None


def _find_db():
    """Folder holding the D05 files (d05_*.1476)."""
    for d in (base_dir() / "d05", base_dir(), Path(r"C:\Program Files\astap")):
        if glob.glob(str(d / "d05_*.1476")):
            return d
    return None


class Astap:
    def __init__(self):
        self.state = "idle"          # idle, downloading, installing, ready, failed
        self.progress = 0.0
        self.message = ""
        self._lock = threading.Lock()

    # ------------------------------------------------------------ status / install
    def status(self):
        cli, db = _find_cli(), _find_db()
        st = self.state
        if st in ("idle", "ready", "failed") and cli and db:
            st = "ready"
        return {"state": st, "progress": round(self.progress, 3), "message": self.message,
                "cli": str(cli) if cli else None, "database": str(db) if db else None, "folder": str(base_dir())}

    def install(self):
        with self._lock:
            if self.state in ("downloading", "installing"):
                return self.status()
            self.state, self.progress, self.message = "downloading", 0.0, "Getting ASTAP"
        threading.Thread(target=self._install, daemon=True).start()
        return self.status()

    def _download(self, url, dest, part0, part1):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                b = r.read(1 << 16)
                if not b:
                    break
                f.write(b)
                got += len(b)
                if total:
                    self.progress = part0 + (part1 - part0) * got / total
        if dest.stat().st_size < 10000 or dest.read_bytes()[:15].lower().startswith(b"<!doctype html"):
            raise IOError("the download page answered instead of the file; try again later")

    def _install(self):
        d = base_dir()
        try:
            d.mkdir(parents=True, exist_ok=True)
            if not _find_cli():
                self.message = "Downloading the ASTAP solver"
                z = d / "astap_cli.zip"
                self._download(CLI_URL, z, 0.0, 0.15)
                with zipfile.ZipFile(z) as zf:
                    for n in zf.namelist():
                        if n.lower().endswith("astap_cli.exe"):
                            (d / "astap_cli.exe").write_bytes(zf.read(n))
                z.unlink(missing_ok=True)
                if not _find_cli():
                    raise IOError("astap_cli.exe was not in the download")
            if not _find_db():
                self.message = "Downloading the D05 star database (about 100 MB)"
                exe = d / "d05_star_database.exe"
                self._download(D05_URL, exe, 0.15, 0.9)
                self.state, self.message = "installing", "Installing the star database (Windows may ask to allow it)"
                target = d / "d05"
                target.mkdir(exist_ok=True)
                # Inno Setup installer: silent, into our folder
                subprocess.run([str(exe), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", f"/DIR={target}"],
                               timeout=900, check=False)
                exe.unlink(missing_ok=True)
                if not _find_db():
                    raise IOError("the star database did not install")
            self.progress, self.state, self.message = 1.0, "ready", "ASTAP is ready"
        except Exception as e:                      # noqa: BLE001 - reported to the user
            self.state, self.message = "failed", f"Could not get ASTAP: {e}"

    # ------------------------------------------------------------ solve
    def available(self):
        return bool(_find_cli() and _find_db())

    def solve(self, image_path, hint_ra_deg, hint_dec_deg, fov_h_deg, radius_deg, timeout=120):
        """Returns dict(ra, dec, scale_deg_px, roll, millis) in J2000 degrees, or None when ASTAP found nothing."""
        cli, db = _find_cli(), _find_db()
        if not cli or not db:
            return None
        img = Path(image_path)
        ini = img.with_suffix(".ini")
        ini.unlink(missing_ok=True)
        args = [str(cli), "-f", str(img), "-ra", f"{hint_ra_deg / 15:.5f}", "-spd", f"{hint_dec_deg + 90:.5f}",
                "-fov", f"{fov_h_deg:.4f}", "-r", f"{max(1.0, min(radius_deg, 30.0)):.1f}", "-z", "0",
                "-d", str(db), "-D", "d05"]
        t0 = time.time()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(args, timeout=timeout, check=False, capture_output=True, creationflags=flags)
        return parse_ini(ini, int((time.time() - t0) * 1000))


def parse_ini(ini_path, millis=0):
    p = Path(ini_path)
    if not p.is_file():
        return None
    kv = {}
    for line in p.read_text(errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip().upper()] = v.strip()
    if kv.get("PLTSOLVD", "F").upper() != "T":
        return None
    try:
        return {"ra": float(kv["CRVAL1"]), "dec": float(kv["CRVAL2"]),
                "scale_deg_px": abs(float(kv.get("CDELT2", kv.get("CDELT1", "0")))),
                "roll": float(kv.get("CROTA2", "0")), "millis": millis}
    except (KeyError, ValueError):
        return None


ASTAP = Astap()


def bridge(a):
    """st_bridge entry: {"action": "status"|"install"}."""
    act = (a or {}).get("action", "status")
    return ASTAP.install() if act == "install" else ASTAP.status()


if __name__ == "__main__":
    print(json.dumps(ASTAP.status(), indent=1))
