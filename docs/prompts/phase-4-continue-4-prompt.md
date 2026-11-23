# Star Tracker Project — Phase 4 (electronics), continuation 4

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Fable 5.2 (Opus 5.5 if Fable is not available) · **Effort:** high

---

You are the lead electronics engineer on my Star Tracker Project, carrying on Phase 4 (electronics). Earlier chats ran out of room. I do not use KiCad: nothing may be left for me to finish by hand in it.

## Context — read first
1. Repo: github.com/bmonte777/start-tracker-project, branch `phase-4-electronics`, draft pull request 6. Attach it with push access before anything else and tell me at once if that is refused.
2. Read `hardware/electronics/PROGRESS.md` first. It says where each board stands, what was changed in the router and why, the plan for the mainboard's power section, the tool chain and what comes next.
3. Project docs: `claude/05-electronics.md` (the Phase 4 document as it stands), `claude/02-decisions-log.md` (D1–D51 are fixed; Q28, Q31–Q35 and Q38–Q41 are open: carry on with the recommended option for each, marked "pending approval", unless I have answered them in this chat), `claude/phase-4-prompt.md` (the original brief: its deliverables, output format and working rules still apply).
4. Docs doc "Phase 4 — Electronics": https://claude.ai/artifact/9Y2pyZBkJu5i3eWqNy6xAx. Board viewer: https://claude.ai/artifact/TntQCR18hPMWE3V6fTQ68L. Parts list Sheet: https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8. All three still show the state of the first chat.

## Where Phase 4 stands
Done: calculations; cartridge board ST-520 (order-ready); mainboard ST-501 schematic; **battery board ST-602** (schematic, layout, fab package; ERC and DRC clean; power paths 1.0 mm or more; fit check done); harness drawings; firmware hand-off; bring-up plan; parts list CSV and cost model (state of 22 November); workflow file (pull request 7 puts it on `main`; it now also builds the battery board and checks power-path widths).

Mainboard ST-501 layout: six layers with filled and capped vias (D51), battery rail on an inner layer (D50). KiCad's check: 2 of about 950 connections open (`B_DP`, `B_CC2`, both at the port B controller U6), no errors. **But `tools/pathwidth.py` shows 11 of its 17 power paths far too thin** (the charger's coil connection is 0.10 mm wide; most others 0.25–0.35 mm where 1.0 mm is wanted). The router lays one track per connection and falls back to thin ones, and the copper areas meant to carry the current are cut up by other tracks. The board cannot be ordered until this is rebuilt.

The battery board was built the other way round and passed at the first attempt: power parts placed by hand, every power net a drawn copper area that no other net may enter (`AREAS` in `battery-board/design.py`), hand-laid tracks at the fine-pitch pins, and only the signals left to the router.

## What to do, in this order
1. **Mainboard power section**, as planned in PROGRESS.md under "What has to be done on ST-501": hand positions for the parts of the five power stages and the two USB-C supply paths (the port B sense resistor R23 next to the converter U7; the switch transistors Q2 and Q3 at least 2.2 mm from U6's pins; both pads of the charger coil within 3 mm of their pins), a drawn copper area for every net in `POWER_PATHS`, then one router run for the signals, the closing pass, and **both** checks: `tools/check.py mainboard` and `tools/pathwidth.py mainboard`. Close what is left open by router work or guided fixes in the routes file. Do not report the board as routed on the connection count alone.
2. When both checks are clean: 3D render, fab package (`tools/fab.py mainboard`), fit check (`hardware/cad`, `python -m stcad.fit_boards`), viewer.
3. Battery board: apply my answers to Q38–Q40 to the pack parts in `hardware/cad` (if I have not answered, leave the CAD alone and say so), rerun the fit check, price the board in `tools/costs.py`, and correct the parts list lines ST-602 to ST-604 (the fuse is the 2-cell ITV4030L0815NR, bought from DigiKey or Mouser; it has no LCSC number).
4. Update the parts list Sheet from `hardware/bom/master-parts-list.csv` (lines ST-501, 509, 512, 513, 517, 518, 519, 520, 530, ST-602 to 604; the mainboard is six layers), and keep the Sheet, the CSV and `bom_data.py` in step.
5. Add block and power-tree diagrams and the board renders to the Docs doc and to `docs/04-electronics.md`.
6. Run the "Phase 4 electronics build" workflow once on GitHub (it needs pull request 7 merged; tell me the clicks if you cannot start it yourself) and fix what it reports.
7. Final check: every value, pin, dimension and price against its source, including the two points the battery board section lists as not confirmed (which LEDs light in four-LED mode, in TI's reference manual SLUUBK0; TI's own fuse-drive resistor values). Update `docs/04-electronics.md`, the Project copy `claude/05-electronics.md` (send it to me as a file too), the Docs doc and the viewer. Mark pull request 6 ready.
8. When all of that is done, write the prompt for Phase 5 (firmware), with the recommended model and effort, save it to the Project as `claude/phase-5-prompt.md` and send it to me as a file.

## Rules
- Never put an LCSC number in a parts list from memory: confirm each one against JLCPCB's library (jlcsearch.tscircuit.com works) or leave it blank.
- Ask me before any design decision not covered by D1–D51; batch the questions with a recommendation each and carry on with the recommended option, marked "pending approval". If a printed or machined part must change, ask me first.
- Commit after each stage, push, and keep `hardware/electronics/PROGRESS.md` up to date so another chat can carry on.
- Tell me plainly what is not finished. Do not describe a board as ready to order unless its checks are clean (design rules **and** power-path widths) and its fab files exist.
- Explain anything I need to do with point-and-click steps, never terminal commands. Skip legal, licence and regulatory caveats.
- Any HTML page has a Day/Night toggle, and every HTML or Markdown file you publish is also sent to me as a downloadable file.
- Never copy anything from `assets/abp` in github.com/bmonte777/Benro-Polaris-Controller (ogecko's driver).

Use a task list. Start now.
