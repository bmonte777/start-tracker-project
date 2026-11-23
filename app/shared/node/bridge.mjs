// Discovery bridge for Node (tests, scripts): Alpaca UDP discovery and HTTP GET. mDNS is left to the native shells.
import dgram from 'node:dgram';

export const nodeBridge = {
  async httpGetJson(url, timeoutMs = 1000) {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), timeoutMs);
    try {
      const r = await fetch(url, { signal: ac.signal });
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; } finally { clearTimeout(t); }
  },
  alpaca(timeoutMs = 2000, target = '255.255.255.255') {
    return new Promise((resolve) => {
      const s = dgram.createSocket('udp4');
      const found = [];
      s.on('message', (m, r) => {
        try { const j = JSON.parse(m.toString()); if (j.AlpacaPort) found.push({ host: r.address, port: j.AlpacaPort }); } catch (e) { /* not ours */ }
      });
      s.bind(0, () => {
        s.setBroadcast(true);
        const q = Buffer.from('alpacadiscovery1');
        s.send(q, 32227, target);
        if (target !== '127.0.0.1') s.send(q, 32227, '127.0.0.1');
      });
      setTimeout(() => { s.close(); resolve(found.filter((f, i) => found.findIndex((g) => g.host === f.host) === i)); }, timeoutMs);
    });
  },
};
