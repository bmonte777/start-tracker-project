# Star Tracker Project — Phase 8 (continued): design for mass production

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Opus 5.5 · **Effort:** high

---

You are the lead engineer on my Star Tracker Project, carrying on Phase 8 (design for mass production) from an earlier chat. The full brief is `claude/phase-8-prompt.md` (repo `docs/prompts/phase-8-prompt.md`): read it first. Its deliverables, output format and working rules all still apply. This prompt only says where the work stands.

## Where it stands (24 Nov 2026, evening)

- **Repo:** github.com/bmonte777/start-tracker-project, branch `phase-8-production` (made from `phase-7-prototype`, because Phase 7 is not finished), draft PR 14 with base `phase-7-prototype`. Attach it with push access before anything else and tell me at once if that is refused. Read `hardware/production/PROGRESS.md` first, then the root `PROGRESS.md` (Phase 7 state).
- **Phase 7:** still at the order stage: nothing measured. I am placing the wave-1 orders. Ask me what has been ordered or has arrived, whether Laifual has replied, and whether any production quote has come back.
- **Decisions:** Q67–Q72 approved on 24 Nov → D87–D92 in `docs/02-decisions-log.md` and Project `claude/02-decisions-log.md`:
  - D87 production cartridges designed for hollow strain-wave component sets in our own CNC housings with a bought crossed-roller bearing (bearing moment stiffness ≥ 6.4 × 10⁴ N·m/rad size 17, ≥ 3.6 × 10⁴ size 14); quotes for both component sets and housed units; final choice at the P2 gate. P0/P1 keep the housed LHT units.
  - D88 processes: cartridge housings CNC 6061 from P2; body/tower MJF at 100, re-quoted at 1,000; covers, bezel, tray, door, pack shells, roll enclosure, carriers and cell holders MJF at 100, aluminium-tool moulding at 1,000; gaskets die-cut or O-ring cord; metal stays CNC.
  - D89 design for IPX6, IPX4 signed off on P2; sealed USB-C sockets on the production ST-501.
  - D90 no board change for scarce chips: TPS25751DREFR buffer stock, MAX-M10M-00B as GNSS alternate, RV-3028-C7 from JLCPCB stock (C3019759).
  - D91 production head alone ≤ 5.1 kg, wedge extra (≤ 5.75 kg together).
  - D92 final assembly in Portugal by me and one helper.
- **Done:**
  - Phase 8 doc, first instalment: Docs "Phase 8 — Design for mass production" https://claude.ai/artifact/SLxdWy4yw5mBx9BivGkV6M = `docs/08-production.md` = Project `claude/09-production.md`. Holds the process per part with break-evens (covers: 407 heads with aluminium tools, 610 with steel; body/tower about 443), the scarce-chip plan, this week's reducer, cell and competitor prices, a preliminary cost/retail check (landed EUR 1,097 today, EUR 1,163 with Laifual's published tiers, EUR 782 with component sets; working retail figure EUR 1,700 before VAT, valid only if landed ≤ EUR 800), the weight check (5.11 kg head alone with D87) and the 18 numbers pending P1.
  - RFQ folders `hardware/production/rfq/`: reducer and battery-pack packages written (quantities, acceptance limits, message to paste); the others are placeholders.
  - CAD generator: build123d 0.13 installs in the container (`pip install --break-system-packages build123d`); `hardware/cad/build_all.py --only parts,assembly,checks` reproduces the Phase 3 checks (about 6 min; the rebuild only changes timestamps in STEP/STL, so do not commit those).
- **Market prices used (read 24 Nov):** Benro Polaris Astro USD 999 (Adorama/Newegg), ZWO AM3N USD 1,499 (ZWO US store), Asterra Z+ USD 699. Recheck them in the week the retail price is recommended.
- **Measured:** nothing.

## Next, in order

1. **Tolerance stack-ups** (deliverable 3), worst-case and RSS with the result against the spec: encoder chip-to-magnet gap (D48) and run-out, belt centre distance and pulley alignment, reducer-to-housing concentricity, clamp and wedge interface, bezel and display window, seals for IPX6 (D89). Take dimensions from `hardware/cad/stcad/params.py` and the part code; production tolerances by process (CNC, MJF, moulding). Write a script under `tools/production/` so they rerun.
2. **Sealed USB-C sockets for ST-501 (D89):** find sealed receptacles in stock (LCSC number confirmed, never from memory), check the footprint against the board and bezel, then show me the proposed board change before making it.
3. **Production parts list and cost model** (deliverable 11): rebuild the master parts list for production with the D87/D88 processes as a Sheets artifact + `hardware/bom/production-parts-list.csv`, priced at 100 / 500 / 1,000 heads from quotes or cited list prices (labelled quoted / list price with date / estimate); tooling amortised; labour from deliverable 8 (estimate until P1); scrap, freight and import to Portugal (D92); landed cost per head; retail at 2.0×, 2.5×, 3.5×.
4. **Assembly line and end-of-line test** (deliverable 8): station plan for one or two people with times (estimates until P1), tools and fixtures per station, the end-of-line test sequence, the test-record format with serial numbers, and the factory-test mode in the firmware (made and pushed directly; the firmware stays the contract for the apps). Limits stay *pending P1* where they wait on a measurement.
5. **Board production revisions** (deliverable 4): panelisation, fiducials, tooling holes, pogo-pin test points, programming in the jig, second sources in the BOMs (D90); ask me before changing any board.
6. **Tooling and fixtures** (deliverable 7, ST-9xx), **pack production** (deliverable 9), **packaging** (deliverable 10).
7. **CAD/DFM revisions** (deliverable 2) as the reducer drawings arrive from the RFQ: component-set cartridges (D87), CNC cartridge housings, moulding versions of the covers (D88), gasket grooves (D89); STEP and A4 drawings with GD&T in `hardware/production/`, a drawing index. Ask me before changing any part.
8. **P2 pilot plan** (deliverable 12) once P1 is reported; the **Phase 8 report** (deliverable 13) at the end.
9. Keep `hardware/production/PROGRESS.md`, the Docs doc, `docs/08-production.md` and Project `claude/09-production.md` in step; commit and push after each deliverable. When a task or the phase is finished, write the next prompt (the Phase 9 prompt at the end of Phase 8), with the recommended model and effort, save it to the Project and send it to me as a file.

Start now.
