# ST-501 — connections still open

From KiCad's design-rule check of `st-501.kicad_pcb`: **2 open connections in 2 nets**, 0 errors. F = front face (red in KiCad), B = inner face (blue), In2 = inner layer 2. X and Y are the cursor position KiCad shows at the bottom of its window.

| No. | Net | From | Face | X | Y | To | Face | X | Y | Distance, mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `B_CC2` | track end (0.5000 mm piece) | F | 54.20 | 99.95 | D8 pad 1 | F | 52.90 | 104.50 | 4.7 |
| 2 | `B_DP` | track end (1.1314 mm piece) | In2 | 51.20 | 104.45 | U6 pad 22 | B | 57.01 | 104.90 | 5.8 |

## Finishing a connection by hand in KiCad 9

1. Start **KiCad**, click **File → Open Project**, choose `hardware/electronics/mainboard/st-501.kicad_pro`, then click the **PCB Editor** button (the green board icon).
2. The thin white lines are the open connections. To find one from the table: click **Edit → Find**, type the part name from the *From* column (for example `U14`) and click **Find Next**; or move the cursor until the X and Y at the bottom of the window match the table.
3. In the **Appearance** panel on the right, tab **Nets**, right-click the net's name and choose **Highlight** to see everything that belongs to it.
4. Click **Route → Route Single Track** (or press **X**), click the pad or track end in the *From* column, move toward the *To* item and click to set corners. KiCad will not let the track touch other copper. Press **V** to drop a via and continue on the other face (red = front, blue = inner face). Click the *To* item to finish; **Esc** leaves the tool.
5. If there is no room, press **Esc**, click a track that is in the way and press **D** to drag it aside, or **U** then **Delete** to remove a leftover track end (the board has some from connections that were taken up).
6. Vias must stay 0.8 mm apart centre to centre, and a track 0.25 mm from a via's hole; the check in step 7 reports any that are not.
7. When the white lines are gone: **Inspect → Design Rules Checker**, tick **Refill all zones before performing DRC** and **Test for parity between PCB and schematic**, click **Run DRC**. The tabs must show 0 *Violations* that are errors and 0 *Unconnected Items*.
8. **File → Save**. Send the saved `st-501.kicad_pcb` back (attach it to a chat or upload it to the branch): the fabrication files are then made from it by `tools/fab.py`. Do not run `tools/layout.py` on the board afterwards: it rebuilds the layout from the scripts and would discard hand-made tracks.
