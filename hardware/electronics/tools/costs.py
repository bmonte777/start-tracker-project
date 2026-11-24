"""Cost of each assembled board from its BOM, at 1 / 100 / 1,000 heads, and the quote estimate for five sets.

Run:  python3 tools/costs.py        -> fab/costs.json and a printed summary
Prices are USD without VAT. "quoted" = read from LCSC / JLCPCB on 22 Nov 2026; everything else is an estimate by part class.
Six-layer bare boards: JLCPCB lists 5 pieces up to 100 x 100 mm from USD 35.1 with ENIG and filled, capped vias included
(jlcpcb.com, multilayer page, read 23 Nov 2026); the 1 oz inner copper (decision D61) and the larger quantities are estimates.
Parts that have their own line in the master parts list (the large ICs, sockets, switches) are left out of the board
totals here so that nothing is counted twice.
"""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, "..", "fab")
BOARDS = {"st-501": dict(per_head=1, layers=6, area_cm2=60.0, sides=2), "st-520": dict(per_head=3, layers=2, area_cm2=7.1, sides=2),
          # battery board: parts on one face; the gauge, the second protector and the fuse have their own parts-list lines
          "st-602": dict(per_head=1, layers=2, area_cm2=12.8, sides=1,
                         own={"BQ40Z50RSMR-R2": "ST-603", "BQ294700DSGR": "ST-604", "ITV4030L0815NR": "ST-604"})}

# manufacturer part -> master parts list line that already carries its price
OWN_LINE = {"ESP32-S3-WROOM-1-N16R8": "ST-502", "RP2354A": "ST-503", "TMC2209-LA-T": "ST-504", "BQ25792RQMR": "ST-505",
            "TPS25751DREFR": "ST-506", "TPS25752ASRSMR": "ST-507", "TPS55288RPMR": "ST-508", "TPS61288RQQR": "ST-509",
            "TPS62932DRLR": "ST-510", "MAX-M10S-00B": "ST-511", "RV-3028-C7 32.768kHz 1ppm TA QC": "ST-513", "MS621FE-FL11E": "ST-513",
            "LSM6DSVTR": "ST-514", "MMC5983MA": "ST-515", "GT-USB-7051A": "ST-517", "TS-1187A-B-A-B": "ST-518",
            "KT-0603R": "ST-519", "19-217/GHC-YR1S2/3T": "ST-519", "19-217/BHC-ZL1M2RY/3T": "ST-519",
            "TLP291(GB-TP,SE": "ST-532", "SM03B-GHS-TB(LF)(SN)": "ST-532", "MT6835GT-STD": "ST-521", "MT6835GT-STD-R": "ST-521"}

# (price at 1, 100, 1000 heads, source)
QUOTED = {"SM04B-GHS-TB(LF)(SN)": (0.47, 0.36, 0.29, "quoted"), "TPS563201DDCR": (0.35, 0.25, 0.20, "est"),
          "CAT24C512WI-GT3": (0.45, 0.32, 0.26, "est"), "AON7403": (0.25, 0.18, 0.14, "est"), "AON7400A": (0.12, 0.09, 0.07, "est"),
          "2N7002": (0.016, 0.010, 0.008, "quoted"), "SRV05-4.TCT": (0.12, 0.08, 0.06, "est"), "SMBJ24A": (0.14, 0.10, 0.07, "est"),
          "SMBJ12A-TR": (0.14, 0.10, 0.07, "quoted"), "BZT52C12S": (0.02, 0.012, 0.01, "est"), "MWSC0630H4R7MT": (0.25, 0.18, 0.14, "est"),
          "MWSC0630H2R2MT": (0.25, 0.18, 0.14, "est"), "SWPA5040S6R8MT": (0.12, 0.08, 0.06, "est"), "X322512MSB4SI": (0.08, 0.06, 0.05, "est"),
          "BLM18PG121SN1D": (0.012, 0.008, 0.006, "est"), "BM15B-GHS-TBT(LF)(SN)": (0.75, 0.55, 0.45, "est"),
          "B4B-PH-SM4-TB(LF)(SN)": (0.20, 0.15, 0.12, "est"), "U.FL-R-SMT-1(80)": (0.15, 0.10, 0.08, "est"),
          "HoJLR1206-1W-1mR-1%": (0.10, 0.07, 0.05, "est"), "BAT54WS": (0.02, 0.012, 0.01, "est"),
          "TS-1187A-B-A-B": (0.06, 0.045, 0.035, "est"), "19-217/GHC-YR1S2/3T": (0.012, 0.008, 0.006, "est")}
CLASS = [(r"^R_0402|^R0402", (0.002, 0.0012, 0.0009)), (r"^R_1206|^R1206", (0.05, 0.03, 0.02)), (r"^C_0402|^C0402", (0.003, 0.002, 0.0015)),
         (r"^C_0603|^C0603", (0.012, 0.008, 0.006)), (r"^C_0805|^C0805", (0.03, 0.02, 0.015)), (r"^C_1206|^C1206", (0.05, 0.035, 0.025)),
         (r"^CP_Elec", (0.35, 0.25, 0.20)), (r"^L_0805|^L_0402", (0.06, 0.04, 0.03)), (r"^D_SOD", (0.03, 0.02, 0.015)),
         (r"^LED", (0.01, 0.007, 0.005)), (r"PinHeader|PinSocket", (0.05, 0.03, 0.02)), (r".", (0.10, 0.07, 0.05))]

# JLCPCB fees (estimates from the public price list; the order page gives the exact figure)
SETUP = {1: 8.0, 2: 50.0}                 # economic one side; standard both sides (2 x 25)
STENCIL = {1: 1.5, 2: 16.0}
EXTENDED_FEE = 3.0                        # per extended (non-basic) part type, once per order
JOINT = 0.0017                            # per solder joint


def pcb_price(layers, area_cm2, n):
    """Bare board price each, USD: JLCPCB prototype tier up to 5-10 pieces, area-priced above that."""
    if layers == 2:                       # small round board, panel-priced
        return 0.8 if n <= 5 else (0.4 if n <= 30 else (0.15 if n <= 500 else 0.08))
    if layers >= 6:                       # 100 x 60 mm, 6 layers, ENIG, filled and capped vias, 1 oz inner copper
        return 9.0 if n <= 5 else (4.0 if n <= 200 else 2.8)
    return 6.0 if n <= 5 else (2.2 if n <= 200 else 1.5)      # 100 x 60 mm, 4 layers, ENIG


FOLDER = {"st-501": "mainboard", "st-520": "cartridge-board", "st-602": "battery-board"}


def bom_path(name):
    for p in (os.path.join(FAB, name, name + "-bom.csv"), os.path.join(HERE, "..", FOLDER[name], name + "-bom.csv")):
        if os.path.exists(p):
            return p
    return None


def board(name, spec):
    rows = list(csv.DictReader(open(bom_path(name))))
    parts = [0.0, 0.0, 0.0]
    own, types, joints, lines = {}, 0, 0, []
    own_map = spec.get("own", OWN_LINE)
    for r in rows:
        q = len(r["Designator"].split(","))
        mpn = r.get("MPN", "")
        if mpn in own_map:
            own[own_map[mpn]] = own.get(own_map[mpn], 0) + q
            if r["LCSC Part #"]:              # a part without an LCSC number is not fitted by JLCPCB (the pack's fuse)
                types += 1
                joints += q * 16
            continue
        pr = QUOTED.get(mpn)
        if pr is None:
            pr = next(v for pat, v in CLASS if re.search(pat, r["Footprint"])) + ("est",)
        for i in range(3):
            parts[i] += q * pr[i]
        types += 0 if re.search(r"^[RC]_?0402|^[RC]0402", r["Footprint"]) and r["LCSC Part #"] else 1
        joints += q * (2 if re.search(r"^[RCLD]_|^LED", r["Footprint"]) else 8)
        lines.append((r["Comment"], q, pr[0]))
    out = {}
    for i, heads in enumerate((1, 100, 1000)):
        n = heads * spec["per_head"]
        built = max(n, 2)
        bare = max(n, 5)
        fixed = SETUP[spec["sides"]] + STENCIL[spec["sides"]] + EXTENDED_FEE * types
        total = fixed + bare * pcb_price(spec["layers"], spec["area_cm2"], bare) + built * (parts[i] + joints * JOINT)
        out[heads] = round(total / n, 2)
    return dict(per_board=out, parts_usd=[round(x, 2) for x in parts], part_types=types, joints=joints, own_lines=own, bom_lines=len(rows))


def main():
    res = {}
    for name, spec in BOARDS.items():
        if bom_path(name):
            res[name] = board(name, spec)
            res[name]["per_head"] = spec["per_head"]
    json.dump(res, open(os.path.join(FAB, "costs.json"), "w"), indent=1)
    for k, v in res.items():
        print(k, v["per_board"], "parts", v["parts_usd"], "types", v["part_types"], "joints", v["joints"], "own", v["own_lines"])


if __name__ == "__main__":
    main()
