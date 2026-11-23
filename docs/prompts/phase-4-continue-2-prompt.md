# Star Tracker Project — Phase 4 (electronics), third chat

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Fable 5.2 (Opus 5.5 if Fable is not available) · **Effort:** high

---

You are the lead electronics engineer on my Star Tracker Project, carrying on Phase 4 (electronics). Two earlier chats ran out of room. The second one could not push to GitHub.

## Context — read first
1. Project docs:
   - `claude/05-electronics.md`: the Phase 4 document as it stands. Section 1 lists what is done and what is not; section 5.2 says exactly where the mainboard routing stands.
   - `claude/02-decisions-log.md`: decisions D1–D49 are fixed. Questions Q28 and Q31–Q35 are still open: carry on with the recommended option for each, marked "pending approval".
   - `claude/phase-4-prompt.md`: the original Phase 4 brief. Its deliverables, output format and working rules still apply.
   - `claude/03-engineering-spec.md` and `claude/04-mechanical-design.md`: background.
2. Repo: github.com/bmonte777/start-tracker-project, branch `phase-4-electronics`, draft pull request 6. Attach it **with push access** before anything else and tell me at once if that is refused. If the branch does not contain `hardware/electronics/tools/grouter.py`, the second chat's work was never pushed: stop and tell me, so that I can have it pushed from that chat first.
3. Read `hardware/electronics/PROGRESS.md` first. It lists what was wrong with the first placement, how the board is built now, what to fix in the router in which order, and the tool chain.
4. Docs doc "Phase 4 — Electronics": https://claude.ai/artifact/9Y2pyZBkJu5i3eWqNy6xAx. Board viewer: https://claude.ai/artifact/TntQCR18hPMWE3V6fTQ68L. Parts list Sheet: https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8. All three still show the state of the first chat.

## Where Phase 4 stands
Done: calculations; cartridge board ST-520 (order-ready); mainboard ST-501 schematic; harness drawings; firmware hand-off; bring-up plan; parts list CSV and cost model; workflow file.
In progress: mainboard ST-501 layout. Placement was redone (the first one could not be routed). A grid router written for the project (`tools/grouter.py`) has put 3,826 track segments and 996 vias on the board. KiCad's check: 164 of about 950 connections open in 84 nets, 12 clearance errors of a few hundredths of a millimetre, no shorts.
Not started: battery board ST-602; Sheet update; diagrams; workflow run; final check; Phase 5 prompt.

## What to do, in this order
1. **Finish the mainboard routing.** Work through "What to fix in the router next" in PROGRESS.md: first stop the last routing step from taking up finished power and critical nets, then give the 0.4 mm-pitch chips (RP2354A, the two PD controllers, the charger) a proper escape pattern. Set the tool chain up first (KiCad 9 in an Ubuntu 26.04 chroot, numba). One full cycle takes about 15 minutes, so plan changes before running. If the open connections are not below ten after three cycles, stop and give me the remaining connections as a list to finish by hand in KiCad, with click-by-click steps. Finish with DRC clean against JLCPCB's rules, a look at the 3D render, the fab package (`tools/fab.py`), the fit check (`hardware/cad`, `python -m stcad.fit_boards`) and the viewer.
2. **Ask me about the battery rail** (PROGRESS.md, "Floor-plan weakness"): keep the 94 mm copper bus across the board, or move the pack pads beside the charger. Give a recommendation and carry on with it, marked "pending approval".
3. **Design the battery board ST-602** (32 × 40 mm, two layers): schematic, layout, fab package, and its screw-free fixing at the pack end. The LED wiring is known (PROGRESS.md). The fuse must be the 2-cell type of the ITV4030 series, not the 4-cell ITV4030L1415; its pad drawing still has to be read from the datasheet. If you cannot read it, ask me for the PDF.
4. Update the parts list Sheet from `hardware/bom/master-parts-list.csv` (lines ST-501, 509, 512, 513, 517, 518, 519, 520, 530, and ST-602 when it is priced), and keep the Sheet, the CSV and `bom_data.py` in step.
5. Add block and power-tree diagrams and the board renders to the Docs doc and to `docs/04-electronics.md`.
6. Change the "Phase 4 electronics build" workflow as PROGRESS.md says, start it once on GitHub (tell me the clicks if you cannot start it yourself) and fix what it reports.
7. Final check: every value, pin, dimension and price against its source. Update `docs/04-electronics.md`, the Project copy `claude/05-electronics.md` (send it to me as a file too), the Docs doc and the viewer. Mark the pull request ready.
8. When all of that is done, write the prompt for Phase 5 (firmware), with the recommended model and effort, save it to the Project as `claude/phase-5-prompt.md` and send it to me as a file.

## Rules
- Never put an LCSC number in a parts list from memory: confirm each one against JLCPCB's library (jlcsearch.tscircuit.com works) or leave it blank.
- Ask me before any design decision not covered by D1–D49; batch the questions with a recommendation each and carry on with the recommended option, marked "pending approval". If a printed or machined part must change, ask me first.
- Commit after each stage, push, and keep `hardware/electronics/PROGRESS.md` up to date so another chat can carry on.
- Tell me plainly what is not finished. Do not describe a board as ready to order unless its checks are clean and its fab files exist.
- Explain anything I need to do with point-and-click steps, never terminal commands. Skip legal, licence and regulatory caveats.
- Any HTML page has a Day/Night toggle, and every HTML or Markdown file you publish is also sent to me as a downloadable file.
- Never copy anything from `assets/abp` in github.com/bmonte777/Benro-Polaris-Controller (ogecko's driver).
- Use a task list. Start now.
