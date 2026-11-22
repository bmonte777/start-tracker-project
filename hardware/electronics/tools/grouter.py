"""Grid router for the boards in this folder (numpy + numba, no KiCad needed).

usage: python3 grouter.py <board-folder> [--plot]

Reads  <board>/out/<name>.pre.json  (written by `layout.py <board> --dump`: pads, ground fan-out, keep-outs, the plan from
design.py:route_plan()) and writes <board>/<name>.routes.json, which `layout.py <board>` lays onto the board as tracks and vias.

How it routes
- 0.05 mm grid, 45-degree geometry, outer layers (an inner layer can be opened per step with a cost).
- The plan is worked through in the order design.py gives it: plane connections first (a via to the inner plane beside
  each pad), then each critical group with its own track widths, then everything else, shortest connection first.
- Every fine-pitch IC pin gets a short straight stub first, so no later track can wall a pin in.
- A connection that finds no way is routed over the tracks in its way; those nets are taken up and routed again.
- Clearances are kept by construction (copper is grown by clearance + half the track width before a path is searched);
  KiCad's DRC on the finished board is still the check that counts.
"""
import heapq
import json
import math
import os
import sys
import time

import numpy as np
from numba import njit

G = 0.05           # grid pitch, mm
CLR = 0.127        # copper clearance, mm (the board's net-class clearance)
MARGIN = 0.02      # added to every clearance for grid rounding
VIA_D, VIA_H = 0.5, 0.3
HOLE_CLR = 0.25    # copper to hole wall
HOLE_HOLE = 0.5    # hole wall to hole wall
EDGE = 0.3         # copper to board edge
BIG = 2147483647


# ------------------------------------------------------------------------------------------------ rasterising (numba)
@njit(cache=True)
def r_rect(m, x0, y0, x1, y1, r, nid, ox, oy, g):
    H, W = m.shape
    ia = max(0, int(math.floor((x0 - r - ox) / g)))
    ib = min(W - 1, int(math.ceil((x1 + r - ox) / g)))
    ja = max(0, int(math.floor((y0 - r - oy) / g)))
    jb = min(H - 1, int(math.ceil((y1 + r - oy) / g)))
    rr = r * r
    for j in range(ja, jb + 1):
        py = oy + j * g
        dy = y0 - py if py < y0 else (py - y1 if py > y1 else 0.0)
        for i in range(ia, ib + 1):
            px = ox + i * g
            dx = x0 - px if px < x0 else (px - x1 if px > x1 else 0.0)
            if dx * dx + dy * dy <= rr:
                c = m[j, i]
                if c == 0:
                    m[j, i] = nid
                elif c != nid:
                    m[j, i] = -1


@njit(cache=True)
def r_seg(m, ax, ay, bx, by, r, nid, ox, oy, g):
    H, W = m.shape
    ia = max(0, int(math.floor((min(ax, bx) - r - ox) / g)))
    ib = min(W - 1, int(math.ceil((max(ax, bx) + r - ox) / g)))
    ja = max(0, int(math.floor((min(ay, by) - r - oy) / g)))
    jb = min(H - 1, int(math.ceil((max(ay, by) + r - oy) / g)))
    rr = r * r
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    for j in range(ja, jb + 1):
        py = oy + j * g
        for i in range(ia, ib + 1):
            px = ox + i * g
            if L2 <= 1e-12:
                t = 0.0
            else:
                t = ((px - ax) * vx + (py - ay) * vy) / L2
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            dx, dy = px - (ax + t * vx), py - (ay + t * vy)
            if dx * dx + dy * dy <= rr:
                c = m[j, i]
                if c == 0:
                    m[j, i] = nid
                elif c != nid:
                    m[j, i] = -1


# ------------------------------------------------------------------------------------------------ search (numba)
@njit(cache=True)
def astar(occT, hardT, occV, hardV, hole, novia, reg, nid, src, tmask, tb, vcost, regmul, lcost, soft, softpen, maxexp):
    NL, H, W = occT.shape
    HW = H * W
    dist = np.full(NL * HW, BIG, np.int32)
    par = np.full(NL * HW, -1, np.int8)
    heap = [(0, 0, 0)]
    heap.pop()
    x0, y0, x1, y1 = tb
    for k in range(src.shape[0]):
        l, y, x = src[k, 0], src[k, 1], src[k, 2]
        idx = l * HW + y * W + x
        if dist[idx] != 0:
            dist[idx] = 0
            par[idx] = 100
            dx = x0 - x if x < x0 else (x - x1 if x > x1 else 0)
            dy = y0 - y if y < y0 else (y - y1 if y > y1 else 0)
            heapq.heappush(heap, (15 * max(dx, dy) + 6 * min(dx, dy), 0, idx))
    DX = (1, 1, 0, -1, -1, -1, 0, 1)
    DY = (0, 1, 1, 1, 0, -1, -1, -1)
    nexp = 0
    while len(heap) > 0:
        f, d, idx = heapq.heappop(heap)
        if d > dist[idx]:
            continue
        l = idx // HW
        rem = idx - l * HW
        y = rem // W
        x = rem - y * W
        if tmask[l, y, x] != 0:
            return idx, par, nexp
        nexp += 1
        if nexp > maxexp:
            break
        for k in range(8):
            nx, ny = x + DX[k], y + DY[k]
            if nx < 0 or ny < 0 or nx >= W or ny >= H:
                continue
            c = occT[l, ny, nx]
            extra = 0
            if c != 0 and c != nid:
                if not soft:
                    continue
                hc = hardT[l, ny, nx]
                if hc != 0 and hc != nid:
                    continue
                extra = softpen
            step = (10 if k % 2 == 0 else 14) * lcost[l]
            rg = reg[l, ny, nx]
            if rg != 0 and rg != nid and rg != -nid:
                if rg < 0:
                    continue
                step *= regmul
            nd = d + step + extra
            nidx = l * HW + ny * W + nx
            if nd < dist[nidx]:
                dist[nidx] = nd
                par[nidx] = k
                dx = x0 - nx if nx < x0 else (nx - x1 if nx > x1 else 0)
                dy = y0 - ny if ny < y0 else (ny - y1 if ny > y1 else 0)
                heapq.heappush(heap, (nd + 15 * max(dx, dy) + 6 * min(dx, dy), nd, nidx))
        if hole[y, x] == 0 and novia[y, x] == 0:
            ok = True
            extra = 0
            for l2 in range(NL):
                c = occV[l2, y, x]
                if c != 0 and c != nid:
                    if soft:
                        hc = hardV[l2, y, x]
                        if hc != 0 and hc != nid:
                            ok = False
                            break
                        extra = softpen * 6
                    else:
                        ok = False
                        break
            if ok:
                for l2 in range(NL):
                    if l2 == l or lcost[l2] >= 100:
                        continue
                    nd = d + vcost + extra
                    nidx = l2 * HW + y * W + x
                    if nd < dist[nidx]:
                        dist[nidx] = nd
                        par[nidx] = 10 + l
                        dx = x0 - x if x < x0 else (x - x1 if x > x1 else 0)
                        dy = y0 - y if y < y0 else (y - y1 if y > y1 else 0)
                        heapq.heappush(heap, (nd + 15 * max(dx, dy) + 6 * min(dx, dy), nd, nidx))
    return -1, par, nexp


@njit(cache=True)
def backtrack(par, idx, H, W):
    HW = H * W
    DX = (1, 1, 0, -1, -1, -1, 0, 1)
    DY = (0, 1, 1, 1, 0, -1, -1, -1)
    out = [(0, 0, 0)]
    out.pop()
    while True:
        l = idx // HW
        rem = idx - l * HW
        y = rem // W
        x = rem - y * W
        out.append((l, y, x))
        p = par[idx]
        if p == 100 or p < 0:
            break
        if p >= 10:
            idx = (p - 10) * HW + y * W + x
        else:
            idx = l * HW + (y - DY[p]) * W + (x - DX[p])
    return out


@njit(cache=True)
def _free(occ, hard, nid, x, y, soft):
    c = occ[y, x]
    if c == 0 or c == nid:
        return True
    if soft:
        hc = hard[y, x]
        return hc == 0 or hc == nid
    return False


@njit(cache=True)
def l45_ok(occ, hard, reg, nid, x0, y0, x1, y1, diag_first, soft):
    """Is the two-leg connection (one diagonal leg, one straight leg) free? Also refuses to enter a foreign pour area."""
    dx, dy = x1 - x0, y1 - y0
    sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
    nd = min(abs(dx), abs(dy))
    ns = max(abs(dx), abs(dy)) - nd
    tx, ty = (sx, 0) if abs(dx) > abs(dy) else (0, sy)
    x, y = x0, y0
    for phase in range(2):
        diag = (phase == 0) == diag_first
        n = nd if diag else ns
        for _ in range(n):
            if diag:
                x += sx
                y += sy
            else:
                x += tx
                y += ty
            if not _free(occ, hard, nid, x, y, soft):
                return False
            rg = reg[y, x]
            if rg != 0 and rg != nid and rg != -nid:
                return False
    return True


@njit(cache=True)
def straighten(occ, hard, reg, nid, xs, ys, soft):
    """Replace the staircase path by the fewest two-leg (45 / 90 degree) pieces that are still free."""
    n = len(xs)
    out = [(xs[0], ys[0])]
    i = 0
    while i < n - 1:
        best_j, best_df = i + 1, True
        j = min(n - 1, i + 1500)
        while j > i + 1:
            if l45_ok(occ, hard, reg, nid, xs[i], ys[i], xs[j], ys[j], True, soft):
                best_j, best_df = j, True
                break
            if l45_ok(occ, hard, reg, nid, xs[i], ys[i], xs[j], ys[j], False, soft):
                best_j, best_df = j, False
                break
            j -= max(1, (j - i) // 12)
        x0, y0, x1, y1 = xs[i], ys[i], xs[best_j], ys[best_j]
        dx, dy = x1 - x0, y1 - y0
        nd = min(abs(dx), abs(dy))
        sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
        sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
        if nd > 0 and nd < max(abs(dx), abs(dy)):
            if best_df:
                out.append((x0 + sx * nd, y0 + sy * nd))
            else:
                out.append((x1 - sx * nd, y1 - sy * nd))
        out.append((x1, y1))
        i = best_j
    return out


# ------------------------------------------------------------------------------------------------ the router
class Router:
    def __init__(self, pre, layers=("F", "B"), widths=(0.15, 0.2, 0.3, 0.5), log=print):
        self.pre, self.log = pre, log
        b = pre["bounds"]                      # board rectangle x0, y0, x1, y1
        self.ox, self.oy = b[0], b[1]
        self.W = int(round((b[2] - b[0]) / G)) + 1
        self.H = int(round((b[3] - b[1]) / G)) + 1
        self.layers = list(layers)
        self.NL = len(self.layers)
        self.widths = list(widths)
        self.cls = {w: i for i, w in enumerate(self.widths)}
        self.VIA = len(self.widths)            # class index of the via map
        self.half = [w / 2 for w in self.widths] + [VIA_H / 2 + HOLE_CLR - CLR + 0.01]
        self.nid = {}
        self.names = {}
        self.shapes = []                        # dict(kind, layers, geom, hw, nid, hard, net)
        self.routes = {}                        # net -> list of connections (dict(segs, vias, shape indices))
        self.rips = {}
        self.max_rips = 4
        self.reg_polys = pre.get("regions", [])
        self._static()
        self.build_maps()

    # ---- ids and conversions
    def id(self, net):
        if not net:
            return -1
        if net not in self.nid:
            self.nid[net] = len(self.nid) + 1
            self.names[self.nid[net]] = net
        return self.nid[net]

    def ix(self, x):
        return int(round((x - self.ox) / G))

    def iy(self, y):
        return int(round((y - self.oy) / G))

    def mm(self, i, j):
        return (round(self.ox + i * G, 4), round(self.oy + j * G, 4))

    def lidx(self, side):
        return [i for i, l in enumerate(self.layers) if side == "*" or l == side]

    # ---- fixed geometry
    def _static(self):
        pre = self.pre
        for p in pre["pads"]:
            ls = tuple(self.lidx(p["side"]))
            if p["npth"]:
                self.shapes.append(dict(kind="s", layers=tuple(range(self.NL)), geom=(p["x"], p["y"], p["x"], p["y"]),
                                        hw=p["drill"] / 2 + HOLE_CLR - CLR + 0.08, nid=-1, hard=True, net=""))
                continue
            r = p["r"]
            if p.get("shape") == "c":
                self.shapes.append(dict(kind="s", layers=ls, geom=(p["x"], p["y"], p["x"], p["y"]), hw=(r[2] - r[0]) / 2, nid=self.id(p["net"]),
                                        hard=True, net=p["net"]))
            else:
                self.shapes.append(dict(kind="r", layers=ls, geom=tuple(r), hw=0.0, nid=self.id(p["net"]), hard=True, net=p["net"]))
        for v in pre["vias"]:
            self.shapes.append(dict(kind="s", layers=tuple(range(self.NL)), geom=(v["x"], v["y"], v["x"], v["y"]),
                                    hw=self.half[self.VIA], nid=self.id(v["net"]), hard=True, net=v["net"], via=True))
        for t in pre["tracks"]:
            l = {"F.Cu": "F", "B.Cu": "B", "In2.Cu": "In2"}.get(t["layer"])
            if l in self.layers:
                self.shapes.append(dict(kind="s", layers=(self.layers.index(l),), geom=(t["a"][0], t["a"][1], t["b"][0], t["b"][1]),
                                        hw=t["w"] / 2, nid=self.id(t["net"]), hard=True, net=t["net"]))
        for c in pre.get("cutouts", []):       # circular holes in the board: x, y, radius
            self.shapes.append(dict(kind="s", layers=tuple(range(self.NL)), geom=(c[0], c[1], c[0], c[1]),
                                    hw=c[2] + EDGE - CLR, nid=-1, hard=True, net=""))
        b = pre["bounds"]
        for (cx, cy) in ((b[0], b[1]), (b[0], b[3]), (b[2], b[1]), (b[2], b[3])):   # rounded board corners
            self.shapes.append(dict(kind="r", layers=tuple(range(self.NL)), geom=(cx - 0.45, cy - 0.45, cx + 0.45, cy + 0.45), hw=0.0,
                                    nid=-1, hard=True, net=""))
        for k in pre.get("keepouts", []):      # rectangles x0, y0, x1, y1 with layers
            ls = tuple(i for i, l in enumerate(self.layers) if l in k["layers"])
            if ls:
                self.shapes.append(dict(kind="r", layers=ls, geom=tuple(k["r"]), hw=-CLR, nid=-1, hard=True, net=""))

    def _rast(self, maps, s, only_class=None):
        for k in range(len(self.half)):
            if only_class is not None and k != only_class:
                continue
            r = s["hw"] + CLR + MARGIN + (self.half[k] if k != self.VIA else VIA_D / 2)
            if s.get("via") and k != self.VIA:
                r = max(r, VIA_H / 2 + HOLE_CLR + self.half[k] + MARGIN)
            if r <= 0:
                r = 0.001
            for l in s["layers"]:
                if s["kind"] == "r":
                    r_rect(maps[k][l], s["geom"][0], s["geom"][1], s["geom"][2], s["geom"][3], r, s["nid"], self.ox, self.oy, G)
                else:
                    r_seg(maps[k][l], s["geom"][0], s["geom"][1], s["geom"][2], s["geom"][3], r, s["nid"], self.ox, self.oy, G)

    def build_maps(self):
        t0 = time.time()
        nk = len(self.half)
        self.occ = [np.zeros((self.NL, self.H, self.W), np.int32) for _ in range(nk)]
        self.hard = [np.zeros((self.NL, self.H, self.W), np.int32) for _ in range(nk)]
        self.hole = np.zeros((self.H, self.W), np.int32)
        self.novia = np.zeros((self.H, self.W), np.int32)
        for k in range(nk):
            n = int(math.ceil((EDGE + (self.half[k] if k != self.VIA else VIA_D / 2) + MARGIN) / G))
            for m in (self.occ[k], self.hard[k]):
                m[:, :n, :] = -1
                m[:, -n:, :] = -1
                m[:, :, :n] = -1
                m[:, :, -n:] = -1
        for s in self.shapes:
            if s.get("dead"):
                continue
            self._rast(self.occ, s)
            if s["hard"]:
                self._rast(self.hard, s)
        for p in self.pre["pads"]:
            if p["drill"] > 0:
                r_seg(self.hole, p["x"], p["y"], p["x"], p["y"], p["drill"] / 2 + HOLE_HOLE + VIA_H / 2 + 0.03, 1, self.ox, self.oy, G)
            if p["side"] != "*":
                r_rect(self.novia, p["r"][0], p["r"][1], p["r"][2], p["r"][3], VIA_D / 2 + 0.05, 1, self.ox, self.oy, G)
        for c in self.pre.get("cutouts", []):
            r_seg(self.hole, c[0], c[1], c[0], c[1], c[2] + HOLE_HOLE + VIA_H / 2, 1, self.ox, self.oy, G)
        for s in self.shapes:
            if s.get("via") and not s.get("dead"):
                self._hole(s)
        self.reg = np.zeros((self.NL, self.H, self.W), np.int32)
        from matplotlib.path import Path
        for rg in self.reg_polys:
            if rg["side"] not in self.layers:
                continue
            poly = np.array(rg["poly"])
            i0, i1 = max(0, self.ix(poly[:, 0].min())), min(self.W - 1, self.ix(poly[:, 0].max()))
            j0, j1 = max(0, self.iy(poly[:, 1].min())), min(self.H - 1, self.iy(poly[:, 1].max()))
            xs, ys = np.meshgrid(self.ox + np.arange(i0, i1 + 1) * G, self.oy + np.arange(j0, j1 + 1) * G)
            m = Path(poly).contains_points(np.column_stack([xs.ravel(), ys.ravel()])).reshape(xs.shape)
            sub = self.reg[self.layers.index(rg["side"]), j0:j1 + 1, i0:i1 + 1]
            sub[m] = -self.id(rg["net"]) if rg.get("hard") else self.id(rg["net"])
        self.t_build = time.time() - t0

    def _hole(self, s):
        r_seg(self.hole, s["geom"][0], s["geom"][1], s["geom"][0], s["geom"][1], VIA_H + HOLE_HOLE + 0.03, 1, self.ox, self.oy, G)

    # ---- groups of connected copper per net
    def pad_cells(self, p):
        r = p["r"]
        dmin = min(r[2] - r[0], r[3] - r[1])
        if p.get("shape") in ("c", "o"):
            # round and oval pads: only the cells on the pad's centre line (a point for a circle) are safely on copper
            rad = dmin / 2 - 0.04
            ax, ay, bx, by = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            if r[2] - r[0] > r[3] - r[1]:
                ax, bx = r[0] + dmin / 2, r[2] - dmin / 2
            else:
                ay, by = r[1] + dmin / 2, r[3] - dmin / 2
            out = set()
            i0, i1 = int(math.ceil((r[0] - self.ox) / G)), int(math.floor((r[2] - self.ox) / G))
            j0, j1 = int(math.ceil((r[1] - self.oy) / G)), int(math.floor((r[3] - self.oy) / G))
            for l in self.lidx(p["side"]):
                for j in range(j0, j1 + 1):
                    for i in range(i0, i1 + 1):
                        px, py = self.ox + i * G, self.oy + j * G
                        tx = min(max(px, min(ax, bx)), max(ax, bx))
                        ty = min(max(py, min(ay, by)), max(ay, by))
                        d = math.hypot(px - tx, py - ty)
                        if rad - 0.11 <= d <= rad or (d <= rad and (i + j) % 3 == 0):
                            out.add((l * self.H + j) * self.W + i)
            if out:
                return out
        sh = 0.03 + max(0.3 * p.get("rr", 0.0), 0.0)
        i0, i1 = int(math.ceil((r[0] + sh - self.ox) / G)), int(math.floor((r[2] - sh - self.ox) / G))
        j0, j1 = int(math.ceil((r[1] + sh - self.oy) / G)), int(math.floor((r[3] - sh - self.oy) / G))
        if i1 < i0:
            i0 = i1 = self.ix((r[0] + r[2]) / 2)
        if j1 < j0:
            j0 = j1 = self.iy((r[1] + r[3]) / 2)
        out = set()
        for l in self.lidx(p["side"]):
            for j in range(j0, j1 + 1):
                base = (l * self.H + j) * self.W
                # the rim of the pad is enough as a start or a target; large pads would cost time otherwise
                if j in (j0, j1) or (j - j0) % 4 == 0:
                    out.update(base + i for i in range(i0, i1 + 1))
                else:
                    out.update((base + i0, base + i1))
                    out.update(base + i for i in range(i0, i1 + 1, 4))
        return out

    def wide_cells(self, p, need=0.55):
        return self.pad_cells(p) if min(p["r"][2] - p["r"][0], p["r"][3] - p["r"][1]) >= need else set()

    def net_groups(self, net):
        pads = [p for p in self.pre["pads"] if p["net"] == net and not p["npth"]]
        groups = []
        for p in pads:
            groups.append(dict(cells=self.pad_cells(p), pads=[p], bbox=list(p["r"])))
        # pads that overlap on a shared layer are one piece of copper already
        merged = True
        while merged:
            merged = False
            for a in range(len(groups)):
                for b in range(a + 1, len(groups)):
                    if groups[a]["cells"] & groups[b]["cells"]:
                        self._merge(groups, a, b)
                        merged = True
                        break
                if merged:
                    break
        return groups

    @staticmethod
    def _merge(groups, a, b):
        ga, gb = groups[a], groups[b]
        ga["cells"] |= gb["cells"]
        ga["wide"] = ga.get("wide", set()) | gb.get("wide", set())
        ga["pads"] += gb["pads"]
        ga["bbox"] = [min(ga["bbox"][0], gb["bbox"][0]), min(ga["bbox"][1], gb["bbox"][1]), max(ga["bbox"][2], gb["bbox"][2]),
                      max(ga["bbox"][3], gb["bbox"][3])]
        del groups[b]

    def _src(self, cells):
        a = cells if isinstance(cells, np.ndarray) else np.fromiter(cells, np.int64, len(cells))
        HW = self.H * self.W
        l = a // HW
        rem = a - l * HW
        return np.column_stack([l, rem // self.W, rem % self.W]).astype(np.int32)

    @staticmethod
    def _gdist(a, b):
        dx = max(a["bbox"][0] - b["bbox"][2], b["bbox"][0] - a["bbox"][2], 0)
        dy = max(a["bbox"][1] - b["bbox"][3], b["bbox"][1] - a["bbox"][3], 0)
        return math.hypot(dx, dy)

    # ---- one connection
    def _search(self, nid, src_cells, tgt_cells, tb, w, lcost, soft=False, vcost=500, regmul=8, maxexp=4000000):
        k = self.cls[w]
        # a track may only start where a track of this width is allowed to lie (a wide track cannot start between the
        # pins of a fine-pitch chip)
        flat = self.occ[k].reshape(-1)
        s_arr = np.fromiter(src_cells, np.int64, len(src_cells))
        c = flat[s_arr]
        s_arr = s_arr[(c == 0) | (c == nid)]
        if s_arr.size == 0:
            return None
        src_cells = s_arr
        tmask = np.zeros((self.NL, self.H, self.W), np.uint8)
        t = np.fromiter(tgt_cells, np.int64, len(tgt_cells))
        tmask.reshape(-1)[t] = 1
        idx, par, nexp = astar(self.occ[k], self.hard[k], self.occ[self.VIA], self.hard[self.VIA], self.hole, self.novia, self.reg, nid,
                               self._src(src_cells), tmask, np.array(tb, np.int64), vcost, regmul, np.array(lcost, np.int64), soft, 60, maxexp)
        self.last_nexp = nexp
        if idx < 0:
            return None
        return backtrack(par, idx, self.H, self.W)[::-1]

    def _path_to_copper(self, nid, path, w, soft=False):
        """Cells -> straightened segments (per layer run) and vias, in mm."""
        k = self.cls[w]
        segs, vias, cells = [], [], set()
        run = [path[0]]
        runs = []
        for a, b in zip(path, path[1:]):
            if a[0] != b[0]:
                runs.append(run)
                vias.append(self.mm(a[2], a[1]))
                run = [b]
            else:
                run.append(b)
        runs.append(run)
        for run in runs:
            l = run[0][0]
            if len(run) < 2:
                cells.add((l * self.H + run[0][1]) * self.W + run[0][2])
                continue
            xs = np.array([c[2] for c in run], np.int64)
            ys = np.array([c[1] for c in run], np.int64)
            pts = straighten(self.occ[k][l], self.hard[k][l], self.reg[l], nid, xs, ys, soft)
            pts = [pts[0]] + [q for p_, q in zip(pts, pts[1:]) if q != p_]
            # merge collinear pieces
            out = [pts[0]]
            for q in pts[1:]:
                if len(out) >= 2:
                    (ax, ay), (bx, by) = out[-2], out[-1]
                    if (bx - ax) * (q[1] - by) == (by - ay) * (q[0] - bx) and ((q[0] - bx) * (bx - ax) + (q[1] - by) * (by - ay)) > 0:
                        out[-1] = q
                        continue
                out.append(q)
            for (ax, ay), (bx, by) in zip(out, out[1:]):
                segs.append((self.layers[l], self.mm(ax, ay), self.mm(bx, by)))
                n = max(abs(bx - ax), abs(by - ay))
                sx, sy = (bx > ax) - (bx < ax), (by > ay) - (by < ay)
                base = l * self.H * self.W
                for i in range(n + 1):
                    cells.add(base + (ay + sy * i) * self.W + ax + sx * i)
        for (vx, vy) in vias:
            for l in range(self.NL):
                cells.add((l * self.H + self.iy(vy)) * self.W + self.ix(vx))
        return segs, vias, cells

    def commit(self, net, segs, vias, w, hard=False, unit=None, plane=False):
        nid = self.id(net)
        unit = unit or net
        idxs = []
        for (layer, a, b) in segs:
            s = dict(kind="s", layers=(self.layers.index(layer),), geom=(a[0], a[1], b[0], b[1]), hw=w / 2, nid=nid, hard=hard, net=net, w=w,
                     layer=layer, unit=unit, plane=plane)
            self.shapes.append(s)
            idxs.append(len(self.shapes) - 1)
            self._rast(self.occ, s)
            if hard:
                self._rast(self.hard, s)
        for (x, y) in vias:
            s = dict(kind="s", layers=tuple(range(self.NL)), geom=(x, y, x, y), hw=self.half[self.VIA], nid=nid, hard=hard, net=net, via=True,
                     unit=unit, plane=plane)
            self.shapes.append(s)
            idxs.append(len(self.shapes) - 1)
            self._rast(self.occ, s)
            if hard:
                self._rast(self.hard, s)
            self._hole(s)
        self.routes.setdefault(unit, []).append(idxs)
        return idxs

    def rip(self, unit):
        for idxs in self.routes.pop(unit, []):
            for i in idxs:
                self.shapes[i]["dead"] = True
        self.rips[unit] = self.rips.get(unit, 0) + 1

    def shape_cells(self, s):
        out = set()
        ax, ay, bx, by = self.ix(s["geom"][0]), self.iy(s["geom"][1]), self.ix(s["geom"][2]), self.iy(s["geom"][3])
        n = max(abs(bx - ax), abs(by - ay))
        sx, sy = (bx > ax) - (bx < ax), (by > ay) - (by < ay)
        for l in s["layers"]:
            base = l * self.H * self.W
            for t in range(n + 1):
                out.add(base + (ay + sy * t) * self.W + ax + sx * t)
        return out

    # ---- victims of a path that was searched through other nets' tracks
    def victims(self, segs, vias, w, net):
        out = set()
        mine = [(a[0], a[1], b[0], b[1], w / 2, l) for (l, a, b) in segs] + [(x, y, x, y, VIA_D / 2 + 0.03, "*") for (x, y) in vias]
        for s in self.shapes:
            if s.get("dead") or s["hard"] or s["net"] == net or s["kind"] != "s" or "unit" not in s:
                continue
            sl = "*" if s.get("via") else self.layers[s["layers"][0]]
            g = s["geom"]
            for (ax, ay, bx, by, hw, l) in mine:
                if l != "*" and sl != "*" and l != sl:
                    continue
                if min(g[0], g[2]) - 1.2 > max(ax, bx) or max(g[0], g[2]) + 1.2 < min(ax, bx) or min(g[1], g[3]) - 1.2 > max(ay, by) \
                        or max(g[1], g[3]) + 1.2 < min(ay, by):
                    continue
                lim = hw + s["hw"] + CLR + MARGIN + 0.03
                if s.get("via") and l == "*":
                    lim = max(lim, VIA_H + HOLE_HOLE + 0.05)
                if seg_dist((ax, ay, bx, by), g) < lim:
                    out.add(s["unit"])
                    break
        return out

    # ---- a whole net
    def route_net(self, net, widths, lcost, hard=False, allow_rip=True, vcost=500, regmul=8, groups=None, extra_targets=None, quiet=False):
        nid = self.id(net)
        groups = groups if groups is not None else self.net_groups(net)
        failed = 0
        ripped = set()
        guard = 0
        while len(groups) > 1 and guard < 400:
            guard += 1
            # closest pair of groups first
            best = None
            for a in range(len(groups)):
                for b in range(len(groups)):
                    if a != b and not (groups[a].get("stuck") and groups[b].get("stuck")):
                        d = self._gdist(groups[a], groups[b])
                        if groups[a].get("stuck"):
                            continue
                        if best is None or d < best[0]:
                            best = (d, a, b)
            if best is None:
                break
            _d, a, b = best
            ga = groups[a]
            tgt = set()
            for i, g_ in enumerate(groups):
                if i != a:
                    tgt |= g_["cells"]
            bb = groups[b]["bbox"]
            tb = (self.ix(bb[0]), self.iy(bb[1]), self.ix(bb[2]), self.iy(bb[3]))
            done = None
            for w in widths:
                src_c, tgt_c = ga["cells"], tgt
                if w > 0.35:                      # a wide track may only start and end on copper that is wide itself
                    src_c = ga.get("wide", set())
                    tgt_c = set()
                    for i, g_ in enumerate(groups):
                        if i != a:
                            tgt_c |= g_.get("wide", set())
                    if not src_c or not tgt_c:
                        continue
                path = self._search(nid, src_c, tgt_c, tb, w, lcost, vcost=vcost, regmul=regmul, maxexp=3000000)
                if path:
                    done = (w, path, False)
                    break
            if done is None and allow_rip and self.rips.get(net, 0) < self.max_rips:
                w = widths[-1]
                path = self._search(nid, ga["cells"], tgt, tb, w, lcost, soft=True, vcost=vcost, regmul=regmul, maxexp=4000000)
                if path:
                    done = (w, path, True)
            if done is None:
                ga["stuck"] = True
                failed += 1
                p0 = ga["pads"][0]
                self.why = getattr(self, "why", {})
                self.why[net] = f"{p0['ref']}.{p0['num']} at ({p0['x']:.1f},{p0['y']:.1f}) {p0['side']}: " + (
                    "boxed in" if self.last_nexp < 3000 else ("search limit" if self.last_nexp >= 2900000 else f"no way ({self.last_nexp} cells)"))
                continue
            w, path, soft = done
            segs, vias, cells = self._path_to_copper(nid, path, w, soft)
            if soft:
                v = self.victims(segs, vias, w, net)
                v = {n for n in v}
                for n in v:
                    self.rip(n)
                ripped |= v
                self.build_maps()
                # the straightened path was checked against hard copper only, so it stands
            self.commit(net, segs, vias, w, hard)
            end = path[-1]
            eidx = (end[0] * self.H + end[1]) * self.W + end[2]
            hit = [i for i, g_ in enumerate(groups) if i != a and eidx in g_["cells"]]
            ga["cells"] |= cells
            if w >= 0.5:
                ga["wide"] = ga.get("wide", set()) | cells
            if hit:
                j = hit[0]
                self._merge(groups, a, j) if a < j else self._merge(groups, j, a)
        nfail = sum(1 for g_ in groups if g_.get("stuck"))
        return nfail if len(groups) > 1 else 0, ripped

    # ---- a via to an inner plane (or to a copper area on the other face) beside a pad
    def drop(self, net, pad, region, w=0.25, n=1, maxlen=3.0, soft=False, extra_cells=None):
        """Returns (number of vias made, units taken up on the way). Each drop is its own unit, so it can be redone."""
        nid = self.id(net)
        k = self.VIA
        unit = f"{net}|{pad['ref']}.{pad['num']}|drop"
        maps = self.hard if soft else self.occ
        ok = (self.hole == 0) & (self.novia == 0) & region
        for l in range(self.NL):
            ok &= (maps[k][l] == 0) | (maps[k][l] == nid)
        if soft:                                   # holes of fixed vias still count
            pass
        made, ripped = 0, set()
        cells = self.pad_cells(pad) | (extra_cells or set())
        for _ in range(n):
            tm = np.zeros((self.NL, self.H, self.W), np.uint8)
            i0, i1 = max(0, self.ix(pad["r"][0] - maxlen)), min(self.W - 1, self.ix(pad["r"][2] + maxlen))
            j0, j1 = max(0, self.iy(pad["r"][1] - maxlen)), min(self.H - 1, self.iy(pad["r"][3] + maxlen))
            for l in self.lidx(pad["side"]):
                tm[l, j0:j1 + 1, i0:i1 + 1] = ok[j0:j1 + 1, i0:i1 + 1]
            if not tm.any():
                break
            path = None
            for wtry in [x for x in sorted(self.widths, reverse=True) if x <= w]:
                kk = self.cls[wtry]
                s_arr = np.fromiter(cells, np.int64, len(cells))
                cc = self.occ[kk].reshape(-1)[s_arr]
                s_arr = s_arr[(cc == 0) | (cc == nid)]
                if s_arr.size == 0:
                    continue
                idx, par, _n = astar(self.occ[kk], self.hard[kk], self.occ[k], self.hard[k], self.hole, self.novia, self.reg, nid, self._src(s_arr), tm,
                                 np.array((0, 0, self.W, self.H), np.int64), 100000, 1, np.ones(self.NL, np.int64), soft, 60,
                                 400000 if maxlen < 5 else 1200000)
                if idx >= 0:
                    path = backtrack(par, idx, self.H, self.W)[::-1]
                    break
            if path is None:
                break
            segs, _v, pc = self._path_to_copper(nid, path, wtry, soft)
            end = path[-1]
            via = [self.mm(end[2], end[1])]
            if soft:
                v = self.victims(segs, via, wtry, net)
                for u in v:
                    self.rip(u)
                ripped |= v
                if v:
                    self.build_maps()
            self.commit(net, segs, via, wtry, False, unit=unit, plane=True)
            made += 1
            vx, vy = end[2], end[1]
            r = int(math.ceil((VIA_H + HOLE_HOLE + 0.05) / G))
            ok[max(0, vy - r):vy + r + 1, max(0, vx - r):vx + r + 1] = False
        return made, ripped

    def plane_cells(self, net):
        out = set()
        for s in self.shapes:
            if s.get("plane") and s["net"] == net and not s.get("dead"):
                out |= self.shape_cells(s)
        return out


def seg_dist(a, b):
    """Shortest distance between two segments (x0, y0, x1, y1)."""
    def pt(px, py, s):
        vx, vy = s[2] - s[0], s[3] - s[1]
        L2 = vx * vx + vy * vy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - s[0]) * vx + (py - s[1]) * vy) / L2))
        return math.hypot(px - s[0] - t * vx, py - s[1] - t * vy)

    def ccw(p, q, r):
        return (r[1] - p[1]) * (q[0] - p[0]) - (q[1] - p[1]) * (r[0] - p[0])
    p1, p2, p3, p4 = (a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])
    if p1 != p2 and p3 != p4 and ccw(p1, p2, p3) * ccw(p1, p2, p4) < 0 and ccw(p3, p4, p1) * ccw(p3, p4, p2) < 0:
        return 0.0
    return min(pt(a[0], a[1], b), pt(a[2], a[3], b), pt(b[0], b[1], a), pt(b[2], b[3], a))


# ------------------------------------------------------------------------------------------------ plan runner
def _rect_overlap(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def net_groups_rect(R, net):
    """Groups of pads of one net that already touch (same layer, overlapping copper)."""
    pads = [p for p in R.pre["pads"] if p["net"] == net and not p["npth"]]
    groups = [dict(cells=R.pad_cells(p), pads=[p], bbox=list(p["r"]), wide=R.wide_cells(p)) for p in pads]
    merged = True
    while merged:
        merged = False
        for a in range(len(groups)):
            for b in range(a + 1, len(groups)):
                if any(_rect_overlap(p["r"], q["r"]) and (p["side"] == q["side"] or "*" in (p["side"], q["side"]))
                       for p in groups[a]["pads"] for q in groups[b]["pads"]):
                    R._merge(groups, a, b)
                    merged = True
                    break
            if merged:
                break
    return groups


Router.net_groups = net_groups_rect


def region_mask(R, polys, exclude=(), erode=0.6):
    from matplotlib.path import Path
    from scipy import ndimage
    xs, ys = np.meshgrid(R.ox + np.arange(R.W) * G, R.oy + np.arange(R.H) * G)
    pts = np.column_stack([xs.ravel(), ys.ravel()])
    m = np.zeros(R.H * R.W, bool)
    for poly in polys:
        m |= Path(np.array(poly)).contains_points(pts)
    for poly in exclude:
        m &= ~Path(np.array(poly)).contains_points(pts)
    m = m.reshape(R.H, R.W)
    return ndimage.binary_erosion(m, iterations=int(round(erode / G)))


def fanout(R, plane_nets, length=0.35, min_pads=12, max_pitch_dim=0.32, w=None, plane_regions=None):
    plane_regions = plane_regions or {}
    """A short straight stub out of every fine-pitch IC pin that has something to connect to."""
    w = w or R.widths[0]
    by_ref = {}
    for p in R.pre["pads"]:
        by_ref.setdefault(p["ref"], []).append(p)
    count = {}
    for p in R.pre["pads"]:
        if p["net"]:
            count[p["net"]] = count.get(p["net"], 0) + 1
    n = 0
    stubs = []
    for ref, pads in by_ref.items():
        fine = [p for p in pads if min(p["r"][2] - p["r"][0], p["r"][3] - p["r"][1]) <= max_pitch_dim and p["side"] != "*"]
        if len(fine) < min_pads:
            continue
        cx = sum((p["r"][0] + p["r"][2]) / 2 for p in fine) / len(fine)
        cy = sum((p["r"][1] + p["r"][3]) / 2 for p in fine) / len(fine)
        for p in fine:
            net = p["net"]
            if not net or net in plane_nets or count.get(net, 0) < 2:
                continue
            dx, dy = p["r"][2] - p["r"][0], p["r"][3] - p["r"][1]
            px, py = (p["r"][0] + p["r"][2]) / 2, (p["r"][1] + p["r"][3]) / 2
            if dx >= dy:
                sgn = 1 if px > cx else -1
                a, b = (px, py), (px + sgn * (dx / 2 + length), py)
            else:
                sgn = 1 if py > cy else -1
                a, b = (px, py), (px, py + sgn * (dy / 2 + length))
            # snap to the grid line nearest the pad axis
            a = R.mm(R.ix(a[0]), R.iy(a[1]))
            b = R.mm(R.ix(b[0]), R.iy(b[1]))
            nid = R.id(net)
            k = R.cls[w]
            l = R.lidx(p["side"])[0]
            ok = True
            steps = max(abs(R.ix(b[0]) - R.ix(a[0])), abs(R.iy(b[1]) - R.iy(a[1])))
            sx = (b[0] > a[0]) - (b[0] < a[0])
            sy = (b[1] > a[1]) - (b[1] < a[1])
            for i in range(steps + 1):
                c = R.occ[k][l][R.iy(a[1]) + sy * i, R.ix(a[0]) + sx * i]
                inside = p["r"][0] <= a[0] + sx * i * G <= p["r"][2] and p["r"][1] <= a[1] + sy * i * G <= p["r"][3]
                if c != 0 and c != nid and not inside:
                    ok = False
                    break
            if ok:
                stubs.append((net, R.layers[l], a, b, p))
    for (net, layer, a, b, p) in stubs:
        idxs = R.commit(net, [(layer, a, b)], [], w, hard=True, unit=f"{net}|{p['ref']}.{p['num']}|stub")
        R.shapes[idxs[0]]["stub"] = (p["ref"], p["num"])
        n += 1
    # plane pins of the same chips: a via straight out on the pin's own axis (never sideways in front of a neighbour),
    # at the first distance where it clears the neighbours' stubs; the next pin's via lands further out by itself
    nv = 0
    R.fanned = set()
    for ref, pads in by_ref.items():
        fine = [p for p in pads if min(p["r"][2] - p["r"][0], p["r"][3] - p["r"][1]) <= max_pitch_dim and p["side"] != "*"]
        if len(fine) < min_pads:
            continue
        cx = sum((p["r"][0] + p["r"][2]) / 2 for p in fine) / len(fine)
        cy = sum((p["r"][1] + p["r"][3]) / 2 for p in fine) / len(fine)
        order = sorted(fine, key=lambda p: (abs(p["x"] - cx) > abs(p["y"] - cy), p["x"] > cx, p["y"] > cy, p["x"], p["y"]))
        kth = 0
        for p in order:
            net = p["net"]
            if net not in plane_regions:
                continue
            kth += 1
            reg = plane_regions[net]
            nid = R.id(net)
            dx, dy = p["r"][2] - p["r"][0], p["r"][3] - p["r"][1]
            px, py = (p["r"][0] + p["r"][2]) / 2, (p["r"][1] + p["r"][3]) / 2
            if dx >= dy:
                ux, uy, half = (1 if px > cx else -1), 0, dx / 2
            else:
                ux, uy, half = 0, (1 if py > cy else -1), dy / 2
            l = R.lidx(p["side"])[0]
            k = R.cls[w]
            i0, j0 = R.ix(px), R.iy(py)
            for d in [(0.55 if kth % 2 else 1.3) + 0.05 * t for t in range(0, 30)]:
                i, j = R.ix(px + ux * (half + d)), R.iy(py + uy * (half + d))
                if not (0 <= i < R.W and 0 <= j < R.H) or not reg[j, i] or R.hole[j, i] or R.novia[j, i]:
                    continue
                if any(R.occ[R.VIA][q][j, i] not in (0, nid) for q in range(R.NL)):
                    continue
                steps = max(abs(i - i0), abs(j - j0))
                clear = True
                for t in range(steps + 1):
                    c = R.occ[k][l][j0 + uy * t, i0 + ux * t]
                    x_, y_ = R.ox + (i0 + ux * t) * G, R.oy + (j0 + uy * t) * G
                    inside = p["r"][0] <= x_ <= p["r"][2] and p["r"][1] <= y_ <= p["r"][3]
                    if c != 0 and c != nid and not inside:
                        clear = False
                        break
                if not clear:
                    break
                R.commit(net, [(R.layers[l], R.mm(i0, j0), R.mm(i, j))], [R.mm(i, j)], w, hard=True,
                         unit=f"{net}|{p['ref']}.{p['num']}|fan", plane=True)
                R.fanned.add((p["ref"], p["num"], p["x"], p["y"]))
                nv += 1
                break
    return n, nv


def stub_cells(R, net, pad):
    """Cells of the fan-out stub that belongs to this pad, if it has one."""
    out = set()
    for idxs in R.routes.get(f"{net}|{pad['ref']}.{pad['num']}|stub", []):
        for i in idxs:
            s = R.shapes[i]
            if s.get("stub") == (pad["ref"], pad["num"]) and not s.get("dead"):
                l = s["layers"][0]
                ax, ay, bx, by = R.ix(s["geom"][0]), R.iy(s["geom"][1]), R.ix(s["geom"][2]), R.iy(s["geom"][3])
                nsteps = max(abs(bx - ax), abs(by - ay))
                sx, sy = (bx > ax) - (bx < ax), (by > ay) - (by < ay)
                for t in range(nsteps + 1):
                    out.add((l * R.H + ay + sy * t) * R.W + ax + sx * t)
    return out


def groups_with_stubs(R, net):
    gs = R.net_groups(net)
    for g_ in gs:
        for p in g_["pads"]:
            g_["cells"] |= stub_cells(R, net, p)
    return gs


def live_groups(R, net):
    """Groups of a net as they stand now: pads joined by the tracks and vias already routed for it."""
    gs = groups_with_stubs(R, net)
    for idxs in R.routes.get(net, []):
        cells = set()
        for i in idxs:
            if not R.shapes[i].get("dead"):
                cells |= R.shape_cells(R.shapes[i])
        hit = [k for k, g_ in enumerate(gs) if g_["cells"] & cells]
        if not hit:
            continue
        gs[hit[0]]["cells"] |= cells
        for k in sorted(hit[1:], reverse=True):
            R._merge(gs, hit[0], k)
    merged = True
    while merged:
        merged = False
        for a in range(len(gs)):
            for b in range(a + 1, len(gs)):
                if gs[a]["cells"] & gs[b]["cells"]:
                    R._merge(gs, a, b)
                    merged = True
                    break
            if merged:
                break
    return gs


def hpwl(R, net):
    pads = [p for p in R.pre["pads"] if p["net"] == net]
    return (max(p["x"] for p in pads) - min(p["x"] for p in pads)) + (max(p["y"] for p in pads) - min(p["y"] for p in pads))


def run(folder, plot=False):
    import fnmatch
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    pre = json.load(open(os.path.join(folder, "out", name + ".pre.json")))
    plan = pre["plan"]
    t0 = time.time()
    R = Router(pre, layers=plan.get("layers", ["F", "B"]), widths=plan.get("widths", [0.15, 0.2, 0.3, 0.5]))
    print(f"grid {R.W} x {R.H}, {len(R.shapes)} fixed shapes, maps built in {R.t_build:.1f} s")
    allnets = sorted({p["net"] for p in pre["pads"] if p["net"]})
    npads = {n: sum(1 for p in pre["pads"] if p["net"] == n) for n in allnets}
    plane_nets = {s["net"] for s in plan["steps"] if s["op"] == "plane"}
    padkey = {f"{p['ref']}.{p['num']}@{p['x']},{p['y']}": p for p in pre["pads"]}
    done, report, queue = set(), {}, []
    lc_default = [plan.get("layer_cost", {}).get(l, 1) for l in R.layers]
    settings = {}                                # net -> (widths, layer cost, via cost, region cost)
    planes = {}                                  # net -> dict(step, region, tied pads)

    def lcost(step):
        c = step.get("layer_cost")
        return [c.get(l, 1) for l in R.layers] if c else lc_default

    def push(units):
        for u in units:
            if u not in queue:
                queue.append(u)
            if "|drop" in u:                     # tracks that were tied to this via have lost their end
                net = u.split("|")[0]
                for other in list(R.routes):
                    if other.startswith(net + "|") and other.endswith("|tie"):
                        R.rip(other)
                        if other not in queue:
                            queue.append(other)

    def do_net(net, widths, lc, hard, vcost=500, regmul=8, allow_rip=True):
        t = time.time()
        nfail, ripped = R.route_net(net, widths, lc, hard=hard, vcost=vcost, regmul=regmul, groups=groups_with_stubs(R, net),
                                    allow_rip=allow_rip)
        report[net] = nfail
        done.add(net)
        push(ripped)
        if nfail or time.time() - t > 8:
            print(f"   {net}: {'OPEN ' + str(nfail) + ' [' + getattr(R, 'why', {}).get(net, '') + ']' if nfail else 'ok'} ({time.time() - t:.1f} s)"
                  f"{' took up ' + ' '.join(sorted(ripped)) if ripped else ''}")

    def do_plane_pad(net, p, quiet=False):
        """One pad of a plane net: a via beside it if there is room, otherwise a track to copper that is on the plane."""
        pl = planes[net]
        step = pl["step"]
        key = f"{p['ref']}.{p['num']}"
        area = (p["r"][2] - p["r"][0]) * (p["r"][3] - p["r"][1])
        want = step.get("n", {}).get(p["ref"], step.get("n_big", 2) if area >= step.get("big_area", 1.6) else 1)
        stubs = stub_cells(R, net, p)
        for soft, ml in ((False, step.get("maxlen", 2.5)), (False, 14.0), (True, step.get("maxlen", 2.5)), (True, 14.0)):
            if soft and R.rips.get(f"{net}|{key}|drop", 0) >= 3:
                break
            m, ripped = R.drop(net, p, pl["region"], w=step.get("w", 0.25), n=want if ml < 5 else 1, maxlen=ml, soft=soft, extra_cells=stubs)
            push(ripped)
            if m:
                report.pop(f"{net}|{key}", None)
                return m
        # no via site: a track to the nearest copper of this net that already reaches the plane
        cells = R.plane_cells(net)
        for q in pl["tied"]:
            cells |= R.pad_cells(q)
        if cells:
            near = min(pl["tied"] or [p], key=lambda q: math.hypot(q["x"] - p["x"], q["y"] - p["y"]))
            sub = [dict(cells=cells, pads=[near], bbox=list(p["r"]), wide=set(cells)),
                   dict(cells=R.pad_cells(p) | stubs, pads=[p], bbox=list(p["r"]), wide=R.wide_cells(p))]
            nid = R.id(net)
            path = None
            for soft in (False, True):
                for w in step.get("widths", [0.3, 0.2, 0.15]):
                    path = R._search(nid, sub[1]["cells"], cells, (0, 0, R.W, R.H), w, lc_default, soft=soft, maxexp=1500000)
                    if path:
                        break
                if path:
                    break
            if path:
                segs, vias, _c = R._path_to_copper(nid, path, w, soft)
                if soft:
                    v = R.victims(segs, vias, w, net)
                    for u in v:
                        R.rip(u)
                    push(v)
                    R.build_maps()
                R.commit(net, segs, vias, w, False, unit=f"{net}|{key}@{p['x']},{p['y']}|tie", plane=True)
                report.pop(f"{net}|{key}", None)
                return 0
        report[f"{net}|{key}"] = 1
        if not quiet:
            print(f"   {net}: pad {key} OPEN")
        return 0

    def redo(unit):
        if "|" in unit:
            net, key, kind = unit.split("|")
            if kind == "drop":
                cand = [p for p in pre["pads"] if p["net"] == net and f"{p['ref']}.{p['num']}" == key]
                for p in cand[:1]:
                    do_plane_pad(net, p)
            else:
                p = padkey.get(key)
                if p:
                    do_plane_pad(net, p)
        else:
            widths, lc, vc, rm = settings.get(unit, ([0.15], lc_default, 500, 8))
            do_net(unit, widths, lc, False, vc, rm)

    def drain(limit=400):
        guard = 0
        while queue and guard < limit:
            guard += 1
            u = queue.pop(0)
            if R.rips.get(u, 0) > R.max_rips:
                report[u] = report.get(u, 0) + 1
                print(f"   {u}: taken up too often, left OPEN")
                continue
            redo(u)

    import pickle
    ck = os.path.join(folder, "out", name + ".ckpt.pkl")
    resume = None
    if os.environ.get("GR_RESUME") and os.path.exists(ck):
        st = pickle.load(open(ck, "rb"))
        R.shapes, R.routes, R.rips, R.nid, R.names = st["shapes"], st["routes"], {}, st["nid"], st["names"]
        done, report, settings = st["done"], st["report"], st["settings"]
        resume = st["step"]
        R.build_maps()
        print(f"resumed after step {resume}")
    for si, step in enumerate(plan["steps"]):
        op = step["op"]
        ts = time.time()
        if resume is not None and si <= resume:
            if op == "plane":
                net = step["net"]
                reg = region_mask(R, step["polys"], step.get("exclude", []))
                tied = []
                for p in [p for p in pre["pads"] if p["net"] == net and not p["npth"]]:
                    inreg = reg[min(R.H - 1, max(0, R.iy(p["y"]))), min(R.W - 1, max(0, R.ix(p["x"])))]
                    if (p["side"] == "*" and inreg) or (p["side"] == step.get("surface") and inreg):
                        tied.append(p)
                planes[net] = dict(step=step, region=reg, tied=tied)
            continue
        if op in ("rest",) and os.environ.get("GR_CKPT"):
            pickle.dump(dict(shapes=R.shapes, routes=R.routes, nid=R.nid, names=R.names, done=done, report=report, settings=settings,
                             step=si - 1), open(ck, "wb"))
        if op == "fanout":
            regs = {s_["net"]: region_mask(R, s_["polys"], s_.get("exclude", [])) for s_ in plan["steps"] if s_["op"] == "plane" and not s_.get("surface")}
            n, nv = fanout(R, plane_nets, length=step.get("length", 0.35), plane_regions=regs)
            print(f"fan-out: {n} pin stubs, {nv} plane vias on chip pins")
        elif op == "plane":
            net = step["net"]
            reg = region_mask(R, step["polys"], step.get("exclude", []))
            pads = [p for p in pre["pads"] if p["net"] == net and not p["npth"]]
            planes[net] = dict(step=step, region=reg, tied=[])
            nv = 0
            todo = []
            for p in sorted(pads, key=lambda p: (p["r"][2] - p["r"][0]) * (p["r"][3] - p["r"][1])):
                inreg = reg[min(R.H - 1, max(0, R.iy(p["y"]))), min(R.W - 1, max(0, R.ix(p["x"])))]
                tied = any(p["r"][0] - 0.01 <= t["a"][0] <= p["r"][2] + 0.01 and p["r"][1] - 0.01 <= t["a"][1] <= p["r"][3] + 0.01 for t in pre["tracks"]
                           if t["net"] == net)
                if (p["side"] == "*" and inreg) or tied or (p["side"] == step.get("surface") and inreg) or \
                        (p["ref"], p["num"], p["x"], p["y"]) in getattr(R, "fanned", ()):
                    planes[net]["tied"].append(p)
                    continue
                area = (p["r"][2] - p["r"][0]) * (p["r"][3] - p["r"][1])
                if step.get("ep") and area >= 3.0 and p["side"] != "*":
                    m = ep_vias(R, net, p, reg)
                    if m:
                        nv += m
                        planes[net]["tied"].append(p)
                        continue
                todo.append(p)
            for p in todo:
                nv += do_plane_pad(net, p, quiet=True)
            nopen = sum(1 for k in report if k.startswith(net + "|"))
            print(f"plane {net}: {len(pads)} pads, {nv} vias, {nopen} pads open ({time.time() - ts:.1f} s)")
            done.add(net)
        elif op == "stitch":
            net = step["net"]
            nid = R.id(net)
            reg = region_mask(R, step["polys"], step.get("exclude", []), erode=step.get("erode", 0.5))
            made = 0
            from matplotlib.path import Path
            for poly in step["areas"]:
                xs = [q[0] for q in poly]
                ys = [q[1] for q in poly]
                path = Path(np.array(poly))
                pitch = step.get("pitch", 1.1)
                cnt = 0
                y = min(ys) + 0.4
                while y <= max(ys) - 0.3 and cnt < step.get("max", 12):
                    x = min(xs) + 0.4
                    while x <= max(xs) - 0.3 and cnt < step.get("max", 12):
                        i, j = R.ix(x), R.iy(y)
                        if path.contains_point((x, y)) and reg[j, i] and not R.hole[j, i] and not R.novia[j, i] and \
                                all(R.occ[R.VIA][l][j, i] in (0, nid) for l in range(R.NL)):
                            R.commit(net, [], [R.mm(i, j)], R.widths[0], hard=False, unit=f"{net}|stitch{made + cnt}|stitch", plane=True)
                            cnt += 1
                        x += pitch
                    y += pitch
                made += cnt
            print(f"stitch {net}: {made} vias")
        elif op in ("route", "rest"):
            if op == "route":
                nets = []
                for pat in step["nets"]:
                    for n in allnets:
                        if fnmatch.fnmatchcase(n, pat) and n not in nets and n not in done and npads[n] >= 2:
                            nets.append(n)
                if step.get("order") != "given":
                    nets.sort(key=lambda n: hpwl(R, n))
            else:
                nets = sorted([n for n in allnets if n not in done and npads[n] >= 2], key=lambda n: hpwl(R, n))
            for n in nets:
                widths = step.get("widths", [0.15])
                for pat, wl in plan.get("class_widths", {}).items() if op == "rest" else ():
                    if fnmatch.fnmatchcase(n, pat):
                        widths = wl
                settings[n] = (widths, lcost(step), step.get("via_cost", 500), step.get("region_cost", 3))
                do_net(n, widths, lcost(step), False, step.get("via_cost", 500), step.get("region_cost", 3), allow_rip=step.get("rip", True))
                drain(60)
            print(f"{step.get('name', op)}: {len(nets)} nets, {sum(1 for n in nets if report.get(n))} with open connections "
                  f"({time.time() - ts:.1f} s)")
        drain()
    # last rounds: everything still open is tried again now that the board has settled, without taking anything up
    for rnd in range(3):
        todo = [k for k, v in report.items() if v]
        if not todo:
            break
        for u in todo:
            if "|" in u:
                net, key = u.split("|")[:2]
                key = key.split("@")[0]
                R.rips[f"{net}|{key}|drop"] = 99
                report.pop(u, None)
                for p in [p for p in pre["pads"] if p["net"] == net and f"{p['ref']}.{p['num']}" == key][:1]:
                    if not any(un.startswith(f"{net}|{key}") and un.endswith(("|drop", "|tie")) for un in R.routes):
                        do_plane_pad(net, p)
            else:
                # what is already connected stays; only the missing connections are searched again
                widths, lc, vc, rm = settings.get(u, ([0.15], lc_default, 500, 3))
                nfail, _r = R.route_net(u, widths, lc, vcost=vc, regmul=rm, groups=live_groups(R, u), allow_rip=False)
                report[u] = nfail
        print(f"closing round {rnd + 1}: {sum(1 for v in report.values() if v)} open")
    bad = {n: v for n, v in report.items() if v}
    print(f"routed in {time.time() - t0:.0f} s; open: {len(bad)} {bad if bad else ''}")
    save(R, os.path.join(folder, name + ".routes.json"), bad)
    if plot:
        plot_routes(R, os.path.join(folder, "out", name + "-routes"))
    return bad


def ep_vias(R, net, pad, reg, pitch=1.2):
    """Vias inside a large exposed pad (thermal pad of an IC), on a grid."""
    nid = R.id(net)
    k = R.VIA
    r = pad["r"]
    nx = max(1, int((r[2] - r[0] - 0.7) / pitch) + 1)
    ny = max(1, int((r[3] - r[1] - 0.7) / pitch) + 1)
    made = 0
    for a in range(nx):
        for b in range(ny):
            x = (r[0] + r[2]) / 2 + (a - (nx - 1) / 2) * pitch
            y = (r[1] + r[3]) / 2 + (b - (ny - 1) / 2) * pitch
            i, j = R.ix(x), R.iy(y)
            if R.hole[j, i] or not reg[j, i]:
                continue
            if any(R.occ[k][l][j, i] not in (0, nid) for l in range(R.NL)):
                continue
            R.commit(net, [], [R.mm(i, j)], R.widths[0], hard=True, unit=f"{net}|{pad['ref']}.{pad['num']}|ep", plane=True)
            made += 1
    return made


def save(R, path, bad):
    tracks, vias = [], []
    stub_ends = {}
    for unit, conns in R.routes.items():
        for idxs in conns:
            for i in idxs:
                s = R.shapes[i]
                net = s["net"]
                if s.get("dead"):
                    continue
                if s.get("via"):
                    vias.append([net, s["geom"][0], s["geom"][1]])
                else:
                    tracks.append([net, s["layer"], s["w"], s["geom"][0], s["geom"][1], s["geom"][2], s["geom"][3], 1 if s.get("stub") else 0])
    # a fan-out stub nothing attached to is dropped
    ends = {}
    for t in tracks:
        for (x, y) in ((t[3], t[4]), (t[5], t[6])):
            ends.setdefault((t[0], t[1], round(x, 3), round(y, 3)), 0)
            ends[(t[0], t[1], round(x, 3), round(y, 3))] += 1
    viaset = {(v[0], round(v[1], 3), round(v[2], 3)) for v in vias}
    keep = []
    for t in tracks:
        if t[7]:
            far = (t[0], t[1], round(t[5], 3), round(t[6], 3))
            touched = ends[far] > 1 or (t[0], far[2], far[3]) in viaset or any(
                o is not t and o[0] == t[0] and o[1] == t[1] and seg_dist((t[5], t[6], t[5], t[6]), (o[3], o[4], o[5], o[6])) < 0.01 for o in tracks)
            if not touched:
                continue
        keep.append(t[:7])
    with open(path, "w") as f:
        json.dump(dict(tracks=keep, vias=vias, open=bad), f, separators=(",", ":"))
    print(f"{len(keep)} track segments, {len(vias)} vias -> {os.path.basename(path)}")


def plot_routes(R, base):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    for layer in R.layers:
        fig, ax = plt.subplots(figsize=(24, 15), dpi=100)
        for p in R.pre["pads"]:
            if p["side"] in (layer, "*"):
                r = p["r"]
                ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="#888" if p["net"] == "GND" else "#c33", lw=0, alpha=0.7))
        for s in R.shapes:
            if s.get("dead") or s["kind"] != "s" or "w" not in s and not s.get("via"):
                continue
            if s.get("via"):
                ax.plot(s["geom"][0], s["geom"][1], "o", ms=2.5, color="#0a0")
            elif s["layer"] == layer:
                ax.plot([s["geom"][0], s["geom"][2]], [s["geom"][1], s["geom"][3]], "-", lw=max(0.5, s["w"] * 4), color="#03c", solid_capstyle="round")
        ax.set_xlim(R.ox, R.ox + (R.W - 1) * G)
        ax.set_ylim(R.oy, R.oy + (R.H - 1) * G)
        ax.set_aspect("equal")
        if layer == "B":
            ax.invert_xaxis()
        fig.tight_layout()
        fig.savefig(f"{base}-{layer}.png")
        plt.close(fig)


if __name__ == "__main__":
    sys.exit(1 if run(os.path.abspath(sys.argv[1]), "--plot" in sys.argv) else 0)
