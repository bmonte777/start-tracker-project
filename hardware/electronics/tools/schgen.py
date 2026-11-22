"""Schematic as code for the Star Tracker boards -> ordinary KiCad 9 schematic files.

Style: every pin carries its net name on a short stub (label style), parts are grouped by function with a
note above each group. The same model (parts, pins, nets) is saved as JSON for the layout script, so the
schematic and the board cannot disagree.
"""
import json
import os
import uuid

import symlib
from kisx import Q, dump

NS = uuid.UUID("5ca1ab1e-0000-4000-8000-0000000005d1")
NC = "__NC__"            # explicit no-connect
GRID = 1.27


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


def _rot(dx, dy, r):
    for _ in range((r // 90) % 4):
        dx, dy = dy, -dx
    return dx, dy


def _fx(size=1.27, hide=False, justify=None):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


PKG = {  # passive footprints
    "R0402": "Resistor_SMD:R_0402_1005Metric", "R0603": "Resistor_SMD:R_0603_1608Metric", "R0805": "Resistor_SMD:R_0805_2012Metric",
    "R1206": "Resistor_SMD:R_1206_3216Metric", "R2512": "Resistor_SMD:R_2512_6332Metric",
    "C0402": "Capacitor_SMD:C_0402_1005Metric", "C0603": "Capacitor_SMD:C_0603_1608Metric", "C0805": "Capacitor_SMD:C_0805_2012Metric",
    "C1206": "Capacitor_SMD:C_1206_3216Metric", "C1210": "Capacitor_SMD:C_1210_3225Metric",
}


class Part:
    def __init__(self, ref, lib_id, value, footprint, pins, fields, sheet, x, y, rot, dnp, bom=True):
        self.ref, self.lib_id, self.value, self.footprint = ref, lib_id, value, footprint
        self.pins, self.fields, self.sheet, self.x, self.y, self.rot, self.dnp, self.bom = pins, fields, sheet, x, y, rot, dnp, bom


class Sheet:
    def __init__(self, design, key, title, paper):
        self.d, self.key, self.title, self.paper = design, key, title, paper
        self.parts, self.notes, self.flags = [], [], []
        self._lane = None

    # ---- placement helpers
    def note(self, x, y, text, size=2.0):
        self.notes.append((x, y, text, size))

    def lane(self, x, y, cols=4, dx=45.72, dy=7.62):
        """Start a block of two-pin parts: they fill left to right, top to bottom."""
        self._lane = dict(x=x, y=y, cols=cols, dx=dx, dy=dy, i=0)

    def _next(self):
        ln = self._lane
        c, r = ln["i"] % ln["cols"], ln["i"] // ln["cols"]
        ln["i"] += 1
        return ln["x"] + c * ln["dx"], ln["y"] + r * ln["dy"]

    def part(self, lib_id, ref, value, footprint, pins, x=None, y=None, rot=0, dnp=False, bom=True, **fields):
        if x is None:
            x, y = self._next()
        x, y = round(x / GRID) * GRID, round(y / GRID) * GRID
        _sym, libpins = self.d.sym(lib_id)
        if footprint is None:
            fp = symlib.prop(_sym, "Footprint")
            footprint = str(fp[2]) if fp else ""
        resolved = {}
        byname = {}
        for p in libpins:
            byname.setdefault(p["name"], []).append(p["num"])
        nums = {p["num"] for p in libpins}
        for k, net in pins.items():
            k = str(k)
            if k in nums:
                resolved[k] = net
            elif k in byname:
                for n in byname[k]:
                    resolved.setdefault(n, net)
            else:
                raise KeyError(f"{ref}: no pin '{k}' on {lib_id}")
        missing = sorted(nums - set(resolved))
        if missing:
            names = {p["num"]: p["name"] for p in libpins}
            raise KeyError(f"{ref} ({lib_id}): pins not assigned: " + ", ".join(f"{m}:{names[m]}" for m in missing))
        p = Part(ref, lib_id, value, footprint, resolved, {k.upper() if k in ("lcsc", "mpn") else k: v for k, v in fields.items()},
                 self, x, y, rot, dnp, bom and bool(pins))
        if ref in self.d.refs:
            raise ValueError("duplicate reference " + ref)
        self.d.refs[ref] = p
        self.parts.append(p)
        return p

    def two(self, lib_id, ref, value, a, b, footprint, **kw):
        return self.part(lib_id, ref, value, footprint, {"1": a, "2": b}, rot=90, **kw)

    def R(self, ref, value, a, b, pkg="R0402", **kw):
        return self.two("Device:R", ref, value, a, b, PKG.get(pkg, pkg), **kw)

    def C(self, ref, value, a, b, pkg="C0402", **kw):
        return self.two("Device:C", ref, value, a, b, PKG.get(pkg, pkg), **kw)

    def L(self, ref, value, a, b, footprint, **kw):
        return self.two("Device:L", ref, value, a, b, footprint, **kw)

    def flag(self, net, x=None, y=None):
        if x is None:
            x, y = self._next()
        self.flags.append((round(x / GRID) * GRID, round(y / GRID) * GRID, net))

    def tp(self, ref, net, footprint="TestPoint:TestPoint_Pad_D1.0mm", **kw):
        return self.part("Connector:TestPoint", ref, net, footprint, {"1": net}, rot=90, bom=False, **kw)


class Design:
    def __init__(self, name, title, rev="A", date="2026-11-22", sym_dirs=()):
        self.name, self.title, self.rev, self.date = name, title, rev, date
        self.sym_dirs = list(sym_dirs)
        self.sheets, self.refs, self._syms = [], {}, {}
        self.root_uuid = uid(name, "root")

    def sym(self, lib_id):
        if lib_id not in self._syms:
            self._syms[lib_id] = symlib.load(lib_id, self.sym_dirs)
        return self._syms[lib_id]

    def sheet(self, key, title, paper="A3"):
        s = Sheet(self, key, title, paper)
        self.sheets.append(s)
        return s

    # ---- model
    def nets(self):
        nets = {}
        for p in self.refs.values():
            for num, net in p.pins.items():
                if net != NC:
                    nets.setdefault(net, []).append((p.ref, num))
        return nets

    def check(self):
        """Every net needs at least two pins (a single-pin net is almost always a typing error)."""
        problems = [f"net {n} has a single pin {v[0][0]}.{v[0][1]}" for n, v in sorted(self.nets().items()) if len(v) < 2]
        return problems

    def save_model(self, path):
        m = dict(name=self.name, title=self.title, rev=self.rev, parts=[
            dict(ref=p.ref, value=p.value, footprint=p.footprint, lib_id=p.lib_id, dnp=p.dnp, bom=p.bom, fields=p.fields, sheet=p.sheet.key,
                 pins={k: (None if v == NC else v) for k, v in p.pins.items()}) for p in self.refs.values()])
        with open(path, "w") as f:
            json.dump(m, f, indent=1)

    # ---- KiCad output
    def _sheet_path(self, sh):
        if len(self.sheets) == 1:
            return "/" + self.root_uuid
        return "/" + self.root_uuid + "/" + uid(self.name, "sheetsym", sh.key)

    def _symbol(self, p, path):
        sym, libpins = self.sym(p.lib_id)
        out = ["symbol", ["lib_id", Q(p.lib_id)], ["at", p.x, p.y, p.rot], ["unit", 1], ["exclude_from_sim", "no"], ["in_bom", "yes" if p.bom else "no"],
               ["on_board", "yes"], ["dnp", "yes" if p.dnp else "no"], ["uuid", Q(uid(self.name, p.ref))]]
        two_pin = p.rot == 90 and len(libpins) <= 2

        def fpos(key, default):
            if two_pin:
                return {"Reference": (p.x, p.y - 2.2, 90), "Value": (p.x, p.y + 2.2, 90)}.get(key, (p.x, p.y, 90))
            lp = symlib.prop(sym, key)
            if lp is None:
                return (p.x, p.y, 0)
            at = lp[3]
            return (p.x + float(at[1]), p.y - float(at[2]), int(float(at[3])) if len(at) > 3 else 0)

        def padd(key, val, hide, size=1.27):
            x, y, a = fpos(key, None)
            just = None
            if not two_pin:
                lp = symlib.prop(sym, key)
                if lp is not None:
                    eff = [z for z in lp if isinstance(z, list) and z[0] == "effects"]
                    if eff:
                        j = [z for z in eff[0] if isinstance(z, list) and z[0] == "justify"]
                        if j:
                            just = " ".join(j[0][1:])
            out.append(["property", Q(key), Q(val), ["at", x, y, a], _fx(size, hide, just)])

        padd("Reference", p.ref, False, 1.0 if two_pin else 1.27)
        padd("Value", p.value, False, 1.0 if two_pin else 1.27)
        padd("Footprint", p.footprint, True)
        ds = symlib.prop(sym, "Datasheet")
        padd("Datasheet", p.fields.get("Datasheet", str(ds[2]) if ds else "~"), True)
        de = symlib.prop(sym, "Description")
        padd("Description", p.fields.get("Description", str(de[2]) if de else ""), True)
        for k, v in p.fields.items():
            if k not in ("Datasheet", "Description"):
                out.append(["property", Q(k), Q(str(v)), ["at", p.x, p.y, 0], _fx(1.27, True)])
        for lp in libpins:
            out.append(["pin", Q(lp["num"]), ["uuid", Q(uid(self.name, p.ref, "pin", lp["num"], lp["x"], lp["y"]))]])
        out.append(["instances", ["project", Q(self.name), ["path", Q(path), ["reference", Q(p.ref)], ["unit", 1]]]])
        return out

    def _pin_items(self, p):
        """Stub wire + global label (or no-connect flag) for every pin."""
        _sym, libpins = self.sym(p.lib_id)
        items = []
        stub = 1.27 if len(libpins) <= 2 else 2.54
        seen = set()
        for lp in libpins:
            ox, oy = {0: (-1, 0), 90: (0, -1), 180: (1, 0), 270: (0, 1)}[lp["ang"]]
            ex, ey = _rot(lp["x"], -lp["y"], p.rot)
            dx, dy = _rot(ox, -oy, p.rot)
            x, y = round(p.x + ex, 4), round(p.y + ey, 4)
            if (x, y) in seen:          # stacked pins share one stub
                continue
            seen.add((x, y))
            net = p.pins[lp["num"]]
            if net == NC:
                items.append(["no_connect", ["at", x, y], ["uuid", Q(uid(self.name, p.ref, "nc", lp["num"]))]])
                continue
            x2, y2 = round(x + dx * stub, 4), round(y + dy * stub, 4)
            items.append(["wire", ["pts", ["xy", x, y], ["xy", x2, y2]], ["stroke", ["width", 0], ["type", "default"]],
                          ["uuid", Q(uid(self.name, p.ref, "w", lp["num"]))]])
            items.append(self._label(net, x2, y2, dx, dy, (p.ref, lp["num"])))
        return items

    def _label(self, net, x, y, dx, dy, key):
        ang, just = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, -1): (90, "left"), (0, 1): (270, "right")}[(dx, dy)]
        return ["global_label", Q(net), ["shape", "passive"], ["at", x, y, ang], ["effects", ["font", ["size", 1.0, 1.0]], ["justify", just]],
                ["uuid", Q(uid(self.name, "lbl", *key))],
                ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, 0], _fx(1.27, True)]]

    def _flag(self, sh, i, x, y, net, path):
        sym, _ = self.sym("power:PWR_FLAG")
        ref = f"#FLG{len(self._flagrefs) + 1:02d}"
        self._flagrefs.append(ref)
        s = ["symbol", ["lib_id", Q("power:PWR_FLAG")], ["at", x, y, 0], ["unit", 1], ["exclude_from_sim", "no"], ["in_bom", "yes"],
             ["on_board", "yes"], ["dnp", "no"], ["uuid", Q(uid(self.name, "flag", sh.key, i))],
             ["property", Q("Reference"), Q(ref), ["at", x, y - 1.9, 0], _fx(1.27, True)],
             ["property", Q("Value"), Q("PWR_FLAG"), ["at", x, y - 3.8, 0], _fx(1.0)],
             ["property", Q("Footprint"), Q(""), ["at", x, y, 0], _fx(1.27, True)],
             ["property", Q("Datasheet"), Q("~"), ["at", x, y, 0], _fx(1.27, True)],
             ["property", Q("Description"), Q("Special symbol for telling ERC where power comes from"), ["at", x, y, 0], _fx(1.27, True)],
             ["pin", Q("1"), ["uuid", Q(uid(self.name, "flagpin", sh.key, i))]],
             ["instances", ["project", Q(self.name), ["path", Q(path), ["reference", Q(ref)], ["unit", 1]]]]]
        w = ["wire", ["pts", ["xy", x, y], ["xy", x, y + 2.54]], ["stroke", ["width", 0], ["type", "default"]],
             ["uuid", Q(uid(self.name, "flagw", sh.key, i))]]
        return [s, w, self._label(net, x, y + 2.54, 0, 1, ("flag", sh.key, i))]

    def _title(self, sh, page, total):
        return ["title_block", ["title", Q(f"{self.title}: {sh.title}" if sh else self.title)], ["date", Q(self.date)], ["rev", Q(self.rev)],
                ["company", Q("Star Tracker Project")], ["comment", 1, Q("Generated by hardware/electronics/tools/schgen.py from design.py")],
                ["comment", 2, Q("Label style: every pin carries its net name; nets join by name across sheets")]]

    def _sheet_file(self, sh, page, total, is_root):
        path = self._sheet_path(sh)
        used = []
        for p in sh.parts:
            if p.lib_id not in used:
                used.append(p.lib_id)
        if sh.flags:
            used.append("power:PWR_FLAG")
        root = ["kicad_sch", ["version", 20250114], ["generator", Q("st_schgen")], ["generator_version", Q("9.0")],
                ["uuid", Q(self.root_uuid if is_root else uid(self.name, "sheetfile", sh.key))], ["paper", Q(sh.paper)],
                self._title(sh, page, total), ["lib_symbols"] + [self.sym(l)[0] for l in used]]
        for i, (x, y, text, size) in enumerate(sh.notes):
            root.append(["text", Q(text), ["exclude_from_sim", "no"], ["at", x, y, 0], ["effects", ["font", ["size", size, size]], ["justify", "left", "bottom"]],
                         ["uuid", Q(uid(self.name, "note", sh.key, i))]])
        for p in sh.parts:
            root += self._pin_items(p)
        for i, (x, y, net) in enumerate(sh.flags):
            root += self._flag(sh, i, x, y, net, path)
        for p in sh.parts:
            root.append(self._symbol(p, path))
        if is_root:
            root.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
        root.append(["embedded_fonts", "no"])
        return dump(root) + "\n"

    def write(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        self._flagrefs = []
        if len(self.sheets) == 1:
            with open(os.path.join(outdir, self.name + ".kicad_sch"), "w") as f:
                f.write(self._sheet_file(self.sheets[0], 1, 1, True))
        else:
            root = ["kicad_sch", ["version", 20250114], ["generator", Q("st_schgen")], ["generator_version", Q("9.0")],
                    ["uuid", Q(self.root_uuid)], ["paper", Q("A4")], self._title(None, 1, len(self.sheets) + 1), ["lib_symbols"]]
            root.append(["text", Q(self.title + "\nSheets:"), ["exclude_from_sim", "no"], ["at", 20, 24, 0],
                         ["effects", ["font", ["size", 3, 3]], ["justify", "left", "bottom"]], ["uuid", Q(uid(self.name, "roottext"))]])
            for i, sh in enumerate(self.sheets):
                x, y, w, h = 20 + (i % 3) * 85, 40 + (i // 3) * 40, 70, 22
                fn = f"{self.name}-{sh.key}.kicad_sch"
                root.append(["sheet", ["at", x, y], ["size", w, h], ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                             ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                             ["uuid", Q(uid(self.name, "sheetsym", sh.key))],
                             ["property", Q("Sheetname"), Q(sh.title), ["at", x, y - 0.7, 0], _fx(1.5, False, "left bottom")],
                             ["property", Q("Sheetfile"), Q(fn), ["at", x, y + h + 0.6, 0], _fx(1.27, False, "left top")],
                             ["instances", ["project", Q(self.name), ["path", Q("/" + self.root_uuid), ["page", Q(str(i + 2))]]]]])
                with open(os.path.join(outdir, fn), "w") as f:
                    f.write(self._sheet_file(sh, i + 2, len(self.sheets) + 1, False))
            root.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
            root.append(["embedded_fonts", "no"])
            with open(os.path.join(outdir, self.name + ".kicad_sch"), "w") as f:
                f.write(dump(root) + "\n")
        self.save_model(os.path.join(outdir, self.name + ".model.json"))


# ---------------------------------------------------------------------------------------------------
# Project symbol library (parts KiCad does not ship): simple box symbols from pin lists
# ---------------------------------------------------------------------------------------------------
def box_symbol(name, left, right, footprint, datasheet, descr, ref="U", top=(), bottom=()):
    """left/right/top/bottom: lists of (number, name, type); None leaves a gap."""
    rows = max(len(left), len(right), 1)
    wl = max([len(p[1]) for p in left if p] + [1])
    wr = max([len(p[1]) for p in right if p] + [1])
    cols = max(len(top), len(bottom))
    w = max(10.16, round(((wl + wr) * 1.1 + 5) / 2.54 + 0.5) * 2.54, (cols + 1) * 2.54)
    h = (rows + 1) * 2.54
    x0, y0 = -w / 2, h / 2
    x0 = round(x0 / 1.27) * 1.27
    pins = []

    def pin(p, x, y, ang):
        num, nm, typ = p
        pins.append(["pin", typ, "line", ["at", x, y, ang], ["length", 2.54], ["name", Q(nm), _fx(1.0)], ["number", Q(str(num)), _fx(1.0)]])

    for i, p in enumerate(left):
        if p:
            pin(p, x0 - 2.54, y0 - (i + 1) * 2.54, 0)
    for i, p in enumerate(right):
        if p:
            pin(p, x0 + w + 2.54, y0 - (i + 1) * 2.54, 180)
    for i, p in enumerate(top):
        if p:
            pin(p, x0 + (i + 1) * 2.54, y0 + 2.54, 270)
    for i, p in enumerate(bottom):
        if p:
            pin(p, x0 + (i + 1) * 2.54, y0 - h - 2.54, 90)
    return ["symbol", Q(name), ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
            ["property", Q("Reference"), Q(ref), ["at", x0, y0 + 1.5, 0], _fx(1.27, False, "left bottom")],
            ["property", Q("Value"), Q(name), ["at", x0 + w, y0 + 1.5, 0], _fx(1.27, False, "right bottom")],
            ["property", Q("Footprint"), Q(footprint), ["at", 0, 0, 0], _fx(1.27, True)],
            ["property", Q("Datasheet"), Q(datasheet), ["at", 0, 0, 0], _fx(1.27, True)],
            ["property", Q("Description"), Q(descr), ["at", 0, 0, 0], _fx(1.27, True)],
            ["symbol", Q(name + "_0_1"), ["rectangle", ["start", x0, y0], ["end", x0 + w, y0 - h], ["stroke", ["width", 0.254], ["type", "default"]],
                                            ["fill", ["type", "background"]]]],
            ["symbol", Q(name + "_1_1")] + pins, ["embedded_fonts", "no"]]


def write_symbol_lib(path, symbols):
    root = ["kicad_symbol_lib", ["version", 20241209], ["generator", Q("st_schgen")], ["generator_version", Q("9.0")]] + symbols
    with open(path, "w") as f:
        f.write(dump(root) + "\n")
