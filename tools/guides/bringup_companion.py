"""Render the P0 bring-up companion (docs/guides/p0-bringup-companion.html) from bringup_data.py.

Same look as the P0 build guide. Day/Night toggle; ticks kept in the browser (localStorage, wrapped in try/catch).
Usage: python tools/guides/bringup_companion.py
"""
from __future__ import annotations

from pathlib import Path

import bringup_data as D

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "guides" / "p0-bringup-companion.html"

CSS = """
/* VOICE  workshop service manual, calm and exact - the companion to the P0 build guide
   IDEA   the test sheet clipped beside the bench: one row per check, the reading to expect, what to do if it is off
   PICTURE the build-and-test route (stages between build sheets), then the sheet itself
   COLOUR aluminium-grey ground, graphite ink, anodised-orange accent, green ticks; night = graphite bench under a lamp
   TYPE   Barlow Condensed 700 (stamped labels) + Barlow
   LAYOUT laptop: steps as a table (do / expect / if wrong); phone: each step a stacked card */
:root{color-scheme:light dark;--bg:light-dark(#e9eaec,#14161a);--panel:light-dark(#ffffff,#1d2026);--ink:light-dark(#16181c,#e8e9ec);--soft:light-dark(#5a606b,#a3a9b4);--line:light-dark(#cdd0d5,#333842);--acc:light-dark(#c9631a,#f08a3c);--accbg:light-dark(#fbe9db,#3a2717);--warn:light-dark(#a8261b,#ff7a6b);--warnbg:light-dark(#fbe3e0,#3a1c19);--ok:light-dark(#2f7d32,#6cc070);--okbg:light-dark(#e3f1e3,#1c2e1d)}
:root[data-theme=light]{color-scheme:light}
:root[data-theme=dark]{color-scheme:dark}
*{box-sizing:border-box;min-width:0}
html{scroll-padding-top:72px}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Barlow,system-ui,sans-serif;overflow-x:clip}
h1,h2,h3{font-family:"Barlow Condensed",Barlow,sans-serif;line-height:1.05;margin:0}
h1{font-size:clamp(34px,5vw,52px);text-wrap:balance}
h2{font-size:clamp(26px,3.4vw,34px)}
h3{font-size:20px;margin:16px 0 6px}
p{margin:.4em 0 .8em}
a{color:var(--acc)}
code{font:14px ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
.band{padding:clamp(22px,3.5vw,44px) max(4vw,16px)}
.wrap{max-width:1240px;margin:0 auto}
.lead{font-size:18px;max-width:66ch}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:16px 0 0}
.fact{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.fact b{display:block;font-family:"Barlow Condensed",sans-serif;font-size:24px;line-height:1.1}
.fact span{color:var(--soft);font-size:14px}
.route{background:var(--panel);border:1px solid var(--line);border-radius:14px;margin-top:18px;padding:10px;overflow-x:auto}
.route svg{display:block;width:100%;min-width:640px;height:auto}
.bar{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.bar .wrap{display:flex;gap:10px;align-items:center;padding:8px max(4vw,16px)}
.chips{display:flex;gap:6px;overflow-x:auto;flex:1;scrollbar-width:thin}
.chips a{flex:none;display:grid;place-items:center;min-width:44px;height:44px;padding:0 10px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);text-decoration:none;font:700 18px "Barlow Condensed",sans-serif}
.chips a.done{background:var(--ok);border-color:var(--ok);color:#fff}
.meter{flex:none;font-size:14px;color:var(--soft);white-space:nowrap}
button.theme{flex:none;height:44px;padding:0 14px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font:600 15px Barlow,sans-serif;cursor:pointer}
button:focus-visible,a:focus-visible,input:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;margin:0 auto 22px;max-width:1240px;overflow:hidden}
.card>header{display:flex;gap:14px;align-items:center;padding:16px 20px;border-bottom:1px solid var(--line)}
.num{flex:none;min-width:52px;height:52px;padding:0 8px;border-radius:10px;background:var(--acc);color:#fff;display:grid;place-items:center;font:700 28px "Barlow Condensed",sans-serif}
.card>header p{margin:2px 0 0;color:var(--soft)}
.inner{padding:16px 20px}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--soft);font-size:14px}
td.id{white-space:nowrap;font:700 18px "Barlow Condensed",sans-serif}
td.id small{display:block;font:600 13px Barlow,sans-serif;color:var(--soft)}
.key{display:inline-block;min-width:26px;text-align:center;border:1px solid var(--line);border-radius:6px;padding:0 6px;font:700 15px ui-monospace,Consolas,monospace;background:var(--bg)}
td.exp{background:var(--okbg)}
td.bad{color:var(--soft)}
td.tick{width:44px;text-align:center}
td.tick input,.checks input{width:24px;height:24px;accent-color:var(--ok)}
tr.ticked td{opacity:.62}
tr.ticked td.tick{opacity:1}
.note{border-left:4px solid var(--acc);background:var(--accbg);padding:10px 14px;border-radius:0 8px 8px 0;margin:10px 0}
.warn{border-left:4px solid var(--warn);background:var(--warnbg);padding:10px 14px;border-radius:0 8px 8px 0;margin:10px 0}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px}
ol,ul{padding-left:1.3em;margin:.3em 0 .8em}
li{margin:.3em 0}
.checks{list-style:none;padding:0}
.checks li{display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-bottom:1px dashed var(--line)}
footer{color:var(--soft);font-size:14px}
@media(max-width:820px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:700px){table{font-size:14px}.stack thead{display:none}.stack tr{display:grid;padding-block:10px;border-bottom:2px solid var(--line)}.stack td{display:flow-root;border:0;padding:4px 0;padding-inline-start:6.5em}.stack td::before{content:attr(data-l);float:inline-start;width:6em;margin-inline-start:-6.5em;color:var(--soft);font-size:13px}.stack td.tick{text-align:start}.stack td.exp{padding-inline-end:6px;border-radius:6px}}
@media print{.bar,button.theme{display:none}.card{break-inside:avoid}}
@media(prefers-reduced-motion:no-preference){.chips a{transition:background .2s}}
"""

JS = r"""
{
  const root = document.documentElement, tb = document.getElementById('theme');
  const sys = matchMedia('(prefers-color-scheme: dark)');
  const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const put = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} };
  let theme = get('st-theme');
  const apply = () => { const dark = theme ? theme === 'dark' : sys.matches; root.dataset.theme = dark ? 'dark' : 'light'; tb.textContent = dark ? 'Day' : 'Night'; };
  tb.addEventListener('click', () => { theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; put('st-theme', theme); apply(); });
  sys.addEventListener('change', apply); apply();
  for (const c of document.querySelectorAll('.stack td:not([data-l])')) { let i = 0, p = c; while ((p = p.previousElementSibling)) i += p.colSpan; c.dataset.l = c.closest('table').rows[0].cells[i]?.textContent || ''; }
  const boxes = [...document.querySelectorAll('input[data-k]')];
  const meter = document.getElementById('meter');
  const refresh = () => {
    let n = 0;
    for (const b of boxes) { const tr = b.closest('tr'); if (tr) tr.classList.toggle('ticked', b.checked); n += b.checked; }
    meter.textContent = n + ' of ' + boxes.length + ' checked';
    for (const a of document.querySelectorAll('.chips a[data-s]')) {
      const mine = boxes.filter((b) => b.dataset.s === a.dataset.s);
      a.classList.toggle('done', mine.length > 0 && mine.every((b) => b.checked));
    }
  };
  for (const b of boxes) { b.checked = get('st-bu-' + b.dataset.k) === '1'; b.addEventListener('change', () => { put('st-bu-' + b.dataset.k, b.checked ? '1' : null); refresh(); }); }
  document.getElementById('reset').addEventListener('click', () => { for (const b of boxes) { b.checked = false; put('st-bu-' + b.dataset.k, null); } refresh(); });
  refresh();
}
"""

ROUTE_SVG = """<svg viewBox="0 0 1200 150" role="img" aria-label="Build and bring-up route: Stage A on the cartridge board before build sheet 8; Stages B and C on the mainboard before sheet 11; sheets 12 and 13; Stage D on the rig; then the P0 measurements">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>
<g style="color:var(--soft)" stroke="currentColor" stroke-width="2" fill="none" marker-end="url(#ar)">
<path d="M150 75H190"/><path d="M330 75H370"/><path d="M510 75H550"/><path d="M690 75H730"/><path d="M870 75H910"/><path d="M1040 75H1060"/>
</g>
<g font-family="Barlow Condensed, sans-serif" text-anchor="middle">
<rect x="20" y="35" width="130" height="80" rx="10" fill="var(--acc)"/><text x="85" y="72" font-size="30" font-weight="700" fill="#fff">A</text><text x="85" y="98" font-size="15" fill="#fff">cartridge board</text>
<rect x="195" y="35" width="135" height="80" rx="10" fill="var(--panel)" stroke="var(--line)" stroke-width="2"/><text x="262" y="72" font-size="22" font-weight="700" fill="var(--ink)">Sheets 1–8</text><text x="262" y="98" font-size="15" fill="var(--soft)">cartridge built</text>
<rect x="375" y="35" width="135" height="80" rx="10" fill="var(--acc)"/><text x="442" y="72" font-size="30" font-weight="700" fill="#fff">B · C</text><text x="442" y="98" font-size="15" fill="#fff">mainboard, bench</text>
<rect x="555" y="35" width="135" height="80" rx="10" fill="var(--panel)" stroke="var(--line)" stroke-width="2"/><text x="622" y="72" font-size="22" font-weight="700" fill="var(--ink)">Sheets 9–13</text><text x="622" y="98" font-size="15" fill="var(--soft)">rig on the tripod</text>
<rect x="735" y="35" width="135" height="80" rx="10" fill="var(--acc)"/><text x="802" y="72" font-size="30" font-weight="700" fill="#fff">D</text><text x="802" y="98" font-size="15" fill="#fff">one axis moving</text>
<rect x="915" y="35" width="125" height="80" rx="10" fill="var(--ok)"/><text x="977" y="72" font-size="24" font-weight="700" fill="#fff">M</text><text x="977" y="98" font-size="15" fill="#fff">measurements</text>
<rect x="1065" y="35" width="120" height="80" rx="10" fill="var(--panel)" stroke="var(--line)" stroke-width="2" stroke-dasharray="6 4"/><text x="1125" y="72" font-size="22" font-weight="700" fill="var(--ink)">P1</text><text x="1125" y="98" font-size="15" fill="var(--soft)">gauge set-up</text>
</g></svg>"""


def steps_table(stage: dict) -> str:
    rows = []
    for sid, key, title, do, expect, bad in stage["steps"]:
        keys = " ".join(f'<span class="key">{k}</span>' for k in key.split()) if key else ""
        rows.append(
            f'<tr id="{sid}"><td class="id">{sid}<small>{keys}</small></td><td><b>{title}</b><br>{do}</td>'
            f'<td class="exp">{expect}</td><td class="bad">{bad}</td>'
            f'<td class="tick"><input type="checkbox" data-k="{sid}" data-s="{stage["id"]}" aria-label="{sid} done"></td></tr>')
    return ('<div class="scroll"><table class="stack"><thead><tr><th>Step</th><th>Do</th><th>Expect</th><th>If it is wrong</th><th>Done</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def card(num: str, cid: str, title: str, sub: str, body: str) -> str:
    return f'<section class="card" id="{cid}"><header><div class="num">{num}</div><div><h2>{title}</h2><p>{sub}</p></div></header><div class="inner">{body}</div></section>'


def main() -> None:
    n_steps = sum(len(s["steps"]) for s in D.STAGES) + len(D.PD_STEPS)
    parts = []
    # before you start
    before = "".join(f"<div><h3>{h}</h3><ul>{''.join(f'<li>{x}</li>' for x in items)}</ul></div>" for h, items in D.BEFORE)
    tools = "<h3>Tools by stage</h3><ul>" + "".join(f"<li><b>{s}</b>: {t}</li>" for s, t in D.TOOLS) + "</ul>"
    safety = '<div class="warn"><b>Safety, every time</b><ul>' + "".join(f"<li>{x}</li>" for x in D.SAFETY) + "</ul></div>"
    parts.append(card("0", "start", "Before you start", "Files, recording, safety, parts that may be missing", f'{safety}<div class="two">{before}</div>{tools}'))
    for st in D.STAGES:
        body = f'<p>{st["intro"]}</p>{steps_table(st)}<div class="note">{st["after"]}</div>'
        parts.append(card(st["id"], st["id"], st["title"], st["when"], body))
        if st["id"] == "C":
            pass
    # PD card placed right after C
    pd_rows = "".join(
        f'<tr id="{sid}"><td class="id">{sid}</td><td><b>{title}</b><ol>{"".join(f"<li>{x}</li>" for x in items)}</ol></td>'
        f'<td class="tick"><input type="checkbox" data-k="{sid}" data-s="PD" aria-label="{sid} done"></td></tr>'
        for sid, title, items in D.PD_STEPS)
    pd = card("PD", "PD", "USB-C PD configuration (for C3 and C4)", "TI's customization tool, the web flasher and menu item P · once per board",
              '<p>The two PD controllers start from a configuration image in their EEPROM (D70). TI\'s tool makes the image; the web flasher puts it on the board; menu item <span class="key">P</span> writes it into each controller\'s EEPROM. Answers below are the Phase 5 section 9.1 settings.</p>'
              f'<div class="scroll"><table class="stack"><thead><tr><th>Step</th><th>Do</th><th>Done</th></tr></thead><tbody>{pd_rows}</tbody></table></div>')
    c_idx = next(i for i, p in enumerate(parts) if 'id="C"' in p)
    parts.insert(c_idx + 1, pd)
    # measurements hand-off
    mrows = "".join(f"<tr><td><span class='key'>{k}</span></td><td class='n'>{d}</td><td>{w}</td><td><code>{s}</code></td></tr>" for k, d, w, s in D.MEASURE)
    parts.append(card("M", "M", "Then the P0 measurements", "Procedures in docs/measurements/procedures.md · analysis in tools/measure/",
                      "<p>With Stage D passed, the same menu runs the measurement items with longer settings; the system firmware and the app run the rest. Each run gives a file; send it to me and I return the number against the spec.</p>"
                      f"<div class='scroll'><table class='stack'><thead><tr><th>Item</th><th>Takes</th><th>What it measures</th><th>Script</th></tr></thead><tbody>{mrows}</tbody></table></div>"))
    # gauge (P1)
    g = "<ol class='checks'>" + "".join(f"<li><input type='checkbox' data-k='G{i + 1}' data-s='G' aria-label='gauge step {i + 1} done'><span>{x}</span></li>" for i, x in enumerate(D.GAUGE)) + "</ol>"
    parts.append(card("G", "G", "Battery gauge in bqStudio (P1)", "EV2400 on the pack's blade connector · settings from firmware/config/bq40z50-r2-p50b.csv", g))
    trows = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td></tr>" for a, b in D.TROUBLE)
    parts.append(card("?", "help", "When something is off", "Quick answers; everything else: stop and send me the log",
                      f"<div class='scroll'><table class='stack'><thead><tr><th>Symptom</th><th>Do</th></tr></thead><tbody>{trows}</tbody></table></div>"))
    chips = "".join(f'<a href="#{c}" data-s="{c}">{c}</a>' for c in ["A", "B", "C", "PD", "D", "G"])
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>P0 Bring-up Companion</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="bar"><div class="wrap"><nav class="chips" aria-label="Stages"><a href="#start">0</a>{chips}<a href="#M">M</a><a href="#help">?</a></nav><span class="meter" id="meter">0 checked</span><button class="theme" id="theme" type="button" aria-label="Switch between day and night display">Night</button></div></div>
<div class="band"><div class="wrap">
<h1>P0 bring&#8209;up companion</h1>
<p class="lead">Stages A–D of the Phase 4 plan, run from the Phase 5 bring-up menu, as a sheet to tick off: what to do, the reading to expect, and what to do when it is wrong. It goes hand in hand with the build guide.</p>
<div class="facts"><div class="fact"><b>4 stages</b><span>A cartridge · B, C mainboard · D rig</span></div><div class="fact"><b>{n_steps} checks</b><span>plus the gauge set-up for P1</span></div><div class="fact"><b>50 mA → 4.5 A</b><span>supply limit grows stage by stage</span></div><div class="fact"><b>Every test → a file</b><span>bench logger, for the measurements</span></div></div>
<div class="route">{ROUTE_SVG}</div>
</div></div>
<div class="band" style="padding-top:0">
{''.join(parts)}
<footer class="wrap"><p>Star Tracker Project · Phase 7, round P0 · from docs/04-electronics.md section 11, docs/05-firmware.md sections 4, 8–10, the bring-up code (tests.c, bringup.cpp), the ST-520 and ST-501 design files and the MT6835 datasheet · 24 Nov 2026. Nothing here has run on hardware yet: every reading is the expected value, not a measured one. <button id="reset" type="button" class="theme" style="height:36px">Clear all ticks</button></p></footer>
</div>
<script>{JS}</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(html):,} bytes, {n_steps} checks)")


if __name__ == "__main__":
    main()
