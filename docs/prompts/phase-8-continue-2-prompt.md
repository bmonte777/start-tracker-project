# Canopus (Star Tracker Project) — Phase 8, carry on after Phase 9a

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Opus 5.5 · **Effort:** high

---

You are the lead engineer on my Star Tracker Project, now named **Canopus**, carrying on Phase 8 (design for mass production) from earlier chats. The full brief is `claude/phase-8-prompt.md` (repo `docs/prompts/phase-8-prompt.md`): read it first. Its deliverables, output format and working rules all still apply. The previous hand-off, `claude/phase-8-continue-prompt.md`, lists the Phase 8 decisions D87–D99 and what was done before the hold; this prompt says what changed since and what comes next.

## First, before any work

1. **Repo:** github.com/bmonte777/start-tracker-project. Attach it with push access before anything else; if that is refused, tell me at once. (It is refused in every new chat until I authorise it in that chat; I will type the authorisation.)
2. **Ask me, in one batched question:** what has been ordered for P0, what has arrived or been measured, whether Laifual or any other supplier has replied, and whether any production quote has come back. The answer decides the plan below.
3. Read `hardware/production/PROGRESS.md`, then the root `PROGRESS.md` (Phase 7) and `docs/PROGRESS-phase-9a.md`.

## Where it stands (24 Nov 2026)

**Branches:** `phase-8-production` (draft PR 14, base `phase-7-prototype`) is on hold. `phase-9a-launch` (draft PR 15, base `phase-8-production`) holds the Phase 9a work and the rename. Merge PR 15 into `phase-8-production` first (I approve that merge now), then carry on on `phase-8-production`.

**Phase 7:** at the order stage when last asked; nothing measured. **Phase 8:** on hold since 24 Nov, waiting for P0 measurements or quotes.

**Phase 9a (done, 24 Nov):**
- Name **Canopus** (D102). Visible names only were changed (D100): Wi-Fi/BLE `Canopus-XXXX`, `canopus.local`, OLED splash, app names, Alpaca/LX200 names, `canopus-update.stfw`, `canopus-release`, app folders. The app id, `/startracker/v1/…`, `_startracker._tcp`, code comments, package names, the bring-up banner and `StarTrackerSim.exe` stay as they are (D103 lists every change; all tests green).
- Look of anything public: D101 "Night observatory".
- User guide, operating chapters: Docs "Canopus — User guide" https://claude.ai/artifact/Gj22crYNNsjG5oRintECHD = `docs/09-user-guide.md` = Project `claude/10-user-guide.md`, with 22 pending-P1 items in one table.
- Website design study (not published): Design canvas https://claude.ai/artifact/1HEVoUPqnL5tCx2WZk1vGN; standalone pages in `docs/website/`.

**Name changes Phase 8 still has to carry:**
- New Phase 8 documents, drawings title blocks, RFQ packages, labels, packaging and the factory-test firmware use **Canopus**. Existing Phase 3–8 documents keep "Star tracker" in history; change only what a supplier or customer will see.
- The root `README.md`, the P0 measurement procedures (`docs/measurements/procedures.md`) and the firmware bring-up banner (`st_sys/bringup.cpp`) still say Star Tracker; rename them only when they are next edited, and tell me.
- The CAD renders carry a baked-in "Star tracker P1" title; the next render run should say "Canopus P1".

## Next, in order

**If nothing has arrived and no quote is back** (Phase 8 stays on hold), do only what is worth doing before P0:
1. **Altitude seal (D95):** find the seal from a supplier table (never from memory) with its fitted width; check it in the CAD; show me the ST-311/ST-312 change before making it; rerun the stack-ups.
2. **Reducer RFQs:** make the reducer RFQ package ready to send under the Canopus name (text, drawings list, quantities 100 / 500 / 1,000), and give me point-and-click steps to send it myself.
3. Then stop, update the progress notes and write the next prompt.

**If P0 results or quotes have arrived**, resume the full Phase 8 list from `claude/phase-8-continue-prompt.md` ("Next, in order"), starting with whatever the new results change:
1. Put every measured number into the "Numbers pending P1" table of `docs/08-production.md` and into the user guide's Pending-P1 table where it applies; show me any number that misses its target, with what it changes.
2. Altitude seal (D95), as above.
3. Sealed USB-C sockets for ST-501 (D89): LCSC number confirmed, footprint checked; show me the board change first.
4. Production parts list and cost model (deliverable 11): Sheets artifact + `hardware/bom/production-parts-list.csv` at 100 / 500 / 1,000 heads, with quotes where they exist; landed cost; retail at 2.0×, 2.5×, 3.5×; recheck the market prices (Benro Polaris Astro, ZWO AM3N, Asterra Z+) in the same week.
5. Assembly line and end-of-line test (deliverable 8), including the factory-test mode in the firmware.
6. Then deliverables 4, 7, 9, 10, 2, 12 and 13 as the brief and the earlier hand-off order them.

## Working rules (same as before)

- I do all physical work. Explain anything I must do with point-and-click steps, never terminal commands.
- Ask me before any decision not in the decisions log. Batch the questions with a recommendation each, carry on with the recommended option marked "pending approval", and add what I approve to the decisions log (repo and Project) as **D104 onwards** (questions from **Q81**).
- Research on the web where facts can change (parts, stock, prices), cite sources, never take a part number from memory.
- Skip legal, licence, certification and regulatory caveats.
- Commit and push after each deliverable; keep `hardware/production/PROGRESS.md`, the Docs doc "Phase 8 — Design for mass production", `docs/08-production.md` and Project `claude/09-production.md` in step.
- Every HTML page has a Day/Night toggle; HTML and Markdown deliverables are also sent to me as files.
- When a task or the phase is finished, write the next prompt (the full Phase 9 prompt at the end of Phase 8: maintenance guide, spare-parts list, photos, unboxing, final packaging, website from the design study, user guide finished with P1 numbers), with the recommended model and effort; save it to the Project and send it to me as a file.

Start now.
