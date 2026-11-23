"""The arithmetic of the Holy Grail (day-to-night) timelapse: the Python port
of HolyGrail.java, so both apps ramp the exposure the same way.

Each frame's brightness is measured from the picture and turned into the
brightness of the scene, independent of the camera settings: scene =
picture EV - log2(shutter x ISO / 100). The scene value is smoothed so a
passing car does not change the exposure. The wanted picture brightness is
the first frame's, made darker as the Sun goes down (nights should look like
nights). The camera moves in 1/3-stop notches, at most two per frame, and
only when the error is larger than the dead band, so it does not hunt."""
import math

DEAD_BAND = 0.4               # stops of error tolerated before the exposure changes
DAY_ALT, NIGHT_ALT = 6.0, -12.0

_LINEAR = [(c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (i / 255.0 for i in range(256))]


def exposure_ev(seconds, iso):
    return math.log2(seconds * iso / 100.0)


class Step:
    __slots__ = ("scene", "wanted", "error", "notches")

    def __init__(self):
        self.scene = self.wanted = self.error = 0.0
        self.notches = 0


class HolyGrail:
    def __init__(self, night_darker_stops):
        self.night_darker = max(0.0, min(6.0, night_darker_stops))
        self.scene_smoothed = float("nan")
        self.picture_ref = float("nan")
        self.trend_at_start = float("nan")

    def trend(self, sun_altitude):
        """0 by day, -night_darker at full night, linear through twilight."""
        if sun_altitude is None or math.isnan(sun_altitude) or sun_altitude >= DAY_ALT:
            return 0.0
        if sun_altitude <= NIGHT_ALT:
            return -self.night_darker
        return -self.night_darker * (DAY_ALT - sun_altitude) / (DAY_ALT - NIGHT_ALT)

    def frame(self, picture_ev, seconds, iso, sun_altitude):
        settings = exposure_ev(seconds, iso)
        scene = picture_ev - settings
        self.scene_smoothed = scene if math.isnan(self.scene_smoothed) else 0.6 * self.scene_smoothed + 0.4 * scene
        tr = self.trend(sun_altitude)
        if math.isnan(self.picture_ref):
            self.picture_ref, self.trend_at_start = picture_ev, tr
        s = Step()
        s.scene = self.scene_smoothed
        s.wanted = self.picture_ref + (tr - self.trend_at_start)
        s.error = (s.wanted - self.scene_smoothed) - settings
        if abs(s.error) > DEAD_BAND:
            s.notches = max(-2, min(2, int(round(s.error * 3))))
        return s


def picture_ev(image):
    """log2 of the mean linear luminance of a PIL image, leaving out the
    brightest 2 % (the Sun, street lights) so they don't drive the exposure."""
    img = image.convert("RGB")
    w, h = img.size
    step = max(1, max(w, h) // 240)
    if step > 1:
        img = img.resize((max(1, w // step), max(1, h // step)))
    bins = 4096
    hist = [0] * bins
    n_px = 0
    for r, g, b in img.getdata():
        y = 0.2126 * _LINEAR[r] + 0.7152 * _LINEAR[g] + 0.0722 * _LINEAR[b]
        hist[min(bins - 1, int(y * bins))] += 1
        n_px += 1
    if n_px == 0:
        return float("nan")
    keep = max(1, round(n_px * 0.98))
    total = n = 0
    for i in range(bins):
        if n >= keep:
            break
        take = min(hist[i], keep - n)
        total += take * ((i + 0.5) / bins)
        n += take
    return math.log2(max(1e-6, total / n))


def sun_altitude(lat_deg, lon_deg, epoch_s):
    """NOAA low-precision formulas, about 0.1° accuracy."""
    jd = epoch_s / 86400.0 + 2440587.5
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    m = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    c = math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t)) + math.sin(2 * m) * (0.019993 - 0.000101 * t) \
        + math.sin(3 * m) * 0.000289
    omega = math.radians(125.04 - 1934.136 * t)
    lam = math.radians(l0 + c - 0.00569 - 0.00478 * math.sin(omega))
    eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + t * t * (0.000387933 - t / 38710000.0)) % 360
    ha = math.radians((gmst + lon_deg - math.degrees(ra)) % 360)
    lat = math.radians(lat_deg)
    return math.degrees(math.asin(math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)))
