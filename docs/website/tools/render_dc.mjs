// Renders the Design-canvas pages (*.dc.html) into standalone HTML pages that
// work offline: loops and values are filled in, Day/Night and the demo form use
// a few lines of plain JavaScript. Usage: node render_dc.mjs <srcDir> <outDir>
import fs from 'node:fs';
import path from 'node:path';

const [src, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });

const pages = { 'Main.dc.html': 'index.html', 'Specs.dc.html': 'specs.html', 'Support.dc.html': 'support.html' };
const blobs = {
  '/_blob/12d2d53c5b0a99ddc92edc060ae45968': 'img/hero.png',
  '/_blob/0791821435e59ae0f53ad3f2e01d8bba': 'img/eq.png',
  '/_blob/a28843005f49ec8c8b96213e7ed4b51a': 'img/nowedge.png',
  '/_blob/b7598c840154be8f391982556541e3b8': 'img/p5.png',
  '/_blob/31f5c098e53cef98b5c1425710c3489c': 'img/cartridge.png',
  '/_blob/03b104636784d6dcff4c41cfc0bfc3fd': 'img/battery.png',
};

class DCLogic { constructor() { this.state = {}; this.props = {}; } setState() {} }

function lookup(expr, scope) {
  expr = expr.trim();
  if (expr === 'false') return false;
  return expr.split('.').reduce((o, k) => (o == null ? undefined : o[k]), scope);
}
const esc = (v) => String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function findClose(s, tag, from) {
  const open = new RegExp(`<${tag}\\b`, 'g'), close = new RegExp(`</${tag}>`, 'g');
  let depth = 1, i = from;
  while (depth > 0) {
    open.lastIndex = i; close.lastIndex = i;
    const o = open.exec(s), c = close.exec(s);
    if (!c) throw new Error('unclosed ' + tag);
    if (o && o.index < c.index) { depth++; i = o.index + 1; } else { depth--; i = c.index + c[0].length; if (!depth) return [c.index, i]; }
  }
}

function render(tpl, scope) {
  let outS = '';
  let i = 0;
  const re = /<(sc-for|sc-if)\b([^>]*)>/g;
  let m;
  while ((m = re.exec(tpl))) {
    outS += tpl.slice(i, m.index);
    const [cStart, cEnd] = findClose(tpl, m[1], m.index + m[0].length);
    const inner = tpl.slice(m.index + m[0].length, cStart);
    if (m[1] === 'sc-for') {
      const list = lookup(/list="\{\{(.*?)\}\}"/.exec(m[2])[1], scope) || [];
      const as = /as="(\w+)"/.exec(m[2])[1];
      for (const item of list) outS += render(inner, { ...scope, [as]: item });
    } else {
      const v = lookup(/value="\{\{(.*?)\}\}"/.exec(m[2])[1], scope);
      if (v) outS += render(inner, scope);
    }
    i = cEnd; re.lastIndex = cEnd;
  }
  outS += tpl.slice(i);
  return outS.replace(/\{\{(.*?)\}\}/g, (_, e) => { const v = lookup(e, scope); return typeof v === 'function' ? '' : esc(v ?? ''); });
}

for (const [file, target] of Object.entries(pages)) {
  const s = fs.readFileSync(path.join(src, file), 'utf8');
  const title = /<title>(.*?)<\/title>/.exec(s)[1];
  const style = /<helmet>\s*<style>([\s\S]*?)<\/style>\s*<\/helmet>/.exec(s)[1];
  let body = /<\/helmet>([\s\S]*?)<\/x-dc>/.exec(s)[1];
  const code = /data-dc-script[^>]*>([\s\S]*?)<\/script>/.exec(s)[1];
  const Component = new Function('DCLogic', code + '\nreturn Component;')(DCLogic);
  const vals = new Component().renderVals();

  body = body
    .replace('class="{{themeClass}}"', 'id="root" class="{{themeClass}}"')
    .replace(/onClick="\{\{setDay\}\}"/, 'data-mode="day"')
    .replace(/onClick="\{\{setNight\}\}"/, 'data-mode="night"')
    .replace(/onSubmit="\{\{submit\}\}"/, 'id="interest-form"')
    .replace(/<sc-if value="\{\{sent\}\}"[^>]*>([\s\S]*?)<\/sc-if>/, (_, inner) => inner.replace('<p role="status"', '<p id="sent" role="status" hidden'));
  body = render(body, vals);
  for (const [b, p] of Object.entries(blobs)) body = body.split(b).join(p);
  for (const [f, t] of Object.entries(pages)) body = body.split(`href="${f}"`).join(`href="${t}"`);

  const script = `<script>
(function(){
  var root=document.getElementById('root');
  function set(night){
    root.className=night?'theme-night':'theme-day';
    document.querySelectorAll('[data-mode]').forEach(function(b){
      var on=(b.getAttribute('data-mode')==='night')===night;
      b.classList.toggle('on',on); b.setAttribute('aria-pressed',on?'true':'false');
    });
    try{localStorage.setItem('canopus-mode',night?'night':'day');}catch(e){}
  }
  document.querySelectorAll('[data-mode]').forEach(function(b){
    b.addEventListener('click',function(){set(b.getAttribute('data-mode')==='night');});
  });
  var saved=null; try{saved=localStorage.getItem('canopus-mode');}catch(e){}
  if(saved==='night') set(true);
  var f=document.getElementById('interest-form');
  if(f) f.addEventListener('submit',function(e){e.preventDefault();document.getElementById('sent').hidden=false;});
})();
</script>`;
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>${title}</title>
<style>${style}</style>
</head>
<body>${body}${script}
</body>
</html>
`;
  fs.writeFileSync(path.join(out, target), html);
  console.log('wrote', target, html.length);
}
