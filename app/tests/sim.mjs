// Start and stop the simulator (firmware/sim) for the tests. Binary: $ST_SIM, else the usual build folders.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const CANDIDATES = [process.env.ST_SIM, path.join(here, '../../firmware/sim/build/startracker-sim'),
  path.join(here, '../../firmware/sim/build/Release/StarTrackerSim.exe'), path.join(here, '../../firmware/sim/build/StarTrackerSim.exe'),
  '/home/claude/simbuild/startracker-sim'].filter(Boolean);
export const SIM_BIN = CANDIDATES.find((p) => fs.existsSync(p));

export async function startSim(args = [], httpPort = 8080) {
  if (!SIM_BIN) throw new Error('simulator not found: build firmware/sim or set ST_SIM');
  const p = spawn(SIM_BIN, ['--http-port', String(httpPort), ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
  let out = '';
  p.stdout.on('data', (d) => { out += d; });
  p.stderr.on('data', (d) => { out += d; });
  for (let i = 0; i < 100; i++) {
    await new Promise((r) => setTimeout(r, 100));
    try { const r = await fetch(`http://127.0.0.1:${httpPort}/startracker/v1/info`); if (r.ok) break; } catch (e) { /* not up yet */ }
  }
  return {
    proc: p, url: `ws://127.0.0.1:${httpPort}/ws/v1`, http: `http://127.0.0.1:${httpPort}`, log: () => out,
    stop: () => new Promise((r) => { if (p.exitCode !== null) return r(); p.once('exit', r); p.kill(); }),
  };
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
