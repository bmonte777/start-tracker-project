"""Board layout as code (KiCad 9 pcbnew API). Coordinates are millimetres from the board origin, X right, Y up,
seen from the top (F.Cu) side - the same sense as the Phase 3 CAD envelopes."""
import json
import math
import os
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisx import parse, find, findall   # noqa: E402

MM = pcbnew.FromMM
KICAD_FP = os.environ.get("KICAD_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
LAYER = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "In1": pcbnew.In1_Cu, "In2": pcbnew.In2_Cu}

# JLCPCB capability (standard service, checked Nov 2026): 2-layer 0.127 / 0.127 mm, 4-layer 0.09 / 0.09 mm track and gap,
# via 0.3 mm drill / 0.6 mm pad as standard (0.2 / 0.45 at extra cost), hole to hole 0.5 mm, copper to routed edge 0.2 mm.
# The boards are drawn to wider limits than the minimum so they stay inside the standard price class.
RULES = {
    2: dict(min_clearance=0.15, min_track_width=0.15, min_via_diameter=0.6, min_via_annular_width=0.13, min_through_hole_diameter=0.3,
            min_hole_to_hole=0.5, min_copper_edge_clearance=0.3, min_hole_clearance=0.25, min_connection=0.15,
            min_silk_clearance=0.0, min_text_height=0.8, min_text_thickness=0.1, solder_mask_to_copper_clearance=0.0),
    4: dict(min_clearance=0.1, min_track_width=0.127, min_via_diameter=0.45, min_via_annular_width=0.1, min_through_hole_diameter=0.2,
            min_hole_to_hole=0.5, min_copper_edge_clearance=0.3, min_hole_clearance=0.25, min_connection=0.127,
            min_silk_clearance=0.0, min_text_height=0.8, min_text_thickness=0.1, solder_mask_to_copper_clearance=0.0),
}


def read_netlist(path):
    root = parse(open(path).read())
    nets = {}
    for n in findall(find(root, "nets"), "net"):
        name = str(find(n, "name")[1])
        for x in findall(n, "node"):
            nets[(str(find(x, "ref")[1]), str(find(x, "pin")[1]))] = name
    comps = {}
    for c in findall(find(root, "components"), "comp"):
        sp = find(c, "sheetpath")
        comps[str(find(c, "ref")[1])] = dict(
            value=str(find(c, "value")[1]), footprint=str(find(c, "footprint")[1]) if find(c, "footprint") else "",
            path=str(find(sp, "tstamps")[1]) + str(find(c, "tstamps")[1]),
            sheetname=str(find(sp, "names")[1]), fields={str(f[1][1]): str(f[2]) if len(f) > 2 else "" for f in findall(find(c, "fields") or [], "field")},
            dnp=any(str(p[1][1]) == "dnp" for p in findall(c, "property") if isinstance(p[1], list)))
    return nets, comps


class PCB:
    def __init__(self, folder, name, layers=2, origin=(100.0, 100.0), default_track=0.2, default_via=(0.6, 0.3), clearance=None):
        self.folder, self.name, self.layers = folder, name, layers
        self.ox, self.oy = origin
        self.path = os.path.join(folder, name + ".kicad_pcb")
        if os.path.exists(self.path):
            os.remove(self.path)
        self.board = pcbnew.NewBoard(self.path)
        self.board.SetCopperLayerCount(layers)
        self.rules = dict(RULES[layers])
        self.default_track, self.default_via = default_track, default_via
        self.clearance = clearance or self.rules["min_clearance"]
        self.model = json.load(open(os.path.join(folder, name + ".model.json")))
        self.netmap, self.comps = read_netlist(os.path.join(folder, "out", name + ".net"))
        self.nets = {}
        self.fps = {}
        self.occ = {"F": [], "B": []}          # occupied rectangles per side (courtyards), board coordinates
        self.padpos = {}                       # net -> [(ref, pad, (x, y), side)]
        self.side = {}
        self._tmpl = {}
        self._load = {}
        self.bounds = None
        self.fanout = {}
        for (r_, p_), n_ in self.netmap.items():
            self.fanout[n_] = self.fanout.get(n_, 0) + 1
        ds = self.board.GetDesignSettings()
        ds.m_MinClearance = MM(self.rules["min_clearance"])
        ds.m_TrackMinWidth = MM(self.rules["min_track_width"])
        ds.m_ViasMinSize = MM(self.rules["min_via_diameter"])
        ds.m_MinThroughDrill = MM(self.rules["min_through_hole_diameter"])
        ds.m_ViasMinAnnularWidth = MM(self.rules["min_via_annular_width"])
        ds.m_CopperEdgeClearance = MM(self.rules["min_copper_edge_clearance"])
        ds.m_HoleToHoleMin = MM(self.rules["min_hole_to_hole"])
        ds.m_HoleClearance = MM(self.rules["min_hole_clearance"])
        nc = ds.m_NetSettings.GetDefaultNetclass()
        nc.SetClearance(MM(self.clearance))
        nc.SetTrackWidth(MM(default_track))
        nc.SetViaDiameter(MM(default_via[0]))
        nc.SetViaDrill(MM(default_via[1]))
        ds.SetAuxOrigin(self.P(0, 0))
        try:
            ds.SetGridOrigin(self.P(0, 0))
        except Exception:
            pass

    def netclass(self, name, track, patterns, clearance=None, via=None):
        """A net class with its own track width; patterns are exact net names or wildcards (KiCad syntax)."""
        ds = self.board.GetDesignSettings()
        ns = ds.m_NetSettings
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(MM(track))
        nc.SetClearance(MM(clearance or self.clearance))
        v = via or self.default_via
        nc.SetViaDiameter(MM(v[0]))
        nc.SetViaDrill(MM(v[1]))
        ns.SetNetclass(name, nc)
        for pat in patterns:
            ns.SetNetclassPatternAssignment(pat, name)
        self._classes = getattr(self, "_classes", []) + [dict(name=name, track_width=track, clearance=clearance or self.clearance,
                                                              via_diameter=v[0], via_drill=v[1], patterns=list(patterns))]

    def sync_classes(self):
        self.board.GetDesignSettings().m_NetSettings.RecomputeEffectiveNetclasses()
        self.board.SynchronizeNetsAndNetClasses(True)

    # ---- geometry
    def P(self, x, y):
        return pcbnew.VECTOR2I(MM(self.ox + x), MM(self.oy - y))

    def xy(self, v):
        return (pcbnew.ToMM(v.x) - self.ox, self.oy - pcbnew.ToMM(v.y))

    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(n)
            self.nets[name] = n
        return self.nets[name]

    # ---- outline and drawings
    def _shape(self, layer, width=0.1):
        s = pcbnew.PCB_SHAPE(self.board)
        s.SetLayer(layer)
        s.SetWidth(MM(width))
        self.board.Add(s)
        return s

    def outline_circle(self, r, cx=0.0, cy=0.0, layer=pcbnew.Edge_Cuts):
        s = self._shape(layer)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetCenter(self.P(cx, cy))
        s.SetEnd(self.P(cx + r, cy))
        return s

    def line(self, a, b, layer=pcbnew.Edge_Cuts, width=0.1):
        s = self._shape(layer, width)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(self.P(*a))
        s.SetEnd(self.P(*b))
        return s

    def arc(self, centre, start, angle_deg, layer=pcbnew.Edge_Cuts, width=0.1):
        s = self._shape(layer, width)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(self.P(*centre))
        s.SetStart(self.P(*start))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(-angle_deg, pcbnew.DEGREES_T), True)
        return s

    def outline_rect(self, w, h, r=0.0, cx=0.0, cy=0.0):
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        if r <= 0:
            for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                self.line(a, b)
            return
        self.line((x0 + r, y0), (x1 - r, y0))
        self.line((x1, y0 + r), (x1, y1 - r))
        self.line((x1 - r, y1), (x0 + r, y1))
        self.line((x0, y1 - r), (x0, y0 + r))
        self.arc((x1 - r, y0 + r), (x1 - r, y0), 90)
        self.arc((x1 - r, y1 - r), (x1, y1 - r), 90)
        self.arc((x0 + r, y1 - r), (x0 + r, y1), 90)
        self.arc((x0 + r, y0 + r), (x0, y0 + r), 90)

    def text(self, s, x, y, size=1.0, layer=pcbnew.F_SilkS, thick=None, rot=0, mirror=None):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(self.P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        t.SetTextThickness(MM(thick or max(0.12, size * 0.15)))
        t.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        if mirror if mirror is not None else layer in (pcbnew.B_SilkS, pcbnew.B_Fab, pcbnew.B_Cu):
            t.SetMirrored(True)
        self.board.Add(t)
        return t

    # ---- parts
    def place(self, ref, x, y, rot=0, side="F", ref_text=True, ref_size=0.8):
        c = self.comps[ref]
        lib, fpname = c["footprint"].split(":", 1)
        libdir = os.path.join(KICAD_FP, lib + ".pretty")
        if lib == "ST":
            libdir = os.path.join(self.folder, "..", "lib", "ST.pretty")
        fp = pcbnew.FootprintLoad(libdir, fpname)
        if fp is None:
            raise RuntimeError(f"footprint not found: {c['footprint']} ({ref})")
        fp.SetFPID(pcbnew.LIB_ID(lib, fpname))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetPosition(self.P(x, y))
        self.board.Add(fp)
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        # bottom side: mirrored about the Y axis, then turned counter-clockwise by rot as seen from the top
        fp.SetOrientationDegrees(180 + rot if side == "B" else rot)
        for pad in fp.Pads():
            net = self.netmap.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(self.net(net))
        m = [p for p in self.model["parts"] if p["ref"] == ref][0]
        if m["dnp"]:
            fp.SetDNP(True)
            fp.SetExcludedFromPosFiles(True)
        if not m.get("bom", True):
            fp.SetExcludedFromPosFiles(True)
            fp.SetExcludedFromBOM(True)
        r = fp.Reference()
        r.SetTextSize(pcbnew.VECTOR2I(MM(ref_size), MM(ref_size)))
        r.SetTextThickness(MM(0.12))
        r.SetVisible(bool(ref_text))
        fp.Value().SetVisible(False)
        self.fps[ref] = fp
        self.side[ref] = side
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd).BBox()
        a, b = self.xy(pcbnew.VECTOR2I(cy.GetLeft(), cy.GetBottom())), self.xy(pcbnew.VECTOR2I(cy.GetRight(), cy.GetTop()))
        rect = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        if rect[2] - rect[0] > 0.01:
            self.occ[side].append(rect)
        tht = [p_ for p_ in fp.Pads() if p_.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)]
        for p_ in tht:
            px, py = self.xy(p_.GetPosition())
            hw = pcbnew.ToMM(max(p_.GetSize().x, p_.GetSize().y)) / 2 + 0.45
            for sd in ("F", "B"):
                self.occ[sd].append((px - hw, py - hw, px + hw, py + hw))
        for p_ in fp.Pads():
            if p_.GetNetname():
                self.padpos.setdefault(p_.GetNetname(), []).append((ref, p_.GetNumber(), self.xy(p_.GetPosition()), side))
        return fp

    # ---- automatic placement of the small parts next to the pin they serve
    def block(self, side, rect):
        for sd in (("F", "B") if side == "*" else (side,)):
            self.occ[sd].append(rect)

    def _template(self, ref):
        c = self.comps[ref]
        key = c["footprint"]
        if key not in self._tmpl:
            lib, fpname = key.split(":", 1)
            libdir = os.path.join(self.folder, "..", "lib", "ST.pretty") if lib == "ST" else os.path.join(KICAD_FP, lib + ".pretty")
            fp = pcbnew.FootprintLoad(libdir, fpname)
            cy = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            mm = pcbnew.ToMM
            self._tmpl[key] = dict(
                pads={}, cy=(mm(cy.GetLeft()), -mm(cy.GetBottom()), mm(cy.GetRight()), -mm(cy.GetTop())),
                small=(mm(cy.GetWidth()) <= 2.2 and mm(cy.GetHeight()) <= 1.2) or "R_1206" in fpname)
            for p_ in fp.Pads():
                self._tmpl[key]["pads"].setdefault(p_.GetNumber(), (mm(p_.GetPosition().x), -mm(p_.GetPosition().y)))
        return self._tmpl[key]

    @staticmethod
    def _xf(pt, side, rot):
        x, y = pt
        if side == "B":
            x = -x
        for _ in range((rot // 90) % 4):
            x, y = -y, x
        return x, y

    def _free(self, side, rect, margin=0.12):
        x0, y0, x1, y1 = rect
        bx0, by0, bx1, by1 = self.bounds
        if x0 < bx0 or y0 < by0 or x1 > bx1 or y1 > by1:
            return False
        for (a0, b0, a1, b1) in self.occ[side]:
            if x0 < a1 + margin and x1 > a0 - margin and y0 < b1 + margin and y1 > b0 - margin:
                return False
        return True

    def _target(self, ref, owner):
        """Pin of this part to pull toward an already placed pad: the most local net first, the owner's pins preferred."""
        best = None
        for (r_, pin), net in self.netmap.items():
            if r_ != ref:
                continue
            pads = [q for q in self.padpos.get(net, []) if q[0] != ref]
            if not pads:
                continue
            own = [q for q in pads if q[0] == owner]
            cand = own or pads
            cand.sort(key=lambda q: self._load.get((q[0], q[1], q[2]), 0))
            q = cand[0]
            rank = (0 if own else 1, 1 if net == "GND" else 0, self.fanout.get(net, 99))
            if best is None or rank < best[0]:
                best = (rank, pin, q)
        return best

    def autoplace(self, refs, near=7.0, far=40.0, both_sides=True, step=0.4):
        import math
        failed = []
        for ref in refs:
            if ref in self.fps:
                continue
            m = [p for p in self.model["parts"] if p["ref"] == ref][0]
            t = self._template(ref)
            tgt = self._target(ref, m.get("owner"))
            if tgt is None:
                failed.append(ref)
                continue
            _rank, pin, (aref, apad, (tx, ty), aside) = tgt
            x0, y0, x1, y1 = t["cy"]
            done = False
            tries = [(aside, near)]
            if both_sides and t["small"]:
                tries.append(("F" if aside == "B" else "B", near))
            tries.append((aside, far))
            for side, rmax in tries:
                r = 0.0
                while r <= rmax and not done:
                    npts = max(1, int(2 * math.pi * r / step))
                    for k in range(npts):
                        ang = 2 * math.pi * k / npts
                        cx0, cy0 = tx + r * math.cos(ang), ty + r * math.sin(ang)
                        for rot in (0, 90, 180, 270):
                            px, py = self._xf(t["pads"][pin], side, rot)
                            cx, cy = round((cx0 - px) / 0.05) * 0.05, round((cy0 - py) / 0.05) * 0.05
                            c1, c2 = self._xf((x0, y0), side, rot), self._xf((x1, y1), side, rot)
                            rect = (cx + min(c1[0], c2[0]), cy + min(c1[1], c2[1]), cx + max(c1[0], c2[0]), cy + max(c1[1], c2[1]))
                            if self._free(side, rect):
                                self.place(ref, cx, cy, rot=rot, side=side, ref_text=False)
                                self._load[(aref, apad, (tx, ty))] = self._load.get((aref, apad, (tx, ty)), 0) + 1
                                done = True
                                break
                        if done:
                            break
                    r += step
                if done:
                    break
            if not done:
                failed.append(ref)
        return failed

    def ref_at(self, ref, x, y, rot=0, size=0.8):
        r = self.fps[ref].Reference()
        r.SetPosition(self.P(x, y))
        r.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        r.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        r.SetVisible(True)

    def pad(self, ref, num, idx=0):
        pads = [p for p in self.fps[ref].Pads() if p.GetNumber() == str(num)]
        return self.xy(pads[idx].GetPosition())

    def solid(self, ref, *nums):
        """Connect these pads to their zone without thermal spokes (fine-pitch IC and connector pads)."""
        for p in self.fps[ref].Pads():
            if not nums or p.GetNumber() in [str(n) for n in nums]:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    def pt(self, p):
        """A point is (x, y) or ('REF', 'pad') or ('REF', 'pad', index)."""
        if isinstance(p[0], str):
            return self.pad(*p)
        return p

    # ---- copper
    def track(self, net, pts, w=None, layer="F"):
        n = self.net(net)
        pts = [self.pt(p) for p in pts]
        for a, b in zip(pts, pts[1:]):
            if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(self.P(*a))
            t.SetEnd(self.P(*b))
            t.SetWidth(MM(w or self.default_track))
            t.SetLayer(LAYER[layer])
            t.SetNet(n)
            self.board.Add(t)

    def via(self, net, p, dia=None, drill=None):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(self.P(*self.pt(p)))
        v.SetDrill(MM(drill or self.default_via[1]))
        try:
            v.SetWidth(pcbnew.F_Cu, MM(dia or self.default_via[0]))
        except TypeError:
            v.SetWidth(MM(dia or self.default_via[0]))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(self.net(net))
        self.board.Add(v)
        return v

    def rect(self, x0, y0, x1, y1):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    def zone(self, net, layer, pts=None, clearance=0.25, min_w=0.2, solid=False, priority=0):
        z = pcbnew.ZONE(self.board)
        z.SetLayer(LAYER[layer])
        z.SetNet(self.net(net))
        o = z.Outline()
        o.NewOutline()
        if pts is None:
            pts = getattr(self, "_default_zone", None)
        for (x, y) in pts:
            v = self.P(x, y)
            o.Append(v.x, v.y)
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(min_w))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.25))
        z.SetThermalReliefSpokeWidth(MM(0.3))
        z.SetAssignedPriority(priority)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        self.board.Add(z)
        return z

    def keepout(self, layers, pts, tracks=True, vias=True, copper=True):
        z = pcbnew.ZONE(self.board)
        ls = pcbnew.LSET()
        for l in layers:
            ls.AddLayer(LAYER[l])
        z.SetLayerSet(ls)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(tracks)
        z.SetDoNotAllowVias(vias)
        z.SetDoNotAllowCopperPour(copper)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        o = z.Outline()
        o.NewOutline()
        for (x, y) in pts:
            v = self.P(x, y)
            o.Append(v.x, v.y)
        self.board.Add(z)
        return z

    def fill(self):
        pcbnew.ZONE_FILLER(self.board).Fill(self.board.Zones())

    # ---- files
    def save(self):
        self.board.BuildConnectivity()
        pcbnew.SaveBoard(self.path, self.board)
        try:
            pcbnew.GetSettingsManager().SaveProject()
        except Exception:
            pass
        self._patch_project()

    def _patch_project(self):
        pro = os.path.join(self.folder, self.name + ".kicad_pro")
        d = json.load(open(pro)) if os.path.exists(pro) else {}
        b = d.setdefault("board", {}).setdefault("design_settings", {})
        b.setdefault("rules", {}).update(self.rules)
        # No check is switched off here: every DRC message is reported, and the ones accepted are listed with their
        # reason in docs/04-electronics.md.
        ns = d.setdefault("net_settings", {})
        classes = ns.setdefault("classes", [{}])
        if not classes:
            classes.append({})
        classes[0].update({"name": "Default", "clearance": self.clearance, "track_width": self.default_track,
                           "via_diameter": self.default_via[0], "via_drill": self.default_via[1]})
        have = {c.get("name") for c in classes}
        pats = ns.setdefault("netclass_patterns", [])
        for c in getattr(self, "_classes", []):
            entry = {k: v for k, v in c.items() if k != "patterns"}
            if c["name"] in have:
                [x for x in classes if x.get("name") == c["name"]][0].update(entry)
            else:
                classes.append(dict(classes[0], **entry))
            for pat in c["patterns"]:
                if not any(q.get("pattern") == pat for q in pats):
                    pats.append({"netclass": c["name"], "pattern": pat})
        with open(pro, "w") as f:
            json.dump(d, f, indent=2)

    def export_dsn(self, path):
        return pcbnew.ExportSpecctraDSN(self.board, path)

    def import_ses(self, path):
        return pcbnew.ImportSpecctraSES(self.board, path)

    def autoroute(self, passes=30, jar=None):
        """Slow signals only: the critical nets are routed by hand before this is called."""
        jar = jar or os.environ.get("FREEROUTING_JAR", "/opt/freerouting/freerouting.jar")
        out = os.path.join(self.folder, "out")
        dsn, ses = os.path.join(out, self.name + ".dsn"), os.path.join(out, self.name + ".ses")
        if os.path.exists(ses):
            os.remove(ses)
        if not self.export_dsn(dsn):
            raise RuntimeError("DSN export failed")
        r = subprocess.run(["java", "-Djava.awt.headless=true", "-jar", jar, "-de", dsn, "-do", ses, "-mp", str(passes),
                            "--gui.enabled=false", "-da"], capture_output=True, text=True, timeout=3600)
        if not os.path.exists(ses):
            raise RuntimeError("Freerouting produced no session file:\n" + r.stdout[-2000:] + r.stderr[-2000:])
        if not self.import_ses(ses):
            raise RuntimeError("SES import failed")
        return r.stdout[-600:]

    def unrouted(self):
        self.board.BuildConnectivity()
        return self.board.GetConnectivity().GetUnconnectedCount(True)
