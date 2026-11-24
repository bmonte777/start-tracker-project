// Gallery and shot log: the pictures the app downloaded from the camera (reused gallery code, CameraNative.gallery()).
import { $, esc, pageHead } from '../app.js';
import { camera } from '../../shared/native.js';

export async function render(root) {
  root.innerHTML = pageHead('Pictures', 'Gallery', 'Frames downloaded over USB-C, newest first, grouped by night.') + '<div id="g"></div>';
  const box = $('#g', root);
  if (!camera.present()) {
    box.innerHTML = `<div class="notice">The gallery shows the pictures the Canopus app downloaded from the camera
      (Pictures/Canopus on Android, Pictures\\Canopus on Windows) and its shot log. Open it in the app.</div>
      <div class="card mt"><h2>Shot log</h2><p>Each frame is logged with the time, the camera settings, and where the head pointed (RA/Dec, alt/az, roll), as CSV next to the pictures.</p></div>`;
    return;
  }
  let items = [];
  try { items = camera.call('gallery') || []; } catch (e) { box.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
  if (!items.length) { box.innerHTML = '<div class="notice">No pictures yet.</div>'; return; }
  let day = '', html = '';
  for (const it of items) {
    const d = (it.date || '').slice(0, 10);
    if (d !== day) { day = d; html += `<div class="day">${esc(d)}</div>`; }
    html += `<button class="item" data-id="${esc(it.id)}" data-mime="${esc(it.mime || '')}"><div class="img" data-thumb="${esc(it.id)}">${esc((it.name || '').split('.').pop().toUpperCase())}</div><span>${esc(it.name)}</span></button>`;
  }
  box.innerHTML = `<div class="photos">${html}</div>`;
  box.addEventListener('click', (e) => { const b = e.target.closest('.item'); if (b) camera.call('galleryOpen', b.dataset.id, b.dataset.mime); });
  for (const el of box.querySelectorAll('[data-thumb]')) {
    try { const t = camera.call('galleryThumb', el.dataset.thumb); if (t) el.innerHTML = `<img alt="" src="data:image/jpeg;base64,${t}">`; } catch (e) { /* no thumbnail */ }
  }
}
