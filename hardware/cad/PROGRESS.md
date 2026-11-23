# Phase 3 — progress

Branch `phase-3-mechanical-design`. Rev C, 22 Nov 2026. Read this first if you pick the work up in a new chat.

## Status by stage

| Stage | Status | Where |
| --- | --- | --- |
| 1. Parameters and bought-part envelopes | Done | `stcad/params.py`, `stcad/bought.py` |
| 2. Three cartridges (size 17 ×2, size 14) | Done | `stcad/parts_cart.py` |
| 3. Structure: base, wedge, body, tower, arm, shelf | Done | `stcad/parts_struct.py` |
| 4. Battery pack, covers, gaskets, small parts | Done | `stcad/parts_misc.py` |
| 5. Assembly, explode, interference and motion checks, mass/CoG, five payload envelopes | Done, all pass | `stcad/assembly.py`, `stcad/checks.py`, `out/checks.json` |
| 6. Drawings (34 parts + index, combined set) | Done | `stcad/drawings.py`, `../drawings/` |
| 7. Parts list, cost model, Sheet | Done (131 lines; Sheet updated to match) | `stcad/bom.py`, `../bom/`, `../../docs/calc/bom_data.py` |
| 8. Fabrication package | Done | `stcad/fab.py`, `../fab/` |
| 9. Renders, step pictures, 3D viewer | Done; viewer published | `stcad/render.py`, `stcad/scenes.py`, `viewer_template.html`, `../viewer/` |
| 10. Phase 3 doc | Done | `../../docs/03-mechanical-design.md`, Docs "Phase 3 — Mechanical Design" |

## Decisions taken in Phase 3

- D33 16 V motor rail. D34 roll offset +23 mm (`D31_EXTRA_OFFSET`). D35 weight changes (MJF body/tower with 2.0 mm walls,
  wedge pockets, 6061 encoder tubes, DDC-60i clamp with `SHELF_TOP`, 7075 reducer screws `joints.ALU7075`, base/shelf pockets).
  D36 coin-slot clamp screw. D37 shelf cantilever 30 mm. D38 raised-hinge wedge.
- Rev C: D39 removable wedge (ST-303 head base plate with its own 3/8"-16 bushing; ST-331 wedge top plate, ST-332 coin
  screw, ST-333 dowels; `Item.wedge` flags wedge parts; `HEAD_ON_TRIPOD_DZ`). D40 payload envelopes `params.RIGS` P1–P5
  replace the single reference lens; `assembly.rig_y0/rig_info`, `checks.payloads()`; dovetail bars sit rear-flush with the clamp.
- D40 confirmed by Bruno. D41: no further weight cutting. Nothing open.

## Key results (rev C)

- No interference at home or at wedge tilt 0/30/60/75°.
- Arm running gap to tower 1.0 mm. 48 mm azimuth motor 1.6 mm to the altitude cartridge housing.
- Per payload (camera gap / roll toward, away): P1 29.5 mm / +9, −175; P2 17.0 / +9, −130; P3 13.5 / +8, −150;
  P4 27.5 / +15, −150; P5 18.2 / +8, −155. P5 roll holds unpowered only within ±43° (park roll at 0°).
- Mass: head alone 6.21 kg, with wedge 6.83 kg (wedge 0.62 kg).
- Materials €1,894.81 / 1,320.26 / 976.10; COGS €2,122 / 1,465 / 1,060; landed at 1,000 €1,105.
- CNC USD 587 (14 pieces); MJF USD 101; 6 print plates, 727 g, 44.4 h.

## How the build works

`python build_all.py` runs all steps; `--only drawings,bom` runs a subset. The checks take about 7 minutes (the payload sweeps included), everything else under 2.
`stcad/bom.py` reads the frozen Phase 2 list in `stcad/bom_phase2_baseline.py` (never its own output) and writes the CSV and `docs/calc/bom_data.py`.

## Known limits and next steps

- Bought parts are envelopes from datasheets; replace with maker STEP files when downloaded.
- 60T pulley bolt pattern to confirm on the Laifual drawing before ordering.
- Phase 4 takes the board outlines in the doc as fixed inputs, reruns the power budget for the 16 V rail (D33) and reviews D26.
- Pull request #4: Phase 3 mechanical design (branch phase-3-mechanical-design). All decisions approved; ready to merge.

## Phase 4 changes (branch `phase-4-electronics`, 23 Nov 2026)

- Battery pack for the ST-602 battery board (D58–D60, approved 23 Nov): board 1.6 mm behind the cell holder (`PK_YB` 74.4); two
  grooved ribs per shell half hold its edges (`_board_rib`, ribs 7.0 wide, groove 1.7, wall 1.45) in ST-605 / ST-612; two 6 × 3 mm
  wire notches in each cell holder ST-606; light pipe ST-611 7.0 mm long (`build_light_pipe`) with a flange 0.5 mm behind the wall, a
  0.5 mm TPU lip (printed in two materials or glued on, it is not a separate part) and a 5 × 5 × 0.2 mm boss on the gauge button.
  Board moved 1.0 mm further from the holder than first drawn, so the ribs have a printable wall. STEP, drawings and `out/checks.json`
  (home pose: no hits, 92 parts) are current.
- Fit check of the real boards: `python -m stcad.fit_boards` (needs `hardware/electronics/fab/<board>/<board>.step`), result in
  `out/fit_boards.json`. 23 Nov 18:15: **no overlaps** for ST-520 ×3 (magnet gap 0.81–0.82 mm), ST-501 and ST-602.
  ST-501: board 0.09 mm from the bezel bosses, OLED glass 0.70 mm from the bezel, J11 tails (cut to 0.6 mm) 0.39 mm from the azimuth
  body. J11 and the OLED module are stand-ins in `fit_boards.py` (assumed module board 1.2 mm and glass 1.6 mm thick: measure the
  bought module). ST-602: 0.05 mm to the shell ribs (the groove), 0.91 mm to the light pipe in the model (switch model about 1.1 mm
  tall; datasheet 1.5 mm, so 0.3 mm in reality), 1.6 mm to the cell holder.

