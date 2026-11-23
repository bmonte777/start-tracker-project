"""Entry point of startracker-backend.exe (PyInstaller)."""
import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from startracker_desktop.__main__ import main  # noqa: E402

raise SystemExit(main())
