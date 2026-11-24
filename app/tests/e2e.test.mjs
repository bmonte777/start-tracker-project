// End-to-end runs against the simulator with different set-ups: go-to and tracking alt-az and EQ, encoder
// calibration of a raw encoder, link loss in the middle of a job, battery-low park.
import assert from 'node:assert/strict';
import net from 'node:net';
import { describe, test } from 'node:test';
import { CONN, StClient } from '../shared/stclient.js';
import { sleep, startSim } from './sim.mjs';

async function withSim(args, fn, port = 8080) {
  const sim = await startSim(args, port);
  const c = new StClient({ url: sim.url, app: 'e2e' });
  try { await c.connect(); await fn(sim, c); } finally { c.close(); await sim.stop(); }
}

// angular distance between two RA/Dec positions, arcsec
function sepAs(ra1, d1, ra2, d2) {
  const r = Math.PI / 180, a1 = ra1 * 15 * r, a2 = ra2 * 15 * r, b1 = d1 * r, b2 = d2 * r;
  const c = Math.sin(b1) * Math.sin(b2) + Math.cos(b1) * Math.cos(b2) * Math.cos(a1 - a2);
  return Math.acos(Math.min(1, c)) / r * 3600;
}

describe('go-to and tracking', () => {
  for (const mode of ['altaz', 'eq']) {
    test(`${mode}: go to Capella, track 10 simulated minutes, pointing stays on target`, async () => {
      await withSim(['--speed', '50', ...(mode === 'eq' ? ['--eq'] : [])], async (sim, c) => {
        assert.equal((await c.getState()).frame, mode);
        await c.gotoRaDec(5.27815, 45.99799);
        await c.waitFor((s) => s.mode === 'tracking', 60000, 'tracking');
        if (mode === 'altaz') await c.rotatorPA(c.state.radec.rot_d);      // hold the field angle: roll de-rotates
        const t0 = Date.now(), errs = [];
        const off = c.on('state', (s) => errs.push(sepAs(s.radec.ra_h, s.radec.dec_d, 5.27815, 45.99799)));
        await sleep(12000);                                  // 600 s simulated at x50
        off();
        const worst = Math.max(...errs);
        const s = c.state;
        assert.ok(worst < 5, `worst ${worst.toFixed(2)}" over ${errs.length} events`);
        if (mode === 'eq') {
          assert.ok(Math.abs(s.axes.alt.rate_dps) < 1e-4, 'EQ: declination axis still');
          assert.ok(Math.abs(s.axes.az.rate_dps - 15.041 / 3600) < 2e-5, 'EQ: polar axis at sidereal');
        } else {
          assert.ok(s.axes.roll.rate_dps !== 0, 'alt-az: roll de-rotates');
        }
        console.log(`${mode}: ${errs.length} events in ${((Date.now() - t0) / 1000).toFixed(1)} s, worst ${worst.toFixed(3)}"`);
      });
    });
  }
});

describe('alignment', () => {
  test('plate-solve style syncs build the pointing model (points and RMS reported)', async () => {
    await withSim(['--speed', '50'], async (sim, c) => {
      // Capella, Sirius, Procyon, Betelgeuse, plus Dubhe and Caph, which never set at the simulator's latitude (Phase 7: the test failed around midday UTC)
      const stars = [[5.27815, 45.99799], [6.75248, -16.71612], [7.65503, 5.225], [5.91953, 7.40706], [11.06213, 61.75103], [0.15297, 59.14978]];
      let n = 0;
      for (const [ra, dec] of stars) {
        try { await c.gotoRaDec(ra, dec); } catch (e) { continue; }     // below the horizon now: skip
        await c.waitFor((s) => s.mode === 'tracking', 60000);
        // a "solve" 30" away from where the head thinks it points
        await c.sync(ra + 30 / 3600 / 15, dec + 20 / 3600);
        n++;
      }
      const s = await c.waitFor((x) => x.model.points === n, 5000, 'model points');
      assert.ok(n >= 2, `synced ${n} stars`);
      assert.equal(s.model.points, n);
      assert.equal(typeof s.model.rms_as, 'number');
      await c.alignClear();
      await c.waitFor((x) => x.model.points === 0, 5000);
    });
  });
});

describe('encoder calibration', () => {
  test('raw encoder (±250" out of the box): a full azimuth turn maps the encoder error and leaves the reducer error', async () => {
    await withSim(['--speed', '50', '--raw-encoder'], async (sim, c) => {
      await c.calEncoderStart(0, 2);
      const s = await c.waitFor((x) => x.cal.state === 'done' || x.cal.state === 'failed', 180000, 'calibration');
      assert.equal(s.cal.state, 'done', s.cal.reason);
      const r = s.cal.result;
      console.log('az calibration', JSON.stringify(r));
      assert.ok(r.full_turn && r.raw_pp_as > 300, 'saw the raw error');
      // the map must hold the encoder's own error (sim: 250" and 60" harmonics, RMS 181.8") ...
      assert.ok(Math.abs(r.harmonic_rms_as - 181.8) < 4, `map ${r.harmonic_rms_as}"`);
      // ... and leave the reducer's periodic error (±20" = 14.1" RMS, not the encoder's) plus noise (5.4")
      assert.ok(r.after_rms_as < 17, `after ${r.after_rms_as}"`);
      await c.calEncoderApply();
      const h = await c.health();
      assert.equal(h.axes[0].calibrated, true);
    });
  });
});

describe('link loss', () => {
  test('a shutter-port job keeps running while the app is cut off; the app reconnects and catches up', async () => {
    await withSim(['--speed', '20'], async (sim) => {
      // the app talks through a proxy we can cut, like Wi-Fi dropping
      let cut = false;
      const socks = new Set();
      const proxy = net.createServer((a) => {
        if (cut) { a.destroy(); return; }
        const b = net.connect(8080, '127.0.0.1');
        socks.add(a); socks.add(b);
        a.pipe(b); b.pipe(a);
        const end = () => { a.destroy(); b.destroy(); socks.delete(a); socks.delete(b); };
        a.on('error', end); b.on('error', end); a.on('close', end); b.on('close', end);
      });
      await new Promise((r) => proxy.listen(18080, r));
      const c = new StClient({ url: 'ws://127.0.0.1:18080/ws/v1', app: 'e2e-link' });
      const conns = [];
      c.on('conn', (st) => conns.push(st));
      try {
        await c.connect();
        const poses = Array.from({ length: 6 }, (_, i) => ({ az_d: 100 + 15 * i, alt_d: 20 }));
        await c.jobStart({ type: 'poses', shutter: 'port', poses, exposure_s: 20, settle_s: 1 });
        await c.waitFor((s) => s.job && s.job.frame >= 2, 30000);
        const frameAtCut = c.state.job.frame;
        cut = true;
        for (const s of socks) s.destroy();
        await sleep(6000);                                   // 2 simulated minutes without the app
        cut = false;
        await c.waitFor(() => c.conn === CONN.LIVE, 15000).catch(() => {});
        for (let i = 0; i < 100 && c.conn !== CONN.LIVE; i++) await sleep(100);
        assert.equal(c.conn, CONN.LIVE, 'reconnected');
        assert.ok(conns.includes(CONN.RECONNECTING), 'went through reconnecting');
        assert.ok(c.info.job.frame > frameAtCut || c.info.job.state === 'done', `hello shows progress: ${JSON.stringify(c.info.job)} (cut at ${frameAtCut})`);
        assert.ok(c.stats.reconnects >= 1);
        await c.jobStop();
      } finally { c.close(); proxy.close(); }
    });
  });
});

describe('battery', () => {
  test('battery low (5 % or 6.2 V): the head finishes, parks (roll to 0 first) and reports it', async () => {
    await withSim(['--speed', '50', '--soc', '9'], async (sim, c) => {
      await c.gotoRaDec(5.27815, 45.99799);
      await c.waitFor((s) => s.mode === 'tracking', 60000);
      const s = await c.waitFor((x) => x.parked, 120000, 'low-battery park');
      assert.ok(Math.abs(s.axes.roll.pos_d) < 0.05, `roll ${s.axes.roll.pos_d}`);
      // the simulator's pack model reaches 6.2 V at 8.3 %, so here the voltage rule trips first
      assert.ok(s.batt.soc <= 5 || s.batt.v <= 6.2, `soc ${s.batt.soc} % at ${s.batt.v} V`);
      assert.ok((await c.faults(0)).entries.some((e) => /battery low/.test(e.msg)));
    });
  });
});
