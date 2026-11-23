// Star Tracker — polar alignment on the wedge from three plate solves (decision Q54 for the solver, D38/D39 wedge).
// Rotate only the polar (azimuth) axis between three solves, e.g. 0°, +30°, +60°. The three sky positions lie on a
// small circle around the axis the head really turns about; its pole, compared with the celestial pole, is the
// polar-alignment error. Then: altitude error → turns of the wedge's latitude screw (about 55′ per turn, D38);
// azimuth error → turn the head base / tripod the stated way.

const R = Math.PI / 180;

/** Greenwich mean sidereal time, degrees. */
export function gmstDeg(date) {
  const jd = date.getTime() / 86400000 + 2440587.5, T = (jd - 2451545) / 36525;
  return ((280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * T * T) % 360 + 360) % 360;
}

/** RA/Dec (of date, degrees) → unit vector in the local horizon frame (x north, y west, z up). */
export function horizonVec(raDeg, decDeg, date, latDeg, lonDeg) {
  const H = (gmstDeg(date) + lonDeg - raDeg) * R, d = decDeg * R, l = latDeg * R;
  const alt = Math.asin(Math.sin(l) * Math.sin(d) + Math.cos(l) * Math.cos(d) * Math.cos(H));
  const az = Math.atan2(-Math.cos(d) * Math.sin(H), Math.sin(d) * Math.cos(l) - Math.cos(d) * Math.cos(H) * Math.sin(l));   // from north, east +
  return [Math.cos(alt) * Math.cos(az), -Math.cos(alt) * Math.sin(az), Math.sin(alt)];
}

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const n = Math.hypot(...a); return a.map((x) => x / n); };

/**
 * @param {Array<{ra_h:number, dec_d:number, t:Date}>} solves  three solves (RA/Dec of date: JNow), polar axis turned between
 * @param {{lat:number, lon:number}} site
 * @returns {{axis_alt_d, axis_az_d, err_alt_arcmin, err_az_arcmin, screw_turns, alt_hint, az_hint, total_arcmin}}
 */
export function polarError(solves, site) {
  if (solves.length !== 3) throw new Error('three solves needed');
  const v = solves.map((s) => horizonVec(s.ra_h * 15, s.dec_d, s.t, site.lat, site.lon));
  // the pole of the small circle through the three points: normal of their plane
  let n = norm(cross(sub(v[1], v[0]), sub(v[2], v[0])));
  const up = site.lat >= 0 ? 1 : -1;            // the visible pole: north pole in the north
  if (n[2] * up < 0) n = n.map((x) => -x);
  const alt = Math.asin(n[2]) / R;
  let az = Math.atan2(-n[1], n[0]) / R;          // from north, east positive (y points west)
  az = ((az + 540) % 360) - 180;
  const poleAlt = Math.abs(site.lat), poleAz = site.lat >= 0 ? 0 : 180;
  const errAlt = (alt - poleAlt) * 60;
  let errAz = (az - poleAz); errAz = ((errAz + 540) % 360) - 180; errAz *= 60 * Math.cos(alt * R);   // on the sky
  return {
    axis_alt_d: alt, axis_az_d: az, err_alt_arcmin: errAlt, err_az_arcmin: errAz, total_arcmin: Math.hypot(errAlt, errAz),
    screw_turns: Math.abs(errAlt) / 55,
    alt_hint: Math.abs(errAlt) < 1 ? 'altitude is good' : errAlt > 0 ? 'axis too high: lower the wedge (latitude screw)' : 'axis too low: raise the wedge (latitude screw)',
    az_hint: Math.abs(errAz) < 1 ? 'azimuth is good' : errAz > 0 ? 'axis points east of the pole: turn the head base west' : 'axis points west of the pole: turn the head base east',
  };
}
