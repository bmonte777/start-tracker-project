"""PTP to a camera through Windows Portable Devices, via ptpwpd.dll
(polaris/desktop/ptpwpd). Windows owns the camera's USB driver; WPD's MTP
extension commands carry any PTP operation, Sony's vendor ones included."""
import ctypes
import os
import sys
import threading

from .ptp import Response, Transport

_dll = None
_lock = threading.Lock()


def _load():
    global _dll
    if _dll is not None:
        return _dll
    here = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for p in (os.path.join(here, "ptpwpd.dll"), os.path.join(here, "..", "ptpwpd.dll")):
        if os.path.exists(p):
            dll = ctypes.WinDLL(p)
            break
    else:
        raise OSError("ptpwpd.dll not found")
    dll.ptp_list.argtypes = [ctypes.c_wchar_p, ctypes.c_int]
    dll.ptp_list.restype = ctypes.c_int
    dll.ptp_open.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
    dll.ptp_open.restype = ctypes.c_void_p
    dll.ptp_close.argtypes = [ctypes.c_void_p]
    dll.ptp_free.argtypes = [ctypes.c_void_p]
    dll.ptp_transact.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.c_int,
        ctypes.c_char_p, ctypes.c_uint, ctypes.c_int,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_int), ctypes.c_wchar_p, ctypes.c_int]
    dll.ptp_transact.restype = ctypes.c_int
    _dll = dll
    return dll


def list_devices():
    """[(id, name, manufacturer)] of the portable devices Windows sees."""
    dll = _load()
    buf = ctypes.create_unicode_buffer(32768)
    n = dll.ptp_list(buf, len(buf))
    if n < 0:
        raise OSError("Windows could not list portable devices")
    out = []
    for line in buf.value.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


class WpdTransport(Transport):
    manages_session = True

    def __init__(self, device_id):
        self._dll = _load()
        err = ctypes.create_unicode_buffer(512)
        h = self._dll.ptp_open(device_id, err, len(err))
        if not h:
            raise OSError(err.value or "Cannot open the camera")
        self._h = h

    def transact(self, op, params=(), data_out=None, want_data=False):
        with _lock:
            if not self._h:
                raise OSError("Camera not open")
            arr = (ctypes.c_uint * max(1, len(params)))(*[p & 0xFFFFFFFF for p in params])
            data_in = ctypes.c_void_p()
            in_len = ctypes.c_uint(0)
            resp = (ctypes.c_uint * 5)()
            n_resp = ctypes.c_int(0)
            err = ctypes.create_unicode_buffer(512)
            out = bytes(data_out) if data_out is not None else None
            code = self._dll.ptp_transact(
                self._h, op, arr, len(params), out, len(out) if out else 0, 1 if want_data else 0,
                ctypes.byref(data_in), ctypes.byref(in_len), resp, ctypes.byref(n_resp), err, len(err))
            if code < 0:
                raise OSError(err.value or "Camera command failed")
            data = b""
            if data_in.value:
                data = ctypes.string_at(data_in.value, in_len.value)
                self._dll.ptp_free(data_in)
            return Response(code, list(resp)[:n_resp.value], data)

    def close(self):
        with _lock:
            if self._h:
                self._dll.ptp_close(self._h)
                self._h = None
