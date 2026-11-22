"""Assembly checks: interference, clearance sweeps, mass and centre of gravity. Writes out/checks.json."""
from __future__ import annotations
import itertools, json, math, os, sys, time
from build123d import Compound, Pos
from . import params as P
from . import assembly as A

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
EXCLUDE = [("Belt", "Pulley"), ("Reducer", "Cartridge housing"), ("Wedge screw", "3/8in-16 bushing (head)"),
           ("Dowel", "Head base plate"), ("Dowel", "Wedge top plate")]     # belt teeth mesh; crush-rib press fit


def _bb(s):
    b = s.bounding_box()
    return (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z)


def _ov(a, b, m=0.05):
    return all(a[i] < b[i + 3] - m and b[i] < a[i + 3] - m for i in range(3))


def interference(pose, label):
    its = A.items()
    sh = [(it, A.placed(it, pose)) for it in its]
    rig = A.rig_shapes(pose)
    sh += [(type("R", (), {"name": f"Reference rig {k}"})(), v) for k, v in rig.items()]
    bbs = [_bb(s) for _, s in sh]
    hits = []
    for i, j in itertools.combinations(range(len(sh)), 2):
        a, b = sh[i][0].name, sh[j][0].name
        if a.startswith("Reference rig") and b.startswith("Reference rig"):
            continue
        if any((x in a and y in b) or (y in a and x in b) for x, y in EXCLUDE):
            continue
        if not _ov(bbs[i], bbs[j]):
            continue
        v = (sh[i][1] & sh[j][1]).volume
        if v > 0.5:
            hits.append(dict(a=a, b=b, mm3=round(v, 1)))
    return dict(pose=label, n_parts=len(sh), hits=hits)


def _group(pose, names_pred):
    return [A.placed(it, pose) for it in A.items() if names_pred(it)]


def min_dist(shapes_a, shapes_b, cap=None):
    """Exact minimum distance between two groups. Pairs are tried nearest bounding box first, so most are skipped.
    With `cap`, pairs whose boxes are further apart than cap are ignored (returns cap if none is closer)."""
    bas = [_bb(a) for a in shapes_a]
    bbs = [_bb(b) for b in shapes_b]
    pairs = []
    for i, ba in enumerate(bas):
        for j, bb in enumerate(bbs):
            gap = max(0, max(ba[k] - bb[k + 3] for k in range(3)), max(bb[k] - ba[k + 3] for k in range(3)))
            if cap is None or gap <= cap:
                pairs.append((gap, i, j))
    pairs.sort()
    best = (1e9 if cap is None else cap, None, None)
    for gap, i, j in pairs:
        if gap >= best[0]:
            break
        d = shapes_a[i].distance_to(shapes_b[j])
        if d < best[0]:
            best = (d, i, j)
    if best[1] is None and pairs:
        gap, i, j = pairs[0]
        best = (best[0], i, j)
    return best


def head_fixed(it):        # parts that do NOT move with altitude
    return it.stage in ("ground", "wedge", "az")


def alt_moving(it):
    return it.stage in ("alt", "roll")


def camera_swing():
    """Reference rig vs every part that does not turn with altitude, alt -10..+95."""
    out = []
    for th in [-10, 0, 20, 40, 60, 70, 80, 85, 90, 95]:
        pose = dict(A.HOME, alt=th)
        fixed = _group(pose, head_fixed)
        names = [it.name for it in A.items() if head_fixed(it)]
        rig = A.rig_shapes(pose)
        d, i, j = min_dist(list(rig.values()), fixed)
        zmin = min(v.bounding_box().min.Z for v in rig.values())
        out.append(dict(alt=th, min_mm=round(d, 1), rig=list(rig.keys())[i], part=names[j],
                        above_tripod_wedge_mm=round(zmin, 1),
                        above_tripod_no_wedge_mm=round(zmin - P.HEAD_ON_TRIPOD_DZ, 1)))
    return out


JOINT = ("Reducer size 17 (altitude)", "Encoder tube (altitude)", "Encoder magnet (altitude)", "V-ring VA-80 (altitude)")


def arm_swing():
    """Arm, roll cartridge and enclosure vs body/tower/wedge, alt -15..+100 (bumper to bumper).
    The altitude output joint (reducer flange, tube, V-ring on the tower pad) is excluded: it touches by design."""
    out = []
    mov = [it for it in A.items() if it.stage == "alt" and it.name not in JOINT]
    fix = [it for it in A.items() if head_fixed(it) and it.name not in JOINT]
    for th in [-15, -10, 0, 30, 60, 90, 100]:
        pose = dict(A.HOME, alt=th)
        d, i, j = min_dist([A.placed(it, pose) for it in mov], [A.placed(it, pose) for it in fix])
        out.append(dict(alt=th, min_mm=round(d, 1), moving=mov[i].name, fixed=fix[j].name))
    return out


def roll_travel(alt=0.0, step=1.0, margin=2.0):
    """Roll the reference rig toward the tower (+) and away (-) until the clearance drops below `margin`."""
    others = [it for it in A.items() if it.stage != "roll" and it.name not in ("Reducer size 14 (roll)",)]
    oth = [A.placed(it, dict(A.HOME, alt=alt)) for it in others]     # roll does not move these
    res = {}
    for sign in (+1, -1):
        last_ok, hit = 0.0, None
        phi = 0.0
        while abs(phi) <= 200:
            pose = dict(A.HOME, alt=alt, roll=phi)
            rig = A.rig_shapes(pose)
            d, i, j = min_dist(list(rig.values()), oth, cap=margin)
            if d < margin:
                hit = dict(at=phi, min_mm=round(d, 1), rig=list(rig.keys())[i], part=others[j].name)
                break
            last_ok = phi
            phi += sign * (step if abs(phi) < 20 else 5.0)
        res["toward_tower" if sign > 0 else "away"] = dict(limit_deg=last_ok, stop=hit)
    # tripod plane: first angle (away) at which any part of the rig drops below the tripod top (Z 0)
    phi = 0.0
    while phi > -200:
        rg = A.rig_shapes(dict(A.HOME, alt=alt, roll=phi))
        zmin = min(v.bounding_box().min.Z for v in rg.values())
        if zmin < 0:
            break
        phi -= 5
    res["below_tripod_plate_at_deg"] = phi
    phi = 0.0
    while phi > -200:
        rg = A.rig_shapes(dict(A.HOME, alt=alt, roll=phi))
        if min(v.bounding_box().min.Z for v in rg.values()) < P.HEAD_ON_TRIPOD_DZ:
            break
        phi -= 5
    res["below_tripod_no_wedge_at_deg"] = phi
    pose0 = dict(A.HOME, alt=alt)
    rig = A.rig_shapes(pose0)
    d, i, j = min_dist(list(rig.values()), [A.placed(it, pose0) for it in others])
    res["clearance_at_0_mm"] = round(d, 1)
    res["clearance_at_0_part"] = others[j].name
    return res


def motor48_clearance():
    its = A.items()
    m = [it for it in its if it.name.startswith("Motor 48")][0]
    s = A.placed(m, A.HOME)
    rows = []
    for it in its:
        if it is m or "(azimuth)" in it.name:
            continue
        if it.stage not in ("az", "wedge", "ground"):
            continue
        o = A.placed(it, A.HOME)
        bm, bo = _bb(s), _bb(o)
        gap = max(0, max(bm[k] - bo[k + 3] for k in range(3)), max(bo[k] - bm[k + 3] for k in range(3)))
        if gap > 25:
            continue
        rows.append(dict(part=it.name, min_mm=round(s.distance_to(o), 1)))
    rows.sort(key=lambda r: r["min_mm"])
    own = [it for it in its if "(azimuth)" in it.name and it is not m and it.name.startswith(("Cartridge housing", "Motor plate", "Pulley", "Belt"))]
    rows_own = [dict(part=it.name, min_mm=round(s.distance_to(A.placed(it, A.HOME)), 1)) for it in own]
    return dict(nearest=rows[:6], own_cartridge=rows_own, motor_top_z=round(_bb(s)[5], 1),
                body_top_z=P.Z_BODY_TOP, tower_inner_top_z=P.TOWER_TOP - P.TOWER_WALL)


def wedge_tilt():
    out = []
    for tau in (0, 30, 60, 75):
        r = interference(dict(A.HOME, wedge=tau), f"wedge {tau}")
        out.append(dict(tilt=tau, hits=r["hits"]))
    return out


SPEC_GROUPS = [   # spec 3.10 groups (P1 kg)
    ("Reducers", 2.70, lambda p: p in ("ST-201", "ST-202")),
    ("Stepper motors", 0.95, lambda p: p in ("ST-203", "ST-214")),
    ("Pulleys and belts", 0.14, lambda p: p in ("ST-204", "ST-205", "ST-206")),
    ("Battery pack", 0.34, lambda p: p.startswith("ST-6")),
    ("Electronics and harness", 0.17, lambda p: p.startswith("ST-5")),
    ("Housings and covers (printed)", 0.56, None),
    ("Aluminium parts and clamp", 1.08, None),
    ("Encoder tubes, magnets", 0.0, lambda p: p in ("ST-208", "ST-209", "ST-215")),
    ("Fasteners, inserts, seals", 0.15, None),
]


def mass_cog(extra_kg):
    from .core import REGISTRY
    its = A.items()
    tot = 0.0
    m_xyz = [0.0, 0.0, 0.0]
    groups = {g[0]: 0.0 for g in SPEC_GROUPS}
    per_part = {}
    for it in its:
        m = it.kg()
        c = A.placed(it, A.HOME).center()
        tot += m
        for k, v in enumerate((c.X, c.Y, c.Z)):
            m_xyz[k] += m * v
        pid = it.pid
        pd = REGISTRY.get(pid)
        per_part.setdefault(pid, [it.name.split(" (")[0], 0.0, 0])
        per_part[pid][1] += m
        per_part[pid][2] += 1
        placed_group = None
        for name, _, pred in SPEC_GROUPS:
            if pred and pred(pid):
                placed_group = name
                break
        if placed_group is None:
            if pd is not None and pd.kind == "printed" and pid not in ("ST-323", "ST-324", "ST-325", "ST-327", "ST-328",
                                                                       "ST-605", "ST-606", "ST-610", "ST-611", "ST-612"):
                placed_group = "Housings and covers (printed)"
            elif pd is not None and pd.kind in ("machined",) or pid in ("ST-314", "ST-304", "ST-307"):
                placed_group = "Aluminium parts and clamp"
            else:
                placed_group = "Fasteners, inserts, seals"
        groups[placed_group] += m
    groups["Fasteners, inserts, seals"] += extra_kg["fasteners"]
    groups["Electronics and harness"] += extra_kg["harness"]
    tot += extra_kg["fasteners"] + extra_kg["harness"]
    cog = [v / (tot - extra_kg["fasteners"] - extra_kg["harness"]) for v in m_xyz]
    # balance of what turns in altitude, and the roll stage + rig
    def cg_of(pred, rig=False):
        mm, s3 = 0.0, [0.0, 0.0, 0.0]
        for it in its:
            if pred(it):
                m = it.kg()
                c = A.placed(it, A.HOME).center()
                mm += m
                for k, v in enumerate((c.X, c.Y, c.Z)):
                    s3[k] += m * v
        if rig:
            ri = A.rig_info()
            for k2, mk in ri["masses"].items():
                c = ri["cgs"][k2]
                mm += mk
                for k, v in enumerate(c):
                    s3[k] += mk * v
        return mm, [v / mm for v in s3]
    m_alt, cg_alt = cg_of(lambda it: it.stage in ("alt", "roll"), rig=True)
    m_roll, cg_roll = cg_of(lambda it: it.stage == "roll", rig=True)
    m_rs, cg_rs = cg_of(lambda it: it.stage in ("roll",) or (it.stage == "alt" and ("(roll)" in it.name or "enclosure" in it.name)))
    from .joints import wedge_fastener_kg
    wedge_kg = sum(it.kg() for it in its if it.wedge) + wedge_fastener_kg()
    return dict(total_kg=round(tot, 3), cog_mm=[round(v, 1) for v in cog],
                wedge_kg=round(wedge_kg, 3), head_only_kg=round(tot - wedge_kg, 3),
                groups={k: round(v, 3) for k, v in groups.items()},
                spec_groups={g[0]: g[1] for g in SPEC_GROUPS},
                per_part={k: dict(name=v[0], kg=round(v[1], 4), qty=v[2]) for k, v in sorted(per_part.items())},
                alt_group=dict(kg=round(m_alt, 3), cg=[round(v, 1) for v in cg_alt],
                               dz_from_alt_axis=round(cg_alt[2] - P.Z_ALT, 1), dy_from_alt_axis=round(cg_alt[1], 1)),
                roll_stage_plus_rig=dict(kg=round(m_roll, 3), cg=[round(v, 1) for v in cg_roll],
                                         offset_from_roll_axis=round(math.hypot(cg_roll[0] - P.X_ROLL, cg_roll[2] - P.Z_ROLL), 1)),
                roll_stage_hardware=dict(kg=round(m_rs, 3), cg=[round(v, 1) for v in cg_rs]))


def payloads():
    """Every payload envelope: balance, loads, camera swing, roll travel, tripod clearance (wedge on and off)."""
    out = {}
    for key in P.RIGS:
        A.RIG = key
        inf = A.rig_info(key)
        cs = camera_swing()
        r0, r45 = roll_travel(0.0), roll_travel(45.0)
        worst = min(cs, key=lambda c: c["min_mm"])
        out[key] = dict(name=inf["name"], kg=round(inf["kg"], 2), mount_center_y=round(inf["mount_center_y"], 1),
                        alt_residual_Nm=round(inf["alt_residual_Nm"], 2), alt_offbalance_Nm=round(inf["alt_offbalance_Nm"], 2),
                        alt_dz_mm=round(inf["alt_dz_mm"], 1), roll_r_mm=round(inf["roll_r_mm"], 1),
                        roll_torque_90_Nm=round(inf["roll_torque_90_Nm"], 2),
                        camera_swing=cs, camera_min=worst,
                        camera_at_85=[c for c in cs if c["alt"] == 85][0],
                        tripod_min_wedge_mm=min(c["above_tripod_wedge_mm"] for c in cs),
                        tripod_min_no_wedge_mm=min(c["above_tripod_no_wedge_mm"] for c in cs),
                        roll_alt0=r0, roll_alt45=r45)
    A.RIG = None
    return out


def main(which=("interference", "motor48", "camera", "arm", "roll", "wedge", "payloads", "mass")):
    t = time.time()
    res = {}
    if "interference" in which:
        res["interference_home"] = interference(A.HOME, "home")
    if "motor48" in which:
        res["motor48"] = motor48_clearance()
    if "camera" in which:
        res["camera_swing"] = camera_swing()
    if "arm" in which:
        res["arm_swing"] = arm_swing()
    if "roll" in which:
        res["roll_travel_alt0"] = roll_travel(0.0)
        res["roll_travel_alt45"] = roll_travel(45.0)
    if "wedge" in which:
        res["wedge_tilt"] = wedge_tilt()
    if "payloads" in which:
        res["payloads"] = payloads()
    if "mass" in which:
        from .joints import fastener_kg
        res["mass"] = mass_cog(dict(fasteners=fastener_kg(), harness=0.06))
    res["seconds"] = round(time.time() - t, 1)
    res["x_roll"] = P.X_ROLL
    return res


if __name__ == "__main__":
    which = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    r = main(which) if which else main()
    os.makedirs(OUT, exist_ok=True)
    fn = os.path.join(OUT, sys.argv[2] if len(sys.argv) > 2 else "checks.json")
    json.dump(r, open(fn, "w"), indent=1)
    print(json.dumps({k: v for k, v in r.items() if k not in ("mass",)}, indent=1)[:6000])
