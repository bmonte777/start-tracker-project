"""Fabrication package: STL plates for the H2S, print time and filament per set, CNC list with quote estimate,
shopping list of bought parts."""
from __future__ import annotations
import csv, math, os
from build123d import Pos, Rot, export_stl, export_step

from . import params as P
from .core import REGISTRY, part_mass, printed_mass

RATE_G_PER_H = {"PAHT-CF": 12.0, "ASA": 22.0, "TPU": 8.0, "PETG": 18.0}     # with the walls of spec 8.2
PLATE_OVERHEAD_H = 0.25
GAP = 8.0


def oriented(pd):
    s = pd.get()
    rx, ry, rz = pd.print_rot
    s = Rot(rx, ry, rz) * s
    bb = s.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * s


def plates():
    """Shelf-pack every printed part (x qty) onto 340 x 320 plates, one material per plate."""
    items = []
    for pd in REGISTRY.values():
        if pd.kind != "printed":
            continue
        s = oriented(pd)
        bb = s.bounding_box()
        for k in range(pd.qty):
            w, d = bb.size.X, bb.size.Y
            if d > w:
                w, d = d, w
            items.append(dict(pid=pd.pid, mat=pd.material, w=w, d=d, h=bb.size.Z, g=part_mass(pd) * 1000))
    plates = []
    for mat in ("PAHT-CF", "ASA", "TPU", "PETG"):
        its = sorted([i for i in items if i["mat"] == mat], key=lambda i: -i["d"])
        cur = None
        for it in its:
            placed = False
            for pl in [p for p in plates if p["mat"] == mat]:
                x, y, row_d = pl["cursor"]
                if x + it["w"] <= P.PLATE_XY[0] - 10:
                    pl["parts"].append(it["pid"])
                    pl["cursor"] = (x + it["w"] + GAP, y, max(row_d, it["d"]))
                    placed = True
                elif y + row_d + GAP + it["d"] <= P.PLATE_XY[1] - 10:
                    y = y + row_d + GAP
                    pl["parts"].append(it["pid"])
                    pl["cursor"] = (10 + it["w"] + GAP, y, it["d"])
                    placed = True
                if placed:
                    pl["g"] += it["g"]
                    pl["hmax"] = max(pl["hmax"], it["h"])
                    break
            if not placed:
                plates.append(dict(mat=mat, parts=[it["pid"]], cursor=(10 + it["w"] + GAP, 10, it["d"]), g=it["g"],
                                   hmax=it["h"]))
    for i, pl in enumerate(plates):
        pl["n"] = i + 1
        pl["filament_g"] = round(pl["g"] * 1.15, 0)
        pl["hours"] = round(pl["g"] / RATE_G_PER_H[pl["mat"]] + PLATE_OVERHEAD_H, 1)
    return plates


def export_parts(root):
    step_dir = os.path.join(root, "step")
    stl_dir = os.path.join(root, "stl")
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    rows = []
    for pd in REGISTRY.values():
        s = pd.get()
        export_step(s, os.path.join(step_dir, f"{pd.pid}.step"))
        if pd.kind == "printed":
            export_stl(oriented(pd), os.path.join(stl_dir, f"{pd.pid}.stl"), tolerance=0.02, angular_tolerance=0.15)
        rows.append(pd.pid)
    return rows


def write_fab(root, drawings_dir):
    fab = os.path.join(root, "..", "fab")
    os.makedirs(os.path.join(fab, "cnc"), exist_ok=True)
    # CNC package: STEP + PDF per part, quote estimate
    from .bom import CNC_USD, USD
    import shutil
    cnc_rows = []
    for pd in REGISTRY.values():
        if pd.kind not in ("machined", "turned"):
            continue
        shutil.copy(os.path.join(root, "step", f"{pd.pid}.step"), os.path.join(fab, "cnc", f"{pd.pid}.step"))
        pdf = os.path.join(drawings_dir, f"{pd.pid}.pdf")
        if os.path.exists(pdf):
            shutil.copy(pdf, os.path.join(fab, "cnc", f"{pd.pid}.pdf"))
        bb = pd.get().bounding_box()
        usd = CNC_USD.get(pd.pid, 30)
        cnc_rows.append([pd.pid, pd.name, pd.qty, P.MAT[pd.material]["label"], pd.finish, pd.tol,
                         f"{bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f}", f"{part_mass(pd) * 1000:.0f}",
                         usd, round(usd * pd.qty, 0), round(usd * pd.qty * USD, 0)])
    tot_usd = sum(r[9] for r in cnc_rows)
    with open(os.path.join(fab, "cnc", "cnc-quote-estimate.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Part", "Name", "Qty per head", "Material", "Finish", "Tolerance", "Size mm", "Mass g",
                    "Est. USD each", "Est. USD line", "Est. EUR line"])
        w.writerows(cnc_rows)
        w.writerow(["", "TOTAL one set", sum(r[2] for r in cnc_rows), "", "", "", "", "", "", tot_usd, round(tot_usd * USD, 0)])
    # print plates
    pls = plates()
    with open(os.path.join(fab, "print-plates.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Plate", "Material", "Parts on the plate (H2S 340 x 320)", "Tallest part mm", "Filament g", "Print time h"])
        for pl in pls:
            w.writerow([pl["n"], pl["mat"], " ".join(pl["parts"]), round(pl["hmax"], 0), pl["filament_g"], pl["hours"]])
        w.writerow(["", "TOTAL", f"{len(pls)} plates", "", sum(p["filament_g"] for p in pls), round(sum(p["hours"] for p in pls), 1)])
    # MJF parts ordered from JLC3DP (D29, D35)
    from .bom import MJF_USD_PER_G
    mjf_rows = []
    for pd in REGISTRY.values():
        if pd.kind == "printed" and pd.material == "PA12-MJF":
            g = part_mass(pd) * 1000
            shutil.copy(os.path.join(root, "step", f"{pd.pid}.step"), os.path.join(fab, "cnc", f"{pd.pid}-MJF.step"))
            mjf_rows.append([pd.pid, pd.name, pd.qty, round(g, 0), round(g * MJF_USD_PER_G, 0), round(g * MJF_USD_PER_G * USD, 0)])
    with open(os.path.join(fab, "mjf-order-estimate.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Part", "Name", "Qty per head", "Mass g", "Est. USD (0.275 / g)", "Est. EUR"])
        w.writerows(mjf_rows)
        w.writerow(["", "TOTAL", "", sum(r[3] for r in mjf_rows), sum(r[4] for r in mjf_rows), sum(r[5] for r in mjf_rows)])
    return cnc_rows, tot_usd, pls


SHOP = [  # (ID, what to buy, qty per head, buy from, link)
    ("ST-202", "Laifual LHT-17-100-U-III hollow harmonic unit", 2, "Laifual (quote) / Alibaba listing", "https://www.alibaba.com/product-detail/Laifual-LHT-series-harmonic-drive-gearbox_1600058558735.html"),
    ("ST-201", "Laifual LHT-14-100-U-III hollow harmonic unit", 1, "Laifual (quote) / Alibaba listing", "https://www.alibaba.com/product-detail/Laifual-LHT-series-harmonic-drive-gearbox_1600058558735.html"),
    ("ST-203", "StepperOnline 17HE15-1504S (38 mm)", 2, "StepperOnline", "https://www.omc-stepperonline.com/e-series-nema-17-bipolar-42ncm-59-49oz-in-1-5a-42x42x38mm-4-wires-w-1m-cable-connector-17he15-1504s"),
    ("ST-214", "StepperOnline 17HS19-2004S1 (48 mm)", 1, "StepperOnline", "https://omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-and-connector.html"),
    ("ST-204", "GT2 pulley 20T, 9 mm, bore 5, M4 set screws (link is the seller's 6.35 bore page: pick the 5 mm bore)", 3, "123-3D / Misumi", "https://www.123-3d.co.uk/123-3D-GT2-timing-belt-pulley-20-teeth-9mm-belt-bore-6-35m-GT2-20T-W9-B6-35-i4690.html"),
    ("ST-205", "GT2 pulley 60T, 9 mm, re-bored to the reducer stub (20 / 25 mm)", 3, "RS (Optibelt 60T bore up to 20) / JLCMC", "https://uk.rs-online.com/web/p/belt-pulleys/2365741"),
    ("ST-206", "2GT closed belt 200 mm, 9 mm wide", 3, "Gates via Motion / generic", "https://www.motion.com/products/sku/05694825"),
    ("ST-209", "Magnet 6 x 2.5 mm diametric N35SH", 3, "LCSC / magnet supplier", ""),
    ("ST-213 / 218 / 219", "V-rings VA-75, VA-80, VA-65 (NBR)", 3, "Simply Bearings / RS (SKF)", "https://simplybearings.co.uk/shop/p83314/VA25-NITRILE-Rubber-V-Ring-For-Shafts-24-27mm/product_info.html"),
    ("ST-304", "Hinge pin 8 h6 x 80, ends tapped M3", 1, "Misumi (shaft, one end / both ends tapped)", ""),
    ("ST-306 / 308 / 309", "Thumb screws M5 x 25 (2), M5 x 16 (2), M3 x 25 knurled (1), stainless", 5, "Accu", "https://accu-components.com/"),
    ("ST-307", "3/8in-16 stainless thread bushing, OD 12 x 8 (base and head base)", 2, "camera hardware supplier", ""),
    ("ST-332", "3/8in-16 x 10 coin-slot camera screw (head onto the wedge)", 1, "camera hardware supplier", ""),
    ("ST-333", "Dowel pin 4 m6 x 10, stainless", 2, "Accu", "https://accu-components.com/"),
    ("ST-314", "Arca clamp 60 mm, screw knob (Sunwayfoto DDC-60i, 71 g)", 1, "B&H / local dealer", "https://www.bhphotovideo.com/c/product/906573-REG/Sunwayfoto_DDC_60i_Screw_Knob_Clamp.html"),
    ("ST-310 / 311", "Azimuth body and tower, MJF PA12 dyed black: upload the two STEP files", 1, "JLC3DP", "https://jlc3dp.com/"),
    ("ST-326", "Clear PC sheet 1 mm, cut 38 x 22", 1, "any plastics shop", ""),
    ("ST-329", "O-ring 80 x 2 NBR 70", 1, "generic", ""),
    ("ST-330", "3/8in-16 x 12 coin-slot camera screw", 1, "camera hardware supplier", ""),
    ("ST-601", "Molicel INR-21700-P50B", 4, "NKON (EU)", "https://www.nkon.nl/novat/rechargeable/molicel-inr21700-p50b-5000mah-50a.html"),
    ("ST-717 / 718", "Aluminium 7075-T6 screws ISO 4762 M3 x 45 (8) and M3 x 50 (24), for the reducers", 32, "Fastener Express / RC hardware", "https://www.fastener-express.com/M3x.5x27mmSocketHeadCapScrews-BlackAluminumQty.aspx"),
    ("ST-710..741", "Stainless A2 screws, ISO 4762 / ISO 7380, 17 sizes (see parts list, 162 pcs)", 162, "Accu / bolts.co.uk", "https://bolts.co.uk/m3-x-10mm-socket-cap-screw-din-912-a2-stainless-steel-pack-of-200-p-SCMCA203010"),
    ("ST-750..752", "Washers M3 / M3 large / M5, stainless", 16, "Accu", "https://accu-components.com/"),
    ("ST-760", "Ruthex heat-set inserts M3 (pack of 100)", 75, "3DJake", "https://www.3djake.com/ruthex/threaded-insert-m3-100-pieces"),
    ("ST-761", "Ruthex heat-set inserts M4 (pack of 50)", 12, "3DJake (Ruthex range)", "https://www.3djake.com/ruthex"),
    ("ST-762", "Ruthex heat-set inserts M5", 6, "3DJake", ""),
    ("Filament", "Bambu PAHT-CF 1 kg (the three cartridge housings use about 380 g)", 1, "Bambu EU store", "https://eu.store.bambulab.com/en-fi/products/paht-cf"),
    ("Filament", "Bambu ASA 1 kg", 1, "Bambu EU store", "https://eu.store.bambulab.com/en-lu/products/asa-filament"),
    ("Filament", "TPU 95A 0.5 kg, PETG clear (small spool)", 1, "Bambu EU store", ""),
    ("ST-5xx", "Electronics: see Phase 4 (boards, ICs, connectors, harness)", 1, "JLCPCB / LCSC", ""),
]


def write_shopping(fab):
    with open(os.path.join(fab, "shopping-list.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Part", "What to buy", "Qty per head", "Buy from", "Link"])
        w.writerows(SHOP)
    return SHOP
