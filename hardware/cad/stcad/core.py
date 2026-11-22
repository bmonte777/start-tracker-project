"""Shared helpers: part registry, hole features, mass estimate for printed parts."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Callable

from build123d import (Axis, Box, Cylinder, Location, Pos, Rot, Part, Compound, Plane, Vector,
                       extrude, make_hull, Circle, Rectangle, RectangleRounded, Polygon, Sketch)

from . import params as P

REGISTRY: dict[str, "PartDef"] = {}


@dataclass
class Feature:
    """One hole/bore feature, for the hole table on the drawing."""
    kind: str                  # 'thru', 'tap', 'insert', 'cbore', 'bore', 'pin', 'slot', 'thread'
    size: str                  # e.g. 'M3', '3.4', '45 H7'
    pos: tuple                 # (x, y, z) in part frame, centre of the entry face
    axis: str = "Z"            # drilling axis in the part frame ('X','Y','Z', '-Z' ...)
    depth: float | None = None  # None = through
    note: str = ""
    qty: int = 1


@dataclass
class PartDef:
    pid: str
    name: str
    kind: str                  # 'printed' | 'machined' | 'turned' | 'bought'
    material: str              # key into P.MAT, or free text for bought parts
    qty: int
    build: Callable[[], Part]
    finish: str = ""
    tol: str = ""
    notes: list = field(default_factory=list)
    print_rot: tuple = (0, 0, 0)       # rotation (deg about X, Y, Z) into print orientation
    ream: list = field(default_factory=list)
    mass_kg: float | None = None       # fixed mass for bought parts
    features: list = field(default_factory=list)
    shape: Part | None = None
    views: tuple = ("front", "top", "left")
    scale: str | None = None
    group: str = ""
    color: tuple = (0.6, 0.6, 0.6)

    def get(self) -> Part:
        if self.shape is None:
            self.features = []
            _CURRENT[0] = self
            self.shape = self.build()
            _CURRENT[0] = None
        return self.shape


_CURRENT: list = [None]


def feat(kind, size, pos, axis="Z", depth=None, note="", qty=1):
    """Record a feature on the part currently being built."""
    if _CURRENT[0] is not None:
        _CURRENT[0].features.append(Feature(kind, size, tuple(round(v, 2) for v in pos), axis, depth, note, qty))


def register(pd: PartDef) -> PartDef:
    REGISTRY[pd.pid] = pd
    return pd


# ---------------------------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------------------------
def cyl(r, h, x=0, y=0, z=0, axis="Z"):
    """Cylinder starting at (x,y,z) and extending +h along axis ('X','Y','Z' or '-X'...)."""
    c = Cylinder(r, abs(h), align=(Align_C, Align_C, Align_MIN))
    sign = -1 if axis.startswith("-") else 1
    a = axis.strip("-")
    if h < 0:
        sign = -sign
    if a == "Z":
        c = c if sign > 0 else Rot(180, 0, 0) * c
    elif a == "X":
        c = Rot(0, 90 * sign, 0) * c
    elif a == "Y":
        c = Rot(-90 * sign, 0, 0) * c
    return Pos(x, y, z) * c


def box(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def polar(n, r, start=0.0):
    return [(r * math.cos(math.radians(start + 360 * i / n)), r * math.sin(math.radians(start + 360 * i / n)))
            for i in range(n)]


def hull_extrude(shapes2d, z0, h):
    """2D hull of circles/rects (given as build123d sketches in XY) extruded from z0 by h."""
    edges = []
    for s in shapes2d:
        edges += s.edges()
    f = make_hull(edges)
    return Pos(0, 0, z0) * extrude(f, h)


def on_plane(part, plane: str):
    """Map a part modelled in XY (sketch frame) onto plane 'YZ' (X = thickness) or 'XZ' (Y = thickness)."""
    if plane == "YZ":       # sketch x->Y, y->Z, extrude z->X
        return Rot(90, 0, 90) * part
    if plane == "XZ":       # sketch x->X, y->Z, extrude z->-Y
        return Rot(90, 0, 0) * part
    return part


# Align shortcuts
from build123d import Align as _A  # noqa: E402
Align_C, Align_MIN, Align_MAX = _A.CENTER, _A.MIN, _A.MAX


def printed_mass(shape, mat_key):
    """Mass of an FDM part: solid shell of `walls` perimeters + top/bottom, rest at infill density."""
    m = P.MAT[mat_key]
    rho = m["rho"]
    v = shape.volume / 1000.0                    # cm3
    shell_t = m["walls"] * P.LINE_W / 10.0       # cm
    v_shell = min(v, shape.area / 100.0 * shell_t)
    return (v_shell + (v - v_shell) * m["infill"]) * rho / 1000.0      # kg


def part_mass(pd: PartDef):
    if pd.mass_kg is not None:
        return pd.mass_kg
    s = pd.get()
    if pd.kind == "printed":
        return printed_mass(s, pd.material)
    return s.volume / 1000.0 * P.MAT[pd.material]["rho"] / 1000.0


def roll_frame():
    """Roll cartridge frame -> world (alt 0, roll 0): origin, x_dir, y_dir (motor), z_dir (input side)."""
    b = math.radians(P.ROLL_CART_ROT)
    o = (P.X_ROLL, P.ROLL_OUT_Y, P.Z_ROLL)
    x = (-math.cos(b), 0.0, math.sin(b))
    y = (-math.sin(b), 0.0, -math.cos(b))
    z = (0.0, -1.0, 0.0)
    return o, x, y, z


def roll_to_world(x, y, z=0.0):
    o, ex, ey, ez = roll_frame()
    return tuple(o[k] + x * ex[k] + y * ey[k] + z * ez[k] for k in range(3))
