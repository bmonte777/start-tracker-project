# Phase 7 — Prototype: progress notes

So a new chat can carry on. Brief: `docs/prompts/phase-7-prompt.md` (Project `claude/phase-7-prompt.md`). Document: `docs/07-prototype.md` (Project copy `claude/08-prototype.md`; Docs version "Phase 7 — Prototype", https://claude.ai/artifact/LVHGbTaGSPDXsHxDAeTkyV). Order plan Sheet: https://claude.ai/artifact/VKiXzXWiCveezhW2ECiHio = `hardware/bom/order-plan-p0-p1.csv` (regenerate with `tools/order_plan.py`, then rewrite the Sheet's rows 9–61).

## State (24 Nov 2026) — round P0, order stage

- **GitHub:** PR 12 was already merged. Branch `phase-7-prototype`; push access granted by Bruno on 24 Nov (the first attach was refused, then approved).
- **Open questions:** Q60–Q66 (doc section "Questions"), all *pending approval*; nothing in D1–D79 changed yet. Q64 (BOM part numbers) and Q65 (ST-205) touch board order files and a part: do not change them before Bruno approves.
- **Printer:** not known whether the H2S has been bought (Q60). Memory says he owned no printer on 20 Nov.

| Round stage | State |
|---|---|
| Order plan P0/P1 | done: Sheet + CSV, 53 lines, prices/stock read 24 Nov where marked |
| P0 order guides | done (doc section "Order guides"): Laifual quote, JLCPCB parts + boards, JLCCNC, JLC3DP |
| P0 order | waiting for Bruno (and the Laifual quote) |
| P0 build guide, bring-up companion, measurement scripts | not started; next |
| P0 build / bring-up / measurements | not started (no hardware) |
| P1 | not started |

## Findings (reported to Bruno)

- F1: ST-520 U1 LCSC C2984637 now lists as MT6835GT-A10K (out of stock); C2932578 = MT6835GT-STD-R, 850 in stock.
- F2: ST-501 U6 MPN TPS25752ARSMR is not orderable; TPS25752ASRSMR (same RSM package) is. Pinout to be checked against the datasheet.
- F3: shopping-list link for ST-205 (RS 236-5741) is a 3 mm HTD pulley, not GT2.
- F4: ST-205 bolt pattern (4 × Ø3.4 on PCD 17) comes from the Harmonic Drive SHF outline; needs Laifual's LHT-III drawing.
- Supply: TPS25751DREFR nearly gone (Mouser 78/0, Jan 2027; DigiKey Oct 2027); MAX-M10S and RV-3028-C7 0 at Mouser; TMC2209 21 at LCSC; ITV4030 fuse non-stocked at Mouser.

## Measured

Nothing yet. `docs/measurements/P0/` and `P1/` are empty (raw data goes there).
