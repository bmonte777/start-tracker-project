# tools/measure — Phase 7 measurement analysis

Turns the raw files from the bench (bring-up console logs, bench-logger recordings, your own readings) into the numbers the round report judges against the spec. Procedures for recording them: `docs/measurements/procedures.md`. Raw data goes in `docs/measurements/<round>/` (one sub-folder per reducer or set-up).

| Script | Input | Gives |
|---|---|---|
| `report.py FOLDER` | everything in a round folder | runs all of the below, writes `results.md` / `results.json` per folder |
| `encoder_noise.py` | bring-up item o log | spread, white-noise check, 200-sample average (D48) |
| `encoder_sweep.py` | bring-up item p log | raw linearity, harmonics 1-8, emulated D67 map residual (R7) |
| `periodic_error.py` | item k log, head recording, or `laser_track.csv` | raw PE, turn-to-turn repeatability, PEC prediction, 5-min windows, full-step ripple (T2, T3 with `--pec`) |
| `lost_motion.py` | item q log (+ dial readings) | lost motion raw and with the encoder loop (T1) |
| `slew_stallguard.py` | item t logs, warm and cold | no-lost-step speed, StallGuard per speed, cold/warm ratio, suggested SGTHRS (T6, R2, R3) |
| `head_results.py` | cal.status / pec.get JSON, head CSV | encoder map residual, PEC table vs T2, temperatures |
| `power.py` | readings CSV or supply log + modes | W per mode vs spec 5.1, runtime (T9) |
| `laser_spot.py` | frames folder or video | spot track -> `t_s,arcsec` for periodic_error.py |
| `stlog.py` | — | parsers, maths, and every spec limit with its source |
| `make_test_data.py`, `test_measure.py` | — | synthetic files with known answers; the self-test (exit 0 = all recovered) |

Python 3.10+ with numpy, scipy (not required), matplotlib and Pillow; `laser_spot.py` uses ffmpeg for videos. Run from any folder: `python tools/measure/report.py docs/measurements/P0`.
