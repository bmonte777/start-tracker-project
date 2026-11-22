# Phase 4 (electronics) — progress

Last update: 22 Nov 2026, 16:30 UTC. Branch `phase-4-electronics`, pull request #6 (draft). Phase 4 is **not complete**.

## Done
- Calculations: `docs/calc/phase4_calcs.py` (+ `.md`, `.json`). D42–D47 approved and in the decisions log.
- ST-520 cartridge board: schematic, layout, fab package (`fab/st-520/`), ERC and DRC clean, fits its carrier. Order-ready.
- ST-501 mainboard schematic: 7 sheets, 391 parts, 229 nets, ERC clean, netlist cross-checked. BOM in `mainboard/st-501-bom.csv`.
- ST-501 placement: all parts placed, ground fan-out (249 vias), pours and planes defined, DRC clean except 499 unrouted connections.
- Fit check (`hardware/cad/stcad/fit_boards.py`), harness drawings (`harness/`), cost model (`tools/costs.py`), parts list CSV and `bom_data.py`,
  document (`docs/04-electronics.md` = Project `claude/05-electronics.md`), board viewer (`doc/board-viewer.html`), workflow file.
- LCSC numbers in `tools/catalog.py` are all confirmed; blank means not confirmed. Never fill one in from memory (many remembered numbers were wrong).

## Next, in this order
1. **Route the mainboard.** `python3 tools/layout.py mainboard` (inside KiCad 9 + Java). Freerouting 2.1.0 did not converge:
   534 open connections after a 26-minute first pass. Notes for the next attempt:
   - It ignores `--router.max_passes`; it saves a session only if its `--router.job_timeout` expires between passes, not during one.
     Give it `JAVA_TOOL_OPTIONS=-Xmx5g` and a long limit, or route in KiCad by hand.
   - Already fixed: In1 marked as a power layer (`pcb.plane_layer`), In2 planes added after routing, class widths 0.2–0.3 mm,
     ground vias placed before routing (`pcb.plane_vias`), bare-hole keep-outs (`pcb.hole_keepouts`).
   - Write the power stages, USB pairs, motor phases, sense lines, encoder SPI and GNSS feed as `pcb.track(...)` calls in
     `mainboard/design.py:layout()` first (as done in `cartridge-board/design.py`), so the autorouter only has slow signals left.
   - 21 ground pads found no via position (listed by the script); check they join the pours.
   - Then `tools/fab.py mainboard`, `tools/viewer.py`, rerun `stcad.fit_boards`, look at the 3D render.
2. **ST-602 battery board.** Needs the BQ40Z50 LED pin mapping (TI reference schematic figure) and the three-terminal fuse footprint.
   Circuit definition is in `docs/04-electronics.md` section 5.3. Folder `battery-board/` does not exist yet.
3. **Sheet** https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8: copy the changed lines from `hardware/bom/master-parts-list.csv`
   (ST-501, 509, 512, 513, 517, 518, 519, 520, 530). Needs the Claude Docs connector's `topic.sheets` guide first.
4. Bruno's answers to Q28–Q35 (decisions log, "pending approval"). Q29 changes printed parts ST-212 / ST-216: do nothing in CAD before he approves.
5. Fill the remaining sections of the Docs doc if any are still pending: https://claude.ai/artifact/9Y2pyZBkJu5i3eWqNy6xAx
6. Run the workflow once on GitHub (Actions → Phase 4 electronics build) and fix what it reports.
7. When 1–4 are done: final check of every value against its source, then write `claude/phase-5-prompt.md`.

## Tools
`tools/build.py <board>` schematic + ERC · `tools/layout.py <board> [--no-route]` · `tools/check.py <board>` · `tools/fab.py <board> [--bom-only]` ·
`tools/docgen.py` · `tools/costs.py` · `tools/compose_doc.py` (reads `doc/status.json`) · `tools/viewer.py` · `harness/harness.py`.
