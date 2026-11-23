# Phase 4 (electronics) — progress

Last update: 23 Nov 2026, 14:30 UTC (fifth Phase 4 chat). Branch `phase-4-electronics`, pull request #6 (draft). Phase 4 is **not complete**.
Bruno does not use KiCad: nothing is left for him to finish by hand in it. Everything is done from `design.py`, the router and the routes files.

## Done
- Calculations: `docs/calc/phase4_calcs.py` (+ `.md`, `.json`). D42–D51 approved and in the decisions log.
- ST-520 cartridge board: schematic, layout, fab package (`fab/st-520/`), ERC and DRC clean, fits its carrier. Order-ready.
- ST-501 mainboard schematic: 7 sheets, 391 parts, 229 nets, ERC clean, netlist cross-checked. BOM in `mainboard/st-501-bom.csv`.
- **ST-602 battery board** (`battery-board/`, new on 23 Nov): schematic, layout, routes, fab package (`fab/st-602/`). ERC clean, DRC clean
  (no errors, no warnings), power paths ≥ 1.0 mm, fit check done. Open points: see "ST-602" below.
- Harness drawings, cost model, parts list CSV and `bom_data.py` (state of 22 Nov), firmware hand-off, bring-up plan, workflow file.
- LCSC numbers in `tools/catalog.py` are all confirmed; blank means not confirmed. Never fill one in from memory.

## ST-501 layout: where it stands (KiCad DRC, 23 Nov 14:00 UTC, `mainboard/out/st-501-drc.json`)
- Six layers (D51), via-in-pad, battery rail on In3 (D50). Stack: F sig / In1 power / In2 sig / In3 sig + VBAT bus / In4 GND / B sig.
- Routes = router cycle "10b" + closer + guided fixes (`mainboard/st-501.routes.json`, laid on `st-501.kicad_pcb`).
  **2 connections open: `B_DP` (U6.22) and `B_CC2` (D8.1). Errors: none.** Warnings: 2 connection_width (VSYS area on In1), 9 via_dangling,
  2 track_dangling, silk overlaps at D11–D13. List: `mainboard/doc/st-501-open-connections.md`.
- **Power paths fail** (`python3 tools/pathwidth.py mainboard` after `kc "python3 tools/dumpcu.py mainboard"`): CHG_SW1 0.10, CHG_SW2 0.25,
  CHG_PMID 0.80, VBUS_CHG 0.25, VBUS_A 0.25, PB_SW2 0.35, VPB_RAW 0.50, VPB 0.25, VBUS_B 0.25, VM_IN 0.25 (all wanted 1.0); +5V 0.25,
  SW_3V3 0.30 (wanted 0.5). OK: VBAT_IN, PB_SW1, PB_MID, BST_SW, SW_5V. **This, not the 2 open connections, is what keeps the board from being ordered.**
- No fab files. Fit check, viewer, 3D render not redone. `costs.py` still prices the bare mainboard as four layers.

### What has to be done on ST-501 (the plan; nothing of it is started)
Build the power section the way ST-602 was built (it worked at the first attempt there):
1. In `mainboard/design.py` put the power parts in `FIXED` by hand, stage by stage, as in the reference layouts: charger U2 with L1 (both
   coil pads within 3 mm of SW1/SW2), C2/C3, PMID and VBUS capacitors; port B converter U7 with Q4/Q5, L2, **R23 next to U7** (it is 35 mm away
   now), C39–C43; port B switch Q2/Q3 **at least 2.2 mm from U6's pin row** (1.1 mm now: three signals need a via there and two fit, which is why
   B_DP stays open); boost U12 with L5, C66 turned so its SW pad faces pin 9, C71/C72; U10/L3 and U11/L4; the VBUS paths J3–U3–U2 and Q3–J4.
2. Add a table `AREAS` as in `battery-board/design.py` (net, face, outline, centre line, half width) for every net of `POWER_PATHS`, pass
   them to the router as hard regions with a spine (no other net's track or via inside), make them zones in `finish()` and block them for the
   autoplacer. Take those nets out of the "switch nodes and power stages" route step or leave only a thin tie track to the router.
3. Parts on the other face inside an area's outline are fine; pads of other nets on the same face are not: keep the areas tight round their pads.
4. One router run, closer, `layout.py`, then **both** checks: `check.py mainboard` and `pathwidth.py mainboard`. Then the remaining opens by
   guided fixes (helpers of this chat: `/home/claude/work/fix.py`, `subsets.py`; they are not in the repo — the ideas are: take named slow
   nets up, lay explicit pieces, close everything again, keep only if all close; and try subsets of up to three neighbouring slow nets).
5. Then: 3D render, `fab.py mainboard`, `python -m stcad.fit_boards`, `viewer.py`.

### Changes of the fifth chat (23 Nov), so nobody repeats or undoes them
- `grouter.py`: region `spine` + `keep` (no foreign vias along the middle of an area: the VBAT bus was cut in two under U14 before);
  escape ring ends half-way to a facing fine-pitch chip (U17.16 / U19.16 had no way out); end-of-row pins of the centre pad's net reach it
  by a 45° leg; `escape(pad_vias=0.5)` reserves an in-pad via on slow-signal pads of R, C, D, J, TP, L, FB, Q; `plan["rules"]`
  (clearance, via, drill) per board; via radius in the clearance model = max(pad, hole + clearance); hand-laid tracks and vias of
  `design.py` (`pre["tracks"]`, `pre["vias"]`) count as connections (`net_groups_rect`).
- `closer.py`: `laid()` (hand-laid copper in islands and prune), `one_more` with alternatives and depth, `plane_pads`, final `prune` + `tee`
  (cuts a track where another ends on it, so KiCad sees a shared end point); prune keeps a via that joins two pads by itself (it removed
  five such vias once and opened AZ_SCK, ALT_SCK, ROLL_SCK, SH_TIP, +3V3G: fixed). Env: `CLOSER_VICTIMS`, `CLOSER_DEPTH`, `CLOSER_ALTS`,
  `CLOSER_ROUNDS`, `CLOSER_WHY`, `CLOSER_KEEP`.
- `mainboard/design.py`: wider free bands (U3, U6 2.4; U14 3.2; U15, U17, U19 2.0), `VBAT_SPINE = 1.2`, `POWER_PATHS`. The block at
  (−13.4, 7.0, −10.9, 9.7) is a leftover the placement depends on (comment in the file).
- New tools: `tools/dumpcu.py <board>` (KiCad's Python) + `tools/pathwidth.py <board>` (numpy, scipy, matplotlib): power-path widths.
- Outer-face ground pours break into islands; a pad in an island without a ground via is "connected" for the router but not for KiCad.
  Found with a pcbnew script (islands of the GND zones without a via); fixed by tie tracks for SW1.2 and J10.2. Worth a step of its own.
- KiCad does not count a via as joined to a chamfered pad when only their copper overlaps: add a short track to the pad centre (CHG_STAT at U2.1).

## ST-602 battery board (23 Nov)
- Built from `battery-board/design.py`: fixed places for all power parts and the gauge's own parts, `AREAS` (drawn copper for BP, BF, VCC,
  PACKP, FUSE_H, GND, PACKN: hard regions with spines, zones), hand-laid pin tracks and the two sense lines (net ties NT1, NT2 on R1's pads;
  SRP_K hops to B for 2 mm), the rest by `grouter.py` + `closer.py`. Rules: clearance 0.15, via 0.6/0.3.
- Flow: `kc "python3 tools/layout.py battery-board --dump"` → `cd battery-board && python3 ../tools/grouter.py .` (5 s) →
  `python3 tools/closer.py battery-board` → `kc "python3 tools/layout.py battery-board"` → `kc "python3 tools/fab.py battery-board"` →
  `kc "python3 tools/dumpcu.py battery-board"` + `python3 tools/pathwidth.py battery-board`.
- Confirmed part numbers added to `catalog.py`: BQ294700DSGR C414622, BAT54WS C2991936, 10 MΩ C26086, 1 mΩ 1206 C2904209. The fuse
  ITV4030L0815NR has none (not at LCSC).
- Not confirmed (said so in the document): LED positions lit in 4-LED mode (SLUUBK0 not read); TI's own fuse-drive resistor values.
- Pack parts that would change (asked as Q38–Q40, not changed): grooved ribs in ST-605 / ST-612, light pipe ST-611 2 mm shorter with a
  way to press the button, wire notches in the cell holders ST-606. `hardware/cad/stcad/fit_boards.py` has the ST-602 frame; the envelope
  in `bought.py` still shows the LEDs at the board centre (they are 13 mm above it, at the light pipe).
- Parts list: ST-602 / 603 / 604 lines in `hardware/bom/master-parts-list.csv`, `bom_data.py` and the Sheet are not updated
  (the fuse line still names the 4-cell part); `costs.py` does not price ST-602 yet.

### Six-layer runs (23 Nov), in order
1. Six layers, in-pad plane vias (`in_pad=True` on plane steps), escape after critical: 64 open.
2. Escape first + critical steps may use In2/In3 at cost 3–6: 39 open, 9 clearance errors.
3. **Clearance bug fixed** (`astar`: after a via the cell on the new layer was not checked in the track's own map; wide tracks ended
   0.05 mm too close). No clearance error since. 58 open (routing got harder, correctly).
4. `plan["via_in_pad"] = 0.5`: signal vias allowed in pads of 0.5 mm and more: 29 open.
5. `*_CPO/_CPI/_VCP/_VREF` and `PB_GV*` moved from the critical steps to the slow signals (so their pins get escapes): 20 open after
   closing. **Committed state = run 5 + closer** (`CLOSER_VICTIMS=8 CLOSER_ROUNDS=3 python3 tools/closer.py mainboard`).
- `closer.py` now: `prune` (loose pieces), `anchor` (track end on the rim of a big pad → pad centre; KiCad does not count rim ends
  on chamfered pads), `close_net` (free cells), `negotiate` (soft path, take up ≤ N slow nets, keep only if all close again;
  `CLOSER_WHY=1` prints why a connection fails). Run-to-run the router lands between 18 and 30; more runs with other net orders may
  close a few more, but the last ones need a human or real negotiated-congestion routing: each crosses 5–15 finished nets near U14/U3/U6.
- Ordering note: Via Covering = Epoxy Filled & Capped. GNSS feed width (now 0.2 mm on B over In4) to be set from JLCPCB's calculator.
- `costs.py` still prices the bare mainboard as four layers.

### The three four-layer cycles (22 Nov), so nobody repeats them
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

### Decisions of 22–23 Nov
Q36 → D50 (pack pads stay, rail on In3), Q37 → D51 (six layers, via-in-pad): approved "Go with recommendations and continue".
Q28, Q31–Q35 are still pending (recommended options in use).

## Next, in this order
1. **ST-501 power section** as planned above, then its 2 open connections, both checks clean, 3D render, fab, fit check, viewer.
2. **ST-602**: apply Bruno's answers to Q38–Q40 in `hardware/cad` (printed parts; ask first if anything else must change), update the
   envelope in `bought.py`, rerun `stcad.fit_boards`; price it in `costs.py`; correct the ST-602 / 603 / 604 lines.
3. **Sheet** https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8: copy the changed lines from `hardware/bom/master-parts-list.csv`
   (ST-501, 509, 512, 513, 517, 518, 519, 520, 530, ST-602 to 604). Not done.
4. Block and power-tree diagrams and board renders into the Docs doc https://claude.ai/artifact/9Y2pyZBkJu5i3eWqNy6xAx and `docs/04-electronics.md`.
   Not done. The Docs doc still has the text of 22 Nov 16:30; `docs/04-electronics.md` and the Project copy `claude/05-electronics.md` are current.
5. Workflow (`.github/workflows/phase4-electronics.yml`): now also the battery board and the power-path width step. **Not yet run on GitHub**
   (pull request 7 must be merged first, then Actions → Phase 4 electronics build → Run workflow → branch `phase-4-electronics`). It ends
   red while the mainboard's checks fail: that is correct.
6. Final check of every value against its source; mark the pull request ready; then `claude/phase-5-prompt.md`.
7. Open questions: Q28, Q31–Q35 (older), Q38–Q41 (23 Nov). Carry on with the recommended options, marked "pending approval".

## Tool chain (as used on 22 and 23 Nov)
KiCad 9.0.8 from Ubuntu 26.04 packages in a chroot (`debootstrap resolute`, then `apt install kicad kicad-footprints kicad-symbols kicad-packages3d
default-jre librsvg2-bin poppler-utils python3-pil`), global library tables copied from the template. Router: Python 3 with numpy, scipy, matplotlib, numba
(host Python, outside the chroot; the chroot is entered only for `layout.py`, `check.py`, `fab.py`, `preview.py`). The chroot takes 4 minutes to build.

## Tools
`tools/build.py <board>` schematic + ERC · `tools/layout.py <board> [--no-route | --dump]` · `tools/grouter.py <board> [--plot]` ·
`tools/closer.py <board>` · `tools/openlist.py <board>` · `tools/check.py <board>` ·
`tools/fab.py <board> [--bom-only]` · `tools/docgen.py` · `tools/costs.py` · `tools/compose_doc.py` (reads `doc/status.json`) · `tools/viewer.py` ·
`tools/preview.py <board>` · `tools/dumpcu.py <board>` · `tools/pathwidth.py <board>` · `harness/harness.py`.
`kc "<command>"` in these notes means: run the command inside the KiCad chroot, in the same folder.
