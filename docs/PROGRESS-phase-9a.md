# Phase 9a — Launch work without hardware: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-9a-prompt.md` (Project `claude/phase-9a-prompt.md`). Branch `phase-9a-launch` from `phase-8-production`; draft PR against `phase-8-production`.

## State (24 Nov 2026)

- **Access:** the push attach was refused at first again; it worked once Bruno authorised it in chat.
- **Deliverable 1, name: done.** Round 1 (Portuguese names) rejected; rounds 2–3 in `docs/09a-name-shortlist.md`. Bruno chose **Canopus** (D102).
- **Rename applied (D103):** visible names only (D100) changed to Canopus in firmware and apps — AP/BLE `Canopus-XXXX`, `canopus.local`, OLED splash, app name, Alpaca/LX200 names, `canopus-update.stfw`, `canopus-release`, folders, `Canopus-SIM`. Kept: app id, `/startracker/v1/…`, `_startracker._tcp`, comments, bring-up banner. Tests: firmware 29/29, protocol 18/18, app 40/40, backend 36.
- **Decisions:** Q77 → D102, Q78 → D100, Q79 → D101, Q80 → D103 (repo and Project decisions log). No open questions.
- **Deliverable 2, user guide: done.** Docs artifact "Canopus — User guide" https://claude.ai/artifact/Gj22crYNNsjG5oRintECHD = `docs/09-user-guide.md` = Project `claude/10-user-guide.md`. 19 chapters + a table of 22 pending-P1 items; three drawn diagrams (button map, connection order, polar alignment; PNG copies in `docs/img/09-*.png`), four CAD renders, six app screenshots. Checked against the source by script (85 strings and numbers, payload roll limits): all match. App screenshots re-rendered with the Canopus name (`app/tools/screenshots.mjs`, Chrome at /usr/bin/google-chrome, `npm i puppeteer-core` in /tmp/pp, `PUPPETEER_DIR=/tmp/pp`): 78/78.
- **Finding (fixed):** the Camera screen said the Windows shot log is in Pictures\Canopus; the code writes Documents\Canopus. Screen text corrected.
- **Deliverable 3, website design study: done.** Design canvas "Canopus — Website design study" https://claude.ai/artifact/1HEVoUPqnL5tCx2WZk1vGN (slug 024437c6-e735-419e-803a-db5925f6f25f): three artboards — landing (hero render, what it does, three axes and both modes, five payload types, key specs, open and repairable per D13, Polaris comparison with sources, demo interest form), specs (seven grouped tables, calculated/target tags), support (user guide link, five-step first night, downloads, updates, repair, FAQ, contact placeholder). Day/Night on every page; Night is #FF3B30 on black and the renders are filtered red-on-black. Standalone offline copies in `docs/website/` (`index.html`, `specs.html`, `support.html`, `img/`), canvas sources in `docs/website/design-canvas/`, generator `docs/website/tools/render_dc.mjs`. No price, no other brand's logo or photo. Every figure checked against the user guide's specification table; unsourced wording found while checking was removed (zero backlash → almost no play; port B carries power only; Sony USB-C goes to the phone/PC; no "signed" bundle; no diagnostics file).
- **Design systems in Bruno's account** (Spanlume, SextantTours, Lustra, LucidField…) belong to other brands, so none was used; D101 sets the look.
- **Next prompt:** nothing has been ordered or measured, so the next prompt goes back to Phase 8 with the on-hold branch first: `docs/prompts/phase-8-continue-2-prompt.md` (Project `claude/phase-8-continue-2-prompt.md`). Opus 5.5, high.
- **Phase 9a is finished.** PR 15 stays a draft until Bruno merges it (the next prompt merges it into `phase-8-production`).

## Facts found for the guide

- OLED: SH1106 128 × 64, one 6 × 8 ASCII font, 21 × 8 characters; splash "Canopus" since D103 (`st_app/app.cpp`).
- Status light (`st_app/app.cpp`): day — red = fault, green blinking = tracking, blue = slewing; night — red only (fault, or blinking while tracking), dim.
