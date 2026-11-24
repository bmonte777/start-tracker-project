"""Reducer periodic error (R1, test T2) and the PEC result (test T3).

Inputs (pick one):
  * console log of bring-up item k ("t_s,cmd_arcsec,enc_arcsec,err_arcsec[,n,temp_c]"), 45 min for T2;
  * a head recording from the bench logger (state events, columns <axis>_pos_d and <axis>_enc_d) with --axis;
  * the CSV written by laser_spot.py (t_s, arcsec) - the independent laser-on-the-wall method of T2.

What it does:
  1. removes a quadratic trend (the unmapped encoder's slow non-linearity over the 11 deg the output turns in
     45 min, and any rate error) together with harmonics 1-12 of the wave-generator turn (861.6 s at sidereal; the
     motor turn, 287.2 s, is harmonic 3 and both pulleys are inside the same set - spec 4.4);
  2. raw periodic error = the harmonic model: half peak-to-peak against +/-20" (T2);
  3. turn-to-turn repeatability: harmonics fitted to each full 861.6 s turn, compared with their mean (<= 3", T2);
  4. what a perfect PEC trained on this log would leave (RMS of data minus the mean turn), and the worst 5-minute
     RMS window as the spec's tracking metric (spec 4: drift kept, counted as d/sqrt 12);
  5. the full-step ripple (5.74 s at sidereal) from the spectrum, corrected for the 1 s averaging.
With --pec (T3) the log is one taken with PEC playing: the result is the RMS left, against 2".

Usage: python tools/measure/periodic_error.py LOG [--axis az] [--pec] [--out DIR]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import stlog

ORDERS = list(range(1, 13))


def load(path: Path, axis: str = "az") -> tuple[np.ndarray, np.ndarray, str]:
    if path.suffix.lower() == ".csv":
        txt = stlog.read_text(path).splitlines()[0]
        if txt.startswith("t_s,arcsec"):
            a = np.genfromtxt(path, delimiter=",", names=True)
            return a["t_s"], a["arcsec"], "laser"
        h = stlog.read_head_csv(path)
        t = h["t_s"]
        err = (h[f"{axis}_enc_d"] - h[f"{axis}_pos_d"]) * 3600.0
        m = np.isfinite(err) & (h["_text_mode"] == "tracking")
        t, err = t[m], err[m]
        # state events carry one encoder sample each (5.4" noise): average into 20 s bins (sinc loss 1 % at 431 s)
        edges = np.arange(t[0], t[-1] + 20.0, 20.0)
        idx = np.digitize(t, edges)
        tb, eb, nb, sb = [], [], [], []
        for k in np.unique(idx):
            sel = idx == k
            if sel.sum() >= 20:
                tb.append(t[sel].mean()); eb.append(err[sel].mean()); nb.append(sel.sum()); sb.append(err[sel].std())
        load.noise_floor = float(np.median(np.array(sb) / np.sqrt(np.array(nb)))) if sb else 0.0
        return np.array(tb), np.array(eb), "head"
    text = stlog.read_text(path)
    b = stlog.block(text, ["t_s", "cmd_arcsec", "enc_arcsec", "err_arcsec"])
    if b is None:
        raise SystemExit(f"{path}: no tracking block (bring-up item k)")
    c = stlog.as_columns(b)
    return c["t_s"], c["err_arcsec"], "console"


def analyse(path: Path, axis: str = "az", pec: bool = False, out: Path | None = None) -> dict:
    load.noise_floor = 0.0
    t, y, kind = load(path, axis)
    floor = load.noise_floor
    m = stlog.robust_mask(y, 10)
    t, y = t[m] - t[m][0], y[m]
    dur = float(t[-1] - t[0])
    P = stlog.WG_PERIOD_S
    fit = stlog.fit_harmonics(t, y, P, ORDERS, poly_deg=2)
    detr = y - fit["poly"]
    model = fit["harm"]
    pe_half_pp = float(np.ptp(model) / 2)
    pe_rms = float(np.std(model))
    noise_rms = float(np.std(fit["resid"]))
    # turn-to-turn
    ncyc = int(dur // P)
    cycles = []
    for i in range(ncyc):
        mm = (t >= i * P) & (t < (i + 1) * P)
        if mm.sum() < 0.8 * P / max(np.median(np.diff(t)), 1e-9):
            continue
        cf = stlog.fit_harmonics(t[mm], detr[mm], P, ORDERS, poly_deg=1)
        phase = np.linspace(0, P, 862, endpoint=False)
        A = stlog.harmonic_design(phase, P, ORDERS, poly_deg=1)
        cycles.append(A[:, 2:] @ cf["coef"][2:])
    repeat_max = repeat_rms = float("nan")
    if len(cycles) >= 2:
        C = np.array(cycles)
        mean_c = C.mean(axis=0)
        repeat_max = float(np.max(np.abs(C - mean_c)))
        repeat_rms = float(np.sqrt(np.mean((C - mean_c) ** 2)))
    # perfect-PEC prediction: data minus the mean turn (as a function of phase)
    phase_t = np.mod(t, P)
    if cycles:
        mean_curve = np.mean(np.array(cycles), axis=0)
        pec_left = detr - np.interp(phase_t, np.linspace(0, P, 862, endpoint=False), mean_curve, period=P)
        pec_left -= pec_left.mean()
    else:
        pec_left = fit["resid"]
    pec_pred_rms = float(np.std(pec_left))
    w_raw = stlog.window_rms(t, detr)
    w_pec = stlog.window_rms(t, pec_left)
    # full-step ripple from the spectrum
    f, amp = stlog.spectrum(t, fit["resid"] + 0)
    f_fs = 1.0 / stlog.FULLSTEP_PERIOD_S
    band = (f > f_fs * 0.97) & (f < f_fs * 1.03)
    dt = float(np.median(np.diff(t)))
    sinc = np.sinc(f_fs * dt) if kind == "console" else 1.0       # 1 s boxcar average in the firmware (item k)
    fs_amp = float(amp[band].max() / sinc) if band.any() else float("nan")
    d = stlog.out_dir(path, out)
    p = stlog.plt()
    fig, ax = p.subplots(3, 1, figsize=(10, 9))
    ax[0].plot(t / 60, detr, lw=0.5, label="encoder minus command, trend removed")
    ax[0].plot(t / 60, model, lw=1.3, label="harmonics 1-12 of 861.6 s")
    ax[0].set_xlabel("minutes")
    ax[0].set_ylabel("arcsec")
    ax[0].legend(loc="upper right")
    ttl = f"{'PEC on: ' if pec else ''}periodic error {pe_half_pp:.1f}\" half p-p ({pe_rms:.1f}\" RMS) over {dur/60:.0f} min"
    ax[0].set_title(ttl)
    ph = np.linspace(0, P, 862, endpoint=False)
    for i, cyc in enumerate(cycles):
        ax[1].plot(ph, cyc, lw=1, label=f"turn {i + 1}")
    ax[1].set_xlabel("seconds into the wave-generator turn (861.6 s)")
    ax[1].set_ylabel("arcsec")
    if cycles:
        ax[1].legend(loc="upper right")
    ax[1].set_title(f"Turn to turn: max {repeat_max:.1f}\" from the mean (limit 3\")" if len(cycles) >= 2 else "Fewer than two full turns: repeatability needs a 45 min log")
    ax[2].semilogx(1 / np.maximum(f[1:], 1e-9), amp[1:], lw=0.7)
    for per, lab in [(P, "WG 861.6 s"), (P / 2, "431 s"), (stlog.MOTOR_PERIOD_S, "motor 287 s"), (stlog.FULLSTEP_PERIOD_S, "full step 5.7 s")]:
        ax[2].axvline(per, color="r", ls=":", lw=0.8)
        ax[2].text(per, ax[2].get_ylim()[1] * 0.9, lab, rotation=90, fontsize=7, ha="right")
    ax[2].set_xlabel("period, s")
    ax[2].set_ylabel("amplitude, arcsec")
    ax[2].invert_xaxis()
    fig.tight_layout()
    fig.savefig(d / ("pec_result.png" if pec else "periodic_error.png"))
    src = path.name
    res = []
    if not pec:
        res += [
            stlog.Result("T2 / R1", "raw periodic error", pe_half_pp, "arcsec half p-p", "<= 20 (+/-20\")", stlog.verdict(pe_half_pp, stlog.lim("pe_half_pp")), src,
                     f"{kind}, {dur/60:.0f} min, {pe_rms:.1f}\" RMS; largest orders " + ", ".join(f"k{k} {v:.1f}\"" for k, v in sorted(fit['amps'].items(), key=lambda kv: -kv[1])[:3])),
            stlog.Result("T2", "turn-to-turn repeatability", repeat_max, "arcsec max", "<= 3", stlog.verdict(repeat_max, stlog.lim("pe_repeat")) if len(cycles) >= 2 else "not run", src,
                         f"{len(cycles)} full turns; RMS difference {repeat_rms:.2f}\""),
            stlog.Result("T3 (prediction)", "left after a perfect PEC from this log", pec_pred_rms, "arcsec RMS", "<= 2", "info", src,
                         f"worst 5-min window {w_pec.max() if len(w_pec) else float('nan'):.2f}\" RMS"),
            stlog.Result("T2", "worst 5-min window, no PEC", float(w_raw.max()) if len(w_raw) else float("nan"), "arcsec RMS", "spec 4.3: 14.4\" expected without PEC", "info", src, ""),
            stlog.Result("spec 4.1", "full-step ripple (5.74 s)", fs_amp, "arcsec amplitude", "budget +/-1.08\"", "info", src, "from the spectrum, 1 s average corrected"),
        ]
    else:
        left_rms = float(np.sqrt(max(0.0, np.std(detr) ** 2 - floor ** 2)))
        res += [
            stlog.Result("T3", "left with PEC playing", left_rms, "arcsec RMS", "<= 2", stlog.verdict(left_rms, stlog.lim("pec_rms")), src,
                         f"{kind}, {dur/60:.0f} min, periodic part {pe_half_pp:.1f}\" half p-p; encoder noise floor {floor:.2f}\" taken out"),
            stlog.Result("spec 1.2", "worst 5-min window with PEC", float(w_raw.max()) if len(w_raw) else float("nan"), "arcsec RMS", "<= 3 (EQ, whole head)", "info", src,
                         "one axis on the bench; the tracking target is judged on the sky in P1 (T4)"),
        ]
    summary = {"kind": kind, "duration_s": dur, "pe_half_pp": pe_half_pp, "pe_rms": pe_rms, "amps": fit["amps"], "noise_rms": noise_rms,
               "turns": len(cycles), "repeat_max": repeat_max, "repeat_rms": repeat_rms, "pec_pred_rms": pec_pred_rms,
               "window5_raw_max": float(w_raw.max()) if len(w_raw) else None, "window5_pec_max": float(w_pec.max()) if len(w_pec) else None,
               "fullstep_amp": fs_amp, "results": res}
    stlog.write_json(d / ("pec_result.json" if pec else "periodic_error.json"), summary)
    return summary


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("log", type=Path)
    a.add_argument("--axis", default="az", choices=["az", "alt", "roll"])
    a.add_argument("--pec", action="store_true", help="log taken with PEC playing (test T3)")
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    for r in analyse(args.log, args.axis, args.pec, args.out)["results"]:
        print(" | ".join(r.row()))
