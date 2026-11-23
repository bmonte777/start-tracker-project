"""Width of the copper between the pins that carry current: for every power net of a board, the narrowest place on the
widest way from one terminal to the others, over tracks and filled copper areas together.

A connection can pass the design-rule check and still be a hair-thin track; this check finds those. It needs the copper
of the laid-out board as JSON (tools/dumpcu.py, run with KiCad's Python) and the list of terminals in the board's
design.py (POWER_PATHS: net -> (list of "REF.pin", width wanted in mm)).

usage:  python3 dumpcu.py <board>.kicad_pcb out/<name>.copper.json NET ...      (inside KiCad's Python)
        python3 pathwidth.py <board-folder>                                      (numpy, scipy, matplotlib)
Writes <board>/out/<name>-pathwidth.json and prints one line per net.
"""
import importlib.util
import json
import math
import os
import sys

import numpy as np
from matplotlib.path import Path
from scipy import ndimage

G = 0.025                                  # raster pitch, mm
STEPS = [1.0, 0.8, 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]      # widths tried, widest first


def raster(net, layers):
    """Boolean grids of one net's copper per layer, the via positions and the pad rectangles."""
    xs, ys = [], []
    for z in net["zones"]:
        xs += [p[0] for p in z["outline"]]
        ys += [p[1] for p in z["outline"]]
    for t in net["tracks"]:
        xs += [t["a"][0], t["b"][0]]
        ys += [t["a"][1], t["b"][1]]
    for p in net["pads"]:
        xs += [p["r"][0], p["r"][2]]
        ys += [p["r"][1], p["r"][3]]
    x0, y0 = min(xs) - 1.5, min(ys) - 1.5
    W, H = int((max(xs) + 1.5 - x0) / G) + 1, int((max(ys) + 1.5 - y0) / G) + 1
    gx, gy = np.meshgrid(x0 + np.arange(W) * G, y0 + np.arange(H) * G)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    grids = {l: np.zeros((H, W), bool) for l in layers}

    def box(l, r):
        i0, i1 = max(0, int((r[0] - x0) / G)), min(W - 1, int(math.ceil((r[2] - x0) / G)))
        j0, j1 = max(0, int((r[1] - y0) / G)), min(H - 1, int(math.ceil((r[3] - y0) / G)))
        return i0, i1, j0, j1
    for z in net["zones"]:
        if z["layer"] not in grids:
            continue
        o = np.array(z["outline"])
        i0, i1, j0, j1 = box(z["layer"], (o[:, 0].min(), o[:, 1].min(), o[:, 0].max(), o[:, 1].max()))
        sub = np.column_stack([gx[j0:j1 + 1, i0:i1 + 1].ravel(), gy[j0:j1 + 1, i0:i1 + 1].ravel()])
        m = Path(o).contains_points(sub)
        for h in z["holes"]:
            m &= ~Path(np.array(h)).contains_points(sub)
        grids[z["layer"]][j0:j1 + 1, i0:i1 + 1] |= m.reshape(j1 - j0 + 1, i1 - i0 + 1)
    for t in net["tracks"]:
        if t["layer"] not in grids:
            continue
        r = t["w"] / 2
        i0, i1, j0, j1 = box(t["layer"], (min(t["a"][0], t["b"][0]) - r, min(t["a"][1], t["b"][1]) - r, max(t["a"][0], t["b"][0]) + r,
                                         max(t["a"][1], t["b"][1]) + r))
        px, py = gx[j0:j1 + 1, i0:i1 + 1], gy[j0:j1 + 1, i0:i1 + 1]
        vx, vy = t["b"][0] - t["a"][0], t["b"][1] - t["a"][1]
        L2 = vx * vx + vy * vy
        u = np.clip(((px - t["a"][0]) * vx + (py - t["a"][1]) * vy) / L2, 0, 1) if L2 > 1e-12 else np.zeros_like(px)
        grids[t["layer"]][j0:j1 + 1, i0:i1 + 1] |= (px - t["a"][0] - u * vx) ** 2 + (py - t["a"][1] - u * vy) ** 2 <= r * r
    for p in net["pads"]:
        for l in p["layers"]:
            if l in grids:
                i0, i1, j0, j1 = box(l, p["r"])
                grids[l][j0:j1 + 1, i0:i1 + 1] = True
    for v in net["vias"]:
        for l in grids:
            i0, i1, j0, j1 = box(l, (v[0] - v[2] / 2, v[1] - v[2] / 2, v[0] + v[2] / 2, v[1] + v[2] / 2))
            px, py = gx[j0:j1 + 1, i0:i1 + 1], gy[j0:j1 + 1, i0:i1 + 1]
            grids[l][j0:j1 + 1, i0:i1 + 1] |= (px - v[0]) ** 2 + (py - v[1]) ** 2 <= (v[2] / 2) ** 2
    return grids, (x0, y0, W, H), box


def joined(net, grids, geo, box, terms, width, use_vias=True):
    """Are all terminals joined by copper at least `width` wide? Returns (yes/no, vias needed on the way or None)."""
    x0, y0, W, H = geo
    n = int(round(width / 2 / G))
    yy, xx = np.ogrid[-n:n + 1, -n:n + 1]
    disk = xx * xx + yy * yy <= n * n
    labels, base = {}, 0
    for l, g in grids.items():
        # copper that a round probe of this width can reach, i.e. opened by the probe
        opened = ndimage.binary_dilation(ndimage.binary_erosion(g, disk), disk) if n > 0 else g
        lab, cnt = ndimage.label(opened)
        lab[lab > 0] += base
        base += cnt
        labels[l] = lab
    par = list(range(base + 1))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    used = {}
    if use_vias:
        for v in net["vias"]:
            hit = set()
            for l, lab in labels.items():
                i0, i1, j0, j1 = box(l, (v[0] - v[2] / 2, v[1] - v[2] / 2, v[0] + v[2] / 2, v[1] + v[2] / 2))
                hit |= set(np.unique(lab[j0:j1 + 1, i0:i1 + 1])) - {0}
            hit = sorted(hit)
            for a in hit[1:]:
                ra, rb = find(hit[0]), find(a)
                if ra != rb:
                    par[ra] = rb
    roots = []
    for (ref, num) in terms:
        got = set()
        for p in net["pads"]:
            if p["ref"] == ref and p["num"] == num:
                for l in p["layers"]:
                    if l in labels:
                        e = n * G + 0.03                   # a narrow pin is reached when the wide copper comes up to it
                        i0, i1, j0, j1 = box(l, (p["r"][0] - e, p["r"][1] - e, p["r"][2] + e, p["r"][3] + e))
                        got |= {find(a) for a in set(np.unique(labels[l][j0:j1 + 1, i0:i1 + 1])) - {0}}
        if not got:
            return False
        roots.append(got)
    common = roots[0]
    for r in roots[1:]:
        common = {find(a) for a in common} & {find(a) for a in r}
    return bool(common)


def main(folder):
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    spec = importlib.util.spec_from_file_location("design", os.path.join(folder, "design.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cu = json.load(open(os.path.join(folder, "out", name + ".copper.json")))
    layers = ["F", "B"] if mod.PCB_ARGS.get("layers", 2) == 2 else ["F", "In1", "In2", "In3", "In4", "B"]
    rows = []
    for net, (terms, want) in mod.POWER_PATHS.items():
        tl = [tuple(t.split(".")) for t in terms]
        grids, geo, box = raster(cu[net], layers)
        res = {}
        for vias in (False, True):
            w_ok = 0.0
            for w in STEPS:
                if joined(cu[net], grids, geo, box, tl, w, vias):
                    w_ok = w
                    break
            res[vias] = w_ok
        rows.append(dict(net=net, terminals=terms, wanted=want, width_one_layer=res[False], width_with_vias=res[True],
                         ok=max(res[False], res[True]) >= want))
        r = rows[-1]
        print(f"{'ok ' if r['ok'] else 'THIN'} {net:9s} wanted {want:.2f}  on one layer {res[False]:.2f}  with vias {res[True]:.2f}   {' '.join(terms)}", flush=True)
    json.dump(rows, open(os.path.join(folder, "out", name + "-pathwidth.json"), "w"), indent=1)
    return rows


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
