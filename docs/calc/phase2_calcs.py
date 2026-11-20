"""Star Tracker Project - Phase 2 engineering calculations.

Every number quoted in docs/02-engineering-spec.md comes from this file.
Run it (GitHub: Actions > "Phase 2 calculations" > Run workflow) to reproduce.
Units: SI unless stated. Angles printed in arc-seconds (") where useful.
"""
import json
import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import bom_data  # noqa: E402

G = 9.81
ARCSEC = 180 / math.pi * 3600  # rad -> arcsec
R = {}  # results


def asec(rad):
    return rad * ARCSEC


# ----------------------------------------------------------------------------------------
# 1. Inputs
# ----------------------------------------------------------------------------------------
SIDEREAL = 15.041  # "/s
PIX = 3.76e-6  # A7R V pixel
m_ref, m_max = 3.2, 7.0  # kg payload: reference rig, rated
N_HD, N_BELT = 100, 3
N = N_HD * N_BELT
SLEW_DPS = 8.0
T_ACC = 0.5  # s to reach slew speed

# geometry assumptions (Phase 3 may move these by a few mm)
h_foot = 0.085     # lens axis to underside of the 200-600 foot
r_shelf = 0.045    # roll axis to clamp seat
d_roll = r_shelf + h_foot          # payload CG offset from roll axis (long lens on foot)
e_alt = 0.080      # roll axis sits this far "below" the altitude axis
m_rollstage = 0.70 + 0.28 + 0.12 + 0.16 + 0.12   # reducer + motor + housing + shelf + clamp
m_tower = 1.00 + 0.28 + 0.17 + 0.05              # alt reducer + motor + tower print + board
y_tower = 0.005    # tower CG to azimuth axis (tower straddles the axis)
y_pay = 0.1125     # payload plane to azimuth axis: tower half-width 42.5 + lens radius 56 + 14 clearance
H_pay = 0.150      # payload CG height above azimuth bearing
H_head = 0.080     # upper-head CG height above azimuth bearing
m_head_upper = m_tower + m_rollstage + 0.90      # + az body, battery, electronics above az bearing
arm_alt_crb = 0.085  # alt bearing centre to payload plane
ax_roll_crb = 0.075  # roll bearing centre to payload CG, along the roll axis

# reducers (Harmonic Drive CSF-2UH-LW product pages; Laifual LSS/FHT tables give the same torque ratings)
HD = {
    14: dict(rated=7.8, avg=11, peak=28, mom=54, K1=0.47e4, T1=2.0, K2=0.61e4, T2=6.9, K3=0.71e4,
             backdrive=1.8, start_ncm=2.5, Mc=33.6, Km=3.6e4, m_solid=0.51, m_hollow=0.70, Jwg=3.3e-6),
    17: dict(rated=24, avg=39, peak=54, mom=108, K1=1.0e4, T1=3.9, K2=1.4e4, T2=12, K3=1.6e4,
             backdrive=3.3, start_ncm=3.4, Mc=52.5, Km=6.4e4, m_solid=0.67, m_hollow=1.00, Jwg=7.9e-6),
}
AX = {"az": 17, "alt": 17, "roll": 14}   # D17: azimuth is size 17
ETA_HD, ETA_BELT = 0.70, 0.95
T_NL = {14: {20: 0.04, -20: 0.16}, 17: {20: 0.06, -20: 0.24}}  # no-load running torque at wave generator, N.m (assumed x4 at -20 C)

# motor: StepperOnline 17HE15-1504S
MOT = dict(name="17HE15-1504S", Th=0.42, Ir=1.5, R=2.3, L=4.0e-3, p=50, J=5.4e-6, detent=0.016, m=0.28)
MOT_ALT = dict(name="17HS19-2004S1", Th=0.59, Ir=2.0, R=1.4, L=3.0e-3, p=50, J=8.2e-6, detent=0.022, m=0.39)
VBUS = 12.0
VDROP = 0.5

# ----------------------------------------------------------------------------------------
# 2. Basic kinematics
# ----------------------------------------------------------------------------------------
R["pixel_scale_300"] = 206.265 * 3.76 / 300
R["pixel_scale_600"] = 206.265 * 3.76 / 600
R["microstep_arcsec"] = 1.8 * 3600 / 256 / N
R["motor_rpm_slew"] = SLEW_DPS * N / 360 * 60
R["step_rate_slew"] = R["motor_rpm_slew"] / 60 * 200 * 256
R["motor_rpm_sidereal"] = SIDEREAL / 3600 * N / 360 * 60
R["ustep_rate_sidereal"] = SIDEREAL / R["microstep_arcsec"]
R["wg_period_s"] = 360 * 3600 / N_HD / SIDEREAL        # one wave-generator turn at sidereal
R["motor_period_s"] = 360 * 3600 / N / SIDEREAL
R["hd_main_period_s"] = R["wg_period_s"] / 2
R["encoder_lsb_arcsec"] = 360 * 3600 / 2 ** 21
R["encoder_inl_arcsec"] = 0.07 * 3600

# ----------------------------------------------------------------------------------------
# 3. Static, acceleration and wind torques
# ----------------------------------------------------------------------------------------
def alt_static(mp, fore_aft):
    up = mp * (d_roll - e_alt) - m_rollstage * e_alt      # kg.m, "up" residual
    fa = mp * fore_aft
    return G * math.hypot(up, fa)


def roll_static(mp):
    return G * (mp * d_roll + 0.28 * r_shelf)


def az_offset(mp, rolled):
    """kg.m of everything above the azimuth bearing about the azimuth axis (payload hangs beside the tower)."""
    return mp * (y_pay + (d_roll if rolled else 0.0)) + m_rollstage * y_pay + m_tower * y_tower


def az_static_eq(mp, lat_deg, rolled):
    tau = math.radians(90 - lat_deg)
    return G * az_offset(mp, rolled) * math.sin(tau)


alpha = math.radians(SLEW_DPS) / T_ACC
J = {  # kg.m2 about each axis: (reference rig, 7 kg)
    "alt": (0.070, 0.180),
    "az": (0.115, 0.265),
    "roll": (0.005 + m_ref * d_roll ** 2, 0.010 + m_max * d_roll ** 2),
}


def wind_force(v, area, cd=1.1, rho=1.225):
    return 0.5 * rho * v * v * cd * area


A_ref, A_max = 0.062, 0.100   # m2 side area
arm_ref, arm_max = 0.060, 0.100
wind = {v: (wind_force(v, A_ref) * arm_ref, wind_force(v, A_max) * arm_max) for v in (3, 5, 10)}
R["wind_torque"] = {str(v): [round(x, 3) for x in wind[v]] for v in wind}

loads = {}
loads["alt"] = dict(
    ref_bal=alt_static(m_ref, 0.010), ref_unbal=alt_static(m_ref, 0.060), max=alt_static(m_max, 0.100))
loads["roll"] = dict(ref_bal=0.0, ref_unbal=roll_static(m_ref), max=roll_static(m_max))
loads["az"] = dict(
    ref_bal=az_static_eq(m_ref, 37, False), ref_unbal=az_static_eq(m_ref, 37, True), max=az_static_eq(m_max, 15, True))
R["az_eq_cases"] = dict(ref_roll0_lat37=round(az_static_eq(m_ref, 37, False), 2), ref_rolled_lat37=round(az_static_eq(m_ref, 37, True), 2),
                        kg7_roll0_lat37=round(az_static_eq(m_max, 37, False), 2), kg7_rolled_lat37=round(az_static_eq(m_max, 37, True), 2),
                        kg7_rolled_lat15=round(az_static_eq(m_max, 15, True), 2), altaz_any=0.0)
R["loads"] = {}
for ax, size in AX.items():
    h = HD[size]
    t_acc = J[ax][1] * alpha
    t_wind = wind[10][1]
    design = loads[ax]["max"] + t_acc + t_wind
    R["loads"][ax] = dict(
        size=size, static_ref_balanced=round(loads[ax]["ref_bal"], 2), static_ref_worst=round(loads[ax]["ref_unbal"], 2),
        static_7kg_worst=round(loads[ax]["max"], 2), accel_7kg=round(t_acc, 3), wind10_7kg=round(t_wind, 2),
        design_total=round(design, 2), sf_vs_peak=round(h["peak"] / design, 2), sf_vs_avg=round(h["avg"] / design, 2),
        sf_vs_momentary=round(h["mom"] / design, 2))
# for the record: what the size 14 first planned for azimuth (D2, before D17) would have given
_d = R["loads"]["az"]["design_total"]
R["az_with_size14"] = dict(sf_vs_peak=round(HD[14]["peak"] / _d, 2), sf_vs_avg=round(HD[14]["avg"] / _d, 2), sf_vs_momentary=round(HD[14]["mom"] / _d, 2))
R["alpha_rad_s2"] = alpha

# ----------------------------------------------------------------------------------------
# 4. Output bearing tilting moment and deflection
# ----------------------------------------------------------------------------------------
def crb(M, size):
    h = HD[size]
    return dict(M=round(M, 2), sf=round(h["Mc"] / M, 2), tilt_arcsec=round(asec(M / h["Km"]), 1))


M_roll = lambda mp: mp * G * math.hypot(ax_roll_crb, d_roll)
M_alt = lambda mp, rolled: G * (mp * (arm_alt_crb + (d_roll if rolled else 0)) + m_rollstage * arm_alt_crb)


def M_az(mp, lat, rolled):
    tau = math.radians(90 - lat)
    return G * math.hypot((mp * H_pay + m_head_upper * H_head) * math.sin(tau), az_offset(mp, rolled))


R["crb"] = {
    "roll_ref": crb(M_roll(m_ref), 14), "roll_7kg": crb(M_roll(m_max), 14),
    "alt_ref": crb(M_alt(m_ref, False), 17), "alt_ref_rolled": crb(M_alt(m_ref, True), 17), "alt_7kg_rolled": crb(M_alt(m_max, True), 17),
    "az_ref_altaz": crb(M_az(m_ref, 90, False), AX["az"]), "az_ref_lat37": crb(M_az(m_ref, 37, False), AX["az"]),
    "az_7kg_altaz_rolled": crb(M_az(m_max, 90, True), AX["az"]), "az_7kg_lat15_rolled": crb(M_az(m_max, 15, True), AX["az"]),
}

# ----------------------------------------------------------------------------------------
# 5. Structural deflection: printed PAHT-CF vs aluminium 6061
# ----------------------------------------------------------------------------------------
E_PRINT, E_ALU = 4.2e9, 69e9


def box_I(b, h, t):
    return (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12


I_arm = box_I(0.060, 0.040, 0.005)
L_arm = 0.085
# shelf: 60 x 8 plate with two 6 x 22 ribs
A1, y1, A2, y2 = 60 * 8, 26.0, 2 * 6 * 22, 11.0
yb = (A1 * y1 + A2 * y2) / (A1 + A2)
I_shelf = (60 * 8 ** 3 / 12 + A1 * (y1 - yb) ** 2 + 2 * 6 * 22 ** 3 / 12 + A2 * (y2 - yb) ** 2) * 1e-12
L_shelf = 0.075


def arm_rot(mp, E):
    F = (mp + m_rollstage) * G
    M = mp * G * d_roll
    return F * L_arm ** 2 / (2 * E * I_arm) + M * L_arm / (E * I_arm)


def shelf_rot(mp, E):
    return mp * G * L_shelf ** 2 / (2 * E * I_shelf)


R["structure"] = dict(
    I_arm_mm4=round(I_arm * 1e12), I_shelf_mm4=round(I_shelf * 1e12),
    arm_ref_printed=round(asec(arm_rot(m_ref, E_PRINT)), 1), arm_ref_alu=round(asec(arm_rot(m_ref, E_ALU)), 1),
    arm_7kg_printed=round(asec(arm_rot(m_max, E_PRINT)), 1), arm_7kg_alu=round(asec(arm_rot(m_max, E_ALU)), 1),
    shelf_ref_printed=round(asec(shelf_rot(m_ref, E_PRINT)), 1), shelf_ref_alu=round(asec(shelf_rot(m_ref, E_ALU)), 1),
    shelf_7kg_printed=round(asec(shelf_rot(m_max, E_PRINT)), 1), shelf_7kg_alu=round(asec(shelf_rot(m_max, E_ALU)), 1))

def windup(T, size):
    """Torsion angle from the catalogue's three-slope stiffness curve."""
    h = HD[size]
    if T <= h["T1"]:
        return T / h["K1"]
    if T <= h["T2"]:
        return h["T1"] / h["K1"] + (T - h["T1"]) / h["K2"]
    return h["T1"] / h["K1"] + (h["T2"] - h["T1"]) / h["K2"] + (T - h["T2"]) / h["K3"]


# torsional wind-up in the typical EQ pose (reference rig, roll 0, latitude 37) and in the worst reference pose
R["windup"] = {ax: round(asec(windup(loads[ax]["ref_bal"], AX[ax])), 1) for ax in AX}
R["windup_worst_ref"] = {ax: round(asec(windup(loads[ax]["ref_unbal"], AX[ax])), 1) for ax in AX}
R["windup_az_size14"] = round(asec(windup(loads["az"]["ref_bal"], 14)), 1)
R["wind_deflection_5ms"] = {ax: round(asec(wind[5][0] / HD[AX[ax]]["K1"]), 2) for ax in AX}
R["wind_deflection_3ms"] = {ax: round(asec(wind[3][0] / HD[AX[ax]]["K1"]), 2) for ax in AX}

# static flexure stack, reference rig, EQ at latitude 37, and its change over a 5-minute exposure
dt = 300.0
rot5 = math.radians(SIDEREAL * dt / 3600)   # sky rotation in 5 min, rad
for label, E in (("alu", E_ALU), ("printed", E_PRINT)):
    parts = [R["crb"]["az_ref_lat37"]["tilt_arcsec"], R["crb"]["alt_ref"]["tilt_arcsec"], R["crb"]["roll_ref"]["tilt_arcsec"],
             asec(arm_rot(m_ref, E)), asec(shelf_rot(m_ref, E)), R["windup"]["alt"], R["windup"]["az"]]
    rss = math.sqrt(sum(p * p for p in parts))
    drift = rss * math.sin(rot5)
    R[f"flexure_{label}"] = dict(static_rss=round(rss, 1), static_sum=round(sum(parts), 1), drift_5min=round(drift, 2),
                                 rms_5min=round(drift / math.sqrt(12), 2))
R["rot5_deg"] = math.degrees(rot5)

# natural frequency and settle
R["dynamics"] = {}
for ax, size in AX.items():
    K = HD[size]["K1"]
    out = {}
    for lab, Jv in zip(("ref", "7kg"), J[ax]):
        w = math.sqrt(K / Jv)
        out[lab] = dict(f_hz=round(w / 2 / math.pi, 1), ring_arcsec=round(asec(alpha / w ** 2), 2))
    R["dynamics"][ax] = out
f_sys, zeta = 10.0, 0.05      # tripod-limited system mode, damping ratio (assumed)
w_sys = 2 * math.pi * f_sys
A0 = asec(alpha / w_sys ** 2)
R["settle"] = dict(f_sys=f_sys, zeta=zeta, A0=round(A0, 1), t_to_1arcsec=round(math.log(A0 / 1.0) / (zeta * w_sys), 2),
                   t_to_1arcsec_zeta002=round(math.log(A0 / 1.0) / (0.02 * w_sys), 2))

# ----------------------------------------------------------------------------------------
# 6. Motor torque needed, and stepper speed-torque at 12 V
# ----------------------------------------------------------------------------------------
def motor_torque_needed(ax, t_out, temp):
    size = AX[ax]
    t_wg = t_out / (N_HD * ETA_HD) + T_NL[size][temp]
    j_ref = MOT["J"] + 0.6e-6 + HD[size]["Jwg"] / N_BELT ** 2
    return t_wg / (N_BELT * ETA_BELT) + j_ref * alpha * N


R["motor_need"] = {}
for ax in AX:
    d = R["loads"][ax]["design_total"]
    bal = loads[ax]["ref_bal"]
    R["motor_need"][ax] = dict(
        slew_7kg_20C=round(motor_torque_needed(ax, d, 20), 3), slew_7kg_m20C=round(motor_torque_needed(ax, d, -20), 3),
        track_ref_20C=round(motor_torque_needed(ax, max(bal, 0.3), 20), 3), track_ref_m20C=round(motor_torque_needed(ax, max(bal, 0.3), -20), 3))


def pullout(m, rpm, i_pk):
    """Largest torque the drive can make at this speed: maximise iq under the voltage and current limits."""
    kt = m["Th"] / (math.sqrt(2) * m["Ir"])
    wm = rpm * 2 * math.pi / 60
    we = wm * m["p"]
    Ebemf = kt * wm
    vmax = VBUS - VDROP
    best = 0.0
    for k in range(0, 721):
        th = math.radians(k * 0.25)          # current angle from d-axis, 0..180
        lo, hi = 0.0, i_pk
        for _ in range(40):                  # largest current magnitude that fits the voltage circle
            mid = (lo + hi) / 2
            idv, iqv = mid * math.cos(th), mid * math.sin(th)
            vd = m["R"] * idv - we * m["L"] * iqv
            vq = m["R"] * iqv + we * m["L"] * idv + Ebemf
            if vd * vd + vq * vq <= vmax * vmax:
                lo = mid
            else:
                hi = mid
        best = max(best, kt * lo * math.sin(th))
    return best


R["kt"] = MOT["Th"] / (math.sqrt(2) * MOT["Ir"])
curve = {}
for m in (MOT, MOT_ALT):
    rows = []
    for rpm in (1, 100, 200, 300, 400, 500, 600, 800):
        t_full = pullout(m, rpm, math.sqrt(2) * m["Ir"] * 0.7071)        # rated-current peak (Ipk = Ir)
        rows.append(dict(rpm=rpm, pullout=round(t_full, 3), usable=round(0.7 * t_full, 3), bemf=round(m["Th"] / (math.sqrt(2) * m["Ir"]) * rpm * 2 * math.pi / 60, 2)))
    curve[m["name"]] = rows
R["speed_torque"] = curve
need400 = max(R["motor_need"][ax]["slew_7kg_m20C"] for ax in AX)
u400 = [r for r in curve[MOT["name"]] if r["rpm"] == 400][0]["usable"]
R["motor_margin_400rpm_m20C"] = round(u400 / need400, 2)
need400w = max(R["motor_need"][ax]["slew_7kg_20C"] for ax in AX)
R["motor_margin_400rpm_20C"] = round(u400 / need400w, 2)
# margins by case: reference rig (worst pose, any axis), 7 kg alt-az (azimuth carries no gravity torque), 7 kg EQ extreme
def _need(ax, t_static, mp_idx, temp):
    return motor_torque_needed(ax, t_static + J[ax][mp_idx] * alpha + wind[10][mp_idx], temp)
cases = {
    "ref_any_pose": max(_need(a, loads[a]["ref_unbal"], 0, 20) for a in AX), "ref_any_pose_m20": max(_need(a, loads[a]["ref_unbal"], 0, -20) for a in AX),
    "kg7_altaz": max(_need("az", 0.0, 1, 20), _need("alt", loads["alt"]["max"], 1, 20), _need("roll", loads["roll"]["max"], 1, 20)),
    "kg7_altaz_m20": max(_need("az", 0.0, 1, -20), _need("alt", loads["alt"]["max"], 1, -20), _need("roll", loads["roll"]["max"], 1, -20)),
    "kg7_eq_extreme": _need("az", loads["az"]["max"], 1, 20), "kg7_eq_extreme_m20": _need("az", loads["az"]["max"], 1, -20),
}
usable = {r["rpm"]: r["usable"] for r in curve[MOT["name"]]}
usable_big = {r["rpm"]: r["usable"] for r in curve[MOT_ALT["name"]]}
R["slew_margins"] = {k: dict(need=round(v, 3), m400=round(usable[400] / v, 2), m300=round(usable[300] / v, 2), m200=round(usable[200] / v, 2),
                             m400_48mm=round(usable_big[400] / v, 2)) for k, v in cases.items()}
R["az_eq_cases"]["note"] = "size 17 on azimuth carries every case below its 39 N.m average-torque limit"
_t30 = G * (m_max * (y_pay + d_roll * math.sin(math.radians(30))) + m_rollstage * y_pay + m_tower * y_tower) * math.sin(math.radians(53))
R["az_eq_cases"]["kg7_roll30_lat37"] = round(_t30, 2)


def irms_for(t, margin=2.0):
    return margin * t / R["kt"] / math.sqrt(2)


R["current_settings"] = dict(
    track_20C=round(irms_for(max(R["motor_need"][a]["track_ref_20C"] for a in AX)), 2),
    track_m20C=round(irms_for(max(R["motor_need"][a]["track_ref_m20C"] for a in AX)), 2),
    slew_20C=round(irms_for(need400w), 2), slew_m20C=round(min(irms_for(need400), MOT["Ir"] / math.sqrt(2)), 2),
    max_rms=round(MOT["Ir"] / math.sqrt(2), 2))

# ----------------------------------------------------------------------------------------
# 7. Belt
# ----------------------------------------------------------------------------------------
z1, z2, pitch, Lb = 20, 60, 2.0, 200.0
d1, d2 = z1 * pitch / math.pi, z2 * pitch / math.pi
# L = 2C + pi(D+d)/2 + (D-d)^2/(4C)
a_, b_, c_ = 2.0, -(Lb - math.pi * (d1 + d2) / 2), (d2 - d1) ** 2 / 4
C = (-b_ + math.sqrt(b_ * b_ - 4 * a_ * c_)) / (2 * a_)
wrap = 180 - 2 * math.degrees(math.asin((d2 - d1) / (2 * C)))
tim = z1 * wrap / 360
span = math.sqrt(C ** 2 - ((d2 - d1) / 2) ** 2)
t_design = need400                       # N.m at the motor pulley, worst cold slew
Te = t_design / (d1 / 2000)
T_max_motor = R["kt"] * MOT["Ir"]        # torque at the highest current we allow (Ipk = Ir)
Te_max = T_max_motor / (d1 / 2000)
WORK_6MM = 27.8                          # N, generic 6 mm GT2 working tension (6.25 lb)
Tst = 14.0                               # N static tension per span (above half the design belt pull)
shaft_load = 2 * Tst * math.sin(math.radians(wrap / 2))
mu = 0.0126                              # kg/m for 9 mm belt (assumed 1.4 g/m per mm)
f_span = math.sqrt(Tst / mu) / (2 * span / 1000)
R["belt"] = dict(d1=round(d1, 2), d2=round(d2, 2), centre=round(C, 2), wrap_deg=round(wrap, 1), teeth_in_mesh=round(tim, 1),
                 span_mm=round(span, 1), Te_design=round(Te, 1), Te_at_max_current=round(Te_max, 1),
                 work_6mm=WORK_6MM, work_9mm=round(WORK_6MM * 1.5, 1), sf_6mm=round(WORK_6MM / Te, 2),
                 sf_9mm=round(WORK_6MM * 1.5 / Te, 2), static_tension=Tst, shaft_load=round(shaft_load, 1), span_freq_hz=round(f_span))
ecc = 0.020e-3  # m, pulley eccentricity (TIR 0.04)
amp_wg = ecc / (d2 / 2000)                # rad at wave generator
R["belt"]["pulley_error_out_arcsec"] = round(asec(amp_wg) / N_HD, 2)

# ----------------------------------------------------------------------------------------
# 8. Power-off holding
# ----------------------------------------------------------------------------------------
R["holding"] = {}
for ax, size in AX.items():
    hold = HD[size]["backdrive"] + MOT["detent"] * N
    R["holding"][ax] = dict(hold=round(hold, 1), sf_ref_typical=round(hold / max(loads[ax]["ref_bal"], 0.01), 2),
                            sf_ref_worst=round(hold / max(loads[ax]["ref_unbal"], 0.01), 2),
                            sf_7kg_worst=round(hold / loads[ax]["max"], 2))


# ----------------------------------------------------------------------------------------
# 9. Accuracy budget (RMS over a 5-minute exposure, 300 mm, reference rig, aluminium arms)
# ----------------------------------------------------------------------------------------
PE_RAW_PK = 20.0          # " typical measured peak (ZWO AM3 class quotes +-15"); catalogue limit is 1.5' p-p = +-45"
PEC_RESIDUAL = 0.12
pe_rms_raw = PE_RAW_PK / math.sqrt(2)
pulley_rms_raw = R["belt"]["pulley_error_out_arcsec"] / math.sqrt(2)
ustep_pk = 0.05 * 1.8 * 3600 / N
ustep_rms = ustep_pk / math.sqrt(2)
pa_err = 120.0            # " polar alignment error
pa_drift = pa_err * rot5
refr = lambda alt: 58.3 / math.sin(math.radians(alt)) ** 2 * math.radians(1.0)   # change over 1 deg of altitude
xtal_ppm = 30
R["budget_inputs"] = dict(pe_rms_raw=round(pe_rms_raw, 1), pulley_rms_raw=round(pulley_rms_raw, 2), ustep_pk=round(ustep_pk, 2),
                          ustep_rms=round(ustep_rms, 2), pa_drift=round(pa_drift, 2), refr45=round(refr(45), 2), refr30=round(refr(30), 2),
                          refr20=round(refr(20), 2), xtal_drift=round(xtal_ppm * 1e-6 * SIDEREAL * dt, 3),
                          pe_max_rate=round(2 * math.pi * PE_RAW_PK / R["hd_main_period_s"], 3))
flex = R["flexure_alu"]["rms_5min"]
wind3 = R["wind_deflection_3ms"]
eq = [
    ("Reducer periodic error, RA axis (after PEC)", pe_rms_raw * PEC_RESIDUAL),
    ("Belt and pulley run-out, 2 pulleys (after PEC)", math.sqrt(2) * pulley_rms_raw * PEC_RESIDUAL),
    ("Stepper microstep non-linearity", ustep_rms),
    ("Encoder loop noise / hunting", 0.30),
    ("Differential flexure (aluminium arms)", flex),
    ("Thermal drift of structure", 0.20),
    ("Polar alignment error 2' (uncorrected)", pa_drift / math.sqrt(12)),
    ("Refraction residual at 45 deg altitude (model on)", 0.1 * refr(45) / math.sqrt(12)),
    ("Clock and step timing (GNSS-disciplined)", 0.04),
    ("Wind 3 m/s gusts on RA and Dec", math.hypot(wind3["az"], wind3["alt"]) / 2),
    ("Low-speed friction ripple", 0.30),
]
cosh = math.cos(math.radians(45))
aa = [
    ("Reducer periodic error, azimuth (after PEC, x cos alt)", pe_rms_raw * PEC_RESIDUAL * cosh),
    ("Reducer periodic error, altitude (after PEC)", pe_rms_raw * PEC_RESIDUAL),
    ("Roll axis error at the field corner (no PEC)", pe_rms_raw * (21.6 / 300) * 0.7),
    ("Belt and pulley run-out, az + alt (after PEC)", math.hypot(math.sqrt(2) * pulley_rms_raw * PEC_RESIDUAL * cosh, math.sqrt(2) * pulley_rms_raw * PEC_RESIDUAL)),
    ("Stepper microstep non-linearity, az + alt", math.hypot(ustep_rms * cosh, ustep_rms)),
    ("Altitude reversal lost motion (encoder-corrected)", 0.50),
    ("Encoder loop noise / hunting", 0.30),
    ("Pointing-model rate error (1' model, alt <= 60 deg)", 1.00),
    ("Differential flexure (aluminium arms)", 0.30),
    ("Thermal drift of structure", 0.20),
    ("Refraction residual at 45 deg altitude (model on)", 0.1 * refr(45) / math.sqrt(12)),
    ("Clock and step timing (GNSS-disciplined)", 0.04),
    ("Wind 3 m/s gusts on az and alt", math.hypot(wind3["az"] * cosh, wind3["alt"]) / 2),
]
rss = lambda rows: math.sqrt(sum(v * v for _, v in rows))
R["budget_eq"] = [(n, round(v, 2)) for n, v in eq]
R["budget_altaz"] = [(n, round(v, 2)) for n, v in aa]
R["budget_eq_total"] = round(rss(eq), 2)
R["budget_altaz_total"] = round(rss(aa), 2)
# sensitivity: no PEC, and reducer at the catalogue limit with PEC
eq_nopec = [(n, v) for n, v in eq]
eq_nopec[0] = (eq[0][0], pe_rms_raw)
eq_nopec[1] = (eq[1][0], math.sqrt(2) * pulley_rms_raw)
aa_nopec = [(n, v) for n, v in aa]
aa_nopec[0] = (aa[0][0], pe_rms_raw * cosh)
aa_nopec[1] = (aa[1][0], pe_rms_raw)
R["budget_eq_no_pec"] = round(rss(eq_nopec), 1)
R["budget_altaz_no_pec"] = round(rss(aa_nopec), 1)
eq_lim = [(n, v) for n, v in eq]
eq_lim[0] = (eq[0][0], 45 / math.sqrt(2) * PEC_RESIDUAL)
R["budget_eq_catalogue_limit"] = round(rss(eq_lim), 2)
eq_printed = [(n, v) for n, v in eq]
eq_printed[4] = (eq[4][0], R["flexure_printed"]["rms_5min"])
R["budget_eq_printed_arms"] = round(rss(eq_printed), 2)
# go-to
goto = dict(gear_az=10.0, gear_alt=10.0, flexure_model_residual=30.0, alignment_model=45.0, level_polar=20.0)
R["goto_rms"] = round(math.sqrt(sum(v * v for v in goto.values())), 0)
goto_nomap = dict(goto, gear_az=32.0, gear_alt=32.0)
R["goto_rms_no_gear_map"] = round(math.sqrt(sum(v * v for v in goto_nomap.values())), 0)
# lost motion from a friction-torque reversal of +-0.3 N.m
R["lost_motion"] = {ax: round(asec(2 * 0.3 / HD[AX[ax]]["K1"]), 0) for ax in AX}
R["belt_backlash_out_arcsec"] = round(asec(0.02e-3 / (d1 / 2000)) / N, 1)

# ----------------------------------------------------------------------------------------
# 10. Power, runtime, thermal
# ----------------------------------------------------------------------------------------
def p_motor(i_rms):
    return 2 * i_rms ** 2 * MOT["R"] + 0.10      # copper loss both phases + driver


ETA_BOOST, ETA_33, ETA_PD = 0.90, 0.90, 0.92
P_ELEC = 0.90 / ETA_33            # ESP32 0.45 + RP2354 0.10 + encoders 0.20 + GNSS/IMU/RTC 0.05 + OLED dimmed 0.05 + gauges 0.05
P_CAM = 5.0 / ETA_PD
modes = {
    "Idle, Wi-Fi on, motors off": P_ELEC + 0.2,
    "EQ tracking, 20 C (1 axis moving, 2 holding at 0.15 A)": (p_motor(0.30) + 2 * p_motor(0.15)) / ETA_BOOST + P_ELEC,
    "Alt-az tracking, 20 C (3 axes at 0.30 A)": 3 * p_motor(0.30) / ETA_BOOST + P_ELEC,
    "Alt-az tracking, -20 C (3 axes at 0.65 A)": 3 * p_motor(0.65) / ETA_BOOST + P_ELEC,
    "Alt-az tracking + camera power, 20 C": 3 * p_motor(0.30) / ETA_BOOST + P_ELEC + P_CAM,
    "Time-lapse / panorama, 20 C (10 % slewing)": 0.9 * (3 * p_motor(0.30) / ETA_BOOST) + 0.1 * (3 * p_motor(0.90) + 2.0) / ETA_BOOST + P_ELEC,
    "Slewing, 3 axes, peak (1.06 A)": (3 * p_motor(1.06) + 2.0) / ETA_BOOST + P_ELEC,
}
E_NOM = 4 * 5.0 * 3.6
E_20 = 4 * 4.85 * 3.6 * 0.90
E_M20 = E_20 * 0.80
R["energy"] = dict(nominal_wh=E_NOM, usable_20C=round(E_20, 1), usable_m20C=round(E_M20, 1))
R["power_modes"] = []
for name, p in modes.items():
    e = E_M20 if "-20" in name else E_20
    R["power_modes"].append((name, round(p, 1), round(e / p, 1)))
# thermal
A_SURF, H_CONV = 0.09, 8.0
r_th = 1 / (H_CONV * A_SURF)
p_int = 3 * p_motor(0.30) + P_ELEC + 0.45 + 1.7     # tracking + PD-out loss + charger loss at 20 W
R["thermal"] = dict(r_th=round(r_th, 2), p_internal=round(p_int, 1), rise=round(p_int * r_th, 1), internal_at_40C=round(40 + p_int * r_th, 1),
                    motor_rise_065A=round((p_motor(0.65) - 0.1) * 12, 0), motor_rise_106A=round((p_motor(1.06) - 0.1) * 12, 0),
                    motor_loss_065A=round(p_motor(0.65) - 0.1, 2), motor_loss_106A=round(p_motor(1.06) - 0.1, 2))
R["boost_current_peak"] = round((3 * p_motor(1.06) + 2.0) / VBUS, 2)

# ----------------------------------------------------------------------------------------
# 11. Mass budget
# ----------------------------------------------------------------------------------------
mass_p1 = {
    "Reducers, hollow units (2 x size 17, 1 x size 14)": 2 * HD[17]["m_hollow"] + HD[14]["m_hollow"],
    "Stepper motors x3": 3 * MOT["m"],
    "Pulleys and belts x3": 3 * 0.045,
    "Battery pack (4 cells + board + shell)": 4 * 0.070 + 0.060,
    "Electronics and harness": 0.165,
    "Printed housings and covers": 0.56,
    "Aluminium parts (wedge, base, arm, shelf, clamp, plates)": 1.08,
    "Fasteners, inserts, seals": 0.15,
}
mass_prod = dict(mass_p1)
mass_prod["Reducers, hollow units (2 x size 17, 1 x size 14)"] = 0.60 + 0.60 + 0.40   # simple hollow units in our own housings
mass_prod["Printed housings and covers"] = 0.95                                         # aluminium housings + moulded covers
mass_prod["Fasteners, inserts, seals"] = 0.12
R["mass_p1"] = {k: round(v, 2) for k, v in mass_p1.items()}
R["mass_p1_total"] = round(sum(mass_p1.values()), 2)
R["mass_prod"] = {k: round(v, 2) for k, v in mass_prod.items()}
R["mass_prod_total"] = round(sum(mass_prod.values()), 2)

# ----------------------------------------------------------------------------------------
# 12. Cost model
# ----------------------------------------------------------------------------------------
tot, groups = bom_data.totals()
LAB = (0.0, 75.0, 33.0)                  # EUR assembly + test labour per head
OVH = (0.12, 0.05, 0.05)                 # freight/import allowance at 1; scrap + overhead at 100 and 1,000
cogs = [round((tot[i] + LAB[i]) * (1 + OVH[i]), 0) for i in range(3)]
R["cost"] = dict(materials=[round(t, 0) for t in tot], labour=LAB, allowance=OVH, cogs=cogs,
                 groups={k: [round(x, 0) for x in v] for k, v in sorted(groups.items())})
red = [sum(q * pr[i] for (pid, _n, q, _a, _b, _c, _d2, pr, _s, _t) in bom_data.PARTS if pid in ("ST-201", "ST-202")) for i in range(3)]
R["cost"]["reducers"] = [round(x, 0) for x in red]
R["cost"]["reducer_share"] = [round(red[i] / tot[i], 2) for i in range(3)]
TOOLING_EUR = round((36000 + 6000 + 7000) * bom_data.USD_TO_EUR, -2)
R["cost"]["tooling_eur"] = TOOLING_EUR
R["cost"]["tooling_per_unit_1000"] = TOOLING_EUR / 1000
landed_1000 = cogs[2] + TOOLING_EUR / 1000
R["cost"]["landed_1000"] = round(landed_1000)
R["cost"]["retail_low_high"] = [round(landed_1000 * 2.5, -1), round(landed_1000 * 3.5, -1)]
# scenario: OEM component sets at USD 95 each
oem = 3 * 95 * bom_data.USD_TO_EUR
cogs_oem = (tot[2] - red[2] + oem + LAB[2]) * (1 + OVH[2]) + TOOLING_EUR / 1000
R["cost"]["landed_1000_oem_sets"] = round(cogs_oem)
R["cost"]["retail_oem_low_high"] = [round(cogs_oem * 2.5, -1), round(cogs_oem * 3.5, -1)]
R["cost"]["retail_multiples"] = {str(k): [round(landed_1000 * k, -1), round(cogs_oem * k, -1)] for k in (2.0, 2.5, 3.5)}

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "phase2_results.json")
    with open(out, "w") as f:
        json.dump(R, f, indent=1)
    bom_data.write_csv(os.path.join(os.path.dirname(__file__), "..", "..", "hardware", "bom", "master-parts-list.csv"))
    print(json.dumps(R, indent=1))
