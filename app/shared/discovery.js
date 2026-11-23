// Star Tracker — finding the head (decision Q55, docs/06-apps.md section 3.6).
// Order: last head used → mDNS (_startracker._tcp) → Alpaca discovery (UDP 32227) → the head's access point
// (192.168.4.1). Each candidate is confirmed with GET /startracker/v1/info, which also gives the WebSocket address.
//
// UDP and mDNS need the native shell, so they come in through a `bridge`:
//   bridge.httpGetJson(url, timeoutMs) -> object | null
//   bridge.mdns(timeoutMs)             -> [{host, port}]        (optional)
//   bridge.alpaca(timeoutMs)           -> [{host, port}]        (optional; port = AlpacaPort)
// The Android and Windows shells provide it (window.StNative.discovery); tests use app/shared/node/bridge.mjs.

export const AP_HOST = '192.168.4.1';
export const ALPACA_DISCOVERY_PORT = 32227;
export const INFO_PATH = '/startracker/v1/info';

/** Build the WebSocket URL from an info answer (falls back to 1.0 defaults: port 80, /ws/v1). */
export function wsUrlFrom(host, info) {
  const port = info && info.ws_port ? info.ws_port : 80;
  const path = info && info.ws_path ? info.ws_path : '/ws/v1';
  return `ws://${host}${port === 80 ? '' : ':' + port}${path}`;
}
export function httpBaseFrom(host, info) {
  const port = info && info.http_port ? info.http_port : 80;
  return `http://${host}${port === 80 ? '' : ':' + port}`;
}

async function confirm(bridge, host, port, timeoutMs) {
  const tries = port ? [port] : [80, 8080];       // 8080: the simulator's web port
  for (const p of tries) {
    const info = await bridge.httpGetJson(`http://${host}${p === 80 ? '' : ':' + p}${INFO_PATH}`, timeoutMs).catch(() => null);
    if (info && info.ws_path) return { host, info, ws: wsUrlFrom(host, info), http: httpBaseFrom(host, info) };
  }
  return null;
}

/**
 * Find heads. Resolves with a list (best first), each {host, info, ws, http, via}. Stops at the first stage that
 * finds anything unless `all` is set.
 */
export async function discover(bridge, { last = null, all = false, onStage = () => {}, timeoutMs = 2000 } = {}) {
  const found = [];
  const add = (r, via) => { if (r && !found.some((f) => f.host === r.host && f.info.ws_port === r.info.ws_port)) found.push({ ...r, via }); };

  if (last) {
    onStage('last');
    add(await confirm(bridge, last.host, last.port, 1000), 'last');
    if (found.length && !all) return found;
  }
  if (bridge.mdns) {
    onStage('mdns');
    for (const s of await bridge.mdns(timeoutMs).catch(() => [])) add(await confirm(bridge, s.host, s.port, 1000), 'mdns');
    if (found.length && !all) return found;
  }
  if (bridge.alpaca) {
    onStage('alpaca');
    for (const s of await bridge.alpaca(timeoutMs).catch(() => [])) {
      // /startracker/v1/info is served on the Alpaca port too, and tells us the web/WebSocket port
      add(await confirm(bridge, s.host, s.port, 1000), 'alpaca');
    }
    if (found.length && !all) return found;
  }
  onStage('ap');
  add(await confirm(bridge, AP_HOST, 80, 1500), 'ap');
  onStage('done');
  return found;
}
