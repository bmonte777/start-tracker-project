"""Star Tracker backend for Windows: the local server behind the Tauri window. Launched hidden by the window; can also
be run with `python -m startracker_desktop` for testing (then open http://127.0.0.1:5570/web/ui/index.html)."""
import socket
import sys
import time

from .bridges import make_bridges
from .server import PORT, serve


def already_running():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.3):
            return True
    except OSError:
        return False


def main():
    if already_running():
        return 0
    serve(make_bridges())
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
