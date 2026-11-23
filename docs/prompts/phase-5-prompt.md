# Star Tracker Project — Phase 5: Firmware (ESP32-S3 and RP2354A)

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Fable 5.2 (Opus 5.5 if Fable is not available) · **Effort:** high

---

You are the lead firmware engineer on my Star Tracker Project. It is an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class), built first as a 3D-printed prototype and later mass-produced. Phases 1–4 are finished: the mechanics are fixed in the CAD, and the three boards (mainboard ST-501, cartridge board ST-520 ×3, battery board ST-602) are designed, checked and ready to order. No board has been built yet, so this phase writes the firmware against the hardware hand-off and proves it on a simulator and in tests, and gives me the bring-up firmware I need the day the first boards arrive.

## Context — read first
1. Project docs:
   - `claude/02-decisions-log.md`: approved decisions D1–D61. Treat them as fixed. Q42 and Q43 are pending (they concern only how the board check is read, not the firmware).
   - `claude/05-electronics.md`: the Phase 4 document. Section 10 (firmware hand-off: ESP32-S3 and RP2354A pin maps, buses and addresses, boot and update path, power-up sequence, analogue inputs, what the firmware must do) and section 11 (bring-up plan) are your starting point. Section 4 (calculations), 5.3 (battery gauge set-up) and 12 (risks) matter too.
   - `claude/03-engineering-spec.md`: the Phase 2 spec, revision C. Section 7 (software and protocols) and the pointing and tracking error budget.
   - `claude/04-mechanical-design.md`: Phase 3, revision C. Axis geometry, travel limits, the five payload envelopes (roll limits per payload, D40) and the wedge (D39).
   - `claude/01-research-report.md`: background only.
2. Repo: github.com/bmonte777/start-tracker-project. Attach it with push access before anything else and tell me at once if that is refused. Work on a new branch, `phase-5-firmware`, from `main` (merge state of pull request 8; if it is not merged yet, branch from `phase-4-electronics` and say so). Use these files:
   - `hardware/electronics/mainboard/design.py` and `cartridge-board/design.py`, `battery-board/design.py`: the schematics as code, the source of truth for every pin and net;
   - `hardware/electronics/mainboard/doc/st-501-schematic.pdf` and the other boards' PDFs;
   - `docs/calc/phase4_calcs.py` and `phase4_results.json`: driver currents, rail levels, monitor scales, the pack-current budget;
   - `hardware/cad/stcad/params.py`: axis geometry and limits.
3. Feature reference only: github.com/bmonte777/Benro-Polaris-Controller (my app; its camera, plate-solver, Holy Grail, Night and Blue Hour features show what the head must support). Never copy anything in `assets/abp` (ogecko's driver). All firmware is written from scratch (D12).

## Goal of this phase
Firmware for both processors that I can load with point-and-click tools, that brings the boards up stage by stage, and that runs the head: tracking, go-to, the three axes with their encoders, power and battery management, the head's own screen and buttons, and the protocols the apps and astronomy programs use (ASCOM Alpaca, LX200, WebSocket JSON, BLE set-up; D11).

## Decisions to ask me first (batch them with a recommendation each, then carry on with the recommended option marked "pending approval")
- Toolchains and language: for example ESP-IDF (C/C++) on the ESP32-S3 and the Pico SDK (C/C++) on the RP2354A, or Rust on one or both.
- How the RP2354A's two cores and PIO are split (step generation, encoder reading, the control loop, the link to the ESP32).
- The link protocol between the two processors (framing, rates, time sync from the 1 PPS and LINK_SYNC strobe).
- Closed-loop strategy: encoders as truth with the steppers driven open-loop and corrected, or a full position loop; encoder calibration method.
- Mount models and coordinate handling for a 3-axis head (alt-az, equatorial on the wedge, the roll axis as field rotator), refraction, and the pointing model.
- Update and recovery: OTA over Wi-Fi, USB, and what happens if an update of either processor fails.
- Anything not covered by D1–D61.

## Deliverables
1. **Architecture first:** a firmware architecture document (tasks, data flow, timing budget, memory, the inter-processor protocol, the state machines for power, motion and safety, error handling) before most code is written. Include diagrams.
2. **Bring-up firmware, delivered early** (ready before the boards arrive): one test image per processor that walks through Stages A–D of the bring-up plan in `claude/05-electronics.md` section 11 from a menu on the serial console and on the OLED: rail readings, I²C scan with the expected addresses, PD contract readout, charger and gauge readout, driver UART check, encoder read-out with field-strength status, thermistors, step and slew tests, the encoder-noise test of D48. Every test prints pass / fail against the limits in the plan.
3. **RP2354A motion firmware:**
   - step generation in PIO for three axes up to the 8°/s slew of D42 with smooth acceleration, and sidereal, lunar and solar rates;
   - MT6835 reading over SPI (shared MISO, three chip selects), multi-turn tracking, calibration, and use of the encoders to correct pointing and tracking;
   - TMC2209 set-up over the single-wire UART (addresses 0, 1, 2): currents, StealthChop / SpreadCycle switching, StallGuard, diagnostics;
   - motor-rail control: soft-start switch, boost enable, the 16 V / 10 V level of D43, VMOT monitoring;
   - limits per payload (D40), park, the low-battery park of D25, the 80 °C thermal derating, end-stop bumpers;
   - the link to the ESP32 and the 1 PPS time base.
4. **ESP32-S3 system firmware:**
   - Wi-Fi (station and access point), BLE set-up, ASCOM Alpaca Telescope and Rotator with discovery, LX200, a WebSocket JSON API documented for the apps (Phase 6);
   - the head's UI on the OLED and four buttons, with the red night mode of D7 and the three status LEDs;
   - power management: both USB-C PD controllers (configuration images, the 27 W camera port B, sourcing from port A), the charger through the port A controller, the battery gauge over SMBus, the pack-current budget of section 10.7, sleep and wake;
   - GNSS (time, position), the real-time clock with its backup cell, IMU and magnetometer for levelling and a first pointing estimate;
   - the camera shutter and focus outputs (opto-couplers) with an intervalometer;
   - programming and updating the RP2354A over SWD (D22, section 10.4);
   - OTA updates for both processors, with a safe fallback.
5. **Simulator and tests:** a host-side simulator of the head (three axes with encoders, drivers, rails, battery, GNSS) that runs the real firmware logic, so the protocols and apps can be tested without hardware; unit tests for the maths (coordinate transforms, rates, refraction, pointing model, current budget); protocol conformance tests (ASCOM ConformU for Alpaca, an LX200 client such as Stellarium or N.I.N.A. against the simulator). Report the results.
6. **Build and release:** a GitHub Actions workflow, started by hand, that builds both firmwares, runs the tests and attaches the images to the run; a way for me to load firmware without terminal commands (for example a web flasher page for the ESP32-S3 in Chrome, and the RP2354A loaded by the ESP32 or by dragging a file onto its USB drive), explained in point-and-click steps.
7. **Battery gauge and PD configuration:** the BQ40Z50-R2 data-flash settings for the 2S2P Molicel P50B pack (as section 5.3 of the Phase 4 document lists), and the TPS25751 / TPS25752 configuration images, with how to make and load them by point and click.

## Output format
- One Docs doc, "Phase 5 — Firmware": architecture, diagrams, the protocols, the bring-up firmware, test results, how to load and update, open questions.
- The same content as Markdown in `docs/05-firmware.md`. Save it to the Project as `claude/06-firmware.md` and send it to me as a downloadable file.
- Firmware in `firmware/esp32s3/` and `firmware/rp2354a/`, shared protocol definitions in `firmware/common/`, simulator in `firmware/sim/`.
- Copy this brief to `docs/prompts/phase-5-prompt.md` in your first commit (it is already there if this file was committed in Phase 4: then leave it).
- Update `claude/02-decisions-log.md` (Project and repo) with every new decision I approve.
- When the phase is complete, write the prompt for Phase 6 (apps for Android and Windows), with the recommended model and effort, save it to the Project as `claude/phase-6-prompt.md` and send it to me as a file.

## Working rules
- Work in stages: architecture and decisions, bring-up firmware, motion firmware, system firmware, protocols, simulator and tests, release.
  - Commit after each stage, push, and keep a pull request open.
  - Keep `firmware/PROGRESS.md` up to date, so a new chat can carry on if this one runs out of room.
- Take every pin, address and scale from the board design files, not from memory; where the hand-off and the design files disagree, the design files win and you tell me.
- Research current library versions, datasheet register maps and protocol specifications on the web and cite sources.
- **Ask me before any design decision not covered by D1–D61.** Batch the questions with your recommendation for each, then carry on with the recommended option marked "pending approval", so the work doesn't stall. If a board, printed or machined part would have to change, ask me first.
- Tell me plainly what is not finished or not tested. Do not describe firmware as working on the head until it has run on real boards; until then say what was tested and how.
- Explain anything I need to do with point-and-click steps, never terminal commands.
- Skip legal, licence and regulatory caveats.
- Any HTML page you make has a Day/Night toggle, and every HTML or Markdown file you publish is also sent to me as a downloadable file.
- Use a task list, and finish by checking every pin, address, register value and timing against its source or by recomputing it.

Out of scope for this phase: the Android and Windows apps (Phase 6), building and measuring the prototype (Phase 7), and production versions of the boards (Phase 8).

Start now.
