# Phase 5 firmware — progress notes

Read this first if you are a new chat continuing Phase 5. Brief: `docs/prompts/phase-5-prompt.md`. Main document: `docs/05-firmware.md` (also Project doc `claude/06-firmware.md`).

## Branch and PR
- Branch `phase-5-firmware` from `main` at 0c3ef7e (merge of PR 8). Draft PR open against `main`.

## Pending decisions (asked 23 Nov 2026, carried on with the recommendation)
Q44 toolchains · Q45 RP2354A core/PIO split · Q46 link protocol · Q47 closed loop + encoder calibration · Q48 mount models and pointing · Q49 updates and recovery · Q50 PD configuration in EEPROM · Q51 small defaults. Text in `docs/05-firmware.md` section 2. When Bruno approves, add them to `docs/02-decisions-log.md` and the Project doc `claude/02-decisions-log.md` as D62 onward.

## Stages
| Stage | State |
|---|---|
| 1 Architecture, decisions, pin header generator | done |
| 2 Bring-up firmware | done: ESP32 menu (st_sys/bringup.cpp) + RP2354A tests (rp2354a/bringup/tests.c); both build, not run on hardware |
| 3 RP2354A motion | motion core + hardware layer build; ESP32 SWD flasher written (untested) |
| 4 ESP32-S3 system | not started |
| 5 Protocols | not started |
| 6 Simulator and tests | not started |
| 7 Release (workflow, web flasher, gauge/PD config) | not started |

## Build environment notes (for the next chat)
- Pico SDK 2.3.1, arm-none-eabi-gcc 13.2 (Ubuntu package `gcc-arm-none-eabi`).
- ESP-IDF v5.5.6: `dl.espressif.com` is blocked from the build workspace; tools come from GitHub, Python env needs `idf_tools.py install-python-env --no-constraints`.
- Pins: never type them; run `firmware/common/tools/gen_board.py` (it checks the schematic model against the hand-off).
