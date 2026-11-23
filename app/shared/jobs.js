// Star Tracker — job planners: turn what you set on the Camera & jobs screen into job.start arguments (API 1.1).

/** Field of view of a lens on a sensor, degrees. */
export function fov(focalMm, sensorW = 35.7, sensorH = 23.8) {
  const f = (s) => 2 * Math.atan(s / (2 * focalMm)) * 180 / Math.PI;
  return { w: f(sensorW), h: f(sensorH) };
}

/**
 * Panorama grid as alt-az poses, rows bottom to top, serpentine so the head never swings back across the frame.
 * Azimuth steps widen with altitude (1/cos alt) so the overlap stays the same on the sky.
 */
export function panoramaPoses({ focal, sensorW = 35.7, sensorH = 23.8, portrait = true, overlap = 0.3, azFrom, azTo, altFrom, altTo, maxPoses = 400 }) {
  const v = fov(focal, sensorW, sensorH);
  const fw = portrait ? v.h : v.w, fh = portrait ? v.w : v.h;     // camera turned: the long side vertical
  const altStep = fh * (1 - overlap);
  const span = ((azTo - azFrom) % 360 + 360) % 360 || 360;
  const rows = Math.max(1, Math.ceil(Math.max(0, altTo - altFrom) / altStep) + (altTo > altFrom ? 0 : 0));
  const poses = [];
  for (let r = 0; r <= rows - (altTo - altFrom <= 0 ? 1 : 0); r++) {
    const alt = Math.min(altTo, altFrom + r * altStep);
    const azStep = Math.min(fw * (1 - overlap) / Math.max(0.05, Math.cos(alt * Math.PI / 180)), 360);
    const n = span >= 359.9 ? Math.ceil(360 / azStep) : Math.max(1, Math.ceil(span / azStep) + 1);
    const step = span >= 359.9 ? 360 / n : (n > 1 ? span / (n - 1) : 0);
    const row = [];
    for (let i = 0; i < n; i++) row.push({ az_d: +(((azFrom + i * step) % 360 + 360) % 360).toFixed(3), alt_d: +alt.toFixed(3) });
    poses.push(...(r % 2 ? row.reverse() : row));
    if (alt >= altTo) break;
  }
  if (poses.length > maxPoses) throw new Error(`${poses.length} frames: more than the head takes (${maxPoses}). Use a wider lens or a smaller area.`);
  return { poses, rows: new Set(poses.map((p) => p.alt_d)).size, fov: v };
}

/** Time-lapse / path-lapse: keys captured from the head's position, spread over the run. */
export function pathlapse({ keys, frames, interval_s, exposure_s, settle_s = 1 }) {
  if (!keys.length) throw new Error('capture at least one position');
  const total = (frames - 1) * interval_s;
  const k = keys.length === 1 ? [{ t_s: 0, ...keys[0] }] : keys.map((p, i) => ({ t_s: +(total * i / (keys.length - 1)).toFixed(2), az_d: p.az_d, alt_d: p.alt_d }));
  return { type: 'pathlapse', keys: k, frames, interval_s, exposure_s, settle_s };
}

/** Astro sequence on the tracked target, dithering every n frames. Dither in arcsec from the lens and pixel size. */
export function astro({ frames, exposure_s, gap_s = 2, dither_px = 10, dither_every = 3, focal = 300, pixel_um = 3.76 }) {
  const scale = 206.265 * pixel_um / focal;              // arcsec per pixel
  return { type: 'astro', frames, exposure_s, interval_s: exposure_s + gap_s, settle_s: 2, dither_as: +(dither_px * scale).toFixed(1), dither_every };
}

/** How long a job will take (rough, for the planner). */
export function duration(job) {
  const per = Math.max(job.interval_s || 0, (job.exposure_s || 1) + (job.settle_s ?? 1) + (job.type === 'poses' ? 4 : 0));
  return (job.frames || job.poses?.length || 1) * per;
}
