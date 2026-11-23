"""Alerts when a camera job finishes or fails on its own (JobAlerts.java on
Android): a Windows notification with a sound, so it is noticed while the
window is in the background. Jobs stopped with the Stop button raise none."""
import os
import subprocess
import threading

_PS = r"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$x = New-Object Windows.Data.Xml.Dom.XmlDocument
$x.LoadXml('<toast><visual><binding template="ToastGeneric"><text>' + $env:BPC_TITLE + '</text><text>' + $env:BPC_TEXT + '</text></binding></visual><audio src="ms-winsoundevent:Notification.Looping.Alarm2" /></toast>')
$id = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show([Windows.UI.Notifications.ToastNotification]::new($x))
"""


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")


def _post(title, text):
    if os.name != "nt":
        return

    def go():
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:      # noqa: BLE001
            pass
        try:
            env = dict(os.environ, BPC_TITLE=_esc(title), BPC_TEXT=_esc(text))
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", _PS],
                           env=env, timeout=20, capture_output=True, creationflags=0x08000000)
        except Exception:      # noqa: BLE001 - the result is still in the camera log
            pass
    threading.Thread(target=go, daemon=True).start()


def done(job, warning=""):
    _post(job + " done", "Finished, with a warning: " + warning if warning else "Finished.")


def failed(job, error=""):
    _post(job + " stopped by a problem", error or "See the camera log.")
