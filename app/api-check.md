# API check: apps against the firmware source

47 of 47 checks pass (`app/tools/check_api.py`).

| Check | Result | Detail |
|---|---|---|
| every op in models.js is handled by wsapi.cpp | pass | 43 ops |
| every op wsapi.cpp handles is known to the apps | pass |  |
| hello's op list matches what wsapi.cpp handles | pass |  |
| every op the client and screens send exists | pass | 42 ops used |
| every op the native camera code sends exists (Android + Windows) | pass | 12 ops |
| goto: argument names match | pass | app ['alt_d', 'az_d', 'body', 'dec_d', 'epoch', 'ra_h'] firmware ['alt_d', 'az_d', 'body', 'dec_d', 'epoch', 'ra_h'] |
| sync: argument names match | pass | app ['dec_d', 'epoch', 'ra_h'] firmware ['dec_d', 'epoch', 'ra_h'] |
| track: argument names match | pass | app ['on', 'rate'] firmware ['on', 'rate'] |
| jog: argument names match | pass | app ['axis', 'dps'] firmware ['axis', 'dps'] |
| guide: argument names match | pass | app ['dir', 'ms'] firmware ['dir', 'ms'] |
| rotator.pa: argument names match | pass | app ['pa_d'] firmware ['pa_d'] |
| rotator.roll: argument names match | pass | app ['roll_d'] firmware ['roll_d'] |
| time.set: argument names match | pass | app ['unix_s'] firmware ['unix_s'] |
| ivm.start: argument names match | pass | app ['count', 'delay_s', 'exposure_s', 'focus_s', 'interval_s'] firmware ['count', 'delay_s', 'exposure_s', 'focus_s', 'interval_s'] |
| pec.record: argument names match | pass | app ['axis', 'cycles'] firmware ['axis', 'cycles'] |
| pec.get: argument names match | pass | app ['axis'] firmware ['axis'] |
| pec.clear: argument names match | pass | app ['axis'] firmware ['axis'] |
| job.ack: argument names match | pass | app ['frame', 'job_id'] firmware ['frame', 'job_id'] |
| cal.encoder.start: argument names match | pass | app ['axis', 'speed_dps'] firmware ['axis', 'speed_dps'] |
| cal.balance: argument names match | pass | app ['swing_d'] firmware ['swing_d'] |
| faults.get: argument names match | pass | app ['since'] firmware ['since'] |
| job.start: every argument the app may send is read by services.cpp | pass | app-only ['hold']; firmware-only [] |
| config.set keys: app = firmware | pass | app-only []; firmware-only [] |
| config.get returns the set keys plus park_az, park_alt | pass | [] |
| every state field parseState reads is sent by the firmware | pass | 30 fields |
| every state field the screens show is sent by the firmware | pass | 13 fields |
| activity names (mode) match | pass |  |
| altitude limits (st_head.h vs models.js) | pass | -10 … 95 |
| jog limit 8°/s = default slew speed (D42) | pass |  |
| payload range 1–5 | pass |  |
| intervalometer exposure limit 3600 s | pass |  |
| margin 3° (LIMIT_MARGIN_DEG) | pass |  |
| payload masses match D40 (1.55, 1.95, 3.75, 2.70, 7.00 kg) | pass |  |
| roll limits in limits.get come from head.cpp's PAYLOADS table | pass | P1: +9/-175, P2: +9/-130, P3: +8/-150, P4: +15/-150, P5: +8/-155 |
| guide directions n/s/e/w | pass |  |
| track rates sidereal/lunar/solar/king | pass |  |
| PEC period: 3 motor turns = 3.6° of output (300:1) | pass |  |
| encoder map size: 8 harmonics + 721-point grid | pass |  |
| BLE service and characteristic UUIDs (ble.cpp vs ble.js) | pass |  |
| BLE Wi-Fi payload keys ssid/psk/mode | pass |  |
| BLE write buffer 256 bytes (255 + terminator) | pass |  |
| .stfw: magic, version 1, ≤ 2 entries, RP image ≤ 0x7F000 | pass |  |
| .stfw upload path /api/update | pass |  |
| HTTP routes /startracker/v1/info and /op on the head | pass |  |
| WebSocket path /ws/v1 | pass |  |
| Alpaca discovery UDP 32227 | pass |  |
| error codes | pass |  |
