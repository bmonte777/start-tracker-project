// Star Tracker — BLE first set-up (firmware/esp32s3/components/st_app/ble.cpp, spec 7.2).
// Service 5354524b-0100-4d2a-9b1e-000000000001 ("STRK"). Pairing: passkey (6 digits) shown on the head's OLED;
// the phone/PC's own pairing dialog asks for it. Characteristics:
//   …0002 Wi-Fi set-up  write (encrypted, authenticated)  {"ssid":"…","psk":"…","mode":"sta"}
//   …0003 Status        read / notify                       {"ip":"…","ap":"StarTracker-XXXX","soc":83,"mode":"idle","fw":"0.1.0"}
//   …0004 Command       write (encrypted)                   WebSocket request format, limited to stop and park
// The radio work is native (Android BluetoothGatt, Windows bleak); this module only shapes the payloads.

export const SERVICE = '5354524b-0100-4d2a-9b1e-000000000001';
export const CH_WIFI = '5354524b-0100-4d2a-9b1e-000000000002';
export const CH_STATUS = '5354524b-0100-4d2a-9b1e-000000000003';
export const CH_CMD = '5354524b-0100-4d2a-9b1e-000000000004';
export const NAME_PREFIX = 'StarTracker-';
export const MAX_WRITE = 255;     // ble.cpp: 256-byte buffer including the terminator

export function wifiPayload(ssid, psk) {
  if (!ssid || ssid.length > 32) throw new Error('Wi-Fi name must be 1–32 characters');
  if (psk && (psk.length < 8 || psk.length > 63)) throw new Error('Wi-Fi password must be 8–63 characters (or empty for an open network)');
  const s = JSON.stringify({ ssid, psk: psk || '', mode: 'sta' });
  if (new TextEncoder().encode(s).length > MAX_WRITE) throw new Error('Wi-Fi name and password are too long together');
  return s;
}

export function commandPayload(op) {
  if (!['stop', 'park'].includes(op)) throw new Error('over BLE the head accepts only stop and park');
  return JSON.stringify({ v: 1, id: 1, op, args: {} });
}

export function parseStatus(text) {
  try {
    const j = JSON.parse(text);
    return { ip: j.ip || '', ap: j.ap || '', soc: Number(j.soc) || 0, mode: j.mode || '', fw: j.fw || '' };
  } catch (e) { return null; }
}

/** A head advertises its name (the access point name) — filter scans by prefix until the advert carries the UUID. */
export function isHeadAdvert(name, uuids = []) {
  return (typeof name === 'string' && name.startsWith(NAME_PREFIX)) || uuids.map((u) => u.toLowerCase()).includes(SERVICE);
}
