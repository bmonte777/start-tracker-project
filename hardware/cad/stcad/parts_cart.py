"""Axis cartridges: housings ST-210/211, encoder-board carriers ST-212/216, motor plate ST-207,
encoder tubes ST-208/215. All in the cartridge frame: origin on the reducer axis at the output face,
+Z toward the input side, motor at +Y (centre distance BELT_C)."""
import math
from build123d import Pos, Rot, extrude, make_hull, Circle, Rectangle, RectangleRounded, Polygon

from . import params as P
from .core import cyl, box, polar, register, PartDef, feat, hull_extrude


def _housing(size):
    r, c = P.RED[size], P.CART[size]
    ear0 = 45.0 if size == 17 else 45.0 - P.ROLL_CART_ROT        # roll: ears stay at 45 deg steps in the world
    D = r["D"]
    ro = D / 2 + c["ring_wall"]
    zf0, zb = r["L_flange"], r["L_body"]           # sleeve from the housing front face to the rear face
    ft = 6.0                                        # rear flange thickness
    yb = P.BELT_C + 25.0                            # bridge end wall outer face
    # sleeve
    s = cyl(ro, zb - zf0, z=zf0)
    # front ears
    for (x, y) in polar(c["ear_n"], c["ear_pcd"] / 2, ear0):
        ang = math.atan2(y, x)
        ear = hull_extrude([Pos(x, y) * Circle(7.0), Pos(0.8 * x * (ro - 2) / (c["ear_pcd"] / 2),
                                                          0.8 * y * (ro - 2) / (c["ear_pcd"] / 2)) * Circle(7.0)],
                           zf0, c["ear_t"])
        s += ear
    # rear flange (keyhole) and bridge
    s += hull_extrude([Circle(ro), Pos(0, yb - 6) * Rectangle(60, 12)], zb, ft)
    zt = c["z_motor_plate"]
    for sx in (-1, 1):
        s += box(sx * 27, sx * 31, 8, yb, zb + ft, zt)                      # side walls
    s += box(-31, 31, yb - 3, yb, zb + ft, zt)                               # end wall
    # bore with crush ribs: print bore D+0.3, six ribs to D-0.2
    s -= cyl(D / 2 + 0.15, zb - zf0 + 0.2, z=zf0 - 0.1)
    for (x, y) in polar(6, D / 2 + 0.15 - 0.25, 30):
        s += Pos(x, y, (zf0 + zb) / 2) * Rot(0, 0, math.degrees(math.atan2(y, x))) * \
            box(-0.25, 0.25, -0.6, 0.6, -(zb - zf0) / 2, (zb - zf0) / 2)
    s -= cyl(14.0, 30, z=zb - 5)                                             # stub clearance
    s -= cyl(r["pcd_hole"] / 2 - 5.5, ft + 2, z=zb - 1)                      # open the flange inside the screw ring
    s -= Pos(0, (ro + yb - 6) / 2 + 2, zb - 1) * extrude(RectangleRounded(44, yb - 6 - ro - 8, 5), ft + 2)
    s -= cyl(8.0, ft + 2, 0, P.BELT_C, zb - 1)                               # motor shaft / pulley clearance
    feat("bore", f"{D:.0f} press (ribs)", (0, 0, zf0), "Z", zb - zf0,
         f"6 crush ribs to {D - 0.2:.1f}; reducer housing register; no reaming")
    # ear inserts (M4) from the front face
    for (x, y) in polar(c["ear_n"], c["ear_pcd"] / 2, ear0):
        d, dep = P.INSERT["M4"]
        s -= cyl(d / 2, dep, x, y, zf0 - 0.01)
    feat("insert", "M4", (round(c["ear_pcd"] / 2 * math.cos(math.radians(ear0)), 1),
                          round(c["ear_pcd"] / 2 * math.sin(math.radians(ear0)), 1), zf0), "Z",
         P.INSERT["M4"][1], f"4x on PCD {c['ear_pcd']:.0f}, at {ear0:.0f} deg + 90 deg steps; cartridge mounting", 4)
    # reducer screws: M3 inserts in the rear flange, entering from the front of the flange
    off = 360 / r["n_hole"] / 2
    for (x, y) in polar(r["n_hole"], r["pcd_hole"] / 2, off):
        s -= cyl(P.INSERT["M3"][0] / 2, ft + 0.2, x, y, zb - 0.1)
    feat("insert", "M3", (round(r["pcd_hole"] / 2 * math.cos(math.radians(off)), 1),
                          round(r["pcd_hole"] / 2 * math.sin(math.radians(off)), 1), zb), "Z", ft,
         f"{r['n_hole']}x on PCD {r['pcd_hole']:.0f}, through the {ft:.0f} mm flange; reducer screws", r["n_hole"])
    # motor-plate clamp inserts on the wall tops, tension screw hole in the end wall
    for sx in (-1, 1):
        for dy in (-12, 12):
            s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], sx * 29, P.BELT_C + dy, zt + 0.01, "-Z")
    feat("insert", "M3", (29, P.BELT_C - 12, zt), "-Z", P.INSERT["M3"][1],
         "4x at X +/-29, Y C+/-12 on the wall tops; motor plate clamp", 4)
    s -= cyl(P.CLEAR["M3"] / 2, 10, 0, yb - 6, zt - 5, "Y")
    feat("thru", "3.4", (0, yb, zt - 5), "-Y", None, "tension screw M3x12")
    # cover posts inserts (2) in the rear flange, -Y side
    for a in (200, 340):
        x, y = 34 * math.cos(math.radians(a)), 34 * math.sin(math.radians(a))
        s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], x, y, zb + ft + 0.01, "-Z")
    feat("insert", "M3", (round(34 * math.cos(math.radians(200)), 1), round(34 * math.sin(math.radians(200)), 1),
                          zb + ft), "-Z", P.INSERT["M3"][1], "2x on R34 at 200/340 deg; cover posts", 2)
    # plug / cable window in the end wall
    s -= box(-12, 12, yb - 5, yb + 1, zb + ft + 2, zb + ft + 10)
    return s


def build_housing17():
    return _housing(17)


def build_housing14():
    return _housing(14)


def _carrier(size):
    r, c = P.RED[size], P.CART[size]
    zb = r["L_body"] + 6.0
    zh = c["z_board"] + 1.6
    s = cyl(22.0, 2.5, z=zh)
    for a in (200, 340):
        x, y = 34 * math.cos(math.radians(a)), 34 * math.sin(math.radians(a))
        s += hull_extrude([Pos(x, y) * Circle(4.5), Pos(x * 0.5, y * 0.5) * Circle(4.5)], zh, 2.5)
        s += cyl(4.5, zh - zb, x, y, zb)
        s -= cyl(P.CLEAR["M3"] / 2, 40, x, y, zb - 1)
        s -= cyl(3.2, 3.5, x, y, zh + 2.5 - 3.4)
    for (x, y) in polar(2, P.ENC_BOARD_HOLE_PCD / 2, 0):
        s -= cyl(1.25, 2.2, x, y, zh - 0.01)
    s -= box(-12.5, 12.5, 2.5, 9.5, zh - 1, zh + 4)         # GH plug window
    s -= box(-6.0, 6.0, -13.0, -5.0, zh - 1, zh + 4)        # PH motor plug window
    feat("thru", "3.4", (34 * math.cos(math.radians(200)), 34 * math.sin(math.radians(200)), zh + 2.5), "-Z",
         None, "2x posts, M3x30 to the housing flange; 6.4 x 3.4 counterbore", 2)
    feat("tap", "M3 self-tap 2.5", (P.ENC_BOARD_HOLE_PCD / 2, 0, zh), "Z", 3.0,
         "2x on PCD 23; encoder board, M3x6 thread-forming into plastic", 2)
    return s


def build_carrier17():
    return _carrier(17)


def build_carrier14():
    return _carrier(14)


def build_motor_plate():
    """Local frame: motor axis at origin, plate underside at Z=0, plate 0..4, tension block below."""
    s = box(-31, 31, -26, 18, 0, 4)
    s -= cyl(11.1, 10, z=-1)
    feat("bore", "22.2 H9", (0, 0, 0), "Z", None, "NEMA 17 pilot")
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            s -= cyl(P.CLEAR["M3"] / 2, 10, x, y, -1)
    feat("thru", "3.4", (15.5, 15.5, 4), "-Z", None, "4x on 31 x 31 square; motor screws M3x8 from below", 4)
    for sx in (-1, 1):
        for dy in (-12, 12):
            s -= Pos(sx * 29, dy, 2) * Rot(0, 0, 90) * extrude(
                RectangleRounded(9.4, 3.4, 1.69), 6, both=True)
    feat("slot", "3.4 x 9.4", (29, 12, 4), "-Z", None, "4x slots along Y at X +/-29, Y +/-12; clamp M3x8", 4)
    s += box(-6, 6, 10, 18, -10, 0)
    s -= cyl(P.TAP["M3"] / 2, 9, 0, 21, -5, "-Y")
    feat("tap", "M3", (0, 18, -5), "-Y", 6, "tension screw")
    return s


def _tube(size):
    c = P.CART[size]
    t = P.ENC_TUBE
    z0 = -5.5
    L = c["z_magnet"] - z0
    s = cyl(t["flange_d"] / 2, t["flange_t"], z=z0)
    s += cyl(t["OD"] / 2, L - t["flange_t"], z=z0 + t["flange_t"])
    s -= cyl(t["ID"] / 2, L - t["solid_end"], z=z0 - 0.1)
    s -= cyl(t["magnet_d"] / 2 + 0.03, 2.6, z=c["z_magnet"] - 2.6 + 0.01)
    zs = c["z_magnet"] - t["solid_end"] - t["slot_l"]
    s -= box(-t["slot_w"] / 2, t["slot_w"] / 2, 0, 6, zs, zs + t["slot_l"])
    for (x, y) in polar(2, 7.0, 90):
        s -= cyl(P.TAP["M3"] / 2, t["flange_t"] + 0.2, x, y, z0 - 0.1)
    feat("tap", "M3", (0, 7, z0), "-Z", None, "2x on PCD 14, through the flange")
    feat("bore", "6.03 +0.02/0", (0, 0, c["z_magnet"]), "-Z", 2.6, "magnet seat, magnet glued (Loctite 638)")
    feat("slot", f"{t['slot_w']} x {t['slot_l']}", (0, 5, zs), "Y", None, "cable window, one side")
    return s


def build_tube17():
    return _tube(17)


def build_tube14():
    return _tube(14)


CARTRIDGE_PARTS = [
    register(PartDef("ST-211", "Cartridge housing, size 17 (azimuth, altitude)", "printed", "PAHT-CF", 2,
                     build_housing17, finish="As printed; bore ribs pressed", tol="Printed: +/-0.2; bore ribs to size",
                     print_rot=(0, 0, 0), group="2xx", color=(0.25, 0.27, 0.30),
                     notes=["Print with the output end (ears) on the plate; no supports except under the end-wall window.",
                            "Press the reducer in; the six crush ribs centre it. Do not ream.",
                            "Fit 4 M4 and 16 M3 heat-set inserts before assembly."])),
    register(PartDef("ST-210", "Cartridge housing, size 14 (roll)", "printed", "PAHT-CF", 1, build_housing14,
                     finish="As printed; bore ribs pressed", tol="Printed: +/-0.2; bore ribs to size",
                     print_rot=(0, 0, 0), group="2xx", color=(0.25, 0.27, 0.30),
                     notes=["Print with the output end (ears) on the plate.",
                            "Fit 4 M4 and 12 M3 heat-set inserts before assembly."])),
    register(PartDef("ST-212", "Cartridge rear cover / encoder-board carrier, size 17", "printed", "ASA", 2,
                     build_carrier17, finish="As printed", tol="Printed: +/-0.2", print_rot=(180, 0, 0),
                     group="2xx", color=(0.15, 0.15, 0.17))),
    register(PartDef("ST-216", "Cartridge rear cover / encoder-board carrier, size 14", "printed", "ASA", 1,
                     build_carrier14, finish="As printed", tol="Printed: +/-0.2", print_rot=(180, 0, 0),
                     group="2xx", color=(0.15, 0.15, 0.17))),
    register(PartDef("ST-207", "Motor plate with belt-tension block", "machined", "6061", 3, build_motor_plate,
                     finish=P.MAT["6061"]["finish"], tol="ISO 2768-m", group="2xx", color=(0.75, 0.76, 0.78),
                     notes=["Break all edges 0.3.", "Pilot bore 22.2 H9 square to the plate within 0.05."])),
    register(PartDef("ST-208", "Encoder reference tube, size 17 (azimuth, altitude)", "turned", "304", 2,
                     build_tube17, finish=P.MAT["304"]["finish"], tol="ISO 2768-m; OD 10 h7 run-out 0.02 to flange face",
                     group="2xx", color=(0.82, 0.82, 0.85),
                     notes=["Cable window milled after turning; deburr inside.",
                            "Magnet: 6 x 2.5 diametric N35SH (ST-209), glued in the seat."])),
    register(PartDef("ST-215", "Encoder reference tube, size 14 (roll)", "turned", "304", 1, build_tube14,
                     finish=P.MAT["304"]["finish"], tol="ISO 2768-m; OD 10 h7 run-out 0.02 to flange face",
                     group="2xx", color=(0.82, 0.82, 0.85))),
]
