"""Encoder noise at the 0.8 mm chip-to-magnet gap (D48): bring-up menu item o.

Input : console log of item o (1000 readings, shaft still, printed as "i,arcsec").
Output: spread (RMS, p-p), the noise left after the motion core's 200-sample average, a histogram and a time plot.
Judged: <= 10.8" RMS, no weak-field flag, no CRC error (Phase 5 sec. 4). Fail = raise the board 0.5 mm (D48).

Usage: python tools/measure/encoder_noise.py LOG.txt [--out DIR]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

import stlog


def analyse(path: Path, out: Path | None = None) -> dict:
    text = stlog.read_text(path)
    b = stlog.block(text, ["i", "arcsec"])
    if b is None:
        raise SystemExit(f"{path}: no 'i,arcsec' block (item o of the bring-up menu, Phase 7 image or later)")
    c = stlog.as_columns(b)
    x = c["arcsec"]
    n = len(x)
    rms = float(np.std(x))
    pp = float(np.ptp(x))
    # the motion core averages 200 readings every 200 ms (D67): white noise falls by sqrt(200); a drift does not
    k = 200
    means = np.array([x[i:i + k].mean() for i in range(0, n - k + 1, k)])
    avg_rms_white = rms / np.sqrt(k)
    lag1 = float(np.corrcoef(x[:-1], x[1:])[0, 1]) if n > 3 else float("nan")
    flags = {"weak": None, "crc": None}
    for line in stlog.verdict_lines(text):
        m = re.search(r"weak-field (\d+), CRC errors (\d+)", line)
        if m:
            flags = {"weak": int(m.group(1)), "crc": int(m.group(2))}
    missing = 1000 - n
    d = stlog.out_dir(path, out)
    p = stlog.plt()
    fig, ax = p.subplots(1, 2, figsize=(10, 3.4))
    ax[0].plot(np.arange(n), x - x.mean(), lw=0.6)
    ax[0].set_xlabel("reading (1 ms apart)")
    ax[0].set_ylabel("arcsec about the mean")
    ax[0].set_title(f"Encoder still: {rms:.2f}\" RMS, {pp:.1f}\" p-p")
    ax[1].hist(x - x.mean(), bins=40)
    ax[1].axvline(-stlog.lim("enc_noise_rms"), color="r", ls="--")
    ax[1].axvline(stlog.lim("enc_noise_rms"), color="r", ls="--", label="limit 10.8\" RMS")
    ax[1].set_xlabel("arcsec")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(d / "encoder_noise.png")
    lim = stlog.lim("enc_noise_rms")
    ok_flags = (flags["weak"] in (0, None)) and (flags["crc"] in (0, None))
    res = [
        stlog.Result("D48 / item o", "encoder noise, shaft still", rms, "arcsec RMS", f"<= {lim}", stlog.verdict(rms, lim) if ok_flags else "fail", path.name,
                     f"{n} readings, p-p {pp:.1f}\", weak-field {flags['weak']}, CRC {flags['crc']}" + (f", {missing} lines missing" if missing > 0 else "")),
        stlog.Result("D48 / item o", "noise after the 200-reading average (estimate)", float(avg_rms_white), "arcsec RMS", "0.3\" allowance (spec 4.1)",
                     "info", path.name, f"white-noise estimate; lag-1 correlation {lag1:.2f} (near 0 = white)"),
    ]
    summary = {"n": n, "rms": rms, "pp": pp, "mean_of_200_rms_measured": float(np.std(means)) if len(means) > 1 else None,
               "avg_rms_white": float(avg_rms_white), "lag1": lag1, "flags": flags, "results": res}
    stlog.write_json(d / "encoder_noise.json", summary)
    return summary


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("log", type=Path)
    a.add_argument("--out", type=Path)
    s = analyse(a.parse_args().log, a.parse_args().out)
    for r in s["results"]:
        print(" | ".join(r.row()))
