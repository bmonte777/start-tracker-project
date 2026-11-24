// Device-client unit tests against the running simulator (real firmware logic and servers, docs/05-firmware.md section 7).
import assert from 'node:assert/strict';
import { after, before, describe, test } from 'node:test';
import { CONN, StClient, StError, httpOp } from '../shared/stclient.js';
import { CONFIG_KEYS, CONFIG_READONLY, OPS, parseState, validate } from '../shared/models.js';
import { discover, wsUrlFrom } from '../shared/discovery.js';
import { nodeBridge } from '../shared/node/bridge.mjs';
import { sleep, startSim } from './sim.mjs';

let sim, c;
before(async () => {
  sim = await startSim(['--speed', '20']);
  c = new StClient({ url: sim.url, app: 'client-test' });
  await c.connect();
});
after(async () => { c.close(); await sim.stop(); });

describe('connection', () => {
  test('hello reports API 1.1, the simulator, and every op the client knows', () => {
    assert.equal(c.info.api, '1.1');
    assert.equal(c.info.platform, 'simulator');
    for (const op of Object.keys(OPS)) assert.ok(c.info.ops.includes(op), `head lacks ${op}`);
    assert.equal(c.conn, CONN.LIVE);
  });

  test('state events arrive 5 times a second with increasing seq and every field typed', async () => {
    const seen = [];
    const off = c.on('state', (s) => seen.push(s));
    await sleep(1200);
    off();
    assert.ok(seen.length >= 4 && seen.length <= 8, `got ${seen.length} events in 1.2 s`);
    for (let i = 1; i < seen.length; i++) assert.ok(seen[i].seq > seen[i - 1].seq, 'seq increases');
    const s = seen.at(-1);
    for (const k of ['pos_d', 'enc_d', 'rate_dps', 'i_ma', 'load', 'temp_c', 'flags']) assert.equal(typeof s.axes.roll[k], 'number');
    assert.equal(typeof s.batt.soc, 'number');
    assert.equal(typeof s.motor.link, 'boolean');
    assert.ok(s.pec && s.cal, 'pec and cal objects present (1.1)');
    assert.deepEqual(Object.keys(s.extra), [], 'no unknown fields');
  });

  test('the state op is answered with its id (Phase 6 fix)', async () => {
    const s = await c.getState();
    assert.equal(typeof s.seq, 'number');
    assert.equal(c.pending.size, 0);
  });

  test('config.get returns exactly the documented keys', async () => {
    const cfg = await c.getConfig();
    assert.deepEqual(Object.keys(cfg).sort(), [...Object.keys(CONFIG_KEYS), ...CONFIG_READONLY].sort());
  });
});

describe('requests and errors', () => {
  test('client-side validation stops a request the head would refuse', async () => {
    await assert.rejects(c.jog(1, 9), (e) => e instanceof StError && e.code === 'invalid');
    assert.match(validate('config.set', { payload: 6 }), /payload/);
    assert.equal(validate('config.set', { payload: 4, mode: 'eq' }), '');
  });

  test('head errors come back as StError with the head\'s code', async () => {
    await assert.rejects(c.request('goto', { az_d: 0, alt_d: -40 }, { skipCheck: true }), (e) => e.code === 'limit');
    await assert.rejects(c.request('nonsense.op', {}, { skipCheck: true }), (e) => e.code === 'invalid');
  });

  test('config.set round trip (site, refraction) and a bad value refused', async () => {
    await c.setConfig({ pressure_hpa: 990, temp_c: 4 });
    const cfg = await c.getConfig();
    assert.equal(cfg.pressure_hpa, 990);
    assert.equal(cfg.temp_c, 4);
    await assert.rejects(c.request('config.set', { lat: 120 }, { skipCheck: true }), (e) => e.code === 'invalid');
    await c.setConfig({ pressure_hpa: 1010, temp_c: 10 });
  });

  test('time.set reaches the head clock (Phase 6 fix)', async () => {
    const t = Date.UTC(2027, 7, 2, 21, 0, 0) / 1000;      // 2 Aug 2027 21:00 UTC (Conil eclipse year)
    await c.setTime(t);
    const s = await c.waitFor((x) => x.t.startsWith('2027-08-02T21:0'), 3000, 'the new time');
    assert.ok(s.t.startsWith('2027-08-02'));
    await c.setTime(Date.now() / 1000);
    await c.waitFor((x) => x.t.startsWith(new Date().toISOString().slice(0, 10)), 3000, 'time back');
  });

  test('one-shot HTTP op transport gives the same answer', async () => {
    const r = await httpOp(sim.http, 'config.get');
    assert.equal(r.name, 'Canopus-SIM');
    await assert.rejects(httpOp(sim.http, 'goto', { az_d: 0, alt_d: -40 }), (e) => e.code === 'limit');
  });
});

describe('queries added in 1.1', () => {
  test('limits.get follows the payload envelope (P3, then P5 caps altitude without a pier extension)', async () => {
    let L = await c.limits();
    assert.equal(L.payload, 3);
    assert.equal(L.alt_cap_d, null);
    assert.equal(L.roll_max_d, 5);                 // 8 - 3 margin
    assert.equal(L.roll_min_d, -147);              // -150 + 3
    await c.setConfig({ payload: 5, pier_extension: false, wedge_fitted: true });
    L = await c.limits();
    assert.equal(L.alt_cap_d, 50);
    assert.equal(L.alt_max_d, 47);
    await c.setConfig({ payload: 3 });
  });

  test('faults.get returns the log with seq; faults.clear empties it', async () => {
    await c.request('goto', { az_d: 0, alt_d: 80 });       // fine
    const f = await c.faults(0);
    assert.ok(Array.isArray(f.entries));
    assert.equal(typeof f.seq, 'number');
    await c.clearFaults();
    assert.equal((await c.faults(0)).entries.length, 0);
    await c.stop();
  });

  test('health.get has three axes and the battery', async () => {
    const h = await c.health();
    assert.deepEqual(h.axes.map((a) => a.axis), ['az', 'alt', 'roll']);
    assert.equal(typeof h.battery.soc, 'number');
    assert.equal(typeof h.battery.cycles, 'number');   // D79: passed on from the gauge (simulator: 37)
    assert.equal(h.battery.cells_v.length, 2);
  });

  test('update.status answers', async () => {
    const u = await c.updateStatus();
    assert.equal(u.api, '1.1');
  });
});

describe('discovery', () => {
  test('Alpaca discovery on UDP 32227 finds the simulator, info gives the WebSocket URL', async () => {
    const found = await discover(nodeBridge, { timeoutMs: 1000 });
    assert.ok(found.length >= 1, 'found a head');
    assert.equal(found[0].via, 'alpaca');
    assert.equal(found[0].ws, sim.url.replace('127.0.0.1', found[0].host));
  });
  test('last-head shortcut answers first', async () => {
    const found = await discover(nodeBridge, { last: { host: '127.0.0.1', port: 8080 } });
    assert.equal(found[0].via, 'last');
    assert.equal(wsUrlFrom('127.0.0.1', found[0].info), sim.url);
  });
});

test('parseState fills defaults for a 1.0 event', () => {
  const s = parseState({ v: 1, ev: 'state', mode: 'tracking', axes: { az: { pos_d: 1 } } });
  assert.equal(s.seq, 0);
  assert.equal(s.axes.alt.pos_d, 0);
  assert.equal(s.job, null);
});
