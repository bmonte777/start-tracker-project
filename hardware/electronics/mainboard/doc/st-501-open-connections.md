# ST-501 — connections still open

From KiCad's design-rule check of `st-501.kicad_pcb`: **98 open connections in 61 nets**, 5 errors. F = front face (red in KiCad), B = inner face (blue), In2 = inner layer 2. X and Y are the cursor position KiCad shows at the bottom of its window.

| No. | Net | From | Face | X | Y | To | Face | X | Y | Distance, mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `+3V3` | R55 pad 1 | B | 81.19 | 111.10 | C20 pad 1 | B | 75.53 | 111.05 | 5.7 |
| 2 | `+3V3` | via | all | 111.85 | 103.70 | via | all | 110.55 | 101.65 | 2.4 |
| 3 | `+3V3` | track end (1.0500 mm piece) | B | 113.55 | 106.50 | track end (0.4950 mm piece) | F | 113.00 | 108.85 | 2.4 |
| 4 | `+3V3` | track end (1.0500 mm piece) | B | 115.40 | 103.05 | track end (1.7000 mm piece) | B | 113.55 | 103.70 | 2.0 |
| 5 | `+3V3` | track end (1.0500 mm piece) | B | 120.45 | 107.70 | track end (1.0500 mm piece) | B | 118.20 | 109.95 | 3.2 |
| 6 | `+3V3` | via | all | 122.15 | 103.70 | via | all | 124.10 | 103.15 | 2.0 |
| 7 | `+3V3` | via | all | 123.20 | 118.55 | track end (0.4000 mm piece) | F | 120.25 | 118.65 | 3.0 |
| 8 | `+3V3` | J5 pad 1 | B | 123.27 | 122.14 | via | all | 123.20 | 118.55 | 3.6 |
| 9 | `+3V3` | track end (0.3500 mm piece) | B | 123.65 | 108.80 | via | all | 121.50 | 107.70 | 2.4 |
| 10 | `+3V3` | C85 pad 1 | B | 124.45 | 111.03 | track end (0.1414 mm piece) | B | 123.75 | 108.70 | 2.4 |
| 11 | `+3V3` | via | all | 125.20 | 116.30 | TP27 pad 1 | B | 123.25 | 117.15 | 2.1 |
| 12 | `AZ_CPI` | C102 pad 2 | B | 105.38 | 75.75 | U15 pad 5 | B | 110.00 | 77.15 | 4.8 |
| 13 | `AZ_VCP` | C103 pad 1 | B | 105.08 | 77.35 | U15 pad 6 | B | 109.50 | 77.15 | 4.4 |
| 14 | `A_CC1` | TP16 pad 1 | B | 65.75 | 110.50 | track end (0.9899 mm piece) | F | 69.00 | 106.15 | 5.4 |
| 15 | `A_CC1` | track end (1.6971 mm piece) | F | 73.90 | 101.95 | U3 pad 28 | B | 73.40 | 104.08 | 2.2 |
| 16 | `A_CC2` | D5 pad 1 | F | 68.40 | 107.50 | TP17 pad 1 | F | 66.05 | 109.70 | 3.2 |
| 17 | `A_CC2` | U3 pad 29 | B | 73.80 | 104.08 | track end (1.7000 mm piece) | F | 70.90 | 102.50 | 3.3 |
| 18 | `A_DP` | track end (0.1000 mm piece) | F | 74.50 | 115.00 | J3 pad B6 | F | 75.38 | 116.11 | 1.4 |
| 19 | `BOOST_EN` | R50 pad 1 | F | 129.51 | 110.10 | track end (0.5657 mm piece) | B | 130.45 | 112.70 | 2.8 |
| 20 | `BST_SW` | U12 pad 9 | B | 133.25 | 111.83 | track end (0.1500 mm piece) | F | 130.40 | 109.60 | 3.6 |
| 21 | `B_CC2` | J4 pad B5 | F | 63.17 | 116.11 | track end (3.0000 mm piece) | F | 56.45 | 108.20 | 10.4 |
| 22 | `B_DP` | TP23 pad 1 | F | 53.60 | 95.50 | U6 pad 22 | B | 57.01 | 104.90 | 10.0 |
| 23 | `B_DP` | J4 pad A6 | F | 61.59 | 114.59 | U6 pad 22 | B | 57.01 | 104.90 | 10.7 |
| 24 | `CHG_REGN` | U2 pad 5 | B | 74.90 | 93.50 | C4 pad 1 | B | 73.78 | 98.60 | 5.2 |
| 25 | `CHG_STAT` | U2 pad 1 | B | 74.90 | 91.90 | track end (0.3000 mm piece) | B | 75.15 | 91.35 | 0.6 |
| 26 | `CHG_TS` | U2 pad 16 | B | 71.15 | 95.10 | track end (4.8000 mm piece) | B | 71.00 | 95.65 | 0.6 |
| 27 | `DIAG_ROLL` | U14 pad 12 | B | 120.45 | 108.10 | track end (0.7500 mm piece) | B | 108.05 | 93.50 | 19.2 |
| 28 | `DIR_ROLL` | track end (0.9500 mm piece) | B | 112.80 | 108.50 | U19 pad 19 | B | 111.00 | 91.05 | 17.5 |
| 29 | `DRV_EN_N` | R66 pad 2 | B | 112.55 | 114.84 | track end (1.3000 mm piece) | B | 112.70 | 108.20 | 6.6 |
| 30 | `ENC_MISO` | track end (3.4500 mm piece) | B | 132.05 | 78.10 | J8 pad 9 | B | 128.25 | 83.55 | 6.6 |
| 31 | `ENC_MOSI_M` | R83 pad 1 | F | 129.34 | 82.20 | track end (0.8485 mm piece) | F | 131.15 | 81.25 | 2.0 |
| 32 | `ENC_MOSI_M` | R83 pad 1 | F | 129.34 | 82.20 | R92 pad 1 | F | 127.34 | 90.25 | 8.3 |
| 33 | `ENC_MOSI_M` | track end (4.5962 mm piece) | In2 | 130.15 | 106.25 | TP42 pad 1 | F | 127.45 | 105.35 | 2.8 |
| 34 | `ENC_SCK_M` | track end (0.1500 mm piece) | B | 118.45 | 113.20 | track end (2.0000 mm piece) | B | 116.00 | 117.40 | 4.9 |
| 35 | `ENC_SCK_M` | R82 pad 1 | F | 129.74 | 83.55 | track end (6.0500 mm piece) | In2 | 130.35 | 86.40 | 2.9 |
| 36 | `ESP_IO0` | R54 pad 2 | F | 109.09 | 110.10 | U13 pad 27 | B | 102.75 | 105.95 | 7.6 |
| 37 | `GND` | copper area | B, | 50.50 | 129.50 | U23 pad 8 | B | 85.85 | 99.15 | 46.6 |
| 38 | `GND` | U4 pad 2 | B | 68.97 | 100.36 | U4 pad 3 | B | 68.97 | 101.64 | 1.3 |
| 39 | `GND` | U4 pad 4 | B | 68.97 | 102.91 | U4 pad 3 | B | 68.97 | 101.64 | 1.3 |
| 40 | `GND` | U23 pad 8 | B | 85.85 | 99.15 | U23 pad 5 | B | 85.85 | 101.85 | 2.7 |
| 41 | `GND` | J2 pad MP | B | 117.12 | 119.15 | SW2 pad 2 | F | 117.00 | 119.88 | 0.7 |
| 42 | `GNSS_BIAS` | R95 pad 2 | F | 91.79 | 94.95 | C137 pad 1 | F | 118.30 | 96.43 | 26.6 |
| 43 | `GNSS_BIAS` | C137 pad 1 | F | 118.30 | 96.43 | L7 pad 1 | F | 118.77 | 93.95 | 2.5 |
| 44 | `GNSS_PPS` | track end (0.7500 mm piece) | B | 120.45 | 105.30 | U24 pad 4 | B | 105.15 | 97.20 | 17.3 |
| 45 | `I2C_SCL` | track end (2.5456 mm piece) | B | 60.45 | 108.25 | track end (3.9000 mm piece) | In2 | 72.45 | 107.40 | 12.0 |
| 46 | `I2C_SCL` | track end (0.8485 mm piece) | In2 | 81.35 | 96.20 | R56 pad 2 | F | 85.45 | 101.51 | 6.7 |
| 47 | `I2C_SCL` | R56 pad 2 | F | 85.45 | 101.51 | U23 pad 3 | B | 87.15 | 100.95 | 1.8 |
| 48 | `I2C_SCL` | U13 pad 17 | B | 89.56 | 104.70 | U23 pad 3 | B | 87.15 | 100.95 | 4.5 |
| 49 | `I2C_SCL` | U21 pad 13 | B | 91.00 | 99.09 | U23 pad 3 | B | 87.15 | 100.95 | 4.3 |
| 50 | `I2C_SDA` | U23 pad 4 | B | 87.15 | 101.85 | track end (2.1920 mm piece) | In2 | 85.75 | 107.40 | 5.7 |
| 51 | `I2C_SDA` | U21 pad 14 | B | 91.50 | 99.09 | U23 pad 4 | B | 87.15 | 101.85 | 5.2 |
| 52 | `IMU_INT` | U13 pad 15 | B | 87.02 | 104.70 | track end (0.4950 mm piece) | B | 92.40 | 101.20 | 6.4 |
| 53 | `LED_B` | R106 pad 1 | F | 87.70 | 99.71 | U13 pad 22 | B | 95.91 | 104.70 | 9.6 |
| 54 | `LINK_RX` | U13 pad 11 | B | 85.25 | 109.76 | TP38 pad 1 | F | 85.75 | 96.15 | 13.6 |
| 55 | `LINK_SYNC` | U13 pad 9 | B | 85.25 | 112.30 | track end (0.7500 mm piece) | B | 120.45 | 104.90 | 36.0 |
| 56 | `LINK_TX` | track end (0.7500 mm piece) | B | 120.45 | 104.50 | U13 pad 10 | B | 85.25 | 111.03 | 35.8 |
| 57 | `MOTOR_PWR_EN` | Q7 pad 1 | B | 109.54 | 106.90 | R44 pad 1 | B | 108.05 | 111.89 | 5.2 |
| 58 | `NTC_AZ_A` | track end (0.6364 mm piece) | B | 109.80 | 110.35 | U14 pad 40 | B | 113.55 | 105.70 | 6.0 |
| 59 | `NTC_ROLL_A` | C128 pad 1 | F | 111.03 | 99.45 | U14 pad 42 | B | 113.55 | 104.90 | 6.0 |
| 60 | `NTC_ROLL_A` | U14 pad 42 | B | 113.55 | 104.90 | TP54 pad 1 | F | 125.85 | 99.10 | 13.6 |
| 61 | `PACK_SCL` | R5 pad 2 | B | 87.46 | 97.70 | TP8 pad 1 | F | 85.80 | 98.55 | 1.9 |
| 62 | `PACK_SCL` | R5 pad 2 | B | 87.46 | 97.70 | U13 pad 19 | B | 92.09 | 104.70 | 8.4 |
| 63 | `PACK_SDA` | R6 pad 2 | B | 84.25 | 101.76 | U13 pad 18 | B | 90.83 | 104.70 | 7.2 |
| 64 | `PACK_SDA` | TP9 pad 1 | B | 88.95 | 94.90 | R6 pad 2 | B | 84.25 | 101.76 | 8.3 |
| 65 | `PACK_SDA` | R3 pad 2 | F | 115.01 | 122.35 | U13 pad 18 | B | 90.83 | 104.70 | 29.9 |
| 66 | `PB_GVBUS` | Q3 pad 4 | B | 55.15 | 109.47 | U6 pad 21 | B | 57.01 | 105.30 | 4.6 |
| 67 | `PDA_IRQC` | R22 pad 2 | B | 71.66 | 110.80 | via | all | 72.05 | 109.35 | 1.5 |
| 68 | `PDA_IRQC` | U3 pad 18 | B | 73.00 | 107.92 | track end (1.4142 mm piece) | F | 72.60 | 93.45 | 14.5 |
| 69 | `PDA_LDO3V3` | R17 pad 1 | B | 77.79 | 101.10 | track end (1.7500 mm piece) | In2 | 78.35 | 101.35 | 0.6 |
| 70 | `PDA_SCLC` | R21 pad 2 | F | 73.99 | 111.05 | track end (1.6500 mm piece) | B | 72.55 | 109.55 | 2.1 |
| 71 | `PDA_SDAC` | U4 pad 5 | B | 64.03 | 102.91 | track end (2.2000 mm piece) | B | 71.55 | 96.50 | 9.9 |
| 72 | `PDA_SDAC` | U3 pad 16 | B | 73.80 | 107.92 | track end (2.6500 mm piece) | F | 72.75 | 110.50 | 2.8 |
| 73 | `PDA_SDAC` | TP13 pad 1 | B | 75.00 | 114.20 | track end (0.8000 mm piece) | F | 76.35 | 111.50 | 3.0 |
| 74 | `PDB_ADC2` | U6 pad 3 | B | 60.99 | 104.90 | R34 pad 1 | B | 66.20 | 104.89 | 5.2 |
| 75 | `PDB_GPIO3` | U6 pad 18 | B | 57.01 | 106.50 | R29 pad 1 | B | 59.24 | 110.75 | 4.8 |
| 76 | `PDB_IRQC` | U7 pad 14 | B | 68.10 | 83.50 | track end (3.9500 mm piece) | In2 | 55.30 | 101.10 | 21.8 |
| 77 | `PDB_LD1` | track end (0.2121 mm piece) | B | 61.70 | 105.70 | R35 pad 1 | B | 61.70 | 110.44 | 4.7 |
| 78 | `PDB_LD2` | R36 pad 1 | F | 63.94 | 107.70 | track end (2.4000 mm piece) | B | 62.00 | 106.20 | 2.5 |
| 79 | `PDB_LDO1V5` | track end (0.7000 mm piece) | B | 61.70 | 105.30 | C47 pad 1 | B | 64.25 | 106.88 | 3.0 |
| 80 | `PDB_LDO3V3` | U8 pad 8 | B | 53.09 | 100.47 | track end (0.6364 mm piece) | B | 60.85 | 99.75 | 7.8 |
| 81 | `PDB_LDO3V3` | track end (0.2828 mm piece) | B | 64.40 | 103.80 | C46 pad 1 | B | 63.97 | 105.30 | 1.6 |
| 82 | `PDB_SDAC` | R31 pad 2 | F | 57.39 | 110.65 | U6 pad 15 | B | 58.00 | 107.49 | 3.2 |
| 83 | `PDB_SDAC` | track end (2.6000 mm piece) | B | 59.70 | 101.35 | U7 pad 6 | B | 71.90 | 83.50 | 21.6 |
| 84 | `PORTB_EN` | U7 pad 4 | B | 71.84 | 82.50 | R28 pad 1 | F | 77.09 | 80.50 | 5.6 |
| 85 | `RP_SWDIO` | U14 pad 25 | B | 116.20 | 109.95 | track end (1.2000 mm piece) | In2 | 108.50 | 114.05 | 8.7 |
| 86 | `RTC_VBAK` | U23 pad 6 | B | 85.85 | 100.95 | track end (3.7000 mm piece) | B | 82.90 | 97.00 | 4.9 |
| 87 | `SMBD_J` | U1 pad 3 | B | 128.41 | 105.10 | R3 pad 1 | F | 113.99 | 122.35 | 22.5 |
| 88 | `STEP_ALT` | track end (0.7500 mm piece) | B | 114.60 | 109.95 | U17 pad 16 | B | 109.50 | 81.65 | 28.8 |
| 89 | `STEP_ROLL` | U19 pad 16 | B | 109.50 | 91.05 | track end (0.7778 mm piece) | B | 112.55 | 108.90 | 18.1 |
| 90 | `TMC_UART` | U14 pad 8 | B | 120.45 | 106.50 | R65 pad 2 | F | 125.06 | 106.10 | 4.6 |
| 91 | `VBAT` | copper area | B, | 128.45 | 122.10 | copper area | F, | 131.21 | 127.16 | 5.8 |
| 92 | `VMOT` | track end (0.0500 mm piece) | F | 115.95 | 73.00 | track end (1.6263 mm piece) | B | 113.30 | 73.00 | 2.7 |
| 93 | `VMOT_MON` | U14 pad 43 | B | 113.55 | 104.50 | C79 pad 1 | B | 107.58 | 105.30 | 6.0 |
| 94 | `VMOT_MON` | R52 pad 1 | F | 118.70 | 99.46 | U14 pad 43 | B | 113.55 | 104.50 | 7.2 |
| 95 | `VM_SEL` | Q8 pad 1 | B | 139.85 | 111.99 | U14 pad 36 | B | 113.55 | 107.30 | 26.7 |
| 96 | `VSYS` | track end (0.4000 mm piece) | B | 81.25 | 114.85 | via | all | 68.60 | 94.65 | 23.8 |
| 97 | `VSYS` | copper area | In2, | 87.50 | 123.40 | copper area | In2, | 50.50 | 129.50 | 37.5 |
| 98 | `WAKE_IRQ_N` | U13 pad 6 | B | 85.25 | 116.11 | U23 pad 2 | B | 87.15 | 100.05 | 16.2 |

## Errors

| Type | What KiCad says | Items | X | Y |
|---|---|---|---|---|
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1250 mm) | Pad 1 [VM_SEL] of Q8 on B.Cu; Track [BST_SW] on B.Cu, length 0.2500 mm | 139.85 | 111.99 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1000 mm) | Pad 2 [+5V] of L4 on B.Cu; Track [VBUS_CHG] on B.Cu, length 2.7500 mm | 84.47 | 73.80 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1011 mm) | Track [+5V] on B.Cu, length 0.7071 mm; Pad 1 [LINK_TX] of TP37 on B.Cu | 81.65 | 122.70 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1000 mm) | Pad 1 [PB_SW1] of L2 on B.Cu; Track [CHG_PMID] on B.Cu, length 0.0707 mm | 72.53 | 74.80 |
| clearance | Clearance violation ( clearance 0.1270 mm; actual 0.1000 mm) | Pad 1 [VBUS_B] of D6 on F.Cu; Track [VPB] on F.Cu, length 2.1920 mm | 54.15 | 115.80 |

## Finishing a connection by hand in KiCad 9

1. Start **KiCad**, click **File → Open Project**, choose `hardware/electronics/mainboard/st-501.kicad_pro`, then click the **PCB Editor** button (the green board icon).
2. The thin white lines are the open connections. To find one from the table: click **Edit → Find**, type the part name from the *From* column (for example `U14`) and click **Find Next**; or move the cursor until the X and Y at the bottom of the window match the table.
3. In the **Appearance** panel on the right, tab **Nets**, right-click the net's name and choose **Highlight** to see everything that belongs to it.
4. Click **Route → Route Single Track** (or press **X**), click the pad or track end in the *From* column, move toward the *To* item and click to set corners. KiCad will not let the track touch other copper. Press **V** to drop a via and continue on the other face (red = front, blue = inner face). Click the *To* item to finish; **Esc** leaves the tool.
5. If there is no room, press **Esc**, click a track that is in the way and press **D** to drag it aside, or **U** then **Delete** to remove a leftover track end (the board has some from connections that were taken up).
6. Vias must stay 0.8 mm apart centre to centre, and a track 0.25 mm from a via's hole; the check in step 7 reports any that are not.
7. When the white lines are gone: **Inspect → Design Rules Checker**, tick **Refill all zones before performing DRC** and **Test for parity between PCB and schematic**, click **Run DRC**. The tabs must show 0 *Violations* that are errors and 0 *Unconnected Items*.
8. **File → Save**. Send the saved `st-501.kicad_pcb` back (attach it to a chat or upload it to the branch): the fabrication files are then made from it by `tools/fab.py`. Do not run `tools/layout.py` on the board afterwards: it rebuilds the layout from the scripts and would discard hand-made tracks.
