"""Results kept by the head's system firmware: encoder map (cal.encoder), PEC table (pec.*), temperatures.

Inputs (saved with the bench logger page while the system firmware runs):
  --cal  cal.json       reply of cal.status after cal.encoder.start has finished (D67 routine)
  --pec  pec.json       reply of pec.get for the axis, after pec.record has finished
  --pe   periodic_error.json   (optional) the T2 result of periodic_error.py, to compare with
  --head head.csv       a state recording (5 Hz) of any session: temperatures and rail voltage

Judged:
  * encoder map: raw p-p within +/-0.07 deg (spec 4.5); what the map itself leaves <= 10" RMS (go-to budget,
    spec 4.5). The routine's after_rms_as still contains the reducer's own error on purpose (D67 grid averages
    over +/-0.9 deg), so the map's own residual is sqrt(after^2 - PE_rms^2) when the T2 result is given.
  * PEC table: learned periodic error p-p; with --pe, how well it matches the T2 curve (correlation, amplitude).
  * temperatures: motor thermistors <= 80 C (Phase 4 10.7, T10), rise above the start of the log.

Usage: python tools/measure/head_results.py [--cal cal.json] [--pec pec.json] [--pe periodic_error.json]
                                            [--head head.csv] [--axis az] [--out DIR]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

import stlog

AX = {"az": 0, "alt": 1, "roll": 2}


def _result(obj):
    """Accept either the bare result object or the whole reply {"v":1,"id":..,"ok":true,"result":{...}}."""
    if isinstance(obj, dict) and "result" in obj and isinstance(obj["result"], dict):
        obj = obj["result"]
    return obj


def encoder_map(cal_path: Path, pe: dict | None) -> list[stlog.Result]:
    c = _result(stlog.read_json(cal_path))
    r = c.get("result", c)
    if "after_rms_as" not in r:
        return [stlog.Result("D67", "encoder map", None, "", "", "not run", cal_path.name, f"no result in the file (state {c.get('state')}, reason {c.get('reason')})")]
    raw_pp, after = float(r["raw_pp_as"]), float(r["after_rms_as"])
    out = [stlog.Result("R7 / D67", f"encoder raw p-p (axis {r.get('axis')})", raw_pp, "arcsec p-p", f"<= {stlog.lim('enc_linearity_pp'):.0f}",
                        stlog.verdict(raw_pp, stlog.lim("enc_linearity_pp")) if r.get("full_turn") else "info", cal_path.name,
                        f"{r.get('samples')} samples over {r.get('travel_d')} deg; harmonics 1-8 {r.get('harmonic_rms_as')}\" RMS")]
    if pe and pe.get("pe_rms") is not None:
        own = math.sqrt(max(0.0, after ** 2 - pe["pe_rms"] ** 2))
        out.append(stlog.Result("spec 4.5 / D67", "residual of the map itself", own, "arcsec RMS", f"<= {stlog.lim('enc_map_after_rms'):.0f}",
                                stlog.verdict(own, stlog.lim("enc_map_after_rms")), cal_path.name, f"after_rms {after:.1f}\" minus the reducer's {pe['pe_rms']:.1f}\" RMS (T2)"))
    else:
        out.append(stlog.Result("D67", "left after the map (includes the reducer's own error)", after, "arcsec RMS", "about the T2 periodic error RMS", "info", cal_path.name,
                                "give --pe to separate the map's own residual"))
    return out


def pec_table(pec_path: Path, pe: dict | None) -> list[stlog.Result]:
    r = _result(stlog.read_json(pec_path))
    tab = np.array(r.get("table_as", []), dtype=float)
    raw = np.array(r.get("raw_as", []), dtype=float)
    if tab.size == 0:
        return [stlog.Result("T3", "PEC table", None, "", "", "not run", pec_path.name, "empty table")]
    learned = -tab          # table = - smoothed error (Phase 6 pec.record)
    out = [stlog.Result("T3", f"PEC learned error (axis {r.get('axis')})", float(np.ptp(learned) / 2), "arcsec half p-p", "compare with T2", "info", pec_path.name,
                        f"{learned.size} points over 861.6 s; raw curve left after smoothing {float(np.std(raw - learned)) if raw.size == learned.size else float('nan'):.2f}\" RMS")]
    if pe and pe.get("pe_half_pp"):
        ratio = float(np.ptp(learned) / 2) / pe["pe_half_pp"]
        out.append(stlog.Result("T3", "PEC amplitude / T2 amplitude", ratio, "", "0.8-1.2 expected", "pass" if 0.8 <= ratio <= 1.2 else "fail", pec_path.name,
                                "the learned table should match the measured periodic error"))
    return out


def temperatures(head_path: Path) -> list[stlog.Result]:
    h = stlog.read_head_csv(head_path)
    out = []
    for ax in ("az", "alt", "roll"):
        k = f"{ax}_temp_c"
        if k not in h or not np.isfinite(h[k]).any():
            continue
        tt = h[k][np.isfinite(h[k])]
        if np.nanmax(tt) > 200 or np.nanmin(tt) < -60:       # open or shorted thermistor (no motor on that axis)
            continue
        out.append(stlog.Result("T10 (bench)", f"motor temperature {ax}", float(tt.max()), "deg C", f"<= {stlog.lim('motor_temp'):.0f}",
                                stlog.verdict(float(tt.max()), stlog.lim("motor_temp")), head_path.name,
                                f"start {tt[0]:.1f} C, rise {tt.max() - tt[0]:.1f} K over {(h['t_s'][-1] - h['t_s'][0]) / 60:.0f} min"))
    if "vmot" in h:
        v = h["vmot"][np.isfinite(h["vmot"]) & (h["vmot"] > 5)]
        if v.size:
            out.append(stlog.Result("Phase 4 C1", "motor rail while on", float(v.min()), "V min", ">= 8.8 (10 V level), >= 14.0 (16 V)", "info", head_path.name,
                                    f"max {v.max():.2f} V"))
    return out


def main(args) -> dict:
    pe = stlog.read_json(args.pe) if args.pe else None
    res: list[stlog.Result] = []
    if args.cal:
        res += encoder_map(args.cal, pe)
    if args.pec:
        res += pec_table(args.pec, pe)
    if args.head:
        res += temperatures(args.head)
    first = args.cal or args.pec or args.head
    if first is None:
        raise SystemExit("give at least one of --cal, --pec, --head")
    d = stlog.out_dir(first, args.out)
    stlog.write_json(d / "head_results.json", {"results": res})
    return {"results": res}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--cal", type=Path)
    a.add_argument("--pec", type=Path)
    a.add_argument("--pe", type=Path)
    a.add_argument("--head", type=Path)
    a.add_argument("--axis", default="az", choices=list(AX))
    a.add_argument("--out", type=Path)
    for r in main(a.parse_args())["results"]:
        print(" | ".join(r.row()))
