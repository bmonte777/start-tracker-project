"""Full head assembly: every made part and bought envelope, placed in the world frame for any pose.

Pose = dict(wedge=deg tilt 0..75, az=deg, alt=deg, roll=deg (+ toward the tower)).
Stages, from the ground up: ground (base, lower wedge plate, arcs) -> wedge (upper plate) ->
az (body, tower, az + alt cartridges, battery, electronics) -> alt (arm, roll cartridge) ->
roll (shelf, clamp, payload).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

from build123d import Location, Plane, Pos, Rot, Compound, Part

from . import params as P
from . import bought as B
from .core import REGISTRY, part_mass
from . import parts_cart, parts_struct, parts_misc  # noqa: F401  (registers parts)
from .parts_misc import (XB0, BTN_Y, BTN_Z, BOARD_X, BOARD_ZC, PK_CX, PK_CZ, PK_Y1, PK_ZM, PX0, PX1, YC)


@dataclass
class Item:
    name: str
    pid: str
    stage: str
    loc: Location
    make: object                      # callable returning a Part in local frame (bought) or None (made)
    mass: float | None = None         # bought mass, kg
    color: tuple = (0.6, 0.6, 0.6)
    group: str = ""
    explode: tuple = (0, 0, 0)        # explode direction * distance, world mm (home pose)
    wedge: bool = False               # part of the removable wedge accessory (D39)
    _shape: Part | None = field(default=None, repr=False)

    def local_shape(self):
        if self._shape is None:
            self._shape = REGISTRY[self.pid].get() if self.make is None else self.make()
        return self._shape

    def kg(self):
        return part_mass(REGISTRY[self.pid]) if self.make is None else self.mass


def cart_loc(axis):
    if axis == "az":
        return Pos(0, 0, P.Z_AZ_OUT)
    if axis == "alt":
        return Location(Plane(origin=(P.ALT_OUT_X, 0, P.Z_ALT), x_dir=(0, 1, 0), z_dir=(-1, 0, 0)))
    from .core import roll_frame
    o, x, y, z = roll_frame()
    return Location(Plane(origin=o, x_dir=x, z_dir=z))


AXIS_STAGE = {"az": "az", "alt": "az", "roll": "alt"}
G_TOWER = (0.0, 0.0, 260.0)
G_ARM = (120.0, 0.0, 260.0)
CART_BASE = {"az": (0.0, 0.0, 0.0), "alt": G_TOWER, "roll": G_ARM}
CART_DIR = {"az": (0, 0, 1), "alt": (-1, 0, 0), "roll": (0, -1, 0)}
CART_STEP = {"housing": 60, "reducer": 60, "tube": -45, "magnet": -45, "p60": 100, "p20": 100, "belt": 110, "plate": 130,
             "motor": 165, "board": 190, "cover": 205}
AXIS_SIZE = {"az": 17, "alt": 17, "roll": 14}
AXIS_MOTOR = {"az": "48", "alt": "38", "roll": "38"}
TUBE_STAGE = {"az": "wedge", "alt": "alt", "roll": "roll"}
EXPLODE_AXIS = {"az": (0, 0, -1), "alt": (-1, 0, 0), "roll": (0, -1, 0)}


def items():
    it: list[Item] = []
    I = lambda *a, **k: it.append(Item(*a, **k))  # noqa: E731
    g = REGISTRY
    ident = Location()
    # ---------------------------------------------------------------- ground and wedge
    W = dict(wedge=True)
    I("Base plate", "ST-301", "ground", ident, None, color=g["ST-301"].color, explode=(0, 0, -200), **W)
    I("Wedge lower plate", "ST-302", "ground", ident, None, color=g["ST-302"].color, explode=(0, 0, -160), **W)
    I("Latitude arc +Y", "ST-305", "wedge", ident, None, color=g["ST-305"].color, explode=(0, 60, -110), **W)
    I("Latitude arc -Y", "ST-305", "wedge", Pos(0, -(P.WEDGE_W + 6.0), 0), None, color=g["ST-305"].color, explode=(0, -60, -110), **W)
    I("Hinge pin 8 h6", "ST-304", "ground", Pos(P.WEDGE_HINGE_X, 0, P.WEDGE_HINGE_Z), B.hinge_pin, mass=0.041, color=(0.85, 0.85, 0.88), explode=(0, -150, -130), **W)
    I("3/8in-16 bushing (base)", "ST-307", "ground", ident, B.bushing38, mass=0.006, color=(0.85, 0.85, 0.88), explode=(0, 0, -230), **W)
    I("Wedge top plate", "ST-331", "wedge", ident, None, color=g["ST-331"].color, explode=(0, 0, -110), **W)
    import math as _m
    for k, a in enumerate(P.WEDGE_PIN_ANG):
        I(f"Dowel 4 m6 x 10 ({k + 1})", "ST-333", "wedge",
          Pos(P.WEDGE_PIN_R * _m.cos(_m.radians(a)), P.WEDGE_PIN_R * _m.sin(_m.radians(a)), P.Z_UPPER_PLATE_TOP - 6.0),
          B.dowel4, mass=0.001, color=(0.85, 0.85, 0.88), explode=(0, 0, -90), **W)
    I("Wedge screw 3/8in-16 x 10, coin slot", "ST-332", "wedge", Pos(0, 0, P.Z_UPPER_BOT + 4.5), B.coin_screw38,
      mass=0.012, color=(0.85, 0.85, 0.88), explode=(0, 0, -140), **W)
    I("Head base plate", "ST-303", "wedge", ident, None, color=g["ST-303"].color, explode=(0, 0, -60))
    I("3/8in-16 bushing (head)", "ST-307", "wedge", Pos(0, 0, P.Z_UPPER_PLATE_TOP), B.bushing38, mass=0.006,
      color=(0.85, 0.85, 0.88), explode=(0, 0, -75))
    I("V-ring VA-75 (azimuth)", "ST-213", "wedge", Pos(0, 0, 39.8), lambda: B.vring(75.0), mass=0.004,
      color=(0.08, 0.08, 0.08), explode=(0, 0, -45))
    # ---------------------------------------------------------------- cartridges
    for ax in ("az", "alt", "roll"):
        s, c = AXIS_SIZE[ax], P.CART[AXIS_SIZE[ax]]
        L = cart_loc(ax)
        st = AXIS_STAGE[ax]
        base, dirv = CART_BASE[ax], CART_DIR[ax]
        ex = lambda d: tuple(b + v * d for b, v in zip(base, dirv))  # noqa: E731
        hid = "ST-211" if s == 17 else "ST-210"
        cid = "ST-212" if s == 17 else "ST-216"
        tid = "ST-208" if s == 17 else "ST-215"
        rid = "ST-202" if s == 17 else "ST-201"
        mid = "ST-214" if AXIS_MOTOR[ax] == "48" else "ST-203"
        tag = {"az": "azimuth", "alt": "altitude", "roll": "roll"}[ax]
        I(f"Reducer size {s} ({tag})", rid, st, L, (lambda s=s: B.reducer(s)), mass=P.RED[s]["mass"],
          color=(0.55, 0.57, 0.60), explode=ex(CART_STEP["reducer"]))
        I(f"Cartridge housing ({tag})", hid, st, L, None, color=g[hid].color, explode=ex(CART_STEP["housing"]))
        I(f"Encoder tube ({tag})", tid, TUBE_STAGE[ax], L, None, color=g[tid].color, explode=ex(CART_STEP["tube"]))
        I(f"Encoder magnet ({tag})", "ST-209", TUBE_STAGE[ax], L * Pos(0, 0, c["z_magnet"] - 2.5),
          (lambda: B.cyl(3.0, 2.5)), mass=0.0005, color=(0.5, 0.1, 0.1), explode=ex(CART_STEP["magnet"]))
        I(f"Pulley 60T ({tag})", "ST-205", st, L * Pos(0, 0, c["z_stub_end"] + 1.0), B.pulley60, mass=P.PULLEY60["mass"],
          color=(0.80, 0.80, 0.82), explode=ex(CART_STEP["p60"]))
        I(f"Pulley 20T ({tag})", "ST-204", st, L * Pos(0, P.BELT_C, c["z_stub_end"] + 1.0), B.pulley20,
          mass=P.PULLEY20["mass"], color=(0.80, 0.80, 0.82), explode=ex(CART_STEP["p20"]))
        I(f"Belt 2GT-200-9 ({tag})", "ST-206", st, L * Pos(0, 0, c["z_belt"]), B.belt, mass=0.003,
          color=(0.05, 0.05, 0.05), explode=ex(CART_STEP["belt"]))
        I(f"Motor plate ({tag})", "ST-207", st, L * Pos(0, P.BELT_C, c["z_motor_plate"]), None,
          color=g["ST-207"].color, explode=ex(CART_STEP["plate"]))
        I(f"Motor {AXIS_MOTOR[ax]} mm ({tag})", mid, st, L * Pos(0, P.BELT_C, c["z_motor_face"]) * Rot(0, 0, 90 if ax == "az" else 0),
          (lambda m=AXIS_MOTOR[ax]: B.nema17(P.MOTOR[m]["L"])), mass=P.MOTOR[AXIS_MOTOR[ax]]["mass"],
          color=(0.18, 0.18, 0.20), explode=ex(CART_STEP["motor"]))
        I(f"Encoder board ({tag})", "ST-520", st, L * Pos(0, 0, c["z_board"]), B.encoder_board, mass=0.004,
          color=(0.10, 0.45, 0.20), explode=ex(CART_STEP["board"]))
        I(f"Cartridge cover ({tag})", cid, st, L, None, color=g[cid].color, explode=ex(CART_STEP["cover"]))
    # ---------------------------------------------------------------- az stage: housings, battery, electronics
    I("Azimuth body", "ST-310", "az", ident, None, color=g["ST-310"].color, explode=(0, 0, 0))
    I("Gasket body-tower", "ST-323", "az", ident, None, color=g["ST-323"].color, explode=(0, 0, 225))
    I("Tower", "ST-311", "az", ident, None, color=g["ST-311"].color, explode=G_TOWER)
    I("Gasket top cover", "ST-324", "az", ident, None, color=g["ST-324"].color, explode=(-40, 0, 60))
    I("Top cover", "ST-319", "az", ident, None, color=g["ST-319"].color, explode=(-40, 0, 90))
    I("GNSS patch antenna", "ST-512", "az", Pos(-120, 40, P.Z_BODY_TOP + P.GASKET_T - 4.5), B.gnss_patch,
      mass=0.010, color=(0.75, 0.65, 0.30), explode=(-40, 0, 75))
    I("Gasket bezel", "ST-327", "az", ident, None, color=g["ST-327"].color, explode=(-50, 0, 0))
    I("Front bezel", "ST-315", "az", ident, None, color=g["ST-315"].color, explode=(-70, 0, 0))
    I("OLED window 38 x 22 x 1 PC", "ST-326", "az", ident,
      (lambda: B.box(XB0 + 0.1, XB0 + 1.1, YC - 19.0, YC + 19.0, BOARD_ZC + 16 - 11.0, BOARD_ZC + 16 + 11.0)), mass=0.001,
      color=(0.6, 0.8, 0.9), explode=(-80, 0, 0))
    for i, y in enumerate(BTN_Y):
        I(f"Button cap {i + 1}", "ST-316", "az", Pos(XB0 - 2.5, y, BTN_Z) * Rot(0, 90, 0), None,
          color=g["ST-316"].color, explode=(-90, 0, 0))
    I("Mainboard", "ST-501", "az", Pos(BOARD_X, YC, BOARD_ZC), B.mainboard, mass=0.045, color=(0.10, 0.45, 0.20),
      explode=(-40, 0, 0))
    I("Battery tray", "ST-317", "az", ident, None, color=g["ST-317"].color, explode=(0, 100, 0))
    I("Battery door", "ST-318", "az", ident, None, color=g["ST-318"].color, explode=(0, 120, 0))
    I("Gasket battery door", "ST-325", "az", ident, None, color=g["ST-325"].color, explode=(0, 110, 0))
    I("Head-side blade connector", "ST-609", "az", Pos(PK_CX, P.PACK_Y0, PK_ZM - 4), B.blade_connector, mass=0.008,
      color=(0.9, 0.9, 0.9), explode=(0, 60, 0))
    # pack
    I("Pack shell lower", "ST-605", "az", ident, None, color=g["ST-605"].color, explode=(0, 100, -10))
    I("Pack gasket", "ST-610", "az", ident, None, color=g["ST-610"].color, explode=(0, 100, 5))
    I("Pack shell upper", "ST-612", "az", ident, None, color=g["ST-612"].color, explode=(0, 100, 20))
    I("Pack light pipe", "ST-611", "az", Pos(PK_CX, PK_Y1, P.PACK_Z0 + 38), None,
      color=g["ST-611"].color, explode=(0, 115, 20))
    I("Pack-side blade connector", "ST-608", "az", Pos(PK_CX, P.PACK_Y0, PK_ZM - 4) * Rot(0, 0, 180),
      B.blade_connector, mass=0.008, color=(0.9, 0.9, 0.9), explode=(0, 100, 0))
    ycell = P.PACK_Y0 + P.PACK["wall"] + 12.0 + 3.0
    I("Cell holder -Y", "ST-606", "az", Pos(PK_CX, ycell - 3.0, PK_CZ), None, color=g["ST-606"].color, explode=(0, 100, 0))
    I("Cell holder +Y", "ST-606", "az", Pos(PK_CX, ycell + P.CELL_L, PK_CZ), None, color=g["ST-606"].color, explode=(0, 100, 0))
    for k, (dx, dz) in enumerate([(-11.1, -11.1), (11.1, -11.1), (-11.1, 11.1), (11.1, 11.1)]):
        I(f"Cell P50B {k + 1}", "ST-601", "az", Pos(PK_CX + dx, ycell, PK_CZ + dz), B.cell, mass=P.CELL_M,
          color=(0.15, 0.35, 0.70), explode=(0, 100, 0))
    I("Battery board", "ST-602", "az", Pos(PK_CX, ycell + P.CELL_L + 3.6, PK_CZ), B.battery_board, mass=0.015,
      color=(0.10, 0.45, 0.20), explode=(0, 100, 0))
    # tower details
    for k, a in enumerate((273.6, 43.4)):
        u, v = 62 * math.cos(math.radians(a)), 62 * math.sin(math.radians(a))
        I(f"Bumper {k + 1}", "ST-322", "az", Pos(P.TOWER_X_MAX, u, P.Z_ALT + v) * Rot(0, 90, 0), None,
          color=g["ST-322"].color, explode=(40, 0, 260))
    I("V-ring VA-80 (altitude)", "ST-218", "alt", Pos(P.ALT_OUT_X, 0, P.Z_ALT) * Rot(0, -90, 0) * Pos(0, 0, -0.0),
      lambda: B.vring(80.0, 6.0, 2.5), mass=0.005, color=(0.08, 0.08, 0.08), explode=(80, 0, 260))
    # ---------------------------------------------------------------- alt stage
    I("Altitude arm", "ST-312", "alt", ident, None, color=g["ST-312"].color, explode=G_ARM)
    I("Cable guide (arm)", "ST-320", "alt", Location(Plane(origin=(P.ALT_OUT_X + P.ARM_T, -30, 196),
                                                          x_dir=(0, 0, 1), z_dir=(1, 0, 0))), None,
      color=g["ST-320"].color, explode=(150, 0, 260))
    I("Cable guide (tower)", "ST-320", "az", Location(Plane(origin=(-60, -49.0, 200), x_dir=(0, 0, 1),
                                                           z_dir=(0, 1, 0))), None, color=g["ST-320"].color,
      explode=(0, -40, 260))
    I("Cable guide (body)", "ST-320", "az", Location(Plane(origin=(-100, -46, P.Z_BODY_BOT + P.BODY_WALL),
                                                          x_dir=(1, 0, 0), z_dir=(0, 0, 1))), None,
      color=g["ST-320"].color, explode=(0, 0, 30))
    # ---------------------------------------------------------------- roll stage
    I("Roll cartridge enclosure", "ST-217", "alt", ident, None, color=g["ST-217"].color, explode=(120, -260, 260))
    I("Gasket roll enclosure", "ST-328", "alt", ident, None, color=g["ST-328"].color, explode=(120, -30, 260))
    I("O-ring 80 x 2 (roll enclosure)", "ST-329", "alt", Pos(P.X_ROLL, -46.0, P.Z_ROLL) * Rot(90, 0, 0),
      lambda: B.cyl(43.0, 1.6) - B.cyl(41.0, 3, z=-1), mass=0.002, color=(0.08, 0.08, 0.08), explode=(120, -230, 260))
    I("Roll shelf", "ST-313", "roll", ident, None, color=g["ST-313"].color, explode=(120, 90, 260))
    I("V-ring VA-65 (roll)", "ST-219", "roll", Pos(P.X_ROLL, P.ROLL_OUT_Y, P.Z_ROLL) * Rot(90, 0, 0),
      lambda: B.vring(65.0, 5.0, 2.5), mass=0.003, color=(0.08, 0.08, 0.08), explode=(120, 60, 260))
    I("Arca clamp 60 mm", "ST-314", "roll", Pos(P.X_ROLL, P.CLAMP_CY, P.Z_ROLL + P.SHELF_TOP), B.clamp60, mass=P.CLAMP["mass"],
      color=(0.20, 0.20, 0.22), explode=(120, 90, 320))
    return it


# ------------------------------------------------------------------------------- kinematics
def stage_loc(stage, pose):
    tau = pose.get("wedge", 0.0)
    a = pose.get("az", 0.0)
    th = pose.get("alt", 0.0)
    ph = pose.get("roll", 0.0)
    hx, hz = P.WEDGE_HINGE_X, P.WEDGE_HINGE_Z
    Lw = Pos(hx, 0, hz) * Rot(0, -tau, 0) * Pos(-hx, 0, -hz)
    La = Rot(0, 0, a)
    Lt = Pos(0, 0, P.Z_ALT) * Rot(th, 0, 0) * Pos(0, 0, -P.Z_ALT)
    Lr = Pos(P.X_ROLL, 0, P.Z_ROLL) * Rot(0, -ph, 0) * Pos(-P.X_ROLL, 0, -P.Z_ROLL)
    if stage == "ground":
        return Location()
    if stage == "wedge":
        return Lw
    if stage == "az":
        return Lw * La
    if stage == "alt":
        return Lw * La * Lt
    if stage in ("roll", "rig"):
        return Lw * La * Lt * Lr
    raise ValueError(stage)


def placed(item, pose, explode=0.0):
    L = stage_loc(item.stage, pose) * item.loc
    s = item.local_shape().moved(L)
    if explode:
        e = item.explode
        s = s.moved(Pos(e[0] * explode, e[1] * explode, e[2] * explode))
    return s


RIG = None              # payload envelope key used by rig_shapes(); None = params.REF_RIG
_RIG_CACHE = {}
_ALT_HW = None


def _alt_hardware():
    """Mass and CG of everything that turns in altitude, without payload (home pose)."""
    global _ALT_HW
    if _ALT_HW is None:
        mm, s3 = 0.0, [0.0, 0.0, 0.0]
        for it in items():
            if it.stage in ("alt", "roll"):
                m = it.kg()
                c = placed(it, HOME).center()
                mm += m
                for k, v in enumerate((c.X, c.Y, c.Z)):
                    s3[k] += m * v
        _ALT_HW = (mm, [v / mm for v in s3])
    return _ALT_HW


def rig_y0(key):
    """Camera mount plane Y that balances payload `key` on the altitude axis (what the user does by
    sliding the foot or dovetail in the clamp)."""
    if key not in _RIG_CACHE:
        mh, ch = _alt_hardware()
        _, mas, cg, _ = B.rig_parts(key, 0.0)
        mr = sum(mas.values())
        yr = sum(mas[k] * cg[k][1] for k in mas) / mr          # rig CG Y relative to y0
        y0 = -(mh * ch[1]) / mr - yr
        # the mount can only slide as far as the clamp jaws still hold it
        yc = B.rig_parts(key, y0)[3]
        lim = P.RIGS[key]["mount_L"] / 2 - P.CLAMP["L"] / 2
        if abs(yc - P.CLAMP_CY) > lim:
            y0 -= (yc - P.CLAMP_CY) - math.copysign(lim, yc - P.CLAMP_CY)
        _RIG_CACHE[key] = y0
    return _RIG_CACHE[key]


def rig_info(key=None):
    """Masses, CG (home pose) and clamp reach of a payload envelope."""
    key = key or RIG or P.REF_RIG
    y0 = rig_y0(key)
    sol, mas, cg, yc = B.rig_parts(key, y0)
    mr = sum(mas.values())
    c = [sum(mas[k] * cg[k][i] for k in mas) / mr for i in range(3)]
    r = P.RIGS[key]
    mh, ch = _alt_hardware()
    dy = (mh * ch[1] + mr * c[1]) / (mh + mr)            # alt group CG off the axis after sliding
    dz = (mh * (ch[2] - P.Z_ALT) + mr * (c[2] - P.Z_ALT)) / (mh + mr)
    return dict(key=key, name=r["name"], y0=y0, kg=mr, cg=c, mount_center_y=yc, masses=mas, cgs=cg,
                alt_group_kg=mh + mr, alt_dy_mm=dy, alt_dz_mm=dz,
                alt_residual_Nm=(mh + mr) * 9.81 * abs(dy) / 1000.0,
                alt_offbalance_Nm=(mh + mr) * 9.81 * math.hypot(dy, dz) / 1000.0,
                roll_r_mm=math.hypot(c[0] - P.X_ROLL, c[2] - P.Z_ROLL),
                roll_torque_90_Nm=mr * 9.81 * math.hypot(c[0] - P.X_ROLL, c[2] - P.Z_ROLL) / 1000.0)


def rig_shapes(pose, key=None):
    key = key or RIG or P.REF_RIG
    L = stage_loc("rig", pose)
    return {k: v.moved(L) for k, v in B.reference_rig(key).items()}


HOME = dict(wedge=0.0, az=0.0, alt=0.0, roll=0.0)
