# Star Tracker Project — Phase 6: Apps for Android and Windows

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Fable 5.2 (Opus 5.5 if Fable is not available) · **Effort:** high

---

You are the lead app engineer on my Star Tracker Project. It is an open-source, user-repairable 3-axis motorised astro head (Polaris / Asterra class), built first as a 3D-printed prototype and later mass-produced. Phases 1–5 are finished: the mechanics are fixed in the CAD, the three boards (ST-501, ST-520 ×3, ST-602) are designed, and the firmware for both processors is written and tested on a simulator. No board has been built yet, so this phase builds the apps against the head's WebSocket API and proves them against the simulator, which runs the real firmware logic and the real servers.

## Context — read first
1. Project docs:
   - `claude/02-decisions-log.md`: approved decisions. Treat them as fixed. D11 (protocols), D12 (apps from scratch, my Benro-Polaris-Controller code may be reused, Android + Windows) and D14 (repo) matter most. Check which of Q44–Q51 (Phase 5) I have approved; ask me about any still pending only if it changes the apps.
   - `claude/06-firmware.md`: the Phase 5 document. Section 6.1 (WebSocket JSON API v1) is the contract the apps talk to. Section 7 (simulator), section 8 (loading and updating: the apps should be able to upload a `.stfw` bundle) and section 10 (what is not finished: `pec.*`, `job.*`, `cal.*` answer `notimpl`, no mDNS yet) are essential.
   - `claude/03-engineering-spec.md`: the Phase 2 spec, revision C. Section 7.5 (app architecture: one shared web UI in my Blue Hour design with Day, Night and Red modes inside a thin native shell; reused modules; new device client; new screens) and the error budget.
   - `claude/04-mechanical-design.md`: the five payload envelopes (D40), the wedge (D39), axis limits.
   - `claude/05-electronics.md`: battery, both USB-C ports (port B is the 27 W camera port), status the head reports.
2. Repo: github.com/bmonte777/start-tracker-project (D14: the apps live here, not in variousapps). Attach it with push access before anything else and tell me at once if that is refused. Work on a new branch, `phase-6-apps`, from `main` after pull request 10 (Phase 5 firmware) is merged; if it is not merged yet, branch from `phase-5-firmware` and say so. Put the apps in `app/` (`app/ui`, `app/shared`, `app/android`, `app/windows`, spec 7.6). Use:
   - `firmware/sim/`: the simulator (`StarTrackerSim.exe` from the Firmware workflow, or built in your workspace) to test every screen;
   - `firmware/esp32s3/components/st_proto/wsapi.cpp` and `firmware/tests/proto/proto_test.py`: the API as implemented;
   - `firmware/common/web/index.html`: the head's own small page (a reference for the API, not the app's design).
3. My app github.com/bmonte777/Benro-Polaris-Controller: its UI and its camera, plate-solver, Holy Grail, astro sequence, star trails, HDR, focus stack, panorama, Night planner, Blue Hour, gallery and shot-log code may be reused (D12). Read it first, find out which technology its native shells use, and reuse that unless there is a strong reason not to (ask me). Never copy anything in `assets/abp` (ogecko's driver) and do not reuse its Polaris BLE protocol: the device client is new.

## Goal of this phase
An Android app and a Windows app, sharing one UI, that find the head, show its state live, and drive everything the head can do: go-to and tracking in alt-az and on the wedge, the roll axis as field rotator and framing axis, alignment and plate-solve sync, the camera (Sony over USB-C, and the head's shutter port with its intervalometer), the imaging jobs (Holy Grail, time-lapse, panorama, astro sequence), the payload envelopes, battery and power, settings, and firmware updates for the head.

## Decisions to ask me first (batch them with a recommendation each, then carry on with the recommended option marked "pending approval")
- Native shell technology on each platform (whatever Benro-Polaris-Controller uses, or an alternative such as Capacitor / Tauri / WebView2 / .NET MAUI), and how the shared web UI is packaged.
- Where each job runs: on the head (firmware `job.*`, keeps running if the phone sleeps or loses Wi-Fi) or in the app (camera-driven jobs that need live view and USB). My expectation is head-side motion with app-side camera control, but recommend.
- Plate solving: which solver on each platform (the one my app already uses, ASTAP, a local astrometry.net index, online), index sizes, and offline use in the field.
- Head discovery and connection: Alpaca discovery (UDP 32227), mDNS once the firmware has it, the head's own access point (192.168.4.1), BLE for Wi-Fi set-up; what happens when the connection drops mid-job.
- The API additions the new screens need (`pec.*`, `job.*`, `cal.*`, health and fault-log reads), designed together with the firmware side.
- Anything not covered by the decisions log.

## Deliverables
1. **App architecture first:** a short design document (layers, the device client, state handling, which modules come from Benro-Polaris-Controller and what changes in them, offline behaviour, how the camera and the head are coordinated) with diagrams, before most code is written.
2. **Device client** (`app/shared`): WebSocket API v1 client with request/response by `id`, state-event stream, reconnect and resume, typed models for every op and state field in section 6.1 of the firmware document; discovery; BLE Wi-Fi set-up (service `5354524b-0100-4d2a-9b1e-000000000001`, passkey shown on the head's OLED); `.stfw` update upload with progress. Unit-tested against the simulator.
3. **Shared UI** (`app/ui`) in my Blue Hour design with Day, Night and Red modes (Red = the night mode of D7: red only, dim):
   - Connect / first set-up (find the head, join its network, give it my Wi-Fi over BLE, set location and time when there is no GNSS fix);
   - Dashboard (sky position, the three axes with encoder and commanded angles, tracking state, battery, motor rail, faults);
   - Sky: a target catalogue (stars, Messier/NGC, planets, Sun, Moon), go-to, tracking rates, jog pad, guide pulses, park/unpark;
   - Alignment wizard (sync points, plate-solve sync, pointing-model terms and RMS) and polar-alignment help for the wedge;
   - Rig: the five payload envelopes with their roll limits, balance check, wedge / pier settings;
   - Roll: field de-rotation and framing by position angle;
   - Camera and jobs: Sony USB-C control with live view, the shutter port intervalometer, Holy Grail, time-lapse, panorama, astro sequence, star trails, HDR, focus stack, Night planner, gallery and shot log;
   - New screens of spec 7.5: PEC trainer, encoder and battery health, firmware update;
   - Settings (everything in `config.get` / `config.set`).
4. **Firmware additions the apps need**, in `firmware/` on the same branch, tested on the simulator: the `pec.*`, `job.*` and `cal.*` operations (PEC training and storage, head-side motion jobs, the encoder calibration routine of Q47), a fault-log read, and mDNS in the workflow build. Keep `docs/05-firmware.md` section 6.1 and section 10 up to date (and the Project copy `claude/06-firmware.md`).
5. **Android app** (`app/android`): installable APK, USB-C camera access, works with the phone's screen off during a job where the platform allows.
6. **Windows app** (`app/windows`): installer, USB camera access.
7. **Tests:** device-client unit tests; end-to-end runs of every screen against the simulator (go-to and track in alt-az and EQ, alignment with simulated plate-solve results, a Holy Grail run at simulator speed-up, battery-low park, link loss, firmware upload); screenshots in Day, Night and Red of every screen. Report the results.
8. **Build and release:** extend the GitHub Actions workflow (started by hand) to build the APK and the Windows installer and attach them to the run, together with the firmware images and the simulator. Explain installing both apps with point-and-click steps.

## Output format
- One Docs doc, "Phase 6 — Apps": architecture, diagrams, the API additions, screens (with screenshots), test results, how to install, open questions.
- The same content as Markdown in `docs/06-apps.md`. Save it to the Project as `claude/07-apps.md` and send it to me as a downloadable file.
- Copy this brief to `docs/prompts/phase-6-prompt.md` in your first commit (it is already there if Phase 5 committed it: then leave it).
- Update `claude/02-decisions-log.md` (Project and repo) with every new decision I approve, and with Q44–Q51 if I approve them during this phase.
- When the phase is complete, write the prompt for Phase 7 (building and measuring the prototype), with the recommended model and effort, save it to the Project as `claude/phase-7-prompt.md` and send it to me as a file.

## Working rules
- Work in stages: architecture and decisions, device client, shared UI, firmware additions, Android shell, Windows shell, tests, release.
  - Commit after each stage, push, and keep a pull request open.
  - Keep `app/PROGRESS.md` up to date, so a new chat can carry on if this one runs out of room.
- The WebSocket API in the firmware is the contract; where the firmware document and the code disagree, the code wins and you tell me. Any change to the API is made on both sides and documented.
- Research current library and SDK versions, the Sony camera protocol my app uses, and the plate solver's interface on the web, and cite sources.
- **Ask me before any design decision not covered by the decisions log.** Batch the questions with your recommendation for each, then carry on with the recommended option marked "pending approval", so the work doesn't stall. If a board, printed or machined part would have to change, ask me first.
- Tell me plainly what is not finished or not tested. Nothing has run on a real head yet: say what was tested against the simulator and how, and do not describe a feature as working on the head.
- Explain anything I need to do with point-and-click steps, never terminal commands.
- Skip legal, licence, store-policy and regulatory caveats.
- Every screen and every HTML page has a Day/Night toggle (plus Red in the app), and every HTML or Markdown file you publish is also sent to me as a downloadable file.
- Use a task list, and finish by checking every API op, field name, unit and limit the apps use against the firmware source.

Out of scope for this phase: building and measuring the prototype (Phase 7) and production versions of the boards (Phase 8). The product website is not part of this phase.

Start now.
