// Alignment wizard: sync points (by eye or by plate solve), pointing-model points and RMS; polar alignment on the wedge.
import { $, act, esc, needHead, pageHead, prefs, store, toast, waitJob } from '../app.js';
import { altaz, search } from '../../shared/catalog.js';
import { fmtDec, fmtRA } from '../../shared/models.js';
import { polarError } from '../../shared/polar.js';
import { camera } from '../../shared/native.js';

let off = null;
export function leave() { if (off) off(); }

const site = () => ({ lat: store.config?.lat ?? 38.72, lon: store.config?.lon ?? -9.14 });

/** Three bright stars, well apart, 25–75° up, for a model: picked by spreading them in azimuth. */
function suggest() {
  const s = site(), now = new Date();
  const c = search('', { limit: 400, site: s }).filter((x) => x.type === 'star' && x.mag < 2.2)
    .map((x) => ({ ...x, ...altaz(x.ra, x.dec, s, now) })).filter((x) => x.alt_d > 25 && x.alt_d < 75).sort((a, b) => a.mag - b.mag);
  const out = [];
  for (const st of c) { if (out.every((o) => Math.abs(((st.az_d - o.az_d + 540) % 360) - 180) > 60)) out.push(st); if (out.length === 3) break; }
  return out;
}

function termsFor(n) { return n === 0 ? 'none' : n <= 2 ? 'two index offsets' : n <= 5 ? 'index offsets and the two tilts of the first axis' : 'all seven terms (index ×2, collimation, non-perpendicularity, tilts ×2, flexure)'; }

export async function render(root) {
  const eq = store.config?.mode === 'eq';
  root.innerHTML = pageHead('Alignment', 'Alignment wizard', eq ? 'EQ on the wedge: polar-align first, then add sync points.' : 'Alt-az: level the head, then add two or three sync points.') + `
  <div class="grid three">
    <section class="card lead span2">
      <h2>Sync points</h2>
      <div class="steps" id="steps"></div>
      <div class="btns"><button id="refresh">Pick other stars</button><button id="clear" class="danger">Clear the model</button></div>
    </section>
    <section class="card">
      <h2>Pointing model</h2>
      <div class="state" id="pts">—</div>
      <table><tr><td>Fit RMS</td><td id="rms">—</td></tr><tr><td>Terms fitted</td><td id="terms" style="white-space:normal;font-family:var(--font)">—</td></tr></table>
      <p class="small mt">1–2 points fit the index offsets; 3–5 add the tilts of the first axis; 6 or more fit all seven terms. Each plate-solve sync adds a point.</p>
    </section>
    <section class="card span2">
      <h2>Plate-solve sync</h2>
      <p>Take a frame with the camera, solve it, and tell the head where it really points. ${camera.present() ? '' : '<b>No camera on USB-C:</b> type a solve result from any solver (ASTAP, astrometry.net) below.'}</p>
      <div class="btns"><button id="solve" class="primary" ${camera.present() ? '' : 'disabled'}>Shoot, solve and sync</button></div>
      <div class="row2 mt"><label class="f">RA (hours, J2000)<input id="sra" type="number" step="0.0001" placeholder="5.27815"></label>
        <label class="f">Dec (°, J2000)<input id="sdec" type="number" step="0.0001" placeholder="45.998"></label><button id="sync">Sync to this</button></div>
      <div id="solvemsg" class="msg mt"></div>
    </section>
    <section class="card" ${eq ? '' : 'style="opacity:.75"'}>
      <h2>Polar alignment (wedge)</h2>
      <p class="small">${eq ? 'Point roughly at the pole. The app solves three frames while it turns the polar axis 0°, 30°, 60°.' : 'Only used on the wedge (EQ). Switch the mode in Rig.'}</p>
      <ol class="how"><li>Wedge set to your latitude (${Math.abs(site().lat).toFixed(1)}°), polar axis roughly north.</li><li>Press <b>Measure</b>; keep the tripod still.</li><li>Turn the latitude screw (≈55′ per turn) and the head base as shown, then measure again.</li></ol>
      <div class="btns"><button id="polar" ${eq && camera.present() ? '' : 'disabled'}>Measure</button></div>
      <div id="polarres" class="mt"></div>
    </section>
  </div>`;
  if (needHead(root)) return;
  const c = () => store.client;
  let stars = suggest(), done = new Set();
  const steps = () => {
    $('#steps', root).innerHTML = stars.map((s, i) => `<div class="step ${done.has(s.name) ? 'done' : ''}"><div style="flex:1"><b>${esc(s.name)}</b> <span class="small">mag ${s.mag} · alt ${s.alt_d.toFixed(0)}° az ${s.az_d.toFixed(0)}°</span>
      <div class="small">Go to it, centre it with the arrows on Sky (or solve), then sync.</div>
      <div class="btns"><button data-go="${i}">Go to</button><button data-sync="${i}" class="primary">Centred: sync</button></div></div></div>`).join('') || '<div class="notice">No bright star is between 25° and 75° up right now. Use plate-solve syncs instead.</div>';
  };
  steps();
  $('#steps', root).addEventListener('click', (e) => {
    const g = e.target.closest('[data-go]'), sy = e.target.closest('[data-sync]');
    if (g) { const s = stars[+g.dataset.go]; act(g, () => c().gotoRaDec(s.ra, s.dec), `Going to ${s.name}`); }
    if (sy) { const s = stars[+sy.dataset.sync]; act(sy, async () => { await c().sync(s.ra, s.dec); done.add(s.name); steps(); }, `${s.name} added to the model`); }
  });
  $('#refresh', root).onclick = () => { stars = suggest().reverse(); steps(); };
  $('#clear', root).onclick = (e) => act(e.target, async () => { await c().alignClear(); done.clear(); steps(); }, 'Model cleared');
  $('#sync', root).onclick = (e) => act(e.target, async () => {
    const ra = parseFloat($('#sra', root).value), dec = parseFloat($('#sdec', root).value);
    if (!(ra >= 0 && ra < 24) || !(Math.abs(dec) <= 90)) throw new Error('type RA in hours (0–24) and Dec in degrees');
    await c().sync(ra, dec);
    $('#solvemsg', root).textContent = `Synced to ${fmtRA(ra)} ${fmtDec(dec)}.`;
  }, 'Sync point added');
  // Plate solve with the reused solver (CameraNative.startSolve / lastSolve from Benro-Polaris-Controller)
  const solveOnce = async () => {
    const st = store.state;
    camera.call('startSolve', JSON.stringify({ action: 'solve', focal: prefs.get('focal_mm', 0), sensorWidth: prefs.get('sensor_w_mm', 35.7), targetRa: st.radec.ra_h, targetDec: st.radec.dec_d, searchRadius: 8 }));
    for (let i = 0; i < 120; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const r = camera.call('lastSolve');
      if (r && r.done) { if (!r.ok) throw new Error(r.error || 'no solution'); return r; }
    }
    throw new Error('the solver did not finish in 2 minutes');
  };
  $('#solve', root).onclick = (e) => act(e.target, async () => {
    const r = await solveOnce();
    await c().sync(r.ra, r.dec);
    $('#solvemsg', root).textContent = `Solved ${fmtRA(r.ra)} ${fmtDec(r.dec)} (${(r.rms ?? 0).toFixed(2)} px fit); synced.`;
  });
  $('#polar', root).onclick = (e) => act(e.target, async () => {
    const solves = [];
    const az0 = store.state.axes.az.pos_d, alt0 = store.state.axes.alt.pos_d;
    await c().track(false);
    for (const d of [0, 30, 60]) {
      await c().request('job.start', { type: 'poses', shutter: 'none', poses: [{ az_d: (az0 + d) % 360, alt_d: alt0 }], settle_s: 2 });
      await waitJob(c(), 120000);
      const r = await solveOnce();
      solves.push({ ra_h: r.ra_now ?? r.ra, dec_d: r.dec_now ?? r.dec, t: new Date() });
    }
    const pe = polarError(solves, site());
    $('#polarres', root).innerHTML = `<table><tr><td>Total error</td><td>${pe.total_arcmin.toFixed(1)}′</td></tr><tr><td>Altitude</td><td>${pe.err_alt_arcmin.toFixed(1)}′</td></tr>
      <tr><td>Azimuth</td><td>${pe.err_az_arcmin.toFixed(1)}′</td></tr></table><div class="warn">${esc(pe.alt_hint)} (about ${pe.screw_turns.toFixed(1)} turns). ${esc(pe.az_hint)}.</div>`;
    toast('Polar error measured');
  });
  const upd = (s) => {
    const m = s.state?.model;
    if (!m) return;
    $('#pts', root).textContent = `${m.points} point${m.points === 1 ? '' : 's'}`;
    $('#pts', root).className = 'state ' + (m.points ? 'ok' : '');
    $('#rms', root).textContent = m.points >= 2 ? m.rms_as.toFixed(1) + '″' : '—';
    $('#terms', root).textContent = termsFor(m.points);
  };
  off = store.on(upd);
  upd(store);
}
