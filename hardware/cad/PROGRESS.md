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

## Pending decisions (carried with the recommended option)

- **Q17** roll offset +23 mm (`D31_EXTRA_OFFSET`, env `ST_D31_EXTRA`).
- **Q18** 3/8"-16 coin-slot clamp screw (D13 exception).
- **Q19** shelf cantilever 30 mm (`SHELF_CANT`).
- **Q20** raised-hinge wedge, arcs below, M3 tangent screw ≈ 55′/turn.
- **Q21** P1 weight target 7.2 kg (CAD 7.21 kg).
- Lens foot height to be measured by Bruno (85 mm assumed, `LENS`/`FOOT_*` in params).

## Key results (X_ROLL 135.5)

- No interference at home or at wedge tilt 0/30/60/75°.
- Camera swing +85°: 14.5 mm. Arm running gap to tower 1.0 mm. Roll +10° / −145°.
- 48 mm azimuth motor: 1.6 mm to the altitude cartridge housing.
- Mass 7.21 kg incl. 0.36 kg fasteners and inserts; altitude CG 2.8 mm below the axis.
- Materials €1,764.67 / 1,289.49 / 958.17; COGS €1,976 / 1,433 / 1,041; landed at 1,000 €1,086.

## How the build works

`python build_all.py` runs all steps; `--only drawings,bom` runs a subset. The checks take about 7 minutes, everything else under 2.
`stcad/bom.py` reads the frozen Phase 2 list in `stcad/bom_phase2_baseline.py` (never its own output) and writes the CSV and `docs/calc/bom_data.py`.

## Known limits and next steps

- Bought parts are envelopes from datasheets; replace with maker STEP files when downloaded.
- 60T pulley bolt pattern to confirm on the Laifual drawing before ordering.
- Phase 4 takes the board outlines in the doc as fixed inputs, reruns the power budget for the 16 V rail (D33) and reviews D26.
- Push and pull request could not be made from the build session (no push access); see the doc for how the files were delivered.
