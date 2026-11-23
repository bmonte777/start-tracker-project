// PEC trainer: learn the periodic error left on an axis while tracking a star, then play it back (pec.*, API 1.1).
import { $, act, esc, needHead, pageHead, store } from '../app.js';

let off = null;
export function leave() { if (off) off(); }

function plot(cv, table, raw) {
  const g = cv.getContext('2d'), W = cv.width, H = cv.height;
  g.clearRect(0, 0, W, H);
  const all = [...table, ...(raw || [])], m = Math.max(2, ...all.map((x) => Math.abs(x))) * 1.15, y = (v) => H / 2 - v / m * (H / 2 - 14);
  g.strokeStyle = 'rgba(255,255,255,.18)'; g.beginPath(); g.moveTo(0, H / 2); g.lineTo(W, H / 2); g.stroke();
  g.fillStyle = '#9fb0c8'; g.font = '600 22px Inter, sans-serif'; g.fillText(`±${m.toFixed(1)}″`, 8, 26); g.fillText('one wave-generator turn (≈ 862 s at sidereal) →', 8, H - 10);
  const line = (arr, col, w) => { if (!arr || !arr.length) return; g.strokeStyle = col; g.lineWidth = w; g.beginPath(); arr.forEach((v, i) => { const x = i / (arr.length - 1) * W; i ? g.lineTo(x, y(v)) : g.moveTo(x, y(v)); }); g.stroke(); };
  line(raw, 'rgba(160,180,210,.7)', 2);
  line(table.map((v) => -v), getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#ffb43d', 4);
}

export async function render(root) {
  root.innerHTML = pageHead('Tracking accuracy', 'PEC trainer', 'Periodic error correction: the head learns the small repeating error of its gear train and cancels it.') + `
  <div class="grid three">
    <section class="card lead span2"><h2>Learned error</h2><canvas id="cv" class="chart" width="1200" height="440"></canvas>
      <div class="legend"><span><i style="background:rgba(160,180,210,.9)"></i>Measured (encoder minus plan, averaged)</span><span><i style="background:var(--accent)"></i>Smoothed: what PEC cancels</span></div></section>
    <section class="card"><h2>Status</h2><div id="st" class="state">—</div><div class="progress"><span id="bar" style="width:0"></span></div>
      <table class="mt"><tr><td>Axis</td><td id="ax">—</td></tr><tr><td>Cycles</td><td id="cy">—</td></tr><tr><td>Error peak-to-peak</td><td id="pp">—</td></tr><tr><td>Error RMS</td><td id="rms">—</td></tr><tr><td>Noise left</td><td id="nz">—</td></tr><tr><td>Saved on the head</td><td id="sv">—</td></tr></table></section>
    <section class="card span2"><h2>Record</h2>
      <ol class="how"><li>Go to a star near the meridian and the celestial equator and start tracking (Sky). On the wedge, use the polar axis (azimuth).</li>
        <li>Pick the axis and the number of cycles (one cycle ≈ 14 minutes), press Record and leave the head alone.</li><li>When it is ready, press Play: the head adds the correction while tracking. Save keeps it after a restart.</li></ol>
      <div class="row2 mt"><label class="f">Axis<select id="axis" class="f"><option value="0">Azimuth / polar</option><option value="1">Altitude / Dec</option><option value="2">Roll</option></select></label>
        <label class="f">Cycles<input id="cycles" type="number" min="1" max="10" value="2"></label></div>
      <div class="btns"><button id="rec" class="primary">Record</button><button id="stop">Stop</button><button id="play">Play</button><button id="noplay">Stop playing</button><button id="save">Save</button><button id="clear" class="danger">Clear</button></div></section>
    <section class="card"><h2>What to expect</h2><p class="small">The head already corrects lost motion from its output encoders five times a second (±2″ deadband). PEC adds the repeating part as a feed-forward, so the loop has less to catch up. In the simulator the error left after the loop is about 1–2″ peak to peak; the real number comes from the prototype (Phase 7).</p></section>
  </div>`;
  if (needHead(root)) return;
  const c = () => store.client;
  let lastState = '';
  const curve = async (axis) => { try { const r = await c().pecCurve(axis); plot($('#cv', root), r.table_as, r.raw_as); } catch (e) { /* not ready */ } };
  const show = (s) => {
    const p = s.state?.pec;
    if (!p) return;
    $('#st', root).textContent = { idle: 'Nothing learned', recording: `Recording · cycle ${Math.min(p.cycle + 1, p.cycles)} of ${p.cycles}`, ready: 'Ready to play', playing: 'Playing' }[p.state] || p.state;
    $('#st', root).className = 'state ' + (p.state === 'playing' ? 'ok' : '');
    $('#bar', root).style.width = (p.progress * 100) + '%';
    $('#ax', root).textContent = ['Azimuth / polar', 'Altitude / Dec', 'Roll'][p.axis];
    $('#cy', root).textContent = p.cycles; $('#pp', root).textContent = p.pp_as.toFixed(2) + '″'; $('#rms', root).textContent = p.rms_as.toFixed(2) + '″';
    $('#nz', root).textContent = p.noise_as.toFixed(2) + '″'; $('#sv', root).textContent = p.saved ? 'yes' : 'no';
    if (p.state !== lastState && (p.state === 'ready' || p.state === 'playing')) curve(p.axis);
    lastState = p.state;
  };
  off = store.on((s, pt) => { if ('state' in pt) show(s); });
  show(store);
  curve(0);
  $('#rec', root).onclick = (e) => act(e.target, () => c().pecRecord(+$('#axis', root).value, +$('#cycles', root).value), 'Recording: keep the head tracking');
  $('#stop', root).onclick = (e) => act(e.target, () => c().pecStop());
  $('#play', root).onclick = (e) => act(e.target, () => c().pecPlay(true), 'PEC playing');
  $('#noplay', root).onclick = (e) => act(e.target, () => c().pecPlay(false));
  $('#save', root).onclick = (e) => act(e.target, () => c().pecSave(), 'Saved on the head');
  $('#clear', root).onclick = (e) => act(e.target, async () => { await c().pecClear(+$('#axis', root).value); plot($('#cv', root), new Array(128).fill(0), []); });
}
