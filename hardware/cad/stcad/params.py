"""Star Tracker Project - Phase 3 shared parameters.

Every dimension used by more than one part lives here. Units: mm, kg, degrees.

Frames
------
WORLD / BODY frame (wedge flat, azimuth 0):  origin on the azimuth axis at the top face of the
tripod plate (= underside of the base plate ST-301). +Z up along the azimuth axis. The altitude
axis is parallel to +X and the payload hangs on the +X side of the tower. At altitude 0 the lens
points along +Y.

Values marked SPEC come from docs/02-engineering-spec.md rev C, section 2.3. Values marked
Items tagged D34-D38 are Phase 3 decisions approved by Bruno (docs/02-decisions-log.md). Values marked DS come from a datasheet (sources in the design doc).
"""
import math
import os

REV = "C"
DATE = "2026-11-22"

# ---------------------------------------------------------------------------------------------
# Layout (spec section 2.3); roll offset from the D31 study (D34)
# ---------------------------------------------------------------------------------------------
PAYLOAD_OFFSET_BASE = 112.5          # SPEC: payload plane to azimuth axis
D31_EXTRA_OFFSET = float(os.environ.get("ST_D31_EXTRA", 23.0))   # D34 (Q17 approved): D31 study, option A
X_ROLL = PAYLOAD_OFFSET_BASE + D31_EXTRA_OFFSET   # roll axis / lens axis X position = 135.5
FOOT_H = 85.0                        # SPEC: lens axis to underside of the 200-600 foot (to be measured)
R_CLAMP_SEAT = 45.0                  # SPEC: roll axis to clamp seat (top of clamp jaws)
D_ROLL_LENS = R_CLAMP_SEAT + FOOT_H  # 130: lens axis above roll axis
E_ALT = 80.0                         # SPEC: roll axis below altitude axis
Z_ALT = 225.0                        # SPEC: altitude axis above the tripod plate, wedge flat
Z_ROLL = Z_ALT - E_ALT               # 145
Z_LENS = Z_ROLL + D_ROLL_LENS        # 275

# Wedge and base stack (spec: wedge and base 45 mm)
Z_BASE_TOP = 8.0                     # base plate ST-301, 8 thick
Z_LOWER_TOP = 18.0                   # wedge lower plate ST-302, 10 thick; 4 mm rest pads above
Z_UPPER_BOT = 22.0                   # wedge upper plate ST-303 rests on 2 mm pads
Z_UPPER_PLATE_TOP = 30.0             # plate 8 thick, centre boss rises to Z_AZ_OUT
Z_AZ_OUT = 45.0                      # azimuth reducer output face (SPEC: 45)
WEDGE_HINGE_X = -62.0                # hinge axis (parallel to Y), on the battery side, outside the drip skirt
WEDGE_HINGE_Z = 37.0                 # raised so the latitude arcs hang below it (D38)
WEDGE_ARC_R = 31.0                   # clamp radius on the arcs (D38; D21 asked 34'/turn)
WEDGE_ARC_RIN, WEDGE_ARC_ROUT = 22.0, 36.0
WEDGE_CLAMP_ANG = 10.0               # clamp point, deg above the hinge line toward +X
WEDGE_TILT_MAX = 75.0                # D21
WEDGE_W = 92.0                       # plate size along Y (arcs bolt to the side faces)
WEDGE_L = 104.0                      # plate size along X (centred on the azimuth axis)
BASE_D = 96.0

# Azimuth body ST-310 and tower ST-311
BODY_GAP = 1.5                       # labyrinth gap above ST-303 boss
Z_BODY_BOT = Z_AZ_OUT + BODY_GAP     # 46.5
Z_BODY_TOP = 125.0                   # tower sits here (body taller than spec: D32 motor + 60 mm board)
BODY_WALL = 2.0                      # W1 (D35): MJF PA12, 2.0 mm walls
BODY_X_MIN = -152.0                  # far end (bezel)
BODY_FRONT_R = 64.0                  # payload-side radius (spec <= 50 at the original offset; see study)
BODY_Y_MIN = -58.0
BODY_Y_MAX = 88.0
TOWER_X_MIN = -76.0
TOWER_X_MAX = 42.5                   # SPEC: tower half-width 42.5 on the payload side
TOWER_Y_MIN = -52.0
TOWER_Y_MAX = 85.0
TOWER_TOP = Z_ALT + 53.0             # cartridge ring top Z_ALT+47, 3 mm skin, 3 mm air
TOWER_WALL = 2.0                     # W1 (D35)
GASKET_T = 1.0                       # flat TPU gaskets under tower, cover, bezel, door

# Altitude arm ST-312 (6061) - L-bracket: hub plate (YZ) + roll pad plate (XZ)
ALT_OUT_X = 46.0                     # altitude reducer output face (faces +X)
ARM_T = 8.0                          # plate thickness
ARM_HUB_R = 42.0                     # covers the VA-80 V-ring seat ring
ARM_PAD_R = 60.0                     # pad outline radius about the roll axis
SHELF_CANT = 30.0                    # D37: roll output face to clamp centre (spec 75)
ROLL_OUT_Y = -22.0                   # roll reducer output face (faces +Y)
ROLL_CART_ROT = 20.0                 # roll motor direction: from straight down, turned toward the tower (camera vs body sweep)
LENS_MOUNT_Y_BAL = None
CLAMP_CY = ROLL_OUT_Y + SHELF_CANT   # clamp centre Y = +8
FOOT_CY = CLAMP_CY + 41.0            # lens foot centre when the rig is balanced (computed in checks)
FOOT_L = 100.0                       # Arca foot plate length (assumed)

# ---------------------------------------------------------------------------------------------
# Bought parts (DS). Reducer envelopes: Harmonic Drive SHF-2UH outline (Laifual says LHT is
# interchangeable with SHF); confirm against Laifual's LHT-III drawing on order.
# ---------------------------------------------------------------------------------------------
RED = {
    17: dict(D=84.0, D_out=62.0, D_pilot=45.0, L_pilot=2.0, L_flange=6.0, L_house=42.5, L_stub=6.5,
             D_stub=25.0, bore=19.0, n_hole=12, pcd_hole=74.0, d_hole=3.5, n_tap=16, pcd_tap=54.0,
             mass=1.00, name="Laifual LHT-17-100-U-III"),
    14: dict(D=74.0, D_out=52.0, D_pilot=36.0, L_pilot=2.0, L_flange=6.0, L_house=38.5, L_stub=6.5,
             D_stub=20.0, bore=14.0, n_hole=8, pcd_hole=64.0, d_hole=3.5, n_tap=12, pcd_tap=44.0,
             mass=0.71, name="Laifual LHT-14-100-U-III"),
}
for _s, _r in RED.items():
    _r["L_body"] = _r["L_flange"] + _r["L_house"]          # output face to input-side housing face
    _r["L_total"] = _r["L_pilot"] + _r["L_body"] + _r["L_stub"]

NEMA = dict(W=42.3, chamfer=4.0, pilot_d=22.0, pilot_h=2.0, shaft_d=5.0, shaft_l=24.0, hole_sq=31.0,
            hole="M3", conn_w=16.0, conn_h=7.0, conn_d=10.0)
MOTOR = {
    "38": dict(L=38.0, mass=0.28, name="StepperOnline 17HE15-1504S"),
    "48": dict(L=48.0, mass=0.39, name="StepperOnline 17HS19-2004S1"),
}

# GT2 belt stage (D23): 20T / 60T, 9 mm, 200 mm closed loop
GT2_PITCH = 2.0
Z_SMALL, Z_LARGE = 20, 60
PD_SMALL = Z_SMALL * GT2_PITCH / math.pi          # 12.73
PD_LARGE = Z_LARGE * GT2_PITCH / math.pi          # 38.20
BELT_L = 200.0
BELT_W = 9.0


def belt_centre(L=BELT_L, D=PD_LARGE, d=PD_SMALL):
    """Solve L = 2C + pi(D+d)/2 + (D-d)^2/4C for C."""
    a = 2.0
    b = math.pi * (D + d) / 2 - L
    c = (D - d) ** 2 / 4
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


BELT_C = belt_centre()                              # 58.62
PULLEY60 = dict(OD=PD_LARGE - 0.508, flange_d=42.0, w_teeth=10.0, hub_d=32.0, hub_h=4.0, bolt_n=4,
                bolt="M3", mass=0.030)
PULLEY20 = dict(OD=PD_SMALL - 0.508, flange_d=18.0, w_teeth=10.0, hub_d=13.0, hub_h=6.0, mass=0.008)

# Cartridge local frame: origin on the reducer axis at the OUTPUT face, +Z toward the input side.
CART = {}
for _s in (17, 14):
    r = RED[_s]
    z_stub_end = r["L_body"] + r["L_stub"]
    CART[_s] = dict(
        z_stub_end=z_stub_end,
        z_belt=z_stub_end + 1.0 + PULLEY60["w_teeth"] / 2,          # belt centre plane
        z_motor_plate=z_stub_end + 1.0 + PULLEY60["w_teeth"] + PULLEY20["hub_h"] + 1.0,
        plate_t=4.0,
        ring_wall=4.0,
        ear_pcd=(108.0 if _s == 17 else 96.0),
        ear_n=4,
        ear_t=9.0,
    )
    CART[_s]["z_motor_face"] = CART[_s]["z_motor_plate"] + CART[_s]["plate_t"]
    CART[_s]["z_magnet"] = z_stub_end + 1.0 + PULLEY60["w_teeth"] + 11.0   # above the cable window
    CART[_s]["z_board"] = CART[_s]["z_magnet"] + 2.0                      # board underside
    CART[_s]["z_cover_top"] = CART[_s]["z_board"] + 1.6 + 8.0

# D39: flange 28 / screws on PCD 22 so the head base keeps a central 3/8"-16 socket under the azimuth tube
ENC_TUBE = dict(OD=10.0, ID=6.5, flange_d=28.0, screw_pcd=22.0, flange_t=3.0, solid_end=6.0, slot_w=4.0, slot_l=12.0,
                magnet_d=6.0, magnet_h=2.5)
ENC_BOARD_D = 30.0
ENC_BOARD_HOLE_PCD = 23.0
MAINBOARD = dict(W=100.0, H=60.0, T=1.6, hole_inset=4.0, comp_h=12.0)
BATT_BOARD = dict(W=32.0, H=40.0, T=1.6)

# Arca clamp ST-314, W5 (D35): Sunwayfoto DDC-60i, jaw 60, 81 wide over the knob, 13 high, 70.9 g (B&H)
CLAMP = dict(L=60.0, W=62.0, H=13.0, mass=0.071, knob_d=14.0, knob_l=19.0)
SHELF_TOP = R_CLAMP_SEAT - CLAMP["H"]   # shelf top above the roll axis, keeps D20 (clamp seat 45 mm)

# Battery (D8): 2S2P Molicel P50B 21700
CELL_D, CELL_L, CELL_M = 21.7, 70.4, 0.070
PACK = dict(W=50.0, H=50.0, L=103.0, wall=2.4)    # shell outside: X x Z x Y (connector, 2 holders, cells, board)
PACK_X0 = -131.0                                 # pack outer -X face (clear of mainboard parts)
PACK_Z0 = Z_BODY_BOT + BODY_WALL + 4.5           # pack underside (rails 2.5 + tray floor 2)
PACK_Y0 = BODY_Y_MAX - BODY_WALL - 1.0 - 103.0   # pack -Y end (connector end)

# Reference rig envelope (A7R V + FE 200-600 on its foot). Sony data; mount offset assumed.
LENS = dict(D=111.5, L=318.0, hood_L=7.0, mass=2.115)
CAMERA = dict(W=131.3, H=96.9, D=82.4, body_depth=62.0, mass=0.723,
              mount_from_tower_side=58.0,    # ASSUMPTION: lens axis 58 mm from the tower-side edge
              axis_above_bottom=46.0)        # ASSUMPTION: lens axis 46 mm above the camera base
LENS_MOUNT_Y = -84.0                         # legacy (rev A/B): camera mount plane for the 200-600 rig

# Payload envelopes (rev C): the head is checked against a family of payloads, not one lens.
# D, L = lens / tube envelope (dew shield included); H = optical axis above the clamp seat; mount = what sits
# in the Arca clamp; cam = mirrorless body (box) or astro camera + flattener (cylinder D x L); kg = whole payload.
RIGS = {
    "P1": dict(name="Mirrorless + standard zoom on an Arca L-plate", D=88.0, L=120.0, ota_kg=0.70, cam="mirrorless",
               H=56.0, mount="plate", mount_L=70.0, kg=1.55),
    "P2": dict(name="Mirrorless + 70-200 f/2.8 on its collar", D=88.0, L=200.0, ota_kg=1.12, cam="mirrorless",
               H=70.0, mount="foot", mount_L=80.0, kg=1.95, collar_D=118.3),
    "P3": dict(name="Mirrorless + 150-600 class lens on its foot", D=121.0, L=320.0, ota_kg=2.90, cam="mirrorless",
               H=90.0, mount="foot", mount_L=100.0, kg=3.75),
    "P4": dict(name="72 mm class refractor + astro camera", D=95.0, L=420.0, ota_kg=1.96, cam="astro", cam_D=80.0,
               cam_L=110.0, cam_kg=0.60, H=75.0, mount="dovetail", mount_L=200.0, kg=2.70),
    "P5": dict(name="90 mm class refractor, full 7 kg", D=121.0, L=510.0, ota_kg=4.17, cam="astro", cam_D=90.0,
               cam_L=140.0, cam_kg=1.00, H=95.0, mount="dovetail", mount_L=250.0, kg=7.00),
}
REF_RIG = "P3"                               # the payload shown in renders and the viewer

# Ranges (spec 1.2 and 2.1)
ALT_MIN, ALT_MAX = -10.0, 95.0
ALT_BUMP_MIN, ALT_BUMP_MAX = -15.0, 100.0
ROLL_TOWARD_TOWER_MAX = 10.0                 # D34 (study result)
ROLL_AWAY_MAX = -150.0

# D39 removable wedge: head base plate ST-303 (stays on the head) and wedge top plate ST-331
HEAD_BASE_R = 37.5                  # = V-ring seat radius; the head stands on this disc on a tripod
WEDGE_PIN_R = 33.0                  # 2 x dowel 4 m6 at this radius, anti-rotation head <-> wedge
WEDGE_PIN_ANG = (11.25, 191.25)     # between the reducer screw cbores
HEAD_ON_TRIPOD_DZ = Z_UPPER_PLATE_TOP   # without the wedge the head drops this far (tripod top at Z 30 in head frame)

# Materials: density g/cm3, and print settings from spec 8.2
MAT = {
    "6061": dict(rho=2.70, label="Aluminium 6061-T6", finish="Bead-blasted, clear anodised 10 um"),
    "304": dict(rho=7.93, label="Stainless steel 304", finish="As turned, Ra 1.6"),
    "PA12-MJF": dict(rho=1.01, label="MJF PA12 (JLC3DP)", walls=99, infill=1.00, layer=0.08, temps="-",
                     dry="-", pattern="solid", finish="Bead-blasted, dyed black"),
    "PAHT-CF": dict(rho=1.18, label="PAHT-CF (Bambu)", walls=6, infill=0.50, layer=0.18,
                    temps="290 / 100 / 60 C", dry="80 C, 8-12 h; print from the dryer", pattern="gyroid"),
    "ASA": dict(rho=1.07, label="ASA", walls=4, infill=0.25, layer=0.20, temps="260 / 100 / 60 C",
                dry="80 C, 4 h", pattern="grid"),
    "TPU": dict(rho=1.21, label="TPU 95A", walls=3, infill=1.00, layer=0.20, temps="230 / 45 C / chamber off",
                dry="70 C, 8 h", pattern="concentric"),
    "PETG": dict(rho=1.27, label="PETG (clear)", walls=3, infill=1.00, layer=0.20, temps="250 / 75 C / off",
                 dry="65 C, 6 h", pattern="concentric"),
}
LINE_W = 0.42          # extrusion width, mm

# Fastener rules (D13): only M3/M4/M5, ISO 4762 or ISO 7380, keys 2 / 2.5 / 3 mm
INSERT = {  # heat-set insert hole: (hole d, depth) for Ruthex standard inserts
    "M3": (4.0, 6.0),   # Ruthex M3x5.7: D3 = 4.0
    "M4": (5.6, 8.5),   # Ruthex M4x8.1: D3 = 5.6
    "M5": (6.4, 10.0),  # Ruthex M5x9.5: D3 = 6.4
}
CLEAR = {"M3": 3.4, "M4": 4.5, "M5": 5.5}         # ISO 273 medium
TAP = {"M3": 2.5, "M4": 3.3, "M5": 4.2}
CBORE = {"M3": (6.0, 3.3), "M4": (7.5, 4.4), "M5": (9.0, 5.4)}   # ISO 4762 counterbore d x depth
TORQUE = {  # N.m. Steel A2-70 into aluminium thread / brass insert in nylon
    ("M3", "alu"): 1.0, ("M4", "alu"): 2.2, ("M5", "alu"): 4.5,
    ("M3", "insert"): 0.6, ("M4", "insert"): 1.2, ("M5", "insert"): 2.0,
    ("M3", "reducer"): 2.0,        # HD recommended for M3 into the reducer flange
}

# H2S build plate (D29)
PLATE_XY = (340.0, 320.0)
