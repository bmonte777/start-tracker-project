// Camera and jobs: Sony over USB-C with live view (reused CameraNative), the head's shutter port with its intervalometer,
// and the imaging jobs (decision Q53: the head moves, the camera shoots; shutter-port jobs run on the head alone).
import { $, $$, act, esc, needHead, pageHead, prefs, store, toast } from '../app.js';
import { astro, duration, fov, panoramaPoses, pathlapse } from '../../shared/jobs.js';
import { camera } from '../../shared/native.js';

let off = null, lvTimer = null, camTimer = null;
export function leave() { if (off) off(); clearInterval(lvTimer); clearInterval(camTimer); }

const PROPS = [['53262', 'Shutter', true], ['20487', 'Aperture', true], ['53790', 'ISO', true], ['20496', 'Exp. comp.', true],
  ['20485', 'White bal.', true], ['53794', 'Save to', false], ['20494', 'Mode', false], ['53784', 'Battery', false]];   // Sony PTP codes (Benro app)
const MODES = [['ivm', 'Time-lapse'], ['pano', 'Panorama'], ['path', 'Path-lapse'], ['astro', 'Astro sequence'], ['hg', 'Holy Grail'],
  ['trails', 'Star trails'], ['hdr', 'HDR'], ['stack', 'Focus stack']];
const CAMERA_ONLY = new Set(['hg', 'hdr', 'stack']);   // need the camera on USB-C (exposure changes between frames)

const f = (id, label, val, extra = '') => `<label class="f">${label}<input id="${id}" type="number" value="${val}" ${extra}></label>`;
const v = (root, id) => +$('#' + id, root).value;

export async function render(root) {
  const P = (k, d) => prefs.get(k, d);
  root.innerHTML = pageHead('Camera and jobs', 'Camera & jobs', 'Sony over USB-C with live view, or any camera on the head’s shutter port.') + `
  <div class="grid three">
    <section class="card lead span2"><div class="row between"><h2 style="margin:0">Sony camera · USB-C</h2><span id="camstate" class="chip"><i></i><span>—</span></span></div>
      <div class="live mt"><div class="lv"><canvas id="lv" width="1024" height="683"></canvas><div class="lvph" id="lvph">${camera.present() ? 'Live view is off.' : 'Camera control runs in the Canopus app: plug the camera into the phone or PC with a USB-C cable and set it to PC Remote.'}</div></div>
      <div class="side"><div id="props"></div><div class="btns"><button id="camconn">Connect camera</button><button id="lvbtn">Live view</button><button id="shoot" class="primary">Shoot</button></div></div></div></section>
    <section class="card"><h2>Trigger and lens</h2>
      <div class="seg" id="trig"><button value="usb">Camera on USB-C</button><button value="port">Head’s shutter port</button></div>
      <p class="small mt" id="trignote"></p>
      <form class="f-grid mt">${f('focal', 'Focal length mm', P('focal_mm', 50), 'min="8" max="2000"')}${f('sw', 'Sensor width mm', P('sensor_w_mm', 35.7), 'step="0.1"')}
        ${f('sh', 'Sensor height mm', P('sensor_h_mm', 23.8), 'step="0.1"')}${f('px', 'Pixel µm', P('pixel_um', 3.76), 'step="0.01"')}</form>
      <p class="small" id="fovtxt"></p></section>
    <section class="card span3"><h2>Jobs</h2>
      <div class="modes" id="modes">${MODES.map(([k, n], i) => `<button value="${k}" ${i === 0 ? 'class="on"' : ''}>${n}</button>`).join('')}</div>
      <div id="form" class="mt"></div>
      <div class="row between mt"><div id="plan" class="msg"></div><button id="start" class="primary bigbtn">Start</button></div></section>
    <section class="card span2"><h2>Running</h2><div id="run" class="msg">Nothing running.</div><div class="progress mt"><span id="runbar" style="width:0"></span></div>
      <div class="btns"><button id="pause">Pause</button><button id="resume">Resume</button><button id="stopjob" class="danger">Stop</button></div></section>
    <section class="card"><h2>Shot log</h2><p class="small">Every frame the app takes is logged with time, settings and head position (CSV in Documents/Canopus on Android, Pictures\\Canopus on Windows).</p>
      <ol id="log"></ol></section>
  </div>`;
  const offline = needHead(root);
  let mode = 'ivm', trig = P('trigger', camera.present() ? 'usb' : 'port');
  const lens = () => ({ focal: v(root, 'focal'), sensorW: v(root, 'sw'), sensorH: v(root, 'sh'), pixel: v(root, 'px') });
  const showTrig = () => {
    $$('#trig button', root).forEach((b) => b.classList.toggle('on', b.value === trig));
    $('#trignote', root).textContent = trig === 'port' ? 'The head fires the camera through its 2.5 mm socket. Jobs then run on the head by themselves: the phone may sleep or leave Wi-Fi.'
      : 'The app sets exposure and downloads frames over USB-C; the head moves and waits for the app at each frame (it pauses, still tracking, if the app goes quiet).';
    const L = lens(), F = fov(L.focal, L.sensorW, L.sensorH);
    $('#fovtxt', root).textContent = `Field of view ${F.w.toFixed(1)}° × ${F.h.toFixed(1)}° · ${(206.265 * L.pixel / L.focal).toFixed(2)}″ per pixel`;
  };
  $('#trig', root).addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { trig = b.value; prefs.set('trigger', trig); showTrig(); form(); } });
  $$('form.f-grid input', root).forEach((i) => i.addEventListener('change', () => {
    prefs.set('focal_mm', v(root, 'focal')); prefs.set('sensor_w_mm', v(root, 'sw')); prefs.set('sensor_h_mm', v(root, 'sh')); prefs.set('pixel_um', v(root, 'px'));
    showTrig(); plan();
  }));

  let keys = [];
  const FORMS = {
    ivm: () => `<form class="f-grid">${f('count', 'Frames (0 = endless)', 300)}${f('exp', 'Exposure s', 1, 'step="0.1"')}${f('intv', 'Interval s', 5, 'step="0.1"')}${f('delay', 'Start delay s', 0)}</form>`,
    pano: () => `<form class="f-grid">${f('az1', 'From azimuth °', 0)}${f('az2', 'To azimuth °', 360)}${f('alt1', 'From altitude °', 0)}${f('alt2', 'To altitude °', 45)}
      ${f('ovl', 'Overlap %', 30)}${f('exp', 'Exposure s', 1, 'step="0.1"')}${f('settle', 'Settle s', 1, 'step="0.5"')}<label class="chk"><input type="checkbox" id="portrait" checked> Camera in portrait</label></form>`,
    path: () => `<form class="f-grid">${f('frames', 'Frames', 300)}${f('intv', 'Interval s', 10, 'step="0.5"')}${f('exp', 'Exposure s', 2, 'step="0.1"')}</form>
      <div class="row mt"><button type="button" id="addkey">Add the head’s position as a key</button><button type="button" id="clrkey">Clear keys</button><span id="keys" class="small"></span></div>
      <p class="small">Move the head with Sky’s arrows, add a key, move again… The head glides through the keys over the run.</p>`,
    astro: () => `<form class="f-grid">${f('frames', 'Frames', 40)}${f('exp', 'Exposure s', 60)}${f('gap', 'Gap s', 2)}${f('dpx', 'Dither px', 10)}${f('devery', 'Dither every', 3)}</form>
      <p class="small">Go to the target and start tracking first (Sky). Dithering moves the frame a few pixels between exposures for cleaner stacks.</p>`,
    hg: () => `<form class="f-grid">${f('count', 'Frames (0 = until stopped)', 0)}${f('intv', 'Interval s', 10)}${f('maxs', 'Longest shutter s', 15)}${f('miniso', 'Lowest ISO', 100)}${f('maxiso', 'Highest ISO', 3200)}${f('dark', 'Night darker by EV', 2, 'step="0.5"')}</form>
      <p class="small">Day-to-night exposure ramping from the camera’s live meter (reused from your Benro app). The head can hold still, track, or glide a path-lapse at the same time.</p>`,
    trails: () => `<form class="f-grid">${f('count', 'Frames', 200)}${f('exp', 'Exposure s', 30)}${f('gap', 'Gap s', 1)}</form>
      <p class="small">Tracking is turned off so the stars trail. With the camera on USB-C the app also builds the lighten blend live.</p>`,
    hdr: () => `<form class="f-grid">${f('shots', 'Shots', 5)}${f('ev', 'EV step', 1, 'step="0.3"')}</form>`,
    stack: () => `<form class="f-grid">${f('shots', 'Shots', 10)}${f('size', 'Step size (1–7)', 2)}${f('pulses', 'Steps per shot', 2)}</form>`,
  };
  const form = () => {
    $('#form', root).innerHTML = FORMS[mode]();
    if (CAMERA_ONLY.has(mode) && trig === 'port') $('#form', root).insertAdjacentHTML('beforeend', '<div class="warn">This job changes exposure or focus between frames, so it needs the camera on USB-C.</div>');
    $$('#form input', root).forEach((i) => i.addEventListener('input', plan));
    const ak = $('#addkey', root);
    if (ak) {
      ak.onclick = () => { const s = store.state; if (!s) return toast('connect to the head first', 'bad'); keys.push({ az_d: +s.altaz.az_d.toFixed(3), alt_d: +s.altaz.alt_d.toFixed(3) }); plan(); };
      $('#clrkey', root).onclick = () => { keys = []; plan(); };
    }
    plan();
  };
  const build = () => {
    const L = lens(), shutter = trig === 'port' ? 'port' : 'app';
    switch (mode) {
      case 'pano': {
        const p = panoramaPoses({ focal: L.focal, sensorW: L.sensorW, sensorH: L.sensorH, portrait: $('#portrait', root).checked, overlap: v(root, 'ovl') / 100,
          azFrom: v(root, 'az1'), azTo: v(root, 'az2'), altFrom: v(root, 'alt1'), altTo: v(root, 'alt2') });
        return { job: { type: 'poses', shutter, poses: p.poses, exposure_s: v(root, 'exp'), settle_s: v(root, 'settle') }, text: `${p.poses.length} frames in ${p.rows} rows` };
      }
      case 'path': { const j = pathlapse({ keys, frames: v(root, 'frames'), interval_s: v(root, 'intv'), exposure_s: v(root, 'exp') }); j.shutter = shutter; return { job: j, text: `${keys.length} keys, ${j.frames} frames` }; }
      case 'astro': { const j = astro({ frames: v(root, 'frames'), exposure_s: v(root, 'exp'), gap_s: v(root, 'gap'), dither_px: v(root, 'dpx'), dither_every: v(root, 'devery'), focal: L.focal, pixel_um: L.pixel }); j.shutter = shutter; return { job: j, text: `${j.frames} × ${j.exposure_s} s, dither ${j.dither_as}″ every ${j.dither_every}` }; }
      case 'ivm': return { ivm: { count: v(root, 'count'), exposure_s: v(root, 'exp'), interval_s: v(root, 'intv'), focus_s: 0.3, delay_s: v(root, 'delay') }, text: `${v(root, 'count') || 'endless'} frames every ${v(root, 'intv')} s` };
      case 'trails': return { ivm: { count: v(root, 'count'), exposure_s: v(root, 'exp'), interval_s: v(root, 'exp') + v(root, 'gap'), focus_s: 0.3, delay_s: 0 }, trails: true, text: `${v(root, 'count')} × ${v(root, 'exp')} s, tracking off` };
      default: return { camera: mode, text: '' };
    }
  };
  const plan = () => {
    try {
      const b = build();
      const secs = b.job ? duration(b.job) : b.ivm ? (b.ivm.count || 0) * Math.max(b.ivm.interval_s, b.ivm.exposure_s + 0.5) : 0;
      $('#plan', root).textContent = b.text + (secs ? ` · about ${secs >= 3600 ? (secs / 3600).toFixed(1) + ' h' : Math.round(secs / 60) + ' min'}` : '');
      if (mode === 'path') $('#keys', root).textContent = keys.map((k, i) => `${i + 1}: ${k.az_d.toFixed(1)}°/${k.alt_d.toFixed(1)}°`).join(' · ');
      $('#start', root).disabled = offline && !CAMERA_ONLY.has(mode);
    } catch (e) { $('#plan', root).textContent = e.message; $('#start', root).disabled = true; }
  };
  $('#modes', root).addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; mode = b.value; $$('#modes button', root).forEach((x) => x.classList.toggle('on', x === b)); form(); });
  $('#start', root).onclick = (e) => act(e.target, async () => {
    const b = build(), c = store.client;
    if (b.job && trig === 'port') { const r = await c.jobStart(b.job); toast(`Job ${r.job_id} started on the head: ${r.frames} frames`); return; }
    if (b.job) { camera.call('startHeadJob', JSON.stringify({ head: store.head?.http, job: b.job })); toast('Job started: the app shoots, the head moves'); return; }
    if (b.ivm && trig === 'port') { if (b.trails) await c.track(false); await c.ivmStart(b.ivm); toast('Intervalometer running on the head'); return; }
    if (b.ivm) { if (b.trails) { await c.track(false); camera.call('startTrails', JSON.stringify({ count: b.ivm.count, gapSeconds: b.ivm.interval_s - b.ivm.exposure_s, bulbSeconds: b.ivm.exposure_s })); } else camera.call('startInterval', JSON.stringify({ count: b.ivm.count, intervalSeconds: b.ivm.interval_s, bulbSeconds: b.ivm.exposure_s })); return; }
    if (mode === 'hg') camera.call('startHolyGrail', JSON.stringify({ count: v(root, 'count'), intervalSeconds: v(root, 'intv'), maxShutter: v(root, 'maxs'), minIso: v(root, 'miniso'), maxIso: v(root, 'maxiso'), nightDarker: v(root, 'dark'), lat: store.config?.lat, lon: store.config?.lon }));
    if (mode === 'hdr') camera.call('startHdr', JSON.stringify({ hdrShots: v(root, 'shots'), hdrEv: v(root, 'ev') }));
    if (mode === 'stack') camera.call('startFocusStack', JSON.stringify({ shots: v(root, 'shots'), size: v(root, 'size'), pulses: v(root, 'pulses') }));
  });
  $('#pause', root).onclick = (e) => act(e.target, () => store.client.jobPause());
  $('#resume', root).onclick = (e) => act(e.target, () => store.client.jobResume());
  $('#stopjob', root).onclick = (e) => act(e.target, async () => {
    if (store.state?.job) await store.client.jobStop();
    if (store.state?.ivm.running) await store.client.ivmStop();
    if (camera.present()) camera.call('stopJob');
  }, 'Stopped');

  // camera status and live view (reused bridge)
  let lvOn = false, seq = 0;
  const cv = $('#lv', root), ctx = cv.getContext('2d'), img = new Image();
  img.onload = () => { cv.width = img.naturalWidth; cv.height = img.naturalHeight; ctx.drawImage(img, 0, 0); $('#lvph', root).hidden = true; };
  const camShow = () => {
    const s = camera.status(), ok = s.state === 'connected';
    $('#camstate', root).querySelector('i').className = ok ? 'ok' : '';
    $('#camstate', root).querySelector('span').textContent = s.job || (ok ? s.model : camera.present() ? 'not connected' : 'needs the app');
    $('#props', root).innerHTML = ok && s.settings ? PROPS.filter(([k]) => s.settings[k]).map(([k, n, step]) => `<div class="set"><span class="lbl">${n}</span>${step ? `<button data-k="${k}" data-d="-1">−</button>` : ''}
      <span class="val" ${step ? '' : 'style="grid-column:span 3"'}>${esc(s.settings[k].text)}</span>${step ? `<button data-k="${k}" data-d="1">+</button>` : ''}</div>`).join('') : '<p class="msg">Connect the camera to see its settings.</p>';
    ['camconn', 'lvbtn', 'shoot'].forEach((id) => { $('#' + id, root).disabled = !camera.present(); });
    $('#camconn', root).textContent = ok ? 'Disconnect' : 'Connect camera';
  };
  $('#props', root).addEventListener('click', (e) => { const b = e.target.closest('[data-k]'); if (b) { try { camera.call('step', +b.dataset.k, +b.dataset.d); camShow(); } catch (er) { toast(er.message, 'bad'); } } });
  $('#camconn', root).onclick = () => { try { camera.status().state === 'connected' ? camera.call('disconnect') : camera.call('connect'); camShow(); } catch (er) { toast(er.message, 'bad'); } };
  $('#shoot', root).onclick = () => { try { camera.call('shoot', JSON.stringify({})); toast('Shot'); } catch (er) { toast(er.message, 'bad'); } };
  $('#lvbtn', root).onclick = () => { try { lvOn = !lvOn; camera.call(lvOn ? 'liveStart' : 'liveStop'); $('#lvbtn', root).classList.toggle('primary', lvOn); } catch (er) { toast(er.message, 'bad'); } };
  lvTimer = setInterval(() => {
    if (!lvOn || document.hidden) return;
    const r = window.CameraNative.liveFrame(seq);
    if (!r) return;
    const comma = r.indexOf(',');
    seq = +r.slice(0, comma);
    img.src = 'data:image/jpeg;base64,' + r.slice(comma + 1);
  }, 90);
  if (camera.present()) camTimer = setInterval(camShow, 1500);
  const runShow = () => {
    const st = store.state, j = st?.job, cs = camera.status();
    const parts = [];
    if (j) parts.push(`Head job ${j.job_id}: ${j.type}, frame ${j.frame} of ${j.frames}, ${j.state.replace('_', ' ')}${j.reason ? ' — ' + j.reason : ''}${j.eta_s ? `, about ${Math.round(j.eta_s / 60)} min left` : ''}`);
    if (st?.ivm.running) parts.push(`Shutter port: frame ${st.ivm.done} of ${st.ivm.count || '∞'}`);
    if (cs.job) parts.push(`Camera: ${cs.job}${cs.step ? ' — ' + cs.step : ''}`);
    $('#run', root).textContent = parts.join(' · ') || 'Nothing running.';
    $('#runbar', root).style.width = j ? (100 * (j.frame - 1) / j.frames) + '%' : st?.ivm.running && st.ivm.count ? (100 * st.ivm.done / st.ivm.count) + '%' : '0';
    $('#pause', root).disabled = !j || j.state === 'paused';
    $('#resume', root).disabled = !j || j.state !== 'paused';
  };
  off = store.on((s, p) => { if ('state' in p) runShow(); });
  showTrig(); form(); camShow(); runShow();
}
