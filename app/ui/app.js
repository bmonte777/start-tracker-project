// Star Tracker app — the one page that holds every screen (docs/06-apps.md section 3.2).
// One WebSocket connection for the whole app, so moving between screens never drops the head. Screens are modules in
// screens/ that render into #view and get the latest head state through the store.
import { CONN, StClient } from '../shared/stclient.js';
import { discover } from '../shared/discovery.js';
import { discoveryBridge, keepAwake, platform } from '../shared/native.js';

// ------------------------------------------------------------------ small helpers for the screens
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export function toast(msg, kind = '') {
  const t = document.createElement('div');
  t.setAttribute('role', 'status');
  t.className = 'toast ' + kind;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3600);
}
/** Run a head request from a button: disables it, shows the head's error as a toast. */
export async function act(btn, fn, okMsg) {
  if (btn) btn.disabled = true;
  try { const r = await fn(); if (okMsg) toast(okMsg); return r; } catch (e) { toast(e.headMsg || e.message, 'bad'); return undefined; } finally { if (btn) btn.disabled = false; }
}
export const fmt = {
  n: (v, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : '—'),
  pct: (v) => (Number.isFinite(v) ? Math.round(v) + ' %' : '—'),
};

/** App-side preferences (lens, sensor, camera choice): kept on this phone/PC, not on the head. */
export const prefs = {
  get(k, d) { try { const v = JSON.parse(localStorage.getItem('st-pref-' + k)); return v ?? d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('st-pref-' + k, JSON.stringify(v)); } catch (e) { /* */ } },
};
/** Wait for the running job to end (job.status, so a state event from before the start cannot fool it). */
export async function waitJob(client, timeoutMs = 3600000) {
  const t0 = Date.now();
  for (;;) {
    const st = await client.jobStatus();
    if (['done', 'stopped', 'failed', 'none'].includes(st.state)) return st;
    if (Date.now() - t0 > timeoutMs) throw new Error('job did not end');
    await new Promise((r) => setTimeout(r, 300));
  }
}

// ------------------------------------------------------------------ store
const listeners = new Set();
export const store = {
  client: null, state: null, conn: CONN.OFFLINE, connWhy: '', head: null, info: null, config: null, limits: null,
  set(patch) { Object.assign(this, patch); for (const f of listeners) f(this, patch); },
  on(f) { listeners.add(f); return () => listeners.delete(f); },
};

const LAST = 'startracker-last-head';
export function lastHead() { try { return JSON.parse(localStorage.getItem(LAST) || 'null'); } catch (e) { return null; } }

/** Connect to a head (found by discovery or typed in). */
export async function connectTo(found) {
  if (store.client) store.client.close();
  const c = new StClient({ url: found.ws, app: `startracker-${platform()}` });
  store.set({ client: c, head: found, conn: CONN.CONNECTING, state: null });
  c.on('conn', (st, why) => store.set({ conn: st, connWhy: why }));
  c.on('state', (s) => store.set({ state: s }));
  c.on('hello', async (info) => {
    store.set({ info });
    try { store.set({ config: await c.getConfig(), limits: c.supports('limits.get') ? await c.limits() : null }); } catch (e) { /* shown by screens */ }
  });
  try { localStorage.setItem(LAST, JSON.stringify({ host: found.host, port: found.info?.http_port || 80 })); } catch (e) { /* */ }
  try { await c.connect(); return true; } catch (e) { toast(e.message, 'bad'); return false; }
}

export async function findHeads(onStage) {
  return discover(discoveryBridge, { last: lastHead(), all: true, onStage, timeoutMs: 2000 });
}

/** Re-read settings and limits (after config.set). */
export async function refreshConfig() {
  const c = store.client;
  if (!c) return;
  store.set({ config: await c.getConfig(), limits: c.supports('limits.get') ? await c.limits() : null });
}

// keep the phone awake while a head job runs (Android foreground service)
let awake = false;
store.on((s) => {
  const want = !!(s.state && s.state.job && !['done', 'stopped', 'failed'].includes(s.state.job.state));
  if (want !== awake) { awake = want; keepAwake(want, want ? `Job: frame ${s.state.job.frame} of ${s.state.job.frames}` : ''); }
});

// ------------------------------------------------------------------ screens and navigation
const ICON = {
  connect: '<path d="M5 12a10 10 0 0 1 14 0M8.5 15.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1.3"/>',
  dashboard: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
  sky: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4"/><circle cx="12" cy="12" r="1.6"/>',
  align: '<path d="M4 20L20 4M14 4h6v6"/><circle cx="7" cy="7" r="2.2"/><circle cx="17" cy="17" r="2.2"/>',
  rig: '<rect x="4" y="9" width="12" height="7" rx="1.5"/><path d="M16 11l4-2v7l-4-2M8 16v4M12 16v4"/>',
  roll: '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4h-4"/>',
  camera: '<rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M8.5 7l1.6-2.5h3.8L15.5 7"/><circle cx="12" cy="13.5" r="3.6"/>',
  night: '<path d="M19 14.5A7.5 7.5 0 1 1 9.5 5a6 6 0 0 0 9.5 9.5z"/>',
  gallery: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 16l5-5 4 4 3-3 5 5"/>',
  pec: '<path d="M3 12c2-6 4-6 6 0s4 6 6 0 4-6 6 0"/>',
  health: '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
  update: '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 19h16"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
};
export const SCREENS = [
  ['dashboard', 'Dashboard', true], ['sky', 'Sky', true], ['camera', 'Camera & jobs', true], ['night', 'Night', true],
  ['align', 'Alignment', false], ['rig', 'Rig', false], ['roll', 'Roll', false], ['gallery', 'Gallery', false],
  ['pec', 'PEC', false], ['health', 'Health', false], ['update', 'Firmware', false], ['settings', 'Settings', false], ['connect', 'Connect', false],
];
const loaded = new Map();
let current = null;

function bar() {
  const prim = SCREENS.filter((s) => s[2]);
  const more = SCREENS.filter((s) => !s[2]);
  const link = ([id, name]) => `<a href="#/${id}" data-id="${id}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICON[id]}</svg><span>${name}</span></a>`;
  const el = document.createElement('header');
  el.className = 'appbar';
  el.innerHTML = `
    <a class="pill brand" href="#/dashboard" aria-label="Star Tracker">
      <svg viewBox="0 0 100 100" aria-hidden="true"><defs><linearGradient id="st-ig" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16243c"/><stop offset=".65" stop-color="#3b5a85"/><stop offset="1" stop-color="#c88f5a"/></linearGradient></defs>
        <rect width="100" height="100" rx="24" fill="url(#st-ig)"/><g fill="none" stroke="#fff" stroke-linecap="round" stroke-opacity=".5" stroke-width="2.4"><circle cx="50" cy="44" r="22"/><circle cx="50" cy="44" r="12"/></g>
        <path d="M50 22 L52.6 41.4 L72 44 L52.6 46.6 L50 66 L47.4 46.6 L28 44 L47.4 41.4Z" fill="#ffb43d"/>
        <path d="M0 80 L22 66 L36 72 L54 58 L70 70 L100 78 L100 100 L0 100Z" fill="#1d2738"/></svg>
      <b>Star Tracker</b><span class="sl">/</span><span class="here"></span></a>
    <nav class="pill screens" aria-label="Screens">${prim.map(link).join('')}
      <details class="more"><summary><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg><span>More</span></summary>
        <div class="menu">${more.map(link).join('')}</div></details></nav>
    <div class="pill status"><span id="link-chip" class="chip"><i></i><span>Offline</span></span>
      <div class="mode" role="group" aria-label="Display mode">
        <button type="button" value="day" title="Day"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M5 19l1.4-1.4M17.6 6.4L19 5"/></svg><span>Day</span></button>
        <button type="button" value="night" title="Night"><svg viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg><span>Night</span></button>
        <button type="button" value="red" title="Red (keeps your night vision)"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="7" style="fill:currentColor;stroke:none"/></svg><span>Red</span></button>
      </div></div>`;
  document.body.insertBefore(el, $('#view').parentNode);
  $$('.mode button', el).forEach((b) => b.addEventListener('click', () => window.StTheme.set(b.value)));
  window.StTheme.set(window.StTheme.get());
  el.addEventListener('click', (e) => { if (e.target.closest('.menu a')) $('details.more', el).open = false; });
}

function chip(s) {
  const el = $('#link-chip');
  if (!el) return;
  const map = { live: ['ok', s.head ? (s.info?.name || s.head.host) : 'Live'], connecting: ['w', 'Connecting'], reconnecting: ['w', 'Reconnecting'], offline: ['', 'Offline'] };
  const [cls, txt] = map[s.conn] || ['', s.conn];
  el.querySelector('i').className = cls;
  el.querySelector('span').textContent = txt;
  el.title = s.connWhy || '';
}

async function route() {
  const id = (location.hash.replace(/^#\/?/, '').split('?')[0]) || (store.conn === CONN.OFFLINE && !lastHead() ? 'connect' : 'dashboard');
  const def = SCREENS.find((s) => s[0] === id) || SCREENS[0];
  if (current && current.leave) { try { current.leave(); } catch (e) { console.error(e); } }
  $$('.screens a').forEach((a) => a.classList.toggle('on', a.dataset.id === def[0]));
  $('.more summary')?.classList.toggle('on', !def[2]);
  $('.brand .here').textContent = def[1];
  document.title = `Star Tracker · ${def[1]}`;
  let mod = loaded.get(def[0]);
  if (!mod) { mod = await import(`./screens/${def[0]}.js`); loaded.set(def[0], mod); }
  const view = $('#view');
  view.innerHTML = '';
  view.dataset.screen = def[0];
  current = mod;
  try { await mod.render(view, store); } catch (e) { console.error(e); view.innerHTML = `<div class="notice">This screen failed to load: ${esc(e.message)}</div>`; }
  window.scrollTo(0, 0);
  window.__screenReady = def[0];
}

/** Shared "not connected" notice for screens that need the head. */
export function needHead(root) {
  if (store.client && store.conn !== CONN.OFFLINE) return false;
  root.insertAdjacentHTML('afterbegin', `<div class="notice offline">No head connected. <a href="#/connect">Connect</a> to the head (or the simulator) first.</div>`);
  return true;
}

export function pageHead(eyebrow, title, sub = '') {
  return `<div class="pagehead"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1>${sub ? `<div class="sub">${sub}</div>` : ''}</div></div>`;
}

async function boot() {
  bar();
  store.on((s) => chip(s));
  window.addEventListener('hashchange', route);
  // auto-connect: ?head=host:port (tests, screenshots), else the last head used
  const q = new URLSearchParams(location.search);
  const pin = q.get('head');
  if (pin) {
    const [host, port] = pin.split(':');
    const info = await discoveryBridge.httpGetJson(`http://${host}:${port || 80}/startracker/v1/info`, 3000);
    if (info) await connectTo({ host, info, ws: `ws://${host}:${info.ws_port}${info.ws_path}`, http: `http://${host}:${info.http_port}`, via: 'pinned' });
  } else if (lastHead()) {
    findHeads().then((f) => { if (f.length && store.conn === CONN.OFFLINE) connectTo(f[0]); });
  }
  await route();
}
window.__st = store;   // for the screenshot and end-to-end scripts (app/tools/screenshots.mjs)
boot();
