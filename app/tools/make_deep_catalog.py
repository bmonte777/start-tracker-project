"""Build stars11.bin, the deeper plate-solving catalogue for 300-600 mm lenses (decision D74).

stars11.bin = every star of stars8.bin (the reused catalogue, to V 8) + Tycho-2 stars with 8.0 < V <= 10.5,
in the same format the solvers read: "STR1", u32 count, then count x (float32 ra, float32 dec, int16 mag*100),
little-endian, sorted brightest first. About 578,000 stars (14 per square degree on average), 5.8 MB.

Tycho-2 (Hog et al. 2000, CDS I/259): tyc2.dat.00.gz ... tyc2.dat.19.gz, records separated by '|':
  field 1 pflag, 2 mRAdeg, 3 mDEdeg (mean position, ICRS, epoch J2000; blank when pflag = X),
  17 BTmag, 19 VTmag, 24 RAdeg, 25 DEdeg (observed position, epoch ~1991, used when the mean one is blank).
  Johnson V = VT - 0.090 (BT - VT); VT alone when BT is blank; BT alone when VT is blank (rare, faint).
Source of the layout: CDS ReadMe for I/259 (byte-by-byte description of tyc2.dat).

Usage (the workflow runs this; no terminal needed on your side):
  python app/tools/make_deep_catalog.py --tycho DIR [--download] --stars8 app/windows/backend/stars8.bin --out stars11.bin
  python app/tools/make_deep_catalog.py --check stars11.bin
"""
import argparse
import gzip
import struct
import sys
import urllib.request
from pathlib import Path

import numpy as np

MIRRORS = ["https://cdsarc.cds.unistra.fr/ftp/cats/I/259/", "https://vizier.cfa.harvard.edu/ftp/cats/1/259/",
           "https://cdsarc.cds.unistra.fr/vizier/ftp/I/259/"]
V_MIN, V_MAX = 8.0, 10.5
MAGIC = 0x31525453
REC = np.dtype([("ra", "<f4"), ("dec", "<f4"), ("mag", "<i2")])


def read_bin(path):
    data = Path(path).read_bytes()
    magic, n = struct.unpack_from("<II", data, 0)
    if magic != MAGIC:
        raise IOError(f"{path}: not a star catalogue")
    return np.frombuffer(data, dtype=REC, count=n, offset=8).copy()


def write_bin(path, rec):
    rec = rec[np.argsort(rec["mag"], kind="stable")]
    with open(path, "wb") as f:
        f.write(struct.pack("<II", MAGIC, len(rec)))
        f.write(rec.astype(REC).tobytes())
    return len(rec)


def download(dirpath):
    d = Path(dirpath)
    d.mkdir(parents=True, exist_ok=True)
    for i in range(20):
        name = f"tyc2.dat.{i:02d}.gz"
        dest = d / name
        if dest.is_file() and dest.stat().st_size > 1_000_000:
            continue
        for m in MIRRORS:
            try:
                print("downloading", m + name, flush=True)
                urllib.request.urlretrieve(m + name, dest)
                break
            except OSError as e:
                print("  failed:", e, flush=True)
        else:
            raise IOError(f"could not download {name}")


def parse_line(line):
    """(ra, dec, V) or None. line: one tyc2.dat record (str)."""
    f = line.split("|")
    if len(f) < 26:
        return None
    try:
        if f[1].strip() == "X" or not f[2].strip():
            ra, dec = float(f[24]), float(f[25])
        else:
            ra, dec = float(f[2]), float(f[3])
    except ValueError:
        return None
    bt, vt = f[17].strip(), f[19].strip()
    if vt and bt:
        v = float(vt) - 0.090 * (float(bt) - float(vt))
    elif vt:
        v = float(vt)
    elif bt:
        v = float(bt)
    else:
        return None
    return ra, dec, v


def read_tycho(dirpath):
    files = sorted(Path(dirpath).glob("tyc2.dat.*"))
    if not files:
        raise IOError(f"no tyc2.dat.* files in {dirpath}")
    ras, decs, mags = [], [], []
    for fp in files:
        op = gzip.open if fp.suffix == ".gz" else open
        with op(fp, "rt", encoding="ascii", errors="replace") as fh:
            for line in fh:
                r = parse_line(line)
                if r and V_MIN < r[2] <= V_MAX:
                    ras.append(r[0]); decs.append(r[1]); mags.append(r[2])
    return np.array(ras), np.array(decs), np.array(mags)


def build(tycho_dir, stars8, out, min_stars=0):
    base = read_bin(stars8)
    ra, dec, v = read_tycho(tycho_dir)
    t = np.zeros(len(ra), dtype=REC)
    t["ra"], t["dec"], t["mag"] = ra % 360.0, dec, np.round(v * 100).astype(np.int16)
    n = write_bin(out, np.concatenate([base, t]))
    print(f"{out}: {n} stars ({len(base)} from stars8, {len(t)} from Tycho-2, V {V_MIN}-{V_MAX})")
    if n < min_stars:
        raise SystemExit(f"only {n} stars: the Tycho-2 files were not read correctly (expected at least {min_stars})")
    return n


def check(path):
    r = read_bin(path)
    m = r["mag"] / 100.0
    ok = (np.all(np.diff(r["mag"]) >= 0) and np.all((r["ra"] >= 0) & (r["ra"] < 360))
          and np.all(np.abs(r["dec"]) <= 90))
    per_deg2 = len(r) / 41253.0
    print(f"{path}: {len(r)} stars, V {m.min():.2f}..{m.max():.2f}, {per_deg2:.1f} per square degree, "
          f"{'sorted and in range' if ok else 'BAD'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tycho", help="folder with tyc2.dat.00.gz ... tyc2.dat.19.gz")
    ap.add_argument("--download", action="store_true", help="fetch the Tycho-2 files from CDS first")
    ap.add_argument("--stars8", default=str(Path(__file__).resolve().parents[1] / "windows/backend/stars8.bin"))
    ap.add_argument("--out", default="stars11.bin")
    ap.add_argument("--min-stars", type=int, default=0, help="fail below this many stars (the workflow uses 450000; Tycho-2 gives about 578000 to V 10.5)")
    ap.add_argument("--check", help="check an existing stars11.bin and exit")
    a = ap.parse_args()
    if a.check:
        sys.exit(0 if check(a.check) else 1)
    if a.download:
        download(a.tycho)
    build(a.tycho, a.stars8, a.out, a.min_stars)
    sys.exit(0 if check(a.out) else 1)
