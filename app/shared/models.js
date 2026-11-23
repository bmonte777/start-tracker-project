// Star Tracker — typed models of WebSocket JSON API v1 (docs/05-firmware.md section 6.1, as implemented in
// firmware/esp32s3/components/st_proto/wsapi.cpp). The firmware is the contract: every op, field, unit and limit here
// is checked against the source by app/tools/check_api.py.
//
// Plain JS with JSDoc types, so it runs unchanged in the WebView, in the Windows window and in Node (tests).

export const API_VERSION = 1;

/** Error codes the head returns in err.code. */
export const ERR = Object.freeze({
  LIMIT: 'limit', PARKED: 'parked', INVALID: 'invalid', STATE: 'state', NOTIMPL: 'notimpl', PARSE: 'parse', ERROR: 'error',
  // client-side only
  TIMEOUT: 'timeout', OFFLINE: 'offline',
});

export const AXES = Object.freeze(['az', 'alt', 'roll']);
export const ACTIVITIES = Object.freeze(['idle', 'slewing', 'tracking', 'moving', 'parking', 'parked', 'fault']);
export const TRACK_RATES = Object.freeze(['sidereal', 'lunar', 'solar', 'king']);
export const GUIDE_DIRS = Object.freeze(['n', 's', 'e', 'w']);

/** Limits the firmware enforces (head.cpp, wsapi.cpp, motion.c). Used to validate before sending. */
export const LIMITS = Object.freeze({
  jog_dps_max: 8,            // D42, Head::move_axis
  slew_dps_max: 8,           // D42
  alt_min_d: -10, alt_max_d: 95,   // motion.c limits (params.py)
  payload_min: 1, payload_max: 5,  // D40
  lat_abs_max: 90, lon_abs_max: 180,
  wedge_deg_min: 0, wedge_deg_max: 75,  // D21
  ivm_exposure_max_s: 3600,
});

/** Settings keys accepted by config.set, with their JSON type (wsapi.cpp). park_az / park_alt are read-only. */
export const CONFIG_KEYS = Object.freeze({
  name: 'string', mode: 'string', lat: 'number', lon: 'number', elev_m: 'number', pressure_hpa: 'number',
  temp_c: 'number', refraction: 'boolean', wedge_deg: 'number', payload: 'number', wedge_fitted: 'boolean',
  pier_extension: 'boolean', roll_derotate: 'boolean', slew_dps: 'number', guide_rate: 'number',
});
export const CONFIG_READONLY = Object.freeze(['park_az', 'park_alt']);

/**
 * Every op the apps use, with its arguments. `since` = API minor version that added it (1.0 = Phase 5,
 * 1.1 = Phase 6 additions, docs/06-apps.md section 4).
 */
export const OPS = Object.freeze({
  // --- 1.0 (Phase 5)
  'goto': { since: '1.0', args: ['ra_h', 'dec_d', 'epoch', 'az_d', 'alt_d', 'body'] },
  'sync': { since: '1.0', args: ['ra_h', 'dec_d', 'epoch'] },
  'track': { since: '1.0', args: ['on', 'rate'] },
  'stop': { since: '1.0', args: [] },
  'park': { since: '1.0', args: [] },
  'unpark': { since: '1.0', args: [] },
  'park.set': { since: '1.0', args: [] },
  'jog': { since: '1.0', args: ['axis', 'dps'] },
  'guide': { since: '1.0', args: ['dir', 'ms'] },
  'rotator.pa': { since: '1.0', args: ['pa_d'] },
  'rotator.roll': { since: '1.0', args: ['roll_d'] },
  'align.clear': { since: '1.0', args: [] },
  'time.set': { since: '1.0', args: ['unix_s'] },
  'config.get': { since: '1.0', args: [] },
  'config.set': { since: '1.0', args: Object.keys(CONFIG_KEYS) },
  'ivm.start': { since: '1.0', args: ['count', 'exposure_s', 'interval_s', 'focus_s', 'delay_s'] },
  'ivm.stop': { since: '1.0', args: [] },
  'state': { since: '1.0', args: [] },
  // --- 1.1 (Phase 6)
  'hello': { since: '1.1', args: ['app', 'last_seq'] },
  'limits.get': { since: '1.1', args: [] },
  'faults.get': { since: '1.1', args: ['since'] },
  'faults.clear': { since: '1.1', args: [] },
  'health.get': { since: '1.1', args: [] },
  'pec.status': { since: '1.1', args: [] },
  'pec.record': { since: '1.1', args: ['axis', 'cycles'] },
  'pec.stop': { since: '1.1', args: [] },
  'pec.play': { since: '1.1', args: ['on'] },
  'pec.save': { since: '1.1', args: [] },
  'pec.clear': { since: '1.1', args: ['axis'] },
  'pec.get': { since: '1.1', args: ['axis'] },
  'job.start': { since: '1.1', args: ['type', 'shutter', 'poses', 'keys', 'frames', 'exposure_s', 'interval_s', 'settle_s',
    'focus_s', 'ack_timeout_s', 'dither_as', 'dither_every', 'hold'] },
  'job.pause': { since: '1.1', args: [] },
  'job.resume': { since: '1.1', args: [] },
  'job.stop': { since: '1.1', args: [] },
  'job.status': { since: '1.1', args: [] },
  'job.ack': { since: '1.1', args: ['job_id', 'frame'] },
  'cal.status': { since: '1.1', args: [] },
  'cal.encoder.start': { since: '1.1', args: ['axis', 'speed_dps'] },
  'cal.encoder.status': { since: '1.1', args: [] },
  'cal.encoder.abort': { since: '1.1', args: [] },
  'cal.encoder.apply': { since: '1.1', args: [] },
  'cal.balance': { since: '1.1', args: ['swing_d'] },
  'update.status': { since: '1.1', args: [] },
});

/** The five payload envelopes (D40, docs/03-mechanical-design.md) — names and masses for the Rig screen. */
export const PAYLOADS = Object.freeze([
  { n: 1, name: 'P1 mirrorless + standard zoom', mass_kg: 1.55, mount: 'L-plate under the body' },
  { n: 2, name: 'P2 70-200 f/2.8 on its collar', mass_kg: 1.95, mount: 'Collar foot, 80 mm' },
  { n: 3, name: 'P3 150-600 class lens on its foot', mass_kg: 3.75, mount: 'Lens foot, 100 mm' },
  { n: 4, name: 'P4 72 mm refractor + astro camera', mass_kg: 2.70, mount: 'Dovetail, 200 mm' },
  { n: 5, name: 'P5 90 mm refractor at the full 7 kg', mass_kg: 7.00, mount: 'Dovetail, 250 mm' },
]);

/**
 * @typedef {Object} AxisState
 * @property {number} pos_d   commanded angle, degrees
 * @property {number} enc_d   encoder angle, degrees
 * @property {number} rate_dps rate, degrees per second
 * @property {number} i_ma    motor current, mA
 * @property {number} load    StallGuard reading (0 = high load)
 * @property {number} temp_c  motor temperature, °C
 * @property {number} flags   motion flags (bit field, st_link.h)
 */

/**
 * @typedef {Object} HeadState
 * @property {number} seq        event sequence number (1.1; 0 on a 1.0 head)
 * @property {string} t          UTC, ISO 8601
 * @property {string} mode       one of ACTIVITIES
 * @property {'altaz'|'eq'} frame
 * @property {boolean} tracking
 * @property {boolean} parked
 * @property {{az:AxisState, alt:AxisState, roll:AxisState}} axes
 * @property {{ra_h:number, dec_d:number, ra_now_h:number, dec_now_d:number, rot_d:number}} radec  J2000, JNow, position angle
 * @property {{az_d:number, alt_d:number}} altaz
 * @property {{soc:number, v:number, temp_c:number, ext:boolean, motion_budget_w:number}} batt
 * @property {{vmot:number, rail:number, faults:number, link:boolean}} motor
 * @property {{points:number, rms_as:number}} model
 * @property {{running:boolean, done:number, count:number}} ivm
 * @property {string[]} faults   latest messages
 * @property {Object|null} job   (1.1) running job summary
 * @property {Object|null} pec   (1.1)
 * @property {Object|null} cal   (1.1)
 */

const num = (v, d = 0) => (typeof v === 'number' && Number.isFinite(v) ? v : d);
const bool = (v, d = false) => (typeof v === 'boolean' ? v : d);
const str = (v, d = '') => (typeof v === 'string' ? v : d);

function axis(a) {
  a = a || {};
  return { pos_d: num(a.pos_d), enc_d: num(a.enc_d), rate_dps: num(a.rate_dps), i_ma: num(a.i_ma), load: num(a.load),
    temp_c: num(a.temp_c), flags: num(a.flags) };
}

/**
 * Normalise a state event into a HeadState with every field present and of the right type. Unknown extra fields are
 * kept under `extra` so a newer head does not break an older app.
 * @returns {HeadState}
 */
export function parseState(e) {
  e = e || {};
  const rd = e.radec || {}, hz = e.altaz || {}, b = e.batt || {}, m = e.motor || {}, pm = e.model || {}, iv = e.ivm || {};
  const known = new Set(['v', 'ev', 'seq', 't', 'mode', 'frame', 'tracking', 'parked', 'axes', 'radec', 'altaz', 'batt', 'motor',
    'model', 'ivm', 'faults', 'job', 'pec', 'cal']);
  const extra = {};
  for (const k of Object.keys(e)) if (!known.has(k)) extra[k] = e[k];
  return {
    seq: num(e.seq), t: str(e.t), mode: ACTIVITIES.includes(e.mode) ? e.mode : 'fault', frame: e.frame === 'eq' ? 'eq' : 'altaz',
    tracking: bool(e.tracking), parked: bool(e.parked),
    axes: { az: axis(e.axes && e.axes.az), alt: axis(e.axes && e.axes.alt), roll: axis(e.axes && e.axes.roll) },
    radec: { ra_h: num(rd.ra_h), dec_d: num(rd.dec_d), ra_now_h: num(rd.ra_now_h), dec_now_d: num(rd.dec_now_d), rot_d: num(rd.rot_d) },
    altaz: { az_d: num(hz.az_d), alt_d: num(hz.alt_d) },
    batt: { soc: num(b.soc), v: num(b.v), temp_c: num(b.temp_c), ext: bool(b.ext), motion_budget_w: num(b.motion_budget_w) },
    motor: { vmot: num(m.vmot), rail: num(m.rail), faults: num(m.faults), link: bool(m.link) },
    model: { points: num(pm.points), rms_as: num(pm.rms_as) },
    ivm: { running: bool(iv.running), done: num(iv.done), count: num(iv.count) },
    faults: Array.isArray(e.faults) ? e.faults.filter((f) => typeof f === 'string') : [],
    job: e.job && typeof e.job === 'object' ? e.job : null,
    pec: e.pec && typeof e.pec === 'object' ? e.pec : null,
    cal: e.cal && typeof e.cal === 'object' ? e.cal : null,
    extra,
  };
}

/** Check a request before it goes out. Returns an error string or ''. Mirrors the firmware's own checks. */
export function validate(op, args = {}) {
  const spec = OPS[op];
  if (!spec) return `unknown op ${op}`;
  for (const k of Object.keys(args)) if (!spec.args.includes(k)) return `${op}: unknown argument ${k}`;
  switch (op) {
    case 'jog':
      if (![0, 1, 2].includes(args.axis)) return 'jog: axis must be 0, 1 or 2';
      if (typeof args.dps !== 'number' || Math.abs(args.dps) > LIMITS.jog_dps_max) return `jog: |dps| ≤ ${LIMITS.jog_dps_max}`;
      break;
    case 'goto':
      if (args.body !== undefined) { if (!['sun', 'moon'].includes(args.body)) return 'goto: body is sun or moon'; break; }
      if (args.az_d !== undefined) {
        if (typeof args.alt_d !== 'number' || args.alt_d < LIMITS.alt_min_d || args.alt_d > LIMITS.alt_max_d) return 'goto: alt_d out of range';
        break;
      }
      if (typeof args.ra_h !== 'number' || args.ra_h < 0 || args.ra_h >= 24) return 'goto: ra_h 0–24';
      if (typeof args.dec_d !== 'number' || Math.abs(args.dec_d) > 90) return 'goto: dec_d ±90';
      break;
    case 'sync':
      if (typeof args.ra_h !== 'number' || typeof args.dec_d !== 'number') return 'sync: ra_h and dec_d required';
      break;
    case 'track':
      if (args.rate !== undefined && !TRACK_RATES.includes(args.rate)) return 'track: unknown rate';
      break;
    case 'guide':
      if (!GUIDE_DIRS.includes(args.dir)) return 'guide: dir is n, s, e or w';
      if (typeof args.ms !== 'number' || args.ms <= 0) return 'guide: ms > 0';
      break;
    case 'config.set':
      for (const [k, v] of Object.entries(args)) if (typeof v !== CONFIG_KEYS[k]) return `config.set: ${k} must be a ${CONFIG_KEYS[k]}`;
      if (args.payload !== undefined && (args.payload < LIMITS.payload_min || args.payload > LIMITS.payload_max)) return 'config.set: payload 1–5';
      if (args.mode !== undefined && !['altaz', 'eq'].includes(args.mode)) return 'config.set: mode altaz or eq';
      if (args.lat !== undefined && Math.abs(args.lat) > LIMITS.lat_abs_max) return 'config.set: lat ±90';
      if (args.lon !== undefined && Math.abs(args.lon) > LIMITS.lon_abs_max) return 'config.set: lon ±180';
      break;
    case 'ivm.start':
      if (args.exposure_s !== undefined && (args.exposure_s <= 0 || args.exposure_s > LIMITS.ivm_exposure_max_s)) return 'ivm.start: exposure 0–3600 s';
      if (args.count !== undefined && args.count < 0) return 'ivm.start: count ≥ 0';
      break;
    default:
  }
  return '';
}

/** Format helpers shared by the screens. */
export function fmtRA(h) {
  h = ((h % 24) + 24) % 24;
  const t = Math.round(h * 36000);
  const hh = Math.floor(t / 36000), mm = Math.floor((t % 36000) / 600), ss = (t % 600) / 10;
  return `${String(hh).padStart(2, '0')}h ${String(mm).padStart(2, '0')}m ${ss.toFixed(1).padStart(4, '0')}s`;
}
export function fmtDec(d) {
  const s = d < 0 ? '−' : '+';
  const t = Math.round(Math.abs(d) * 3600);
  return `${s}${String(Math.floor(t / 3600)).padStart(2, '0')}° ${String(Math.floor((t % 3600) / 60)).padStart(2, '0')}′ ${String(t % 60).padStart(2, '0')}″`;
}
export function fmtDeg(d, places = 3) { return `${d.toFixed(places)}°`; }
export function fmtArcsec(as) { return Math.abs(as) >= 60 ? `${(as / 60).toFixed(1)}′` : `${as.toFixed(1)}″`; }
