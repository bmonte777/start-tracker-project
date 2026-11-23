#!/usr/bin/env python3
"""Generate firmware/common/include/st_board.h from the ST-501 schematic model.

Source of truth: hardware/electronics/mainboard/st-501.model.json, written by
hardware/electronics/mainboard/design.py. Every pin, strap-derived address and divider
scale the firmware uses comes from this file; nothing is typed in by hand.

The script also cross-checks the result against the Phase 4 hand-off tables (section 10 of
docs/04-electronics.md, transcribed in HANDOFF_* below) and stops with an error on any
difference, so a schematic change can never reach the firmware silently.

Run it from the GitHub Actions workflow (it runs on every firmware build) or locally.
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODEL = ROOT / "hardware/electronics/mainboard/st-501.model.json"
OUT = ROOT / "firmware/common/include/st_board.h"

# ESP32-S3-WROOM-1 module pad -> chip GPIO (Espressif ESP32-S3-WROOM-1 datasheet v1.x, table "Pin Definitions").
WROOM1_PAD = {
    1: "GND", 2: "3V3", 3: "EN", 4: 4, 5: 5, 6: 6, 7: 7, 8: 15, 9: 16, 10: 17, 11: 18, 12: 8, 13: 19, 14: 20,
    15: 3, 16: 46, 17: 9, 18: 10, 19: 11, 20: 12, 21: 13, 22: 14, 23: 21, 24: 47, 25: 48, 26: 45, 27: 0,
    28: 35, 29: 36, 30: 37, 31: 38, 32: 39, 33: 40, 34: 41, 35: 42, 36: "RXD0", 37: "TXD0", 38: 2, 39: 1,
    40: "GND", 41: "EPAD",
}
# RP2350A QFN-60 package pin -> GPIO (RP2350 datasheet, section 14.? "Pinout", QFN-60). RP2354A = RP2350A + 2 MB flash.
RP2350A_PIN = {
    2: 0, 3: 1, 4: 2, 5: 3, 7: 4, 8: 5, 9: 6, 10: 7, 12: 8, 13: 9, 14: 10, 15: 11, 16: 12, 17: 13, 18: 14, 19: 15,
    27: 16, 28: 17, 29: 18, 31: 19, 32: 20, 33: 21, 34: 22, 35: 23, 36: 24, 37: 25, 40: 26, 41: 27, 42: 28, 43: 29,
    24: "SWCLK", 25: "SWDIO", 26: "RUN", 51: "USB_DM", 52: "USB_DP", 60: "QSPI_SS",
}

# Phase 4 hand-off, section 10.1 / 10.2 (net -> GPIO). Used only as a cross-check.
HANDOFF_ESP = {
    "ESP_IO0": 0, "BTN1": 1, "BTN2": 2, "IMU_INT": 3, "BTN3": 4, "BTN4": 5, "WAKE_IRQ_N": 6, "VSYS_MON": 7,
    "I2C_SDA": 8, "I2C_SCL": 9, "PACK_SDA": 10, "PACK_SCL": 11, "LED_R": 12, "LED_G": 13, "LED_B": 14,
    "GNSS_PPS": 15, "LINK_SYNC": 16, "LINK_TX": 17, "LINK_RX": 18, "PWR_IRQ_N": 21, "SWCLK_E": 38, "SWDIO_E": 39,
    "RP_RUN": 40, "SHUT_FOCUS": 41, "SHUT_REL": 42, "ESP_IO45": 45, "PORTB_EN": 46, "GNSS_TXD": 47, "GNSS_RXD": 48,
}
HANDOFF_RP = {
    "LINK_RX": 0, "LINK_TX": 1, "LINK_SYNC": 2, "GNSS_PPS": 3, "TMC_TX": 4, "TMC_UART": 5, "DIAG_AZ": 6,
    "DIAG_ALT": 7, "DIAG_ROLL": 8, "LED_RP": 9, "CS_ALT_M": 10, "CS_ROLL_M": 11, "ENC_MISO": 12, "CS_AZ_M": 13,
    "ENC_SCK_M": 14, "ENC_MOSI_M": 15, "STEP_AZ": 16, "DIR_AZ": 17, "STEP_ALT": 18, "DIR_ALT": 19, "STEP_ROLL": 20,
    "DIR_ROLL": 21, "DRV_EN_N": 22, "BOOST_EN": 23, "VM_SEL": 24, "MOTOR_PWR_EN": 25, "NTC_AZ_A": 26,
    "NTC_ALT_A": 27, "NTC_ROLL_A": 28, "VMOT_MON": 29,
}
HANDOFF_I2C = {"TPS25751": 0x20, "TPS25752": 0x21, "MMC5983MA": 0x30, "SH1106": 0x3C, "RV-3028": 0x52, "LSM6DSV": 0x6A}


def ohms(v: str) -> float:
    """Parse '100k', '4k7', '0R15', '33R', '5k23', '1M' into ohms."""
    v = v.split()[0]
    for sym, mul in (("M", 1e6), ("k", 1e3), ("R", 1.0)):
        if sym in v:
            a, b = v.split(sym)
            return float((a or "0") + "." + (b or "0")) * mul
    return float(v)


def main() -> int:
    m = json.loads(MODEL.read_text())
    parts = {p["ref"]: p for p in m["parts"]}
    nets: dict[str, list] = {}
    for p in m["parts"]:
        if p.get("dnp"):
            continue
        for pin, net in p["pins"].items():
            if net:
                nets.setdefault(net, []).append((p["ref"], pin, p["value"]))
    errors = []

    def mcu_map(ref, table):
        out = {}
        for pin, net in parts[ref]["pins"].items():
            if not net or not pin.isdigit():
                continue
            g = table.get(int(pin))
            if isinstance(g, int) and net not in ("GND", "+3V3"):
                out[net] = g
        return out

    esp = mcu_map("U13", WROOM1_PAD)
    rp = mcu_map("U14", RP2350A_PIN)
    for net, g in HANDOFF_ESP.items():
        if esp.get(net) != g:
            errors.append(f"ESP32 {net}: design files GPIO{esp.get(net)}, hand-off GPIO{g}")
    for net, g in HANDOFF_RP.items():
        if rp.get(net) != g:
            errors.append(f"RP2354A {net}: design files GPIO{rp.get(net)}, hand-off GPIO{g}")

    def other_end(ref, net):
        """Net at the other pin of a 2-pin part."""
        pins = parts[ref]["pins"]
        return [n for n in pins.values() if n != net][0]

    def divider(mon_net):
        """Return (top ohms, bottom ohms) of the resistor divider feeding mon_net."""
        rs = [r for r, _, v in nets[mon_net] if r.startswith("R")]
        top = bot = None
        for r in rs:
            o = other_end(r, mon_net)
            if o == "GND":
                bot = ohms(parts[r]["value"])
            else:
                top = ohms(parts[r]["value"])
        return top, bot

    vs_t, vs_b = divider("VSYS_MON")
    vm_t, vm_b = divider("VMOT_MON")
    ntc_pull = ohms([parts[r]["value"] for r, _, _ in nets["NTC_AZ"] if r.startswith("R") and other_end(r, "NTC_AZ") == "+3V3A"][0])
    vref_t, vref_b = divider("AZ_VREF")
    rsense = ohms(parts[[r for r, _, _ in nets["AZ_BRA"] if r.startswith("R")][0]]["value"])

    # TMC2209 UART addresses from the MS1/AD0 (pin 9) and MS2/AD1 (pin 10) straps (TMC2209 datasheet, pinout QFN28).
    tmc = {}
    for ax, ref in (("AZ", "U15"), ("ALT", "U17"), ("ROLL", "U19")):
        pins = parts[ref]["pins"]
        ad0 = pins.get("9") == "+3V3"
        ad1 = pins.get("10") == "+3V3"
        tmc[ax] = int(ad0) | (int(ad1) << 1)
    if tmc != {"AZ": 0, "ALT": 1, "ROLL": 2}:
        errors.append(f"TMC2209 addresses from straps {tmc}, hand-off az 0 alt 1 roll 2")

    # LSM6DSV: SDO/SA0 (pin 1) low -> 0x6A, high -> 0x6B (ST datasheet DS13510, I2C operation).
    sa0 = parts["U21"]["pins"].get("1")
    lsm = 0x6B if sa0 == "+3V3" else 0x6A
    if lsm != HANDOFF_I2C["LSM6DSV"]:
        errors.append(f"LSM6DSV address 0x{lsm:02X}")
    # TPS25751/52 ADCIN straps (design.py note: port A ADCIN1=LDO_3V3 (code 7) ADCIN2=GND -> 0x20;
    # port B both GND -> 0x21). Read back from the 0R links.
    adc_a = (other_end("R17", "PDA_ADC1"), other_end("R18", "PDA_ADC2"))
    adc_b = (other_end("R33", "PDB_ADC1"), other_end("R34", "PDB_ADC2"))
    if adc_a != ("PDA_LDO3V3", "GND") or adc_b != ("GND", "GND"):
        errors.append(f"PD controller ADCIN straps changed: A {adc_a}, B {adc_b}")
    # Port B enable: R29 (PDB_GPIO3 -> PORTB_EN) must stay unfitted, else IO46 fights the PD controller.
    if not parts["R29"].get("dnp") and "PDB_GPIO3" in parts["R29"]["pins"].values():
        errors.append("R29 fitted: PORTB_EN is also driven by TPS25752 GPIO3")
    # OLED supply orientation (R96/R97 fitted = VCC-GND-SCL-SDA module)
    oled_vcc_pin1 = not parts["R96"].get("dnp")

    if errors:
        print("Design files and hand-off disagree:\n  " + "\n  ".join(errors))
        return 1

    vsys_scale = (vs_t + vs_b) / vs_b
    vmot_scale = (vm_t + vm_b) / vm_b
    vref = 5.0 * vref_b / (vref_t + vref_b)
    ifs0 = 0.325 / (rsense + 0.020) / math.sqrt(2)
    ifs1 = 0.180 / (rsense + 0.020) / math.sqrt(2)

    L = ["/* GENERATED by firmware/common/tools/gen_board.py from hardware/electronics/mainboard/st-501.model.json",
         f" * (board {m['name']} rev {m['rev']}). Do not edit: change the schematic and re-run the script. */",
         "#pragma once", "", "/* ---- ESP32-S3 (U13, ESP32-S3-WROOM-1-N16R8): GPIO numbers ---- */"]
    for net, g in sorted(esp.items(), key=lambda x: x[1]):
        if net in ("A_DN", "A_DP"):
            continue
        L.append(f"#define ESP_GPIO_{net:<14} {g}")
    L += ["", "/* ---- RP2354A (U14): GPIO numbers ---- */"]
    for net, g in sorted(rp.items(), key=lambda x: x[1]):
        L.append(f"#define RP_GPIO_{net:<14} {g}")
    L += ["",
          "/* ---- Bus addresses (7-bit) ---- */",
          "#define I2C_ADDR_TPS25751   0x20  /* port A, ADCIN1 = LDO_3V3, ADCIN2 = GND (design.py note) */",
          "#define I2C_ADDR_TPS25752   0x21  /* port B, ADCIN1 = ADCIN2 = GND */",
          "#define I2C_ADDR_MMC5983MA  0x30",
          "#define I2C_ADDR_SH1106     0x3C",
          "#define I2C_ADDR_RV3028     0x52",
          f"#define I2C_ADDR_LSM6DSV    0x{lsm:02X}  /* SA0 = {sa0} */",
          "#define SMB_ADDR_BQ40Z50    0x0B  /* battery SMBus */",
          "#define PDA_ADDR_BQ25792    0x6B  /* on port A's private bus, reached via 4CC I2Cr/I2Cw */",
          "#define PDB_ADDR_TPS55288   0x74  /* on port B's private bus */",
          "#define PDX_ADDR_EEPROM     0x50",
          f"#define TMC_ADDR_AZ  {tmc['AZ']}", f"#define TMC_ADDR_ALT {tmc['ALT']}", f"#define TMC_ADDR_ROLL {tmc['ROLL']}",
          "",
          "/* ---- Analogue scales (from the divider resistor values) ---- */",
          f"#define VSYS_MON_SCALE   {vsys_scale:.4f}f  /* ({vs_t:.0f} + {vs_b:.0f}) / {vs_b:.0f} */",
          f"#define VMOT_MON_SCALE   {vmot_scale:.4f}f  /* ({vm_t:.0f} + {vm_b:.0f}) / {vm_b:.0f} */",
          f"#define NTC_PULLUP_OHM   {ntc_pull:.0f}.0f   /* to +3V3A; bead 10 k B3950 to GND (D46) */",
          "#define NTC_R25_OHM      10000.0f",
          "#define NTC_BETA         3950.0f",
          f"#define TMC_RSENSE_OHM   {rsense:.3f}f",
          f"#define TMC_IFS_VSENSE0  {ifs0:.4f}f  /* A RMS full scale, internal reference */",
          f"#define TMC_IFS_VSENSE1  {ifs1:.4f}f",
          f"#define TMC_VREF_STRAP_V {vref:.4f}f  /* 5VOUT x {vref_b:.0f} / ({vref_t:.0f} + {vref_b:.0f}); 0.34 A before set-up */",
          f"#define OLED_VCC_ON_PIN1 {1 if oled_vcc_pin1 else 0}",
          ""]
    OUT.write_text("\n".join(L))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(esp)} ESP32 nets, {len(rp)} RP2354A nets; all match the hand-off")
    return 0


if __name__ == "__main__":
    sys.exit(main())
