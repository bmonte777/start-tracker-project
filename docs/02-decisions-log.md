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

## 23 Nov 2026 — Phase 4 open questions (approved: "Q28-Q41 - proceed with recommendations")

| # | Topic | Decision |
|---|---|---|
| D52 | Clock backup (Q28) | Seiko MS621FE rechargeable cell (about three months) instead of the 0.1 F capacitor (about two days) |
| D53 | Buttons (Q31) | TS-1187A (1.5 mm tall); the four printed button caps grow by 2 mm |
| D54 | GNSS antenna (Q32) | Active patch on a coax lead (U.FL socket on the board), flat under the top cover |
| D55 | Shutter socket (Q33) | Panel-mount 2.5 mm jack in the bezel, through a 9 mm cut-out in the mainboard, wired to plug J12 |
| D56 | Status light (Q34) | Three single-colour 0603 LEDs behind the light pipe instead of one RGB package |
| D57 | Battery lead (Q35) | Soldered to two pads on the mainboard, with an in-line XT30 |
| D58 | Battery board fixing in the pack (Q38; printed parts ST-605 and ST-612) | A rib 7 mm wide with a 1.7 mm groove on the floor of the lower shell and one under the roof of the upper shell; the board's bottom and top edges sit 2 mm deep in them, no screws. To give the ribs a printable wall on the cell side (1.45 mm), the board stands 1.6 mm behind the cell holder instead of 0.6 mm. In the CAD since 23 Nov |
| D59 | Pack light pipe and button (Q39; printed part ST-611) | The pipe ends 2.0 mm before the board, with a flat boss over the button 0.3 mm from its top (switch 1.5 mm tall), and slides 0.3 mm in its window to press it. A flange behind the wall keeps it in; a TPU lip 0.5 mm thick, printed onto the flange, closes the window. In the CAD since 23 Nov |
| D60 | Wire passages in the pack (Q40; printed part ST-606) | A notch 6 × 3 mm at mid-height on the left and right edge of both cell holders: PACK+ on one side; PACK−, the three bus wires, the middle tap and the thermistor leads on the other. In the CAD since 23 Nov |
| D61 | Inner copper of the mainboard (Q41) | 1 oz inner layers instead of JLCPCB's standard 0.5 oz: the battery rail on inner layer 3 then has about 10 mΩ instead of 20 mΩ (0.36 W instead of 0.72 W at the pack's 6 A limit). A small surcharge on the bare boards |

## 23 Nov 2026 — Phase 4 width-check decisions (approved: "Q42 and Q43 - Continue with your recommendation")

| # | Topic | Decision |
|---|---|---|
| D62 | Narrow pins in the mainboard's power-path width check (Q42) | Three places are accepted as they are, each written into the check (`POWER_PATHS` in `mainboard/design.py`) with its own allowance instead of the standard 0.8 mm: the VBUS pins of both USB-C sockets (0.3 mm wide, between the shell pins and the CC and data pins), where wide copper may begin within 1.5 mm of the row A pins and within 2.9 mm of the row B pins, which reach it through the row A pin opposite (each pin carries a quarter of the port current, 0.75 A at 3 A); and pad 25 of the port B converter TPS55288, under the package and reached through pin 21 (TI's own land pattern), within 1.1 mm |
| D63 | Ends of a power path (Q43) | Pins that only sense or supply the chip itself are not ends of a power path: the charger's input path ends at its two VBUS pins (2 and 3), not at the sense pin VAC2 (8); pin 7 of the boost converter TPS61288 (its own supply, a few milliamps) is not an end of the motor-rail input |

Reported here because they change the layout, not the circuit (23 Nov): the port A controller is turned by 180° so that its two power pins face east; the charger and its coil moved 3 mm east, with the coil above the chip; the port B output switch (Q2, Q3) stands at the west edge, 2.6 mm from the controller; the motor switch Q6 and the boost coil L5 moved next to each other east of the boost converter; the sense resistor R23 stands right below the port B converter; the shutter opto-coupler U26 is on the front face behind plug J12; the port B memory chip U8 moved to the upper left. The inner power layer carries, besides 3.3 V and the system and motor rails, one area each for the two USB VBUS rails, the charger input, the port B output and 5 V.

Later the same evening, while finishing the mainboard (layout only, no circuit change): the port B controller U6 moved 1 mm further east, which leaves the port B switch Q2–Q3 about 3.6 mm from its pin row; on both USB-C sockets the four data vias moved into the data pads (the socket's footprint forbids front-face copper just beyond those pins); C2–C4 of the charger sit on the front face at the charger's under-chip vias. The mainboard passes both checks (design rules: 0 errors, 0 open; power-path widths: 17 of 17) with Q42 and Q43 as recommended.

## 23 Nov 2026 — Phase 5 firmware decisions (approved: "Q44–Q51 - Go with recommended")

The reasoning is in `docs/05-firmware.md` sections 2 and 3.

| # | Topic | Decision |
|---|---|---|
| D64 | Toolchains and language (Q44) | ESP-IDF 5.5 (C++17) on the ESP32-S3, Pico SDK 2.3 (C11) on the RP2354A. Motion logic, maths and protocol handlers are portable C/C++, so the PC simulator builds the same source. Rust not taken (its BLE, HTTP and OTA stacks are less mature) |
| D65 | RP2354A core and PIO split (Q45) | Core 1 runs only a hard 1 kHz motion tick (profiles, tracking, PEC, step planning, and the 5 Hz encoder correction inside it). Core 0 runs the link, the 1 kHz encoder reads, the driver UART, safety and the ADC. PIO0: one state machine per axis playing "N steps in this millisecond" segments. PPS and LINK_SYNC edges time-stamped in a GPIO interrupt. Core 1 owns the motion state; the cores share data only through a single-producer queue and sequence-locked blocks |
| D66 | Link protocol (Q46) | UART0 at 921 600 baud; COBS frames of type, sequence, payload (≤ 240 B) and CRC-16/CCITT-FALSE; the messages of spec 7.1 (STATE at 100 Hz, SETPOINT at 10 Hz, heartbeats at 10 Hz, 500 ms = link lost); head time in µs steered by the GNSS 1 PPS; a LINK_SYNC pulse every second followed by the time of that edge, fitted over 16 pairs on the RP2354A |
| D67 | Closed loop and encoder calibration (Q47) | Steppers driven open-loop with PEC (the gear train is the fine control). Encoders give the absolute position at power-up, a 5 Hz lost-motion correction with a ±2″ deadband (1″/s while tracking, 30″/s while holding) and slip detection at 0.05°. Calibration: each axis is mapped once against motor steps over its travel (harmonics 1–8 of the output angle plus a 0.5° residual grid). The MT6835's own self-calibration is not used (it needs ≥ 25 rpm for 64 turns) |
| D68 | Mount models and pointing (Q48) | Internal frame = the head's own axis angles; matrix kinematics with the wedge tilt and the IMU level. Alt-az (roll de-rotates the field, served as the Alpaca Rotator) and EQ on the wedge (azimuth = hour angle, altitude = declination, roll = framing). Saemundsson refraction scaled by pressure and temperature; a seven-term pointing model (IA, IE, CA, NP, AN, AW, TF) fitted by least squares; J2000 ↔ JNow with IAU 1976 precession, IAU 1980 nutation and annual aberration |
| D69 | Updates and recovery (Q49) | Two ESP32 OTA slots with rollback; the ESP32 keeps the last good RP2354A image and rewrites it over SWD if the RP2354A does not answer after an update; one `.stfw` bundle for both processors; the ESP32 never takes its USB pins away from the built-in USB-serial/JTAG, so the web flasher can always recover it; no secure boot on prototypes |
| D70 | PD controller configuration (Q50) | Each controller's configuration is written into its EEPROM once (bring-up Stage C, 4CC `FLad`/`FLwd`/`FLvy`); the ESP32 also keeps both images (pd_cfg partition) and loads them over I²C (`PBMs`/`PBMc`) if a controller starts in patch-wait mode |
| D71 | Small defaults (Q51) | Access point "StarTracker-XXXX" with a password shown on the OLED; mDNS `startracker.local`; BLE pairing with a 6-digit passkey on the OLED; settings in NVS; Alpaca on port 32323 (and 80), LX200 on TCP 4030 |

## 23 Nov 2026 — Phase 6 app decisions (approved: "Approve Q44–Q57")

Q44–Q51 in the same reply confirm D64–D71 above. The app reasoning is in `docs/06-apps.md` section 2.

| # | Topic | Decision |
|---|---|---|
| D72 | App native shells (Q52) | Same technology as Benro-Polaris-Controller: Android = native Java app with the shared UI in a WebView (Chaquopy dropped, the driver is gone); Windows = Tauri 2 window + Python 3.13 backend (PyInstaller), reusing the Sony WPD camera code and the plate solver. The shared UI is plain HTML/CSS/JS modules with no build step, bundled as app assets on Android and served by the backend on Windows |
| D73 | Where jobs run (Q53) | The head moves, the app shoots. Motion jobs run on the head (`job.*`: poses for panoramas, path-lapse, astro dither); shutter-port jobs run on the head alone and survive the phone sleeping or losing Wi-Fi. USB-camera jobs run their exposures in the app; the head waits at each frame for `job.ack` and, if the app goes quiet, pauses with tracking kept and never moves on blind |
| D74 | Plate solving (Q54) | Bruno's hinted solver on both platforms (offline, wide fields); ASTAP `astap_cli` on Windows for long lenses, with its D05 database downloaded once from the app; on Android a deeper catalogue (Tycho-2 to about mag 10.5) added to the hinted solver for 300–600 mm. No online solver |
| D75 | Discovery and connection (Q55) | Search order: last head used → mDNS → Alpaca discovery UDP 32227 → the head's access point 192.168.4.1, confirmed by `GET /startracker/v1/info` (also served on the Alpaca port), which gives the WebSocket address. BLE only for first Wi-Fi set-up and emergency stop/park. On link loss the app reconnects (1, 2, 5, 5 … s) and catches up with `hello`; head jobs carry on, USB jobs pause at the next frame with the head tracking |
| D76 | API 1.1 additions (Q56) | Made on both sides: `hello`, `limits.get`, `faults.get` / `faults.clear`, `health.get`, `pec.*`, `job.*`, `cal.status` and `cal.encoder.*`, `cal.balance`, `update.status`, `seq` on state events, the `state` op answered with its `id`, `POST /startracker/v1/op`, CORS for the apps' pages, the service UUID in the BLE scan response |
| D77 | App defaults (Q57) | App name "Star Tracker", id `pt.brunomonte.startracker`, installed alongside the Benro app; Android 10+ and Windows 10/11 x64; a fixed signing key in the repo; angles in degrees and arcseconds |

## 23 Nov 2026 — Phase 6 continuation (approved: "Yes to Q58 and Q59")

| # | Topic | Decision |
|---|---|---|
| D78 | Persistent head data (Q58) | The fault log, the three PEC tables and the three encoder maps are kept in files in the ESP32's `storage` partition (LittleFS) instead of NVS or RAM, so they survive a restart; settings stay in NVS. `faults.get` reports `persistent: true` on the head |
| D79 | Battery health to the apps (Q59) | The power task passes the gauge's cycle count, state of health and both cell voltages to the Head; `health.get` reports them (`battery.cycles`, `soh_pct`, `cells_v`) and the Health screen shows them |

## 24 Nov 2026 — Phase 7 order decisions (Bruno's answers to Q60–Q66)

The reasoning is in `docs/07-prototype.md`, sections "Questions" and "Findings".

| # | Topic | Decision |
|---|---|---|
| D80 | Printed parts (Q60, changes D15 and D29) | No printer is bought: every printed part of P0 and P1 is ordered from JLC3DP. The cartridge housings ST-210 and ST-211 are FDM PA12-CF (JLC3DP's nearest material to the PAHT-CF of D35); the body, tower, bezel and carriers are MJF PA12. Materials for the parts drawn in ASA, TPU and PETG are chosen at the P1 order. Bruno: "No, I will outsource this job" |
| D81 | P0 bench rig (Q61) | P0 is built in the real azimuth body ST-310 as P1 assembly steps 2–4, standing on a tripod or a 3/8"-16 bolt through ST-303's socket. Body, motor and mainboard (on the bezel ST-315) turn together; only the bench-supply and USB leads leave the axis. No new fixture. Approved: "Go as recommended" |
| D82 | Reducers for P0 (Q62) | Two LHT-17-100-U-III are bought now and both measured on P0; the better unit goes on azimuth, the other on altitude. The LHT-14 is bought after P0 test T2. Approved: "OK" |
| D83 | First board order (Q63) | ST-501: 5 bare, 2 assembled; ST-520: 5 assembled (P0 1, P1 3, spare 1); ST-602: 2 assembled, in the P1 order. If the clock U23 or the GNSS U24 is out of stock at upload, those pads stay empty and the parts are fitted by hand later. Approved: "OK" |
| D84 | Part numbers in the board order files (Q64) | ST-520 U1: LCSC C2984637 (now listed as the MT6835GT-A10K variant) → C2932578, MPN MT6835GT-STD-R. ST-501 U6: TPS25752ARSMR (not orderable) → TPS25752ASRSMR, the only orderable TPS25752A, in the same 32-pin RSM package; pins checked one by one against the datasheet table. No layout change. Applied in the BOMs, models, `design.py`, `catalog.py`, `costs.py` and the Phase 4 doc. Approved: "Approved" |
| D85 | 60T pulley ST-205 (Q65) | Laifual's LHT-17/14-100-U-III drawing is asked for with the quote; ST-205's bolt pattern is then corrected from it (shown to Bruno first) and the pulley ordered as a configured GT2 pulley or from JLCCNC. Approved: "OK" |
| D86 | Bench tools (Q66) | Bruno owns none: the tools wave of the order plan buys the whole bench kit (supply, multimeter, scope, soldering and hot-air station, PD tester, Debug Probe, TC2030 cable, USB-UART adapter, crimper, torque drivers, dial indicator and base). Answer: "None" |

## 24 Nov 2026 — Phase 8 production decisions (Bruno: "Q67-Q72 - Approved recommendations")

The reasoning and numbers are in `docs/08-production.md`, sections "Decisions", "Production process per part" and "Weight and spec budgets".

| # | Topic | Decision |
|---|---|---|
| D87 | Reducers in production (Q67, refines D18 for production) | The production cartridges are designed for hollow strain-wave component sets (circular spline, flexspline, wave generator) in our own CNC housings with a bought crossed-roller output bearing. Quotes are asked for both these sets and the housed LHT units (Laifual, Leaderdrive, Honpine, KOFON, Hansheng, Goldgun; 100 / 500 / 1,000 sets). The choice is confirmed at the P2 gate from the measured periodic error. The bearing must reach the housed units' moment stiffness (6.4 × 10⁴ N·m/rad size 17, 3.6 × 10⁴ size 14, spec 3.4). The customer interface of a cartridge (4 + 4 screws, one plug, D13) does not change. P0/P1 keep the housed LHT units (D18, D82) |
| D88 | Production processes (Q68) | Cartridge housings ST-210/211 in CNC 6061 from P2 on, at every volume. Body and tower ST-310/311 in MJF PA12 at 100 heads; MJF, CNC and moulded PA66-GF30 re-quoted with the 1,000 order. Bezel, tray, door, top cover, pack shells, roll enclosure, carriers and cell holders in MJF PA12 at 100 and injection-moulded from aluminium tools at 1,000 (PC/ABS or ASA for covers, PA66-GF30 for carriers and cell holders, clear PC for the light pipe). TPU buttons, guides and bumpers stay printed. Gaskets become die-cut silicone/EPDM or O-ring cord (groove changes). Metal parts stay CNC 6061 up to 1,000 heads |
| D89 | Sealing in production (Q69, confirms D9, changes D49 for production) | Design for IPX6; IPX4 signed off on P2; IPX6 tested on the first production sample. ST-501 gets sealed USB-C receptacles in its production revision (footprint change); P0/P1 keep the open GT-USB-7051A of D49 |
| D90 | Scarce chips (Q70) | No board change. TPS25751DREFR: buffer stock of 110 for the first 100 heads as soon as a franchised distributor has stock, a scheduled order ≥ 12 weeks ahead for 1,000, no brokers; TPS25750 only as an emergency fallback after checking its charger list for the BQ25792. GNSS alternate MAX-M10M-00B (same MAX footprint; the active antenna of D54 supplies the LNA), after a pin-table and antenna-bias check. Clock RV-3028-C7 bought from JLCPCB stock (C3019759), QA grade as alternate. TMC2209-LA and MT6835GT-STD-R get a stock check and buffer buy with the board RFQ |
| D91 | Production weight target (Q71, changes D28) | Production head alone ≤ 5.1 kg; the removable wedge (0.62 kg) is extra, ≤ 5.75 kg together. Estimate with D87: 5.11 kg head alone, 5.73 kg with the wedge |
| D92 | Final assembly (Q72) | Heads are assembled and tested in Portugal by Bruno and one helper, from kits of finished parts and boards; the cost model uses Portugal as the landing point |

## Phase 8 — tolerance stack-ups (approved 24 Nov 2026)

Questions Q73–Q76 came from the stack-ups in `hardware/production/tolerances/stackups.md` (`tools/production/tolerance_stackups.py`). Bruno answered on 24 Nov: ST-303 "order as drawn for P0"; the part and production fixes "recommend and implement"; altitude seal "narrower seal on housing face".

| # | Topic | Decision |
|---|---|---|
| D93 | ST-303 in the P0 order (Q73) | The P0 ST-303 is ordered as drawn (rev C): the bench uses neither the V-ring nor the wedge dowels. The P1 order takes ST-303 rev D |
| D94 | V-ring fitted widths and wedge dowels, P1 and production (Q74) | ST-303 rev D: V-ring shoulder at Z 37.5 (was 39.8), VA-75 fitted width 9.0 (B1 9.0 ± 1.2). Dowel holes: one 4 E7 round hole at 11.25° and one 4 E7 × 6 radial slot at 191.25° (were 2 × 4 H7 on 4 m6 dowels, −0.012…+0.008 mm). ST-313 rev D: VA-65 back support widened to R36 (axial support ≥ d1 + 0.5c); the 1 mm seat recess that was approved could not be made, because the clamp's end sits on the shelf face, so the roll fitted width stays 6.0 (inside 7.0 ± 1.0 at nominal, 0.15 mm under at worst case). ST-313 +28 g |
| D95 | Altitude seal (Q75) | The VA-80 cannot fit the 2.5 mm between arm and tower, and a seal on the 80 mm seat cannot get past the tower's Ø84 opening (R42). The fix: a smaller seal on a new, smaller seat on the arm hub (for example a VA-65 size on a 65 mm seat, outside the R31 output flange). Its lip runs on the reducer's fixed front face inside the opening, 6.0 mm from the arm face. The seal is chosen from a supplier table and shown to Bruno before the arm (ST-312) or tower (ST-311) changes |
| D96 | Encoder in production (Q76) | Encoder board seated chip-side down on three pads machined in the CNC housing and located by two pins; nominal chip-to-magnet gap 1.5 mm (worst case 1.08–1.92); tube flange 28 h7 in a 28 H7 seat; magnet seat 6.00 +0.02/0; tube length and seat depth called out ±0.03/±0.05. P1 keeps D48 |
| D97 | 60T pulley in production (Q76) | Pulley bore a light press on the wave-generator stub (run-out ≤ 0.03 mm, spec 3.5) |
| D98 | Housing seals in production (Q76, details D88/D89) | 3.0 mm O-ring cord in 2.15 mm deep grooves with hard stops, screws ≤ 40 mm apart, instead of the 1 mm flat gaskets (squeeze 15–30 % worst case). The customer can still open covers with the hex keys; the cord stays in its groove |
| D99 | Bezel window in production (Q76) | 45° chamfer through the 3 mm bezel around the OLED window, so the edge that limits the view is 2 mm from the glass instead of 5 mm: every pixel reads from 39° off-axis at nominal and 18° at worst case (without it: 18° and 6°) |
