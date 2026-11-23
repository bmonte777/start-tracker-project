// Star Tracker — target catalogue: named stars, Messier and bright NGC/IC (catalog_data.js), planets, Sun and Moon.
// Planets come from Astronomy Engine (app/ui/vendor/astronomy.browser.min.js, MIT) when it is loaded; the Sun and the
// Moon are tracked by the head itself (goto {body}), which follows their own motion.
import { DSO, STARS } from './catalog_data.js';

export const PLANETS = ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune'];

const norm = (s) => s.toLowerCase().replace(/[\s_-]+/g, '');

/** All fixed objects, each {name, type, ra (h, J2000), dec (deg), mag, common, alt name, size}. */
export function all() {
  const out = [];
  for (const s of STARS) out.push({ name: s.n, type: 'star', ra: s.ra, dec: s.dec, mag: s.m });
  for (const d of DSO) out.push({ name: d.n, type: d.t, ra: d.ra, dec: d.dec, mag: d.m, common: d.c, alt: d.x, size: d.s });
  return out;
}
let cache = null;

/** J2000 position of a planet now (astrometric, Astronomy Engine). */
export function planet(name, date = new Date(), site = { lat: 0, lon: 0, elev_m: 0 }) {
  const A = globalThis.Astronomy;
  if (!A) return null;
  const obs = new A.Observer(site.lat, site.lon, site.elev_m || 0);
  const eq = A.Equator(name, date, obs, false, true);      // J2000, with aberration
  const hz = A.Horizon(date, obs, A.Equator(name, date, obs, true, true).ra, A.Equator(name, date, obs, true, true).dec, 'normal');
  const illum = A.Illumination(name, date);
  return { name, type: 'planet', ra: eq.ra, dec: eq.dec, mag: Math.round(illum.mag * 10) / 10, alt_d: hz.altitude, az_d: hz.azimuth };
}

/** Search by name, Messier/NGC number or common name. Best matches first. */
export function search(q, { limit = 40, date = new Date(), site } = {}) {
  cache = cache || all();
  const n = norm(q || '');
  const items = [
    { name: 'Sun', type: 'sun', body: 'sun' }, { name: 'Moon', type: 'moon', body: 'moon' },
    ...PLANETS.map((p) => planet(p, date, site) || { name: p, type: 'planet', unavailable: true }),
    ...cache,
  ];
  if (!n) return items.slice(0, limit);
  const scored = [];
  for (const it of items) {
    const keys = [it.name, it.common, it.alt].filter(Boolean).map(norm);
    let best = 99;
    for (const k of keys) {
      if (k === n) best = Math.min(best, 0);
      else if (k.startsWith(n)) best = Math.min(best, 1 + (k.length - n.length) / 100);
      else if (k.includes(n)) best = Math.min(best, 3);
    }
    if (best < 99) scored.push([best + (it.mag ?? 8) / 1000, it]);
  }
  return scored.sort((a, b) => a[0] - b[0]).slice(0, limit).map((x) => x[1]);
}

/** Altitude/azimuth of a J2000 position for a site and time (good to a few arcminutes: for "is it up" only). */
export function altaz(raH, decD, site, date = new Date()) {
  const R = Math.PI / 180;
  const jd = date.getTime() / 86400000 + 2440587.5;
  const T = (jd - 2451545) / 36525;
  const gmst = (280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T * T) % 360;
  const lst = gmst + site.lon;
  // precess to date (enough for "is it up": 50"/yr)
  const ra = raH * 15 + (3.075 + 1.336 * Math.sin(raH * 15 * R) * Math.tan(decD * R)) * 15 / 3600 * T * 100;
  const dec = decD + 20.04 * Math.cos(raH * 15 * R) / 3600 * T * 100;
  const H = (lst - ra) * R, d = dec * R, l = site.lat * R;
  const alt = Math.asin(Math.sin(l) * Math.sin(d) + Math.cos(l) * Math.cos(d) * Math.cos(H));
  const az = Math.atan2(-Math.sin(H) * Math.cos(d), Math.cos(l) * Math.sin(d) - Math.sin(l) * Math.cos(d) * Math.cos(H));
  return { alt_d: alt / R, az_d: ((az / R) + 360) % 360 };
}

export const counts = () => ({ stars: STARS.length, dso: DSO.length, messier: DSO.filter((d) => /^M\d+$/.test(d.n)).length });
