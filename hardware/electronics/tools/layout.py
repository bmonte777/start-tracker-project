"""Build one board's layout from design.py, autoroute the slow nets, fill zones, save and run DRC.
usage: python3 layout.py <board-folder> [--no-route]

The DRC report lists every message KiCad produces; nothing is filtered here."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build      # noqa: E402
import netcheck   # noqa: E402
import stfp       # noqa: E402


def drc(folder, name):
    rpt = os.path.join(folder, "out", name + "-drc.json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--units", "mm", "-o", rpt,
                    os.path.join(folder, name + ".kicad_pcb")], check=False, capture_output=True)
    r = json.load(open(rpt))
    n = {}
    for key in ("violations", "unconnected_items", "schematic_parity"):
        for v in r.get(key, []):
            k = (key, v["severity"], v["type"])
            n[k] = n.get(k, 0) + 1
            if n[k] <= 4:
                items = "; ".join(i.get("description", "") for i in v.get("items", []))
                pos = v.get("items", [{}])[0].get("pos", {})
                print(f"  DRC {v['severity']} {v['type']}: {v['description']} [{items}] @ {pos.get('x', 0):.2f},{pos.get('y', 0):.2f}"[:260])
    print("DRC summary:", {f"{a}/{b}/{c}": v for (a, b, c), v in sorted(n.items())} or "clean")
    return n


def main(folder, route=True):
    lib = os.path.join(HERE, "..", "lib", "ST.pretty")
    os.makedirs(lib, exist_ok=True)
    for nm, text in stfp.FPS:
        with open(os.path.join(lib, nm + ".kicad_mod"), "w") as f:
            f.write(text)
    d = build.sch(folder)
    build.erc(folder, d.name)
    if netcheck.compare(folder, d.name):
        sys.exit("schematic netlist does not match the model")
    from pcbgen import PCB
    mod = build.load_design(folder)
    pcb = PCB(folder, d.name, **getattr(mod, "PCB_ARGS", {}))
    mod.layout(pcb)
    missing = [r for r in pcb.comps if r not in pcb.fps]
    if missing:
        sys.exit("not placed: " + " ".join(sorted(missing)))
    if route and pcb.unrouted():
        print("unrouted before autoroute:", pcb.unrouted())
        print(pcb.autoroute(passes=int(os.environ.get("ROUTE_PASSES", getattr(mod, "ROUTE_PASSES", 20)))))
        print("stubs removed:", pcb.trim_stubs(getattr(mod, "POUR_NETS", ("GND",))))
    pcb.hole_keepouts()
    if hasattr(mod, "finish"):
        mod.finish(pcb)
    pcb.fill()
    pcb.save()
    print("unrouted after:", pcb.unrouted())
    return drc(folder, d.name)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]), "--no-route" not in sys.argv)
