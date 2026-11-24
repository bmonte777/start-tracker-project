"""Encoder linearity over one revolution (D48 part 2, R7): bring-up menu item p.

Input : console log of item p ("t_s,cmd_deg,enc_deg,dev_arcsec,status" every 100 ms, plus the verdict line).
Output: raw encoder-minus-steps curve against angle; its harmonics 1-8 (magnet and mounting errors, D67); what a
        D67 map (harmonics 1-8 plus a 0.5 deg grid averaged over +/-0.9 deg) would leave; the reducer's own error
        seen in the sweep (orders 100 and 200 of the output turn).
Judged: no reversal, jump, flat spot, weak-field flag or CRC error (Phase 5 sec. 4, item p);
        raw p-p within the datasheet +/-0.07 deg (spec 4.5) - larger means the magnet is off-centre (R7);
        residual after the map <= 10" RMS (go-to budget, spec 4.5).

Usage: python tools/measure/encoder_sweep.py LOG.txt [--out DIR]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

import stlog


def map_residual(ang_deg: np.ndarray, dev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Emulate the D67 map: harmonics 1-8 of the turn, then a 0.5 deg grid of the remainder averaged over +/-0.9 deg."""
    fit = stlog.fit_harmonics(ang_deg, dev, 360.0, range(1, 9), poly_deg=0)
    rem = fit["resid"]
    grid = np.arange(np.floor(ang_deg.min()), np.ceil(ang_deg.max()) + 0.5, 0.5)
    gval = np.array([rem[np.abs(ang_deg - g) <= 0.9].mean() if np.any(np.abs(ang_deg - g) <= 0.9) else 0.0 for g in grid])
    model = fit["poly"] + fit["harm"] + np.interp(ang_deg, grid, gval)
    return fit, dev - model


def analyse(path: Path, out: Path | None = None) -> dict:
    text = stlog.read_text(path)
    b = stlog.block(text, ["t_s", "cmd_deg", "enc_deg", "dev_arcsec"])
    if b is None:
        raise SystemExit(f"{path}: no sweep block (item p of the bring-up menu, Phase 7 image or later)")
    c = stlog.as_columns(b)
    ang = c["cmd_deg"] - c["cmd_deg"][0]
    dev = c["dev_arcsec"]
    m = stlog.robust_mask(dev, 15)
    ang, dev = ang[m], dev[m]
    order = np.argsort(ang)
    ang, dev = ang[order], dev[order]
    span = float(np.ptp(ang))
    raw_pp = float(np.ptp(dev))
    fit, resid = map_residual(ang, dev)
    harm_pp = float(np.ptp(fit["harm"]))
    # the reducer's own error (output angle: wave generator turn = 3.6 deg, main error 1.8 deg) is left in on purpose
    # by the map (D67 grid averages over +/-0.9 deg); take it out to judge the map itself
    red = {}
    if span > 30:
        rf = stlog.fit_harmonics(ang, resid, 360.0, [100, 200, 300, 400], poly_deg=0)
        red, resid_map = rf["amps"], rf["resid"]
    else:
        resid_map = resid
    after_rms = float(np.std(resid_map))
    after_rms_with_reducer = float(np.std(resid))
    counts = {}
    for line in stlog.verdict_lines(text):
        mm = re.search(r"reversals (\d+), jumps (\d+), flat spots (\d+), weak-field (\d+), CRC (\d+)", line)
        if mm:
            counts = dict(zip(["reversals", "jumps", "flat_spots", "weak_field", "crc"], map(int, mm.groups())))
    clean = bool(counts) and all(v == 0 for v in counts.values())
    d = stlog.out_dir(path, out)
    p = stlog.plt()
    fig, ax = p.subplots(2, 1, figsize=(10, 6), sharex=True)
    ax[0].plot(ang, dev, lw=0.6, label="encoder minus steps (raw)")
    ax[0].plot(ang, fit["poly"] + fit["harm"], lw=1.2, label="harmonics 1-8")
    ax[0].set_ylabel("arcsec")
    ax[0].legend()
    ax[0].set_title(f"Raw linearity {raw_pp:.0f}\" p-p over {span:.0f} deg; limit {stlog.lim('enc_linearity_pp'):.0f}\" p-p")
    ax[1].plot(ang, resid, lw=0.6)
    ax[1].set_ylabel("left after map, arcsec")
    ax[1].set_xlabel("angle swept (encoder side), deg")
    ax[1].set_title(f"After a D67 map: {after_rms:.1f}\" RMS (limit {stlog.lim('enc_map_after_rms'):.0f}\")")
    fig.tight_layout()
    fig.savefig(d / "encoder_sweep.png")
    res = [
        stlog.Result("D48 / item p", "sweep clean (reversals, jumps, flat spots, weak field, CRC)", None, "", "all 0",
                     "pass" if clean else ("fail" if counts else "not run"), path.name, str(counts) if counts else "verdict line not found"),
        stlog.Result("R7 / item p", "raw linearity", raw_pp, "arcsec p-p", f"<= {stlog.lim('enc_linearity_pp'):.0f} (+/-0.07 deg)",
                     stlog.verdict(raw_pp, stlog.lim("enc_linearity_pp")) if span > 300 else "info", path.name,
                     f"swept {span:.0f} deg" + ("" if span > 300 else "; less than a turn, so p-p is a lower bound")),
        stlog.Result("D67 / item p", "residual after a map (emulated)", after_rms, "arcsec RMS", f"<= {stlog.lim('enc_map_after_rms'):.0f}",
                     stlog.verdict(after_rms, stlog.lim("enc_map_after_rms")), path.name, f"harmonics 1-8 carry {harm_pp:.0f}\" p-p; with the reducer's own error left in: {after_rms_with_reducer:.1f}\" RMS"),
    ]
    summary = {"span_deg": span, "raw_pp": raw_pp, "harmonic_pp": harm_pp, "harmonic_amps": fit["amps"], "after_map_rms": after_rms, "after_map_rms_with_reducer": after_rms_with_reducer,
               "reducer_in_sweep_amps": red, "counts": counts, "results": res}
    stlog.write_json(d / "encoder_sweep.json", summary)
    return summary


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("log", type=Path)
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    for r in analyse(args.log, args.out)["results"]:
        print(" | ".join(r.row()))
