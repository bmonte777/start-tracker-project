// Firmware update for the head: pick a .stfw bundle, the app checks it, uploads it with progress, then waits for the
// head to come back and compares the version (docs/05-firmware.md section 8.5, Q49).
import { $, act, esc, needHead, pageHead, store, toast } from '../app.js';
import { inspectBundle, uploadBundle } from '../../shared/stfw.js';
import { CONN } from '../../shared/stclient.js';

export async function render(root) {
  root.innerHTML = pageHead('Head firmware', 'Firmware update', 'One file updates both processors; if anything fails the head goes back to the firmware it had.') + `
  <div class="grid three">
    <section class="card lead"><h2>On the head now</h2><table id="now"></table></section>
    <section class="card span2"><h2>Update</h2>
      <ol class="how"><li>Get <b>star-tracker-update.stfw</b> from the Firmware workflow run on GitHub (Actions → Firmware → the newest run → <b>esp32s3-images-and-flasher</b>).</li>
        <li>Pick it below. The app checks every image’s checksum before anything is sent.</li><li>Keep the head on power (USB-C or a charged pack) until it says it is back.</li></ol>
      <div class="row mt"><input id="file" type="file" accept=".stfw"><button id="send" class="primary" disabled>Update the head</button></div>
      <div id="check" class="mt"></div><div class="progress mt"><span id="bar" style="width:0"></span></div><div id="msg" class="msg mt"></div></section>
  </div>`;
  if (needHead(root)) return;
  const showNow = async () => {
    try {
      const u = await store.client.updateStatus();
      $('#now', root).innerHTML = `<tr><td>Firmware</td><td>${esc(u.fw)}</td></tr><tr><td>App API</td><td>${esc(u.api)}</td></tr>
        <tr><td>Running slot</td><td>${esc(u.running_slot || '—')}</td></tr><tr><td>Can go back</td><td>${u.rollback_possible ? 'yes' : 'no'}</td></tr>
        ${u.last_upload ? `<tr><td>Last upload</td><td style="white-space:normal">${esc(u.last_upload)}</td></tr>` : ''}${u.rp_good_copy !== undefined ? `<tr><td>Motion processor copy</td><td>${u.rp_good_copy ? 'kept' : 'none'}</td></tr>` : ''}`;
    } catch (e) { $('#now', root).innerHTML = `<tr><td>Firmware</td><td>${esc(store.info?.fw || '—')}</td></tr>`; }
  };
  showNow();
  let bytes = null;
  $('#file', root).onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    bytes = new Uint8Array(await f.arrayBuffer());
    const r = await inspectBundle(bytes);
    $('#check', root).innerHTML = r.ok ? `<div class="state ok">Bundle checked</div><table>${r.entries.map((x) => `<tr><td>${esc(x.name)}</td><td>${(x.size / 1024).toFixed(0)} KB · checksum OK</td></tr>`).join('')}</table>`
      : `<div class="state bad">Not usable</div><p>${esc(r.error)}</p>`;
    $('#send', root).disabled = !r.ok;
  };
  $('#send', root).onclick = (e) => act(e.target, async () => {
    const before = store.info?.fw;
    $('#msg', root).textContent = 'Sending…';
    const r = await uploadBundle(store.head.http, bytes, (p) => { $('#bar', root).style.width = (p * 100).toFixed(0) + '%'; });
    if (!r.ok) throw new Error(r.text || `the head refused the bundle (HTTP ${r.status})`);
    $('#msg', root).textContent = r.text + '. Waiting for the head to come back…';
    const t0 = Date.now();
    await new Promise((res) => setTimeout(res, 3000));
    while (Date.now() - t0 < 180000) {
      if (store.conn === CONN.LIVE && Date.now() - t0 > 4000) break;
      await new Promise((res) => setTimeout(res, 1000));
    }
    await showNow();
    $('#msg', root).textContent = store.conn === CONN.LIVE ? `The head is back${store.info?.fw && store.info.fw !== before ? ` with firmware ${store.info.fw}` : ''}.` : 'The head has not come back yet: check its screen.';
    toast('Update sent');
  });
}
