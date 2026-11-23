// Settings: everything in config.get / config.set (docs/05-firmware.md 6.1), plus the app's own preferences.
import { $, act, esc, needHead, pageHead, prefs, refreshConfig, store } from '../app.js';
import { CONFIG_KEYS, PAYLOADS } from '../../shared/models.js';

const FIELDS = [
  ['name', 'Head name', 'text'], ['lat', 'Latitude °', 'number', '0.00001'], ['lon', 'Longitude ° (east +)', 'number', '0.00001'], ['elev_m', 'Elevation m', 'number', '1'],
  ['pressure_hpa', 'Air pressure hPa', 'number', '1'], ['temp_c', 'Air temperature °C', 'number', '0.5'], ['refraction', 'Correct for refraction', 'bool'],
  ['mode', 'Mount mode', 'select', [['altaz', 'Alt-az'], ['eq', 'EQ on the wedge']]], ['wedge_deg', 'Wedge tilt °', 'number', '0.1'],
  ['payload', 'Payload', 'select', PAYLOADS.map((p) => [p.n, p.name])], ['wedge_fitted', 'Wedge fitted', 'bool'], ['pier_extension', 'Pier extension fitted', 'bool'],
  ['roll_derotate', 'Roll de-rotates the field (alt-az)', 'bool'], ['slew_dps', 'Slew speed °/s (max 8)', 'number', '0.5'], ['guide_rate', 'Guide rate × sidereal', 'number', '0.05'],
];

export async function render(root) {
  root.innerHTML = pageHead('Settings', 'Settings', 'Stored on the head (its settings survive a restart) and, at the bottom, on this device.') + `
  <div class="grid three"><section class="card lead span2"><h2>Head</h2><form id="f" class="f-grid"></form>
    <div class="btns"><button id="save" class="primary">Save to the head</button><button id="reload">Reload</button></div>
    <p class="small mt">Read-only: park position ${'<span id="park" class="k"></span>'} (set it on Sky with “Set park here”).</p></section>
  <section class="card"><h2>This app</h2>
    <label class="chk"><input type="checkbox" id="keep"> Keep the screen on while a job runs</label>
    <label class="chk"><input type="checkbox" id="redauto"> Switch to Red after sunset</label>
    <p class="small mt">Lens and sensor are set on Camera & jobs. The display mode (Day, Night, Red) is in the top bar.</p></section></div>`;
  if (needHead(root)) return;
  const fill = () => {
    const c = store.config;
    if (!c) return;
    $('#f', root).innerHTML = FIELDS.map(([k, l, t, x]) => t === 'bool' ? `<label class="chk"><input type="checkbox" name="${k}" ${c[k] ? 'checked' : ''}> ${l}</label>`
      : t === 'select' ? `<label class="f">${l}<select name="${k}">${x.map(([v, n]) => `<option value="${v}" ${String(c[k]) === String(v) ? 'selected' : ''}>${esc(n)}</option>`).join('')}</select></label>`
        : `<label class="f">${l}<input name="${k}" type="${t}" ${x ? `step="${x}"` : ''} value="${esc(c[k])}"></label>`).join('');
    $('#park', root).textContent = `az ${c.park_az}°, alt ${c.park_alt}°`;
  };
  fill();
  $('#keep', root).checked = prefs.get('keep_on', true); $('#keep', root).onchange = (e) => prefs.set('keep_on', e.target.checked);
  $('#redauto', root).checked = prefs.get('red_auto', false); $('#redauto', root).onchange = (e) => prefs.set('red_auto', e.target.checked);
  $('#reload', root).onclick = (e) => act(e.target, async () => { await refreshConfig(); fill(); });
  $('#save', root).onclick = (e) => act(e.target, async () => {
    const kv = {}, c = store.config;
    for (const [k] of FIELDS) {
      const el = $(`[name="${k}"]`, root);
      const t = CONFIG_KEYS[k];
      const val = t === 'boolean' ? el.checked : t === 'number' ? Number(el.value) : el.value;
      if (val !== c[k]) kv[k] = val;
    }
    if (!Object.keys(kv).length) return;
    await store.client.setConfig(kv);
    await refreshConfig();
    fill();
  }, 'Saved on the head');
}
