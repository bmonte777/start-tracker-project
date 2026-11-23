"""The pictures downloaded from the camera (Pictures\\Star Tracker),
newest first, with thumbnails; opened in the default Windows viewer."""
import base64
import io
import json
import mimetypes
import os
import subprocess
import sys

from PIL import Image

from .paths import pictures_dir


def _files():
    d = pictures_dir()
    out = []
    for name in os.listdir(d):
        p = d / name
        if p.is_file() and not name.endswith(".part"):
            out.append(p)
    out.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return out[:500]


def listing():
    items = []
    for p in _files():
        st = p.stat()
        items.append({"id": p.name, "name": p.name, "size": st.st_size, "date": int(st.st_mtime * 1000),
                      "mime": mimetypes.guess_type(p.name)[0] or "application/octet-stream"})
    return json.dumps(items)


def _path(name):
    p = pictures_dir() / os.path.basename(str(name))
    return p if p.is_file() else None


def thumb(name):
    p = _path(name)
    if p is None or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".heif", ".hif"):
        return ""
    try:
        im = Image.open(p)
        im.draft("RGB", (320, 320))
        im = im.convert("RGB")
        im.thumbnail((320, 320))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:      # noqa: BLE001
        return ""


def open_file(name):
    p = _path(name)
    if p is None:
        return "File not found"
    try:
        if sys.platform == "win32":
            os.startfile(str(p))      # noqa: S606 - opens the user's own photo
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return "ok"
    except OSError as e:
        return str(e)
