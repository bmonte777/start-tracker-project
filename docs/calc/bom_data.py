"""Star Tracker Project - master parts list skeleton (Phase 2).

Single source of truth for hardware/bom/master-parts-list.csv and for the
cost model in phase2_calcs.py. Prices are per piece at build quantities of
1, 100 and 1,000 heads. 'src' says where a price comes from:
  quoted  = read from a supplier/distributor page on 20 Nov 2026 (see spec sources)
  est     = engineering estimate, to be replaced by a quote in Phase 3/4
"""
USD_TO_EUR = 0.91  # mid-market, 17-18 Nov 2026


def U(a, b, c):
    """USD prices -> EUR."""
    return tuple(round(x * USD_TO_EUR, 2) for x in (a, b, c))


def E(a, b, c):
    return (a, b, c)


# (id, name, qty, material prototype, material production, make/buy, supplier, (p1, p100, p1000) EUR each, src, note)
PARTS = [
    # ---- 0xx assemblies -------------------------------------------------------------------
    ("ST-000", "Star tracker head, complete", 1, "-", "-", "make", "-", E(0, 0, 0), "-", "top assembly"),
    ("ST-010", "Azimuth cartridge assembly", 1, "-", "-", "make", "-", E(0, 0, 0), "-", "ST-201,203..213"),
    ("ST-020", "Altitude cartridge assembly", 1, "-", "-", "make", "-", E(0, 0, 0), "-", "ST-202,203..213"),
    ("ST-030", "Roll cartridge assembly", 1, "-", "-", "make", "-", E(0, 0, 0), "-", "ST-201,203..213"),
    ("ST-040", "Wedge and base assembly", 1, "-", "-", "make", "-", E(0, 0, 0), "-", "ST-301..307"),
    ("ST-050", "Battery pack assembly", 1, "-", "-", "make", "-", E(0, 0, 0), "-", "ST-601..611"),
    # ---- 2xx axis cartridges --------------------------------------------------------------
    ("ST-201", "Strain-wave reducer, hollow-shaft unit, size 14, 100:1 (az, roll)", 2, "steel/alu unit", "same; component set option", "buy", "Laifual LHT-14-100-U-III (alt: Leaderdrive, HD SHF-14-100-2UH)", U(260, 230, 185), "est", "listing range USD 180-588; quote needed"),
    ("ST-202", "Strain-wave reducer, hollow-shaft unit, size 17, 100:1 (alt)", 1, "steel/alu unit", "same; component set option", "buy", "Laifual LHT-17-100-U-III (alt: Leaderdrive, HD SHF-17-100-2UH)", U(300, 265, 215), "est", "listing range USD 180-588; quote needed"),
    ("ST-203", "Stepper motor NEMA 17, 1.8 deg, 42 N.cm, 1.5 A, 38 mm", 3, "-", "-", "buy", "StepperOnline 17HE15-1504S", U(5.93, 3.75, 3.30), "quoted", "1k price est"),
    ("ST-204", "GT2 pulley 20T, 9 mm belt, bore 5 mm, TIR <= 0.03", 3, "aluminium 6061", "aluminium 6061", "buy", "Misumi / Gates / JLCMC", U(2.5, 1.2, 0.8), "est", ""),
    ("ST-205", "GT2 pulley 60T, 9 mm belt, hollow bore, TIR <= 0.03", 3, "aluminium 6061", "aluminium 6061", "buy", "Misumi / Gates / JLCMC (bored to reducer input)", U(6, 3, 2), "est", "two bore sizes: size 14 and 17"),
    ("ST-206", "Timing belt 2GT, 200 mm closed loop (100 teeth), 9 mm wide", 3, "neoprene + glass fibre", "same", "buy", "Gates 2MGT-200-9", U(11, 5, 3.5), "est", "Gates 160-2MGT-06 quoted USD 10.96"),
    ("ST-207", "Motor plate with belt-tension slide", 3, "aluminium 6061 CNC", "aluminium 6061 CNC", "make", "JLCCNC", U(28, 9, 5), "est", ""),
    ("ST-208", "Encoder reference tube, dia 10, with magnet seat", 3, "stainless 304 turned", "stainless 304 turned", "make", "JLCCNC", U(9, 3, 1.5), "est", ""),
    ("ST-209", "Encoder magnet, dia 6 x 2.5, diametric, N35SH", 3, "NdFeB", "NdFeB", "buy", "LCSC / magnet supplier", U(1.5, 0.5, 0.3), "est", ""),
    ("ST-210", "Cartridge housing, size 14 (az, roll)", 2, "PAHT-CF printed", "aluminium 6061 CNC", "make", "own printer / JLC3DP MJF / JLCCNC", U(22, 25, 22), "est", ""),
    ("ST-211", "Cartridge housing, size 17 (alt)", 1, "PAHT-CF printed", "aluminium 6061 CNC", "make", "own printer / JLC3DP MJF / JLCCNC", U(30, 33, 28), "est", ""),
    ("ST-212", "Cartridge rear cover", 3, "ASA printed", "PA66-GF30 moulded", "make", "own printer / moulder", U(2, 7, 1.2), "est", ""),
    ("ST-213", "Rotary seal (V-ring) for axis gap", 3, "NBR", "NBR", "buy", "SKF / Trelleborg", U(3, 1.5, 1.0), "est", ""),
    # ---- 3xx structure, wedge, clamp -----------------------------------------------------
    ("ST-301", "Base plate with 3/8in-16 socket", 1, "aluminium 6061 CNC", "aluminium 6061 CNC, hard anodised", "make", "JLCCNC", U(45, 15, 9), "est", ""),
    ("ST-302", "Wedge lower plate with azimuth fine adjust", 1, "aluminium 6061 CNC", "aluminium 6061 CNC", "make", "JLCCNC", U(55, 18, 11), "est", ""),
    ("ST-303", "Wedge upper plate (azimuth reducer mount)", 1, "aluminium 6061 CNC", "aluminium 6061 CNC", "make", "JLCCNC", U(60, 20, 12), "est", ""),
    ("ST-304", "Wedge hinge pin, dia 8 h6", 1, "stainless ground", "stainless ground", "buy", "Misumi", U(4, 2, 1.2), "est", ""),
    ("ST-305", "Wedge latitude arc with clamp", 2, "aluminium 6061 CNC", "aluminium 6061 CNC", "make", "JLCCNC", U(30, 10, 6), "est", ""),
    ("ST-306", "Fine-adjust screw assembly M5 with knob", 2, "stainless + alu knob", "stainless + alu knob", "buy", "Misumi", U(12, 6, 4), "est", "latitude and azimuth"),
    ("ST-307", "3/8in-16 stainless thread bushing", 1, "stainless", "stainless", "buy", "camera hardware supplier", U(3, 1.5, 1), "est", ""),
    ("ST-310", "Azimuth body (main housing)", 1, "PAHT-CF printed", "aluminium 6061 CNC", "make", "own printer / JLC3DP MJF / JLCCNC", U(45, 50, 45), "est", ""),
    ("ST-311", "Tower (altitude housing)", 1, "PAHT-CF printed", "aluminium 6061 CNC", "make", "own printer / JLC3DP MJF / JLCCNC", U(42, 47, 40), "est", ""),
    ("ST-312", "Altitude arm", 1, "aluminium 6061 CNC", "aluminium 6061 CNC", "make", "JLCCNC", U(70, 22, 13), "est", "metal from prototype P1"),
    ("ST-313", "Roll shelf (L-arm) with clamp seat", 1, "aluminium 6061 CNC", "aluminium 6061 CNC", "make", "JLCCNC", U(65, 20, 12), "est", "metal from prototype P1"),
    ("ST-314", "Arca-Swiss clamp, 60 mm, screw type", 1, "aluminium", "aluminium (own design later)", "buy", "Leofoto / Sunwayfoto class", U(25, 12, 8), "est", ""),
    ("ST-315", "Front bezel with OLED window", 1, "ASA printed", "PC/ABS moulded", "make", "own printer / moulder", U(4, 9, 1.5), "est", ""),
    ("ST-316", "Button cap", 4, "TPU 95A printed", "silicone moulded", "make", "own printer / moulder", U(0.5, 0.6, 0.15), "est", ""),
    ("ST-317", "Battery bay tray", 1, "ASA printed", "PA66-GF30 moulded", "make", "own printer / moulder", U(6, 10, 1.5), "est", ""),
    ("ST-318", "Battery door with latch", 1, "ASA printed", "PA66-GF30 moulded", "make", "own printer / moulder", U(5, 9, 1.8), "est", ""),
    ("ST-319", "Top cover with GNSS window", 1, "ASA printed", "PC/ABS moulded", "make", "own printer / moulder", U(4, 8, 1.4), "est", ""),
    ("ST-320", "Cable guide / strain relief", 3, "TPU 95A printed", "TPU moulded", "make", "own printer / moulder", U(1, 1.2, 0.3), "est", ""),
    ("ST-321", "Bubble level, dia 12", 1, "-", "-", "buy", "generic", U(2, 1, 0.6), "est", ""),
    ("ST-322", "End-stop bumper", 4, "TPU 95A printed", "TPU moulded", "make", "own printer / moulder", U(0.5, 0.6, 0.2), "est", ""),
    # ---- 5xx electronics -----------------------------------------------------------------
    ("ST-501", "Mainboard: PCB, passives, inductors, EEPROM, ESD, assembly", 1, "FR-4 4-layer", "FR-4 4-layer", "make", "JLCPCB", U(91, 22, 13.9), "est", "ICs listed separately below"),
    ("ST-502", "Wi-Fi/BLE module ESP32-S3-WROOM-1-N16R8", 1, "-", "-", "buy", "Espressif via LCSC", U(5.21, 4.09, 3.90), "quoted", ""),
    ("ST-503", "Motion MCU RP2354A (RP2350A + 2 MB flash, A4 stepping)", 1, "-", "-", "buy", "Raspberry Pi", U(1.4, 1.2, 1.1), "est", "RP2350A quoted USD 1.10 / 0.90 / 0.80"),
    ("ST-504", "Stepper driver TMC2209-LA", 3, "-", "-", "buy", "ADI Trinamic via LCSC", U(3.24, 2.77, 2.0), "quoted", "1k price est"),
    ("ST-505", "Buck-boost charger BQ25792RQMR", 1, "-", "-", "buy", "TI via LCSC", U(1.76, 1.12, 1.00), "quoted", "TI list 1ku USD 2.52"),
    ("ST-506", "USB-C PD controller TPS25751D (port A, sink/source)", 1, "-", "-", "buy", "TI via LCSC", U(2.50, 1.60, 1.49), "quoted", "LCSC price for TPS25751S; D variant listed from USD 1.92"),
    ("ST-507", "USB-C PD source controller TPS25752A (port B, camera)", 1, "-", "-", "buy", "TI", U(2.5, 1.8, 1.5), "est", ""),
    ("ST-508", "Buck-boost converter TPS55288 (port B rail)", 1, "-", "-", "buy", "TI", U(3.0, 2.2, 1.8), "est", ""),
    ("ST-509", "12 V boost converter TPS61288", 1, "-", "-", "buy", "TI", U(2.0, 1.4, 1.1), "est", ""),
    ("ST-510", "3.3 V buck converter TPS62932", 1, "-", "-", "buy", "TI", U(0.8, 0.5, 0.4), "est", ""),
    ("ST-511", "GNSS module u-blox MAX-M10S", 1, "-", "-", "buy", "u-blox", U(16, 13, 11), "est", ""),
    ("ST-512", "GNSS patch antenna 25 x 25 mm", 1, "-", "-", "buy", "Taoglas class", U(3, 2, 1.5), "est", ""),
    ("ST-513", "Real-time clock RV-3028-C7 + 0.1 F backup capacitor", 1, "-", "-", "buy", "Micro Crystal", U(2.5, 1.8, 1.5), "est", ""),
    ("ST-514", "IMU LSM6DSV (accelerometer + gyro)", 1, "-", "-", "buy", "ST", U(3, 2.2, 1.8), "est", ""),
    ("ST-515", "Magnetometer MMC5983MA", 1, "-", "-", "buy", "MEMSIC", U(2.8, 2, 1.7), "est", ""),
    ("ST-516", "OLED display 1.3 in, 128 x 64, SH1106, I2C", 1, "-", "-", "buy", "generic", U(4, 3, 2.5), "est", ""),
    ("ST-517", "USB-C receptacle, sealed (IPX7 class)", 2, "-", "-", "buy", "GCT / Amphenol", U(3, 2, 1.5), "est", ""),
    ("ST-518", "Tact switch, sealed", 4, "-", "-", "buy", "C&K", U(0.6, 0.4, 0.3), "est", ""),
    ("ST-519", "Status LED, RGB", 1, "-", "-", "buy", "generic", U(0.3, 0.2, 0.15), "est", ""),
    ("ST-520", "Cartridge board: PCB, NTC, connectors, assembly", 3, "FR-4 2-layer", "FR-4 2-layer", "make", "JLCPCB", U(8, 3, 2), "est", "MT6835 listed separately"),
    ("ST-521", "Magnetic encoder MT6835GT, 21-bit", 3, "-", "-", "buy", "MagnTek via LCSC", U(6.75, 4.62, 4.0), "quoted", "1k price est"),
    ("ST-530", "Axis harness, JST-GH 15-way", 3, "-", "-", "make", "harness house", U(5, 2.5, 1.6), "est", ""),
    ("ST-531", "Power and battery-bay harness", 1, "-", "-", "make", "harness house", U(5, 2, 1.2), "est", ""),
    ("ST-532", "Shutter port: 2.5 mm jack + 2 optocouplers", 1, "-", "-", "buy", "generic", U(3, 1.5, 1), "est", ""),
    # ---- 6xx battery pack ----------------------------------------------------------------
    ("ST-601", "Li-ion cell Molicel INR-21700-P50B", 4, "-", "-", "buy", "NKON (EU)", E(4.95, 4.45, 3.80), "quoted", "1k price est"),
    ("ST-602", "Battery board: PCB, FETs, sense, LEDs, assembly", 1, "FR-4 2-layer", "FR-4 2-layer", "make", "JLCPCB", U(16.5, 6, 4.3), "est", ""),
    ("ST-603", "Fuel gauge + protector BQ40Z50-R2", 1, "-", "-", "buy", "TI", U(3.5, 2.6, 2.2), "est", "alt: BQ28Z610 quoted USD 1.55-2.32"),
    ("ST-604", "Second-level protector + fuse", 1, "-", "-", "buy", "TI / Dexerials", U(1.5, 1, 0.8), "est", ""),
    ("ST-605", "Pack shell, two halves", 1, "ASA printed", "PC/ABS FR moulded", "make", "own printer / moulder", U(5, 8, 1.6), "est", ""),
    ("ST-606", "Cell holder / spacer", 1, "ASA printed", "PC/ABS FR moulded", "make", "own printer / moulder", U(2, 3, 0.5), "est", ""),
    ("ST-607", "Nickel strip set", 1, "nickel 0.15 mm", "nickel 0.15 mm", "buy", "generic", U(1.5, 0.8, 0.5), "est", "spot-welded"),
    ("ST-608", "Battery blade connector, pack side, 5-way", 1, "-", "-", "buy", "Amphenol class", U(3, 2, 1.5), "est", ""),
    ("ST-609", "Battery blade connector, head side, 5-way", 1, "-", "-", "buy", "Amphenol class", U(3, 2, 1.5), "est", ""),
    ("ST-610", "Pack gasket", 1, "TPU 95A printed", "silicone moulded", "make", "own printer / moulder", U(1, 0.8, 0.4), "est", ""),
    ("ST-611", "Pack light pipe + button", 1, "clear PETG printed", "PC moulded", "make", "own printer / moulder", U(1, 0.8, 0.3), "est", ""),
    # ---- 7xx fasteners and standard parts -------------------------------------------------
    ("ST-701", "Screw set M3 (ISO 4762 / 7380), about 40 pcs", 1, "stainless A2", "stainless A4", "buy", "Bossard / Wurth", U(6, 2.5, 1.6), "est", "full list in Phase 3"),
    ("ST-702", "Screw set M4, about 24 pcs", 1, "stainless A2", "stainless A4", "buy", "Bossard / Wurth", U(4, 1.6, 1.0), "est", ""),
    ("ST-703", "Screw set M5, about 12 pcs", 1, "stainless A2", "stainless A4", "buy", "Bossard / Wurth", U(3, 1.2, 0.8), "est", ""),
    ("ST-704", "Heat-set insert set M3, about 30 pcs", 1, "brass", "not used (tapped aluminium)", "buy", "Ruthex / CNC Kitchen", U(4, 1.5, 0), "est", ""),
    ("ST-705", "Heat-set insert set M4/M5, about 16 pcs", 1, "brass", "not used (tapped aluminium)", "buy", "Ruthex / CNC Kitchen", U(3, 1.2, 0), "est", ""),
    ("ST-706", "Dowel pin set, dia 3 m6, 6 pcs", 1, "steel", "steel", "buy", "Misumi", U(2, 0.8, 0.5), "est", ""),
    ("ST-707", "Gasket and O-ring set", 1, "NBR / TPU", "silicone / EPDM", "buy", "generic", U(6, 3, 2), "est", ""),
    ("ST-708", "Thread locker and grease (per head)", 1, "-", "-", "buy", "Loctite / Kluber", U(2, 0.5, 0.3), "est", ""),
    # ---- 8xx accessories and packaging ----------------------------------------------------
    ("ST-801", "Hex key set 2 / 2.5 / 3 mm", 1, "-", "-", "buy", "generic", U(3, 1.5, 1), "est", ""),
    ("ST-802", "USB-C cable, 1 m, 60 W", 1, "-", "-", "buy", "generic", U(4, 2, 1.5), "est", ""),
    ("ST-803", "QR label set (maintenance guide links)", 1, "-", "-", "make", "label printer", U(1, 0.4, 0.2), "est", ""),
    ("ST-804", "Packaging box with foam", 1, "-", "-", "buy", "packaging supplier", U(6, 4, 3), "est", ""),
    ("ST-805", "Quick-start card", 1, "-", "-", "make", "printer", U(0.5, 0.3, 0.15), "est", ""),
]


def write_csv(path):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Name", "Qty per head", "Material (prototype)", "Material (production)", "Make/Buy", "Supplier",
                    "Unit price EUR @1", "Unit price EUR @100", "Unit price EUR @1000",
                    "Line total EUR @1", "Line total EUR @100", "Line total EUR @1000", "Price source", "Note"])
        for (pid, name, qty, mp, mq, mb, sup, pr, src, note) in PARTS:
            w.writerow([pid, name, qty, mp, mq, mb, sup, f"{pr[0]:.2f}", f"{pr[1]:.2f}", f"{pr[2]:.2f}",
                        f"{qty*pr[0]:.2f}", f"{qty*pr[1]:.2f}", f"{qty*pr[2]:.2f}", src, note])


def totals():
    t = [0.0, 0.0, 0.0]
    groups = {}
    for (pid, name, qty, mp, mq, mb, sup, pr, src, note) in PARTS:
        g = pid[3]
        for i in range(3):
            t[i] += qty * pr[i]
            groups.setdefault(g, [0.0, 0.0, 0.0])[i] += qty * pr[i]
    return t, groups


if __name__ == "__main__":
    import sys
    write_csv(sys.argv[1])
    print(totals())
