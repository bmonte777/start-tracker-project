"""Block diagram and power tree of the head's electronics, drawn from the schematic's own names.

Run:  python3 tools/diagrams.py        -> docs/img/04-block-diagram.{svg,png}, docs/img/04-power-tree.{svg,png}
Needs matplotlib only. The boxes and arrows are listed below as data; change them there when the schematic changes.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.abspath(os.path.join(HERE, "..", "..", "..", "docs", "img"))
INK, MUTED = "#1f2933", "#52606d"
FILL = {"power": "#fde8d0", "logic": "#dbeafe", "motion": "#dcfce7", "io": "#f3e8ff", "ext": "#f1f5f9"}
EDGE = {"power": "#c2410c", "logic": "#1d4ed8", "motion": "#15803d", "io": "#7e22ce", "ext": "#64748b"}


def draw(name, size, boxes, arrows, title, legend):
    fig, ax = plt.subplots(figsize=size, dpi=150)
    ax.set_xlim(0, size[0] * 10)
    ax.set_ylim(0, size[1] * 10)
    ax.axis("off")
    pos = {}
    for key, x, y, w, h, kind, head, sub in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2", fc=FILL[kind], ec=EDGE[kind], lw=1.2))
        ax.text(x + w / 2, y + h - 2.3, head, ha="center", va="top", fontsize=8.2, color=INK, weight="bold")
        if sub:
            ax.text(x + w / 2, y + h - 5.6, sub, ha="center", va="top", fontsize=6.6, color=MUTED, linespacing=1.25)
        pos[key] = (x, y, w, h)

    def anchor(key, side, t=0.5):
        x, y, w, h = pos[key]
        return {"l": (x - 0.2, y + h * t), "r": (x + w + 0.2, y + h * t), "t": (x + w * t, y + h + 0.2), "b": (x + w * t, y - 0.2)}[side]

    for a, sa, ta, b, sb, tb, label, kind, both in arrows:
        p, q = anchor(a, sa, ta), anchor(b, sb, tb)
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=9, lw=1.3 if kind == "power" else 0.9,
                                     color=EDGE[kind], shrinkA=0, shrinkB=0))
        if label:
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            ax.text(mx, my + 0.9, label, ha="center", va="bottom", fontsize=6.2, color=INK,
                    bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))
    ax.text(1, size[1] * 10 - 1.5, title, fontsize=10.5, color=INK, weight="bold", va="top")
    x = 1
    for kind, text in legend:
        ax.add_patch(FancyBboxPatch((x, 1.2), 3, 2, boxstyle="round,pad=0.1,rounding_size=0.5", fc=FILL[kind], ec=EDGE[kind], lw=1))
        ax.text(x + 4, 2.2, text, fontsize=6.6, color=MUTED, va="center")
        x += 6 + len(text) * 1.02
    os.makedirs(IMG, exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(os.path.join(IMG, f"{name}.{ext}"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def block():
    B = [  # key, x, y, w, h, kind, heading, text
        ("pack", 2, 62, 24, 14, "ext", "Battery pack", "2 cells in series, 6 A limit\nST-602: BQ40Z50-R2 gauge,\nBQ294700, fuse, charge LEDs"),
        ("usba", 2, 42, 24, 12, "ext", "USB-C port A (J3)", "power in or out, USB data"),
        ("usbb", 2, 22, 24, 12, "ext", "USB-C port B (J4)", "27 W to the camera"),
        ("chg", 34, 54, 28, 22, "power", "Power in", "Q1 reverse-polarity FET\nTPS25751D PD controller (U3)\nBQ25792 charger and power path (U2)\n-> system rail VSYS"),
        ("pb", 34, 22, 28, 22, "power", "Port B supply", "TPS25752A PD controller (U6)\nTPS55288 buck-boost (U7), 5 to 9 V\nsense resistor R23, switch Q2-Q3"),
        ("rails", 70, 54, 26, 22, "power", "Rails", "TPS62932: 3.3 V (U10)\nTPS563201: 5 V (U11)\nQ6 + TPS61288: motor rail\n10 V or 16 V (U12)"),
        ("esp", 70, 24, 26, 22, "logic", "ESP32-S3-WROOM-1 (U13)", "Wi-Fi, BLE, USB, apps\nI2C: display, sensors, clock,\nboth PD controllers\nprograms the RP2354A over SWD"),
        ("rp", 104, 24, 26, 22, "motion", "RP2354A (U14)", "three step trains (PIO)\nencoder SPI, driver UART\ntemperatures (ADC)"),
        ("drv", 104, 54, 26, 22, "motion", "3 x TMC2209 (U15, U17, U19)", "one UART, addresses 0, 1, 2\n0.15 ohm sense resistors"),
        ("cart", 138, 40, 24, 36, "ext", "3 cartridges (J7, J8, J9)", "azimuth, altitude, roll\n\nstepper motor\nMT6835 encoder on ST-520\nNTC thermistor\n\n15-way JST-GH harness"),
        ("ui", 70, 4, 26, 14, "io", "User interface", "OLED 1.3 in (I2C), 4 buttons,\n3 status LEDs, shutter port\n(two opto-couplers)"),
        ("sens", 104, 4, 26, 14, "io", "Sensors", "LSM6DSV, MMC5983MA,\nRV-3028 clock + cell,\nMAX-M10S GNSS (UART, PPS)"),
    ]
    A = [  # from, side, t, to, side, t, label, kind, both ways
        ("pack", "r", 0.6, "chg", "l", 0.72, "pack + / -, SMBus, presence", "power", True),
        ("usba", "r", 0.5, "chg", "l", 0.2, "VBUS 5 to 20 V, CC", "power", True),
        ("pb", "l", 0.5, "usbb", "r", 0.5, "VBUS 5 / 9 V, CC", "power", False),
        ("chg", "b", 0.5, "pb", "t", 0.5, "VSYS", "power", False),
        ("chg", "r", 0.6, "rails", "l", 0.6, "VSYS", "power", False),
        ("rails", "r", 0.7, "drv", "l", 0.7, "motor rail", "power", False),
        ("rails", "b", 0.5, "esp", "t", 0.5, "3.3 V", "power", False),
        ("usba", "r", 0.15, "esp", "l", 0.85, "USB D+ / D-", "logic", True),
        ("esp", "l", 0.4, "pb", "r", 0.4, "I2C, interrupt, enable", "logic", True),
        ("esp", "r", 0.5, "rp", "l", 0.5, "UART link, sync, SWD", "logic", True),
        ("rp", "t", 0.5, "drv", "b", 0.5, "step, dir, UART", "motion", False),
        ("drv", "r", 0.6, "cart", "l", 0.75, "motor phases", "motion", False),
        ("cart", "l", 0.25, "rp", "r", 0.75, "encoder SPI, NTC", "motion", True),
        ("esp", "b", 0.5, "ui", "t", 0.5, "", "io", True),
        ("esp", "b", 0.9, "sens", "t", 0.2, "I2C, UART", "io", True),
    ]
    draw("04-block-diagram", (16.4, 8.0), B, A, "Star tracker head: electronics block diagram (mainboard ST-501, cartridge boards ST-520, battery board ST-602)",
         [("power", "power"), ("logic", "processor and data"), ("motion", "motion"), ("io", "sensors and user interface"), ("ext", "outside the mainboard")])


def power_tree():
    B = [
        ("pack", 2, 44, 24, 14, "ext", "Battery pack, 2 cells", "6.0 to 8.4 V, 6 A limit\nfuse, gauge and FETs on ST-602"),
        ("usba", 2, 20, 24, 14, "ext", "USB-C port A", "5 to 20 V in (charging)\nor 5 V out"),
        ("q1", 32, 46, 18, 10, "power", "Q1", "reverse polarity"),
        ("pd", 32, 22, 18, 10, "power", "TPS25751D", "port A switch"),
        ("chg", 56, 30, 22, 22, "power", "BQ25792", "buck-boost charger,\n750 kHz, power path:\nbattery <-> system rail"),
        ("sys", 84, 36, 14, 10, "power", "VSYS", "system rail"),
        ("b33", 106, 62, 24, 10, "power", "TPS62932", "3.3 V logic rail, always on"),
        ("b5", 106, 46, 24, 10, "power", "TPS563201", "5 V, 3 A, always on"),
        ("pb", 106, 28, 24, 12, "power", "TPS55288", "port B, 5 to 9 V, 3 A (27 W)\nI2C from the port B controller"),
        ("mot", 106, 8, 24, 14, "power", "Q6 + TPS61288", "motor rail: off until the\nfirmware turns it on;\n10 V or 16 V"),
        ("l33", 138, 62, 24, 10, "logic", "Logic", "ESP32-S3, RP2354A (own 1.1 V\nregulator), sensors, encoders"),
        ("l5", 138, 46, 24, 10, "ext", "PP5V of both PD controllers", "5 V out on port A and B"),
        ("lpb", 138, 28, 24, 12, "ext", "USB-C port B", "through R23 (10 mohm) and\nthe switch Q2-Q3 to the camera"),
        ("lmot", 138, 8, 24, 14, "motion", "3 x TMC2209", "stepper motors of the\nthree cartridges"),
    ]
    A = [
        ("pack", "r", 0.5, "q1", "l", 0.5, "VBAT_IN", "power", True),
        ("q1", "r", 0.5, "chg", "l", 0.85, "VBAT (inner layer 3)", "power", True),
        ("usba", "r", 0.5, "pd", "l", 0.5, "VBUS_A", "power", True),
        ("pd", "r", 0.5, "chg", "l", 0.15, "VBUS_CHG", "power", True),
        ("chg", "r", 0.5, "sys", "l", 0.5, "", "power", False),
        ("sys", "r", 0.9, "b33", "l", 0.5, "", "power", False),
        ("sys", "r", 0.7, "b5", "l", 0.5, "", "power", False),
        ("sys", "r", 0.3, "pb", "l", 0.5, "", "power", False),
        ("sys", "r", 0.1, "mot", "l", 0.5, "VM_IN after Q6", "power", False),
        ("b33", "r", 0.5, "l33", "l", 0.5, "+3V3", "power", False),
        ("b5", "r", 0.5, "l5", "l", 0.5, "+5V", "power", False),
        ("pb", "r", 0.5, "lpb", "l", 0.5, "VPB_RAW, VPB, VBUS_B", "power", False),
        ("mot", "r", 0.5, "lmot", "l", 0.5, "VMOT", "power", False),
    ]
    draw("04-power-tree", (16.6, 7.6), B, A, "Star tracker head: power tree (net names as in the schematic)",
         [("power", "converters and switches"), ("ext", "sources and loads outside the board"), ("logic", "logic"), ("motion", "motion")])


if __name__ == "__main__":
    block()
    power_tree()
