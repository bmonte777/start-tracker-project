# Phase 4 — progress

Branch `phase-4-electronics`. Read this first if you pick the work up in a new chat.

## How the electronics are built

Every board is code: `hardware/electronics/<board>/design.py` holds the schematic (`build()`) and the layout (`layout()`, `finish()`).
The tools in `hardware/electronics/tools/` turn it into ordinary KiCad 9 files and check them:

| Tool | Does |
| --- | --- |
| `schgen.py`, `symlib.py`, `kisx.py` | Write `.kicad_sch` files (label style: every pin carries its net name) and the model JSON |
| `stlib.py`, `stfp.py` | Project symbol and footprint libraries in `hardware/electronics/lib/` (parts KiCad does not ship) |
| `build.py <board>` | Schematic + ERC |
| `netcheck.py <board>` | Compares the netlist KiCad extracts with the model |
| `pcbgen.py`, `layout.py <board>` | Placement and hand-routed nets from `design.py`, Freerouting for the slow nets, zones, DRC with schematic parity |

They need KiCad 9 (`kicad-cli`, `pcbnew` Python) and Java for Freerouting. In the Phase 4 chat they ran in an Ubuntu 26.04 chroot
with KiCad 9.0.8; the GitHub workflow uses the `kicad/kicad:9.0` container.

## Status by stage

| Stage | Status | Where |
| --- | --- | --- |
| 1. Calculations (D33 rerun, D26 review, drivers, boost, charger, port B, rails, thermal) | Done | `docs/calc/phase4_calcs.py`, `phase4_results.json`, `phase4_calcs.md` |
| 2. Mainboard ST-501 schematic | Not started | `mainboard/design.py` |
| 3a. Cartridge board ST-520 schematic | Done: ERC 0 errors, 0 warnings; netlist matches the model | `cartridge-board/` |
| 3b. Battery board ST-602 schematic | Not started | `battery-board/design.py` |
| 4a. Cartridge board layout | Done: 0 unrouted, DRC clean with schematic parity; 3D render checked | `cartridge-board/st-520.kicad_pcb` |
| 4b. Battery board layout | Not started | |
| 4c. Mainboard layout | Not started | |
| 5. Fit check in the Phase 3 assembly | Not started | |
| 6. Harness drawings | Not started | `harness/` |
| 7. Fab package, per-board BOMs, master parts list, cost model | Not started | `fab/` |
| 8. Firmware hand-off, bring-up plan, viewer, Phase 4 doc, workflow, Phase 5 prompt | Not started | |

## Findings so far

- D27 confirmed: the TPS25751 datasheet lists the BQ25792 among the chargers its firmware drives (I2C address 0x6B).
- D32: the two motors use different lead colours for the same phases. 17HE15-1504S: A+ black, A- blue, B+ green, B- red.
  17HS19-2004S1: A+ black, A- green, B+ red, B- blue. Harnesses are wired by phase.
- D33 rerun: at 16 V the 7 kg EQ extreme at -20 C has a margin of 1.48 at 8 deg/s and 1.50 at 6 deg/s, so the 6 deg/s cold limit no longer helps.
- The TPS25752A needs a 5 V supply on PP5V (TI's own evaluation board has a separate 5 V converter), so a 5 V rail is added.
- KiCad 9's 3D library has no model for the 15-way JST-GH header or the SMD JST-PH header; envelope models are generated for the fit check.

## Questions for Bruno (work continues with the recommended option, marked pending approval)

| # | Question | Recommendation |
| --- | --- | --- |
| Q22 | D26 cold slew limit | Drop the 6 deg/s limit: 8 deg/s over the whole -20 to +40 C range (changes D26) |
| Q23 | Two-level motor rail | 16 V for slews, 10 V for tracking and holding, switched by one pin (VM_SEL): StealthChop cannot regulate the small tracking currents on 16 V |
| Q24 | 5 V rail | Add a TPS62933 3 A buck for PP5V of both PD controllers (extends D27) |
| Q25 | Inrush and reverse polarity | P-FET switch with soft start in front of the boost (also a true off for the motor rail), and a P-FET at the pack input against a reversed bench supply |
| Q26 | Motor thermistor | A 10 k bead on wires taped to the motor case, soldered to two pads on the cartridge board, instead of a chip thermistor on the board 58 mm from the motor |
| Q27 | Cartridge plug pinout | Phase A on pins 1-4, signals on 5-11, phase B on 12-15 (keeps each phase pair together and away from the encoder) |

## Open access issue

The session could attach the repository read-only. Commits are on the local branch; pushing and the pull request need push access.
