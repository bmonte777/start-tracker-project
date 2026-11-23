"""Assemble docs/04-electronics.md from doc/04-electronics.tmpl.md and the generated data.

Run after docgen.py, costs.py and the fit check:  python3 tools/compose_doc.py
The hand-written state of the phase (what is finished, what is not) is in doc/status.json.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from costs import BOARDS, pcb_price  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ROOT, "..", ".."))
USD = 0.91


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main():
    tmpl = open(os.path.join(ROOT, "doc", "04-electronics.tmpl.md")).read()
    T = json.load(open(os.path.join(ROOT, "doc", "tables.json")))
    S = json.load(open(os.path.join(ROOT, "doc", "status.json")))
    C = json.load(open(os.path.join(ROOT, "fab", "costs.json")))
    fit = json.load(open(os.path.join(REPO, "hardware", "cad", "out", "fit_boards.json")))
    cm = json.load(open(os.path.join(REPO, "docs", "calc", "phase4_cost_model.json")))["cost"]

    rows = []
    gaps = []
    for r in fit if isinstance(fit, list) else fit.get("results", []):
        if r.get("missing"):
            rows.append((r["board"], "—", "not exported yet", "—"))
            continue
        near = "; ".join(f"{n['part']} {n['distance']} mm" for n in r.get("nearest", [])[:3])
        ov = "; ".join(f"{o['part']} ({o['overlap_mm3']} mm³)" for o in r.get("overlaps", [])) or "none"
        rows.append((f"{r['board']} {r['instance']}", ov, near, r.get("magnet_gap", "—")))
        if "magnet_gap" in r:
            gaps.append(r["magnet_gap"])
    fit_md = table(["Board", "Overlaps", "Nearest parts", "Chip-to-magnet gap, mm"], rows) + "\n\n" + S["fit_note"]

    nol = []
    for name in ("st-520", "st-501"):
        for value, mpn in T[name + "_stats"]["no_lcsc"]:
            nol.append((name.upper(), value, mpn, S["no_stock_how"].get(mpn, S["no_stock_how"].get(value, "pick in JLCPCB's parts matcher at upload"))))
    nol = [("ST-520", "MT6835GT-STD", "MT6835GT-STD (C2984637)", "in the library, 0 in stock on the check date: pre-order through JLCPCB Parts Manager"),
           ("ST-501", "TMC2209-LA-T", "TMC2209-LA-T (C465949)", "21 in stock, 15 needed for five sets: buy into your JLCPCB parts account before ordering")] + nol + [
           ("ST-602", "ITV4030L0815NR", "Littelfuse three-terminal fuse, 2-cell, 15 A", "not at LCSC: buy from DigiKey or Mouser, consign it to JLCPCB or fit it by hand with hot air")]
    no_stock = table(["Board", "Value", "Part", "How to get it on the board"], nol)

    def eur(x):
        return f"{x * USD:,.2f}"
    q = []
    tot = 0.0
    for name, label, n in (("st-501", "Mainboard ST-501", 5), ("st-520", "Cartridge board ST-520", 15), ("st-602", "Battery board ST-602", 5)):
        c = C[name]
        spec = BOARDS[name]
        fixed = 50 + (16 if spec["sides"] == 2 else 8) + 3 * c["part_types"]
        pcb = n * pcb_price(spec["layers"], spec["area_cm2"], n)
        parts = n * (c["parts_usd"][0] + c["joints"] * 0.0017)
        line = fixed + pcb + parts
        tot += line
        q.append((label, n, f"{fixed:.0f}", f"{pcb:.0f}", f"{parts:.0f}", f"{line:.0f}", eur(line)))
    q.append(("**Boards and small parts, 5 sets**", "", "", "", "", f"**{tot:.0f}**", f"**{eur(tot)}**"))
    quote = (table(["Order line", "Boards", "Setup, stencils, part-type fees (USD)", "Bare boards (USD)", "Small parts + soldering (USD)",
                    "Total (USD)", "Total (EUR)"], q)
             + "\n\n" + S["quote_note"])

    bom = (f"The master parts list keeps its 131 lines. The three board lines are priced from the board BOMs "
           f"(`hardware/electronics/tools/costs.py`), and the lines for the clock, sockets, switches, LEDs, antenna and harness carry the Phase 4 part choices. "
           f"Large ICs keep their own lines and are left out of the board lines, so nothing is counted twice.\n\n"
           + table(["", "1 head", "100 heads", "1,000 heads"],
                   [("ST-501 board line, EUR each", *[f"{C['st-501']['per_board'][k] * USD:.2f}" for k in ("1", "100", "1000")]),
                    ("ST-520 board line, EUR each (3 per head)", *[f"{C['st-520']['per_board'][k] * USD:.2f}" for k in ("1", "100", "1000")]),
                    ("ST-602 board line, EUR each", *[f"{C['st-602']['per_board'][k] * USD:.2f}" for k in ("1", "100", "1000")]),
                    ("Electronics group (ST-5xx), EUR per head", *[f"{v:,.0f}" for v in cm["groups"]["5"]]),
                    ("Materials, EUR per head", *[f"{v:,.0f}" for v in cm["materials"]]),
                    ("Cost of goods, EUR per head", *[f"{v:,.0f}" for v in cm["cogs"]])])
           + f"\n\nLanded cost at 1,000 heads: EUR {cm['landed_1000']:,} (tooling EUR {cm['tooling_eur']:,.0f} spread over 1,000). "
           + S["bom_note"])

    status = table(["Deliverable", "State", "Where"], S["status_rows"])
    out = tmpl
    for k, v in dict(status_table=status, not_ready=S["not_ready"], magnet_gap=f"{min(gaps):.2f}" if gaps else "0.8",
                     test_points=T["test_points"], layout_status=S["layout_status"], st602_status=S["st602_status"], fit_table=fit_md,
                     no_stock=no_stock, quote=quote, bom_section=bom, esp_pins=T["esp_pins"], rp_pins=T["rp_pins"],
                     sources="\n".join(f"- {s}" for s in S["sources"])).items():
        assert "{{" + k + "}}" in out, k
        out = out.replace("{{" + k + "}}", v)
    assert "{{" not in out, out[out.index("{{"):][:40]
    open(os.path.join(REPO, "docs", "04-electronics.md"), "w").write(out)
    print("wrote docs/04-electronics.md", len(out.splitlines()), "lines; quote total USD", round(tot))


if __name__ == "__main__":
    main()
