"""Star Tracker for Windows (D72): the backend behind the Tauri window. Serves the shared UI (app/ui, app/shared),
answers window.StNative calls (discovery, BLE set-up, location) and window.CameraNative (the Sony camera code reused
from Benro-Polaris-Controller, which now talks to the Star Tracker head through head_client.py)."""
