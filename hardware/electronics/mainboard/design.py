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
PCB_ARGS = dict(layers=4, default_track=0.15, default_via=(0.5, 0.3), clearance=0.127)

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
    s.note(20, 20, "Battery input. J1: XT30 from the battery bay (pad 2 is +). Q1 blocks a reversed bench supply. J2: pack SMBus and presence.", 1.6)
    ic(s, "Connector_Generic:Conn_01x02", "J", "XT30", {1: "GND", 2: "VBAT_IN"}, 35, 40)
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
                   "9 V / 3 A comes from the TPS55288 (I2C 0x74) through Q4-Q5. Data pins go to pads for camera control in v2 (D6).", 1.6)
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
    s.note(20, 20, "ESP32-S3-WROOM-1-N16R8: Wi-Fi, BLE, USB, apps. Programs the RP2354A over SWD (IO38-IO40). J8: Tag-Connect for the ESP32 console.", 1.6)
    pins = {"GND": "GND", "3V3": "+3V3", "EN": "ESP_EN"}
    pins.update(ESP)
    ic(s, "RF_Module:ESP32-S3-WROOM-1", "U", "ESP32", pins, 70, 90)
    s.note(165, 30, "RP2354A: three PIO step trains, encoder SPI, driver UART. 12 MHz crystal, core supply 1.1 V from its own regulator. J9: Tag-Connect SWD.", 1.6)
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
                   "enabled before set-up.\nCartridge plugs J10-J12, JST-GH 15-way: 1-2 A1, 3-4 A2, 5 GND, 6 CS, 7 SCK, 8 MOSI, 9 MISO, 10 NTC, 11 3V3, 12-13 B1, 14-15 B2.", 1.6)
    for i, (ax, addr) in enumerate(AXES):
        x0 = 30 + i * 135
        ic(s, "Driver_Motor:TMC2209-LA", "U", "TMC2209",
           {"OB2": f"{ax}_B2", "~{EN}": "DRV_EN_N", "GND": "GND", "CPO": f"{ax}_CPO", "CPI": f"{ax}_CPI", "VCP": f"{ax}_VCP", "SPREAD": "GND",
            "5VOUT": f"{ax}_5V", "MS1/AD0": "+3V3" if addr & 1 else "GND", "MS2/AD1": "+3V3" if addr & 2 else "GND", "DIAG": f"DIAG_{ax}",
            "INDEX": NC, "CLK": "GND", "~{PD}/UART": "TMC_UART", "VCC_IO": "+3V3", "STEP": f"STEP_{ax}", "VREF": f"{ax}_VREF", "DIR": f"DIR_{ax}",
            "STDBY": "GND", "OA2": f"{ax}_A2", "VS": "VMOT", "BRA": f"{ax}_BRA", "OA1": f"{ax}_A1", "NC": NC, "OB1": f"{ax}_B1", "BRB": f"{ax}_BRB"},
           x0 + 45, 70)
        fp, f = cat.fields("P", "GH15H")
        s.part("Connector_Generic_MountingPin:Conn_01x15_MountingPin", ref("J"), cat.PART["GH15H"][1], fp,
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
    two(s, "Device:C_Polarized", "C", "SUPERCAP", "RTC_VBAK", "GND", value="0.1F 5.5V")
    two(s, "Device:FerriteBead", "FB", "FB", "+3V3", "+3V3G")
    c(s, "10u", "+3V3G", "GND")
    c(s, "100n", "+3V3G", "GND")
    c(s, "47p", "GNSS_ANT", "GNSS_RF")
    two(s, "Device:L", "L", "L47n", "GNSS_BIAS", "GNSS_ANT", value="47n")
    r(s, "10R", "GNSS_VRF", "GNSS_BIAS")
    c(s, "10n", "GNSS_BIAS", "GND")

    s.note(20, 122, "OLED 1.3 in SH1106 module on a 4-pin header (J14). R fitted for modules marked VCC-GND-SCL-SDA; swap to the two unfitted ones for GND-VCC.", 1.6)
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

    s.note(200, 122, "Shutter port J15 (to the 2.5 mm jack on the bezel): tip = shutter, ring = focus, sleeve = camera ground. Isolated from the head by U21-U22.", 1.6)
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
