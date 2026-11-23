// Star Tracker — the bridge between the shared UI and the native shell (docs/06-apps.md section 3.5).
//
// Android (app/android, Java) adds window.StNative with  call(method, argsJson, callbackId); results come back through
// window.__stNativeDone(callbackId, ok, json). Windows (app/windows, Python backend) answers the same calls at
// POST /bridge/st/<method>. In a plain browser (tests, screenshots, the head's own network) there is no shell: the
// functions that need one say so instead of pretending.
//
// The Sony camera keeps the bridge it has in Benro-Polaris-Controller: window.CameraNative (CameraBridge.java on
// Android, bridges.py on Windows), so the reused camera code needs no change.

let seq = 0;
const waiting = new Map();
if (typeof window !== 'undefined') {
  window.__stNativeDone = (id, ok, json) => {
    const w = waiting.get(id);
    if (!w) return;
    waiting.delete(id);
    let v = null;
    try { v = json ? JSON.parse(json) : null; } catch (e) { v = json; }
    ok ? w.resolve(v) : w.reject(new Error(typeof v === 'string' ? v : (v && v.error) || 'native call failed'));
  };
}

export function platform() {
  if (typeof window === 'undefined') return 'node';
  if (window.StNative) return 'android';
  if (window.ST_PLATFORM === 'windows') return 'windows';
  return 'browser';
}
export const hasShell = () => ['android', 'windows'].includes(platform());

/** Call the native shell. Rejects with a readable message where there is none. */
export function native(method, args = {}, timeoutMs = 30000) {
  const p = platform();
  if (p === 'android') {
    return new Promise((resolve, reject) => {
      const id = 'n' + (++seq);
      const t = setTimeout(() => { waiting.delete(id); reject(new Error(method + ': no answer from the app')); }, timeoutMs);
      waiting.set(id, { resolve: (v) => { clearTimeout(t); resolve(v); }, reject: (e) => { clearTimeout(t); reject(e); } });
      window.StNative.call(method, JSON.stringify(args), id);
    });
  }
  if (p === 'windows') {
    return fetch('/bridge/st/' + method, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-StarTracker': '1' }, body: JSON.stringify(args) })
      .then(async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.error || 'HTTP ' + r.status); return j.result; });
  }
  return Promise.reject(new Error('needs the Star Tracker app (Android or Windows)'));
}

/** Discovery bridge for app/shared/discovery.js. HTTP works everywhere (the head allows cross-origin reads). */
export const discoveryBridge = {
  async httpGetJson(url, timeoutMs = 1000) {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), timeoutMs);
    try { const r = await fetch(url, { signal: ac.signal }); return r.ok ? await r.json() : null; } catch (e) { return null; } finally { clearTimeout(t); }
  },
  mdns: (timeoutMs) => (hasShell() ? native('discoverMdns', { timeoutMs }, timeoutMs + 2000) : Promise.resolve([])),
  alpaca: (timeoutMs) => (hasShell() ? native('discoverAlpaca', { timeoutMs }, timeoutMs + 2000) : Promise.resolve([])),
};

/** BLE first set-up (payloads from ble.js). */
export const ble = {
  scan: (ms = 6000) => native('bleScan', { ms }, ms + 5000),                       // -> [{id, name, rssi}]
  connect: (id) => native('bleConnect', { id }, 60000),                           // pairing: the OS asks for the OLED code
  write: (id, ch, text) => native('bleWrite', { id, ch, text }, 20000),
  read: (id, ch) => native('bleRead', { id, ch }, 10000),
  disconnect: (id) => native('bleDisconnect', { id }, 5000),
};

/** Keep the job alive with the screen off (Android: foreground service + wake and Wi-Fi locks). No-op elsewhere. */
export function keepAwake(on, text = '') {
  return hasShell() ? native('keepAwake', { on, text }).catch(() => null) : Promise.resolve(null);
}
export function notify(title, text) {
  return hasShell() ? native('notify', { title, text }).catch(() => null) : Promise.resolve(null);
}
/** Open a system settings page: 'wifi', 'bluetooth', 'location'. */
export function openSettings(what) { return native('openSettings', { what }).catch(() => null); }

/** Phone/PC location for first set-up when the head has no GNSS fix. Browser geolocation where allowed. */
export function location() {
  if (hasShell()) return native('location', {}, 20000);
  return new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) return reject(new Error('no location on this device'));
    navigator.geolocation.getCurrentPosition((p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude, elev_m: p.coords.altitude || 0 }),
      (e) => reject(new Error(e.message)), { timeout: 15000 });
  });
}

/** Sony camera (reused CameraNative bridge). Every call is synchronous in the shells; wrapped so a missing camera is a
 *  clear message, not an exception in a screen. */
export const camera = {
  present: () => typeof window !== 'undefined' && !!window.CameraNative,
  call(method, ...args) {
    if (!this.present()) throw new Error('camera control needs the Star Tracker app with the camera on USB-C');
    const r = window.CameraNative[method](...args);
    if (typeof r === 'string' && /^[[{]/.test(r)) { try { return JSON.parse(r); } catch (e) { return r; } }
    return r;
  },
  status() { try { return this.present() ? this.call('status') : { connected: false }; } catch (e) { return { connected: false, error: e.message }; } },
};
