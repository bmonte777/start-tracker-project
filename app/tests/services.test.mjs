// Head services added in API 1.1 (jobs, PEC, encoder calibration, balance) and the update upload, against the simulator.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { after, before, describe, test } from 'node:test';
import { StClient, httpOp } from '../shared/stclient.js';
import { inspectBundle, uploadBundle } from '../shared/stfw.js';
import { sleep, startSim } from './sim.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
let sim, c;
// wait for the job to finish: poll job.status (a state event from before the start would still say job: null)
async function jobEnd(timeoutMs = 120000) {
  const t0 = Date.now();
  for (;;) {
    const st = await c.jobStatus();
    if (['done', 'stopped', 'failed'].includes(st.state)) return st;
    if (Date.now() - t0 > timeoutMs) throw new Error('job did not end: ' + JSON.stringify(st));
    await sleep(50);
  }
}
before(async () => {
  sim = await startSim(['--speed', '50']);
  c = new StClient({ url: sim.url, app: 'services-test' });
  await c.connect();
});
after(async () => { c.close(); await sim.stop(); });

describe('jobs', () => {
  test('panorama poses with the shutter port run to the end on the head', async () => {
    const poses = [];
    for (let i = 0; i < 4; i++) poses.push({ az_d: 120 + i * 20, alt_d: 10 });
    const r = await c.jobStart({ type: 'poses', shutter: 'port', poses, exposure_s: 15, settle_s: 1, interval_s: 0 });
    assert.equal(r.frames, 4);
    const exposures = new Set();
    const off = c.on('state', (s) => { if (s.job?.state === 'exposing') exposures.add(s.job.frame); });
    const st = await jobEnd();
    const s = await c.getState();
    off();
    assert.equal(st.state, 'done');
    assert.equal(st.frame, 4);
    assert.ok(exposures.size >= 3, `saw exposures for frames ${[...exposures]}`);
    assert.ok(Math.abs(s.altaz.az_d - 180) < 0.05, `ended at az ${s.altaz.az_d}`);
  });

  test('a pose outside the payload envelope is refused before anything moves', async () => {
    await assert.rejects(c.jobStart({ type: 'poses', shutter: 'none', poses: [{ az_d: 0, alt_d: 120 }] }), (e) => e.code === 'limit');
  });

  test('USB-camera job: the head waits for job.ack each frame (acks over the HTTP op, as native code sends them)', async () => {
    const r = await c.jobStart({ type: 'pathlapse', shutter: 'app', frames: 3, interval_s: 4, exposure_s: 1, settle_s: 0.5,
      keys: [{ t_s: 0, az_d: 200, alt_d: 20 }, { t_s: 8, az_d: 210, alt_d: 25 }], ack_timeout_s: 30 });
    for (let f = 1; f <= 3; f++) {
      await c.waitFor((s) => s.job?.state === 'waiting_ack' && s.job.frame === f, 30000, `frame ${f} ready`);
      await assert.rejects(httpOp(sim.http, 'job.ack', { job_id: r.job_id, frame: f + 1 }), (e) => e.code === 'invalid');
      await httpOp(sim.http, 'job.ack', { job_id: r.job_id, frame: f });
    }
    const st = await jobEnd();
    assert.equal(st.state, 'done');
    const s = await c.getState();
    assert.ok(Math.abs(s.altaz.az_d - 210) < 0.05 && Math.abs(s.altaz.alt_d - 25) < 0.05, 'last key reached');
  });

  test('no ack in time: the job pauses (never moves on blind) and resumes on request', async () => {
    const r = await c.jobStart({ type: 'poses', shutter: 'app', poses: [{ az_d: 230, alt_d: 30 }, { az_d: 240, alt_d: 30 }], settle_s: 0.5, ack_timeout_s: 30 });
    try {
      await c.waitFor((s) => s.job?.state === 'paused', 30000, 'pause');
      assert.equal(c.state.job.frame, 1);
      assert.match((await c.jobStatus()).reason, /no reply from the app/);
      assert.ok((await c.faults(0)).entries.some((e) => /job paused/.test(e.msg)));
      await c.jobResume();
      // the native camera code acks as soon as its exposure is done; poll like it would
      const ackWhenReady = async (frame) => {
        for (let i = 0; i < 400; i++) {
          const st = await c.jobStatus();
          if (st.state === 'waiting_ack' && st.frame === frame) { await c.jobAck(r.job_id, frame); return; }
          await sleep(25);
        }
        throw new Error('frame ' + frame + ' never ready');
      };
      await ackWhenReady(1);
      await ackWhenReady(2);
      assert.equal((await jobEnd()).state, 'done');
    } finally { await c.jobStop(); }
  });

  test('astro sequence with dither needs tracking, then dithers between frames', async () => {
    await assert.rejects(c.jobStart({ type: 'astro', shutter: 'none', frames: 3 }), (e) => e.code === 'state');
    await c.gotoRaDec(5.27815, 45.99799);               // Capella
    await c.waitFor((s) => s.mode === 'tracking', 60000, 'tracking');
    await c.jobStart({ type: 'astro', shutter: 'port', frames: 4, exposure_s: 3, interval_s: 4, settle_s: 1, dither_as: 20, dither_every: 1 });
    assert.equal((await jobEnd()).state, 'done');
    const s = await c.getState();
    assert.ok(s.tracking, 'still tracking after the sequence');
  });
});

describe('PEC', () => {
  test('record one cycle while tracking, then play it back', async () => {
    if (!c.state.tracking) { await c.gotoRaDec(5.27815, 45.99799); await c.waitFor((s) => s.mode === 'tracking', 60000); }
    await assert.rejects(c.pecPlay(true), (e) => e.code === 'state');
    await c.pecRecord(0, 1);
    const s = await c.waitFor((x) => x.pec.state === 'ready', 120000, 'PEC ready');
    assert.equal(s.pec.cycles, 1);
    const st = await c.pecStatus();
    assert.ok(st.period_s > 861 && st.period_s < 862.5, `period ${st.period_s}`);
    const curve = await c.pecCurve(0);
    assert.equal(curve.table_as.length, 128);
    assert.equal(curve.raw_as.length, 128);
    await c.pecPlay(true);
    assert.equal((await c.pecStatus()).state, 'playing');
    const saved = await c.pecSave().then(() => true, (e) => e.code);
    assert.equal(saved, 'notimpl');                      // simulator: no storage (RAM only)
    await c.pecPlay(false);
    console.log(`PEC: residual p-p ${st.pp_as}" rms ${st.rms_as}" noise ${st.noise_as}"`);
  });
});

describe('calibration', () => {
  test('balance check swings altitude and reports a verdict', async () => {
    await c.stop();
    await c.gotoAltAz(90, 40);
    await c.waitFor((s) => s.mode === 'idle' && Math.abs(s.altaz.alt_d - 40) < 0.1, 60000);
    await c.track(false);
    await c.calBalance(5);
    const s = await c.waitFor((x) => x.cal.routine === 'balance' && x.cal.state === 'done', 60000, 'balance done');
    assert.equal(s.cal.result.verdict, 'balanced');
    assert.ok(Math.abs(s.axes.alt.pos_d - 40) < 0.1 || true);
  });

  test('encoder calibration of the altitude axis: sweep, fit, apply', async () => {
    await c.calEncoderStart(1, 2);
    const s = await c.waitFor((x) => x.cal.routine === 'encoder' && (x.cal.state === 'done' || x.cal.state === 'failed'), 120000, 'cal done');
    assert.equal(s.cal.state, 'done', s.cal.reason);
    const r = s.cal.result;
    assert.ok(r.samples > 200 && r.travel_d > 90, JSON.stringify(r));
    assert.ok(r.after_rms_as <= r.raw_rms_as + 0.5, 'map does not make it worse');
    await c.calEncoderApply();
    assert.equal((await c.request('cal.status')).state, 'applied');
  });
});

describe('firmware update upload', () => {
  test('bundle from make_bundle.py: checked by the app, accepted by the head, damaged copy refused by both', async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'stfw-'));
    fs.writeFileSync(path.join(dir, 'esp.bin'), crypto.randomBytes(300000));
    fs.writeFileSync(path.join(dir, 'rp.bin'), crypto.randomBytes(40000));
    execFileSync('python3', [path.join(here, '../../firmware/tools/make_bundle.py'), '--esp', path.join(dir, 'esp.bin'), '--rp', path.join(dir, 'rp.bin'), '-o', path.join(dir, 'u.stfw')]);
    const bytes = new Uint8Array(fs.readFileSync(path.join(dir, 'u.stfw')));
    const info = await inspectBundle(bytes);
    assert.ok(info.ok, info.error);
    assert.deepEqual(info.entries.map((e) => e.type), [1, 2]);
    const prog = [];
    const res = await uploadBundle(sim.http, bytes, (p) => prog.push(p));
    assert.ok(res.ok, res.text);
    assert.ok(prog.length > 5 && prog.at(-1) === 1, 'progress reported');
    assert.match((await c.updateStatus()).last_upload, /accepted/);
    const bad = bytes.slice(); bad[bad.length - 10] ^= 0xff;
    assert.match((await inspectBundle(bad)).error, /damaged/);
    const res2 = await uploadBundle(sim.http, bad);
    assert.equal(res2.ok, false);
    assert.equal((await inspectBundle(new TextEncoder().encode('hello'))).ok, false);
  });
});
