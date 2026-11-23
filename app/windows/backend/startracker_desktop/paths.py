"""Where things live on Windows (and on other systems for testing)."""
import os
import sys
from pathlib import Path


def bundle_dir():
    """Folder of the app's own files (PyInstaller unpacks them to _MEIPASS)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def web_dir():
    """The shared UI: bundled as web/ (web/ui, web/shared), or app/ when run from source (app/ui, app/shared)."""
    b = bundle_dir() / "web"
    return b if b.is_dir() else Path(__file__).resolve().parents[3]


def catalog_file():
    """Star catalogue for plate solving: stars11.bin (to V 10.5, built by app/tools/make_deep_catalog.py in the
    workflow, D74) when present, else stars8.bin; bundled, or next to the backend when run from source."""
    for name in ("stars11.bin", "stars8.bin"):
        for d in (bundle_dir(), Path(__file__).resolve().parents[1]):
            if (d / name).is_file():
                return d / name
    return bundle_dir() / "stars8.bin"


def data_dir():
    """Per-user writable folder: %LOCALAPPDATA%\\Star Tracker."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(Path.home(), ".local", "share")
    d = Path(base) / "Star Tracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pictures_dir():
    """The user's Pictures folder (follows OneDrive redirection) / Star Tracker."""
    pics = None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            guid = ctypes.c_byte * 16
            # FOLDERID_Pictures {33E28130-4E1E-4676-835A-98395C3BC3BB}
            fid = guid(*bytes.fromhex("3081e2331e4e7646835a98395c3bc3bb"))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(fid, 0, None, ctypes.byref(p)) == 0:
                pics = Path(p.value)
                ctypes.windll.ole32.CoTaskMemFree(p)
        except Exception:
            pics = None
    if pics is None:
        pics = Path.home() / "Pictures"
    d = pics / "Star Tracker"
    d.mkdir(parents=True, exist_ok=True)
    return d
