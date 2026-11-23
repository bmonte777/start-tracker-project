"""List what KiCad's DRC still reports on a board: open connections and errors, as Markdown and CSV.

usage: python3 openlist.py <board-folder>      (reads <board>/out/<name>-drc.json, written by layout.py or check.py)

The positions are the ones KiCad shows in its status bar (X, Y in mm), so each item can be found with the cursor."""
import csv
import json
import math
import os
import re
import sys


def item(i):
    d = i.get("description", "")
    m = re.match(r"Pad (\S+) \[(\S+)\] of (\S+) on (\S+)", d)
    if m:
        return f"{m.group(3)} pad {m.group(1)}", m.group(4).replace(".Cu", "")
    m = re.match(r"Track \[(\S+)\] on (\S+), length ([\d.]+)", d)
    if m:
        return f"track end ({m.group(3)} mm piece)", m.group(2).replace(".Cu", "")
    m = re.match(r"Via \[(\S+)\]", d)
    if m:
        return "via", "all"
    m = re.match(r"Zone \[(\S+)\] on (\S+)", d)
    if m:
        return "copper area", m.group(2).replace(".Cu", "")
    return d[:40], ""


def main(folder):
    name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
    r = json.load(open(os.path.join(folder, "out", name + "-drc.json")))
    rows = []
    for v in r.get("unconnected_items", []):
        a, b = v["items"][0], v["items"][1]
        net = re.search(r"\[(\S+)\]", a["description"]).group(1)
        (na, la), (nb, lb) = item(a), item(b)
        pa, pb = a["pos"], b["pos"]
        rows.append(dict(net=net, a=na, la=la, ax=pa["x"], ay=pa["y"], b=nb, lb=lb, bx=pb["x"], by=pb["y"],
                         d=math.hypot(pa["x"] - pb["x"], pa["y"] - pb["y"])))
    rows.sort(key=lambda q: (q["net"], q["ax"], q["ay"]))
    errs = [v for v in r.get("violations", []) if v["severity"] == "error"]
    doc = os.path.join(folder, "doc")
    os.makedirs(doc, exist_ok=True)
    with open(os.path.join(doc, name + "-open-connections.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["No.", "Net", "From", "Face", "X mm", "Y mm", "To", "Face", "X mm", "Y mm", "Straight distance mm"])
        for i, q in enumerate(rows, 1):
            w.writerow([i, q["net"], q["a"], q["la"], f"{q['ax']:.2f}", f"{q['ay']:.2f}", q["b"], q["lb"], f"{q['bx']:.2f}", f"{q['by']:.2f}",
                        f"{q['d']:.1f}"])
    nets = sorted({q["net"] for q in rows})
    out = [f"# {name.upper()} — connections still open", "",
           f"From KiCad's design-rule check of `{name}.kicad_pcb`: **{len(rows)} open connections in {len(nets)} nets**, "
           f"{len(errs)} errors. F = front face (red in KiCad), B = back face (blue), In2 = inner layer 2. "
           "X and Y are KiCad's page coordinates (board centre at 100, 100; Y grows downwards).", "",
           "| No. | Net | From | Face | X | Y | To | Face | X | Y | Distance, mm |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, q in enumerate(rows, 1):
        out.append(f"| {i} | `{q['net']}` | {q['a']} | {q['la']} | {q['ax']:.2f} | {q['ay']:.2f} | {q['b']} | {q['lb']} | {q['bx']:.2f} | "
                   f"{q['by']:.2f} | {q['d']:.1f} |")
    if errs:
        out += ["", "## Errors", "", "| Type | What KiCad says | Items | X | Y |", "|---|---|---|---|---|"]
        for v in errs:
            its = "; ".join(i.get("description", "") for i in v.get("items", []))
            p = v["items"][0]["pos"] if v.get("items") else {"x": 0, "y": 0}
            out.append(f"| {v['type']} | {v['description']} | {its} | {p['x']:.2f} | {p['y']:.2f} |")
    if rows or errs:
        out += ["", "## How these are closed", "",
                "Nobody finishes the board by hand in KiCad. Each open connection is joined on free cells by "
                "`tools/closeonly.py <board> NET ...` (or laid by hand as explicit pieces), the result goes into the board's "
                "`route_fixes.py` as a new stage, `tools/fixroutes.py <board>` applies it to the routes file and `tools/layout.py <board>` "
                "lays the board and runs this check again."]
    else:
        out += ["", "Nothing is open: the board's connections are complete and KiCad reports no errors."]
    with open(os.path.join(doc, name + "-open-connections.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"{len(rows)} open connections in {len(nets)} nets, {len(errs)} errors -> {name}-open-connections.md / .csv")
    return rows, errs


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
