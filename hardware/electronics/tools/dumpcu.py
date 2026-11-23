"""Dump the copper of a board's power nets (zone fills, tracks, vias, pads) per layer as JSON, for tools/pathwidth.py.
Run with KiCad's Python.   usage: python3 dumpcu.py <board-folder>
The nets are the keys of POWER_PATHS in the board's design.py; the result is <board>/out/<name>.copper.json."""
import importlib.util
import json
import os
import sys

import pcbnew

folder = os.path.abspath(sys.argv[1])
name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
spec = importlib.util.spec_from_file_location("design", os.path.join(folder, "design.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
want = set(mod.POWER_PATHS)
b = pcbnew.LoadBoard(os.path.join(folder, name + ".kicad_pcb"))


def xy(p): return [round(p.x / 1e6 - 100, 4), round(100 - p.y / 1e6, 4)]
def chain(c): return [xy(c.CPoint(i)) for i in range(c.PointCount())]
out = {n: dict(zones=[], tracks=[], vias=[], pads=[]) for n in want}
for z in b.Zones():
    n = z.GetNetname()
    if n not in want: continue
    for lid in z.GetLayerSet().Seq():
        ps = z.GetFilledPolysList(lid)
        for i in range(ps.OutlineCount()):
            out[n]["zones"].append(dict(layer=b.GetLayerName(lid).replace(".Cu", ""), outline=chain(ps.Outline(i)),
                                        holes=[chain(ps.Hole(i, h)) for h in range(ps.HoleCount(i))]))
for t in b.GetTracks():
    n = t.GetNetname()
    if n not in want: continue
    if t.Type() == pcbnew.PCB_VIA_T:
        out[n]["vias"].append(xy(t.GetPosition()) + [pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))])
    else:
        out[n]["tracks"].append(dict(layer=t.GetLayerName().replace(".Cu", ""), a=xy(t.GetStart()), b=xy(t.GetEnd()), w=pcbnew.ToMM(t.GetWidth())))
for fp in b.GetFootprints():
    for p in fp.Pads():
        n = p.GetNetname()
        if n not in want: continue
        bb = p.GetBoundingBox()
        a, c = xy(bb.GetOrigin()), xy(bb.GetEnd())
        layers = [l for l in ("F", "In1", "In2", "In3", "In4", "B") if p.IsOnLayer(b.GetLayerID(l + ".Cu"))]
        out[n]["pads"].append(dict(ref=fp.GetReference(), num=p.GetNumber(), layers=layers, r=[min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])],
                                   drill=pcbnew.ToMM(p.GetDrillSize().x)))
os.makedirs(os.path.join(folder, "out"), exist_ok=True)
json.dump(out, open(os.path.join(folder, "out", name + ".copper.json"), "w"))
print(name, "copper of", len(out), "power nets written")
