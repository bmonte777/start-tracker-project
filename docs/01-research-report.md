# Star Tracker Project — Phase 1 Research Report

**Project:** 3-axis motorised astro head (Polaris / Asterra class), 3D-printed prototype first, then mass production
**Repo:** github.com/bmonte777/start-tracker-project
**Date:** 20 November 2026 · **Status:** Research done; design decisions awaiting Bruno's approval (section 10)

---

## 1. Summary

- **What we are building:** a 3-axis motorised head with azimuth, altitude and roll axes. It does star tracking, go-to, panoramas, time-lapse and Holy Grail shots, and controls the camera. It is built to beat the Benro Polaris where the Polaris is weak: gear backlash, drift at long focal lengths, and the need for a separate PC driver.
- **Biggest finding:** the Polaris uses worm gears. The community driver's own measurements put its backlash at about **125–160″ on M1, 280–620″ on M2 and about 310″ on M3**. At 600 mm on an A7R V, one pixel is 1.29″, so that slack is worth hundreds of pixels each time an axis reverses. This explains the drift you saw during the eclipse.
- **Our answer:**
  - **zero-backlash strain-wave (harmonic) reducers** with a belt stage, giving about 300:1 (the same idea as ZWO's AM3/AM5)
  - **21-bit absolute magnetic encoders** on every output axis
  - an optional **built-in latitude wedge**, so long lenses can track on one axis in pure equatorial mode
- **Brains on the head, not on a PC:** the firmware runs the ASCOM Alpaca server and the LX200 protocol itself. NINA, Stellarium and SkySafari connect straight to the head over Wi-Fi, with no driver to install.
- **Software:** your Benro-Polaris-Controller app code (camera control, plate solver, Holy Grail, Night screen, Blue Hour UI) is your own code and can be reused. The only third-party part is the ogecko driver in `assets/abp`. Our firmware replaces it completely, so **we don't need anyone's permission**.
- **Power:** a tool-free, swappable **2S2P 21700 Li-ion pack (7.2 V, about 10 Ah, about 72 Wh)** with USB-C PD charging and a USB-C output to power the camera. You can also run it from a power bank at the same time.

---

## 2. What a star tracker is and how it works

### 2.1 The problem
The sky turns about 15″ (arc-seconds) per second of time, so long exposures from a fixed tripod show star trails. A tracker turns the camera in step with the sky so the stars stay as points.

### 2.2 Two ways to track

| | Equatorial (EQ) | Alt-azimuth (Alt-Az) + roll |
|---|---|---|
| Axes moving during tracking | 1 (the polar axis, at a constant sidereal rate) | 3 (azimuth and altitude at changing rates, plus roll to cancel field rotation) |
| Setup | Polar alignment needed | Level and sync on stars, or plate solve |
| Accuracy at long focal lengths | Best: a constant rate, so gear errors are easy to learn | Good, but rates change constantly and axes reverse |
| Versatility | Tracking only | Tracking, panoramas, time-lapse, video and go-to anywhere |
| Examples | Star Adventurer, Asterra Z+, ZWO AM3 in EQ mode | Benro Polaris |

**Field rotation:** an alt-az mount keeps the target centred, but the star field slowly rotates around it. The rate is greatest at high altitude when pointing north or south, and smallest when pointing east or west. The Polaris and our design cancel it with a third motor that turns the camera around the lens axis.

**Our approach:** a 3-axis alt-az head with roll, like the Polaris, plus a **latitude wedge** that tilts the azimuth axis parallel to Earth's axis. With the wedge set, the head becomes a true equatorial tracker: one axis at sidereal rate, with roll and altitude holding still. Use it for 300–600 mm.

### 2.3 Tracking accuracy needed (Sony A7R V, 3.76 µm pixels)

| Focal length | Pixel scale | Target tracking error for round stars |
|---|---|---|
| 20 mm | 38.8″/px | ≤ 40″ (easy) |
| 135 mm | 5.7″/px | ≤ 6″ RMS |
| 300 mm | 2.6″/px | **≤ 3″ RMS** (design target) |
| 600 mm | 1.3″/px | ≤ 2″ RMS (stretch goal: EQ wedge mode, short subs or guiding) |

Formula: pixel scale (″) = 206.265 × pixel size (µm) / focal length (mm).

### 2.4 What else the device must do (from the Polaris, your app and the market)
- **Astro:** polar alignment help, multi-star alignment or pointing model, plate-solve sync, go-to, sidereal, lunar, solar and half-speed tracking, Milky Way landscapes, star trails, astro panoramas and mosaics, pulse guiding from PHD2, dithering, periodic error correction (PEC), satellite, comet and ISS tracking (TLE).
- **Day:** panoramas (multi-row, 360° and 720° sphere), time-lapse, motion time-lapse with keyframes, Holy Grail day-to-night, focus stacking, HDR, video moves, Sun time-lapse, path-lapse.
- **System:** GPS, compass, IMU, real-time clock, battery gauge, cable-wrap and collision limits, safe stop on power loss, firmware updates over Wi-Fi.

---

## 3. Market reference products

| Product | Type | Payload | Weight | Drive | Power | Notes |
|---|---|---|---|---|---|---|
| **Benro Polaris Astro** | 3-axis smart head (alt-az + roll, via an angled astro module) | 7 kg | ~1.5 kg | Brushless motors with worm gears (6° worm period, 60-tooth wheel per the driver source) | Internal battery, ~20–24 h, USB-C, charges the camera | IPX6, microSD, GPS and compass. The app is criticised; large backlash (see §1) |
| **Asterra Z+** | Single-axis EQ tracker | 5 kg, 8 N·m | Compact, 6061 aluminium | Not published | Hot-swap 3×AA pack, about 17.5 h, plus 5 V USB-C | OLED screen; polar alignment by magnetometer, laser and IMU; vibration and stall detection; down to −20 °C |
| **ZWO AM3 / AM3N** | Harmonic EQ/Alt-Az mount | 8 kg (13 kg with counterweight) | 4.1 kg | Strain wave + belt, 300:1 | 12 V, 3 A external | Periodic error ±15″, brakes on power loss |
| **OpenAstroTracker / OpenAstroMount** | Open-source 3D-printed EQ trackers | DSLR, up to ~300 mm | — | Steppers; the OAT body acts as a giant gear | External | LX200 firmware; a proven open community model |

**Gaps we can fill:** Polaris-class versatility, plus zero backlash, the controller in the head (no PC driver), user repairability, open source, and a swappable battery.

---

## 4. Mechanics

### 4.1 Design load
- Your heaviest real-use rig: **A7R V (~0.72 kg) + Sony 200–600 (~2.1 kg) + plate ≈ 3.0–3.2 kg**, mounted by the lens foot.
- Proposed **rated payload: 7 kg**, matching the Polaris, with a safety factor of at least 2 over your rig.
- **Worst-case altitude-axis moment** at 7 kg with a 100 mm offset: 7 × 9.81 × 0.10 ≈ **6.9 N·m**. Your rig at a 60 mm offset needs about 1.9 N·m.

### 4.2 Drive train options

| | **A. Strain wave (harmonic) + GT2 belt** (recommended) | B. Precision worm (steel worm, bronze wheel, spring preload) | C. Hybrid |
|---|---|---|---|
| Backlash | ≤ 10–20″ (zero-backlash class) | Low only with preload; Polaris-type worms measured 125–620″ | Mixed |
| Periodic error | ±15″ class (AM3N) | Larger; needs PEC | — |
| Holds the camera with power off | Stepper detent and holding current (to verify on the prototype); optional brake | Yes, self-locking | — |
| Weight | Housed gearboxes are heavy (~0.4–0.5 kg each); bare component sets built into our housing are light | Light | — |
| Cost per axis (prototype) | ~€150–350 housed; less for component sets | ~€40–120 | — |
| Repairability | The reducer is a sealed unit you swap | Needs adjustment | — |

**Recommendation:** strain wave on all three axes. Size 17 on altitude (the highest torque), size 14 on azimuth and roll. Each is fed by a NEMA 17 stepper through a 3:1 GT2 belt, for about 300:1 overall. At 256 microsteps that gives **0.084″ per microstep** at the output, and slews of about 8°/s need about 400 rpm at the motor, which is easy at 12 V.

### 4.3 Axis cartridge concept (key to repairability)
Each axis is **one swappable cartridge** containing: stepper, belt and pulleys, strain-wave reducer, output bearing(s), MT6835 encoder board, and a JST-GH connector. It is held by 4 screws with one plug. You can replace a whole axis in about 10 minutes with one hex key.

### 4.4 Bearings and fasteners (standardised)
- **Bearings:** thin-section deep groove (6800 / 61804 / 61805 series), or a crossed-roller bearing on the altitude output.
- **Screws:** **M3, M4 and M5 only**, ISO 7380 / ISO 4762, stainless A2 for the prototype and A4 for production.
- **Threads in parts:** brass heat-set inserts in printed parts; tapped threads or Helicoils in aluminium.
- **Tool kit:** 2.0 / 2.5 / 3.0 mm hex keys plus a coin slot for the battery door.

### 4.5 Materials

| Part group | Prototype (3D printer) | Mass production (high quality) |
|---|---|---|
| Structural housings, altitude arm, base | PA-CF or PAHT-CF (or PETG-CF if the printer can't do nylon), 5–6 walls, 40–60 % gyroid infill | 6061-T6 or 7075-T6 aluminium, CNC or die-cast, hard anodised (type III) |
| Arca clamp, top plate, wedge hinge | **6061 aluminium milled on your CNC** (must be metal, even on the prototype) | 6061-T6 CNC, anodised |
| Gears and reducers | **Bought metal**: strain-wave reducers, steel GT2 pulleys, glass-fibre GT2 belts | Same family, OEM component sets |
| Shafts and pins | Ground steel (h6), stainless | Same |
| Covers, battery door, buttons | ASA or PETG (UV-stable) | PA66-GF30 or PC/ABS, injection moulded |
| Seals and grips | TPU 95A | Silicone or EPDM moulded gaskets |
| Camera clamp knobs | PETG + brass insert | Aluminium knurled |

---

## 5. Electronics (proposal)

| Function | Part | Why |
|---|---|---|
| Connectivity CPU | **ESP32-S3** (Wi-Fi, BLE 5, USB OTG) | Runs Alpaca, LX200, WebSocket API, web pages and OTA updates |
| Real-time motion CPU | **RP2350** (PIO step generation) or **STM32G4** | Jitter-free step timing that Wi-Fi activity can't disturb ("no glitches") |
| Motor drivers | 3× **TMC2209** (UART, StealthChop, StallGuard) | Silent, smooth microstepping; stall detection |
| Output encoders | 3× **MT6835** 21-bit magnetic, SPI | 0.6″ resolution; absolute position after power-up; detects slipped steps and knocks. Note: its absolute accuracy (INL about ±0.07°) is for homing and safety; fine tracking comes from the gear train plus PEC and plate solving |
| Orientation | IMU (accelerometer, gyro) + magnetometer | Levelling, compass heading, vibration detection |
| Position and time | u-blox M10 GPS + real-time clock with backup | Location and exact time in the field |
| Power | 2S BMS + fuel gauge, USB-C PD in (charge and run), 12 V boost for the drivers, USB-C PD out for the camera | See §6 |
| Interface | 0.96–1.3″ OLED + 4 buttons + status LED with a red-only night mode | Works without a phone (like the Asterra). *Decision* |
| Camera | USB-C host port (camera control from the head, later) + shutter port | *Decision* |

---

## 6. Battery and power

### 6.1 Power budget (estimate, to be measured on the prototype)

| State | Draw |
|---|---|
| Tracking (3 motors at reduced current + CPUs + Wi-Fi) | ~4–6 W |
| Slewing (peak) | ~15–25 W |
| Idle with Wi-Fi | ~1 W |
| Powering the A7R V over USB-C (optional) | +3–6 W |

### 6.2 Cell choice
- **Samsung 50S / Molicel P50B 21700** (5,000 mAh class).
- At our low currents, high-capacity cells such as the Samsung 50S or 50E run slightly longer. The P50B is rated −40 to 60 °C for discharge and is much stronger at high current; good for cold nights.
- **Recommendation:** Molicel P50B for cold-weather headroom and cycle life.

### 6.3 Pack (recommended)
- **2S2P = 4 × 21700 → 7.2 V nominal, about 10 Ah, about 72 Wh** (stays under 100 Wh, so it flies in hand luggage).
- **Runtime:** about **12–16 h of tracking** alone, or about **7–9 h** while also powering the camera.
- **Form:** a sealed, keyed pack with a BMS. It slides in behind a tool-free door, with a fuel-gauge LED on the pack.
- **Spares:** customers can carry spare packs. The pack uses standard cells, so a service centre or a handy user can re-cell it.
- **Always:** USB-C PD input runs the head and charges the pack at the same time, so a power bank works on long nights.

---

## 7. Firmware

### 7.1 Architecture
- **Motion core** (RP2350 / STM32, C):
  - step generation with acceleration profiles
  - closed loop on the encoders
  - limits and cable wrap
  - safe stop if communication or power fails
- **Application core** (ESP32-S3, C++17 on ESP-IDF / FreeRTOS):
  - **Kinematics** with quaternions (Az/Alt/Roll ↔ RA/Dec ↔ camera frame), including refraction
  - **Pointing model:** 1/2/3-star and N-point models, levelling and cone error, plate-solve sync
  - **Tracking:** sidereal, lunar, solar, custom and ¼–¾ speed; field-rotation roll; EQ-wedge single-axis mode
  - **PEC:** learn the residual periodic error from plate solves and cancel it
  - **Ephemerides:** Sun, Moon and planets, plus SGP4 for satellites and the ISS
  - **Motion jobs:** panoramas, time-lapse with keyframes, Holy Grail moves, video moves
  - **Protocols:**
    - **ASCOM Alpaca** Telescope (and Rotator for roll): HTTP REST on port 32323 with UDP discovery on 32227
    - **LX200** over TCP for Stellarium and SkySafari
    - **WebSocket JSON** for our apps
    - **BLE** for setup and pairing
  - **System:** Wi-Fi access point or join an existing network, OTA updates with rollback, logging to flash, settings backup
- **Tooling:** PlatformIO builds started by hand from GitHub Actions, unit tests for the maths, and a simulator mode that runs the firmware on a PC.

### 7.2 Written from scratch
We implement everything from public maths: textbook astronomy algorithms and published standards (the ASCOM spec, the LX200 command set). We do not copy ogecko's code. Ideas such as PID, Kalman filtering and PEC are general engineering knowledge.

---

## 8. Software (apps)

- **Platforms:** Android and Windows 11, one shared web UI (your Blue Hour design) with Day/Night/Red modes, as in your current app.
- **Reused from your app (your own code):**
  - Sony A7R V USB-C PTP control, with live view, focus peaking and the HFR meter
  - shooting modes: Holy Grail, astro sequence, star trails, HDR, focus stack, panorama, 720° sphere
  - the hinted plate solver (Android and Windows)
  - the Night planner, the gallery and the shot log
- **New:** a device client for our head (WebSocket + Alpaca) in place of the Polaris driver and BLE protocol. Also: an alignment wizard, a PEC trainer, and live encoder, battery and health readouts.
- **Optional lost-in-space solver:** the tetra3 / cedar-solve family of fast "lost-in-space" solvers, used next to your hinted solver. This allows alignment with no starting guess. Its licence is to be confirmed before use.
- **Third-party software:** NINA, Stellarium, SkySafari, PHD2 and CCDciel work directly through the head's own Alpaca and LX200 servers.

---

## 9. Repairability rules (applied to every part)

1. One small hex-key set (2/2.5/3 mm) opens everything. No glue, no hidden clips.
2. Battery: tool-free swap in under 10 seconds.
3. Each axis is a cartridge (motor, belt, reducer, encoder) held by 4 screws and 1 connector.
4. Electronics: one mainboard plus small encoder boards, all with keyed JST-GH plugs.
5. Only M3, M4 and M5 screws, standard bearings, standard belts and standard cells. Every part has a public part number and a supplier link in the BOM.
6. A QR code inside each cover links to that part's page in the maintenance guide.
7. All CAD (STEP and STL), drawings, firmware and app code are published in the repo.

---

## 10. Design decisions for Bruno (needed before detailed CAD)

| # | Decision | Recommendation |
|---|---|---|
| 1 | Drive train | **Strain wave on all 3 axes** (size 17 altitude, size 14 azimuth and roll) + 3:1 belt |
| 2 | Built-in latitude wedge (EQ mode for 300–600 mm) | **Yes** |
| 3 | Rated payload | **7 kg** |
| 4 | Camera control | **v1: from the app** (tablet or PC over USB-C, as now); head hardware ready for onboard control in v2 |
| 5 | Screen and buttons on the head | **Yes** (small OLED + 4 buttons, red night mode) |
| 6 | Battery format | **Sealed, swappable 2S2P P50B pack**, plus run from USB-C PD |
| 7 | Weather sealing target | **IPX4** for the prototype, **IPX6** for production |
| 8 | Prototype equipment | Your 3D printer model and filaments; can your CNC mill aluminium? |
| 9 | Target retail price band | To set (affects strain-wave grade and housing process) |

---

## 11. Roadmap

| Phase | Output | Model / effort |
|---|---|---|
| 1 Research | This report | Opus 5.5 high ✔ |
| 2 Requirements and architecture | Spec sheet, axis layout, torque, stiffness and power calculations, block diagrams | Fable 5.2 high/max |
| 3 Mechanical detail | Every part in 3D (STEP/STL) and 2D A4 dimensioned drawings (one part per sheet), materials, BOM to the last screw | Opus 5.5 high |
| 4 Electronics | Schematic, PCB (KiCad), wiring harness | Fable 5.2 / Opus 5.5 |
| 5 Firmware | Motion core + application core, simulator, tests | Opus 5.5 high, Fable for the maths |
| 6 Apps | Android + Windows, reusing your code | Opus 5.5 high |
| 7 Prototype rounds | Print, assemble, measure backlash, periodic error and power; iterate 2–3 times | Opus 5.5 |
| 8 Design for mass production | Aluminium / moulded versions, tolerances, finishes | Fable 5.2 |
| 9 Launch package | Name, website, user guide, maintenance guide, spare-parts list | Opus 5.5 |

---

## Sources

- Alpaca Benro Polaris Driver v2.2 feature list — https://ogecko.github.io/alpaca-benro-polaris/v2.2/
- Driver source `control_worm.py` and `config.toml` (worm geometry, measured backlash, slew limits), as vendored in github.com/bmonte777/Benro-Polaris-Controller
- Asterra Z+ — https://www.theasterra.com/
- Benro Polaris specs — Adorama, Clifton Cameras, Capture the Atlas review (https://capturetheatlas.com/benro-polaris-review/), Digital Camera World review
- ZWO AM3 / AM3N — zwoastro.com, Adorama, B&H
- OpenAstroTech (OAT / OAM) — https://openastrotech.com/ , https://wiki.openastrotech.com/
- OnStepX — https://github.com/hjd1964/OnStepX
- ASCOM Alpaca API reference — https://ascom-standards.org/AlpacaDeveloper/ASCOMAlpacaAPIReference.html
- Strain-wave reducers — VXB (NEMA 17 100:1 units), SITO HS-14-III, Harmonic Drive CSF catalogues
- MT6835 encoder — MagnTek datasheet
- 21700 cells — Molicel P50B datasheet summary (18650batterystore.com), bench tests (e-cigarette-forum, budgetlightforum)
- Field rotation — Bill Keicher, "Field Rotation in Altitude over Azimuth Mounts"; IRAIT design paper (arXiv astro-ph/0609624)
- tetra3 / cedar-solve — https://github.com/oakamil/cedar-solve , https://docs.rs/tetra3
