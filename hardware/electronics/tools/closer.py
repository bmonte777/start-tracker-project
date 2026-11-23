"""Closing pass for a board routed by grouter.py: connects what is still open.

usage: python3 closer.py <board-folder> [routes-in.json]

Reads <board>/out/<name>.pre.json and the routes file, takes every track and via in it as fixed copper, works out for each
signal net which of its pads are already joined (by geometry: track ends on pads, on vias and on other tracks) and searches
a way between the separate groups on the free cells that are left. Before that, loose track pieces are removed; after it,
connections that are still open may take slow signals up, but only if those close again (negotiate). A run can therefore only
add connections. Nets that live on a plane (their pads are joined through vias to an inner layer) are left alone.
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


def prune(pre, rt, skip):
    """Drop what hangs loose: track pieces with an end that touches no pad, via or other track of their net, and vias
    nothing is attached to. Left-over escape tracks and half-made connections only stand in the way of the search."""
    out_t, out_v, gone = [], [], 0
    nets = {}
    for t in rt["tracks"]:
        nets.setdefault(t[0], [[], []])[0].append(t)
    for v in rt["vias"]:
        nets.setdefault(v[0], [[], []])[1].append(v)
    pads_of = {}
    for p in pre["pads"]:
        if p["net"] and not p["npth"]:
            pads_of.setdefault(p["net"], []).append(p)
    for net, (segs, vias) in nets.items():
        if net in skip:
            out_t += segs
            out_v += vias
            continue
        pads = pads_of.get(net, [])
        segs = list(segs)
        fix_s, fix_v = laid(pre, net)           # copper laid by hand in design.py: it stays, and what hangs on it is not loose
        if (fix_s or fix_v) and len(pads) > 1 and len(islands(None, net, pads, fix_s, fix_v)) <= 1:
            gone += len(segs) + len(vias)       # the hand-laid copper alone joins every pad of this net: nothing else is needed
            segs, vias = [], []
        if fix_s:                               # a routed piece that lies on hand-laid copper from end to end adds nothing
            def on_laid(x, y, layer):
                return any(o[1] == layer and g.seg_dist((x, y, x, y), (o[3], o[4], o[5], o[6])) <= o[2] / 2 + 0.03 for o in fix_s)
            n0 = len(segs)
            segs = [s_ for s_ in segs if not (on_laid(s_[3], s_[4], s_[1]) and on_laid(s_[5], s_[6], s_[1])
                                              and on_laid((s_[3] + s_[5]) / 2, (s_[4] + s_[6]) / 2, s_[1]))]
            gone += n0 - len(segs)
        changed = True
        while changed:
            changed = False
            for s in list(segs):
                for (x, y) in ((s[3], s[4]), (s[5], s[6])):
                    ok = any((p["side"] in ("*", s[1])) and p["r"][0] - 0.01 <= x <= p["r"][2] + 0.01 and p["r"][1] - 0.01 <= y <= p["r"][3] + 0.01
                             for p in pads)
                    ok = ok or any(math.hypot(v[1] - x, v[2] - y) <= 0.24 for v in vias + fix_v)
                    ok = ok or any(o is not s and o[1] == s[1] and g.seg_dist((x, y, x, y), (o[3], o[4], o[5], o[6])) <= o[2] / 2 - 0.01
                                   for o in segs + fix_s)
                    if not ok:
                        segs.remove(s)
                        gone += 1
                        changed = True
                        break
        keep_v = []
        for v in vias:
            n = sum(1 for s in segs + fix_s if g.seg_dist((v[1], v[2], v[1], v[2]), (s[3], s[4], s[5], s[6])) <= 0.24)
            inpad = any(p["r"][0] - 0.01 <= v[1] <= p["r"][2] + 0.01 and p["r"][1] - 0.01 <= v[2] <= p["r"][3] + 0.01 for p in pads)
            sides = {p["side"] for p in pads if p["r"][0] - 0.01 <= v[1] <= p["r"][2] + 0.01 and p["r"][1] - 0.01 <= v[2] <= p["r"][3] + 0.01}
            if n >= 2 or (n >= 1 and inpad) or len(sides) >= 2 or "*" in sides:     # a via through two pads joins them by itself
                keep_v.append(v)
            else:
                gone += 1
        # a via that went may leave a track end loose: one more round for those
        segs2 = [s for s in segs if all(
            any((p["side"] in ("*", s[1])) and p["r"][0] - 0.01 <= x <= p["r"][2] + 0.01 and p["r"][1] - 0.01 <= y <= p["r"][3] + 0.01 for p in pads)
            or any(math.hypot(v[1] - x, v[2] - y) <= 0.24 for v in keep_v + fix_v)
            or any(o is not s and o[1] == s[1] and g.seg_dist((x, y, x, y), (o[3], o[4], o[5], o[6])) <= o[2] / 2 - 0.01 for o in segs + fix_s)
            for (x, y) in ((s[3], s[4]), (s[5], s[6])))]
        gone += len(segs) - len(segs2)
        out_t += segs2
        out_v += keep_v
    return out_t, out_v, gone


def tee(rt):
    """Where a track ends on the middle of another track of its net, cut that track there, so that the two share an end
    point (KiCad reports an end that lies on a track but on none of its ends as hanging loose)."""
    by = {}
    for t in rt["tracks"]:
        by.setdefault((t[0], t[1]), []).append(t)
    cut = 0
    for segs in by.values():
        again = True
        while again:
            again = False
            for s in segs:
                for k in (3, 5):
                    x, y = s[k], s[k + 1]
                    if any(o is not s and (math.hypot(o[3] - x, o[4] - y) < 1e-6 or math.hypot(o[5] - x, o[6] - y) < 1e-6) for o in segs):
                        continue                 # it already shares an end point with another track
                    for o in segs:
                        if o is s:
                            continue
                        vx, vy = o[5] - o[3], o[6] - o[4]
                        L2 = vx * vx + vy * vy
                        if L2 < 1e-9:
                            continue
                        u = ((x - o[3]) * vx + (y - o[4]) * vy) / L2
                        px, py = o[3] + u * vx, o[4] + u * vy
                        if 0.0 < u < 1.0 and math.hypot(px - x, py - y) <= 0.04 and min(u, 1 - u) * math.sqrt(L2) > 0.02:
                            s[k], s[k + 1] = round(px, 4), round(py, 4)
                            segs.append([o[0], o[1], o[2], round(px, 4), round(py, 4), o[5], o[6]])
                            o[5], o[6] = round(px, 4), round(py, 4)
                            rt["tracks"].append(segs[-1])
                            cut += 1
                            again = True
                            break
                    if again:
                        break
                if again:
                    break
    rt["tracks"] = [t for t in rt["tracks"] if math.hypot(t[5] - t[3], t[6] - t[4]) > 1e-6]
    return cut


def anchor(pre, rt):
    """A track that ends on the rim of a pad is joined to the pad's centre: KiCad only counts a track as connected when
    its end lies on the pad's copper, and the corner of a chamfered or rounded pad is not copper."""
    n = 0
    have = {(t[0], t[1], round(t[3], 3), round(t[4], 3), round(t[5], 3), round(t[6], 3)) for t in rt["tracks"]}
    pads_of = {}
    for p in pre["pads"]:
        if p["net"] and not p["npth"] and p["side"] != "*":
            pads_of.setdefault(p["net"], []).append(p)
    for t in list(rt["tracks"]):
        for (x, y) in ((t[3], t[4]), (t[5], t[6])):
            for p in pads_of.get(t[0], []):
                r = p["r"]
                if p["side"] != t[1] or not (r[0] - 0.01 <= x <= r[2] + 0.01 and r[1] - 0.01 <= y <= r[3] + 0.01):
                    continue
                rim = min(x - r[0], r[2] - x, y - r[1], r[3] - y)
                if rim < 0.06 and min(r[2] - r[0], r[3] - r[1]) >= 0.6 and p.get("shape") != "c":
                    key = (t[0], t[1], round(x, 3), round(y, 3), round(p["x"], 3), round(p["y"], 3))
                    if key in have or t[2] > 0.16 and False:
                        continue
                    have.add(key)
                    rt["tracks"].append([t[0], t[1], 0.15, x, y, p["x"], p["y"]])
                    n += 1
    return n


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


def make_router(pre0, rt, plan, hard):
    """A router with every track and via of the routes file on it; the nets in hard are fixed, the others can be taken up."""
    R = g.Router(pre0, layers=plan["layers"], widths=plan["widths"])
    for t in rt["tracks"]:
        R.commit(t[0], [(t[1], (t[3], t[4]), (t[5], t[6]))], [], t[2], hard=t[0] in hard, unit=t[0])
    for v in rt["vias"]:
        R.commit(v[0], [], [(v[1], v[2])], R.widths[0], hard=v[0] in hard, unit=v[0])
    return R


def laid(pre, net):
    """The tracks and vias of a net that design.py laid by hand before routing (they are part of the board, not of the
    routes file), in the routes file's form."""
    return ([[net, t["layer"].replace(".Cu", ""), t["w"], t["a"][0], t["a"][1], t["b"][0], t["b"][1]] for t in pre.get("tracks", []) if t["net"] == net],
            [[net, v["x"], v["y"]] for v in pre.get("vias", []) if v["net"] == net])


def close_net(R, rt, pre, net, lc, hard=True):
    """Join the separate groups of one net on free cells. Returns (connections added, connections still missing)."""
    pads = [p for p in pre["pads"] if p["net"] == net and not p["npth"]]
    if len(pads) < 2:
        return 0, 0
    segs = [t for t in rt["tracks"] if t[0] == net] + laid(pre, net)[0]
    vias = [v for v in rt["vias"] if v[0] == net] + laid(pre, net)[1]
    groups = islands(R, net, pads, segs, vias)
    if len(groups) < 2:
        return 0, 0
    nid = R.id(net)
    cs = [cells_of(R, grp, pads, segs, vias) for grp in groups]
    stuck, added = set(), 0
    while len(cs) > 1 and len(stuck) < len(cs):
        a = next(i for i in range(len(cs)) if i not in stuck)
        tgt = set().union(*[c for i, c in enumerate(cs) if i != a])
        path = R._search(nid, cs[a], tgt, (0, 0, R.W, R.H), R.widths[0], lc, vcost=300, regmul=3, maxexp=5000000)
        if not path:
            stuck.add(a)
            continue
        sg, vs, cells = R._path_to_copper(nid, path, R.widths[0])
        if not sg and not vs:
            # the two groups already share a point (a track runs over a pad without ending on it): tie it to the pad
            l0, x0_, y0_ = R.layers[path[0][0]], *R.mm(path[0][2], path[0][1])
            hit = [p for p in pads if p["side"] in ("*", l0) and p["r"][0] <= x0_ <= p["r"][2] and p["r"][1] <= y0_ <= p["r"][3]
                   and math.hypot(p["x"] - x0_, p["y"] - y0_) > 0.02]
            if not hit:
                stuck.add(a)
                continue
            sg = [(l0, (x0_, y0_), (hit[0]["x"], hit[0]["y"]))]
        R.commit(net, sg, vs, R.widths[0], hard=hard, unit=net)
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
    return added, len(cs) - 1


def one_more(R, rt, pre, plan, net, hard, lc, depth, max_victims, why=None):
    """Try to add one connection to net by taking slow signals up. Each net that is taken up is routed again on free cells
    and, if that is not enough and depth allows, may itself take others up (never the nets already being worked on).
    Returns (router, True) if the board is better afterwards, (router, False) with everything as before otherwise."""
    pads = [p for p in pre["pads"] if p["net"] == net and not p["npth"]]
    segs = [t for t in rt["tracks"] if t[0] == net] + laid(pre, net)[0]
    vias = [v for v in rt["vias"] if v[0] == net] + laid(pre, net)[1]
    groups = islands(R, net, pads, segs, vias)
    if len(groups) < 2:
        return R, False
    nid = R.id(net)
    cs = [cells_of(R, grp, pads, segs, vias) for grp in groups]
    npads = {}
    for p in pre["pads"]:
        npads[p["net"]] = npads.get(p["net"], 0) + 1
    banned = set()          # nets that turned out not to give way: the next search has to go round them
    for _alt in range(int(os.environ.get("CLOSER_ALTS", "5"))):
        Rb = make_router(pre, rt, plan, hard | banned) if banned else R
        progress = False
        for a in sorted(range(len(cs)), key=lambda i: len(cs[i]))[:2]:
            tgt = set().union(*[c for i, c in enumerate(cs) if i != a])
            path = Rb._search(nid, cs[a], tgt, (0, 0, R.W, R.H), R.widths[0], lc, soft=True, vcost=200, regmul=3, maxexp=7000000, softpen=500)
            if not path:
                if why is not None:
                    why.append("no way, even through slow signals")
                continue
            sg, vs, _c = Rb._path_to_copper(nid, path, R.widths[0], True)
            if not sg and not vs:
                continue
            victims = tuple(sorted(Rb.victims(sg, vs, R.widths[0], net, slack=0.002)))
            if len(victims) > max_victims:
                big = sorted(victims, key=lambda v: -npads.get(v, 0))[:len(victims) - max_victims]
                banned.update(big)
                progress = True
                if why is not None:
                    why.append("too many in the way: " + " ".join(victims))
                continue
            snap = (list(rt["tracks"]), list(rt["vias"]))
            rt["tracks"] = [t for t in rt["tracks"] if t[0] not in victims] + [[net, l_, R.widths[0], p0[0], p0[1], p1[0], p1[1]] for (l_, p0, p1) in sg]
            rt["vias"] = [v for v in rt["vias"] if v[0] not in victims] + [[net, x, y] for (x, y) in vs]
            fixed = hard | {net}
            R2 = make_router(pre, rt, plan, fixed)
            ok = True
            for v in victims:
                miss = close_net(R2, rt, pre, v, lc, hard=False)[1]
                tries = 0
                while miss and depth > 0 and tries < miss + 1:
                    tries += 1
                    R2, got = one_more(R2, rt, pre, plan, v, fixed | set(victims) - {v}, lc, depth - 1, max_victims)
                    if not got:
                        break
                    miss = close_net(R2, rt, pre, v, lc, hard=False)[1]
                if miss:
                    ok = False
                    banned.add(v)
                    progress = True
                    if why is not None:
                        why.append(f"{v} would not close again")
                    break
            if not ok:
                rt["tracks"], rt["vias"] = snap
                continue
            return make_router(pre, rt, plan, hard), True
        if not progress:
            break
    return R, False


def negotiate(R, rt, pre, plan, left, hard, lc, max_victims=int(os.environ.get("CLOSER_VICTIMS", "4"))):
    """For what is still open: search a way through the slow signals that are in the way, take those nets up, lay the new
    connection and route the nets that were taken up again. The change is kept only if every one of them closes again."""
    won = 0
    depth = int(os.environ.get("CLOSER_DEPTH", "1"))
    for net in list(left):
        for _try in range(left[net]):
            why = []
            n0 = (len(rt["tracks"]), len(rt["vias"]))
            R, got = one_more(R, rt, pre, plan, net, hard, lc, depth, max_victims, why)
            if not got:
                if os.environ.get("CLOSER_WHY"):
                    print(f"   {net}: " + "; ".join(sorted(set(why))), flush=True)
                break
            won += 1
            print(f"   {net}: one more connection", flush=True)
            json.dump(dict(tracks=rt["tracks"], vias=rt["vias"], open={}), open(os.environ.get("CLOSER_SAVE", "/tmp/closer-progress.json"), "w"),
                      separators=(",", ":"))
    return R, won


def plane_pads(R, rt, pre, plane, lc):
    """Pads of plane nets that have neither a via of their own nor a track to one: lead each to the nearest copper of
    its net that does."""
    added, left = 0, {}
    for net in sorted(plane):
        pads = [p for p in pre["pads"] if p["net"] == net and not p["npth"] and p["side"] != "*"]
        segs = [t for t in rt["tracks"] if t[0] == net] + laid(pre, net)[0]
        vias = [v for v in rt["vias"] if v[0] == net] + laid(pre, net)[1]
        groups = islands(R, net, pads, segs, vias)
        withvia = [grp for grp in groups if any(k == "v" for k, _i in grp)]
        if not withvia:
            continue
        tgt = set()
        for grp in withvia:
            tgt |= cells_of(R, grp, pads, segs, vias)
        nid = R.id(net)
        for grp in groups:
            if any(k == "v" for k, _i in grp):
                continue
            src = cells_of(R, grp, pads, segs, vias)
            path = R._search(nid, src, tgt, (0, 0, R.W, R.H), R.widths[0], lc, vcost=200, regmul=3, maxexp=5000000)
            name = ", ".join(f"{pads[i]['ref']}.{pads[i]['num']}" for k, i in grp if k == "p")
            if not path:
                left[f"{net} {name}"] = 1
                continue
            sg, vs, _c = R._path_to_copper(nid, path, R.widths[0])
            R.commit(net, sg, vs, R.widths[0], hard=True, unit=net)
            rt["tracks"] += [[net, l_, R.widths[0], p0[0], p0[1], p1[0], p1[1]] for (l_, p0, p1) in sg]
            rt["vias"] += [[net, x, y] for (x, y) in vs]
            added += 1
    return added, left


def run(folder, routes=None, lcost=None):
    import fnmatch
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    routes = routes or os.path.join(folder, name + ".routes.json")
    pre = json.load(open(os.path.join(folder, "out", name + ".pre.json")))
    rt = json.load(open(routes))
    plan = pre["plan"]
    plane = {s["net"] for s in plan["steps"] if s["op"] == "plane"}
    allnets = sorted({p["net"] for p in pre["pads"] if p["net"]})
    crit = {n for s_ in plan["steps"] if s_["op"] == "route" and s_.get("hard") for pat in s_["nets"] for n in allnets if fnmatch.fnmatchcase(n, pat)}
    if not os.environ.get("CLOSER_KEEP"):
        rt["tracks"], rt["vias"], gone = prune(pre, rt, plane)
        print(f"closing pass: {gone} loose track pieces and vias removed, {anchor(pre, rt)} track ends joined to their pad's centre")
    hard = plane | crit
    R = make_router(pre, rt, plan, hard)
    lc = lcost or [1 if l in ("F", "B") else 3 for l in R.layers]
    added, left = 0, {}
    for net in [n for n in allnets if n not in plane]:
        n_add, n_left = close_net(R, rt, pre, net, lc, hard=net in hard)
        added += n_add
        if n_left:
            left[net] = n_left
    pa, pleft = plane_pads(R, rt, pre, plane, lc)
    print(f"closing pass: {added} connections added on free cells, {pa} supply pads joined to their plane ({pleft or 'none left'}); "
          f"still open by this count: {sum(left.values())} in {len(left)} nets", flush=True)
    for rnd in range(int(os.environ.get("CLOSER_ROUNDS", "2"))):
        if not left:
            break
        R, won = negotiate(R, rt, pre, plan, left, hard, lc)
        left = {}
        for net in [n for n in allnets if n not in plane]:
            n_left = close_net(R, rt, pre, net, lc, hard=net in hard)[1]
            if n_left:
                left[net] = n_left
        print(f"closing pass, round {rnd + 1} of taking up: {won} more; still open by this count: {sum(left.values())} in {len(left)} nets")
        if not won:
            break
    if not os.environ.get("CLOSER_KEEP"):         # what the passes above left hanging (dead ends, vias nothing uses) goes too
        rt["tracks"], rt["vias"], gone = prune(pre, rt, plane)
        print(f"closing pass: {gone} loose pieces removed at the end, {tee(rt)} tracks cut where another ends on them")
    json.dump(dict(tracks=rt["tracks"], vias=rt["vias"], open=left), open(os.path.join(folder, name + ".routes.json"), "w"), separators=(",", ":"))
    print(" ", left)
    return left


if __name__ == "__main__":
    run(os.path.abspath(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None)
