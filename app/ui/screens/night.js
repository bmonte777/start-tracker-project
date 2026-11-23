// Night planner: darkness window, Moon, Milky Way core, altitude chart, cloud and dew forecast (Open-Meteo, when online).
// Sun, Moon and Sky come from the Benro-Polaris-Controller planner (vendor/sun.js, vendor/moon.js, reused under D12).
import { $, act, esc, pageHead, store } from '../app.js';

let off = null;
export function leave() { if (off) off(); }

const t = (d) => (d ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—');

function crossings(from, hours, f, level) {
  const out = [];
  let prev = f(from) - level;
  for (let m = 5; m <= hours * 60; m += 5) {
    const d = new Date(from.getTime() + m * 60000), cur = f(d) - level;
    if ((prev < 0) !== (cur < 0)) out.push({ type: cur > 0 ? 'rise' : 'set', time: d });
    prev = cur;
  }
  return out;
}

export async function render(root) {
  const site = { lat: store.config?.lat ?? 38.72, lon: store.config?.lon ?? -9.14 };
  root.innerHTML = pageHead('Planner', 'Night', `Tonight at ${site.lat.toFixed(2)}°, ${site.lon.toFixed(2)}° (the head’s site)`) + `
  <div class="grid three">
    <section class="card lead span2"><h2>Altitude tonight</h2><canvas id="nchart" class="chart" width="1200" height="440"></canvas>
      <div class="legend"><span><i style="background:#ffcf4a"></i>Sun</span><span><i style="background:#dfe6f0"></i>Moon</span><span><i style="background:#b9a7ff"></i>Milky Way core</span><span><i style="background:var(--accent)"></i>Where the head points</span></div></section>
    <section class="card"><h2>Darkness</h2><table id="dark"></table></section>
    <section class="card"><h2>Moon</h2><table id="moon"></table><div class="btns"><button id="trkmoon">Track the Moon</button></div></section>
    <section class="card"><h2>Milky Way core</h2><table id="core"></table><div class="btns"><button id="gocore">Go to the core</button></div>
      <p class="small">For a single-shot Milky Way over a landscape, track at half star speed from Sky (tracking: Stars) and keep exposures short; the foreground blurs less.</p></section>
    <section class="card"><h2>Clouds and dew</h2><div id="wx" class="msg">Loading the forecast…</div></section>
  </div>`;
  const now = new Date(), from = new Date(now); from.setHours(16, 0, 0, 0);
  const S = window.Sun, M = window.Moon, K = window.Sky;
  const sunAlt = (d) => S.position(d, site.lat, site.lon).alt;
  const moonAlt = (d) => M.position(d, site.lat, site.lon).alt;
  const coreAlt = (d) => { const p = K.precess(K.CORE.ra, K.CORE.dec, d); return K.altaz(p.ra, p.dec, d, site.lat, site.lon).alt; };
  const ev = (f, lvl) => crossings(from, 18, f, lvl);
  const astro = ev(sunAlt, -18), naut = ev(sunAlt, -12), sun = ev(sunAlt, -0.833);
  const dStart = astro.find((x) => x.type === 'set'), dEnd = astro.find((x) => x.type === 'rise' && (!dStart || x.time > dStart.time));
  $('#dark', root).innerHTML = `<tr><td>Sunset</td><td>${t(sun.find((x) => x.type === 'set')?.time)}</td></tr><tr><td>Nautical dusk</td><td>${t(naut.find((x) => x.type === 'set')?.time)}</td></tr>
    <tr><td>Astronomical night</td><td>${t(dStart?.time)} – ${t(dEnd?.time)}</td></tr><tr><td>Sunrise</td><td>${t(sun.find((x) => x.type === 'rise')?.time)}</td></tr>`;
  const mp = M.position(now, site.lat, site.lon), mev = M.events(from, new Date(from.getTime() + 18 * 3600000), site.lat, site.lon);
  $('#moon', root).innerHTML = `<tr><td>Illuminated</td><td>${Math.round(mp.illum * 100)} % ${mp.waxing ? '(waxing)' : '(waning)'}</td></tr><tr><td>Altitude now</td><td>${mp.alt.toFixed(0)}°</td></tr>
    ${mev.map((e) => `<tr><td>Moon${e.type}</td><td>${t(e.time)} · az ${e.az.toFixed(0)}°</td></tr>`).join('')}`;
  const cev = ev(coreAlt, 0);
  let best = { alt: -90, time: null };
  for (let m = 0; m <= 18 * 60; m += 10) { const d = new Date(from.getTime() + m * 60000); const a = coreAlt(d); if (a > best.alt && sunAlt(d) < -12) best = { alt: a, time: d }; }
  $('#core', root).innerHTML = `${cev.map((e) => `<tr><td>Core ${e.type}s</td><td>${t(e.time)}</td></tr>`).join('') || '<tr><td>Rises / sets</td><td>not tonight</td></tr>'}
    <tr><td>Highest in darkness</td><td>${best.time ? `${best.alt.toFixed(0)}° at ${t(best.time)}` : 'not up in darkness'}</td></tr>`;
  // chart
  const cv = $('#nchart', root), g = cv.getContext('2d');
  const draw = () => {
    const W = cv.width, H = cv.height, x = (d) => (d - from) / (18 * 3600000) * W, y = (a) => H / 2 - a / 90 * (H / 2 - 20);
    g.clearRect(0, 0, W, H);
    for (let m = 0; m <= 18 * 60; m += 10) { const d = new Date(from.getTime() + m * 60000), a = sunAlt(d); g.fillStyle = a > 0 ? 'rgba(120,160,220,.10)' : a > -18 ? 'rgba(70,90,140,.10)' : 'rgba(0,0,0,0)'; g.fillRect(x(d), 0, W / 108 + 1, H); }
    g.strokeStyle = 'rgba(255,255,255,.18)'; g.lineWidth = 1; g.beginPath(); g.moveTo(0, y(0)); g.lineTo(W, y(0)); g.stroke();
    g.fillStyle = '#9fb0c8'; g.font = '600 22px Inter, sans-serif';
    for (let h = 0; h <= 18; h += 2) { const d = new Date(from.getTime() + h * 3600000); g.fillText(d.getHours() + 'h', x(d) + 4, H - 8); }
    const line = (f, col) => { g.strokeStyle = col; g.lineWidth = 4; g.beginPath(); for (let m = 0; m <= 18 * 60; m += 10) { const d = new Date(from.getTime() + m * 60000); const px = x(d), py = y(f(d)); m ? g.lineTo(px, py) : g.moveTo(px, py); } g.stroke(); };
    line(sunAlt, '#ffcf4a'); line(moonAlt, '#dfe6f0'); line(coreAlt, '#b9a7ff');
    const st = store.state;
    if (st) { g.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent'); g.beginPath(); g.arc(x(new Date()), y(st.altaz.alt_d), 9, 0, 7); g.fill(); }
    g.strokeStyle = 'rgba(255,255,255,.5)'; g.setLineDash([6, 6]); g.beginPath(); g.moveTo(x(new Date()), 0); g.lineTo(x(new Date()), H); g.stroke(); g.setLineDash([]);
  };
  draw();
  off = store.on((s, p) => { if ('state' in p && Math.random() < 0.1) draw(); });
  $('#trkmoon', root).onclick = (e) => act(e.target, () => store.client.gotoBody('moon'), 'Tracking the Moon');
  $('#gocore', root).onclick = (e) => act(e.target, () => store.client.gotoRaDec(K.CORE.ra / 15, K.CORE.dec), 'Going to the core');
  if (!store.client) { $('#trkmoon', root).disabled = true; $('#gocore', root).disabled = true; }
  // forecast
  try {
    const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${site.lat}&longitude=${site.lon}&hourly=cloud_cover,cloud_cover_low,relative_humidity_2m,temperature_2m,dew_point_2m&forecast_days=2&timezone=auto`, { signal: AbortSignal.timeout(6000) });
    const j = await r.json(), h = j.hourly;
    const rows = [];
    for (let i = 0; i < h.time.length; i++) {
      const d = new Date(h.time[i]);
      if (d < from || d > new Date(from.getTime() + 16 * 3600000) || d.getHours() % 2) continue;
      const spread = h.temperature_2m[i] - h.dew_point_2m[i];
      rows.push(`<tr><td>${d.getHours()}h</td><td>${h.cloud_cover[i]} % cloud · ${h.temperature_2m[i].toFixed(0)} °C${spread < 2.5 ? ' · <span class="warn-t">dew likely</span>' : ''}</td></tr>`);
    }
    $('#wx', root).outerHTML = `<table>${rows.join('')}</table><p class="small">Open-Meteo forecast. Dew is likely when the air is within 2.5 °C of its dew point: use a dew heater on port B.</p>`;
  } catch (e) { $('#wx', root).textContent = 'No forecast: offline. Everything else on this page works without a connection.'; }
}
