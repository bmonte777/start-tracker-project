# Star Tracker Project — Phase 8, carry on (after the tolerance stack-ups)

**Use:** new chat in the "Star Tracker Project" Project · **Model:** Opus 5.5 · **Effort:** high

---

You are the lead engineer on my Star Tracker Project, carrying on Phase 8 (design for mass production) from an earlier chat. The full brief is `claude/phase-8-prompt.md` (repo `docs/prompts/phase-8-prompt.md`): read it first. Its deliverables, output format and working rules all still apply. This prompt only says where the work stands.

## Where it stands (24 Nov 2026, night)

**Repo:** github.com/bmonte777/start-tracker-project, branch `phase-8-production` (made from `phase-7-prototype`, because Phase 7 is not finished), draft PR 14 with base `phase-7-prototype`. Attach it with push access before anything else; if that is refused, tell me at once (last time it worked once I authorised it in chat). Read `hardware/production/PROGRESS.md` first, then the root `PROGRESS.md` (Phase 7 state).

**Phase 7:** still at the order stage, nothing measured. I am placing the wave-1 orders. Ask me what has been ordered or has arrived, whether Laifual has replied, and whether any production quote has come back.

**Decisions:** D87–D92 (24 Nov) and D93–D99 (24 Nov, from the stack-ups) are in `docs/02-decisions-log.md` and Project `claude/02-decisions-log.md`:
- D93: the P0 ST-303 is ordered as drawn (rev C); P1 takes rev D.
- D94: ST-303 rev D has the V-ring shoulder at Z 37.5 (VA-75 fitted width 9.0) and dowel holes 4 E7 round + 4 E7 × 6 radial slot. ST-313 rev D: VA-65 back support R36; roll fitted width stays 6.0, because a recess would hit the clamp overhang; +28 g.
- D95: altitude seal. The VA-80 cannot fit (2.5 mm). A smaller seal goes on a smaller arm seat (e.g. VA-65 size on a 65 seat outside the R31 output flange), with its lip on the reducer's fixed face inside the tower's Ø84 opening, 6.0 mm away. **Open: choose the seal from a supplier table and show me before changing ST-311/ST-312.**
- D96: production encoder board chip-side down on 3 pads in the CNC housing, located by 2 pins; gap 1.5 mm (WC 1.08–1.92); tube flange 28 h7/H7; magnet seat 6.00 +0.02/0.
- D97: 60T pulley a light press on the wave-generator stub.
- D98: 3.0 mm O-ring cord in 2.15 mm grooves with hard stops, screws ≤ 40 mm apart.
- D99: 45° chamfer around the OLED window.

**Done:**
- Phase 8 doc, second instalment: Docs "Phase 8 — Design for mass production" https://claude.ai/artifact/SLxdWy4yw5mBx9BivGkV6M = `docs/08-production.md` = Project `claude/09-production.md`. It holds deliverables 1 and 3, the scarce-chip plan, prices, the preliminary cost/retail check (landed EUR 1,097 today, EUR 782 with component sets; working retail EUR 1,700 before VAT only if landed ≤ EUR 800), weight (now 5.14 kg head alone with D87 and ST-313 rev D, against D91's 5.1) and the 18 numbers pending P1.
- Tolerance stack-ups: `tools/production/tolerance_stackups.py` (+ `test_tolerance_stackups.py`, 12/12) → `hardware/production/tolerances/stackups.md/.json`.
- CAD: ST-303 and ST-313 rev D (`params.PART_REV` stamps the rev on their drawings); checks clean. build123d, numba and matplotlib install with `pip install --break-system-packages`. `hardware/cad/build_all.py --only parts,assembly,checks` takes about 6 min; `--only drawings,fab` about 1 min. A rebuild rewrites every STEP/STL/PDF: commit only the files of parts that changed.
- RFQ folders: reducer and battery-pack packages written; the others are placeholders.

**Market prices used (read 24 Nov):** Benro Polaris Astro USD 999, ZWO AM3N USD 1,499, Asterra Z+ USD 699. Recheck them in the week the retail price is recommended.

**Measured:** nothing.

## Next, in order

1. **Altitude seal (D95):** find the seal (confirmed from a supplier table, never from memory) and its fitted width; check it in the CAD; show me the ST-311/ST-312 change before making it. Then rerun the stack-ups.
2. **Sealed USB-C sockets for ST-501 (D89):** find sealed receptacles in stock (LCSC number confirmed, never from memory); check the footprint against the board and bezel; show me the proposed board change before making it.
3. **Production parts list and cost model (deliverable 11):** a Sheets artifact + `hardware/bom/production-parts-list.csv`, priced at 100 / 500 / 1,000 heads (quoted / list price with date / estimate); tooling amortised; labour (estimate until P1); scrap, freight and import to Portugal (D92); landed cost per head; retail at 2.0×, 2.5×, 3.5×.
4. **Assembly line and end-of-line test (deliverable 8):** stations for one or two people, with times, tools and fixtures; the test sequence; the test-record format; the factory-test mode in the firmware (made and pushed directly).
5. **Board production revisions (deliverable 4):** ask me before changing any board.
6. **Tooling and fixtures (7), pack production (9), packaging (10).**
7. **CAD/DFM revisions (deliverable 2), as the reducer drawings arrive:** D96 encoder pads and pins, D97, D98 grooves, D99 chamfer and the moulding versions; STEP and A4 drawings with GD&T; a drawing index. Ask me before changing any part not already covered by D94–D99.
8. **P2 pilot plan (12)** once P1 is reported; **Phase 8 report (13)** at the end.

Keep `hardware/production/PROGRESS.md`, the Docs doc, `docs/08-production.md` and Project `claude/09-production.md` in step; commit and push after each deliverable. When a task or the phase is finished, write the next prompt (the Phase 9 prompt at the end of Phase 8), with the recommended model and effort; save it to the Project and send it to me as a file.

Start now.
