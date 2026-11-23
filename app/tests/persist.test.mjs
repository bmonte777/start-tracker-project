// D78 and D79 against the simulator: PEC tables and the fault log survive a restart (the simulator's --data folder
// runs the same FileStore code the head runs on LittleFS), and health.get carries the gauge's cycles, SoH and cells.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { StClient } from '../shared/stclient.js';
import { sleep, startSim } from './sim.mjs';

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'st-data-'));

async function open(args = []) {
  const sim = await startSim(['--speed', '50', '--data', dir, ...args]);
  const c = new StClient({ url: sim.url, app: 'persist-test' });
  await c.connect();
  return { sim, c };
}

test('PEC table and fault log are kept across a restart; health.get reports the gauge', async () => {
  let { sim, c } = await open();
  let faultSeq, pecTable;
  try {
    // a fault entry: a USB-camera job nobody acks pauses itself and logs why
    await c.jobStart({ type: 'poses', shutter: 'app', poses: [{ az_d: 200, alt_d: 30 }], settle_s: 0.5, ack_timeout_s: 20 });
    await c.waitFor((s) => s.job?.state === 'paused', 30000, 'pause');
    await c.jobStop();
    const f1 = await c.faults(0);
    assert.equal(f1.persistent, true);
    const paused = f1.entries.find((e) => /job paused/.test(e.msg));
    assert.ok(paused, 'job paused entry');
    faultSeq = paused.seq;

    // a PEC table, played and saved
    await c.gotoRaDec(5.27815, 45.99799);
    await c.waitFor((s) => s.mode === 'tracking', 60000, 'tracking');
    await c.pecRecord(0, 1);
    await c.waitFor((x) => x.pec.state === 'ready', 120000, 'PEC ready');
    await c.pecPlay(true);
    await c.pecSave();
    const st = await c.pecStatus();
    assert.equal(st.saved, true);
    pecTable = (await c.pecCurve(0)).table_as;
    assert.ok(fs.existsSync(path.join(dir, 'pec0.tbl')), 'pec0.tbl written');

    // D79
    const h = await c.health();
    assert.equal(h.battery.cycles, 37);
    assert.equal(h.battery.soh_pct, 97);
    assert.equal(h.battery.cells_v.length, 2);
    assert.ok(Math.abs(h.battery.cells_v[0] + h.battery.cells_v[1] - h.battery.v) < 0.01, 'cells add up to the pack');
  } finally { c.close(); await sim.stop(); }

  // restart on the same folder: everything is back without the app sending anything
  ({ sim, c } = await open());
  try {
    const f2 = await c.faults(0);
    assert.ok(f2.entries.some((e) => e.seq === faultSeq && /job paused/.test(e.msg)), 'fault entry kept');
    assert.ok(f2.seq >= faultSeq, 'sequence continues');
    const st = await c.pecStatus();
    assert.equal(st.saved, true);
    assert.equal(st.state, 'playing');
    const t2 = (await c.pecCurve(0)).table_as;
    assert.deepEqual(t2, pecTable);

    // pec.clear removes the saved copy too; faults.clear empties the file
    await c.pecClear(0);
    assert.equal(fs.existsSync(path.join(dir, 'pec0.tbl')), false);
    await c.request('faults.clear');
    assert.equal((await c.faults(0)).entries.length, 0);
  } finally { c.close(); await sim.stop(); }

  ({ sim, c } = await open());
  try {
    assert.equal((await c.pecStatus()).saved, false);
    assert.ok(!(await c.faults(0)).entries.some((e) => e.seq === faultSeq), 'cleared log stays cleared');
  } finally { c.close(); await sim.stop(); fs.rmSync(dir, { recursive: true, force: true }); }
});

test('a damaged table file is ignored, not loaded', async () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'st-data-'));
  const good = Buffer.alloc(12 + 2 * 1024);
  good.write('STT1', 0); good.writeUInt32LE(1024, 4);
  for (let i = 0; i < 1024; i++) good.writeInt16LE(100, 8 + 2 * i);
  let sum = 0; for (let i = 0; i < good.length - 4; i++) sum += good[i];
  good.writeUInt32LE(sum >>> 0, good.length - 4);
  good[20] ^= 0xff;                                       // damage one byte: checksum no longer matches
  fs.writeFileSync(path.join(d, 'pec1.tbl'), good);
  const sim = await startSim(['--speed', '50', '--data', d]);
  const c = new StClient({ url: sim.url, app: 'persist-test' });
  await c.connect();
  try {
    await sleep(300);
    const st = await c.pecStatus();
    assert.equal(st.saved, false);
    assert.equal(st.state, 'idle');
  } finally { c.close(); await sim.stop(); fs.rmSync(d, { recursive: true, force: true }); }
});
