"""Slew current and StallGuard margins, warm and cold (R2, R3, test T6 part): bring-up menu item t.

Input : one or more console logs of item t ("t_s,set_dps,rate_dps,cmd_deg,enc_deg,err_arcsec,sg,i_ma,vmot_v,temp_c,diag"
        every 100 ms, then "summary" lines). Run it once at room temperature and once after a night in the freezer
        (rig at about -20 C, R2/R3), each with the current the firmware would use (20 C: 830 mA azimuth; -20 C: 1260 mA).
Output: per speed the lowest and mean StallGuard value while cruising, the worst encoder-minus-steps difference
        (lost steps), DIAG; the cold/warm ratio; a suggested SGTHRS (stall when SG_RESULT <= 2 x SGTHRS, so
        2 x SGTHRS = half the lowest cruising value keeps a factor 2 between normal load and a trip).
Judged: no lost step (< 0.05 deg, D67) up to 8 deg/s warm and up to 6 deg/s at -20 C (spec 1.2, D26).
        StallGuard has no spec number: the margin is reported for the firmware tuning (Phase 5 sec. 10).

Usage: python tools/measure/slew_stallguard.py LOG1.txt [LOG2.txt ...] [--out DIR]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

import stlog

COLS = ["t_s", "set_dps", "rate_dps", "cmd_deg", "enc_deg", "err_arcsec", "sg", "i_ma", "vmot_v", "temp_c", "diag"]


def one(path: Path) -> dict:
    text = stlog.read_text(path)
    b = stlog.block(text, COLS[:4])
    if b is None:
        raise SystemExit(f"{path}: no slew-log block (bring-up item t, Phase 7 image)")
    c = stlog.as_columns(b)
    temp = float(np.nanmedian(c["temp_c"][:20]))          # temperature at the start of the run
    ma = int(np.nanmedian(c["i_ma"]))
    speeds = {}
    for s in sorted(set(c["set_dps"])):
        m = c["set_dps"] == s
        cruise = m & (np.abs(c["rate_dps"]) >= 0.9 * s)
        speeds[float(s)] = {
            "sg_min": float(c["sg"][cruise].min()) if cruise.any() else float("nan"),
            "sg_mean": float(c["sg"][cruise].mean()) if cruise.any() else float("nan"),
            "err_max": float(np.abs(c["err_arcsec"][m]).max()),
            "diag": int(c["diag"][m].sum()),
            "vmot_min": float(c["vmot_v"][m].min()),
        }
    slipped = None
    for line in stlog.verdict_lines(text):
        mm = re.search(r"slipped at (\d+) deg/s", line)
        if mm:
            slipped = float(mm.group(1))
    return {"file": path.name, "temp_c": temp, "i_ma": ma, "speeds": speeds, "slipped_at": slipped, "t": c["t_s"], "sg": c["sg"], "rate": c["rate_dps"],
            "tmax": float(np.nanmax(c["temp_c"]))}


def analyse(paths: list[Path], out: Path | None = None) -> dict:
    runs = [one(p) for p in paths]
    d = stlog.out_dir(paths[0], out)
    p = stlog.plt()
    fig, ax = p.subplots(len(runs), 1, figsize=(10, 3.2 * len(runs)), squeeze=False)
    for i, r in enumerate(runs):
        a = ax[i, 0]
        a.plot(r["t"], r["sg"], lw=0.7, label="SG_RESULT")
        a2 = a.twinx()
        a2.plot(r["t"], r["rate"], lw=0.7, color="tab:orange", label="rate deg/s")
        a.set_ylabel("SG_RESULT (lower = more load)")
        a2.set_ylabel("deg/s")
        a.set_title(f"{r['file']}: {r['temp_c']:.0f} C, {r['i_ma']} mA" + (f", SLIPPED at {r['slipped_at']:.0f} deg/s" if r["slipped_at"] else ""))
    ax[-1, 0].set_xlabel("s")
    fig.tight_layout()
    fig.savefig(d / "slew_stallguard.png")
    res = []
    lowest = []
    for r in runs:
        cold = r["temp_c"] < 0
        need = 6.0 if cold else 8.0
        reached = [s for s, v in r["speeds"].items() if v["err_max"] < stlog.lim("slip")]
        ok = (r["slipped_at"] is None or r["slipped_at"] > need) and all(r["speeds"].get(s, {"err_max": 1e9})["err_max"] < stlog.lim("slip") for s in r["speeds"] if s <= need)
        top = max(reached) if reached else 0.0
        res.append(stlog.Result("T6 / R2-R3", f"slews without lost steps, {r['temp_c']:.0f} C, {r['i_ma']} mA", top, "deg/s",
                                f">= {need:.0f} deg/s ({'-20 C, D26' if cold else '20 C, spec 1.2'})", "pass" if ok and top >= need else "fail", r["file"],
                                "per speed sg_min/mean/err_max: " + "; ".join(f"{s:.0f}: {v['sg_min']:.0f}/{v['sg_mean']:.0f}/{v['err_max']:.0f}\"" for s, v in r["speeds"].items())))
        lowest += [v["sg_min"] for v in r["speeds"].values() if np.isfinite(v["sg_min"])]
        res.append(stlog.Result("T10 (bench)", f"motor temperature during the slew run, {r['temp_c']:.0f} C start", r["tmax"], "deg C", f"<= {stlog.lim('motor_temp'):.0f}",
                                stlog.verdict(r["tmax"], stlog.lim("motor_temp")), r["file"], "thermistor on the cartridge board"))
    ratio = None
    warm = [r for r in runs if r["temp_c"] >= 10]
    coldr = [r for r in runs if r["temp_c"] < 0]
    if warm and coldr:
        w, c = warm[0], coldr[0]
        common = sorted(set(w["speeds"]) & set(c["speeds"]))
        ratio = {s: c["speeds"][s]["sg_mean"] / w["speeds"][s]["sg_mean"] for s in common if w["speeds"][s]["sg_mean"] > 0}
        res.append(stlog.Result("R2", "StallGuard cold / warm (mean while cruising)", float(np.nanmin(list(ratio.values()))) if ratio else float("nan"), "ratio",
                                "lower = more drag in the cold", "info", f"{w['file']} + {c['file']}", ", ".join(f"{s:.0f} deg/s {v:.2f}" for s, v in ratio.items())))
    sgthrs = int(np.floor(0.25 * min(lowest))) if lowest else None
    if sgthrs is not None:
        res.append(stlog.Result("Phase 5 sec. 10", "suggested SGTHRS (stall at SG_RESULT <= 2 x SGTHRS)", sgthrs, "", "half the lowest cruising SG", "info",
                                ", ".join(r["file"] for r in runs), f"lowest cruising SG_RESULT {min(lowest):.0f}; set with config key ST_CFG_SGTHRS after P1 confirms"))
    summary = {"runs": [{k: v for k, v in r.items() if k not in ("t", "sg", "rate")} for r in runs], "cold_warm_ratio": ratio, "sgthrs": sgthrs, "results": res}
    stlog.write_json(d / "slew_stallguard.json", summary)
    return summary


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("logs", type=Path, nargs="+")
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    for r in analyse(args.logs, args.out)["results"]:
        print(" | ".join(r.row()))
