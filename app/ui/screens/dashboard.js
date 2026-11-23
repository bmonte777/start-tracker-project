// Dashboard: where the head points, the three axes (commanded and encoder), tracking, battery, motor rail, faults.
import { $, act, esc, fmt, needHead, pageHead, store } from '../app.js';
import { fmtDec, fmtRA } from '../../shared/models.js';

let off = null;
export function leave() { if (off) off(); }

const AX = [['az', 'Azimuth', 'pan'], ['alt', 'Altitude', 'tilt'], ['roll', 'Roll', 'framing']];
const MODE = { idle: 'Idle', slewing: 'Slewing', tracking: 'Tracking', moving: 'Moving', parking: 'Parking', parked: 'Parked', fault: 'Fault' };
const MFAULTS = ['link lost', 'VMOT low', 'VMOT high', 'driver UART', 'driver over-temp', 'driver short', 'encoder', 'motor over-temp', 'slip', 'stall', 'limit', 'setpoint stale', 'tip-over', 'watchdog', 'power budget'];
const FLAGS = [[0, 'at min'], [1, 'at max'], [2, 'stall'], [3, 'driver diag'], [4, 'derated'], [5, 'encoder bad'], [6, 'slip'], [7, 'correcting'], [8, 'SpreadCycle'], [9, 'calibrated']];

function dial(cmd, enc) {
  const pt = (a, r) => [60 + r * Math.sin(a * Math.PI / 180), 60 - r * Math.cos(a * Math.PI / 180)];
  let ticks = '';
  for (let a = 0; a < 360; a += 30) { const [x1, y1] = pt(a, 44), [x2, y2] = pt(a, 50); ticks += `<line class="tick" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`; }
  const [cx, cy] = pt(cmd, 40), [ex, ey] = pt(enc, 46);
  return `<svg class="dial" viewBox="0 0 120 120" aria-hidden="true"><circle class="ring" cx="60" cy="60" r="47"/>${ticks}
    <line class="enc" x1="60" y1="60" x2="${ex}" y2="${ey}"/><line class="cmd" x1="60" y1="60" x2="${cx}" y2="${cy}"/><circle cx="60" cy="60" r="3" fill="var(--accent)"/></svg>`;
}

export async function render(root) {
  root.innerHTML = pageHead('Head · live', 'Dashboard', '') + '<div id="dash"></div>';
  if (needHead(root)) return;
  const box = $('#dash', root);
  box.innerHTML = `
  <div class="grid three">
    <section class="card lead span2">
      <div class="row between"><h2 style="margin:0">Sky position</h2><span id="t" class="small k"></span></div>
      <div id="mode" class="state">…</div>
      <div class="readout">
        <div><small>RA (J2000)</small><b id="ra">—</b></div><div><small>Dec (J2000)</small><b id="dec">—</b></div>
        <div><small>Azimuth</small><b id="az">—</b></div><div><small>Altitude</small><b id="alt">—</b></div>
        <div><small>RA (now)</small><b id="ran">—</b></div><div><small>Dec (now)</small><b id="decn">—</b></div>
        <div><small>Position angle</small><b id="pa">—</b></div><div><small>Frame</small><b id="frame">—</b></div>
      </div>
      <div class="btns">
        <button id="stop" class="danger bigbtn">Stop all</button>
        <button id="trk" class="bigbtn">Tracking</button>
        <button id="park" class="bigbtn">Park</button>
        <a href="#/sky"><button class="primary bigbtn">Go to…</button></a>
      </div>
    </section>
    <section class="card">
      <h2>Battery</h2>
      <div class="hero"><svg class="ring" viewBox="0 0 120 120" aria-hidden="true"><circle class="trk" cx="60" cy="60" r="50" fill="none" stroke-width="10"/>
        <circle id="socring" class="val" cx="60" cy="60" r="50" fill="none" stroke-width="10" stroke-linecap="round" transform="rotate(-90 60 60)" stroke-dasharray="0 400"/>
        <text id="soc" x="60" y="68" text-anchor="middle" style="fill:var(--ink);font:700 26px var(--font)">—</text></svg>
        <table><tr><td>Pack</td><td id="bv">—</td></tr><tr><td>Temperature</td><td id="bt">—</td></tr><tr><td>USB-C power in</td><td id="bext">—</td></tr><tr><td>Motion budget</td><td id="bud">—</td></tr></table></div>
      <div id="battwarn"></div>
    </section>
    <section class="card span3">
      <div class="row between"><h2 style="margin:0">Axes</h2><span class="small">amber: commanded · dashed: encoder</span></div>
      <div class="axes mt">${AX.map(([k, n, w]) => `<div class="axis" id="ax-${k}"><div class="name"><span>${n} <span class="dim" style="letter-spacing:0;text-transform:none">· ${w}</span></span><span class="pill-num" data-f="mode">—</span></div>
        <div class="row" style="flex-wrap:nowrap"><div style="flex:1;min-width:0"><div class="ang" data-f="pos">—</div><div class="enc" data-f="enc">—</div>
        <div class="enc" data-f="rate">—</div></div><div style="width:96px" data-f="dial"></div></div>
        <div class="bars"><span>Current</span><div class="meter"><span data-f="ibar"></span></div><span class="k" data-f="i">—</span>
        <span>Load</span><div class="meter"><span data-f="lbar"></span></div><span class="k" data-f="load">—</span>
        <span>Motor</span><div class="meter"><span data-f="tbar"></span></div><span class="k" data-f="temp">—</span></div>
        <div class="chips mt" data-f="flags"></div></div>`).join('')}</div>
    </section>
    <section class="card">
      <h2>Motor rail and link</h2>
      <table><tr><td>Rail</td><td id="rail">—</td></tr><tr><td>VMOT</td><td id="vmot">—</td></tr><tr><td>Motion processor link</td><td id="link">—</td></tr>
        <tr><td>Motion faults</td><td id="mf">—</td></tr><tr><td>Pointing model</td><td id="model">—</td></tr><tr><td>Intervalometer</td><td id="ivm">—</td></tr></table>
    </section>
    <section class="card" id="jobcard"><h2>Job</h2><div id="job" class="msg">No job running.</div><div class="progress mt"><span id="jobbar" style="width:0"></span></div></section>
    <section class="card"><div class="row between"><h2 style="margin:0">Messages</h2><a href="#/health" class="small">Fault log</a></div><ol id="faults" class="mt"></ol></section>
  </div>`;
  const q = (id) => $('#' + id, box);
  const update = (s) => {
    const st = s.state;
    if (!st) return;
    q('t').textContent = st.t.replace('T', ' ').slice(0, 19) + ' UTC';
    q('mode').textContent = (MODE[st.mode] || st.mode) + (st.tracking && st.mode !== 'tracking' ? ' · tracking on' : '');
    q('mode').className = 'state ' + (st.mode === 'fault' ? 'bad' : st.mode === 'idle' && !st.tracking ? '' : 'ok');
    q('ra').textContent = fmtRA(st.radec.ra_h); q('dec').textContent = fmtDec(st.radec.dec_d);
    q('ran').textContent = fmtRA(st.radec.ra_now_h); q('decn').textContent = fmtDec(st.radec.dec_now_d);
    q('az').textContent = st.altaz.az_d.toFixed(3) + '°'; q('alt').textContent = st.altaz.alt_d.toFixed(3) + '°';
    q('pa').textContent = st.radec.rot_d.toFixed(2) + '°'; q('frame').textContent = st.frame === 'eq' ? 'EQ (wedge)' : 'Alt-az';
    q('trk').textContent = st.tracking ? 'Tracking: on' : 'Tracking: off';
    q('trk').classList.toggle('primary', st.tracking);
    q('park').textContent = st.parked ? 'Unpark' : 'Park';
    for (const [k] of AX) {
      const a = st.axes[k], el = q('ax-' + k), f = (n) => el.querySelector(`[data-f="${n}"]`);
      f('pos').textContent = a.pos_d.toFixed(4) + '°';
      const d = (a.enc_d - a.pos_d) * 3600;
      f('enc').textContent = `enc ${a.enc_d.toFixed(4)}° (${d >= 0 ? '+' : ''}${d.toFixed(1)}″)`;
      f('rate').textContent = Math.abs(a.rate_dps) < 0.01 ? `${(a.rate_dps * 3600).toFixed(2)} ″/s` : `${a.rate_dps.toFixed(3)} °/s`;
      f('dial').innerHTML = dial(a.pos_d, a.enc_d);
      f('i').textContent = a.i_ma + ' mA'; f('ibar').style.width = Math.min(100, a.i_ma / 13) + '%';
      f('load').textContent = a.load; f('lbar').style.width = Math.max(0, Math.min(100, 100 - a.load / 5.11)) + '%';
      f('temp').textContent = a.temp_c.toFixed(0) + ' °C'; f('tbar').style.width = Math.min(100, a.temp_c / 0.95) + '%';
      f('mode').textContent = Math.abs(a.rate_dps) > 0.05 ? 'moving' : Math.abs(a.rate_dps) > 1e-6 ? 'tracking' : 'holding';
      f('flags').innerHTML = FLAGS.filter(([b]) => a.flags & (1 << b)).map(([b, n]) => `<span class="chip"><i class="${b === 9 ? 'ok' : b === 7 || b === 8 ? '' : 'w'}"></i>${n}</span>`).join('');
    }
    const b = st.batt;
    q('soc').textContent = Math.round(b.soc) + '%';
    q('socring').setAttribute('stroke-dasharray', `${(b.soc / 100) * 314} 400`);
    q('bv').textContent = b.v.toFixed(2) + ' V'; q('bt').textContent = b.temp_c.toFixed(0) + ' °C';
    q('bext').textContent = b.ext ? 'yes' : 'no'; q('bud').textContent = b.motion_budget_w.toFixed(1) + ' W';
    q('battwarn').innerHTML = b.soc <= 15 ? `<div class="warn">Battery ${Math.round(b.soc)} %: at 5 % (or 6.2 V) the head finishes the exposure, parks with roll at 0° and sleeps.</div>` : '';
    const m = st.motor;
    q('rail').textContent = ['off', '10 V (tracking)', '16 V (slew)'][m.rail] || m.rail;
    q('vmot').textContent = m.vmot ? m.vmot.toFixed(2) + ' V' : '—';
    q('link').innerHTML = m.link ? '<span class="ok-t">OK</span>' : '<span class="bad-t">lost</span>';
    q('mf').textContent = m.faults ? MFAULTS.filter((n, i) => m.faults & (1 << i)).join(', ') || '0x' + m.faults.toString(16) : 'none';
    q('model').textContent = st.model.points ? `${st.model.points} points, ${st.model.rms_as.toFixed(1)}″ RMS` : 'no points';
    q('ivm').textContent = st.ivm.running ? `${st.ivm.done} of ${st.ivm.count || '∞'}` : 'off';
    const j = st.job;
    q('job').textContent = j ? `${j.type} · frame ${j.frame} of ${j.frames} · ${j.state.replace('_', ' ')}${j.reason ? ' · ' + j.reason : ''} · about ${Math.round(j.eta_s / 60)} min left` : 'No job running.';
    q('jobbar').style.width = j ? (100 * (j.frame - 1) / j.frames) + '%' : '0';
    q('faults').innerHTML = st.faults.length ? st.faults.slice(-6).reverse().map((f) => `<li><span class="t">${esc(f)}</span></li>`).join('') : '<li><span class="t">None.</span></li>';
  };
  off = store.on(update);
  update(store);
  const c = () => store.client;
  q('stop').onclick = (e) => act(e.target, () => c().stop(), 'Stopped');
  q('trk').onclick = (e) => act(e.target, () => c().track(!store.state?.tracking));
  q('park').onclick = (e) => act(e.target, () => (store.state?.parked ? c().unpark() : c().park()));
}
