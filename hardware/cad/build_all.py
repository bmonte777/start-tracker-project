"""Rebuild every Phase 3 output from the scripts. Run from hardware/cad:  python build_all.py [--only parts,...]

Outputs: step/ stl/ (CAD), ../drawings/ (A4 PDFs + set), ../../docs/img/03-*.png (renders), ../fab/ (CNC + print +
shopping), ../bom/master-parts-list.csv + ../../docs/calc/bom_data.py, out/checks.json, ../viewer/*.html
"""
import argparse, json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

from build123d import Compound, export_step  # noqa: E402
from stcad import params as P, assembly as A  # noqa: E402
from stcad.core import REGISTRY, part_mass  # noqa: E402

STEPS = ["parts", "assembly", "checks", "renders", "steps", "sheets", "drawings", "bom", "fab", "viewer"]


def do_parts():
    from stcad import fab
    fab.export_parts(HERE)
    for name, f in {"reducer-size17": lambda: __import__("stcad.bought", fromlist=["x"]).reducer(17),
                    "reducer-size14": lambda: __import__("stcad.bought", fromlist=["x"]).reducer(14)}.items():
        pass


def do_assembly():
    its = A.items()
    shapes = []
    for it in its:
        s = A.placed(it, A.HOME)
        s.label = f"{it.pid} {it.name}"
        shapes.append(s)
    for k, v in A.rig_shapes(A.HOME).items():
        v.label = f"Reference rig {k}"
        shapes.append(v)
    os.makedirs(os.path.join(HERE, "step", "assembly"), exist_ok=True)
    export_step(Compound(children=shapes, label="ST-000 Star tracker head P1"), os.path.join(HERE, "step", "assembly", "ST-000-head-P1.step"))
    ex = []
    for it in its:
        s = A.placed(it, A.HOME, explode=1.0)
        s.label = f"{it.pid} {it.name}"
        ex.append(s)
    export_step(Compound(children=ex, label="ST-000 exploded"), os.path.join(HERE, "step", "assembly", "ST-000-head-P1-exploded.step"))
    from stcad import bought as B
    os.makedirs(os.path.join(HERE, "step", "bought"), exist_ok=True)
    for name, s in {"reducer-LHT-17-envelope": B.reducer(17), "reducer-LHT-14-envelope": B.reducer(14),
                    "motor-17HE15-1504S-envelope": B.nema17(38), "motor-17HS19-2004S1-envelope": B.nema17(48),
                    "pulley-GT2-60T": B.pulley60(), "pulley-GT2-20T": B.pulley20(), "belt-2GT-200-9": B.belt(),
                    "arca-clamp-60": B.clamp60(), "mainboard-outline": B.mainboard(), "encoder-board-outline": B.encoder_board(),
                    "battery-board-outline": B.battery_board()}.items():
        export_step(s, os.path.join(HERE, "step", "bought", f"{name}.step"))


def do_renders():
    from stcad import scenes
    scenes.renders(os.path.join(ROOT, "docs", "img"))


def do_steps():
    from stcad import scenes
    scenes.step_images(os.path.join(ROOT, "docs", "img"))


def do_sheets():
    """Picture sheets for the design doc: 3 x 2 renders and 2 x 5 assembly steps."""
    from PIL import Image
    img = os.path.join(ROOT, "docs", "img")

    def grid(names, cols, w, h, out):
        rows = (len(names) + cols - 1) // cols
        sh = Image.new("RGB", (cols * w, rows * h), "white")
        for k, n in enumerate(names):
            f = os.path.join(img, n)
            if os.path.exists(f):
                im = Image.open(f).convert("RGB")
                im.thumbnail((w, h), Image.LANCZOS)
                sh.paste(im, ((k % cols) * w + (w - im.width) // 2, (k // cols) * h + (h - im.height) // 2))
        sh.save(os.path.join(img, out))

    grid(["03-three-quarter.png", "03-exploded.png", "03-no-wedge.png", "03-payload-p5.png",
          "03-swing-85.png", "03-roll-limits.png"], 2, 778, 588, "03-renders-sheet.png")
    grid([f"03-step-{k:02d}.png" for k in range(1, 11)], 2, 658, 494, "03-steps-sheet.png")


def do_drawings():
    from stcad import drawings as D
    from pypdf import PdfWriter
    out = os.path.join(ROOT, "hardware", "drawings")
    os.makedirs(os.path.join(out, "iso"), exist_ok=True)
    made = sorted([pd for pd in REGISTRY.values() if pd.kind in ("printed", "machined", "turned")], key=lambda p: p.pid)
    total = len(made) + 1
    rows = []
    for i, pd in enumerate(made, start=2):
        iso = D.iso_image(pd, os.path.join(out, "iso", f"{pd.pid}.png"))
        fn, s = D.draw_part(pd, out, i, total, iso)
        rows.append((i, pd.pid, pd.name, pd.kind, P.MAT[pd.material]["label"], pd.qty, D.SCALE_TXT.get(s, str(s))))
        print("drawing", pd.pid, flush=True)
    idx = os.path.join(out, "00-index.pdf")
    D.index_sheet(rows, idx)
    w = PdfWriter()
    for f in [idx] + [os.path.join(out, f"{r[1]}.pdf") for r in rows]:
        w.append(f)
    w.write(os.path.join(out, "ST-P1-drawing-set.pdf"))
    json.dump(rows, open(os.path.join(out, "index.json"), "w"), indent=1)


def do_bom():
    from stcad import bom
    parts, tot = bom.write()
    print("parts list lines", len(parts), "materials per head", [round(x, 2) for x in tot[0]])


def do_fab():
    from stcad import fab
    cnc, usd, pls = fab.write_fab(HERE, os.path.join(ROOT, "hardware", "drawings"))
    fab.write_shopping(os.path.join(ROOT, "hardware", "fab"))
    print("CNC one set USD", usd, "plates", len(pls))


def do_checks():
    from stcad import checks
    r = checks.main()
    json.dump(r, open(os.path.join(HERE, "out", "checks.json"), "w"), indent=1)


def do_viewer():
    from stcad import scenes
    data, n = scenes.viewer_data()
    tpl = open(os.path.join(HERE, "viewer_template.html")).read()
    os.makedirs(os.path.join(ROOT, "hardware", "viewer"), exist_ok=True)
    import csv
    rows = {r["ID"]: r for r in csv.DictReader(open(os.path.join(ROOT, "hardware", "bom", "master-parts-list.csv")))}
    parts = {}
    for pid, pd in REGISTRY.items():
        mat = P.MAT[pd.material]["label"] if pd.material in P.MAT else pd.material
        kind = {"printed": "3D printed", "machined": "CNC machined", "turned": "Turned", "bought": "Bought"}.get(pd.kind, pd.kind)
        files = f"step/{pid}.step" + (f", stl/{pid}.stl" if pd.kind == "printed" else "") + ("" if pd.kind == "bought" else f", drawings/{pid}.pdf")
        r = rows.get(pid, {})
        parts[pid] = dict(name=pd.name, kind=kind, material=mat, qty=int(r.get("Qty per head") or pd.qty),
                          mass_g=round(part_mass(pd) * 1000, 1), files=files)
    for pid, r in rows.items():
        if pid not in parts:
            parts[pid] = dict(name=r["Name"], kind="Bought" if r["Make/Buy"] == "buy" else r["Make/Buy"], material=r["Material (prototype)"],
                              qty=int(float(r["Qty per head"] or 0)), mass_g=None, files="-")
    k = dict(hinge_x=P.WEDGE_HINGE_X, hinge_z=P.WEDGE_HINGE_Z, z_alt=P.Z_ALT, x_roll=P.X_ROLL, z_roll=P.Z_ROLL,
             head_drop=P.HEAD_ON_TRIPOD_DZ, ref_rig=P.REF_RIG,
             rigs={rk: dict(name=r["name"], kg=r["kg"]) for rk, r in P.RIGS.items()})
    html = (tpl.replace("__MODEL_DATA__", data).replace("__REV__", P.REV).replace("__DATE__", P.DATE)
            .replace("__PARTS__", json.dumps(parts, separators=(",", ":"))).replace("__PARAMS__", json.dumps(k)))
    open(os.path.join(ROOT, "hardware", "viewer", "star-tracker-viewer.html"), "w").write(html)
    print("viewer bytes", len(html))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=",".join(STEPS))
    a = ap.parse_args()
    for st in a.only.split(","):
        t = time.time()
        globals()[f"do_{st}"]()
        print(f"[{st}] {time.time() - t:.0f} s", flush=True)
