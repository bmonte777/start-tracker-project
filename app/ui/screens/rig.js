// Rig: the five payload envelopes (D40) with their roll limits, balance check, wedge and pier settings.
import { $, $$, act, esc, needHead, pageHead, refreshConfig, store, toast } from '../app.js';
import { PAYLOADS } from '../../shared/models.js';

let off = null;
export function leave() { if (off) off(); }

// simple outline drawings of each payload class
const ART = [
  '<rect x="30" y="18" width="34" height="26" rx="4"/><rect x="64" y="22" width="26" height="18" rx="3"/><path d="M26 48h44"/>',
  '<rect x="18" y="18" width="30" height="24" rx="4"/><rect x="48" y="20" width="70" height="20" rx="5"/><path d="M78 40v8M66 48h24"/>',
  '<rect x="10" y="18" width="26" height="22" rx="4"/><rect x="36" y="16" width="96" height="26" rx="7"/><path d="M80 42v8M66 50h30"/>',
  '<rect x="16" y="20" width="100" height="18" rx="5"/><rect x="116" y="22" width="16" height="14" rx="2"/><path d="M40 38v6M90 38v6M30 46h70"/>',
  '<rect x="8" y="14" width="124" height="28" rx="6"/><rect x="132" y="20" width="12" height="16" rx="2"/><path d="M40 42v6M100 42v6M28 50h90"/>',
];

function rollArc(L, roll) {
  // roll scale −180…+30 drawn as an arc; allowed range green, the rest red, needle at the current roll
  const a = (r) => (-90 + (r + 75) * 1.2) * Math.PI / 180, p = (r, rad) => [110 + rad * Math.cos(a(r)), 110 + rad * Math.sin(a(r))];
  const arc = (r1, r2, cls) => { const [x1, y1] = p(r1, 80), [x2, y2] = p(r2, 80); return `<path class="${cls}" d="M${x1} ${y1} A80 80 0 ${Math.abs(r2 - r1) * 1.2 > 180 ? 1 : 0} 1 ${x2} ${y2}"/>`; };
  const [nx, ny] = p(Math.max(-180, Math.min(30, roll)), 66);
  let ticks = '';
  for (const r of [-180, -135, -90, -45, 0, 30]) { const [x, y] = p(r, 98); ticks += `<text x="${x}" y="${y + 4}" text-anchor="middle" style="fill:var(--muted);font:600 11px var(--font)">${r}°</text>`; }
  return `<svg viewBox="0 0 220 200" style="width:100%;max-width:320px;display:block;margin:0 auto">
    ${arc(-180, 30, 'ring')}<g style="stroke:var(--ok);stroke-width:8;fill:none;stroke-linecap:round">${arc(L.roll_lo_now_d, L.roll_hi_now_d, '')}</g>${ticks}
    <line x1="110" y1="110" x2="${nx}" y2="${ny}" style="stroke:var(--accent);stroke-width:4;stroke-linecap:round"/><circle cx="110" cy="110" r="5" fill="var(--accent)"/></svg>`;
}

export async function render(root) {
  root.innerHTML = pageHead('Rig', 'Payload and mounting', 'Pick the class closest to your camera and lens; the head sets its roll and altitude limits from it.') + `
  <div class="grid three">
    <section class="card lead span3"><h2>Payload envelope</h2><div class="payloads" id="pl">${PAYLOADS.map((p, i) => `<button class="tile" data-p="${p.n}">
      <svg viewBox="0 0 150 56" aria-hidden="true">${ART[i]}</svg><b>${esc(p.name)}</b><span>${p.mass_kg.toFixed(2)} kg · ${esc(p.mount)}</span></button>`).join('')}</div></section>
    <section class="card"><h2>Limits for this payload</h2><div id="arc"></div><table id="lim"></table></section>
    <section class="card"><h2>Mounting</h2>
      <label class="chk"><input type="checkbox" id="wedge"> Wedge fitted (EQ possible)</label>
      <label class="chk"><input type="checkbox" id="pier"> Pier extension fitted (lifts the altitude cap)</label>
      <div class="row2 mt"><label class="f">Mode<select id="mode" class="f"><option value="altaz">Alt-az</option><option value="eq">EQ (wedge)</option></select></label>
        <label class="f">Wedge tilt °<input id="wdeg" type="number" min="0" max="75" step="0.1"></label></div>
      <p class="small">For EQ set the wedge to your latitude (${Math.abs(store.config?.lat ?? 0).toFixed(1)}°): the azimuth axis becomes the polar axis, altitude is declination, roll frames.</p>
      <div class="btns"><button id="save" class="primary">Save mounting</button></div></section>
    <section class="card"><h2>Balance check</h2>
      <p>Balance the payload on the altitude axis first (slide the foot or plate until it sits level). The check then rocks altitude ±5° and compares the motor load each way.</p>
      <div class="btns"><button id="bal" class="primary">Run balance check</button></div><div id="balres" class="mt"></div></section>
  </div>`;
  if (needHead(root)) return;
  const c = () => store.client;
  const show = () => {
    const cfg = store.config, L = store.limits;
    if (!cfg) return;
    $$('#pl .tile', root).forEach((t) => t.classList.toggle('on', +t.dataset.p === cfg.payload));
    $('#wedge', root).checked = cfg.wedge_fitted; $('#pier', root).checked = cfg.pier_extension;
    $('#mode', root).value = cfg.mode; $('#wdeg', root).value = cfg.wedge_deg.toFixed(1);
    if (L) {
      $('#arc', root).innerHTML = rollArc(L, store.state?.axes.roll.pos_d ?? 0);
      const t = L.tripod_roll_d;
      $('#lim', root).innerHTML = `<tr><td>Roll (whole range)</td><td>${L.roll_min_d}° … +${L.roll_max_d}°</td></tr>
        <tr><td>Roll now (at this altitude)</td><td>${L.roll_lo_now_d.toFixed(0)}° … +${L.roll_hi_now_d.toFixed(0)}°</td></tr>
        <tr><td>Meets the tripod top at</td><td>${t.alt0 === null ? 'never' : t.alt0 + '°'} (alt 0) · ${t.alt45 === null ? 'never' : t.alt45 + '°'} (alt 45)</td></tr>
        <tr><td>Altitude</td><td>${L.alt_min_d}° … +${L.alt_max_d}°</td></tr>
        <tr><td>Altitude cap without pier</td><td>${L.alt_cap_d === null ? 'none' : L.alt_cap_d + '°'}</td></tr>
        <tr><td>Safety margin</td><td>${L.margin_d}°</td></tr>`;
    }
    const cal = store.state?.cal;
    if (cal && cal.routine === 'balance') {
      const r = cal.result;
      $('#balres', root).innerHTML = r ? `<div class="state ${r.verdict === 'balanced' ? 'ok' : ''}">${esc(r.verdict)}</div><table><tr><td>Load swinging up / down</td><td>${r.load_up} / ${r.load_down}</td></tr>
        <tr><td>Current up / down</td><td>${r.i_up_ma} / ${r.i_down_ma} mA</td></tr></table>${r.note ? `<p class="small">${esc(r.note)}</p>` : ''}`
        : `<div class="msg">${esc(cal.state.replace('_', ' '))}…</div>`;
    }
  };
  off = store.on((s, patch) => { if ('config' in patch || 'limits' in patch || 'state' in patch) show(); });
  show();
  $('#pl', root).addEventListener('click', (e) => {
    const t = e.target.closest('[data-p]');
    if (t) act(t, async () => { await c().setConfig({ payload: +t.dataset.p }); await refreshConfig(); }, 'Payload set: limits updated');
  });
  $('#save', root).onclick = (e) => act(e.target, async () => {
    await c().setConfig({ wedge_fitted: $('#wedge', root).checked, pier_extension: $('#pier', root).checked, mode: $('#mode', root).value, wedge_deg: +$('#wdeg', root).value });
    await refreshConfig();
  }, 'Mounting saved');
  $('#bal', root).onclick = (e) => act(e.target, async () => {
    if (store.state?.tracking) await c().track(false);
    await c().calBalance(5);
    toast('Swinging altitude ±5°…');
  });
}
