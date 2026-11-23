# ST-501 — connections still open

From KiCad's design-rule check of `st-501.kicad_pcb`: **18 open connections in 17 nets**, 0 errors. F = front face (red in KiCad), B = inner face (blue), In2 = inner layer 2. X and Y are the cursor position KiCad shows at the bottom of its window.

| No. | Net | From | Face | X | Y | To | Face | X | Y | Distance, mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `+3V3` | via | all | 119.90 | 118.80 | J5 pad 1 | B | 123.27 | 122.14 | 4.7 |
| 2 | `ALT_VREF` | track end (1.5000 mm piece) | F | 105.50 | 82.35 | U17 pad 17 | B | 110.00 | 81.65 | 4.6 |
| 3 | `A_CC2` | U3 pad 29 | B | 73.80 | 104.08 | track end (3.3941 mm piece) | In3 | 76.45 | 102.40 | 3.1 |
| 4 | `B_DP` | track end (3.3500 mm piece) | F | 63.40 | 99.20 | U6 pad 22 | B | 57.01 | 104.90 | 8.6 |
| 5 | `CHG_TS` | via | all | 70.95 | 95.45 | U2 pad 16 | B | 71.15 | 95.10 | 0.4 |
| 6 | `LED_RP_A` | D10 pad 2 | F | 112.81 | 99.05 | R64 pad 2 | B | 125.25 | 109.51 | 16.3 |
| 7 | `LINK_SYNC` | U14 pad 4 | B | 120.45 | 104.90 | U13 pad 9 | B | 85.25 | 112.30 | 36.0 |
| 8 | `NTC_ALT_A` | C119 pad 1 | F | 110.08 | 100.90 | U14 pad 41 | B | 113.55 | 105.30 | 5.6 |
| 9 | `NTC_ALT_A` | U14 pad 41 | B | 113.55 | 105.30 | TP53 pad 1 | B | 126.65 | 98.35 | 14.8 |
| 10 | `PDA_ADC2` | R18 pad 1 | B | 77.24 | 110.95 | U3 pad 3 | B | 77.92 | 105.80 | 5.2 |
| 11 | `PDA_LDO3V3` | TP15 pad 1 | B | 74.95 | 117.05 | track end (0.0500 mm piece) | In3 | 74.90 | 111.95 | 5.1 |
| 12 | `PDA_SDAC` | track end (3.6062 mm piece) | F | 72.30 | 110.60 | U3 pad 16 | B | 73.80 | 107.92 | 3.1 |
| 13 | `PDB_LD1` | U6 pad 5 | B | 60.99 | 105.70 | R35 pad 1 | B | 61.70 | 110.44 | 4.8 |
| 14 | `PDB_SDAC` | track end (2.4500 mm piece) | In3 | 57.90 | 106.35 | U6 pad 15 | B | 58.00 | 107.49 | 1.1 |
| 15 | `STEP_ALT` | U17 pad 16 | B | 109.50 | 81.65 | U14 pad 29 | B | 114.60 | 109.95 | 28.8 |
| 16 | `STEP_ROLL` | U19 pad 16 | B | 109.50 | 91.05 | U14 pad 32 | B | 113.55 | 108.90 | 18.3 |
| 17 | `VMOT_MON` | R51 pad 2 | B | 109.60 | 111.89 | track end (0.7071 mm piece) | In2 | 108.80 | 106.30 | 5.6 |
| 18 | `VPB` | copper area | B, | 51.45 | 111.59 | copper area | B, | 51.45 | 111.59 | 0.0 |

## Finishing a connection by hand in KiCad 9

1. Start **KiCad**, click **File → Open Project**, choose `hardware/electronics/mainboard/st-501.kicad_pro`, then click the **PCB Editor** button (the green board icon).
2. The thin white lines are the open connections. To find one from the table: click **Edit → Find**, type the part name from the *From* column (for example `U14`) and click **Find Next**; or move the cursor until the X and Y at the bottom of the window match the table.
3. In the **Appearance** panel on the right, tab **Nets**, right-click the net's name and choose **Highlight** to see everything that belongs to it.
4. Click **Route → Route Single Track** (or press **X**), click the pad or track end in the *From* column, move toward the *To* item and click to set corners. KiCad will not let the track touch other copper. Press **V** to drop a via and continue on the other face (red = front, blue = inner face). Click the *To* item to finish; **Esc** leaves the tool.
5. If there is no room, press **Esc**, click a track that is in the way and press **D** to drag it aside, or **U** then **Delete** to remove a leftover track end (the board has some from connections that were taken up).
6. Vias must stay 0.8 mm apart centre to centre, and a track 0.25 mm from a via's hole; the check in step 7 reports any that are not.
7. When the white lines are gone: **Inspect → Design Rules Checker**, tick **Refill all zones before performing DRC** and **Test for parity between PCB and schematic**, click **Run DRC**. The tabs must show 0 *Violations* that are errors and 0 *Unconnected Items*.
8. **File → Save**. Send the saved `st-501.kicad_pcb` back (attach it to a chat or upload it to the branch): the fabrication files are then made from it by `tools/fab.py`. Do not run `tools/layout.py` on the board afterwards: it rebuilds the layout from the scripts and would discard hand-made tracks.
