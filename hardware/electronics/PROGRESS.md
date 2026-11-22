# Phase 4 (electronics) — progress

Last update: 22 Nov 2026, 20:00 UTC. Branch `phase-4-electronics`, pull request #6 (draft). Phase 4 is **not complete**.
The second Phase 4 chat could not push (the repo attached read-only); Bruno uploaded its files to the branch by hand on GitHub.

## Done
- Calculations: `docs/calc/phase4_calcs.py` (+ `.md`, `.json`). D42–D49 approved and in the decisions log.
- ST-520 cartridge board: schematic, layout, fab package (`fab/st-520/`), ERC and DRC clean, fits its carrier. Order-ready.
- ST-501 mainboard schematic: 7 sheets, 391 parts, 229 nets, ERC clean, netlist cross-checked. BOM in `mainboard/st-501-bom.csv`.
- Harness drawings, cost model, parts list CSV and `bom_data.py`, firmware hand-off, bring-up plan, workflow file.
- LCSC numbers in `tools/catalog.py` are all confirmed; blank means not confirmed. Never fill one in from memory.

## ST-501 layout: where it stands (KiCad DRC, 22 Nov, `mainboard/out/st-501-drc.json`)
- 3,826 track segments, 996 vias. **164 connections open in 84 nets** (of about 950): 79 on power and critical nets, 85 on slow signals.
- Errors: 4 clearance (0.097–0.100 mm vs 0.127), 8 hole clearance (0.2493 vs 0.25), 2 starved thermals (SW1, SW3 ground pads). No shorts.
- Warnings that matter: 35 dangling tracks, 12 dangling vias (left by connections that were taken up).
- No fab files. Fit check, viewer, 3D render not redone for the new placement.

### What was wrong with the first placement (do not go back to it)
- Courtyard-to-courtyard margin 0.12 mm gave pad gaps of 0.42–0.44 mm; a 0.15 mm track with 0.127 mm clearance needs 0.44 mm. Nothing could pass between parts.
- `owner` in the model was the last IC declared on the sheet, so about 80 parts sat beside the wrong chip (5–45 mm away).
- `pcb.plane_vias()` put ground vias straight in front of chip pins. It is no longer called for this board.
- Antenna keep-out was on F and B only.
- Freerouting 2.1.0: the ground net costs 0.5 s per ratsnest update ("too many items"); without ground a pass takes under 2 min, but it still left 483 open
  after 3 passes. Freerouting 1.9.0 needs a display (`xvfb-run`) and the full JRE; it was not seen to finish a pass in 5 min. Neither is used for ST-501 now.

### What the board is built from now
- `mainboard/design.py`: `FIXED` (hand positions; port B re-arranged), `owners()` + `HOT` + `OWNER` (which chip each small part belongs to and the placement order),
  `escape_ring` bands, `IN2` (power-layer areas), `VBAT_BUS` (battery rail on F, also blocked for parts and for foreign tracks), `pour_areas()`,
  `route_plan()` (router steps, in order), `finish()` (zones).
- `tools/pcbgen.py`: `autoplace` (rings on both faces, margin 0.27), `escape_ring`, `dump` (hand-over file), `apply_routes`, `thick`.
- `tools/grouter.py`: grid router, numpy + numba (`pip install numba`), runs outside KiCad. 0.05 mm grid, F and B, 45 degrees.
- Flow: `layout.py mainboard --dump` (40 s) → `grouter.py mainboard` (10–14 min) → `layout.py mainboard` (routes, zones, DRC; 40 s).
  `GR_CKPT=1` saves a checkpoint before the last step; `GR_RESUME=1` restarts from it. `--plot` writes `out/st-501-routes-{F,B}.png`.

### What to fix in the router next (in this order)
1. **The last step ("rest") takes finished critical nets up and cannot always restore them.** Each earlier step ends with 0 open; the 79 open power and critical
   connections appear during "rest". Make the units of the earlier steps hard once their step ends (`commit(..., hard=True)` or flip `s["hard"]` and `build_maps()`),
   and let "rest" take up only other "rest" nets.
2. **Fan-out of the 0.4 mm-pitch chips (U14 RP2354A, U3, U6, U2).** A hard run of the "rest" step without taking anything up leaves 70 of 110 nets open with
   "boxed in" / "no way": signal pins are walled in by the plane vias of neighbouring pins (`fanout()`, the on-axis vias, staggered 0.55 / 1.3 mm). A real escape
   pattern is needed: per side of the chip, give every pin (signal and plane) its via slot in two or three staggered rows fanned out so that a 0.15 mm track passes
   between vias (0.8 mm via pitch does not leave it: 0.5 pad + 2 × 0.127 + 0.15 = 0.904 mm needed), or route signal pins out on B first and add plane vias last.
   Widening the bands (`escape_ring`) to 3 mm for U14 may be needed.
3. Clearance misses of 0.03 mm: tracks whose ends sit where a neighbouring track of another class was added later; raise `MARGIN` to 0.04 or check ends in all classes.
   Hole clearance 0.2493: add 0.005 more to the via half-width. Starved thermals: make SW1–SW4 ground pads solid (`pcb.solid`).
4. `live_groups()` (used by the closing rounds) reports nets open that are connected; KiCad's DRC is the count to trust.
5. If the router is not finished: open the board in KiCad and route the open connections by hand (they are short, the board is not dense).

### Floor-plan weakness to raise with Bruno
The pack pads J1 are at the lower right, the charger U2 at the left: the battery rail crosses the board as a 4.6 mm front-face copper area, about 94 mm, about 10 mΩ
(0.36 W at 6 A). There is no free 9 × 6 mm area on the inner face near U2 with the present placement rules. Options: accept it; or move J1 + Q1 next to U2 and
shuffle U25/U26/J12/BT1 into the freed corner (changes harness lengths ST-531-PWR and ST-532).

## Next, in this order
1. **Finish the ST-501 routing** (above), DRC clean, 3D render, `tools/fab.py mainboard`, `python -m stcad.fit_boards` (hardware/cad), `tools/viewer.py`.
2. **ST-602 battery board** (folder `battery-board/` does not exist yet). Inputs found on 22 Nov:
   - LEDs: charlieplexed on LEDCNTLA/B/C as on TI's EVM: LED1 A→B, LED2 B→A, LED3 B→C, LED4 C→B, LED5 C→A (anode→cathode); 3, 4 or 5 LEDs by setting.
     Still to read in SLUUBK0: which positions a 3-LED display uses.
   - Fuse body (Littelfuse ITV4030): 4.0 × 3.0 × 0.9 mm; A1 0.58, A2 0.50, A3 2.20, B1 0.80, B2 1.44, B3 1.03. Pad drawing and terminal numbering not read (figures).
   - **ITV4030L1415 (C3672030) is the 4-cell part (heater 10.5–19.6 V): wrong for a 2S pack.** Use the 2-cell part of the series (ITV4030L0815); confirm its
     heater range in the datasheet table and its LCSC number in JLCPCB's library before it goes in a BOM.
3. **Sheet** https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8: copy the changed lines from `hardware/bom/master-parts-list.csv`
   (ST-501, 509, 512, 513, 517, 518, 519, 520, 530, and ST-602 when priced).
4. Block and power-tree diagrams and board renders into the Docs doc https://claude.ai/artifact/9Y2pyZBkJu5i3eWqNy6xAx and `docs/04-electronics.md`.
   The Docs doc still has the text of 22 Nov 16:30; `docs/04-electronics.md` is newer.
5. Run the workflow once on GitHub (Actions → Phase 4 electronics build). It must be changed first: it calls Freerouting for the mainboard; it should
   `pip install numba`, lay the committed `st-501.routes.json` on the board and not run the router. KiCad needs its global library tables
   (`cp /usr/share/kicad/template/*-lib-table ~/.config/kicad/9.0/`), otherwise ERC gives 391 "library not configured" warnings.
6. Final check of every value against its source; mark the pull request ready; then `claude/phase-5-prompt.md`.
7. Q28, Q31–Q35 still await Bruno; carry on with the recommended options.

## Tool chain (as used on 22 Nov)
KiCad 9.0.8 from Ubuntu 26.04 packages in a chroot (`debootstrap resolute`, then `apt install kicad kicad-footprints kicad-symbols kicad-packages3d
default-jre librsvg2-bin poppler-utils python3-pil`), global library tables copied from the template. Router: Python 3 with numpy, scipy, matplotlib, numba.

## Tools
`tools/build.py <board>` schematic + ERC · `tools/layout.py <board> [--no-route | --dump]` · `tools/grouter.py <board> [--plot]` · `tools/check.py <board>` ·
`tools/fab.py <board> [--bom-only]` · `tools/docgen.py` · `tools/costs.py` · `tools/compose_doc.py` (reads `doc/status.json`) · `tools/viewer.py` ·
`tools/preview.py <board>` · `harness/harness.py`.
