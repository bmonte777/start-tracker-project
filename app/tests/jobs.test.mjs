// Job planners (no simulator needed).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { astro, fov, panoramaPoses, pathlapse } from '../shared/jobs.js';

test('field of view of a 24 mm lens on full frame', () => {
  const v = fov(24, 35.7, 23.8);
  assert.ok(Math.abs(v.w - 73.3) < 0.3 && Math.abs(v.h - 52.8) < 0.3);
});
test('360° panorama with a 24 mm in portrait: overlap kept, serpentine order, widening steps at altitude', () => {
  const { poses, rows } = panoramaPoses({ focal: 24, overlap: 0.3, azFrom: 0, azTo: 360, altFrom: 0, altTo: 60 });
  assert.ok(rows >= 2 && rows <= 3, `rows ${rows}`);
  const r0 = poses.filter((p) => p.alt_d === 0), r1 = poses.filter((p) => p.alt_d === poses.find((q) => q.alt_d > 0).alt_d);
  assert.ok(r0.length > r1.length, 'fewer frames higher up');
  const v = fov(24);
  assert.ok(360 / r0.length <= v.h * 0.7 + 1e-6, 'azimuth step within the overlap');
  // serpentine: the second row starts where the first ended
  assert.ok(Math.abs(poses[r0.length].az_d - r0.at(-1).az_d) < 360 / r1.length + 1);
});
test('a panorama larger than 400 frames is refused', () => {
  assert.throws(() => panoramaPoses({ focal: 600, azFrom: 0, azTo: 360, altFrom: 0, altTo: 80 }), /more than the head takes/);
});
test('path-lapse keys spread over the run; astro dither from the image scale', () => {
  const p = pathlapse({ keys: [{ az_d: 10, alt_d: 5 }, { az_d: 40, alt_d: 10 }, { az_d: 80, alt_d: 20 }], frames: 101, interval_s: 10, exposure_s: 2 });
  assert.deepEqual(p.keys.map((k) => k.t_s), [0, 500, 1000]);
  const a = astro({ frames: 30, exposure_s: 120, focal: 300, pixel_um: 3.76, dither_px: 10 });
  assert.ok(Math.abs(a.dither_as - 25.9) < 0.2, `dither ${a.dither_as}`);
});
