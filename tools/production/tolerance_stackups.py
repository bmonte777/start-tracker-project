"""Star Tracker Project - Phase 8, deliverable 3: tolerance stack-ups.

Every stack is a 1-D chain of contributors (nominal, +/- tolerance, sign) taken from
hardware/cad/stcad/params.py and the part code, evaluated for three cases:

  P1    the prototype as ordered in Phase 7 (FDM / MJF / JLCCNC to ISO 2768-m)
  PROD  production processes of D87/D88 with the Phase 3 geometry unchanged
  FIX   production with the changes proposed in docs/08-production.md (pending approval)

Worst case: nominal +/- sum(|t|).  RSS: nominal +/- sqrt(sum t^2), each tolerance taken as +/-3 sigma
of a centred normal distribution; the out-of-spec fraction is from that normal model.

Run:  python tools/production/tolerance_stackups.py      (writes hardware/production/tolerances/)
Test: python tools/production/test_tolerance_stackups.py
"""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "hardware", "cad"))
from stcad import params as P  # noqa: E402  (params imports only math/os; build123d not needed)

OUT = os.path.join(ROOT, "hardware", "production", "tolerances")

# ------------------------------------------------------------------------------------------------
# Process tolerances (+/- mm). Sources are listed in SOURCES and in the report.
# ------------------------------------------------------------------------------------------------
SOURCES = {
    "ISO2768": "ISO 2768 general tolerances, as tabled by Protolabs Network manufacturing standards v2.1 "
               "(f: 3-6 +/-0.05, 6-30 +/-0.1, 30-120 +/-0.15; m: 3-6 +/-0.1, 6-30 +/-0.2, 30-120 +/-0.3)",
    "CNC_CALLOUT": "Protolabs precision machining +/-0.051 mm (toleranced dimension called out on the drawing)",
    "MJF": "JLC3DP capabilities: +/-0.2 mm within 100 mm, +/-0.3 % above",
    "FDM": "JLC3DP MJF-vs-FDM page: FDM +/-0.3 mm to 100 mm, +/-0.4 % above",
    "MOULD": "Protolabs: tool +/-0.076 mm plus resin >= 0.002 mm/mm",
    "PCB": "JLCPCB: finished thickness +/-10 % (1.6 -> 1.44-1.76 mm)",
    "MT6835": "MT6835 datasheet rev 1.3: TSSOP-16 A <= 1.20, A1 0.05-0.15, A2 0.80-1.00; sensing centre "
              "X 2.45-2.55, Y 2.15-2.25; air gap 1.0-3.0 mm; off-axis DISP <= 0.3 mm",
    "VRING": "V-ring type A tables (Hennlich 2017; NAK VA80; SKF 80 VAV): VA-65 fitted width B1 7.0 +/- 1.0, "
             "VA-70...VA-100 9.0 +/- 1.2",
    "ORING": "Static face-seal squeeze: Parker ORD 5700 about 15-25 %, Marco 20-30 %, ISO 3601 13-30 %; "
             "window used here 15-30 %",
    "BELT": "Synchronous belt misalignment <= 1/4 deg angular (Gates/Pfeifer; Fenner: 1/4 deg or 5 mm/m parallel)",
    "OLED": "1.3 in 128 x 64 SH1106 panels: active area 29.42 x 14.70 mm (DisplayModule DM-OLED13-637); "
            "module drawing general tolerance +/-0.3 (Tailor Pixels TOJMD013C)",
    "SPEC": "docs/02-engineering-spec.md rev C (section 3.5 pulley run-out <= 0.03 mm; 4.1 budget)",
    "EST": "estimate: no published figure found; replace with the supplier drawing or a P1 measurement",
}


def iso2768(L, cls="m"):
    tab = {"f": [(3, 0.05), (6, 0.05), (30, 0.1), (120, 0.15), (400, 0.2)],
           "m": [(3, 0.1), (6, 0.1), (30, 0.2), (120, 0.3), (400, 0.5)]}[cls]
    for lim, t in tab:
        if L <= lim:
            return t
    return tab[-1][1]


def mjf(L):
    return 0.2 if L <= 100 else 0.003 * L


def fdm(L):
    return 0.3 if L <= 100 else 0.004 * L


def mould(L):
    return 0.076 + 0.002 * L


# ------------------------------------------------------------------------------------------------
class C:
    """Contributor: sign * nominal, +/- tol, where it comes from."""

    def __init__(self, name, nominal, tol, sign=+1, src="EST", part=""):
        self.name, self.nominal, self.tol, self.sign, self.src, self.part = name, nominal, tol, sign, src, part

    def as_dict(self):
        return dict(name=self.name, part=self.part, nominal=round(self.sign * self.nominal, 4),
                    tol=round(self.tol, 4), source=self.src)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


class Stack:
    def __init__(self, sid, title, unit, lo, hi, limit_src, contributors, note="", radial=False, extra=None):
        self.sid, self.title, self.unit, self.lo, self.hi = sid, title, unit, lo, hi
        self.limit_src, self.c, self.note, self.radial, self.extra = limit_src, contributors, note, radial, extra or {}

    def evaluate(self):
        nom = sum(c.sign * c.nominal for c in self.c)
        wc = sum(abs(c.tol) for c in self.c)
        rss = math.sqrt(sum(c.tol ** 2 for c in self.c))
        if self.radial:      # magnitudes that add: worst case = sum, RSS of a sum of offsets (Rayleigh-ish, kept simple)
            nom, wc_lo, wc_hi, rss_lo, rss_hi = 0.0, 0.0, wc, 0.0, rss
        else:
            wc_lo, wc_hi, rss_lo, rss_hi = nom - wc, nom + wc, nom - rss, nom + rss
        ok_wc = (self.lo is None or wc_lo >= self.lo - 1e-9) and (self.hi is None or wc_hi <= self.hi + 1e-9)
        ok_rss = (self.lo is None or rss_lo >= self.lo - 1e-9) and (self.hi is None or rss_hi <= self.hi + 1e-9)
        sigma = rss / 3 if rss > 0 else 1e-9
        if self.radial:
            mean = 0.0
        else:
            mean = nom
        out = 0.0
        if self.lo is not None and not self.radial:
            out += phi((self.lo - mean) / sigma)
        if self.hi is not None:
            out += 1 - phi((self.hi - mean) / sigma)
        return dict(id=self.sid, title=self.title, unit=self.unit, nominal=round(nom, 4), wc=[round(wc_lo, 4), round(wc_hi, 4)],
                    rss=[round(rss_lo, 4), round(rss_hi, 4)], limits=[self.lo, self.hi], limit_source=self.limit_src,
                    pass_wc=ok_wc, pass_rss=ok_rss, out_of_spec_ppm=round(out * 1e6, 1), radial=self.radial,
                    note=self.note, contributors=[c.as_dict() for c in self.c], extra=self.extra)


# ================================================================================================ stacks
def encoder_gap(size, case):
    """Chip-to-magnet gap along the axis, cartridge frame (origin = reducer output face)."""
    r, c = P.RED[size], P.CART[size]
    t = P.ENC_TUBE
    ft = 6.0                                           # housing rear flange (parts_cart._housing)
    zh = c["z_board"] + P.MAINBOARD["T"]               # board top = carrier plate underside
    post = zh - (r["L_body"] + ft)
    L_t = c["z_magnet"] - 2.6 - (-5.5)                 # tube: flange underside -> magnet seat floor
    seat = 5.5                                         # tube flange seat floor below the output face
    chip, solder, mag, glue = 1.00, 0.05, t["magnet_h"], 0.02
    if case in ("P1", "PROD"):
        p1 = case == "P1"
        cs = [
            C("Reducer: output face to input-side housing face (housed LHT unit)", r["L_body"], 0.10, +1, "EST", "ST-201/202"),
            C("Housing rear flange thickness", ft, fdm(ft) if p1 else iso2768(ft, "m"), +1, "FDM" if p1 else "ISO2768",
              "ST-210/211"),
            C("Carrier post length (flange face to board top)", post, fdm(post) if p1 else mjf(post), +1,
              "FDM" if p1 else "MJF", "ST-212/216"),
            C("Board thickness (board located by its top face)", P.MAINBOARD["T"], 0.16, -1, "PCB", "ST-520"),
            C("MT6835 package height A (A1 + A2)", chip, 0.15, -1, "MT6835", "ST-521"),
            C("Solder joint under the leads", solder, 0.03, -1, "EST", "ST-520"),
            C("Tube flange seat depth below the output face", seat, iso2768(seat, "m"), +1, "ISO2768", "ST-303/312/313"),
            C("Tube length, flange underside to magnet seat floor", L_t, iso2768(L_t, "m"), -1, "ISO2768", "ST-208/215"),
            C("Glue line under the magnet", glue, 0.02, -1, "EST", "ST-209"),
            C("Magnet height 2.5 mm", mag, 0.05, -1, "EST", "ST-209"),
            C("Output tilt / axial deflection under load", 0.0, 0.01, +1, "EST", ""),
        ]
        note = ("Nominal gap with a typical package (A = 1.00) is about 1.0 mm; D48's 0.81-0.82 mm used the 1.20 mm "
                "maximum package. The board thickness, the long tube length at ISO 2768-m and the printed carrier dominate.")
    else:
        gap_target = 1.50
        cs = [
            C("Housing: output-bearing shoulder to the 3 board datum pads (one CNC set-up)", 0.0, 0.03, +1, "CNC_CALLOUT", "ST-210/211 P2"),
            C("Crossed-roller bearing: seat face to output face", 0.0, 0.05, +1, "EST", "bought bearing (D87)"),
            C("Board seated chip-side down on the pads: thickness drops out", 0.0, 0.0, +1, "PCB", "ST-520"),
            C("MT6835 package height A (A1 + A2)", 0.0, 0.15, -1, "MT6835", "ST-521"),
            C("Solder joint under the leads", 0.0, 0.03, -1, "EST", "ST-520"),
            C("Tube flange seat depth (called-out)", 0.0, 0.05, +1, "CNC_CALLOUT", "ST-303/312/313"),
            C("Tube length flange to magnet seat (called-out, turned)", 0.0, 0.03, -1, "CNC_CALLOUT", "ST-208/215"),
            C("Glue line under the magnet", 0.0, 0.02, -1, "EST", "ST-209"),
            C("Magnet height 2.5 mm", 0.0, 0.05, -1, "EST", "ST-209"),
            C("Output tilt / axial deflection under load", 0.0, 0.01, +1, "EST", ""),
            C("Nominal gap set by the datum-pad height", gap_target, 0.0, +1, "", "design"),
        ]
        note = ("Fix (D96, approved 24 Nov): the encoder board sits chip-side down on three pads machined in the CNC "
                "housing, so the board thickness and the carrier drop out; nominal gap raised to 1.5 mm, the middle "
                "of what the datasheet allows; the two lengths that remain long get a called-out tolerance.")
    return Stack(f"S1-{size}", f"Encoder chip-to-magnet gap, size {size} ({'azimuth/altitude' if size == 17 else 'roll'})",
                 "mm", 0.2, 3.0, "Hard limit: >= 0.2 mm, no contact with tilt and dirt (estimate). Datasheet window "
                 "1.0-3.0 mm checked in the 'datasheet' column", cs, note,
                 extra=dict(datasheet_window=[1.0, 3.0]))


def encoder_disp(case):
    """Radial offset between the sensing centre and the rotation axis (worst case adds magnitudes)."""
    die = math.hypot(0.05, 0.05)
    if case == "P1":
        cs = [C("Sensing centre in the package (X/Y +/-0.05)", 0, die, src="MT6835", part="ST-521"),
              C("SMT placement", 0, 0.05, src="EST", part="ST-520"),
              C("Board holes to pads (drill registration)", 0, 0.075, src="EST", part="ST-520"),
              C("Board holes 3.2 on M3 thread-forming screws: float", 0, 0.10, src="EST", part="ST-520"),
              C("Carrier: screw holes to post holes", 0, fdm(34), src="FDM", part="ST-212/216"),
              C("Carrier post holes 3.4 on M3: float", 0, 0.20, src="ISO2768", part="ST-212/216"),
              C("Insert position in the housing flange", 0, fdm(74), src="FDM", part="ST-210/211"),
              C("Reducer centred by crush ribs", 0, 0.10, src="EST", part="ST-210/211"),
              C("Magnet in its seat (6.03 +0.02 / magnet +/-0.05)", 0, 0.05, src="EST", part="ST-208/209"),
              C("Tube seat run-out 0.02 TIR", 0, 0.01, src="ISO2768", part="ST-208/215"),
              C("Tube flange in its 28.2 seat, both ISO 2768-m", 0, (28.2 + 0.2 - (28.0 - 0.2)) / 2, src="ISO2768", part="ST-208/303"),
              C("Seat to output pilot, same set-up", 0, 0.02, src="EST", part="ST-303/312/313"),
              C("Output pilot 45 H7 on the reducer pilot", 0, 0.02, src="EST", part=""),
              C("Output bearing radial run-out", 0, 0.01, src="EST", part="reducer")]
    elif case == "PROD":
        cs = [C("Sensing centre in the package", 0, die, src="MT6835", part="ST-521"),
              C("SMT placement", 0, 0.05, src="EST", part="ST-520"),
              C("Board holes to pads", 0, 0.075, src="EST", part="ST-520"),
              C("Board hole float", 0, 0.10, src="EST", part="ST-520"),
              C("Carrier: screw holes to post holes (MJF)", 0, mjf(34), src="MJF", part="ST-212/216"),
              C("Carrier post holes 3.4 on M3: float", 0, 0.20, src="ISO2768", part="ST-212/216"),
              C("Tapped holes in the CNC housing", 0, 0.05, src="ISO2768", part="ST-210/211"),
              C("Reducer in an H7 bore", 0, 0.02, src="EST", part="ST-210/211"),
              C("Magnet in its seat", 0, 0.05, src="EST", part="ST-208/209"),
              C("Tube seat run-out", 0, 0.01, src="ISO2768", part="ST-208/215"),
              C("Tube flange in its seat, ISO 2768-m", 0, 0.30, src="ISO2768", part="ST-208/303"),
              C("Seat to output pilot", 0, 0.02, src="EST", part=""),
              C("Output pilot fit", 0, 0.02, src="EST", part=""),
              C("Output bearing run-out", 0, 0.01, src="EST", part="")]
    else:
        cs = [C("Sensing centre in the package", 0, die, src="MT6835", part="ST-521"),
              C("SMT placement", 0, 0.05, src="EST", part="ST-520"),
              C("Two NPTH locating holes to pads", 0, 0.05, src="EST", part="ST-520"),
              C("Locating pins 2 m6 in 2 H7 NPTH: clearance", 0, 0.015, src="EST", part="ST-520"),
              C("Pins to bearing bore, same CNC set-up", 0, 0.02, src="CNC_CALLOUT", part="ST-210/211"),
              C("Bearing bore fit (H6/h5 class)", 0, 0.01, src="EST", part="ST-210/211"),
              C("Magnet in a 6.00 +0.02 seat, magnet +/-0.02", 0, 0.02, src="EST", part="ST-208/209"),
              C("Tube seat run-out", 0, 0.01, src="ISO2768", part="ST-208/215"),
              C("Tube flange 28 h7 in a 28 H7 seat", 0, 0.021, src="EST", part="ST-208/303"),
              C("Seat to output pilot, same set-up", 0, 0.02, src="CNC_CALLOUT", part=""),
              C("Output pilot fit", 0, 0.02, src="EST", part=""),
              C("Output bearing run-out", 0, 0.01, src="EST", part="")]
    note = {"P1": "Fails: the carrier floats on its screws and the tube flange has 0.3 mm of radial play. The angle "
                  "error this causes is mostly first-harmonic and the per-unit cal.encoder map removes it, but DISP "
                  "above 0.3 mm is outside the datasheet's limit.",
            "PROD": "Still fails: the carrier float and the tube-flange play remain.",
            "FIX": "Fix (D96, approved 24 Nov): board located by two pins in the CNC housing; tube flange 28 h7 in a 28 H7 "
                   "seat; magnet seat 6.00 +0.02/0. Our magnet is 6 mm, smaller than the datasheet's 10 mm, so keep "
                   "DISP small."}[case]
    return Stack("S2", "Encoder off-axis offset DISP (chip sensing centre to rotation axis)", "mm", None, 0.30,
                 "MT6835 datasheet: DISP <= 0.3 mm", cs, note, radial=True)


def belt_range(case):
    """Centre-distance adjustment range of the motor plate against what the belt needs."""
    slot_travel = (9.4 - 3.4) / 2                       # ST-207 slots 9.4 x 3.4 on M3
    pos = {"P1": fdm(60) + iso2768(24, "m"), "PROD": iso2768(60, "m") + iso2768(24, "m"),
           "FIX": 0.05 + 0.05}[case]                    # insert/tap positions + slot positions
    need_long = 0.25 + 0.10                             # belt length +/-0.5 -> C +/-0.25; tension stretch 0.1 (est.)
    need_short = (P.PULLEY60["flange_d"] - P.PULLEY60["OD"]) / 2      # slack to slip the belt over the 60T outer flange (EST)
    avail = slot_travel - pos
    return dict(id=f"S3-{case}", title="Belt centre-distance range", C_nominal=round(P.BELT_C, 2),
                slot_travel=round(slot_travel, 2), position_tolerance=round(pos, 3), available=round(avail, 2),
                needed_long=round(need_long, 2), needed_short=round(need_short, 2),
                pass_wc=avail >= need_long and avail >= need_short,
                margin_long=round(avail - need_long, 2), margin_short=round(avail - need_short, 2),
                sources=["EST belt length +/-0.5 mm on a 200 mm loop", "EST install slack = 60T flange height",
                         "FDM/ISO2768 hole positions"])


def pulley_offset(case):
    """Axial offset between the belt planes of the 60T and 20T pulleys (cartridge frame Z)."""
    c = P.CART[17]
    p1 = case == "P1"
    cs = [C("Reducer: housing rear face to wave-generator hub face", 0, 0.10, src="EST", part="reducer"),
          C("60T pulley: mounting face to tooth-band centre", 0, 0.05 if not p1 else iso2768(6, "m"),
            src="CNC_CALLOUT" if not p1 else "ISO2768", part="ST-205"),
          C("Housing: rear flange face to wall tops (motor plate seat)", 0,
            fdm(c["z_motor_plate"]) if p1 else (iso2768(30, "m") if case == "PROD" else 0.05),
            src="FDM" if p1 else ("ISO2768" if case == "PROD" else "CNC_CALLOUT"), part="ST-210/211"),
          C("Motor plate thickness 4", 0, iso2768(4, "m") if case != "FIX" else 0.05,
            src="ISO2768" if case != "FIX" else "CNC_CALLOUT", part="ST-207"),
          C("20T pulley set on the shaft with a gauge", 0, 0.15, src="EST", part="ST-204"),
          C("20T pulley: hub face to tooth-band centre", 0, 0.05, src="EST", part="ST-204")]
    allow = (P.PULLEY60["w_teeth"] - P.BELT_W) / 2
    return Stack(f"S4", "Pulley axial alignment (belt-plane offset)", "mm", -allow, allow,
                 f"Belt must run between the flanges on both pulleys: tooth width {P.PULLEY60['w_teeth']} - belt "
                 f"{P.BELT_W} = +/-{allow:.2f}", cs,
                 "Fails worst case on P1 (printed housing). With a gauge for the 20T pulley and called-out CNC heights "
                 "it passes." if p1 else "")


def pulley_angle(case):
    """Angular misalignment of motor shaft to reducer axis, in degrees."""
    def deg(t, L):
        return math.degrees(math.atan(t / L))
    p1 = case == "P1"
    cs = [C("NEMA 17 face perpendicular to shaft (0.05 over the 22 pilot)", 0, deg(0.05, 22), src="EST", part="motor"),
          C("Motor plate pilot square to plate (0.05 now; 0.02 called out in FIX)", 0, deg(0.05 if case != "FIX" else 0.02, 22.2),
            src="ISO2768" if case != "FIX" else "CNC_CALLOUT", part="ST-207"),
          C("Housing wall tops parallel to the rear flange over 62 mm", 0,
            deg(fdm(62) * 2, 62) if p1 else deg(0.1 if case == "PROD" else 0.03, 62),
            src="FDM" if p1 else "CNC_CALLOUT", part="ST-210/211"),
          C("Reducer input axis to housing face", 0, deg(0.02, 25), src="EST", part="reducer")]
    return Stack("S5", "Pulley angular misalignment", "deg", None, 0.25, "Gates/Fenner: <= 1/4 deg", cs,
                 "P1 relies on the printed wall tops; production CNC passes." if p1 else "", radial=True)


def pulley_runout(case):
    """Run-out (TIR) of the 60T pulley pitch circle, and its share of the accuracy budget."""
    cs = [C("Wave-generator stub run-out", 0, 0.01, src="EST", part="reducer"),
          C("Pulley bore on the 25 stub, H7/g6 clearance (TIR = max clearance)", 0, 0.041 if case != "FIX" else 0.0,
            src="EST", part="ST-205"),
          C("Pulley spigot H6 / light press, eccentricity <= 0.005", 0, 0.0 if case != "FIX" else 0.01, src="EST", part="ST-205"),
          C("Pitch circle to bore", 0, 0.02 if case != "FIX" else 0.01, src="EST", part="ST-205")]
    st = Stack("S6", "60T pulley run-out (TIR)", "mm", None, 0.03, "Spec 3.5: <= 0.03 mm", cs, radial=True)
    ev = st.evaluate()
    tir = ev["wc"][1]
    # spec 3.5: 0.04 TIR -> +/-2.16" per pulley -> 0.26" RMS after PEC for two pulleys; scale linearly
    belt_rms = 0.26 * tir / 0.04
    base = 2.19
    total = math.sqrt(base ** 2 - 0.26 ** 2 + belt_rms ** 2)
    st.extra = dict(belt_term_rms_arcsec=round(belt_rms, 3), eq_budget_total_arcsec=round(total, 2), eq_target=3.0)
    st.note = (f"Worst-case TIR {tir:.3f} mm raises the belt term from 0.26 to {belt_rms:.2f} arcsec RMS; the EQ budget "
               f"goes from 2.19 to {total:.2f} arcsec (target 3). Accuracy holds, the pulley spec does not, unless the "
               f"bore is a light press (fix).")
    return st


def concentricity(case):
    """Circular-spline register to output-bearing register in our CNC housing (D87 component sets)."""
    if case == "FIX":
        cs = [C("CS register and bearing bore bored in one set-up", 0, 0.008, src="EST", part="ST-210/211 P2"),
              C("CS register fit H6 / CS OD", 0, 0.006, src="EST", part=""),
              C("Bearing bore fit (bearing maker's H6 class)", 0, 0.006, src="EST", part="")]
        note = "Requirement to be replaced by the selected component set's assembly-tolerance table (RFQ)."
    else:
        cs = [C("CS register and bearing bore, two set-ups, ISO 2768-m position", 0, 0.10, src="ISO2768", part=""),
              C("CS register fit H7", 0, 0.015, src="EST", part=""),
              C("Bearing bore fit H7", 0, 0.015, src="EST", part="")]
        note = "Two set-ups or general tolerances cannot hold a strain-wave assembly; both bores must be one set-up."
    return Stack("S7", "Component-set concentricity in the CNC housing (D87)", "mm", None, 0.015,
                 "Estimate 0.015 mm (typical of strain-wave component-set catalogues; replace with the RFQ drawing)",
                 cs, note, radial=True)


def vrings():
    """V-ring fitted width available in the geometry against the catalogue B1."""
    rows = []
    # azimuth: V-ring back on the ST-303 shoulder, counterface = body ST-310 floor underside Z 46.5
    for rev, sh in (("rev C", 39.8), ("rev D (D94)", P.VRING_AZ_SHOULDER)):
        rows.append(dict(axis="azimuth", rev=rev, seal="VA-75 (ST-213)", available=round(P.Z_BODY_BOT - sh, 2), B1=9.0, tol=1.2,
                         chain=f"ST-303 shoulder Z {sh} -> body ST-310 floor underside Z {P.Z_BODY_BOT}",
                         contrib=[("ST-303 shoulder to output face (CNC)", 0.10), ("Housing ear face to output face (reducer flange)", 0.10),
                                  ("Body ear boss height to floor (MJF, Z)", 0.30), ("Body floor flatness R42-R48 (MJF)", 0.20)],
                         fix="done in rev D: shoulder 2.3 mm lower" if sh != 39.8 else ""))
    # altitude: V-ring back on the arm face X 46, counterface = tower pad face X 43.5 (1 mm proud of 42.5)
    rows.append(dict(axis="altitude", rev="rev C/D", seal="VA-80 (ST-218)", available=round(P.ALT_OUT_X - (P.TOWER_X_MAX + 1.0), 2),
                     B1=9.0, tol=1.2, chain="arm ST-312 hub face X 46 -> tower ST-311 counterface pad X 43.5",
                     contrib=[("Reducer flange, output face to housing face", 0.10), ("Tower wall / pad (MJF)", 0.30),
                              ("Cartridge ear seat in the tower (MJF)", 0.20)],
                     fix="D95: smaller seal on a smaller arm seat (e.g. VA-65 size), lip on the reducer face inside the tower opening (6.0 mm); being chosen"))
    # roll: V-ring back on the shelf face (output face), counterface = reducer / housing front face at z = L_flange
    rows.append(dict(axis="roll", rev="rev C/D", seal="VA-65 (ST-219)", available=round(P.RED[14]["L_flange"] + P.VRING_ROLL_RECESS, 2),
                     B1=7.0, tol=1.0, chain="shelf ST-313 face (output face) -> reducer and housing front face",
                     contrib=[("Reducer flange, output face to housing face", 0.10), ("Shelf seat face (CNC)", 0.05)],
                     fix="Recess not possible (clamp end sits on the shelf face). 6.0 is inside 7.0 +/- 1.0 at nominal; "
                         "0.15 mm under at worst case. Rev D adds the missing back support (R36)"))
    for r in rows:
        wc = sum(t for _, t in r["contrib"])
        lo, hi = r["B1"] - r["tol"], r["B1"] + r["tol"]
        r["wc"] = [round(r["available"] - wc, 2), round(r["available"] + wc, 2)]
        r["window"] = [lo, hi]
        r["pass_nominal"] = lo <= r["available"] <= hi
        r["pass_wc"] = r["wc"][0] >= lo and r["wc"][1] <= hi
        r["over_compression_mm"] = round(max(0.0, lo - r["available"]), 2)
    return rows


def wedge_dowels():
    """Two 4 m6 dowels in ST-331 into two 4 H7 holes in ST-303 at R33 (66 mm apart)."""
    span = 2 * P.WEDGE_PIN_R
    h7, m6 = (0.0, 0.012), (0.004, 0.012)
    cmin, cmax = h7[0] - m6[1], h7[1] - m6[0]
    pos_m = iso2768(span, "m")                       # pin spacing and hole spacing at general tolerance
    need = 2 * pos_m                                 # spacing mismatch to absorb
    # fix: hole A 4 E7 round, hole B 4 E7 slot along the pin line (E7 for 3-6 mm: +0.020/+0.032)
    f7 = (0.020, 0.032)
    fmin, fmax = f7[0] - m6[1], f7[1] - m6[0]
    yaw_arcsec = math.degrees(fmax / span) * 3600 * 2   # both ends play across the slot width
    return dict(id="S8", title="Wedge dowels head <-> wedge", span=span,
                as_designed=dict(fit="4 H7 / 4 m6, two round holes", clearance=[round(cmin, 3), round(cmax, 3)],
                                 spacing_mismatch_to_absorb=round(need, 2), passes=cmin > 0 and cmax / 1 >= need),
                fix=dict(fit="hole A 4 E7 round, hole B 4 E7 x 6 slot on the pin line; spacing +/-0.05 called out",
                         clearance=[round(fmin, 3), round(fmax, 3)], yaw_play_arcsec=round(yaw_arcsec, 0),
                         lateral_play=round(fmax / 2, 3), passes=fmin > 0),
                note="With H7/m6 the clearance is -0.012...+0.008 mm and two round holes must also absorb the "
                     f"pin-spacing error (+/-{pos_m} each at ISO 2768-m): the head will not drop onto the wedge by hand. "
                     "The head's azimuth on the wedge is not accuracy-critical (encoder and pointing model take it).")


def clamp_seat(case):
    p1 = case == "P1"
    cs = [C("Roll pilot bore 36 H7 to shelf top 32 (CNC)", P.SHELF_TOP, iso2768(P.SHELF_TOP, "m") if case != "FIX" else 0.05,
            src="ISO2768" if case != "FIX" else "CNC_CALLOUT", part="ST-313"),
          C("Clamp height 13 (Sunwayfoto DDC-60i)", P.CLAMP["H"], 0.10, src="EST", part="ST-314")]
    return Stack("S9", "Clamp seat above the roll axis (D20, 45 mm)", "mm", 44.5, 45.5,
                 "Balance only: +/-0.5 mm moves a 7 kg load's balance by 3.4 N.mm (estimate of what matters)", cs,
                 "Not accuracy-critical; the clamp's yaw on its 3/8 in screw (10.2 hole, +/-0.34 mm) is a fixed "
                 "collimation term, which the firmware's 7-term pointing model fits.")


def oled_window(case):
    p1 = case == "P1"
    proc = (lambda L: fdm(L)) if p1 else ((lambda L: mjf(L)) if case == "PROD" else (lambda L: mould(L)))
    src = "FDM" if p1 else ("MJF" if case == "PROD" else "MOULD")
    rows = {}
    for axis, win, act in (("vertical", 18.0, 14.70), ("horizontal", 34.0, 29.42)):
        cs = [C("Window position to the board bosses (bezel)", 0, proc(40), src=src, part="ST-315"),
              C("Window half-size", 0, proc(win) / 2, src=src, part="ST-315"),
              C("Board holes 3.4 on M3 thread-forming: float", 0, 0.20, src="ISO2768", part="ST-501"),
              C("OLED module soldered on a 4-pin header", 0, 0.30, src="EST", part="ST-516"),
              C("Active area to module PCB", 0, 0.30, src="OLED", part="ST-516")]
        margin = (win - act) / 2
        st = Stack(f"S10-{axis}", f"OLED active area inside the bezel window ({axis})", "mm", 0.0, None,
                   "Every pixel visible straight on: margin >= 0", [C("Nominal margin per side", margin, 0.0, +1, "OLED", "")] +
                   [C(x.name, 0, x.tol, -1, x.src, x.part) for x in cs])
        ev = st.evaluate()
        depth = 2.0 if case == "FIX" else 5.0         # glass 2 mm behind the bezel inner face + 3 mm bezel; D99 chamfer -> 2
        ev["view_angle_nominal_deg"] = round(math.degrees(math.atan(margin / depth)), 1)
        ev["view_angle_wc_deg"] = round(math.degrees(math.atan(max(ev["wc"][0], 0) / depth)), 1)
        rows[axis] = ev
    return rows


def usb_opening(case):
    p1 = case == "P1"
    proc = fdm if p1 else mjf
    cs = [C("Opening position to the board bosses", 0, proc(40), src="FDM" if p1 else "MJF", part="ST-315"),
          C("Opening half-size", 0, proc(10) / 2, src="FDM" if p1 else "MJF", part="ST-315"),
          C("Board float on its screws", 0, 0.20, src="ISO2768", part="ST-501"),
          C("Socket on the board (placement + pin play)", 0, 0.10, src="EST", part="GT-USB-7051A")]
    margin = (10.0 - 8.94) / 2                          # USB-C receptacle shell 8.94 wide (typical)
    return Stack("S11", "USB-C shell inside the bezel opening (horizontal)", "mm", 0.0, None,
                 "No contact with the bezel: margin >= 0", [C("Nominal margin per side (10.0 vs 8.94 shell)", margin, 0, +1, "EST", "")] +
                 [C(x.name, 0, x.tol, -1, x.src, x.part) for x in cs],
                 "Production replaces this socket with a sealed one (D89); the opening is redesigned with it.")


def oring_groove(cs_d=2.5, cs_tol=0.08, case="FIX"):
    """Face-seal O-ring cord in a groove with a hard stop: squeeze range, and the groove depth that centres it."""
    depth_tol = {"PROD": mjf(2), "FIX": mould(2)}[case]
    gap = {"PROD": 0.20, "FIX": 0.10}[case]            # local face gap between screws from flatness (estimate)
    best = None
    for i in range(0, 200):
        d = cs_d * 0.6 + i * 0.005
        smin = (cs_d - cs_tol - (d + depth_tol) - gap) / (cs_d - cs_tol)
        smax = (cs_d + cs_tol - (d - depth_tol)) / (cs_d + cs_tol)
        score = min(smin - 0.15, 0.30 - smax)
        if best is None or score > best[0]:
            best = (score, d, smin, smax)
    _, d, smin, smax = best
    return dict(id=f"S12-{case}", title=f"O-ring cord {cs_d} mm face seal (D88/D89)", cs=cs_d, cs_tol=cs_tol,
                depth=round(d, 2), depth_tol=round(depth_tol, 3), face_gap=gap,
                squeeze_wc=[round(100 * smin, 1), round(100 * smax, 1)], window=[15, 30],
                pass_wc=smin >= 0.15 - 1e-9 and smax <= 0.30 + 1e-9)


def flat_gasket():
    """Why the 1.0 mm flat gaskets do not hold IPX6 on MJF faces."""
    comp_ok = (0.15, 0.30)                            # same window applied to a solid 1.0 mm silicone strip
    t = P.GASKET_T
    gap = mjf(150) * 2                               # opposed faces each +/- 0.3 % over a 150 mm cover flange
    return dict(id="S13", title="Flat 1.0 mm gasket on MJF faces", thickness=t,
                compression_window_mm=[t * comp_ok[0], t * comp_ok[1]], flatness_gap_mm=round(gap, 2),
                passes=gap <= t * (comp_ok[1] - comp_ok[0]),
                note="The face gap from MJF tolerance (up to 0.9 mm over 150 mm) is larger than the 0.15 mm usable "
                     "compression range of a 1 mm gasket, so low spots leak. Production uses O-ring cord in a groove "
                     "with a hard stop (S12), as D88 says.")


# ================================================================================================ run
def run():
    res = dict(rev="Phase 8, 24 Nov 2026", sources=SOURCES, cases={}, single={})
    for case in ("P1", "PROD", "FIX"):
        r = {}
        for s in (17, 14):
            r[f"S1-{s}"] = encoder_gap(s, case).evaluate()
            lo, hi = r[f"S1-{s}"]["extra"]["datasheet_window"]
            r[f"S1-{s}"]["pass_datasheet_wc"] = r[f"S1-{s}"]["wc"][0] >= lo and r[f"S1-{s}"]["wc"][1] <= hi
            r[f"S1-{s}"]["pass_datasheet_rss"] = r[f"S1-{s}"]["rss"][0] >= lo and r[f"S1-{s}"]["rss"][1] <= hi
        r["S2"] = encoder_disp(case).evaluate()
        r["S3"] = belt_range(case)
        r["S4"] = pulley_offset(case).evaluate()
        r["S5"] = pulley_angle(case).evaluate()
        r["S6"] = pulley_runout(case).evaluate()
        if case != "P1":
            r["S7"] = concentricity(case).evaluate()
        r["S9"] = clamp_seat(case).evaluate()
        r["S10"] = oled_window(case)
        if case != "FIX":
            r["S11"] = usb_opening(case).evaluate()
        if case != "P1":
            r["S12"] = oring_groove(case=case)
        if case == "FIX":
            r["S12b"] = oring_groove(cs_d=3.0, case=case)
            r["S12b"]["id"] = "S12b-FIX"
        res["cases"][case] = r
    res["single"]["vrings"] = vrings()
    res["single"]["S8"] = wedge_dowels()
    res["single"]["S13"] = flat_gasket()
    return res


def yn(b):
    return "pass" if b else "**fail**"


def fmt_range(a):
    return f"{a[0]:.3f} … {a[1]:.3f}"


def report(res):
    L = ["# Tolerance stack-ups (Phase 8, deliverable 3)", "",
         "Generated by `tools/production/tolerance_stackups.py` from `hardware/cad/stcad/params.py` and the part code. "
         "Cases: **P1** = prototype as ordered (FDM/MJF/JLCCNC, ISO 2768-m); **PROD** = D87/D88 processes, Phase 3 "
         "geometry; **FIX** = production with the changes approved on 24 Nov (D94–D99). Worst case (WC) adds every "
         "tolerance; RSS takes each as ±3σ. Contributors marked EST are estimates.", ""]
    L += ["## Summary", "", "| Stack | Limit | P1 WC / RSS | PROD WC / RSS | FIX WC / RSS |", "|---|---|---|---|---|"]
    C_ = res["cases"]

    def cell(case, key, sub=None):
        if key not in C_[case]:
            return "–"
        e = C_[case][key] if sub is None else C_[case][key][sub]
        if "pass_rss" in e:
            return f"{yn(e['pass_wc'])} / {yn(e['pass_rss'])}"
        return yn(e["pass_wc"])
    rows = [("S1-17 encoder gap, size 17", "≥ 0.2 (hard)", "S1-17", None), ("S1-14 encoder gap, size 14", "≥ 0.2 (hard)", "S1-14", None),
            ("S2 encoder DISP", "≤ 0.3", "S2", None), ("S3 belt adjustment range", "covers belt", "S3", None),
            ("S4 pulley axial offset", "±0.5", "S4", None), ("S5 pulley angle", "≤ 0.25°", "S5", None),
            ("S6 60T pulley run-out", "≤ 0.03 TIR", "S6", None), ("S7 component-set concentricity", "≤ 0.015 (est.)", "S7", None),
            ("S9 clamp seat", "45 ± 0.5", "S9", None), ("S10 OLED window, vertical", "margin ≥ 0", "S10", "vertical"),
            ("S10 OLED window, horizontal", "margin ≥ 0", "S10", "horizontal"), ("S11 USB-C opening", "margin ≥ 0", "S11", None),
            ("S12 O-ring cord 2.5 squeeze", "15–30 %", "S12", None),
            ("S12b O-ring cord 3.0 squeeze", "15–30 %", "S12b", None)]
    for name, lim, key, sub in rows:
        L.append(f"| {name} | {lim} | {cell('P1', key, sub)} | {cell('PROD', key, sub)} | {cell('FIX', key, sub)} |")
    v = res["single"]["vrings"]
    for r in v:
        L.append(f"| V-ring {r['axis']} {r['seal']} {r['rev']} | B1 {r['B1']} ± {r['tol']} | {r['available']} mm, WC {r['wc'][0]}–{r['wc'][1]}: "
                 f"{yn(r['pass_wc'])} | same as P1 | {r['fix']} |")
    w = res["single"]["S8"]
    L.append(f"| S8 wedge dowels | slide by hand | H7/m6: {yn(w['as_designed']['passes'])} | same as P1 | E7 + slot: {yn(w['fix']['passes'])} |")
    L.append(f"| S13 flat 1 mm gasket on MJF | IPX6 | {yn(res['single']['S13']['passes'])} | same as P1 | replaced by S12 |")
    L.append("")

    for case in ("P1", "PROD", "FIX"):
        L += [f"## Case {case}", ""]
        for key, e in C_[case].items():
            if key == "S10":
                for ax, ev in e.items():
                    L += _stack_md(ev)
                    L.append(f"Edge pixels stay visible up to {ev['view_angle_nominal_deg']}° off-axis at nominal, "
                             f"{ev['view_angle_wc_deg']}° at worst case ({'45° chamfer, D99: limiting edge 2 mm from the glass' if case == 'FIX' else 'glass 5 mm behind the outer face'}).")
                    L.append("")
                continue
            if key == "S3":
                L += [f"### {e['title']} ({case})", "",
                      f"Nominal C {e['C_nominal']} mm. Slot travel ±{e['slot_travel']} mm, minus hole/slot position "
                      f"tolerance {e['position_tolerance']} → ±{e['available']} mm available. Needed: +{e['needed_long']} mm "
                      f"(longest belt + stretch), −{e['needed_short']} mm (belt over the 20T flange). Margins "
                      f"+{e['margin_long']} / {e['margin_short']} mm → {yn(e['pass_wc'])}.", ""]
                continue
            if key in ("S12", "S12b"):
                L += [f"### {e['title']} ({case})", "",
                      f"Cord {e['cs']} ± {e['cs_tol']} mm; groove depth {e['depth']} ± {e['depth_tol']} mm (depth chosen "
                      f"to centre the window); face gap up to {e['face_gap']} mm between screws. Squeeze {e['squeeze_wc'][0]}–"
                      f"{e['squeeze_wc'][1]} % worst case against {e['window'][0]}–{e['window'][1]} % → {yn(e['pass_wc'])}.", ""]
                continue
            L += _stack_md(e)
    L += ["## V-ring fitted widths (all cases)", "", "| Axis | Rev | Seal | Chain | Available | Catalogue B1 | WC range | Result | Fix |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in v:
        L.append(f"| {r['axis']} | {r['rev']} | {r['seal']} | {r['chain']} | {r['available']} | {r['B1']} ± {r['tol']} "
                 f"({r['window'][0]}–{r['window'][1]}) | {r['wc'][0]}–{r['wc'][1]} | {yn(r['pass_wc'])} | {r['fix']} |")
    L += ["", "## S8 Wedge dowels", "", w["note"], "",
          f"Fix: {w['fix']['fit']}. Clearance {w['fix']['clearance'][0]}–{w['fix']['clearance'][1]} mm; yaw play "
          f"≤ {w['fix']['yaw_play_arcsec']:.0f}″; lateral ≤ {w['fix']['lateral_play']} mm.", "",
          "## S13 Flat gaskets", "", res["single"]["S13"]["note"], "", "## Sources", ""]
    for k, s in res["sources"].items():
        L.append(f"- **{k}**: {s}")
    return "\n".join(L) + "\n"


def _stack_md(e):
    L = [f"### {e['id']} {e['title']}", ""]
    if e["radial"]:
        L.append(f"Radial/angular magnitudes add. WC {e['wc'][1]:.3f} {e['unit']}, RSS {e['rss'][1]:.3f} {e['unit']}; "
                 f"limit {e['limits'][1]} ({e['limit_source']}). WC {yn(e['pass_wc'])}, RSS {yn(e['pass_rss'])}.")
    else:
        lim = " … ".join("–" if x is None else f"{x}" for x in e["limits"])
        L.append(f"Nominal {e['nominal']:.3f} {e['unit']}; WC {fmt_range(e['wc'])}; RSS {fmt_range(e['rss'])}; "
                 f"limit {lim} ({e['limit_source']}). WC {yn(e['pass_wc'])}, RSS {yn(e['pass_rss'])}; "
                 f"about {e['out_of_spec_ppm']:.0f} ppm out of spec (normal model).")
        if "pass_datasheet_wc" in e:
            L.append(f"Against the datasheet's 1.0–3.0 mm: WC {yn(e['pass_datasheet_wc'])}, RSS {yn(e['pass_datasheet_rss'])}.")
    L += ["", "| Contributor | Part | Nominal | ± | Source |", "|---|---|---|---|---|"]
    for c in e["contributors"]:
        L.append(f"| {c['name']} | {c['part']} | {c['nominal']:.3f} | {c['tol']:.3f} | {c['source']} |")
    if e.get("note"):
        L += ["", e["note"]]
    L.append("")
    return L


def main():
    res = run()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stackups.json"), "w") as f:
        json.dump(res, f, indent=1)
    with open(os.path.join(OUT, "stackups.md"), "w") as f:
        f.write(report(res))
    print(f"wrote {OUT}/stackups.md and stackups.json")
    return res


if __name__ == "__main__":
    main()
