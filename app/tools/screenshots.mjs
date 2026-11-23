#!/usr/bin/env node
// Screenshots of every screen in Day, Night and Red against the running simulator, plus an end-to-end check that each
// screen renders without errors. Needs Chrome/Chromium and puppeteer-core (npm i puppeteer-core; CI installs it).
//   node app/tools/screenshots.mjs [--out docs/img/06-screens] [--chrome /path/to/chrome] [--sizes desktop,phone]
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { startSim, sleep } from '../tests/sim.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(here, '..');
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const OUT = path.resolve(arg('--out', path.join(APP, '../docs/img/06-screens')));
const CHROME = arg('--chrome', process.env.CHROME || ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  'C:/Program Files/Google/Chrome/Application/chrome.exe'].find((p) => fs.existsSync(p)));
const SIZES = { desktop: { width: 1440, height: 1000 }, phone: { width: 412, height: 915, isMobile: true, deviceScaleFactor: 2 } };
const sizes = arg('--sizes', 'desktop').split(',');
const require = createRequire(process.env.PUPPETEER_DIR ? path.join(process.env.PUPPETEER_DIR, 'x.js') : import.meta.url);
const puppeteer = require('puppeteer-core');

const SCREENS = arg('--screens', 'connect,dashboard,sky,align,rig,roll,camera,night,gallery,pec,health,update,settings').split(',');
const THEMES = arg('--themes', 'day,night,red').split(',');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json' };

const server = http.createServer((req, res) => {
  const p = path.join(APP, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(APP) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(5599, r));
const sim = await startSim(['--speed', '1']);
fs.mkdirSync(OUT, { recursive: true });
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-gpu'] });
const report = [];
try {
  // put the simulated head in an interesting state: tracking Capella with the field held
  const { StClient } = await import('../shared/stclient.js');
  const c = new StClient({ url: sim.url });
  await c.connect();
  await c.gotoRaDec(5.27815, 45.99799);
  await c.waitFor((s) => s.mode === 'tracking', 120000);
  await c.rotatorPA(c.state.radec.rot_d);
  await c.sync(5.27815 + 20 / 3600 / 15, 45.99799 + 15 / 3600);
  c.close();
  for (const size of sizes) {
    for (const theme of THEMES) {
      for (const scr of SCREENS) {
        const page = await browser.newPage();
        await page.setViewport(SIZES[size]);
        const errors = [];
        page.on('pageerror', (e) => errors.push(e.message));
        page.on('console', (m) => { if (m.type() === 'error' && !/favicon|ERR_CONNECTION_REFUSED|Failed to load resource|blocked by CORS policy/.test(m.text())) errors.push(m.text()); });
        await page.goto(`http://127.0.0.1:5599/ui/index.html?head=127.0.0.1:8080&theme=${theme}#/${scr}`, { waitUntil: 'load' });
        await page.waitForFunction((s) => window.__screenReady === s && window.__st && window.__st.state, { timeout: 20000 }, scr).catch((e) => errors.push('not ready: ' + e.message));
        await sleep(scr === 'pec' || scr === 'health' || scr === 'rig' ? 2500 : 1500);
        const file = path.join(OUT, `${scr}-${theme}${size === 'desktop' ? '' : '-' + size}.png`);
        await page.screenshot({ path: file, fullPage: true });
        const empty = await page.evaluate(() => document.querySelector('#view').innerText.trim().length < 20);
        report.push({ screen: scr, theme, size, ok: errors.length === 0 && !empty, errors, file: path.relative(path.join(APP, '..'), file) });
        console.log(`${errors.length || empty ? 'FAIL' : 'PASS'} ${scr} ${theme} ${size}${errors.length ? '  ' + errors.join(' | ') : ''}`);
        await page.close();
      }
    }
  }
} finally {
  await browser.close();
  await sim.stop();
  server.close();
}
fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 1));
const bad = report.filter((r) => !r.ok).length;
console.log(`${report.length - bad} of ${report.length} screen renders passed`);
process.exit(bad ? 1 : 0);
