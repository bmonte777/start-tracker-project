# Phase 4 (electronics) — progress

Last update: 23 Nov 2026, 19:30 UTC (sixth Phase 4 chat). Branch `phase-4-electronics`, pull request #6 (draft). Phase 4 is complete except for the open points listed under "State at the end of the sixth chat".
Bruno does not use KiCad: nothing is left for him to finish by hand in it. Everything is done from `design.py`, the router and the routes files.

## Done
- Calculations: `docs/calc/phase4_calcs.py` (+ `.md`, `.json`). D42–D51 approved and in the decisions log.
- ST-520 cartridge board: schematic, layout, fab package (`fab/st-520/`), ERC and DRC clean, fits its carrier. Order-ready.
- ST-501 mainboard schematic: 7 sheets, 391 parts, 229 nets, ERC clean, netlist cross-checked. BOM in `mainboard/st-501-bom.csv`.
- **ST-602 battery board** (`battery-board/`, new on 23 Nov): schematic, layout, routes, fab package (`fab/st-602/`). ERC clean, DRC clean
  (no errors, no warnings), power paths ≥ 1.0 mm, fit check done. Open points: see "ST-602" below.
- Harness drawings, cost model, parts list CSV and `bom_data.py` (state of 22 Nov), firmware hand-off, bring-up plan, workflow file.
- LCSC numbers in `tools/catalog.py` are all confirmed; blank means not confirmed. Never fill one in from memory.

## ST-501 layout: where it stands (23 Nov 18:40 UTC)
- **Both checks clean.** `tools/check.py mainboard`: ERC clean, DRC 0 errors, 0 open connections, 14 warnings (9 silk_overlap at the
  front LEDs and buttons, 2 silk_edge_clearance where the ESP32 module's outline meets the board edge, 2 lib_footprint_mismatch,
  1 silk_over_copper; none touches copper). `tools/pathwidth.py mainboard`: all 17 power paths reach their width (list below).
- Six layers (D51), via-in-pad filled and capped. Stack: F sig / In1 3.3 V plane + power rails / In2 sig + 3.3 V and system-rail areas /
  In3 sig + battery bus (D50) / In4 GND / B sig.
- Built from: `mainboard/design.py` (hand positions of all power stages in `FIXED`, drawn copper `AREAS`, hand tracks and vias
  `HAND_TRACKS`/`HAND_VIAS`, In1 `RAILS` with via-free `RAIL_SPINES`, `POWER_PATHS`) → one router run (`grouter.py`, 7 min) → closing pass
  (`CLOSER_VICTIMS=8 CLOSER_ROUNDS=3 closer.py`, 9 open left) → **`mainboard/route_fixes.py`** (seven stages of corrections applied by
  `tools/fixroutes.py mainboard`) → `layout.py mainboard`.
- Routes file `st-501.routes.json` = closing-pass output + the fixes (key `"fixes"` lists the stages applied). The fixes belong to this
  routing result. **After a new router or closer run, empty `STAGES` in `route_fixes.py` and look at the opens afresh**; `fixroutes.py`
  stops with an error if a segment it wants to remove is not there.
- Power paths (wanted / reached, mm): VBAT_IN, CHG_SW1, CHG_SW2, CHG_PMID, VBUS_CHG, VBUS_A, PB_SW1, PB_SW2, VPB_RAW, VPB, PB_MID, VBUS_B,
  VM_IN 1.0 / 1.0; BST_SW 0.35 / 1.0; SW_5V 0.5 / 0.5; +5V 0.5 / 0.8; SW_3V3 0.5 / 1.0. Three pins are measured with a wider neck than the
  standard 0.8 mm because the pin itself is narrow or sits in a row (Q42, pending approval): J3/J4 A4 1.5 mm, J3/J4 B9 2.9 mm (joined to
  row A through the gap between the rows), U7.25 1.1 mm. Terminal changes (Q43, pending): U2.8 → U2.3 for VBUS_CHG, U12.7 removed.

### What the sixth chat changed on ST-501 (so nobody undoes it)
- Placement: U3 turned 180°, charger block U2/L1 3 mm east, U6 1 mm east, Q2/Q3 on the west edge, R23 next to U7, Q6/L5 moved, U26 on
  the front face behind J12, U4/U8/U23/J10 moved, C2/C3/C4 on the front face at the charger's under-chip vias, C17 horizontal, R9, R15,
  C20, C44 fixed. All positions are in `FIXED`.
- USB-C sockets: the footprint forbids front-face copper just beyond the tips of the D+/D- pins, so the four data vias per socket sit in
  the pads (D- vias at the pad's end so the holes are 0.5 mm apart). Row B VBUS pins join row A through the row gap. The old via spots
  stay blocked for parts in `layout()` (the routes of 23 Nov were laid with them; otherwise C26, C27, R16, U9 move).
- 3.3 V for the west half: In2 feeder from a via east of the system-rail trunk to U3.38 and U6.32 (the In1 3.3 V plane is EAST only).
- `grouter.py`: regions on In1 mark their spine as via-free (`occ[VIA]`), hard regions get a halo (0.3 mm closed to foreign tracks,
  `halo_v` 0.45 mm / 0.3 mm on the F VBUS blobs closed to foreign vias), fan-out skips pads where a hand track starts (`byhand`).
- `pathwidth.py`: per-terminal neck `"REF.pin~1.5"`.
- New tools: `tools/fixroutes.py <board>` (applies `<board>/route_fixes.py`), `tools/closeonly.py <board> NET ...` (joins nets on free cells
  only and prints the pieces as `route_fixes.py` operations), `tools/diagrams.py` (block diagram and power tree → `docs/img/`).
- `tools/openlist.py` no longer tells anyone to finish the board in KiCad.
- Helpers of this chat, not in the repo (`/home/claude/work`): `flow.sh` (dump → router → closer → layout → dumpcu → pathwidth),
  `win.py x0 y0 x1 y1 [layers]` (everything in a window), `netinfo.py NET` (pads and pieces of a net), `drc.py` (DRC list in board
  coordinates), `pwdbg.py NET w out.png ...` (copper a probe of width w reaches), `view.py`.

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
Q28, Q31–Q35, Q38–Q41 → D52–D61, approved 23 Nov ("Q28-Q41 - proceed with recommendations"). Q42, Q43 pending.

## State at the end of the sixth chat (23 Nov, evening)
- Phase 4 is complete apart from the points below. All three boards: ERC/DRC clean, power paths at width, fab files, STEP, renders.
  Fit check: no overlaps. Parts list CSV, `bom_data.py`, `phase4_cost_model.json` and the Sheet agree (EUR 2,157.43 / 1,308.23 / 969.11).
  Docs doc, `docs/04-electronics.md` (rev B), Project copy `claude/05-electronics.md`, viewer: current.
- Workflow "Phase 4 electronics build" run on GitHub on the branch: run 45238347825, green (all checks, all boards).
- Pull request 6 was merged into main at 08:45 UTC on 23 Nov (before this chat's work); the work since is in pull request 8.
- Still open: Q42, Q43 (pending approval); 19 mainboard BOM lines without a confirmed LCSC number (matched at upload or hand-fitted,
  list in `docs/04-electronics.md` 8.3); battery board: LED positions in 4-LED mode and TI's fuse-drive resistor values only in figures
  (topology confirmed, TI probably 5.1 k / 5.1 k, ours 10 k / 100 k); display module thickness assumed in the fit check.
- Next phase: firmware, prompt in the Project as `claude/phase-5-prompt.md`.

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
