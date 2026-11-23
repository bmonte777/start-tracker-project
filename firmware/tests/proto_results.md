| Check | Result | Detail |
|---|---|---|
| alpaca discovery answers with the port | pass | {"AlpacaPort":32323} |
| telescope connect | pass |  |
| rightascension readable, transaction id echoed | pass |  |
| synchronous slew returns when finished | pass | 0.8 s real |
| pointing after the slew within 2 arcsec (JNow) | pass | 0.01" |
| invalid RA -> error 0x401 | pass |  |
| axis rates 0..8 deg/s (D42) | pass |  |
| rotator position readable | pass |  |
| unknown member -> HTTP 400 | pass |  |
| LX200 :GR# high precision HH:MM:SS# | pass | 05:16:41# |
| LX200 :GD# sDD*MM:SS# | pass | +45*59:53# |
| LX200 :Sr accepted | pass |  |
| LX200 :Sd accepted | pass |  |
| LX200 :MS# to Sirius (below the horizon or slewing) | pass | '1Below horizon or outside the limits#' |
| LX200 ACK -> A (alt-az) | pass |  |
| WebSocket upgrade (101) | pass |  |
| WebSocket config.get reply | pass |  |
| WebSocket state events | pass |  |
