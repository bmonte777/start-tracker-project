"""A simulated Sony camera for tests: answers the PTP/SDIO operations
SonyCamera uses, with shutter, ISO, aperture, save destination, focus
steps, live view and downloads of real JPEGs."""
import io
import struct

from startracker_desktop.ptp import Response, Transport

SPEEDS = [(1 << 16) | d for d in (8000, 4000, 2000, 1000, 500, 250, 125, 60, 30, 15, 8, 4, 2)] + \
         [(n << 16) | 1 for n in (1, 2, 4, 8, 15, 30)] + [0]   # 0 = BULB


def _u16(v):
    return struct.pack("<H", v & 0xFFFF)


def _u32(v):
    return struct.pack("<I", v & 0xFFFFFFFF)


class FakeSony(Transport):
    manages_session = True

    def __init__(self, list_choices=True, step_reversed=False, frames=None):
        self.list_choices = list_choices
        self.step_reversed = step_reversed     # +1 makes the shutter faster on this "body"
        self.shutter = SPEEDS.index((1 << 16) | 125)
        self.iso = 800
        self.dest = 0x11
        self.pressed = False
        self.pending = []
        self.focus_pos = 0
        self.shots = []                         # shutter value of each shot
        self.frames = frames or []              # JPEG bytes handed out per shot, cycling
        self.calls = []
        self.recording = []                     # movie button presses: 2 down, 1 up

    # -- property list in the 0x9209 format
    def _prop(self, code, t, value, choices=None):
        size = {4: 2, 6: 4}[t]
        enc = (lambda v: _u16(v)) if size == 2 else (lambda v: _u32(v))
        b = _u16(code) + _u16(t) + bytes([1, 1]) + enc(value) + enc(value)
        if choices is None:
            b += bytes([0])
        else:
            b += bytes([2]) + _u16(len(choices)) + b"".join(enc(c) for c in choices)
        return b

    def _all_props(self):
        props = [
            self._prop(0xD20D, 6, SPEEDS[self.shutter], SPEEDS if self.list_choices else None),
            self._prop(0xD21E, 6, self.iso, [100, 200, 400, 800, 1600]),
            self._prop(0x5007, 4, 280),
            self._prop(0xD222, 4, self.dest, [0x01, 0x10, 0x11]),
            self._prop(0xD215, 4, (0x8000 | len(self.pending)) if self.pending else 0),
            self._prop(0x500A, 4, 1, [1, 2, 0x8006]),
        ]
        return struct.pack("<Q", len(props)) + b"".join(props)

    def transact(self, op, params=(), data_out=None, want_data=False):
        self.calls.append(op)
        if op == 0x9201:
            # The real body sends a data phase here; Windows refuses it
            # unless the command was sent as one that reads data.
            if not want_data:
                raise OSError("Camera command failed (0x8007065D)")
            return Response(0x2001, data=b"\0" * 8)
        if op == 0x9202:
            return Response(0x2001, data=_u16(0x012C) + b"\0" * 8)
        if op == 0x9209:
            return Response(0x2001, data=self._all_props())
        if op == 0x9205:                         # set a value
            code, v = params[0], int.from_bytes(data_out, "little")
            if code == 0xD20D and v in SPEEDS and self.list_choices:
                self.shutter = SPEEDS.index(v)
            elif code == 0xD21E:
                self.iso = v
            elif code == 0xD222:
                self.dest = v
            return Response(0x2001)
        if op == 0x9207:                         # control
            code = params[0]
            if code == 0xD20D:
                d = 1 if data_out[0] == 1 else -1
                if self.step_reversed:
                    d = -d
                self.shutter = max(0, min(len(SPEEDS) - 1, self.shutter + d))
            elif code == 0xD2C2:
                v = int.from_bytes(data_out, "little")
                if v == 2:
                    self.pressed = True
                elif v == 1 and self.pressed:
                    self.pressed = False
                    self.shots.append(SPEEDS[self.shutter])
                    if self.dest in (0x01, 0x11):
                        n = len(self.shots)
                        jpg = self.frames[(n - 1) % len(self.frames)] if self.frames else b"\xff\xd8jpeg\xff\xd9"
                        self.pending += [("DSC%05d.ARW" % n, b"RAWDATA" * 10), ("DSC%05d.JPG" % n, jpg)]
            elif code == 0xD2C8:
                self.recording.append(int.from_bytes(data_out, "little"))
            elif code == 0xD2D1:
                self.focus_pos += struct.unpack("<h", data_out)[0]
            return Response(0x2001)
        if op == 0x1008 and params[0] == 0xFFFFC001:
            name, data = self.pending[0]
            info = bytearray(52)
            struct.pack_into("<I", info, 8, len(data))
            s = name + "\0"
            info += bytes([len(s)]) + s.encode("utf-16-le")
            return Response(0x2001, data=bytes(info))
        if op == 0x1009 and params[0] == 0xFFFFC001:
            name, data = self.pending.pop(0)
            return Response(0x2001, data=data)
        if op == 0x1009 and params[0] == 0xFFFFC002:
            jpg = self.frames[0] if self.frames else b"\xff\xd8live\xff\xd9"
            return Response(0x2001, data=_u32(16) + _u32(len(jpg)) + b"\0" * 8 + jpg)
        if op == 0x1004:
            return Response(0x2001, data=_u32(1) + _u32(0x00010001))
        if op == 0x1005:
            d = bytearray(26)
            struct.pack_into("<QQI", d, 6, 128_000_000_000, 100_000_000_000, 1450)
            return Response(0x2001, data=bytes(d))
        return Response(0x2005)                 # operation not supported


def jpeg(img):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    return buf.getvalue()
