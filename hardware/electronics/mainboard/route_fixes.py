"""ST-501: corrections laid by hand on top of the routing result of 23 Nov 2026 (router + closing pass).

Applied by `python3 tools/fixroutes.py mainboard`; each stage is applied once and recorded in the routes file. The
coordinates are board coordinates (mm, X right, Y up, seen from the front). They belong to this routing result: after a
new router run this list has to be emptied and the remaining opens looked at afresh.
"""
ROUTES = "st-501.routes.json"

STAGES = [
    # RP2354A pins 24-26 (SWCLK, SWDIO, RUN) had no way out: the channel below them was crossed on the front face by
    # LINK_SYNC. That track moves 1.35 mm south; the three pins go straight down to three staggered vias.
    ("u14-swd", [
        ("drop", "LINK_SYNC", "F", (11.0, -11.75), (18.2, -11.75)), ("drop", "LINK_SYNC", "F", (18.2, -11.75), (18.75, -11.2)),
        ("track", "LINK_SYNC", "F", 0.15, [(11.0, -11.75), (12.35, -13.1), (17.4, -13.1), (18.75, -11.75), (18.75, -11.2)]),
        ("track", "RP_RUN", "B", 0.15, [(15.8, -9.95), (15.8, -11.1), (15.43, -11.47), (15.43, -11.65)]), ("via", "RP_RUN", (15.43, -11.65)),
        ("track", "RP_SWDIO", "B", 0.15, [(16.2, -9.95), (16.2, -11.85), (15.6, -12.45)]), ("via", "RP_SWDIO", (15.6, -12.45)),
        ("track", "RP_SWCLK", "B", 0.15, [(16.6, -9.95), (16.6, -12.39), (16.44, -12.55)]), ("via", "RP_SWCLK", (16.44, -12.55)),
    ]),
    # C14 (system rail capacitor of the charger) was fenced in by CHG_ILIM on its own face: a via in its pad to the
    # system-rail areas on inner layers 1 and 2; CHG_TS on the front face steps 0.45 mm north to make room for it.
    # CHG_TS: the via at the corner of pin 16 gets a short track to the pad's centre (KiCad wants one).
    ("c14", [
        ("drop", "CHG_TS", "F", (-26.45, 4.05), (-29.45, 4.05)), ("drop", "CHG_TS", "F", (-29.45, 4.05), (-31.4, 6.0)),
        ("track", "CHG_TS", "F", 0.15, [(-26.45, 4.05), (-28.0, 4.05), (-28.45, 4.5), (-29.9, 4.5), (-31.4, 6.0)]),
        ("via", "VSYS", (-29.1, 3.9)), ("track", "VSYS", "B", 0.3, [(-29.3, 3.55), (-29.1, 3.9)]),
        ("track", "CHG_TS", "B", 0.15, [(-26.15, 4.35), (-25.85, 4.9)]),
    ]),
    # PDA_IRQC at the charger's pin 21: out to the west between pin 20's resistor and the battery area to a via, on
    # inner layer 2 to a second via south of the charger, on the front face to the track that was already there.
    # The ground tie of R9 moves 0.08 mm south for the first via.
    ("pda-irqc", [
        ("drop", "GND", "B", (-28.1, 6.2), (-30.3, 6.2)), ("drop", "GND", "B", (-30.3, 6.2), (-31.2, 7.1)),
        ("track", "GND", "B", 0.3, [(-28.1, 6.12), (-30.22, 6.12), (-31.2, 7.1)]),
        ("track", "PDA_IRQC", "B", 0.15, [(-25.9, 6.87), (-28.4, 6.87), (-28.6, 6.72)]), ("via", "PDA_IRQC", (-28.6, 6.72)),
        ("track", "PDA_IRQC", "In2", 0.15, [(-28.6, 6.72), (-28.6, 5.9), (-25.1, 2.4), (-24.32, 2.4)]), ("via", "PDA_IRQC", (-24.32, 2.4)),
        ("track", "PDA_IRQC", "F", 0.15, [(-24.32, 2.4), (-24.32, 1.02), (-22.5, -0.8)]),
    ]),
    # Port B controller, left pin row (D+ on pin 22 had no way out: three vias do not fit beside pins 21-23 with the
    # inner-layer track of the 3.3 V regulator pin behind them). The gate drive PB_GVSYS loses its hop over the front
    # face and stays on the inner face; D- gets its via further west, on its track to TP24, and comes back on the front
    # face to its old track to the socket; D+ passes above the one via left beside the pins to a via of its own and runs
    # on inner layer 3 to a via on its front-face track at TP23.
    ("u6-dp", [
        ("drop", "PB_GVSYS", "B", (-44.1, -5.8), (-44.3, -5.6)), ("drop", "PB_GVSYS", "F", (-44.3, -5.6), (-44.85, -5.05)),
        ("drop", "PB_GVSYS", "F", (-44.85, -5.05), (-44.85, -4.8)), ("drop", "PB_GVSYS", "In2", (-44.85, -4.8), (-44.9, -4.75)),
        ("drop", "PB_GVSYS", "B", (-44.85, -4.8), (-45.7, -3.95)), ("dropvia", "PB_GVSYS", (-44.3, -5.6)), ("dropvia", "PB_GVSYS", (-44.85, -4.8)),
        ("track", "PB_GVSYS", "B", 0.15, [(-44.1, -5.8), (-45.7, -4.2), (-45.7, -3.95)]),
        ("dropvia", "B_DN", (-43.1, -4.45)), ("drop", "B_DN", "B", (-43.1, -4.45), (-43.1, -4.5)), ("drop", "B_DN", "B", (-43.1, -4.5), (-44.0, -4.5)),
        ("drop", "B_DN", "B", (-44.0, -4.5), (-45.35, -3.15)), ("drop", "B_DN", "F", (-42.15, -5.4), (-43.1, -4.45)),
        ("track", "B_DN", "B", 0.15, [(-43.1, -4.5), (-43.5, -4.5), (-43.75, -4.25), (-44.75, -4.25), (-44.87, -4.13), (-45.35, -3.65), (-45.35, -3.15)]),
        ("via", "B_DN", (-44.87, -4.13)), ("track", "B_DN", "F", 0.2, [(-44.87, -4.13), (-43.42, -4.13), (-42.15, -5.4)]),
        ("track", "B_DP", "B", 0.15, [(-42.0, -4.82), (-44.14, -4.82), (-44.27, -4.95)]), ("via", "B_DP", (-44.27, -4.95)),
        ("track", "B_DP", "In3", 0.15, [(-44.27, -4.95), (-45.0, -4.95), (-45.45, -4.5), (-45.45, -0.5), (-44.7, 0.25), (-44.7, 2.9),
                                        (-43.9, 3.7), (-43.0, 3.7)]),
        ("via", "B_DP", (-43.0, 3.7)),
    ]),
    # Power paths: the sense resistor's VPB pad and the VBUS_CHG capacitor C19 were joined to their inner-layer areas
    # only by thin tracks to vias beside the pad. Vias in the pads now.
    ("power-pad-vias", [
        ("via", "VPB", (-36.45, 14.575)), ("via", "VPB", (-35.85, 13.975)), ("via", "VPB", (-35.55, 15.2)),
        ("via", "VBUS_CHG", (-21.2, -0.25)), ("via", "VBUS_CHG", (-19.75, -0.75)), ("via", "VBUS_CHG", (-19.1, -0.1)),
    ]),
    # the three RP2354A vias above joined to the rest of their nets on free cells (tools/closeonly.py)
    ("u14-swd-join", [
        ("track", "RP_RUN", "In3", 0.15, [(7.700, -21.150), (8.600, -20.250)]),
        ("track", "RP_RUN", "In3", 0.15, [(8.600, -20.250), (9.900, -20.250)]),
        ("track", "RP_RUN", "In3", 0.15, [(9.900, -20.250), (11.400, -18.750)]),
        ("track", "RP_RUN", "In3", 0.15, [(11.400, -18.750), (11.450, -18.750)]),
        ("track", "RP_RUN", "F", 0.15, [(11.450, -18.750), (11.700, -18.500)]),
        ("track", "RP_RUN", "F", 0.15, [(11.700, -18.500), (11.700, -17.450)]),
        ("track", "RP_RUN", "B", 0.15, [(11.700, -17.450), (12.450, -16.700)]),
        ("track", "RP_RUN", "B", 0.15, [(12.450, -16.700), (12.450, -16.450)]),
        ("track", "RP_RUN", "In2", 0.15, [(12.450, -16.450), (12.450, -14.650)]),
        ("track", "RP_RUN", "In2", 0.15, [(12.450, -14.650), (15.450, -11.650)]),
        ("via", "RP_RUN", (11.450, -18.750)),
        ("via", "RP_RUN", (11.700, -17.450)),
        ("via", "RP_RUN", (12.450, -16.450)),
        ("track", "RP_SWDIO", "In2", 0.15, [(15.600, -12.450), (16.050, -12.900)]),
        ("track", "RP_SWDIO", "In2", 0.15, [(16.050, -12.900), (16.050, -17.100)]),
        ("track", "RP_SWDIO", "In2", 0.15, [(16.050, -17.100), (15.500, -17.650)]),
        ("track", "RP_SWDIO", "In2", 0.15, [(15.500, -17.650), (15.500, -18.450)]),
        ("track", "RP_SWDIO", "B", 0.15, [(15.500, -18.450), (14.250, -19.700)]),
        ("track", "RP_SWDIO", "B", 0.15, [(14.250, -19.700), (13.950, -19.700)]),
        ("via", "RP_SWDIO", (15.500, -18.450)),
        ("track", "RP_SWCLK", "In2", 0.15, [(16.450, -12.550), (16.450, -17.150)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(16.450, -17.150), (17.550, -18.250)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(17.550, -18.250), (17.550, -18.300)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(17.550, -18.300), (17.650, -18.400)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(17.650, -18.400), (17.650, -18.450)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(17.650, -18.450), (18.150, -18.950)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(18.150, -18.950), (18.400, -18.950)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(18.400, -18.950), (18.650, -19.200)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(18.650, -19.200), (18.650, -20.000)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(18.650, -20.000), (18.350, -20.300)]),
        ("track", "RP_SWCLK", "In2", 0.15, [(18.350, -20.300), (18.350, -20.900)]),
        ("track", "RP_SWCLK", "In3", 0.15, [(18.350, -20.900), (17.700, -21.550)]),
        ("track", "RP_SWCLK", "In3", 0.15, [(17.700, -21.550), (17.700, -21.850)]),
        ("via", "RP_SWCLK", (18.350, -20.900)),
    ]),
    # tidying: two MAG_CAP vias 0.35 mm apart lead nowhere (the track on the back face ends in C132's pad): both go;
    # three vias that touch their net on one layer only are taken out
    ("tidy", [
        ("dropvia", "MAG_CAP", (-5.4, 20.6)), ("drop", "MAG_CAP", "F", (-5.4, 20.6), (-5.75, 20.6)),
        ("track", "MAG_CAP", "B", 0.15, [(-5.4, 20.6), (-5.75, 20.6)]), ("dropvia", "MAG_CAP", (-5.75, 20.6)),
        ("dropvia", "OLED_P1", (-4.7, 25.25)), ("dropvia", "PDA_DRAIN", (-24.3, -3.4)), ("dropvia", "PDB_IRQC", (-33.35, 16.55)),
        ("drop", "PDA_DRAIN", "B", (-24.25, -3.45), (-24.3, -3.4)),
    ]),
]
