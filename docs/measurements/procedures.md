# P0 measurement procedures

Star Tracker Project · Phase 7, round P0 · 24 Nov 2026 · deliverable 5 of the brief

Each procedure says what you set up, what you record, where the file goes, which script turns it into a number, and the spec target it is judged against. You do the physical part; I run the scripts on the files you send (or that you copy into `docs/measurements/P0/A/` for reducer A, `P0/B/` for reducer B). `python tools/measure/report.py docs/measurements/P0` writes `results.md` for the round report. Every limit and its source is in `tools/measure/stlog.py`.

**Before any of these:** Stage D of the bring-up companion has passed, the rig stands on its tripod (build sheet 12) with the body at the zero mark, and the bench logger is recording with the label `P0-A`. The bring-up items **k** (with its duration question), **o** and **p** (raw logs), **q** and **t** need an image built from `phase-7-prototype` after 24 November.

**Nothing below has been run on hardware.** The scripts are tested on synthetic files with known answers (`tools/measure/test_measure.py`: 8 of 8 recovered).

| # | What | Menu / tool | Time | Script | Judged against |
|---|---|---|---|---|---|
| M1 | Encoder noise at the 0.8 mm gap (D48) | bring-up **o** | 1 min | `encoder_noise.py` | ≤ 10.8″ RMS, no weak-field flag, no CRC error (Phase 5 §4) |
| M2 | Encoder linearity, raw (D48, R7) | bring-up **p** | 8 min | `encoder_sweep.py` | no jump / reversal / flat spot; ≤ ±0.07° raw (spec 4.5) |
| M3 | Reducer periodic error (R1, T2) | bring-up **k**, 45 min; laser as check | 50 min | `periodic_error.py`, `laser_spot.py` | ≤ ±20″, repeatable ≤ 3″ turn to turn (T2) |
| M4 | Backlash and lost motion (T1) | bring-up **q** + dial indicator | 10 min | `lost_motion.py` | raw ≤ 20″ (az, alt), ≤ 30″ (roll); with the loop ≤ 10″ (spec 1.2, T1) |
| M5 | Encoder calibration map (D67) | system firmware, app **Health → Start calibration** | 15 min | `head_results.py --cal` | map's own residual ≤ 10″ RMS (go-to budget, spec 4.5) |
| M6 | PEC training and result (T3) | app **PEC → Record**, then tracking 45 min with PEC playing | 2 h | `head_results.py --pec`, `periodic_error.py --pec` | ≤ 2″ RMS left (T3) |
| M7 | Slew current and StallGuard, warm and cold (R2, R3, T6 part) | bring-up **t**, room and freezer | 2 × 10 min + a night | `slew_stallguard.py` | no lost step to 8°/s warm, 6°/s at −20 °C (spec 1.2, D26); SGTHRS suggestion |
| M8 | Motor and driver temperatures (T10 on the bench) | from M3, M6, M7 logs + IR thermometer | — | `head_results.py --head`, `slew_stallguard.py` | motor ≤ 80 °C (Phase 4 10.7) |
| M9 | Power per mode (T9) | bench supply readings | 30 min | `power.py` | within 20 % of the spec 5.1 formulas (T9) |

P0 has no camera, no pack and one axis, so these wait for P1 and get their procedures with the P1 build guide: camera port B under load, tracking from real frames (T4), pointing-model RMS (T5), balance against a real load, stiffness and settling (T7, T11), runtime on the pack (T9 full discharge).

---

## M1 · Encoder noise at the 0.8 mm gap (D48)

**Set up.** Rig standing still, motor holding (the test does not move it). Nobody touching the tripod.

**Record.** Bring-up menu **o**, axis 0. The test takes 1,000 readings 1 ms apart, then prints them (about 10 s) and the verdict. The logger saves `P0-A_o_az_<time>.txt`. Run it three times: motor holding, motor holding after a 10-minute track (warm), and again after **M7** (hot).

**Result.** `encoder_noise.py` gives the spread (RMS and peak-to-peak), a histogram, how white the noise is, and what the motion core's 200-reading average leaves (the spec allows 0.3″ for encoder loop noise, 4.1).

**Judged.** ≤ 10.8″ RMS (twice the datasheet's 0.0015° at the bandwidth setting used), no weak-field flag, no CRC error. **If it fails:** D48 says the board goes up 0.5 mm (carriers ST-212, ST-216). That is a part change: I propose it to you first.

## M2 · Encoder linearity, raw (D48 part 2, R7)

**Set up.** As M1. The body turns half a turn back, one full turn at 1°/s, then back: the leads must have their ±180° loops (sheet 12).

**Record.** Menu **p**, axis 0, answer **n**. About 8 minutes. File `P0-A_p_az_<time>.txt` (a line every 100 ms: angle commanded, encoder angle, the difference).

**Result.** `encoder_sweep.py`: the raw encoder-minus-steps curve over the turn, its harmonics 1–8 (the magnet and mounting errors the map removes), what a D67 map would leave, and the reducer's own error seen in the sweep.

**Judged.** No reversal, jump over 0.05° or flat spot (the firmware's own counts); raw p-p within ±0.07° (504″ p-p). More means the magnet is off-centre (R7): check its seating in the tube (sheet 10) before anything else.

## M3 · Reducer periodic error (R1, test T2)

**Set up.** Body at the zero mark. No draughts, nobody walking near the tripod. For the independent check (recommended once per reducer): the laser module stuck to ST-303's top face pointing at a wall 3–10 m away, and a camera on its own tripod framing the spot's 11° path (at 5 m about 1 m of wall), shooting one frame per second (the A7R V's interval shooting, 2,700 frames) or filming.

**Record.** Menu **k**, axis 0, **n**, minutes **45** — three turns of the wave generator (861.6 s each, spec 4.4). Each line is the mean of 1,000 encoder readings over one second. File `P0-A_k_az_<time>.txt`. Note the room temperature. Repeat once for repeatability on another day; after sheet R the same for reducer B (D82).

**Result.** `periodic_error.py`: removes the slow trend (the unmapped encoder over 11° of output), fits harmonics 1–12 of the wave-generator turn, and gives the raw periodic error, the turn-to-turn difference, what a perfect PEC trained on this log would leave, the worst 5-minute window (the spec's tracking metric, drift kept), and the full-step ripple from the spectrum. For the laser frames: `laser_spot.py FRAMES_DIR --red` writes `laser_track.csv`, then `periodic_error.py laser_track.csv` gives the same numbers from an independent sensor.

**Judged.** ≤ ±20″ raw and repeatable within 3″ (T2). Spec 4.3: a reducer at its 1.5′ catalogue limit misses the 3″ target even with PEC, so **the better of A and B goes on azimuth** (D82).

## M4 · Backlash and lost motion at reversals (T1)

**Set up.** Dial indicator (0.001 mm) on its magnetic base on a steel plate on the bench, its tip on a 200 mm arm screwed to ST-303's top face, the arm square to the tip (T1: 1 µm = 1.03″ at 200 mm). The base must not stand on the tripod. Zero the dial.

**Record.** Menu **q**, axis 0, **n**, step **60**″. Runs of five moves forward, five back, three cycles; at each stop the axis settles and is averaged for a second, then waits — read the dial during each stop and write it down (or film the dial with the phone and read it afterwards). Pass 0 has the encoder correction off (raw), pass 1 on (D67). File `P0-A_q_az_<time>.txt`, plus your readings as `P0-A_dial.csv` with the header `pass,n,dial_um` (n is the stop number the log prints, 0–29).

**Result.** `lost_motion.py P0-A_q_az.txt --dial P0-A_dial.csv --arm-mm 200`: lost motion from the encoder (both passes) and from the dial (pass 0), per cycle.

**Judged.** Raw ≤ 20″ on azimuth and altitude, ≤ 30″ on roll; with the encoder loop ≤ 10″ (spec 1.2, T1). If the dial and the encoder disagree by more than 3″, the encoder reading is the doubtful one (it is unmapped): I compare after M5.

## M5 · Encoder calibration map (D67, `cal.encoder`)

**Set up.** System firmware loaded (web flasher → `st-esp32s3-system-full.bin`; it writes the RP2354A motion image itself). App on the PC (Phase 6 install), connected to the head's Wi-Fi. Bench logger part 2 connected to the head as well. Tracking off.

**Record.** App → **Health** → axis azimuth → **Start calibration**. The axis turns half a turn back, sweeps one full turn and stops half a turn from where it began (about 15 minutes at 0.5°/s; the sweep is centred so the leads stay within their loops). When the app shows the result: logger → **Save cal.status** (file `P0-A_cal-status_az_<time>.json`), then **Apply the map** in the app. Turn the body back to the zero mark with the app's jog.

**Result.** `head_results.py --cal P0-A_cal.json --pe <M3's periodic_error.json>`: raw p-p, and the map's own residual (the routine's `after_rms` minus the reducer error, which the map leaves on purpose).

**Judged.** Raw within ±0.07°; the map's own residual ≤ 10″ RMS (gear-error map term of the go-to budget, spec 4.5). After sheet R the map is made again: it belongs to the reducer and tube as assembled.

## M6 · PEC training and the result (T3)

**Set up.** As M5, map applied. Leads at the zero mark (tracking turns the body 11° in 45 min).

**Record.** 1. App → **Sky** → **Track** (sidereal). 2. App → **PEC** → axis azimuth, cycles **3** → **Record** (about 45 min). 3. When ready: **Save** and **Play**; logger → **Save pec.get** and **Save pec.status**. 4. Logger → **Start recording**; let it track with PEC playing for 45 minutes; **Save recording** — name it with `pec` in it (`P0-A_head_pec_<time>.csv`).

**Result.** `head_results.py --pec P0-A_pec-get_az.json --pe <M3>` compares the learned table with M3. `periodic_error.py P0-A_head_pec.csv --pec` gives what is left with PEC playing (the head's state events carry one encoder sample each; the script averages them in 20 s bins and takes the noise floor out).

**Judged.** ≤ 2″ RMS left (T3). The learned table should match M3's curve within ±20 %.

## M7 · Slew current and StallGuard margins, warm and cold (R2, R3, T6 part)

**Set up, warm.** Rig at room temperature (note it), supply limit 3 A, hands clear: the body swings ±60°.

**Record, warm.** Menu **t**, axis 0, current **830** mA (the 20 °C slew current, Phase 5 §5). Slews out and back at 2, 4, 6 and 8°/s with a line every 100 ms (speed, encoder minus steps, StallGuard value, current setting, rail, motor temperature). File `P0-A_t_az_warm_<time>.txt` (rename the logger's file or set the label to `P0-A-warm`). Note the supply's peak current at 8°/s from its display.

**Set up, cold.** The rig on its small board with the 3/8" bolt (sheet 12) in a freezer at about −20 °C for at least 6 hours, the two leads through the door seal. Supply and PC outside.

**Record, cold.** Without opening the freezer: menu **h** (motor temperature should read about −18 to −20 °C), then menu **t**, axis 0, current **1260** mA (the −20 °C value). File `P0-A_t_az_cold_<time>.txt`. Then once more at **830** mA to see the margin without the cold current.

**Result.** `slew_stallguard.py warm.txt cold.txt`: per speed the lowest and mean StallGuard value while cruising, lost steps, the cold-to-warm ratio (how much the grease drags, R2), and a suggested SGTHRS (stall trips at half the lowest cruising value).

**Judged.** No lost step up to 8°/s warm and up to 6°/s cold at the cold current (spec 1.2, D26). D42 keeps 8°/s down to −20 °C with the 16 V rail: if the cold run reaches 8°/s, D42 holds on the bench. StallGuard has no spec figure: the suggested SGTHRS goes into the firmware defaults after P1 confirms it (a firmware change, made and pushed directly).

## M8 · Motor and driver temperatures (T10, bench part)

**Set up.** Nothing new: the motor thermistor is in every **k** and **t** log and in every head recording.

**Record.** After M7 warm, and after 45 minutes of tracking (M3 or M6): IR thermometer on the motor can, on L5 and on the azimuth driver (U15) — write the readings into a note `P0-A_temps.txt`, or photograph the display of the thermometer on each part.

**Result.** `slew_stallguard.py` and `head_results.py --head` report the thermistor maximum and its rise; your IR readings go beside them in the round report.

**Judged.** Motor ≤ 80 °C (the current derate threshold, Phase 4 10.7); spec 5.3 predicts +48 K above the inside air for the azimuth motor at 1.20 A held for a minute, and a few kelvin at tracking currents.

## M9 · Power per mode (T9)

**Set up.** Bench supply at 7.4 V. If the RD6006's PC software is installed, start its recording (export CSV); otherwise read the display.

**Record.** About 3 minutes in each mode, then read the supply's current (the steady value, or the middle of its swing): **idle** (bring-up menu, rail off), **hold** (system firmware, axis holding), **track** (system firmware, sidereal tracking), **slew** (during a long slew at 8°/s). Write `P0-A_power.csv`:

```
mode,volts,amps,note
idle,7.40,0.140,bring-up menu
hold,7.40,0.185,system firmware
track,7.40,0.200,sidereal
slew,7.40,0.620,8 deg/s
```

(the numbers above are an example, not a measurement). With a recording, send the export and a `modes.csv` (`mode,start_s,end_s`) instead.

**Result.** `power.py P0-A_power.csv`: watts per mode against the spec 5.1 formulas for one azimuth axis (logic 0.90 W ÷ 0.90, motor 2 I²R + 0.1 W ÷ 0.90 with 1.4 Ω), and the runtime each would give on the 62.9 Wh pack.

**Judged.** Within 20 % (T9) for idle, hold and track; slewing is information only (mechanical power comes on top of the copper loss).

---

## File names and where they go

| File | From | Put in |
|---|---|---|
| `P0-A_<item>_<axis>_<time>.txt` | bench logger, part 1 (one per test) | `docs/measurements/P0/A/` |
| `P0-A_head_<time>.csv`, `…_head_pec_…csv` | bench logger, part 2 | same |
| `P0-A_cal-status_az_….json`, `P0-A_pec-get_az_….json` | bench logger, part 2 buttons | same |
| `P0-A_dial.csv`, `P0-A_power.csv`, `P0-A_temps.txt` | written by you | same |
| photos (scope, dial, IR thermometer, FNB58) | phone | same, any name |
| laser frames | camera | keep them on your PC; send a zip of the frames or the video, or run `laser_spot.py` from me |

Reducer B: the same with `P0-B` into `docs/measurements/P0/B/`.
