# Phase 8 — Design for mass production: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-8-prompt.md` (Project `claude/phase-8-prompt.md`). Document: `docs/08-production.md` (Project copy `claude/09-production.md`; Docs version "Phase 8 — Design for mass production", https://claude.ai/artifact/SLxdWy4yw5mBx9BivGkV6M).

## State (24 Nov 2026)

- **GitHub:** branch `phase-8-production`, made from `phase-7-prototype` (Phase 7 not finished, so its PR 13 is not merged). Draft PR open. The first attach was refused; Bruno fixed access the same day.
- **Phase 7:** order stage, nothing measured. Every number that waits on P0/P1 is in the "Numbers pending P1" table of `docs/08-production.md` (18 rows).
- **Decisions:** Q67–Q72 approved 24 Nov → D87–D92 in `docs/02-decisions-log.md` and Project `claude/02-decisions-log.md`. No open questions.

| Deliverable (brief) | State |
|---|---|
| 1 Process per part | done (doc section 3, D88) |
| 2 DFM revisions, STEP, drawings, GD&T | not started; needs build123d in the container and the Laifual drawing (D85) |
| 3 Tolerance stack-ups | not started |
| 4 Production board revisions | sourcing plan done (D90); sealed USB-C (D89) and panel/jig changes not started |
| 5 Reducer and bought-part quotes | list prices found; RFQ text ready; no quotes yet |
| 6 RFQ folders | skeleton in `hardware/production/rfq/` with a README per package |
| 7 Tooling and fixtures ST-9xx | not started |
| 8 Assembly, end-of-line test, factory-test firmware | not started |
| 9 Pack production | assemblers found; not started |
| 10 Packaging | not started |
| 11 Production parts list (Sheet + CSV), retail price | preliminary figures in the doc; Sheet not built |
| 12 P2 pilot plan | not started |
| 13 Phase 8 report | the doc is its first instalment |

## Key numbers so far (all estimates or list prices, read 24 Nov)

- Landed cost at 1,000 heads: EUR 1,097 (Phase 4); EUR 1,163 with Laifual's published volume tiers; EUR 782 with component sets (D87, spec 9.3 + EUR 7).
- Covers MJF vs moulding break-even: 610 heads (steel tools), 407 (aluminium tools). Body/tower: 443 heads if two tools cost USD 40,000.
- Market: Benro Polaris Astro USD 999 (Adorama/Newegg), ZWO AM3N USD 1,499 (ZWO US), Asterra Z+ USD 699.
- Working retail figure EUR 1,700 before VAT, only if landed ≤ EUR 800.
- Weight with D87: 5.11 kg head alone, 5.73 kg with wedge (D91 target ≤ 5.1 / ≤ 5.75).
