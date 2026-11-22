"""ST-520 cartridge (encoder) board: schematic and layout as code.
Rebuild: tools/layout.py cartridge-board (or the GitHub workflow "Phase 4 electronics").

One board per axis, round 30 mm, two M3 holes on PCD 23. MT6835 on the underside, 2.0 mm above the magnet face.
J1 is the single plug to the head (D13); J2 takes the motor lead and stays inside the cartridge.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from schgen import Design, NC   # noqa: E402

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
PCB_ARGS = dict(layers=2, default_track=0.2, default_via=(0.6, 0.3), clearance=0.15)

# J1 pinout, the same at both ends of the cartridge harness (pin 1 is marked on the housing).
# Phase A on one end, phase B on the other, signals in the middle with ground and 3.3 V next to the phases.
J1_PINS = {1: "M_A1", 2: "M_A1", 3: "M_A2", 4: "M_A2", 5: "GND", 6: "ENC_CS", 7: "ENC_SCK", 8: "ENC_MOSI", 9: "ENC_MISO",
           10: "NTC", 11: "+3V3", 12: "M_B1", 13: "M_B1", 14: "M_B2", 15: "M_B2"}


def build():
    d = Design("st-520", "ST-520 cartridge board", rev="A", sym_dirs=[LIB])
    s = d.sheet("main", "Encoder, motor pass-through, thermistor", paper="A4")

    s.note(20, 30, "J1: plug to the head, JST-GH 15-way.\nMotor phases use two contacts each (1 A per contact).", 1.5)
    pins = dict(J1_PINS)
    pins["MP"] = "GND"
    s.part("Connector_Generic_MountingPin:Conn_01x15_MountingPin", "J1", "BM15B-GHS-TBT",
           "Connector_JST:JST_GH_BM15B-GHS-TBT_1x15-1MP_P1.25mm_Vertical", pins, x=40, y=60, LCSC="C265111", MPN="BM15B-GHS-TBT(LF)(SN)")

    s.note(20, 118, "J2: motor lead, JST-PH 4-way. Wire by phase, not by colour:\nthe 38 mm and 48 mm motors use different colours (D32).", 1.5)
    s.part("Connector_Generic_MountingPin:Conn_01x04_MountingPin", "J2", "B4B-PH-SM4-TB",
           "Connector_JST:JST_PH_B4B-PH-SM4-TB_1x04-1MP_P2.00mm_Vertical",
           {1: "M_A1", 2: "M_A2", 3: "M_B1", 4: "M_B2", "MP": "GND"}, x=40, y=132, LCSC="C160260", MPN="B4B-PH-SM4-TB(LF)(SN)")

    s.note(95, 34, "U1: MT6835 21-bit encoder, on the underside at the board centre. SPI mode 3.\nTEST and TEST_EN stay open (factory pins).\n"
                   "CAL_EN: bridge TP7 to TP1 (3V3) to run self-calibration.", 1.5)
    s.part("ST:MT6835GT", "U1", "MT6835GT-STD", None,
           {"VDD": "+3V3", "VSS": "GND", "CSN": "ENC_CS", "SCK": "ENC_SCK", "MOSI": "ENC_MOSI", "MISO": "MISO_U", "CAL_EN": "CAL_EN",
            "A": NC, "B": NC, "Z": NC, "U": NC, "V": NC, "W": NC, "OUT": "ENC_PWM", "TEST": NC, "TEST_EN": NC},
           x=135, y=62, LCSC="C2984637", MPN="MT6835GT-STD")
    s.lane(105, 92, cols=3)
    s.C("C1", "100n", "+3V3", "GND", LCSC="C1525")
    s.C("C2", "1u", "+3V3", "GND", LCSC="C52923")
    s.C("C3", "10u", "+3V3", "GND", pkg="C0603", LCSC="C19702")
    s.R("R1", "33R", "MISO_U", "ENC_MISO", LCSC="C25105")
    s.R("R2", "10k", "+3V3", "ENC_CS", LCSC="C25744")
    s.R("R3", "100k", "CAL_EN", "GND", LCSC="C25741")

    s.note(95, 124, "Motor thermistor: 10 k B3950 bead on two wires, taped to the motor case\nand soldered to TH1. "
                    "RT1 (same value, on the board) is fitted only if no bead is used.", 1.5)
    s.part("Connector_Generic:Conn_01x02", "TH1", "NTC 10k bead", "ST:WirePads_1x02_P2.0mm_1.5x2.4mm", {1: "NTC", 2: "GND"}, x=110, y=136)
    s.part("Device:Thermistor_NTC", "RT1", "10k B3950", "Resistor_SMD:R_0603_1608Metric", {1: "NTC", 2: "GND"}, x=150, y=136, rot=90, dnp=True,
           LCSC="C13564")

    s.note(200, 24, "Test points", 1.5)
    s.lane(205, 30, cols=1, dy=7.62)
    for i, net in enumerate(["+3V3", "GND", "ENC_CS", "ENC_SCK", "ENC_MISO", "ENC_MOSI", "CAL_EN", "ENC_PWM", "NTC"]):
        s.tp(f"TP{i + 1}", net)
    s.note(200, 110, "Mounting: 2 x M3 on PCD 23", 1.5)
    s.part("Mechanical:MountingHole", "H1", "M3", "ST:MountingHole_3.2mm_M3_ISO7380", {}, x=210, y=120)
    s.part("Mechanical:MountingHole", "H2", "M3", "ST:MountingHole_3.2mm_M3_ISO7380", {}, x=230, y=120)
    s.lane(205, 140, cols=2, dx=25.4)
    s.flag("+3V3")
    s.flag("GND")
    return d


def layout(pcb):
    """Top view, X right, Y up, origin at the board centre (the encoder axis)."""
    pcb.outline_circle(15.0)
    # connectors and holes at the Phase 3 positions (J1 0.3 mm outward so its pads clear the screw heads)
    pcb.place("J1", 0, 6.3, ref_text=False)
    pcb.place("J2", 0, -9.0, ref_text=False)
    pcb.place("H1", -11.5, 0, ref_text=False)
    pcb.place("H2", 11.5, 0, ref_text=False)
    # encoder on the underside, exactly on the axis: VDD (pin 9) toward J1 pin 11, SPI pins toward J1 pins 6-9
    pcb.place("U1", 0, 0, rot=180, side="B", ref_text=False)
    pcb.place("C1", 5.3, 2.3, rot=90, side="B", ref_text=False)
    pcb.place("C2", 6.4, 2.3, rot=90, side="B", ref_text=False)
    pcb.place("C3", 7.6, 2.0, rot=90, side="B", ref_text=False)
    pcb.place("R2", -5.7, 3.2, side="B", ref_text=False)
    pcb.place("R3", -5.3, -0.35, side="B", ref_text=False)
    # top side
    pcb.place("R1", 1.25, 1.75, rot=90, ref_text=False)
    pcb.place("TH1", 4.4, -1.0, ref_text=False)
    pcb.place("RT1", 4.4, -3.3, ref_text=False)
    tps = [(x, y) for y in (1.05, -1.05, -3.15) for x in (-5.1, -2.95, -0.8)]
    for i, (x, y) in enumerate(tps):
        pcb.place(f"TP{i + 1}", x, y, ref_text=False)
    pcb.solid("U1", 12)
    pcb.solid("J1", 5, "MP")
    pcb.solid("J2", "MP")
    pcb.solid("TH1", 2)
    for c in ("C1", "C2", "C3", "R3", "RT1"):
        pcb.solid(c)

    # motor phases: each pair kept together, down the two sides, at least 4 mm from the encoder axis
    w = 0.6
    for sgn, outer, inner, p_out, p_in in ((-1, "M_A1", "M_A2", ("1", "2", "1"), ("3", "4", "2")),
                                           (1, "M_B2", "M_B1", ("15", "14", "4"), ("13", "12", "3"))):
        a, b, jp = p_out
        pcb.track(outer, [("J1", a), ("J1", b)], 0.4)
        pcb.track(outer, [("J1", a), (sgn * 8.75, 3.2), (sgn * 8.2, 2.65), (sgn * 8.2, -4.35), (sgn * 7.3, -5.25), (sgn * 3.6, -5.25),
                          (sgn * 3.0, -5.85), ("J2", jp)], w)
        a, b, jp = p_in
        pcb.track(inner, [("J1", a), ("J1", b)], 0.4)
        pcb.track(inner, [("J1", a), (sgn * 6.25, 3.3), (sgn * 6.9, 2.65), (sgn * 6.9, -3.5), (sgn * 6.0, -4.4), (sgn * 1.6, -4.4),
                          (sgn * 1.0, -5.0), ("J2", jp)], w)

    # SPI and supply by hand: straight down from J1, through to the underside, into the chip from the inside of its pad row
    t = 0.2
    pcb.track("ENC_SCK", [("J1", 7), (-1.25, 2.75)], t)
    pcb.via("ENC_SCK", (-1.25, 2.75))
    pcb.track("ENC_SCK", [(-1.25, 2.75), (-1.25, 2.0), (-1.625, 1.625), ("U1", 7)], t, "B")
    pcb.track("ENC_MOSI", [("J1", 8), (0, 2.75)], t)
    pcb.via("ENC_MOSI", (0, 2.75))
    pcb.track("ENC_MOSI", [(0, 2.75), (0, 1.9), (-0.925, 0.975), ("U1", 6)], t, "B")
    pcb.track("ENC_MISO", [("J1", 9), ("R1", 2)], t)
    pcb.track("MISO_U", [("R1", 1), (1.25, 0.325)], t)
    pcb.via("MISO_U", (1.25, 0.325))
    pcb.track("MISO_U", [(1.25, 0.325), ("U1", 5)], t, "B")
    pcb.track("ENC_CS", [("J1", 6), (-2.5, 3.1), (-3.1, 2.5), (-4.6, 2.5)], t)
    pcb.via("ENC_CS", (-4.6, 2.5))
    pcb.track("ENC_CS", [(-4.6, 2.5), (-4.375, 2.275), ("U1", 8)], t, "B")
    pcb.track("ENC_CS", [(-4.6, 2.5), (-5.0, 2.1), (-6.21, 2.1), ("R2", 2)], t, "B")
    pcb.track("+3V3", [("J1", 11), (3.75, 3.35), (4.2, 2.9)], 0.3)
    pcb.via("+3V3", (4.2, 2.9))
    pcb.track("+3V3", [(4.2, 2.9), (4.2, 2.5), (3.975, 2.275), ("U1", 9)], 0.3, "B")
    pcb.track("+3V3", [(4.2, 2.9), ("C1", 1), ("C2", 1), ("C3", 1)], 0.3, "B")
    pcb.track("+3V3", [(4.2, 2.9), (3.65, 3.45), (-4.94, 3.45), ("R2", 1)], t, "B")
    pcb.track("CAL_EN", [("R3", 1), ("U1", 4)], t, "B")
    pcb.track("GND", [("U1", 12), (4.4, 0.325)], 0.25, "B")

    # ground on both sides, stitched; no copper under the two screw heads
    ring = [(14.6 * math.cos(math.radians(a)), 14.6 * math.sin(math.radians(a))) for a in range(0, 360, 5)]
    for hx in (-11.5, 11.5):
        k = [(hx + 3.0 * math.cos(math.radians(a)), 3.0 * math.sin(math.radians(a))) for a in range(0, 360, 15)]
        pcb.keepout(["F", "B"], k)
    for v in ((0.6, -2.2), (0, -5.6), (-12.3, 4.6), (12.3, 4.6), (-10.6, -6.6), (10.6, -6.6), (0, -13.6), (0, 9.9), (-8.0, -8.5), (8.0, -8.5)):
        pcb.via("GND", v)
    return pcb


def finish(pcb):
    """After the autorouter: ground pours on both sides and the silkscreen text."""
    import pcbnew
    ring = [(14.6 * math.cos(math.radians(a)), 14.6 * math.sin(math.radians(a))) for a in range(0, 360, 5)]
    pcb.zone("GND", "F", ring)
    pcb.zone("GND", "B", ring)
    pcb.text("ST-520 A", 0, 7.0, 0.8, layer=pcbnew.B_SilkS)
    pcb.text("NTC", 7.5, -1.0, 0.8, rot=90)
