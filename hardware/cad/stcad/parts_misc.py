"""Covers, battery bay, pack shell, gaskets and small TPU parts. World frame unless noted."""
import math
from build123d import Pos, Rot, Plane, extrude, Circle, Rectangle, RectangleRounded, Polygon, offset

from . import params as P
from .core import cyl, box, polar, register, PartDef, feat, hull_extrude
from .parts_struct import plate_yz, plate_xz, tower_face, TOWER_EARS, COVER_X, COVER_PTS

G = P.GASKET_T
XB0 = P.BODY_X_MIN - G - 3.0          # bezel outer face
XB1 = P.BODY_X_MIN - G                # bezel inner face
BZ = (50.0, 122.0)                    # bezel Z extent
BY = 59.0                             # bezel half width
YC = (P.BODY_Y_MIN + P.BODY_Y_MAX) / 2   # bezel / mainboard centre line (Y 15)
BOARD_ZC = 86.0                       # mainboard centre height
BOARD_X = P.BODY_X_MIN + 5.0          # mainboard outer face (OLED side)
BTN_Y = [YC - 36.0, YC - 25.0, YC - 14.0, YC - 3.0]
BTN_Z = BOARD_ZC - 18.0
USB_A = (YC + 25.0, BOARD_ZC - 15.35)
USB_B = (YC + 38.0, BOARD_ZC - 15.35)
JACK = (YC + 41.0, BOARD_ZC + 11.0)
LED = (YC + 37.5, BOARD_ZC + 19.5)
BEZEL_SCREWS = [(YC + y, z) for y in (-55.5, 55.5) for z in (58.0, 86.0, 114.0)]
BOARD_HOLES = [(YC + y, BOARD_ZC + dz) for y in (-46.0, 46.0) for dz in (-26.0, 26.0)]


# ============================================================================== ST-315 bezel
def build_bezel():
    f = RectangleRounded(2 * BY, BZ[1] - BZ[0], 6)
    s = plate_yz(Pos(YC, (BZ[0] + BZ[1]) / 2) * f, XB0, 3.0)
    s -= plate_yz(Pos(YC, BOARD_ZC + 16) * Rectangle(34, 18), XB0 - 1, 5)
    s -= plate_yz(Pos(YC, BOARD_ZC + 16) * RectangleRounded(38.4, 22.4, 1), XB0 - 0.01, 1.2)
    feat("opening", "34 x 18", (XB0, YC, BOARD_ZC + 16), "X", None, "OLED window; 38.4 x 22.4 x 1.2 recess for ST-326")
    for y in BTN_Y:
        s -= cyl(4.25, 6, XB0 - 1, y, BTN_Z, "X")
    feat("thru", "8.5", (XB0, BTN_Y[0], BTN_Z), "X", None, "4x buttons, pitch 11", 4)
    for (y, z) in (USB_A, USB_B):
        s -= plate_yz(Pos(y, z) * RectangleRounded(10.0, 4.6, 2.2), XB0 - 1, 5)
    feat("opening", "10 x 4.6", (XB0, USB_A[0], USB_A[1]), "X", None, "2x USB-C (A charge / B camera)", 2)
    s -= cyl(3.25, 6, XB0 - 1, JACK[0], JACK[1], "X")
    feat("thru", "6.5", (XB0, JACK[0], JACK[1]), "X", None, "2.5 mm shutter jack")
    s -= cyl(1.6, 6, XB0 - 1, LED[0], LED[1], "X")
    feat("thru", "3.2", (XB0, LED[0], LED[1]), "X", None, "status LED light pipe")
    for (y, z) in BEZEL_SCREWS:
        s -= cyl(P.CLEAR["M3"] / 2, 6, XB0 - 1, y, z, "X")
    feat("thru", "3.4", (XB0, BEZEL_SCREWS[3][0], 58), "X", None, "6x bezel screws M3x8 ISO 7380", 6)
    for (y, z) in BOARD_HOLES:
        s += cyl(3.5, BOARD_X - XB1, XB1, y, z, "X")
        s -= cyl(1.25, 6, BOARD_X - 5.5, y, z, "X")
    feat("tap", "2.5", (BOARD_X, YC + 46, BOARD_ZC + 26), "-X", 5.5, "4x mainboard bosses, M3x6 thread-forming", 4)
    s -= plate_yz(Pos(YC - 44, 118) * RectangleRounded(14, 3, 1), XB0 - 0.01, 0.4)
    return s


def build_button():
    """Local: axis along Z, outer face at Z=0, cap toward +Z (inward)."""
    s = cyl(3.9, 7.5)
    s += cyl(5.5, 1.2, z=6.3)
    feat("pin", "7.8", (0, 0, 0), "Z", 7.5, "plunger; flange 11 x 1.2 retains and seals")
    return s


# ============================================================================== ST-319 top cover
def build_cover():
    z0 = P.Z_BODY_TOP + G
    f = Pos((P.BODY_X_MIN + COVER_X[1] + 3) / 2, (P.BODY_Y_MIN + P.BODY_Y_MAX) / 2) * \
        RectangleRounded(COVER_X[1] + 3 - P.BODY_X_MIN, P.BODY_Y_MAX - P.BODY_Y_MIN, 12)
    s = Pos(0, 0, z0) * extrude(f, 3.0)
    s -= Pos(-120, 40, z0 - 0.01) * extrude(RectangleRounded(34, 34, 4), 1.5)
    feat("pocket", "34 x 34", (-120, 40, z0), "Z", 1.5, "GNSS window: 1.5 mm skin; patch antenna ST-512 stuck underneath")
    s -= Pos(-120, -20, z0 + 3 - 0.4) * extrude(RectangleRounded(26, 26, 2), 0.5)
    feat("pocket", "26 x 26", (-120, -20, z0 + 3), "-Z", 0.4, "QR label recess (ST-803)")
    for (x, y) in COVER_SCREWS:
        s -= cyl(P.CLEAR["M3"] / 2, 6, x, y, z0 - 1)
    feat("thru", "3.4", (COVER_SCREWS[0][0], COVER_SCREWS[0][1], z0 + 3), "-Z", None, "8x M3x10 ISO 7380", 8)
    s -= Pos(-138, 20, z0 + 2.6) * extrude(RectangleRounded(3, 30, 1), 0.5)
    s -= cyl(6.1, 2.5, -138, 62, z0 + 0.5)
    feat("pocket", "12.2", (-138, 62, z0 + 3), "-Z", 2.5, "bubble level ST-321, glued")
    return s


COVER_SCREWS = COVER_PTS


# ============================================================================== ST-317 battery tray, ST-318 door
PX0, PX1 = P.PACK_X0, P.PACK_X0 + P.PACK["W"]
PZ0 = P.PACK_Z0
YD = P.BODY_Y_MAX + G                 # door inner face


def build_tray():
    s = box(PX0 - 1.8, PX1 + 1.8, P.PACK_Y0 - 2, YD - 2, PZ0 - 2.0, PZ0)
    for x in (PX0 - 1.8, PX1 + 0.2):
        s += box(x, x + 1.6, P.PACK_Y0 - 2, YD - 6, PZ0, PZ0 + 18)
    s += box(PX0 - 1.8, PX1 + 1.8, YD - 4, YD - 2, PZ0 - 2.0, PZ0 + 18)       # front flange
    s += box(PX0 - 1.8, PX1 + 1.8, P.PACK_Y0 - 2, P.PACK_Y0, PZ0, PZ0 + 4)     # rear stop lip
    for x in (PX0 + 10, PX1 - 10):
        s -= cyl(P.CLEAR["M3"] / 2, 6, x, YD - 5, PZ0 + 9, "Y")
    feat("thru", "3.4", (PX0 + 10, YD - 2, PZ0 + 9), "-Y", None, "2x to the door, M3x8 ISO 7380", 2)
    s -= Pos((PX0 + PX1) / 2, 40, PZ0 - 2.1) * extrude(RectangleRounded(30, 60, 6), 3)
    return s


def build_door():
    xc = (PX0 + PX1) / 2
    s = box(xc - 31, xc + 31, YD, YD + 3, PZ0 - 7, PZ0 + P.PACK["H"] + 9)
    s += box(xc - 14, xc + 14, YD + 3, YD + 7, PZ0 + 18, PZ0 + 30)              # finger grip
    for x in (PX0 + 8, PX1 - 8):                                               # snap hooks
        s += box(x - 3.5, x + 3.5, YD - P.BODY_WALL - 1.5, YD, PZ0 + P.PACK["H"] + 5.5, PZ0 + P.PACK["H"] + 7.5)
        s += box(x - 3.5, x + 3.5, YD - P.BODY_WALL - 2.5, YD - P.BODY_WALL - 1.5, PZ0 + P.PACK["H"] + 5.5,
                 PZ0 + P.PACK["H"] + 9.0)
    feat("snap", "7 x 2", (PX0 + 8, YD, PZ0 + P.PACK["H"] + 6.5), "-Y", P.BODY_WALL + 2.5, "2x snap hooks; press to release", 2)
    for x in (PX0 + 10, PX1 - 10):
        s -= cyl(1.25, 2.9, x, YD - 0.01, PZ0 + 9, "Y")
    feat("tap", "2.5", (PX0 + 10, YD, PZ0 + 9), "Y", 2.9, "2x tray screws, thread-forming M3x8", 2)
    return s


# ============================================================================== pack: ST-605 lower, ST-612 upper
PK_Y1 = P.PACK_Y0 + P.PACK["L"]
PK_ZM = PZ0 + 24.5                     # split plane (lower shell top)
PK_CX, PK_CZ = (PX0 + PX1) / 2, PZ0 + P.PACK['H'] / 2
PK_W = P.PACK["wall"]
PK_BOSS = [(PX0 + 4.5, P.PACK_Y0 + 6), (PX1 - 4.5, P.PACK_Y0 + 6), (PX0 + 4.5, PK_Y1 - 6), (PX1 - 4.5, PK_Y1 - 6)]
# Battery board ST-602 (decision D58, was Q38): it stands 1.6 mm behind the +Y cell holder, its bottom and top edges in
# the grooves of one rib on the floor of the lower shell and one under the roof of the upper shell. No screws.
PK_YB = P.PACK_Y0 + PK_W + 12.0 + 3.0 + P.CELL_L + 3.0 + 1.6      # the board's inner face
RIB_W, RIB_GROOVE, RIB_IN, RIB_WALL = 7.0, 1.7, 2.0, 1.45          # rib width, groove width, depth the board sits in, wall each side


def _board_rib(z_edge, up):
    """Grooved rib for one edge of the battery board. z_edge: the board edge; up: the rib stands on the floor (True)
    or hangs from the roof (False)."""
    y0 = PK_YB + P.BATT_BOARD["T"] / 2 - RIB_GROOVE / 2
    z_wall = PZ0 + PK_W if up else PZ0 + P.PACK["H"] - PK_W
    z_tip = z_edge + RIB_IN if up else z_edge - RIB_IN
    rib = box(PK_CX - RIB_W / 2, PK_CX + RIB_W / 2, y0 - RIB_WALL, y0 + RIB_GROOVE + RIB_WALL, min(z_wall, z_tip), max(z_wall, z_tip))
    z_g = z_edge - 0.2 if up else z_edge + 0.2                       # 0.2 mm under / over the board edge
    rib -= box(PK_CX - RIB_W / 2 - 1, PK_CX + RIB_W / 2 + 1, y0, y0 + RIB_GROOVE, min(z_g, z_tip + (1 if up else -1)), max(z_g, z_tip + (1 if up else -1)))
    return rib


def _shell(z0, z1, open_top):
    s = box(PX0, PX1, P.PACK_Y0, PK_Y1, z0, z1)
    if open_top:
        s -= box(PX0 + PK_W, PX1 - PK_W, P.PACK_Y0 + PK_W, PK_Y1 - PK_W, z0 + PK_W, z1 + 1)
    else:
        s -= box(PX0 + PK_W, PX1 - PK_W, P.PACK_Y0 + PK_W, PK_Y1 - PK_W, z0 - 1, z1 - PK_W)
    for (x, y) in PK_BOSS:
        s += cyl(3.5, z1 - z0, x, y, z0)
    return s


def build_pack_lower():
    s = _shell(PZ0, PK_ZM, True)
    for (x, y) in PK_BOSS:
        s -= cyl(P.CLEAR["M3"] / 2, 40, x, y, PZ0 - 1)
        s -= cyl(3.0, 3.0, x, y, PZ0 - 0.01)
    feat("cbore", "3.4 / 6x3", (PK_BOSS[0][0], PK_BOSS[0][1], PZ0), "Z", None, "4x M3x30 ISO 4762, pack closing screws", 4)
    s -= box(-10 + (PX0 + PX1) / 2, 10 + (PX0 + PX1) / 2, P.PACK_Y0 - 1, P.PACK_Y0 + PK_W + 1, PK_ZM - 8, PK_ZM + 1)
    feat("opening", "20 x 8", ((PX0 + PX1) / 2, P.PACK_Y0, PK_ZM - 4), "Y", None, "blade connector, lower half")
    s -= box(PX0 + 6, PX1 - 6, P.PACK_Y0 + 20, PK_Y1 - 20, PZ0 - 0.01, PZ0 + 0.6)
    s += _board_rib(PK_CZ - P.BATT_BOARD["H"] / 2, True)
    feat("slot", "1.7 x 7", (PK_CX, PK_YB + 0.8, PK_CZ - P.BATT_BOARD["H"] / 2), "Z", RIB_IN, "grooved rib: bottom edge of the battery board ST-602")
    return s


def build_pack_upper():
    s = _shell(PK_ZM + G, PZ0 + P.PACK["H"], False)
    for (x, y) in PK_BOSS:
        s -= cyl(P.INSERT["M3"][0] / 2, P.INSERT["M3"][1], x, y, PK_ZM + G - 0.01)
    feat("insert", "M3", (PK_BOSS[0][0], PK_BOSS[0][1], PK_ZM + G), "Z", 6, "4x closing screw inserts", 4)
    s -= box(-10 + (PX0 + PX1) / 2, 10 + (PX0 + PX1) / 2, P.PACK_Y0 - 1, P.PACK_Y0 + PK_W + 1, PK_ZM + G - 1, PK_ZM + G + 4)
    s -= box(PX0 + 10, PX1 - 10, PK_Y1 - PK_W - 1, PK_Y1 + 1, PZ0 + 34, PZ0 + 42)
    feat("opening", "30 x 8", ((PX0 + PX1) / 2, PK_Y1, PZ0 + 38), "-Y", None, "light pipe / button ST-611")
    s -= Pos((PX0 + PX1) / 2, 44, PZ0 + P.PACK["H"] - 0.4) * extrude(RectangleRounded(30, 40, 3), 0.5)
    s += _board_rib(PK_CZ + P.BATT_BOARD["H"] / 2, False)
    feat("slot", "1.7 x 7", (PK_CX, PK_YB + 0.8, PK_CZ + P.BATT_BOARD["H"] / 2), "-Z", RIB_IN, "grooved rib: top edge of the battery board ST-602")
    return s


def build_cell_holder():
    """End holder, one at each end of the cells. Local: XZ plate, centre of the 2x2 group at origin, Y 0..3."""
    s = box(-22.5, 22.5, 0, 3, -22.5, 22.5)
    for (dx, dz) in [(-11.1, -11.1), (11.1, -11.1), (-11.1, 11.1), (11.1, 11.1)]:
        s -= cyl(10.95, 2.0, dx, 1.0, dz, "Y")
        s -= cyl(8.0, 5, dx, -1, dz, "Y")
    feat("pocket", "21.9", (11.1, 1, 11.1), "Y", 2.0, "4x cell pockets; 16 mm windows for the nickel strip", 4)
    # wire passages (decision D60, was Q40): PACK+ on one side; PACK-, the three bus wires, the middle tap and the
    # thermistor leads on the other
    for sx in (-1, 1):
        s -= box(min(sx * 19.5, sx * 22.6), max(sx * 19.5, sx * 22.6), -1, 4, -3, 3)
    feat("notch", "6 x 3", (22.5, 1.5, 0), "X", 3.0, "2x wire passage at mid-height, left and right edge", 2)
    return s


def build_pack_gasket():
    f = Rectangle(P.PACK["W"], P.PACK["L"]) - Rectangle(P.PACK["W"] - 2 * PK_W, P.PACK["L"] - 2 * PK_W)
    s = Pos((PX0 + PX1) / 2, (P.PACK_Y0 + PK_Y1) / 2, PK_ZM) * extrude(f, G)
    for (x, y) in PK_BOSS:
        s += cyl(3.5, G, x, y, PK_ZM) - cyl(1.8, G + 1, x, y, PK_ZM - 0.5)
    return s


LP_LEN = PK_Y1 - (PK_YB + P.BATT_BOARD["T"]) - 2.0      # the pipe ends 2.0 mm before the board face (decision D59, was Q39)


def build_light_pipe():
    """Local: outer face at Y=0, the pipe runs -Y into the pack and ends 2.0 mm before the battery board. It slides
    0.3 mm in its window: the flat boss on its inner end then presses the gauge button (1.5 mm tall), whose spring
    pushes it back. A flange behind the wall keeps it in; the TPU lip on the flange closes the window."""
    s = box(-14.6, 14.6, -LP_LEN, 0, -3.6, 3.6)
    s += box(-3, 3, 0, 0.8, -3, 3)                                    # finger nub outside
    s += box(-16.6, 16.6, -PK_W - 1.5, -PK_W - 0.5, -5.6, 5.6)         # flange, 0.5 mm behind the wall's inner face
    lip = box(-16.6, 16.6, -PK_W - 0.5, -PK_W, -5.6, 5.6) - box(-15.4, 15.4, -PK_W - 1, 0, -4.4, 4.4)
    s += lip                                                          # TPU lip, 0.5 mm, printed onto the flange
    s += box(-2.5, 2.5, -LP_LEN - 0.2, -LP_LEN, -2.5, 2.5)             # boss over the button: 0.3 mm from its top
    feat("pin", "29.2 x 7.2", (0, 0, 0), "-Y", LP_LEN, "clear PETG; slides 0.3 mm in the shell window to press the gauge button")
    feat("flange", "33.2 x 11.2 x 1.0", (0, -PK_W - 1.0, 0), "-Y", 1.0, "behind the wall; TPU 95A lip 1.2 wide x 0.5 printed on its outer face")
    feat("boss", "5 x 5 x 0.2", (0, -LP_LEN, 0), "-Y", 0.2, "flat boss over the gauge button SW1")
    return s


# ============================================================================== gaskets
def build_tower_gasket():
    T = tower_face()
    s = Pos(0, 0, P.Z_BODY_TOP) * extrude(T - offset(T, -P.TOWER_WALL), G)
    for (x, y) in TOWER_EARS:
        s += cyl(7.0, G, x, y, P.Z_BODY_TOP) - cyl(2.8, G + 1, x, y, P.Z_BODY_TOP - 0.5)
    return s


def build_cover_gasket():
    z0 = P.Z_BODY_TOP
    f = Pos((P.BODY_X_MIN + COVER_X[1] + 3) / 2, (P.BODY_Y_MIN + P.BODY_Y_MAX) / 2) * \
        RectangleRounded(COVER_X[1] + 3 - P.BODY_X_MIN, P.BODY_Y_MAX - P.BODY_Y_MIN, 12)
    s = Pos(0, 0, z0) * extrude(f - offset(f, -4.0), G)
    for (x, y) in COVER_SCREWS:
        s += cyl(4.0, G, x, y, z0) - cyl(1.8, G + 1, x, y, z0 - 0.5)
    return s


def build_door_gasket():
    xc = (PX0 + PX1) / 2
    f = Pos(xc, PZ0 + 26) * (RectangleRounded(62, 66, 3) - Rectangle(54, 58))
    s = plate_xz(f, YD, G)
    for x in (PX0 + 8, PX1 - 8):
        s -= box(x - 4, x + 4, YD - 2, YD + 1, PZ0 + P.PACK["H"] + 5, PZ0 + P.PACK["H"] + 8)
    return s


def build_bezel_gasket():
    f = Pos(YC, (BZ[0] + BZ[1]) / 2) * (RectangleRounded(2 * BY, BZ[1] - BZ[0], 6) - Rectangle(103, 66))
    s = plate_yz(f, XB1, G)
    for (y, z) in BEZEL_SCREWS:
        s -= cyl(1.8, 3, XB1 - 1, y, z, "X")
    return s


# ============================================================================== ST-217 roll enclosure + ST-328 gasket
RE_Y0 = -45.0 - G                       # enclosure front face (behind the arm pad and its gasket)
RE_D = 92.0
RE_SCREWS = [(54.0, a) for a in (0.0, 180.0, 270.0)]


def build_roll_enclosure():
    """Shell over the roll cartridge's input end. Front wall seals on the arm pad (ST-328) and, at its
    bore, on the cartridge sleeve (O-ring ST-329). Top flattened under the clamp seat."""
    from build123d import make_hull
    xr, zr = P.X_ROLL, P.Z_ROLL
    b = P.ROLL_CART_ROT
    motor = Pos(xr, zr) * Rot(0, 0, -b) * Pos(0, -64.0) * RectangleRounded(70, 52, 6)
    f = make_hull((Pos(xr, zr) * Circle(58.0)).edges() + motor.edges())
    wall = 1.8
    s = plate_xz(f, RE_Y0, RE_D)
    s -= plate_xz(offset(f, -wall), RE_Y0 - wall, RE_D - 2 * wall)
    s -= box(xr - 90, xr + 90, RE_Y0 - RE_D - 1, RE_Y0 + 1, zr + 43.3, zr + 90)        # flat top under the clamp seat
    s += box(xr - 45, xr + 45, RE_Y0 - RE_D, RE_Y0, zr + 41.5, zr + 43.3) & plate_xz(f, RE_Y0, RE_D)
    s -= cyl(41.6, 5, xr, RE_Y0 + 1, zr, "-Y")
    s -= cyl(43.2, 1.6, xr, RE_Y0 - 0.0, zr, "-Y")
    feat("bore", "83.2 / groove 86.4 x 1.6", (xr, RE_Y0, zr), "-Y", None,
         "bore on the cartridge sleeve (82); O-ring 80 x 2 ST-329 in the front groove")
    for (r, a) in RE_SCREWS:
        x, z = xr + r * math.cos(math.radians(a)), zr + r * math.sin(math.radians(a))
        s += cyl(4.0, 7.0, x, RE_Y0, z, "-Y")
        s -= cyl(P.INSERT["M3"][0] / 2, 6.0, x, RE_Y0 + 0.01, z, "-Y")
    feat("insert", "M3", (xr + 54, RE_Y0, zr), "-Y", 6, "3x at R54, 0/180/270 deg; M3x12 from the arm pad front", 3)
    s -= cyl(4.0, 12, xr - 64, -60, 160, "X")
    feat("thru", "8", (xr - 58, -60, 160), "X", None, "roll harness grommet")
    feat("shell", "1.8 wall", (xr, RE_Y0 - RE_D, zr), "Y", None, "4 perimeters; print front face down")
    return s


def build_roll_enclosure_gasket():
    xr, zr = P.X_ROLL, P.Z_ROLL
    f = Pos(xr, zr) * (Circle(58.0) - Circle(49.0))
    s = plate_xz(f, -45.0, G)
    s -= box(xr - 70, xr + 70, -47, -44, zr + 41.0, zr + 80)
    s -= cyl(0.01, 0.01)
    for (r, a) in RE_SCREWS:
        x, z = xr + r * math.cos(math.radians(a)), zr + r * math.sin(math.radians(a))
        s -= cyl(1.8, 4, x, -44, z, "-Y")
    return s


# ============================================================================== small TPU parts
def build_cable_guide():
    """Local: base on Z=0, channel along X."""
    s = box(-15, 15, -6, 6, 0, 9)
    s -= box(-16, 16, -3.5, 3.5, 1.5, 7.5)
    s -= box(-16, 16, -2.0, 2.0, 7.0, 10)
    for x in (-10.0, 10.0):
        s -= cyl(1.7, 12, x, 0, -1)
    feat("thru", "3.4", (10, 0, 9), "-Z", None, "2x M3x12 ISO 7380, pitch 20 (pull the TPU over the head)", 2)
    feat("slot", "7 x 6", (0, 0, 1.5), "X", None, "harness channel, snap-in opening 4 wide")
    return s


def build_bumper():
    s = box(-5, 5, -5, 5, 0, 2.5)
    s -= cyl(1.7, 5, z=-1)
    s -= cyl(3.0, 1.2, z=1.31)
    feat("cbore", "3.4 / 6x1.2", (0, 0, 2.5), "-Z", None, "M3x5 ISO 7380 (head sits 0.1 below the face)")
    return s


MISC_PARTS = [
    register(PartDef("ST-315", "Front bezel with OLED window", "printed", "ASA", 1, build_bezel, finish="As printed, outer face textured plate",
                     tol="Printed: +/-0.2", print_rot=(0, 90, 0), group="3xx", color=(0.12, 0.12, 0.13),
                     notes=["Print outer face down on the textured plate.", "Glue window ST-326 into the recess (clear silicone)."])),
    register(PartDef("ST-316", "Button cap", "printed", "TPU", 4, build_button, finish="As printed", tol="Printed: +/-0.1",
                     print_rot=(180, 0, 0), group="3xx", color=(0.85, 0.20, 0.15))),
    register(PartDef("ST-317", "Battery bay tray", "printed", "ASA", 1, build_tray, finish="As printed", tol="Printed: +/-0.2",
                     print_rot=(0, 0, 0), group="3xx", color=(0.30, 0.30, 0.32))),
    register(PartDef("ST-318", "Battery door with snap latch", "printed", "ASA", 1, build_door, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(-90, 0, 0), group="3xx", color=(0.12, 0.12, 0.13),
                     notes=["Print outer face down; hooks print vertical so the layers run along the flex."])),
    register(PartDef("ST-319", "Top cover with GNSS window", "printed", "ASA", 1, build_cover, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(180, 0, 0), group="3xx", color=(0.12, 0.12, 0.13))),
    register(PartDef("ST-320", "Cable guide / strain relief", "printed", "TPU", 3, build_cable_guide, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 0, 0), group="3xx", color=(0.85, 0.20, 0.15))),
    register(PartDef("ST-322", "End-stop bumper (altitude)", "printed", "TPU", 2, build_bumper, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 0, 0), group="3xx", color=(0.85, 0.20, 0.15))),
    register(PartDef("ST-323", "Gasket, body to tower", "printed", "TPU", 1, build_tower_gasket, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 0, 0), group="3xx", color=(0.10, 0.10, 0.10))),
    register(PartDef("ST-324", "Gasket, top cover", "printed", "TPU", 1, build_cover_gasket, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 0, 0), group="3xx", color=(0.10, 0.10, 0.10))),
    register(PartDef("ST-325", "Gasket, battery door", "printed", "TPU", 1, build_door_gasket, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(90, 0, 0), group="3xx", color=(0.10, 0.10, 0.10))),
    register(PartDef("ST-327", "Gasket, bezel", "printed", "TPU", 1, build_bezel_gasket, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 90, 0), group="3xx", color=(0.10, 0.10, 0.10))),
    register(PartDef("ST-217", "Roll cartridge enclosure", "printed", "ASA", 1, build_roll_enclosure, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(-90, 0, 0), group="2xx", color=(0.22, 0.23, 0.25),
                     notes=["Print front face down (on the bed); 4 walls, 15 % infill is enough for a cover.",
                            "Fit 3 M3 heat-set inserts; grommet for the roll harness in the -X wall."])),
    register(PartDef("ST-328", "Gasket, roll enclosure", "printed", "TPU", 1, build_roll_enclosure_gasket, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(90, 0, 0), group="2xx", color=(0.10, 0.10, 0.10))),
    register(PartDef("ST-605", "Pack shell, lower half", "printed", "ASA", 1, build_pack_lower, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 0, 0), group="6xx", color=(0.95, 0.55, 0.10))),
    register(PartDef("ST-612", "Pack shell, upper half", "printed", "ASA", 1, build_pack_upper, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(180, 0, 0), group="6xx", color=(0.95, 0.55, 0.10))),
    register(PartDef("ST-606", "Cell holder (end)", "printed", "ASA", 2, build_cell_holder, finish="As printed",
                     tol="Printed: +/-0.15", print_rot=(-90, 0, 0), group="6xx", color=(0.30, 0.30, 0.32))),
    register(PartDef("ST-610", "Pack gasket", "printed", "TPU", 1, build_pack_gasket, finish="As printed",
                     tol="Printed: +/-0.2", print_rot=(0, 0, 0), group="6xx", color=(0.10, 0.10, 0.10))),
    register(PartDef("ST-611", "Pack light pipe + button", "printed", "PETG", 1, build_light_pipe, finish="As printed, clear",
                     tol="Printed: +/-0.1", print_rot=(-90, 0, 0), group="6xx", color=(0.85, 0.90, 0.95))),
]
