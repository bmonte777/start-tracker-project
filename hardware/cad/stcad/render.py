"""Software renderer (numba z-buffer) for CAD-style shaded images with outlines. No GPU or CAD program needed."""
from __future__ import annotations
import math
import numpy as np
from numba import njit
from PIL import Image, ImageDraw, ImageFont


def tess(shape, tol=0.15, ang=0.3):
    # OCCT can leave a tiny face untriangulated at a coarse tolerance: retry finer, then face by face
    for k in range(3):
        try:
            verts, tris = shape.tessellate(tol / (2 ** k), ang)
            break
        except AttributeError:
            continue
    else:
        verts, tris = [], []
        for f in shape.faces():
            try:
                fv, ft = f.tessellate(tol / 4, ang)
            except AttributeError:
                continue
            n0 = len(verts)
            verts += fv
            tris += [(a + n0, b + n0, c + n0) for (a, b, c) in ft]
    v = np.array([(p.X, p.Y, p.Z) for p in verts], dtype=np.float64)
    t = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return v, t


def view_matrix(az_deg, el_deg):
    """Camera looks from direction (az, el): az measured from +X toward +Y, el above the XY plane."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])   # toward the camera
    up = np.array([0.0, 0.0, 1.0])
    if abs(d[2]) > 0.999:
        up = np.array([0.0, 1.0, 0.0]) if d[2] > 0 else np.array([0.0, -1.0, 0.0])
    x = np.cross(up, d)
    x /= np.linalg.norm(x)
    y = np.cross(d, x)
    return np.stack([x, y, d])     # rows: screen x, screen y, depth (toward camera)


@njit(cache=True)
def _raster(sx, sy, sz, tris, shade, oid, W, H, zbuf, cbuf, ibuf):
    for k in range(tris.shape[0]):
        a, b, c = tris[k, 0], tris[k, 1], tris[k, 2]
        x0, y0, z0 = sx[a], sy[a], sz[a]
        x1, y1, z1 = sx[b], sy[b], sz[b]
        x2, y2, z2 = sx[c], sy[c], sz[c]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-12:
            continue
        xmin = max(int(min(x0, x1, x2)), 0)
        xmax = min(int(max(x0, x1, x2)) + 1, W - 1)
        ymin = max(int(min(y0, y1, y2)), 0)
        ymax = min(int(max(y0, y1, y2)) + 1, H - 1)
        for py in range(ymin, ymax + 1):
            for px in range(xmin, xmax + 1):
                fx, fy = px + 0.5, py + 0.5
                w0 = ((x1 - fx) * (y2 - fy) - (x2 - fx) * (y1 - fy)) / area
                w1 = ((x2 - fx) * (y0 - fy) - (x0 - fx) * (y2 - fy)) / area
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                z = w0 * z0 + w1 * z1 + w2 * z2
                if z > zbuf[py, px]:
                    zbuf[py, px] = z
                    cbuf[py, px, 0] = shade[k, 0]
                    cbuf[py, px, 1] = shade[k, 1]
                    cbuf[py, px, 2] = shade[k, 2]
                    ibuf[py, px] = oid[k]


def render(meshes, az=-35, el=22, W=1600, H=1200, ssaa=2, margin=0.06, bg=(255, 255, 255), fit=None,
           outline=True, scale_override=None):
    """meshes: list of (verts Nx3, tris Mx3, rgb 0..1, id). Returns PIL image and the projection used."""
    R = view_matrix(az, el)
    allv = np.vstack([m[0] for m in meshes]) if fit is None else fit
    P = allv @ R.T
    xmin, xmax = P[:, 0].min(), P[:, 0].max()
    ymin, ymax = P[:, 1].min(), P[:, 1].max()
    Ws, Hs = W * ssaa, H * ssaa
    s = min(Ws * (1 - 2 * margin) / (xmax - xmin), Hs * (1 - 2 * margin) / (ymax - ymin))
    if scale_override:
        s = scale_override * ssaa
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    zbuf = np.full((Hs, Ws), -1e18)
    cbuf = np.zeros((Hs, Ws, 3))
    ibuf = np.full((Hs, Ws), -1, dtype=np.int64)
    light = np.array([0.35, 0.55, 0.75])
    light /= np.linalg.norm(light)
    light2 = np.array([-0.6, -0.2, 0.3])
    light2 /= np.linalg.norm(light2)
    for (v, t, rgb, oid) in meshes:
        if len(t) == 0:
            continue
        q = v @ R.T
        sx = (q[:, 0] - cx) * s + Ws / 2
        sy = Hs / 2 - (q[:, 1] - cy) * s
        sz = q[:, 2]
        e1 = q[t[:, 1]] - q[t[:, 0]]
        e2 = q[t[:, 2]] - q[t[:, 0]]
        n = np.cross(e1, e2)
        nl = np.linalg.norm(n, axis=1)
        nl[nl == 0] = 1
        n /= nl[:, None]
        n[n[:, 2] < 0] *= -1                      # two-sided
        lam = np.clip(n @ (R @ light), 0, 1)
        lam2 = np.clip(n @ (R @ light2), 0, 1)
        spec = np.clip(n[:, 2], 0, 1) ** 24
        k = 0.30 + 0.62 * lam + 0.18 * lam2
        col = np.clip(np.array(rgb)[None, :] * k[:, None] + 0.25 * spec[:, None], 0, 1)
        _raster(sx, sy, sz, t, col, np.full(len(t), oid, dtype=np.int64), Ws, Hs, zbuf, cbuf, ibuf)
    img = (cbuf * 255).astype(np.uint8)
    mask = ibuf < 0
    img[mask] = bg
    if outline:
        edge = np.zeros((Hs, Ws), dtype=bool)
        idd = ibuf
        edge[:, 1:] |= idd[:, 1:] != idd[:, :-1]
        edge[1:, :] |= idd[1:, :] != idd[:-1, :]
        z = np.where(mask, zbuf.min() if (~mask).any() else 0, zbuf)
        dz = np.zeros_like(edge)
        thr = 1.2 / s * 6
        dz[:, 1:] |= np.abs(z[:, 1:] - z[:, :-1]) > thr
        dz[1:, :] |= np.abs(z[1:, :] - z[:-1, :]) > thr
        g = cbuf.mean(axis=2)
        dc = np.zeros_like(edge)
        dc[:, 1:] |= np.abs(g[:, 1:] - g[:, :-1]) > 0.10
        dc[1:, :] |= np.abs(g[1:, :] - g[:-1, :]) > 0.10
        e = edge | dz | (dc & ~mask)
        img[e] = (img[e] * 0.25).astype(np.uint8)
    im = Image.fromarray(img).resize((W, H), Image.LANCZOS)
    return im, dict(R=R, s=s / ssaa, cx=cx, cy=cy, W=W, H=H)


def project_point(p, proj):
    q = np.asarray(p) @ proj["R"].T
    return ((q[0] - proj["cx"]) * proj["s"] + proj["W"] / 2, proj["H"] / 2 - (q[1] - proj["cy"]) * proj["s"])


def font(size=22, bold=False):
    for f in (["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"] if bold else ["DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def caption(im, text, sub=None):
    d = ImageDraw.Draw(im)
    d.text((24, 18), text, fill=(30, 30, 30), font=font(30, True))
    if sub:
        d.text((24, 58), sub, fill=(90, 90, 90), font=font(20))
    return im
