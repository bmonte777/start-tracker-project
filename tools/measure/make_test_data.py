"""Synthetic raw files with known answers, in the exact formats the bring-up image and the bench logger write.

Used by test_measure.py to prove each script recovers what was put in. Nothing here is a measurement.
Usage: python tools/measure/make_test_data.py OUT_DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

import stlog

RNG = np.random.default_rng(7)
TRUTH = {}


def console(lines: list[str], title: str) -> str:
    head = ["", "===== Star Tracker bring-up, ESP32-S3 image 0.1.0 =====", "choose: ", f"--- {title} ---",
            "axis? 0 = azimuth (J7), 1 = altitude (J8), 2 = roll (J9)  [default 0]", "0"]
    return "\n".join(head + ["  " + l for l in lines]) + "\n"


def noise(d: Path):
    x = RNG.normal(0, 6.0, 1000)
    lines = ["i,arcsec"] + [f"{i},{v:.3f}" for i, v in enumerate(x)]
    lines.append(f"PASS  azimuth: 1000 readings, spread {x.std():.2f}\" RMS, {np.ptp(x):.1f}\" p-p, weak-field 0, CRC errors 0 (limit 10.8\" RMS = 2x datasheet, no warnings). Fail = raise the board 0.5 mm (D48)")
    (d / "P0-A_o_az.txt").write_text(console(lines, "D8  encoder noise, 1000 readings (D48)"))
    TRUTH["noise_rms"] = float(x.std())


def sweep(d: Path):
    t = np.arange(0, 360, 0.1)
    ang = t * 1.0
    th = np.radians(ang)
    dev = 150 * np.sin(th + 0.3) + 40 * np.sin(2 * th) + 15 * np.sin(np.radians(ang * 200)) + RNG.normal(0, 2.0, ang.size)
    lines = ["t_s,cmd_deg,enc_deg,dev_arcsec,status"] + [f"{a:.2f},{c:.5f},{c + v / 3600:.5f},{v:.2f},0" for a, c, v in zip(t, ang + 12.3, dev)]
    lines.append("PASS  azimuth sweep 360 deg: 360000 samples, reversals 0, jumps 0, flat spots 0, weak-field 0, CRC 0; encoder minus steps -190..190\" (raw linearity, before the map)")
    (d / "P0-A_p_az.txt").write_text(console(lines, "D8  encoder sweep, one revolution (D48)"))
    TRUTH["sweep_pp"] = float(np.ptp(dev))


def track(d: Path, minutes=45, name="P0-A_k45_az.txt"):
    t = np.arange(0, minutes * 60 + 1, 1.0)
    P = stlog.WG_PERIOD_S
    pe = 15 * np.sin(2 * np.pi * 2 * t / P) + 6 * np.sin(2 * np.pi * t / P + 1.0) + 3 * np.sin(2 * np.pi * 3 * t / P + 0.4)
    fs = 1.0 * np.sinc(1 / stlog.FULLSTEP_PERIOD_S) * np.sin(2 * np.pi * t / stlog.FULLSTEP_PERIOD_S)
    trend = 4e-6 * (t - 1000) ** 2 + 0.002 * t
    err = pe + fs + trend + RNG.normal(0, 0.3, t.size)
    cmd = stlog.SIDEREAL_ASPS * t
    lines = ["t_s,cmd_arcsec,enc_arcsec,err_arcsec,n,temp_c"] + [f"{a:.0f},{c:.2f},{c + e:.2f},{e:.2f},1000,24.0" for a, c, e in zip(t, cmd, err)]
    lines.append(f"PASS  azimuth tracking {minutes} min: encoder minus command 12.0\" RMS, 40.0\" p-p, 0 CRC errors")
    (d / name).write_text(console(lines, "D4  sidereal tracking (CSV, 10-240 min)"))
    TRUTH["pe_half_pp"] = float(np.ptp(pe) / 2)
    TRUTH["pe_rms"] = float(np.std(pe))


def lost(d: Path):
    lines = ["pass,n,dir,cmd_arcsec,enc_arcsec,err_arcsec"]
    for ps, lm in ((0, 14.0), (1, 3.0)):
        cmd = 0.0
        wind = 0.0
        for n in range(30):
            dr = -1 if (n // 5) % 2 else 1
            cmd += dr * 60
            # wind-up: the output lags by lm/2 in the direction of travel after the first move of a run
            target = -dr * lm / 2
            wind = target if n % 5 >= 1 else (wind + target) / 2
            e = cmd + wind + RNG.normal(0, 0.2)
            lines.append(f"{ps},{n},{dr},{cmd:.2f},{e:.2f},{e - cmd:.2f}")
    lines.append("PASS  azimuth lost motion with 60\" steps: raw 14.0\" (limit 20\"), with the encoder loop 3.0\" (limit 10\")")
    (d / "P0-A_q_az.txt").write_text(console(lines, "D5  lost motion at reversals (T1)"))
    TRUTH["lm_raw"], TRUTH["lm_loop"] = 14.0, 3.0


def slew(d: Path, temp: float, ma: int, sg_base: float, name: str):
    lines = ["t_s,set_dps,rate_dps,cmd_deg,enc_deg,err_arcsec,sg,i_ma,vmot_v,temp_c,diag"]
    t = 0.0
    for s in (2, 4, 6, 8):
        for rep in range(2):
            sign = -1 if rep else 1
            dur = 60 / s + 2 * s / 4
            for k in range(int(dur * 10)):
                tt = k / 10
                ramp = min(1, tt / (s / 4), (dur - tt) / (s / 4))
                rate = sign * s * max(0, ramp)
                sg = sg_base - 12 * s + RNG.normal(0, 3) if abs(rate) > 0.9 * s else 300
                lines.append(f"{t:.1f},{s},{rate:.3f},0,0,{RNG.normal(0, 5):.1f},{max(0, sg):.0f},{ma},16.02,{temp + 0.05 * t:.1f},0")
                t += 0.1
    for s in (2, 4, 6, 8):
        lines.append(f"summary,{s},{sg_base - 12 * s - 6:.0f},{sg_base - 12 * s:.0f},12.0,0")
    lines.append(f"PASS  azimuth slews 2-8 deg/s at {ma} mA: worst encoder-steps difference 15.0\" (limit 180\" = 0.05 deg), DIAG high 0 times")
    (d / name).write_text(console(lines, "D5  slew log: current + StallGuard (T6)"))


def head_files(d: Path):
    cal = {"v": 1, "id": 5, "ok": True, "result": {"routine": "encoder", "state": "done", "axis": 0, "progress": 1,
           "result": {"axis": 0, "samples": 7200, "travel_d": 360.0, "raw_pp_as": 380.0, "raw_rms_as": 110.0, "harmonic_rms_as": 108.0,
                      "after_rms_as": float(np.hypot(TRUTH["pe_rms"], 4.0)), "full_turn": True}}}
    (d / "P0-A_cal_az.json").write_text(json.dumps(cal))
    P = stlog.WG_PERIOD_S
    ph = np.arange(128) / 128 * P
    learned = 15 * np.sin(2 * np.pi * 2 * ph / P) + 6 * np.sin(2 * np.pi * ph / P + 1.0) + 3 * np.sin(2 * np.pi * 3 * ph / P + 0.4)
    pec = {"v": 1, "id": 9, "ok": True, "result": {"axis": 0, "n": 128, "table_as": (-learned).round(2).tolist(), "raw_as": (learned + RNG.normal(0, 0.5, 128)).round(2).tolist()}}
    (d / "P0-A_pec_az.json").write_text(json.dumps(pec))
    # head recording with PEC playing: 30 min at 5 Hz, 1.2" RMS left
    t = np.arange(0, 1800, 0.2)
    left_true = 1.0 * np.sin(2 * np.pi * t / 430.8) + 0.5 * np.sin(2 * np.pi * t / 287.2 + 1)
    left = left_true + RNG.normal(0, 5.4, t.size)          # one encoder sample per state event
    pos = 100 + stlog.SIDEREAL_ASPS * t / 3600
    rows = ["t_s,t,mode,az_pos_d,az_enc_d,az_rate_dps,az_i_ma,az_load,az_temp_c,az_flags,alt_temp_c,vmot,batt_v"]
    for a, p_, l in zip(t, pos, left):
        rows.append(f"{a:.1f},,tracking,{p_:.7f},{p_ + l / 3600:.7f},0.004178,320,250,{24 + a / 300:.2f},0,-273.0,10.02,")
    (d / "P0-A_head_pec_az.csv").write_text("\n".join(rows) + "\n")
    TRUTH["pec_left"] = float(np.std(left_true))
    (d / "P0-A_power.csv").write_text("mode,volts,amps,note\nidle,7.40,0.140,bring-up menu\nhold,7.40,0.185,0.25 A\ntrack,7.40,0.200,0.32 A\nslew,7.40,0.62,8 deg/s\n")


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    noise(out)
    sweep(out)
    track(out)
    lost(out)
    slew(out, 22.0, 830, 260, "P0-A_t_az_warm.txt")
    slew(out, -19.0, 1260, 200, "P0-A_t_az_cold.txt")
    head_files(out)
    (out / "truth.json").write_text(json.dumps(TRUTH, indent=2))
    return TRUTH


if __name__ == "__main__":
    print(main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/st_measure_test")))
