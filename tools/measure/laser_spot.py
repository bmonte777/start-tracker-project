"""Laser spot on a wall: the independent check of periodic error and lost motion (spec 11.2 T1/T2 bench method).

A laser module sits on the head base plate ST-303; its spot falls on a wall a few metres away and a camera on its
own tripod photographs the wall (interval shooting, e.g. one frame per second) or films it. The spot's position
along its path is turned into the axis angle:
  * scale from the commanded rate (default): the mean spot speed over the run is the sidereal rate, 15.041"/s;
  * or from a ruler in the picture: --px-per-mm and --distance-mm (laser pivot to wall).
Output: CSV "t_s,arcsec" (angle minus the straight sidereal line) for periodic_error.py, and a plot of the track.

Usage: python tools/measure/laser_spot.py FRAMES_DIR_or_VIDEO [--interval-s 1] [--fps 1] [--red]
                                         [--px-per-mm P --distance-mm D] [--out DIR]
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import stlog


def frames(src: Path, fps: float):
    if src.is_dir():
        files = sorted([p for p in src.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff")])
        return files, None
    tmp = Path(tempfile.mkdtemp(prefix="laser_"))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src), "-vf", f"fps={fps}", str(tmp / "f_%06d.png")], check=True)
    return sorted(tmp.glob("f_*.png")), 1.0 / fps


def centroid(path: Path, red: bool) -> tuple[float, float, float]:
    im = Image.open(path)
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    g = a[:, :, 0] - 0.5 * (a[:, :, 1] + a[:, :, 2]) if red else a.mean(axis=2)
    # coarse peak on a 4x reduced image, then a weighted centroid in a window around it
    s = g[::4, ::4]
    py, px = np.unravel_index(np.argmax(s), s.shape)
    py, px = py * 4, px * 4
    r = 40
    y0, y1, x0, x1 = max(0, py - r), min(g.shape[0], py + r), max(0, px - r), min(g.shape[1], px + r)
    w = g[y0:y1, x0:x1]
    bg = np.median(g)
    w = np.clip(w - bg - 0.5 * (w.max() - bg), 0, None)
    if w.sum() <= 0:
        return np.nan, np.nan, 0.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    return float((xx * w).sum() / w.sum()), float((yy * w).sum() / w.sum()), float(w.max())


def analyse(src: Path, interval_s: float = 1.0, fps: float = 1.0, red: bool = False, px_per_mm: float | None = None,
            distance_mm: float | None = None, out: Path | None = None) -> dict:
    files, dt_video = frames(src, fps)
    dt = dt_video or interval_s
    pts = np.array([centroid(f, red) for f in files])
    t = np.arange(len(files)) * dt
    ok = np.isfinite(pts[:, 0]) & (pts[:, 2] > 0)
    t, xy = t[ok], pts[ok, :2]
    # direction of travel from the first and last tenth of the track
    n = max(3, len(xy) // 10)
    u = xy[-n:].mean(0) - xy[:n].mean(0)
    u /= np.linalg.norm(u)
    s_px = (xy - xy[0]) @ u
    if px_per_mm and distance_mm:
        ang = np.degrees(np.arctan(s_px / px_per_mm / distance_mm)) * 3600.0
        scale_note = f"ruler scale {px_per_mm} px/mm at {distance_mm} mm"
    else:
        b = np.polyfit(t, s_px, 1)[0]
        ang = s_px * (stlog.SIDEREAL_ASPS / b)
        scale_note = f"scaled from the sidereal rate: {abs(stlog.SIDEREAL_ASPS / b):.2f}\"/px"
    dev = ang - np.sign(ang[-1]) * stlog.SIDEREAL_ASPS * t
    dev -= dev[0]
    d = stlog.out_dir(src, out)
    with open(d / "laser_track.csv", "w") as f:
        f.write("t_s,arcsec\n")
        for a_, b_ in zip(t, dev):
            f.write(f"{a_:.2f},{b_:.3f}\n")
    p = stlog.plt()
    fig, ax = p.subplots(1, 2, figsize=(10, 3.4))
    ax[0].plot(xy[:, 0], xy[:, 1], ".", ms=1)
    ax[0].invert_yaxis()
    ax[0].set_title(f"spot track, {len(t)} frames")
    ax[1].plot(t / 60, dev, lw=0.6)
    ax[1].set_xlabel("minutes")
    ax[1].set_ylabel("arcsec from the sidereal line")
    ax[1].set_title(scale_note)
    fig.tight_layout()
    fig.savefig(d / "laser_track.png")
    return {"frames": len(files), "used": int(ok.sum()), "csv": str(d / "laser_track.csv"), "scale": scale_note}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("src", type=Path)
    a.add_argument("--interval-s", type=float, default=1.0)
    a.add_argument("--fps", type=float, default=1.0)
    a.add_argument("--red", action="store_true", help="red laser: use red minus the other channels")
    a.add_argument("--px-per-mm", type=float)
    a.add_argument("--distance-mm", type=float)
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    print(analyse(args.src, args.interval_s, args.fps, args.red, args.px_per_mm, args.distance_mm, args.out))
