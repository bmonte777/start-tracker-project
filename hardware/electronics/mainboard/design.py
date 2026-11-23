"""ST-501 mainboard: schematic as code (layout follows in layout()).
Rebuild: tools/build.py mainboard (schematic + ERC) or the GitHub workflow "Phase 4 electronics".

100 x 60 mm, 4 layers, upright behind the front bezel. Front face: OLED, four buttons, two USB-C, status LED.
Inner face: everything else, parts up to 12 mm tall.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import catalog as cat                    # noqa: E402
from schgen import Design, NC           # noqa: E402

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
PCB_ARGS = dict(layers=6, default_track=0.15, default_via=(0.5, 0.3), clearance=0.127)

# Cartridge plug, the same pin numbers at both ends of the harness (see cartridge-board/design.py)
AXES = [("AZ", 0), ("ALT", 1), ("ROLL", 2)]

# Firmware pin maps (also written to docs/04-electronics.md)
ESP = {"IO0": "ESP_IO0", "IO1": "BTN1", "IO2": "BTN2", "IO3": "IMU_INT", "IO4": "BTN3", "IO5": "BTN4", "IO6": "WAKE_IRQ_N", "IO7": "VSYS_MON",
       "IO8": "I2C_SDA", "IO9": "I2C_SCL", "IO10": "PACK_SDA", "IO11": "PACK_SCL", "IO12": "LED_R", "IO13": "LED_G", "IO14": "LED_B",
       "IO15": "GNSS_PPS", "IO16": "LINK_SYNC", "IO17": "LINK_TX", "IO18": "LINK_RX", "USB_D-": "A_DN", "USB_D+": "A_DP", "IO21": "PWR_IRQ_N",
       "IO35": NC, "IO36": NC, "IO37": NC, "IO38": "SWCLK_E", "IO39": "SWDIO_E", "IO40": "RP_RUN", "IO41": "SHUT_FOCUS", "IO42": "SHUT_REL",
       "TXD0": "ESP_TXD0", "RXD0": "ESP_RXD0", "IO45": "ESP_IO45", "IO46": "PORTB_EN", "IO47": "GNSS_TXD", "IO48": "GNSS_RXD"}
RP = {"GPIO0": "LINK_RX", "GPIO1": "LINK_TX", "GPIO2": "LINK_SYNC", "GPIO3": "GNSS_PPS", "GPIO4": "TMC_TX", "GPIO5": "TMC_UART",
      "GPIO6": "DIAG_AZ", "GPIO7": "DIAG_ALT", "GPIO8": "DIAG_ROLL", "GPIO9": "LED_RP", "GPIO10": "CS_ALT_M", "GPIO11": "CS_ROLL_M",
      "GPIO12": "ENC_MISO", "GPIO13": "CS_AZ_M", "GPIO14": "ENC_SCK_M", "GPIO15": "ENC_MOSI_M", "GPIO16": "STEP_AZ", "GPIO17": "DIR_AZ",
      "GPIO18": "STEP_ALT", "GPIO19": "DIR_ALT", "GPIO20": "STEP_ROLL", "GPIO21": "DIR_ROLL", "GPIO22": "DRV_EN_N", "GPIO23": "BOOST_EN",
      "GPIO24": "VM_SEL", "GPIO25": "MOTOR_PWR_EN", "GPIO26/ADC0": "NTC_AZ_A", "GPIO27/ADC1": "NTC_ALT_A", "GPIO28/ADC2": "NTC_ROLL_A",
      "GPIO29/ADC3": "VMOT_MON"}


def build():
    d = Design("st-501", "ST-501 mainboard", rev="A", sym_dirs=[LIB])
    n = {}

    def ref(prefix):
        n[prefix] = n.get(prefix, 0) + 1
        return f"{prefix}{n[prefix]}"

    def r(s, value, a, b, **kw):
        fp, f = cat.fields("R", value)
        f.update(kw)
        return s.R(ref("R"), value, a, b, pkg=fp, **f)

    def c(s, value, a, b, **kw):
        fp, f = cat.fields("C", value)
        f.update(kw)
        shown = {"100n50": "100n 50V", "10u50": "10u 50V"}.get(value, value)
        return s.C(ref("C"), shown, a, b, pkg=fp, **f)

    def two(s, lib, prefix, key, a, b, value=None, **kw):
        fp, f = cat.fields("P", key)
        f.update(kw)
        return s.two(lib, ref(prefix), value or cat.PART[key][1], a, b, fp, **f)

    def ic(s, lib, prefix, key, pins, x, y, value=None, **kw):
        fp, f = cat.fields("P", key)
        f.update(kw)
        return s.part(lib, ref(prefix), value or cat.PART[key][1], fp, pins, x=x, y=y, **f)

    tpn = [0]

    def tp(s, net):
        tpn[0] += 1
        return s.tp(f"TP{tpn[0]}", net)

    # ------------------------------------------------------------------------------------------ 1 battery input and charger
    s = d.sheet("power", "Battery input, charger and system rail")
    s.note(20, 20, "Battery input. J1: two solder pads for the battery lead (pad 1 +, pad 2 -); the lead carries an in-line XT30.\n"
                   "Q1 blocks a reversed bench supply. J2: pack SMBus and presence.", 1.6)
    s.part("Connector_Generic:Conn_01x02", ref("J"), "BAT+ BAT-", cat.PART["BATPADS"][0], {1: "VBAT_IN", 2: "GND"}, x=35, y=40, bom=False)
    ic(s, "ST:PMOS_DFN33", "Q", "PFET", {"G": "Q1_G", "D": "VBAT_IN", "S": "VBAT"}, 80, 45)
    fp, f = cat.fields("P", "GH4H")
    s.part("Connector_Generic_MountingPin:Conn_01x04_MountingPin", ref("J"), cat.PART["GH4H"][1], fp,
           {1: "SMBC_J", 2: "SMBD_J", 3: "PRES_J", 4: "GND", "MP": "GND"}, x=35, y=80, **f)
    ic(s, "Power_Protection:SRV05-4", "U", "SRV05", {"IO1": "SMBC_J", "IO2": "SMBD_J", "IO3": "PRES_J", "IO4": "PRES_J", "VP": "+3V3", "VN": "GND"}, 80, 85)
    s.lane(25, 110, cols=3)
    r(s, "100k", "Q1_G", "GND")
    two(s, "Device:D_Zener", "D", "ZENER12", "VBAT", "Q1_G")
    two(s, "Device:D_TVS", "D", "TVS12", "VBAT_IN", "GND")
    r(s, "100R", "SMBC_J", "PACK_SCL")
    r(s, "100R", "SMBD_J", "PACK_SDA")
    r(s, "1k", "PRES_J", "GND")
    r(s, "4k7", "+3V3", "PACK_SCL")
    r(s, "4k7", "+3V3", "PACK_SDA")
    r(s, "100k", "VSYS", "VSYS_MON")
    r(s, "33k", "VSYS_MON", "GND")
    c(s, "100n", "VSYS_MON", "GND")

    s.note(150, 28, "Charger and power path: BQ25792, 2 cells, 750 kHz. Controlled over I2C by the port A PD controller (address 0x6B).", 1.6)
    ic(s, "Battery_Management:BQ25798", "U", "BQ25792",
       {"STAT": "CHG_STAT", "VBUS": "VBUS_CHG", "BTST1": "CHG_BT1", "REGN": "CHG_REGN", "D+": NC, "D-": NC, "VAC2": "VBUS_CHG", "VAC1": "VBUS_CHG",
        "ACDRV2": "GND", "ACDRV1": "GND", "~{QON}": "CHG_QON", "~{CE}": "GND", "SCL": "PDA_SCLC", "SDA": "PDA_SDAC", "TS": "CHG_TS",
        "ILIM_HIZ": "CHG_ILIM", "BATP": "CHG_BATP", "BTST2": "CHG_BT2", "PROG": "CHG_PROG", "~{INT}": "PDA_IRQC", "BAT": "VBAT", "SDRV": "CHG_SDRV",
        "SYS": "VSYS", "SW2": "CHG_SW2", "GND": "GND", "SW1": "CHG_SW1", "PMID": "CHG_PMID"}, 215, 75)
    s.lane(150, 135, cols=5)
    two(s, "Device:L", "L", "L2u2", "CHG_SW1", "CHG_SW2", value="2u2")
    c(s, "47n", "CHG_BT1", "CHG_SW1")
    c(s, "47n", "CHG_BT2", "CHG_SW2")
    c(s, "4u7", "CHG_REGN", "GND")
    c(s, "1n", "CHG_SDRV", "GND")
    for _ in range(2):
        c(s, "10u50", "VBUS_CHG", "GND")
    c(s, "100n50", "VBUS_CHG", "GND")
    for _ in range(3):
        c(s, "10u50", "CHG_PMID", "GND")
    c(s, "100n50", "CHG_PMID", "GND")
    for _ in range(3):
        c(s, "22u", "VSYS", "GND")
    c(s, "100n50", "VSYS", "GND")
    for _ in range(2):
        c(s, "22u", "VBAT", "GND")
    r(s, "8k2", "CHG_PROG", "GND")
    r(s, "5k23", "CHG_REGN", "CHG_TS")
    r(s, "30k1", "CHG_TS", "GND")
    r(s, "10k", "CHG_TS", "GND")
    r(s, "10k", "CHG_REGN", "CHG_ILIM")
    r(s, "26k7", "CHG_ILIM", "GND")
    r(s, "100R", "VBAT", "CHG_BATP")
    r(s, "10k", "+3V3", "CHG_STAT")
    two(s, "Device:C_Polarized", "C", "CP47u25", "VBUS_CHG", "GND", value="47u 25V")
    s.lane(330, 40, cols=1, dy=7.62)
    for net in ("VBAT_IN", "VBAT", "VSYS", "VBUS_CHG", "CHG_REGN", "CHG_STAT", "CHG_QON", "PACK_SCL", "PACK_SDA", "GND", "GND"):
        tp(s, net)
    s.lane(380, 40, cols=1, dy=15.24)
    for net in ("VBAT_IN", "VBUS_CHG", "GND"):
        s.flag(net)

    # ------------------------------------------------------------------------------------------ 2 USB-C port A
    s = d.sheet("usb_a", "USB-C port A: power in or out, USB data")
    s.note(20, 20, "Port A: TPS25751D (I2C target address 0x20; ADCIN1 = 7, ADCIN2 = 0: safe mode with a dead battery). "
                   "Its controller port drives the charger and reads the configuration EEPROM (0x50).", 1.6)
    usb = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND", "A8": NC, "B8": NC}
    fp, f = cat.fields("P", "USBC")
    pins = dict(usb, **{"A4": "VBUS_A", "A9": "VBUS_A", "B4": "VBUS_A", "B9": "VBUS_A", "A5": "A_CC1", "B5": "A_CC2", "A6": "A_DP", "B6": "A_DP",
                        "A7": "A_DN", "B7": "A_DN"})
    s.part("Connector:USB_C_Receptacle_USB2.0_16P", ref("J"), "USB-C A", fp, pins, x=40, y=80, **f)
    ic(s, "ST:TPS25751D", "U", "TPS25751D",
       {"VIN_3V3": "+3V3", "LDO_3V3": "PDA_LDO3V3", "LDO_1V5": "PDA_LDO1V5", "ADCIN1": "PDA_ADC1", "ADCIN2": "PDA_ADC2", "I2Ct_SDA": "I2C_SDA",
        "I2Ct_SCL": "I2C_SCL", "I2Ct_IRQ": "PWR_IRQ_N", "I2Cc_SDA": "PDA_SDAC", "I2Cc_SCL": "PDA_SCLC", "I2Cc_IRQ": "PDA_IRQC", "GPIO0": "PDA_GPIO0",
        "GPIO1": NC, "GPIO2": NC, "GPIO3": NC, "GPIO6": NC, "GPIO7": NC, "GPIO11": NC, "GND": "GND", "EP_GND": "GND", "VBUS": "VBUS_A",
        "VBUS_IN": "VBUS_A", "PPHV": "VBUS_CHG", "DRAIN": "PDA_DRAIN", "EP_DRAIN": "PDA_DRAIN", "PP5V": "+5V", "CC1": "A_CC1", "CC2": "A_CC2",
        "GPIO4/USB_P": NC, "GPIO5/USB_N": NC}, 150, 85)
    ic(s, "Memory_EEPROM:24LC512", "U", "EEPROM",
       {"A0": "GND", "A1": "GND", "A2": "GND", "GND": "GND", "SDA": "PDA_SDAC", "SCL": "PDA_SCLC", "WP": "GND", "VCC": "PDA_LDO3V3"}, 240, 60)
    ic(s, "Power_Protection:SRV05-4", "U", "SRV05", {"IO1": "A_DP", "IO2": "A_DN", "IO3": "A_DP", "IO4": "A_DN", "VP": "+3V3", "VN": "GND"}, 240, 110)
    s.lane(30, 170, cols=5)
    c(s, "10u", "+3V3", "GND")
    c(s, "10u", "PDA_LDO3V3", "GND")
    c(s, "10u", "PDA_LDO1V5", "GND")
    c(s, "10u50", "VBUS_A", "GND")
    c(s, "100n50", "VBUS_A", "GND")
    c(s, "10u", "+5V", "GND")
    c(s, "220p", "A_CC1", "GND")
    c(s, "220p", "A_CC2", "GND")
    c(s, "100n", "PDA_LDO3V3", "GND")
    two(s, "Device:D_TVS", "D", "TVS24", "VBUS_A", "GND")
    two(s, "Device:D_TVS", "D", "ESD24", "A_CC1", "GND")
    two(s, "Device:D_TVS", "D", "ESD24", "A_CC2", "GND")
    r(s, "0R", "PDA_LDO3V3", "PDA_ADC1")
    r(s, "0R", "PDA_ADC2", "GND")
    r(s, "10k", "PDA_GPIO0", "GND")
    r(s, "3k3", "PDA_LDO3V3", "PDA_SDAC")
    r(s, "3k3", "PDA_LDO3V3", "PDA_SCLC")
    r(s, "10k", "PDA_LDO3V3", "PDA_IRQC")
    s.lane(330, 40, cols=1, dy=7.62)
    for net in ("VBUS_A", "PDA_SDAC", "PDA_SCLC", "PDA_LDO3V3", "A_CC1", "A_CC2"):
        tp(s, net)
    s.lane(380, 40, cols=1, dy=15.24)
    s.flag("VBUS_A")

    # ------------------------------------------------------------------------------------------ 3 USB-C port B
    s = d.sheet("usb_b", "USB-C port B: 27 W to the camera")
    s.note(20, 20, "Port B, source only: TPS25752A (I2C target address 0x21; ADCIN1 = 0, ADCIN2 = 0). 5 V / 3 A comes from the 5 V rail through the chip;\n"
                   "9 V / 3 A comes from the TPS55288 (I2C 0x74) through Q2-Q3. Data pins go to pads for camera control in v2 (D6).", 1.6)
    fp, f = cat.fields("P", "USBC")
    pins = dict(usb, **{"A4": "VBUS_B", "A9": "VBUS_B", "B4": "VBUS_B", "B9": "VBUS_B", "A5": "B_CC1", "B5": "B_CC2", "A6": "B_DP", "B6": "B_DP",
                        "A7": "B_DN", "B7": "B_DN"})
    s.part("Connector:USB_C_Receptacle_USB2.0_16P", ref("J"), "USB-C B", fp, pins, x=40, y=85, **f)
    ic(s, "ST:TPS25752A", "U", "TPS25752A",
       {"VIN_3V3": "+3V3", "LDO_3V3": "PDB_LDO3V3", "LDO_1V5": "PDB_LDO1V5", "ADCIN1": "PDB_ADC1", "ADCIN2": "PDB_ADC2", "I2Ct_SDA": "I2C_SDA",
        "I2Ct_SCL": "I2C_SCL", "I2Ct_IRQ": "PWR_IRQ_N", "I2Cc_SDA": "PDB_SDAC", "I2Cc_SCL": "PDB_SCLC", "I2Cc_IRQ": "PDB_IRQC", "GPIO0/LD1": "PDB_LD1",
        "GPIO1": NC, "GPIO2/LD2": "PDB_LD2", "GPIO3": "PDB_GPIO3", "GPIO6": NC, "GPIO7": NC, "GPIO11": NC, "GND": "GND", "EP": "GND",
        "VBUS": "VBUS_B", "PP5V": "+5V", "VSYS": "VPB", "GATE_VSYS": "PB_GVSYS", "GATE_VBUS": "PB_GVBUS", "CC1": "B_CC1", "CC2": "B_CC2",
        "GPIO4/USB_P": "B_DP", "GPIO5/USB_N": "B_DN"}, 135, 85)
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "PB_GVSYS", "D": "PB_MID", "S": "VPB"}, 205, 50)
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "PB_GVBUS", "D": "PB_MID", "S": "VBUS_B"}, 245, 50)
    ic(s, "ST:TPS55288", "U", "TPS55288",
       {"VIN": "VSYS", "EN/UVLO": "PORTB_EN", "SCL": "PDB_SCLC", "SDA": "PDB_SDAC", "MODE": "PB_MODE", "FSW": "PB_FSW", "DITH/SYNC": "PB_DITH",
        "ILIM": "PB_ILIM", "COMP": "PB_COMP", "CDC": NC, "FB/INT": "PDB_IRQC", "VCC": "PB_VCC", "AGND": "GND", "PGND": "GND", "DR1H": "PB_DR1H",
        "BOOT1": "PB_BOOT1", "SW1": "PB_SW1", "DR1L": "PB_DR1L", "BOOT2": "PB_BOOT2", "SW2": "PB_SW2", "VOUT": "VPB_RAW", "ISP": "VPB_RAW",
        "ISN": "VPB"}, 215, 120)
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "PB_DR1H", "D": "VSYS", "S": "PB_SW1"}, 290, 100)
    ic(s, "ST:NMOS_DFN33", "Q", "NFET", {"G": "PB_DR1L", "D": "PB_SW1", "S": "GND"}, 290, 140)
    ic(s, "Memory_EEPROM:24LC512", "U", "EEPROM",
       {"A0": "GND", "A1": "GND", "A2": "GND", "GND": "GND", "SDA": "PDB_SDAC", "SCL": "PDB_SCLC", "WP": "GND", "VCC": "PDB_LDO3V3"}, 50, 150)
    ic(s, "Power_Protection:SRV05-4", "U", "SRV05", {"IO1": "B_DP", "IO2": "B_DN", "IO3": "B_DP", "IO4": "B_DN", "VP": "+3V3", "VN": "GND"}, 110, 155)
    s.lane(30, 190, cols=6, dx=45.72)
    two(s, "Device:L", "L", "L4u7", "PB_SW1", "PB_SW2", value="4u7")
    r(s, "0R01", "VPB_RAW", "VPB")
    c(s, "100n", "PB_BOOT1", "PB_SW1")
    c(s, "100n", "PB_BOOT2", "PB_SW2")
    c(s, "4u7", "PB_VCC", "GND")
    c(s, "10n", "PB_DITH", "GND")
    r(s, "49k9", "PB_FSW", "GND")
    r(s, "6k19", "PB_MODE", "GND")
    r(s, "44k2", "PB_ILIM", "GND")
    r(s, "20k", "PB_COMP", "PB_COMP_C")
    c(s, "10n", "PB_COMP_C", "GND")
    c(s, "100p", "PB_COMP", "GND")
    for _ in range(3):
        c(s, "22u", "VSYS", "GND")
    c(s, "100n50", "VSYS", "GND")
    for _ in range(3):
        c(s, "22u", "VPB_RAW", "GND")
    c(s, "100n50", "VPB_RAW", "GND")
    c(s, "22u", "VPB", "GND")
    r(s, "100k", "PORTB_EN", "GND")
    r(s, "0R", "PDB_GPIO3", "PORTB_EN", dnp=True)
    r(s, "10k", "PDB_LDO3V3", "PDB_IRQC")
    r(s, "3k3", "PDB_LDO3V3", "PDB_SDAC")
    r(s, "3k3", "PDB_LDO3V3", "PDB_SCLC")
    r(s, "0R", "PDB_ADC1", "GND")
    r(s, "0R", "PDB_ADC2", "GND")
    r(s, "100k", "PDB_LD1", "GND")
    r(s, "100k", "PDB_LD2", "GND")
    c(s, "10u", "+3V3", "GND")
    c(s, "10u", "PDB_LDO3V3", "GND")
    c(s, "100n", "PDB_LDO3V3", "GND")
    c(s, "10u", "PDB_LDO1V5", "GND")
    c(s, "10u", "+5V", "GND")
    two(s, "Device:C_Polarized", "C", "CP100u10", "+5V", "GND", value="100u 10V")
    c(s, "10u50", "VBUS_B", "GND")
    c(s, "100n50", "VBUS_B", "GND")
    c(s, "220p", "B_CC1", "GND")
    c(s, "220p", "B_CC2", "GND")
    two(s, "Device:D_TVS", "D", "TVS24", "VBUS_B", "GND")
    two(s, "Device:D_TVS", "D", "ESD24", "B_CC1", "GND")
    two(s, "Device:D_TVS", "D", "ESD24", "B_CC2", "GND")
    s.lane(350, 40, cols=1, dy=7.62)
    for net in ("VBUS_B", "VPB", "PDB_SDAC", "PDB_SCLC", "PDB_LDO3V3", "B_DP", "B_DN", "B_CC1", "B_CC2"):
        tp(s, net)
    s.lane(390, 40, cols=1, dy=15.24)
    for net in ("VBUS_B", "VPB", "PB_MID"):
        s.flag(net)

    # ------------------------------------------------------------------------------------------ 4 rails
    s = d.sheet("rails", "3.3 V, 5 V and the motor rail")
    s.note(20, 20, "3.3 V logic rail: TPS62932, 500 kHz (RT open), always on.", 1.6)
    ic(s, "Regulator_Switching:TPS62932", "U", "TPS62932",
       {"RT": NC, "EN": NC, "VIN": "VSYS", "GND": "GND", "SW": "SW_3V3", "BST": "BST_3V3", "SS": "SS_3V3", "FB": "FB_3V3"}, 60, 45)
    s.lane(110, 30, cols=3)
    two(s, "Device:L", "L", "L6u8", "SW_3V3", "+3V3", value="6u8")
    c(s, "100n", "BST_3V3", "SW_3V3")
    c(s, "22n", "SS_3V3", "GND")
    r(s, "31k6", "+3V3", "FB_3V3")
    r(s, "10k", "FB_3V3", "GND")
    c(s, "22u", "VSYS", "GND")
    c(s, "100n50", "VSYS", "GND")
    c(s, "22u", "+3V3", "GND")
    c(s, "22u", "+3V3", "GND")

    s.note(20, 78, "5 V rail for PP5V of both PD controllers (5 V / 3 A on port B, cable supply): TPS563201, always on. Pending approval, Q24.", 1.6)
    ic(s, "Regulator_Switching:TPS563201", "U", "TPS563201",
       {"GND": "GND", "SW": "SW_5V", "VIN": "VSYS", "VFB": "FB_5V", "EN": "EN_5V", "VBST": "BST_5V"}, 60, 100)
    s.lane(110, 88, cols=3)
    two(s, "Device:L", "L", "L4u7", "SW_5V", "+5V", value="4u7")
    c(s, "100n", "BST_5V", "SW_5V")
    r(s, "100k", "VSYS", "EN_5V")
    r(s, "54k9", "+5V", "FB_5V")
    r(s, "10k", "FB_5V", "GND")
    c(s, "22u", "VSYS", "GND")
    c(s, "100n50", "VSYS", "GND")
    c(s, "22u", "+5V", "GND")
    c(s, "22u", "+5V", "GND")

    s.note(20, 138, "Motor rail: Q6 switches the system rail to the boost with a soft start (MOTOR_PWR_EN); TPS61288 makes 10 V (VM_SEL low) or 16 V (VM_SEL high).\n"
                    "BOOST_EN, VM_SEL and MOTOR_PWR_EN come from the RP2354A and are pulled low, so the motor rail is off until the firmware turns it on.", 1.6)
    ic(s, "ST:PMOS_DFN33", "Q", "PFET", {"G": "MSW_G", "D": "VM_IN", "S": "VSYS"}, 45, 170)
    fp, f = cat.fields("P", "NFET_S")
    s.part("ST:NMOS_SOT23", ref("Q"), "2N7002", fp, {"G": "MOTOR_PWR_EN", "D": "MSW_D", "S": "GND"}, x=45, y=205, **f)
    ic(s, "ST:TPS61288", "U", "TPS61288",
       {"VIN": "VM_IN", "EN": "BOOST_EN", "VCC": "BST_VCC", "COMP": "BST_COMP", "FB": "BST_FB", "AGND": "GND", "SW": "BST_SW", "BST": "BST_BT",
        "VOUT": "VMOT", "PGND": "GND"}, 120, 175)
    s.part("ST:NMOS_SOT23", ref("Q"), "2N7002", fp, {"G": "VM_SEL", "D": "VMSEL_D", "S": "GND"}, x=120, y=215, **f)
    s.lane(180, 150, cols=5)
    r(s, "100k", "VSYS", "MSW_G")
    r(s, "10k", "MSW_G", "MSW_D")
    two(s, "Device:D_Zener", "D", "ZENER12", "VSYS", "MSW_G")
    c(s, "100n50", "MSW_G", "VM_IN")
    r(s, "100k", "MOTOR_PWR_EN", "GND")
    two(s, "Device:L", "L", "L4u7", "VM_IN", "BST_SW", value="4u7")
    c(s, "100n50", "BST_BT", "BST_SW")
    c(s, "2u2", "BST_VCC", "GND")
    r(s, "84k5", "BST_COMP", "BST_COMP_C")
    c(s, "15n", "BST_COMP_C", "GND")
    c(s, "39p", "BST_COMP", "GND")
    r(s, "365k", "VMOT", "BST_FB")
    c(s, "27p", "VMOT", "BST_FB")
    r(s, "23k2", "BST_FB", "GND")
    r(s, "36k5", "BST_FB", "VMSEL_D")
    r(s, "100k", "VM_SEL", "GND")
    r(s, "100k", "BOOST_EN", "GND")
    for _ in range(2):
        c(s, "22u", "VM_IN", "GND")
    for _ in range(3):
        c(s, "22u", "VMOT", "GND")
    c(s, "100n50", "VMOT", "GND")
    for _ in range(2):
        two(s, "Device:C_Polarized", "C", "CP100u25", "VMOT", "GND", value="100u 25V")
    r(s, "100k", "VMOT", "VMOT_MON")
    r(s, "15k", "VMOT_MON", "GND")
    c(s, "100n", "VMOT_MON", "GND")
    s.lane(350, 30, cols=1, dy=7.62)
    for net in ("+3V3", "+5V", "VM_IN", "VMOT", "GND", "GND"):
        tp(s, net)
    s.lane(390, 30, cols=1, dy=15.24)
    for net in ("+3V3", "+5V", "VM_IN"):
        s.flag(net)

    # ------------------------------------------------------------------------------------------ 5 processors
    s = d.sheet("mcu", "ESP32-S3 (connectivity) and RP2354A (motion)")
    s.note(20, 20, "ESP32-S3-WROOM-1-N16R8: Wi-Fi, BLE, USB, apps. Programs the RP2354A over SWD (IO38-IO40). J5: Tag-Connect for the ESP32 console.", 1.6)
    pins = {"GND": "GND", "3V3": "+3V3", "EN": "ESP_EN"}
    pins.update(ESP)
    ic(s, "RF_Module:ESP32-S3-WROOM-1", "U", "ESP32", pins, 70, 90)
    s.note(165, 30, "RP2354A: three PIO step trains, encoder SPI, driver UART. 12 MHz crystal, core supply 1.1 V from its own regulator. J6: Tag-Connect SWD.", 1.6)
    pins = {"IOVDD": "+3V3", "DVDD": "+1V1", "XIN": "RP_XIN", "XOUT": "RP_XOUT", "SWCLK": "RP_SWCLK", "SWDIO": "RP_SWDIO", "RUN": "RP_RUN",
            "ADC_AVDD": "+3V3A", "VREG_AVDD": "RP_AVDD", "VREG_PGND": "GND", "VREG_LX": "RP_LX", "VREG_VIN": "+3V3", "VREG_FB": "+1V1",
            "USB_DM": "RP_USB_DM", "USB_DP": "RP_USB_DP", "USB_OTP_VDD": "+3V3", "QSPI_IOVDD": "+3V3", "QSPI_SD3": NC, "QSPI_SCLK": NC,
            "QSPI_SD0": NC, "QSPI_SD2": NC, "QSPI_SD1": NC, "~{QSPI_SS}": "RP_BOOTSEL", "GND": "GND"}
    pins.update(RP)
    ic(s, "MCU_RaspberryPi:RP2354A", "U", "RP2354A", pins, 245, 110)
    fp, f = cat.fields("P", "XTAL12")
    s.part("Device:Crystal_GND24", ref("Y"), "12 MHz", fp, {1: "RP_XIN", 3: "RP_XOUT_X", "G": "GND"}, x=330, y=60, **f)
    tc = "Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical"
    s.part("Connector_Generic:Conn_02x03_Odd_Even", ref("J"), "TC2030 ESP32", tc,
           {1: "+3V3", 2: "ESP_EN", 3: "ESP_TXD0", 4: "ESP_RXD0", 5: "GND", 6: "ESP_IO0"}, x=40, y=180, bom=False)
    s.part("Connector_Generic:Conn_02x03_Odd_Even", ref("J"), "TC2030 RP2354", tc,
           {1: "+3V3", 2: "RP_SWDIO", 3: "RP_RUN", 4: "RP_SWCLK", 5: "GND", 6: "LINK_RX"}, x=90, y=180, bom=False)
    s.lane(25, 210, cols=8, dx=45.72)
    c(s, "22u", "+3V3", "GND")
    c(s, "100n", "+3V3", "GND")
    r(s, "10k", "+3V3", "ESP_EN")
    c(s, "1u", "ESP_EN", "GND")
    r(s, "10k", "+3V3", "ESP_IO0")
    r(s, "2k2", "+3V3", "I2C_SDA")
    r(s, "2k2", "+3V3", "I2C_SCL")
    r(s, "10k", "+3V3", "PWR_IRQ_N")
    r(s, "10k", "+3V3", "WAKE_IRQ_N")
    r(s, "100R", "SWCLK_E", "RP_SWCLK")
    r(s, "100R", "SWDIO_E", "RP_SWDIO")
    r(s, "10k", "+3V3", "RP_RUN")
    r(s, "1k", "RP_XOUT", "RP_XOUT_X")
    c(s, "27p", "RP_XIN", "GND")
    c(s, "27p", "RP_XOUT_X", "GND")
    two(s, "Device:L", "L", "L3u3", "RP_LX", "+1V1", value="3u3")
    c(s, "4u7", "+3V3", "GND")
    r(s, "33R", "+3V3", "RP_AVDD")
    c(s, "4u7", "RP_AVDD", "GND")
    for _ in range(2):
        c(s, "4u7", "+1V1", "GND")
    for _ in range(3):
        c(s, "100n", "+1V1", "GND")
    for _ in range(8):
        c(s, "100n", "+3V3", "GND")
    two(s, "Device:FerriteBead", "FB", "FB", "+3V3", "+3V3A")
    c(s, "1u", "+3V3A", "GND")
    c(s, "100n", "+3V3A", "GND")
    r(s, "1k", "LED_RP", "LED_RP_A")
    two(s, "Device:LED", "D", "LED_G", "GND", "LED_RP_A", value="green")
    r(s, "1k", "TMC_TX", "TMC_UART")
    r(s, "10k", "+3V3", "DRV_EN_N")
    r(s, "1k", "RP_BOOTSEL", "BOOTSEL_PAD")
    s.lane(380, 40, cols=1, dy=7.62)
    for net in ("+1V1", "+3V3A", "I2C_SDA", "I2C_SCL", "LINK_TX", "LINK_RX", "LINK_SYNC", "TMC_UART", "ENC_SCK_M", "ENC_MOSI_M", "ENC_MISO",
                "GNSS_PPS", "RP_USB_DM", "RP_USB_DP", "BOOTSEL_PAD", "IMU_INT", "ESP_IO45", "PWR_IRQ_N", "WAKE_IRQ_N"):
        tp(s, net)
    s.lane(350, 150, cols=1, dy=15.24)
    for net in ("+1V1", "+3V3A", "RP_AVDD"):
        s.flag(net)

    # ------------------------------------------------------------------------------------------ 6 drivers
    s = d.sheet("drivers", "Stepper drivers and cartridge plugs")
    s.note(20, 16, "Three TMC2209-LA on one UART (addresses 0, 1, 2). Sense resistors 0.15 ohm: 1.35 A RMS full scale. VREF strap gives 0.34 A if a driver is "
                   "enabled before set-up.\nCartridge plugs J7 (azimuth), J8 (altitude), J9 (roll), JST-GH 15-way: 1-2 A1, 3-4 A2, 5 GND, 6 CS, 7 SCK, 8 MOSI, 9 MISO, 10 NTC, 11 3V3, 12-13 B1, 14-15 B2.", 1.6)
    for i, (ax, addr) in enumerate(AXES):
        x0 = 30 + i * 135
        ic(s, "Driver_Motor:TMC2209-LA", "U", "TMC2209",
           {"OB2": f"{ax}_B2", "~{EN}": "DRV_EN_N", "GND": "GND", "CPO": f"{ax}_CPO", "CPI": f"{ax}_CPI", "VCP": f"{ax}_VCP", "SPREAD": "GND",
            "5VOUT": f"{ax}_5V", "MS1/AD0": "+3V3" if addr & 1 else "GND", "MS2/AD1": "+3V3" if addr & 2 else "GND", "DIAG": f"DIAG_{ax}",
            "INDEX": NC, "CLK": "GND", "~{PD}/UART": "TMC_UART", "VCC_IO": "+3V3", "STEP": f"STEP_{ax}", "VREF": f"{ax}_VREF", "DIR": f"DIR_{ax}",
            "STDBY": "GND", "OA2": f"{ax}_A2", "VS": "VMOT", "BRA": f"{ax}_BRA", "OA1": f"{ax}_A1", "NC": NC, "OB1": f"{ax}_B1", "BRB": f"{ax}_BRB"},
           x0 + 45, 70)
        fp, f = cat.fields("P", "GH15V")
        s.part("Connector_Generic_MountingPin:Conn_01x15_MountingPin", ref("J"), cat.PART["GH15V"][1], fp,
               {1: f"{ax}_A1", 2: f"{ax}_A1", 3: f"{ax}_A2", 4: f"{ax}_A2", 5: "GND", 6: f"{ax}_CS", 7: f"{ax}_SCK", 8: f"{ax}_MOSI", 9: "ENC_MISO",
                10: f"NTC_{ax}", 11: f"{ax}_3V3", 12: f"{ax}_B1", 13: f"{ax}_B1", 14: f"{ax}_B2", 15: f"{ax}_B2", "MP": "GND"}, x=x0 + 20, y=150, **f)
        ic(s, "Power_Protection:SRV05-4", "U", "SRV05",
           {"IO1": f"{ax}_CS", "IO2": f"{ax}_SCK", "IO3": f"{ax}_MOSI", "IO4": "ENC_MISO", "VP": f"{ax}_3V3", "VN": "GND"}, x0 + 85, 150)
        s.lane(x0, 195, cols=3, dx=44.45)
        r(s, "0R15", f"{ax}_BRA", "GND")
        r(s, "0R15", f"{ax}_BRB", "GND")
        c(s, "22n", f"{ax}_CPO", f"{ax}_CPI")
        c(s, "100n50", f"{ax}_VCP", "VMOT")
        c(s, "2u2", f"{ax}_5V", "GND")
        r(s, "33k", f"{ax}_5V", f"{ax}_VREF")
        r(s, "4k7", f"{ax}_VREF", "GND")
        c(s, "100n", "+3V3", "GND")
        c(s, "100n50", "VMOT", "GND")
        c(s, "100n50", "VMOT", "GND")
        c(s, "22u", "VMOT", "GND")
        r(s, "33R", f"CS_{ax}_M", f"{ax}_CS")
        r(s, "33R", "ENC_SCK_M", f"{ax}_SCK")
        r(s, "33R", "ENC_MOSI_M", f"{ax}_MOSI")
        two(s, "Device:FerriteBead", "FB", "FB", "+3V3", f"{ax}_3V3")
        c(s, "100n", f"{ax}_3V3", "GND")
        r(s, "10k", "+3V3A", f"NTC_{ax}")
        r(s, "1k", f"NTC_{ax}", f"NTC_{ax}_A")
        c(s, "100n", f"NTC_{ax}_A", "GND")
        tp(s, f"NTC_{ax}_A")

    # ------------------------------------------------------------------------------------------ 7 sensors and user interface
    s = d.sheet("ui", "Sensors, GNSS, display, buttons, LED, shutter")
    s.note(20, 16, "I2C bus (ESP32 IO8 / IO9, 400 kHz): OLED 0x3C, IMU 0x6A, magnetometer 0x30, clock 0x52, port A 0x20, port B 0x21.", 1.6)
    ic(s, "ST:LSM6DSV", "U", "LSM6DSV",
       {"SDO/SA0": "GND", "SDX": "GND", "SCX": "GND", "INT1": "IMU_INT", "VDDIO": "+3V3", "GND": "GND", "VDD": "+3V3", "INT2": NC, "NC": NC,
        "CS": "+3V3", "SCL": "I2C_SCL", "SDA": "I2C_SDA"}, 50, 50)
    ic(s, "ST:MMC5983MA", "U", "MMC5983MA",
       {"VDD": "+3V3", "VDDIO": "+3V3", "CAP": "MAG_CAP", "GND": "GND", "SCL": "I2C_SCL", "SDA": "I2C_SDA", "SPI_CS": "+3V3", "SPI_SDO": NC, "INT": NC,
        "NC": NC}, 115, 50)
    fp, f = cat.fields("P", "RV3028")
    s.part("Timer_RTC:RV-3028-C7", ref("U"), "RV-3028-C7", None,
           {"CLKOUT": NC, "~{INT}": "WAKE_IRQ_N", "SCL": "I2C_SCL", "SDA": "I2C_SDA", "VSS": "GND", "VBACKUP": "RTC_VBAK", "VDD": "+3V3", "EVI": "GND"},
           x=180, y=50, **f)
    fp, f = cat.fields("P", "MAXM10S")
    s.part("RF_GPS:MAX-M10S", ref("U"), "MAX-M10S", None,
           {"GND": "GND", "TXD": "GNSS_TXD", "RXD": "GNSS_RXD", "TIMEPULSE": "GNSS_PPS", "EXTINT": NC, "V_BCKP": "+3V3G", "VCC_IO": "+3V3G",
            "VCC": "+3V3G", "~{RESET}": "GNSS_RST", "RF_IN": "GNSS_RF", "LNA_EN": NC, "VCC_RF": "GNSS_VRF", "VIO_SEL": NC, "SDA": NC, "SCL": NC,
            "~{SAFEBOOT}": "GNSS_SAFE"}, x=265, y=55, **f)
    fp, f = cat.fields("P", "UFL")
    s.part("Connector:Conn_Coaxial", ref("J"), "U.FL GNSS", fp, {"In": "GNSS_ANT", "Ext": "GND"}, x=335, y=50, **f)
    s.lane(25, 95, cols=8, dx=45.72)
    c(s, "100n", "+3V3", "GND")
    c(s, "100n", "+3V3", "GND")
    c(s, "1u", "+3V3", "GND")
    c(s, "10u", "MAG_CAP", "GND")
    c(s, "100n", "+3V3", "GND")
    fp, f = cat.fields("P", "RTCBAT")
    s.part("Device:Battery_Cell", ref("BT"), "MS621FE", fp, {"+": "RTC_VBAK", "-": "GND"}, **f)
    two(s, "Device:FerriteBead", "FB", "FB", "+3V3", "+3V3G")
    c(s, "10u", "+3V3G", "GND")
    c(s, "100n", "+3V3G", "GND")
    c(s, "47p", "GNSS_ANT", "GNSS_RF")
    two(s, "Device:L", "L", "L47n", "GNSS_BIAS", "GNSS_ANT", value="47n")
    r(s, "10R", "GNSS_VRF", "GNSS_BIAS")
    c(s, "10n", "GNSS_BIAS", "GND")

    s.note(20, 122, "OLED 1.3 in SH1106 module on a 4-pin header (J11). R fitted for modules marked VCC-GND-SCL-SDA; swap to the two unfitted ones for GND-VCC.", 1.6)
    s.part("Connector_Generic:Conn_01x04", ref("J"), "OLED 1.3in SH1106", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
           {1: "OLED_P1", 2: "OLED_P2", 3: "I2C_SCL", 4: "I2C_SDA"}, x=35, y=140, bom=False)
    s.lane(70, 132, cols=4)
    r(s, "0R", "+3V3", "OLED_P1")
    r(s, "0R", "OLED_P2", "GND")
    r(s, "0R", "OLED_P1", "GND", dnp=True)
    r(s, "0R", "+3V3", "OLED_P2", dnp=True)

    s.note(20, 162, "Buttons (to ground, 10 k pull-up, 100 nF), status LEDs behind one light pipe, RP2354A heartbeat LED is on the MCU sheet.", 1.6)
    for i in range(4):
        fp, f = cat.fields("P", "TACT")
        s.part("Switch:SW_Push", ref("SW"), "TS-1187A", fp, {1: f"BTN{i + 1}", 2: "GND"}, x=35 + i * 40, y=178, **f)
    s.lane(25, 195, cols=8, dx=45.72)
    for i in range(4):
        r(s, "10k", "+3V3", f"BTN{i + 1}")
        c(s, "100n", f"BTN{i + 1}", "GND")
    for col, key, val in (("R", "LED_R", "red"), ("G", "LED_G", "green"), ("B", "LED_B", "blue")):
        r(s, "1k", f"LED_{col}", f"LED_{col}_A")
        two(s, "Device:LED", "D", key, "GND", f"LED_{col}_A", value=val)

    s.note(200, 122, "Shutter port J12 (to the 2.5 mm jack on the bezel): tip = shutter, ring = focus, sleeve = camera ground. Isolated from the head by U25-U26.", 1.6)
    ic(s, "Isolator:TLP291", "U", "TLP291", {1: "OPT_F_A", 2: "GND", 3: "SH_SLEEVE", 4: "SH_RING"}, 225, 142)
    ic(s, "Isolator:TLP291", "U", "TLP291", {1: "OPT_S_A", 2: "GND", 3: "SH_SLEEVE", 4: "SH_TIP"}, 275, 142)
    fp, f = cat.fields("P", "GH3H")
    s.part("Connector_Generic_MountingPin:Conn_01x03_MountingPin", ref("J"), cat.PART["GH3H"][1], fp,
           {1: "SH_TIP", 2: "SH_RING", 3: "SH_SLEEVE", "MP": "GND"}, x=335, y=142, **f)
    s.lane(210, 165, cols=4)
    r(s, "330R", "SHUT_FOCUS", "OPT_F_A")
    r(s, "330R", "SHUT_REL", "OPT_S_A")
    two(s, "Device:D_TVS", "D", "ESD5", "SH_TIP", "SH_SLEEVE")
    two(s, "Device:D_TVS", "D", "ESD5", "SH_RING", "SH_SLEEVE")
    s.lane(380, 80, cols=1, dy=7.62)
    for net in ("GNSS_RST", "GNSS_SAFE", "GNSS_TXD", "GNSS_RXD", "RTC_VBAK"):
        tp(s, net)
    for i in range(4):
        s.part("Mechanical:MountingHole", f"H{i + 1}", "M3", "ST:MountingHole_3.2mm_M3_ISO7380", {}, x=300 + i * 20, y=250)
    s.lane(380, 150, cols=1, dy=15.24)
    for net in ("+3V3G", "RTC_VBAK"):
        s.flag(net)
    return d


# ----------------------------------------------------------------------------------------------------------------------
# Layout. Coordinates: seen from the front (the bezel side), X right, Y up, origin at the board centre.
# The Phase 3 CAD uses (Y - 15, Z - 86) with +Y to the left in this view, so x = -(Y - 15), y = Z - 86.
# F = front face (OLED, buttons, USB-C, LEDs), B = inner face (everything else, up to 12 mm tall).
# ----------------------------------------------------------------------------------------------------------------------
FIXED = {
    # front face, positions set by the bezel openings
    "J11": (-3.81, 27.9, 90, "F"), "SW1": (3, -18, 0, "F"), "SW2": (14, -18, 0, "F"), "SW3": (25, -18, 0, "F"), "SW4": (36, -18, 0, "F"),
    "J3": (-25, -15.35, 0, "F"), "J4": (-38, -15.35, 0, "F"), "D11": (-37.5, 19.5, 0, "F"), "D12": (-37.5, 21.0, 0, "F"),
    "D13": (-37.5, 18.0, 0, "F"), "H1": (-46, 26, 0, "F"), "H2": (46, 26, 0, "F"), "H3": (-46, -26, 0, "F"), "H4": (46, -26, 0, "F"),
    # inner face: cartridge plugs and drivers
    "J7": (29.5, 25.5, 0, "B"), "J8": (29.5, 18.4, 0, "B"), "J9": (29.5, 11.3, 0, "B"),
    "U15": (10.5, 25.3, 270, "B"), "U17": (10.5, 15.9, 270, "B"), "U19": (10.5, 6.5, 270, "B"),
    # processors
    "U13": (-6.0, -17.2, 180, "B"), "U14": (17.0, -6.5, 0, "B"),
    # battery input: the TVS diode back to back with the lead pads
    "J1": (38.3, -25.5, 0, "B"), "Q1": (29.8, -25.5, 0, "B"), "D2": (38.65, -25.5, 180, "F"),
    # motor rail: the coil right under the boost converter's switch pin, the switch transistor and the input capacitors at
    # the coil's other pad
    "U12": (33.5, -13.0, 0, "B"), "L5": (36.52, -18.6, 0, "B"), "Q6": (45.7, -19.9, 0, "B"), "C71": (42.0, -17.05, 270, "B"),
    "C72": (42.0, -17.05, 90, "F"), "C77": (45.0, -6.5, 90, "B"), "C78": (45.0, 3.3, 90, "B"),
    # charger, laid out as TI's reference: the coil above the SW1 / SW2 pins, the PMID capacitors on a bar to the right of
    # them, the input (VBUS) capacitors right of the VBUS pins, the battery capacitors left of the BAT pins
    "U2": (-24.0, 6.5, 0, "B"), "L1": (-23.5, 12.55, 0, "B"),
    "C12": (-18.35, 9.9, 270, "B"), "C9": (-16.45, 10.775, 270, "B"), "C10": (-21.3, 10.775, 90, "F"), "C11": (-18.9, 10.775, 90, "F"),
    "C6": (-19.125, 5.6, 180, "B"), "C7": (-19.125, 5.6, 0, "F"), "C8": (-18.32, 7.6, 180, "B"), "C19": (-17.3, -0.4, 180, "B"),
    "C17": (-30.45, 7.7, 0, "B"), "C18": (-30.45, 7.7, 180, "F"),
    "C2": (-23.1, 8.3, 90, "F"), "C3": (-25.5, 8.3, 90, "F"), "C4": (-22.9, 4.9, 270, "F"),
    "R9": (-27.41, 6.25, 0, "B"), "R15": (-28.9, 5.25, 180, "B"),
    # port A: the controller turned so that its two power pins face east: PPHV (to the charger) above VBUS (to the socket)
    "U3": (-25.0, -6.0, 180, "B"), "D3": (-29.75, -21.6, 180, "F"), "U4": (-33.5, -5.2, 90, "B"),
    "C20": (-28.175, -10.3, 180, "F"), "C44": (-38.6, -0.075, 90, "F"),
    # port B converter, laid out as TI's reference: the two external FETs on the gate-drive side of the chip with their
    # drains (Q4) and sources (Q5) toward the input capacitors, the coil above the chip between the SW1 and SW2 pins,
    # the output capacitors and the sense resistor R23 right below the VOUT pins
    "U7": (-30.0, 17.5, 0, "B"), "L2": (-30.5, 25.2, 0, "B"), "Q4": (-23.3, 25.0, 180, "B"), "Q5": (-23.3, 20.8, 0, "B"),
    "C29": (-29.0, 20.73, 270, "B"), "C30": (-31.8, 20.73, 270, "B"), "C42": (-30.27, 14.75, 180, "B"), "C39": (-30.3, 13.3, 180, "B"),
    "C40": (-30.3, 11.2, 180, "B"), "C41": (-30.3, 13.3, 0, "F"), "R23": (-34.55, 14.4, 0, "B"),
    "C38": (-20.7, 23.12, 90, "B"), "C35": (-19.25, 22.9, 90, "B"), "C36": (-19.25, 22.9, 270, "F"), "C37": (-21.3, 22.9, 270, "F"),
    # port B controller and its output switch: Q2 (from the converter) above Q3 (to the socket) at the board edge, drains
    # together, 3.6 mm west of the controller's pins so that every one of them has room for its via
    "U6": (-40.0, -5.5, 0, "B"), "Q2": (-47.3, -2.0, 90, "B"), "Q3": (-47.3, -6.6, 270, "B"), "C43": (-47.05, 1.6, 180, "B"),
    "C50": (-46.9, -11.225, 90, "B"), "D6": (-40.2, -22.3, 270, "F"), "C49": (-37.25, 2.6, 0, "B"), "U8": (-41.0, 21.0, 0, "B"),
    # shutter opto-coupler on the front face, right behind the shutter plug J12
    "U26": (-47.5, -18.5, 90, "F"),
    # 5 V and 3.3 V rails
    "U11": (-15.5, 19.6, 0, "B"), "L4": (-11.6, 26.2, 0, "B"), "C63": (-17.1, 24.9, 90, "B"), "C64": (-17.1, 24.9, 270, "F"),
    "U10": (-7.5, 12.5, 0, "B"), "L3": (-11.9, 9.0, 0, "B"),
    # sensors
    "U24": (0.4, 1.7, 0, "B"), "U21": (-9.0, 0.0, 0, "B"), "U22": (-2.5, 20.5, 0, "B"), "U23": (-11.5, 4.3, 0, "B"),
    # GNSS antenna socket (its footprint carries a no-copper area that the small parts must stay out of)
    "J10": (-0.025, 10.65, 180, "B"),
    "J2": (13.4, -20.5, 180, "B"), "J12": (-45.5, -20.0, 90, "B"), "J5": (22.0, -21.5, 0, "B"), "J6": (22.0, -27.0, 0, "B"),
}
JACK = (-41.0, 11.0, 4.5)     # cut-out for the panel-mount 2.5 mm jack that sits in the bezel


def layout(pcb):
    import math
    pcb.outline_rect(100.0, 60.0, r=1.0)
    pcb.outline_circle(JACK[2], JACK[0], JACK[1])
    pcb.bounds = (-49.4, -29.4, 49.4, 29.4)
    pcb.block("*", (JACK[0] - JACK[2] - 0.6, JACK[1] - JACK[2] - 0.6, JACK[0] + JACK[2] + 0.6, JACK[1] + JACK[2] + 0.6))
    for ref, (x, y, rot, side) in FIXED.items():
        pcb.place(ref, x, y, rot=rot, side=side, ref_text=False)
    import pcbnew
    for pad in pcb.fps["U3"].Pads():          # the package's own gap between the wide pads 20 and 23 is 0.12 mm
        if pad.GetNumber() in ("20", "23"):
            pad.SetLocalClearance(pcbnew.FromMM(0.1))
    # sense resistors between each driver and its plug, right at the BRA / BRB pins
    for (ax, _a), drv in zip(AXES, ("U15", "U17", "U19")):
        x, y = FIXED[drv][0], FIXED[drv][1]
        for net, dy in ((f"{ax}_BRA", 2.35), (f"{ax}_BRB", -2.35)):
            rr = [r_ for (r_, _p), n_ in pcb.netmap.items() if n_ == net and r_.startswith("R")][0]
            pcb.place(rr, x + 5.25, y + dy, rot=90, side="B", ref_text=False)
    # ESP32 antenna: nothing under the last 6 mm of the module and 15 mm either side (its footprint carries the keep-out zone)
    pcb.block("*", ANT)
    for (ax, ay), (bx, by) in zip(VBAT_BUS, VBAT_BUS[1:]):          # no parts on the front face where the battery bus runs
        h = VBAT_BUS_W / 2 + 0.3
        pcb.block("F", (min(ax, bx) - h, min(ay, by) - h, max(ax, bx) + h, max(ay, by) + h))
    pcb.keepout(["F", "B", "In1", "In2", "In3", "In4"], pcb.rect(*ANT), tracks=True, vias=True, copper=True)
    # no small parts on the copper areas of the power paths, nor on the tracks and vias laid by hand
    for _net, face, poly, _sp, _k in AREAS:
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        pcb.block(face, (min(xs) - 0.25, min(ys) - 0.25, max(xs) + 0.25, max(ys) + 0.25))
    hand(pcb)
    # the places where the USB data vias were before they moved into the socket pads stay closed to parts: the routed
    # tracks of 23 Nov were laid for this placement (C26, C27, R16 and U9 move otherwise)
    for x_ in (0.0, -13.0):
        for vx, vy in ((-25.41, -13.3), (-24.62, -12.75), (-24.62, -17.4), (-25.41, -17.95)):
            x, y = pcb.pt((vx + x_, vy))
            pcb.block("*", (x - 0.7, y - 0.7, x + 0.7, y + 0.7))
    pcb.block("*", (-1.3, 9.4, 1.4, 11.9))                     # the no-copper area under the antenna socket J10
    # room for every pin of the fine-pitch chips to get out: a band round each of them stays free of other parts
    for ref, w in (("U2", 1.8), ("U3", 2.4), ("U6", 2.4), ("U7", 1.5), ("U12", 1.5), ("U14", 3.2), ("U15", 2.0), ("U17", 2.0), ("U19", 2.0),
                   ("U13", 1.3), ("U24", 1.2), ("U21", 1.0), ("U22", 1.0), ("U10", 0.7), ("U11", 0.7)):
        pcb.escape_ring(ref, w)
    own, rank = owners(pcb)
    for p in pcb.model["parts"]:
        if p["ref"] in own:
            p["owner"] = own[p["ref"]]
    order = [p["ref"] for p in pcb.model["parts"] if p["ref"] not in FIXED and p["ref"] not in pcb.fps]
    # each part goes beside the pin of the chip it serves; the parts in a converter's switching loop and the ones on a
    # chip's own small nets (boot, charge pump, regulator output, feedback) are placed before the rail capacitors and
    # pull-ups, test points last
    order.sort(key=lambda r: rank[r])
    failed = pcb.autoplace(order)
    if failed:
        print("AUTOPLACE FAILED:", " ".join(failed))

    # net classes. The widths are what still fits between 0.4 mm-pitch pins; the current itself is carried by the copper
    # areas that finish() lays over every power net (outer layers) and by the inner planes.
    pcb.netclass("Power", 0.3, POWER_NETS)
    pcb.netclass("Phase", 0.3, PHASE_NETS)
    pcb.netclass("Supply", 0.2, ["+3V3", "+3V3A", "+3V3G", "+1V1", "PDA_LDO3V3", "PDB_LDO3V3", "CHG_REGN", "PB_VCC", "BST_VCC", "RP_LX"]
                 + [f"{ax}_{p_}" for ax, _a in AXES for p_ in ("3V3", "5V")])
    pcb.sync_classes()
    # Six layers (decision D51): F signal, In1 power, In2 and In3 signal, In4 ground, B signal. The inner face (B) carries
    # the converters and nearly all parts, so the ground plane is the layer next to it.
    pcb.plane_layer("In1")
    pcb.plane_layer("In4")
    # ground: the router puts a via to the In4 plane in or beside every ground pad (tools/grouter.py, first step of the plan)
    pcb.zone("GND", "In4", pcb.rect(-49.5, -29.5, 49.5, 29.5), clearance=0.2, solid=True)
    return pcb


# Which chip a small part belongs to, where the schematic order does not say it.
OWNER = {
    # port B buck-boost: input capacitors at the external half bridge, output capacitors and sense resistor at the chip
    "C35": "Q4", "C36": "Q4", "C37": "Q4", "C38": "Q4", "C13": "U2", "C14": "U2", "C15": "U2", "C16": "U2",
    # battery input: TVS and gate parts at the reverse-polarity FET
    "D1": "Q1", "D2": "Q1", "D3": "J3", "D6": "J4",
    "Q7": "Q6", "Q8": "U12", "L7": "J10", "C137": "J10",
}
# Placed first, chip by chip and net by net: the capacitors of each converter's switching loop, then its boot, bias and
# output capacitors. Within a net the 100 nF goes nearest the pin.
HOT = [("U2", ["CHG_PMID", "CHG_BT1", "CHG_BT2", "CHG_REGN", "VBUS_CHG", "VSYS", "VBAT"]),
       ("Q4", ["VSYS"]), ("U7", ["PB_BOOT1", "PB_BOOT2", "PB_VCC", "VPB_RAW", "VPB"]),
       ("U12", ["VMOT", "BST_BT", "BST_VCC", "VM_IN"]),
       ("U10", ["VSYS", "BST_3V3", "+3V3"]), ("U11", ["VSYS", "BST_5V", "+5V"]),
       ("U15", ["AZ_CPO", "AZ_VCP", "AZ_5V", "VMOT", "+3V3"]), ("U17", ["ALT_CPO", "ALT_VCP", "ALT_5V", "VMOT", "+3V3"]),
       ("U19", ["ROLL_CPO", "ROLL_VCP", "ROLL_5V", "VMOT", "+3V3"]),
       ("U14", ["+1V1", "RP_AVDD", "+3V3A", "RP_XIN", "RP_XOUT_X", "+3V3"]), ("U13", ["+3V3", "ESP_EN"]),
       ("U3", ["PDA_LDO3V3", "PDA_LDO1V5", "+5V", "VBUS_A", "+3V3"]), ("U6", ["PDB_LDO3V3", "PDB_LDO1V5", "+5V", "VBUS_B", "+3V3"]),
       ("Q1", ["VBAT_IN", "VBAT"]), ("Q6", ["VM_IN", "VSYS"])]


def owners(pcb):
    """ref -> the fixed part it is placed beside, and a placement rank for every part that is not fixed."""
    fan = pcb.fanout
    netpads = {}
    for (r_, pin), n_ in pcb.netmap.items():
        netpads.setdefault(n_, set()).add(r_)
    anchors = [r_ for r_ in FIXED if not r_.startswith("H")]

    parts = pcb.model["parts"]
    sheet = {p["ref"]: p["sheet"] for p in parts}
    # the transistors, inductors and crystal are placed first and then count as fixed parts for everything else
    anchors += [p["ref"] for p in parts if p["ref"] not in FIXED and p["ref"][0] in "QLY" and "0402" not in p["footprint"]]

    def weight(r_, sh=None):
        return (sheet.get(r_) != sh, {"U": 0, "Q": 1, "L": 2, "Y": 2, "J": 3}.get(r_[0], 4))
    own = {}
    small = [p for p in parts if p["ref"] not in FIXED]
    for p in small:                               # 1. a net that is local to one fixed part
        if p["ref"] in anchors:
            continue
        nets = sorted({n_ for n_ in p["pins"].values() if n_ and n_ != "GND"}, key=lambda n_: (fan.get(n_, 99), n_))
        for n_ in nets:
            if fan.get(n_, 99) > 8:
                break
            cand = sorted((a for a in anchors if a in netpads.get(n_, ())), key=lambda a: (weight(a, p["sheet"]), a))
            if cand:
                own[p["ref"]] = cand[0]
                break
    for _ in range(4):                            # 2. through another small part on a local net
        for p in small:
            if p["ref"] in own:
                continue
            for n_ in sorted({n_ for n_ in p["pins"].values() if n_ and n_ != "GND"}, key=lambda n_: (fan.get(n_, 99), n_)):
                if fan.get(n_, 99) > 8:
                    break
                nb = [r_ for r_ in netpads.get(n_, ()) if r_ in own]
                if nb:
                    own[p["ref"]] = own[sorted(nb)[0]]
                    break
    last = {}
    for p in parts:                               # 3. rail capacitors and pull-ups: the chip whose parts they follow
        if p["ref"] in FIXED:
            if p["ref"][0] == "U" and p["sheet"] not in last:
                last[p["sheet"]] = p["ref"]
            continue
        if p["ref"] in own:
            if not p["ref"].startswith("TP") and own[p["ref"]][0] in "UQ":
                last[p["sheet"]] = own[p["ref"]]
        elif p["sheet"] in last:
            own[p["ref"]] = last[p["sheet"]]
    own.update(OWNER)

    hot = {o: (i, nets_) for i, (o, nets_) in enumerate(HOT)}

    def rank(p):
        ref = p["ref"]
        nets = [n_ for n_ in p["pins"].values() if n_ and n_ != "GND"]
        f = min([fan.get(n_, 99) for n_ in nets] or [99])
        local = sum(1 for n_ in nets if fan.get(n_, 99) <= 4)
        o = own.get(ref)
        if ref[0] == "C" and o in hot and any(n_ in hot[o][1] for n_ in nets):
            k = min(hot[o][1].index(n_) for n_ in nets if n_ in hot[o][1])
            return (0, hot[o][0], k, 0 if p["value"].startswith("100n") else 1)
        if ref.startswith("TP"):
            return (9, 0, 0, 0)
        if ref in anchors:
            return (-1, f, 0, 0)
        if ref[0] == "D" or ref.startswith(("FB", "BT", "J", "SW")):
            return (1, f, 0, 0)
        if ref[0] == "C" and local >= 2:
            return (2, f, 0, 0)                             # boot and charge-pump capacitors
        if ref[0] == "C" and f <= 4:
            return (3, f, 0, 0)                             # a chip's own regulator or reference capacitor
        if ref[0] == "C":
            return (4, 0 if "100n" in p["value"] else 1, 0, 0)
        return (5, f, 0, 0)
    return own, {p["ref"]: rank(p) for p in small}


POWER_NETS = ["VBAT", "VBAT_IN", "VSYS", "VM_IN", "VMOT", "VBUS_A", "VBUS_B", "VBUS_CHG", "VPB", "VPB_RAW", "PB_MID", "+5V",
              "CHG_SW1", "CHG_SW2", "CHG_PMID", "PB_SW1", "PB_SW2", "BST_SW", "SW_5V", "SW_3V3"]
PHASE_NETS = [f"{ax}_{p_}" for ax, _a in AXES for p_ in ("A1", "A2", "B1", "B2", "BRA", "BRB")]
POUR_NETS = ("GND",)
# The pins that carry the current of each power net and the copper width wanted between them (tools/pathwidth.py measures
# the narrowest place on the widest way, over tracks and filled areas together). The supply planes are not in this list.
POWER_PATHS = {
    "VBAT_IN": (["J1.1", "Q1.9"], 1.0),
    "CHG_SW1": (["U2.28", "L1.1"], 1.0), "CHG_SW2": (["U2.26", "L1.2"], 1.0), "CHG_PMID": (["U2.29", "C9.1", "C10.1", "C11.1"], 1.0),
    # U2 pins 2 and 3 are the charger's VBUS pins; pins 8 and 9 (VAC2, VAC1) only sense the voltage
    "VBUS_CHG": (["U3.20", "U2.2", "U2.3", "C19.1"], 1.0),
    # "~1.5": at this pin the wide copper may begin up to 1.5 mm away instead of 0.8 mm. The VBUS pins of the USB-C
    # sockets (0.3 mm wide) stand between the shell pins and the CC / data pins, which have to get out past them: the
    # row A pins reach the wide copper above the socket by a neck 1.7 mm long, the row B pins through the row A pin
    # opposite them ("~2.9"). Each pin carries a quarter of the port current, 0.75 A at 3 A.
    "VBUS_A": (["J3.A4~1.5", "J3.B9~2.9", "U3.23", "U3.32"], 1.0),
    # U7 pad 25 lies under the package and is reached through pin 21 only (0.25 mm wide, TI's own land pattern)
    "PB_SW1": (["Q4.1", "Q5.9", "L2.1"], 1.0), "PB_SW2": (["L2.2", "U7.21", "U7.25~1.1"], 1.0),
    "VPB_RAW": (["U7.11", "U7.12", "C39.1", "C40.1", "R23.1"], 1.0), "VPB": (["R23.2", "Q2.1", "C43.1"], 1.0),
    "PB_MID": (["Q2.9", "Q3.9"], 1.0), "VBUS_B": (["Q3.1", "J4.A4~1.5", "J4.B9~2.9", "C50.1"], 1.0),
    # U12 pin 7 (VIN) is the converter's own supply, a few milliamps: it is not a terminal of the power path
    "VM_IN": (["Q6.9", "L5.1", "C71.1", "C72.1"], 1.0), "BST_SW": (["U12.4", "L5.2"], 0.35),
    "SW_5V": (["U11.2", "L4.1"], 0.5), "+5V": (["L4.2", "C63.1", "U3.34", "U6.28"], 0.5), "SW_3V3": (["U10.5", "L3.1"], 0.5),
}


def _rect(net, face, x0, y0, x1, y1):
    """A rectangular copper area with its centre line; no other net's via within reach of the centre line."""
    w, h = x1 - x0, y1 - y0
    if w >= h:
        sp = [(x0 + h / 2, (y0 + y1) / 2), (x1 - h / 2, (y0 + y1) / 2)]
    else:
        sp = [((x0 + x1) / 2, y0 + w / 2), ((x0 + x1) / 2, y1 - w / 2)]
    if sp[0] == sp[1]:
        sp[1] = (sp[1][0] + 0.05, sp[1][1])
    return (net, face, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], sp, min(w, h) / 2 + 0.3)


# Copper areas of the power paths on the outer faces: net, face, outline, centre line, half width kept free of other
# nets' vias. No other net's track or via may lie in them (tools/grouter.py: hard region with a spine); finish() makes
# each one a filled zone. Built the way the battery board ST-602 was built.
AREAS = [
    # battery input: from the reverse-polarity FET's drain up and east over the minus pad to the plus pad
    ("VBAT_IN", "B", [(27.9, -26.7), (30.6, -26.7), (30.6, -22.75), (39.3, -22.75), (39.3, -23.3), (42.5, -23.3), (42.5, -21.5),
                      (29.0, -21.5), (29.0, -24.3), (27.9, -24.3)], [(28.5, -25.5), (29.8, -25.5), (29.8, -22.1), (41.0, -22.1), (41.0, -23.0)], 0.9),
    # charger: SW1 and SW2 straight up from their pins into the coil pads, PMID out to the right under the coil pad
    ("CHG_SW1", "B", [(-23.8, 8.95), (-23.27, 8.95), (-22.75, 9.47), (-22.75, 10.8), (-19.4, 10.8), (-19.4, 14.2), (-21.6, 14.2),
                      (-21.6, 12.2), (-23.8, 12.2)], [(-24.0, 9.25), (-23.4, 9.6), (-23.3, 11.5), (-20.5, 11.5), (-20.5, 13.6)], 0.6),
    ("CHG_SW2", "B", [(-25.25, 8.95), (-24.2, 8.95), (-24.2, 12.2), (-25.3, 12.2), (-25.3, 14.2), (-27.6, 14.2), (-27.6, 10.8),
                      (-25.25, 10.8)], [(-24.72, 9.5), (-24.72, 11.5), (-26.5, 11.5), (-26.5, 13.6)], 0.6),
    ("CHG_PMID", "B", [(-22.5, 8.7), (-15.3, 8.7), (-15.3, 9.9), (-22.5, 9.9)], [(-22.0, 9.3), (-15.9, 9.3)], 0.7),
    ("VBUS_CHG", "B", [(-21.55, 5.0), (-21.3, 5.0), (-21.3, 4.6), (-19.9, 4.6), (-19.9, 5.0), (-18.4, 5.0), (-18.4, 8.4), (-21.3, 8.4),
                       (-21.3, 7.6), (-21.55, 7.6)], [(-20.0, 5.6), (-20.0, 7.8)], 1.6),
    _rect("VBAT", "B", -30.1, 7.15, -26.45, 8.25),
    # port A controller: PPHV and VBUS leave to the east, each into its own inner-layer area
    _rect("VBUS_CHG", "B", -22.3, -5.85, -18.5, -4.6), _rect("VBUS_A", "B", -22.3, -7.4, -18.5, -6.15),
    _rect("VBUS_A", "B", -25.45, -9.55, -24.3, -8.45), _rect("+5V", "B", -26.9, -9.55, -25.75, -8.45),
    # port A socket (front face): a pad of copper above the socket at each pair of VBUS pins
    _rect("VBUS_A", "F", -30.4, -12.4, -26.42, -11.2), _rect("VBUS_A", "F", -23.62, -12.4, -20.4, -11.2),
    # 5 V: at the port B controller's pins and at the converter's output
    _rect("+5V", "B", -40.45, -2.9, -39.55, -1.9), _rect("+5V", "B", -17.85, 25.3, -15.7, 26.4),
    # port B converter
    ("PB_SW1", "B", [(-27.0, 19.55), (-22.45, 19.55), (-22.45, 22.3), (-24.42, 22.3), (-24.42, 25.55), (-27.0, 25.55)],
     [(-23.5, 20.6), (-25.7, 20.6), (-25.7, 24.9)], 0.9),
    ("PB_SW2", "B", [(-30.79, 19.5), (-30.075, 19.5), (-30.075, 19.65), (-29.55, 20.18), (-29.55, 22.2), (-32.3, 24.95), (-32.3, 26.9),
                     (-34.65, 26.9), (-34.65, 23.5), (-33.3, 23.5), (-32.3, 22.5), (-32.3, 20.75), (-31.28, 20.75), (-31.28, 20.11),
                     (-30.79, 19.62)], [(-30.4, 20.3), (-30.4, 22.0), (-33.3, 24.9), (-33.5, 26.0)], 0.6),
    ("VPB_RAW", "B", [(-31.3, 15.52), (-30.22, 15.52), (-30.22, 15.2), (-30.35, 15.07), (-30.35, 10.4), (-31.85, 10.4), (-31.85, 13.7),
                      (-34.05, 13.7), (-34.05, 15.1), (-32.3, 15.1), (-32.3, 15.3), (-31.3, 15.3)],
     [(-30.76, 15.2), (-31.1, 14.4), (-31.1, 11.2), (-31.1, 14.4), (-33.5, 14.4)], 0.6),
    # port B output switch
    ("VPB", "B", [(-48.75, -0.8), (-46.72, -0.8), (-46.72, 0.7), (-47.4, 0.7), (-47.4, 2.4), (-48.75, 2.4)], [(-47.9, -0.3), (-48.1, 1.9)], 0.8),
    _rect("PB_MID", "B", -48.55, -7.38, -46.05, -1.22), _rect("VBUS_B", "B", -47.85, -10.5, -45.9, -7.85),
    # port B socket (front face)
    _rect("VBUS_B", "F", -43.4, -12.4, -39.42, -11.2), _rect("VBUS_B", "F", -36.62, -12.4, -33.5, -11.2),
    # motor rail
    ("VM_IN", "B", [(38.4, -20.3), (40.7, -20.3), (41.2, -21.05), (46.5, -21.05), (46.5, -18.75), (43.0, -18.75), (43.0, -17.45),
                    (41.25, -17.45), (41.25, -16.9), (38.4, -16.9)], [(39.5, -18.6), (42.0, -19.3), (45.4, -19.9)], 0.9),
    _rect("VM_IN", "F", 41.2, -18.6, 42.8, -17.4),
    ("BST_SW", "B", [(33.25, -13.3), (33.75, -13.3), (33.75, -14.65), (34.6, -15.5), (34.6, -20.3), (32.4, -20.3), (32.4, -15.5),
                     (33.25, -14.65)], [(33.5, -14.0), (33.5, -19.5)], 0.6),
    # 5 V converter
    ("SW_5V", "B", [(-13.75, 19.3), (-11.0, 19.3), (-7.65, 23.5), (-7.65, 27.9), (-9.9, 27.9), (-9.9, 24.3), (-12.3, 21.2), (-12.3, 19.9),
                    (-13.75, 19.9)], [(-13.0, 19.6), (-11.6, 19.9), (-8.8, 24.0), (-8.8, 27.0)], 0.5),
]

# Tracks and vias laid by hand: the short necks at the fine-pitch pins of the power stages, the connections under the
# charger and the port B converter, and the vias from the copper areas into the inner layers.
# (net, points, width, face); a point is (x, y) or ("REF", pad).
HAND_TRACKS = [
    # charger U2: ground, system rail, boot and regulator pins go inward to vias under the package (it has no centre pad)
    ("GND", [("U2", 27), (-24.0, 6.3)], 0.2, "B"), ("GND", [("U2", 13), (-24.2, 5.4), (-24.0, 5.6), (-24.0, 6.3)], 0.2, "B"),
    ("GND", [("U2", 10), (-23.0, 5.25), (-23.4, 5.25)], 0.2, "B"), ("GND", [("U2", 11), (-23.4, 5.25), (-23.75, 5.6), (-24.0, 5.85)], 0.2, "B"),
    ("VSYS", [("U2", 25), (-24.9, 6.35)], 0.2, "B"),
    ("CHG_BT2", [("U2", 19), (-25.45, 6.1), (-25.05, 5.7), (-25.05, 5.5)], 0.15, "B"), ("CHG_BT1", [("U2", 4), (-23.05, 6.9)], 0.15, "B"),
    ("CHG_REGN", [("U2", 5), (-22.65, 6.5), (-23.05, 6.1)], 0.15, "B"), ("CHG_STAT", [("U2", 1), (-21.9, 8.3)], 0.3, "B"),
    ("CHG_SW1", [("U2", 28), (-23.55, 9.3)], 0.2, "B"), ("CHG_SW2", [("U2", 26), (-24.45, 9.3)], 0.2, "B"),
    ("CHG_PMID", [("U2", 29), (-23.1, 8.75), (-22.45, 9.4)], 0.2, "B"),
    ("VBUS_CHG", [("U2", 2), (-21.0, 7.7)], 0.2, "B"), ("VBUS_CHG", [("U2", 3), (-21.2, 7.3)], 0.2, "B"),
    ("VBUS_CHG", [("U2", 8), (-21.2, 5.3)], 0.2, "B"), ("VBUS_CHG", [("U2", 9), (-21.9, 4.65), (-21.55, 5.0), (-21.2, 5.0)], 0.2, "B"),
    ("VBAT", [("U2", 23), (-26.6, 7.7)], 0.2, "B"), ("VBAT", [("U2", 22), (-26.6, 7.3)], 0.2, "B"),
    # the boot and regulator capacitors stand on the front face under the charger, at the vias from its pins
    ("CHG_BT1", [("C2", 1), (-23.1, 7.3), (-23.05, 6.9)], 0.15, "F"), ("CHG_SW1", [("C2", 2), (-23.25, 9.7)], 0.15, "F"),
    ("CHG_BT2", [("C3", 1), (-25.6, 7.3), (-25.6, 6.05), (-25.05, 5.5)], 0.15, "F"), ("CHG_SW2", [("C3", 2), (-24.75, 9.7)], 0.15, "F"),
    ("CHG_REGN", [("C4", 1), (-23.05, 6.1)], 0.2, "F"),
    # port B converter U7
    ("PB_SW2", [("U7", 21), (-30.25, 19.6), (-30.4, 19.9)], 0.25, "B"), ("PB_SW2", [("U7", 21), (-30.25, 18.75), (-30.0, 18.5), ("U7", 25)], 0.25, "B"),
    ("VPB_RAW", [("U7", 11), ("U7", 26)], 0.25, "B"), ("VPB_RAW", [("U7", 11), (-30.62, 15.3)], 0.25, "B"),
    ("VPB_RAW", [("U7", 12), (-31.12, 15.3)], 0.25, "B"),
    ("GND", [("U7", 9), ("U7", 24)], 0.25, "B"), ("GND", [("U7", 10), (-29.88, 16.35), (-29.38, 16.35)], 0.2, "B"),
    ("GND", [("U7", 9), (-29.38, 15.3), (-29.2, 15.0)], 0.25, "B"),
    ("PB_BOOT1", [("U7", 22), (-29.75, 19.6), (-29.3, 20.05), ("C29", 1)], 0.15, "B"),
    ("PB_BOOT2", [("U7", 20), (-31.05, 19.6), (-31.49, 20.04), ("C30", 1)], 0.15, "B"),
    ("PB_SW1", [("U7", 23), (-28.95, 19.5), (-28.42, 20.03), (-28.42, 21.21), ("C29", 2)], 0.15, "B"),
    ("PB_SW1", [("C29", 2), (-28.42, 21.21), (-26.9, 21.21)], 0.2, "B"),
    # the converter's current-sense pin, straight from the far pad of the sense resistor (Kelvin connection)
    ("VPB", [("U7", 13), (-31.9, 15.62), (-35.0, 15.62), (-35.6, 15.02), (-35.6, 14.6)], 0.15, "B"),
    # port A controller U3
    ("VBUS_CHG", [("U3", 20), (-21.3, -5.22)], 0.6, "B"), ("VBUS_A", [("U3", 23), (-21.3, -6.78)], 0.6, "B"),
    ("+5V", [("U3", 34), (-26.0, -8.6), (-26.3, -9.0)], 0.6, "B"), ("VBUS_A", [("U3", 32), (-25.2, -8.6), (-24.85, -9.0)], 0.6, "B"),
    # port B controller U6: its VPB sense pin to a via into the VPB area
    ("VPB", [("U6", 19), (-45.4, -6.1)], 0.15, "B"),
    ("+5V", [("U6", 28), (-40.2, -2.6)], 0.2, "B"), ("+5V", [("U6", 29), (-39.8, -2.6)], 0.2, "B"),
    # USB-C sockets: the VBUS pins of row A go out upward between the shell pin and their neighbour; those of row B
    # join them through the gap between the two rows, so that the CC and data pins of row B have the whole lower side
    ("VBUS_A", [("J3", "A4"), (-26.99, -14.05), (-26.57, -13.63), (-26.57, -12.0)], 0.3, "F"),
    ("VBUS_A", [("J3", "A9"), (-23.04, -14.05), (-23.47, -13.62), (-23.47, -12.0)], 0.3, "F"),
    ("VBUS_A", [("J3", "B9"), ("J3", "A4")], 0.3, "F"), ("VBUS_A", [("J3", "B4"), ("J3", "A9")], 0.3, "F"),
    ("VBUS_B", [("J4", "A4"), (-39.99, -14.05), (-39.57, -13.63), (-39.57, -12.0)], 0.3, "F"),
    ("VBUS_B", [("J4", "A9"), (-36.04, -14.05), (-36.47, -13.62), (-36.47, -12.0)], 0.3, "F"),
    ("VBUS_B", [("J4", "B9"), ("J4", "A4")], 0.3, "F"), ("VBUS_B", [("J4", "B4"), ("J4", "A9")], 0.3, "F"),
    # USB-C sockets, data pins: D+ and D- are on both rows and in opposite order. The socket's footprint forbids copper on
    # the front face just beyond the pad tips of these four pins, so each pin has a via in its own pad (filled and capped,
    # D51; the D- vias sit at the pad's end so that the drill holes are 0.5 mm apart); D+ is joined on the inner face
    # under the socket, D- on inner layer 2
] + [t_ for x_, n_, j_ in ((0.0, "A", "J3"), (-13.0, "B", "J4")) for t_ in (
    (n_ + "_DP", [(j_, "A6"), (-25.41 + x_, -14.3)], 0.15, "F"), (n_ + "_DN", [(j_, "A7"), (-24.62 + x_, -14.1)], 0.15, "F"),
    (n_ + "_DP", [(j_, "B6"), (-24.62 + x_, -16.4)], 0.15, "F"), (n_ + "_DN", [(j_, "B7"), (-25.41 + x_, -16.6)], 0.15, "F"),
    (n_ + "_DP", [(-25.41 + x_, -14.3), (-24.62 + x_, -15.09), (-24.62 + x_, -17.4)], 0.15, "B"),
    (n_ + "_DN", [(-24.62 + x_, -14.1), (-24.62 + x_, -15.6), (-25.41 + x_, -16.39), (-25.41 + x_, -16.6)], 0.15, "In2"))
] + [
    # where the routed tracks take over: port A, D- from above on inner layer 2 and from below on the front face (the
    # stub ends 0.15 mm short of the forbidden strip); port B, D+ from above and D- from below on the inner face
    ("A_DN", [(-24.62, -12.75), (-24.62, -14.1)], 0.15, "In2"), ("A_DN", [("J3", "B7"), (-25.41, -17.0)], 0.15, "F"),
    ("B_DP", [(-38.41, -13.3), (-38.41, -14.3)], 0.15, "B"), ("B_DN", [(-38.41, -16.6), (-38.41, -17.95)], 0.15, "B"),
    # port A, CC pins: CC1 up between the two VBUS pads and east to a via, CC2 down to a via; both then run on the
    # inner face straight to their pins on the controller
    ("A_CC1", [("J3", "A5"), (-26.2, -10.9), (-26.05, -10.75), (-23.7, -10.75), (-23.3, -10.35), (-23.3, -9.85)], 0.15, "F"),
    ("A_CC1", [("U3", 28), (-23.4, -8.5), (-23.3, -8.7), (-23.3, -9.85)], 0.15, "B"),
    ("A_CC2", [("J3", "B5"), (-23.83, -17.95)], 0.15, "F"),
    ("A_CC2", [("U3", 29), (-23.8, -8.4), (-23.83, -8.6), (-23.83, -17.95)], 0.15, "B"),
    # 3.3 V for the west of the board, where inner layer 1 is taken by the other rails: a feeder on inner layer 2 from
    # the 3.3 V plane (via east of the system-rail trunk) to a via at each USB controller's supply pin
    ("+3V3", [("U6", 32), (-38.6, -0.85)], 0.2, "B"), ("+3V3", [("U3", 38), (-27.4, -10.3)], 0.2, "B"),
    ("+3V3", [(-14.2, 0.9), (-31.0, 0.9), (-31.0, -9.4), (-30.1, -10.3), (-27.4, -10.3)], 0.4, "In2"),
    ("+3V3", [(-31.0, 0.9), (-37.0, 0.9), (-38.6, -0.7), (-38.6, -0.85)], 0.4, "In2"),
    # 3.3 V converter: switch pin to the coil
    ("SW_3V3", [("U10", 5), (-9.2, 11.75), (-9.85, 11.1), (-9.85, 10.8)], 0.3, "B"),
]
HAND_VIAS = [
    ("GND", (-24.0, 7.2)), ("GND", (-24.0, 6.3)), ("VSYS", (-24.9, 7.15)), ("VSYS", (-24.9, 6.35)), ("CHG_BT2", (-25.05, 5.5)),
    ("CHG_BT1", (-23.05, 6.9)), ("CHG_REGN", (-23.05, 6.1)), ("CHG_SW1", (-23.25, 9.7)), ("CHG_SW2", (-24.75, 9.7)), ("CHG_STAT", (-21.9, 8.3)),
    ("VBUS_CHG", (-20.9, 6.8)), ("VBUS_CHG", (-20.1, 6.8)), ("VBUS_CHG", (-19.3, 6.8)),
    ("VBUS_CHG", (-20.9, 7.7)), ("VBUS_CHG", (-20.1, 7.7)), ("VBUS_CHG", (-19.3, 7.7)),
    ("CHG_PMID", (-21.75, 9.3)), ("CHG_PMID", (-20.85, 9.3)), ("CHG_PMID", (-19.35, 9.3)), ("CHG_PMID", (-18.45, 9.3)),
    ("VBAT", (-28.3, 7.7)), ("VBAT", (-27.5, 7.7)),
    ("GND", (-29.2, 15.0)),
    ("VBUS_CHG", (-21.25, -5.22)), ("VBUS_CHG", (-20.45, -5.22)), ("VBUS_CHG", (-19.65, -5.22)), ("VBUS_CHG", (-18.85, -5.22)),
    ("VBUS_A", (-21.25, -6.78)), ("VBUS_A", (-20.45, -6.78)), ("VBUS_A", (-19.65, -6.78)), ("VBUS_A", (-18.85, -6.78)),
    ("+5V", (-26.3, -9.0)), ("VBUS_A", (-24.85, -9.0)), ("+5V", (-40.0, -2.35)), ("VPB", (-45.4, -6.1)),
    ("VBUS_A", (-29.6, -11.8)), ("VBUS_A", (-28.8, -11.8)), ("VBUS_A", (-28.0, -11.8)),
    ("VBUS_A", (-22.6, -11.8)), ("VBUS_A", (-21.8, -11.8)), ("VBUS_A", (-21.0, -11.8)),
    ("VBUS_B", (-42.6, -11.8)), ("VBUS_B", (-41.8, -11.8)), ("VBUS_B", (-41.0, -11.8)),
    ("VBUS_B", (-35.6, -11.8)), ("VBUS_B", (-34.8, -11.8)), ("VBUS_B", (-34.0, -11.8)),
    ("VPB", (-48.35, 0.35)), ("VPB", (-47.55, 0.35)),
    ("VM_IN", (41.6, -18.0)), ("VM_IN", (42.4, -18.0)), ("VBAT_IN", (40.3, -25.5)), ("VBAT_IN", (41.3, -25.5)),
    ("A_CC1", (-23.3, -9.85)), ("A_CC2", (-23.83, -17.95)), ("+3V3", (-38.6, -0.85)), ("+3V3", (-27.4, -10.3)), ("+3V3", (-14.2, 0.9)),
] + [v_ for x_, n_ in ((0.0, "A"), (-13.0, "B")) for v_ in (
    (n_ + "_DP", (-25.41 + x_, -14.3)), (n_ + "_DN", (-24.62 + x_, -14.1)), (n_ + "_DP", (-24.62 + x_, -16.4)), (n_ + "_DN", (-25.41 + x_, -16.6)))]


def hand(pcb):
    """Lays HAND_TRACKS and HAND_VIAS and keeps the small parts off them."""
    for net, pts, w, face in HAND_TRACKS:
        pcb.track(net, pts, w, face)
        q = [pcb.pt(p_) for p_ in pts]
        for a, b in zip(q, q[1:]):
            n_ = max(1, int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / 0.3))
            for i in range(n_ + 1):
                x, y = a[0] + (b[0] - a[0]) * i / n_, a[1] + (b[1] - a[1]) * i / n_
                if face in ("F", "B"):
                    pcb.block(face, (x - 0.4, y - 0.4, x + 0.4, y + 0.4))
    for net, p_ in HAND_VIAS:
        pcb.via(net, p_)
        x, y = pcb.pt(p_)
        pcb.block("*", (x - 0.7, y - 0.7, x + 0.7, y + 0.7))


ANT = (-30.0, -30.0, 18.0, -23.9)        # ESP32 antenna: no copper on any layer

# In1 (inner layer 1) is the power layer: 3.3 V everywhere, and on top of it one area per supply rail.
# The system rail runs from the charger north to the port B converter, east to the 3.3 V and 5 V converters and down a
# trunk east of port A to the corridor along the bottom edge that feeds the motor switch. The long runs of the USB and
# 5 V rails lie here too, each as its own area: they are joined to the copper on the outer faces by vias in the pads.
FULL = [(-49.5, -29.5), (49.5, -29.5), (49.5, 29.5), (-49.5, 29.5)]
WEST = [(-49.5, -29.5), (-15.4, -29.5), (-15.4, 9.3), (-5.0, 9.3), (-5.0, 22.2), (-13.3, 22.2), (-13.3, 29.5), (-49.5, 29.5)]
EAST = [(-15.4, -29.5), (49.5, -29.5), (49.5, 29.5), (-13.3, 29.5), (-13.3, 22.2), (-5.0, 22.2), (-5.0, 9.3), (-15.4, 9.3)]
RAILS = [
    ("VBUS_CHG", [(-21.75, -5.85), (-18.4, -5.85), (-18.4, 8.4), (-21.75, 8.4)]),
    ("VBUS_A", [(-31.0, -12.4), (-31.0, -9.9), (-25.5, -9.9), (-25.5, -8.4), (-24.2, -8.4), (-24.2, -9.9), (-22.0, -9.9), (-22.0, -6.15),
                (-18.4, -6.15), (-18.4, -12.4)]),
    ("VBUS_B", [(-48.2, -12.4), (-33.4, -12.4), (-33.4, -10.0), (-45.6, -10.0), (-45.6, -7.9), (-48.2, -7.9)]),
    # from the far pad of the sense resistor R23 round the north of the jack cut-out and down the west edge to Q2
    ("VPB", [(-35.65, 13.0), (-35.65, 18.6), (-49.2, 18.6), (-49.2, -7.6), (-44.9, -7.6), (-44.9, -5.0), (-45.9, -5.0), (-45.9, 16.1),
             (-37.4, 16.1), (-37.4, 13.0)]),
    # from the 5 V converter along the top edge, down between the jack cut-out and the converters, to both USB controllers
    ("+5V", [(-13.3, 22.5), (-13.3, 29.2), (-35.4, 29.2), (-35.4, -1.0), (-40.7, -1.0), (-40.7, -3.0), (-35.4, -3.0), (-35.4, -9.75),
             (-25.65, -9.75), (-25.65, -8.3), (-33.7, -8.3), (-33.7, 27.4), (-18.2, 27.4), (-18.2, 24.9), (-16.6, 24.9), (-16.6, 22.5)]),
]
# Centre lines of the rails on In1 and the half width kept free of other nets' vias (tools/grouter.py), so that the via
# holes of the signals can never cut a rail through: the copper left whole is 2 x (half width - 0.45 mm).
RAIL_SPINES = [
    ("VBUS_CHG", [(-20.1, -5.2), (-20.1, 7.6)], 1.0),
    ("VBUS_A", [(-20.0, -6.8), (-20.0, -11.1), (-30.0, -11.1)], 1.0),
    ("VBUS_A", [(-24.85, -8.9), (-24.85, -10.5)], 0.95),
    ("VBUS_B", [(-46.9, -9.0), (-46.9, -11.2), (-34.5, -11.2)], 1.0),
    ("VPB", [(-36.4, 14.4), (-36.4, 17.35), (-47.55, 17.35), (-47.55, -6.3), (-45.4, -6.3)], 1.0),
    ("+5V", [(-15.0, 26.0), (-17.4, 28.3), (-34.55, 28.3), (-34.55, -9.0), (-26.3, -9.0)], 0.8), ("+5V", [(-34.55, -2.0), (-40.0, -2.0)], 0.8),
]
IN2 = [
    ("+3V3", EAST, 0),
    ("VSYS", [(-33.4, 2.9), (-22.0, 2.9), (-22.0, 8.65), (-18.1, 8.65), (-18.1, -23.4), (-15.4, -23.4), (-15.4, 9.3), (-5.0, 9.3),
              (-5.0, 22.2), (-16.9, 22.2), (-16.9, 24.7), (-18.4, 24.7), (-18.4, 27.1), (-33.4, 27.1)], 1),
    ("VSYS", [(-18.1, -23.4), (48.9, -23.4), (48.9, -18.4), (46.2, -18.4), (46.2, -19.6), (-18.1, -19.6)], 2),
    ("VMOT", [(11.8, 3.0), (11.8, 29.5), (49.5, 29.5), (49.5, -16.0), (25.5, -16.0), (25.5, 3.0)], 3),
] + [(n_, poly, 4) for n_, poly in RAILS]
# The battery rail crosses the board as one wide copper area (the pack input is at the lower right, the charger at the
# left; decision D50 keeps the pack pads there): out of the reverse-polarity FET, up between buttons 3 and 4, west above
# the buttons and under the ESP32 module, north past port A and west below the charger to its BAT pins. On the six-layer
# board it lies on In3, so both outer faces are free; In2 crosses it freely.
VBAT_BUS = [(32.9, -25.6), (30.5, -23.0), (30.5, -15.0), (29.0, -13.6), (3.5, -13.6), (1.5, -11.0), (-14.8, -11.0), (-17.4, -8.4),
            (-17.4, -0.4), (-19.0, 1.2), (-29.0, 1.2), (-29.0, 8.6)]
VBAT_BUS_W = 4.6
VBAT_LAYER = "In3"
VBAT_SPINE = 1.2                          # mm each side of the centre line without foreign vias


def in2_polys(net):
    return [poly for n_, poly, _p in IN2 if n_ == net]


def clusters(pts, gap=8.0):
    """Groups of points in which every point is within gap of another one of its group."""
    import math
    left = list(pts)
    out = []
    while left:
        grp = [left.pop()]
        grew = True
        while grew:
            grew = False
            for q in list(left):
                if any(math.hypot(q[0] - g_[0], q[1] - g_[1]) <= gap for g_ in grp):
                    grp.append(q)
                    left.remove(q)
                    grew = True
        out.append(grp)
    return out


def pour_areas(pcb):
    """Copper areas on the outer faces: one round every group of pads of a power or motor-phase net that lie together."""
    out = []
    drawn = {a_[0] for a_ in AREAS} | {r_[0] for r_ in RAILS}
    for net in [n_ for n_ in POWER_NETS + PHASE_NETS if n_ not in drawn or n_ == "VBAT"]:
        for side in ("B", "F"):
            pts = [xy for (r_, _p, xy, sd) in pcb.padpos.get(net, []) if sd == side and not r_.startswith("TP")]
            for grp in clusters(pts):
                if len(grp) >= 2:
                    out.append(dict(net=net, side=side, poly=pcb.hull(grp, 0.9)))
    return out


def route_plan(pcb):
    """What tools/grouter.py routes, in which order and how wide. The order is the layout intent:
    planes and the battery bus first, then the power stages, phases, USB, antenna feed and encoder bus, then the rest."""
    bus = pcb.thick(VBAT_BUS, VBAT_BUS_W)
    areas = pour_areas(pcb)
    regions = [dict(net=a["net"], side=a["side"], poly=a["poly"]) for a in areas]
    regions += [dict(net=n_, side=f_, poly=[list(q) for q in poly], hard=True, spine=[list(q) for q in sp], keep=k_,
                     halo_v=0.3 if f_ == "F" and n_ in ("VBUS_A", "VBUS_B") else 0.45)
                for n_, f_, poly, sp, k_ in AREAS]
    rails = [poly for _n, poly in RAILS]
    regions += [dict(net=n_, side="In1", poly=[list(q) for q in dict(RAILS)[n_]], spine=[list(q) for q in sp], keep=k_) for n_, sp, k_ in RAIL_SPINES]
    # the middle of the battery bus stays free of other nets' vias (tools/grouter.py: spine), which leaves it at least
    # 1.5 mm of unbroken copper from the pack to the charger whatever is routed across it
    regions.append(dict(net="VBAT", side=VBAT_LAYER, poly=bus, hard=True, spine=[list(q) for q in VBAT_BUS], keep=VBAT_SPINE))
    plane3v3 = ["+3V3"]
    steps = [
        dict(op="fanout", length=0.35),
        dict(op="plane", net="GND", polys=[FULL], w=0.25, ep=True, maxlen=4.0, in_pad=True),
        dict(op="plane", net="VMOT", polys=in2_polys("VMOT"), w=0.3, n_big=3, big_area=1.0, in_pad=True,
             n={"U15": 2, "U17": 2, "U19": 2, "U12": 3}),
        dict(op="plane", net="VSYS", polys=in2_polys("VSYS"), w=0.3, n_big=3, big_area=1.0, n={"Q6": 2, "Q4": 2}, in_pad=True),
        dict(op="plane", net="VBAT", polys=[bus], w=0.3, n_big=3, big_area=1.0, n={"Q1": 2, "U2": 3}, maxlen=3.0, in_pad=True),
        dict(op="stitch", net="VBAT", polys=[bus], areas=[a["poly"] for a in areas if a["net"] == "VBAT" and a["side"] == "B"], max=10),
        dict(op="stitch", net="VSYS", polys=in2_polys("VSYS"),
             areas=[a["poly"] for a in areas if a["net"] == "VSYS" and a["side"] == "B"], max=6),
        dict(op="stitch", net="VMOT", polys=in2_polys("VMOT"),
             areas=[a["poly"] for a in areas if a["net"] == "VMOT" and a["side"] == "B"], max=6),
        # the rails that have their own area on In1: a via in or beside every pad, several in the large ones
    ] + [dict(op="plane", net=n_, polys=[poly], w=0.3, n_big=3, big_area=1.0, maxlen=3.0, in_pad=True) for n_, poly in RAILS] + [
        # 3.3 V: not in the west of the board, where the plane is cut up by the other rails (its pads there are routed)
        dict(op="plane", net="+3V3", polys=[FULL], exclude=[WEST] + in2_polys("VSYS") + in2_polys("VMOT") + rails, w=0.25, in_pad=True),
        # Every slow-signal pin of the fine-pitch chips gets its way out first (tools/grouter.py: escape): a fixed track to
        # a ring 3 mm from its chip, so that no power or critical track can lie across it. The critical nets that follow
        # stay on the outer faces where they can and pay three to six times as much for an inner layer.
        dict(op="escape", name="escape of the fine-pitch chips", ring=3.0, layer_cost={"B": 3, "In2": 2, "In3": 2}, pad_vias=0.5),
        dict(op="route", name="GNSS antenna feed", nets=["GNSS_ANT", "GNSS_RF"], widths=[0.2], hard=True, layer_cost={"F": 100}),
        # The current of these nets is carried by their drawn areas (AREAS); what is routed here are the thin ties to
        # the pads that lie outside an area (boot capacitors, test points, sense pins).
        dict(op="route", name="switch nodes and power stages", layer_cost={"In2": 6, "In3": 6}, hard=True, region_cost=1,
             nets=["CHG_SW1", "CHG_SW2", "PB_SW1", "PB_SW2", "BST_SW", "SW_3V3", "SW_5V", "CHG_PMID", "VM_IN", "VBAT_IN",
                   "VPB_RAW", "PB_MID"], widths=[0.3, 0.2, 0.15], order="given"),
        dict(op="route", name="boot, gate drive and bias", layer_cost={"In2": 3, "In3": 3}, hard=True,
             nets=["CHG_BT?", "PB_BOOT?", "BST_BT", "BST_5V", "BST_3V3", "PB_DR1?", "CHG_REGN", "PB_VCC", "BST_VCC", "MSW_G", "Q1_G",
                   "*_5V", "RP_LX", "+1V1", "RP_AVDD", "+3V3A", "+3V3G"], widths=[0.3, 0.2, 0.15]),
        dict(op="route", name="motor phases and sense", layer_cost={"In2": 6, "In3": 6}, nets=["*_A1", "*_A2", "*_B1", "*_B2", "*_BRA", "*_BRB"], hard=True,
             widths=[0.5, 0.3, 0.2]),
        dict(op="route", name="USB pairs", layer_cost={"In2": 3, "In3": 3}, nets=["A_DP", "A_DN", "B_DP", "B_DN"], widths=[0.2, 0.15], hard=True, order="given"),
        dict(op="route", name="crystal and feedback", layer_cost={"In2": 3, "In3": 3}, hard=True,
             nets=["RP_XIN", "RP_XOUT", "RP_XOUT_X", "FB_3V3", "FB_5V", "BST_FB", "BST_COMP*", "PB_COMP*", "VMSEL_D", "PB_FSW", "PB_ILIM",
                   "PB_MODE", "PB_DITH", "CHG_ILIM", "CHG_PROG", "CHG_TS", "SS_3V3", "CHG_BATP", "CHG_SDRV"], widths=[0.15]),
        # The drivers' charge-pump and reference pins and the gate lines of port B's output switch carry next to no
        # current; they are routed with the slow signals, so that their pins get an escape track like the others
        # (their capacitors stand west of the drivers, across the neighbouring pins' way out).
        # From here on the slow signals, on all four signal layers; the two inner ones cost twice an outer face, so
        # short connections stay outside.
        dict(op="route", name="encoder SPI", nets=["ENC_MISO", "ENC_SCK_M", "ENC_MOSI_M", "CS_*_M", "*_SCK", "*_MOSI", "*_CS"], widths=[0.15],
             layer_cost={"In2": 2, "In3": 2}),
        dict(op="rest", name="all other signals", widths=[0.15], layer_cost={"In2": 2, "In3": 2}),
    ]
    return dict(plan=dict(layers=["F", "B", "In2", "In3"], via_in_pad=0.5, layer_cost={"In2": 1000, "In3": 1000}, widths=[0.15, 0.2, 0.3, 0.35, 0.5, 1.0], steps=steps,
                          class_widths={"*_3V3": [0.3, 0.2, 0.15], "PDA_LDO*": [0.2, 0.15], "PDB_LDO*": [0.2, 0.15]}),
                regions=regions, cutouts=[list(JACK)],
                keepouts=[dict(r=list(ANT), layers=["F", "B", "In1", "In2", "In3", "In4"])])


def finish(pcb):
    """After routing: copper areas over every power net, the inner power layer, the battery bus, ground on both outer faces."""
    full = pcb.rect(-49.5, -29.5, 49.5, 29.5)
    for ref in pcb.fps:                       # IC ground pads and thermal pads join the pours solidly
        if ref.startswith(("U", "Q", "J", "L", "R", "C", "SW", "D", "TP")):
            pcb.solid(ref)
    for a in pour_areas(pcb):
        pcb.zone(a["net"], a["side"], a["poly"], clearance=0.2, solid=True, priority=5)
    for net, face, poly, _sp, _k in AREAS:
        pcb.zone(net, face, poly, clearance=0.2, solid=True, priority=6)
    pcb.zone("VBAT", VBAT_LAYER, pcb.thick(VBAT_BUS, VBAT_BUS_W), clearance=0.2, solid=True, priority=4)
    for net, poly, prio in IN2:
        pcb.zone(net, "In1", poly, clearance=0.2, solid=True, priority=prio)
    pcb.zone("GND", "F", full, clearance=0.2)
    pcb.zone("GND", "B", full, clearance=0.2)
