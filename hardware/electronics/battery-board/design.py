"""ST-602 battery board: schematic and layout as code.
Rebuild: tools/layout.py battery-board (or the GitHub workflow "Phase 4 electronics").

The board stands at the outer end of the 2S2P pack (ST-601 cells), 32 x 40 mm, two layers, every part on the outer face
(the inner face lies 0.6 mm from the cell holder and the nickel strips). Seen from outside the pack: the cell pair on the
left ends in B+ at the board, the pair on the right in B-; the middle of the pack (MID) comes from the far end on a thin wire.

Circuit (TI BQ40Z50-R2 data sheet SLUSCS4C section 9.2 and evaluation module SLUUAV7C, set up for two cells in series):
  B+ -> three-terminal fuse F1 -> charge FET Q1 -> discharge FET Q2 -> PACK+      (high side)
  B- -> 1 mohm sense resistor R1 -> PACK-
  U1 BQ40Z50-R2 gauge and first-level protector, U2 BQ294700 second-level over-voltage protector (4.35 V per cell);
  either of them blows F1 through Q3. Four charge-state LEDs and the button behind the pack's light pipe ST-611.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from schgen import Design, NC   # noqa: E402
import catalog as cat           # noqa: E402

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
PCB_ARGS = dict(layers=2, default_track=0.2, default_via=(0.6, 0.3), clearance=0.15)
W, H = 32.0, 40.0
LED_Y = 13.0                     # centre line of the light pipe ST-611 (board centre + 13 mm), window 29.2 x 7.2 mm
LED_X = (-10.5, -6.0, 6.0, 10.5)


def build():
    d = Design("st-602", "ST-602 battery board", rev="A", sym_dirs=[LIB])
    n = {}

    def ref(prefix):
        n[prefix] = n.get(prefix, 0) + 1
        return f"{prefix}{n[prefix]}"

    def r(s, value, a, b, **kw):
        fp, f = cat.fields("R", value)
        f.update(kw)
        return s.R(ref("R"), value, a, b, pkg=fp, **f)

    def c(s, value, a, b, **kw):
        fp, f = cat.fields("C", value)
        f.update(kw)
        return s.C(ref("C"), {"100n50": "100n 50V"}.get(value, value), a, b, pkg=fp, **f)

    def ic(s, lib, prefix, key, pins, x, y, value=None, **kw):
        fp, f = cat.fields("P", key)
        f.update(kw)
        return s.part(lib, ref(prefix), value or cat.PART[key][1], fp, pins, x=x, y=y, **f)

    def pad(s, name, net, fp, x, y):
        return s.part("Connector_Generic:Conn_01x01", ref("J"), name, fp, {1: net}, x=x, y=y, bom=False)

    s = d.sheet("main", "Gauge, protection, fuse and charge display", paper="A3")

    # ------------------------------------------------------------------ cells, fuse, FETs, sense resistor
    s.note(20, 18, "Cell connections (nickel tabs soldered to J1, J2; MID on a thin wire) and the pack leads.\n"
                   "High side: B+ -> fuse F1 -> charge FET Q1 -> discharge FET Q2 -> PACK+. Low side: B- -> R1 (1 mohm) -> PACK-.\n"
                   "GND on this board is the cells' minus (B-), the gauge's VSS.", 1.6)
    pad(s, "B+ tab", "BP", "ST:TabPad_5.0x5.5mm", 30, 50)
    pad(s, "B- tab", "GND", "ST:TabPad_5.0x5.5mm", 30, 62)
    pad(s, "MID wire", "MID", "ST:WirePad_1.6x2.6mm", 30, 74)
    pad(s, "PACK+ lead", "PACKP", "ST:WirePad_3.2x4.0mm", 30, 86)
    pad(s, "PACK- lead", "PACKN", "ST:WirePad_3.2x4.0mm", 30, 98)
    pad(s, "SMBC wire", "SMBC_J", "ST:WirePad_1.6x2.6mm", 30, 110)
    pad(s, "SMBD wire", "SMBD_J", "ST:WirePad_1.6x2.6mm", 30, 122)
    pad(s, "PRES wire", "PRES_J", "ST:WirePad_1.6x2.6mm", 30, 134)
    ic(s, "ST:ITV4030", "F", "FUSE3T", {"F1": "BF", "F2": "BP", "HEAT": "FUSE_H"}, 75, 50, value="ITV4030L0815")
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "CHG_G", "D": "VCC", "S": "BF"}, 115, 50)          # Q1 charge FET
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "DSG_G", "D": "VCC", "S": "PACKP"}, 155, 50)       # Q2 discharge FET
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "FUSE_G", "D": "FUSE_H", "S": "GND"}, 75, 95)      # Q3 fuse driver
    fp, f = cat.fields("P", "NFET_S")
    s.part("ST:NMOS_SOT23", ref("Q"), "2N7002", fp, {"G": "Q4_G", "D": "DSG_G", "S": "PACKP"}, x=155, y=95, **f)   # Q4
    s.lane(60, 125, cols=4)
    r(s, "0R001", "GND", "PACKN")            # R1 sense resistor
    # Kelvin taps: the two sense lines start on the inner edges of R1's pads and are nets of their own, so that neither
    # the ground plane nor the copper carrying the pack current can share them
    s.part("Device:NetTie_2", "NT1", "tap B-", "ST:NetTie_2_Kelvin_0.3mm", {1: "GND", 2: "SRP_K"}, x=115, y=150, bom=False)
    s.part("Device:NetTie_2", "NT2", "tap PACK-", "ST:NetTie_2_Kelvin_0.3mm", {1: "PACKN", 2: "SRN_K"}, x=155, y=150, bom=False)
    r(s, "5k1", "CHG", "CHG_G", owner="Q1")
    r(s, "10M", "CHG_G", "BF", owner="Q1")
    r(s, "5k1", "DSG", "DSG_G", owner="Q2")
    r(s, "10M", "DSG_G", "PACKP", owner="Q2")
    r(s, "10k", "Q4_G", "GND", owner="Q4")
    r(s, "5k1", "OV_OUT", "FUSE_G", owner="Q3")
    r(s, "49k9", "FUSE_G", "GND", owner="Q3")
    c(s, "100n", "FUSE_G", "GND", owner="Q3")

    # ------------------------------------------------------------------ gauge
    s.note(200, 18, "U1 BQ40Z50-R2 for two cells: VC2 is the top of the stack, VC3 and VC4 are tied to it. PCHG is not used (the charger\n"
                    "BQ25792 does the pre-charge). PTC is switched off (PTC and PTCEN to VSS). TS1: 10 k thermistor bead on the cells.\n"
                    "LEDs wired between pairs of the three LED pins as on TI's evaluation module; R21-R23 are 0 ohm links.", 1.6)
    ic(s, "ST:BQ40Z50", "U", "BQ40Z50",
       {"BAT": "BAT", "VCC": "VCC", "PACK": "PACK_S", "PBI": "PBI", "VC4": "VC2", "VC3": "VC2", "VC2": "VC2", "VC1": "VC1", "SRP": "SRP",
        "SRN": "SRN", "TS1": "TS1", "TS2": "GND", "TS3": "GND", "TS4": "GND", "PTC": "GND", "PTCEN": "GND", "VSS": "GND", "EP": "GND",
        "CHG": "CHG", "PCHG": NC, "DSG": "DSG", "FUSE": "FUSE_G", "SMBC": "SMBC", "SMBD": "SMBD", "PRES/SHUTDN": "PRES", "BTP_INT": "GND",
        "DISP": "DISP", "LEDCNTLA": "LEDA", "LEDCNTLB": "LEDB", "LEDCNTLC": "LEDC", "NC": NC}, 250, 75)
    s.lane(205, 135, cols=5)
    c(s, "2u2", "PBI", "GND", owner="U1")
    r(s, "100R", "MID", "VC1", owner="U1")
    r(s, "100R", "BP", "VC2", owner="U1")
    c(s, "100n", "VC1", "GND", owner="U1")
    c(s, "100n", "VC2", "VC1", owner="U1")
    r(s, "100R", "SRP_K", "SRP", owner="U1")
    r(s, "100R", "SRN_K", "SRN", owner="U1")
    c(s, "100n", "SRP", "SRN", owner="U1")
    fp, f = cat.fields("P", "BAT54")
    s.two("Device:D_Schottky", ref("D"), "BAT54WS", "BAT_D", "BP", fp, owner="U1", **f)      # D1: pin 1 cathode, pin 2 anode
    r(s, "100R", "BAT_D", "BAT", owner="U1")
    c(s, "100n50", "BAT", "GND", owner="U1")
    c(s, "100n50", "VCC", "GND", owner="U1")
    r(s, "10k", "PACKP", "PACK_S", owner="U1")
    s.part("Connector_Generic:Conn_01x02", "TH1", "NTC 10k bead", "ST:WirePads_1x02_P2.0mm_1.5x2.4mm", {1: "TS1", 2: "GND"}, x=330, y=60, bom=False)

    # ------------------------------------------------------------------ second-level protector
    s.note(20, 165, "U2 BQ294700: trips at 4.35 V on either cell after 1 to 2 s (C11) and drives Q3 through R7.\n"
                    "V3 and V4 are tied to V2 for two cells.", 1.6)
    ic(s, "ST:BQ2947", "U", "BQ2947", {"VDD": "VDD2", "V4": "V2", "V3": "V2", "V2": "V2", "V1": "V1", "VSS": "GND", "EP": "GND",
                                       "OUT": "OV_OUT", "CD": "CD"}, 60, 195)
    s.lane(20, 225, cols=4)
    r(s, "1k", "MID", "V1", owner="U2")
    r(s, "1k", "BP", "V2", owner="U2")
    c(s, "100n", "V1", "GND", owner="U2")
    c(s, "100n", "V2", "V1", owner="U2")
    r(s, "100R", "BP", "VDD2", owner="U2")
    c(s, "100n50", "VDD2", "GND", owner="U2")
    c(s, "100n", "CD", "GND", owner="U2")

    # ------------------------------------------------------------------ SMBus, presence, display
    s.note(200, 165, "SMBus and presence to the blade connector through 100 ohm and an ESD array. The head pulls PRES to ground (1 k).\n"
                     "SW1 shows the charge state on D2-D5 (LED 1 = lowest).", 1.6)
    ic(s, "Power_Protection:SRV05-4", "U", "SRV05", {"IO1": "SMBC_J", "IO2": "SMBD_J", "IO3": "PRES_J", "IO4": "PRES_J", "VP": NC, "VN": "GND"},
       250, 195)
    s.lane(205, 225, cols=5)
    r(s, "100R", "SMBC", "SMBC_J", owner="U3")
    r(s, "100R", "SMBD", "SMBD_J", owner="U3")
    r(s, "100R", "PRES", "PRES_J", owner="U3")
    r(s, "0R", "LEDA", "LA", owner="U1")
    r(s, "0R", "LEDB", "LB", owner="U1")
    r(s, "0R", "LEDC", "LC", owner="U1")
    fp, f = cat.fields("P", "LED_G")
    for a, k in (("LA", "LB"), ("LB", "LA"), ("LB", "LC"), ("LC", "LB")):     # LED 1 to 4: anode, cathode
        s.two("Device:LED", ref("D"), "green", k, a, fp, **f)
    fp, f = cat.fields("P", "TACT")
    s.part("Switch:SW_Push", ref("SW"), "TS-1187A", fp, {1: "DISP", 2: "GND"}, x=330, y=195, **f)
    s.lane(330, 225, cols=1, dy=7.62)
    for i, net in enumerate(["FUSE_G", "GND", "VCC"]):
        s.tp(f"TP{i + 1}", net)
    s.lane(330, 110, cols=2, dx=25.4)
    for net in ("GND", "BAT", "VCC", "VDD2"):
        s.flag(net)
    return d


FIXED = {
    # high side, left column, bottom to top
    "J1": (-11.1, -16.8, 0), "F1": (-11.0, -10.3, 180), "Q1": (-11.0, -4.6, 90), "Q2": (-11.0, 1.4, 270), "J4": (-13.2, 6.3, 0),
    # low side, right column
    "J2": (11.1, -16.8, 0), "R1": (11.1, -10.6, 90), "J5": (13.2, -5.0, 0),
    # thin wires at the right edge
    "J3": (14.1, -0.6, 90), "J8": (14.1, 1.7, 90), "J7": (14.1, 4.0, 90), "J6": (14.1, 6.3, 90),
    "U1": (0.4, -2.0, 90), "Q3": (-5.4, -10.3, 180), "U2": (-3.4, -15.3, 0), "U3": (8.6, 3.2, 90), "TH1": (5.4, -16.3, 0),
    "Q4": (-7.2, 6.4, 0), "NT1": (10.1, -11.75, 180), "NT2": (10.1, -9.45, 180),
    # sense filter: the two 100 ohm resistors side by side, their far ends toward the sense resistor (R11 SRP, R12 SRN)
    "R11": (4.0, -8.2, 180), "R12": (4.0, -9.2, 180), "C5": (2.4, -8.7, 270),
    # the gauge's own capacitors and resistors, each right at its pin (left side of U1, top to bottom; PBI below; LED links above)
    "C7": (-4.6, -0.6, 180), "R14": (-4.6, -1.9, 0), "C6": (-4.6, -3.8, 180), "R13": (-4.6, -4.8, 0), "C2": (-1.0, -6.3, 270),
    "R21": (0.6, 3.2, 90), "R22": (-0.35, 3.2, 90), "R23": (-1.3, 3.2, 90),
    "D1": (-7.5, -4.8, 180), "R10": (-6.9, -6.35, 0), "R19": (5.0, 3.3, 0), "R18": (5.0, 4.3, 0),
    "SW1": (0.0, LED_Y, 0), "D2": (LED_X[0], LED_Y, 90), "D3": (LED_X[1], LED_Y, 90), "D4": (LED_X[2], LED_Y, 90), "D5": (LED_X[3], LED_Y, 90),
}


# Copper areas of the pack-current path on the outer face (6 A): net, outline, centre line. No other net's track or via
# may lie in them (tools/grouter.py: hard region with a spine).
AREAS = [
    ("BP", [(-13.0, -14.6), (-9.4, -14.6), (-9.4, -10.9), (-13.0, -10.9)], [(-11.2, -14.4), (-11.2, -11.1)], 1.9),
    ("BF", [(-12.4, -9.1), (-10.45, -9.1), (-10.45, -5.9), (-12.4, -5.9)], [(-11.4, -8.9), (-11.4, -6.1)], 1.1),
    ("VCC", [(-12.25, -5.3), (-9.75, -5.3), (-9.75, 2.1), (-12.25, 2.1)], [(-11.0, -5.1), (-11.0, 1.9)], 1.35),
    ("PACKP", [(-11.5, 2.65), (-9.85, 2.65), (-9.85, 6.2), (-11.5, 8.1), (-14.6, 8.1), (-14.6, 4.5), (-11.5, 4.0)],
     [(-10.7, 2.9), (-10.7, 5.6), (-13.0, 6.3)], 0.95),
    ("FUSE_H", [(-9.5, -10.9), (-4.7, -10.9), (-4.7, -9.7), (-9.5, -9.7)], [(-9.3, -10.3), (-4.9, -10.3)], 0.7),
    ("GND", [(10.3, -14.4), (12.2, -14.4), (12.2, -11.55), (10.3, -11.55)], [(11.25, -14.2), (11.25, -11.8)], 1.05),
    ("PACKN", [(10.3, -9.65), (12.0, -9.65), (14.6, -6.9), (14.6, -3.2), (11.8, -3.2), (11.8, -6.6), (10.3, -8.1)],
     [(11.15, -9.4), (11.15, -8.4), (13.2, -6.3), (13.2, -3.6)], 0.95),
]


def layout(pcb):
    """Outer face seen from outside the pack: X to the right, Y up, origin at the board centre."""
    pcb.outline_rect(W, H, r=1.0)
    pcb.bounds = (-W / 2 + 0.6, -H / 2 + 0.6, W / 2 - 0.6, H / 2 - 0.6)
    for ref, (x, y, rot) in FIXED.items():
        pcb.place(ref, x, y, rot=rot, ref_text=False)
    # the board's bottom and top edges sit in grooves of the pack shells at the middle of the board (fixing without screws)
    pcb.block("*", (-3.5, -20.0, 3.5, -18.2))
    pcb.block("*", (-3.5, 18.2, 3.5, 20.0))
    # nothing but the LEDs and the button under the light pipe
    pcb.block("F", (-14.6, LED_Y - 3.6, 14.6, LED_Y + 3.6))
    for _net, poly, _spine, _keep in AREAS:                    # no small parts on the pack-current copper
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        pcb.block("F", (min(xs) - 0.3, min(ys) - 0.3, max(xs) + 0.3, max(ys) + 0.3))
    # every track and via laid by hand below is recorded, so that no small part is placed on it
    track0 = pcb.track

    def track(net, pts, w=None, layer="F"):
        track0(net, pts, w, layer)
        q = [pcb.pt(p_) for p_ in pts]
        for a, b in zip(q, q[1:]):
            n_ = max(1, int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / 0.3))
            for i in range(n_ + 1):
                x, y = a[0] + (b[0] - a[0]) * i / n_, a[1] + (b[1] - a[1]) * i / n_
                pcb.block(layer, (x - 0.4, y - 0.4, x + 0.4, y + 0.4))
    pcb.track = track
    via0 = pcb.via

    def via(net, p_, *a_, **k_):
        via0(net, p_, *a_, **k_)
        x, y = pcb.pt(p_)
        pcb.block("*", (x - 0.75, y - 0.75, x + 0.75, y + 0.75))
    pcb.via = via
    # the fuse driver's ground: three vias beside its source pins into the ground plane on the inner face
    for k, y in enumerate((-11.4, -10.6, -9.8)):
        pcb.track("GND", [("Q3", k + 1), (-2.85, y)], 0.3)
        pcb.via("GND", (-2.85, y))
    for xy in ((12.95, -13.2), (12.95, -12.2)):                # and two at the B- end of the sense resistor (the tab pad has its own)
        pcb.via("GND", xy)
        pcb.track("GND", [xy, (12.0, xy[1])], 0.5)
    pcb.escape_ring("U1", 1.7)                                 # room for every pin of the gauge to get out
    pcb.escape_ring("U2", 0.7)
    # By hand: the gauge's pins to the parts at them, and the two sense lines from the taps on the sense resistor to their
    # filter. The SRP line changes face for 2 mm to pass under the SRN line (the pins and the taps are in opposite order).
    t = 0.15
    pcb.track("VCC", [("U1", 26), (-2.6, -1.0), (-3.0, -0.6), ("C7", 1)], t)
    pcb.track("PACK_S", [("U1", 27), (-2.9, -1.4), (-3.4, -1.9), ("R14", 2)], t)
    pcb.track("DSG", [("U1", 28), (-2.7, -1.8), (-3.35, -2.45), (-5.7, -2.45)], t)
    pcb.track("CHG", [("U1", 31), (-3.3, -3.0), (-3.4, -2.9), (-5.7, -2.9)], t)
    pcb.track("BAT", [("U1", 32), (-3.0, -3.4), (-3.4, -3.8), ("C6", 1)], t)
    pcb.track("BAT", [("C6", 1), ("R13", 2)], 0.2)
    pcb.track("PBI", [("U1", 1), ("C2", 1)], 0.2)
    pcb.track("VC2", [("U1", 2), ("U1", 4)], 0.2)
    pcb.track("SRP", [("U1", 8), (1.8, -7.6), (2.4, -8.2), ("R11", 2)], t)
    pcb.track("SRN", [("U1", 6), (1.0, -8.2), (1.98, -9.18), ("C5", 2), ("R12", 2)], t)
    pcb.track("LEDA", [("U1", 20), ("R21", 1)], t)
    pcb.track("LEDB", [("U1", 21), (0.2, 1.3), (-0.35, 1.85), ("R22", 1)], t)
    pcb.track("LEDC", [("U1", 22), (-0.2, 0.9), (-1.3, 2.0), ("R23", 1)], t)
    pcb.track("BAT_D", [("D1", 1), ("R13", 1)], 0.2)
    pcb.track("BP", [("D1", 2), (-8.55, -5.18), ("R10", 1)], 0.2)
    pcb.track("SMBC", [("U1", 19), (1.0, 1.2), (1.3, 1.5), (1.3, 3.6), (2.0, 4.3), ("R18", 1)], t)
    pcb.track("SMBD", [("U1", 18), (1.4, 0.9), (1.9, 1.4), (1.9, 2.6), (2.6, 3.3), ("R19", 1)], t)
    pcb.track("DISP", [("U1", 17), (1.8, 0.7)], t)
    pcb.track("SRN_K", [("R12", 1), (9.6, -9.2), ("NT2", 2)], 0.2)
    pcb.track("SRP_K", [("R11", 1), (5.3, -8.2)], 0.2)
    pcb.via("SRP_K", (5.3, -8.2))
    pcb.track("SRP_K", [(5.3, -8.2), (5.3, -10.2)], 0.2, "B")
    pcb.via("SRP_K", (5.3, -10.2))
    pcb.track("SRP_K", [(5.3, -10.2), (8.3, -10.2), ("NT1", 2)], 0.2)
    pcb.track, pcb.via = track0, via0
    free0 = pcb._free
    pcb._free = lambda side, rect, margin=0.5: free0(side, rect, margin)      # a track fits between any two small parts
    rest = [p["ref"] for p in pcb.model["parts"] if p["ref"] not in FIXED]
    rank = {"C": 0, "R": 1, "D": 2, "Q": 3, "T": 4}
    rest.sort(key=lambda r_: (rank.get(r_[0], 5), int("".join(ch for ch in r_ if ch.isdigit()) or 0)))
    failed = pcb.autoplace(rest, both_sides=False)
    if failed:
        print("not placed:", failed)
    return pcb


def route_plan(pcb):
    """What tools/grouter.py routes: the high-current paths are laid by hand in layout(); everything else is routed here."""
    full = [(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)]
    steps = [
        dict(op="fanout", length=0.35),
        dict(op="plane", net="GND", polys=[full], w=0.25, ep=True, maxlen=4.0),
        # every signal pin of the gauge (0.4 mm pitch) gets its way out first, as on the mainboard
        dict(op="escape", name="escape of the gauge", ring=2.0, layer_cost={"B": 2}, min_pads=12),
        dict(op="route", name="gate drive and sense", nets=["CHG_G", "DSG_G", "FUSE_G", "SRP", "SRN", "VC1", "VC2", "BAT", "BAT_D", "PBI",
                                                         "VDD2", "V1", "V2", "CD", "OV_OUT", "PACK_S", "Q4_G", "SRP_K", "SRN_K"], widths=[0.2, 0.15], hard=True),
        dict(op="rest", name="all other signals", widths=[0.2, 0.15]),
    ]
    return dict(plan=dict(layers=["F", "B"], widths=[0.15, 0.2, 0.3, 0.5, 1.0], steps=steps, rules=dict(clearance=0.15, via=0.6, drill=0.3)),
                regions=[dict(net=n_, side="F", poly=[list(q) for q in poly], hard=True, spine=[list(q) for q in sp], keep=k)
                         for n_, poly, sp, k in AREAS], cutouts=[], keepouts=[])


def finish(pcb):
    import pcbnew
    full = pcb.rect(-W / 2 + 0.4, -H / 2 + 0.4, W / 2 - 0.4, H / 2 - 0.4)
    for net, poly, _sp, _k in AREAS:
        pcb.zone(net, "F", poly, clearance=0.2, solid=True, priority=5)
    for ref in ("J1", "J2", "J4", "J5", "F1", "Q1", "Q2", "Q3", "R1", "U1", "U2"):
        pcb.solid(ref)
    pcb.zone("GND", "B", full, clearance=0.25)
    pcb.text("ST-602 A", 0, 17.4, 0.8, layer=pcbnew.F_SilkS)
