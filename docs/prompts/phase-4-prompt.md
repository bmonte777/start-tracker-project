You are the lead electronics engineer on my Star Tracker Project. It is an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class), built first as a 3D-printed prototype and later mass-produced. Phases 1–3 are finished and merged. The mechanical design is fixed: every part, board outline and fixing point is in the CAD.

Context — read first
Project docs:
claude/02-decisions-log.md: approved decisions D1–D41. Treat them as fixed.
claude/03-engineering-spec.md: the Phase 2 spec, revision C. Section 5 (power and battery), section 6 (electronics architecture: ICs, connectors, board split), 3.6 (stepper at 12 V) and 5.3 (thermal check) are your starting point.
claude/04-mechanical-design.md: Phase 3, revision C. The "Battery and board mounts" section gives the board outlines and fixings, which are fixed inputs. "Cable path and altitude twist" gives the harness route, and "Payload envelopes" gives the loads.
claude/01-research-report.md: background only.
Repo: github.com/bmonte777/start-tracker-project, branch main. Attach it with push access and work on a new branch, phase-4-electronics. Use these files:
the calculations in docs/calc/ (phase2_calcs.py, bom_data.py);
the parts list in hardware/bom/master-parts-list.csv;
the parametric CAD in hardware/cad/ (stcad/params.py holds every shared dimension, and build_all.py rebuilds everything);
the assembly STEP in hardware/cad/step/.
Parts list Sheet: https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8 (131 lines). Keep it, the CSV and bom_data.py in step.
Phase 3 design doc: https://claude.ai/artifact/8hpmMtaoBVQgPinbwvfbfW. 3D viewer: https://claude.ai/artifact/Sw757qqspnFjuqk8EyUjpj. Change them only to record a decision I approve.
Feature reference only: github.com/bmonte777/Benro-Polaris-Controller. Never copy anything in assets/abp (ogecko's driver).
Open items carried into this phase
D33 (16 V motor rail): rerun phase2_calcs.py at 16 V, covering the speed–torque curves, cold-slew margins, power budget, runtime and thermal check. Then review the 6°/s cold limit of D26. Changing D26 is a decision: ask me.
D27: confirm that the TPS25751D works with the BQ25792 (TI's reference design pairs it with the BQ25798). If it doesn't, recommend the fix and ask me.
D32: check the lead order of the 48 mm azimuth motor (17HS19-2004S1) against the 38 mm motors (17HE15-1504S) before you fix the harness pinout.
Battery board ST-602: Phase 3 left its screw-free fixing at the pack end to be designed together with the board.
Roll harness: 15 wires through the altitude encoder tube (ST-208), twisting ±52.5° over the soft range. Phase 3 recommends fine PTFE-insulated wire.
Prototype round P0 (spec 8.5): the mainboard plus one cartridge board must be able to run the azimuth cartridge alone on the bench. Plan the first board order so P0 can start before the full head.
Goal of this phase

Design every board and every harness, so that I can order assembled boards from JLCPCB, buy or make the harnesses, and wire prototype P1 without guessing.

Deliverables
Calculations first (before the schematics, because they set part values):
the D33 rerun and the D26 review
stepper driver current and sense resistors at 16 V
TPS61288 boost design at 16 V from the 6.0–8.4 V pack: inductor, capacitors and peak current
charger and USB-C PD settings, the 27 W camera port B, and the 3.3 V rail
an updated thermal check
for every calculation: formula → numbers → result, with assumptions stated
Schematics in KiCad (version 8 or later) for the mainboard (ST-501), the cartridge board (ST-520, ×3) and the battery board (ST-602):
every IC from spec section 6.2, with its datasheet application circuit, decoupling, ESD protection on every external connector, test points on every rail and bus, and a reverse-polarity and inrush plan
the encoder MT6835 on the cartridge board's underside, 2.0 mm above the magnet face
a thermistor next to each motor, read by the firmware's 80 °C current derating
schematic as code (SKiDL, atopile or similar) is welcome if it outputs a normal KiCad project I can open; the KiCad files are the deliverable
ERC clean, with every waived warning explained
PCB layouts in KiCad, to the Phase 3 outlines and holes:
mainboard 100 × 60 × 1.6 mm, 4 layers, parts up to 12 mm tall, 4 × M3 holes 4 mm in from each corner
cartridge board Ø30 mm round, 2 × M3 holes on PCD 23
battery board 32 × 40 mm
place the connectors, OLED, buttons, LEDs and USB-C receptacles where the Phase 3 housings have their openings
route the power paths, USB, motor phases, sense resistors, SPI and the GNSS antenna feed deliberately; an autorouter (e.g. Freerouting) only for slow signals
DRC clean against JLCPCB's rules
look at a 3D render of every board before moving on, and fix anything wrong
Fit check against the mechanics:
export each board as STEP and load it into the Phase 3 assembly
check clearances, connector cut-outs, the OLED window, button caps, the GNSS window and the magnet gap with the existing check code
if a printed or machined part must change, ask me first, then update the CAD, drawings and parts list
Wiring harness:
a drawing for each harness: the three cartridge harnesses (JST-GH 15-way, two contacts per motor phase), the motor leads (JST-PH 4-way), the power and battery-bay harness, and the shutter port
lengths taken from the CAD route, wire gauge, insulation, colours, a pinout table for both ends, strain relief, and the twist allowance through the hollow shafts
prefer ready-made pre-crimped leads, so I don't need a crimp tool. If something can't be bought ready-made, say what to buy and how to make it
Fabrication and purchase package in hardware/electronics/fab/:
for each board: Gerbers, drill files, BOM and pick-and-place files ready to upload to JLCPCB assembly, using LCSC part numbers from current stock
list the parts JLCPCB can't place (out of stock, or not in their library) and how to get them on the board
a quote estimate for 5 sets
a bench equipment list for bring-up (current-limited supply, multimeter, USB-C PD tester), with links
Parts list down to the last component:
a full per-board BOM (every resistor, capacitor, inductor, connector and IC, with LCSC numbers) in each board's folder
in the master parts list, the ST-501 / ST-520 / ST-602 lines get their prices from these BOMs and the assembly quote
IC lines that are already in the list stay, without double counting
update the Sheet, the CSV and bom_data.py together, and rerun the cost model (materials, cost of goods and landed cost at 1 / 100 / 1,000)
Firmware hand-off for Phase 5:
full pin maps for the RP2354A and the ESP32-S3
I²C address map, SPI and UART assignments
boot, flashing and update path (the ESP32-S3 programs the RP2354A over SWD)
the power-up sequence
every signal the firmware needs: thermistors, rail monitors, pack SMBus, buttons, LEDs, shutter optocouplers, 1 pps
Bring-up and test plan:
power-up steps for each board, current limits to set, what each test point should read, and a first-light test for each function
everything I do by hand, as point-and-click or plain physical steps
Board viewer page: one HTML page, published as an artifact, with an interactive BOM for each board (click a part to see it on the board and in the list) and 3D renders. It must have a Day/Night toggle.
Output format
One Docs doc, "Phase 4 — Electronics": the calculations, block and power-tree diagrams, board renders, the fit check, the harness drawings, cost and the open questions, with links to the KiCad files, the board viewer and the Sheet.
The same content as Markdown in docs/04-electronics.md. Save it to the Project as claude/05-electronics.md and send it to me as a downloadable file.
KiCad projects in hardware/electronics/<board>/, harness drawings in hardware/electronics/harness/, renders in docs/img/.
A GitHub Actions workflow, started only by hand, that runs ERC and DRC and rebuilds the Gerbers, BOM and pick-and-place files, renders and the interactive BOM from the KiCad files.
Copy this brief to docs/prompts/phase-4-prompt.md in your first commit.
Update claude/02-decisions-log.md (Project and repo) with every new decision I approve.
When the phase is complete, write the prompt for Phase 5 (firmware), with the recommended model and effort, save it to the Project as claude/phase-5-prompt.md and send it to me as a file.
Working rules
Work in stages: calculations, then the mainboard schematic, cartridge and battery schematics, layouts, fit check, harness, then the fab package, parts list and viewer.
Commit after each stage and open a pull request.
Keep hardware/electronics/PROGRESS.md up to date, so a new chat can carry on if this one runs out of room.
Research current part availability, stock and prices on the web (LCSC / JLCPCB first), and cite sources.
Ask me before any design decision not covered by D1–D41. Batch the questions with your recommendation for each, then carry on with the recommended option marked "pending approval", so the work doesn't stall.
Explain anything I need to do with point-and-click steps, never terminal commands.
Skip legal, licence and regulatory caveats.
Any HTML page you make has a Day/Night toggle, and every HTML or Markdown file you publish is also sent to me as a downloadable file.
Use a task list, and finish by checking every part value, pin, dimension and price against its source or by recomputing it.

Out of scope for this phase: firmware and apps (Phases 5–6), building and measuring the prototype (Phase 7), and production versions of the boards (Phase 8).

Start now.