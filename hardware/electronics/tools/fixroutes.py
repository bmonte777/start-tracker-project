"""Applies a board's hand-made corrections to its routed tracks.

    python3 tools/fixroutes.py <board>

Reads <board>/route_fixes.py (a list STAGES of (name, [operations])) and applies every stage that is not yet recorded in
the routes file (<name>.routes.json, key "fixes"). Operations:
    ("drop", net, layer, (x, y), (x, y))      take one routed segment out (either direction)
    ("dropvia", net, (x, y))                  take one routed via out
    ("track", net, layer, width, [points])    lay a track through the points
    ("via", net, (x, y))                      set a through via
A stage stops with an error, and nothing is written, if a segment or via it wants to take out is not there: the list
belongs to one routing result and must not be applied to another one.
"""
import importlib.util
import json
import os
import sys


def same(a, b):
    return abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6


def apply(rt, ops):
    for op in ops:
        if op[0] == "drop":
            _, net, layer, a, b = op
            hit = [i for i, t in enumerate(rt["tracks"]) if t[0] == net and t[1] == layer and
                   ((same(t[3:5], a) and same(t[5:7], b)) or (same(t[3:5], b) and same(t[5:7], a)))]
            if not hit:
                raise SystemExit(f"no such segment: {op}")
            for i in reversed(hit):
                del rt["tracks"][i]
        elif op[0] == "dropvia":
            _, net, p = op
            hit = [i for i, v in enumerate(rt["vias"]) if v[0] == net and same(v[1:3], p)]
            if not hit:
                raise SystemExit(f"no such via: {op}")
            for i in reversed(hit):
                del rt["vias"][i]
        elif op[0] == "track":
            _, net, layer, w, pts = op
            for a, b in zip(pts, pts[1:]):
                rt["tracks"].append([net, layer, w, a[0], a[1], b[0], b[1]])
        elif op[0] == "via":
            _, net, p = op
            rt["vias"].append([net, p[0], p[1]])
        else:
            raise SystemExit(f"unknown operation {op[0]}")


def main(folder):
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(here, "..", folder)
    spec = importlib.util.spec_from_file_location("route_fixes", os.path.join(base, "route_fixes.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    path = os.path.join(base, mod.ROUTES)
    rt = json.load(open(path))
    done = rt.setdefault("fixes", [])
    for name, ops in mod.STAGES:
        if name in done:
            continue
        apply(rt, ops)
        done.append(name)
        print(f"{name}: {len(ops)} operations")
    json.dump(rt, open(path, "w"))
    print(f"{len(rt['tracks'])} track segments, {len(rt['vias'])} vias -> {mod.ROUTES}")


if __name__ == "__main__":
    main(sys.argv[1])
