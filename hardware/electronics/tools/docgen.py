"""Tables for the Phase 4 document, taken straight from the schematic models so they cannot drift from the boards.

Run:  python3 tools/docgen.py     -> hardware/electronics/doc/tables.json  (markdown fragments by name)
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import symlib  # noqa: E402

BOARDS = {"st-501": "mainboard", "st-520": "cartridge-board"}
NOTE = {
    "ESP_IO0": "boot strap (low at reset = serial download); also on the programming pads", "ESP_EN": "reset, 10 k / 1 uF",
    "BTN1": "button 1 (left), low when pressed", "BTN2": "button 2", "BTN3": "button 3", "BTN4": "button 4 (right)",
    "IMU_INT": "LSM6DSV INT1", "WAKE_IRQ_N": "RTC alarm, open drain, wakes from deep sleep", "VSYS_MON": "system rail / 4.03 (100 k / 33 k), ADC1",
    "I2C_SDA": "main I2C, 2.2 k pull-up", "I2C_SCL": "main I2C, 400 kHz", "PACK_SDA": "battery SMBus data (100 kHz)", "PACK_SCL": "battery SMBus clock",
    "LED_R": "status LED red, high = on", "LED_G": "status LED green", "LED_B": "status LED blue", "GNSS_PPS": "1 pulse per second, to both MCUs",
    "LINK_SYNC": "time-sync strobe ESP32 -> RP2354A", "LINK_TX": "UART ESP32 TX -> RP2354A RX (GPIO1)", "LINK_RX": "UART RP2354A TX (GPIO0) -> ESP32 RX",
    "A_DN": "USB D- of port A (native USB serial / JTAG)", "A_DP": "USB D+ of port A", "PWR_IRQ_N": "both PD controllers, open drain",
    "SWCLK_E": "SWD clock to the RP2354A (firmware update)", "SWDIO_E": "SWD data to the RP2354A", "RP_RUN": "RP2354A reset, low = reset",
    "SHUT_FOCUS": "optocoupler, high = focus (half press)", "SHUT_REL": "optocoupler, high = shutter", "ESP_TXD0": "debug UART on the programming pads",
    "ESP_RXD0": "debug UART", "ESP_IO45": "spare, test pad (strap: keep low at reset)", "PORTB_EN": "enables the camera-port converter (strap: low at reset)",
    "GNSS_TXD": "GNSS module TX -> ESP32 RX", "GNSS_RXD": "ESP32 TX -> GNSS module RX",
    "TMC_TX": "UART1 TX through 1 k onto the one-wire driver bus", "TMC_UART": "UART1 RX: the shared PDN_UART line of the three drivers",
    "DIAG_AZ": "driver DIAG (stall / fault), azimuth", "DIAG_ALT": "driver DIAG, altitude", "DIAG_ROLL": "driver DIAG, roll", "LED_RP": "heartbeat LED",
    "ALT_CS_M": "encoder chip select, altitude", "ROLL_CS_M": "encoder chip select, roll", "AZ_CS_M": "encoder chip select, azimuth",
    "ENC_MISO": "SPI1 RX, shared by the three encoders", "ENC_SCK_M": "SPI1 SCK (mode 3)", "ENC_MOSI_M": "SPI1 TX",
    "DRV_EN_N": "all three driver enables, low = on, pulled high", "BOOST_EN": "motor-rail converter enable, pulled low",
    "VM_SEL": "motor rail level: low = 10 V, high = 16 V", "MOTOR_PWR_EN": "soft-start switch in front of the boost, pulled low",
    "NTC_AZ_A": "motor thermistor, azimuth (10 k to 3.3 V)", "NTC_ALT_A": "motor thermistor, altitude", "NTC_ROLL_A": "motor thermistor, roll",
    "VMOT_MON": "motor rail / 7.67 (100 k / 15 k)",
}
for ax in ("AZ", "ALT", "ROLL"):
    NOTE[f"{ax}_STEP"] = f"step pulses, {ax.lower()}"
    NOTE[f"{ax}_DIR"] = f"direction, {ax.lower()}"


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main():
    out = {}
    m = json.load(open(os.path.join(ROOT, "mainboard", "st-501.model.json")))
    parts = {p["ref"]: p for p in m["parts"]}

    def pinmap(ref, keep):
        p = parts[ref]
        got = symlib.load(p["lib_id"], [os.path.join(ROOT, "lib")])
        plist = got[1] if isinstance(got, tuple) else got["pins"]
        names = {str(q["num"]): q["name"] for q in plist}
        rows = []
        for num, net in p["pins"].items():
            nm = names.get(num, "?")
            if not keep(nm) or net in ("NC", None):
                continue
            rows.append((nm, num, f"`{net}`", NOTE.get(net, "")))
        return rows

    def gp(nm):
        d = "".join(ch for ch in nm.split("/")[0] if ch.isdigit())
        return int(d) if d else 99

    esp = pinmap("U13", lambda n: n.startswith(("IO", "TXD", "RXD", "EN", "USB")))
    esp.sort(key=lambda r: (not r[0].startswith("IO"), gp(r[0])))
    out["esp_pins"] = table(["ESP32-S3 pin", "Module pad", "Net", "Use"], esp)
    rp = pinmap("U14", lambda n: n.startswith(("GPIO", "RUN", "SWCLK", "SWD", "USB", "QSPI")))
    rp.sort(key=lambda r: (not r[0].startswith("GPIO"), gp(r[0])))
    out["rp_pins"] = table(["RP2354A pin", "Package pin", "Net", "Use"], rp)
    out["test_points"] = table(["Pad", "Net", "Pad", "Net", "Pad", "Net"],
                               [sum(([r, f"`{list(parts[r]['pins'].values())[0]}`"] for r in row), [])
                                for row in [[f"TP{i}" for i in range(a, min(a + 3, 60))] for a in range(1, 60, 3)]
                                if all(r in parts for r in row)])
    conns = []
    for ref in sorted([r for r in parts if r.startswith("J")], key=lambda r: int(r[1:])):
        p = parts[ref]
        pins = ", ".join(f"{k} `{v}`" for k, v in p["pins"].items() if k != "MP" and not k.startswith("S"))
        conns.append((ref, p["value"], pins))
    out["connectors"] = table(["Ref", "Part", "Pins"], conns)
    for name, folder in BOARDS.items():
        mm = json.load(open(os.path.join(ROOT, folder, name + ".model.json")))
        ps = [p for p in mm["parts"] if p.get("bom", True) and not p.get("dnp")]
        nol = sorted({(p["value"], p["fields"].get("MPN", "")) for p in ps if not p["fields"].get("LCSC")})
        out[name + "_stats"] = dict(parts=len(ps), no_lcsc=[list(x) for x in nol],
                                    dnp=sorted(p["ref"] for p in mm["parts"] if p.get("dnp")))
    os.makedirs(os.path.join(ROOT, "doc"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "doc", "tables.json"), "w"), indent=1)
    print(out["esp_pins"][:1500])
    print(out["rp_pins"][:600])
    print(out["st-501_stats"])


if __name__ == "__main__":
    main()
