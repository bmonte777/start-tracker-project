# Phase 4 (electronics) — progress

Last update: 22 Nov 2026, 23:15 UTC (third Phase 4 chat; this one can push). Branch `phase-4-electronics`, pull request #6 (draft). Phase 4 is **not complete**.
The second Phase 4 chat could not push (the repo attached read-only); Bruno uploaded its files to the branch by hand on GitHub.

## Done
- Calculations: `docs/calc/phase4_calcs.py` (+ `.md`, `.json`). D42–D49 approved and in the decisions log.
- ST-520 cartridge board: schematic, layout, fab package (`fab/st-520/`), ERC and DRC clean, fits its carrier. Order-ready.
- ST-501 mainboard schematic: 7 sheets, 391 parts, 229 nets, ERC clean, netlist cross-checked. BOM in `mainboard/st-501-bom.csv`.
- Harness drawings, cost model, parts list CSV and `bom_data.py`, firmware hand-off, bring-up plan, workflow file.
- LCSC numbers in `tools/catalog.py` are all confirmed; blank means not confirmed. Never fill one in from memory.

## ST-501 layout: where it stands (KiCad DRC, 22 Nov evening, `mainboard/out/st-501-drc.json`)
- 4,729 track segments, 1,211 vias; 444 segments (779 mm) of slow signals on In2. **98 connections open in 61 nets** (of about 950):
  20 on plane nets (+3V3 11, GND 5, VSYS 2, VBAT 1, VMOT 1), 15 on critical nets, 63 on slow signals.
- Errors: 5 track-to-pad clearances (0.100–0.125 vs 0.127; all a power track beside a pad of L2, L4, D6, Q8, TP37: cause not found). No shorts.
- Warnings that matter: 62 dangling tracks, 21 dangling vias, 12 isolated copper islands, 1 hole-to-hole 0.49.
- Every open connection with its position: `mainboard/doc/st-501-open-connections.md` / `.csv` (`tools/openlist.py mainboard`), with click steps
  for finishing by hand.
- No fab files. Fit check, viewer, 3D render not redone for the new placement.
- **Bruno's rule was: three router cycles, then stop and hand over the list. The three are used (150, 111, 132 open). Do not start a
  fourth without his answer to Q37 (hand-finish, six layers, or pin reassignment).**

### The third chat's three cycles (22 Nov), so nobody repeats them
Baseline reproduced exactly first (164 open) with the tool chain below.
1. *Critical nets hard before the slow signals* (`hardnets` in `grouter.run`: at the first step that is not `hard`, every unit of the
   earlier hard steps becomes hard). Hardening after *each* step was tried first and is worse: later critical steps need to move earlier ones.
   Also fixed: `save()` dropped a pin stub when a track joined it part-way (13 false opens). → **150 open**.
2. *Escape step* (`op="escape"`, `grouter.escape`), placed after the critical steps: per chip with 12 or more pads of 0.32 mm or less, each
   signal pin gets a hard track to a ring 3 mm out; via rows by pin position on its side (`rows`: pin 0 of 4 any distance, 1 not before
   1.1 mm, 3 not before 1.9 mm, 2 no via inside the ring); kept only if the neighbours can still get out; falls back to soft (takes up
   plane drops). Removed `+ 0.01` in `half[VIA]`: with it a lane 0.5 mm from a via centre was blocked, which walled in every pin beside
   a plane pin (this was the "boxed in" of the old notes). Vias now also keep 0.25 mm hole clearance to existing copper when they are
   placed (the old 0.2493 errors). In2 opened for encoder and rest steps (`layers=["F","B","In2"]`, cost 5; critical steps 1000 = closed).
   → 73 of 96 pins escaped, **111 open**, U14 12 instead of 34. **This is the committed state** (plus the closing pass).
3. *Escape before the critical steps*: 93 of 96 pins out, encoder bus and USB complete, but critical nets lost room (+1V1 9 open,
   RP_XIN, VREF …) → **132 open**. Not kept; `design.py` has the order of cycle 2.
- *Closing pass* `tools/closer.py mainboard [routes.json]` (40 s): all copper fixed, joins what is still apart on free cells, never takes
  anything up. 111 → **98**. Its island finder is geometric and more reliable than `live_groups()`.
- *Freerouting 2.1.0 on top of the critical routes* (DSN edited: plane nets removed from the netlist so they are net-less copper,
  finished nets in an ignored class): passes take 1–3 min but it routes almost nothing ("maze search algorithm could not be created",
  "no connection found"); with all nets left in, one pass takes 12 min and also closes nothing. Do not spend more time on it.

### Why it does not close (my reading)
Not density. (1) U14's GPIOs were assigned by function, so most signals leave on the side away from their destination and must cross
within 3 mm of the chip; (2) the VBAT bus takes the front face from y −15.9 to −11.3 right under U14's south side and under U13;
(3) vias: 0.8 mm centre to centre and 0.96 mm for a track between two, against 0.4 mm pin pitch; (4) the rest step's rip-up has no
memory (same nets take each other up until `max_rips`). A negotiated-congestion (PathFinder) rest step would fix (4) only.
Recommended to Bruno (Q37): six layers with via-in-pad (free at JLCPCB from six layers: jlcpcb.com/resources/6-layer-pcbs); the router
then needs: vias allowed on pads of the fine-pitch chips, two more signal layers (stack F, GND, sig, sig/power, GND or power, B), the
VBAT bus on an inner layer.

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

### Router notes that still hold
- Flow: `layout.py mainboard --dump` (40 s) → `grouter.py mainboard` (critical part 90 s, escape 30 s, rest 13 min with In2) →
  `closer.py mainboard` → `layout.py mainboard` (routes, zones, DRC; 40 s) → `openlist.py mainboard`.
- `GR_CKPT_AT="<part of a step name>"` writes a checkpoint before that step (`GR_CKPT_FILE` = where, `GR_STOP=1` = stop there);
  `GR_RESUME=1` restarts from `out/st-501.ckpt.pkl`; `GR_SKIP=escape` leaves an op out. A checkpoint made with two layers cannot be
  resumed with three.
- `live_groups()` (closing rounds inside the router) still reports connected nets as open; KiCad's DRC is the count to trust.
- The 5 clearance errors: all a wide power track 0.100 mm from a pad of another power net; not explained yet (MARGIN is 0.02).

### Questions put to Bruno on 22 Nov (answers pending; recommended option used)
- **Q36 battery rail**: keep the pack pads at the lower right (94 mm bus, about 10 mΩ, 0.36 W at 6 A) — recommended, no harness change;
  on six layers the bus goes to an inner layer. Alternative: J1 + Q1 beside U2, shuffle U25/U26/J12/BT1 (changes ST-531-PWR, ST-532).
- **Q37 how to finish ST-501**: six layers with via-in-pad (recommended) / finish 98 connections by hand / reassign RP2354A pins on four layers.

## Next, in this order
1. **ST-501**: wait for Q37. Then finish the layout that way, DRC clean, 3D render, `tools/fab.py mainboard`,
   `python -m stcad.fit_boards` (hardware/cad), `tools/viewer.py`. If Bruno hand-finishes: take his saved `.kicad_pcb` as the board
   (do not run `layout.py` over it), run `check.py`, then fab.
2. **ST-602 battery board** (folder `battery-board/` does not exist yet). Inputs, all read now:
   - LEDs: charlieplexed on LEDCNTLA/B/C as on TI's EVM: LED1 A→B, LED2 B→A, LED3 B→C, LED4 C→B, LED5 C→A (anode→cathode); 3, 4 or 5 LEDs by setting.
     Still to read in SLUUBK0: which positions a 3-LED display uses.
   - Fuse **ITV4030L0815** (2 cells, 15 A, VOP 5.0–9.0 V, heater 2.2–3.3 Ω, fuse 1.0–3.0 mΩ; the L1415 at C3672030 is the 4-cell part and wrong).
     Read from the datasheet drawing (rev. 08/22/23, page 4, static.chipdip.ru/lib/556/DOC043556381.pdf): terminals 1 and 3 = fuse ends,
     2 = heater (to the fuse mid-point). Body 4.0 × 3.0 × 0.9; terminal 2 on a short edge, 3 and 1 on the long edges.
     Land pattern: A1 1.20, A2 1.55, A3 2.40, B1 1.20, B2 1.60, B3 1.55, B4 0.90, B5 1.55 → pad 2 1.20 × 1.60 at (−1.97, 0);
     pad 3 2.40 × 1.55 at (0.18, +1.225); pad 1 2.40 × 1.55 at (0.18, −1.225), origin at the body centre.
     LCSC number of the L0815: not looked up yet — confirm in JLCPCB's library or leave blank.
   - Screw-free fixing at the pack end: not designed.
3. **Sheet** https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8: copy the changed lines from `hardware/bom/master-parts-list.csv`
   (ST-501, 509, 512, 513, 517, 518, 519, 520, 530, and ST-602 when priced). Not done.
4. Block and power-tree diagrams and board renders into the Docs doc https://claude.ai/artifact/9Y2pyZBkJu5i3eWqNy6xAx and `docs/04-electronics.md`.
   Not done. The Docs doc still has the text of 22 Nov 16:30; `docs/04-electronics.md` and the Project copy `claude/05-electronics.md` are current.
5. Workflow: changed on 22 Nov (no Freerouting, library tables copied, routes laid on the board only when `regenerate` = yes, fab files
   only for a board whose checks are clean, list of open connections in the download, run fails if a check has errors). **Not yet run on
   GitHub.** With the mainboard open it will end red at the last step: that is correct until ST-501 is finished.
6. Final check of every value against its source; mark the pull request ready; then `claude/phase-5-prompt.md`.
7. Q28, Q31–Q37 await Bruno; carry on with the recommended options.

## Tool chain (as used on 22 Nov)
KiCad 9.0.8 from Ubuntu 26.04 packages in a chroot (`debootstrap resolute`, then `apt install kicad kicad-footprints kicad-symbols kicad-packages3d
default-jre librsvg2-bin poppler-utils python3-pil`), global library tables copied from the template. Router: Python 3 with numpy, scipy, matplotlib, numba
(host Python, outside the chroot; the chroot is entered only for `layout.py`, `check.py`, `fab.py`, `preview.py`). The chroot takes 4 minutes to build.

## Tools
`tools/build.py <board>` schematic + ERC · `tools/layout.py <board> [--no-route | --dump]` · `tools/grouter.py <board> [--plot]` ·
`tools/closer.py <board>` · `tools/openlist.py <board>` · `tools/check.py <board>` ·
`tools/fab.py <board> [--bom-only]` · `tools/docgen.py` · `tools/costs.py` · `tools/compose_doc.py` (reads `doc/status.json`) · `tools/viewer.py` ·
`tools/preview.py <board>` · `harness/harness.py`.
