"""Bought-part envelopes, modelled from datasheet dimensions (sources in docs/03-mechanical-design.md).

Each envelope is built in its own local frame (documented per function) and placed by assembly.py.
Where a maker's STEP file can be downloaded (StepperOnline motors, Harmonic Drive SHF units), it can be
dropped into hardware/cad/vendor/ and assembly.py will use it instead; the envelopes below match their
outline dimensions.
"""
import math
from build123d import Box, Cylinder, Pos, Rot, extrude, make_hull, Circle, Rectangle, Polygon, Part

from . import params as P
from .core import cyl, box, polar, register, PartDef


# ----------------------------------------------------------------------------- reducers
def reducer(size):
    """Cartridge frame: origin on the axis at the output face, +Z toward the input side."""
    r = P.RED[size]
    s = cyl(r["D_pilot"] / 2, -r["L_pilot"])
    s += cyl(r["D_out"] / 2, r["L_flange"])
    s += cyl(r["D"] / 2, r["L_house"], z=r["L_flange"])
    s += cyl(r["D_stub"] / 2, r["L_stub"], z=r["L_body"])
    s -= cyl(r["bore"] / 2, r["L_total"] + 2, z=-r["L_pilot"] - 1)
    for (x, y) in polar(r["n_hole"], r["pcd_hole"] / 2, 360 / r["n_hole"] / 2):
        s -= cyl(r["d_hole"] / 2, r["L_house"] + 0.2, x, y, r["L_flange"] - 0.1)
    for (x, y) in polar(r["n_tap"], r["pcd_tap"] / 2):
        s -= cyl(1.25, 6, x, y, -0.01)
    return s


# ----------------------------------------------------------------------------- motors
def nema17(length):
    """Origin on the shaft axis at the mounting face; body extends +Z, shaft points -Z."""
    n = P.NEMA
    w = n["W"]
    c = n["chamfer"]
    pts = [(-w / 2 + c, -w / 2), (w / 2 - c, -w / 2), (w / 2, -w / 2 + c), (w / 2, w / 2 - c),
           (w / 2 - c, w / 2), (-w / 2 + c, w / 2), (-w / 2, w / 2 - c), (-w / 2, -w / 2 + c)]
    body = extrude(Polygon(*pts, align=None), length)
    body += cyl(n["pilot_d"] / 2, -n["pilot_h"])
    body += cyl(n["shaft_d"] / 2, -n["shaft_l"])
    for (x, y) in [(a * n["hole_sq"] / 2, b * n["hole_sq"] / 2) for a in (-1, 1) for b in (-1, 1)]:
        body -= cyl(1.25, 4.5, x, y, -0.01)
    body += box(-n["conn_w"] / 2, n["conn_w"] / 2, w / 2, w / 2 + 3, length - n["conn_d"], length)
    return body


# ----------------------------------------------------------------------------- pulleys and belt
def pulley60(bore_clear=13.0):
    """Origin at the face that bolts to the reducer input stub; extends +Z."""
    p = P.PULLEY60
    s = cyl(p["flange_d"] / 2, 0.6)
    s += cyl(p["OD"] / 2, p["w_teeth"] - 1.2, z=0.6)
    s += cyl(p["flange_d"] / 2, 0.6, z=p["w_teeth"] - 0.6)
    s -= cyl(bore_clear / 2, 20, z=-5)
    for (x, y) in polar(4, 8.5, 45):
        s -= cyl(1.7, 20, x, y, -5)
    return s


def pulley20():
    """Origin on the axis at the teeth face nearest the reducer side; teeth 0..10, hub 10..16 (+Z)."""
    p = P.PULLEY20
    s = cyl(p["flange_d"] / 2, 0.6)
    s += cyl(p["OD"] / 2, p["w_teeth"] - 1.2, z=0.6)
    s += cyl(p["flange_d"] / 2, 0.6, z=p["w_teeth"] - 0.6)
    s += cyl(p["hub_d"] / 2, p["hub_h"], z=p["w_teeth"])
    s -= cyl(2.5, 40, z=-5)
    return s


def belt():
    """Closed GT2 belt; centred on Z=0 (belt plane), large pulley at origin, small at (0, C)."""
    t = 1.38
    rl, rs = P.PD_LARGE / 2, P.PD_SMALL / 2
    outer = make_hull(Circle(rl + t - 0.25).edges() + (Pos(0, P.BELT_C) * Circle(rs + t - 0.25)).edges())
    inner = make_hull(Circle(rl - 0.25).edges() + (Pos(0, P.BELT_C) * Circle(rs - 0.25)).edges())
    return Pos(0, 0, -P.BELT_W / 2) * (extrude(outer, P.BELT_W) - extrude(inner, P.BELT_W))


# ----------------------------------------------------------------------------- electronics
def encoder_board():
    """Origin at board centre, underside (chip side) at Z=0, board 0..1.6, plug on top."""
    b = cyl(P.ENC_BOARD_D / 2, 1.6)
    for (x, y) in polar(2, P.ENC_BOARD_HOLE_PCD / 2, 0):
        b -= cyl(1.7, 3, x, y, -0.5)
    b += box(-1.5, 1.5, -1.5, 1.5, -0.9, 0)                     # MT6835 (QFN 3 x 3)
    b += box(-11.5, 11.5, 3.0, 9.0, 1.6, 5.85)                  # JST-GH 15-way, vertical (SM15B-GHS)
    b += box(-5.0, 5.0, -12.0, -6.0, 1.6, 7.6)                  # JST-PH 4-way motor plug
    return b


def mainboard():
    """Board in the YZ plane: origin at board centre, outer face (OLED side) toward -X at X=0."""
    m = P.MAINBOARD
    b = box(0, m["T"], -m["W"] / 2, m["W"] / 2, -m["H"] / 2, m["H"] / 2)
    for sy in (-1, 1):
        for sz in (-1, 1):
            b -= cyl(1.7, 4, -1, sy * (m["W"] / 2 - m["hole_inset"]), sz * (m["H"] / 2 - m["hole_inset"]), "X")
    b += box(m["T"], m["T"] + m["comp_h"], -40, 40, -22, 22)     # components on the inner face
    b += box(-4.0, 0, -18, 18, 6, 26)                             # OLED module glass 36 x 20
    for i in range(4):                                            # 4 tact switches
        y = -27 + i * 18 if False else (-36 + i * 11)
        b += box(-3.5, 0, y - 3, y + 3, -18 - 3, -18 + 3)
    b += box(-3.5, 0, 25 - 4.5, 25 + 4.5, -17, -13.7)             # USB-C port A
    b += box(-3.5, 0, 38 - 4.5, 38 + 4.5, -17, -13.7)             # USB-C port B
    b += cyl(3.0, -10.0, 0, 41, 11, "X")                          # 2.5 mm jack barrel
    b += box(-2, 0, 36, 39, 18, 21)                               # RGB LED
    return b


def battery_board():
    m = P.BATT_BOARD
    b = box(-m["W"] / 2, m["W"] / 2, 0, m["T"], -m["H"] / 2, m["H"] / 2)
    b += box(-12, 12, m["T"], m["T"] + 1.5, 10, 16)               # 4 LEDs + gauge button, facing +Y, 13 mm above the centre
    return b


def blade_connector():
    """5-way blade connector half, 20 x 8 x 12, mating face at Y=0, body toward -Y."""
    return box(-10, 10, -12, 0, -4, 4)


def gnss_patch():
    return box(-12.5, 12.5, -12.5, 12.5, 0, 4.5)


def clamp60():
    """Arca clamp, origin at the centre of its base; jaws along Y; knob on +X."""
    c = P.CLAMP
    s = box(-c["W"] / 2, c["W"] / 2, -c["L"] / 2, c["L"] / 2, 0, c["H"])
    s -= box(-19.5, 19.5, -c["L"] / 2 - 1, c["L"] / 2 + 1, c["H"] - 5, c["H"] + 1)
    s += cyl(c["knob_d"] / 2, c["knob_l"], c["W"] / 2, 0, 8, "X")
    s -= cyl(5.0, 10, 0, 0, -0.1)                                    # 3/8"-16 socket
    return s


def cell():
    return cyl(P.CELL_D / 2, P.CELL_L, axis="Y")


def vring(seat_d, section=7.0, width=6.7):
    """V-ring stretched on a seat: annulus from seat_d out, width along +Z from 0."""
    return cyl(seat_d / 2 + section, width) - cyl(seat_d / 2, width + 2, z=-1)


def usb_c():
    return box(-4.5, 4.5, 0, 7.4, -1.65, 1.65)


def hinge_pin():
    return cyl(4.0, 80.0, y=-40.0, axis="Y")


def bubble_level():
    return cyl(6.0, 6.0)


def bushing38():
    return cyl(6.0, 8.0) - cyl(4.5, 10, z=-1)


def coin_screw38(length=10.0):
    """3/8in-16 coin-slot screw: head 19 x 4.5 below z=0, shank up."""
    return cyl(9.5, 4.5, z=-4.5) + cyl(4.75, length) - box(-9.6, 9.6, -0.6, 0.6, -4.6, -3.0)


def dowel4(length=10.0):
    return cyl(2.0, length)


# ----------------------------------------------------------------------------- payload envelopes
def rig_parts(key, y0):
    """Payload envelope `key` (params.RIGS) with its camera mount plane at Y = y0, world frame at alt 0, roll 0.
    Returns (solids dict, masses dict, CG of each solid as (x, y, z))."""
    r, C = P.RIGS[key], P.CAMERA
    za = P.Z_ROLL + P.R_CLAMP_SEAT + r["H"]
    sol, mas, cg = {}, {}, {}
    sol["lens"] = Pos(P.X_ROLL, y0, za) * Rot(-90, 0, 0) * Cylinder(r["D"] / 2, r["L"], align=(_C, _C, _MIN))
    if r["cam"] == "mirrorless":
        xt = P.X_ROLL - C["mount_from_tower_side"]
        zb = za - C["axis_above_bottom"]
        cam = box(xt, xt + C["W"], y0 - C["body_depth"], y0, zb, zb + C["H"] - 14)
        cam += box(P.X_ROLL - 20, P.X_ROLL + 20, y0 - C["body_depth"], y0 - 10, zb + C["H"] - 14, zb + C["H"])
        cam += box(xt + C["W"] - 33, xt + C["W"], y0, y0 + 20, zb, zb + C["H"] - 22)
        cam_kg = C["mass"]
        cgc = (xt + C["W"] / 2, y0 - C["body_depth"] / 2, zb + C["H"] / 2)
    else:
        cam = Pos(P.X_ROLL, y0, za) * Rot(90, 0, 0) * Cylinder(r["cam_D"] / 2, r["cam_L"], align=(_C, _C, _MIN))
        cam_kg = r["cam_kg"]
        cgc = (P.X_ROLL, y0 - r["cam_L"] / 2, za)
    sol["camera"] = cam
    extra = max(r["kg"] - r["ota_kg"] - cam_kg, 0.0)
    mas["lens"], cg["lens"] = r["ota_kg"] + extra, (P.X_ROLL, y0 + r["L"] * 0.45, za)
    mas["camera"], cg["camera"] = cam_kg, cgc
    m = mas["lens"] + mas["camera"]
    ycg = (mas["lens"] * cg["lens"][1] + mas["camera"] * cg["camera"][1]) / m
    zs = P.Z_ROLL + P.R_CLAMP_SEAT
    if r["mount"] == "plate":                       # L-plate under the camera body
        yc = y0 - C["body_depth"] / 2
        top = za - C["axis_above_bottom"]
    elif r["mount"] == "foot":                      # lens foot or collar under the balance point
        yc = ycg
        top = za - r["D"] / 2 + 6
    else:                                           # dovetail bar: rear end flush with the clamp's rear jaw, so it
        yc = P.CLAMP_CY - P.CLAMP["L"] / 2 + r["mount_L"] / 2   # never reaches back over the roll cartridge;
        top = za - r["D"] / 2 + 2                   # the tube is balanced by sliding it in its rings on the bar
    sol["mount"] = box(P.X_ROLL - 19, P.X_ROLL + 19, yc - r["mount_L"] / 2, yc + r["mount_L"] / 2, zs, max(top, zs + 8))
    mas["mount"], cg["mount"] = 0.0, (P.X_ROLL, yc, zs + 5)
    return sol, mas, cg, yc


def reference_rig(key=None, y0=None):
    """Solids of a payload envelope, balanced on the altitude axis (see assembly.rig_y0)."""
    from .assembly import rig_y0
    key = key or P.REF_RIG
    return rig_parts(key, rig_y0(key) if y0 is None else y0)[0]


from build123d import Align as _Al  # noqa: E402
_C, _MIN = _Al.CENTER, _Al.MIN
