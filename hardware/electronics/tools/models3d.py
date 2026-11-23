"""Envelope 3D models for the two connectors KiCad 9's library has no model for. Body sizes: the 15-way JST-GH top-entry
header is the library's 14-way model plus one 1.25 mm pitch; the SMD JST-PH header takes the body of the through-hole
B4B-PH-K model. Run with build123d installed:  python3 models3d.py   -> ../lib/3d/*.step"""
import os

from build123d import Box, Pos, export_step, import_step

M = os.environ.get("KICAD9_3DMODEL_DIR", "/opt/resolute/usr/share/kicad/3dmodels")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "3d")
os.makedirs(OUT, exist_ok=True)


def bbox(path):
    b = import_step(path).bounding_box()
    return b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z


x0, y0, z0, x1, y1, z1 = bbox(os.path.join(M, "Connector_JST.3dshapes", "JST_GH_BM14B-GHS-TBT_1x14-1MP_P1.25mm_Vertical.step"))
print("GH 14-way model box:", [round(v, 2) for v in (x0, y0, z0, x1, y1, z1)])
w, d, h = (x1 - x0) + 1.25, y1 - y0, z1 - z0
gh = Pos(0, (y0 + y1) / 2, z0 + h / 2) * Box(w, d, h)
export_step(gh, os.path.join(OUT, "JST_GH_BM15B-GHS-TBT_envelope.step"))
print("GH 15-way envelope:", round(w, 2), round(d, 2), round(h, 2))

x0, y0, z0, x1, y1, z1 = bbox(os.path.join(M, "Connector_JST.3dshapes", "JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical.step"))
print("PH 4-way THT model box:", [round(v, 2) for v in (x0, y0, z0, x1, y1, z1)])
w, d, h = x1 - x0, y1 - y0, z1 - max(z0, 0.0)
ph = Pos(0, 0, h / 2) * Box(w, d, h)
export_step(ph, os.path.join(OUT, "JST_PH_B4B-PH-SM4-TB_envelope.step"))
print("PH 4-way envelope:", round(w, 2), round(d, 2), round(h, 2))
