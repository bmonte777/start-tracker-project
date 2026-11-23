# Phase 6 — Apps: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-6-prompt.md`. Document: `docs/06-apps.md` (Project copy `claude/07-apps.md`; Docs version "Phase 6 — Apps", https://claude.ai/artifact/NWYSdVtWxhScLNuzifSd4j). Firmware document revision B: `docs/05-firmware.md` (Project copy `claude/06-firmware.md`).

## State (23 Nov 2026)

- **Branch** `phase-6-apps`, made from `phase-5-firmware` because PR 10 was not merged yet.
- **Push access** to `bmonte777/start-tracker-project` was refused by the session's permission check at the start. Everything is committed locally in the workspace; push and open the pull request once Bruno has fixed GitHub access (github.com → Settings → Applications → Installed GitHub Apps → Claude → Configure → Repository access).
- **Decisions** Q44–Q57 approved on 23 Nov ("Approve Q44–Q57"): D64–D71 (logged by the Phase 5 session) and D72–D77 in `docs/02-decisions-log.md` and the Project copy. New open questions Q58 (fault log, PEC tables, encoder maps in the `storage` partition) and Q59 (gauge values in `health.get`), both recommended yes.

| Stage | State |
|---|---|
| 1 Architecture + decisions | done: `docs/06-apps.md` sections 2–4, diagrams `docs/img/06-*.svg/png` (`app/tools/diagrams.py`) |
| 2 Device client `app/shared` | done: `stclient.js`, `models.js`, `discovery.js`, `stfw.js`, `ble.js`, `native.js`, `catalog.js`, `jobs.js`, `polar.js`, `node/bridge.mjs` |
| 3 Shared UI `app/ui` | done: 13 screens (`screens/*.js`), Blue Hour Day/Night/Red, 39 screenshots in `docs/img/06-screens/` |
| 4 Firmware additions (API 1.1) | portable code + simulator done and tested; ESP32-only (routes, CORS, NVS store, `update.status`, mDNS, BLE UUID) written, **not compiled here** |
| 5 Android shell `app/android` | written (`MainActivity`, `StNative`, `HeadClient`, reused `camera/`), javac parse-check only; **first compile in the workflow** |
| 6 Windows shell `app/windows` | written; backend runs on Linux and 33/33 pytest pass; WPD camera (`ptpwpd`), PyInstaller and Tauri build only on Windows (workflow) |
| 7 Tests | all below pass |
| 8 Release workflow | `.github/workflows/firmware.yml` renamed "Firmware and apps": jobs `app-tests`, `android-app`, `windows-app`, `release` (artifact `star-tracker-release`). **Never run yet** |

## Tests (build the simulator first; `app/package.json` test script)

- Node against the simulator: `client` 16/16, `services` 9/9, `e2e` 7/7, `polar` 3/3, `jobs` 4/4 = 38/38.
- Screens: 39/39 (`app/tools/screenshots.mjs`, desktop size; phone size in the workflow).
- Windows backend pytest 33/33. API check against firmware source 47/47 (`app/api-check.md`).
- Firmware's own: `st-tests` 29/29, `proto_test.py` 18/18 still pass.

## Still to do (Phase 6 continuation)

1. Push `phase-6-apps`, open the PR, run the workflow once and fix compile errors in Android, Windows (ptpwpd, PyInstaller, Tauri) and ESP32.
2. D74: ASTAP download button and solver path on Windows; Tycho-2-based deeper catalogue for the Android solver (300–600 mm).
3. Check the phone-size screenshots from the workflow and fix layout.
4. Then write the Phase 7 prompt.

## Findings (reported to Bruno)

- Code vs Phase 5 document: `state` op answered without its `id` (fixed); `time.set` never reached the head clock (fixed: `Head::on_set_time`); RP2354A stale-setpoint flag always set (unsigned age; fixed); simulator SIGPIPE crash (fixed); BLE advert lacked the service UUID (fixed); `config.get` also returns `park_az`, `park_alt`; `mode` can be `fault`; `track` without `on` turns tracking on.
- Alpaca discovery returns only the Alpaca port, hence `/startracker/v1/info` on port 80 and 32323.
- Node's WebSocket reports a failed open with `error` only; the client treats it as a lost link.
- Sim battery reaches 6.2 V at 8.3 %, so the voltage rule parks before 5 %.
- PEC: residual left to learn after the 5 Hz encoder loop is 1.2–1.4″ p-p in the simulator.
- Simulator has no load model, so `cal.balance` always reads balanced.
