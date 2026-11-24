"""Content of the P0 bring-up companion (rendered by bringup_companion.py).

Sources for every expected reading:
  docs/04-electronics.md section 11 (Stages A-E), 10.3-10.6 (buses, boot, power-up, analogue scales), 5.1-5.3
  docs/05-firmware.md section 4 (bring-up menu and limits), 8 (loading), 9 (PD and gauge configuration), 10 (untested)
  firmware/rp2354a/bringup/tests.c and firmware/esp32s3/components/st_sys/bringup.cpp (the limits as coded)
  hardware/electronics/cartridge-board/design.py (ST-520 test pads TP1-TP9), mainboard model (C77/C78 on VMOT)
  MT6835 datasheet rev 1.3 (supply 22 mA typ, 15-28 mA; PWM on pin 10 by default at 994 Hz +/-8 %)
Each step: (id, menu key or "", title, do, expect, if_wrong). Text is HTML-safe by construction (no user data).
"""

SAFETY = [
    "Set the bench supply's voltage and current limit with the output <b>off</b>, before anything is connected. Use the limit given for each stage.",
    "If the supply drops into current limit (the CC lamp lights, the voltage falls), switch the output off at once and look for the cause before trying again.",
    "Plug and unplug harnesses, the display and the motor only with the supply off.",
    "Stage D moves the axis: the rig stands on its tripod, the body is free to turn ±180°, hands and cables are clear of the belt.",
    "Power resistors get hot (the 10 Ω load reaches about 26 W): lay them on a metal plate or a tile, not on the mat.",
]

BEFORE = [
    ("Files", [
        "On github.com open the repository, click <b>Actions</b> → <b>Firmware and apps</b> → <b>Run workflow</b>. In <b>Use workflow from</b> pick <code>phase-7-prototype</code> (or <code>main</code> once PR 13 is merged), then <b>Run workflow</b>. When it shows a green tick (about 30 minutes), open the run.",
        "Download <b>esp32s3-images-and-flasher</b> (web-flasher.html, st-esp32s3-bringup-full.bin, st-esp32s3-system-full.bin) and <b>rp2354a-images</b> (st_rp2354a_bringup.elf, for the Debug Probe route). Unzip both into one folder, e.g. <code>Documents\\StarTracker\\bringup</code>.",
        "Put <b>bench-logger.html</b> (sent with this page) in the same folder. It records the console into files for the measurements.",
        "The items <b>q</b> and <b>t</b>, the duration question of <b>k</b>, and the raw logs of <b>o</b> and <b>p</b> exist only in images built from <code>phase-7-prototype</code> after 24 November.",
    ]),
    ("Recording", [
        "Double-click bench-logger.html: it opens in Chrome or Edge. Type the label <code>P0-A</code> (reducer A; <code>P0-B</code> after sheet R).",
        "<b>Connect to the board</b> → pick the board's serial port → the menu appears. Use the key buttons or type into the box. Leave <b>Save each test to its own file</b> ticked: every test ends in a file named e.g. <code>P0-A_k_az_142310.txt</code>.",
        "Send me the files in the chat, or copy them into <code>docs/measurements/P0/A/</code>. Take a photo of anything you measure by hand (multimeter, scope) and send it too.",
    ]),
    ("Parts that may still be missing (D83)", [
        "If the clock U23 (RV-3028) is not fitted yet: item <b>2</b> lists 0x52 as MISSING and says FAIL — expected; every other address must be there. Skip item <b>4</b>.",
        "If the GNSS U24 (MAX-M10S) is not fitted yet: skip item <b>3</b> and step B8.",
        "The display is soldered at build sheet 11, after Stages B and C. Until then item <b>6</b> is skipped (or wire the module to J11 with four jumper wires: pin 1 VCC, 2 GND, 3 SCL, 4 SDA).",
        "P0 has no battery pack: item <b>c</b> (gauge) and the gauge set-up wait for P1.",
    ]),
]

TOOLS = [
    ("A", "Magnifier or phone macro, multimeter, bench supply, oscilloscope, spare magnet 6 × 2.5 mm diametric, two short thin wires"),
    ("B", "Bench supply with the XT30 bench lead, multimeter, PC with Chrome, USB-A to USB-C data cable, Debug Probe + TC2030 cable (fallback)"),
    ("C", "Oscilloscope, 10 Ω 50 W resistor + two 0.5 mm² wires, IR thermometer, 45 W USB-C charger + e-marked cable, FNB58 PD tester, port B load (see C4), multimeter"),
    ("D", "Rig on its tripod (sheet 12), the cartridge harness on J7, bench supply up to 3 A"),
]

STAGES = [
    {
        "id": "A", "title": "Stage A — cartridge board alone", "when": "Before build sheet 8 · 5 minutes per board · supply 3.3 V, limit 50 mA",
        "intro": "The ST-520 on the bench, nothing plugged in. Test pads on the top face (design.py): TP1 3.3 V, TP2 GND, TP3 CS, TP4 SCK, TP5 MISO, TP6 MOSI, TP7 CAL_EN, <b>TP8 PWM</b>, TP9 NTC.",
        "steps": [
            ("A1", "", "Look at the encoder chip", "Magnifier on U1's pins and the small capacitors beside it.",
             "No solder bridge, no ball of solder, the chip square on its pads, pin 1 mark matching the silkscreen dot.",
             "A bridge: flux, then drag a clean iron tip along the pins; look again. A crooked chip: ask me before reflowing it (the chip is scarce)."),
            ("A2", "", "No short on the supply", "Multimeter on continuity (beep) between TP1 (3.3 V) and TP2 (GND).",
             "No steady beep. A short chirp as the capacitors charge is normal; on the resistance range it climbs past 1 kΩ.",
             "Steady beep: a short. Look at C1–C3 and the chip pins again. Do not power the board."),
            ("A3", "", "Supply current", "Solder two short thin wires to TP1 and TP2 (pads are 1 mm). Supply at 3.3 V, limit 50 mA, output off; red to TP1, black to TP2; output on.",
             "15–28 mA (MT6835 datasheet: 22 mA typical, 15 min, 28 max; the Phase 4 plan said 15–25). The supply stays in voltage mode at 3.3 V.",
             "0–2 mA: the chip is not powered — VDD joint open, look at its supply pin. At the 50 mA limit: off at once; a short or a part turned round. 29–45 mA and the chip warm: off, report with a photo."),
            ("A4", "", "Encoder output (PWM)", "Scope probe on <b>TP8</b>, ground clip on TP2, 1 V/div, 500 µs/div. Hold the magnet 1–2 mm under the chip and turn it slowly.",
             "A square wave 0–3.3 V at 994 Hz (period 0.92–1.09 ms, ±8 %). Its duty follows the angle smoothly from about 0.4 % to 99.8 % once per magnet turn. Note: the Phase 4 plan names TP9; TP9 is the NTC pad, PWM is TP8 (finding F6).",
             "No signal: check TP7 (CAL_EN) reads 0 V; if it is high the pin shows calibration status instead (50 % duty). Duty does not move: the magnet is axial, not diametric, or too far away. Steps or jumps in the duty: report with a scope photo."),
            ("A5", "", "Thermistor bead (after you solder it at sheet 8)", "Supply off and wires removed. Multimeter on resistance between TP9 (NTC) and TP2 (GND).",
             "About 10 kΩ at 25 °C (10 k B3950: 12.5 kΩ at 20 °C, 8.1 kΩ at 30 °C).",
             "Open: a lead not soldered. Near 0 Ω: the leads touch. Far from these values: wrong bead (it must be 10 k B3950)."),
        ],
        "after": "Supply off, wires off, clean the flux with isopropyl alcohol. Write the current from A3 on the board's bag. Then build sheet 8.",
    },
    {
        "id": "B", "title": "Stage B — mainboard, no motors", "when": "Before build sheet 11 · supply 7.4 V, limit 0.3 A, then 1 A",
        "intro": "ST-501 on the mat. Nothing in J7–J9, no display. Supply through the XT30 bench lead to the battery pads J1 (red +). Test pads are named on the back face's silkscreen.",
        "steps": [
            ("B1", "", "No short on the rails", "Continuity from each of TP1 VBAT_IN, TP3 VSYS, TP27 +3V3, TP28 +5V, TP30 VMOT to ground (TP10 or TP11).",
             "No steady beep on any of them (a short chirp is the capacitors charging).",
             "Steady beep: find the short before powering — look for bridges near the converter on that rail (U8–U12 area) and turned capacitors."),
            ("B2", "", "First power-up", "Supply 7.4 V, limit <b>0.3 A</b>, output off. Plug the XT30. Output on, watch the current.",
             "30–120 mA, and the supply stays at 7.4 V (voltage mode).",
             "Current at the limit: output off at once. Feel for a warm part with a fingertip after power-off; look for a turned part. Below 10 mA: VSYS is not coming up — check B3."),
            ("B3", "", "Rails by hand", "Multimeter on TP3, TP27, TP28, TP33, TP30 (black on TP10).",
             "TP3 VSYS 7.3–7.4 V · TP27 +3V3 3.27–3.39 V · TP28 +5V 4.9–5.1 V · TP33 +1V1 1.05–1.15 V · TP30 VMOT 0 V.",
             "VSYS 0: the reverse-polarity P-FET or the charger U2 (BQ25792) does not pass the battery through. +3V3 wrong: TPS62932 and its divider 31.6 k / 10 k. +5V wrong: TPS563201, divider 54.9 k / 10 k. +1V1 wrong: the RP2354A's own core regulator and its 3.3 µH coil. VMOT not 0: the soft-start switch conducts — output off and report."),
            ("B4", "", "Reverse polarity", "Output off. At the supply end, swap the red and black banana plugs. Output on for two seconds, then off. Swap back.",
             "Current stays at 0 mA.",
             "Any current: the reverse-polarity FET is wrong or damaged — stop and report; do not go on."),
            ("B5", "", "USB and the bring-up image", "Raise the limit to <b>1 A</b>. USB cable from the PC to port A. In Windows, Device Manager → Ports shows a new COM port. Load the image: double-click web-flasher.html → <b>Connect to the head</b> → pick the port → <b>Choose file</b> st-esp32s3-bringup-full.bin → <b>Write complete image</b>. Then open bench-logger.html → <b>Connect to the board</b>.",
             "A new serial port appears (a blank ESP32-S3 starts its own USB loader). After the write the board restarts and the logger shows the menu ‘===== Star Tracker bring-up …’. Multimeter on J11 pins 1–2: 3.3 V.",
             "No port: try another cable (many charge-only cables have no data wires). Still none: the J5 pads with the TC2030 cable and the CP2102 adapter (Phase 4 section 10.4: IO0, EN, TX, RX, 3.3 V, GND). Write fails: retry once, then try another USB port on the PC."),
            ("B6", "1", "VSYS through the ESP32", "Menu <b>1</b>.",
             "PASS: VSYS 7.1–7.6 V (7.3–7.4 V plus the ADC's ±2 %).",
             "Far off with a good TP3 reading: the divider 100 k / 33 k on IO7 (scale × 4.03)."),
            ("B7", "2", "I²C scan", "Menu <b>2</b>.",
             "PASS: 0x20 (port A), 0x21 (port B), 0x30 (magnetometer), 0x52 (clock), 0x6A (IMU) present; 0x3C only with the display. Battery SMBus 0x0B ‘absent’ is right for P0 (no pack).",
             "One address missing: that chip's joints (or not fitted, D83: 0x52). None at all: SDA/SCL — TP35 and TP36 must idle at 3.3 V through the 2.2 k pull-ups; 0 V means a short to ground."),
            ("B8", "L", "Load the RP2354A bring-up image over SWD", "Menu <b>L</b>.",
             "‘written, verified’, PASS, and the heartbeat LED blinks at 2 Hz.",
             "This path is untested (Phase 5 section 10). Fallback: Debug Probe on J6 with the TC2030 cable; in VS Code with the Raspberry Pi Pico extension open st_rp2354a_bringup.elf and click <b>Flash</b>. Send me the log of L either way."),
            ("B9", "7", "Link to the RP2354A", "Menu <b>7</b>.",
             "PASS: ‘RP2354A firmware 0.1.0 (…), protocol’ equal to the ESP32's; good frames counting, 0 CRC errors.",
             "Silent: LINK_TX/RX (TP37, TP38) — both idle high at 3.3 V. CRC errors: report the counts."),
            ("B10", "8", "Step generators", "Menu <b>8</b>.",
             "PASS: 10 pulses queued on each STEP line, no FIFO overflow.",
             "FAIL: report the log (PIO set-up)."),
            ("B11", "4", "Clock and backup cell (if U23 is fitted)", "Menu <b>4</b>; answer <b>y</b> to set switchover and trickle charge.",
             "The clock answers; after y: ‘level mode (ok)’, trickle on. TP59 RTC_VBAK climbs toward about 3.0 V over a few hours.",
             "No answer: U23 joints. TP59 stays at 0 V after a day: the backup cell BT1 or its diode."),
            ("B12", "5", "IMU and magnetometer", "Menu <b>5</b>, board flat, away from the magnet and the motor.",
             "PASS: WHO_AM_I 0x70, |a| 0.9–1.1 g (about 1.00 g flat); magnetometer ID 0x30, |B| 0.15–0.8 G (Earth's field in Lisbon is about 0.44 G).",
             "|B| too high: a magnet or a steel tool nearby; move them and repeat. |a| far from 1 g: report the three axes."),
            ("B13", "3", "GNSS and 1 PPS (if U24 is fitted)", "Antenna or board near a window. Menu <b>3</b>; wait up to 5 minutes.",
             "PASS: bytes and NAV-PVT counting, then three PPS edges (TP44 pulses once a second); position printed.",
             "No bytes: the module's joints or its 3.3 V feed. Bytes but no PPS: no fix yet — more sky, wait longer."),
        ],
        "after": "Leave the display for sheet 11. Go on to Stage C with the board still on the bench.",
    },
    {
        "id": "C", "title": "Stage C — power paths", "when": "Before build sheet 11 · motor still unplugged · supply limit 3 A",
        "intro": "Same set-up. Item <b>P</b> (PD configuration) needs the two images from TI's tool (next card); do it before <b>b</b> and <b>d</b>.",
        "steps": [
            ("C1", "9", "Motor rail 10 V and 16 V", "Supply limit <b>3 A</b>. Menu <b>9</b>. Multimeter on TP30 during each level; then scope on TP30 (AC, 20 MHz limit, short ground spring to TP31).",
             "PASS: 9.5–10.5 V and 15.5–16.5 V (calculation 10.04 V and 16.04 V). Ripple under 100 mV peak-to-peak.",
             "Rail never comes up: the soft-start switch, then the TPS61288 (BOOST_EN) and coil L5. 16 V level wrong: the 36.5 k resistor switched by VM_SEL. Ripple high: photo of the scope."),
            ("C2", "a", "16 V under a 10 Ω load for one minute", "Supply off. Solder two 0.5 mm² wires to the two ends of <b>C77</b> (the 100 µF can on the VMOT rail; its + side is VMOT) and connect the 10 Ω 50 W resistor to them, lying on a tile. Do not load TP30: it is a 1 mm pad on one via. Raise the supply limit to <b>4.5 A</b> for this step only: 26 W out of the boost is about 3.9 A from 7.4 V. Supply on, menu <b>a</b>. After the minute, IR thermometer on L5.",
             "PASS: VMOT min and max within 16.04 ± 0.2 V over 60 s (1.6 A in the resistor). Supply current about 3.9 A. L5 below 70 °C.",
             "Voltage sags with the supply in current limit: the limit is too low (the Phase 4 plan's 3 A does not cover this step, finding F9). Sags with the supply in voltage mode: the boost's own current limit — note the supply current and send the log. L5 hot: report."),
            ("C3", "b", "Port A: contract and charger", "After PD1–PD4 below. Charger → FNB58 → port A. Menu <b>b</b>.",
             "PASS: controller mode ‘APP ’, a 15 V or 20 V contract (the FNB58 shows it), the charger BQ25792 answers through the controller; TP4 VBUS_CHG follows the contract voltage. P0 has no pack, so no charge current is expected.",
             "Mode ‘PTCH’ or ‘BOOT’: the configuration did not load — repeat PD4, then send me the log. 5 V only: same cause (an empty controller only negotiates 5 V)."),
            ("C4", "d", "Port B: 5 V and 9 V at 3 A", "Port B → FNB58 → a USB-C PD trigger board (decoy) set to 5 V, its terminals on two 3.3 Ω 50 W resistors in parallel (3.0 A). Menu <b>d</b>; hold one minute. Then the trigger at 9 V on one 3.3 Ω (2.7 A), or an electronic load at 3.0 A, one minute.",
             "5 V and 9 V each hold for a minute; FNB58 reads 3.0 A at 5 V and 2.7–3.0 A at 9 V; answer <b>y</b>.",
             "Voltage drops or the port shuts off: the TPS55288 (its compensation is the datasheet's typical design, Phase 4 risks) — photo of the FNB58 and a scope trace of VBUS_B (TP18) at switch-on."),
            ("C5", "e", "Buttons and LEDs", "Menu <b>e</b>: press each button when asked, confirm each LED.",
             "Each of the four buttons seen; red, green, blue each light.",
             "A button not seen: its joint or pull-up. An LED dark: turned the wrong way."),
            ("C6", "f", "Shutter port", "Multimeter on continuity across the 2.5 mm jack: tip–sleeve, then ring–sleeve. Menu <b>f</b>.",
             "Beep on tip–sleeve while the shutter output is on, on ring–sleeve while focus is on; answer <b>y</b> each time.",
             "No beep: the optocoupler or its LED resistor; reversed: the jack wiring."),
        ],
        "after": "Supply off; remove the C77 wires and clean the joints. Then build sheet 11 (display, harness, bezel) and sheets 12–13.",
    },
    {
        "id": "D", "title": "Stage D — P0, one axis on the bench", "when": "After build sheet 13 · rig on the tripod · supply limit 1.5 A, then 3 A for slews",
        "intro": "The encoder is on the reducer output (cartridge in place, D81): answer <b>n</b> when a test asks ‘magnet on the bare motor shaft?’. Axis 0 = azimuth on J7.",
        "steps": [
            ("D1", "", "Power up the rig", "Supply 7.4 V, limit 1.5 A. Body at the zero mark. Output on; logger connected; menu appears.",
             "30–120 mA idle, as in B2.",
             "Higher than in B2: something in the harness — off, check the harness continuity (sheet 11 check)."),
            ("D2", "g", "Encoder read-out", "Menu <b>g</b>, axis 0.",
             "PASS: 10 of 10 readings with good CRC and status 000 (no under-voltage, no weak field, no over-speed). The angle is any value; it changes in D4.",
             "CRC errors: harness pins 5–11 (SPI) and the 33 Ω on MISO; send me the log. Weak-field flag (middle digit 1): the magnet is too far or missing — stop and report (D48)."),
            ("D3", "h", "Thermistor", "Menu <b>h</b>, axis 0.",
             "PASS: azimuth 1.6–1.9 V and room temperature (5–45 °C limit). Altitude and roll read ‘open’ on P0 (no beads there) — only the tested axis counts.",
             "Open on azimuth: the bead leads (sheet 8) or harness pin 15. Short: the leads touch."),
            ("D4", "i", "Drivers answer", "Menu <b>i</b>. The rail switches to 10 V during the test.",
             "PASS: three drivers answer, version 0x21, set-up verified (all three are on the mainboard, so they answer without motors).",
             "One silent: its address straps (MS1/MS2) or the 1 k on the one-wire UART (TP40). All silent: the rail did not come up (repeat C1)."),
            ("D5", "j", "Slow steps, encoder follows", "Hands clear. Menu <b>j</b>, axis 0, answer <b>n</b>. The body turns 5° in 20 s.",
             "PASS: commanded +5.000°, encoder within 2 %, same direction. The motor holds before and after.",
             "Opposite direction: send me the log — I set DIR_INVERT for azimuth in the firmware. No motion but a hum: motor pairs swapped (harness pins 1–4, 12–15). Rough or noisy: belt tension (sheet 7)."),
            ("D6", "k", "Sidereal tracking, 10 minutes", "Menu <b>k</b>, axis 0, <b>n</b>, minutes <b>10</b>.",
             "Informational: RMS and peak-to-peak of encoder minus command printed; 600 lines of CSV saved. CRC errors under 1 %.",
             "Many CRC errors: as D2. Keep the file whatever it shows — it is the first periodic-error number."),
            ("D7", "m", "Ten slews at 8°/s", "Supply limit <b>3 A</b>. Menu <b>m</b>, axis 0, <b>n</b>. The body swings ±30° ten times at 8°/s on the 16 V rail.",
             "PASS: worst difference between encoder and steps under 0.05°, DIAG never high.",
             "Difference large: lost steps — current or belt slip; send the log. Supply in current limit: note the peak current from its display."),
            ("D8", "n", "Encoder field check", "Menu <b>n</b>, axis 0. The motor holds at 1.35 A for 2 s, then is switched off.",
             "PASS: the mean reading at full current and at zero differs by 10″ or less.",
             "More than 10″: the motor's field reaches the chip; the map can take it out (D67) — note it and go on."),
            ("D9", "o", "Encoder noise at the 0.8 mm gap (D48)", "Motor still. Menu <b>o</b>, axis 0.",
             "PASS: spread ≤ 10.8″ RMS (twice the datasheet's 0.0015°), no weak-field flag, no CRC error. The logger saves the 1000 readings.",
             "FAIL: D48 says the board goes up 0.5 mm (carriers ST-212 and ST-216). That is a part change — stop and send me the file; I propose the change first."),
            ("D10", "p", "One slow revolution (D48)", "Menu <b>p</b>, axis 0, <b>n</b>. The body first turns half a turn back, then one full turn at 1°/s (6 minutes), then back to the start.",
             "PASS: no reversal, no jump over 0.05°, no flat spot, no weak-field flag, no CRC error. The raw ‘encoder minus steps’ range is printed (expect up to about ±250″ before the map).",
             "Jumps or flat spots: magnet seating (sheet 10) or the gap; send the file. Leads pulling: stop with <b>x</b>, re-dress the loops (sheet 12)."),
            ("D11", "g h j m", "The other two channels", "Supply off. Move the harness plug from J7 to <b>J8</b>; on. Run <b>g</b>, <b>h</b>, <b>j</b>, <b>m</b> with axis <b>1</b>. Off, plug into <b>J9</b>, repeat with axis <b>2</b>. Off, back to J7.",
             "The same results as on J7 (h reads the azimuth bead on the tested channel).",
             "A channel differs: that driver or plug — report which item failed on which channel."),
        ],
        "after": "Stage D passed: the P0 measurements can start (card M). Keep the rig as it is.",
    },
]

PD_STEPS = [
    ("PD1", "Make port A's image", [
        "In Chrome open <a href=\"https://dev.ti.com/gallery/info/USBPD/USBCPD_Application_Customization_Tool/\">dev.ti.com/gallery → USBCPD Application Customization Tool</a> and start it (install the TI Cloud Agent when it asks; it is needed even just to make a file).",
        "Device: <b>TPS25751</b>. Configuration: the one with device variant <b>D</b>, power role <b>Source and Sink (DRP)</b>, <b>BQ support yes</b> (index 1 in TI's table).",
        "Answer the questions: maximum source power <b>15 W</b> (5 V 3 A, from the pack); maximum sink power <b>45 W</b> (5 V 3 A, 9 V 3 A, 15 V 3 A, 20 V 2.25 A); preferred role <b>sink</b>; charger <b>BQ25792</b>, <b>2 cells</b>, charge voltage <b>8.4 V</b>, charge current <b>4 A</b>; dead battery: <b>negotiate high voltage</b>; I²C target address <b>0x20</b>.",
        "Switch on <b>Advanced Configuration</b> → interrupt mask for the I²C target port: tick <b>PlugInsertOrRemoval, NewContract, PowerStatusUpdate, Error</b>.",
        "<b>Export</b> (top right) → <b>Generate low region binary</b> → format <b>Binary</b>, name <code>pd_port_a_low.bin</code> → Download. Also <b>Export settings</b> → <code>pd_port_a.json</code>, and send me both so they go in the repo.",
    ]),
    ("PD2", "Make port B's image", [
        "Same tool, <b>Reset Configuration</b>. Device: <b>TPS25752A</b>, the source-only configuration with an external DC/DC.",
        "Source power <b>27 W</b>: PDOs <b>5 V 3 A</b> and <b>9 V 3 A</b>; DC/DC <b>TPS55288</b> at target address <b>0x74</b> (question ‘DCDC target address’); I²C target address <b>0x21</b>; same interrupt mask as port A.",
        "<b>Export</b> → <b>Generate low region binary</b> → <code>pd_port_b_low.bin</code>; <b>Export settings</b> → <code>pd_port_b.json</code>.",
        "If a question is not covered here, take a screenshot and send it before you answer it.",
    ]),
    ("PD3", "Put both images on the board", [
        "Web flasher → <b>Connect to the head</b> → under <b>Load the USB-C PD configuration images</b> pick port A's and port B's .bin → <b>Write PD configuration</b>. The board restarts into the menu.",
    ]),
    ("PD4", "Write them into the controllers' EEPROMs (menu P)", [
        "Menu <b>P</b>; answer <b>y</b> for port A and for port B. Expect ‘written and verified’ for each (D70: FLad / FLwd / FLvy). Then switch the supply off for 5 s and on again so both controllers start from their EEPROM.",
        "This path is written from TI's manual and untested (Phase 5 section 10). If P fails or C3 still shows ‘PTCH’, send me the log; if TI's low-region file is refused, the full-flash binary from the same Export menu is the next thing to try.",
    ]),
]

MEASURE = [
    ("k", "45 min", "Periodic error T2 (three wave-generator turns)", "periodic_error.py"),
    ("o", "1 s + 10 s dump", "Encoder noise D48", "encoder_noise.py"),
    ("p", "8 min", "Encoder linearity, raw (R7)", "encoder_sweep.py"),
    ("q", "6 min", "Lost motion at reversals T1 (with the dial indicator as the check)", "lost_motion.py"),
    ("t", "4 min", "Slew current + StallGuard, warm, then after a night in the freezer", "slew_stallguard.py"),
    ("system", "—", "Encoder map, PEC, temperatures, power (system firmware + app + bench logger)", "head_results.py, power.py"),
]

GAUGE = [
    "Wave 3 brings the EV2400 and the battery board. Install TI <a href=\"https://www.ti.com/tool/BQSTUDIO\">Battery Management Studio (bqStudio)</a>; plug the EV2400 into the PC.",
    "Wake the new pack first: a 2-cell pack must see a charger on PACK+ (data sheet). Put the pack in the head and plug the 45 W charger into port A for 10 seconds, then take the pack out.",
    "EV2400 <b>SMBus</b> port to the pack's blade connector: SMBD to SMBus data, SMBC to SMBus clock, GND to power −. Nothing on PACK+.",
    "bqStudio → <b>Gauge</b> → it finds <b>bq40z50-R2</b>. Not found: wiring, or wake the pack again.",
    "<b>Commands</b> panel → <b>UNSEAL</b>, then <b>FULL ACCESS</b> (TI's default keys) so Data Memory can be written.",
    "<b>Data Memory</b> → type each name from <code>firmware/config/bq40z50-r2-p50b.csv</code> into the search box, enter its value, press Enter (it writes at once). DA Configuration: tick <b>2 cells</b> in the bit view.",
    "<b>Chemistry</b> → find <b>Molicel INR-21700-P50B</b> → <b>Program Selected Chemistry</b>. Not in the list: tell me — we log one relaxation and discharge for TI's GPCCHEM.",
    "<b>Commands</b> → <b>RESET</b>. <b>Data Memory</b> → <b>Export</b> → save the golden file (<code>.gg.csv</code>) and send it to me.",
    "LED check: press the pack button: the lit LEDs follow the charge; step the charge by charging and discharging to see positions 1–4 light in order (Phase 4: wiring as TI's module, to be confirmed).",
    "Learning cycle (as TI's guide): <b>Commands</b> → <b>Gauging</b> on; charge full; rest 2 h; discharge at 2 A (C/5) to empty; rest 5 h; charge. Then bring-up menu <b>c</b>: 5.8–8.5 V, −20…60 °C, no safety flags.",
]

TROUBLE = [
    ("Supply drops into current limit", "Output off. Something is shorted or a part is turned: feel for the warm part after power-off; compare with the step's expected current."),
    ("The logger shows nothing after Connect", "Press Enter (key button). Another program (Arduino IDE, PuTTY, the web flasher) may hold the port: close it."),
    ("‘RP2354A not answering on the link’", "Run L (or flash with the Debug Probe), then 7."),
    ("A test hangs", "Key <b>x</b> (or button 1) aborts an RP2354A test; the motor stops."),
    ("Encoder CRC errors", "Harness SPI pins and crimps; the harness must not run beside the motor leads."),
    ("Motor hums, does not turn", "Coil pairs swapped in the harness; current too low for the belt tension."),
    ("Anything not on this page", "Stop, save the session (logger → Save the whole session) and send it with a photo."),
]
