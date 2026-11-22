"""Renders, assembly-step pictures and 3D-viewer data, from cached meshes (tessellate once, then move)."""
from __future__ import annotations
import base64, gzip, json, math, os
import numpy as np
from build123d import Location

from . import params as P
from . import assembly as A
from . import bought as B
from . import render as R

_CACHE: dict = {}


def _trsf(loc: Location):
    t = loc.wrapped.Transformation()
    M = np.array([[t.Value(i, j) for j in range(1, 5)] for i in range(1, 4)])
    return M[:, :3], M[:, 3]


def item_mesh(it, tol=0.2, ang=0.35):
    key = (it.name, it.pid, tol)
    if key not in _CACHE:
        v, t = R.tess(it.local_shape(), tol, ang)
        _CACHE[key] = (v, t)
    return _CACHE[key]


def placed_mesh(it, pose, explode=0.0, tol=0.2):
    v, t = item_mesh(it, tol)
    L = A.stage_loc(it.stage, pose) * it.loc
    Rm, tv = _trsf(L)
    w = v @ Rm.T + tv
    if explode:
        w = w + np.array(it.explode) * explode
    return w, t


_RIG = {}


def rig_meshes(pose, tol=0.3, color_cam=(0.22, 0.22, 0.24), color_lens=(0.86, 0.87, 0.89), oid0=1000):
    if not _RIG:
        for k, s in B.reference_rig().items():
            _RIG[k] = R.tess(s, tol, 0.4)
    L = A.stage_loc("rig", pose)
    Rm, tv = _trsf(L)
    out = []
    for j, (k, (v, t)) in enumerate(_RIG.items()):
        col = color_cam if k == "camera" else (color_lens if k == "lens" else (0.25, 0.25, 0.27))
        out.append((v @ Rm.T + tv, t, col, oid0 + j))
    return out


def scene(pose, explode=0.0, filt=None, highlight=None, grey=None, rig=False, tol=0.2, oid0=0):
    its = A.items()
    ms = []
    for k, it in enumerate(its):
        if filt and not filt(it):
            continue
        v, t = placed_mesh(it, pose, explode, tol)
        col = it.color
        if grey and grey(it):
            col = tuple(0.55 + 0.35 * c for c in (0.6, 0.6, 0.62))
        if highlight and highlight(it):
            col = (0.95, 0.55, 0.15)
        ms.append((v, t, col, oid0 + k))
    if rig:
        ms += rig_meshes(pose)
    return ms


def save(ms, path, az, el, title=None, sub=None, W=1600, H=1200, fit=None):
    im, proj = R.render(ms, az, el, W, H, fit=fit)
    if title:
        R.caption(im, title, sub)
    im.save(path)
    return proj


STEP_OF = {   # assembly step that installs each item (by name prefix or pid)
    1: lambda it: it.pid in ("ST-301", "ST-302", "ST-307"),
    3: lambda it: it.pid == "ST-310" or ("(azimuth)" in it.name and not it.name.startswith(("Encoder tube", "Encoder magnet")))
                  or it.name == "Cable guide (body)",
    4: lambda it: it.pid in ("ST-303", "ST-213", "ST-305") or it.name in ("Encoder tube (azimuth)", "Encoder magnet (azimuth)"),
    5: lambda it: it.pid == "ST-304",
    6: lambda it: it.pid in ("ST-311", "ST-323", "ST-322") or ("(altitude)" in it.name and not it.name.startswith(("Encoder tube", "Encoder magnet")) and "V-ring" not in it.name)
                  or it.name == "Cable guide (tower)",
    7: lambda it: it.pid in ("ST-312", "ST-217", "ST-328", "ST-329", "ST-218") or it.name in ("Encoder tube (altitude)", "Encoder magnet (altitude)", "Cable guide (arm)")
                  or ("(roll)" in it.name and not it.name.startswith(("Encoder tube", "Encoder magnet", "V-ring"))),
    8: lambda it: it.pid in ("ST-313", "ST-219", "ST-314") or it.name in ("Encoder tube (roll)", "Encoder magnet (roll)"),
    9: lambda it: it.pid in ("ST-501", "ST-315", "ST-327", "ST-326", "ST-316", "ST-609", "ST-512", "ST-319", "ST-324"),
    10: lambda it: it.pid in ("ST-317", "ST-318", "ST-325", "ST-605", "ST-610", "ST-612", "ST-611", "ST-608", "ST-606", "ST-601", "ST-602"),
}


def step_of(it):
    for k, f in STEP_OF.items():
        if f(it):
            return k
    return 2


def renders(img_dir):
    os.makedirs(img_dir, exist_ok=True)
    H = A.HOME
    out = {}
    out["three_quarter"] = save(scene(H, rig=True), f"{img_dir}/03-three-quarter.png", -50, 24,
                                "Star tracker P1 - three-quarter view", "With the reference rig (A7R V + FE 200-600) balanced")
    out["front"] = save(scene(H, rig=True), f"{img_dir}/03-front.png", -90, 0, "Front view (from -Y)", "Lens points into the page")
    out["side"] = save(scene(H, rig=True), f"{img_dir}/03-side.png", 0, 0, "Side view (from the payload side, +X)")
    out["top"] = save(scene(H, rig=True), f"{img_dir}/03-top.png", -90, 89.9, "Top view")
    save(scene(H), f"{img_dir}/03-head-three-quarter.png", -50, 24, "Head without payload")
    save(scene(H, explode=1.0), f"{img_dir}/03-exploded.png", -50, 22, "Exploded view",
         "Every part we make or buy except screws; the viewer page lets you slide this")
    save(scene(H, explode=1.0), f"{img_dir}/03-exploded-rear.png", 135, 22, "Exploded view from the battery side")
    pose = dict(H, alt=85.0)
    save(scene(pose, rig=True), f"{img_dir}/03-swing-85.png", -90, 0, "Camera swing at +85 deg altitude",
         "Nearest point: camera to azimuth body 14.5 mm")
    # roll limits: both extremes drawn together
    ms = scene(H)
    ms += rig_meshes(dict(H, roll=P.ROLL_TOWARD_TOWER_MAX), color_cam=(0.20, 0.35, 0.75), color_lens=(0.55, 0.68, 0.95), oid0=2000)
    ms += rig_meshes(dict(H, roll=-145.0), color_cam=(0.80, 0.40, 0.10), color_lens=(0.98, 0.75, 0.50), oid0=3000)
    save(ms, f"{img_dir}/03-roll-limits.png", -90, 0, "Roll travel with the 200-600 on its foot",
         "Blue: +10 deg toward the tower (lens meets the arm hub). Orange: -145 deg (camera meets the roll enclosure)")
    save(scene(dict(H, wedge=52.0, alt=30.0), rig=True), f"{img_dir}/03-eq-mode.png", -60, 18,
         "EQ mode: wedge tilted 52 deg (latitude 38 deg N, Lisbon)", "Azimuth becomes right ascension")
    cart = lambda it: "(azimuth)" in it.name  # noqa: E731
    save(scene(H, explode=1.0, filt=cart), f"{img_dir}/03-cartridge-exploded.png", -40, 25,
         "Azimuth cartridge, exploded", "Reducer, housing, pulleys, belt, motor plate, 48 mm motor, encoder tube, board, carrier")
    batt = lambda it: it.pid in ("ST-317", "ST-318", "ST-325", "ST-605", "ST-610", "ST-612", "ST-611", "ST-608", "ST-606", "ST-601", "ST-602")  # noqa
    ms = scene(H, explode=0.7, filt=lambda it: batt(it) or it.pid in ("ST-310", "ST-609"), grey=lambda it: it.pid == "ST-310")
    save(ms, f"{img_dir}/03-battery.png", 60, 25, "Tool-free battery: press the two snap hooks, pull the door, lift the pack out",
         "Door, tray and pack shown drawn out of the body")
    return out


def step_images(img_dir):
    os.makedirs(img_dir, exist_ok=True)
    H = A.HOME
    titles = {1: "Base plate and wedge lower plate", 2: "Build the three axis cartridges", 3: "Azimuth cartridge into the body",
              4: "Body onto the wedge upper plate, arcs on", 5: "Upper plate onto the lower plate: hinge pin",
              6: "Altitude cartridge into the tower, tower onto the body", 7: "Arm, roll cartridge and roll enclosure",
              8: "Roll shelf and Arca clamp", 9: "Mainboard, bezel and top cover", 10: "Battery pack, tray and door"}
    paths = {}
    for k in range(1, 11):
        p = f"{img_dir}/03-step-{k:02d}.png"
        if k == 2:
            ms = scene(H, explode=0.6, filt=lambda it: "(azimuth)" in it.name or it.name in ("Encoder tube (azimuth)",))
        else:
            ms = scene(H, filt=lambda it, k=k: step_of(it) <= k, highlight=lambda it, k=k: step_of(it) == k)
        az = 125 if k in (9, 10) else -50
        save(ms, p, az, 24, f"Step {k}: {titles[k]}", "New parts in orange", W=1200, H=900)
        paths[k] = p
    return paths


def viewer_data(tol=0.3):
    """Compact meshes for the HTML viewer: Int16 positions (0.05 mm), Uint32 indices, gzip + base64."""
    H = A.HOME
    its = A.items()
    recs = []
    for k, it in enumerate(its):
        v, t = R.tess(it.local_shape(), tol, 0.45)
        L = A.stage_loc(it.stage, H) * it.loc
        Rm, tv = _trsf(L)
        w = v @ Rm.T + tv
        q = np.round(w / 0.05).astype(np.int16)
        recs.append(dict(name=it.name, pid=it.pid, stage=it.stage, color=[round(c, 3) for c in it.color],
                         explode=[round(e, 1) for e in it.explode], step=step_of(it),
                         p=base64.b64encode(q.tobytes()).decode(), i=base64.b64encode(t.astype(np.uint32).tobytes()).decode()))
    for k, s in B.reference_rig().items():
        v, t = R.tess(s, tol, 0.45)
        q = np.round(v / 0.05).astype(np.int16)
        recs.append(dict(name=f"Reference rig: {k}", pid="RIG", stage="rig", color=[0.86, 0.87, 0.89] if k == "lens" else [0.25, 0.25, 0.27],
                         explode=[0, 0, 0], step=99, p=base64.b64encode(q.tobytes()).decode(),
                         i=base64.b64encode(t.astype(np.uint32).tobytes()).decode()))
    raw = json.dumps(recs, separators=(",", ":")).encode()
    return base64.b64encode(gzip.compress(raw, 9)).decode(), len(raw)
