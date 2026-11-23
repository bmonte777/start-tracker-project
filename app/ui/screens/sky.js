// Sky: target catalogue (stars, Messier/NGC, planets, Sun, Moon), go-to, tracking rates, jog pad, guide pulses, park.
import { $, $$, act, esc, needHead, pageHead, store } from '../app.js';
import { altaz, counts, search } from '../../shared/catalog.js';
import { fmtDec, fmtRA } from '../../shared/models.js';
import { STARS } from '../../shared/catalog_data.js';

let off = null, timer = null;
export function leave() { if (off) off(); clearInterval(timer); }

const SPEEDS = [[0.02, '0.02°/s'], [0.25, '0.25°/s'], [2, '2°/s'], [8, '8°/s']];
const site = () => ({ lat: store.config?.lat ?? 38.72, lon: store.config?.lon ?? -9.14, elev_m: store.config?.elev_m ?? 0 });

function chart(sel) {
  const R = 240, C = 260, p = (az, alt) => { const r = R * (90 - alt) / 90, a = az * Math.PI / 180; return [C + r * Math.sin(a), C - r * Math.cos(a)]; };
  let g = '';
  for (const alt of [0, 30, 60]) g += `<circle class="grid" cx="${C}" cy="${C}" r="${R * (90 - alt) / 90}"/>`;
  for (let az = 0; az < 360; az += 45) { const [x, y] = p(az, 0); g += `<line class="grid" x1="${C}" y1="${C}" x2="${x}" y2="${y}"/>`; }
  for (const [n, az] of [['N', 0], ['E', 90], ['S', 180], ['W', 270]]) { const [x, y] = p(az, -6); g += `<text x="${x}" y="${y + 5}" text-anchor="middle">${n}</text>`; }
  const now = new Date(), s = site();
  for (const st of STARS) {
    if (st.m > 3.5) continue;
    const h = altaz(st.ra, st.dec, s, now);
    if (h.alt_d < 0) continue;
    const [x, y] = p(h.az_d, h.alt_d);
    g += `<circle class="star" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${Math.max(0.8, 3.6 - st.m * 0.8).toFixed(1)}"/>`;
  }
  if (window.Sun) { const sp = window.Sun.position(now, s.lat, s.lon); if (sp.alt > -2) { const [x, y] = p(sp.az, Math.max(0, sp.alt)); g += `<circle class="sun" cx="${x}" cy="${y}" r="8"/>`; } }
  if (window.Moon) { const mp = window.Moon.position(now, s.lat, s.lon); if (mp.alt > -2) { const [x, y] = p(mp.az, Math.max(0, mp.alt)); g += `<circle class="moon" cx="${x}" cy="${y}" r="7"/>`; } }
  if (sel && sel.alt_d > 0) { const [x, y] = p(sel.az_d, sel.alt_d); g += `<circle class="tgt" cx="${x}" cy="${y}" r="13"/>`; }
  const st = store.state;
  if (st) { const [x, y] = p(st.altaz.az_d, Math.max(-5, st.altaz.alt_d)); g += `<circle class="ptr" cx="${x}" cy="${y}" r="10"/><line class="ptr" x1="${x - 16}" y1="${y}" x2="${x - 6}" y2="${y}"/><line class="ptr" x1="${x + 6}" y1="${y}" x2="${x + 16}" y2="${y}"/>`; }
  return `<svg class="skychart" viewBox="0 0 520 520" role="img" aria-label="Sky chart, north up">${g}</svg>`;
}

export async function render(root) {
  const n = counts();
  root.innerHTML = pageHead('Go-to and tracking', 'Sky', `${n.stars} named stars, ${n.messier} Messier and ${n.dso - n.messier} bright NGC/IC objects, planets, Sun and Moon`) + `
  <div class="grid three">
    <section class="card lead">
      <h2>Target</h2>
      <input id="q" class="search" type="text" placeholder="Search: Andromeda, M42, Vega, Jupiter, NGC 7000…" autocomplete="off">
      <ol id="res" class="results"></ol>
    </section>
    <section class="card">
      <h2>Selected</h2>
      <div id="sel" class="big">Pick a target</div>
      <table id="seltab"></table>
      <div class="btns"><button id="goto" class="primary bigbtn" disabled>Go to and track</button><button id="syncbtn" disabled title="Tell the head it points at this target now">Sync here</button></div>
      <div class="hr"></div>
      <h3>Alt/Az position (hold, no tracking)</h3>
      <div class="row2"><label class="f">Azimuth °<input id="gaz" type="number" step="0.1" value="180"></label><label class="f">Altitude °<input id="galt" type="number" step="0.1" value="30"></label><button id="gotoaa">Go</button></div>
    </section>
    <section class="card"><h2>Sky now</h2><div id="skyc"></div><p class="small">Amber: where the head points. Green: the selected target. Stars to magnitude 3.5.</p></section>
    <section class="card">
      <h2>Tracking</h2>
      <div class="seg" id="rates"><button value="sidereal" class="on">Stars</button><button value="lunar">Moon</button><button value="solar">Sun</button><button value="king">King</button></div>
      <div class="btns"><button id="trkon" class="primary">Track</button><button id="trkoff">Stop tracking</button></div>
      <div class="hr"></div>
      <h3>Park</h3>
      <div class="btns"><button id="park">Park</button><button id="unpark">Unpark</button><button id="setpark" title="Store this pose as the park position">Set park here</button></div>
      <p class="small">Parking turns roll to 0° first (P5 only stays put within ±43° without power).</p>
    </section>
    <section class="card">
      <h2>Move</h2>
      <div class="seg" id="speeds">${SPEEDS.map(([v, l], i) => `<button value="${v}" ${i === 1 ? 'class="on"' : ''}>${l}</button>`).join('')}</div>
      <div class="row mt" style="justify-content:space-around;align-items:center">
        <div class="jog" id="jog">
          <span class="blank"></span><button data-ax="1" data-dir="1" aria-label="Up">▲</button><span class="blank"></span>
          <button data-ax="0" data-dir="-1" aria-label="Left">◀</button><button class="stop" id="jstop">STOP</button><button data-ax="0" data-dir="1" aria-label="Right">▶</button>
          <span class="blank"></span><button data-ax="1" data-dir="-1" aria-label="Down">▼</button><span class="blank"></span></div>
        <div class="stack"><button data-ax="2" data-dir="1">Roll ↻</button><button data-ax="2" data-dir="-1">Roll ↺</button></div>
      </div>
      <p class="small">Hold a button to move; let go to stop. Tracking carries on from the new position.</p>
    </section>
    <section class="card">
      <h2>Guide pulses</h2>
      <div class="row2"><label class="f">Length ms<input id="gms" type="number" value="500" min="10" step="10"></label></div>
      <div class="btns" id="guide"><button value="n">North</button><button value="s">South</button><button value="e">East</button><button value="w">West</button></div>
      <p class="small">At the guide rate set in Settings (× sidereal). For nudging a framing or testing guiding.</p>
    </section>
  </div>`;
  const offline = needHead(root);
  let sel = null, rate = 'sidereal', speed = 0.25, results = [];
  const showRes = () => {
    const s = site(), now = new Date();
    results = search($('#q', root).value, { limit: 40, site: s }).map((r) => {
      if (r.ra !== undefined && r.alt_d === undefined) Object.assign(r, altaz(r.ra, r.dec, s, now));
      if (r.body && window.Sun && window.Moon) { const p = r.body === 'sun' ? window.Sun.position(now, s.lat, s.lon) : window.Moon.position(now, s.lat, s.lon); r.alt_d = p.alt; r.az_d = p.az; }
      return r;
    });
    $('#res', root).innerHTML = results.map((r, i) => `<li data-i="${i}" class="${sel && sel.name === r.name ? 'sel' : ''}"><span class="t"><b>${esc(r.name)}${r.common ? ' · ' + esc(r.common) : ''}</b>${esc(r.type)}${r.mag !== undefined ? ' · mag ' + r.mag : ''}</span>
      <span class="k ${r.alt_d > 0 ? 'ok-t' : 'dim'}">${r.alt_d !== undefined ? (r.alt_d > 0 ? '▲ ' : '▼ ') + r.alt_d.toFixed(0) + '°' : ''}</span></li>`).join('');
  };
  const showSel = () => {
    $('#sel', root).textContent = sel ? sel.name + (sel.common ? ' · ' + sel.common : '') : 'Pick a target';
    $('#seltab', root).innerHTML = sel ? `${sel.ra !== undefined ? `<tr><td>RA / Dec (J2000)</td><td>${fmtRA(sel.ra)}<br>${fmtDec(sel.dec)}</td></tr>` : ''}
      <tr><td>Altitude now</td><td>${sel.alt_d !== undefined ? sel.alt_d.toFixed(1) + '°' : '—'}</td></tr><tr><td>Azimuth now</td><td>${sel.az_d !== undefined ? sel.az_d.toFixed(1) + '°' : '—'}</td></tr>
      ${sel.size ? `<tr><td>Size</td><td>${sel.size}′</td></tr>` : ''}${sel.alt ? `<tr><td>Also</td><td>${esc(sel.alt)}</td></tr>` : ''}` : '';
    $('#goto', root).disabled = !sel || offline || (sel.alt_d !== undefined && sel.alt_d < -5);
    $('#syncbtn', root).disabled = !sel || offline || sel.body || sel.ra === undefined;
    $('#skyc', root).innerHTML = chart(sel);
  };
  $('#q', root).addEventListener('input', showRes);
  $('#res', root).addEventListener('click', (e) => { const li = e.target.closest('li[data-i]'); if (!li) return; sel = results[+li.dataset.i]; showRes(); showSel(); });
  const c = () => store.client;
  $('#goto', root).onclick = (e) => act(e.target, () => (sel.body ? c().gotoBody(sel.body) : c().gotoRaDec(sel.ra, sel.dec, 'J2000')), `Going to ${sel.name}`);
  $('#syncbtn', root).onclick = (e) => act(e.target, () => c().sync(sel.ra, sel.dec), 'Synced: pointing model updated');
  $('#gotoaa', root).onclick = (e) => act(e.target, () => c().gotoAltAz(+$('#gaz', root).value, +$('#galt', root).value));
  $('#rates', root).addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; rate = b.value; $$('#rates button', root).forEach((x) => x.classList.toggle('on', x === b)); });
  $('#speeds', root).addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; speed = +b.value; $$('#speeds button', root).forEach((x) => x.classList.toggle('on', x === b)); });
  $('#trkon', root).onclick = (e) => act(e.target, () => c().track(true, rate), 'Tracking');
  $('#trkoff', root).onclick = (e) => act(e.target, () => c().track(false));
  $('#park', root).onclick = (e) => act(e.target, () => c().park(), 'Parking');
  $('#unpark', root).onclick = (e) => act(e.target, () => c().unpark());
  $('#setpark', root).onclick = (e) => act(e.target, () => c().setPark(), 'Park position stored');
  $('#jstop', root).onclick = (e) => act(e.target, () => c().stop());
  $('#guide', root).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) act(b, () => c().guide(b.value, +$('#gms', root).value)); });
  // press and hold to jog
  $$('[data-ax]', root).forEach((b) => {
    const start = (ev) => { ev.preventDefault(); if (!c()) return; b.setPointerCapture?.(ev.pointerId); c().jog(+b.dataset.ax, speed * +b.dataset.dir).catch((er) => import('../app.js').then((m) => m.toast(er.headMsg || er.message, 'bad'))); };
    const stop = () => { if (c()) c().jog(+b.dataset.ax, 0).catch(() => {}); };
    b.addEventListener('pointerdown', start);
    b.addEventListener('pointerup', stop);
    b.addEventListener('pointercancel', stop);
  });
  off = store.on((s, patch) => { if ('state' in patch) $('#skyc', root).innerHTML = chart(sel); });
  timer = setInterval(showRes, 30000);
  showRes();
  showSel();
}
