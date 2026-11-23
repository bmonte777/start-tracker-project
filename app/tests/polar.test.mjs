// Polar alignment from three solves: a synthetic mount whose polar axis is off by a known amount.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { gmstDeg, polarError } from '../shared/polar.js';

const R = Math.PI / 180;
// rotate vector v about unit axis k by angle a (Rodrigues)
function rot(v, k, a) {
  const c = Math.cos(a), s = Math.sin(a), d = v[0] * k[0] + v[1] * k[1] + v[2] * k[2];
  const x = [k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2], k[0] * v[1] - k[1] * v[0]];
  return v.map((vi, i) => vi * c + x[i] * s + k[i] * d * (1 - c));
}
function toRaDec(vec, date, lat, lon) {             // horizon (N, W, U) -> RA/Dec of date
  const alt = Math.asin(vec[2]), az = Math.atan2(-vec[1], vec[0]), l = lat * R;
  const dec = Math.asin(Math.sin(l) * Math.sin(alt) + Math.cos(l) * Math.cos(alt) * Math.cos(az));
  const H = Math.atan2(-Math.sin(az) * Math.cos(alt), Math.sin(alt) * Math.cos(l) - Math.cos(alt) * Math.cos(az) * Math.sin(l));
  return { ra_h: (((gmstDeg(date) + lon - H / R) % 360) + 360) % 360 / 15, dec_d: dec / R };
}

for (const [dAlt, dAz] of [[0.5, -0.3], [-0.2, 0.8], [0, 0]]) {
  test(`recovers a polar axis off by ${dAlt}° in altitude and ${dAz}° in azimuth (Lisbon)`, () => {
    const lat = 38.72, lon = -9.14, t = new Date('2026-11-23T22:00:00Z');
    const aAlt = (lat + dAlt) * R, aAz = dAz * R;
    const axis = [Math.cos(aAlt) * Math.cos(aAz), -Math.cos(aAlt) * Math.sin(aAz), Math.sin(aAlt)];
    // a star 40° from the axis, then the polar axis turned by 30° and 60° (the sky turns too, but the solves are of date
    // and taken within a minute, so the sky's own motion is part of what the solver reports: 0.25° per minute)
    const start = rot([Math.cos(30 * R), 0, Math.sin(30 * R)], [0, 0, 1], 0.4);
    const solves = [0, 30, 60].map((deg, i) => ({ ...toRaDec(rot(start, axis, deg * R), t, lat, lon), t }));
    const r = polarError(solves, { lat, lon });
    assert.ok(Math.abs(r.err_alt_arcmin - dAlt * 60) < 0.5, `alt ${r.err_alt_arcmin}`);
    assert.ok(Math.abs(r.err_az_arcmin - dAz * 60 * Math.cos(aAlt)) < 0.5, `az ${r.err_az_arcmin}`);
  });
}
