# Phase 9a — Launch work without hardware: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-9a-prompt.md` (Project `claude/phase-9a-prompt.md`). Branch `phase-9a-launch` from `phase-8-production`; draft PR against `phase-8-production`.

## State (24 Nov 2026)

- **Access:** the push attach was refused at first again; it worked once Bruno authorised it in chat.
- **Deliverable 1, name:** shortlist of 12 in `docs/09a-name-shortlist.md`; top 3 Vela, Corvo, Caravela. Waiting for Bruno's pick (Q77). Domain checks: Bruno will do them once a name is chosen.
- **Questions asked (24 Nov):** Q77 name; Q78 how far to rename the firmware ↔ app contract; Q79 website visual direction. Nothing below the name starts until Q77 is answered.
- **Deliverable 2, user guide:** not started (waits on Q77).
- **Deliverable 3, website design study:** not started (waits on Q77, Q79).

## Facts found for the guide

- OLED: SH1106 128 × 64, one 6 × 8 ASCII font, 21 × 8 characters; splash "Star Tracker" (`st_app/app.cpp`).
- Status light (`st_app/app.cpp`): day — red = fault, green blinking = tracking, blue = slewing; night — red only (fault, or blinking while tracking), dim.
