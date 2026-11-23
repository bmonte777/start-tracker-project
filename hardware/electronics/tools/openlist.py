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
           f"{len(errs)} errors. F = front face (red in KiCad), B = inner face (blue), In2 = inner layer 2. "
           "X and Y are the cursor position KiCad shows at the bottom of its window.", "",
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
    out += ["", "## Finishing a connection by hand in KiCad 9", "",
            "1. Start **KiCad**, click **File → Open Project**, choose `hardware/electronics/mainboard/" + name + ".kicad_pro`, then click the "
            "**PCB Editor** button (the green board icon).",
            "2. The thin white lines are the open connections. To find one from the table: click **Edit → Find**, type the part name "
            "from the *From* column (for example `U14`) and click **Find Next**; or move the cursor until the X and Y at the bottom of the "
            "window match the table.",
            "3. In the **Appearance** panel on the right, tab **Nets**, right-click the net's name and choose **Highlight** to see everything "
            "that belongs to it.",
            "4. Click **Route → Route Single Track** (or press **X**), click the pad or track end in the *From* column, move toward the *To* "
            "item and click to set corners. KiCad will not let the track touch other copper. Press **V** to drop a via and continue on the "
            "other face (red = front, blue = inner face). Click the *To* item to finish; **Esc** leaves the tool.",
            "5. If there is no room, press **Esc**, click a track that is in the way and press **D** to drag it aside, or **U** then "
            "**Delete** to remove a leftover track end (the board has some from connections that were taken up).",
            "6. Vias must stay 0.8 mm apart centre to centre, and a track 0.25 mm from a via's hole; the check in step 7 reports any that "
            "are not.",
            "7. When the white lines are gone: **Inspect → Design Rules Checker**, tick **Refill all zones before performing DRC** and "
            "**Test for parity between PCB and schematic**, click **Run DRC**. The tabs must show 0 *Violations* that are errors and 0 "
            "*Unconnected Items*.",
            "8. **File → Save**. Send the saved `" + name + ".kicad_pcb` back (attach it to a chat or upload it to the branch): the "
            "fabrication files are then made from it by `tools/fab.py`. Do not run `tools/layout.py` on the board afterwards: it rebuilds "
            "the layout from the scripts and would discard hand-made tracks."]
    with open(os.path.join(doc, name + "-open-connections.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"{len(rows)} open connections in {len(nets)} nets, {len(errs)} errors -> {name}-open-connections.md / .csv")
    return rows, errs


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
