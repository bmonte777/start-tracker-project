"""Project symbol library ST.kicad_sym: the parts KiCad 9 does not ship. Pin tables are from the datasheets
(sources in docs/04-electronics.md). Run: python3 stlib.py  -> ../lib/ST.kicad_sym"""
import os

from schgen import box_symbol, write_symbol_lib

I, O, B, P, PI, PO, OC, T = "input", "output", "bidirectional", "passive", "power_in", "power_out", "open_collector", "tri_state"

SYMS = []


def add(*a, **k):
    SYMS.append(box_symbol(*a, **k))


add("MT6835GT",
    [(9, "VDD", PI), (8, "CSN", I), (7, "SCK", I), (6, "MOSI", I), (5, "MISO", T), (4, "CAL_EN", I), (12, "VSS", PI)],
    [(16, "A", O), (15, "B", O), (14, "Z", O), (1, "U", O), (2, "V", O), (3, "W", O), (10, "OUT", O), (11, "TEST", P), (13, "TEST_EN", P)],
    "Package_SO:TSSOP-16_4.4x5mm_P0.65mm", "https://www.magntek.com.cn/upload/MT6835_Rev.1.4.pdf",
    "21-bit magnetic angle encoder, SPI / ABZ / UVW / PWM, TSSOP-16")

add("TPS61288",
    [(7, "VIN", PI), (6, "EN", I), (11, "VCC", P), (2, "COMP", P), (1, "FB", I), (10, "AGND", PI)],
    [(4, "SW", P), (9, "SW", P), (8, "BST", P), (5, "VOUT", PO), (3, "PGND", PI)],
    "Package_DFN_QFN:Texas_VQFN-HR-20_3x2.5mm_P0.5mm_RQQ0011A", "https://www.ti.com/lit/gpn/tps61288",
    "18 V, 15 A synchronous boost converter, 500 kHz, VQFN-HR-11 2.5 x 3 mm")

add("TPS55288",
    [(3, "VIN", PI), (4, "EN/UVLO", I), (5, "SCL", I), (6, "SDA", B), (15, "MODE", P), (8, "FSW", P), (7, "DITH/SYNC", P), (17, "ILIM", P),
     (18, "COMP", P), (16, "CDC", P), (14, "FB/INT", OC), (19, "VCC", P), (10, "AGND", PI)],
    [(2, "DR1H", O), (22, "BOOT1", P), (23, "SW1", P), (1, "DR1L", O), (20, "BOOT2", P), (21, "SW2", P), (25, "SW2", P), (11, "VOUT", PO),
     (26, "VOUT", P), (12, "ISP", I), (13, "ISN", I), (9, "PGND", PI), (24, "PGND", P)],
    "ST:Texas_RPM0026A_VQFN-HR-26_3.5x4mm", "https://www.ti.com/lit/gpn/tps55288",
    "36 V, 16 A buck-boost converter with I2C, VQFN-HR-26 3.5 x 4 mm")

add("TPS25751D",
    [(38, "VIN_3V3", PI), (1, "LDO_3V3", PO), (4, "LDO_1V5", PO), (2, "ADCIN1", I), (3, "ADCIN2", I), (8, "I2Ct_SDA", B), (9, "I2Ct_SCL", I),
     (10, "I2Ct_IRQ", OC), (16, "I2Cc_SDA", B), (17, "I2Cc_SCL", O), (18, "I2Cc_IRQ", I), (5, "GPIO0", B), (6, "GPIO1", B), (7, "GPIO2", B),
     (19, "GPIO3", B), (37, "GPIO6", B), (36, "GPIO7", B), (13, "GPIO11", B), (11, "GND", PI), (12, "GND", P), (14, "GND", P), (31, "GND", P),
     (39, "EP_GND", P)],
    [(32, "VBUS", P), (33, "VBUS", P), (23, "VBUS_IN", P), (24, "VBUS_IN", P), (25, "VBUS_IN", P), (20, "PPHV", P), (21, "PPHV", P),
     (22, "PPHV", P), (15, "DRAIN", P), (30, "DRAIN", P), (40, "EP_DRAIN", P), (34, "PP5V", PI), (35, "PP5V", P), (28, "CC1", B), (29, "CC2", B),
     (26, "GPIO4/USB_P", B), (27, "GPIO5/USB_N", B)],
    "Package_DFN_QFN:Texas_REF0038A_WQFN-38-2EP_6x4mm_P0.4", "https://www.ti.com/lit/gpn/tps25751",
    "USB Type-C PD 3.1 controller with integrated 5 A bidirectional power path, WQFN-38 4 x 6 mm")

add("TPS25752A",
    [(32, "VIN_3V3", PI), (1, "LDO_3V3", PO), (4, "LDO_1V5", PO), (2, "ADCIN1", I), (3, "ADCIN2", I), (8, "I2Ct_SDA", B), (9, "I2Ct_SCL", I),
     (10, "I2Ct_IRQ", OC), (15, "I2Cc_SDA", B), (16, "I2Cc_SCL", O), (17, "I2Cc_IRQ", I), (5, "GPIO0/LD1", B), (6, "GPIO1", B), (7, "GPIO2/LD2", B),
     (18, "GPIO3", B), (31, "GPIO6", B), (30, "GPIO7", B), (13, "GPIO11", B), (11, "GND", PI), (12, "GND", P), (14, "GND", P), (33, "EP", P)],
    [(26, "VBUS", P), (27, "VBUS", P), (28, "PP5V", PI), (29, "PP5V", P), (19, "VSYS", I), (20, "GATE_VSYS", O), (21, "GATE_VBUS", O),
     (24, "CC1", B), (25, "CC2", B), (22, "GPIO4/USB_P", B), (23, "GPIO5/USB_N", B)],
    "Package_DFN_QFN:VQFN-32-1EP_4x4mm_P0.4mm_EP2.8x2.8mm", "https://www.ti.com/lit/gpn/tps25752a",
    "USB Type-C PD 3.2 source-only controller, 5 V path inside, gate drive for an external high-voltage path, VQFN-32 4 x 4 mm")

add("BQ40Z50",
    [(32, "BAT", PI), (26, "VCC", PI), (27, "PACK", I), (1, "PBI", P), (2, "VC4", I), (3, "VC3", I), (4, "VC2", I), (5, "VC1", I), (8, "SRP", I),
     (6, "SRN", I), (10, "TS1", I), (11, "TS2", I), (12, "TS3", I), (13, "TS4", I), (23, "PTC", I), (24, "PTCEN", I), (9, "VSS", PI), (33, "EP", P)],
    [(31, "CHG", O), (30, "PCHG", O), (28, "DSG", O), (25, "FUSE", O), (19, "SMBC", B), (18, "SMBD", B), (16, "PRES/SHUTDN", I), (15, "BTP_INT", O),
     (17, "DISP", I), (20, "LEDCNTLA", B), (21, "LEDCNTLB", B), (22, "LEDCNTLC", B), (7, "NC", "no_connect"), (14, "NC", "no_connect"),
     (29, "NC", "no_connect")],
    "Package_DFN_QFN:VQFN-32-1EP_4x4mm_P0.4mm_EP2.8x2.8mm", "https://www.ti.com/lit/gpn/bq40z50-r2",
    "1-4 series Li-ion gauge, protector and balancer, SMBus, VQFN-32 4 x 4 mm")

add("MMC5983MA",
    [(2, "VDD", PI), (13, "VDDIO", PI), (10, "CAP", P), (9, "GND", PI), (11, "GND", P)],
    [(1, "SCL", I), (16, "SDA", B), (4, "SPI_CS", I), (5, "SPI_SDO", O), (15, "INT", O), (3, "NC", "no_connect"), (6, "NC", "no_connect"),
     (7, "NC", "no_connect"), (8, "NC", "no_connect"), (12, "NC", "no_connect"), (14, "NC", "no_connect")],
    "Package_LGA:LGA-16_3x3mm_P0.5mm", "https://www.memsic.com/Public/Uploads/uploadfile/files/20220119/MMC5983MADatasheetRevA.pdf",
    "3-axis AMR magnetometer, I2C / SPI, LGA-16 3 x 3 mm")

add("LSM6DSV",
    [(8, "VDD", PI), (5, "VDDIO", PI), (12, "CS", I), (1, "SDO/SA0", I), (2, "SDX", P), (3, "SCX", P), (6, "GND", PI), (7, "GND", P)],
    [(13, "SCL", I), (14, "SDA", B), (4, "INT1", O), (9, "INT2", O), (10, "NC", "no_connect"), (11, "NC", "no_connect")],
    "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y", "https://www.st.com/resource/en/datasheet/lsm6dsv.pdf",
    "6-axis IMU, I2C / SPI / I3C, LGA-14 2.5 x 3 mm")

for nm, descr in (("NMOS_DFN33", "N-channel MOSFET, DFN 3x3-8 (S 1-3, G 4, D 5-8 and pad)"), ("PMOS_DFN33", "P-channel MOSFET, DFN 3x3-8 (S 1-3, G 4, D 5-8 and pad)")):
    add(nm, [(4, "G", I)], [(5, "D", P), (6, "D", P), (7, "D", P), (8, "D", P), (9, "D", P), (1, "S", P), (2, "S", P), (3, "S", P)],
        "Package_DFN_QFN:DFN-8-1EP_3x3mm_P0.65mm_EP1.55x2.4mm", "~", descr, ref="Q")
for nm, descr in (("NMOS_SOT23", "N-channel MOSFET, SOT-23 (G 1, S 2, D 3)"), ("PMOS_SOT23", "P-channel MOSFET, SOT-23 (G 1, S 2, D 3)")):
    add(nm, [(1, "G", I)], [(3, "D", P), (2, "S", P)], "Package_TO_SOT_SMD:SOT-23", "~", descr, ref="Q")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
    os.makedirs(out, exist_ok=True)
    write_symbol_lib(os.path.join(out, "ST.kicad_sym"), SYMS)
    print("wrote", len(SYMS), "symbols")
