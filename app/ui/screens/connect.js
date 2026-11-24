// Connect / first set-up: find the head, join its network, give it your Wi-Fi over BLE, set location and time.
import { $, act, connectTo, esc, findHeads, pageHead, refreshConfig, store, toast } from '../app.js';
import { CONN } from '../../shared/stclient.js';
import { wsUrlFrom, httpBaseFrom } from '../../shared/discovery.js';
import { CH_STATUS, CH_WIFI, isHeadAdvert, parseStatus, wifiPayload } from '../../shared/ble.js';
import { ble, discoveryBridge, hasShell, location as deviceLocation, openSettings, platform } from '../../shared/native.js';

let off = null;
export function leave() { if (off) off(); }

const STAGES = { last: 'Trying the last head…', mdns: 'Looking on this network (mDNS)…', alpaca: 'Asking for Alpaca devices (UDP 32227)…', ap: 'Trying the head’s own access point…', done: '' };

export async function render(root) {
  root.innerHTML = pageHead('Connect · first set-up', 'Find your head', 'The app looks for the head on your network, on its own Wi-Fi, or over Bluetooth.') + `
  <div class="grid three">
    <section class="card lead span2">
      <h2>Heads found</h2>
      <div id="status" class="state">…</div>
      <div id="stage" class="msg"></div>
      <ol id="found" class="mt"></ol>
      <div class="btns"><button id="find" class="primary">Look again</button><button id="disc" hidden>Disconnect</button></div>
      <div class="hr"></div>
      <h3>Type an address</h3>
      <div class="row"><input id="addr" type="text" placeholder="192.168.1.42 or name:8080" style="flex:1;min-width:200px"><button id="go">Connect</button></div>
      <p class="small mt">The simulator answers on <span class="k">localhost:8080</span>. The head’s own Wi-Fi is <span class="k">Canopus-XXXX</span> at <span class="k">192.168.4.1</span>; its password is on the head’s screen (network page).</p>
    </section>
    <section class="card">
      <h2>No GNSS fix yet?</h2>
      <p>Indoors or right after switching on, the head may not know where and when it is. Send it this ${platform() === 'android' ? 'phone' : 'device'}’s position and clock.</p>
      <div class="btns"><button id="loc">Send my location</button><button id="time">Send my time</button></div>
      <div id="locmsg" class="msg mt"></div>
    </section>
    <section class="card span2">
      <h2>Give the head your Wi-Fi (Bluetooth)</h2>
      <div class="steps">
        <div class="step"><div>Switch the head on. Its screen shows a <b>6-digit code</b> on the network page (button 2 or 3 to change page).</div></div>
        <div class="step"><div><button id="scan">Search for heads over Bluetooth</button> <span id="blemsg" class="small"></span><ol id="bles" class="mt"></ol></div></div>
        <div class="step"><div>Pick your head; ${platform() === 'windows' ? 'Windows' : 'Android'} asks for the code: type the one on the head’s screen.</div></div>
        <div class="step"><div class="stack" style="width:100%">
          <div class="row"><input id="ssid" type="text" placeholder="Your Wi-Fi name" style="flex:1"><input id="psk" type="text" placeholder="Password" style="flex:1"></div>
          <div><button id="sendwifi" disabled>Send Wi-Fi to the head</button> <span id="wifimsg" class="small"></span></div></div></div>
      </div>
      ${hasShell() ? '' : '<div class="warn">Bluetooth set-up needs the Canopus app on Android or Windows. In a browser, join the head’s own Wi-Fi instead.</div>'}
    </section>
    <section class="card">
      <h2>Or use the head’s own Wi-Fi</h2>
      <ol class="how"><li>Open your ${platform() === 'windows' ? 'computer' : 'phone'}’s Wi-Fi settings.</li><li>Join <b>Canopus-XXXX</b> with the password on the head’s screen.</li><li>Come back here and press <b>Look again</b>.</li></ol>
      <div class="btns"><button id="wifiset">Open Wi-Fi settings</button></div>
    </section>
  </div>`;

  const list = $('#found', root);
  let heads = [];
  const show = () => {
    const live = store.conn === CONN.LIVE;
    $('#status', root).className = 'state ' + (live ? 'ok' : '');
    $('#status', root).textContent = live ? `Connected to ${store.info?.name || store.head?.host}` : store.conn === CONN.OFFLINE ? 'Not connected' : store.conn === CONN.RECONNECTING ? 'Reconnecting…' : 'Connecting…';
    $('#disc', root).hidden = store.conn === CONN.OFFLINE;
    list.innerHTML = heads.length ? heads.map((h, i) => `<li><span class="t"><b>${esc(h.info.name)}</b>${esc(h.host)} · firmware ${esc(h.info.fw)} · API ${esc(h.info.api)} · found by ${esc(h.via)}${h.info.platform === 'simulator' ? ' · simulator' : ''}</span>
      <button data-i="${i}" ${store.head && store.head.host === h.host && store.conn === CONN.LIVE ? 'disabled' : ''}>${store.head && store.head.host === h.host && store.conn === CONN.LIVE ? 'Connected' : 'Connect'}</button></li>`).join('')
      : '<li><span class="t">None yet.</span></li>';
  };
  off = store.on(show);
  const find = async () => {
    $('#find', root).disabled = true;
    heads = await findHeads((st) => { $('#stage', root).textContent = STAGES[st] || ''; });
    $('#find', root).disabled = false;
    $('#stage', root).textContent = heads.length ? '' : 'Nothing found. Check that the head is on and on the same network, or set it up over Bluetooth below.';
    show();
  };
  list.addEventListener('click', async (e) => {
    const b = e.target.closest('button[data-i]');
    if (!b) return;
    b.disabled = true;
    if (await connectTo(heads[+b.dataset.i])) location.hash = '#/dashboard';
    show();
  });
  $('#find', root).onclick = find;
  $('#disc', root).onclick = () => { store.client?.close(); store.set({ client: null, conn: CONN.OFFLINE, state: null }); };
  $('#go', root).onclick = async () => {
    const v = $('#addr', root).value.trim();
    if (!v) return;
    const [host, port] = v.replace(/^\w+:\/\//, '').split(':');
    const info = await discoveryBridge.httpGetJson(`http://${host}:${port || 80}/startracker/v1/info`, 2500);
    if (!info) { toast(`No Canopus head answers at ${v}`, 'bad'); return; }
    if (await connectTo({ host, info, ws: wsUrlFrom(host, info), http: httpBaseFrom(host, info), via: 'typed' })) location.hash = '#/dashboard';
  };
  $('#loc', root).onclick = (e) => act(e.target, async () => {
    if (!store.client) throw new Error('connect to the head first');
    const p = await deviceLocation();
    await store.client.setConfig({ lat: +p.lat.toFixed(5), lon: +p.lon.toFixed(5), elev_m: Math.round(p.elev_m || 0) });
    await refreshConfig();
    $('#locmsg', root).textContent = `Sent ${p.lat.toFixed(4)}°, ${p.lon.toFixed(4)}°.`;
  });
  $('#time', root).onclick = (e) => act(e.target, async () => {
    if (!store.client) throw new Error('connect to the head first');
    await store.client.setTime(Date.now() / 1000);
    $('#locmsg', root).textContent = `Sent ${new Date().toISOString().replace('T', ' ').slice(0, 19)} UTC. A GNSS fix takes over when it comes.`;
  });
  $('#wifiset', root).onclick = () => openSettings('wifi');
  let bleId = null;
  $('#scan', root).onclick = (e) => act(e.target, async () => {
    $('#blemsg', root).textContent = 'Searching…';
    const found = (await ble.scan(6000)).filter((d) => isHeadAdvert(d.name, d.uuids));
    $('#blemsg', root).textContent = found.length ? '' : 'No head found. Is Bluetooth on, and the head switched on?';
    $('#bles', root).innerHTML = found.map((d) => `<li><span class="t"><b>${esc(d.name)}</b>signal ${d.rssi} dBm</span><button data-id="${esc(d.id)}">Pair</button></li>`).join('');
  });
  $('#bles', root).addEventListener('click', (e) => {
    const b = e.target.closest('button[data-id]');
    if (!b) return;
    act(b, async () => { await ble.connect(b.dataset.id); bleId = b.dataset.id; $('#sendwifi', root).disabled = false; b.textContent = 'Paired'; });
  });
  $('#sendwifi', root).onclick = (e) => act(e.target, async () => {
    await ble.write(bleId, CH_WIFI, wifiPayload($('#ssid', root).value.trim(), $('#psk', root).value));
    $('#wifimsg', root).textContent = 'Sent. The head joins your network…';
    for (let i = 0; i < 20; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const st = parseStatus(await ble.read(bleId, CH_STATUS));
      if (st && st.ip && st.ip !== '0.0.0.0') { $('#wifimsg', root).textContent = `Joined: ${st.ip}. Looking for it…`; await ble.disconnect(bleId); find(); return; }
    }
    $('#wifimsg', root).textContent = 'The head did not report an address. Check the Wi-Fi name and password and send again.';
  });
  show();
  find();
}
