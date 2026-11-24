# Phase 6 — Apps: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-6-prompt.md`. Document: `docs/06-apps.md` (Project copy `claude/07-apps.md`; Docs version "Phase 6 — Apps", https://claude.ai/artifact/NWYSdVtWxhScLNuzifSd4j). Firmware document revision B: `docs/05-firmware.md` (Project copy `claude/06-firmware.md`).

## State (23 Nov 2026) — Phase 6 complete

- **GitHub:** PR 11 (`phase-6-apps`) and PR 10 (`phase-5-firmware` → `main`) merged; the continuation is `phase-6-continue`, PR 12. This session has push access and can merge.
- **Decisions:** D72–D77 ("Approve Q44–Q57"), D78–D79 ("Yes to Q58 and Q59") in `docs/02-decisions-log.md` and the Project copy. No open questions.
- **Workflow "Firmware and apps"** is on `main` and green: APK, Windows installer, ESP32 and RP2354A images, both simulators, `stars11.bin` (578,242 stars), all tests. Artifact downloads are blocked from the Claude workspace (blob storage host), so phone screenshots are rendered locally.

| Stage | State |
|---|---|
| 1–3 Architecture, device client, shared UI | done; 39 desktop + 13 phone screen renders |
| 4 Firmware additions | API 1.1, D78 LittleFS storage (`st_proto/filestore.cpp`, `st_app/storage.cpp`), D79 gauge values; ESP32 builds in CI |
| 5 Android | APK builds in CI; `stars11.bin` asset from the `deep-catalog` job |
| 6 Windows | installer builds and passes its smoke test in CI; ASTAP (`astap.py`, Settings card) |
| 7 Tests | node 40/40 (incl. `persist.test.mjs`), backend 36 (3 skipped on Linux), API check 47/47, firmware 29/29 and 18/18 |
| 8 Release | `star-tracker-release` artifact |

## Tests (build the simulator first; `app/package.json` test script; backend: pytest in `app/windows/backend`)

## Not tested (Phase 7)

Everything on a real head, phone and Windows PC: install, Sony camera jobs, BLE set-up, mDNS, ASTAP download and solve, deep-catalogue memory/time on a phone, LittleFS on the head, real gauge values.

## Findings (reported to Bruno)

- Code vs Phase 5 document: `state` op answered without its `id` (fixed); `time.set` never reached the head clock (fixed: `Head::on_set_time`); RP2354A stale-setpoint flag always set (unsigned age; fixed); simulator SIGPIPE crash (fixed); BLE advert lacked the service UUID (fixed); `config.get` also returns `park_az`, `park_alt`; `mode` can be `fault`; `track` without `on` turns tracking on.
- Alpaca discovery returns only the Alpaca port, hence `/startracker/v1/info` on port 80 and 32323.
- Node's WebSocket reports a failed open with `error` only; the client treats it as a lost link.
- Sim battery reaches 6.2 V at 8.3 %, so the voltage rule parks before 5 %.
- PEC: residual left to learn after the 5 Hz encoder loop is 1.2–1.4″ p-p in the simulator.
- Simulator has no load model, so `cal.balance` always reads balanced.
