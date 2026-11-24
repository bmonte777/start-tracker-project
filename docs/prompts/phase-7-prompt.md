# Star Tracker Project — Phase 7: Prototype rounds (order, build, bring up, measure, iterate)

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Opus 5.5 · **Effort:** high

---

You are the lead engineer on my Star Tracker Project, now running the prototype rounds. It is an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class). Phases 1–6 are finished on paper and in the simulator: the mechanics are fixed in the CAD, the three boards are designed and checked, the firmware and the Android and Windows apps build in the workflow and pass their tests against the simulator. **Nothing has been built yet.** In this phase I order the parts, build the prototypes and measure them, and you plan every step, give me the order lists and build instructions, read my measurements and logs, and fix the firmware, apps or design where the measurements say so.

I do the physical work. You cannot touch the hardware: everything I must do is written as plain physical steps or point-and-click steps, never terminal commands.

## Context — read first
1. Project docs:
   - `claude/02-decisions-log.md`: D1–D79 are fixed.
   - `claude/03-engineering-spec.md` (Phase 2, rev C): section 8.5 (prototype rounds P0, P1), section 11 (risk register and prototype test plan), the error and power budgets the measurements are judged against.
   - `claude/04-mechanical-design.md` (Phase 3, rev C): parts, drawings, print settings, assembly order, the five payload envelopes (D40) and the removable wedge (D39).
   - `claude/05-electronics.md` (Phase 4): fab packages, harness drawings, section 11 bring-up plan (Stages B–D), parts list.
   - `claude/06-firmware.md` (Phase 5, rev C): bring-up firmware and menu (section 4), loading and recovery (section 8), gauge and PD configuration (section 9), what is untested (section 10).
   - `claude/07-apps.md` (Phase 6, rev B): install steps (section 7), what is untested (section 8).
2. Repo: github.com/bmonte777/start-tracker-project, `main` (PR 12 may still be open: merge it first if its checks are green). Attach it with push access before anything else and tell me at once if that is refused. Work on a branch `phase-7-prototype`. Read `app/PROGRESS.md`, `firmware/PROGRESS.md` and `hardware/electronics/PROGRESS.md`.
3. Equipment: I own no 3D printer or CNC (D15). The plan is a Bambu Lab H2S with AMS HT (D29), JLCCNC for aluminium, JLC3DP for MJF PA12, Xometry Europe as backup, JLCPCB for assembled boards. Check whether I have bought the printer before planning printed parts; if I have not, give me the option of ordering the printed parts from JLC3DP for P0.

## Goal of this phase
A working P0 bench rig, then a working P1 head, both measured against the spec, with each problem found fixed in the right place (firmware, app, board, printed or machined part) and a clear decision on whether P1 needs a second round (P1b) before Phase 8.

## Deliverables
1. **Order plan for P0 and P1**, split by supplier, as a Sheets artifact (and CSV in `hardware/bom/`): every line with quantity, supplier part number, link, price checked this week, lead time and which round needs it. JLCPCB board orders (assembled: which boards, how many, which options), JLCCNC and JLC3DP uploads (which files from the repo, material, finish, quantity), LCSC/DigiKey/Mouser parts not placed by JLCPCB, motors, reducers, bearings, belts, screws, cells, cables, tools (EV2400 for the gauge, Debug Probe, PD tester, crimp tool, multimeter, bench supply with current limit), and the order in which to place them so P0 can start first (spec 8.5).
2. **Step-by-step order guides**, point and click, for JLCPCB (Gerbers, BOM, pick-and-place from the workflow's artifacts), JLCCNC and JLC3DP: every field and option I must choose.
3. **Build guide P0 and P1**: an illustrated assembly guide (images from the CAD renders and drawings), one step per page or card, with the parts and tools for that step, torque values, thread-locker where needed, checks after each step, and the harness wiring. Printed-part settings per part if I print them.
4. **Bring-up companion**: Stages B–D from the Phase 4 plan and the Phase 5 bring-up menu as a checklist I tick off, with the expected readings and what to do when a reading is wrong. Include loading the PD configuration and setting up the gauge in bqStudio, point and click.
5. **Measurement procedures and analysis tools** for the risk register: encoder chip-to-magnet gap result (D48, noise and linearity tests o and p), reducer periodic error (sidereal log, encoder vs. command), backlash and lost motion at reversals, encoder calibration map (`cal.encoder`), PEC training result, slew current and StallGuard margins hot and cold, motor and driver temperatures, power per mode and runtime, camera port B under load, tracking accuracy from real frames (star trails or plate solves over time), pointing-model RMS, balance check against a real load, and stiffness (settling after a slew, wind). For each: what I set up, what I record (CSV from the bring-up menu, app logs, photos), and a script or page that turns my data into the number and compares it with the spec. Analysis runs in your workspace on the files I upload.
6. **First real use of the apps**: install on my phone and PC, connect to the head, BLE set-up, Sony camera jobs over USB-C with the screen off, a shutter-port job, ASTAP download on Windows, the deep catalogue on the phone (memory and solve time), firmware update over Wi-Fi. Record what works and fix what does not.
7. **Fixes and iteration**: every problem found, with its cause, the fix (firmware, app, board, part) and the re-test. Firmware and app fixes are made and pushed directly; board, printed or machined part changes are proposed to me first.
8. **Round report**: per round, a results table against the spec targets (pass / fail / measured value), photos I send, and a recommendation: go to Phase 8, or a P1b round with the list of changes.

## Output format
- One Docs doc, "Phase 7 — Prototype", updated per round (P0, P1, P1b if needed).
- The same content as `docs/07-prototype.md`; save it to the Project as `claude/08-prototype.md` and send it to me as a downloadable file.
- Order plan as a Sheets artifact + CSV; build guide and bring-up companion as artifacts (HTML pages with a Day/Night toggle, also sent as files).
- Measurement data in `docs/measurements/<round>/`, analysis scripts in `tools/measure/`.
- Copy this brief to `docs/prompts/phase-7-prompt.md` (already there).
- Update `claude/02-decisions-log.md` (Project and repo) with every decision I approve.
- When the phase is complete, write the Phase 8 prompt (design for mass production), with the recommended model and effort, save it to the Project as `claude/phase-8-prompt.md` and send it to me as a file.

## Working rules
- Work round by round: order plan → P0 order → P0 build and bring-up → P0 measurements → fixes → P1 order → P1 build → P1 measurements → report.
- Commit after each stage, push, keep a pull request open and a `PROGRESS.md` for this phase up to date so another chat can carry on.
- Research current prices, stock and lead times on the web, and cite sources. Never put an LCSC number in a list from memory: confirm it or leave it blank.
- **Ask me before any design decision not covered by D1–D79**, batch the questions with a recommendation each, and carry on with the recommended option marked "pending approval". **Ask me first before any board, printed or machined part changes.**
- The firmware code is the contract for the apps; any API change is made on both sides and documented.
- Only report a feature as working on the head after I have confirmed it on the hardware or my logs show it. Say plainly what is measured, what is estimated and what is still untested.
- Safety first in every step that involves the pack, the bench supply or moving axes: current limits, fuse, first power-up without motors, hands clear of moving parts.
- Explain anything I need to do with point-and-click or plain physical steps, never terminal commands.
- Skip legal, licence and regulatory caveats.
- Every HTML page has a Day/Night toggle, and every HTML or Markdown file you publish is also sent to me as a downloadable file.
- Never copy anything from `assets/abp` in Benro-Polaris-Controller (ogecko's driver) and never reuse the Polaris BLE protocol.
- Use a task list, and finish each round by checking every measured number against its raw data and every spec target against its source.

Out of scope: production versions of the boards and parts, tooling and costs at volume (Phase 8), and the launch package and website (Phase 9).

Start now.
