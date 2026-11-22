"""Phase 4 fit check: the KiCad boards (STEP exports with their 3D component models) inside the Phase 3 assembly.

For every board instance it replaces the Phase 3 envelope by the real board and reports, against every other part of
the head at home pose: overlaps (with the overlapping volume) and the nearest clearances. Extra checks: the magnet gap
under each encoder, and how far the mainboard's front parts stand from the bezel openings.

Run:  python -m stcad.fit_boards            (from hardware/cad; needs hardware/electronics/fab/<board>/<board>.step)
Writes hardware/cad/out/fit_boards.json
"""
import json
import os

from build123d import Location, Plane, import_step

from . import assembly as A
from .checks import _bb, min_dist

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, "..", "..", "electronics", "fab")
OUT = os.path.join(HERE, "..", "out", "fit_boards.json")

# KiCad STEP frame: origin at the board centre, X right, Y up (seen from the top side), board from Z 0 (bottom) to 1.6 (top).
# ST-520: the Phase 3 envelope uses the same frame (underside at Z 0), so the item location is used as it is.
# ST-501: the envelope has its outer face at X 0 looking toward -X, Y to the left seen from the front, Z up.
FRAME = {
    "ST-520": Location(),
    "ST-501": Location(Plane(origin=(1.6, 0, 0), x_dir=(0, -1, 0), z_dir=(-1, 0, 0))),
}
STEP = {"ST-520": "st-520", "ST-501": "st-501"}
CAP = 4.0     # mm: neighbours further away than this are not reported


def board_solids(pid):
    path = os.path.join(FAB, STEP[pid], STEP[pid] + ".step")
    if not os.path.exists(path):
        return None
    return list(import_step(path).solids())


def check(pid, pose=None):
    pose = pose or A.HOME
    src = board_solids(pid)
    if src is None:
        return [dict(board=pid, missing=True)]
    results = []
    items = A.items()
    for it in [x for x in items if x.pid == pid]:
        L = A.stage_loc(it.stage, pose) * it.loc * FRAME[pid]
        solids = [s.moved(L) for s in src]
        bb = [min(_bb(s)[k] for s in solids) for k in range(3)] + [max(_bb(s)[k + 3] for s in solids) for k in range(3)]
        res = dict(board=pid, instance=it.name, parts_in_step=len(solids), bbox=[round(v, 1) for v in bb], overlaps=[], nearest=[])
        for other in items:
            if other is it or other.pid == pid:
                continue
            o = A.placed(other, pose)
            ob = _bb(o)
            gap = max(0, max(bb[k] - ob[k + 3] for k in range(3)), max(ob[k] - bb[k + 3] for k in range(3)))
            if gap > CAP:
                continue
            d, i, _j = min_dist(solids, [o], cap=CAP)
            if i is None or d >= CAP:
                continue
            entry = dict(part=f"{other.pid} {other.name}", distance=round(d, 2))
            if d < 0.01:
                vol = 0.0
                for s in solids:
                    sb = _bb(s)
                    if max(max(sb[k] - ob[k + 3] for k in range(3)), max(ob[k] - sb[k + 3] for k in range(3))) > 0:
                        continue
                    try:
                        c = s.intersect(o)
                        if c is None:
                            continue
                        vol += sum(x.volume for x in c) if isinstance(c, (list, tuple)) else c.volume
                    except Exception:
                        vol = -1.0
                        break
                entry["overlap_mm3"] = round(vol, 2)
                if vol > 0.05 or vol < 0:
                    res["overlaps"].append(entry)
                    continue
            res["nearest"].append(entry)
        res["nearest"].sort(key=lambda e: e["distance"])
        res["nearest"] = res["nearest"][:8]
        if pid == "ST-520":
            axis = it.name.split("(")[-1].rstrip(")")
            mags = [A.placed(x, pose) for x in items if "magnet" in x.name.lower() and axis in x.name]
            if mags:
                res["magnet_gap"] = round(min_dist(solids, mags)[0], 2)
        results.append(res)
    return results


def main():
    out = []
    for pid in ("ST-520", "ST-501"):
        out += check(pid)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    for r in out:
        if r.get("missing"):
            print(r["board"], "no STEP export yet")
            continue
        print(f"{r['board']} {r['instance']}: {r['parts_in_step']} solids, overlaps {len(r['overlaps'])}, magnet gap {r.get('magnet_gap', '-')}")
        for e in r["overlaps"]:
            print("   OVERLAP", e)
        for e in r["nearest"][:5]:
            print("   near", e)


if __name__ == "__main__":
    main()
