"""Wiring harness drawings and tables for the Star Tracker head (Phase 4).

One definition per harness; the script writes an SVG drawing for each, a README with the pin tables and a CSV
purchase list.  Run:  python3 harness.py      (plain Python, no extra packages)
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

COL = {"black": "#222", "red": "#d22", "blue": "#26c", "green": "#2a2", "yellow": "#db0", "white": "#eee", "orange": "#f80",
       "violet": "#84c", "grey": "#888", "brown": "#853"}

# D47 pinout, the same at both ends (cable is 1:1, pin 1 to pin 1)
GH15 = [(1, "A1", "motor phase A, start", "red"), (2, "A1", "second contact, same wire pair", "red"),
        (3, "A2", "motor phase A, end", "blue"), (4, "A2", "second contact", "blue"),
        (5, "GND", "ground, also the shield between motor and SPI wires", "black"),
        (6, "CS", "encoder chip select", "yellow"), (7, "SCK", "encoder SPI clock", "white"),
        (8, "MOSI", "encoder SPI data in", "orange"), (9, "MISO", "encoder SPI data out", "violet"),
        (10, "NTC", "motor thermistor", "grey"), (11, "+3V3", "encoder supply", "brown"),
        (12, "B1", "motor phase B, start", "green"), (13, "B1", "second contact", "green"),
        (14, "B2", "motor phase B, end", "black"), (15, "B2", "second contact", "black")]

TWIST_R, TWIST_DEG, TWIST_L = 1.4, 52.5, 82.0           # bundle radius, roll travel each way, free length in the tube
_g = TWIST_R * math.radians(TWIST_DEG) / TWIST_L
TWIST_STRETCH = TWIST_L * (math.sqrt(1 + _g * _g) - 1)

HARNESSES = [
    dict(id="ST-530-AZ", title="Azimuth cartridge harness", length=190, tol="+10 / 0",
         a=("Mainboard J7 (AZ)", "JST GHR-15V-S"), b=("Cartridge board J1, azimuth", "JST GHR-15V-S"), pins=GH15,
         wire="28 AWG, PVC (UL1571) or PTFE; 15 wires", route="mainboard, down the left wall, into the base under the azimuth cartridge",
         relief="cable tie to the anchor on the body floor 20 mm from each plug; no load on the plugs",
         notes=["Fixed parts at both ends: no twist allowance needed."]),
    dict(id="ST-530-ALT", title="Altitude cartridge harness", length=280, tol="+10 / 0",
         a=("Mainboard J8 (ALT)", "JST GHR-15V-S"), b=("Cartridge board J1, altitude", "JST GHR-15V-S"), pins=GH15,
         wire="28 AWG, PVC (UL1571) or PTFE; 15 wires", route="mainboard, up the tower, into the altitude cartridge cover",
         relief="cable tie at the tower entry and at the cartridge cover",
         notes=["A ready-made 305 mm lead set fits with 25 mm to spare."]),
    dict(id="ST-530-ROLL", title="Roll cartridge harness", length=680, tol="+15 / 0",
         a=("Mainboard J9 (ROLL)", "JST GHR-15V-S"), b=("Cartridge board J1, roll", "JST GHR-15V-S"), pins=GH15,
         wire="28 AWG PTFE (UL1213 / UL10064 class), 19-strand; 15 wires, outside diameter of the bundle about 2.8 mm",
         route="mainboard, up the tower, through the altitude encoder tube ST-208 (bore 6.5 mm), along the arm to the roll cartridge",
         relief="cable tie on the tower side of the tube and on the arm side, 90 mm apart, so only the 82 mm inside the tube twists",
         notes=[f"Twist: the bundle turns +/-{TWIST_DEG} deg over {TWIST_L:.0f} mm. Strand stretch = L (sqrt(1 + (r theta / L)^2) - 1) = "
                f"{TWIST_STRETCH:.3f} mm: negligible, but lay the 15 wires straight (not plaited) inside the tube and leave 5 mm of slack.",
                "PTFE insulation because the bundle slides on the tube wall at every altitude move; PVC would wear and stick.",
                "Longer than any ready-made lead (305 mm), so this one is crimped by hand or ordered from a cable maker."]),
    dict(id="ST-531-PWR", title="Battery power lead", length=90, tol="+/-5",
         a=("Mainboard J1 pads (+ and -)", "soldered; in-line XT30U-F 40 mm from the board"),
         b=("Head-side battery blade connector ST-609, P+ and P-", "soldered; XT30U-M on this half"),
         pins=[(1, "VBAT_IN", "pack +, pad marked +", "red"), (2, "GND", "pack -", "black")],
         wire="18 AWG silicone (UL3135), red and black", route="battery bay roof to the lower right corner of the mainboard",
         relief="heat-shrink over both solder joints; the XT30 pair lets the mainboard come out without unsoldering",
         notes=["Carries up to 6 A (blade connector limit). 18 AWG: 21 mohm per metre, 0.011 V drop over 2 x 90 mm at 6 A."]),
    dict(id="ST-531-SMB", title="Battery data lead", length=90, tol="+/-5",
         a=("Mainboard J2", "JST GHR-04V-S"), b=("Head-side battery blade connector ST-609, signal blades", "soldered"),
         pins=[(1, "SMBC", "pack SMBus clock", "yellow"), (2, "SMBD", "pack SMBus data", "white"),
               (3, "PRES", "pack-present, pulled to ground inside the pack", "grey"), (4, "GND", "signal ground", "black")],
         wire="28 AWG PVC, 4 wires", route="alongside the power lead", relief="tied to the power lead",
         notes=["Half of a ready-made 4-way GH lead: cut in two and solder the free ends to the blade connector."]),
    dict(id="ST-532", title="Shutter port lead", length=60, tol="+/-5",
         a=("Mainboard J12", "JST GHR-03V-S"), b=("2.5 mm stereo panel jack in the bezel", "soldered"),
         pins=[(1, "SHUTTER", "jack tip", "red"), (2, "FOCUS", "jack ring", "white"), (3, "COMMON", "jack sleeve", "black")],
         wire="28 AWG PVC, 3 wires", route="mainboard cut-out to the jack nut in the bezel", relief="heat-shrink on the jack tags",
         notes=["The jack is isolated from the head's ground by the two optocouplers; do not join COMMON to the chassis."]),
]

MOTOR_LEADS = [
    ("Altitude and roll: 17HE15-1504S (38 mm)", [("1", "A1", "black (A+)"), ("2", "A2", "blue (A-)"), ("3", "B1", "green (B+)"), ("4", "B2", "red (B-)")]),
    ("Azimuth: 17HS19-2004S1 (48 mm)", [("1", "A1", "black (A+)"), ("2", "A2", "green (A-)"), ("3", "B1", "red (B+)"), ("4", "B2", "blue (B-)")]),
]

PURCHASE = [
    ("JST GHR-15V-S housing", 6, "2 per cartridge harness", "JST", "GHR-15V-S"),
    ("JST GH pre-crimped lead, 28 AWG, 305 mm, socket to socket", 30, "azimuth and altitude harness: 15 each", "JST", "AGHGH28K305"),
    ("JST GH crimp contact (for the roll harness)", 40, "30 needed + spares", "JST", "SSHL-002T-P0.2"),
    ("PTFE hook-up wire 28 AWG, 19-strand, 10 colours", 12, "metres; roll harness 15 x 0.68 m", "generic", "UL1213 28 AWG"),
    ("JST GHR-04V-S lead, 4-way, ready-made 150 mm", 1, "battery data lead (cut in two)", "JST", "GHR-04V-S"),
    ("JST GHR-03V-S lead, 3-way, ready-made 150 mm", 1, "shutter lead (cut in two)", "JST", "GHR-03V-S"),
    ("JST PHR-4 housing", 3, "motor plug", "JST", "PHR-4"),
    ("JST PH crimp contact", 20, "12 needed + spares", "JST", "SPH-002T-P0.5S"),
    ("XT30U-F and XT30U-M pair", 1, "battery power lead", "Amass", "XT30U"),
    ("Silicone wire 18 AWG, red and black", 1, "0.25 m of each", "generic", "UL3135 18 AWG"),
    ("NTC bead thermistor 10 k, B 3950, 1 %, 2 leads 100 mm", 3, "one per motor (D46)", "generic", "MF52-103 3950"),
    ("2.5 mm stereo panel jack, threaded nose", 1, "shutter port", "CUI / generic", "PJ-2.5 panel"),
    ("Cable ties 2.5 x 100 mm, heat-shrink 2 / 4 / 6 mm, Kapton tape", 1, "set", "generic", "-"),
]


def svg(h):
    pins = h["pins"]
    n = len(pins)
    row, top = 16, 100
    H = top + n * row + 110
    W = 980
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="20" y="28" font-size="18" font-weight="bold">{h["id"]}  {h["title"]}</text>',
         f'<text x="20" y="46">Length {h["length"]} mm ({h["tol"]}), plug face to plug face.</text>',
         f'<text x="20" y="61" font-size="11">Wire: {h["wire"]}.</text>',
         f'<rect x="20" y="{top - 22}" width="200" height="{n * row + 30}" fill="#f4f4f4" stroke="#333"/>',
         f'<rect x="{W - 220}" y="{top - 22}" width="200" height="{n * row + 30}" fill="#f4f4f4" stroke="#333"/>',
         f'<text x="26" y="{top - 8}" font-weight="bold">{h["a"][0]}</text>',
         f'<text x="{W - 214}" y="{top - 8}" font-weight="bold">{h["b"][0][:34]}</text>']
    for i, (num, sig, _d, colour) in enumerate(pins):
        y = top + 10 + i * row
        c = COL[colour]
        o.append(f'<text x="30" y="{y + 4}">{num}</text><text x="60" y="{y + 4}">{sig}</text>')
        o.append(f'<text x="{W - 210}" y="{y + 4}">{num}</text><text x="{W - 180}" y="{y + 4}">{sig}</text>')
        o.append(f'<line x1="220" y1="{y}" x2="{W - 220}" y2="{y}" stroke="#000" stroke-width="5"/>')
        o.append(f'<line x1="220" y1="{y}" x2="{W - 220}" y2="{y}" stroke="{c}" stroke-width="3.4"/>')
        o.append(f'<text x="{W / 2 - 20}" y="{y - 4}" font-size="9" fill="#555">{colour}</text>')
    yb = top + n * row + 26
    o.append(f'<line x1="220" y1="{yb}" x2="{W - 220}" y2="{yb}" stroke="#333"/>')
    o.append(f'<line x1="220" y1="{yb - 6}" x2="220" y2="{yb + 6}" stroke="#333"/><line x1="{W - 220}" y1="{yb - 6}" x2="{W - 220}" y2="{yb + 6}" stroke="#333"/>')
    o.append(f'<text x="{W / 2 - 40}" y="{yb + 16}">{h["length"]} mm {h["tol"]}</text>')
    o.append(f'<text x="20" y="{yb + 2}" font-size="11">{h["a"][1]}</text>')
    o.append(f'<text x="{W - 220}" y="{yb + 2}" font-size="11">{h["b"][1][:38]}</text>')
    o.append(f'<text x="20" y="{yb + 40}">Route: {h["route"]}.</text>')
    o.append(f'<text x="20" y="{yb + 58}">Strain relief: {h["relief"]}.</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    md = ["# Wiring harnesses", "",
          "Generated by `harness.py`; edit the data there, not this file. Lengths of the three cartridge harnesses are measured",
          "along the cable route in the Phase 3 CAD model; the three short leads are estimates to confirm on the first build.",
          "Every plug is drawn with pin 1 at the top. Cartridge harnesses are wired 1:1 (pin 1 to pin 1).", ""]
    for h in HARNESSES:
        open(os.path.join(HERE, h["id"] + ".svg"), "w").write(svg(h))
        md += [f"## {h['id']}  {h['title']}", "", f"![{h['id']}]({h['id']}.svg)", "",
               f"- **Length:** {h['length']} mm ({h['tol']})", f"- **Wire:** {h['wire']}",
               f"- **End A:** {h['a'][0]}: {h['a'][1]}", f"- **End B:** {h['b'][0]}: {h['b'][1]}",
               f"- **Route:** {h['route']}", f"- **Strain relief:** {h['relief']}"]
        md += [f"- {n}" for n in h["notes"]]
        md += ["", "| Pin (both ends) | Signal | What it does | Wire colour |", "|---|---|---|---|"]
        md += [f"| {p} | {s} | {d} | {c} |" for (p, s, d, c) in h["pins"]]
        md.append("")
    md += ["## Motor leads (JST-PH 4-way to cartridge board J2)", "",
           "Cut the motor's own leads to 80 mm, crimp JST SPH-002T-P0.5S contacts and push them into a PHR-4 housing in this order.",
           "The two motor types have different colours for the same phase, so follow the table for the motor in hand.", ""]
    for name, rows in MOTOR_LEADS:
        md += [f"**{name}**", "", "| J2 pin | Phase | Motor lead colour |", "|---|---|---|"]
        md += [f"| {p} | {s} | {c} |" for (p, s, c) in rows] + [""]
    md += ["If an axis runs backwards, swap nothing: direction is a firmware setting per axis.", "",
           "## Motor thermistor (D46)", "",
           "10 k B3950 bead on two 100 mm leads. Glue the bead to the motor body next to the lead exit with thermal epoxy, run the",
           "leads with the motor leads and solder them to the two pads marked NTC on the underside of the cartridge board.",
           "Polarity does not matter.", "",
           "## Purchase list", "", "| Item | Qty | Use | Maker | Part |", "|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} | {e} |" for (a, b, c, d, e) in PURCHASE]
    open(os.path.join(HERE, "README.md"), "w").write("\n".join(md) + "\n")
    with open(os.path.join(HERE, "harness-purchase-list.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "qty", "use", "maker", "part"])
        w.writerows(PURCHASE)
    print("wrote", len(HARNESSES), "drawings; twist stretch", round(TWIST_STRETCH, 4), "mm")


if __name__ == "__main__":
    main()
