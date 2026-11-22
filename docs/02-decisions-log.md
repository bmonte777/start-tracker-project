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

Still open: Bruno to measure the FE 200-600 foot height (lens axis to Arca base); 85 mm assumed.
