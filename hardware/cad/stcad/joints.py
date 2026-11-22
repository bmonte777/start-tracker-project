"""Every joint of prototype P1: which screw, how many, into what, tightening torque and key.

D13: only M3 / M4 / M5 screws, ISO 4762 or ISO 7380, hex keys 2 / 2.5 / 3 mm. ISO 4762 M5 needs a 4 mm key,
so every M5 here is ISO 7380 (3 mm key).
Torques: A2-70 steel into 6061 thread or the reducer flange (Loctite 243), or into brass heat-set inserts.
"""
from . import params as P

KEY = {("ISO 4762", "M3"): "2.5", ("ISO 4762", "M4"): "3", ("ISO 7380", "M3"): "2", ("ISO 7380", "M4"): "2.5",
       ("ISO 7380", "M5"): "3", ("thumb", "M5"): "none", ("thumb", "M3"): "none", ("coin", "3/8"): "coin"}

# (step, joint, standard, size, length, qty, into, torque Nm, locker, note)
JOINTS = [
    # ---- wedge and base
    (1, "3/8in-16 bushing ST-307 into base ST-301", "-", "-", 0, 1, "press", 0, "638", "press in, wipe off, cure 1 h"),
    (1, "Base ST-301 to wedge lower plate ST-302 (azimuth lock)", "ISO 7380", "M5", 12, 2, "alu", 4.5, "-", "with washer ST-752; leave loose until set"),
    (1, "Azimuth fine-adjust push screws ST-306", "thumb", "M5", 25, 2, "alu", 0, "-", "finger tight, push the base boss"),
    (5, "Latitude arcs ST-305 to wedge top plate ST-331", "ISO 7380", "M5", 12, 4, "alu", 4.5, "243", ""),
    (5, "Dowels ST-333 into wedge top plate ST-331", "-", "-", 0, 2, "press", 0, "-", "press into the 6 mm blind holes from the top, 4 mm proud"),
    (5, "Hinge pin ST-304 retaining screws", "ISO 7380", "M3", 6, 2, "alu", 1.0, "243", "with large washer ST-751 each end"),
    (5, "Latitude clamp knobs ST-308", "thumb", "M5", 16, 2, "alu", 0, "-", "finger tight"),
    (5, "Latitude tangent screw ST-309 (D38)", "thumb", "M3", 25, 1, "alu", 0, "-", ""),
    (5, "Head onto the wedge top plate ST-331 (D39)", "coin", "3/8", 10, 1, "head", 0, "-", "coin-slot screw ST-332 from below, wedge tilted to 45 deg; dowels locate"),
    # ---- azimuth cartridge (and the same for altitude and roll)
    (2, "Reducer size 17 to cartridge housing ST-211 (x2 axes)", "ISO 4762", "M3", 50, 24, "insert", 0.6, "-", "12 per reducer, criss-cross; 7075 aluminium screws, 0.6 N\u00b7m max"),
    (2, "Reducer size 14 to cartridge housing ST-210", "ISO 4762", "M3", 45, 8, "insert", 0.6, "-", "criss-cross; 7075 aluminium screws, 0.6 N\u00b7m max"),
    (2, "60T pulley ST-205 to reducer input stub (x3)", "ISO 4762", "M3", 12, 12, "reducer", 1.5, "243", "pattern to confirm on the Laifual drawing"),
    (2, "Motor to motor plate ST-207 (x3)", "ISO 4762", "M3", 8, 12, "motor", 1.0, "243", ""),
    (2, "Motor plate to housing walls (x3)", "ISO 7380", "M3", 8, 12, "insert", 0.6, "-", "with washer ST-750; tighten after tensioning"),
    (2, "Belt tension screw (x3)", "ISO 4762", "M3", 12, 3, "alu", 0.3, "-", "turn until the span reads 290 Hz"),
    (2, "Encoder board ST-520 to carrier (x3)", "ISO 7380", "M3", 6, 6, "plastic", 0.3, "-", "cuts its own thread in ASA"),
    (2, "Carrier ST-212/216 posts to housing flange (x3)", "ISO 4762", "M3", 30, 6, "insert", 0.5, "-", ""),
    (4, "3/8in-16 bushing ST-307 into head base ST-303", "-", "-", 0, 1, "press", 0, "638", "press in, wipe off, cure 1 h"),
    (4, "Encoder tube ST-208 to head base plate ST-303 (azimuth)", "ISO 4762", "M3", 8, 2, "alu", 1.0, "243", "from below"),
    # ---- body, tower, cartridges in place
    (3, "Azimuth cartridge to body floor", "ISO 7380", "M4", 10, 4, "insert", 1.2, "-", "from below"),
    (4, "Azimuth reducer output flange to head base plate ST-303", "ISO 4762", "M3", 16, 16, "reducer", 2.0, "243", "from below, criss-cross"),
    (6, "Altitude cartridge to tower wall", "ISO 7380", "M4", 12, 4, "insert", 1.2, "-", "from outside the +X face"),
    (6, "Bumpers ST-322 to tower", "ISO 7380", "M3", 6, 2, "insert", 0.4, "-", ""),
    (3, "Cable guides ST-320 to body", "ISO 7380", "M3", 12, 2, "insert", 0.4, "-", ""),
    (6, "Cable guides ST-320 to tower", "ISO 7380", "M3", 12, 2, "insert", 0.4, "-", ""),
    (6, "Tower to body (with gasket ST-323)", "ISO 7380", "M5", 16, 4, "insert", 2.0, "-", "even, criss-cross"),
    # ---- altitude arm, roll cartridge, shelf
    (7, "Arm ST-312 to altitude reducer output", "ISO 4762", "M3", 10, 16, "reducer", 2.0, "243", "criss-cross"),
    (7, "Altitude encoder tube to arm hub", "ISO 7380", "M3", 5, 2, "alu", 0.8, "243", "thread the roll harness through first"),
    (7, "Roll cartridge to arm pad", "ISO 4762", "M4", 16, 4, "insert", 1.2, "-", "from the back of the pad"),
    (7, "Cable guide ST-320 to arm", "ISO 7380", "M3", 12, 2, "alu", 0.8, "-", ""),
    (7, "Roll enclosure ST-217 to arm pad (gasket ST-328, O-ring ST-329)", "ISO 4762", "M3", 16, 3, "insert", 0.5, "-", "from the pad front"),
    (8, "Roll shelf ST-313 to roll reducer output", "ISO 4762", "M3", 12, 12, "reducer", 2.0, "243", "criss-cross"),
    (8, "Roll encoder tube ST-215 to shelf", "ISO 4762", "M3", 6, 2, "alu", 1.0, "243", ""),
    (8, "Arca clamp ST-314 to shelf (D36)", "coin", "3/8", 12, 1, "clamp", 0, "243", "coin-slot screw ST-330"),
    # ---- electronics, covers, battery
    (9, "Mainboard ST-501 to bezel bosses", "ISO 7380", "M3", 6, 4, "plastic", 0.3, "-", ""),
    (9, "Bezel ST-315 to body (gasket ST-327)", "ISO 7380", "M3", 10, 6, "insert", 0.5, "-", ""),
    (9, "Head-side blade connector ST-609 to bracket", "ISO 7380", "M3", 8, 2, "insert", 0.4, "-", ""),
    (9, "Top cover ST-319 to body (gasket ST-324)", "ISO 7380", "M3", 10, 8, "insert", 0.5, "-", "criss-cross"),
    (10, "Pack shell halves ST-605/612 (gasket ST-610)", "ISO 4762", "M3", 30, 4, "insert", 0.5, "-", "pack stays closed: user never opens it"),
    (10, "Battery tray ST-317 to door ST-318", "ISO 7380", "M3", 8, 2, "plastic", 0.3, "-", ""),
]

# joints that belong to the removable wedge accessory (D39): their fasteners leave with the wedge
WEDGE_JOINTS = {"Base ST-301 to wedge lower plate ST-302 (azimuth lock)", "Azimuth fine-adjust push screws ST-306",
                "Latitude arcs ST-305 to wedge top plate ST-331", "Hinge pin ST-304 retaining screws",
                "Latitude clamp knobs ST-308", "Latitude tangent screw ST-309 (D38)", "Head onto the wedge top plate ST-331 (D39)"}
WEDGE_WASHERS = {"hinge pin ends", "azimuth lock"}

WASHERS = [("ISO 7089", "M3", 12, "motor plate clamp"), ("ISO 7093", "M3", 2, "hinge pin ends"), ("ISO 7089", "M5", 2, "azimuth lock")]


# D35: the reducer-to-housing screws only clamp the reducer into PAHT-CF inserts at 0.6 N.m, so they are
# 7075-T6 aluminium (density 2.81 instead of 7.9): about 50 g lighter per head
ALU7075 = {("ISO 4762", "M3", 50), ("ISO 4762", "M3", 45)}


def screw_mass_g(size, length, std):
    if (std, size, length) in ALU7075:
        return _steel_screw_g(size, length, std) * 2.81 / 7.9
    return _steel_screw_g(size, length, std)


def _steel_screw_g(size, length, std):
    d = {"M3": 3.0, "M4": 4.0, "M5": 5.0}.get(size, 0)
    if not d:
        return 14.0 if size == "3/8" else 4.0      # 3/8"-16 x 16 coin-slot clamp screw
    shank = 3.1416 / 4 * (d * 0.9) ** 2 * length * 7.9e-3
    head = {"ISO 4762": {"M3": 0.45, "M4": 1.0, "M5": 1.7}, "ISO 7380": {"M3": 0.35, "M4": 0.8, "M5": 1.4},
            "thumb": {"M3": 2.0, "M5": 6.0}}.get(std, {}).get(size, 1.0)
    return shank + head


def screw_summary():
    agg = {}
    for (step, joint, std, size, L, qty, into, tq, lk, note) in JOINTS:
        if std in ("-",):
            continue
        k = (std, size, L)
        a = agg.setdefault(k, dict(qty=0, joints=[]))
        a["qty"] += qty
        a["joints"].append(joint)
    return agg


def insert_summary():
    from .core import REGISTRY
    n = {"M3": 0, "M4": 0, "M5": 0}
    for pd in REGISTRY.values():
        pd.get()
        for f in pd.features:
            if f.kind == "insert":
                n[f.size] += f.qty * pd.qty
    return n


def fastener_kg():
    """Steel screws + washers + brass heat-set inserts, from the joint table."""
    g = sum(screw_mass_g(size, L, std) * a["qty"] for (std, size, L), a in screw_summary().items())
    g += sum({"M3": 0.1, "M4": 0.3, "M5": 0.45}[sz] * q for _, sz, q, _ in WASHERS)
    ins = insert_summary()
    g += ins["M3"] * 0.25 + ins["M4"] * 0.55 + ins["M5"] * 0.9
    return g / 1000.0


def wedge_fastener_kg():
    """Fasteners that leave with the wedge (screws + washers)."""
    g = sum(screw_mass_g(size, L, std) * qty for (st, j, std, size, L, qty, *_r) in JOINTS
            if j in WEDGE_JOINTS and std not in ("-",))
    g += sum({"M3": 0.1, "M4": 0.3, "M5": 0.45}[sz] * q for _, sz, q, use in WASHERS if use in WEDGE_WASHERS)
    return g / 1000.0
