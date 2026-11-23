"""Board viewer: one self-contained HTML page with an interactive BOM for every board that has a fab package,
the 3D renders, and a Day / Night switch.     usage: python3 tools/viewer.py     -> doc/board-viewer.html

Click a BOM line to light up its parts on the board; click a part on the board to find its line.
Needs KiCad 9 (pcbnew, kicad-cli) and rsvg-convert, like the other tools here.
"""
import base64
import csv
import io
import json
import os
import subprocess
import tempfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, "..", "..", "docs", "img")
TITLES = {"st-501": ("ST-501 mainboard", "mainboard"), "st-520": ("ST-520 cartridge board", "cartridge-board"),
          "st-602": ("ST-602 battery board", "battery-board")}
PX_PER_MM = {"st-501": 16, "st-520": 30, "st-602": 26}


def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def shrink(png):
    """Palette PNG if Pillow is there (about a third of the size)."""
    try:
        from PIL import Image
        im = Image.open(png).convert("RGB").quantize(96)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        open(png, "wb").write(buf.getvalue())
    except Exception:
        pass


def board(name):
    title, folder = TITLES[name]
    pcbfile = os.path.join(ROOT, folder, name + ".kicad_pcb")
    bomfile = os.path.join(ROOT, "fab", name, name + "-bom.csv")
    released = os.path.exists(bomfile)
    if not released:
        bomfile = os.path.join(ROOT, folder, name + "-bom.csv")
        title += " (layout in progress)"
    if not (os.path.exists(pcbfile) and os.path.exists(bomfile)):
        return None
    b = pcbnew.LoadBoard(pcbfile)
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0, w, h = (pcbnew.ToMM(v) for v in (bb.GetX(), bb.GetY(), bb.GetWidth(), bb.GetHeight()))
    comps = {}
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        pads = list(fp.Pads())
        if not pads:
            continue
        xs, ys = [], []
        for p in pads:
            r = p.GetBoundingBox()
            xs += [pcbnew.ToMM(r.GetX()), pcbnew.ToMM(r.GetX() + r.GetWidth())]
            ys += [pcbnew.ToMM(r.GetY()), pcbnew.ToMM(r.GetY() + r.GetHeight())]
        side = "B" if fp.IsFlipped() else "F"
        a, c = (min(xs) - x0) / w, (max(xs) - x0) / w
        if side == "B":                       # the back view is mirrored left-right
            a, c = 1 - c, 1 - a
        comps[ref] = [side, round(a, 4), round((min(ys) - y0) / h, 4), round(c - a, 4), round((max(ys) - min(ys)) / h, 4), fp.GetValue()]
    images = {}
    with tempfile.TemporaryDirectory() as tmp:
        for side, layers, mirror in (("F", "F.Cu,F.Fab,F.SilkS,Edge.Cuts", False), ("B", "B.Cu,B.Fab,B.SilkS,Edge.Cuts", True)):
            svg, png = os.path.join(tmp, side + ".svg"), os.path.join(tmp, side + ".png")
            cmd = ["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--mode-single", "--exclude-drawing-sheet", "--page-size-mode", "2",
                   "-o", svg, pcbfile]
            if mirror:
                cmd.insert(4, "--mirror")
            subprocess.run(cmd, capture_output=True)
            subprocess.run(["rsvg-convert", "-w", str(int(w * PX_PER_MM[name])), "-b", "white", svg, "-o", png], capture_output=True)
            shrink(png)
            images[side] = b64(png, "image/png")
    rows = []
    for r in csv.DictReader(open(bomfile)):
        rows.append([r["Comment"], r["Designator"].split(","), r["Footprint"], r["LCSC Part #"], r.get("MPN", "")])
    renders = []
    for tag in ("top", "bottom"):
        p = os.path.join(IMG, f"04-{name}-{tag}.png")
        if os.path.exists(p):
            renders.append([tag, b64(p, "image/png")])
    return dict(id=name, title=title, w=round(w, 2), h=round(h, 2), comps=comps, img=images, bom=rows, renders=renders)


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Star Tracker — board viewer</title>
<style>
:root{--bg:#f6f5f1;--panel:#ffffff;--ink:#1c1d21;--mute:#666a73;--line:#d9d7d0;--acc:#b5471b;--hit:rgba(255,196,0,.55);--hitb:#b06a00;--row:#fff3d6}
html[data-theme=night]{--bg:#111316;--panel:#1a1d22;--ink:#e9e6df;--mute:#9aa0aa;--line:#2c3038;--acc:#ff9a62;--hit:rgba(255,120,60,.55);--hitb:#ffb38a;--row:#3a2a1c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 "Avenir Next","Segoe UI",system-ui,sans-serif}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;padding:14px 20px;border-bottom:1px solid var(--line)}
h1{font-size:19px;margin:0 auto 0 0;font-weight:650;letter-spacing:.01em}h1 small{color:var(--mute);font-weight:400;margin-left:8px}
button{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:6px 12px;cursor:pointer}
button[aria-pressed=true]{background:var(--acc);color:#fff;border-color:var(--acc)}
main{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:18px;padding:18px 20px}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.bar .sp{margin-left:auto;color:var(--mute);font-size:13px}
#stage{position:relative;line-height:0;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:#fff}
#stage img{width:100%;height:auto;display:block}html[data-theme=night] #stage img{filter:invert(1) hue-rotate(180deg) brightness(.92)}
html[data-theme=night] #stage{background:#000}
.c{position:absolute;border:1px solid transparent;border-radius:2px;cursor:pointer}.c:hover{border-color:var(--hitb)}
.c.on{background:var(--hit);border-color:var(--hitb);box-shadow:0 0 0 2px var(--hitb)}
#tip{min-height:22px;color:var(--mute);font-size:13px;margin-top:8px}
input[type=search]{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--ink);flex:1;min-width:140px}
.tbl{max-height:70vh;overflow:auto;border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--panel);font-weight:600;z-index:1}tbody tr{cursor:pointer}tbody tr:hover{background:var(--bg)}
tbody tr.on{background:var(--row)}td.q{text-align:right;font-variant-numeric:tabular-nums}td.refs{color:var(--mute);word-break:break-word}
td.no{color:var(--acc)}.renders{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-top:14px}
.renders figure{margin:0}.renders img{width:100%;border-radius:6px;border:1px solid var(--line)}figcaption{color:var(--mute);font-size:13px;margin-top:4px}
footer{padding:0 20px 24px;color:var(--mute);font-size:13px}
</style></head><body>
<header><h1>Board viewer<small>Star Tracker Project · Phase 4</small></h1><span id="tabs"></span>
<button id="theme" aria-label="Switch between day and night display">Night</button></header>
<main>
<section class="card"><div class="bar"><button id="sF" aria-pressed="true">Front</button><button id="sB" aria-pressed="false">Back</button>
<span class="sp" id="dims"></span></div><div id="stage"></div><div id="tip">Click a part or a parts-list line.</div>
<div class="renders" id="renders"></div></section>
<section class="card"><div class="bar"><input type="search" id="q" placeholder="Filter: value, reference, LCSC number" aria-label="Filter the parts list">
<span class="sp" id="count"></span></div><div class="tbl"><table><thead><tr><th>Value</th><th>Qty</th><th>References</th><th>LCSC</th><th>Maker part</th></tr></thead>
<tbody id="bom"></tbody></table></div></section>
</main>
<footer>Built from the KiCad files by <code>hardware/electronics/tools/viewer.py</code>. A line with no LCSC number is a part to pick in JLCPCB's parts matcher or to fit by hand. The back view is drawn as you see it when the board is turned over.</footer>
<script>
const DATA = __DATA__;
let cur = DATA[0], side = "F", sel = -1;
const $ = id => document.getElementById(id);
function theme(t){document.documentElement.dataset.theme=t;$("theme").textContent=t==="night"?"Day":"Night";try{localStorage.setItem("st-theme",t)}catch(e){}}
let t0="day";try{t0=localStorage.getItem("st-theme")||(matchMedia("(prefers-color-scheme: dark)").matches?"night":"day")}catch(e){}
theme(t0);$("theme").onclick=()=>theme(document.documentElement.dataset.theme==="night"?"day":"night");
function tabs(){$("tabs").innerHTML="";DATA.forEach(b=>{const x=document.createElement("button");x.textContent=b.title;x.setAttribute("aria-pressed",b===cur);
 x.onclick=()=>{cur=b;sel=-1;side="F";draw()};$("tabs").appendChild(x);$("tabs").appendChild(document.createTextNode(" "))})}
function stage(){const s=$("stage");s.innerHTML="";const im=document.createElement("img");im.src=cur.img[side];im.alt=cur.title+(side==="F"?" front":" back");s.appendChild(im);
 const on=sel>=0?new Set(cur.bom[sel][1]):new Set();
 for(const [ref,c] of Object.entries(cur.comps)){if(c[0]!==side)continue;const d=document.createElement("div");d.className="c"+(on.has(ref)?" on":"");
  d.style.cssText=`left:${c[1]*100}%;top:${c[2]*100}%;width:${c[3]*100}%;height:${c[4]*100}%`;d.title=ref+"  "+c[5];
  d.onclick=()=>{const i=cur.bom.findIndex(r=>r[1].includes(ref));pick(i,ref)};s.appendChild(d)}
 $("sF").setAttribute("aria-pressed",side==="F");$("sB").setAttribute("aria-pressed",side==="B");
 $("dims").textContent=cur.w+" × "+cur.h+" mm · "+Object.keys(cur.comps).length+" parts"}
function pick(i,ref){sel=i;if(i<0){$("tip").textContent=ref?ref+" is not in the parts list (not fitted, or a test pad).":"";stage();rows();return}
 const r=cur.bom[i],f=r[1].filter(x=>cur.comps[x]&&cur.comps[x][0]==="F").length,b=r[1].filter(x=>cur.comps[x]&&cur.comps[x][0]==="B").length;
 if(ref&&cur.comps[ref])side=cur.comps[ref][0];else if((side==="F"&&!f&&b)||(side==="B"&&!b&&f))side=f?"F":"B";
 $("tip").textContent=r[0]+" — "+r[1].length+" × ("+f+" front, "+b+" back)"+(r[3]?" · LCSC "+r[3]:" · no LCSC number");stage();rows();
 const tr=document.querySelector("tbody tr.on");if(tr&&ref)tr.scrollIntoView({block:"nearest"})}
function rows(){const q=$("q").value.trim().toLowerCase(),tb=$("bom");tb.innerHTML="";let n=0;
 cur.bom.forEach((r,i)=>{const hay=(r[0]+" "+r[1].join(" ")+" "+r[3]+" "+r[4]).toLowerCase();if(q&&!hay.includes(q))return;n++;
  const tr=document.createElement("tr");if(i===sel)tr.className="on";
  tr.innerHTML=`<td></td><td class="q">${r[1].length}</td><td class="refs"></td><td class="${r[3]?"":"no"}"></td><td></td>`;
  tr.children[0].textContent=r[0];tr.children[2].textContent=r[1].join(" ");tr.children[3].textContent=r[3]||"—";tr.children[4].textContent=r[4];
  tr.onclick=()=>pick(i===sel?-1:i);tb.appendChild(tr)});
 $("count").textContent=n+" of "+cur.bom.length+" lines"}
function renders(){$("renders").innerHTML="";cur.renders.forEach(([tag,src])=>{const f=document.createElement("figure");
 f.innerHTML=`<img alt="3D render, ${tag}"><figcaption>3D render, ${tag} side</figcaption>`;f.firstChild.src=src;$("renders").appendChild(f)})}
function draw(){tabs();stage();rows();renders();$("tip").textContent="Click a part or a parts-list line."}
$("sF").onclick=()=>{side="F";stage()};$("sB").onclick=()=>{side="B";stage()};$("q").oninput=rows;draw();
</script></body></html>
"""


def main():
    data = [d for d in (board(n) for n in ("st-501", "st-520", "st-602")) if d]
    out = os.path.join(ROOT, "doc", "board-viewer.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(PAGE.replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    print("wrote", out, round(os.path.getsize(out) / 1e6, 2), "MB;", ", ".join(f"{d['id']}: {len(d['comps'])} parts, {len(d['bom'])} lines" for d in data))


if __name__ == "__main__":
    main()
