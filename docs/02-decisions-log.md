# Star Tracker Project — Decisions Log

Approved decisions, newest last. Every later phase must follow these unless Bruno changes them.

## 20 Nov 2026 — Phase 1 decisions (approved: "go with your recommendations")

| # | Topic | Decision |
|---|---|---|
| D1 | Product type | 3-axis motorised head (Azimuth → Altitude → Roll), Polaris / Asterra class |
| D2 | Drive train | Strain-wave (harmonic) reducers on all 3 axes: size 17 on altitude, size 14 on azimuth and roll, each fed by a NEMA 17 stepper through a 3:1 GT2 belt (about 300:1 overall). **Azimuth changed to size 17 by D17** |
| D3 | EQ mode | Built-in latitude wedge, so 300–600 mm lenses can track on a single axis |
| D4 | Rated payload | 7 kg (reference rig: Sony A7R V + Sony 200–600 ≈ 3.0–3.2 kg) |
| D5 | Lens range | Main target up to 300 mm; 600 mm usable with some drift that can be corrected |
| D6 | Camera control | v1 from the app (tablet or PC over USB-C, as Bruno's current app does); the head's hardware is ready for onboard camera control in v2 |
| D7 | Head interface | Small OLED + 4 buttons + status LED with a red night mode |
| D8 | Battery | Sealed, tool-free swappable 2S2P Molicel P50B 21700 pack (7.2 V, about 10 Ah, about 72 Wh) with BMS and fuel gauge; runs and charges from USB-C PD; USB-C PD output to power the camera |
| D9 | Sealing | IPX4 for the prototype, IPX6 for production |
| D10 | Electronics | ESP32-S3 for connectivity + a separate real-time motion MCU (RP2350 or STM32G4, final choice in Phase 2), 3× TMC2209, 3× MT6835 output encoders, IMU + magnetometer, GPS, RTC |
| D11 | Protocols | ASCOM Alpaca (Telescope + Rotator) and LX200 served by the head itself; WebSocket JSON for the apps; BLE for setup |
| D12 | Software | Firmware and apps written from scratch (no ogecko code). Bruno's own Benro-Polaris-Controller code (camera, plate solver, Holy Grail, Night, Blue Hour UI) may be reused. Apps for Android + Windows |
| D13 | Repairability | One hex-key set, M3/M4/M5 screws only, axis cartridges (4 screws + 1 plug), JST-GH connectors, standard bearings, belts and cells, QR codes to the maintenance guide |
| D14 | Repo | github.com/bmonte777/start-tracker-project (not variousapps) |
| D15 | Prototype equipment | Bruno owns no 3D printer or CNC. Plan: buy an enclosed printer with a heated chamber for printed parts (recommended: Bambu Lab H2S; cheaper options in the Phase 1 reply); get aluminium parts CNC-machined by a service (JLCCNC, or Xometry Europe for EU-based shops); use MJF PA12 / PA12-CF from a service for final-quality printed parts |
| D16 | Retail price | Not set yet. Phase 2 builds a cost model (1 / 100 / 1,000 units) to set it |

## 20 Nov 2026 — Phase 2 decisions (approved: "Approve all")

The reasoning and numbers are in `docs/02-engineering-spec.md`. The label in brackets is the item's name in that spec.

| # | Topic | Decision |
|---|---|---|
| D17 | Azimuth reducer size (CR1, changes D2) | Size 17 on azimuth instead of size 14. In EQ-wedge mode the azimuth axis carries up to 17.6 N·m at 7 kg, above the size-14 average-torque limit of 11 N·m. Sizes are now: azimuth 17, altitude 17, roll 14 |
| D18 | Reducer format (Q1) | Hollow-shaft housed units with crossed-roller output bearing: Laifual LHT-17-100-U-III (azimuth, altitude), LHT-14-100-U-III (roll). Encoder reference tube and cables run through the bore |
| D19 | Where the electronics sit (Q2) | Battery, boards and azimuth motor above the azimuth bearing: unlimited azimuth, no slip ring |
| D20 | Roll geometry (Q3) | Roll axis parallel to the lens axis and 130 mm from it for a lens on its foot; L-shaped shelf with Arca clamp |
| D21 | Wedge range (Q4) | Tilt 0–75° (latitudes 15–90° N and S), fine adjust 34′ per turn, locks flat for alt-az |
| D22 | Motion MCU (Q5) | Raspberry Pi RP2354A (RP2350A with 2 MB flash, A4 stepping). Closes the open choice in D10 |
| D23 | Motor and belt (Q6) | StepperOnline 17HE15-1504S on all axes; 20T:60T GT2, 9 mm wide, 200 mm closed belt. **Azimuth motor changed by D32** |
| D24 | Metal parts on prototype P1 (Q7) | Altitude arm and roll shelf CNC-machined in 6061 from the first prototype |
| D25 | Brake (Q8) | None. Low-battery park at 5 % and end-stop bumpers |
| D26 | Slew speed in the cold (Q9) | 8°/s down to 0 °C, 6°/s at −20 °C. **Cold limit to be re-checked under D33 in Phase 4** |
| D27 | Power chips (Q10) | BQ25792 + TPS25751D (port A), TPS25752A + TPS55288 (27 W camera port B), TPS61288 (12 V), TPS62932 (3.3 V), BQ40Z50-R2 in the pack. The BQ25792 / TPS25751D pairing is to be confirmed in Phase 4. **Motor rail raised to 16 V by D33** |
| D28 | Weight target (Q11) | Prototype P1 ≤ 6.1 kg, production ≤ 5.1 kg, weight-cutting pass in Phase 8. First approved as 5.8 kg and 4.9 kg; restated after the size-17 azimuth (D17) added 0.3 kg, and confirmed with D32. Revision C of the spec predicts 6.08 kg and 5.34 kg, so production depends on the Phase 8 pass |
| D29 | Printer, dryer, services (Q12) | Bambu Lab H2S + AMS HT; JLCCNC for aluminium, JLC3DP for MJF PA12, Xometry Europe as backup |
| D30 | Arca clamp on the prototype (Q13) | Buy a standard 60 mm clamp |
| D31 | Roll travel with long lenses (Q14) | Accept 155° of travel (+5° to −150°) with the 200–600 on its foot for prototype P1; study a wider payload offset or a raised roll axis in the Phase 3 CAD |

**D17 follow-up, done 20 Nov 2026:** revision B of the spec reran the calculations, mass budget, cost model and parts list with size 17 on azimuth (two ST-202, one ST-201).

## 20 Nov 2026 — Phase 2 follow-up decisions (approved: "Continue with recommendations")

| # | Topic | Decision |
|---|---|---|
| D32 | Azimuth motor (Q15, changes D23) | 48 mm StepperOnline 17HS19-2004S1 on azimuth only (part ST-214); altitude and roll keep the 38 mm 17HE15-1504S. Same mount, +110 g, about €3.50 more per head. At −20 °C a 7 kg load in the EQ extreme had a margin of 0.84 at 8°/s and 1.08 at 6°/s with the 38 mm motor; it has 1.23 and 1.51 with the 48 mm motor, so the cold limit of D26 holds for every load |

The restated weight target was confirmed in the same reply and is recorded in D28. Revision C of the spec carries D32 through the calculations, mass budget, power budget, cost model and parts list.

## 21 Nov 2026 — Phase 3 decisions

| # | Topic | Decision |
|---|---|---|
| D33 | Motor rail voltage (Q16, changes D27) | Motor rail raised from 12 V to 16 V, still from the TPS61288 boost converter (rated to 18 V). Lifts the 7 kg cold-slew margin at 8°/s from about 1.2 to about 1.6, so the 6°/s cold limit of D26 may be dropped. No mechanical part changes. The rerun of `phase2_calcs.py`, the power budget and the D26 review belong to Phase 4. Approved by Bruno: "yes, it can be 16V" |
| D34 | Roll axis offset (Q17, D31 study) | Roll axis 23 mm further from the azimuth axis (X 135.5 instead of 112.5). Roll travel +10° toward the tower to −145° away with the 200–600 on its foot; worst-case azimuth torque 19.45 N·m, 2.0× under the 39 N·m limit. Approved: "Yes, move it 23 mm" |
| D35 | Weight changes for P1 (Q21, changes D28) | Make W1–W5 to bring P1 to about 6.8 kg (mount without payload): body and tower walls 2.0 mm (W1) and printed in MJF PA12 by JLC3DP (W2); ribbed pockets under ST-302 and ST-303 (W3); 6061 encoder tubes (W4); Sunwayfoto DDC-60i clamp, 71 g (W5). Also 7075 aluminium screws for the reducer-to-housing joints and deeper pockets in ST-301 and ST-313. The cartridge housings stay PAHT-CF for torsional stiffness. Approved: "Make the changes to reach 6.8 kg". Payload rating stays 7 kg (D4); further weight options are open with Bruno |
| D36 | Arca clamp fixing (Q18, exception to D13) | One 3/8"-16 × 12 coin-slot screw (ST-330) fixes any standard clamp. Approved: "go with your recommendations" |
| D37 | Roll shelf cantilever (Q19) | 30 mm from the roll output face to the clamp centre instead of 75 mm. Approved: "go with your recommendations" |
| D38 | Wedge layout (Q20, refines D21) | Raised hinge with the latitude arcs hanging below it, two M5 clamp knobs, M3 tangent screw at R31 mm giving about 55′ per turn instead of 34′. Approved: "go with your recommendations" |

## 22 Nov 2026 — Phase 3 rev C decisions

| # | Topic | Decision |
|---|---|---|
| D39 | Removable wedge (Q21 option, changes D21 and D38) | The wedge comes off without tools: the head stands on a new head base plate (ST-303, Ø75 disc with its own pressed 3/8"-16 bushing) and sits on the wedge top plate (ST-331) on two Ø4 dowels (ST-333), held by one 3/8"-16 × 10 coin-slot screw from below (ST-332). For alt-az nights the wedge stays at home and the head screws straight onto any tripod. Head alone 6.21 kg, wedge 0.62 kg, both together 6.83 kg (the interface adds about 30 g). Approved: "I will go with the removable wedge" |
| D40 | Payload envelopes instead of one reference lens (refines D4, D31, D34) | The design is checked against five generic payloads, not one lens: P1 mirrorless + standard zoom on an L-plate (1.55 kg), P2 70-200 f/2.8 on its collar (1.95 kg), P3 150-600 class lens on its foot (3.75 kg), P4 72 mm refractor + astro camera (2.70 kg), P5 90 mm refractor at the full 7 kg. Each is balanced on the altitude axis within the clamp's reach, and swing, roll travel, tripod clearance (wedge on and off) and loads are reported for each. Roll limits are set per payload in the firmware. Direction from Bruno: "This tracker is not just for me and my gear". Approved: "Yes, the 5 payloads do cover almost all gear" |
| D41 | No further weight cutting for P1 (closes the options left open by D35) | P1 stays at 6.21 kg for the head alone and 6.83 kg with the wedge. Titanium screws, a 2S1P battery, a pocketed arm and shelf, and a size-14 azimuth reducer are not taken. The production weight pass of D28 (Phase 8) is not affected. Approved: "No more weight cutting" |

The FE 200-600 foot-height question is closed by D40: the design no longer depends on one lens.

## 22 Nov 2026 — Phase 4 decisions (approved: "Go with all recommendations")

The reasoning and numbers are in `docs/04-electronics.md` and `docs/calc/phase4_calcs.py`.

| # | Topic | Decision |
|---|---|---|
| D42 | Slew speed in the cold (Q22, changes D26) | 8°/s over the whole −20 to +40 °C range; the 6°/s cold limit is dropped. At 16 V (D33) and with the Phase 3 geometry (D34), a 7 kg load in the EQ extreme at −20 °C has a margin of 1.48 at 8°/s and 1.50 at 6°/s, so slowing down no longer helps. The firmware still lowers the slew speed by itself if StallGuard reports a high load |
| D43 | Two-level motor rail (Q23, refines D33) | The TPS61288 makes 16 V for slews and 10 V for tracking and holding, switched by one pin (VM_SEL, low = 10 V). On 16 V the drivers cannot regulate the small tracking currents: the StealthChop floor is 0.15 A on the 38 mm motors and 0.25 A on azimuth; on 10 V it is 0.10 A and 0.16 A |
| D44 | 5 V rail (Q24, extends D27) | A TPS563201 buck (3 A) supplies PP5V of both PD controllers: 5 V / 3 A on port B and the cable supply. The TPS25752A needs it; TI's own evaluation board has a separate 5 V converter |
| D45 | Inrush and reverse polarity (Q25) | A P-FET switch with soft start (MOTOR_PWR_EN) sits in front of the boost: 1.5 A inrush instead of about 62 A, and a true off for the motor rail. A second P-FET at the pack input blocks a reversed bench supply |
| D46 | Motor thermistor (Q26) | A 10 k B3950 bead on two wires, taped to the motor case and soldered to two pads on the cartridge board. A chip thermistor on the board would sit 58 mm from the motor; its footprint stays on the board, not fitted |
| D47 | Cartridge plug pinout (Q27) | JST-GH 15-way, the same at both ends: 1–2 phase A1, 3–4 phase A2, 5 GND, 6 CS, 7 SCK, 8 MOSI, 9 MISO, 10 thermistor, 11 +3.3 V, 12–13 phase B1, 14–15 phase B2. Wired by phase, not by lead colour: the 38 mm and 48 mm motors use different colours for the same phases (D32 check) |

D27 is confirmed: the TPS25751 datasheet lists the BQ25792 among the chargers its firmware drives.

## 22 Nov 2026 — Phase 4 follow-up decisions

| # | Topic | Decision |
|---|---|---|
| D48 | Encoder chip-to-magnet gap (Q29) | The encoder board stays where Phase 3 put it; carriers ST-212 and ST-216 are not changed. The gap is 0.81–0.82 mm with the real chip package, under the MT6835 datasheet's 1.0 mm minimum, so the encoder error is measured on the P0 bench (bring-up Stage D) before anything is changed. Approved: "Continue as it is" |
| D49 | USB-C sockets on the prototypes (Q30) | Upright GT-USB-7051A (LCSC C2843970), not sealed, about 1.5 mm proud of the bezel face. A sealed socket is looked at later if needed. Approved: "leave it unsealed for the prototype" |

## 22 Nov 2026 — Phase 4 mainboard decisions (approved: "Go with recommendations and continue")

| # | Topic | Decision |
|---|---|---|
| D50 | Battery rail on the mainboard (Q36) | The pack pads stay at the lower right, so no harness and no printed part changes. The rail crosses the board as one copper area 4.6 mm wide and about 94 mm long (about 10 mΩ: 0.36 W and 60 mV at the pack's 6 A limit); on the six-layer board of D51 it lies on inner layer 3 and both outer faces are free |
| D51 | Mainboard build (Q37) | Six layers instead of four, with filled and capped vias (via-in-pad), which JLCPCB makes at no extra charge from six layers up. Stack: front face signal, power, two signal layers, ground, inner face signal. The vias to the planes sit in the pads of the small parts; outline, parts and placement do not change. Reason: on four layers 98 of about 950 connections could not be closed in three router runs |

### Phase 4 — pending approval (not decisions yet)

The Phase 4 design carries on with the recommended option for each of these. Nothing that changes a printed or machined part has been changed.

| # | Question | Recommended, used in the design |
|---|---|---|
| Q28 | Clock backup | Seiko MS621FE rechargeable cell (about three months) instead of the 0.1 F capacitor (about two days) |
| Q31 | Buttons | TS-1187A (1.5 mm tall); the four printed button caps grow by 2 mm |
| Q32 | GNSS antenna | Active patch on a coax lead (U.FL socket on the board), flat under the top cover |
| Q33 | Shutter socket | Panel-mount 2.5 mm jack in the bezel, through a 9 mm cut-out in the mainboard, wired to plug J12 |
| Q34 | Status light | Three single-colour 0603 LEDs behind the light pipe instead of one RGB package |
| Q35 | Battery lead | Soldered to two pads on the mainboard, with an in-line XT30 |
| Q38 | Battery board fixing in the pack (changes printed parts ST-605 and ST-612) | A rib 7 mm wide with a 1.7 mm groove on the floor of the lower shell and one under the roof of the upper shell; the board's bottom and top edges sit in them. The board ST-602 keeps those edges free. Not changed in the CAD yet |
| Q39 | Pack light pipe and button (changes printed part ST-611) | The pipe ends 2.0 mm before the board, with a flat boss over the button, and slides 0.3 mm in its window to press it; a thin TPU lip on its flange keeps the window closed. Not changed in the CAD yet |
| Q40 | Wire passages in the pack (changes printed part ST-606) | A notch 6 × 3 mm at mid-height on the left and right edge of both cell holders: PACK+ on one side; PACK−, the three bus wires, the middle tap and the thermistor leads on the other. Not changed in the CAD yet |
| Q41 | Inner copper of the mainboard | Order 1 oz inner layers instead of JLCPCB's standard 0.5 oz: the battery rail on inner layer 3 then has about 10 mΩ instead of 20 mΩ (0.36 W instead of 0.72 W at the pack's 6 A limit). A small surcharge on the bare boards |

Also done since the last approval and reported here because they change the layout, not the circuit: small parts round the processor, the PD controllers and the drivers were moved to widen the free bands; slow-signal resistors and capacitors carry a via in their pad; the drivers' charge-pump and reference nets are routed with the slow signals.
