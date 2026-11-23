"""Phase 3 parts list: applies the Phase 3 changes to docs/calc/bom_data.py (Phase 2 rev C) and rewrites it,
then rewrites hardware/bom/master-parts-list.csv through bom_data.write_csv().

Price rules added in Phase 3 (EUR without VAT, per piece at 1 / 100 / 1,000 heads):
- Printed on the H2S (1 unit): filament mass x 1.15 (supports, purge, failed prints) x price per kg ex VAT
  (PAHT-CF EUR 46.29/kg from EUR 56.94 incl. VAT, Bambu EU store; ASA EUR 20.32/kg from EUR 24.99 incl. VAT,
  Bambu EU store; TPU and PETG estimated). 100 / 1,000 columns keep the Phase 2 MJF / moulded estimates.
- Machined at JLCCNC (1 unit): estimate by complexity, anodising included, USD -> EUR at 0.91.
- Screws: pack price per piece (M3 x 10 A2 ISO 4762, 200 for GBP 12.72 ex VAT at bolts.co.uk, GBP 1 = EUR 1.15),
  other sizes scaled; inserts from Ruthex packs at 3DJake (M3 100 for USD 8.34, M4 50 for USD 8.80 ex VAT).
"""
from __future__ import annotations
import importlib.util, os, pprint, sys

from . import params as P
from .core import REGISTRY, part_mass
from . import joints as J

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BOM_PY = os.path.join(ROOT, "docs", "calc", "bom_data.py")
CSV = os.path.join(ROOT, "hardware", "bom", "master-parts-list.csv")
USD = 0.91
GBP = 1.15
FIL = {"PAHT-CF": 56.94 / 1.23, "ASA": 24.99 / 1.23, "TPU": 32.0 / 1.23, "PETG": 22.0 / 1.23}   # EUR/kg ex VAT


def _load_phase2():
    # frozen copy of docs/calc/bom_data.py as approved at the end of Phase 2 (rev C); never the file this script writes
    spec = importlib.util.spec_from_file_location("bom_data_p2", os.path.join(os.path.dirname(__file__), "bom_phase2_baseline.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def U(a, b, c):
    return tuple(round(x * USD, 2) for x in (a, b, c))


def E(a, b, c):
    return (round(a, 2), round(b, 2), round(c, 2))


def filament_eur(pid):
    pd = REGISTRY[pid]
    return round(part_mass(pd) * 1.15 * FIL[pd.material], 2)


MJF_USD_PER_G = 0.275      # JLC3DP MJF PA12, as cited in the Phase 2 spec section 8

# JLCCNC one-off estimates in USD, anodising included (Phase 2 kept for 100 / 1,000)
CNC_USD = {"ST-301": 36, "ST-302": 80, "ST-303": 48, "ST-331": 70, "ST-305": 28, "ST-207": 26, "ST-312": 118, "ST-313": 66,
           "ST-208": 12, "ST-215": 11}

def screw_price(std, size, L):
    base = 12.72 / 200 * GBP          # EUR per M3 x 10 A2 ISO 4762
    if std == "thumb":
        return E(1.6 if size == "M5" else 1.0, 0.7 if size == "M5" else 0.5, 0.4 if size == "M5" else 0.3)
    if std == "coin":
        return E(1.5, 0.6, 0.3)
    k = {"M3": 1.0, "M4": 1.6, "M5": 2.4}[size] * (1.0 + max(0, L - 12) / 30.0) * (1.1 if std == "ISO 7380" else 1.0)
    p1 = base * k
    return E(p1, p1 * 0.45, p1 * 0.27)


def _phase4_costs():
    import json
    return json.load(open(os.path.join(ROOT, "hardware", "electronics", "fab", "costs.json")))


def build_parts():
    global P4
    P4 = _phase4_costs()
    p2 = _load_phase2()
    old = {row[0]: list(row) for row in p2.PARTS}
    out = []

    def keep(pid, **ch):
        r = list(old[pid])
        for k, v in ch.items():
            idx = {"name": 1, "qty": 2, "mp": 3, "mq": 4, "mb": 5, "sup": 6, "pr": 7, "src": 8, "note": 9}[k]
            r[idx] = v
        out.append(tuple(r))

    def new(pid, name, qty, mp, mq, mb, sup, pr, src, note):
        out.append((pid, name, qty, mp, mq, mb, sup, pr, src, note))

    def printed(pid, **ch):
        r = old.get(pid)
        pd = REGISTRY[pid]
        mjf = pd.material == "PA12-MJF"
        p1 = round(part_mass(pd) * 1000 * MJF_USD_PER_G * USD, 2) if mjf else filament_eur(pid)
        pr = (p1, r[7][1], r[7][2]) if r else (p1, round(p1 * 2.5, 2), round(p1 * 0.6, 2))
        if mjf:
            ch.setdefault("mp", "MJF PA12 (JLC3DP)")
            ch.setdefault("sup", "JLC3DP (MJF PA12), D29")
            ch.setdefault("note", "W1 + W2 (D35): MJF PA12, 2.0 mm walls")
        args = dict(pr=pr, src="est (JLC3DP MJF, USD 0.275 / g, spec 8)" if mjf else "filament", note="; ".join(x for x in (ch.pop("note", ""), (f"{part_mass(pd) * 1000:.0f} g printed" if part_mass(pd) >= 0.001 else f"{part_mass(pd) * 1000:.1f} g printed")) if x))
        args.update(ch)
        if r:
            keep(pid, **args)
        else:
            new(pid, ch.get("name", pd.name), ch.get("qty", pd.qty), f"{pd.material} printed", ch.get("mq", "moulded"),
                "make", "own printer (H2S)", args["pr"], "filament", args["note"])

    def machined(pid, **ch):
        r = old[pid]
        p1 = round(CNC_USD[pid] * USD, 2)
        keep(pid, pr=(p1, r[7][1], r[7][2]), src="est (JLCCNC class)", **ch)

    # ---- assemblies
    keep("ST-000")
    keep("ST-010", note="ST-202, 204-209, 211-214 + fasteners; motor 48 mm (ST-214)")
    keep("ST-020", note="ST-202, 203-209, 211, 212, 218 + fasteners")
    keep("ST-030", note="ST-201, 203-207, 209, 210, 215-217, 219 + fasteners")
    keep("ST-040", note="ST-301-309 + fasteners")
    keep("ST-050", note="ST-601-612")
    # ---- 2xx
    keep("ST-201")
    keep("ST-202")
    keep("ST-203")
    keep("ST-204", name="GT2 pulley 20T, 9 mm belt, bore 5 mm, 2 x M4 set screws (2 mm key), TIR <= 0.03",
         note="M3 set screws would need a 1.5 mm key (D13)")
    keep("ST-205", note="bolts to the reducer input stub with 4 x M3; pattern to confirm on the Laifual drawing")
    keep("ST-206")
    machined("ST-207", name="Motor plate with belt-tension block", note="same part on all three axes")
    machined("ST-208", name="Encoder reference tube, size 17 (azimuth, altitude)", qty=2, mp="aluminium 6061 turned",
             mq="aluminium 6061 turned", note="6061 instead of 304 (W4, D35): 12 g instead of 34 g")
    keep("ST-209")
    printed("ST-210")
    printed("ST-211")
    printed("ST-212", name="Cartridge rear cover / encoder-board carrier, size 17", qty=2)
    keep("ST-213", name="V-ring VA-75, NBR (azimuth, on ST-303)", qty=1, pr=E(2.50, 1.10, 0.70), src="est",
         note="Simply Bearings VA25 EUR 1.95 single, 0.48 at 100+: scaled for size")
    keep("ST-214")
    out.append(("ST-215", "Encoder reference tube, size 14 (roll)", 1, "aluminium 6061 turned", "aluminium 6061 turned",
                "make", "JLCCNC", (round(CNC_USD["ST-215"] * USD, 2), 2.73, 1.36), "est (JLCCNC class)", ""))
    printed("ST-216", name="Cartridge rear cover / encoder-board carrier, size 14", qty=1, mq="PA66-GF30 moulded")
    printed("ST-217", name="Roll cartridge enclosure", qty=1, mq="PC/ABS moulded", note="IPX4: the roll cartridge sits outside the body")
    new("ST-218", "V-ring VA-80, NBR (altitude, on the arm hub)", 1, "NBR", "NBR", "buy", "SKF / Simply Bearings",
        E(2.60, 1.15, 0.75), "est", "")
    new("ST-219", "V-ring VA-65, NBR (roll, on the shelf)", 1, "NBR", "NBR", "buy", "SKF / Simply Bearings",
        E(2.40, 1.05, 0.65), "est", "")
    # ---- 3xx
    machined("ST-301")
    machined("ST-302")
    machined("ST-303", name="Head base plate (azimuth reducer mount, 3/8in-16 tripod socket)",
             note="D39: stays on the head; the head stands on any tripod without the wedge")
    keep("ST-304", name="Wedge hinge pin, dia 8 h6 x 80, ends tapped M3", note="retained by 2 x M3x6 ISO 7380 + ST-751")
    machined("ST-305", note="fixed to ST-303; clamp knobs on ST-302 press it (D38)")
    keep("ST-306", name="Azimuth fine-adjust thumb screw M5 x 25, stainless", qty=2, pr=E(1.6, 0.7, 0.4), src="est",
         note="push the base boss from both sides")
    keep("ST-307", qty=2, note="one in the base ST-301, one in the head base ST-303 (D39)")
    new("ST-308", "Latitude clamp knob, thumb screw M5 x 16, stainless", 2, "stainless", "stainless", "buy",
        "Misumi / Accu", E(1.4, 0.6, 0.35), "est", "")
    new("ST-331", "Wedge top plate (removable wedge, D39)", 1, "aluminium 6061 CNC", "aluminium 6061 CNC", "make",
        "JLCCNC", (round(CNC_USD["ST-331"] * USD, 2), 16.38, 10.01), "est (JLCCNC class)", "hinge knuckle, arcs, 2 dowels; head held by ST-332")
    new("ST-332", "Wedge screw 3/8in-16 x 10, coin slot, stainless", 1, "stainless", "stainless", "buy",
        "camera hardware supplier", E(1.5, 0.6, 0.3), "est", "holds the head on the wedge top plate (D39)")
    new("ST-333", "Dowel pin 4 m6 x 10, stainless", 2, "stainless", "stainless", "buy", "Misumi / Accu",
        E(0.40, 0.15, 0.08), "est", "anti-rotation, head on the wedge (D39)")
    new("ST-309", "Latitude tangent screw, knurled thumb screw M3 x 25", 1, "stainless", "stainless", "buy",
        "Misumi / Accu", E(1.0, 0.5, 0.3), "est", "fine adjust, D38")
    printed("ST-310")
    printed("ST-311")
    machined("ST-312")
    machined("ST-313")
    keep("ST-314", name="Arca-Swiss clamp, 60 mm, screw knob (Sunwayfoto DDC-60i)", pr=(round(35.0 * USD, 2), 10.92, 7.28),
         src="quoted (eBay USD 35; NZD 64 at photogear)", note="W5 (D35): 70.9 g, 60 x 81 x 13, 3/8in-16 mount (B&H)")
    printed("ST-315")
    printed("ST-316")
    printed("ST-317")
    printed("ST-318")
    printed("ST-319", note="QR label recess")
    printed("ST-320")
    keep("ST-321", note="glued in the recess on the top cover")
    printed("ST-322", qty=2, note="altitude stops at -15 / +100 deg")
    printed("ST-323", name="Gasket, body to tower", qty=1, mq="silicone moulded")
    printed("ST-324", name="Gasket, top cover", qty=1, mq="silicone moulded")
    printed("ST-325", name="Gasket, battery door", qty=1, mq="silicone moulded")
    new("ST-326", "OLED window, clear PC 38 x 22 x 1 mm", 1, "polycarbonate", "polycarbonate", "buy", "laser-cut sheet",
        E(1.5, 0.3, 0.1), "est", "glued with clear silicone")
    printed("ST-327", name="Gasket, bezel", qty=1, mq="silicone moulded")
    printed("ST-328", name="Gasket, roll enclosure", qty=1, mq="silicone moulded")
    new("ST-329", "O-ring 80 x 2, NBR 70 (roll enclosure on the cartridge sleeve)", 1, "NBR", "NBR", "buy", "generic",
        E(0.6, 0.15, 0.08), "est", "")
    new("ST-330", "Clamp screw 3/8in-16 x 12, coin slot, stainless", 1, "stainless", "stainless", "buy",
        "camera hardware supplier", E(1.5, 0.6, 0.3), "est", "D13 exception, D36")
    # ---- 5xx unchanged (Phase 4 details them)
    for pid in [r[0] for r in p2.PARTS if r[0].startswith("ST-5")]:
        # Phase 4: board lines priced from the board BOMs (hardware/electronics/tools/costs.py -> fab/costs.json).
        # Parts with their own line below (large ICs, sockets, switches, LEDs) are not inside the board lines.
        if pid == "ST-501":
            c = P4["st-501"]
            keep(pid, name="Mainboard: 6-layer PCB, assembly, passives, small semiconductors, inductors, connectors",
                 mp="FR-4 6-layer", mq="FR-4 6-layer",
                 pr=U(*[c["per_board"][k] for k in ("1", "100", "1000")]), src="est",
                 note=f"Phase 4 BOM: {c['bom_lines']} lines; six layers with filled and capped vias (D51) and 1 oz inner copper (D61); "
                      "JLCPCB fees estimated; at 1 head the price is the minimum order (5 bare boards, 2 assembled). "
                      "ICs listed separately below")
        elif pid == "ST-512":
            keep(pid, name="GNSS active patch antenna 25 x 25 mm with U.FL lead", note="under the top cover's 1.5 mm window; D54")
        elif pid == "ST-509":
            keep(pid, name="Boost converter TPS61288 (motor rail 16 V / 10 V, D33, D43)", note="LCSC C5219223")
        elif pid == "ST-513":
            keep(pid, name="Real-time clock RV-3028-C7 + MS621FE backup cell", note="D52 (was a 0.1 F capacitor)")
        elif pid == "ST-517":
            keep(pid, name="USB-C receptacle, upright, GT-USB-7051A", note="prototype part, LCSC C2843970, not sealed; Q30 pending")
        elif pid == "ST-518":
            keep(pid, name="Tact switch TS-1187A", note="LCSC C318884; D53")
        elif pid == "ST-519":
            keep(pid, name="Status LEDs: red, green, blue, 0603 (set of 3)", note="D56")
        elif pid == "ST-520":
            c = P4["st-520"]
            keep(pid, name="Cartridge board: 2-layer PCB, assembly, passives, connectors",
                 pr=U(*[c["per_board"][k] for k in ("1", "100", "1000")]), src="est",
                 note=f"Phase 4 BOM: {c['bom_lines']} lines; round 30 mm, MT6835 on the underside (listed separately)")
        elif pid == "ST-530":
            keep(pid, name="Axis harness, JST-GH 15-way (190 / 280 / 680 mm)", note="D47 pinout; roll harness in PTFE wire")
        else:
            keep(pid)
    # ---- 6xx
    keep("ST-601")
    c = P4["st-602"]
    keep("ST-602", name="Battery board: 2-layer PCB, assembly, passives, FETs, sense resistor, LEDs, button",
         pr=U(*[c["per_board"][k] for k in ("1", "100", "1000")]), src="est",
         note=f"Phase 4 BOM: {c['bom_lines']} lines; 32 x 40 x 1.6 at the +Y end of the pack, held in two grooved ribs (D58), "
              "LEDs face the light pipe; at 1 head the price is the minimum order (5 bare boards, 2 assembled). "
              "Gauge, second protector and fuse listed separately below")
    keep("ST-603", note="BQ40Z50RSMR-R2, LCSC C2845123; alt: BQ28Z610 quoted USD 1.55-2.32")
    # second protector: estimate; fuse: DigiKey list price read 23 Nov 2026 (SGD 7.32 / 4.29 / 3.47 at 1 / 100 / 1,000)
    keep("ST-604", name="Second-level protector BQ294700 + three-terminal fuse ITV4030L0815NR (2-cell, 15 A)", sup="TI / Littelfuse",
         pr=U(0.75 + 5.40, 0.55 + 3.17, 0.45 + 2.57), src="est + quoted (fuse)",
         note="BQ294700DSGR, LCSC C414622. The fuse has no LCSC number: bought from DigiKey or Mouser and fitted by hand "
              "(or consigned to JLCPCB)")
    printed("ST-605", name="Pack shell, lower half")
    printed("ST-606", name="Cell holder (end)", qty=2)
    keep("ST-607")
    keep("ST-608")
    keep("ST-609")
    printed("ST-610")
    printed("ST-611")
    printed("ST-612", name="Pack shell, upper half", qty=1, mq="PC/ABS FR moulded")
    # ---- 7xx: old sets kept with qty 0 so IDs are not reused
    for pid in ("ST-701", "ST-702", "ST-703", "ST-704", "ST-705", "ST-706", "ST-707"):
        r = old[pid]
        keep(pid, qty=0, note="replaced in Phase 3 by single lines ST-710 to ST-762")
    keep("ST-708")
    agg = J.screw_summary()
    order = sorted((k for k in agg if k[0] in ("ISO 4762", "ISO 7380")), key=lambda k: (k[1], k[0], k[2]))
    nid = {"ISO 4762": {"M3": 710, "M4": 730}, "ISO 7380": {"M3": 720, "M4": 732, "M5": 740}}
    used = {}
    for (std, size, L) in order:
        base = nid[std][size]
        i = used.get((std, size), 0)
        used[(std, size)] = i + 1
        pid = f"ST-{base + i}"
        joints = "; ".join(sorted(set(agg[(std, size, L)]["joints"])))
        if (std, size, L) in J.ALU7075:
            out.append((pid, f"Screw {std} {size} x {L}, aluminium 7075-T6", agg[(std, size, L)]["qty"], "aluminium 7075-T6",
                        "aluminium 7075-T6", "buy", "Fastener Express / RC hardware", E(0.90, 0.45, 0.25),
                        "est (7075 M3 x 27, 50 pcs USD 36.95, Fastener Express)", joints + "; D35 weight saving"))
            continue
        out.append((pid, f"Screw {std} {size} x {L}, stainless A2", agg[(std, size, L)]["qty"], "stainless A2", "stainless A4",
                    "buy", "Accu / bolts.co.uk / Bossard", screw_price(std, size, L),
                    "quoted (pack)" if (std, size, L) == ("ISO 4762", "M3", 10) else "est (pack)", joints))
    for k, (std, size, qty, use) in enumerate(J.WASHERS):
        pr = E(0.04, 0.015, 0.008) if std == "ISO 7093" else E(0.03, 0.012, 0.006)
        out.append((f"ST-{750 + k}", f"Washer {std} {size}, stainless A2", qty, "stainless A2", "stainless A4", "buy",
                    "Accu / Bossard", pr, "est (pack)", use))
    ins = J.insert_summary()
    ip = {"M3": E(8.34 * USD / 100, 0.04, 0.0), "M4": E(8.80 * USD / 50, 0.07, 0.0), "M5": E(0.25, 0.11, 0.0)}
    for k, size in enumerate(("M3", "M4", "M5")):
        out.append((f"ST-{760 + k}", f"Heat-set insert {size} (Ruthex {size} standard), brass", ins[size], "brass",
                    "not used (tapped aluminium)", "buy", "Ruthex via 3DJake", ip[size],
                    "quoted (pack)" if size != "M5" else "est (pack)", "count from the drawings"))
    # ---- 8xx
    for pid in [r[0] for r in p2.PARTS if r[0].startswith("ST-8")]:
        keep(pid)
    out = [r for r in out if r is not None]
    return out


HEADER = '''"""Star Tracker Project - master parts list (Phase 3, rev A, generated by hardware/cad/stcad/bom.py).

Single source of truth for hardware/bom/master-parts-list.csv and for the cost model in phase2_calcs.py.
Prices are per piece at build quantities of 1, 100 and 1,000 heads, EUR without VAT. 'src' says where a price
comes from:
  quoted        = read from a supplier page (Phase 2: 20 Nov 2026; Phase 3: 21 Nov 2026), see the specs' sources
  quoted (pack) = pack price divided by pack size
  filament      = printed on the H2S: printed mass x 1.15 x filament price per kg (Phase 3 rule)
  est           = engineering estimate, to be replaced by a quote
Phase 3 split every screw set into single lines (ST-710 to ST-762); the old sets keep their IDs with qty 0.
"""
USD_TO_EUR = 0.91  # mid-market, 17-18 Nov 2026


def U(a, b, c):
    """USD prices -> EUR."""
    return tuple(round(x * USD_TO_EUR, 2) for x in (a, b, c))


def E(a, b, c):
    return (a, b, c)


# (id, name, qty, material prototype, material production, make/buy, supplier, (p1, p100, p1000) EUR each, src, note)
PARTS = '''

FOOTER = '''


def write_csv(path):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Name", "Qty per head", "Material (prototype)", "Material (production)", "Make/Buy", "Supplier",
                    "Unit price EUR @1", "Unit price EUR @100", "Unit price EUR @1000",
                    "Line total EUR @1", "Line total EUR @100", "Line total EUR @1000", "Price source", "Note"])
        for (pid, name, qty, mp, mq, mb, sup, pr, src, note) in PARTS:
            w.writerow([pid, name, qty, mp, mq, mb, sup, f"{pr[0]:.2f}", f"{pr[1]:.2f}", f"{pr[2]:.2f}",
                        f"{qty*pr[0]:.2f}", f"{qty*pr[1]:.2f}", f"{qty*pr[2]:.2f}", src, note])


def totals():
    t = [0.0, 0.0, 0.0]
    groups = {}
    for (pid, name, qty, mp, mq, mb, sup, pr, src, note) in PARTS:
        g = pid[3]
        for i in range(3):
            t[i] += qty * pr[i]
            groups.setdefault(g, [0.0, 0.0, 0.0])[i] += qty * pr[i]
    return t, groups


if __name__ == "__main__":
    import sys
    write_csv(sys.argv[1])
    print(totals())
'''


def write():
    parts = build_parts()
    body = "[\n" + "".join("    " + repr(r) + ",\n" for r in parts) + "]"
    open(BOM_PY, "w").write(HEADER + body + FOOTER)
    spec = importlib.util.spec_from_file_location("bom_data_new", BOM_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.write_csv(CSV)
    return parts, m.totals()


if __name__ == "__main__":
    parts, tot = write()
    print(len(parts), tot[0])
