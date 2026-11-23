/*
 * Star Tracker · design "Blue Hour" (from Benro-Polaris-Controller, D12): display mode and the scene behind every screen.
 *
 * Day / Night / Red. Night (the default) is dark; Red (D7's night mode: red only, dim) keeps the night layout and
 * multiplies everything, live view and pictures included, by dim red, so it does not spoil dark-adapted eyes.
 * Loaded in <head> before anything is drawn, so a dark screen never flashes white. The choice is remembered, and on
 * Android passed to the shell so the status bar follows. `?theme=day|night|red` in the address overrides it (screenshots).
 */
(function () {
  var KEY = 'startracker-theme', MODES = ['day', 'night', 'red'];
  var root = document.documentElement;

  function read() {
    var q = /[?&]theme=(day|night|red)/.exec(location.search);
    if (q) return q[1];
    try { var t = localStorage.getItem(KEY); if (MODES.indexOf(t) >= 0) return t; } catch (e) { /* storage blocked */ }
    return 'night';
  }

  var style = document.createElement('style');
  style.textContent =
    '#theme-red{position:fixed;inset:0;z-index:2147483647;pointer-events:none;background:#b80000;mix-blend-mode:multiply;display:none}' +
    'html[data-theme=red] #theme-red{display:block}html[data-theme=red]{background:#000}';
  document.head.appendChild(style);

  var listeners = [];
  function apply(t) {
    root.setAttribute('data-theme', t);
    try { localStorage.setItem(KEY, t); } catch (e) { /* */ }
    try { if (window.StNative && StNative.setTheme) StNative.setTheme(t); } catch (e) { /* */ }
    var set = document.querySelectorAll('.mode button');
    for (var i = 0; i < set.length; i++) set[i].setAttribute('aria-pressed', String(set[i].value === t));
    listeners.forEach(function (f) { f(t); });
  }
  apply(read());

  // Mountains at dusk; stars and the Milky Way show at night only.
  function scene() {
    var seed = 11, stars = '';
    function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    for (var i = 0; i < 260; i++) {
      var s = rnd();
      stars += '<circle cx="' + (rnd() * 1600).toFixed(0) + '" cy="' + (rnd() * 560).toFixed(0) + '" r="' +
        (s > 0.985 ? 1.8 : s > 0.93 ? 1.2 : 0.7) + '" opacity="' + (0.35 + rnd() * 0.65).toFixed(2) + '"/>';
    }
    return '<svg class="scene" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs>' +
      '<linearGradient id="st-sky" x1="0" y1="0" x2="0" y2="1"><stop class="s1" offset="0"/><stop class="s2" offset=".45"/><stop class="s3" offset=".7"/></linearGradient>' +
      '<radialGradient id="st-glow" cx=".62" cy=".66" r=".55"><stop class="glow" offset="0" stop-opacity=".55"/><stop class="glow" offset="1" stop-opacity="0"/></radialGradient>' +
      '<filter id="st-b30" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="30"/></filter>' +
      '<linearGradient id="st-wf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>' +
      '<rect width="1600" height="1000" fill="url(#st-sky)"/><rect width="1600" height="1000" fill="url(#st-glow)"/>' +
      '<g class="mw" filter="url(#st-b30)" fill="#d9d2ff"><ellipse cx="1050" cy="330" rx="640" ry="70" transform="rotate(-32 1050 330)" opacity=".55"/>' +
      '<ellipse cx="1120" cy="300" rx="300" ry="46" transform="rotate(-32 1120 300)" fill="#fff1e0" opacity=".6"/></g>' +
      '<g class="stars" fill="#fff">' + stars + '</g>' +
      '<path class="m1" d="M0 640 L120 590 L230 615 L360 520 L470 575 L560 545 L700 470 L820 545 L930 510 L1060 560 L1180 480 L1300 545 L1420 505 L1520 545 L1600 525 L1600 1000 L0 1000Z"/>' +
      '<path class="m2" d="M0 700 L140 650 L260 680 L380 610 L520 670 L640 630 L780 690 L900 640 L1040 690 L1160 625 L1300 680 L1440 640 L1600 690 L1600 1000 L0 1000Z"/>' +
      '<path class="m3" d="M0 760 L180 720 L320 748 L460 705 L620 750 L780 725 L940 760 L1100 718 L1260 752 L1420 722 L1600 755 L1600 1000 L0 1000Z"/>' +
      '<rect class="water" y="800" width="1600" height="200"/><rect y="800" width="1600" height="200" fill="url(#st-wf)"/>' +
      '<g class="fg"><path d="M0 805 L0 770 L20 760 L40 700 L52 745 L66 690 L80 748 L96 712 L108 760 L130 735 L150 790 L170 760 L190 805Z"/>' +
      '<path d="M1380 805 L1400 760 L1412 715 L1424 760 L1440 700 L1456 752 L1470 680 L1486 750 L1502 718 L1516 765 L1534 735 L1552 772 L1572 745 L1600 770 L1600 805Z"/>' +
      '<path d="M0 800 L1600 800 L1600 812 L0 812Z"/></g></svg>';
  }

  function frame() {
    var veil = document.createElement('div');
    veil.id = 'theme-red';
    document.body.appendChild(veil);
    document.body.insertAdjacentHTML('afterbegin', scene());
    apply(read());
  }
  if (document.body) frame(); else document.addEventListener('DOMContentLoaded', frame);

  window.StTheme = { get: read, set: apply, onChange: function (f) { listeners.push(f); } };
})();
