# Phase 6 — Apps: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-6-prompt.md`. Document: `docs/06-apps.md` (Project copy `claude/07-apps.md`).

## State (23 Nov 2026)

- **Branch** `phase-6-apps`, made from `phase-5-firmware` because PR 10 was not merged yet.
- **Push access** to `bmonte777/start-tracker-project` was refused by the session's permission check at the start. Work is committed locally in the workspace; push once Bruno has fixed GitHub access (Claude GitHub app → repository access).
- **Decisions** Q44–Q57 approved by Bruno on 23 Nov ("Approve Q44–Q57"): recorded as D64–D71 (already logged by the Phase 5 session) and D72–D77 in `docs/02-decisions-log.md` and the Project copy.

| Stage | State |
|---|---|
| 1 Architecture + decisions | done: `docs/06-apps.md` sections 1–4, diagrams `docs/img/06-*.svg/png` (`app/tools/diagrams.py`) |
| 2 Device client `app/shared` | done: `stclient.js`, `models.js`, `discovery.js`, `stfw.js`, `ble.js`, `node/bridge.mjs`; tests `app/tests/*.test.mjs` |
| 4 Firmware additions (API 1.1) | done in the portable code + simulator: `st_proto/services.cpp`, `wsapi.cpp`, `head.cpp` (fault log, time.set fix, on_tick); sim `/startracker/v1/info`, `/startracker/v1/op`, `/api/update`, `--raw-encoder`, `--soc`. **ESP32 side still to wire:** `/startracker/v1/info` + `/op` routes, CORS OPTIONS, NVS store hook, `update_status` hook, mDNS in the workflow, BLE advert UUID |
| 3 Shared UI `app/ui` | not started |
| 5 Android shell | not started |
| 6 Windows shell | not started |
| 7 Tests + screenshots | device-client and e2e tests pass (see below); screens not yet |
| 8 Release workflow | not started |

## Tests (run: build the simulator, then `node --test --test-concurrency=1 app/tests/`)

- `client.test.mjs` 16/16, `services.test.mjs` 9/9, `e2e.test.mjs` 7/7 (go-to + track alt-az and EQ, sync/model, raw-encoder calibration, link loss through a cut proxy, battery-low park).
- Firmware's own: `st-tests` 29/29, `proto_test.py` 18/18 still pass after the changes.

## Findings so far (tell Bruno)

- Code vs Phase 5 document: the `state` op answered without its `id` (fixed); `time.set` stored an offset nobody read, so it never reached the head clock (fixed: `Head::on_set_time` → `clock_set_unix`); `config.get` also returns `park_az`, `park_alt` (read-only); `mode` can be `fault`; `track` without `on` turns tracking on.
- Alpaca discovery returns only the Alpaca port; the WebSocket is on port 80 (8080 in the simulator), hence `/startracker/v1/info` on both ports.
- BLE advert carries the name only, not the service UUID.
- Node's WebSocket reports a failed opening with `error` only (no `close`): the client treats that as a lost link.
- Sim battery model reaches 6.2 V at 8.3 %, so the voltage rule parks before 5 %.
- PEC: with the 5 Hz encoder loop the residual left to learn is about 1–2″ p-p in the simulator (the loop already removes the reducer error above its ±2″ deadband).
