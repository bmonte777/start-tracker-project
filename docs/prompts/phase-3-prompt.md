# Star Tracker Project — Phase 3: Mechanical Design (every part in 3D and on A4)

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Opus 5.5 · **Effort:** high

---

You are the lead mechanical engineer on my Star Tracker Project: an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class). It will be a 3D-printed prototype first, then mass-produced.

## Context — read first
1. Project docs:
   - `claude/01-research-report.md`: Phase 1 research
   - `claude/02-decisions-log.md`: approved decisions D1–D32. Treat them as fixed.
   - `claude/03-engineering-spec.md`: the Phase 2 engineering spec, revision C. Every load, dimension, material and process in it is your starting point. Section 2.3 (key dimensions), 3.10 (mass budget), 8 (manufacturing plan) and 10 (parts list) matter most.
2. Repo: github.com/bmonte777/start-tracker-project. Attach it with push access. Everything you produce goes in it. The calculations are in `docs/calc/` (`phase2_calcs.py`, `bom_data.py`) and the parts list in `hardware/bom/master-parts-list.csv`.
3. Parts list Sheet: https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8 (88 lines, ST-000 to ST-805). Keep it and the CSV in step.
4. Live spec doc: https://claude.ai/artifact/HrJ3eDJexNkq9QpU9hBu8x. Change it only to record a decision I approve.
5. Feature reference only: github.com/bmonte777/Benro-Polaris-Controller. Never copy anything in `assets/abp` (ogecko's driver).

## Open item carried over from Phase 2
**Q16, awaiting my answer: raise the motor rail from 12 V to 16 V.** The TPS61288 boost converter goes up to 18 V, so the same chip can supply 16 V. That lifts the 7 kg cold-slew margin at 8°/s from about 1.2 to about 1.6, and the 6°/s cold limit of D26 could go. It changes no mechanical part, so treat it as pending and remind me once in your first reply. If I approve it, record it as D33. The rerun of the calculations belongs to Phase 4.

## Goal of this phase
Model every part of the head in 3D and draw every part we make on its own A4 sheet, so that I can print the printed parts, order the machined parts from JLCCNC and buy the rest, then assemble prototype P1 without guessing.

## Deliverables
1. **Parametric CAD in code.** Use build123d (CadQuery if build123d cannot do something), so every part is a script I can re-run.
   - Put every dimension that is shared between parts in one parameters file. Take the values from the spec, section 2.3.
   - Model bought parts as accurate envelopes from their datasheets: the Laifual LHT-14/17 reducers, both NEMA 17 motors (38 mm and 48 mm), GT2 pulleys and belt, Arca clamp, cells, boards. Use the maker's STEP file where one can be downloaded.
   - Export each part as STEP. Export each printed part as STL too, already turned to its print orientation.
2. **Full assembly:**
   - assembly STEP of the whole head
   - an exploded view, and renders from front, side, top and three-quarter
   - an automatic check for interference, with the minimum clearances listed. Check the azimuth body around the 48 mm motor (D32, 10 mm longer than the others), the camera swing up to +85° altitude, and the roll travel of D31.
   - mass of every part, and total mass and centre of gravity compared with the spec (sections 2.5 and 3.10) and the weight target of D28 (P1 ≤ 6.1 kg)
3. **Design studies, closed before the parts that depend on them:**
   - D31 roll clearance: compare a wider payload offset with a raised roll axis, using the CAD and the spec's load formulas. Recommend one.
   - Cable path through the hollow shafts and the altitude twist of ±52.5°; plug positions for one plug per cartridge (D13).
   - Sealing for IPX4: V-rings, labyrinths, gaskets and cover joints.
   - Tool-free battery tray and pack shell (D8), and the mounting points for the boards (mainboard about 100 × 60 mm, three round encoder boards about 30 mm, battery board). Board outlines and hole positions become fixed inputs for Phase 4.
   - Belt tension slide and how to set it without special tools.
4. **A4 drawings, one part per sheet**, for every part we make (printed, machined and turned):
   - ISO first-angle projection, dimensions in mm, as many views and sections as the part needs
   - title block with part ID (ST-xxx), name, material, finish, general tolerance (ISO 2768-m for machined parts), scale, revision, date and sheet number
   - tolerances and fits where they matter (H7 on reducer registers and bores), threads, insert holes, surface finish, notes
   - for printed parts: print orientation, the walls, infill and material from spec section 8.2, and which bores to ream
   - PDF per part, plus one combined PDF drawing set with an index sheet
5. **Parts list down to the last screw:**
   - split every assembly and screw set into single parts: each screw (ISO 4762 / 7380, size and length), heat-set insert, dowel pin, washer, seal, bumper, label
   - only M3, M4 and M5 screws and 2 / 2.5 / 3 mm hex keys (D13)
   - same columns as now, prices researched and cited, totals recalculated, the Sheet and the CSV both updated, and `bom_data.py` updated so the cost model still runs
6. **Fabrication package:**
   - CNC parts: STEP + PDF drawing per part, ready to upload to JLCCNC, with a quote estimate for one set
   - printed parts: STL per part, how many fit on each H2S plate, and the print time and filament per set
   - a shopping list of bought parts with links
7. **Assembly sequence for P1:** numbered steps with a picture each, the tools, the screw for each joint and its tightening torque, and the belt-tension and balance checks.
8. **3D viewer page:** one HTML page, published as an artifact, that shows the assembly in 3D with an exploded-view slider and a parts list you can click to highlight each part. It must have a Day/Night toggle. I have no CAD program, so this is how I will look at the design.

## Output format
- One Docs doc, "Phase 3 — Mechanical Design": the design studies, the main renders inline, the checks (clearance, mass, centre of gravity) and links to the drawing set, the viewer and the Sheet.
- The same content as Markdown in `docs/03-mechanical-design.md`. Save it to the Project as `claude/04-mechanical-design.md` and send it to me as a downloadable file.
- CAD sources and STEP/STL in `hardware/cad/`, drawings in `hardware/drawings/`, renders in `docs/img/`, the parts list in `hardware/bom/`.
- A GitHub Actions workflow, started only by hand, that rebuilds every STEP, STL, drawing and render from the scripts.
- Copy this brief to `docs/prompts/phase-3-prompt.md` in your first commit.
- Update `claude/02-decisions-log.md` (Project and repo) with every new decision I approve.

## Working rules
- This phase is long. Work in stages: parameters and bought-part envelopes, then the three cartridges, then the structure (base, wedge, body, tower, arm, shelf), then the battery and covers, then the assembly checks, drawings, parts list and viewer.
  - Commit after each stage on a branch and open a pull request.
  - Keep `hardware/cad/PROGRESS.md` up to date, so a new chat can carry on if this one runs out of room.
- Look at every render and drawing you make before you move on. Fix anything unclear, overlapping or wrong.
- Research current part dimensions and prices on the web, and cite sources.
- Show the working for any new calculation (formula → numbers → result), and state your assumptions.
- **Ask me before any design decision not covered by D1–D32.** Batch the questions with your recommendation for each, then carry on with the recommended option marked "pending approval", so the work doesn't stall.
- If a dimension depends on my own gear, ask me to measure it. The height of the Sony 200–600 lens foot, assumed 85 mm in the spec, is one of these.
- Explain anything I need to do with point-and-click steps, never terminal commands.
- Skip legal, licence and regulatory caveats.
- Any HTML page you make has a Day/Night toggle.
- Use a task list, and finish by checking every dimension, mass and price against its source or by recomputing it.

Out of scope for this phase: PCB layout and wiring harness (Phase 4, which uses your board outlines), firmware and apps (Phases 5–6), and design for mass production: moulded and die-cast versions (Phase 8).

Start now.
