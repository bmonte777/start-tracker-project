"""Project footprint library ST.pretty (footprints KiCad 9 does not ship). Run: python3 stfp.py"""
import os

from kisx import Q, dump


def _prop(key, val, y, layer, hide=False):
    p = ["property", Q(key), Q(val), ["at", 0, y, 0], ["layer", Q(layer)]]
    if hide:
        p.append(["hide", "yes"])
    p.append(["effects", ["font", ["size", 0.8, 0.8], ["thickness", 0.12]]])
    return p


def footprint(name, descr, pads, courtyard, fab=None, silk=(), smd=True, model=None):
    """pads: (num, x, y, w, h, kind) with kind 'smd' or 'smd_nopaste'; coordinates in mm, Y down (KiCad)."""
    circle = None
    if courtyard[0] == "circle":
        circle = courtyard[1]
        courtyard = (-circle, -circle, circle, circle)
    x0, y0, x1, y1 = courtyard
    fp = ["footprint", Q(name), ["version", 20241229], ["generator", Q("st_stfp")], ["generator_version", Q("9.0")], ["layer", Q("F.Cu")],
          ["descr", Q(descr)], _prop("Reference", "REF**", y0 - 0.9, "F.SilkS"), _prop("Value", name, y1 + 0.9, "F.Fab"),
          _prop("Datasheet", "", 0, "F.Fab", True), _prop("Description", descr, 0, "F.Fab", True), ["attr", "smd"] if smd else ["attr", "exclude_from_pos_files", "exclude_from_bom"],
          (["fp_circle", ["center", 0, 0], ["end", circle, 0], ["stroke", ["width", 0.05], ["type", "solid"]], ["fill", "no"], ["layer", Q("F.CrtYd")]]
           if circle else
           ["fp_rect", ["start", x0, y0], ["end", x1, y1], ["stroke", ["width", 0.05], ["type", "solid"]], ["fill", "no"], ["layer", Q("F.CrtYd")]])]
    if fab:
        fp.append(["fp_rect", ["start", fab[0], fab[1]], ["end", fab[2], fab[3]], ["stroke", ["width", 0.1], ["type", "solid"]], ["fill", "no"],
                   ["layer", Q("F.Fab")]])
    for (a, b, c, d) in silk:
        fp.append(["fp_line", ["start", a, b], ["end", c, d], ["stroke", ["width", 0.12], ["type", "solid"]], ["layer", Q("F.SilkS")]])
    for (num, x, y, w, h, kind) in pads:
        if kind == "npth":
            fp.append(["pad", Q(""), "np_thru_hole", "circle", ["at", x, y], ["size", w, w], ["drill", w], ["layers", Q("*.Cu"), Q("*.Mask")]])
            continue
        layers = ["layers", Q("F.Cu"), Q("F.Mask")] + ([] if kind == "smd_nopaste" else [Q("F.Paste")])
        fp.append(["pad", Q(str(num)), "smd", "roundrect", ["at", x, y], ["size", w, h], layers, ["roundrect_rratio", 0.2]])
    if model:
        fp.append(["model", Q(model), ["offset", ["xyz", 0, 0, 0]], ["scale", ["xyz", 1, 1, 1]], ["rotate", ["xyz", 0, 0, 0]]])
    fp.append(["embedded_fonts", "no"])
    return name, dump(fp) + "\n"


FPS = [
    footprint("MountingHole_3.2mm_M3_ISO7380", "M3 clearance hole, not plated; courtyard is the 5.7 mm button head of an ISO 7380 screw",
              [("", 0, 0, 3.2, 3.2, "npth")], ("circle", 2.9), smd=False),
    footprint("WirePads_1x02_P2.0mm_1.5x2.4mm", "Two solder pads for the wires of a bead thermistor (hand-soldered, no paste)",
              [(1, -1.0, 0, 1.5, 2.4, "smd_nopaste"), (2, 1.0, 0, 1.5, 2.4, "smd_nopaste")], (-2.0, -1.45, 2.0, 1.45), fab=(-1.75, -1.2, 1.75, 1.2)),
]


def _rpm0026a():
    """TPS55288 land pattern (TI RPM0026A). Pad positions agree in three independent published footprints
    (greatscottgadgets/tycho, TI's Ultra Librarian export, and a third project); corner pins are two rectangles each."""
    p = [(1, -1.837, -1.488, 0.725, 0.225), (1, -1.625, -1.66, 0.4, 0.575), (2, -1.9, -1.0, 0.6, 0.25), (3, -1.837, -0.5, 0.725, 0.25),
         (4, -1.837, 0.0, 0.725, 0.25), (5, -1.837, 0.5, 0.725, 0.25), (6, -1.9, 1.0, 0.6, 0.25), (7, -1.9, 1.488, 0.6, 0.225),
         (7, -1.675, 1.663, 0.35, 0.575), (8, -1.125, 1.637, 0.25, 0.625), (9, -0.625, 1.637, 0.25, 0.625), (10, -0.125, 1.637, 0.25, 0.625),
         (11, 0.625, 1.637, 0.25, 0.625), (12, 1.125, 1.637, 0.25, 0.625), (13, 1.675, 1.663, 0.35, 0.575), (13, 1.9, 1.488, 0.6, 0.225),
         (14, 1.9, 1.0, 0.6, 0.25), (15, 1.837, 0.5, 0.725, 0.25), (16, 1.837, 0.0, 0.725, 0.25), (17, 1.837, -0.5, 0.725, 0.25),
         (18, 1.9, -1.0, 0.6, 0.25), (19, 1.625, -1.66, 0.4, 0.575), (19, 1.837, -1.488, 0.725, 0.225), (20, 1.05, -1.613, 0.25, 0.675),
         (21, 0.25, -1.65, 0.25, 0.6), (22, -0.25, -1.65, 0.25, 0.6), (23, -1.05, -1.613, 0.25, 0.675), (24, -0.625, 0.0, 0.375, 1.425),
         (25, 0.0, 0.0, 0.375, 1.425), (26, 0.625, 0.0, 0.375, 1.425)]
    return footprint("Texas_RPM0026A_VQFN-HR-26_3.5x4mm", "TI RPM0026A, VQFN-HR 26 pins, 4.0 x 3.5 mm body (TPS55288)",
                     [(n, x, y, w, h, "smd") for (n, x, y, w, h) in p], (-2.25, -2.0, 2.25, 2.0), fab=(-2.0, -1.75, 2.0, 1.75),
                     silk=((-2.1, -1.95, -2.3, -1.95), (-2.3, -1.95, -2.3, -1.75)))


FPS.append(_rpm0026a())

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "ST.pretty")
    os.makedirs(out, exist_ok=True)
    for name, text in FPS:
        with open(os.path.join(out, name + ".kicad_mod"), "w") as f:
            f.write(text)
    print("wrote", len(FPS), "footprints")
