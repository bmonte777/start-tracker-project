# ST-501 — connections still open

From KiCad's design-rule check of `st-501.kicad_pcb`: **39 open connections in 30 nets**, 10 errors. F = front face (red in KiCad), B = inner face (blue), In2 = inner layer 2. X and Y are the cursor position KiCad shows at the bottom of its window.

| No. | Net | From | Face | X | Y | To | Face | X | Y | Distance, mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `+3V3` | via | all | 120.65 | 118.80 | J5 pad 1 | B | 123.27 | 122.14 | 4.2 |
| 2 | `ALT_VREF` | U17 pad 17 | B | 110.00 | 81.65 | R80 pad 1 | B | 105.31 | 80.65 | 4.8 |
| 3 | `AZ_CPI` | C102 pad 2 | B | 105.38 | 75.75 | U15 pad 5 | B | 110.00 | 77.15 | 4.8 |
| 4 | `AZ_VCP` | C103 pad 1 | B | 105.08 | 77.35 | U15 pad 6 | B | 109.50 | 77.15 | 4.4 |
| 5 | `A_CC2` | U3 pad 29 | B | 73.80 | 104.08 | track end (4.3841 mm piece) | In2 | 76.65 | 103.50 | 2.9 |
| 6 | `CHG_SDRV` | track end (0.3500 mm piece) | B | 71.05 | 91.35 | U2 pad 24 | B | 71.14 | 91.90 | 0.6 |
| 7 | `CHG_STAT` | U2 pad 1 | B | 74.90 | 91.90 | track end (0.3500 mm piece) | B | 74.95 | 91.35 | 0.6 |
| 8 | `CHG_TS` | track end (3.3234 mm piece) | B | 70.85 | 95.65 | U2 pad 16 | B | 71.15 | 95.10 | 0.6 |
| 9 | `ENC_MISO` | track end (0.1000 mm piece) | In2 | 128.30 | 85.90 | J9 pad 9 | B | 128.25 | 90.65 | 4.8 |
| 10 | `ENC_MISO` | U18 pad 6 | B | 129.11 | 93.15 | J9 pad 9 | B | 128.25 | 90.65 | 2.6 |
| 11 | `ENC_MISO` | track end (2.6870 mm piece) | In3 | 130.30 | 111.65 | TP43 pad 1 | F | 129.60 | 107.95 | 3.8 |
| 12 | `ENC_MISO` | U20 pad 6 | B | 133.70 | 95.64 | U18 pad 6 | B | 129.11 | 93.15 | 5.2 |
| 13 | `ENC_MOSI_M` | R92 pad 1 | F | 127.34 | 90.25 | R83 pad 1 | F | 129.34 | 82.20 | 8.3 |
| 14 | `ENC_SCK_M` | track end (0.4500 mm piece) | In3 | 126.40 | 87.15 | R91 pad 1 | F | 129.74 | 90.65 | 4.8 |
| 15 | `LINK_TX` | track end (0.7500 mm piece) | B | 120.45 | 104.50 | track end (0.5000 mm piece) | B | 98.80 | 116.30 | 24.7 |
| 16 | `NTC_AZ` | J7 pad 10 | B | 127.00 | 76.45 | R76 pad 1 | F | 126.70 | 78.04 | 1.6 |
| 17 | `NTC_AZ` | R75 pad 2 | F | 127.85 | 75.11 | J7 pad 10 | B | 127.00 | 76.45 | 1.6 |
| 18 | `NTC_ROLL_A` | C128 pad 1 | F | 111.03 | 99.45 | track end (0.7778 mm piece) | B | 111.15 | 105.00 | 5.6 |
| 19 | `NTC_ROLL_A` | track end (0.7500 mm piece) | B | 113.55 | 104.90 | TP54 pad 1 | F | 125.85 | 99.10 | 13.6 |
| 20 | `PB_GVBUS` | Q3 pad 4 | B | 55.15 | 109.47 | U6 pad 21 | B | 57.01 | 105.30 | 4.6 |
| 21 | `PB_GVSYS` | Q2 pad 4 | B | 55.15 | 105.17 | U6 pad 20 | B | 57.01 | 105.70 | 1.9 |
| 22 | `PDA_ADC2` | R18 pad 1 | B | 77.24 | 110.95 | U3 pad 3 | B | 77.92 | 105.80 | 5.2 |
| 23 | `PDA_LDO3V3` | R21 pad 1 | F | 75.01 | 111.05 | R20 pad 1 | F | 71.44 | 110.80 | 3.6 |
| 24 | `PDA_SDAC` | R20 pad 2 | F | 72.46 | 110.80 | U3 pad 16 | B | 73.80 | 107.92 | 3.2 |
| 25 | `PDB_ADC2` | track end (0.8000 mm piece) | B | 63.60 | 105.85 | R34 pad 1 | B | 66.20 | 104.89 | 2.8 |
| 26 | `PDB_LD1` | track end (0.4243 mm piece) | B | 61.70 | 105.70 | R35 pad 1 | B | 61.70 | 110.44 | 4.7 |
| 27 | `PDB_SCLC` | R32 pad 2 | F | 53.91 | 109.05 | track end (3.7000 mm piece) | In3 | 57.50 | 108.25 | 3.7 |
| 28 | `PDB_SCLC` | U8 pad 6 | B | 55.63 | 100.47 | track end (5.5500 mm piece) | In3 | 57.55 | 101.25 | 2.1 |
| 29 | `PDB_SDAC` | R31 pad 2 | F | 57.39 | 110.65 | U6 pad 15 | B | 58.00 | 107.49 | 3.2 |
| 30 | `PWR_IRQ_N` | track end (0.3536 mm piece) | B | 60.00 | 110.10 | via | all | 76.10 | 109.95 | 16.1 |
| 31 | `PWR_IRQ_N` | R57 pad 2 | F | 90.15 | 97.01 | track end (1.5000 mm piece) | F | 93.85 | 93.35 | 5.2 |
| 32 | `ROLL_VREF` | U19 pad 17 | B | 110.00 | 91.05 | track end (0.3000 mm piece) | B | 103.60 | 88.80 | 6.8 |
| 33 | `RP_SWCLK` | track end (5.4000 mm piece) | B | 115.55 | 112.00 | via | all | 106.85 | 111.70 | 8.7 |
| 34 | `RP_SWDIO` | track end (4.0000 mm piece) | F | 116.30 | 109.35 | R60 pad 2 | B | 106.56 | 112.70 | 10.3 |
| 35 | `RP_SWDIO` | J6 pad 2 | B | 123.27 | 126.36 | track end (4.0000 mm piece) | F | 116.30 | 109.35 | 18.4 |
| 36 | `VMOT` | copper area | B, | 112.05 | 95.00 | copper area | In1, | 111.80 | 97.00 | 2.0 |
| 37 | `VMOT_MON` | track end (0.2000 mm piece) | F | 110.35 | 104.00 | C79 pad 1 | B | 107.58 | 105.30 | 3.1 |
| 38 | `VMOT_MON` | R52 pad 1 | F | 118.70 | 99.46 | track end (0.7500 mm piece) | B | 113.55 | 104.50 | 7.2 |
| 39 | `VPB` | U6 pad 19 | B | 57.01 | 106.10 | track end (2.2000 mm piece) | In2 | 56.60 | 104.20 | 1.9 |

## Errors

| Type | What KiCad says | Items | X | Y |
|---|---|---|---|---|
| starved_thermal | Thermal relief connection to zone incomplete (layer F.Cu; zone min spoke count 2; actual 1) | Zone [GND] on F.Cu, priority 0; Pad 1 [GND] of TP10 on F.Cu | 50.50 | 129.50 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1000 mm) | Track [+5V] on B.Cu, length 0.4243 mm; Track [VBUS_A] on B.Cu, length 3.7000 mm | 68.95 | 115.65 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.0968 mm) | Track [BST_SW] on B.Cu, length 0.4950 mm; Track [VM_IN] on B.Cu, length 0.0707 mm | 130.95 | 109.50 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.0977 mm) | Track [BST_SW] on B.Cu, length 0.2000 mm; Track [VM_IN] on B.Cu, length 0.0707 mm | 131.15 | 109.50 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.0977 mm) | Pad 1 [PDB_SCLC] of TP21 on F.Cu; Track [VBUS_B] on F.Cu, length 0.4243 mm | 51.90 | 100.80 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1225 mm) | Track [VBUS_B] on B.Cu, length 0.2121 mm; Pad 6 [PDB_SCLC] of U8 on B.Cu | 55.30 | 98.90 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1236 mm) | Track [VBUS_CHG] on B.Cu, length 0.4950 mm; Track [+5V] on B.Cu, length 0.1414 mm | 74.85 | 100.15 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1180 mm) | Track [+5V] on B.Cu, length 0.3500 mm; Pad 1 [A_CC1] of TP16 on B.Cu | 64.75 | 111.00 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1250 mm) | Track [+5V] on B.Cu, length 0.0707 mm; Pad 1 [CHG_REGN] of C4 on B.Cu | 73.75 | 99.70 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1000 mm) | Track [VPB] on F.Cu, length 1.9799 mm; Pad 1 [VBUS_B] of D6 on F.Cu | 52.40 | 115.75 |

## Finishing a connection by hand in KiCad 9

1. Start **KiCad**, click **File → Open Project**, choose `hardware/electronics/mainboard/st-501.kicad_pro`, then click the **PCB Editor** button (the green board icon).
2. The thin white lines are the open connections. To find one from the table: click **Edit → Find**, type the part name from the *From* column (for example `U14`) and click **Find Next**; or move the cursor until the X and Y at the bottom of the window match the table.
3. In the **Appearance** panel on the right, tab **Nets**, right-click the net's name and choose **Highlight** to see everything that belongs to it.
4. Click **Route → Route Single Track** (or press **X**), click the pad or track end in the *From* column, move toward the *To* item and click to set corners. KiCad will not let the track touch other copper. Press **V** to drop a via and continue on the other face (red = front, blue = inner face). Click the *To* item to finish; **Esc** leaves the tool.
5. If there is no room, press **Esc**, click a track that is in the way and press **D** to drag it aside, or **U** then **Delete** to remove a leftover track end (the board has some from connections that were taken up).
6. Vias must stay 0.8 mm apart centre to centre, and a track 0.25 mm from a via's hole; the check in step 7 reports any that are not.
7. When the white lines are gone: **Inspect → Design Rules Checker**, tick **Refill all zones before performing DRC** and **Test for parity between PCB and schematic**, click **Run DRC**. The tabs must show 0 *Violations* that are errors and 0 *Unconnected Items*.
8. **File → Save**. Send the saved `st-501.kicad_pcb` back (attach it to a chat or upload it to the branch): the fabrication files are then made from it by `tools/fab.py`. Do not run `tools/layout.py` on the board afterwards: it rebuilds the layout from the scripts and would discard hand-made tracks.
