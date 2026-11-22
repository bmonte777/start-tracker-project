"""Structure: base ST-301, wedge ST-302/303, latitude arcs ST-305, azimuth body ST-310, tower ST-311,
altitude arm ST-312, roll shelf ST-313. Modelled in the world frame (wedge flat, az 0, alt 0, roll 0)."""
import math
from build123d import (Pos, Rot, Plane, extrude, make_hull, Circle, Rectangle, RectangleRounded, Polygon,
                       offset, Kind, fillet, Axis, Sketch)

from . import params as P
from .core import cyl, box, polar, register, PartDef, feat, hull_extrude, roll_to_world


def _hull(faces):
    e = []
    for f in faces:
        e += f.edges()
    return make_hull(e)


def plate_yz(face, x0, t):
    """Face sketched with (u, v) = (Y, Z), extruded from X = x0 toward +X by t."""
    pl = Plane(origin=(x0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    return extrude(pl * face, t, dir=(1, 0, 0))


def plate_xz(face, y0, t):
    """Face sketched with (u, v) = (X, Z), extruded from Y = y0 toward -Y by t."""
    pl = Plane(origin=(0, y0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
    return extrude(pl * face, t, dir=(0, -1, 0))


def cbore_hole(s, size, x, y, z_face, depth, direction="+Z"):
    """Clearance hole with ISO 4762 counterbore, entering at z_face and going `direction`."""
    d_c, h_c = P.CBORE[size]
    sgn = 1 if direction == "+Z" else -1
    s -= cyl(P.CLEAR[size] / 2, sgn * (depth + 0.2), x, y, z_face - sgn * 0.1)
    s -= cyl(d_c / 2, sgn * (h_c + 0.1), x, y, z_face - sgn * 0.1)
    return s


# ============================================================================== ST-301 base plate
def build_base():
    f = _hull([Circle(42.0), Pos(48, 0) * RectangleRounded(36, 52, 8)])
    s = extrude(f, P.Z_BASE_TOP)
    s += cyl(10.0, 4.0, z=P.Z_BASE_TOP)                                  # pivot spigot
    s += cyl(3.0, 6.0, 58, 0, P.Z_BASE_TOP)                              # fine-adjust boss
    s -= cyl(6.0, 30, z=-1)
    feat("bore", "12 H7", (0, 0, 0), "Z", None, "3/8\"-16 stainless bushing ST-307 pressed + Loctite 641")
    feat("pin", "20 h7", (0, 0, P.Z_BASE_TOP), "Z", 4.0, "pivot spigot, fits ST-302 20 H7")
    feat("pin", "6 h9", (58, 0, P.Z_BASE_TOP), "Z", 6.0, "azimuth fine-adjust boss")
    for sy in (-1, 1):
        x, y = 50 * math.cos(math.radians(25)), sy * 50 * math.sin(math.radians(25))
        s -= cyl(P.TAP["M5"] / 2, 20, x, y, -1)
    feat("tap", "M5", (45.3, 21.1, P.Z_BASE_TOP), "-Z", None, "2x at R50, +/-25 deg; azimuth lock screws", 2)
    # lightening ring pocket from below
    s -= extrude(Circle(35.0) - Circle(13.0), 6.0)                       # 2 mm skin (D35)
    s -= Pos(50, 0) * extrude(RectangleRounded(16, 26, 4), 5.0)
    feat("pocket", "R13-R35", (0, 0, 0), "Z", 5.0, "lightening, from below; plus 16 x 26 under the tab")
    return s


# ============================================================================== ST-302 wedge lower plate
CLAMP_PT = (P.WEDGE_HINGE_X + P.WEDGE_ARC_R * math.cos(math.radians(P.WEDGE_CLAMP_ANG)),
            P.WEDGE_HINGE_Z + P.WEDGE_ARC_R * math.sin(math.radians(P.WEDGE_CLAMP_ANG)))


def build_wedge_lower():
    z0, z1 = P.Z_BASE_TOP, P.Z_LOWER_TOP
    hx, hz = P.WEDGE_HINGE_X, P.WEDGE_HINGE_Z
    f = RectangleRounded(104, P.WEDGE_W, 8) + Pos(56, 0) * RectangleRounded(20, 48, 6)
    s = Pos(0, 0, z0) * extrude(f, z1 - z0)
    yw = P.WEDGE_W / 2
    for sy in (-1, 1):                                                     # hinge posts
        y0, y1 = sorted((sy * 19.0, sy * 40.0))
        s += box(hx - 9, -50, y0, y1, z0, z1)
        s += box(hx - 9, hx + 9, y0, y1, z1, hz)
        s += cyl(9.0, 21.0, hx, y0, hz, "Y")
    s -= cyl(4.0, 120, hx, -60, hz, "Y")
    feat("bore", "8 H7", (hx, -40, hz), "Y", None, "hinge pin ST-304 (8 h6 x 80) through both posts")
    for sy in (-1, 1):                                                     # clamp towers outside the arcs
        y0, y1 = sorted((sy * (yw + 6), sy * (yw + 13)))
        s += box(CLAMP_PT[0] - 7, -12, y0, y1, z0, 46.0)
        ya, yb = sorted((sy * yw, sy * (yw + 6)))
        s += box(-24, -12, ya, yb, z0, z1)
        s -= cyl(P.TAP["M5"] / 2, 10, CLAMP_PT[0], sy * (yw + 14), CLAMP_PT[1], "-Y" if sy > 0 else "Y")
    feat("tap", "M5", (CLAMP_PT[0], yw + 13, CLAMP_PT[1]), "-Y", None, "2x clamp knob ST-308 (M5 x 16 thumb screw) presses the arc", 2)
    s -= cyl(P.TAP["M3"] / 2, 12, CLAMP_PT[0] + 5, yw + 9.5, 46.01, "-Z")
    feat("tap", "M3", (CLAMP_PT[0] + 5, yw + 9.5, 46), "-Z", 12, "+Y tower only: tangent screw for fine adjust (D38)")
    for (x, y) in [(-30, 34), (-30, -34), (40, 0)]:                        # rest pads for the upper plate
        s += cyl(6.0, P.Z_UPPER_BOT - z1, x, y, z1)
    feat("pad", "12 x 4", (40, 0, z1), "Z", P.Z_UPPER_BOT - z1, "3x rest pads at (-30,+/-34) (40,0); grind flat together", 3)
    s -= cyl(10.05, 4.5, z=z0 - 0.01)
    feat("bore", "20 H7", (0, 0, z0), "Z", 4.5, "pivot, from below")
    s -= cyl(6.0, 30, z=z0 - 1)
    for sy in (-1, 1):                                                     # azimuth lock slots
        a0 = sy * 25
        for k in range(-8, 9, 2):
            a = math.radians(a0 + k)
            s -= cyl(P.CLEAR["M5"] / 2, 20, 50 * math.cos(a), 50 * math.sin(a), z0 - 1)
    feat("slot", "5.5 R50", (45.3, 21.1, z1), "-Z", None, "2x arc slots R50, 25 +/- 8 deg; M5x12 ISO 7380 + washer", 2)
    s -= box(55, 61, -5, 5, z0 - 1, z1 + 1)                                 # fine-adjust slot
    for sy in (-1, 1):
        s -= cyl(P.TAP["M5"] / 2, 20, 58, sy * 24.5, (z0 + z1) / 2, "-Y" if sy > 0 else "Y")
    feat("tap", "M5", (58, 24, 13), "-Y", 19, "2x push screws ST-306 from +/-Y into the fine-adjust slot", 2)
    # W3 (D35): ribbed pockets from below, 2 mm top skin, 5 mm cross ribs, 4 mm rim; material kept round
    # the pivot, the rest pads and the azimuth lock slots
    reg = RectangleRounded(96, 84, 4)
    reg -= Rectangle(200, 5) + Rectangle(5, 200)
    reg -= Circle(13.0)
    for (x, y) in [(-30, 34), (-30, -34), (40, 0)]:
        reg -= Pos(x, y) * Circle(8.0)
    for sy in (-1, 1):
        for k in range(-8, 9, 2):
            a = math.radians(sy * 25 + k)
            reg -= Pos(50 * math.cos(a), 50 * math.sin(a)) * Circle(P.CLEAR["M5"] / 2 + 2.5)
    s -= Pos(0, 0, z0 - 0.01) * extrude(reg, (z1 - z0) - 2.0)
    feat("pocket", "ribbed", (24, 26, z0), "Z", (z1 - z0) - 2.0, "4 ribbed lightening pockets from below, 2 mm skin, 5 mm ribs (W3)", 4)

    return s


# ============================================================================== ST-303 wedge upper plate
def build_wedge_upper():
    z0, z1, zt = P.Z_UPPER_BOT, P.Z_UPPER_PLATE_TOP, P.Z_AZ_OUT
    hx, hz = P.WEDGE_HINGE_X, P.WEDGE_HINGE_Z
    s = Pos(-4, 0, z0) * extrude(RectangleRounded(96, P.WEDGE_W, 8), z1 - z0)
    s += box(hx - 9, -50, -18.3, 18.3, z0, z1)                               # knuckle block
    s += box(hx - 9, hx + 9, -18.3, 18.3, z1, hz)
    s += cyl(9.0, 36.6, hx, -18.3, hz, "Y")
    s -= cyl(4.0, 120, hx, -60, hz, "Y")
    feat("bore", "8 H7", (hx, -18, hz), "Y", None, "hinge knuckle")
    s += cyl(37.5, zt - z1, z=z1)                                            # boss = V-ring seat
    s += cyl(40.0, 1.5, z=38.3)                                              # V-ring back shoulder
    feat("pin", "75 h9", (0, 0, 39.8), "Z", zt - 39.8, "V-ring VA-75 seat (ST-213); 1.5 mm shoulder ring at Z 38.3")
    s -= cyl(22.5, 2.5, z=zt - 2.5 + 0.01)
    feat("bore", "45 H7", (0, 0, zt), "-Z", 2.5, "azimuth reducer output pilot")
    s -= cyl(10.1, 3.0, z=zt - 5.5)
    feat("bore", "20.2", (0, 0, zt - 2.5), "-Z", 3.0, "encoder tube flange seat")
    r = P.RED[17]
    for (x, y) in polar(r["n_tap"], r["pcd_tap"] / 2):
        s -= cyl(P.CLEAR["M3"] / 2, zt - z0 + 1, x, y, z0 - 0.5)
        s -= cyl(3.0, 30.0 - z0, x, y, z0 - 0.01)
    feat("cbore", "3.4 / 6.0 to Z30", (27, 0, z0), "Z", None, "16x on PCD 54; output flange M3x20 ISO 4762, head seat at Z 30", 16)
    s -= cyl(22.0, 36.0 - z0, z=z0 - 0.01)
    feat("pocket", "44", (0, 0, z0), "Z", 36.0 - z0, "boss hollowed from below to Z 36")
    s -= cyl(3.25, 20, z=30)
    for (x, y) in polar(2, 7.0, 90):
        s -= cyl(P.CLEAR["M3"] / 2, 10, x, y, 35.0)
    feat("thru", "3.4", (0, 7, 36), "Z", None, "2x on PCD 14 from inside the pocket; encoder tube M3x6 ISO 4762", 2)
    for sy in (-1, 1):
        for x in (-46.0, -34.0):
            s -= cyl(P.TAP["M5"] / 2, 11, x, sy * (P.WEDGE_W / 2 + 0.01), 26.0, "-Y" if sy > 0 else "Y")
    feat("tap", "M5", (-46, P.WEDGE_W / 2, 26.0), "-Y", 10, "4x side faces at X -46 / -34, Z 26; latitude arcs", 4)
    # W3 (D35): ribbed pockets from below, 2 mm skin, kept clear of the reducer screw ring and arc taps
    reg = Pos(-4, 0) * RectangleRounded(88, 84, 4)
    reg -= Rectangle(200, 5) + Rectangle(5, 200)
    reg -= Circle(33.0)
    for sy in (-1, 1):
        reg -= Pos(-40, sy * 40) * Rectangle(22, 16)
    s -= Pos(0, 0, z0 - 0.01) * extrude(reg, (z1 - z0) - 2.0)
    feat("pocket", "ribbed", (31, 28, z0), "Z", (z1 - z0) - 2.0, "4 ribbed lightening pockets from below, 2 mm skin, 5 mm ribs (W3)", 4)
    return s


# ============================================================================== ST-305 latitude arc
def build_arc():
    """Fixed to the upper plate side, hangs below the hinge; clamp knob on ST-302 presses it."""
    hx, hz = P.WEDGE_HINGE_X, P.WEDGE_HINGE_Z
    R0, R1 = P.WEDGE_ARC_RIN, P.WEDGE_ARC_ROUT
    a_hi, a_lo = P.WEDGE_CLAMP_ANG + 2.0, P.WEDGE_CLAMP_ANG - P.WEDGE_TILT_MAX - 4.0
    angs = [a_hi - k * (a_hi - a_lo) / 30 for k in range(31)]
    pts_o = [(hx + R1 * math.cos(math.radians(a)), hz + R1 * math.sin(math.radians(a))) for a in angs]
    pts_i = [(hx + R0 * math.cos(math.radians(a)), hz + R0 * math.sin(math.radians(a))) for a in reversed(angs)]
    sector = Polygon(*(pts_o + pts_i), align=None)
    tab = Pos(-40, 26) * RectangleRounded(24, 8, 2)
    y1 = P.WEDGE_W / 2 + 6.0
    s = plate_xz(sector + tab + Pos(-38, 30) * Rectangle(10, 12), y1, 6.0)    # occupies Y 46..52
    for x in (-46.0, -34.0):
        s -= cyl(P.CLEAR["M5"] / 2, 10, x, y1 - 8, 26.0, "Y")
    feat("thru", "5.5", (-46, y1, 26), "-Y", None, "2x at X -46 / -34, Z 26; M5x12 ISO 7380 into ST-303", 2)
    feat("face", "R22-R36", (hx + 31, y1, hz), "-Y", None, "clamp face; engrave latitude 15-90 deg every 5 deg at R31")
    return s


# ============================================================================== footprints
def tower_face():
    """Tower footprint: one rounded rectangle; the +Y side houses the azimuth motor (D32)."""
    return Pos((P.TOWER_X_MIN + P.TOWER_X_MAX) / 2, (P.TOWER_Y_MIN + P.TOWER_Y_MAX) / 2) * \
        RectangleRounded(P.TOWER_X_MAX - P.TOWER_X_MIN, P.TOWER_Y_MAX - P.TOWER_Y_MIN, 6)


def body_face():
    rear = Pos((P.BODY_X_MIN - 30) / 2, (P.BODY_Y_MIN + P.BODY_Y_MAX) / 2) * \
        RectangleRounded(-30 - P.BODY_X_MIN, P.BODY_Y_MAX - P.BODY_Y_MIN, 12)
    tw = offset(tower_face(), 3.0)
    return _hull([Circle(P.BODY_FRONT_R), rear, tw])


COVER_X = (-149.0, -93.0)


# ============================================================================== ST-310 azimuth body
def build_body():
    z0, z1, w = P.Z_BODY_BOT, P.Z_BODY_TOP, P.BODY_WALL
    F = body_face()
    s = Pos(0, 0, z0) * extrude(F, z1 - z0)
    s -= Pos(0, 0, z0 + w) * extrude(offset(F, -w), z1 - z0)                 # open tub
    skin = Pos(0, 0, z1 - w) * extrude(F, w)
    skin -= Pos(0, 0, z1 - w - 1) * extrude(offset(tower_face(), -P.TOWER_WALL), w + 2)
    skin -= box(COVER_X[0], COVER_X[1], P.BODY_Y_MIN + 3, P.BODY_Y_MAX - 3, z1 - w - 1, z1 + 1)
    s += skin
    feat("opening", "tower", (-10, 0, z1), "-Z", None, "tower footprint, inset 3 mm")
    # floor: azimuth opening + drip skirt
    s -= cyl(41.0, 10, z=z0 - 1)
    s += cyl(49.5, -(z0 - 36.0), z=z0) - cyl(47.5, -(z0 - 35.0), z=z0 + 0.5)
    feat("bore", "82", (0, 0, z0), "Z", None, "azimuth opening; V-ring counterface under the floor, R42-R48 flat")
    feat("skirt", "95/99", (0, 0, z0), "-Z", z0 - 36.0, "drip skirt over ST-303 boss (labyrinth)")
    # azimuth cartridge ear bosses (motor at +Y)
    c = P.CART[17]
    for (x, y) in polar(4, c["ear_pcd"] / 2, 45):
        s += cyl(8.0, 51.0 - z0, x, y, z0)
        d_c = 8.0
        s -= cyl(P.CLEAR["M4"] / 2, 10, x, y, z0 - 1)
        s -= cyl(d_c / 2, 2.4 + 0.01, x, y, z0 - 0.01)
    feat("cbore", "4.5 / 8.0x2.4", (38.2, 38.2, z0), "Z",
         None, "4x on PCD 108 at 45/135/225/315 deg; cartridge M4x10 ISO 7380 from below", 4)
    # battery bay: rails, door opening, connector bracket
    px0, px1 = P.PACK_X0, P.PACK_X0 + P.PACK["W"]
    for x in (px0 + 6, px1 - 6):
        s += box(x - 2, x + 2, P.PACK_Y0 - 2, P.BODY_Y_MAX - w, z0 + w, P.PACK_Z0 - 2.0)
    s -= box(px0 - 3, px1 + 3, P.BODY_Y_MAX - w - 1, P.BODY_Y_MAX + 1, P.PACK_Z0 - 3, P.PACK_Z0 + P.PACK["H"] + 3)
    feat("opening", f"{P.PACK['W'] + 6:.0f} x {P.PACK['H'] + 6:.0f}", ((px0 + px1) / 2, P.BODY_Y_MAX, P.PACK_Z0 + 25),
         "-Y", None, "battery door opening, +Y wall")
    for x in (px0 + 8, px1 - 8):                                              # door snap slots
        s -= box(x - 4, x + 4, P.BODY_Y_MAX - w - 1, P.BODY_Y_MAX + 1, P.PACK_Z0 + P.PACK["H"] + 5, P.PACK_Z0 + P.PACK["H"] + 8)
    feat("slot", "8 x 3", (px0 + 8, P.BODY_Y_MAX, P.PACK_Z0 + 55), "-Y", None, "2x door snap catches", 2)
    cx = (px0 + px1) / 2
    yb = P.PACK_Y0 - 12.0
    s += box(cx - 18, cx + 18, yb - 8, yb, z0 + w, P.PACK_Z0 + 36)
    for dx in (-14, 14):
        s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], cx + dx, yb + 0.01, P.PACK_Z0 + 20.5, "-Y")
    feat("insert", "M3", (cx + 14, yb, P.PACK_Z0 + 20.5), "-Y", 6, "2x head-side blade connector ST-609", 2)
    # end wall opening for the bezel + 6 inserts
    xe = P.BODY_X_MIN
    yc = (P.BODY_Y_MIN + P.BODY_Y_MAX) / 2
    s -= box(xe - 1, xe + w + 1, yc - 50.5, yc + 50.5, 54.0, 118.0)
    feat("opening", "101 x 64", (xe, yc, 86), "X", None, "bezel / mainboard opening, centred at Y 15")
    for y in (yc - 55.5, yc + 55.5):
        for z in (58.0, 86.0, 114.0):
            s += cyl(4.5, 9.0, xe + w, y, z, "X")
            s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], xe - 0.01, y, z, "X")
    feat("insert", "M3", (xe, yc + 55.5, 58), "X", 6, "6x at Y 15 +/- 55.5, Z 58/86/114; bezel screws", 6)
    # top cover inserts (8) and tower inserts (4)
    cover_pts = COVER_PTS
    for (x, y) in cover_pts:
        s += cyl(4.5, 12, x, y, z1 - 12)
        s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], x, y, z1 + 0.01, "-Z")
    feat("insert", "M3", (COVER_PTS[0][0], COVER_PTS[0][1], z1), "-Z", 6, "8x top cover screws (see view)", 8)
    for (x, y) in TOWER_EARS:
        s += cyl(6.5, 14, x, y, z1 - 14)
        s -= cyl(P.INSERT["M5"][0] / 2, P.INSERT["M5"][1], x, y, z1 + 0.01, "-Z")
    feat("insert", "M5", TOWER_EARS[0] + (z1,), "-Z", 10, "4x tower screws M5x16 ISO 7380", 4)
    # counterweight bar inserts (2) from below
    for (x, y) in [(-72, -36), (-72, 36)]:
        s += cyl(7.0, 12, x, y, z0)
        s -= cyl(P.INSERT["M5"][0] / 2, P.INSERT["M5"][1], x, y, z0 - 0.01)
    feat("insert", "M5", (-72, 40, z0), "Z", 10, "2x counterweight bar (optional), from below", 2)
    return s


TOWER_EARS = [(50.0, 26.0), (5.0, -57.5), (-82.0, -40.0), (-82.0, 68.0)]
YM = P.BODY_Y_MAX - P.BODY_WALL
COVER_PTS = [(-140, -54), (-140, YM - 1), (-118, -54), (-118, YM - 1), (-97, -54), (-97, YM - 1), (-140, 15), (-97, 15)]


# ============================================================================== ST-311 tower
def build_tower():
    z0, z1, w = P.Z_BODY_TOP + P.GASKET_T, P.TOWER_TOP, P.TOWER_WALL
    T = tower_face()
    s = Pos(0, 0, z0) * extrude(T, z1 - z0)
    s -= Pos(0, 0, z0 - 1) * extrude(offset(T, -w), z1 - z0 - w + 1)
    # +X wall: thinner to the cartridge ear face, opening, V-ring counterface pad
    s -= box(P.TOWER_X_MAX - w - 2, P.TOWER_X_MAX - 2.5, P.TOWER_Y_MIN + w, P.TOWER_Y_MAX - w, z0 + 1, z1 - w)
    s -= cyl(42.0, 20, 30, 0, P.Z_ALT, "X")
    s += cyl(50.0, 1.0, P.TOWER_X_MAX, 0, P.Z_ALT, "X") - cyl(42.0, 3, P.TOWER_X_MAX - 1, 0, P.Z_ALT, "X")
    feat("bore", "84", (P.TOWER_X_MAX, 0, P.Z_ALT), "-X", None, "altitude opening; V-ring VA-80 counterface pad R42-R50, 1 mm proud, sand flat")
    for (u, v) in polar(4, P.CART[17]["ear_pcd"] / 2, 45):
        s -= cyl(P.CLEAR["M4"] / 2, 10, P.TOWER_X_MAX - 6, u, P.Z_ALT + v, "X")
    feat("thru", "4.5", (P.TOWER_X_MAX, 38.2, P.Z_ALT - 38.2), "-X", None, "4x on PCD 108 at 45 deg steps; alt cartridge M4x12 ISO 7380", 4)
    for a in (273.6, 43.4):                                                 # bumper inserts
        u, v = 62 * math.cos(math.radians(a)), 62 * math.sin(math.radians(a))
        s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], P.TOWER_X_MAX + 0.01, u, P.Z_ALT + v, "-X")
    feat("insert", "M3", (P.TOWER_X_MAX, 3.9, P.Z_ALT - 61.9), "-X", 6, "2x bumpers ST-322 at R62, 273.6 / 43.4 deg (contact at -15 / +100 deg)", 2)
    # bolting ears to the body
    for (x, y) in TOWER_EARS:
        cx = max(min(x, P.TOWER_X_MAX - 10), P.TOWER_X_MIN + 10)
        cy = max(min(y, P.TOWER_Y_MAX - 10), P.TOWER_Y_MIN + 10)
        s += hull_extrude([Pos(x, y) * Circle(7.0), Pos(cx, cy) * Circle(7.0)], z0, 8)
        s -= cyl(P.CLEAR["M5"] / 2, 20, x, y, z0 - 1)
    feat("thru", "5.5", (50, 26, z0 + 8), "-Z", None, "4x ears; M5x16 ISO 7380 into body inserts", 4)
    return s


# ============================================================================== ST-312 altitude arm
def build_arm():
    xa, t = P.ALT_OUT_X, P.ARM_T
    xr, zr = P.X_ROLL, P.Z_ROLL
    ypad = -37.0                                                             # pad front face (cartridge ears)
    # hub plate (YZ)
    pin_a = math.radians(296.0)
    pin = (62 * math.cos(pin_a), P.Z_ALT + 62 * math.sin(pin_a))
    hub_f = _hull([Pos(0, P.Z_ALT) * Circle(P.ARM_HUB_R), Pos(-42, 173) * Rectangle(10, 54),
                   Pos(pin[0], pin[1]) * Circle(8)])
    s = plate_yz(hub_f, xa, t)
    # pad plate (XZ): circle about the roll axis + bridge to the hub plate
    pad_f = Pos(xr, zr) * Circle(P.ARM_PAD_R) + Pos(68, 173) * Rectangle(44, 54)     # union, not hull: stays out of the body sweep
    pad = plate_xz(pad_f, ypad, t)
    pad -= box(xr - 70, xr + 70, ypad - t - 1, ypad + 1, zr + 41.0, zr + 80)       # stay under the clamp seat
    s += pad
    s -= cyl(47.5, 20, xr, ypad + 1, zr, "-Y")
    feat("bore", "95", (xr, ypad, zr), "-Y", None, "roll cartridge sleeve clearance")
    for (x, y) in polar(4, P.CART[14]["ear_pcd"] / 2, 45.0 - P.ROLL_CART_ROT):
        X, _, Z = roll_to_world(x, y)
        s -= cyl(P.CLEAR["M4"] / 2, 20, X, ypad + 1, Z, "-Y")
    feat("thru", "4.5", (xr - 33.9, ypad - t, zr - 33.9), "Y", None, "4x on PCD 96 about the roll axis; M4x16 from the back", 4)
    for a in (0.0, 180.0, 270.0):
        s -= cyl(P.CLEAR["M3"] / 2, 20, xr + 54 * math.cos(math.radians(a)), ypad + 1, zr + 54 * math.sin(math.radians(a)), "-Y")
    feat("thru", "3.4", (xr + 54, ypad, zr), "-Y", None, "3x at R54, 0/180/270 deg; roll enclosure M3x12", 3)
    # hub details
    s += cyl(40.0, -2.5, xa, 0, P.Z_ALT, "X") - cyl(35.0, -5, xa + 1, 0, P.Z_ALT, "X")
    feat("pin", "80 h9 / 70", (xa, 0, P.Z_ALT), "-X", 2.5, "V-ring VA-80 seat ring (ST-218)")
    s -= cyl(22.5, 2.5, xa - 0.01, 0, P.Z_ALT, "X")
    feat("bore", "45 H7", (xa, 0, P.Z_ALT), "X", 2.5, "altitude reducer output pilot")
    s -= cyl(10.1, 3.0, xa + 2.5, 0, P.Z_ALT, "X")
    feat("bore", "20.2", (xa + 2.5, 0, P.Z_ALT), "X", 3.0, "encoder tube flange seat")
    s -= cyl(4.0, 20, xa - 1, 0, P.Z_ALT, "X")
    feat("thru", "8", (xa + t, 0, P.Z_ALT), "-X", None, "roll harness exit from the encoder tube")
    r = P.RED[17]
    for (u, v) in polar(r["n_tap"], r["pcd_tap"] / 2):
        s -= cyl(P.CLEAR["M3"] / 2, t + 1, xa - 0.5, u, P.Z_ALT + v, "X")
        s -= cyl(P.CBORE["M3"][0] / 2, P.CBORE["M3"][1] + 0.1, xa + t + 0.01, u, P.Z_ALT + v, "-X")
    feat("cbore", "3.4 / 6.0x3.3", (xa + t, 27, P.Z_ALT), "-X", None, "16x on PCD 54; output flange M3x10 ISO 4762", 16)
    for (u, v) in polar(2, 7.0, 90):
        s -= cyl(P.CLEAR["M3"] / 2, t + 1, xa - 0.5, u, P.Z_ALT + v, "X")
        s -= cyl(3.0, 1.9, xa + t + 0.01, u, P.Z_ALT + v, "-X")
    feat("cbore", "3.4 / 6.0x1.9", (xa + t, 0, P.Z_ALT + 7), "-X", None, "2x on PCD 14; encoder tube M3x5 ISO 7380", 2)
    s += cyl(3.0, -2.5, xa, pin[0], pin[1], "X")
    feat("pin", "6", (xa, pin[0], pin[1]), "-X", 2.5, "end-stop boss at R62, 296 deg; hits bumpers ST-322 (1 mm running gap to the tower)")
    # cable guide holes and lightening
    for (y, z) in [(-30, 186), (-30, 206)]:
        s -= cyl(P.TAP["M3"] / 2, t + 1, xa - 0.5, y, z, "X")
    feat("tap", "M3", (xa + t, -30, 186), "-X", None, "2x cable guide ST-320 fixings, pitch 20", 2)
    s -= plate_yz(Pos(-24, 176) * Circle(10.0), xa - 1, t + 2)
    s -= plate_xz(Pos(64, 173) * RectangleRounded(22, 34, 6), ypad + 1, t + 2)
    feat("pocket", "thru", (64, ypad, 173), "-Y", None, "lightening window 22 x 34")
    return s


# ============================================================================== ST-313 roll shelf
def build_shelf():
    xr, zr = P.X_ROLL, P.Z_ROLL
    y0, t = P.ROLL_OUT_Y, 10.0
    st = P.SHELF_TOP
    leg_f = _hull([Pos(xr, zr) * Circle(30), Pos(xr, zr + st - 5) * Rectangle(60, 10)])
    s = plate_xz(leg_f, y0 + t, t)                                             # Y -22..-12
    s += box(xr - 30, xr + 30, y0, 40, zr + st - 8, zr + st)                  # horizontal leg, 8 thick
    for sx in (-1, 1):                                                         # ribs
        rib = Polygon((y0 + t, zr - 2), (y0 + t, zr + st - 8), (32, zr + st - 8), align=None)
        pl = Plane(origin=(xr + sx * 24 - 3, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        s += extrude(pl * rib, 6, dir=(1, 0, 0))
    s += cyl(32.5, -2.5, xr, y0, zr, "Y") - cyl(27.5, -6, xr, y0 + 1, zr, "Y")
    feat("pin", "65 h9 / 55", (xr, y0, zr), "-Y", 2.5, "V-ring VA-65 seat ring (ST-219)")
    s -= cyl(18.0, 2.5, xr, y0 - 0.01, zr, "Y")
    feat("bore", "36 H7", (xr, y0, zr), "Y", 2.5, "roll reducer output pilot")
    s -= cyl(10.1, 3.0, xr, y0 + 2.5, zr, "Y")
    s -= cyl(3.25, 20, xr, y0 - 1, zr, "Y")
    feat("bore", "20.2", (xr, y0 + 2.5, zr), "Y", 3.0, "encoder tube flange seat")
    r = P.RED[14]
    for (u, v) in polar(r["n_tap"], r["pcd_tap"] / 2):
        s -= cyl(P.CLEAR["M3"] / 2, t + 1, xr + u, y0 - 0.5, zr + v, "Y")
        s -= cyl(P.CBORE["M3"][0] / 2, P.CBORE["M3"][1] + 0.1, xr + u, y0 + t + 0.01, zr + v, "-Y")
    feat("cbore", "3.4 / 6.0x3.3", (xr + 22, y0 + t, zr), "-Y", None, "12x on PCD 44; output flange M3x12", 12)
    for (u, v) in polar(2, 7.0, 90):
        s -= cyl(P.CLEAR["M3"] / 2, t + 1, xr + u, y0 - 0.5, zr + v, "Y")
        s -= cyl(P.CBORE["M3"][0] / 2, P.CBORE["M3"][1] + 0.1, xr + u, y0 + t + 0.01, zr + v, "-Y")
    feat("cbore", "3.4 / 6.0x3.3", (xr, y0 + t, zr + 7), "-Y", None, "2x on PCD 14; encoder tube M3x6 ISO 4762", 2)
    s -= cyl(5.1, 20, xr, P.CLAMP_CY, zr + st - 11, "Z")
    s -= cyl(9.5, 4.5, xr, P.CLAMP_CY, zr + st - 11, "Z")
    feat("cbore", "10.2 / 19x4.5", (xr, P.CLAMP_CY, zr + st - 10), "Z", None, "clamp 3/8\"-16 x 12 coin-slot screw (D36)")
    for dy in (-15, 15):
        s -= cyl(P.CLEAR["M4"] / 2, 20, xr, P.CLAMP_CY + dy, zr + st - 11, "Z")
    feat("thru", "4.5", (xr, P.CLAMP_CY + 15, zr + st), "-Z", None, "2x at +/-15 for clamps with M4 holes", 2)
    # D35: pocket under the horizontal leg, between the ribs, 4 mm skin under the clamp
    pk = Pos(xr, (y0 + t + 40) / 2) * RectangleRounded(36, 40 - (y0 + t) - 6, 3)
    pk -= Pos(xr, P.CLAMP_CY) * Circle(12.0)
    for dy in (-15, 15):
        pk -= Pos(xr, P.CLAMP_CY + dy) * Circle(5.0)
    s -= Pos(0, 0, zr + st - 8 - 0.01) * extrude(pk, 4.0)
    feat("pocket", "36 wide", (xr, 20, zr + st - 8), "Z", 4.0, "lightening pocket under the leg, between the ribs")
    return s


STRUCT_PARTS = [
    register(PartDef("ST-301", "Base plate with 3/8in-16 socket", "machined", "6061", 1, build_base,
                     finish=P.MAT["6061"]["finish"], tol="ISO 2768-m", group="3xx", color=(0.70, 0.71, 0.73),
                     notes=["Underside flat within 0.05.", "Break all edges 0.3."])),
    register(PartDef("ST-302", "Wedge lower plate with azimuth fine adjust", "machined", "6061", 1, build_wedge_lower,
                     finish=P.MAT["6061"]["finish"], tol="ISO 2768-m", group="3xx", color=(0.70, 0.71, 0.73),
                     notes=["Hinge bore 8 H7 in line through both knuckles.",
                            "Engrave azimuth scale +/-10 deg every 1 deg on the +X tab, 0.2 deep."])),
    register(PartDef("ST-303", "Wedge upper plate (azimuth reducer mount)", "machined", "6061", 1, build_wedge_upper,
                     finish=P.MAT["6061"]["finish"], tol="ISO 2768-m; pilot 45 H7 square to the base within 0.02",
                     group="3xx", color=(0.70, 0.71, 0.73),
                     notes=["Seat face for the reducer (Z 45) flat within 0.01 and parallel to the underside within 0.02.",
                            "V-ring seat 75 h9, Ra 0.8."])),
    register(PartDef("ST-305", "Wedge latitude arc", "machined", "6061", 2, build_arc,
                     finish=P.MAT["6061"]["finish"], tol="ISO 2768-m", group="3xx", color=(0.70, 0.71, 0.73),
                     notes=["Same part on both sides.", "Engrave latitude scale 15-90 deg every 5 deg along the slot, 0.2 deep."])),
    register(PartDef("ST-310", "Azimuth body (main housing)", "printed", "PA12-MJF", 1, build_body,
                     finish="MJF PA12, bead-blasted, dyed black", tol="MJF: +/-0.3 or 0.3 %", print_rot=(0, 0, 0), group="3xx",
                     color=(0.30, 0.31, 0.34),
                     notes=["Order from JLC3DP (MJF PA12, D29); 2.0 mm walls (W1, D35).",
                            "Fit 8 M3 (cover), 6 M3 (bezel), 2 M3 (connector), 4 M5 (tower), 2 M5 (counterweight) inserts."])),
    register(PartDef("ST-311", "Tower (altitude housing)", "printed", "PA12-MJF", 1, build_tower,
                     finish="MJF PA12, bead-blasted, dyed black; V-ring pad Ra 1.6", tol="MJF: +/-0.3 or 0.3 %", print_rot=(180, 0, 0),
                     group="3xx", color=(0.30, 0.31, 0.34),
                     notes=["Order from JLC3DP (MJF PA12, D29); 2.0 mm walls (W1, D35).",
                            "Sand the V-ring pad flat on 400 grit on glass."])),
    register(PartDef("ST-312", "Altitude arm", "machined", "6061", 1, build_arm, finish=P.MAT["6061"]["finish"],
                     tol="ISO 2768-m; pilot 45 H7; roll pad face square to the hub face within 0.03",
                     group="3xx", color=(0.72, 0.73, 0.76),
                     notes=["Machined from one block 160 x 90 x 190.", "Hub face flat within 0.01."])),
    register(PartDef("ST-313", "Roll shelf (L-arm) with clamp seat", "machined", "6061", 1, build_shelf,
                     finish=P.MAT["6061"]["finish"], tol="ISO 2768-m; pilot 36 H7; clamp seat parallel to the roll axis within 0.05",
                     group="3xx", color=(0.72, 0.73, 0.76))),
]
