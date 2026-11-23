"""Joins the named nets on free cells only, with every other track and via left where it is, and prints what it laid
in the form of route_fixes.py operations (nothing is written).

    python3 tools/closeonly.py <board> NET [NET ...]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closer as c  # noqa: E402


def main(folder, nets):
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    pre = json.load(open(os.path.join(folder, "out", name + ".pre.json")))
    rt = json.load(open(os.path.join(folder, name + ".routes.json")))
    plan = pre["plan"]
    allnets = {t[0] for t in rt["tracks"]} | {v[0] for v in rt["vias"]} | {p["net"] for p in pre["pads"] if p["net"]}
    R = c.make_router(pre, rt, plan, allnets)
    lc = [1 if l in ("F", "B") else 3 for l in R.layers]
    for net in nets:
        n0, v0 = len(rt["tracks"]), len(rt["vias"])
        added, left = c.close_net(R, rt, pre, net, lc, hard=True)
        print(f"# {net}: {added} connections added, {left} still missing")
        for t in rt["tracks"][n0:]:
            print(f'        ("track", "{t[0]}", "{t[1]}", {t[2]}, [({t[3]:.3f}, {t[4]:.3f}), ({t[5]:.3f}, {t[6]:.3f})]),')
        for v in rt["vias"][v0:]:
            print(f'        ("via", "{v[0]}", ({v[1]:.3f}, {v[2]:.3f})),')


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), sys.argv[2:])
