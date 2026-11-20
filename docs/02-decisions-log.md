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
| D23 | Motor and belt (Q6) | StepperOnline 17HE15-1504S on all axes; 20T:60T GT2, 9 mm wide, 200 mm closed belt |
| D24 | Metal parts on prototype P1 (Q7) | Altitude arm and roll shelf CNC-machined in 6061 from the first prototype |
| D25 | Brake (Q8) | None. Low-battery park at 5 % and end-stop bumpers |
| D26 | Slew speed in the cold (Q9) | 8°/s down to 0 °C, 6°/s at −20 °C |
| D27 | Power chips (Q10) | BQ25792 + TPS25751D (port A), TPS25752A + TPS55288 (27 W camera port B), TPS61288 (12 V), TPS62932 (3.3 V), BQ40Z50-R2 in the pack. The BQ25792 / TPS25751D pairing is to be confirmed in Phase 4 |
| D28 | Weight target (Q11) | Approved as prototype P1 ≤ 5.8 kg, production ≤ 4.9 kg, weight-cutting pass in Phase 8. The size-17 azimuth (D17) adds 0.3 kg, so revision B of the spec restates it as P1 ≤ 6.1 kg, production ≤ 5.1 kg. **Restated figures await Bruno's confirmation** |
| D29 | Printer, dryer, services (Q12) | Bambu Lab H2S + AMS HT; JLCCNC for aluminium, JLC3DP for MJF PA12, Xometry Europe as backup |
| D30 | Arca clamp on the prototype (Q13) | Buy a standard 60 mm clamp |
| D31 | Roll travel with long lenses (Q14) | Accept 155° of travel (+5° to −150°) with the 200–600 on its foot for prototype P1; study a wider payload offset or a raised roll axis in the Phase 3 CAD |

**D17 follow-up, done 20 Nov 2026:** revision B of the spec reruns the calculations, mass budget, cost model and parts list with size 17 on azimuth (two ST-202, one ST-201).

## Awaiting Bruno's approval

Not decisions yet.

| # | Question | Recommendation |
|---|---|---|
| Q15 | Motor on azimuth | 48 mm StepperOnline 17HS19-2004S1 on azimuth only (same mount, +110 g). The size-17 reducer drags more in the cold: at −20 °C a 7 kg load in the EQ extreme has a margin of 0.84 at 8°/s and 1.08 at 6°/s with the 38 mm motor of D23, against 1.23 and 1.55 with the 48 mm motor. Until decided, the spec keeps the 38 mm motor on all axes |
| D28 restated | Weight target after D17 | Prototype P1 ≤ 6.1 kg, production ≤ 5.1 kg |
