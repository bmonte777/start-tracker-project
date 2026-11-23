# Phase 5 firmware — progress notes

Read this first if you are a new chat continuing Phase 5. Brief: `docs/prompts/phase-5-prompt.md`. Main document: `docs/05-firmware.md` (also Project doc `claude/06-firmware.md`).

## Branch and PR
- Branch `phase-5-firmware` from `main` at 0c3ef7e (merge of PR 8); `main` merged in again after PR 9 (D62–D63). PR 10 open against `main`: https://github.com/bmonte777/start-tracker-project/pull/10

## Decisions
Q44–Q51 approved by Bruno on 23 Nov 2026 ("Go with recommended") and recorded as D64–D71 in `docs/02-decisions-log.md` and the Project doc `claude/02-decisions-log.md`. Q42–Q43 (Phase 4) are D62–D63. No open questions from this phase.

## Stages
| Stage | State |
|---|---|
| 1 Architecture, decisions, pin header generator | done |
| 2 Bring-up firmware | done, builds; not run on hardware |
| 3 RP2354A motion | done, builds; motion core tested in the simulator |
| 4 ESP32-S3 system | done, builds (1.33 MB); not run on hardware |
| 5 Protocols | done: Alpaca, LX200, WebSocket, BLE; tested in-process and against the simulator (ConformU only in the workflow) |
| 6 Simulator and tests | done: 29/29 unit+integration, 18/18 protocol |
| 7 Release | done: workflow (not run yet: it must be on main to be started), web flasher, bundle, gauge CSV, check_all 40/40 |
| 8 Deliver | done: Docs doc "Phase 5 — Firmware" (https://claude.ai/artifact/A6iY9Ye6ca5gv9BDEiazDP), `docs/05-firmware.md`, Project `claude/06-firmware.md`, Phase 6 brief `docs/prompts/phase-6-prompt.md` = Project `claude/phase-6-prompt.md` |

Open work for the next phase or a follow-up (Phase 6 brief, deliverable 4, picks up cal/pec/job/mDNS): encoder calibration routine (cal.*), PEC training (pec.*), jobs (job.*), TLE tracking, mDNS, ConformU findings, port B 15 W PDO switching, magnetometer heading. See docs/05-firmware.md section 10.

## Build environment notes (for the next chat)
- Pico SDK 2.3.1, arm-none-eabi-gcc 13.2 (Ubuntu package `gcc-arm-none-eabi`).
- ESP-IDF v5.5.6: `dl.espressif.com` is blocked from the build workspace; tools come from GitHub, Python env needs `idf_tools.py install-python-env --no-constraints`.
- Pins: never type them; run `firmware/common/tools/gen_board.py` (it checks the schematic model against the hand-off).
