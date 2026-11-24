"""Backlash and lost motion at reversals (spec 1.2, test T1): bring-up menu item q.

Input : console log of item q ("pass,n,dir,cmd_arcsec,enc_arcsec,err_arcsec"): pass 0 with the encoder correction
        off (raw), pass 1 with it on (D67, 2" deadband); runs of 5 moves forward then 5 back, 3 cycles.
        Optional --dial FILE: your dial-indicator readings for the same stops (CSV "pass,n,dial_um"), read on an arm
        of --arm-mm length (T1: 200 mm, where 1 um = 1.03"); this is the independent check of the encoder.
Output: lost motion = mean error after moves 3-5 of the forward runs minus the same for the back runs, per pass and
        per cycle; a plot of error against stop number.
Judged: raw <= 20" (azimuth, altitude) or 30" (roll); with the loop <= 10" (spec 1.2, T1).

Usage: python tools/measure/lost_motion.py LOG.txt [--axis az] [--dial dial.csv --arm-mm 200] [--out DIR]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import stlog


def lm_of(n, dirs, err):
    use = (n % 5) >= 2
    f, b = err[use & (dirs > 0)], err[use & (dirs < 0)]
    if len(f) == 0 or len(b) == 0:
        return float("nan"), []
    per = []
    for cyc in range(int(n.max() // 10) + 1):
        mc = use & (n // 10 == cyc)
        ff, bb = err[mc & (dirs > 0)], err[mc & (dirs < 0)]
        if len(ff) and len(bb):
            per.append(float(abs(ff.mean() - bb.mean())))
    return float(abs(f.mean() - b.mean())), per


def analyse(path: Path, axis: str = "az", dial: Path | None = None, arm_mm: float = 200.0, out: Path | None = None) -> dict:
    text = stlog.read_text(path)
    b = stlog.block(text, ["pass", "n", "dir", "cmd_arcsec", "enc_arcsec", "err_arcsec"])
    if b is None:
        raise SystemExit(f"{path}: no lost-motion block (bring-up item q, Phase 7 image)")
    c = stlog.as_columns(b)
    out_p = {}
    for ps in (0, 1):
        m = c["pass"] == ps
        if m.sum() < 10:
            continue
        lm, per = lm_of(c["n"][m].astype(int), c["dir"][m], c["err_arcsec"][m])
        out_p[ps] = {"lm": lm, "per_cycle": per, "n": int(m.sum())}
    dial_res = None
    if dial is not None:
        dd = np.genfromtxt(dial, delimiter=",", names=True)
        m0 = c["pass"] == 0
        cmd = dict(zip(c["n"][m0].astype(int), c["cmd_arcsec"][m0]))
        dirs = dict(zip(c["n"][m0].astype(int), c["dir"][m0]))
        sel = dd["pass"] == 0
        n = dd["n"][sel].astype(int)
        ang = dd["dial_um"][sel] / 1000.0 / arm_mm * 206264.8
        ang -= ang[0]
        ok = np.array([k in cmd for k in n])
        err = ang[ok] - np.array([cmd[k] for k in n[ok]])
        lm, per = lm_of(n[ok], np.array([dirs[k] for k in n[ok]]), err)
        dial_res = {"lm": lm, "per_cycle": per, "arcsec_per_um": 206264.8 / 1000.0 / arm_mm}
    d = stlog.out_dir(path, out)
    p = stlog.plt()
    fig, ax = p.subplots(1, 1, figsize=(10, 3.8))
    for ps, lab in [(0, "raw (loop off)"), (1, "encoder loop on")]:
        m = c["pass"] == ps
        if m.any():
            ax.plot(c["n"][m], c["err_arcsec"][m] - np.mean(c["err_arcsec"][m]), "o-", ms=3, lw=0.8, label=lab)
    ax.set_xlabel("stop (runs of 5: forward, back, ...)")
    ax.set_ylabel("encoder minus command, arcsec")
    ax.legend()
    ax.set_title("Lost motion: " + ", ".join(f"{'raw' if k == 0 else 'loop'} {v['lm']:.1f}\"" for k, v in out_p.items()))
    fig.tight_layout()
    fig.savefig(d / "lost_motion.png")
    raw_lim = stlog.lim("lost_motion_raw_roll" if axis == "roll" else "lost_motion_raw_az_alt")
    res = []
    if 0 in out_p:
        v = out_p[0]
        res.append(stlog.Result("T1", f"lost motion raw, {axis}", v["lm"], "arcsec", f"<= {raw_lim:.0f}", stlog.verdict(v["lm"], raw_lim), path.name,
                                "per cycle " + ", ".join(f"{x:.1f}" for x in v["per_cycle"]) + "\""))
    if 1 in out_p:
        v = out_p[1]
        res.append(stlog.Result("T1", f"lost motion with encoder loop, {axis}", v["lm"], "arcsec", f"<= {stlog.lim('lost_motion_loop'):.0f}",
                                stlog.verdict(v["lm"], stlog.lim("lost_motion_loop")), path.name, "per cycle " + ", ".join(f"{x:.1f}" for x in v["per_cycle"]) + "\""))
    if dial_res:
        enc = out_p.get(0, {}).get("lm", float("nan"))
        res.append(stlog.Result("T1 (dial)", "lost motion raw, dial indicator", dial_res["lm"], "arcsec", f"<= {raw_lim:.0f}", stlog.verdict(dial_res["lm"], raw_lim),
                                Path(dial).name, f"arm {arm_mm:.0f} mm ({dial_res['arcsec_per_um']:.2f}\"/um); encoder said {enc:.1f}\""))
    summary = {"passes": out_p, "dial": dial_res, "results": res}
    stlog.write_json(d / "lost_motion.json", summary)
    return summary


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("log", type=Path)
    a.add_argument("--axis", default="az", choices=["az", "alt", "roll"])
    a.add_argument("--dial", type=Path)
    a.add_argument("--arm-mm", type=float, default=200.0)
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    for r in analyse(args.log, args.axis, args.dial, args.arm_mm, args.out)["results"]:
        print(" | ".join(r.row()))
