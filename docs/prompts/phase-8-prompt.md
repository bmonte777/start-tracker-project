# Star Tracker Project — Phase 8: Design for mass production

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Fable 5.2 · **Effort:** high

---

You are the lead engineer on my Star Tracker Project, now turning the prototype into a product that can be made in batches of 100 to 1,000 and more. It is an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class): harmonic-drive axes with a belt stage, magnetic encoders on every output, a 2S2P 21700 pack the customer can swap, USB-C PD in and a USB-C camera port, firmware on an RP2350, Android and Windows apps.

Phases 1–6 are finished on paper and in the simulator. Phase 7 builds and measures the prototypes (P0 bench rig, P1 full head, P1b if needed). In this phase you redesign each part, board and process for production, get real quotes, plan the assembly and end-of-line test, and finish with a costed production plan, a retail price worked out from that cost, and a pilot build (P2) ready to order.

I do any physical work and place every order. You cannot touch hardware: everything I must do is written as plain physical steps or point-and-click steps, never terminal commands.

## Context: read first
1. Project docs:
   - `claude/02-decisions-log.md`: every decision up to the end of Phase 7 is fixed (D1–D86 at the time of writing, plus whatever Phase 7 adds).
   - `claude/03-engineering-spec.md` (Phase 2, rev C): section 8.1 (production process per part group), section 9 (cost model, tooling and retail range), section 10 (master parts list), section 11 (risk register), and the accuracy, power and stiffness budgets the product must still meet.
   - `claude/04-mechanical-design.md` (Phase 3, rev C): every part, drawing, joint and assembly step; the five payload envelopes (D40) and the removable wedge (D39).
   - `claude/05-electronics.md` (Phase 4): the three boards (ST-501 mainboard, ST-520 cartridge board, ST-602 battery board), their fab packages, harnesses and parts list.
   - `claude/06-firmware.md` (Phase 5) and `claude/07-apps.md` (Phase 6).
   - `claude/08-prototype.md` (Phase 7): the order plan, the build guides, the bring-up results, every measurement, the fixes, and the round reports with their recommendation. **This is the most important input.**
2. Phase 7 state: check the round reports first. If P1 (or P1b) has been measured and the report says "go to Phase 8", work from its numbers. If Phase 7 is not finished, say so at the start, do the work that does not depend on the measurements (process choice, DFM, quotes, test plan, cost model), mark every number that waits on a measurement as *pending P1*, and list them in one table so they can be filled in later.
3. Repo: github.com/bmonte777/start-tracker-project. Attach it with push access before anything else and tell me at once if that is refused. Merge the Phase 7 pull request first if its checks are green and I have said Phase 7 is done; otherwise branch from it. Work on a branch `phase-8-production`. Read `PROGRESS.md`, `hardware/electronics/PROGRESS.md`, `firmware/PROGRESS.md`, `app/PROGRESS.md`. The CAD generator is `hardware/cad/stcad/` (build123d); the board designs are under `hardware/electronics/`.
4. Equipment: I own no 3D printer and no CNC machine (D15, D80); every part is made by a service. I own the bench tool kit bought in Phase 7 (D86).

## Goal of this phase
A production design of every part, board and the pack, each with its process, drawings and a real quote at 100 and 1,000 units; an assembly line and end-of-line test that one or two people can run; a landed cost per head and a recommended retail price; and a P2 pilot build of about 5 heads, fully specified and ready to order, that proves the production parts before tooling is paid for.

## Deliverables
1. **Production process per part.** For every ST- part: the production process at 100 and at 1,000 units (CNC aluminium, injection moulding, die casting, sheet metal, MJF, bought), material, finish and colour, and why. Start from spec section 8.1 and the Phase 7 findings. Include the break-even volumes where a process changes (for example MJF vs. CNC vs. moulding for the housings and covers; die casting above about 2,000 heads, spec 9.2).
2. **Design for manufacture, per part.** New production revisions of the parts in the CAD generator, with the changes each process needs: draft angles, uniform walls, ribs and bosses, moulded-in or ultrasonic inserts, gate and ejector locations, parting lines, undercut removal for moulding; set-ups, fixturing faces, tool access, radii and thread choices for CNC; anodise allowances on fits. STEP and A4 drawings, one part per sheet, with GD&T on the critical features: reducer registers (H7), bearing bores, encoder tube concentricity, the 0.8 mm chip-to-magnet gap (D48), belt centre distance, the 3/8" and Arca interfaces.
3. **Tolerance stack-ups** for the joints that set accuracy or fit: encoder gap and run-out, belt tension and pulley alignment, reducer-to-housing concentricity, clamp and wedge, the bezel and display window, seals (IPX4 target). Worst-case and RSS, with the result against the spec.
4. **Boards for production.** A production revision of each board: the Phase 7 fixes, panelisation, fiducials and tooling holes, test points for a pogo-pin jig, programming in the jig (RP2350 and the PD controllers' configuration), and a second source for every part with a stock risk. Phase 7 found the TPS25751DREFR close to sold out and the MAX-M10S and RV-3028-C7 out of stock: solve these for production (alternatives, buffer stock or design change). Keep the same DRC and ERC standard as Phase 4.
5. **Reducers and other key bought parts.** Quotes for OEM component sets and housed units from Laifual, Leaderdrive and at least two others, at 100, 500 and 1,000 sets: price, MOQ, lead time, the measured periodic error and backlash from Phase 7 as the acceptance limits. The same for motors, pulleys and belts, the clamp, the cells and the pack assembly.
6. **Request-for-quote packages and real quotes.** For each part or board, a folder in `hardware/production/rfq/` with the STEP, drawing, material, finish, quantity breaks and acceptance criteria, and the quotes you get or that I bring back from the suppliers' online quote pages: JLCCNC, Xometry Europe, PCBWay, Protolabs or others for CNC and moulding; JLCPCB and one European assembler for boards; a pack assembler for ST-050. Point-and-click guides for every quote I must request myself.
7. **Tooling and fixtures.** Moulds (number, cavities, steel, cost, life), anodise racks, assembly fixtures and the board test jig (ST-9xx), each with a drawing or a clear specification and a price.
8. **Assembly and end-of-line test.** The production assembly sequence for one head with a time per step, the tools and fixtures at each station, and an end-of-line test: firmware self-test, encoder calibration map per unit, PEC baseline, current and StallGuard check, battery gauge learning, a short tracking test, IPX4 spray check on a sample. Firmware for a factory test mode is made and pushed directly (the firmware stays the contract for the apps). A test-record format so every head has a serial number and its own results.
9. **Battery pack production.** The pack built by an assembler from ST-602 and four P50B cells: spot-weld layout, the shell, the end-of-line pack test, and how packs are shipped with the head.
10. **Packaging.** A shipping box and insert that protect the head (drop from 1 m), the wedge, the pack, cables and printed guide: dimensions, materials, price at 100 and 1,000.
11. **Production cost model and retail price.** The master parts list rebuilt for production as a Sheets artifact (and CSV in `hardware/bom/`), with every line priced from a quote or a cited price at 100, 500 and 1,000 heads; tooling amortised; assembly and test labour from deliverable 8; scrap, freight and import; landed cost per head. From that, the retail price at 2.0×, 2.5× and 3.5× (spec 9.3), compared with the Benro Polaris, ZWO AM3N and Asterra prices on the web this week, and your recommended retail price with the reasons. I set the price from this.
12. **P2 pilot build plan.** About 5 heads built with production parts (or the nearest process that does not need tooling yet), as spec 8.5 describes: order plan (Sheets + CSV), order guides, the build changes against the P1 guide, the tests that sign off each production change, and what must pass before moulds are ordered.
13. **Phase 8 report.** What changed against the prototype and why, the open risks, the go/no-go list for tooling, and what is measured, quoted, estimated or still untested.

## Output format
- One Docs doc, "Phase 8 — Design for mass production".
- The same content as `docs/08-production.md`; save it to the Project as `claude/09-production.md` and send it to me as a downloadable file.
- Production master parts list and P2 order plan as Sheets artifacts + CSV.
- Drawings and STEP files in `hardware/production/`, generated by the CAD code, and a drawing index.
- Any HTML page (guides, comparison pages) has a Day/Night toggle and is also sent to me as a file.
- Copy this brief to `docs/prompts/phase-8-prompt.md`.
- Update `claude/02-decisions-log.md` (Project and repo) with every decision I approve.
- When the phase is complete, write the Phase 9 prompt (launch package: name, website, user guide, maintenance guide, spare-parts list), with the recommended model and effort, save it to the Project as `claude/phase-9-prompt.md` and send it to me as a file.

## Working rules
- Commit after each deliverable, push, keep a pull request open and a `PROGRESS.md` for this phase up to date so another chat can carry on. You do the merges and pushes yourself.
- Research current prices, MOQs and lead times on the web, and cite sources. Never put a part number or an LCSC number in a list from memory: confirm it or leave it blank. Label each price: *quoted*, *list price* (with the date read) or *estimate*.
- Show the working for every calculation (formula → numbers → result), and state your assumptions.
- **Ask me before any design decision not covered by the decisions log**, batch the questions with a recommendation each, and carry on with the recommended option marked "pending approval". **Ask me first before changing any board, printed, moulded or machined part.**
- Keep the product user-repairable: the customer can swap the pack, a cartridge and the covers with the hex keys in the box (D13). Say so explicitly for every production change that touches a part the customer handles.
- The production design must still meet the spec budgets (accuracy, power, stiffness, payload envelopes); show the check for every change that affects one.
- Look at every render and drawing you make before you move on, and fix anything unclear or wrong.
- Explain anything I need to do with point-and-click or plain physical steps, never terminal commands.
- Skip legal, licence, certification and regulatory caveats.
- Never copy anything from `assets/abp` in Benro-Polaris-Controller (ogecko's driver) and never reuse the Polaris BLE protocol.
- Use a task list, and finish by checking every number against its quote or source, or by recomputing it.

Out of scope: the name, branding, website, user and maintenance guides and spare-parts list (Phase 9), and selling or marketing.

Start now.
