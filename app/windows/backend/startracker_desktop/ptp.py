"""PTP transport interface. On Windows the camera is reached through
ptpwpd.dll (ptp_win.py); tests use a simulated camera (tests/fake_sony.py)."""

OK = 0x2001
DEVICE_BUSY = 0x2019


class Response:
    def __init__(self, code, params=(), data=b""):
        self.code = code
        self.params = list(params)
        self.data = data

    def ok(self):
        return self.code == OK


class Transport:
    #: True when the system keeps the PTP session itself (Windows WPD).
    manages_session = False

    def transact(self, op, params=(), data_out=None, want_data=False):
        raise NotImplementedError

    def close(self):
        pass
