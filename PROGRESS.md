# Phase 7 — Prototype: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-7-prompt.md` (Project `claude/phase-7-prompt.md`). Document: `docs/07-prototype.md` (Project copy `claude/08-prototype.md`; Docs version "Phase 7 — Prototype", https://claude.ai/artifact/LVHGbTaGSPDXsHxDAeTkyV). Order plan Sheet: https://claude.ai/artifact/VKiXzXWiCveezhW2ECiHio = `hardware/bom/order-plan-p0-p1.csv` (regenerate with `tools/order_plan.py`, then rewrite the Sheet's rows 9–71).

## State (24 Nov 2026) — round P0, order stage

- **GitHub:** PR 12 was already merged. Branch `phase-7-prototype`, draft PR 13; push access granted by Bruno on 24 Nov (the first attach was refused, then approved).
- **Decisions:** Q60–Q66 answered on 24 Nov → D80–D86 in `docs/02-decisions-log.md` and Project `claude/02-decisions-log.md`. No open questions.
- **Printer:** none, and none will be bought (D80): all printed parts from JLC3DP.
- **D84 applied:** ST-520 U1 → C2932578 / MT6835GT-STD-R; ST-501 U6 → TPS25752ASRSMR (pins checked against the datasheet). Changed in both BOM copies, both model JSONs, `cartridge-board/design.py`, `tools/catalog.py`, `tools/costs.py`, `tools/compose_doc.py`, `doc/status.json`, `doc/tables.json`, the doc template and `docs/04-electronics.md`. The cartridge BOMs keep CRLF line ends.
- **ST-205:** shopping-list line now says "made from the Laifual drawing (D85)"; the wrong HTD link is removed.

| Round stage | State |
|---|---|
| Order plan P0/P1 | done: Sheet + CSV, 63 lines (full tool kit, D86; OLED, thermal epoxy, bench XT30 lead added for the build guide), prices/stock read 24 Nov where marked |
| P0 order guides | done (doc section "Order guides"): Laifual quote, JLCPCB parts + boards, JLCCNC, JLC3DP |
| P0 order | waiting for Bruno (and the Laifual quote) |
| P0 build guide | done: `docs/guides/p0-build-guide.html` = https://claude.ai/artifact/HiuZScf8CjeMNvxB91qPxm (sheets 0–13 + R, harness and torque reference). Built from `joints.py`, harness data, D46/D48/D80–D86 |
| P0 bring-up companion, measurement scripts | next |
| Hand-off prompts | `docs/prompts/phase-7-continue-prompt.md` (carry on Phase 7 in a new chat) and `docs/prompts/phase-8-prompt.md` (written early at Bruno's request, 24 Nov; update it with Phase 7 results before use). Both in the Project |
| P0 build / bring-up / measurements | not started (no hardware) |
| P1 | not started |

## Findings (reported to Bruno)

- F5 (text fixed): `parts_cart.py` notes said ST-211 takes 16 M3 inserts and ST-210 12 M3; the feature tables give 18 and 14. Notes corrected; the drawing PDFs still carry the old note until they are rebuilt (build123d not in this container).

- F1 (fixed, D84): ST-520 U1 LCSC C2984637 now lists as MT6835GT-A10K (out of stock); C2932578 = MT6835GT-STD-R, 850 in stock.
- F2 (fixed, D84): ST-501 U6 MPN TPS25752ARSMR is not orderable; TPS25752ASRSMR (same RSM package) is. Pinout to be checked against the datasheet.
- F3: shopping-list link for ST-205 (RS 236-5741) is a 3 mm HTD pulley, not GT2.
- F4: ST-205 bolt pattern (4 × Ø3.4 on PCD 17) comes from the Harmonic Drive SHF outline; needs Laifual's LHT-III drawing.
- Supply: TPS25751DREFR nearly gone (Mouser 78/0, Jan 2027; DigiKey Oct 2027); MAX-M10S and RV-3028-C7 0 at Mouser; TMC2209 21 at LCSC; ITV4030 fuse non-stocked at Mouser.

## Measured

Nothing yet. `docs/measurements/P0/` and `P1/` are empty (raw data goes there).
