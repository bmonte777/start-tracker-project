"""Parts catalogue shared by the three boards: one LCSC number per value, so the BOMs stay consistent.

Each entry: value -> (footprint key or full footprint, manufacturer part, LCSC number).
Every LCSC number here was confirmed on 22 Nov 2026 against JLCPCB's parts library (jlcsearch.tscircuit.com, lcsc.com)
or against the same manufacturer-part / LCSC pair in public KiCad projects. A blank number means "not confirmed":
the BOM then carries the manufacturer part or the value only, and the part is picked in JLCPCB's parts matcher
when the BOM is uploaded. Never fill a number in from memory.
"""

R = {  # 0402, 1 % unless noted
    "0R": ("R0402", "0402WGF0000TCE", "C17168"), "10R": ("R0402", "0402WGF100JTCE", "C25077"), "33R": ("R0402", "0402WGF330JTCE", "C25105"),
    "100R": ("R0402", "0402WGF1000TCE", "C25076"), "330R": ("R0402", "0402WGF3300TCE", "C25104"), "470R": ("R0402", "0402WGF4700TCE", "C25117"),
    "1k": ("R0402", "0402WGF1001TCE", "C11702"), "2k2": ("R0402", "0402WGF2201TCE", "C25879"), "3k3": ("R0402", "0402WGF3301TCE", "C25890"),
    "4k7": ("R0402", "0402WGF4701TCE", "C25900"), "5k1": ("R0402", "0402WGF5101TCE", "C25905"), "5k23": ("R0402", "RC0402FR-075K23L", "C477746"),
    "6k19": ("R0402", "RC0402FR-076K19L", "C112297"), "8k2": ("R0402", "0402WGF8201TCE", "C25924"), "10k": ("R0402", "0402WGF1002TCE", "C25744"),
    "14k3": ("R0402", "RC0402FR-0714K3L", "C185465"), "15k": ("R0402", "0402WGF1502TCE", "C25756"), "20k": ("R0402", "0402WGF2002TCE", "C25765"),
    "23k2": ("R0402", "RC0402FR-0723K2L", "C163477"), "26k7": ("R0402", "RC0402FR-0726K7L", "C138023"), "30k1": ("R0402", "RC0402FR-0730K1L", "C138009"),
    "31k6": ("R0402", "RC0402FR-0731K6L", "C276265"), "33k": ("R0402", "0402WGF3302TCE", "C25779"), "36k5": ("R0402", "RC0402FR-0736K5L", "C15011"),
    "44k2": ("R0402", "RC0402FR-0744K2L", "C354260"), "49k9": ("R0402", "0402WGF4992TCE", "C25897"), "54k9": ("R0402", "RC0402FR-0754K9L", "C137959"),
    "84k5": ("R0402", "RC0402FR-0784K5L", "C185390"), "100k": ("R0402", "0402WGF1003TCE", "C25741"), "365k": ("R0402", "RC0402FR-07365KL", "C276268"),
    "0R15": ("R1206", "0.15 ohm 1 % 0.5 W current sense", ""), "0R01": ("R1206", "0.010 ohm 1 % 1 W current sense", ""),
    # confirmed 23 Nov 2026 on lcsc.com (product pages C26086 and C2904209)
    "10M": ("R0402", "0402WGJ0106TCE", "C26086"), "0R001": ("R1206", "HoJLR1206-1W-1mR-1%", "C2904209"),
}

C = {
    "22p": ("C0402", "0402CG220J500NT", "C1555"), "27p": ("C0402", "CL05C270JB5NNNC", "C1557"), "39p": ("C0402", "39 pF C0G 50 V 0402", ""),
    "47p": ("C0402", "0402CG470J500NT", "C1567"), "100p": ("C0402", "CL05C101JB5NNNC", "C1546"), "220p": ("C0402", "0402B221K500NT", "C1530"),
    "1n": ("C0402", "0402B102K500NT", "C1523"), "10n": ("C0402", "CL05B103KB5NNNC", "C15195"), "15n": ("C0402", "15 nF X7R 50 V 0402", ""),
    "22n": ("C0402", "CL05B223KB5NNNC", "C1532"), "47n": ("C0402", "47 nF X7R 25 V 0402", ""), "100n": ("C0402", "CL05B104KO5NNNC", "C1525"),
    "100n50": ("C0402", "CL05B104KB54PNC", "C307331"), "1u": ("C0402", "CL05A105KA5NQNC", "C52923"), "2u2": ("C0603", "CL10A225KO8NNNC", "C23630"),
    "4u7": ("C0603", "CL10A475KO8NNNC", "C19666"), "10u": ("C0603", "CL10A106KP8NNNC", "C19702"), "22u": ("C0805", "CL21A226MAQNNNE", "C45783"),
    "10u50": ("C1206", "CL31A106KBHNNNE", "C13585"),
}

PART = {  # active parts, connectors, magnetics
    "BQ25792": ("Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", "BQ25792RQMR", "C2862876"),
    "TPS25751D": (None, "TPS25751DREFR", ""),
    "TPS25752A": (None, "TPS25752ASRSMR", ""),
    "TPS55288": (None, "TPS55288RPMR", ""),
    "TPS61288": (None, "TPS61288RQQR", "C5219223"),
    "TPS62932": ("Package_TO_SOT_SMD:SOT-583-8", "TPS62932DRLR", "C3032935"),
    "TPS563201": ("Package_TO_SOT_SMD:TSOT-23-6", "TPS563201DDCR", "C116592"),
    "ESP32": ("ST:ESP32-S3-WROOM-1_BodyCourtyard", "ESP32-S3-WROOM-1-N16R8", "C2913202"),
    "RP2354A": (None, "RP2354A", "C41378174"),
    "TMC2209": ("Package_DFN_QFN:VQFN-28-1EP_5x5mm_P0.5mm_EP3.7x3.7mm_ThermalVias", "TMC2209-LA-T", "C465949"),
    "MT6835": (None, "MT6835GT-STD-R", "C2932578"),
    "LSM6DSV": ("Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y", "LSM6DSVTR", ""),
    "MMC5983MA": (None, "MMC5983MA", "C404329"),
    "RV3028": (None, "RV-3028-C7 32.768kHz 1ppm TA QC", ""),
    "MAXM10S": (None, "MAX-M10S-00B", ""),
    "BQ40Z50": (None, "BQ40Z50RSMR-R2", "C2845123"),
    "EEPROM": ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "CAT24C512WI-GT3", "C79986"),
    "SRV05": ("Package_TO_SOT_SMD:SOT-23-6", "SRV05-4.TCT", "C2687126"),
    "TLP291": ("Package_SO:SOIC-4_4.55x2.6mm_P1.27mm", "TLP291(GB-TP,SE", "C55144"),
    "PFET": ("Package_DFN_QFN:DFN-8-1EP_3x3mm_P0.65mm_EP1.55x2.4mm", "AON7403", "C5310961"),
    "NFET": ("Package_DFN_QFN:DFN-8-1EP_3x3mm_P0.65mm_EP1.55x2.4mm", "AON7400A", "C85734"),
    "NFET_S": ("Package_TO_SOT_SMD:SOT-23", "2N7002", "C8545"),
    "ZENER12": ("Diode_SMD:D_SOD-323", "BZT52C12S", "C14643"),
    "TVS24": ("Diode_SMD:D_SMB", "SMBJ24A", "C353373"),
    "TVS12": ("Diode_SMD:D_SMB", "SMBJ12A-TR", "C133677"),
    "ESD24": ("Diode_SMD:D_SOD-323", "PESD24VS1UB", ""),
    "ESD5": ("Diode_SMD:D_SOD-523", "ESD5Z5.0T1G", ""),
    "L4u7": ("Inductor_SMD:L_Sunlord_MWSA0603S", "MWSC0630H4R7MT", "C2991788"),
    "L2u2": ("Inductor_SMD:L_Sunlord_MWSA0603S", "MWSC0630H2R2MT", ""),
    "L6u8": ("Inductor_SMD:L_Sunlord_SWPA5040S", "SWPA5040S6R8MT", "C36411"),
    "L3u3": ("Inductor_SMD:L_0805_2012Metric", "AOTA-B201610S3R3-101-T", ""),
    "L47n": ("Inductor_SMD:L_0402_1005Metric", "LQG15HS47NJ02D", "C97998"),
    "FB": ("Inductor_SMD:L_0603_1608Metric", "BLM18PG121SN1D", "C14709"),
    "XTAL12": ("Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "X322512MSB4SI", "C9002"),
    "CP100u25": ("Capacitor_SMD:CP_Elec_6.3x7.7", "100 uF 25 V polymer hybrid", ""),
    "CP47u25": ("Capacitor_SMD:CP_Elec_6.3x5.8", "47 uF 25 V polymer", ""),
    "CP100u10": ("Capacitor_SMD:CP_Elec_6.3x5.8", "100 uF 10 V polymer", ""),
    "RTCBAT": ("Battery:BatteryHolder_Seiko_MS621F", "MS621FE-FL11E", ""),
    "LED_R": ("LED_SMD:LED_0603_1608Metric", "KT-0603R", "C2286"), "LED_G": ("LED_SMD:LED_0603_1608Metric", "19-217/GHC-YR1S2/3T", "C72043"),
    "LED_B": ("LED_SMD:LED_0603_1608Metric", "19-217/BHC-ZL1M2RY/3T", "C72041"),
    "TACT": ("Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", "TS-1187A-B-A-B", "C318884"),
    "USBC": ("Connector_USB:USB_C_Receptacle_G-Switch_GT-USB-7051x", "GT-USB-7051A", "C2843970"),
    "GH15H": ("Connector_JST:JST_GH_SM15B-GHS-TB_1x15-1MP_P1.25mm_Horizontal", "SM15B-GHS-TB(LF)(SN)", "C265027"),
    "GH15V": ("ST:JST_GH_BM15B-GHS-TBT_1x15-1MP_P1.25mm_Vertical_3D", "BM15B-GHS-TBT(LF)(SN)", "C5305069"),
    "GH4H": ("Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal", "SM04B-GHS-TB(LF)(SN)", "C189895"),
    "GH3H": ("Connector_JST:JST_GH_SM03B-GHS-TB_1x03-1MP_P1.25mm_Horizontal", "SM03B-GHS-TB(LF)(SN)", "C514175"),
    "PH4V": ("ST:JST_PH_B4B-PH-SM4-TB_1x04-1MP_P2.00mm_Vertical_3D", "B4B-PH-SM4-TB(LF)(SN)", "C160354"),
    "XT30": ("Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal", "XT30PW-M", "C431092"),
    "UFL": ("Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", "U.FL-R-SMT-1(80)", "C88374"),
    "BATPADS": ("ST:WirePads_1x02_P5.0mm_3.5x5mm", "battery lead pads", ""),
    "NTC": ("Resistor_SMD:R_0603_1608Metric", "10 k B3950 NTC 0603", ""),
    # battery board ST-602. Confirmed 23 Nov 2026: BQ294700DSGR on lcsc.com (C414622), BAT54WS (JSCJ) on jlcpcb.com (C2991936).
    # The fuse ITV4030L0815 (2-cell) is not in LCSC's catalogue (only the 4-cell L1415 is): no number, bought from DigiKey / Mouser.
    "BQ2947": ("Package_SON:WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm", "BQ294700DSGR", "C414622"),
    "BAT54": ("Diode_SMD:D_SOD-323", "BAT54WS", "C2991936"),
    "FUSE3T": ("ST:Fuse_Littelfuse_ITV4030", "ITV4030L0815NR", ""),
}


def fields(kind, key):
    fp, mpn, lcsc = {"R": R, "C": C, "P": PART}[kind][key][:3]
    f = {"MPN": mpn}
    if lcsc and not lcsc.endswith("X"):
        f["LCSC"] = lcsc
    return fp, f
