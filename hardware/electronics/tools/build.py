"""Rebuild one board's schematic from its design.py and run ERC.  usage: python3 build.py <board-folder> [sch]"""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def load_design(folder):
    spec = importlib.util.spec_from_file_location("design", os.path.join(folder, "design.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sch(folder):
    import stlib
    from schgen import write_symbol_lib
    lib = os.path.join(HERE, "..", "lib")
    os.makedirs(lib, exist_ok=True)
    write_symbol_lib(os.path.join(lib, "ST.kicad_sym"), stlib.SYMS)
    mod = load_design(folder)
    d = mod.build()
    for p in d.check():
        print("CHECK:", p)
    d.write(folder)
    for fn, body in (("sym-lib-table", '(sym_lib_table\n  (version 7)\n  (lib (name "ST")(type "KiCad")(uri "${KIPRJMOD}/../lib/ST.kicad_sym")(options "")(descr "Star Tracker project symbols"))\n)\n'),
                     ("fp-lib-table", '(fp_lib_table\n  (version 7)\n  (lib (name "ST")(type "KiCad")(uri "${KIPRJMOD}/../lib/ST.pretty")(options "")(descr "Star Tracker project footprints"))\n)\n')):
        with open(os.path.join(folder, fn), "w") as f:
            f.write(body)
    pro = os.path.join(folder, d.name + ".kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w") as f:
            json.dump({"meta": {"filename": d.name + ".kicad_pro", "version": 3}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
                       "sheets": [], "text_variables": {}}, f, indent=2)
    return d


def erc(folder, name):
    out = os.path.join(folder, "out")
    os.makedirs(out, exist_ok=True)
    rpt = os.path.join(out, name + "-erc.json")
    subprocess.run(["kicad-cli", "sch", "erc", "--format", "json", "--severity-all", "-o", rpt, os.path.join(folder, name + ".kicad_sch")],
                   check=False, capture_output=True)
    with open(rpt) as f:
        r = json.load(f)
    n = {"error": 0, "warning": 0}
    for sh in r.get("sheets", []):
        for v in sh.get("violations", []):
            n[v["severity"]] = n.get(v["severity"], 0) + 1
            items = "; ".join(i.get("description", "") for i in v.get("items", []))
            print(f"  ERC {v['severity']}: {v['type']}: {v['description']} [{items}]"[:230])
    print("ERC:", n)
    return n


if __name__ == "__main__":
    folder = os.path.abspath(sys.argv[1])
    d = sch(folder)
    print(d.name, "parts", len(d.refs), "nets", len(d.nets()))
    erc(folder, d.name)
