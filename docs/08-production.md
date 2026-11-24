# Phase 8 — Design for mass production

24 Nov 2026 · Bruno · Second instalment (tolerance stack-ups added)

Live copy: [Phase 8 — Design for mass production](https://claude.ai/artifact/SLxdWy4yw5mBx9BivGkV6M)

## Where Phase 8 stands

Phase 8 has started on paper only. Phase 7 is still at the order stage: on 24 Nov nothing had been ordered, built or measured, and Laifual had not replied. Every number that depends on a measurement is marked *pending P1* and collected in one table near the end.

The repo is attached (the first request was refused; access was fixed on 24 Nov). The work is on branch `phase-8-production`, made from `phase-7-prototype` because Phase 7 is not finished.

This first instalment holds the work that does not need the measurements:

- six production decisions (Q67–Q72, approved as D87–D92);
- the tolerance stack-ups (deliverable 3) and the fixes they led to (D93–D99), with ST-303 and ST-313 at rev D;
- the production process for every made part at 100 and 1,000 heads, with the break-even working;
- a production fix for each scarce board part;
- this week's prices for reducers, cells and competitors;
- a first check of cost, retail price and production weight against the spec.

The main finding: at the current cost (landed EUR 1,097 per head at 1,000), the spec's 2.0–3.5× markups give EUR 2,194–3,840 before VAT. A Benro Polaris Astro now sells for USD 999 at US dealers and a ZWO AM3N for USD 1,499 at ZWO's US store. Moving to reducer component sets in our own housings (Q67) is the only change large enough to close most of that gap.

No prices have been quoted to us yet. Every price below is either a list price with the date it was read or an estimate.

## Decisions Q67–Q72 → D87–D92 (approved 24 Nov)

Bruno approved all six recommendations on 24 Nov ("Q67-Q72 - Approved recommendations"). They are D87–D92 in `docs/02-decisions-log.md` and the Project's `claude/02-decisions-log.md`.

| # | Question | Decision | Why | Customer-handled parts (D13) |
| --- | --- | --- | --- | --- |
| Q67 → D87 | Reducers in production: keep the housed Laifual LHT units (D18), or use hollow component sets (circular spline, flexspline, wave generator) in our own housings with a crossed-roller bearing? | Design the production cartridges for hollow component sets. Ask for quotes on both. Decide at the P2 gate from the measured periodic error | The spec's mass budget saves 1.10 kg (2.70 kg to 1.60 kg, spec 3.10). The spec's landed cost falls from about EUR 1,090 to about EUR 775 at 1,000 heads (spec 9.3). It is the only change big enough for the price gap (section 6). Risk: we have to hold the bearing and the concentricity ourselves | The cartridge keeps its interface: 4 + 4 screws and one plug, the same hex keys |
| Q68 → D88 | Process for housings and covers at 100 and 1,000 heads | Cartridge housings ST-210/211 in CNC 6061 from P2 on, at every volume. Body and tower ST-310/311 in MJF PA12 at 100; re-quote MJF, CNC and moulding with the 1,000 order. Covers, bezel, tray, door, pack shells and carriers in MJF PA12 at 100 and injection-moulded in aluminium tools at 1,000. Gaskets as die-cut flat seals or O-ring cord | Printed nylon cannot hold an H7 reducer register and creeps under belt tension (risk R6). For the covers, moulding pays above about 410–610 heads (section 3) | Door, tray, covers and pack shell keep their snap latch and screws. No new tool for the customer |
| Q69 → D89 | Sealing class in production: IPX6 (D9) or IPX4 (as your Phase 8 brief says) | Keep D9: design for IPX6, sign off IPX4 on P2, then test IPX6 on the first production sample. That means sealed USB-C sockets on ST-501 in production, which changes D49 and the board footprints | The Polaris is rated IPX6. The open sockets of D49 would fail either test | The sockets look the same; cables plug in the same way |
| Q70 → D90 | Second sources for the scarce chips | No board change. Buy buffer stock of TPS25751DREFR. Add MAX-M10M-00B as the GNSS alternate and the RV-3028-C7 QA grade as the clock alternate | Details and stock in section 4 | None |
| Q71 → D91 | Production weight target (D28 says ≤ 5.1 kg with wedge and battery) | Restate it as ≤ 5.1 kg for the head alone, with the 0.62 kg wedge extra (≤ 5.75 kg together) | With Q67 the estimate is 5.11 kg for the head alone; 5.1 kg with the wedge would need another 0.6 kg cut (section 7) | None |
| Q72 → D92 | Where the heads are assembled and tested | In Portugal, by you and one helper, from kits of finished parts | This sets freight, import and labour in the cost model. The spec assumed 12 % freight and import and 1.5–3 h of labour | None |

## Production process per part (D88)

The metal parts stay CNC at every volume up to 1,000 heads. The plastic covers switch from MJF to moulding somewhere between about 410 and 610 heads. Part names and P1 processes are from Phase 3 rev C and D80. Anodise colour is left to Phase 9 (branding); clear in the meantime.

| Part | P1 (now) | 100 heads | 1,000 heads | Material and finish | Why |
| --- | --- | --- | --- | --- | --- |
| ST-312 altitude arm, ST-313 roll shelf | CNC | CNC | CNC | 6061-T6, bead-blast, hard anodise | Stiffness (spec 3.7). Too few parts for die casting, which pays above about 2,000 heads (spec 9.2) |
| ST-301, 302, 303, 331 plates, ST-305 arcs | CNC | CNC | CNC | 6061-T6, bead-blast, hard anodise | As above. Fixturing faces and set-ups are added in the CAD revision |
| ST-207 motor plate (×3) | CNC | CNC | CNC | 6061-T6, anodise | Small and simple; a batch run is cheap |
| ST-208, ST-215 encoder tubes | Turned | Turned | Turned (bar-fed lathe) | 6061 (D35), clear anodise | Concentricity sets the encoder run-out |
| ST-210, ST-211 cartridge housings | FDM PA12-CF (D80) | **CNC** | **CNC** | 6061-T6, anodise | H7 reducer register; no creep under belt tension (R6). With Q67 they also carry the crossed-roller bearing |
| ST-310 body, ST-311 tower | MJF PA12 | MJF PA12, dyed black | MJF, or moulded PA66-GF30 if the quote is right | PA12 / PA66-GF30 | EUR 92 per head in MJF; moulding pays above about 440 heads if two tools cost USD 40,000 (estimate) |
| ST-315 bezel, ST-317 tray, ST-318 door, ST-319 top cover, ST-605/612 pack shells, ST-217 roll enclosure | Printed | MJF PA12 | **Moulded**, aluminium tools | PC/ABS or ASA (UV), chosen at the RFQ | Break-even below |
| ST-212, ST-216 carriers, ST-606 cell holders | Printed | MJF PA12 | Moulded (family tool) | PA66-GF30 | Each encoder board must stay within 0.1 mm of its magnet (D48) |
| ST-611 light pipe | PETG | Clear resin print | Moulded | Clear PC | Must be clear |
| ST-316 button caps, ST-320 cable guides, ST-322 bumpers | TPU | Printed TPU | Printed TPU | TPU 95A | Too small to pay for tools; re-check at 2,000 |
| ST-323–325, 327, 328, 610 gaskets | TPU | Die-cut or O-ring cord | Same | Silicone or EPDM | Printed TPU is not a reliable IPX6 seal; needs groove changes (Q68) |
| ST-205 60T pulley | Waits for Laifual drawing (D85) | CNC | CNC or configured bought pulley | 6061 or 7075, anodise | Run-out ≤ 0.03 mm (spec 3.5) |
| ST-501, 520, 602 boards | JLCPCB | JLCPCB, panelised | JLCPCB and one EU assembler quoted | As Phase 4 | Same files; jig programming added |
| ST-050 pack | Battery shop | Pack assembler | Pack assembler | 4 × P50B + ST-602 | Spot welding and pack test at the assembler |

**Covers: MJF against moulding (estimate).** The moulded set is the bezel, tray, door, top cover, two pack shells, roll enclosure, carriers and cell holders. That is 9 pieces from 6 tools, with family tools for tray + door, pack halves and carriers + cell holders (the spec's 6 tools, 9.2).

1. Mass as printed (Phase 3 table): 24 + 17 + 15 + 26 + 30 + 32 + 111 + 3 × 7 + 2 × 2 = 280 g. MJF parts are solid, so this is a lower bound.
2. MJF: 280 g × USD 0.275/g = USD 77.00 = EUR 70.07 per head (JLC3DP list price used in the spec, read 20 Nov).
3. Moulded: 9 pieces × USD 2.00 = USD 18.00 = EUR 16.38 per head (estimate, inside a published band of USD 0.60–4.00 per part).
4. Saving per head: 70.07 − 16.38 = EUR 53.69.
5. Steel tools, 6 × USD 6,000 = USD 36,000 = EUR 32,760: break-even 32,760 ÷ 53.69 = **610 heads**.
6. Aluminium tools, 6 × USD 4,000 = USD 24,000 = EUR 21,840: break-even 21,840 ÷ 53.69 = **407 heads**.
7. Over 1,000 heads with aluminium tools: 1,000 × 53.69 − 21,840 = EUR 31,850 saved.

Aluminium tools usually last several thousand shots, well beyond the first 1,000 heads, so they are the recommendation. The exchange rate is the spec's USD 1 = EUR 0.91.

**Body and tower (estimate).** MJF: 368 g × USD 0.275 = USD 101.20 = EUR 92.09 per head. If the two moulds cost USD 40,000 (EUR 36,400) and the moulded pair costs EUR 10, break-even is 36,400 ÷ (92.09 − 10) = **443 heads**. The real mould price decides this, so it goes in the 1,000-head RFQ.

## Scarce board parts in production (D90)

None of the three needs a board change: one needs buffer stock, one gets a same-footprint alternate, and the third is in stock at JLCPCB. Stock was read on 24 Nov 2026 and moves daily.

| Part | What was found | Production fix | Check before adopting |
| --- | --- | --- | --- |
| TPS25751DREFR, port A (U3) | LCSC [C30169739](https://www.lcsc.com/product-detail/C30169739.html) pages show anything from out of stock to 5,039 depending on the day. TI's [own page](https://www.ti.com/product/TPS25751/part-details/TPS25751DREFR) limits orders to protect samples until more stock comes. DigiKey gives a 12-week standard lead time at GBP 2.17. One broker lists 14,860 at USD 9.92, about 4× the distributor price | Buy 110 pieces (100 heads + 10 %) as soon as a franchised distributor shows stock. For 1,000 heads, place a scheduled order at least 12 weeks ahead. No brokers. The TPS25750 is pin-for-pin compatible ([TI FAQ](https://e2e.ti.com/f/1/t/1346998)) and stays an emergency fallback only | TI fixed charger-pairing problems in the TPS25751, so the TPS25750's supported-charger list must include the BQ25792 before it could be used |
| MAX-M10S-00B, GNSS (U24) | DigiKey: out of stock, backorder, 16-week lead time. Future Electronics lists 774 at USD 12.97 for 250+ | Add **MAX-M10M-00B** as the alternate. It is the same MAX-M10 family; u-blox describes both as pin-compatible with earlier MAX modules. It lacks the S version's LNA and SAW filter, which D54's active antenna already provides | Compare the two pin tables and the antenna-bias pin before adding it to the BOM. The firmware's UBX set-up should carry over (same M10 platform) |
| RV-3028-C7, clock (U23) | Out of stock only at Mouser. JLCPCB lists [C3019759](https://jlcpcb.com/partdetail/C3019759) (RV-3028-C7-32.768kHz-1ppm-TA-QC): 19,386 in stock, USD 1.55 at 100+. DigiKey: 1,265 of the same part, and 75,731 of the automotive QA grade | Buy from JLCPCB's own stock, so it is placed like any library part. QA grade as the alternate | None: same part number family and package |

Two more parts need volume checks before the 100-head board order. The TMC2209-LA (LCSC C465949) had only 21 in stock on 24 Nov, and a batch of 100 heads needs 300. The MT6835GT-STD-R (C2932578) had 850, and 100 heads need 300. Both get a stock check and a buffer buy with the board RFQ.

## Reducers and key bought parts

No reducer maker has quoted yet. Published volume tiers suggest the spec's 1,000-head reducer price is about 12 % too optimistic.

**Prices found this week** (list prices, read 24 Nov 2026; USD 1 = EUR 0.91):

| Source | Item | Price | Use here |
| --- | --- | --- | --- |
| [Laifual, Alibaba](https://www.alibaba.com/product-detail/High-precision-Laifual-Harmonic-reducer-for_62499927002.html) | LSS series unit | USD 220 (1–499), 198 (500–999), 176 (≥ 1,000); sample 242 | The only published volume tiers: −10 % at 500, −20 % at 1,000 |
| [Laifual store](https://zjlaifual.en.alibaba.com/) | LHT series, size not stated | FOB USD 490–530 per set | Upper bound for a housed hollow unit |
| [Laifual, Alibaba](https://www.alibaba.com/product-detail/Laifual-high-torque-LSG-series-harmonic_62022131184.html) | LSG series | USD 180, MOQ 2 | Lower bound for a Laifual set |
| [Goldgun, Alibaba](https://www.alibaba.com/product-detail/LFS-Harmonic-Motor-Drive-Gearbox-High_1600968013163.html?s=p) | Harmonic gearbox, sizes 11–32, ratio 50–160 | Sample USD 145.70 | Second maker for the RFQ |
| [eBay (surplus)](https://www.ebay.com/itm/204610445897) | Leaderdrive LHS-17-80 | USD 199.90 | Not a quote; shows the size-17 price level |
| [NKON](https://www.nkon.nl/novat/rechargeable/molicel-inr21700-p50b-5000mah-50a.html) | Molicel P50B cell | EUR 4.95; EUR 4.45 for 11+ | EUR 17.80 for a pack's 4 cells |
| [18650 Battery Store](https://www.18650batterystore.com/products/molicel-21700-p50b-5000mah-50a-battery?qv=B71cH3x1S) | Molicel P50B cell | USD 11.99; USD 7.50 for 1,000+ | US price, above NKON |

**What the tiers do to the reducer cost (estimate).** The spec puts an LHT-17 at EUR 273 for one, EUR 241 at 100 and EUR 196 at 1,000: that is 88 % and 72 % of the single price. Laifual's published LSS tiers fall only to 80 % at 1,000. Applied to the spec's single prices (2 × EUR 273 + EUR 237 = EUR 783), the three reducers cost 783 × 0.80 = **EUR 626** at 1,000 heads against the spec's EUR 560: EUR 66 more per head. That is why Q67 matters.

**RFQs to send** (folders in `hardware/production/rfq/`; reducers and battery pack written):

| RFQ | Suppliers | Quantities | Acceptance |
| --- | --- | --- | --- |
| Hollow reducers, size 17 and 14, ratio 100: housed units and component sets | Laifual, Leaderdrive, [Honpine](https://www.directindustry.com/prod/suzhou-honpine-precision-industry-co-ltd/product-4614476-2802388.html), [KOFON](https://www.directindustry.com/prod/kofon-motion-group/product-181579-2483233.html), [Hansheng](https://www.directindustry.com/prod/hansheng-automation-dongguan-co-ltd/product-4605437-2740892.html), Goldgun | 100, 500, 1,000 sets | Periodic error ≤ ±20″ raw, repeatable within 3″; backlash ≤ 20″ (spec 4, T1, T2). Tightened to the P0 values when measured. One PE curve per unit |
| Battery pack ST-050 (cells, spot welding, ST-602 fitted, pack test) | [CM Batteries](https://cmbatteries.com/?p=21097) (lists a 2S2P 21700 pack, small batches), [Shenzhen First Power](https://ejfirstpower.en.alibaba.com/videoshow.html?d_type=cv), [Aceon](https://www.aceongroup.com/custom-battery-packs/battery-pack-manufacturing/battery-pack-assembly/) (UK, small runs) | 100, 500, 1,000 | Capacity ≥ 4,850 mAh per cell pair, cell match, gauge learned, pack test log per serial |
| Motors, pulleys, belts, clamp | StepperOnline, a pulley maker, Sunwayfoto (OEM DDC-60i) | 100, 500, 1,000 | Motor winding data within 10 % of datasheet; pulley run-out ≤ 0.03 mm |

**How to send the reducer RFQ (point and click).** On Alibaba, open each supplier's store, click **Contact supplier**, and paste: *"Please quote hollow-shaft strain-wave gears, ratio 100, size 17 (2 per set) and size 14 (1 per set), both as housed units with crossed-roller bearing and as component sets (circular spline, flexspline, wave generator) for our own housing. Quantities 100, 500 and 1,000 sets. Please give unit price, MOQ, lead time, shipping to Portugal (DAP), the drawings and STEP models, and whether you can supply a measured transmission-error curve per unit."* Forward each reply to me here; do not pay anything.

## Cost and retail price (preliminary)

At today's cost the product cannot be priced near its rivals; with component-set reducers (Q67) it comes within about 15 % of a ZWO AM3N. These figures start from the Phase 4 cost model and will be replaced line by line as quotes arrive. The full production parts list (Sheet + CSV) is rebuilt when the first quotes are in.

**Starting point (Phase 4, per head, before VAT):** materials EUR 2,157 / 1,308 / 969 at 1 / 100 / 1,000 heads; cost of goods EUR 2,416 / 1,452 / 1,052. Landed at 1,000 heads: 1,052 + 44,600 tooling ÷ 1,000 = **EUR 1,097**.

**Three cost cases at 1,000 heads:**

1. Today: EUR 1,097.
2. Today with Laifual's published volume tiers instead of the spec's (section 5): 1,097 + 66 = EUR 1,163.
3. Component sets in our own housings (Q67): the spec's EUR 775 (9.3) plus the EUR 7 the landed cost has grown since Phase 2 (1,097 − 1,090) = EUR 782.

**Retail before VAT, landed cost × markup (the chart in the live doc):**

| Cost case | Landed | 2.0× | 2.5× | 3.5× |
| --- | --- | --- | --- | --- |
| Component sets (Q67) | EUR 782 | EUR 1,564 | EUR 1,955 | EUR 2,737 |
| Today (Phase 4) | EUR 1,097 | EUR 2,194 | EUR 2,743 | EUR 3,840 |
| Today + reducer tiers | EUR 1,163 | EUR 2,326 | EUR 2,908 | EUR 4,071 |

Prices with Portugal's 23 % VAT, for comparison with shop prices: case 1 at 2.0× is EUR 2,194 × 1.23 = EUR 2,699; case 3 at 2.0× is EUR 1,564 × 1.23 = EUR 1,924, and at 2.5× EUR 1,955 × 1.23 = EUR 2,405.

**The market this week:**

| Product | Price | Where | What it is |
| --- | --- | --- | --- |
| [Benro Polaris Astro](https://www.newegg.com/p/0FY-002Z-003T1) | USD 999 (≈ EUR 909); GBP 1,100 at [Park Cameras](https://www.parkcameras.com/shop/benro-polaris-astro-3-axis-head_6375994k) | Adorama via Newegg (US, before sales tax); UK with VAT | 3-axis head, 1.5 kg, 7 kg payload, IPX6. The spec's comparison (USD 1,470) is out of date |
| [ZWO AM3N](https://us.zwoastro.com/products/am3n-harmonic-equatorial-mount) | USD 1,499 (≈ EUR 1,364; regular 1,699); USD 2,166 at [astroshop.eu](https://www.astroshop.eu/p,87038) | ZWO US store (before sales tax); EU shop with VAT | Harmonic EQ mount, about 4.1 kg, 8 kg without counterweight |
| [Asterra Z+](https://www.theasterra.com/products/asterra-z-plus) | USD 699 (≈ EUR 636) | Maker's store | Camera star tracker, 850 g, 5 kg; a different, lighter class |

**Recommended retail price: not yet.** Working figure: **EUR 1,700 before VAT (EUR 2,091 with 23 % VAT)**. That is 2.17× the component-set cost, and it holds only if the reducer quotes bring landed cost to EUR 800 or less. Why that level: it sits between the AM3N and the dealer price of a full astro mount, while carrying more than the Polaris (harmonic drives and output encoders on three axes, 7 kg). Selling at 2.0–2.5× on today's cost would put us at 2.4–3.0 times the Polaris price (EUR 2,194–2,743 against EUR 909). I recommend a final figure after the quotes, from the rebuilt cost model.

## Weight and spec budgets (estimate, pending CAD)

With component-set reducers the head alone comes to about 5.11 kg (5.14 kg after ST-313 rev D, see the stack-ups). That is within 10 g of 5.1 kg for the head, but 0.63 kg over D28's 5.1 kg with the wedge: hence Q71.

1. P1 (Phase 3 rev C): head alone 6.21 kg, wedge 0.62 kg, together 6.83 kg.
2. Q67, reducers 2.70 kg → 1.60 kg (spec 3.10): 6.21 − 1.10 = **5.11 kg** head alone; 5.11 + 0.62 = **5.73 kg** with the wedge.
3. Q68, cartridge housings in aluminium instead of printed (101 + 2 × 115 = 331 g today): plus or minus about 0.15 kg until the CAD is redrawn, because the component-set housing also replaces the reducer's own case.
4. Gap to D28 as written (5.1 kg with the wedge): 5.73 − 5.10 = 0.63 kg, which would need another redesign (thinner arm and shelf pockets, a lighter wedge).

**Budget checks for each proposed change.**

- Q67 keeps the same gear sizes and ratio, so torque margins (spec 3.3) and torsional stiffness do not change. The bought crossed-roller bearing must match the housed units' moment stiffness (spec 3.4: 6.4 × 10⁴ N·m/rad for size 17, 3.6 × 10⁴ for size 14). Otherwise the flexure term in the accuracy budget (0.59″ of the 2.19″ EQ total, spec 4.1) grows. This goes into the RFQ as a requirement.
- Q68 aluminium cartridge housings are stiffer than printed ones, so the stiffness and accuracy budgets can only improve. Moulded covers carry no load.
- Q69 sealed sockets and new gaskets change no power or accuracy figure.
- Q70 MAX-M10M-00B draws less power than the S version (u-blox: up to 9 mW less), so the power budget improves slightly.

## Tolerance stack-ups (deliverable 3)

The full report, with every contributor and its source, is `hardware/production/tolerances/stackups.md`; the script `tools/production/tolerance_stackups.py` reruns it from `params.py` (self-test 12/12). Three cases: **P1** as ordered (printed and MJF parts, CNC to ISO 2768-m), **PROD** with the D87/D88 processes but the Phase 3 geometry, and **FIX** with the changes approved on 24 Nov (D94–D99). Worst case (WC) adds every tolerance. RSS treats each tolerance as ±3σ of a normal spread. Lines marked *estimate* in the report have no published figure yet and wait for a supplier drawing or a P1 measurement.

**Method.** For a chain of contributors with nominal values nᵢ, signs sᵢ and tolerances ±tᵢ: nominal = Σ sᵢnᵢ; WC = nominal ± Σ tᵢ; RSS = nominal ± √(Σ tᵢ²). For radial offsets and angles the magnitudes add (WC = Σ tᵢ).

| Stack | Limit | P1 | Production, Phase 3 geometry | Production with D94–D99 |
| --- | --- | --- | --- | --- |
| Encoder gap, size 17 | ≥ 0.2 mm, no contact (datasheet 1.0–3.0) | 1.03 nominal; WC -0.49…2.55; RSS 0.45…1.61 | WC -0.19…2.25 | 1.50; WC 1.08…1.92: inside 1.0–3.0 |
| Encoder off-axis offset (DISP) | ≤ 0.3 mm | WC 1.61, RSS 0.59: **fail** | WC 1.18: **fail** | WC 0.32, RSS 0.11: pass (RSS) |
| Belt centre-distance range | covers belt tolerance and fitting | margin +2.15 / +0.34 mm | same | +2.55 / +0.74 mm |
| Pulley axial offset | ±0.5 mm | WC ±0.80: **fail**; RSS pass | WC ±0.65 | WC ±0.45: pass |
| Pulley angle | ≤ 0.25° | WC 0.86°: **fail** | WC 0.40°, RSS pass | WC 0.26°, RSS 0.15° |
| 60T pulley run-out | ≤ 0.03 mm TIR | 0.071: **fail** (EQ budget 2.19 → 2.22″, still < 3″) | same | 0.030: pass |
| Component-set concentricity (D87) | ≤ 0.015 mm (estimate) | – | two set-ups: **fail** | one set-up: WC 0.020, RSS 0.012 |
| V-ring azimuth VA-75 | fitted width 9.0 ± 1.2 | 6.7: **fail** | same | rev D: 9.0 (WC 8.3–9.7) |
| V-ring altitude VA-80 | 9.0 ± 1.2 | 2.5: **fail** | same | D95: narrower seal on the housing face, being chosen |
| V-ring roll VA-65 | 7.0 ± 1.0 | 6.0 (WC 5.85–6.15) | same | kept; back support added |
| Wedge dowels | head drops on by hand | H7/m6 −0.012…+0.008 mm: **fail** | same | 4 E7 hole + slot: 0.008–0.028 mm |
| Clamp seat (D20) | 45 ± 0.5 mm | pass | pass | pass |
| OLED in the bezel window | margin ≥ 0 | pass; edge rows hide past 18° (WC 4.6°) | pass | chamfer (D99): 39° (WC 18°) |
| USB-C in the bezel opening | margin ≥ 0 | WC -0.22 mm: may touch; RSS pass | same | sealed socket (D89) replaces it |
| Housing seals | squeeze 15–30 % | 1 mm flat gasket on MJF: cannot take the 0.9 mm face error | 2.5 mm cord on MJF: 8.1–37.0 % | 3.0 mm cord, 2.15 groove: 16.1–28.9 % |

**What the stack-ups found, in order of importance.**

1. **V-ring fitted widths (Phase 3 error, affects P1).** A V-ring only seals at its catalogue fitted width B1 (VA-75 and VA-80: 9.0 ± 1.2 mm; VA-65: 7.0 ± 1.0 mm). The Phase 3 geometry gives 6.7 mm on azimuth, 2.5 mm on altitude and 6.0 mm on roll. ST-303 rev D moves the azimuth shoulder down 2.3 mm (D94). On roll a 1 mm recess would put the seal into the clamp's overhang (the clamp end sits on the shelf face), so 6.0 stays: inside the window at nominal, 0.15 mm under at worst case. Rev D adds the back support the seal was missing (support diameter ≥ d1 + 0.5c = 67.5 mm). The altitude joint needs a narrower seal running on the cartridge housing face (D95, next).
2. **Wedge dowels (affects P1).** H7 holes on m6 dowels give −0.012…+0.008 mm, and two round holes must also take the ±0.3 mm pin-spacing tolerance of ISO 2768-m. Rev D has one 4 E7 round hole and one 4 E7 × 6 radial slot: 0.008–0.028 mm clearance, ≤ 175″ yaw play. Yaw on the wedge is harmless: the encoder and the pointing model take it.
3. **Encoder gap.** With the typical package height (A = A1 + A2 = 1.00 mm) the P1 gap is 1.03 mm nominal, not the 0.81 mm of D48, which used the 1.20 mm maximum. The worst case still reaches contact (−0.49 mm). The main terms are the board thickness (±0.16, because the board is located by its top face), the 80 mm tube length at ISO 2768-m (±0.3) and the printed carrier. RSS gives 0.45–1.61 mm, about 10 ppm below 0.2 mm, so P1 is fine on a bench check, as D48 planned. In production the board sits chip-side down on three pads in the CNC housing, located by two pins (D96): 1.50 mm, worst case 1.08–1.92.
4. **Encoder off-axis offset.** The datasheet allows 0.3 mm, for a 10 mm magnet; ours is 6 mm. P1 reaches 1.61 mm worst case: the carrier floats on its screws and the tube flange has up to 0.3 mm of play. Most of the resulting error is first-harmonic and the per-unit `cal.encoder` map removes it, but the production fix (pins, 28 h7/H7 flange) brings it to 0.32 mm worst case and 0.11 mm RSS.
5. **Belt and pulleys.** The adjustment range is enough in every case. P1's printed housing can misalign the pulleys (0.86° worst case against 0.25°); the CNC housings pass on RSS. The 60T pulley on an H7/g6 bore runs out up to 0.071 mm against the spec's 0.03; that only moves the EQ budget from 2.19″ to 2.22″, but a light press (D97) meets the spec.
6. **Seals.** A 1 mm flat gasket has about 0.15 mm of useful compression; MJF faces can differ by 0.9 mm over 150 mm, so low spots leak. A 3.0 mm cord in a 2.15 mm groove with hard stops stays at 15–30 % squeeze in moulded parts (D98). It needs a local flange about 6 mm wide around each joint; that goes into the moulding revisions.

**Budget checks.** No change touches the torque, power or stiffness budgets. Accuracy: D97 brings the belt term back to 0.20″ (EQ total 2.18″). Weight: ST-313 rev D is 28 g heavier (149 → 177 g), so the D87 estimate goes from 5.11 to about **5.14 kg** for the head alone, 0.04 kg over D91. The CNC-housing redesign (deliverable 2) must find that back. **Customer-handled parts (D13):** none of D94–D99 changes how the customer swaps the pack, a cartridge or the covers; with D98 the cord stays in its groove when a cover comes off.

## Numbers pending P1

Eighteen numbers in this phase wait on Phase 7. Each row says which measurement or order fills it and what it changes here.

| # | Number waiting | Filled by | What it sets in Phase 8 |
| --- | --- | --- | --- |
| 1 | Reducer periodic error and repeatability | P0 M3 (T2) | Reducer RFQ acceptance limit; Q67 decision at the P2 gate |
| 2 | Backlash and lost motion | P0 M4 (T1) | Reducer acceptance limit; end-of-line lost-motion check |
| 3 | Encoder noise at the 0.8 mm gap | P0 M1 (D48) | Whether the production carriers move the encoder board |
| 4 | Encoder linearity | P0 M2 | Magnet and tube tolerances in the stack-up (S1/S2 estimates) |
| 5 | Encoder map residual | P0 M5 | End-of-line calibration pass limit |
| 6 | PEC residual | P0 M6 (T3) | End-of-line PEC baseline limit |
| 7 | Slew current and StallGuard, warm and at −20 °C | P0 M7 (T6) | End-of-line current and StallGuard thresholds; motor on altitude and roll |
| 8 | Motor and driver temperatures | P0 M8 | Cover material near the motors |
| 9 | Power per mode | P0 M9 (T9) | End-of-line current limits; pack test limits |
| 10 | Runtime on the pack | P1 (T9) | Pack spec for the assembler |
| 11 | Stiffness and settling | P1 (T7) | Housing material and wall thickness (Q68) |
| 12 | Tracking RMS, EQ and alt-az | P1 (T4) | Short tracking test limit at end of line |
| 13 | Go-to accuracy | P1 (T5) | Pointing check, if one is added to the end-of-line test |
| 14 | Power-off holding | P1 (T8) | Bumper and park settings |
| 15 | Internal temperature at 40 °C | P1 (T10) | Moulded cover material |
| 16 | Assembly time per step | P1 build | Labour cost per head and the station plan |
| 17 | Real CNC, MJF and board prices | P0 and P1 orders | Calibrates every estimate in the cost model |
| 18 | Laifual input-side drawing | Laifual reply (D85) | ST-205 and the cartridge housings in the CAD revision |

IPX4 (T12) is a P2 test by plan, so it is not on this list.

## State of the deliverables, and next steps

The repo is attached and the CAD generator runs here (build123d 0.13, Phase 3 checks reproduced), so nothing is blocked on access any more. Phase 7's orders still come first: Phase 8 must not hold them up.

| Deliverable (brief) | State | Waiting on |
| --- | --- | --- |
| 1 Process per part | Done (section 3, D88) | — |
| 2 DFM revisions, STEP, A4 drawings with GD&T | Not started | Reducer drawings (RFQ, D87), Laifual drawing (D85) |
| 3 Tolerance stack-ups | Done (section "Tolerance stack-ups", D93–D99); rerun when the reducer drawings arrive | Altitude seal choice (D95) |
| 4 Production board revisions | Sourcing plan done (D90); sealed USB-C (D89) not started | Sealed socket choice |
| 5 Reducer and bought-part quotes | Prices found, RFQ text ready (section 5) | Suppliers' replies |
| 6 RFQ folders and quote guides | Folders made; reducer and pack packages written | CAD revisions for the made parts |
| 7 Tooling and fixtures (ST-9xx) | Not started | CAD revisions |
| 8 Assembly line, end-of-line test, factory-test firmware | Not started | Limits pending P1 |
| 9 Pack production | Assemblers found, RFQ written | Quotes |
| 10 Packaging | Not started | — |
| 11 Production parts list and retail price | Preliminary (section 6) | Quotes |
| 12 P2 pilot plan | Not started | P1 report |
| 13 Phase 8 report | This doc is its first instalment | All of the above |

**For you, in this order:**

- [x] Fix GitHub access (done 24 Nov).
- [x] Answer Q67–Q72 (approved 24 Nov: D87–D92).
- [x] Answer Q73–Q76 (approved 24 Nov: D93–D99).
- [ ] Carry on with the Phase 7 wave-1 orders: TPS25751DREFR first, then the Laifual quote. ST-303 for P0 goes in as drawn (D93); for P1 order `hardware/fab/cnc/ST-303.step` + `.pdf` rev D and ST-313 rev D.
- [ ] When you send the Laifual message, also send the production RFQ text from section 5 to Laifual and the other five makers.

**For me (repo attached 24 Nov):** branch `phase-8-production` made from the Phase 7 branch; brief already in `docs/prompts/phase-8-prompt.md`; progress in `hardware/production/PROGRESS.md`; RFQ folders made; tolerance stack-ups done (D93–D99); next the altitude seal (D95), the sealed USB-C choice for ST-501, the production parts list (Sheet + CSV), then the CAD revisions as the reducer drawings arrive.

## Sources

Pages read on 24 Nov 2026. USD converted at the spec's USD 1 = EUR 0.91. Project inputs: spec rev C (sections 3, 4, 8, 9), Phase 3 rev C (parts and masses), Phase 4 (cost model), Phase 7 (order state and findings), decisions log D1–D92.

- Market: [Benro Polaris Astro, Newegg/Adorama](https://www.newegg.com/p/0FY-002Z-003T1); [Park Cameras](https://www.parkcameras.com/shop/benro-polaris-astro-3-axis-head_6375994k); [ZWO AM3N, ZWO US store](https://us.zwoastro.com/products/am3n-harmonic-equatorial-mount); [ZWO AM3N, astroshop.eu](https://www.astroshop.eu/p,87038); [Asterra Z+](https://www.theasterra.com/products/asterra-z-plus)
- Reducers: [Laifual LSS tiers](https://www.alibaba.com/product-detail/High-precision-Laifual-Harmonic-reducer-for_62499927002.html); [Laifual store](https://zjlaifual.en.alibaba.com/); [Laifual LSG](https://www.alibaba.com/product-detail/Laifual-high-torque-LSG-series-harmonic_62022131184.html); [Goldgun](https://www.alibaba.com/product-detail/LFS-Harmonic-Motor-Drive-Gearbox-High_1600968013163.html?s=p); [Leaderdrive LHS-17 surplus](https://www.ebay.com/itm/204610445897); [Honpine LHSG-RDP](https://www.directindustry.com/prod/suzhou-honpine-precision-industry-co-ltd/product-4614476-2802388.html); [KOFON KC-MC](https://www.directindustry.com/prod/kofon-motion-group/product-181579-2483233.html); [Hansheng CSF-17-I](https://www.directindustry.com/prod/hansheng-automation-dongguan-co-ltd/product-4605437-2740892.html)
- Chips: [LCSC TPS25751DREFR C30169739](https://www.lcsc.com/product-detail/C30169739.html); [TI TPS25751DREFR](https://www.ti.com/product/TPS25751/part-details/TPS25751DREFR); [DigiKey TPS25751DREFR](https://www.digikey.co.uk/en/products/detail/texas-instruments/TPS25751DREFR/23028775); [SnapMagic stock table](https://www.snapeda.com/parts/TPS25751DREFR/Texas%20Instruments/view-part/); [TI FAQ, TPS25750 to TPS25751](https://e2e.ti.com/f/1/t/1346998); [DigiKey MAX-M10S-00B](https://www.digikey.ca/en/products/detail/u-blox/MAX-M10S-00B/15712909); [DigiKey MAX-M10 series](https://www.digikey.com/en/product-highlight/u/u-blox/max-m10-series); [Future Electronics MAX-M10S-00B](https://www.futureelectronics.com/p/semiconductors--wireless-rf--rf-modules-solutions--gps/max-m10s-00b-u-blox-8161892); [JLCPCB RV-3028-C7 C3019759](https://jlcpcb.com/partdetail/C3019759); [DigiKey RV-3028-C7 QC](https://www.digikey.com/en/products/detail/micro-crystal-ag/RV-3028-C7-32-768KHZ-1PPM-TA-QC/10431070); [DigiKey RV-3028-C7 QA](https://www.digikey.ca/en/products/detail/micro-crystal-ag/RV-3028-C7-32-768KHZ-1PPM-TA-QA/10499248)
- Cells and packs: [NKON P50B](https://www.nkon.nl/novat/rechargeable/molicel-inr21700-p50b-5000mah-50a.html); [18650 Battery Store P50B](https://www.18650batterystore.com/products/molicel-21700-p50b-5000mah-50a-battery?qv=B71cH3x1S); [CM Batteries 2S2P pack](https://cmbatteries.com/?p=21097); [Shenzhen First Power](https://ejfirstpower.en.alibaba.com/videoshow.html?d_type=cv); [Aceon pack assembly](https://www.aceongroup.com/custom-battery-packs/battery-pack-manufacturing/battery-pack-assembly/)
- Moulding cost bands: [LANPDT, low-volume moulding](https://lanpdt.com/low-volume-injection-molding-cost/); [enclosure tooling range](https://dev.to/china-sourcing-agents/injection-mold-tooling-costs-for-electronics-enclosures-16dl)
- Tolerance stack-ups: [MT6835 datasheet rev 1.3](https://cdn.promelec.ru/upload/items/2026/01/26/magntek~mt6835gt-std.pdf) (air gap, DISP, TSSOP-16 heights); [Protolabs Network standards, ISO 2768](https://hubs.com/manufacturing-standards); [Protolabs precision machining](https://www.protolabs.com/en-gb/resources/design-tips/fine-tuning-tolerances-for-cnc-machined-parts/); [JLC3DP capabilities (MJF)](https://jlc3dp.com/capabilities/3d-printing-service); [JLC3DP FDM/MJF accuracy](https://jlc3dp.com/blog/mjf-vs-fdm); [Protolabs moulding tolerances](https://www.protolabs.com/resources/blog/understanding-injection-molding-tolerances/); [JLCPCB thickness tolerance](https://jlcpcb.com/capabilities/Capabilities); [Hennlich V-ring tables](https://shop.hennlich.at/media/0a/3e/fc/1730191856/V-Ringe_2017.pdf_6720a1f084df1.pdf); [NAK VA80](https://simplybearings.co.uk/shop/p20725228/NAK-VA80-FKM-Rubber-V-Ring-Seal-For-Shafts-78-83mm/product_info.html); [V-ring installation guide (support diameter)](https://www.seals-shop.com/content/medias/installation_guides/en/IG_V%20Rings_EN.pdf); [Marco O-ring gland guide](https://www.marcorubber.com/assets/site/userAssets/file/O-Ring_Gland_General_Design_Considerations02.pdf); [Global O-Ring on Parker ORD 5700](https://www.globaloring.com/blog/o-ring-groove-design-calculator-engineering-the-right-gland-geometry-the-first-time/); [Fenner belt alignment](https://issuu.com/eriksuk/docs/fenner_ddmm_synchronous_belts/s/14967538); [Pfeifer belt misalignment](https://www.pfeiferindustries.com/information.php?info_id=51); [DisplayModule DM-OLED13-637](https://cdn.shopify.com/s/files/1/0264/7629/files/DM-OLED13-637_Datasheet.pdf); [Tailor Pixels TOJMD013C](https://pdf.directindustry.com/pdf/tailor-pixels-technology-co-ltd/product-specification-model-tojmd013c-13-oled-arduino-display-module-128-64/245050-1023033.html). Read 24 Nov 2026.
