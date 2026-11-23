"""Local web server for the Star Tracker window: serves the shared UI (app/ui and app/shared, the same files
as the Android app) and answers their bridge calls. Listens on 127.0.0.1
only, and requires a custom header so other web pages cannot call it."""
import json
import mimetypes
import posixpath
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .paths import web_dir

PORT = 5570


def web_root():
    return web_dir()


class Handler(BaseHTTPRequestHandler):
    bridges = {}
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _local(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._local():
            return self._send(403, "{}")
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/web", "/web/", "/web/ui", "/web/ui/"):
            return self._send(302, b"", "text/plain", {"Location": "/web/ui/index.html"})
        if not path.startswith("/web/"):
            return self._send(404, "{}")
        rel = posixpath.normpath(path[len("/web/"):]).lstrip("/")
        if rel.startswith(".."):
            return self._send(403, "{}")
        f = web_root() / rel
        if not f.is_file():
            return self._send(404, "{}")
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self._send(200, f.read_bytes(), ctype)

    def do_POST(self):
        if not self._local() or self.headers.get("X-StarTracker") != "1":
            return self._send(403, "{}")
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "bridge":
            return self._send(404, "{}")
        obj = self.bridges.get(parts[1])
        method = getattr(obj, parts[2], None) if obj is not None and not parts[2].startswith("_") else None
        if method is None:
            return self._send(404, json.dumps({"error": "unknown call"}))
        n = int(self.headers.get("Content-Length") or 0)
        try:
            args = json.loads(self.rfile.read(n) or b"[]")
            result = method(args) if isinstance(args, dict) else method(*args)   # StNative: one object; CameraNative: a list
            self._send(200, json.dumps({"result": result}))
        except Exception as e:      # noqa: BLE001 - reported to the page
            self._send(500, json.dumps({"error": str(e)}))


def serve(bridges, port=PORT):
    Handler.bridges = bridges
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, name="app-server", daemon=True)
    t.start()
    return httpd
