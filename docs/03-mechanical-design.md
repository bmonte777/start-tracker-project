# Phase 3 — Mechanical Design

Rev C · 22 Nov 2026 · Bruno

## Summary

The P1 head is fully modelled: 89 placed parts, no clashes at home or across 0–75° of wedge tilt, and every made part has a STEP, a drawing and (if printed) a print-oriented STL. Revision C makes the wedge removable (D39) and checks the design against five generic payloads instead of one lens (D40), so it holds for a small mirrorless kit up to a 7 kg refractor.

| Item | Result |
| --- | --- |
| Mass, head alone (alt-az, wedge left at home) | **6.21 kg** |
| Mass, head on its wedge (EQ) | **6.83 kg** (wedge 0.62 kg) |
| Payloads checked | 5 envelopes, 1.55 to 7.0 kg (P1–P5), all balance on the altitude axis |
| Made parts drawn | 34 (A4, ISO first angle, rev C), one combined 35-page set with index |
| CNC parts | 10 designs, 14 pieces per head, about USD 587 (€534) for one set |
| MJF parts (JLC3DP) | Body and tower, 368 g, about USD 101 (€92) |
| Printed parts (own H2S) | 6 plates, 727 g filament, 44.4 h |
| Nearest camera gap over the altitude swing | 13.5 mm (P3 at +95°); 17–29.5 mm for the others |
| Roll travel | +8° to +15° toward the tower, −130° to −175° away, set per payload |
| 48 mm azimuth motor | fits; 1.6 mm to the altitude cartridge housing |
| Materials per head | €1,894.81 at 1 · €1,320.26 at 100 · €976.10 at 1,000 |

Decisions taken in Phase 3:

| # | Decision |
| --- | --- |
| D33 | Motor rail 16 V (Q16) |
| D34 | Roll axis 23 mm further out, X 135.5 (Q17) |
| D35 | Weight changes to reach about 6.8 kg (Q21) |
| D36 | Arca clamp fixed by one 3/8"-16 coin-slot screw, an exception to D13 (Q18) |
| D37 | Roll shelf overhang 30 mm instead of 75 mm (Q19) |
| D38 | Raised-hinge wedge, arcs below, two clamp knobs, M3 tangent screw at 55′ per turn (Q20) |
| D39 | Removable wedge: the head stands on any tripod by itself; on two dowels and one coin screw on the wedge |
| D40 | Five payload envelopes (P1–P5) replace the single reference lens; roll limits set per payload |
| D41 | No further weight cutting: P1 stays at 6.21 kg (head) and 6.83 kg (with wedge) |

Bruno confirmed the five payload envelopes cover almost all gear (D40), and the weight stays as it is (D41). Nothing in Phase 3 is open.

## Layout and frames

The head stacks five stages on one vertical azimuth axis: ground, wedge, azimuth, altitude and roll. All dimensions below are from the world origin, which sits on the azimuth axis at the top face of the tripod plate with the wedge fitted, with Z up, the payload on +X and the lens pointing +Y at altitude 0. Without the wedge the head stands 30 mm lower: its own base (Z 30) is then the tripod top.

![Three-quarter view with payload P3, exploded view, the head on a tripod without its wedge, the 7 kg refractor P5, camera swing at +85 degrees and roll limits](img/03-renders-sheet.png)

| Stage | Turns about | Pivot (mm) | Range |
| --- | --- | --- | --- |
| Wedge (latitude) | Y | X −62, Z 37 | 0–75° tilt (latitude 90° down to 15°) |
| Azimuth | Z | X 0, Y 0 | unlimited, no slip ring (D19) |
| Altitude | X | Z 225 | −15° to +100° (TPU bumpers) |
| Roll | Y | X 135.5, Z 145 | per payload: +8° to +15° toward the tower, −130° to −175° away |

Key heights: wedge top plate Z 22–30, head base plate Z 30–45 (the azimuth reducer output face sits on it at Z 45), body Z 46.5–125, Arca clamp top Z 190 (45 mm above the roll axis, D20).

Changes from the Phase 2 spec, all forced by the clash checks:

- Body is taller: the altitude axis now sits 100 mm above the body top instead of 120 mm.
- Body front radius is 64 mm; tower footprint is X −76 to 42.5, Y −52 to 85.
- Roll axis moved 23 mm outward (X 112.5 to 135.5) for D31 roll travel (D34).
- Roll cartridge rotated 20° about its axis so its motor clears the body when the arm swings.
- A printed roll enclosure (ST-217) was added so the roll cartridge meets IPX4 like the other two.
- The wedge hinge was raised and the latitude arcs now hang below it (D38).
- The wedge comes off (D39): the head keeps its own base plate with a 3/8"-16 socket.

## Parts

We make 34 different parts: 10 in aluminium, 2 in MJF PA12 from JLC3DP and 22 printed on the H2S. Each has a STEP file, an A4 drawing with title block, ISO 2768-m general tolerance and its fits, and a features table that locates every hole from the drawing datum O. Masses are calculated from the CAD (FDM parts: walls plus infill; MJF parts solid at 1.01 g/cm³).

| Part | Name | Process, material | Qty | Mass each (g) |
| --- | --- | --- | --- | --- |
| ST-207 | Motor plate with belt-tension block | CNC, 6061-T6 | 3 | 26 |
| ST-208 | Encoder reference tube, size 17 | Turned, 6061 (D35) | 2 | 15 |
| ST-215 | Encoder reference tube, size 14 | Turned, 6061 (D35) | 1 | 14 |
| ST-301 | Base plate with 3/8"-16 socket | CNC, 6061-T6 | 1 | 96 |
| ST-302 | Wedge lower plate with azimuth fine adjust, ribbed pockets | CNC, 6061-T6 | 1 | 245 |
| ST-303 | Head base plate: azimuth reducer mount, 3/8"-16 tripod socket, lightening ring (D39) | CNC, 6061-T6 | 1 | 132 |
| ST-331 | Wedge top plate: hinge knuckle, arcs, two dowels, ribbed pockets (D39) | CNC, 6061-T6 | 1 | 126 |
| ST-305 | Wedge latitude arc | CNC, 6061-T6 | 2 | 10 |
| ST-312 | Altitude arm | CNC, 6061-T6 | 1 | 250 |
| ST-313 | Roll shelf (L-arm) with clamp seat | CNC, 6061-T6 | 1 | 150 |
| ST-310 | Azimuth body (main housing), 2.0 mm walls | MJF PA12, JLC3DP | 1 | 184 |
| ST-311 | Tower (altitude housing), 2.0 mm walls | MJF PA12, JLC3DP | 1 | 184 |
| ST-210 | Cartridge housing, size 14 (roll) | Printed, PAHT-CF | 1 | 101 |
| ST-211 | Cartridge housing, size 17 (azimuth, altitude) | Printed, PAHT-CF | 2 | 115 |
| ST-212 / 216 | Cartridge rear cover and encoder-board carrier | Printed, ASA | 2 + 1 | 7 |
| ST-217 | Roll cartridge enclosure | Printed, ASA | 1 | 111 |
| ST-315 | Front bezel with OLED window | Printed, ASA | 1 | 24 |
| ST-317 / 318 | Battery bay tray / battery door with snap latch | Printed, ASA | 1 + 1 | 17 / 15 |
| ST-319 | Top cover with GNSS window | Printed, ASA | 1 | 26 |
| ST-605 / 612 | Pack shell, lower / upper half | Printed, ASA | 1 + 1 | 30 / 32 |
| ST-606 | Cell holder (end) | Printed, ASA | 2 | 2 |
| ST-611 | Pack light pipe and button | Printed, PETG | 1 | 3 |
| ST-316, 320, 322 | Button caps, cable guides, end-stop bumpers | Printed, TPU 95A | 4, 3, 2 | 1–2 |
| ST-323–325, 327, 328, 610 | Gaskets: body/tower, top cover, door, bezel, roll enclosure, pack | Printed, TPU 95A | 1 each | 1–3 |

The main bought parts are the three Laifual hollow harmonic units (two size 17, one size 14), three NEMA 17 steppers (48 mm on azimuth, D32), GT2 20T/60T pulleys and 200 mm belts, a 60 mm Arca clamp, four Molicel P50B cells, an 8 h6 hinge pin, two 3/8"-16 bushings, two 4 mm dowels, V-rings and an O-ring. The full list, down to every screw, is in the parts list section. Bought parts are modelled as envelopes from the datasheet dimensions (reducer outline and bolt circles, NEMA 17 frame, pulley and clamp sizes); the makers' own STEP files could not be downloaded from the build workspace, so swap them in under `hardware/cad/step/bought/` when you download them.

## Checks

Every check runs automatically on the exact solids (OpenCascade distance and boolean tests), and all of them pass. The head checks run once; the payload checks run for each of the five envelopes (next section). Results are written to `hardware/cad/out/checks.json` on every build.

| Check | How | Result |
| --- | --- | --- |
| Interference at home | All 89 parts and payload P3 against each other | No overlaps |
| Wedge tilt | 0°, 30°, 60°, 75° | No overlaps |
| Altitude arm swing | −15° to +100° | 1.0 mm running gap to the tower face; touches the TPU bumpers at −15° and +100° |
| 48 mm azimuth motor | Distance to everything outside its cartridge | 1.6 mm to the altitude cartridge housing, 3.2 mm to body and tower; motor top Z 170 |
| Camera swing, each payload | Altitude −10° to +95° | Nearest gap 13.5 mm (P3 at +95°, camera to azimuth body); the others 17.0–29.5 mm |
| Roll travel, each payload | Step until contact, at altitude 0° and 45° | Limits in the payload table; every stop leaves at least 0.9 mm before contact |
| Tripod clearance, each payload | Lowest point of the payload over the altitude swing and the roll travel, with and without the wedge | In the payload table; the firmware uses these as soft limits |

The firmware soft limits have to use the tripod plane as well as the head: long payloads reach below the tripod top at high altitude or far roll, and they reach it sooner when the wedge is left at home, because the head then stands 30 mm lower.

## Payload envelopes

The tracker is meant for many kits, not one lens, so revision C checks five generic payloads that span the range the spec allows (D4: up to 7 kg). Each one is a simple envelope (tube, camera body and its mounting), built from published sizes of typical gear, and the model balances each on the altitude axis by sliding its foot, plate or dovetail in the clamp, as far as the clamp jaws still hold it. Refractors on a dovetail are balanced by sliding the tube in its rings; the bar itself stays with its rear end flush with the clamp's rear jaw so it never reaches back over the roll cartridge.

![Payload P5, a 90 mm refractor at the full 7 kg, balanced on the head](img/03-payload-p5.png)

| Payload | What it stands for | Total (kg) | Tube Ø × length (mm) | Mounting |
| --- | --- | --- | --- | --- |
| P1 | Mirrorless body with a standard zoom | 1.55 | 88 × 120 | L-plate under the body |
| P2 | Mirrorless with a 70-200 f/2.8 (Sony GM II class: Ø88 × 200, 1.05 kg) | 1.95 | 88 × 200 | Collar foot, 80 mm |
| P3 | Mirrorless with a 150-600 class zoom (Sigma 150-600 S: Ø121 × 290, 2.86 kg) | 3.75 | 121 × 320 | Lens foot, 100 mm |
| P4 | 72 mm ED refractor with an astro camera (Evostar 72ED class: 1.96 kg) | 2.70 | 95 × 420 | Dovetail, 200 mm |
| P5 | 90 mm refractor at the full rating (FLT91 class: 121 mm dew shield, 4.17 kg tube) | 7.00 | 121 × 510 | Dovetail, 250 mm |

Results for each, from the CAD:

| Payload | Nearest gap over the altitude swing | Roll toward tower / away (alt 0°) | Altitude out of balance | Roll torque at 90° |
| --- | --- | --- | --- | --- |
| P1 | 29.5 mm (camera to altitude reducer) | +9° / −175° | 1.12 N·m (CG 34 mm below the axis) | 1.55 N·m |
| P2 | 17.0 mm at +85° (camera to azimuth body) | +9° / −130° | 0.96 N·m (foot at the end of the clamp, 0.56 N·m left along the tube) | 2.22 N·m |
| P3 | 13.5 mm at +95° (camera to azimuth body) | +8° / −150° | 0.58 N·m | 4.98 N·m |
| P4 | 27.5 mm at +95° (tube to azimuth body) | +15° / −150° | 0.40 N·m | 3.18 N·m |
| P5 | 18.2 mm at +95° (tube to azimuth body) | +8° / −155° | 2.66 N·m (CG 31 mm above the axis) | 9.61 N·m |

The altitude hold with the power off is 8.1 N·m, so every payload stays put in altitude (P5 with a margin of 3.0). The roll hold is 6.6 N·m: P1 to P4 stay put at any roll angle, but P5 only within ±43° of level, so the firmware parks roll at 0° before it powers down and at the low-battery park.

Where the payload goes below the tripod top (the firmware's tripod limit):

| Payload | Lowest point over the altitude swing, wedge on / off | Roll angle where it passes the tripod top, alt 0°, wedge on / off | Same at alt 45° |
| --- | --- | --- | --- |
| P1 | 174 / 144 mm above | −135° / −110° | never / never |
| P2 | 129 / 99 mm above | −125° / −110° | −130° / −105° |
| P3 | 69 / 39 mm above | −120° / −105° | −100° / −80° |
| P4 | 8 mm above / 22 mm below (from about +68°) | −145° / −125° | −85° / −65° |
| P5 | 96 / 126 mm below (from about +50° / +41°) | −130° / −115° | −35° / at 0° |

P4 without the wedge and P5 in both cases hang below the tripod top near the zenith. Whether that touches a leg depends on the tripod and the azimuth, so the app should ask once whether a pier extension is fitted; without one, it caps altitude at the angle in the table.

## Mass and centre of gravity

The head alone weighs **6.21 kg**; on its wedge the mount weighs **6.83 kg**. The wedge (base, lower plate, top plate, arcs, hinge pin, knobs and their screws) is 0.62 kg, and making it removable cost about 30 g over rev B's 6.80 kg: the second 3/8"-16 bushing, two dowels, the coin screw and slightly larger encoder-tube flanges, against 6 g saved on the two plates.

| Group | Spec 3.10 (kg) | Rev A (kg) | Rev B (kg) | Rev C (kg) |
| --- | --- | --- | --- | --- |
| Reducers | 2.70 | 2.71 | 2.71 | 2.71 |
| Stepper motors | 0.95 | 0.95 | 0.95 | 0.95 |
| Pulleys and belts | 0.14 | 0.12 | 0.12 | 0.12 |
| Battery pack | 0.34 | 0.38 | 0.38 | 0.38 |
| Electronics and harness | 0.17 | 0.13 | 0.13 | 0.13 |
| Housings and covers (printed, MJF) | 0.56 | 1.07 | 0.92 | 0.92 |
| Aluminium parts and clamp | 1.08 | 1.36 | 1.23 | 1.22 |
| Encoder tubes and magnets | — | 0.10 | 0.04 | 0.04 |
| Fasteners, inserts, dowels, seals | 0.15 | 0.38 | 0.33 | 0.35 |
| **Total with the wedge** | **6.09** | **7.21** | **6.80** | **6.83** |
| **Head alone** | — | — | — | **6.21** |

What D35 changed, with the saving measured on the CAD:

| Change | Saving (g) |
| --- | --- |
| W1 + W2: body and tower in MJF PA12 with 2.0 mm walls (255 + 263 g → 184 + 184 g) | 150 |
| W3: ribbed pockets under the wedge plates, 2 mm skin (ST-302 304 → 245 g; the old upper plate 275 → 263 g) | 71 |
| W4: encoder tubes in 6061 instead of 304 (34 / 32 g → 12 / 11 g; 15 / 14 g in rev C with the wider flange) | 66 |
| W5: Sunwayfoto DDC-60i clamp, 71 g instead of 120 g (the shelf seat rises 2 mm so the clamp top stays 45 mm above the roll axis, D20) | 49 |
| 7075 aluminium screws for the 32 reducer-to-housing joints (0.6 N·m, into inserts) | 53 |
| Deeper pocket under the base (ST-301) and a pocket under the shelf leg (ST-313), net of the 2 mm higher seat | 16 |
| **Total** | **405** |

The cartridge housings stay PAHT-CF on purpose: the reducer's reaction torque goes through them, and MJF PA12 is about 2.5× less stiff, which would add about 20″ of azimuth wind-up for a 45 g saving. The body and tower in MJF PA12 tilt about 27″ under the full altitude load (PAHT-CF: about 9″); that sag is repeatable and the pointing model removes it.

Fasteners come from the joint table: 162 stainless screws, 32 aluminium screws, 5 thumb screws, 2 coin screws, 2 dowels, 16 washers and 93 brass inserts make 0.32 kg; seals add 0.03 kg. Of these, 0.07 kg leave with the wedge.

Centre of gravity of the head on its wedge (no payload): X 22.1, Y −7.0, Z 128.0 mm. With payload P3, everything that turns in altitude (5.54 kg) has its centre 10.7 mm above the altitude axis (0.58 N·m), and the roll stage plus payload (3.99 kg) sits 129 mm from the roll axis, as D20 intends. The other payloads are in the table above.

Further savings that were looked at and not taken (D41):

| Option | Saving | Cost |
| --- | --- | --- |
| Titanium screws for the rest | about 0.10 kg | about €100–150 per head |
| Battery 2S1P instead of 2S2P | 0.14 kg | half the runtime (36 Wh) |
| Pocketed arm and shelf | about 0.1 kg | more machining time |
| Size 14 reducer on azimuth | about 0.3 kg | lower EQ-mode payload (to be calculated); reverses D17 |

## Design studies

### Roll clearance (D31, Q17)

With the Phase 2 layout the roll stage could not turn toward the tower at all, and the camera hit the body from about +75° altitude. Two fixes were modelled.

| Option | Roll toward the tower | Cost |
| --- | --- | --- |
| A: roll axis 23 mm further out (X 135.5) | +10° (travel +10° to −145°, 155° in all) | Worst-case azimuth torque rises to 19.45 N·m, still 2.0× under the size-17 average-torque limit of 39 N·m; typical load +20 % (4.92 N·m) |
| B: raise the roll axis | about +38° | Altitude out of balance by 4.08 N·m with the reference rig and 8.93 N·m at 7 kg, so the power-off hold margin drops below 1 at 7 kg |

Option A keeps finding 5 of the spec (the camera stays put with power off) and gives the same 155° that D31 accepted, shifted 5° toward the useful side. Bruno approved it as D34. (This study used the FE 200-600 as the reference lens; revision C replaced it with the five payload envelopes, whose limits are in the payload table.)

### Removable wedge (D39)

![The head standing on a tripod without its wedge, with payload P1](img/03-no-wedge.png)

For alt-az nights the wedge stays at home and the head screws straight onto any tripod or levelling base, which saves 0.62 kg to carry. The interface:

- **On the head:** the head base plate ST-303, a Ø75 aluminium disc (Z 30–45) that carries the azimuth reducer output and the VA-75 V-ring. A 3/8"-16 stainless bushing (ST-307) is pressed into its centre with Loctite 638, so a standard tripod screw holds the head directly. Two Ø4 H7 holes at R33 take the wedge dowels; a ring pocket underneath keeps the plate to 132 g.
- **On the wedge:** the top plate ST-331 (Z 22–30) carries the hinge knuckle, the two latitude arcs and two Ø4 m6 dowels (ST-333) pressed in 4 mm proud. They locate the head and take the azimuth reaction torque, so the screw only clamps.
- **Fixing:** one 3/8"-16 × 10 coin-slot screw (ST-332) from below the top plate into the head's bushing, the same thread and coin as the clamp screw (D36). Tilt the wedge to 45° to reach it.

Swapping takes about a minute and needs only a coin. The dowels put the head back on the wedge within the H7/m6 fit: at most 0.008 mm of play at R33, about 50″ in azimuth, and polar alignment is redone at every set-up anyway. Without the wedge the head stands 30 mm lower, which the firmware's tripod limits allow for (payload table).

### Cable path and altitude twist

No wire crosses the azimuth axis (D19): battery, both boards and the azimuth motor ride above the azimuth bearing. The 15-wire roll harness runs from the body through the tower, enters the altitude encoder tube (ST-208) and leaves through an 8 mm hole in the arm hub. Over the −10° to +95° soft range it twists ±52.5° along the 82 mm tube, which a loose bundle takes without a service loop (recommended for the Phase 4 harness: fine PTFE-insulated wire). TPU cable guides (ST-320) hold the bundle on the body, the tower and the arm, and the roll motor sits on the arm side, so no wire crosses the roll axis either.

### Sealing to IPX4 (D9)

- Rotating joints: NBR V-rings VA-75 (azimuth, on the Ø75 rim of ST-303), VA-80 (altitude, on the arm spigot) and VA-65 (roll).
- Static joints: 1 mm TPU gaskets printed to shape at body/tower, top cover, battery door, bezel, roll enclosure and battery pack; an 80 × 2 O-ring in a groove on the roll enclosure.
- Water path: the body has a drip skirt, all joints face down or sideways, and the bezel window is a bonded 1 mm polycarbonate sheet.

### Battery and board mounts

The battery is fully tool-free: the door snaps open, the pack slides into its tray and mates on a 5-way blade connector, and the pack's own LEDs show the charge. The pack is closed with 4 screws that the user never opens. Boards are not tool-free on purpose: each encoder board must stay within 0.1 mm of its magnet, so it is held by two M3 button screws (2 mm key), and the mainboard by four. A cartridge swap is 4 + 4 screws and one plug (D13); the azimuth cartridge first needs the head lifted off the wedge (one coin screw, D39).

Board outlines and fixings, fixed as inputs for Phase 4:

| Board | Outline (mm) | Fixing | Where |
| --- | --- | --- | --- |
| Mainboard ST-501 | 100 × 60 × 1.6, parts up to 12 high | 4 × M3, holes 4 mm in from each corner | On bosses behind the front bezel (ST-315) |
| Cartridge board ST-520 (×3) | Round Ø30 × 1.6 | 2 × M3 on PCD 23 | On the rear carrier, MT6835 on the underside, 2.0 mm above the magnet face |
| Battery board ST-602 | 32 × 40 × 1.6 | Clamped at the pack end; screw-free fixing detailed with the board in Phase 4 | +Y end of the pack, LEDs facing the light pipe (ST-611) |

Each cartridge has one plug to the head: a JST-GH 15-way socket on the cartridge board, reached through a window in the rear carrier. The motor lead plugs into the same board through a second, smaller window, so it stays inside the cartridge.

### Belt tension

Each motor sits on a plate (ST-207) that slides on the cartridge walls. One M3 × 12 screw in the tension block pushes it until each span carries 14 N, then four M3 button screws with washers lock it. Check it either way: pluck the span and read about 290 Hz on a phone tuner app, or press the middle of the 57 mm span with 2 N (a 200 g weight) and see about 2 mm of deflection.

## Parts list and cost

The parts list has 131 lines and goes down to the last screw, washer and insert. Rev C adds the wedge interface (ST-331, ST-332, ST-333 and a second ST-307): about €41 more for one prototype, €11 more at 1,000.

| Per head (€) | 1 unit | 100 units | 1,000 units |
| --- | --- | --- | --- |
| Materials, Phase 2 (rev C) | 1,829 | 1,289 | 962 |
| Materials, Phase 3 rev A | 1,765 | 1,289 | 958 |
| Materials, Phase 3 rev B | 1,854 | 1,302 | 965 |
| Materials, Phase 3 rev C | 1,895 | 1,320 | 976 |
| Cost of goods, rev C | 2,122 | 1,465 | 1,060 |

The Phase 2 lines keep their cited prices; the Phase 3 lines (screws, inserts, knobs, seals, gaskets) are priced from one cited pack price per family (bolts.co.uk M3 × 10 A2, 200 pcs; Ruthex via 3DJake; Fastener Express 7075 M3, 50 pcs USD 36.95) and scaled by size, marked "est (pack)". Landed cost at 1,000 units is €1,105 (rev B €1,093), and the reducers are still 41–57 % of materials. The retail band at 2.5–3.5× landed is €2,760–3,870.

What changed in the list:

- New lines: ST-215–219 (roll tube, roll carrier, roll enclosure, V-rings VA-80 and VA-65), ST-308/309 wedge knobs and tangent screw, ST-323–330 (gaskets, window, O-ring, clamp screw), ST-612 pack upper half.
- Fasteners as their own lines: ST-710–741 (19 screw sizes, 194 pieces; ST-716/717 in 7075 aluminium), ST-750–752 washers, ST-760–762 Ruthex inserts (75 M3, 12 M4, 6 M5).
- D13 is met: only M3, M4 and M5, all driven by 2, 2.5 or 3 mm keys. M5 is always ISO 7380 (a 3 mm key) because ISO 4762 M5 needs 4 mm, and the 20T pulley uses M4 set screws because M3 grub screws need 1.5 mm. The exceptions are the two 3/8"-16 coin-slot screws, for the clamp (D36) and the wedge (D39), both turned with a coin.
- Rev B: ST-310/311 MJF PA12, ST-208/215 6061, ST-314 Sunwayfoto DDC-60i, ST-716/717 aluminium 7075. ST-509 is the 16 V boost converter (D33).
- Rev C (D39): ST-303 is now the head base plate, ST-331 the new wedge top plate, ST-332 the wedge coin screw, ST-333 two dowels; ST-307 quantity 2.
- ST-701–707 (Phase 2 allowances) stay in the list at quantity 0 so their history is kept.

Files: `hardware/bom/master-parts-list.csv`, `docs/calc/bom_data.py` (the cost model reads it and still runs) and the shared [parts list Sheet](https://claude.ai/artifact/9T9Gpvm2vWPRYqJtPChJa8).

## Fabrication package

Everything needed to order and print one head is in `hardware/fab/`: CNC files with a quote estimate, the two MJF parts for JLC3DP, six ready plates for the H2S, and a shopping list with links.

### CNC (JLCCNC, D29)

Upload the STEP and PDF pairs from `hardware/fab/cnc/`. The drawing carries the fits, finish and tolerance; the STEP is the master geometry.

| Part | Qty | Finish | Est. USD each | Est. USD line |
| --- | --- | --- | --- | --- |
| ST-312 Altitude arm | 1 | Bead-blast, clear anodise | 118 | 118 |
| ST-302 Wedge lower plate | 1 | Bead-blast, clear anodise | 80 | 80 |
| ST-207 Motor plate | 3 | Bead-blast, clear anodise | 26 | 78 |
| ST-331 Wedge top plate | 1 | Bead-blast, clear anodise | 70 | 70 |
| ST-313 Roll shelf | 1 | Bead-blast, clear anodise | 66 | 66 |
| ST-305 Latitude arc | 2 | Bead-blast, clear anodise | 28 | 56 |
| ST-303 Head base plate | 1 | Bead-blast, clear anodise | 48 | 48 |
| ST-301 Base plate | 1 | Bead-blast, clear anodise | 36 | 36 |
| ST-208 Encoder tube, size 17 (6061) | 2 | Clear anodise | 12 | 24 |
| ST-215 Encoder tube, size 14 (6061) | 1 | Clear anodise | 11 | 11 |
| **One set** | **14** | | | **587 (≈ €534)** |

These are estimates from part size and complexity; the real price comes from JLCCNC's instant quote when you upload the files.

### MJF parts (JLC3DP, D29)

Upload `ST-310-MJF.step` and `ST-311-MJF.step` from `hardware/fab/cnc/`, choose MJF PA12, dyed black. Body 184 g and tower 184 g: about USD 101 (€92) for the pair at the spec's USD 0.275 per gram; the instant quote gives the real price.

### Printing (Bambu H2S + AMS HT)

| Plate | Material | Parts | Filament (g) | Time (h) |
| --- | --- | --- | --- | --- |
| 1 | PAHT-CF | ST-210, ST-211 × 2 | 380 | 27.8 |
| 2 | ASA | ST-217, 315, 317, 318, 319, 605, 606 | 259 | 10.5 |
| 3 | ASA | ST-612, 606, 212 × 2, 216 | 63 | 2.7 |
| 4 | TPU 95A | Gaskets, cable guides, a button cap | 20 | 2.5 |
| 5 | TPU 95A | Button caps, bumpers | 2 | 0.5 |
| 6 | PETG | ST-611 light pipe | 3 | 0.4 |
| **Total** | | **6 plates** | **727** | **44.4** |

The STL files are already turned to print orientation. Dry PAHT-CF at 80 °C for 8–12 h and print it straight from the dryer; print settings for each material are on every drawing. Press the heat-set inserts with a soldering iron at 230 °C before assembly.

### Shopping list

`hardware/fab/shopping-list.csv` has every bought item with quantity, supplier and link: reducers, motors, pulleys, belts, V-rings, hinge pin, two 3/8"-16 bushings, two coin-slot screws, two dowels, thumb screws, the DDC-60i clamp, cells, the MJF order, 162 stainless and 32 aluminium screws, washers, inserts and filament (1 × PAHT-CF, 1 × ASA, small TPU and PETG spools). Two links point at the seller's nearest page rather than the exact item: the 20T pulley (order the 5 mm bore) and the M4 inserts (Ruthex range page). Electronics come with Phase 4.

## P1 assembly sequence

The head goes together in ten steps, bench work first. Every screw, its key and its torque come from the same joint table that builds the parts list, so the two cannot disagree. New parts in each step picture are orange.

**Tools:** hex keys 2, 2.5 and 3 mm (a torque screwdriver covering 0.3–5 N·m is best), soldering iron with a heat-set tip at 230 °C, Loctite 243 and 638, a vice or small arbor press, a coin, a phone with a guitar-tuner app, and a 200 g weight. **Before you start:** press all heat-set inserts (75 M3, 12 M4, 6 M5) into the printed parts.

### Step 1 — Base and wedge lower plate

![Step 1](img/03-step-01.png)

Press the 3/8"-16 bushing into the base, then fit the base under the wedge lower plate with the azimuth lock loose.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| 3/8in-16 bushing ST-307 into base ST-301 | - | press / arbor | - | Loctite 638 (retaining); press in, wipe off, cure 1 h |
| Base ST-301 to wedge lower plate ST-302 (azimuth lock) | 2 × M5 × 12 ISO 7380 | 3 mm key | 4.5 | with washer ST-752; leave loose until set |
| Azimuth fine-adjust push screws ST-306 | 2 × M5 × 25 thumb screw | by hand | - | finger tight, push the base boss |

### Step 2 — Build the three cartridges on the bench

![Step 2](img/03-step-02.png)

Press each reducer into its housing (the crush ribs centre it), fit the 60T pulley, mount the motor on its plate with the 20T pulley (two M4 set screws on the shaft flat, 2 mm key), fit the belt and tension it, then fit the encoder carrier and board. Do all three cartridges the same way.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Reducer size 17 to cartridge housing ST-211 (x2 axes) | 24 × M3 × 50 ISO 4762 | 2.5 mm key | 0.6 | 12 per reducer, criss-cross; 7075 aluminium screws, 0.6 N·m max |
| Reducer size 14 to cartridge housing ST-210 | 8 × M3 × 45 ISO 4762 | 2.5 mm key | 0.6 | criss-cross; 7075 aluminium screws, 0.6 N·m max |
| 60T pulley ST-205 to reducer input stub (x3) | 12 × M3 × 12 ISO 4762 | 2.5 mm key | 1.5 | Loctite 243; pattern to confirm on the Laifual drawing |
| Motor to motor plate ST-207 (x3) | 12 × M3 × 8 ISO 4762 | 2.5 mm key | 1 | Loctite 243 |
| Motor plate to housing walls (x3) | 12 × M3 × 8 ISO 7380 | 2 mm key | 0.6 | with washer ST-750; tighten after tensioning |
| Belt tension screw (x3) | 3 × M3 × 12 ISO 4762 | 2.5 mm key | 0.3 | turn until the span reads 290 Hz |
| Encoder board ST-520 to carrier (x3) | 6 × M3 × 6 ISO 7380 | 2 mm key | 0.3 | cuts its own thread in ASA |
| Carrier ST-212/216 posts to housing flange (x3) | 6 × M3 × 30 ISO 4762 | 2.5 mm key | 0.5 | - |

### Step 3 — Azimuth cartridge into the body

![Step 3](img/03-step-03.png)

Lower the azimuth cartridge into the body from above, motor toward +Y, and screw it to the floor from below.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Azimuth cartridge to body floor | 4 × M4 × 10 ISO 7380 | 2.5 mm key | 1.2 | from below |
| Cable guides ST-320 to body | 2 × M3 × 12 ISO 7380 | 2 mm key | 0.4 | - |

### Step 4 — Head base plate onto the azimuth output

![Step 4](img/03-step-04.png)

Press the 3/8"-16 bushing into the head base plate, fit the azimuth encoder tube, seat the VA-75 V-ring on the plate's rim and screw the reducer output to the plate from below. From here on the head can stand on a tripod by itself.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| 3/8in-16 bushing ST-307 into head base ST-303 | - | press / arbor | - | Loctite 638 (retaining); press in, wipe off, cure 1 h |
| Encoder tube ST-208 to head base plate ST-303 (azimuth) | 2 × M3 × 8 ISO 4762 | 2.5 mm key | 1 | Loctite 243; from below |
| Azimuth reducer output flange to head base plate ST-303 | 16 × M3 × 16 ISO 4762 | 2.5 mm key | 2 | Loctite 243; from below, criss-cross |

### Step 5 — Wedge top plate, hinge, and the head onto the wedge

![Step 5](img/03-step-05.png)

Press the two dowels into the wedge top plate and bolt the latitude arcs to it, hinge it to the lower plate with the pin, fit the clamp knobs and tangent screw. Then stand the head on the dowels and, with the wedge tilted to 45°, turn the coin-slot screw up into the head's bushing from below.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Dowels ST-333 into wedge top plate ST-331 | 2 × Ø4 m6 × 10 | press / arbor | - | into the 6 mm blind holes from the top, 4 mm proud |
| Latitude arcs ST-305 to wedge top plate ST-331 | 4 × M5 × 12 ISO 7380 | 3 mm key | 4.5 | Loctite 243 |
| Hinge pin ST-304 retaining screws | 2 × M3 × 6 ISO 7380 | 2 mm key | 1 | Loctite 243; with large washer ST-751 each end |
| Latitude clamp knobs ST-308 | 2 × M5 × 16 thumb screw | by hand | - | finger tight |
| Latitude tangent screw ST-309 (D38) | 1 × M3 × 25 thumb screw | by hand | - | - |
| Head onto the wedge top plate ST-331 (D39) | 1 × 3/8"-16 × 10 coin-slot | coin | - | screw ST-332 from below, firm by hand; the dowels locate and take the torque |

To use the head without the wedge, undo the coin screw, lift the head off the dowels and screw it onto the tripod by its own socket.

### Step 6 — Tower and altitude cartridge

![Step 6](img/03-step-06.png)

Fit the altitude cartridge through the tower's +X face, the bumpers and cable guides, then the tower onto the body over its gasket.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Altitude cartridge to tower wall | 4 × M4 × 12 ISO 7380 | 2.5 mm key | 1.2 | from outside the +X face |
| Bumpers ST-322 to tower | 2 × M3 × 6 ISO 7380 | 2 mm key | 0.4 | - |
| Cable guides ST-320 to tower | 2 × M3 × 12 ISO 7380 | 2 mm key | 0.4 | - |
| Tower to body (with gasket ST-323) | 4 × M5 × 16 ISO 7380 | 3 mm key | 2 | even, criss-cross |

### Step 7 — Altitude arm and roll cartridge

![Step 7](img/03-step-07.png)

Thread the roll harness through the altitude encoder tube, bolt the arm to the altitude output, then the roll cartridge to the arm pad and the roll enclosure over it.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Arm ST-312 to altitude reducer output | 16 × M3 × 10 ISO 4762 | 2.5 mm key | 2 | Loctite 243; criss-cross |
| Altitude encoder tube to arm hub | 2 × M3 × 5 ISO 7380 | 2 mm key | 0.8 | Loctite 243; thread the roll harness through first |
| Roll cartridge to arm pad | 4 × M4 × 16 ISO 4762 | 3 mm key | 1.2 | from the back of the pad |
| Cable guide ST-320 to arm | 2 × M3 × 12 ISO 7380 | 2 mm key | 0.8 | - |
| Roll enclosure ST-217 to arm pad (gasket ST-328, O-ring ST-329) | 3 × M3 × 16 ISO 4762 | 2.5 mm key | 0.5 | from the pad front |

### Step 8 — Roll shelf and Arca clamp

![Step 8](img/03-step-08.png)

Bolt the roll shelf to the roll output, fit the roll encoder tube and the Arca clamp.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Roll shelf ST-313 to roll reducer output | 12 × M3 × 12 ISO 4762 | 2.5 mm key | 2 | Loctite 243; criss-cross |
| Roll encoder tube ST-215 to shelf | 2 × M3 × 6 ISO 4762 | 2.5 mm key | 1 | Loctite 243 |
| Arca clamp ST-314 to shelf (D36) | 1 × 3/8"-16 × 12 coin-slot | coin or flat screwdriver | - | Loctite 243; coin-slot screw ST-330 |

### Step 9 — Electronics and covers

![Step 9](img/03-step-09.png)

Fit the mainboard to the bezel, the bezel to the body, the battery connector, and the top cover last.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Mainboard ST-501 to bezel bosses | 4 × M3 × 6 ISO 7380 | 2 mm key | 0.3 | - |
| Bezel ST-315 to body (gasket ST-327) | 6 × M3 × 10 ISO 7380 | 2 mm key | 0.5 | - |
| Head-side blade connector ST-609 to bracket | 2 × M3 × 8 ISO 7380 | 2 mm key | 0.4 | - |
| Top cover ST-319 to body (gasket ST-324) | 8 × M3 × 10 ISO 7380 | 2 mm key | 0.5 | criss-cross |

### Step 10 — Battery

![Step 10](img/03-step-10.png)

Close the pack once at the bench, fit the tray to the door, then slide the pack in. From here on the battery is tool-free.

| Joint | Screws | Tool | Torque (N·m) | Notes |
| --- | --- | --- | --- | --- |
| Pack shell halves ST-605/612 (gasket ST-610) | 4 × M3 × 30 ISO 4762 | 2.5 mm key | 0.5 | pack stays closed: user never opens it |
| Battery tray ST-317 to door ST-318 | 2 × M3 × 8 ISO 7380 | 2 mm key | 0.3 | - |

### Final checks

1. **Belt tension, each axis:** pluck the middle of the long span; the tuner should read about 290 Hz. Or hang 200 g on the middle of the span: it should deflect about 2 mm. Tighten the four plate screws only after this.
2. **Free running:** with the motors unplugged, turn each motor pulley by hand for a few turns; it should feel even, with no tight spot or belt rub.
3. **Balance:** mount the payload, loosen the clamp, and slide the foot or plate (or the tube in its rings, for a refractor on a dovetail) until it sits level on the altitude axis. The app's balance check then rocks altitude ±5° and compares motor load each way. Short collar feet (P2) may run out of clamp before full balance; up to 0.6 N·m left over is fine.
4. **Roll limits:** pick the payload type in the app (or the nearest envelope), roll slowly to its limits from the payload table and confirm the gaps; set the soft limits a few degrees inside. Tell the app whether the wedge and a pier extension are fitted, so it applies the right tripod limits.
5. **Seals:** check every gasket sits in its groove all round before closing, and that the three V-rings touch their faces evenly.

## Files, viewer and rebuilding

The [3D viewer](https://claude.ai/artifact/Sw757qqspnFjuqk8EyUjpj) shows the whole head: a payload picker with the five envelopes, a Wedge on/off switch that shows the head standing on the tripod by itself, an explode slider, sliders for azimuth, wedge tilt, altitude and roll, a clickable parts list grouped by assembly step (click a part to see its material, process, mass and files), and a Day/Night toggle. The same page is `hardware/viewer/star-tracker-viewer.html`; open it in any browser.

| Folder | What is in it |
| --- | --- |
| `hardware/cad/stcad/` | The parametric model (build123d): `params.py` holds every shared dimension; parts, assembly, checks, drawings, renders |
| `hardware/cad/step/` | STEP per part, bought-part envelopes, assembly and exploded assembly |
| `hardware/cad/stl/` | Printed parts in print orientation |
| `hardware/drawings/` | PDF per part, `ST-P1-drawing-set.pdf` (35 pages with index), PNG previews |
| `hardware/fab/` | CNC files and quote, print plates, shopping list |
| `hardware/bom/` | `master-parts-list.csv` |
| `docs/img/03-*.png` | Renders and assembly step pictures |
| `hardware/cad/out/` | Check results (`checks.json`) |
| `hardware/cad/PROGRESS.md` | Stage-by-stage status of Phase 3 |

To rebuild everything after changing a dimension, use the manual GitHub workflow: open the repository on github.com, click **Actions**, pick **Phase 3 CAD build** in the left list, click **Run workflow**, then **Run workflow** again. When it finishes (about 20 minutes), open the run and download **phase3-cad-output** at the bottom of the page. It never runs on its own.

The roll offset (D34) is a single parameter: to try another offset, only `D31_EXTRA_OFFSET` in `params.py` changes and the build redoes every part, check and drawing. The payload envelopes are the `RIGS` table in the same file: add a line for any other kit and the build checks it too. Option B would instead raise the roll axis (Z_ROLL) and reshape the arm and shelf.
