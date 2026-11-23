"""Plate solver on synthetic star fields, as tools/platesolve-test does for
the Android version: random sky positions, lenses 14-200 mm, hints up to
5° off, lens width off by up to 10 %, barrel distortion, lost stars, hot
pixels and noise. A wrong solve would sync the Polaris to the wrong place,
so "wrong" must stay 0; most fields must solve."""
import math
from pathlib import Path

import numpy as np

from startracker_desktop import plate_solver as ps

CATALOG = Path(__file__).resolve().parents[1] / "stars8.bin"


def render(cat, rnd, f, W=2000, H=1333):
    ra0 = rnd.random() * 360
    dec0 = min(89.0, -45 + rnd.random() * 130)
    roll = rnd.random() * 360
    fpx = f / 36.0 * W
    k1 = -0.03 if f <= 24 else -0.01 if f <= 50 else 0.0
    mag_lim = min(8.0, 5.3 + 2.2 * math.log10(f / 14.0))
    yy, xx = np.mgrid[0:H, 0:W]
    img = 18 + rnd.random() * 0.02 * xx + rnd.random() * 0.02 * yy + rnd.normal(0, 3, (H, W))
    fov_diag = 2 * math.degrees(math.atan(math.hypot(W, H) / 2 / fpx))
    idx = cat.cone(ra0, dec0, fov_diag / 2 + 1, mag_lim)
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    sigma = 1.0 + rnd.random() * 1.2
    for i in idx:
        p = ps.project(cat.ra[i], cat.dec[i], ra0, dec0)
        if p is None:
            continue
        xi, eta = math.radians(p[0]), math.radians(p[1])
        u, v = -(xi * cr - eta * sr), -(xi * sr + eta * cr)          # camera: east to the left
        rr = (u * u + v * v) / (math.hypot(W, H) / 2 / fpx) ** 2
        dist = 1 + k1 * rr
        x, y = W / 2 + fpx * u * dist, H / 2 + fpx * v * dist
        if x < 4 or y < 4 or x >= W - 4 or y >= H - 4 or rnd.random() < 0.1:
            continue
        flux = 4000 * 10 ** (-0.4 * (cat.mag[i] - (mag_lim - 1.5))) * (0.6 + 0.4 * rnd.random())
        x0, y0 = int(round(x)), int(round(y))
        ys, xs = slice(max(0, y0 - 6), min(H, y0 + 7)), slice(max(0, x0 - 6), min(W, x0 + 7))
        gy, gx = np.mgrid[ys, xs]
        img[ys, xs] += flux / (2 * math.pi * sigma * sigma) * np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * sigma * sigma))
    for _ in range(40):
        img[rnd.integers(H), rnd.integers(W)] = 255              # hot pixels
    img = np.clip(img, 0, 255)
    off, d = rnd.random() * 5, rnd.random() * 2 * math.pi
    hint = ps.unproject(off * math.cos(d), off * math.sin(d), ra0, dec0)
    true_w = 2 * math.degrees(math.atan(W / 2 / fpx))
    plane_w = math.degrees(W / fpx) * (true_w * (0.9 + 0.2 * rnd.random()) / true_w)
    return img, ra0, dec0, roll, hint, plane_w


def test_synthetic_fields_never_wrong():
    cat = ps.Catalog.read(CATALOG)
    rnd = np.random.default_rng(1)
    focals = [14, 20, 24, 35, 50, 85, 135, 200]
    ok = wrong = 0
    trials = 16
    for t in range(trials):
        f = focals[t % len(focals)]
        img, ra0, dec0, roll, hint, plane_w = render(cat, rnd, f)
        stars = ps.detect(img, 60)
        s = ps.solve(cat, stars, img.shape[1], img.shape[0], hint[0], hint[1], 6, plane_w, 0.25)
        if s is None:
            print(f"f={f:3d} not solved, {len(stars)} stars, dec {dec0:.1f}")
            continue
        e = ps.project(s.ra, s.dec, ra0, dec0)
        err = math.hypot(*e) * 3600
        if err > max(120, 3 * s.scale * 3600):
            wrong += 1
            print(f"f={f:3d} WRONG {err:.0f}\" {s}")
            continue
        ok += 1
        roll_err = abs(((s.roll - roll) % 360 + 540) % 360 - 180)
        print(f"f={f:3d} ok {err:.1f}\" roll err {roll_err:.2f}° matched {s.matched} in {s.millis} ms")
    print(f"solved {ok}/{trials}, wrong {wrong}")
    assert wrong == 0
    assert ok >= trials * 0.75
