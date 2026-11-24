# Phase 9a — Product name shortlist

24 Nov 2026. Waiting for Bruno's pick (Q77). Domain checks are left until a name is chosen (Bruno, 24 Nov).

**OLED limits (from the source):** the head's screen is an SH1106 128 × 64 driven with one 6 × 8 font, 21 characters × 8 rows (`st_hal.h`, `oled.text`); the splash today is "Star Tracker" in inverse on row 0 (`st_app/app.cpp`). Any name up to 21 letters fits, but the font is plain ASCII, so accents (é, á) are dropped on the OLED, in the Wi-Fi network name, in mDNS and in the app id.

**How "already used" was checked:** web searches for the name with star tracker / telescope mount / tripod head / camera / app (24 Nov 2026). A plain check, not a trademark search.

| # | Name | What it says | English / Portuguese | OLED and app | Already used? |
|---|---|---|---|---|---|
| 1 | **Vela** | The constellation "the Sails" (the old ship Argo); in Portuguese also sail and candle: a light in the dark, finding your way | Same sound in both (VEH-la); easy | 4 letters, clean on the OLED; "Vela" reads well as an app name | No astro, camera or tripod product found. Vela is a common astro-photo target name, so searches are noisy |
| 2 | **Corvo** | Corvus (the Crow); the ravens of Lisbon's coat of arms; Corvo, the smallest Azores island, very dark skies | KOR-vo in both; easy | 5 letters; good app name | No astro, camera or tripod product found |
| 3 | **Caravela** | The caravel: Portuguese ships that crossed oceans by the stars | ka-ra-VEH-la; English speakers know "caravel" | 8 letters, fits; a little long as an app icon label | No astro, camera or tripod product found |
| 4 | **Mira** | The star Mira ("the wonderful"); in Portuguese *mira* is the sight you aim with ("ter em mira") | MEE-ra in both | 4 letters; very good app name | Crowded: many "Mira" tracker apps, above all the Mira fertility tracker (app + hormone-tracker device), so "Mira tracker" searches clash |
| 5 | **Nauta** | Latin / Portuguese for sailor, navigator | NOW-ta; fine in both | 5 letters | Nauta is the Cuban telecom's internet service and app (ETECSA), well known in Spanish |
| 6 | **Estrela** | "Star" in Portuguese; Serra da Estrela | esh-TREH-la (PT) vs es-TREL-a (EN); a little hard for English speakers | 7 letters | No astro product found; a very common word, hard to own in searches |
| 7 | **Sidera** | Latin "stars", the root of *sidereal*, the rate the head tracks at | SID-er-a; PT *sideral* is close | 6 letters | Very close to Explore Scientific's new **Sidara** telescope-and-mount series (2026), same market |
| 8 | **Zénite** | The zenith | PT word; EN "zenith" | Shows as "Zenite" (no accent) | Close to **Zenit**, the camera brand (relaunched with a mirrorless camera) |
| 9 | **Astrolábio** | The navigators' star instrument | Long; EN "astrolabe" | 10 letters, accent lost | No mount found; generic word |
| 10 | **Azimute** | Azimuth, one of the three axes | Technical; in English it can read as "a-zi-mute" | 7 letters | No product found; says only one of three axes |
| 11 | **Lume** | Portuguese for fire / light; "lume" is also the glow on watch dials | LOO-me; fine | 4 letters | No tracker found; common watch-world word |
| 12 | **Nocta** | Night (Latin root) | Fine in both | 5 letters | Taken in spirit: **NOCTA**, the Nike × Drake brand |

## Recommendation

1. **Vela** — short, a real southern constellation, a double meaning in Portuguese (sail / candle), same sound in both languages, nothing in the astro or tripod world uses it.
2. **Corvo** — a Lisbon and Azores story nobody else has, distinctive and easy to say.
3. **Caravela** — the clearest Portuguese identity (navigation by the stars), slightly long.

Mira would be first on sound and meaning, but the "Mira tracker" clash with the fertility device is hard to get past in searches.

## What the name changes (the firmware ↔ app contract) — nothing changed until Bruno says so

| Item | Today | Where |
|---|---|---|
| App name | "Star Tracker" (D77) | `app/ui/app.js`, Android label, Windows (Tauri) product name, installer |
| App id | `pt.brunomonte.startracker` (D77) | `app/android/app/build.gradle`, Java package folders |
| Access point | "StarTracker-XXXX" (D71) | `firmware/esp32s3/components/st_app/net.cpp`; apps look for the prefix in `app/shared/ble.js` (`NAME_PREFIX`), `StNative.java`, help text in `connect.js`, `firmware/tools/web-flasher.html` |
| BLE name | same prefix | `ble.cpp`, `app/shared/ble.js` |
| Head name | "StarTracker" | `st_core/include/st_head.h`; simulator "StarTracker-SIM" + `app/tests/client.test.mjs` |
| mDNS | `startracker.local`, service `_startracker._tcp` (D71) | `net.cpp`, `idf_component.yml`, `discovery.js` |
| API path | `/startracker/v1/info`, `/startracker/v1/op` (D75, D76) | firmware `services.cpp`, apps |
| OLED splash | "Star Tracker" | `st_app/app.cpp` |
| Update file | `star-tracker-update.stfw` | release workflow, web flasher |
