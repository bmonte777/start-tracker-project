"""Star Tracker Project - Phase 4 electronics calculations.

Every part value on the three boards that is calculated (not copied from a datasheet application circuit)
comes from this file. Each result is recorded as: formula -> numbers -> result, with its assumptions.

Run it by hand:  GitHub > Actions > "Phase 4 electronics" > Run workflow  (it never runs on its own).
It reruns phase2_calcs.py at 12 V and at 16 V (D33) with the Phase 3 geometry (D34) and writes
  docs/calc/phase4_results.json   all numbers
  docs/calc/phase4_calcs.md       the same as readable tables (pasted into docs/04-electronics.md)
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = {}          # numbers
ROWS = []       # (section, item, formula, numbers, result, note)


def row(section, item, formula, numbers, result, note=""):
    ROWS.append((section, item, formula, numbers, result, note))


def e96(x):
    """Nearest E96 value."""
    dec = 10 ** math.floor(math.log10(x))
    best = min((round(10 ** (i / 96), 2) for i in range(97)), key=lambda v: abs(v * dec - x))
    return round(best * dec, 6)


def par(a, b):
    return a * b / (a + b)


# ------------------------------------------------------------------------------------------------
# 1. D33 rerun: phase2_calcs.py at 12 V and 16 V, Phase 3 geometry (roll axis at X 135.5, D34)
# ------------------------------------------------------------------------------------------------
def run_phase2(vbus, ypay):
    out = os.path.join(HERE, f"_p2_{vbus:g}_{ypay:g}.json")
    env = dict(os.environ, ST_VBUS=str(vbus), ST_YPAY=str(ypay), ST_OUT=out)
    subprocess.run([sys.executable, os.path.join(HERE, "phase2_calcs.py")], env=env, check=True)
    with open(out) as f:
        d = json.load(f)
    os.remove(out)
    return d


P12_OLD = run_phase2(12.0, 0.1125)     # revision C of the Phase 2 spec, for reference
P12 = run_phase2(12.0, 0.1355)         # 12 V with the Phase 3 geometry
P16 = run_phase2(16.0, 0.1355)         # the design: 16 V (D33), Phase 3 geometry (D34)

CASES = [("ref_any_pose", "Reference rig, any pose, 20 C"), ("ref_any_pose_m20", "Reference rig, any pose, -20 C"),
         ("kg7_altaz", "7 kg, alt-az, 20 C"), ("kg7_altaz_m20", "7 kg, alt-az, -20 C"),
         ("kg7_eq_extreme", "7 kg, EQ extreme, 20 C"), ("kg7_eq_extreme_m20", "7 kg, EQ extreme, -20 C")]
R["d33"] = dict(
    az_design_torque=P16["loads"]["az"]["design_total"], az_static_7kg=P16["loads"]["az"]["static_7kg_worst"],
    az_sf_avg=P16["loads"]["az"]["sf_vs_avg"],
    margins=[dict(case=lab, axis=P16["slew_margins"][k]["governing_axis"], need=P16["slew_margins"][k]["need"],
                  m8_12V_revC=P12_OLD["slew_margins"][k]["m400"], m8_12V=P12["slew_margins"][k]["m400"],
                  m6_12V=P12["slew_margins"][k]["m300"], m8_16V=P16["slew_margins"][k]["m400"],
                  m6_16V=P16["slew_margins"][k]["m300"]) for k, lab in CASES],
    curve={name: [dict(rpm=a["rpm"], dps=a["rpm"] / 50.0, usable_12V=a["usable"], usable_16V=b["usable"],
                       pullout_16V=b["pullout"], bemf=b["bemf"])
                  for a, b in zip(P12["speed_torque"][name], P16["speed_torque"][name])]
           for name in P16["speed_torque"]},
    currents=P16["current_settings"], power_modes=P16["power_modes"], power_modes_12V=P12_OLD["power_modes"],
    thermal=P16["thermal"], peak_slew_power_w=P16["peak_slew_power_w"], boost_current_peak=P16["boost_current_peak"],
    pack_current_peak=P16["pack_current_peak"], motor_need=P16["motor_need"])

# 10 deg/s headroom at 16 V (500 rpm)
u48 = {r["rpm"]: r["usable"] for r in P16["speed_torque"]["17HS19-2004S1"]}
u38 = {r["rpm"]: r["usable"] for r in P16["speed_torque"]["17HE15-1504S"]}
need = P16["slew_margins"]
R["d33"]["headroom_10dps"] = dict(
    az_eq_extreme_m20=round(u48[500] / need["kg7_eq_extreme_m20"]["need"], 2),
    alt_7kg_m20=round(u38[500] / need["kg7_altaz_m20"]["need_by_axis"]["alt"], 2),
    az_eq_extreme_20=round(u48[500] / need["kg7_eq_extreme"]["need"], 2))
m = {d["case"]: d for d in R["d33"]["margins"]}
worst_cold = m["7 kg, EQ extreme, -20 C"]
row("D33 rerun", "Azimuth worst static torque, 7 kg, EQ at latitude 15, rolled out",
    "g x [m(y_pay + d_roll) + m_stage y_pay + m_tower y_t] x sin 75",
    "9.81 x [7 x (0.1355 + 0.130) + 1.38 x 0.1355 + 1.5 x 0.005] x 0.966",
    f"{R['d33']['az_static_7kg']:.2f} N.m (design {R['d33']['az_design_torque']:.2f} N.m with wind and acceleration)",
    "Phase 3 geometry (D34); the Phase 2 spec had 17.63 / 18.37 N.m")
row("D33 rerun", "Back-EMF at 8 deg/s (400 rpm)", "Kt x omega", "0.198 x 41.9 rad/s (38 mm); 0.209 x 41.9 (48 mm)",
    f"{P16['bemf_400rpm']['alt']:.1f} V and {P16['bemf_400rpm']['az']:.1f} V of the 15.5 V available",
    "at 12 V only 11.5 V was available, so 8 deg/s sat on the voltage limit")
row("D33 rerun", "Cold-slew margin, 7 kg EQ extreme, -20 C, 8 deg/s", "usable torque / torque needed",
    f"{u48[400]:.3f} / {worst_cold['need']:.3f} N.m",
    f"{worst_cold['m8_16V']:.2f} (12 V: {worst_cold['m8_12V']:.2f})",
    "D33 quoted 'about 1.6' with the Phase 2 geometry; D34 added 10 % to the azimuth load")
row("D33 rerun", "Same case at 6 deg/s", "usable / needed", f"{u48[300]:.3f} / {worst_cold['need']:.3f} N.m",
    f"{worst_cold['m6_16V']:.2f}", "no gain over 8 deg/s: at 16 V the motor is current-limited up to 400 rpm")

# ------------------------------------------------------------------------------------------------
# 2. Stepper drivers: TMC2209-LA at 16 V, sense resistors, current settings
# ------------------------------------------------------------------------------------------------
RS = 0.15            # ohm, sense resistor (spec 6.2)
R_INT = 0.020        # ohm, internal resistance in the sense path (TMC2209 datasheet)
VFS = {0: 0.325, 1: 0.180}   # full-scale sense voltage, vsense bit 0 / 1


def i_fs(vsense, rs=RS):
    return VFS[vsense] / (rs + R_INT) / math.sqrt(2)


def cs_for(i_rms):
    """Best (vsense, CS) for a target RMS current: the high-sensitivity range whenever it reaches."""
    vs = 1 if i_rms <= i_fs(1) else 0
    cs = max(0, min(31, round(32 * i_rms / i_fs(vs)) - 1))
    return vs, cs, (cs + 1) / 32 * i_fs(vs)


cur = R["d33"]["currents"]
settings = [("Azimuth, tracking 20 C", cur["az"]["track_20C"]), ("Azimuth, tracking -20 C", cur["az"]["track_m20C"]),
            ("Azimuth, slew 7 kg 20 C", cur["az"]["slew_20C"]), ("Azimuth, slew 7 kg -20 C", cur["az"]["slew_m20C"]),
            ("Azimuth, ceiling", cur["az"]["max_rms"]),
            ("Alt / roll, holding", 0.15),
            ("Alt / roll, tracking 20 C", cur["alt_roll"]["track_20C"]), ("Alt / roll, tracking -20 C", cur["alt_roll"]["track_m20C"]),
            ("Alt / roll, slew 7 kg 20 C", cur["alt_roll"]["slew_20C"]), ("Alt / roll, slew 7 kg -20 C", cur["alt_roll"]["slew_m20C"]),
            ("Alt / roll, ceiling", cur["alt_roll"]["max_rms"])]
R["driver"] = dict(rs=RS, i_fs_vsense0=round(i_fs(0), 3), i_fs_vsense1=round(i_fs(1), 3),
                   p_rs_at_fs=round(i_fs(0) ** 2 * RS, 3), settings=[])
for name, i in settings:
    vs, cs, got = cs_for(i)
    R["driver"]["settings"].append(dict(setting=name, target=i, vsense=vs, CS=cs, actual=round(got, 3)))
row("Stepper drivers", "Full-scale RMS current, vsense = 0", "V_FS / (R_S + 0.020) / sqrt 2", f"0.325 / ({RS} + 0.020) / 1.414",
    f"{i_fs(0):.3f} A", "TMC2209 datasheet; 0.15 ohm kept from the spec")
row("Stepper drivers", "Full-scale RMS current, vsense = 1 (tracking range)", "V_FS / (R_S + 0.020) / sqrt 2",
    f"0.180 / ({RS} + 0.020) / 1.414", f"{i_fs(1):.3f} A", "finer current steps for tracking: 23 mA per CS step")
row("Stepper drivers", "Sense resistor loss at full scale", "I_rms^2 x R_S", f"{i_fs(0):.3f}^2 x {RS}",
    f"{i_fs(0) ** 2 * RS:.2f} W each", "1206, 0.5 W part: 55 % of rating; two per driver")
# StealthChop lower current limit (TMC2209 datasheet: I_lower = t_BLANK x f_PWM x V_M / R_coil)
F_CLK = 12e6
T_BLANK = 16 / F_CLK          # TBL = 0
F_PWM = 2 / 1024 * F_CLK      # pwm_freq = 0
R["driver"]["stealth_floor"] = {}
for vm in (16.0, 10.0):
    for name, rc in (("38 mm (2.3 ohm)", 2.3), ("48 mm (1.4 ohm)", 1.4)):
        R["driver"]["stealth_floor"][f"{name} at {vm:g} V"] = round(T_BLANK * F_PWM * vm / rc / math.sqrt(2), 3)
sf = R["driver"]["stealth_floor"]
row("Stepper drivers", "Lowest current StealthChop can regulate, 38 mm motor", "t_BLANK x f_PWM x V_M / R_coil / sqrt 2",
    f"1.33 us x 23.4 kHz x V_M / 2.3 ohm / 1.414", f"{sf['38 mm (2.3 ohm) at 16 V']:.3f} A RMS at 16 V, {sf['38 mm (2.3 ohm) at 10 V']:.3f} A at 10 V",
    "TBL = 0, pwm_freq = 0. Holding (0.15 A) and tracking (0.18 A) sit at this floor on 16 V: see Q23")
row("Stepper drivers", "Same, 48 mm azimuth motor", "as above", "1.33 us x 23.4 kHz x V_M / 1.4 ohm / 1.414",
    f"{sf['48 mm (1.4 ohm) at 16 V']:.3f} A RMS at 16 V, {sf['48 mm (1.4 ohm) at 10 V']:.3f} A at 10 V",
    f"azimuth tracks at {cur['az']['track_20C']:.2f} A")
# VREF strap: default current before the firmware has configured the driver
VREF = 5.0 * 4.7 / (33 + 4.7)
R["driver"]["vref"] = round(VREF, 3)
R["driver"]["i_default"] = round(VREF / 2.5 * i_fs(0), 2)
row("Stepper drivers", "Current if a driver is enabled before UART set-up", "VREF / 2.5 V x I_FS, VREF = 5 V x 4.7k / (33k + 4.7k)",
    f"{VREF:.2f} / 2.5 x {i_fs(0):.2f}", f"{VREF / 2.5 * i_fs(0):.2f} A RMS", "safe default; firmware then sets I_scale_analog = 0")

# ------------------------------------------------------------------------------------------------
# 3. Motor rail: TPS61288 boost, 16 V from the 6.0-8.6 V system rail (two levels: 16 V slew, 10 V track)
# ------------------------------------------------------------------------------------------------
VREF_B, F_SW, GEA, KCOMP = 0.6, 500e3, 180e-6, 13.5      # TPS61288 datasheet
VIN_MIN, VIN_MAX, ETA = 6.0, 8.6, 0.90
VOUT = 16.0
I_PEAK_LOAD = R["d33"]["boost_current_peak"]             # A at 16 V, three axes slewing
I_OUT = 1.5                                              # A design load (40 % over the calculated peak)
R1 = 365e3
R2_LOW = e96(R1 * VREF_B / (10.0 - VREF_B))              # FET off: 10 V
R2_16 = R1 * VREF_B / (VOUT - VREF_B)
R2_PAR = e96(1 / (1 / R2_16 - 1 / R2_LOW))               # switched in parallel: 16 V
V_HI = VREF_B * (1 + R1 / par(R2_LOW, R2_PAR))
V_LO = VREF_B * (1 + R1 / R2_LOW)
D_MAX = 1 - VIN_MIN * ETA / VOUT
I_IN = VOUT * I_OUT / (VIN_MIN * ETA)
L = 4.7e-6
DI = VIN_MIN * D_MAX / (L * F_SW)
DI_HI = VIN_MAX * (1 - VIN_MAX * ETA / VOUT) / (L * F_SW)
I_LPK = I_IN + DI / 2
C_CER = 3 * 22e-6 * 0.42                                 # 22 uF 25 V 1206 X5R at 16 V bias: about 42 % left
C_POLY, ESR_POLY = 2 * 100e-6, 0.030 / 2                 # two 100 uF 25 V polymer hybrids, 30 mohm each
C_O = C_CER + C_POLY
RO = VOUT / I_OUT
F_RHPZ = RO * (VIN_MIN / VOUT) ** 2 / (2 * math.pi * L)
F_C = 2000.0
RC = 2 * math.pi * VOUT * C_O * F_C / ((VIN_MIN / VOUT) * VREF_B * GEA * KCOMP)
RC_E = e96(RC)
CC = RO * C_O / (2 * RC_E)
CP = ESR_POLY * C_O / RC_E
DV_RIPPLE = I_OUT * D_MAX / (F_SW * C_O) + I_LPK * ESR_POLY * (C_POLY / C_O) * 0   # ESR term carried by the ceramics
P_L = I_IN ** 2 * 0.020
P_FET = I_IN ** 2 * (0.0065 * D_MAX + 0.0085 * (1 - D_MAX))
P_SW = 0.5 * VOUT * I_IN * 20e-9 * F_SW
R["boost"] = dict(v_hi=round(V_HI, 2), v_lo=round(V_LO, 2), r1=R1, r2_low=R2_LOW, r2_par=R2_PAR, d_max=round(D_MAX, 3),
                  i_in=round(I_IN, 2), l=L, ripple=round(DI, 2), ripple_vin_max=round(DI_HI, 2), i_lpk=round(I_LPK, 2),
                  i_sat_min=round(1.3 * I_LPK, 1), c_o_eff=round(C_O * 1e6), f_rhpz=round(F_RHPZ), f_c=F_C, rc=RC_E,
                  cc=CC, cp=CP, ripple_mv=round(DV_RIPPLE * 1e3, 1), loss_w=round(P_L + P_FET + P_SW, 2),
                  eff=round(1 - (P_L + P_FET + P_SW) / (VOUT * I_OUT), 3), i_peak_load=I_PEAK_LOAD)
row("16 V motor rail (TPS61288)", "Design load", "calculated slew peak x 1.4", f"{I_PEAK_LOAD:.2f} A x 1.4", f"{I_OUT:.1f} A at 16 V (24 W)",
    "three axes slewing at the highest settings")
row("16 V motor rail (TPS61288)", "Feedback divider, 16 V", "V_REF x (1 + R1 / (R2a || R2b))",
    f"0.6 x (1 + 365k / ({R2_LOW / 1e3:g}k || {R2_PAR / 1e3:g}k))", f"{V_HI:.2f} V", "VM_SEL high (Q4 on)")
row("16 V motor rail (TPS61288)", "Feedback divider, tracking level", "V_REF x (1 + R1 / R2a)", f"0.6 x (1 + 365k / {R2_LOW / 1e3:g}k)",
    f"{V_LO:.2f} V", "VM_SEL low (default); pending approval, Q23")
row("16 V motor rail (TPS61288)", "Duty cycle at the lowest input", "1 - V_IN x eta / V_OUT", f"1 - 6.0 x 0.90 / 16", f"{D_MAX:.3f}", "eta 0.90 assumed")
row("16 V motor rail (TPS61288)", "Input (inductor average) current", "V_OUT x I_OUT / (V_IN x eta)", f"16 x {I_OUT} / (6.0 x 0.90)", f"{I_IN:.2f} A", "")
row("16 V motor rail (TPS61288)", "Inductor ripple with 4.7 uH", "V_IN x D / (L x f_SW)", f"6.0 x {D_MAX:.3f} / (4.7 uH x 500 kHz)",
    f"{DI:.2f} A ({DI / I_IN * 100:.0f} % of the average; {DI_HI:.2f} A at 8.6 V in)", "2.2 uH would give 81 %")
row("16 V motor rail (TPS61288)", "Inductor peak current", "I_IN + ripple / 2", f"{I_IN:.2f} + {DI / 2:.2f}", f"{I_LPK:.2f} A",
    f"switch limit 15 A typ (12 A min); inductor saturation current at least {1.3 * I_LPK:.1f} A")
row("16 V motor rail (TPS61288)", "Effective output capacitance", "3 x 22 uF x 0.42 + 2 x 100 uF", "27.7 uF ceramic at 16 V bias + 200 uF polymer",
    f"{C_O * 1e6:.0f} uF", "the polymer pair also takes the energy the motors return when they brake")
row("16 V motor rail (TPS61288)", "Right-half-plane zero", "R_O x (V_IN / V_OUT)^2 / (2 pi L)", f"{RO:.2f} x (6 / 16)^2 / (2 pi x 4.7 uH)",
    f"{F_RHPZ / 1e3:.1f} kHz", "crossover must stay below one fifth of this")
row("16 V motor rail (TPS61288)", "Compensation resistor for 2 kHz crossover", "2 pi V_OUT C_O f_C / ((1 - D) V_REF G_EA K_COMP)",
    f"2 pi x 16 x {C_O * 1e6:.0f} uF x 2 kHz / (0.375 x 0.6 x 180 uS x 13.5 A/V)", f"{RC / 1e3:.1f} k -> {RC_E / 1e3:g} k",
    "the motor drivers are slow constant-current loads, so 2 kHz is enough")
row("16 V motor rail (TPS61288)", "Compensation capacitors", "C_C = R_O C_O / (2 R_C);  C_P = R_ESR C_O / R_C",
    f"{RO:.2f} x {C_O * 1e6:.0f} uF / (2 x {RC_E / 1e3:g} k);  15 mohm x {C_O * 1e6:.0f} uF / {RC_E / 1e3:g} k",
    f"{CC * 1e9:.1f} nF -> 15 nF;  {CP * 1e12:.0f} pF -> 39 pF", "")
row("16 V motor rail (TPS61288)", "Losses at the design load", "I^2 DCR + I^2 R_DS + 0.5 V I t f",
    f"{P_L:.2f} + {P_FET:.2f} + {P_SW:.2f} W", f"{P_L + P_FET + P_SW:.2f} W, efficiency {100 * (1 - (P_L + P_FET + P_SW) / (VOUT * I_OUT)):.0f} %",
    "20 mohm inductor, 6.5 / 8.5 mohm switches, 20 ns edges; the power budget keeps 90 %")
# inrush: the boost has no output disconnect, so a P-FET switch (Q2) with a Miller capacitor sits in front of it
C_RAIL = 3 * 22e-6 * 0.7 + C_POLY                 # ceramics at 8 V bias
I_RES = VIN_MAX * math.sqrt(C_RAIL / L)
RG, CGD, V_PLAT = 100e3, 10e-9, 2.5
DVDT = (VIN_MAX - V_PLAT) / RG / CGD
I_INRUSH = C_RAIL * DVDT
R["boost"].update(inrush_unswitched_a=round(I_RES), dvdt_v_per_ms=round(DVDT / 1e3, 1), inrush_a=round(I_INRUSH, 2),
                  t_ramp_ms=round(VIN_MAX / DVDT * 1e3, 1))
row("Inrush and reverse polarity", "Inrush into the motor-rail capacitors without a switch", "V x sqrt(C / L)",
    f"8.6 x sqrt({C_RAIL * 1e6:.0f} uF / 4.7 uH)", f"{I_RES:.0f} A", "the boost's body diode passes the pack straight through; not acceptable")
row("Inrush and reverse polarity", "With the P-FET switch Q2 and a 10 nF gate-drain capacitor", "C x (V_IN - V_plateau) / (R_G x C_GD)",
    f"{C_RAIL * 1e6:.0f} uF x (8.6 - 2.5) / (100 k x 10 nF)", f"{I_INRUSH:.2f} A, rail up in {VIN_MAX / DVDT * 1e3:.1f} ms",
    "MOTOR_PWR_EN; also gives a true off for the motor rail")

# ------------------------------------------------------------------------------------------------
# 4. Charger BQ25792 and USB-C PD port A (TPS25751D)
# ------------------------------------------------------------------------------------------------
E_NOM, CAP_AH = 72.0, 2 * 4.85
P_IN, ETA_CHG = 45.0, 0.92
P_SYS_IDLE = P16["power_modes"][0][1]
I_CHG = 4.0
I_AVAIL_74 = (P_IN * ETA_CHG - P_SYS_IDLE) / 7.4
I_AVAIL_84 = (P_IN * ETA_CHG - P_SYS_IDLE) / 8.4
T_CC = CAP_AH * 0.80 / I_CHG
ILIM_HW = 3.3
V_ILIM = 1.0 + 0.8 * ILIM_HW
R_ILIM_TOP, R_ILIM_BOT = 10e3, e96(10e3 * V_ILIM / (5.0 - V_ILIM))
V_ILIM_GOT = 5.0 * R_ILIM_BOT / (R_ILIM_TOP + R_ILIM_BOT)
TS_PCT = par(30.1e3, 10e3) / (5.23e3 + par(30.1e3, 10e3))
L_CHG, F_CHG = 2.2e-6, 750e3
DI_CHG = 8.4 * (1 - 8.4 / 20.0) / (L_CHG * F_CHG)          # buck from 20 V into a full pack
P_CHG_LOSS = 20.0 * (1 / ETA_CHG - 1)                      # at the 20 W the thermal check uses
R["charger"] = dict(prog_r=8.2e3, cells=2, f_sw=F_CHG, l=L_CHG, v_reg=8.4, i_chg=I_CHG, i_avail_7v4=round(I_AVAIL_74, 2),
                    i_avail_8v4=round(I_AVAIL_84, 2), t_cc_h=round(T_CC, 2), t_full_h=round(T_CC + 1.0, 1),
                    ilim_hw=round((V_ILIM_GOT - 1) / 0.8, 2), r_ilim_bot=R_ILIM_BOT, ts_pct=round(TS_PCT * 100, 1),
                    ripple=round(DI_CHG, 2), c_rate=round(I_CHG / CAP_AH, 2))
row("Charger (BQ25792)", "Cell count and switching frequency", "PROG resistor table", "8.2 k", "2 cells, 750 kHz, 8.4 V, 2 A default",
    "datasheet table 9-1; the PD controller raises the charge current over I2C")
row("Charger (BQ25792)", "Charge current the 45 W input can supply", "(P_IN x eta - P_system) / V_BAT",
    f"(45 x 0.92 - {P_SYS_IDLE}) / 7.4 V, / 8.4 V", f"{I_AVAIL_74:.1f} A at 7.4 V, {I_AVAIL_84:.1f} A at 8.4 V",
    f"so the 4 A setting ({I_CHG / CAP_AH:.2f} C, 2 A per cell) holds over the whole charge")
row("Charger (BQ25792)", "Charge time", "0.8 x capacity / I_CHG + about 1 h at constant voltage", f"0.8 x {CAP_AH:.1f} Ah / 4 A + 1 h",
    f"about {T_CC + 1:.0f} h", "blade connector 6 A: 4 A is 67 % of its rating")
row("Charger (BQ25792)", "Hardware input current limit", "V(ILIM_HIZ) = 1 V + 0.8 ohm x I;  divider from REGN (5 V)",
    f"5 x {R_ILIM_BOT / 1e3:g} k / (10 k + {R_ILIM_BOT / 1e3:g} k) = {V_ILIM_GOT:.2f} V", f"{(V_ILIM_GOT - 1) / 0.8:.2f} A",
    "backstop above the 3 A a USB-C cable carries; the PD contract sets the working limit")
row("Charger (BQ25792)", "Inductor ripple, 20 V input, full pack", "V_BAT (1 - V_BAT / V_IN) / (L f)", "8.4 x (1 - 8.4 / 20) / (2.2 uH x 750 kHz)",
    f"{DI_CHG:.2f} A", "2.2 uH as in the datasheet's 750 kHz example; saturation at least 7 A")
row("Charger (BQ25792)", "TS pin with a fixed network", "(RT2 || 10 k) / (RT1 + RT2 || 10 k)", "(30.1 k || 10 k) / (5.23 k + 7.51 k)",
    f"{TS_PCT * 100:.1f} % of REGN", "inside the normal window; the pack's own gauge stops charging outside 0-45 C")

# ------------------------------------------------------------------------------------------------
# 5. Port B: 27 W camera port (TPS25752A + TPS55288) and the 5 V rail
# ------------------------------------------------------------------------------------------------
P_B, ETA_B = 27.0, 0.93
I_IN_B = P_B / (ETA_B * VIN_MIN)
L_B, F_B = 4.7e-6, 400e3
D_B = 1 - VIN_MIN / 9.0
DI_B = VIN_MIN * D_B / (L_B * F_B)
R_FSW = 20000.0 / 400.0
R_ILIM_B = e96(330.0 / 7.5 * 1e3)
I_AVG_LIM = 330.0 / (R_ILIM_B / 1e3)
RSNS_B = 0.010
R["port_b"] = dict(i_in=round(I_IN_B, 2), ripple=round(DI_B, 2), i_lpk=round(I_IN_B + DI_B / 2, 2), r_fsw_k=R_FSW,
                   r_ilim=R_ILIM_B, i_avg_lim=round(I_AVG_LIM, 2), i_out_lim_default=round(0.050 / RSNS_B, 1),
                   i_out_lim_set=round(0.033 / RSNS_B, 1), pdos=["5 V / 3 A", "9 V / 3 A"])
row("Camera port B (TPS25752A + TPS55288)", "Input current at 9 V / 3 A, pack nearly empty", "P / (eta x V_IN)", "27 / (0.93 x 6.0)",
    f"{I_IN_B:.2f} A", "boost mode: this is also the inductor average current")
row("Camera port B (TPS25752A + TPS55288)", "Inductor ripple and peak, 4.7 uH at 400 kHz", "V_IN (1 - V_IN / V_OUT) / (L f)",
    "6.0 x (1 - 6 / 9) / (4.7 uH x 400 kHz)", f"{DI_B:.2f} A ripple, {I_IN_B + DI_B / 2:.2f} A peak", "R_FSW = 20000 / 400 kHz = 49.9 k")
row("Camera port B (TPS25752A + TPS55288)", "Average inductor current limit", "330 / R_ILIM (k)", f"330 / {R_ILIM_B / 1e3:g} k", f"{I_AVG_LIM:.2f} A",
    "1.5 x the working current")
row("Camera port B (TPS25752A + TPS55288)", "Output current limit", "V_SNS / R_SNS", "33 mV / 10 mohm (register); 50 mV default",
    "3.3 A set by the PD controller; 5.0 A at power-up", "10 mohm, 1 %, 0.5 W: 0.09 W at 3 A")
# 5 V rail for PP5V of both PD controllers (TPS62933, 3 A) - pending approval (Q22)
V5_RT, V5_RB = 52.3e3, 10e3
V5 = 0.8 * (1 + V5_RT / V5_RB)
L5 = (VIN_MAX - V5) * V5 / (VIN_MAX * 500e3 * 0.9)
R["rail_5v"] = dict(v=round(V5, 3), l_calc_uh=round(L5 * 1e6, 2), l_uh=4.7, i_max=3.0)
row("5 V rail (TPS62933, pending Q24)", "Output voltage", "0.8 V x (1 + R_T / R_B)", "0.8 x (1 + 52.3 k / 10 k)", f"{V5:.2f} V",
    "feeds PP5V on both PD controllers: 5 V / 3 A for port B and the cable supply (VCONN)")
row("5 V rail (TPS62933, pending Q24)", "Inductor", "(V_IN - V_O) V_O / (V_IN f 0.3 I)", "(8.6 - 5) x 5 / (8.6 x 500 kHz x 0.9 A)",
    f"{L5 * 1e6:.1f} uH -> 4.7 uH", "30 % ripple at 3 A")

# ------------------------------------------------------------------------------------------------
# 6. 3.3 V rail (TPS62932, 2 A)
# ------------------------------------------------------------------------------------------------
LOADS_33 = [("ESP32-S3 (Wi-Fi on)", 136, 355), ("RP2354A", 40, 50), ("3 x MT6835 encoder", 66, 84), ("MAX-M10S GNSS", 15, 25),
            ("OLED 1.3 in (dimmed / full)", 15, 40), ("IMU, magnetometer, clock", 2, 6), ("3 x TMC2209 logic", 3, 3),
            ("2 x PD controller", 10, 10), ("LED, optocouplers, pull-ups", 10, 45)]
I33_TYP = sum(a for _, a, _ in LOADS_33)
I33_PK = sum(b for _, _, b in LOADS_33)
V33 = 0.8 * (1 + 31.6e3 / 10e3)
L33 = (VIN_MAX - V33) * V33 / (VIN_MAX * 500e3 * 0.6)
P33_IN = V33 * I33_TYP / 1e3 / 0.90
R["rail_3v3"] = dict(v=round(V33, 3), i_typ_ma=I33_TYP, i_peak_ma=I33_PK, l_calc_uh=round(L33 * 1e6, 2), l_uh=6.8, loads=LOADS_33,
                     p_in_typ=round(P33_IN, 2))
row("3.3 V rail (TPS62932)", "Load", "sum of the consumers (typical; peak)", "; ".join(f"{n} {a}/{b}" for n, a, b in LOADS_33) + " mA",
    f"{I33_TYP} mA typical, {I33_PK} mA peak", f"{I33_PK / 2000 * 100:.0f} % of the 2 A rating at the peak")
row("3.3 V rail (TPS62932)", "Output voltage", "0.8 V x (1 + R_T / R_B)", "0.8 x (1 + 31.6 k / 10 k)", f"{V33:.2f} V", "1 % resistors")
row("3.3 V rail (TPS62932)", "Inductor", "(V_IN - V_O) V_O / (V_IN f 0.3 I_max)", "(8.6 - 3.33) x 3.33 / (8.6 x 500 kHz x 0.6 A)",
    f"{L33 * 1e6:.1f} uH -> 6.8 uH", "500 kHz (RT pin open)")

# ------------------------------------------------------------------------------------------------
# 7. Monitors and thermistors
# ------------------------------------------------------------------------------------------------
def ntc(t_c, r25=10e3, beta=3950.0):
    return r25 * math.exp(beta * (1 / (t_c + 273.15) - 1 / 298.15))


def v_ntc(t_c, r_pull=10e3):
    r = ntc(t_c)
    return 3.3 * r / (r + r_pull)


R["ntc"] = {str(t): dict(r=round(ntc(t)), v=round(v_ntc(t), 3)) for t in (-20, 0, 25, 60, 80, 95)}
LSB = 3.3 / 4096
R["ntc"]["lsb_per_k_at_80"] = round((v_ntc(79.5) - v_ntc(80.5)) / LSB, 1)
row("Monitors", "Motor thermistor at 80 C (10 k, B 3950, 10 k pull-up)", "R = R25 exp(B (1/T - 1/298)); V = 3.3 R / (R + 10 k)",
    f"R = {ntc(80):.0f} ohm", f"{v_ntc(80):.3f} V (95 C: {v_ntc(95):.3f} V; -20 C: {v_ntc(-20):.2f} V)",
    f"{R['ntc']['lsb_per_k_at_80']:.0f} ADC counts per kelvin at 80 C")
VM_DIV = 15e3 / (100e3 + 15e3)
R["vm_mon"] = dict(ratio=round(VM_DIV, 4), v_at_16=round(16 * VM_DIV, 3), v_at_19=round(19 * VM_DIV, 3), v_at_10=round(10 * VM_DIV, 3))
row("Monitors", "Motor rail monitor", "V_M x 15 k / (100 k + 15 k)", "16 V; 19 V (boost over-voltage limit)",
    f"{16 * VM_DIV:.2f} V; {19 * VM_DIV:.2f} V", "RP2354A ADC, 3.3 V full scale. Under-voltage stop: 14.0 V on the 16 V level, 8.8 V on the 10 V level")
VSYS_DIV = 33e3 / (100e3 + 33e3)
R["vsys_mon"] = dict(ratio=round(VSYS_DIV, 4), v_at_8v6=round(8.6 * VSYS_DIV, 3))
row("Monitors", "System rail monitor", "V_SYS x 33 k / (100 k + 33 k)", "8.6 V", f"{8.6 * VSYS_DIV:.2f} V", "ESP32-S3 ADC1 (11 dB range reads to 3.1 V)")

# ------------------------------------------------------------------------------------------------
# 8. Pack current, power budget and thermal check at 16 V
# ------------------------------------------------------------------------------------------------
P_SLEW = R["d33"]["peak_slew_power_w"]
P_DRV16 = 0.10 * 16 / 12
P_SLEW_TYP = (2 * cur["az"]["slew_20C"] ** 2 * 1.4 + 2 * 2 * cur["alt_roll"]["slew_20C"] ** 2 * 2.3 + 3 * P_DRV16 + 2.0) / 0.90 + 1.0
P_CAM27 = 27.0 / ETA_B
P_TRACK = [p for n, p, _ in P16["power_modes"] if n.startswith("Alt-az tracking, 20")][0]
I_BLADE = 6.0
pack = [("Slew peak (cold, highest settings), 6.0 V", P_SLEW, 6.0), ("Tracking + camera at 27 W, 6.0 V", P_TRACK + P_CAM27, 6.0),
        ("Typical 20 C slew + camera at 27 W, 6.0 V", P_SLEW_TYP + P_CAM27, 6.0),
        ("Slew peak + camera at 27 W, 7.2 V", P_SLEW + P_CAM27, 7.2), ("Slew peak + camera at 27 W, 6.0 V", P_SLEW + P_CAM27, 6.0)]
R["pack_current"] = {k: round(p / v, 2) for k, p, v in pack}
R["pack_current"]["p_slew_typ_w"] = round(P_SLEW_TYP, 1)
R["pack_current"]["budget_w_at_6v"] = I_BLADE * 6.0
for k, p, v in pack:
    row("Pack current", k, "P / V_pack", f"{p:.1f} W / {v} V", f"{p / v:.2f} A", "over the 6 A blade rating" if p / v > I_BLADE else "")
row("Pack current", "Rule for the firmware (power arbitration)", "P_motion + P_camera <= 6 A x V_pack", f"6 A x 6.0 V = 36 W; 6 A x 7.2 V = 43 W",
    "if a cold full-current slew and a 27 W camera load coincide, the firmware lowers the slew current first, then re-advertises port B at 15 W",
    "only that one combination passes 6 A; the pack's own protection sits above it at 10 A")
# thermal (same housing model as Phase 2: 0.09 m2, 8 W/m2K)
th = R["d33"]["thermal"]
P_MOTORS_TRACK = sum(P16["motor_loss_tracking"].values())
P_ELEC = 0.90 / 0.90
P_PD_OUT = 5.0 / 0.92 - 5.0                                 # camera drawing 5 W (Phase 2 case)
P_CHG = 20.0 * (1 / ETA_CHG - 1)
P_BOOST = P_MOTORS_TRACK * (1 / 0.90 - 1)
P_INT = P_MOTORS_TRACK + P_ELEC + P_PD_OUT + P_CHG + P_BOOST
P_INT_27 = P_MOTORS_TRACK + P_ELEC + (27.0 / ETA_B - 27.0) + 45.0 * (1 / ETA_CHG - 1) + P_BOOST
RTH = th["r_th"]
R["thermal"] = dict(p_motors_track=round(P_MOTORS_TRACK, 2), p_int=round(P_INT, 2), t_int_40=round(40 + P_INT * RTH, 1),
                    p_int_27w_45w=round(P_INT_27, 2), t_int_27w_45w=round(40 + P_INT_27 * RTH, 1),
                    motor_rise_065=th["motor_rise_065A"], motor_rise_106=th["motor_rise_106A"], az_rise_peak=th["az_motor_rise_peak"],
                    az_peak_current=th["az_peak_current"], r_th=RTH)
row("Thermal check", "Heat inside the head: tracking, charging at 20 W, camera drawing 5 W", "motors + logic + PD-out loss + charger loss + boost loss",
    f"{P_MOTORS_TRACK:.2f} + {P_ELEC:.2f} + {P_PD_OUT:.2f} + {P_CHG:.2f} + {P_BOOST:.2f} W", f"{P_INT:.1f} W",
    "the Phase 2 case, with the 16 V driver loss")
row("Thermal check", "Inside air at 40 C ambient", "40 + P x R_th, R_th = 1 / (8 W/m2K x 0.09 m2)", f"40 + {P_INT:.1f} x {RTH}", f"{40 + P_INT * RTH:.1f} C",
    "cells allow 60 C")
row("Thermal check", "Worst steady case: charging at 45 W while the camera draws 27 W", "as above with full-power losses",
    f"{P_MOTORS_TRACK:.2f} + {P_ELEC:.2f} + {27.0 / ETA_B - 27.0:.2f} + {45.0 * (1 / ETA_CHG - 1):.2f} + {P_BOOST:.2f} W",
    f"{P_INT_27:.1f} W, inside air {40 + P_INT_27 * RTH:.1f} C at 40 C ambient",
    "charging stops by itself above 45 C cell temperature, so this case cannot run hot for long")
row("Thermal check", "Motor case above inside air", "copper loss x 12 K/W",
    f"38 mm at 0.65 A: {th['motor_loss_065A']} W; at 1.06 A: {th['motor_loss_106A']} W; azimuth at {th['az_peak_current']} A: {th['az_motor_loss_peak']} W",
    f"+{th['motor_rise_065A']:.0f} K, +{th['motor_rise_106A']:.0f} K, +{th['az_motor_rise_peak']:.0f} K",
    "highest settings limited to 60 s; thermistor on each motor lowers the current above 80 C")
# main IC junction temperatures on the mainboard (4-layer board, thermal pads stitched to the ground plane)
P_CHG_OUT = 4.0 * 8.0 + 2.0                                   # 4 A into the pack at 8 V + the running system
P_CHG_LOSS_FULL = P_CHG_OUT * (1 / 0.93 - 1)
P_CHG_IC = P_CHG_LOSS_FULL - 4.0 ** 2 * 0.020                 # less the inductor's share
ICS = [("TPS61288 at 24 W out", P_FET + P_SW, 45.0), ("BQ25792 charging at 4 A", P_CHG_IC, 30.0),
       ("TPS55288 and its two FETs at 27 W", (27.0 / ETA_B - 27.0) * 0.7, 35.0), ("TMC2209 at 1.35 A", 2 * 1.35 ** 2 * 0.17 + 0.14, 30.0),
       ("TPS62932 at 0.6 A", 0.15, 80.0)]
R["ic_temps"] = []
for name, p, rja in ICS:
    tj40, tj20 = 46.7 + 10 + p * rja, 26.7 + 10 + p * rja
    R["ic_temps"].append(dict(ic=name, p=round(p, 2), rja=rja, tj_40=round(tj40), tj_20=round(tj20)))
    row("Thermal check", f"Junction, {name}", "T_air + 10 K board + P x R_JA", f"46.7 + 10 + {p:.2f} W x {rja:g} K/W",
        f"{tj40:.0f} C at 40 C ambient, {tj20:.0f} C at 20 C", "limit 125 C" if tj40 < 110 else "at the charger's 120 C regulation point: see the next line")
I_CHG_40 = math.sqrt(max(0.0, (120 - 56.7) / 30.0) / (P_CHG_IC / 16.0))      # loss taken as proportional to I^2
R["charger"]["i_chg_at_40C"] = round(min(4.0, I_CHG_40), 1)
R["charger"]["p_ic_w"] = round(P_CHG_IC, 2)
row("Thermal check", "Charge current the BQ25792 holds at 40 C ambient", "I where T_J = 120 C (its thermal regulation, default setting)",
    f"sqrt((120 - 56.7) / 30 K/W / ({P_CHG_IC:.2f} W / 4 A^2))", f"about {min(4.0, I_CHG_40):.1f} A",
    "4 A holds at 20 C; in a hot head the charger trims the current by itself, and the firmware sets 3 A above 35 C inside. To be measured on P1 (T10)")

# runtime table at 16 V
R["runtime"] = [dict(mode=n, p16=p, h16=h, p12=p2, h12=h2) for (n, p, h), (_, p2, h2) in zip(P16["power_modes"], P12_OLD["power_modes"])]

if __name__ == "__main__":
    with open(os.path.join(HERE, "phase4_results.json"), "w") as f:
        json.dump(R, f, indent=1)
    lines = ["# Phase 4 calculations", "",
             "Generated by `docs/calc/phase4_calcs.py`. Every line is formula, numbers, result.", ""]
    sec = None
    for (s, item, formula, numbers, result, note) in ROWS:
        if s != sec:
            lines += ["", f"## {s}", "", "| Item | Formula | Numbers | Result | Note |", "| --- | --- | --- | --- | --- |"]
            sec = s
        lines.append("| " + " | ".join(x.replace("|", "/") for x in (item, formula, numbers, result, note)) + " |")
    with open(os.path.join(HERE, "phase4_calcs.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({k: R[k] for k in ("boost", "charger", "port_b", "rail_5v", "rail_3v3", "pack_current", "thermal", "ic_temps")}, indent=1))
