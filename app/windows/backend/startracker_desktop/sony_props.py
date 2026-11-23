"""Sony camera properties read with SDIO GetAllExtDevicePropInfo (0x9209),
and how to show them. Port of SonyProps.java; codes follow libgphoto2."""
import struct

WHITE_BALANCE = 0x5005
F_NUMBER = 0x5007
FOCUS_MODE = 0x500A
EXPOSURE_PROGRAM = 0x500E
EXPOSURE_COMP = 0x5010
SHUTTER = 0xD20D
COLOR_TEMP = 0xD20F
OBJECT_IN_MEMORY = 0xD215
BATTERY = 0xD218
ISO = 0xD21E
SAVE_DESTINATION = 0xD222
AUTOFOCUS_BUTTON = 0xD2C1
SHUTTER_BUTTON = 0xD2C2
NEAR_FAR = 0xD2D1

DEST_TABLET = 0x01   # "Tablet only" / "PC only"
DEST_CARD = 0x10
DEST_BOTH = 0x11

TYPE_STRING = 0xFFFF


class Prop:
    def __init__(self):
        self.code = 0
        self.type = 0
        self.writable = False
        self.enabled = False
        self.value = 0
        self.text = None
        self.choices = []


class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def take(self, n):
        if self.p + n > len(self.d):
            raise ValueError("truncated")
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack("<H", self.take(2))[0]

    def remaining(self):
        return len(self.d) - self.p


def _size(t):
    t &= 0xFFF
    return {1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 8, 8: 8, 9: 16, 10: 16}.get(t) or _bad(t)


def _bad(t):
    raise ValueError("unknown data type 0x%x" % t)


def read_string(r):
    n = r.u8()
    chars = [struct.unpack("<H", r.take(2))[0] for _ in range(n)]
    return "".join(chr(c) for c in chars if c)


def _skip(r, t):
    if t == TYPE_STRING:
        read_string(r)
    elif t & 0x4000:
        n = struct.unpack("<I", r.take(4))[0]
        r.take(n * _size(t))
    else:
        r.take(_size(t))


def _number(r, t):
    if t & 0x4000:
        _skip(r, t)
        return 0
    fmt = {1: "<b", 2: "<B", 3: "<h", 4: "<H", 5: "<i", 6: "<I", 7: "<q", 8: "<Q"}.get(t)
    if fmt is None:
        r.take(_size(t))
        return 0
    return struct.unpack(fmt, r.take(struct.calcsize(fmt)))[0]


def looks_like_prop(r, off):
    if off + 6 > len(r.d):
        return False
    code, t = struct.unpack_from("<HH", r.d, off)
    return ((0x5000 <= code <= 0x5FFF) or (0xD000 <= code <= 0xDFFF)) and \
        (1 <= t <= 10 or 0x4001 <= t <= 0x400A or t == TYPE_STRING)


def _enum(r, t):
    n = r.u16()
    out = []
    for _ in range(n):
        if t == TYPE_STRING:
            read_string(r)
        else:
            out.append(_number(r, t))
    return out


def _read_prop(r):
    p = Prop()
    p.code = r.u16()
    p.type = r.u16()
    p.writable = r.u8() != 0
    p.enabled = r.u8() != 0
    _skip(r, p.type)                       # factory default
    if p.type == TYPE_STRING:
        p.text = read_string(r)
    else:
        p.value = _number(r, p.type)
    form = r.u8()
    if form == 1:
        for _ in range(3):
            _skip(r, p.type)
    elif form == 2:
        p.choices = _enum(r, p.type)
        # Newer protocols add a second list; read it only when what follows
        # does not look like the next property.
        if r.remaining() > 0 and not looks_like_prop(r, r.p):
            mark = r.p
            try:
                second = _enum(r, p.type)
                if r.remaining() == 0 or looks_like_prop(r, r.p):
                    p.choices = second
                else:
                    r.p = mark
            except ValueError:
                r.p = mark
    return p


class SonyProps:
    def __init__(self):
        self.props = {}
        self.parse_problem = None

    @staticmethod
    def parse(data):
        sp = SonyProps()
        if len(data) < 8:
            sp.parse_problem = "empty property list"
            return sp
        r = Reader(data)
        count = struct.unpack("<Q", r.take(8))[0]
        i = 0
        while i < count and r.remaining() > 0:
            start = r.p
            try:
                p = _read_prop(r)
                sp.props[p.code] = p
            except ValueError as e:
                sp.parse_problem = "stopped at entry %d (offset %d): %s" % (i, start, e)
                break
            i += 1
        return sp

    def get(self, code, fallback):
        p = self.props.get(code)
        return fallback if p is None else p.value


def _trim(d):
    return str(int(d)) if d == int(d) else "%.1f" % d


def shutter(v):
    if v == 0:
        return "BULB"
    num, den = (v >> 16) & 0xFFFF, v & 0xFFFF
    if den == 0:
        return "0x%x" % v
    if num == 1 and den > 1:
        return "1/%d" % den
    return _trim(num / den) + '"'


def iso(v):
    i = v & 0xFFFFFF
    return "ISO AUTO" if i in (0, 0xFFFFFF) else "ISO %d" % i


PROGRAMS = {1: "M", 2: "P", 3: "A", 4: "S"}
WB = {0x0002: "Auto", 0x0004: "Daylight", 0x8011: "Shade", 0x8010: "Cloudy", 0x0006: "Tungsten",
      0x8001: "Fluor. warm white", 0x8002: "Fluor. cool white", 0x8003: "Fluor. day white",
      0x8004: "Fluor. daylight", 0x0007: "Flash", 0x8012: "Colour temp.", 0x8020: "Custom 1",
      0x8021: "Custom 2", 0x8022: "Custom 3", 0x8023: "Custom", 0x8030: "Underwater auto"}
FOCUS = {0x0001: "MF", 0x0002: "AF-S", 0x8004: "AF-C", 0x8005: "AF-A", 0x8006: "DMF"}
DEST = {DEST_TABLET: "Computer only", DEST_CARD: "Camera card", DEST_BOTH: "Card + computer"}


def fmt(code, v):
    if code == SHUTTER:
        return shutter(v)
    if code == ISO:
        return iso(v)
    if code == F_NUMBER:
        return "--" if v == 0 else "f/" + _trim(v / 100.0)
    if code == BATTERY:
        return "--" if v < 0 else "%d%%" % v
    if code == EXPOSURE_PROGRAM:
        return PROGRAMS.get(v, "mode 0x%x" % v)
    if code == SAVE_DESTINATION:
        return DEST.get(v, "0x%x" % v)
    if code == EXPOSURE_COMP:
        return "±0 EV" if v == 0 else "%+.1f EV" % (v / 1000.0)
    if code == WHITE_BALANCE:
        return WB.get(v, "WB 0x%x" % v)
    if code == COLOR_TEMP:
        return "%d K" % v
    if code == FOCUS_MODE:
        return FOCUS.get(v, "focus 0x%x" % v)
    return "0x%x" % v


def is_bulb(v):
    return v == 0
