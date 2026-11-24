# Phase 9a — Launch work without hardware: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-9a-prompt.md` (Project `claude/phase-9a-prompt.md`). Branch `phase-9a-launch` from `phase-8-production`; draft PR against `phase-8-production`.

## State (24 Nov 2026)

- **Access:** the push attach was refused at first again; it worked once Bruno authorised it in chat.
- **Deliverable 1, name: done.** Round 1 (Portuguese names) rejected; rounds 2–3 in `docs/09a-name-shortlist.md`. Bruno chose **Canopus** (D102).
- **Rename applied (D103):** visible names only (D100) changed to Canopus in firmware and apps — AP/BLE `Canopus-XXXX`, `canopus.local`, OLED splash, app name, Alpaca/LX200 names, `canopus-update.stfw`, `canopus-release`, folders, `Canopus-SIM`. Kept: app id, `/startracker/v1/…`, `_startracker._tcp`, comments, bring-up banner. Tests: firmware 29/29, protocol 18/18, app 40/40, backend 36.
- **Decisions:** Q77 → D102, Q78 → D100, Q79 → D101, Q80 → D103 (repo and Project decisions log). No open questions.
- **Deliverable 2, user guide:** in progress.
- **Deliverable 3, website design study:** next, look D101.

## Facts found for the guide

- OLED: SH1106 128 × 64, one 6 × 8 ASCII font, 21 × 8 characters; splash "Star Tracker" (`st_app/app.cpp`).
- Status light (`st_app/app.cpp`): day — red = fault, green blinking = tracking, blue = slewing; night — red only (fault, or blinking while tracking), dim.
