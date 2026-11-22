"""A4 drawings, one part per sheet, ISO first-angle projection. Writes PDF per part + combined set with index.

Views: FRONT (seen from -Y; X right, Z up) top-left; PLAN (from +Z; X right, Y up) below it; LEFT view
(from -X; -Y right, Z up) to the right of the front view (first-angle placement). Feature positions are given
in a hole/feature table from datum O, marked on every view.
"""
from __future__ import annotations
import io, math, os, datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly, Circle as MCircle
from build123d import Pos, Rot, Compound

from . import params as P
from .core import REGISTRY, part_mass
from . import render as R

A4 = (297.0, 210.0)
FRAME = (20.0, 10.0, 287.0, 200.0)
TB = (107.0, 10.0, 287.0, 44.0)
PANEL = (199.0, 44.0, 287.0, 200.0)
VIEWS = (22.0, 46.0, 197.0, 198.0)
SCALES = [5, 2, 1, 0.5, 0.4, 0.25, 0.2]
SCALE_TXT = {5: "5:1", 2: "2:1", 1: "1:1", 0.5: "1:2", 0.4: "1:2.5", 0.25: "1:4", 0.2: "1:5"}
VIEWDEF = {"front": ((0, -1, 0), (0, 0, 1)), "top": ((0, 0, 1), (0, 1, 0)), "left": ((-1, 0, 0), (0, 0, 1))}
LW_VIS, LW_HID, LW_THIN = 0.45, 0.2, 0.18

# per-part drawing options: datum and view set
OPTS = {
    "ST-310": dict(views=("front", "top"), datum="bbox"),
    "ST-311": dict(views=("front", "top", "left"), datum="bbox"),
    "ST-319": dict(views=("top", "front"), datum="bbox"),
    "ST-324": dict(views=("top",), datum="bbox"),
    "ST-323": dict(views=("top",), datum="bbox"),
    "ST-325": dict(views=("front",), datum="bbox"),
    "ST-327": dict(views=("left",), datum="bbox"),
    "ST-328": dict(views=("front",), datum="bbox"),
    "ST-610": dict(views=("top",), datum="bbox"),
    "ST-208": dict(views=("front", "top"), datum="origin", section=True),
    "ST-215": dict(views=("front", "top"), datum="origin", section=True),
    "ST-211": dict(views=("front", "top"), datum="origin", section=True),
    "ST-210": dict(views=("front", "top"), datum="origin", section=True),
    "ST-212": dict(views=("front", "top"), datum="origin"),
    "ST-216": dict(views=("front", "top"), datum="origin"),
    "ST-207": dict(views=("front", "top", "left"), datum="origin"),
    "ST-316": dict(views=("front", "top"), datum="origin"),
    "ST-320": dict(views=("front", "top", "left"), datum="origin"),
    "ST-322": dict(views=("front", "top"), datum="origin"),
    "ST-606": dict(views=("front", "top"), datum="origin"),
    "ST-611": dict(views=("front", "top", "left"), datum="origin"),
}


def _proj(shape, view):
    d, up = VIEWDEF[view]
    org = tuple(5000 * v for v in d)
    vis, hid = shape.project_to_viewport(org, up, (0, 0, 0))
    return vis, hid


def _edge_pts(e, n=24):
    try:
        if e.geom_type.name == "LINE":
            a, b = e.start_point(), e.end_point()
            return np.array([[a.X, a.Y], [b.X, b.Y]])
    except Exception:
        pass
    pts = [e.position_at(t) for t in np.linspace(0, 1, n)]
    return np.array([[p.X, p.Y] for p in pts])


def _bb2(edges):
    allp = np.vstack([_edge_pts(e, 8) for e in edges]) if edges else np.zeros((1, 2))
    return allp.min(axis=0), allp.max(axis=0)


def _arrow(ax, x0, y0, x1, y1, txt, off=6.0, fs=6.5, ext=None):
    """Linear dimension between (x0,y0)-(x1,y1) in paper mm, drawn offset `off` along the normal."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    nx, ny = -dy / L, dx / L
    a = (x0 + nx * off, y0 + ny * off)
    b = (x1 + nx * off, y1 + ny * off)
    for (px, py), (qx, qy) in [((x0, y0), a), ((x1, y1), b)]:
        ax.plot([px + nx * 1.0, qx + nx * 1.5], [py + ny * 1.0, qy + ny * 1.5], color="k", lw=LW_THIN)
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<|-|>", lw=LW_THIN, color="k",
                                                    shrinkA=0, shrinkB=0, mutation_scale=5))
    ang = math.degrees(math.atan2(dy, dx))
    if ang > 90 or ang < -90:
        ang += 180
    ax.text((a[0] + b[0]) / 2 + nx * 1.6, (a[1] + b[1]) / 2 + ny * 1.6, txt, fontsize=fs, rotation=ang,
            ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.2))


def _fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _section_fill(ax, shape, view, plane_y, tf):
    """Hatch the faces of `shape` lying on the cut plane Y = plane_y (front view)."""
    for f in shape.faces():
        try:
            c = f.center()
            n = f.normal_at(c)
        except Exception:
            continue
        if abs(abs(n.Y) - 1) > 1e-3 or abs(c.Y - plane_y) > 1e-3:
            continue
        for wi, w in enumerate([f.outer_wire()] + list(f.inner_wires())):
            pts = []
            for e in w.order_edges() if hasattr(w, "order_edges") else w.edges():
                for t in np.linspace(0, 1, 16):
                    p = e.position_at(t)
                    pts.append(tf(p.X, p.Z))
            pts = np.array(pts)
            if wi == 0:
                ax.add_patch(MPoly(pts, closed=True, fc="none", ec="0.35", hatch="////", lw=0.05))
            else:
                ax.add_patch(MPoly(pts, closed=True, fc="white", ec="none"))


def draw_part(pd, out_dir, sheet_no, sheet_total, iso_png=None):
    opt = OPTS.get(pd.pid, {})
    views = opt.get("views", pd.views if pd.views else ("front", "top", "left"))
    shape = pd.get()
    bb = shape.bounding_box()
    datum = opt.get("datum", "bbox")
    if datum == "bbox":
        d0 = (bb.min.X, bb.min.Y, bb.min.Z)
    else:
        d0 = (0.0, 0.0, 0.0)
    sh = shape.moved(Pos(-d0[0], -d0[1], -d0[2]))
    bb = sh.bounding_box()
    ext = {"front": (bb.size.X, bb.size.Z), "top": (bb.size.X, bb.size.Y), "left": (bb.size.Y, bb.size.Z)}
    W = VIEWS[2] - VIEWS[0] - 6
    H = VIEWS[3] - VIEWS[1] - 10
    G2 = 20.0                                   # paper gap between views, mm

    def fit(vs):
        v0 = vs[0]
        best = None
        for sc in SCALES:
            w = ext[v0][0] * sc + (G2 + ext["left"][0] * sc if "left" in vs else 0)
            others = [v for v in vs[1:] if v in ("top", "front")]
            h = ext[v0][1] * sc + sum(G2 + ext[v][1] * sc for v in others)
            if w <= W and h <= H:
                best = sc
                break
        return best or SCALES[-1]

    s = fit(views)
    if "left" in views and len(views) == 3:
        alt = tuple(v for v in views if v != "left")
        if fit(alt) >= 2 * s:
            views, s = alt, fit(alt)
    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0])
    ax.set_ylim(0, A4[1])
    ax.set_aspect("equal")
    ax.axis("off")
    # frame and title block
    ax.add_patch(Rectangle((FRAME[0], FRAME[1]), FRAME[2] - FRAME[0], FRAME[3] - FRAME[1], fill=False, lw=0.7))
    ax.add_patch(Rectangle((TB[0], TB[1]), TB[2] - TB[0], TB[3] - TB[1], fill=False, lw=0.6))
    ax.plot([PANEL[0], PANEL[0]], [PANEL[1], PANEL[3]], color="k", lw=0.4)
    # place views
    origin = {}
    x_left = VIEWS[0] + 8
    y_top = VIEWS[3] - 8
    v0 = views[0]
    origin[v0] = (x_left, y_top - ext[v0][1] * s)
    yb = origin[v0][1]
    for v in views[1:]:
        if v in ("top", "front"):
            origin[v] = (x_left, yb - G2 - ext[v][1] * s)
            yb = origin[v][1]
        elif v == "left":
            origin[v] = (x_left + ext[v0][0] * s + G2, origin[v0][1])
    section = opt.get("section", False)
    for v in views:
        ox, oy = origin[v]
        vis, hid = _proj(sh, v)
        mn, mx = _bb2(vis)
        # map view coords so that the view's min corner sits at the origin
        tf = (lambda ox, oy, mn: (lambda x, y: (ox + (x - mn[0]) * s, oy + (y - mn[1]) * s)))(ox, oy, mn)
        if section and v == "front":
            ymid = (bb.min.Y + bb.max.Y) / 2
            from .core import box as _box
            cut = sh & _box(bb.min.X - 5, bb.max.X + 5, ymid, bb.max.Y + 5, bb.min.Z - 5, bb.max.Z + 5)
            vis, hid = _proj(cut, v)
            mn2, _ = _bb2(vis)
            tf = (lambda ox, oy, mn: (lambda x, y: (ox + (x - mn[0]) * s, oy + (y - mn[1]) * s)))(ox, oy, mn)
            _section_fill(ax, cut, v, ymid, lambda X, Z: tf(X, Z))
            hid = []
        for e in hid:
            p = _edge_pts(e)
            q = np.array([tf(*xy) for xy in p])
            ax.plot(q[:, 0], q[:, 1], color="0.45", lw=LW_HID, ls=(0, (3, 1.5)))
        for e in vis:
            p = _edge_pts(e)
            q = np.array([tf(*xy) for xy in p])
            ax.plot(q[:, 0], q[:, 1], color="k", lw=LW_VIS, solid_capstyle="round")
        # view label
        lab = {"front": "FRONT", "top": "PLAN (from above)", "left": "LEFT SIDE (from -X)"}[v]
        if section and v == "front":
            lab = "SECTION A-A (through the axis)"
        w, h = ext[v][0] * s, ext[v][1] * s
        ax.text(ox, oy + h + 3.2, lab, fontsize=6.5, fontweight="bold")
        # overall dimensions
        dims = {"front": ("X", "Z"), "top": ("X", "Y"), "left": ("Y", "Z")}[v]
        size = {"X": bb.size.X, "Y": bb.size.Y, "Z": bb.size.Z}
        _arrow(ax, ox, oy, ox + w, oy, _fmt(size[dims[0]]), off=-6.0)
        _arrow(ax, ox + w, oy, ox + w, oy + h, _fmt(size[dims[1]]), off=-6.5)
        # datum O marker
        pO = {"front": (0 - 0, 0), "top": (0, 0), "left": (0, 0)}
        if v == "front":
            dx, dy = (0 - bb.min.X), (0 - bb.min.Z)
        elif v == "top":
            dx, dy = (0 - bb.min.X), (0 - bb.min.Y)
        else:
            dx, dy = (bb.max.Y - 0), (0 - bb.min.Z)
        Ox, Oy = ox + dx * s, oy + dy * s
        ax.add_patch(MCircle((Ox, Oy), 1.4, fill=False, lw=0.35, color="tab:blue"))
        ax.plot([Ox - 2.4, Ox + 2.4], [Oy, Oy], color="tab:blue", lw=0.3)
        ax.plot([Ox, Ox], [Oy - 2.4, Oy + 2.4], color="tab:blue", lw=0.3)
        ax.text(Ox + 1.6, Oy + 1.4, "O", fontsize=5.5, color="tab:blue")
        # axis arrows
        ax_l = {"front": ("X", "Z"), "top": ("X", "Y"), "left": ("-Y", "Z")}[v]
        bx, by = ox - 7, oy - 4
        ax.annotate("", xy=(bx + 5, by), xytext=(bx, by), arrowprops=dict(arrowstyle="->", lw=0.3, color="tab:blue"))
        ax.annotate("", xy=(bx, by + 5), xytext=(bx, by), arrowprops=dict(arrowstyle="->", lw=0.3, color="tab:blue"))
        ax.text(bx + 5.4, by - 0.8, ax_l[0], fontsize=4.5, color="tab:blue")
        ax.text(bx - 1.0, by + 5.6, ax_l[1], fontsize=4.5, color="tab:blue")
        # diameter callouts for bores/pins whose axis looks at the viewer
        look = {"front": "Y", "top": "Z", "left": "X"}[v]
        k = 0
        for f in pd.features:
            if f.kind not in ("bore", "pin") or f.axis.strip("-") != look:
                continue
            fx, fy, fz = (f.pos[0] - d0[0], f.pos[1] - d0[1], f.pos[2] - d0[2])
            if v == "front":
                px, py = ox + (fx - bb.min.X) * s, oy + (fz - bb.min.Z) * s
            elif v == "top":
                px, py = ox + (fx - bb.min.X) * s, oy + (fy - bb.min.Y) * s
            else:
                px, py = ox + (bb.max.Y - fy) * s, oy + (fz - bb.min.Z) * s
            try:
                dval = float(f.size.split()[0])
            except ValueError:
                continue
            ang = math.radians(35 + 25 * k)
            rr = dval / 2 * s
            ax.annotate(f"Ø{f.size}", xy=(px + rr * math.cos(ang), py + rr * math.sin(ang)),
                        xytext=(px + (rr + 9) * math.cos(ang), py + (rr + 9) * math.sin(ang)), fontsize=5.5,
                        arrowprops=dict(arrowstyle="-|>", lw=0.25, color="k", mutation_scale=4),
                        bbox=dict(fc="white", ec="none", pad=0.1))
            k += 1
    # iso image, bottom of the notes panel
    if iso_png is not None and len(pd.features) <= 9:
        box_iso = (PANEL[0] + 6, PANEL[1] + 2, 76, 46)
        ia = fig.add_axes([box_iso[0] / A4[0], box_iso[1] / A4[1], box_iso[2] / A4[0], box_iso[3] / A4[1]])
        ia.imshow(plt.imread(iso_png))
        ia.axis("off")
        ax.text(PANEL[0] + 2, PANEL[1] + 48.5, "ISOMETRIC (not to scale)", fontsize=5)
    # projection symbol (first angle)
    _first_angle_symbol(ax, TB[0] + 150, TB[1] + 6)
    # title block text
    m = P.MAT.get(pd.material, {})
    kg = part_mass(pd)
    rows = [
        ("PART", pd.pid, 0), ("NAME", pd.name, 1),
        ("MATERIAL", m.get("label", pd.material), 2), ("FINISH", pd.finish or "-", 3),
        ("GENERAL TOL.", pd.tol or "-", 4), ("MASS", f"{kg * 1000:.0f} g (calc.)", 5),
    ]
    x0, y0 = TB[0] + 2, TB[3] - 4.2
    for lab, val, i in rows:
        yy = y0 - i * 4.85
        ax.text(x0, yy, lab, fontsize=5, color="0.35")
        ax.text(x0 + 22, yy, val, fontsize=6.4 if lab != "NAME" else 6.8, fontweight="bold" if lab in ("PART", "NAME") else None)
    rx = TB[0] + 128
    for i, (lab, val) in enumerate([("SCALE", SCALE_TXT.get(s, f"{s}")), ("REV", P.REV), ("DATE", P.DATE),
                                   ("SHEET", f"{sheet_no} / {sheet_total}"), ("UNITS", "mm")]):
        yy = y0 - i * 4.85
        ax.text(rx, yy, lab, fontsize=5, color="0.35")
        ax.text(rx + 12, yy, val, fontsize=6.4)
    ax.text(TB[0] + 2, TB[1] + 1.4, "Star Tracker Project  -  github.com/bmonte777/start-tracker-project  -  drawn by Claude for Bruno",
            fontsize=4.6, color="0.3")
    for xx in (TB[0] + 126,):
        ax.plot([xx, xx], [TB[1] + 4, TB[3]], color="k", lw=0.3)
    ax.plot([TB[0], TB[2]], [TB[1] + 4, TB[1] + 4], color="k", lw=0.3)
    # panel: notes + feature table
    _panel(ax, pd, d0)
    fn = os.path.join(out_dir, f"{pd.pid}.pdf")
    fig.savefig(fn)
    png = os.path.join(out_dir, "png", f"{pd.pid}.png")
    os.makedirs(os.path.dirname(png), exist_ok=True)
    fig.savefig(png, dpi=110)
    plt.close(fig)
    return fn, s


def _first_angle_symbol(ax, x, y):
    ax.add_patch(MPoly([(x, y + 2), (x + 8, y + 0.5), (x + 8, y + 7.5), (x, y + 6)], closed=True, fill=False, lw=0.35))
    ax.add_patch(MCircle((x + 14, y + 4), 3.5, fill=False, lw=0.35))
    ax.add_patch(MCircle((x + 14, y + 4), 1.6, fill=False, lw=0.35))
    ax.plot([x - 1, x + 19], [y + 4, y + 4], color="k", lw=0.2, ls=(0, (4, 1, 1, 1)))
    ax.text(x - 1, y - 1.6, "ISO first angle", fontsize=4.4)


def _wrap(t, n):
    words, lines, cur = t.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def _panel(ax, pd, d0):
    x, y = PANEL[0] + 2, PANEL[3] - 4
    ax.text(x, y, "NOTES", fontsize=6.5, fontweight="bold")
    y -= 4.2
    notes = list(pd.notes)
    m = P.MAT.get(pd.material, {})
    if pd.kind == "printed":
        notes = [f"Print in {m.get('label', pd.material)}: {m.get('walls')} walls, {int(m.get('infill', 0) * 100)} % {m.get('pattern')}, "
                 f"layer {m.get('layer')} mm, {m.get('temps')}. Dry {m.get('dry')}.",
                 f"Print orientation: STL is supplied already turned (rotation {pd.print_rot} deg about X, Y, Z).",
                 "Bores marked 'ream': print 0.2 under and ream to size. Heat-set inserts: Ruthex, soldering iron at 230 C."] + notes
    elif pd.kind == "machined":
        notes = ["General tolerance ISO 2768-m. Fits as stated in the table (H7 / h9).",
                 "Threads ISO metric coarse, 6H. Break all sharp edges 0.2-0.5.", "Surface Ra 3.2 unless stated."] + notes
    elif pd.kind == "turned":
        notes = ["General tolerance ISO 2768-m. Surface Ra 1.6.", "Threads ISO metric coarse, 6H."] + notes
    notes.append("Feature positions: from datum O, in the axes shown on each view. STEP file is the master geometry.")
    for n in notes:
        for line in _wrap(n, 62):
            ax.text(x, y, line, fontsize=4.7)
            y -= 2.9
        y -= 0.8
    y -= 2
    ax.text(x, y, "FEATURES", fontsize=6.5, fontweight="bold")
    y -= 3.6
    hdr = ["Qty", "Type", "Size / fit", "X", "Y", "Z", "Dir", "Depth"]
    cx = [x, x + 5, x + 14, x + 36, x + 45, x + 54, x + 63, x + 71]
    for c, h in zip(cx, hdr):
        ax.text(c, y, h, fontsize=4.8, fontweight="bold")
    y -= 1.2
    ax.plot([PANEL[0] + 1, PANEL[2] - 1], [y, y], color="k", lw=0.25)
    y -= 2.8
    kinds = {"thru": "thru", "tap": "tap", "insert": "insert", "cbore": "c'bore", "bore": "bore", "pin": "spigot",
             "slot": "slot", "pocket": "pocket", "pad": "pad", "opening": "opening", "skirt": "skirt", "snap": "snap",
             "face": "face", "shell": "shell", "thread": "thread"}
    for f in pd.features:
        if y < PANEL[1] + (54 if len(pd.features) <= 9 else 4):
            ax.text(x, y, "... more in the STEP file", fontsize=4.5)
            break
        vals = [str(f.qty), kinds.get(f.kind, f.kind), f.size[:17], _fmt(f.pos[0] - d0[0]), _fmt(f.pos[1] - d0[1]),
                _fmt(f.pos[2] - d0[2]), f.axis, "thru" if f.depth is None else _fmt(f.depth)]
        for c, v in zip(cx, vals):
            ax.text(c, y, v, fontsize=4.5)
        y -= 2.5
        if f.note:
            for line in _wrap(f.note, 70)[:2]:
                ax.text(x + 5, y, line, fontsize=4.0, color="0.3")
                y -= 2.2
        y -= 0.5


def iso_image(pd, path, az=-50, el=28):
    from .render import tess, render
    s = pd.get()
    v, t = tess(s, 0.15, 0.3)
    col = tuple(min(1.0, c * 1.25 + 0.15) for c in pd.color)
    im, _ = render([(v, t, col, 0)], az, el, 560, 520, ssaa=2, margin=0.04)
    im.save(path)
    return path


def index_sheet(rows, fn):
    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0])
    ax.set_ylim(0, A4[1])
    ax.axis("off")
    ax.add_patch(Rectangle((FRAME[0], FRAME[1]), FRAME[2] - FRAME[0], FRAME[3] - FRAME[1], fill=False, lw=0.7))
    ax.text(26, 192, "STAR TRACKER - PROTOTYPE P1 - DRAWING SET", fontsize=12, fontweight="bold")
    ax.text(26, 186, f"Index sheet  -  rev {P.REV}  -  {P.DATE}  -  ISO first-angle projection, dimensions in mm, "
                     "machined parts ISO 2768-m", fontsize=7)
    hdr = ["Sheet", "Part", "Name", "Process", "Material", "Qty / head", "Scale"]
    cx = [26, 40, 58, 168, 192, 236, 258]
    y = 178
    for c, h in zip(cx, hdr):
        ax.text(c, y, h, fontsize=6.5, fontweight="bold")
    y -= 1.5
    ax.plot([24, 283], [y, y], color="k", lw=0.4)
    y -= 4
    per_col = 40
    for i, r in enumerate(rows):
        if i == per_col:
            pass
        vals = [str(r[0]), r[1], r[2][:62], r[3], r[4][:22], str(r[5]), r[6]]
        for c, v in zip(cx, vals):
            ax.text(c, y, v, fontsize=5.6)
        y -= 3.85
    ax.text(26, 14, "Process key: machined = 6061-T6 CNC at JLCCNC; turned = stainless 304; printed = Bambu H2S (PAHT-CF / ASA / TPU / PETG) "
                    "with the settings on each sheet.", fontsize=5.5)
    fig.savefig(fn)
    plt.close(fig)
