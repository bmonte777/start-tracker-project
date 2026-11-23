"""Plate solving with a hint, for the Windows app: the Python port of the
Android app's PlateSolver.java (same steps, same settings), with numpy for
the pixel and matching work.

Finds exactly where a photo of the night sky points. It is told roughly
where to look (the Polaris pointing) and how wide the frame is (the lens),
so it only matches against the catalogue stars near the hint.

Steps: detect stars (local maxima over a background, centroided); project
the catalogue around the hint onto a tangent plane; match triangles of
bright stars, which keep their shape under rotation and scale; check each
candidate transform by counting how many detected stars land on catalogue
stars; refine the best one with all its matches (with one radial lens
distortion term), three times, re-projecting around the solved centre.

Coordinates: RA/Dec J2000 in degrees. Image x to the right, y down.
tests/test_plate_solver.py renders synthetic star fields and must keep
"wrong 0": a wrong solve would sync the Polaris to the wrong place.
"""
import math
import struct
import time
from dataclasses import dataclass

import numpy as np

PAT_SIDE = 0.4      # triangle sides up to this x frame width
PAT_K = 14          # each catalogue star with its PAT_K brightest neighbours
PAT_N = 25          # triangles from the PAT_N brightest detected stars
MAX_RMS_PX = 3.0    # largest fit residual (pixels rms) accepted as a solve


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------

class Catalog:
    """Stars sorted by magnitude (brightest first): ra, dec in degrees; mag."""

    def __init__(self, ra, dec, mag):
        self.ra = np.asarray(ra, dtype=np.float64)
        self.dec = np.asarray(dec, dtype=np.float64)
        self.mag = np.asarray(mag, dtype=np.float64)
        a, d = np.radians(self.ra), np.radians(self.dec)
        self.xyz = np.stack([np.cos(d) * np.cos(a), np.cos(d) * np.sin(a), np.sin(d)], axis=1)
        self.mag_max = float(self.mag[-1]) if len(self.mag) else 8.0   # 8 for stars8.bin, 10.5 for stars11.bin

    @classmethod
    def read(cls, path):
        """stars8.bin / stars11.bin: "STR1", count, then (float ra, float dec, short mag*100) little-endian."""
        with open(path, "rb") as f:
            data = f.read()
        magic, n = struct.unpack_from("<II", data, 0)
        if magic != 0x31525453:
            raise IOError("Not a star catalogue")
        rec = np.frombuffer(data, dtype=np.dtype([("ra", "<f4"), ("dec", "<f4"), ("mag", "<i2")]), count=n, offset=8)
        return cls(rec["ra"].astype(np.float64), rec["dec"].astype(np.float64), rec["mag"].astype(np.float64) / 100.0)

    def cone(self, ra0, dec0, radius_deg, mag_limit):
        """Indices of stars within radius (degrees) of ra0/dec0, brightest first."""
        a, d = math.radians(ra0), math.radians(dec0)
        c = np.array([math.cos(d) * math.cos(a), math.cos(d) * math.sin(a), math.sin(d)])
        last = int(np.searchsorted(self.mag, mag_limit, side="right"))
        dots = self.xyz[:last] @ c
        return np.nonzero(dots >= math.cos(math.radians(radius_deg)))[0]


# --------------------------------------------------------------------------
# Star detection
# --------------------------------------------------------------------------

@dataclass
class Star:
    x: float
    y: float
    flux: float


def detect(lum, max_stars=60):
    """Finds stars in a luminance image (2-D array, 0..255). The background
    is estimated per 32x32 block (median), the noise from the lower half of
    each block; a star is a local maximum well above it. Returns at most
    max_stars, brightest first."""
    lum = np.asarray(lum, dtype=np.float32)
    h, w = lum.shape
    bs = 32
    bh, bw = (h + bs - 1) // bs, (w + bs - 1) // bs
    bg = np.empty((bh, bw), np.float32)
    noise = np.empty((bh, bw), np.float32)
    for by in range(bh):
        for bx in range(bw):
            block = np.sort(lum[by * bs:by * bs + bs, bx * bs:bx * bs + bs], axis=None)
            n = block.size
            med = block[n // 2]
            bg[by, bx] = med
            noise[by, bx] = max(0.8, med - block[max(0, int(n * 0.16))])
    bgf = np.repeat(np.repeat(bg, bs, 0), bs, 1)[:h, :w]
    nzf = np.repeat(np.repeat(noise, bs, 0), bs, 1)[:h, :w]
    thresh = bgf + np.maximum(6 * nzf, 12)
    r = 3
    cand = np.zeros((h, w), bool)
    cand[r:h - r, r:w - r] = lum[r:h - r, r:w - r] >= thresh[r:h - r, r:w - r]
    ys, xs = np.nonzero(cand)
    found = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        v = lum[y, x]
        win = lum[y - 2:y + 3, x - 2:x + 3]
        if (win > v).any():
            continue
        # ties: the first (earlier row, or same row and to the left) wins
        tie = win == v
        tie[2, 2] = False
        if tie[:2, :].any() or tie[2, :2].any():
            continue
        b, nz = bg[min(bh - 1, y // bs), min(bw - 1, x // bs)], noise[min(bh - 1, y // bs), min(bw - 1, x // bs)]
        f = lum[y - r:y + r + 1, x - r:x + r + 1].astype(np.float64) - b
        pos = f > 0
        bright = int((f > 2 * nz).sum())
        sf = float(f[pos].sum())
        if sf <= 0 or bright < 2:
            continue                                    # a single hot pixel
        gy, gx = np.mgrid[-r:r + 1, -r:r + 1]
        found.append(Star(float((f[pos] * (x + gx[pos])).sum() / sf), float((f[pos] * (y + gy[pos])).sum() / sf), sf))
    found.sort(key=lambda s: -s.flux)
    # A saturated star can give several maxima: keep the brightest within 8 px.
    kept = []
    for st in found:
        if not any(abs(k.x - st.x) < 8 and abs(k.y - st.y) < 8 for k in kept):
            kept.append(st)
        if len(kept) >= max_stars * 3:
            break
    return kept[:max_stars]


# --------------------------------------------------------------------------
# Projection
# --------------------------------------------------------------------------

def project(ra, dec, ra0, dec0):
    """Gnomonic projection around ra0/dec0: (xi, eta) degrees (xi east, eta north), or None behind."""
    a, d, d0 = math.radians(ra - ra0), math.radians(dec), math.radians(dec0)
    cosc = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a)
    if cosc <= 0.1:
        return None
    xi = math.cos(d) * math.sin(a) / cosc
    eta = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a)) / cosc
    return math.degrees(xi), math.degrees(eta)


def _project_many(ra, dec, ra0, dec0):
    a, d, d0 = np.radians(ra - ra0), np.radians(dec), math.radians(dec0)
    cosc = math.sin(d0) * np.sin(d) + math.cos(d0) * np.cos(d) * np.cos(a)
    ok = cosc > 0.1
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = np.degrees(np.cos(d) * np.sin(a) / cosc)
        eta = np.degrees((math.cos(d0) * np.sin(d) - math.sin(d0) * np.cos(d) * np.cos(a)) / cosc)
    return xi, eta, ok


def unproject(xi_deg, eta_deg, ra0, dec0):
    """Inverse gnomonic: tangent-plane degrees back to RA/Dec."""
    xi, eta, d0 = math.radians(xi_deg), math.radians(eta_deg), math.radians(dec0)
    rho = math.hypot(xi, eta)
    if rho == 0:
        return ra0, dec0
    c = math.atan(rho)
    dec = math.asin(math.cos(c) * math.sin(d0) + eta * math.sin(c) * math.cos(d0) / rho)
    ra = ra0 + math.degrees(math.atan2(xi * math.sin(c), rho * math.cos(d0) * math.cos(c) - eta * math.sin(d0) * math.sin(c)))
    return (ra % 360 + 360) % 360, math.degrees(dec)


# --------------------------------------------------------------------------
# Solving
# --------------------------------------------------------------------------

@dataclass
class Solution:
    ra: float = 0.0          # image centre, J2000 degrees
    dec: float = 0.0
    roll: float = 0.0        # angle of the image's up direction east of north
    scale: float = 0.0       # degrees per pixel
    fovW: float = 0.0
    fovH: float = 0.0
    mirrored: bool = False
    matched: int = 0
    used: int = 0
    rmsArcsec: float = 0.0
    millis: int = 0


class _Fit:
    """Similarity from image (x, -y) to tangent plane: xi = a*x - b*y' + c, eta = b*x + a*y' + d."""
    __slots__ = ("a", "b", "c", "d", "k", "norm2", "mirror", "matched", "rms")

    def __init__(self):
        self.k, self.norm2, self.mirror, self.matched, self.rms = 0.0, 1.0, False, 0, 0.0

    def apply(self, x, y):
        f = 1 + self.k * (x * x + y * y) / self.norm2
        x = x * f
        y = y * f
        yy = y if self.mirror else -y
        return self.a * x - self.b * yy + self.c, self.b * x + self.a * yy + self.d

    def scale(self):
        return math.hypot(self.a, self.b)


def _triangle(p, q, s, px, py):
    """Vertices in canonical order (A opposite the shortest side…) and the
    ratios short/long, middle/long; None if degenerate or too flat."""
    v = (p, q, s)
    side = []
    for n in range(3):
        u, w = v[(n + 1) % 3], v[(n + 2) % 3]
        side.append(math.hypot(px[u] - px[w], py[u] - py[w]))
    o = sorted(range(3), key=lambda n: side[n])
    longest = side[o[2]]
    if longest <= 0 or side[o[0]] < longest * 0.08:
        return None
    return v[o[0]], v[o[1]], v[o[2]], side[o[0]] / longest, side[o[1]] / longest, longest


def _key(r1, r2):
    return int(round(r1 * 100)) * 1000 + int(round(r2 * 100))


def _fit_pairs(ax, ay, bx, by, mirror):
    ax, ay, bx, by = (np.asarray(v, dtype=np.float64) for v in (ax, ay, bx, by))
    yy = ay if mirror else -ay
    mx, my, nx, ny = ax.mean(), yy.mean(), bx.mean(), by.mean()
    px, py, qx, qy = ax - mx, yy - my, bx - nx, by - ny
    sxx = float((px * px + py * py).sum())
    if sxx <= 0:
        return None
    f = _Fit()
    f.mirror = mirror
    f.a = float((px * qx + py * qy).sum()) / sxx
    f.b = float((px * qy - py * qx).sum()) / sxx
    f.c = nx - (f.a * mx - f.b * my)
    f.d = ny - (f.b * mx + f.a * my)
    return f


def _fit_with_k(ax, ay, bx, by, mirror, norm2, k):
    f = 1 + k * (ax * ax + ay * ay) / norm2
    fit = _fit_pairs(ax * f, ay * f, bx, by, mirror)
    if fit is not None:
        fit.k, fit.norm2 = k, norm2
    return fit


def _residual(ax, ay, bx, by, mirror, norm2, k):
    f = _fit_with_k(ax, ay, bx, by, mirror, norm2, k)
    if f is None:
        return float("inf")
    tx, ty = f.apply(ax, ay)
    return float(((tx - bx) ** 2 + (ty - by) ** 2).sum())


def _fit_distorted(ax, ay, bx, by, mirror, norm2):
    """Similarity plus one radial distortion coefficient, by golden-section search."""
    ax, ay, bx, by = (np.asarray(v, dtype=np.float64) for v in (ax, ay, bx, by))
    if len(ax) < 10:
        f = _fit_pairs(ax, ay, bx, by, mirror)
        if f is not None:
            f.norm2 = norm2
        return f
    lo, hi, g = -0.12, 0.12, (math.sqrt(5) - 1) / 2
    k1, k2 = hi - g * (hi - lo), lo + g * (hi - lo)
    r1, r2 = _residual(ax, ay, bx, by, mirror, norm2, k1), _residual(ax, ay, bx, by, mirror, norm2, k2)
    for _ in range(30):
        if r1 < r2:
            hi, k2, r2 = k2, k1, r1
            k1 = hi - g * (hi - lo)
            r1 = _residual(ax, ay, bx, by, mirror, norm2, k1)
        else:
            lo, k1, r1 = k1, k2, r2
            k2 = lo + g * (hi - lo)
            r2 = _residual(ax, ay, bx, by, mirror, norm2, k2)
    return _fit_with_k(ax, ay, bx, by, mirror, norm2, (lo + hi) / 2)


def _count_matches(f, ix, iy, cx, cy, tol0, widen, want_pairs=False):
    """Image stars landing within tol of a catalogue star, one-to-one, in image-star order."""
    tx, ty = f.apply(ix, iy)
    tol = tol0 * (1 + widen * (ix * ix + iy * iy) / f.norm2)
    dx = cx[None, :] - tx[:, None]
    dy = cy[None, :] - ty[:, None]
    d2 = dx * dx + dy * dy
    within = d2 < (tol * tol)[:, None]
    n = 0
    pairs_i, pairs_c = [], []
    used = np.zeros(len(cx), bool)
    rows = np.nonzero(within.any(axis=1))[0]
    for i in rows:
        cand = np.nonzero(within[i] & ~used)[0]
        if cand.size == 0:
            continue
        j = cand[np.argmin(d2[i, cand])]
        used[j] = True
        n += 1
        if want_pairs:
            pairs_i.append(i)
            pairs_c.append(j)
    return (n, pairs_i, pairs_c) if want_pairs else n


def solve(cat, stars, w, h, hint_ra, hint_dec, hint_radius, fov_w, fov_tolerance):
    """stars: detected (brightest first); w, h: image size; hint: rough centre
    (J2000 degrees) and how far off it may be; fov_w: rough frame width in the
    tangent plane (degrees); fov_tolerance e.g. 0.25 for ±25 %. None when no
    convincing match is found."""
    t0 = time.time()
    n_img = min(len(stars), 40)
    if n_img < 6:
        return None
    ix = np.array([s.x - w / 2.0 for s in stars[:n_img]])
    iy = np.array([s.y - h / 2.0 for s in stars[:n_img]])
    scale0 = fov_w / w
    norm2 = (w * w + h * h) / 4.0
    fov_diag = math.hypot(w, h) * scale0 * (1 + fov_tolerance)

    radius = min(85.0, hint_radius + fov_diag / 2)
    frame_area = w * h * scale0 * scale0
    region_area = math.pi * radius * radius
    allc = cat.cone(hint_ra, hint_dec, radius, cat.mag_max)   # brightest first; 'want' below keeps the density right
    want = int(max(30, min(len(allc), 3.0 * n_img * region_area / frame_area)))
    region = allc[:min(len(allc), want)]
    deep = allc[:min(len(allc), int(want * 2.5))]
    if len(region) < 6:
        return None

    xi, eta, ok = _project_many(cat.ra[deep], cat.dec[deep], hint_ra, hint_dec)
    slot_cat = deep[ok]
    cx, cy = xi[ok], eta[ok]
    n_region = int((cat.mag[slot_cat] <= cat.mag[region[-1]]).sum())
    if n_region < 6:
        return None

    # Catalogue triangles: each region star with its brightest neighbours within reach.
    max_side = PAT_SIDE * w * scale0 * (1 + fov_tolerance)
    table = {}
    seen = set()
    rx, ry = cx[:n_region], cy[:n_region]
    dist = np.hypot(rx[:, None] - rx[None, :], ry[:, None] - ry[None, :])
    for p in range(n_region):
        near = [q for q in np.nonzero(dist[p] <= max_side)[0].tolist() if q != p][:PAT_K]
        for u in range(len(near)):
            for v in range(u + 1, len(near)):
                q, s = near[u], near[v]
                if dist[q, s] > max_side:
                    continue
                key3 = tuple(sorted((p, q, s)))
                if key3 in seen:
                    continue
                seen.add(key3)
                t = _triangle(p, q, s, cx, cy)
                if t is None:
                    continue
                table.setdefault(_key(t[3], t[4]), []).append(t)

    # Image triangles from the brightest image stars, matched against the table.
    n_pat = min(n_img, PAT_N)
    max_side_pix = PAT_SIDE * w
    best = None
    tol_pix = 2.5
    tried = 0
    clear = max(10, n_img * 0.6)
    for p in range(n_pat):
        for q in range(p + 1, n_pat):
            for s in range(q + 1, n_pat):
                ti = _triangle(p, q, s, ix, iy)
                if ti is None or ti[5] < 0.05 * w or ti[5] > max_side_pix:
                    continue
                expected = ti[5] * scale0
                for dr1 in (-1, 0, 1):
                    for dr2 in (-1, 0, 1):
                        cands = table.get(_key(ti[3] + dr1 * 0.01, ti[4] + dr2 * 0.01))
                        if not cands:
                            continue
                        for tc in cands:
                            if abs(tc[3] - ti[3]) > 0.008 or abs(tc[4] - ti[4]) > 0.008:
                                continue
                            ratio = tc[5] / expected
                            if ratio < 1 - fov_tolerance or ratio > 1 + fov_tolerance:
                                continue
                            tried += 1
                            if tried > 400000:
                                break
                            for mirror in (False, True):
                                f = _fit_pairs([ix[ti[0]], ix[ti[1]], ix[ti[2]]], [iy[ti[0]], iy[ti[1]], iy[ti[2]]],
                                               [cx[tc[0]], cx[tc[1]], cx[tc[2]]], [cy[tc[0]], cy[tc[1]], cy[tc[2]]], mirror)
                                if f is None:
                                    continue
                                f.norm2 = norm2
                                f.matched = _count_matches(f, ix, iy, cx, cy, tol_pix * f.scale(), 5)
                                if best is None or f.matched > best.matched:
                                    best = f
                if best is not None and best.matched >= clear:
                    break
            if best is not None and best.matched >= clear:
                break
        if best is not None and best.matched >= clear:
            break
    if best is None:
        return None
    need = max(6, math.ceil(n_img * 0.3))
    if best.matched < need:
        return None

    # Refine with all matches, re-projecting around the solved centre each pass.
    ra0, dec0 = hint_ra, hint_dec
    fit = best
    deep_ra, deep_dec = cat.ra[deep], cat.dec[deep]
    for pss in range(3):
        nm, mi, mc = _count_matches(fit, ix, iy, cx, cy, tol_pix * fit.scale(), 5 if pss == 0 else 2, True)
        if nm < need:
            return None
        ax, ay = ix[mi], iy[mi]
        pair_cat = slot_cat[mc]
        nf = _fit_distorted(ax, ay, cx[mc], cy[mc], fit.mirror, norm2)
        if nf is None:
            return None
        ra0, dec0 = unproject(nf.c, nf.d, ra0, dec0)
        xi, eta, ok = _project_many(deep_ra, deep_dec, ra0, dec0)
        slot_cat, cx, cy = deep[ok], xi[ok], eta[ok]
        bx, by, _ = _project_many(cat.ra[pair_cat], cat.dec[pair_cat], ra0, dec0)
        nf = _fit_distorted(ax, ay, bx, by, fit.mirror, norm2)
        if nf is None:
            return None
        tx, ty = nf.apply(ax, ay)
        nf.rms = math.sqrt(float(((tx - bx) ** 2 + (ty - by) ** 2).sum()) / nm)
        nf.matched = nm
        ra0, dec0 = unproject(nf.c, nf.d, ra0, dec0)
        fit = nf

    # A loose fit is not trusted: syncing on it would move the alignment by a
    # fraction of a degree at wide angles.
    if fit.rms / fit.scale() > MAX_RMS_PX:
        return None

    s = Solution()
    s.ra, s.dec = ra0, dec0
    s.scale = fit.scale()
    s.fovW, s.fovH = w * s.scale, h * s.scale
    s.mirrored = fit.mirror
    up = fit.apply(0.0, -100.0)
    s.roll = (math.degrees(math.atan2(up[0], up[1])) + 360) % 360
    s.matched, s.used = fit.matched, n_img
    s.rmsArcsec = fit.rms * 3600
    s.millis = int((time.time() - t0) * 1000)
    return s


def to_j2000(ra_deg, dec_deg, epoch_s):
    """Precession of date back to J2000 (enough for a search hint)."""
    years = (epoch_s * 1000 - 946728000000) / 31557600000.0
    m, n = 3.07496, 1.33621
    ra, dec = ra_deg, dec_deg
    for _ in range(2):
        dra = (m + n * math.sin(math.radians(ra)) * math.tan(math.radians(dec))) * years * 15 / 3600
        ddec = n * 15 * math.cos(math.radians(ra)) * years / 3600
        ra, dec = ra_deg - dra, dec_deg - ddec
    return (ra % 360 + 360) % 360, dec
