# Phase 9a — Product name shortlist (rounds 2 and 3)

24 Nov 2026. **Bruno's direction after round 1: no names tied to Portugal; the name must come from space or astronomy.** Round 1 (Vela, Corvo, Caravela, Mira, …) is set aside. Domain checks are left until a name is chosen (Bruno). Waiting for the pick (Q77).

**OLED limits (from the source):** the head's screen is an SH1106 128 × 64 driven with one 6 × 8 font, 21 characters × 8 rows (`st_hal.h`, `oled.text`); the splash today is "Star Tracker" in inverse on row 0 (`st_app/app.cpp`). Every name below fits. The font is plain ASCII.

**How "already used" was checked:** web searches for each name with telescope mount / star tracker / tripod / camera / app / brand, 24 Nov 2026. A plain check, not a trademark search.

| # | Name | What it says about the product | English / Portuguese | OLED and app | Already used? |
|---|---|---|---|---|---|
| 1 | **Trifid** | The Trifid Nebula (M20), a favourite astrophoto target; *trifid* means "split in three": three axes | TRY-fid / *trífida*; easy in both | 6 letters; strong app name | No astro, camera or tripod product found |
| 2 | **Octans** | The constellation that holds the south celestial pole (the octant): polar alignment, on both hemispheres | OK-tanz / *Octante*; easy | 6 letters | No astro, camera or tripod product found |
| 3 | **Tycho** | Tycho Brahe, the great naked-eye astronomer; also the Tycho-2 star catalogue the app's plate solver uses on long lenses (D74) | TY-ko / "Tico"; easy | 5 letters | No mount, tracker or camera product found; a well-known astronomy name (crater, catalogue) |
| 4 | **Gnomon** | The pointer of a sundial, set parallel to the Earth's axis: a polar-aligned instrument | NO-mon (silent G) / *gnómon*; the silent G will be misspelt | 6 letters | No product found |
| 5 | **Ecliptic** | The Sun's path across the sky | ee-KLIP-tik / *eclíptica* | 8 letters; reads like an adjective | No product found |
| 6 | **Regulus** | "Little king", the bright star of Leo, on the ecliptic | REG-yoo-lus / *Régulo* | 7 letters | No product found |
| 7 | **Carina** | The Keel; home of the Carina Nebula | ka-REE-na; same in PT | 6 letters | No astro product found; also a common first name and product name |
| 8 | **Armilla** | The armillary sphere: rings turning about axes, like a 3-axis head | ar-MIL-a / *armila* | 7 letters | No product found. Note: the armillary sphere is on the Portuguese flag, so it carries a Portuguese link |
| 9 | **Syzygy** | Three bodies in a line, as in an eclipse; three axes | SIZ-i-jee; hard to spell and say in both | 6 letters | No product found |
| 10 | **Astraeus** | The Titan of dusk and father of the stars | as-TREE-us; spelling unclear | 8 letters | No product found |
| 11 | **Umbra** | The darkest part of an eclipse shadow | UM-bra / *umbra*; easy | 5 letters | **Clash:** Umbra is a known US space company (radar satellites) |
| 12 | **Orrery** | A clockwork model of the solar system: precise gearing | OR-er-ee; hard in PT | 6 letters | **Clash:** several astronomy apps are already called Orrery / Solar Orrery |

Left out without a full check: names already used by astro brands (Polaris, Altair, Vega, Sirius, Atlas, Orion, Pegasus, Antares, Fornax, Pyxis, Nyx, Zenith, Equinox, Apogee, Pulsar, Messier, Celestia).

## Recommendation

1. **Trifid** — a famous nebula every astrophotographer knows, and the word itself means "in three parts", like the head's three axes. Short, easy in both languages, nothing in the market uses it.
2. **Octans** — the south-pole constellation: a quiet nod to polar alignment and to working on both hemispheres.
3. **Tycho** — the astronomer, and the star catalogue the app actually solves against.

## What the name changes (D100: visible names only)

| Item | Today | Changes? | Where |
|---|---|---|---|
| App name | "Star Tracker" (D77) | yes | `app/ui/app.js`, Android label, Windows (Tauri) product name, installer |
| OLED splash | "Star Tracker" | yes | `st_app/app.cpp` |
| Access point | "StarTracker-XXXX" (D71) | yes | `net.cpp`; apps look for the prefix in `app/shared/ble.js` (`NAME_PREFIX`), `StNative.java`, help text in `connect.js`, `firmware/tools/web-flasher.html` |
| BLE name | same prefix | yes | `ble.cpp`, `app/shared/ble.js` |
| Head name | "StarTracker" | yes | `st_core/include/st_head.h`; simulator "StarTracker-SIM" + `app/tests/client.test.mjs` |
| mDNS host | `startracker.local` (D71) | yes | `net.cpp`, `discovery.js` |
| Update file | `star-tracker-update.stfw` | yes | release workflow, web flasher |
| App id | `pt.brunomonte.startracker` (D77) | **no** | — |
| API paths | `/startracker/v1/info`, `/startracker/v1/op` (D75, D76) | **no** | — |
| mDNS service | `_startracker._tcp` | **no** | — |

The code change itself is made only after Bruno confirms it (one firmware + app release, tests rerun).

## Round 3 (Bruno asked for more, 24 Nov)

Same checks as round 2.

| # | Name | What it says about the product | English / Portuguese | OLED and app | Already used? |
|---|---|---|---|---|---|
| 13 | **Canopus** | The second-brightest star, and the guide star that spacecraft star trackers lock onto to hold their attitude: the original "star tracker" star | ka-NOH-pus / *Canopo*; easy | 7 letters | No astro, camera or tripod product found |
| 14 | **Caelum** | Latin for "the sky"; also a small southern constellation (the engraver's chisel: precision) | SEE-lum or KYE-lum (two ways to say it) / *Célum* | 6 letters | No product found |
| 15 | **Thuban** | The pole star of 5,000 years ago (Egypt's pyramids point to it): precession and polar alignment | THOO-ban / "Tuban"; fine | 6 letters | No product found |
| 16 | **Sagitta** | The Arrow: precise pointing | sa-JIT-a / *Sagita* | 7 letters | No product found |
| 17 | **Albireo** | The gold-and-blue double star in Cygnus, a favourite first target | al-BIR-ee-oh / *Albíreo* | 7 letters | No product found |
| 18 | **Culmina** | From *culmination*: the moment a target is highest and sharpest, the best time to shoot | KUL-min-a / *culminar*; easy | 7 letters | No product found |
| 19 | **Corvus** | The Crow constellation (Latin name only) | KOR-vus | 6 letters | No product found |
| 20 | **Kochab** | The pole star of the ancient Greeks | KOH-kab; awkward in both | 6 letters | No product found |
| 21 | **Aphelion** | A planet's farthest point from the Sun | a-FEE-lee-on / *afélio* | 8 letters | No product found |
| 22 | **Lagrange** | The mathematician, and the L-points where telescopes like JWST park | la-GRAHNZH | 8 letters | No product found |
| 23 | **Meridian** | The line where a target culminates (meridian flip) | Easy | 8 letters | No brand found, but it is an everyday mount term ("meridian flip"), so it cannot be owned in searches |
| 24 | **Auriga** | The Charioteer | Easy | 6 letters | **Clash:** Auriga is an astronomy eyepiece brand |

### Round 3 recommendation

1. **Canopus** — the star real star trackers use; a strong, easy, unused name.
2. **Thuban** — the old pole star: a story about polar alignment that photographers enjoy telling.
3. **Caelum** — "the sky" in Latin, short and elegant, but people say it two ways.

Overall favourites across rounds 2 and 3: **Canopus**, **Trifid**, **Thuban**.
