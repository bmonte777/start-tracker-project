# Phase 3 — progress

Branch `phase-3-mechanical-design`. Rev A, 21–22 Nov 2026. Read this first if you pick the work up in a new chat.

## Status by stage

| Stage | Status | Where |
| --- | --- | --- |
| 1. Parameters and bought-part envelopes | Done | `stcad/params.py`, `stcad/bought.py` |
| 2. Three cartridges (size 17 ×2, size 14) | Done | `stcad/parts_cart.py` |
| 3. Structure: base, wedge, body, tower, arm, shelf | Done | `stcad/parts_struct.py` |
| 4. Battery pack, covers, gaskets, small parts | Done | `stcad/parts_misc.py` |
| 5. Assembly, explode, interference and motion checks, mass/CoG | Done, all pass with Q17 option A | `stcad/assembly.py`, `stcad/checks.py`, `out/checks.json` |
| 6. Drawings (33 parts + index, combined set) | Done | `stcad/drawings.py`, `../drawings/` |
| 7. Parts list, cost model, Sheet | Done (129 lines; Sheet updated to match) | `stcad/bom.py`, `../bom/`, `../../docs/calc/bom_data.py` |
| 8. Fabrication package | Done | `stcad/fab.py`, `../fab/` |
| 9. Renders, step pictures, 3D viewer | Done; viewer published | `stcad/render.py`, `stcad/scenes.py`, `viewer_template.html`, `../viewer/` |
| 10. Phase 3 doc | Done | `../../docs/03-mechanical-design.md`, Docs "Phase 3 — Mechanical Design" |

## Decisions taken in Phase 3 (rev B, 22 Nov 2026)

- D33 16 V motor rail. D34 roll offset +23 mm (`D31_EXTRA_OFFSET`). D35 weight changes (MJF body/tower with 2.0 mm walls,
  wedge pockets, 6061 encoder tubes, DDC-60i clamp with `SHELF_TOP`, 7075 reducer screws `joints.ALU7075`, base/shelf pockets).
  D36 coin-slot clamp screw. D37 shelf cantilever 30 mm. D38 raised-hinge wedge.
- Open: lens foot height (85 mm assumed); whether to go lighter than 6.8 kg (options in the doc).

## Key results (rev B)

- No interference at home or at wedge tilt 0/30/60/75°.
- Camera swing +85°: 14.5 mm. Arm running gap to tower 1.0 mm. Roll +10° / −145°.
- 48 mm azimuth motor: 1.6 mm to the altitude cartridge housing, 3.2 mm to body and tower.
- Mass 6.80 kg (rev A 7.21); altitude CG 1.9 mm below the axis.
- Materials €1,853.54 / 1,301.62 / 964.88; COGS €2,076 / 1,445 / 1,048; landed at 1,000 €1,093.
- CNC USD 547; MJF USD 101; 6 print plates, 727 g, 44.4 h.

## How the build works

`python build_all.py` runs all steps; `--only drawings,bom` runs a subset. The checks take about 7 minutes, everything else under 2.
`stcad/bom.py` reads the frozen Phase 2 list in `stcad/bom_phase2_baseline.py` (never its own output) and writes the CSV and `docs/calc/bom_data.py`.

## Known limits and next steps

- Bought parts are envelopes from datasheets; replace with maker STEP files when downloaded.
- 60T pulley bolt pattern to confirm on the Laifual drawing before ordering.
- Phase 4 takes the board outlines in the doc as fixed inputs, reruns the power budget for the 16 V rail (D33) and reviews D26.
- Pull request: Phase 3 mechanical design (branch phase-3-mechanical-design). Merge once Q17-Q21 are answered.
