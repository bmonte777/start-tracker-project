// Roll: field de-rotation in alt-az, framing by position angle (both modes), within the payload's roll limits.
import { $, act, needHead, pageHead, refreshConfig, store } from '../app.js';

let off = null;
export function leave() { if (off) off(); }

function frameArt(pa) {
  return `<svg viewBox="0 0 200 200" style="width:100%;max-width:260px;display:block;margin:0 auto" aria-hidden="true">
    <circle cx="100" cy="100" r="92" style="fill:var(--well);stroke:var(--tile-line)"/>
    <text x="100" y="22" text-anchor="middle" style="fill:var(--muted);font:600 12px var(--font)">N</text><text x="20" y="104" text-anchor="middle" style="fill:var(--muted);font:600 12px var(--font)">E</text>
    <g transform="rotate(${-pa} 100 100)"><rect x="52" y="68" width="96" height="64" rx="4" style="fill:none;stroke:var(--accent);stroke-width:3"/>
    <path d="M100 68 L100 56" style="stroke:var(--accent);stroke-width:3"/></g></svg>`;
}

export async function render(root) {
  const eq = store.config?.mode === 'eq';
  root.innerHTML = pageHead('Roll axis', 'Roll', eq ? 'On the wedge the sky does not rotate: roll only frames.' : 'In alt-az the field turns as the sky moves: roll can turn the camera with it.') + `
  <div class="grid three">
    <section class="card lead"><h2>Image angle now</h2><div id="art"></div><div class="readout" style="grid-template-columns:repeat(2,1fr)">
      <div><small>Position angle</small><b id="pa">—</b></div><div><small>Roll axis</small><b id="roll">—</b></div></div></section>
    <section class="card"><h2>Field de-rotation</h2>
      <label class="chk"><input type="checkbox" id="derot" ${eq ? 'disabled' : ''}> Keep the field angle while tracking (alt-az)</label>
      <p class="small mt">The head turns roll so stars stay at the same angle in long exposures and stacks. It holds the angle you set below; roll stops at the payload’s limit and reports it.</p>
      <div class="btns"><button id="hold" class="primary" ${eq ? 'disabled' : ''}>Hold the angle it has now</button></div>
      <div id="limwarn"></div></section>
    <section class="card"><h2>Frame by position angle</h2>
      <div class="row2"><label class="f">Position angle °<input id="tpa" type="number" step="0.5" value="0"></label><button id="setpa">Turn to it</button></div>
      <div class="btns"><button data-pa="0">0° (north up)</button><button data-pa="90">90°</button><button data-pa="-90">−90°</button></div>
      <div class="hr"></div>
      <h3>Roll axis angle</h3>
      <div class="row2"><label class="f">Roll °<input id="troll" type="number" step="0.5" value="0"></label><button id="setroll">Turn roll</button></div>
      <div class="btns"><button data-roll="0">Level (0°)</button><button data-step="-15">−15°</button><button data-step="15">+15°</button></div>
      <p class="small" id="rlim"></p></section>
  </div>`;
  if (needHead(root)) return;
  const c = () => store.client;
  const show = () => {
    const st = store.state, L = store.limits;
    if (!st) return;
    $('#art', root).innerHTML = frameArt(st.radec.rot_d);
    $('#pa', root).textContent = st.radec.rot_d.toFixed(2) + '°';
    $('#roll', root).textContent = st.axes.roll.pos_d.toFixed(2) + '°';
    if (store.config) $('#derot', root).checked = store.config.roll_derotate;
    if (L) {
      $('#rlim', root).textContent = `Allowed now: ${L.roll_lo_now_d.toFixed(0)}° … +${L.roll_hi_now_d.toFixed(0)}° (payload P${L.payload}).`;
      const near = st.axes.roll.pos_d < L.roll_lo_now_d + 5 || st.axes.roll.pos_d > L.roll_hi_now_d - 5;
      $('#limwarn', root).innerHTML = near ? '<div class="warn">Roll is within 5° of its limit: de-rotation will stop there. Re-frame or start a new sequence.</div>' : '';
    }
  };
  off = store.on((s, p) => { if ('state' in p || 'config' in p) show(); });
  show();
  $('#derot', root).onchange = (e) => act(null, async () => { await c().setConfig({ roll_derotate: e.target.checked }); await refreshConfig(); });
  $('#hold', root).onclick = (e) => act(e.target, () => c().rotatorPA(store.state.radec.rot_d), 'Holding this angle');
  $('#setpa', root).onclick = (e) => act(e.target, () => c().rotatorPA(+$('#tpa', root).value));
  $('#setroll', root).onclick = (e) => act(e.target, () => c().rotatorRoll(+$('#troll', root).value));
  root.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pa],[data-roll],[data-step]');
    if (!b) return;
    if (b.dataset.pa !== undefined) act(b, () => c().rotatorPA(+b.dataset.pa));
    else if (b.dataset.roll !== undefined) act(b, () => c().rotatorRoll(+b.dataset.roll));
    else act(b, () => c().rotatorRoll(store.state.axes.roll.pos_d + +b.dataset.step));
  });
}
