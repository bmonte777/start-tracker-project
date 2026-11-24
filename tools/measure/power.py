"""Power per mode and runtime (test T9, spec 5.1).

Inputs:
  * readings.csv, written by hand from the bench supply's display: "mode,volts,amps[,note]" - one row per mode,
    each read after the value has settled (or the average of a few readings); or
  * --log supply.csv --modes modes.csv: a recording from the RD6006 PC software (any CSV with a time column and
    voltage and current columns; names are matched loosely) and "mode,start_s,end_s" marking when each mode ran.
Modes understood (P0, one azimuth axis on the bench supply):
  idle      bring-up menu or system firmware, motor rail off
  hold      rail on, azimuth holding (system default 0.25 A; bring-up tests 0.30 A)
  track     azimuth tracking at sidereal (system default 0.32 A; bring-up item k 0.30 A)
  slew      a slew at 8 deg/s (mechanical power on top, so information only)
P1 modes (whole head, spec 5.1): p1_idle, p1_eq_track, p1_altaz_track, p1_altaz_cold, p1_track_camera.
Predictions use spec 5.1's own formulas: logic 0.90 W / 0.90, each motor (2 I^2 R + 0.1 W) / 0.90 boost efficiency,
R = 1.4 ohm (48 mm motor) or 2.3 ohm (38 mm). Judged: within 20 % (T9). Runtime = 62.9 Wh (spec 5.1) / power.

Usage: python tools/measure/power.py readings.csv [--hold-a 0.25 --track-a 0.32] [--out DIR]
       python tools/measure/power.py --log supply.csv --modes modes.csv [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

import stlog

USABLE_WH = 62.9   # spec 5.1, 20 C


def motor_w(i_a: float, r: float) -> float:
    return (2 * i_a * i_a * r + 0.1) / stlog.BOOST_EFF


def predictions(hold_a: float, track_a: float, slew_a: float) -> dict[str, tuple[float, str, bool]]:
    logic = stlog.LOGIC_W / stlog.BOOST_EFF
    R = stlog.R_COIL["az"]
    return {
        "idle": (logic, "0.90 W / 0.90 (spec 5.1); Wi-Fi off in the bring-up image", True),
        "hold": (logic + motor_w(hold_a, R), f"logic + (2 x {hold_a}^2 x 1.4 + 0.1) / 0.90", True),
        "track": (logic + motor_w(track_a, R), f"logic + (2 x {track_a}^2 x 1.4 + 0.1) / 0.90", True),
        "slew": (logic + motor_w(slew_a, R), f"logic + copper loss at {slew_a} A; mechanical power comes on top", False),
        "p1_idle": (1.2, "spec 5.1 table", True),
        "p1_eq_track": (1.8, "spec 5.1 table", True),
        "p1_altaz_track": (2.5, "spec 5.1 table", True),
        "p1_altaz_cold": (7.0, "spec 5.1 table", True),
        "p1_track_camera": (8.0, "spec 5.1 table (camera 5 W)", True),
    }


def _col(names, *keys):
    for n in names:
        low = n.lower()
        if any(k in low for k in keys):
            return n
    return None


def from_log(log: Path, modes: Path) -> list[tuple[str, float, float, str]]:
    with open(log, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    names = list(rows[0].keys())
    ct, cv, ci = _col(names, "time", "sec", "t_s"), _col(names, "volt", "u(", "v_out", "vout"), _col(names, "curr", "amp", "i(", "i_out", "iout")
    if not (ct and cv and ci):
        raise SystemExit(f"{log}: need time, voltage and current columns; found {names}")

    def num(x):
        try:
            return float(x)
        except ValueError:
            # hh:mm:ss
            parts = [float(p) for p in x.split(":")]
            return sum(p * 60 ** (len(parts) - 1 - i) for i, p in enumerate(parts))

    t = np.array([num(r[ct]) for r in rows])
    t -= t[0]
    v = np.array([float(r[cv]) for r in rows])
    i = np.array([float(r[ci]) for r in rows])
    out = []
    with open(modes, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = (t >= float(r["start_s"])) & (t <= float(r["end_s"]))
            if m.sum():
                out.append((r["mode"].strip(), float(v[m].mean()), float(i[m].mean()), f"{m.sum()} samples"))
    return out


def analyse(readings: Path | None, log: Path | None, modes: Path | None, hold_a=0.25, track_a=0.32, slew_a=0.83, out: Path | None = None) -> dict:
    if readings:
        with open(readings, newline="", encoding="utf-8") as f:
            data = [(r["mode"].strip(), float(r["volts"]), float(r["amps"]), r.get("note", "")) for r in csv.DictReader(f)]
        src = readings
    else:
        data = from_log(log, modes)
        src = log
    pred = predictions(hold_a, track_a, slew_a)
    res = []
    table = []
    for mode, v, a, note in data:
        w = v * a
        p = pred.get(mode)
        if p:
            dev = (w - p[0]) / p[0]
            verdict = ("pass" if abs(dev) <= stlog.lim("power_tol") else "fail") if p[2] else "info"
            lim = f"{p[0]:.2f} W +/-20 % ({p[1]})"
        else:
            dev, verdict, lim = float("nan"), "info", "no prediction for this mode"
        runtime = USABLE_WH / w if w > 0 else float("nan")
        res.append(stlog.Result("T9", f"power, {mode}", w, "W", lim, verdict, Path(src).name, f"{v:.2f} V x {a:.3f} A; {dev:+.0%} vs prediction; {runtime:.1f} h on 62.9 Wh. {note}".strip()))
        table.append({"mode": mode, "v": v, "a": a, "w": w, "pred_w": p[0] if p else None, "dev": dev, "runtime_h": runtime})
    d = stlog.out_dir(Path(src), out)
    stlog.write_json(d / "power.json", {"table": table, "results": res})
    return {"table": table, "results": res}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("readings", type=Path, nargs="?")
    a.add_argument("--log", type=Path)
    a.add_argument("--modes", type=Path)
    a.add_argument("--hold-a", type=float, default=0.25)
    a.add_argument("--track-a", type=float, default=0.32)
    a.add_argument("--slew-a", type=float, default=0.83)
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    if not args.readings and not (args.log and args.modes):
        a.error("give readings.csv, or --log and --modes")
    for r in analyse(args.readings, args.log, args.modes, args.hold_a, args.track_a, args.slew_a, args.out)["results"]:
        print(" | ".join(r.row()))
