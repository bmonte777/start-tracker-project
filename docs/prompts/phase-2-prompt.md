# Star Tracker Project — Phase 2: Engineering Spec, Architecture & Calculations

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Fable 5.2 · **Effort:** high (max for the calculation sections)

---

You are the lead engineer on my Star Tracker Project: an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class). It will be a 3D-printed prototype first, then mass-produced.

## Context — read first
1. Project docs: `claude/01-research-report.md` (Phase 1 research) and `claude/02-decisions-log.md` (approved decisions D1–D16). Treat the decisions as fixed.
2. Repo: github.com/bmonte777/start-tracker-project. Attach it with push access. Everything you produce goes in it (`docs/`, `hardware/`, `electronics/`, `firmware/`, `app/`).
3. Feature reference only: github.com/bmonte777/Benro-Polaris-Controller (my app). My own code there may be reused later. Never copy anything in `assets/abp` (ogecko's driver).

## Goal of this phase
Turn the research into an engineering specification complete enough that Phase 3 can model every part in 3D and draw it on A4 sheets without guessing.

## Deliverables
1. **Product requirements spec:** functions, performance targets and interfaces. Start from these targets and refine them:
   - tracking ≤ 3″ RMS over 5 min at 300 mm in EQ-wedge mode, ≤ 5″ RMS in alt-az mode
   - go-to ≤ 2′ after alignment
   - backlash ≤ 20″
   - payload 7 kg
   - slew 8°/s
   - −20 to +40 °C
   - IPX4 prototype / IPX6 production
   - weight target
   - Arca clamp on top, 3/8″-16 base
2. **Kinematic layout:**
   - axis order Az → Alt → Roll, plus the latitude wedge (its range)
   - range of each axis, and slip ring vs cable wrap
   - clearance for an A7R V + Sony 200–600 on its lens foot
   - centre of gravity and balance
   - diagrams of the layout
3. **Load and stiffness calculations, per axis:**
   - static, acceleration and wind torques
   - strain-wave reducer selection with real models: size, ratio, rated/peak torque, tilting moment, weight, price, supplier
   - output bearings
   - GT2 belt width and tension
   - stepper model checked against a speed–torque curve at 12 V
   - deflection under load in arc-seconds, for printed parts vs aluminium
   - settle time after a slew
   - whether the camera stays put with power off (detent torque reflected through the reducer), and whether a brake is needed
4. **Accuracy budget:**
   - every error source: reducer periodic error, belt, encoder, flexure, thermal, polar alignment, refraction, timing
   - combined into an RMS total for EQ mode and alt-az mode
5. **Power and battery:**
   - power per operating mode
   - pack design (2S2P P50B): BMS IC, fuel gauge, charger, USB-C PD controller, 12 V boost, USB-C PD output for the camera
   - runtime table and thermal check
6. **Electronics architecture:**
   - block diagram
   - every main IC with a part number, including the final pick of RP2350 vs STM32G4 for the motion MCU, with reasons
   - connector list
   - board split: mainboard + 3 encoder boards + battery board
7. **Firmware and software architecture:**
   - modules and the interfaces between them
   - Alpaca / LX200 / WebSocket / BLE message formats
   - state machines and safety behaviour
   - simulator mode
   - app architecture (Android + Windows) reusing my own code
   - repo structure
   - CI: GitHub Actions that run only when I start them by hand
8. **Prototype manufacturing plan:**
   - per part: printed (material + print settings), CNC-machined in aluminium by a service, or bought
   - confirm the 3D printer to buy and the filament dryer
   - service choice for CNC and MJF parts
9. **Cost model:**
   - BOM cost at 1, 100 and 1,000 units, using researched current prices
   - tooling costs (moulds, die-casting) for production
   - a suggested retail price range from typical hardware margins, so I can set the price
10. **Master parts list skeleton:**
    - every part with an ID (ST-xxx), name, quantity, material (prototype / production), make or buy, supplier and price
    - delivered as a Sheets artifact + CSV in `hardware/bom/`
11. **Risk register and prototype test plan:** how we will measure backlash, periodic error, tracking, power and stiffness.

## Output format
- One Docs doc, "Phase 2 — Engineering Spec", with diagrams inline.
- The same content as Markdown in `docs/02-engineering-spec.md`.
- Save the Markdown to the Project and send it to me as a downloadable file.
- BOM as a Sheets artifact + CSV.
- Update `claude/02-decisions-log.md` (Project and repo) with every new decision I approve.

## Working rules
- Research current part availability and prices on the web, and cite sources.
- Show the working for every calculation (formula → numbers → result), and state your assumptions.
- **Ask me before any design decision not covered by D1–D16.** Batch the questions with your recommendation for each, then carry on with the recommended option marked "pending approval", so the work doesn't stall.
- Explain anything I need to do with point-and-click steps, never terminal commands.
- Skip legal, licence and regulatory caveats.
- Any HTML page you make has a Day/Night toggle.
- Use a task list, and finish by checking every number against its source or by recomputing it.

Out of scope for this phase: detailed per-part CAD and A4 drawings (Phase 3), PCB layout (Phase 4), writing the firmware and app code (Phases 5–6).

Start now.
