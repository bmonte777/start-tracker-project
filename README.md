# Star Tracker Project (working name)

Open-source 3-axis motorised astro head: star tracking, go-to, panoramas, time-lapse and camera control. 3D-printed prototype first, then mass production. Built to be repaired by its owner.

## Status
- Phase 1: research — done → [`docs/01-research-report.md`](docs/01-research-report.md)
- Phase 2: engineering spec — done → [`docs/02-engineering-spec.md`](docs/02-engineering-spec.md), parts list in [`hardware/bom/master-parts-list.csv`](hardware/bom/master-parts-list.csv), calculations in [`docs/calc/`](docs/calc/), decisions D1–D31 in [`docs/02-decisions-log.md`](docs/02-decisions-log.md). Open follow-up: revise the spec for the size-17 azimuth reducer (D17)

## Repository layout (planned)
| Folder | Contents |
|---|---|
| `docs/` | Research, specs, user guide, maintenance guide |
| `hardware/cad/` | 3D models (STEP for production, STL for printing) |
| `hardware/drawings/` | A4 dimensioned drawings, one part per sheet (PDF) |
| `hardware/bom/` | Bill of materials, down to the last screw, with supplier part numbers |
| `electronics/` | Schematics and PCB (KiCad) |
| `firmware/` | Motion core + application core (ASCOM Alpaca, LX200, WebSocket) |
| `app/` | Android and Windows apps |
| `website/` | Product website |
