"""Compare the netlist KiCad extracts from the schematic with the design model (must be identical)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisx import parse, find, findall


def kicad_nets(sch_file, tmp):
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", tmp, sch_file], check=True, capture_output=True)
    root = parse(open(tmp).read())
    nets = {}
    for n in findall(find(root, "nets"), "net"):
        name = str(find(n, "name")[1]).lstrip("/")
        nodes = {(str(find(x, "ref")[1]), str(find(x, "pin")[1])) for x in findall(n, "node")}
        nets[name] = nodes
    comps = {str(find(c, "ref")[1]): (str(find(c, "value")[1]), str(find(c, "footprint")[1]) if find(c, "footprint") else "")
             for c in findall(find(root, "components"), "comp")}
    return nets, comps


def compare(folder, name):
    model = json.load(open(os.path.join(folder, name + ".model.json")))
    want = {}
    for p in model["parts"]:
        for num, net in p["pins"].items():
            if net:
                want.setdefault(net, set()).add((p["ref"], num))
    got, comps = kicad_nets(os.path.join(folder, name + ".kicad_sch"), os.path.join(folder, "out", name + ".net"))
    got = {k: v for k, v in got.items() if not k.startswith("unconnected-")}
    bad = 0
    for net in sorted(set(want) | set(got)):
        a, b = want.get(net, set()), got.get(net, set())
        if a != b:
            bad += 1
            print(f"  NET MISMATCH {net}: model-only {sorted(a - b)[:6]} kicad-only {sorted(b - a)[:6]}")
    refs = {p["ref"] for p in model["parts"] if p["pins"]}
    missing = refs - set(comps)
    if missing:
        bad += 1
        print("  parts missing in KiCad netlist:", sorted(missing))
    print(f"netlist check: {len(want)} nets, {len(comps)} components, {bad} mismatches")
    return bad


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1])
    name = [f[:-11] for f in os.listdir(folder) if f.endswith(".model.json")][0]
    sys.exit(1 if compare(folder, name) else 0)
