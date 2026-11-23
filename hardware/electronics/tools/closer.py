"""Closing pass for a board routed by grouter.py: connects what is still open without moving anything.

usage: python3 closer.py <board-folder> [routes-in.json]

Reads <board>/out/<name>.pre.json and the routes file, takes every track and via in it as fixed copper, works out for each
signal net which of its pads are already joined (by geometry: track ends on pads, on vias and on other tracks) and searches
a way between the separate groups on the free cells that are left. Nothing is taken up, so a run can only add
connections. Nets that live on a plane (their pads are joined through vias to an inner layer) are left alone.
KiCad's DRC on the finished board is the check that counts."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grouter as g  # noqa: E402


def islands(R, net, pads, segs, vias):
    """Union-find over the pads, track segments and vias of one net. Returns lists of (kind, index)."""
    nodes = [("p", i) for i in range(len(pads))] + [("s", i) for i in range(len(segs))] + [("v", i) for i in range(len(vias))]
    par = list(range(len(nodes)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def join(a, b):
        par[find(a)] = find(b)
    np_, ns = len(pads), len(segs)

    def in_pad(p, x, y, layer):
        return (p["side"] == "*" or p["side"] == layer or layer == "*") and p["r"][0] - 0.01 <= x <= p["r"][2] + 0.01 and \
            p["r"][1] - 0.01 <= y <= p["r"][3] + 0.01
    for i, s in enumerate(segs):
        for j, p in enumerate(pads):
            if in_pad(p, s[3], s[4], s[1]) or in_pad(p, s[5], s[6], s[1]):
                join(np_ + i, j)
        for j in range(i + 1, ns):
            t = segs[j]
            if t[1] != s[1]:
                continue
            a, b = (s[3], s[4], s[5], s[6]), (t[3], t[4], t[5], t[6])
            if min(a[0], a[2]) - 1.1 > max(b[0], b[2]) or max(a[0], a[2]) + 1.1 < min(b[0], b[2]) or \
                    min(a[1], a[3]) - 1.1 > max(b[1], b[3]) or max(a[1], a[3]) + 1.1 < min(b[1], b[3]):
                continue
            ends_a = min(g.seg_dist((a[0], a[1], a[0], a[1]), b), g.seg_dist((a[2], a[3], a[2], a[3]), b))
            ends_b = min(g.seg_dist((b[0], b[1], b[0], b[1]), a), g.seg_dist((b[2], b[3], b[2], b[3]), a))
            if ends_a <= t[2] / 2 - 0.01 or ends_b <= s[2] / 2 - 0.01 or g.seg_dist(a, b) < 1e-6:
                join(np_ + i, np_ + j)
        for j, v in enumerate(vias):
            if g.seg_dist((v[1], v[2], v[1], v[2]), (s[3], s[4], s[5], s[6])) <= 0.24 and \
                    (math.hypot(v[1] - s[3], v[2] - s[4]) <= 0.24 or math.hypot(v[1] - s[5], v[2] - s[6]) <= 0.24 or True):
                join(np_ + i, np_ + ns + j)
    for i, v in enumerate(vias):
        for j, p in enumerate(pads):
            if in_pad(p, v[1], v[2], "*"):
                join(np_ + ns + i, j)
        for j in range(i + 1, len(vias)):
            if math.hypot(v[1] - vias[j][1], v[2] - vias[j][2]) < 0.2:
                join(np_ + ns + i, np_ + ns + j)
    out = {}
    for k, n in enumerate(nodes):
        out.setdefault(find(k), []).append(n)
    return [grp for grp in out.values() if any(n[0] == "p" for n in grp)]


def cells_of(R, grp, pads, segs, vias):
    c = set()
    for kind, i in grp:
        if kind == "p":
            c |= R.pad_cells(pads[i])
        elif kind == "s":
            s = segs[i]
            c |= R.shape_cells(dict(geom=(s[3], s[4], s[5], s[6]), layers=(R.layers.index(s[1]),)))
        else:
            v = vias[i]
            for l in range(R.NL):
                c.add((l * R.H + R.iy(v[2])) * R.W + R.ix(v[1]))
    return c


def run(folder, routes=None, lcost=None):
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    routes = routes or os.path.join(folder, name + ".routes.json")
    pre = json.load(open(os.path.join(folder, "out", name + ".pre.json")))
    rt = json.load(open(routes))
    plan = pre["plan"]
    pre["tracks"] = pre.get("tracks", []) + [dict(net=t[0], layer=t[1] + ".Cu", w=t[2], a=[t[3], t[4]], b=[t[5], t[6]]) for t in rt["tracks"]]
    pre["vias"] = pre.get("vias", []) + [dict(net=v[0], x=v[1], y=v[2]) for v in rt["vias"]]
    R = g.Router(pre, layers=plan["layers"], widths=plan["widths"])
    lc = lcost or [1 if l in ("F", "B") else 6 for l in R.layers]
    plane = {s["net"] for s in plan["steps"] if s["op"] == "plane"}
    nets = sorted({p["net"] for p in pre["pads"] if p["net"]} - plane)
    added, left = 0, {}
    for net in nets:
        pads = [p for p in pre["pads"] if p["net"] == net and not p["npth"]]
        if len(pads) < 2:
            continue
        segs = [t for t in rt["tracks"] if t[0] == net]
        vias = [v for v in rt["vias"] if v[0] == net]
        groups = islands(R, net, pads, segs, vias)
        if len(groups) < 2:
            continue
        nid = R.id(net)
        cs = [cells_of(R, grp, pads, segs, vias) for grp in groups]
        stuck = set()
        while len(cs) > 1 and len(stuck) < len(cs):
            a = next(i for i in range(len(cs)) if i not in stuck)
            tgt = set().union(*[c for i, c in enumerate(cs) if i != a])
            path = R._search(nid, cs[a], tgt, (0, 0, R.W, R.H), R.widths[0], lc, vcost=300, regmul=3, maxexp=5000000)
            if not path:
                stuck.add(a)
                continue
            sg, vs, cells = R._path_to_copper(nid, path, R.widths[0])
            R.commit(net, sg, vs, R.widths[0], hard=True)
            for (layer, p0, p1) in sg:
                rt["tracks"].append([net, layer, R.widths[0], p0[0], p0[1], p1[0], p1[1]])
            for (x, y) in vs:
                rt["vias"].append([net, x, y])
            end = path[-1]
            eidx = (end[0] * R.H + end[1]) * R.W + end[2]
            b = next(i for i, c in enumerate(cs) if i != a and eidx in c)
            cs[a] |= cells | cs[b]
            del cs[b]
            stuck = set()
            added += 1
        if len(cs) > 1:
            left[net] = len(cs) - 1
    json.dump(dict(tracks=rt["tracks"], vias=rt["vias"], open=left), open(os.path.join(folder, name + ".routes.json"), "w"), separators=(",", ":"))
    print(f"closing pass: {added} connections added; still open by this count: {sum(left.values())} in {len(left)} nets")
    print(" ", left)
    return left


if __name__ == "__main__":
    run(os.path.abspath(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None)
