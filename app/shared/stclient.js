// Star Tracker — device client for WebSocket JSON API v1.
//
//   const c = new StClient({ url: 'ws://192.168.4.1/ws/v1' });
//   c.on('state', s => …); c.on('conn', st => …);
//   await c.connect();                    // resolves after hello (or after the first state event on a 1.0 head)
//   await c.goto({ ra_h: 5.58, dec_d: -5.39 });   // rejects with StError {code, msg} if the head says no
//
// Requests are matched to replies by id. The head pushes a state event 5×/s, which doubles as the heartbeat: two
// seconds without one and the client reconnects (1, 2, 5, 5 … s), then says hello again with the last seq it saw.
// Runs in the Android WebView, the Windows window and Node 22 (global WebSocket) without changes.
import { ERR, OPS, parseState, validate } from './models.js';

export class StError extends Error {
  constructor(code, msg, op) { super(`${op ? op + ': ' : ''}${msg} (${code})`); this.code = code; this.op = op; this.headMsg = msg; }
}

const BACKOFF_S = [1, 2, 5];
export const CONN = Object.freeze({ OFFLINE: 'offline', CONNECTING: 'connecting', LIVE: 'live', RECONNECTING: 'reconnecting' });

export class StClient {
  /**
   * @param {Object} o
   * @param {string} o.url              ws://host[:port]/ws/v1
   * @param {Function} [o.WebSocket]    implementation (default: global WebSocket)
   * @param {number} [o.timeoutMs]      per-request timeout (default 5000)
   * @param {number} [o.staleMs]        no state event for this long = link lost (default 2000)
   * @param {string} [o.app]            app name/version sent in hello
   * @param {boolean} [o.validate]      check requests against the models before sending (default true)
   */
  constructor(o) {
    this.url = o.url;
    this.WS = o.WebSocket || globalThis.WebSocket;
    this.timeoutMs = o.timeoutMs ?? 5000;
    this.staleMs = o.staleMs ?? 2000;
    this.app = o.app || 'startracker-app';
    this.check = o.validate !== false;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();          // id -> {resolve, reject, timer, op}
    this.stateWaiters = [];            // for the 1.0 'state' reply, which carries no id
    this.listeners = new Map();
    this.conn = CONN.OFFLINE;
    this.state = null;                 // latest HeadState
    this.info = null;                  // hello result (1.1) or {api:'1.0'}
    this.lastSeq = 0;
    this.lastEventAt = 0;
    this.attempt = 0;
    this.wanted = false;
    this.stats = { events: 0, reconnects: 0, gaps: 0, replies: 0 };
    this._watch = null;
    this._retry = null;
  }

  // ------------------------------------------------------------ events
  on(ev, fn) { if (!this.listeners.has(ev)) this.listeners.set(ev, new Set()); this.listeners.get(ev).add(fn); return () => this.off(ev, fn); }
  off(ev, fn) { this.listeners.get(ev)?.delete(fn); }
  emit(ev, ...a) { for (const fn of this.listeners.get(ev) || []) { try { fn(...a); } catch (e) { /* a screen's bug must not kill the link */ console.error(e); } } }

  _setConn(c, why) { if (this.conn !== c) { this.conn = c; this.emit('conn', c, why || ''); } }

  /** api version as a number, e.g. 1.1 */
  get api() { return this.info ? parseFloat(this.info.api) : 1.0; }
  supports(op) { const s = OPS[op]; return !!s && parseFloat(s.since) <= this.api + 1e-9; }

  // ------------------------------------------------------------ connection
  connect() {
    this.wanted = true;
    return new Promise((resolve, reject) => {
      let settled = false;
      const offLive = this.on('conn', (c, why) => {
        if (settled) return;
        if (c === CONN.LIVE) { settled = true; offLive(); resolve(this.info); }
        else if (c === CONN.RECONNECTING && this.attempt >= 1 && !this.everLive) { settled = true; offLive(); reject(new StError(ERR.OFFLINE, why || 'cannot reach the head')); }
      });
      this._open();
    });
  }

  close() {
    this.wanted = false;
    clearTimeout(this._retry); clearInterval(this._watch);
    if (this.ws) { try { this.ws.close(); } catch (e) { /* already closed */ } }
    this.ws = null;
    this._failAll(ERR.OFFLINE, 'disconnected');
    this._setConn(CONN.OFFLINE, 'closed by the app');
  }

  _open() {
    clearTimeout(this._retry);
    this._setConn(this.everLive ? CONN.RECONNECTING : CONN.CONNECTING);
    let ws;
    try { ws = new this.WS(this.url); } catch (e) { this._lost(String(e.message || e)); return; }
    this.ws = ws;
    ws.onopen = () => { clearTimeout(openTimer); this._onOpen(ws); };
    ws.onmessage = (m) => this._onMessage(typeof m.data === 'string' ? m.data : String(m.data));
    // Some WebSocket implementations (Node's undici) report a failed opening with 'error' only and never 'close',
    // and a dead Wi-Fi link may report nothing: treat an error before 'open', or 5 s without 'open', as a lost link.
    const openTimer = setTimeout(() => { if (this.ws === ws && ws.readyState !== 1) { try { ws.close(); } catch (e) { /* */ } this._lost('no answer from the head'); } }, 5000);
    ws.onerror = () => { if (this.ws === ws && ws.readyState !== 1) { clearTimeout(openTimer); this._lost('cannot open the connection'); } };
    ws.onclose = () => { clearTimeout(openTimer); if (this.ws === ws) this._lost('connection closed'); };
  }

  async _onOpen(ws) {
    if (this.ws !== ws) return;
    this.lastEventAt = Date.now();
    clearInterval(this._watch);
    this._watch = setInterval(() => {
      if (this.ws === ws && Date.now() - this.lastEventAt > this.staleMs) { try { ws.close(); } catch (e) { /* */ } this._lost('no state from the head for 2 s'); }
    }, Math.min(500, this.staleMs / 2));
    // Say hello. A 1.0 head answers "invalid op hello": fall back to 1.0 behaviour.
    try {
      const r = await this.request('hello', { app: this.app, last_seq: this.lastSeq }, { skipCheck: true });
      this.info = r || { api: '1.1' };
      if (this.info.seq !== undefined && this.lastSeq && this.info.seq > this.lastSeq + 1) this.stats.gaps++;
    } catch (e) {
      if (e.code === ERR.INVALID || e.code === ERR.NOTIMPL) this.info = { api: '1.0' };
      else { this._lost('hello failed: ' + e.message); return; }
    }
    if (this.ws !== ws) return;
    this.attempt = 0;
    if (this.everLive) this.stats.reconnects++;
    this.everLive = true;
    this._setConn(CONN.LIVE);
    this.emit('hello', this.info);
  }

  _lost(why) {
    clearInterval(this._watch);
    this.ws = null;
    this._failAll(ERR.OFFLINE, why);
    if (!this.wanted) { this._setConn(CONN.OFFLINE, why); return; }
    const wait = BACKOFF_S[Math.min(this.attempt, BACKOFF_S.length - 1)] * 1000;
    this.attempt++;
    this._setConn(CONN.RECONNECTING, why);
    this.emit('retry', this.attempt, wait);
    this._retry = setTimeout(() => this._open(), wait);
  }

  _failAll(code, why) {
    for (const [, p] of this.pending) { clearTimeout(p.timer); p.reject(new StError(code, why, p.op)); }
    this.pending.clear();
    for (const w of this.stateWaiters.splice(0)) { clearTimeout(w.timer); w.reject(new StError(code, why, 'state')); }
  }

  _onMessage(text) {
    let j;
    try { j = JSON.parse(text); } catch (e) { this.emit('protocol', 'not JSON: ' + text.slice(0, 80)); return; }
    if (j.ev === 'state') {
      this.lastEventAt = Date.now();
      const s = parseState(j);
      if (s.seq) { if (this.lastSeq && s.seq > this.lastSeq + 1) this.stats.gaps++; this.lastSeq = s.seq; }
      this.state = s;
      this.stats.events++;
      // a 1.0 head answers the 'state' op with an event that has no id
      if (typeof j.id === 'number' && this.pending.has(j.id)) { this._settle(j.id, true, s); return; }
      const w = this.stateWaiters.shift();
      if (w) { clearTimeout(w.timer); w.resolve(s); }
      this.emit('state', s);
      return;
    }
    if (j.ev) { this.emit('event', j); this.emit('ev:' + j.ev, j); return; }
    if (typeof j.id === 'number' && this.pending.has(j.id)) {
      this.stats.replies++;
      if (j.ok) this._settle(j.id, true, j.result);
      else this._settle(j.id, false, j.err || { code: ERR.ERROR, msg: 'no error text' });
    }
  }

  _settle(id, ok, v) {
    const p = this.pending.get(id);
    if (!p) return;
    this.pending.delete(id);
    clearTimeout(p.timer);
    if (p.waiter) { const i = this.stateWaiters.indexOf(p.waiter); if (i >= 0) this.stateWaiters.splice(i, 1); clearTimeout(p.waiter.timer); }
    if (ok) p.resolve(v); else p.reject(new StError(v.code || ERR.ERROR, v.msg || '', p.op));
  }

  // ------------------------------------------------------------ requests
  /**
   * Send one request and wait for its reply.
   * @returns {Promise<any>} the reply's result (undefined when the head sends none)
   */
  request(op, args = {}, opt = {}) {
    if (this.check && !opt.skipCheck) {
      const bad = validate(op, args);
      if (bad) return Promise.reject(new StError(ERR.INVALID, bad, op));
    }
    const ws = this.ws;
    if (!ws || ws.readyState !== 1) return Promise.reject(new StError(ERR.OFFLINE, 'not connected', op));
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new StError(ERR.TIMEOUT, `no reply in ${opt.timeoutMs ?? this.timeoutMs} ms`, op));
      }, opt.timeoutMs ?? this.timeoutMs);
      const p = { resolve, reject, timer, op };
      this.pending.set(id, p);
      if (op === 'state') {
        // 1.0 compatibility: the reply is a state event without id, so the next event answers it too
        p.waiter = { resolve: (s) => this._settle(id, true, s), reject, timer: null };
        this.stateWaiters.push(p.waiter);
      }
      ws.send(JSON.stringify({ v: 1, id, op, args }));
    });
  }

  /** Wait until a predicate on the state is true (or time out). */
  waitFor(pred, timeoutMs = 60000, what = 'condition') {
    if (this.state && pred(this.state)) return Promise.resolve(this.state);
    return new Promise((resolve, reject) => {
      const off = this.on('state', (s) => { if (pred(s)) { clearTimeout(t); off(); resolve(s); } });
      const t = setTimeout(() => { off(); reject(new StError(ERR.TIMEOUT, `waiting for ${what}`)); }, timeoutMs);
    });
  }

  // ------------------------------------------------------------ typed helpers (section 6.1 + 1.1 additions)
  goto(a) { return this.request('goto', a, { timeoutMs: 8000 }); }
  gotoRaDec(ra_h, dec_d, epoch = 'J2000') { return this.goto({ ra_h, dec_d, epoch }); }
  gotoAltAz(az_d, alt_d) { return this.goto({ az_d, alt_d }); }
  gotoBody(body) { return this.goto({ body }); }
  sync(ra_h, dec_d, epoch = 'J2000') { return this.request('sync', { ra_h, dec_d, epoch }); }
  track(on, rate) { return this.request('track', rate ? { on, rate } : { on }); }
  stop() { return this.request('stop'); }
  park() { return this.request('park'); }
  unpark() { return this.request('unpark'); }
  setPark() { return this.request('park.set'); }
  jog(axis, dps) { return this.request('jog', { axis, dps }); }
  guide(dir, ms) { return this.request('guide', { dir, ms }); }
  rotatorPA(pa_d) { return this.request('rotator.pa', { pa_d }); }
  rotatorRoll(roll_d) { return this.request('rotator.roll', { roll_d }); }
  alignClear() { return this.request('align.clear'); }
  setTime(unix_s) { return this.request('time.set', { unix_s }); }
  getConfig() { return this.request('config.get'); }
  setConfig(kv) { return this.request('config.set', kv); }
  ivmStart(a) { return this.request('ivm.start', a); }
  ivmStop() { return this.request('ivm.stop'); }
  getState() { return this.request('state'); }
  // 1.1
  limits() { return this.request('limits.get'); }
  faults(since = 0) { return this.request('faults.get', { since }); }
  clearFaults() { return this.request('faults.clear'); }
  health() { return this.request('health.get'); }
  pecStatus() { return this.request('pec.status'); }
  pecRecord(axis, cycles) { return this.request('pec.record', { axis, cycles }); }
  pecStop() { return this.request('pec.stop'); }
  pecPlay(on) { return this.request('pec.play', { on }); }
  pecSave() { return this.request('pec.save'); }
  pecClear(axis) { return this.request('pec.clear', { axis }); }
  pecCurve(axis) { return this.request('pec.get', { axis }); }
  jobStart(a) { return this.request('job.start', a); }
  jobPause() { return this.request('job.pause'); }
  jobResume() { return this.request('job.resume'); }
  jobStop() { return this.request('job.stop'); }
  jobStatus() { return this.request('job.status'); }
  jobAck(job_id, frame) { return this.request('job.ack', { job_id, frame }); }
  calEncoderStart(axis, speed_dps) { return this.request('cal.encoder.start', speed_dps ? { axis, speed_dps } : { axis }); }
  calEncoderStatus() { return this.request('cal.encoder.status'); }
  calEncoderAbort() { return this.request('cal.encoder.abort'); }
  calEncoderApply() { return this.request('cal.encoder.apply'); }
  calBalance(swing_d = 5) { return this.request('cal.balance', { swing_d }, { timeoutMs: 60000 }); }
  updateStatus() { return this.request('update.status'); }
}

/** One-shot transport for native code and scripts: POST one request to /startracker/v1/op (API 1.1). */
export async function httpOp(base, op, args = {}, fetchImpl = globalThis.fetch) {
  const r = await fetchImpl(`${base}/startracker/v1/op`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ v: 1, id: 1, op, args }) });
  const j = await r.json();
  if (!j.ok) throw new StError(j.err?.code || ERR.ERROR, j.err?.msg || 'error', op);
  return j.result;
}
