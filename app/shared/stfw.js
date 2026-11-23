// Star Tracker — firmware update bundle (.stfw) check and upload.
// Format (firmware/tools/make_bundle.py, firmware/esp32s3/components/st_app/ota.cpp):
//   header 64 bytes, little-endian: "STFW" | u32 version (1) | u32 entries (1–2) | u32 reserved |
//   per entry, 24 bytes from offset 16: u8 type (1 = ESP32 app, 2 = RP2354A image) | u8[3] pad | u32 offset | u32 size |
//   u8[12] first 12 bytes of the image's SHA-256;  then the images.
// The head checks the full SHA-256 while writing; the app checks it before sending so a damaged download never reaches
// the head. Upload: POST /api/update with the raw bundle as the body.

export const ENTRY_TYPES = Object.freeze({ 1: 'ESP32-S3 application', 2: 'RP2354A motion image' });
export const RP_MAX = 0x7F000;          // ota.cpp: RP2354A image limit (508 KB)
export const ESP_MAX = 4 * 1024 * 1024; // 4 MB OTA slot (docs/05-firmware.md 3.3)

async function sha256(bytes) {
  if (globalThis.crypto?.subtle) return new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes));
  const { createHash } = await import('node:crypto');
  return new Uint8Array(createHash('sha256').update(bytes).digest());
}

/**
 * Parse and check a bundle. Never throws: returns {ok, error, version, entries:[{type, name, offset, size, shaOk}]}.
 * @param {ArrayBuffer|Uint8Array} buf
 */
export async function inspectBundle(buf) {
  const b = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  const out = { ok: false, error: '', version: 0, size: b.length, entries: [] };
  if (b.length < 64) { out.error = 'file is too short to be a Star Tracker bundle'; return out; }
  const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
  if (String.fromCharCode(b[0], b[1], b[2], b[3]) !== 'STFW') { out.error = 'not a Star Tracker bundle (.stfw)'; return out; }
  out.version = dv.getUint32(4, true);
  const n = dv.getUint32(8, true);
  if (out.version !== 1) { out.error = `bundle version ${out.version}; this app understands version 1`; return out; }
  if (n < 1 || n > 2) { out.error = `bundle has ${n} images; 1 or 2 expected`; return out; }
  let prevEnd = 64;
  for (let i = 0; i < n; i++) {
    const p = 16 + 24 * i;
    const type = b[p], offset = dv.getUint32(p + 4, true), size = dv.getUint32(p + 8, true);
    const e = { type, name: ENTRY_TYPES[type] || `unknown type ${type}`, offset, size, shaOk: false };
    out.entries.push(e);
    if (!ENTRY_TYPES[type]) { out.error = e.name; return out; }
    if (offset < prevEnd || offset + size > b.length || size === 0) { out.error = `image ${i + 1} lies outside the file`; return out; }
    if (type === 2 && size > RP_MAX) { out.error = 'RP2354A image is larger than the head accepts (508 KB)'; return out; }
    if (type === 1 && size > ESP_MAX) { out.error = 'ESP32-S3 image is larger than its 4 MB slot'; return out; }
    const dig = await sha256(b.subarray(offset, offset + size));
    e.shaOk = dig.subarray(0, 12).every((x, k) => x === b[p + 12 + k]);
    if (!e.shaOk) { out.error = `image ${i + 1} (${e.name}) is damaged: checksum does not match`; return out; }
    prevEnd = offset + size;
  }
  out.ok = true;
  return out;
}

/**
 * Upload a checked bundle to the head. Reports progress 0–1. Uses XMLHttpRequest where it exists (WebView, Windows
 * window: real upload progress), otherwise fetch with a counting stream (Node).
 * @returns {Promise<{ok:boolean, status:number, text:string}>}
 */
export function uploadBundle(base, bytes, onProgress = () => {}) {
  const url = `${base}/api/update`;
  if (typeof XMLHttpRequest !== 'undefined') {
    return new Promise((resolve) => {
      const x = new XMLHttpRequest();
      x.open('POST', url);
      x.setRequestHeader('Content-Type', 'application/octet-stream');
      x.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
      x.onload = () => { onProgress(1); resolve({ ok: x.status === 200, status: x.status, text: x.responseText }); };
      x.onerror = () => resolve({ ok: false, status: 0, text: 'the head did not answer' });
      x.send(bytes);
    });
  }
  const total = bytes.length, CH = 16384;
  let sent = 0;
  const body = new ReadableStream({
    pull(ctrl) {
      if (sent >= total) { ctrl.close(); return; }
      const n = Math.min(CH, total - sent);
      ctrl.enqueue(bytes.subarray(sent, sent + n));
      sent += n;
      onProgress(sent / total);
    },
  });
  return fetch(url, { method: 'POST', body, duplex: 'half', headers: { 'Content-Type': 'application/octet-stream', 'Content-Length': String(total) } })
    .then(async (r) => ({ ok: r.ok, status: r.status, text: await r.text() }))
    .catch((e) => ({ ok: false, status: 0, text: String(e.message || e) }));
}
