"""D74: the deeper catalogue (stars11.bin) for 300-600 mm, and ASTAP's result file.

1. make_deep_catalog.py reads Tycho-2 records (mean J2000 position, or the observed one when pflag = X; V from
   BT/VT) and merges them with stars8.bin, sorted brightest first.
2. On synthetic 400-600 mm fields of a synthetic sky with Tycho-2's density, the hinted solver with stars to V 10.5
   solves fields it cannot solve with stars to V 8 alone, and is never wrong.
3. astap.parse_ini reads PLTSOLVD / CRVAL1 / CRVAL2 / CDELT2 / CROTA2.
"""
import gzip
import importlib.util
import math
import struct
from pathlib import Path

import numpy as np

from startracker_desktop import astap
from startracker_desktop import plate_solver as ps

APP = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("mdc", APP / "tools" / "make_deep_catalog.py")
mdc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mdc)
STARS8 = Path(__file__).resolve().parents[1] / "stars8.bin"


def tycho_line(ra, dec, bt, vt, pflag=" "):
    """One tyc2.dat record laid out as in the CDS ReadMe (206 bytes, '|' separators)."""
    mra = "" if pflag == "X" else f"{ra:12.8f}"
    mde = "" if pflag == "X" else f"{dec:12.8f}"
    f = ["0001 00008 1", pflag, f"{mra:>12}", f"{mde:>12}", "   -12.3", "    -5.1", " 21", " 24", " 2.0", " 2.2",
         "1990.95", "1990.88", " 2", "1.0", "1.0", "0.9", "1.0",
         f"{bt:6.3f}" if bt is not None else "      ", "0.123",
         f"{vt:6.3f}" if vt is not None else "      ", "0.120", "999", "T", "            ",
         f"{ra:12.8f}", f"{dec:12.8f}", "1.81", "1.73", "26.2", "27.3", "1.4", "0.9", "  "]
    return "|".join(f)


def test_generator_reads_tycho_records(tmp_path):
    d = tmp_path / "t2"
    d.mkdir()
    lines = [tycho_line(10.0, 20.0, 9.6, 9.0),            # V = 9.0 - 0.09*0.6 = 8.946: kept
             tycho_line(11.0, -30.0, None, 10.2),          # VT only: kept
             tycho_line(12.0, 40.0, 11.9, 11.0),           # V 10.92: too faint
             tycho_line(13.0, 50.0, 7.5, 7.0),             # V 6.95: in stars8 already, not added
             tycho_line(359.5, 89.0, 10.4, 10.0, "X")]     # no mean position: observed one used
    with gzip.open(d / "tyc2.dat.00.gz", "wt") as fh:
        fh.write("\n".join(lines) + "\n")
    assert mdc.parse_line(lines[0])[2] == 9.0 - 0.090 * 0.6
    out = tmp_path / "stars11.bin"
    base = mdc.read_bin(STARS8)
    n = mdc.build(d, STARS8, out)
    assert n == len(base) + 3
    cat = ps.Catalog.read(out)
    assert np.all(np.diff(cat.mag) >= 0)
    assert abs(cat.mag_max - 10.2) < 1e-6
    added = [(round(r, 4), round(dd, 4), round(m, 2)) for r, dd, m in zip(cat.ra, cat.dec, cat.mag) if m > 8.0]
    assert (10.0, 20.0, 8.95) in added and (11.0, -30.0, 10.2) in added and (359.5, 89.0, 9.96) in added
    assert mdc.check(out)


def synthetic_sky(rnd, ra0, dec0, radius=25.0, v_max=10.5, density=14.0):
    """Uniform stars around ra0/dec0 with Tycho-2-like counts to V 10.5: 14 per deg^2 on average (578,000 stars in
    the real build), about 6 near the galactic poles. Cumulative counts grow about 10^(0.49 m) (1.0 -> 14 per deg^2
    from V 8 to 10.5, as stars8 and the Tycho-2 build give)."""
    area = 2 * math.pi * (1 - math.cos(math.radians(radius))) * (180 / math.pi) ** 2
    n = int(density * area)
    u = rnd.random(n)
    v = v_max + np.log10(np.maximum(u, 1e-9)) / 0.46
    z = rnd.uniform(math.cos(math.radians(radius)), 1.0, n)
    phi = rnd.uniform(0, 2 * math.pi, n)
    x, y = np.sqrt(1 - z * z) * np.cos(phi), np.sqrt(1 - z * z) * np.sin(phi)
    a, d = math.radians(ra0), math.radians(dec0)
    # rotate the cap around +z to (ra0, dec0)
    xr = x * math.sin(d) * math.cos(a) - y * math.sin(a) + z * math.cos(d) * math.cos(a)
    yr = x * math.sin(d) * math.sin(a) + y * math.cos(a) + z * math.cos(d) * math.sin(a)
    zr = -x * math.cos(d) + z * math.sin(d)
    ra = np.degrees(np.arctan2(yr, xr)) % 360
    dec = np.degrees(np.arcsin(np.clip(zr, -1, 1)))
    o = np.argsort(v)
    return ps.Catalog(ra[o], dec[o], v[o])


def render(cat, rnd, f, ra0, dec0, W=2000, H=1333, mag_lim=10.5):
    roll = rnd.random() * 360
    fpx = f / 36.0 * W
    img = 18 + rnd.normal(0, 3, (H, W))
    fov_diag = 2 * math.degrees(math.atan(math.hypot(W, H) / 2 / fpx))
    idx = cat.cone(ra0, dec0, fov_diag / 2 + 0.5, mag_lim)
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    sigma = 1.3
    for i in idx:
        p = ps.project(cat.ra[i], cat.dec[i], ra0, dec0)
        if p is None:
            continue
        xi, eta = math.radians(p[0]), math.radians(p[1])
        u, v = -(xi * cr - eta * sr), -(xi * sr + eta * cr)
        x, y = W / 2 + fpx * u, H / 2 + fpx * v
        if x < 4 or y < 4 or x >= W - 4 or y >= H - 4 or rnd.random() < 0.1:
            continue
        flux = 4000 * 10 ** (-0.4 * (cat.mag[i] - (mag_lim - 1.5)))
        x0, y0 = int(round(x)), int(round(y))
        ys, xs = slice(max(0, y0 - 6), min(H, y0 + 7)), slice(max(0, x0 - 6), min(W, x0 + 7))
        gy, gx = np.mgrid[ys, xs]
        img[ys, xs] += flux / (2 * math.pi * sigma * sigma) * np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * sigma * sigma))
    img = np.clip(img, 0, 255)
    off, dd = 0.5 + rnd.random() * 1.5, rnd.random() * 2 * math.pi       # head pointing 0.5-2 deg off
    hint = ps.unproject(off * math.cos(dd), off * math.sin(dd), ra0, dec0)
    return img, hint, math.degrees(W / fpx)


def test_long_lens_fields_need_the_deep_catalogue():
    rnd = np.random.default_rng(7)
    ok_deep = ok_shallow = wrong = 0
    trials = 8
    for t in range(trials):
        ra0, dec0 = rnd.random() * 360, -60 + rnd.random() * 120
        density = 6.0 if t % 2 else 14.0                  # odd trials: a sparse field near a galactic pole
        deep = synthetic_sky(rnd, ra0, dec0, density=density)
        keep = deep.mag <= 8.0
        shallow = ps.Catalog(deep.ra[keep], deep.dec[keep], deep.mag[keep])
        f = [400, 500, 600][t % 3]
        img, hint, plane_w = render(deep, rnd, f, ra0, dec0)
        stars = ps.detect(img, 60)
        for cat, name in ((deep, "deep"), (shallow, "shallow")):
            s = ps.solve(cat, stars, img.shape[1], img.shape[0], hint[0], hint[1], 3, plane_w, 0.25)
            if s is None:
                print(f"f={f} {density:.0f}/deg2 {name}: not solved ({len(stars)} stars in the frame)")
                continue
            err = math.hypot(*ps.project(s.ra, s.dec, ra0, dec0)) * 3600
            if err > max(60, 3 * s.scale * 3600):
                wrong += 1
                print(f"f={f} {name}: WRONG by {err:.0f}\"")
                continue
            print(f"f={f} {density:.0f}/deg2 {name}: ok {err:.1f}\" matched {s.matched} in {s.millis} ms")
            if name == "deep":
                ok_deep += 1
            else:
                ok_shallow += 1
    print(f"deep {ok_deep}/{trials}, stars8-depth {ok_shallow}/{trials}, wrong {wrong}")
    assert wrong == 0
    assert ok_deep >= trials - 1
    assert ok_deep > ok_shallow


def test_astap_ini_parsing(tmp_path):
    ini = tmp_path / "frame.ini"
    ini.write_text("PLTSOLVD=T\nCRVAL1= 8.3901876E+001\nCRVAL2= 2.2014540E+001\nCDELT1=-1.0E-003\n"
                   "CDELT2= 1.0007E-003\nCROTA1= 1.2E+002\nCROTA2= 1.2012E+002\nCMDLINE=astap_cli -f frame.jpg\n")
    r = astap.parse_ini(ini, 1500)
    assert abs(r["ra"] - 83.901876) < 1e-9 and abs(r["dec"] - 22.01454) < 1e-9
    assert abs(r["scale_deg_px"] - 1.0007e-3) < 1e-12 and abs(r["roll"] - 120.12) < 1e-9 and r["millis"] == 1500
    ini.write_text("PLTSOLVD=F\nERROR=No solution found!\n")
    assert astap.parse_ini(ini) is None
    assert astap.parse_ini(tmp_path / "missing.ini") is None
