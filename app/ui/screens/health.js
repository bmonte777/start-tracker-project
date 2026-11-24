// Encoder and battery health: residuals per axis, encoder calibration (the Q47 routine, cal.encoder.*), battery, fault log.
import { $, act, esc, needHead, pageHead, store, toast } from '../app.js';

let off = null, timer = null;
export function leave() { if (off) off(); clearInterval(timer); }

export async function render(root) {
  root.innerHTML = pageHead('Head health', 'Encoders and battery', 'What the three output encoders and the pack report, and the encoder calibration.') + `
  <div class="grid three">
    <section class="card lead span2"><h2>Encoders</h2><table class="t" id="enc"><tr><th>Axis</th><th>Calibrated</th><th>Encoder − plan (RMS)</th><th>Mean</th><th>Motor</th><th>Load</th></tr></table>
      <p class="small mt">Encoder − plan is measured while an axis holds or tracks: it holds the encoder noise (0.0015° = 5.4″ per reading, about 0.4″ after the 5 Hz average) and the reducer’s own periodic error.</p></section>
    <section class="card"><h2>Battery</h2><table id="bat"></table><p class="small">From the pack's gauge (BQ40Z50). State of health is the pack's capacity now against new; below about 80 % expect noticeably shorter nights.</p></section>
    <section class="card span2"><h2>Encoder calibration</h2>
      <p>Each MT6835 encoder is about ±250″ out of true when new. The head turns one axis slowly over its whole travel, using the gear train as the reference, fits the error and stores a map. Do it once per head, with the payload off, the head level and nothing in the way (azimuth makes a full turn).</p>
      <div class="row2"><label class="f">Axis<select id="cax" class="f"><option value="0">Azimuth (full turn)</option><option value="1">Altitude (−7° … 90°)</option><option value="2">Roll (payload range)</option></select></label>
        <label class="f">Speed °/s<input id="cspd" type="number" value="0.5" min="0.05" max="2" step="0.05"></label></div>
      <div class="btns"><button id="cstart" class="primary">Start calibration</button><button id="capply">Apply the map</button><button id="cabort" class="danger">Abort</button></div>
      <div class="progress mt"><span id="cbar" style="width:0"></span></div><div id="cres" class="mt"></div></section>
    <section class="card"><h2>Drivers and rail</h2><table id="drv"></table></section>
    <section class="card span3"><div class="row between"><h2 style="margin:0">Fault log</h2><div class="row"><span class="small" id="fpers"></span><button id="fref">Refresh</button><button id="fclr">Clear</button></div></div>
      <table class="t mt" id="flog"></table></section>
  </div>`;
  if (needHead(root)) return;
  const c = () => store.client;
  // cells more than 50 mV apart point to a weak cell or a balancing problem
  const cellNote = (cv) => { const d = Math.abs(cv[0] - cv[1]) * 1000; return d > 50 ? ` <span class="warn-t">${d.toFixed(0)} mV apart</span>` : ''; };
  const health = async () => {
    try {
      const h = await c().health();
      $('#enc', root).innerHTML = '<tr><th>Axis</th><th>Calibrated</th><th>Encoder − plan (RMS)</th><th>Mean</th><th>Motor</th><th>Load</th></tr>' + h.axes.map((a) => `<tr><td>${esc(a.axis)}</td>
        <td>${a.calibrated ? '<span class="ok-t">yes</span>' : '<span class="warn-t">no</span>'}${a.encoder_ok ? '' : ' <span class="bad-t">encoder fault</span>'}</td>
        <td class="k">${a.enc_minus_cmd_rms_as.toFixed(2)}″</td><td class="k">${a.enc_minus_cmd_mean_as.toFixed(2)}″</td><td class="k">${a.temp_c} °C · ${a.i_ma} mA</td><td class="k">${a.load}</td></tr>`).join('');
      const b = h.battery;
      $('#bat', root).innerHTML = `<tr><td>Charge</td><td>${b.soc} %</td></tr><tr><td>Voltage</td><td>${b.v.toFixed(2)} V</td></tr><tr><td>Temperature</td><td>${b.temp_c} °C</td></tr>
        <tr><td>USB-C power in</td><td>${b.ext ? 'yes' : 'no'}</td></tr><tr><td>Motion budget</td><td>${b.motion_budget_w.toFixed(1)} W</td></tr>
        <tr><td>Charge cycles</td><td>${b.cycles ?? 'not read yet'}</td></tr>
        <tr><td>State of health</td><td>${b.soh_pct == null ? 'not read yet' : `<span class="${b.soh_pct >= 80 ? 'ok-t' : b.soh_pct >= 65 ? 'warn-t' : 'bad-t'}">${b.soh_pct} %</span>`}</td></tr>
        <tr><td>Cells</td><td>${Array.isArray(b.cells_v) ? b.cells_v.map((v) => v.toFixed(3) + ' V').join(' · ') + cellNote(b.cells_v) : 'not read yet'}</td></tr>`;
      $('#drv', root).innerHTML = `<tr><td>Motor rail</td><td>${['off', '10 V', '16 V'][h.motor.rail] ?? h.motor.rail} · ${h.motor.vmot.toFixed(2)} V</td></tr>
        <tr><td>Motion faults</td><td>${h.motor.faults ? '0x' + h.motor.faults.toString(16) : 'none'}</td></tr><tr><td>Link to the motion processor</td><td>${h.link_ok ? 'OK' : 'lost'}</td></tr>
        <tr><td>Messages since start</td><td>${h.faults_total}</td></tr><tr><td>Running on</td><td>${esc(h.platform)}</td></tr>`;
    } catch (e) { /* offline */ }
  };
  const flog = async () => {
    try {
      const f = await c().faults(0);
      $('#fpers', root).textContent = f.persistent ? 'kept in the head\'s flash: it survives a restart' : 'kept in memory until the head restarts';
      $('#flog', root).innerHTML = '<tr><th>#</th><th>Time (UTC)</th><th>Level</th><th>Message</th></tr>' + (f.entries.slice().reverse().map((e) => `<tr><td class="k">${e.seq}</td><td class="k">${esc(e.t.slice(0, 19).replace('T', ' '))}</td>
        <td>${e.level === 'fault' ? '<span class="bad-t">fault</span>' : '<span class="warn-t">warning</span>'}</td><td>${esc(e.msg)}</td></tr>`).join('') || '<tr><td colspan="4">Empty.</td></tr>');
    } catch (e) { /* offline */ }
  };
  const cal = (s) => {
    const k = s.state?.cal;
    if (!k || k.routine !== 'encoder') return;
    $('#cbar', root).style.width = (k.progress * 100) + '%';
    const r = k.result;
    $('#cres', root).innerHTML = `<div class="msg">${esc({ to_start: 'Moving to the start…', sweeping: 'Turning slowly and measuring…', done: 'Done: check the result and apply', applied: 'Map applied', failed: 'Failed: ' + (k.reason || ''), idle: '' }[k.state] || k.state)}</div>` +
      (r ? `<table class="mt"><tr><td>Samples over ${r.travel_d}°</td><td>${r.samples}</td></tr><tr><td>Raw error (p-p / RMS)</td><td>${r.raw_pp_as}″ / ${r.raw_rms_as}″</td></tr>
        <tr><td>Held by the map (harmonics)</td><td>${r.harmonic_rms_as}″ RMS</td></tr><tr><td>Left after the map</td><td>${r.after_rms_as}″ RMS</td></tr></table>
        <p class="small">What is left is the reducer’s own periodic error and the encoder noise; the map must not take those in.</p>` : '');
    $('#capply', root).disabled = k.state !== 'done';
  };
  off = store.on((s, p) => { if ('state' in p) cal(s); });
  cal(store);
  health(); flog();
  timer = setInterval(health, 3000);
  $('#cstart', root).onclick = (e) => act(e.target, async () => { if (store.state?.tracking) await c().track(false); await c().calEncoderStart(+$('#cax', root).value, +$('#cspd', root).value); toast('Calibration running'); });
  $('#capply', root).onclick = (e) => act(e.target, () => c().calEncoderApply(), 'Map applied and stored');
  $('#cabort', root).onclick = (e) => act(e.target, () => c().calEncoderAbort(), 'Aborted: the previous map is back');
  $('#fref', root).onclick = flog;
  $('#fclr', root).onclick = (e) => act(e.target, async () => { await c().clearFaults(); flog(); });
}
