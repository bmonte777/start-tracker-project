"""Fabrication outputs for one board, ready for JLCPCB: Gerbers + drill (zipped), BOM and pick-and-place in JLCPCB's
column layout, a STEP model, renders and the schematic PDF.   usage: python3 fab.py <board-folder> [--bom-only]

Outputs go to hardware/electronics/fab/<name>/ and docs/img/.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run(*cmd):
    r = subprocess.run(list(cmd), capture_output=True, text=True)
    if r.returncode:
        print("  FAILED:", " ".join(cmd[:4]), (r.stderr or r.stdout)[-300:])
    return r


def bom(model):
    """One line per value + footprint + LCSC number. Parts marked do-not-fit or not in the BOM are left out."""
    groups = {}
    for p in model["parts"]:
        if p["dnp"] or not p.get("bom", True):
            continue
        key = (p["value"], p["footprint"].split(":")[-1], p["fields"].get("LCSC", ""), p["fields"].get("MPN", ""))
        groups.setdefault(key, []).append(p["ref"])

    def refkey(r):
        head = r.rstrip("0123456789")
        return head, int(r[len(head):] or 0)
    rows = []
    for (value, fp, lcsc, mpn), refs in groups.items():
        refs.sort(key=refkey)
        rows.append(dict(Comment=value, Designator=",".join(refs), Footprint=fp, **{"LCSC Part #": lcsc}, MPN=mpn, Qty=len(refs)))
    rows.sort(key=lambda r: refkey(r["Designator"].split(",")[0]))
    return rows


def main(folder, bom_only=False):
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    pcb, sch = os.path.join(folder, name + ".kicad_pcb"), os.path.join(folder, name + ".kicad_sch")
    model = json.load(open(os.path.join(folder, name + ".model.json")))
    if bom_only:                # a board whose layout is not released yet: its parts list only, in its own folder
        b = bom(model)
        with open(os.path.join(folder, f"{name}-bom.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #", "MPN", "Qty"])
            w.writeheader()
            w.writerows(b)
        print(f"{name}: {len(b)} BOM lines, {sum(r['Qty'] for r in b)} parts (BOM only; no fabrication files)")
        return
    out = os.path.join(HERE, "..", "fab", name)
    img = os.path.join(HERE, "..", "..", "..", "docs", "img")
    gdir = os.path.join(out, "gerbers")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(gdir)
    os.makedirs(img, exist_ok=True)
    layers = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
    head = open(pcb).read(20000)
    ncu = 6 if '"In4.Cu"' in head else (4 if '"In1.Cu"' in head else 2)
    if ncu >= 4:
        layers = "F.Cu," + ",".join(f"In{i}.Cu" for i in range(1, ncu - 1)) + ",B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
    run("kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "--use-drill-file-origin", "-o", gdir + "/", pcb)
    run("kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "plot", "--excellon-units", "mm",
        "--excellon-separate-th", "--generate-map", "--map-format", "pdf", "-o", gdir + "/", pcb)
    with zipfile.ZipFile(os.path.join(out, f"{name}-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            if not f.endswith(".pdf"):
                z.write(os.path.join(gdir, f), f)
    # pick and place: KiCad's CSV -> JLCPCB columns
    pos = os.path.join(out, "pos.csv")
    run("kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--use-drill-file-origin",
        "--exclude-dnp", "-o", pos, pcb)
    rows = list(csv.DictReader(open(pos)))
    with open(os.path.join(out, f"{name}-cpl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            w.writerow([r["Ref"], f"{float(r['PosX']):.3f}mm", f"{float(r['PosY']):.3f}mm", "Top" if r["Side"] == "top" else "Bottom", f"{float(r['Rot']):.0f}"])
    os.remove(pos)
    b = bom(model)
    with open(os.path.join(out, f"{name}-bom.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #", "MPN", "Qty"])
        w.writeheader()
        w.writerows(b)
    shutil.copy(os.path.join(out, f"{name}-bom.csv"), os.path.join(folder, f"{name}-bom.csv"))
    run("kicad-cli", "pcb", "export", "step", "--subst-models", "--drill-origin", "--no-dnp", "-o", os.path.join(out, f"{name}.step"), pcb)
    run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(out, f"{name}-schematic.pdf"), sch)
    for side, extra in (("top", ["--perspective", "--rotate", "-30,0,0"]), ("bottom", [])):
        run("kicad-cli", "pcb", "render", "--side", side, "--zoom", "0.9", "-w", "1400", "-h", "1000", "--quality", "high", "--background", "opaque",
            *extra, "-o", os.path.join(img, f"04-{name}-{side}.png"), pcb)
    placed = {r["Ref"] for r in rows}
    no_lcsc = [x for x in b if not x["LCSC Part #"]]
    print(f"{name}: {len(b)} BOM lines, {sum(x['Qty'] for x in b)} parts, {len(placed)} in the placement file, "
          f"{len(no_lcsc)} lines without an LCSC number: " + "; ".join(f"{x['Comment']} ({x['Designator']})" for x in no_lcsc))


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), bom_only="--bom-only" in sys.argv)
