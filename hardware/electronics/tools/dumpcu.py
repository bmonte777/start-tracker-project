"""Dump the copper of chosen nets of a board (zone fills, tracks, vias, pads) per layer as JSON. Run inside KiCad's Python.
usage: python3 dumpcu.py <board.kicad_pcb> <out.json> NET [NET ...]"""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
want = set(sys.argv[3:])
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
json.dump(out, open(sys.argv[2], "w"))
print("dumped", {n: (len(v["zones"]), len(v["tracks"]), len(v["vias"]), len(v["pads"])) for n, v in out.items()})
