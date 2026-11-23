"""Check the committed boards without changing them: ERC on the schematic, DRC (with schematic parity) on the layout.

usage: python3 check.py <board-folder> [...]       exit code 1 if any error-level message is found
Reports go to <board-folder>/out/ as JSON; a one-line summary per board is printed.
"""
import json
import os
import subprocess
import sys


def count(path, keys):
    d = json.load(open(path))
    n = {}
    for k in keys:
        for v in d.get(k, []) if k != "sheets" else [x for s in d.get("sheets", []) for x in s.get("violations", [])]:
            n[v["severity"]] = n.get(v["severity"], 0) + 1
    return n


def main(folders):
    bad = 0
    for folder in folders:
        name = [f[:-10] for f in os.listdir(folder) if f.endswith(".kicad_pcb")][0]
        out = os.path.join(folder, "out")
        os.makedirs(out, exist_ok=True)
        erc, drc = os.path.join(out, name + "-erc.json"), os.path.join(out, name + "-drc.json")
        subprocess.run(["kicad-cli", "sch", "erc", "--format", "json", "--severity-all", "-o", erc, os.path.join(folder, name + ".kicad_sch")],
                       capture_output=True)
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "-o", drc,
                        os.path.join(folder, name + ".kicad_pcb")], capture_output=True)
        e, d = count(erc, ["sheets"]), count(drc, ["violations", "unconnected_items", "schematic_parity"])
        print(f"{name}: ERC {e or 'clean'}; DRC {d or 'clean'}")
        bad += e.get("error", 0) + d.get("error", 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
