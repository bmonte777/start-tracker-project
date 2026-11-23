/*
 * Windows only: the Star Tracker backend (app/windows/backend) serves these pages at http://127.0.0.1:5570 and answers
 * window.CameraNative calls synchronously at POST /bridge/camera/<method> (the same methods as CameraBridge.java on
 * Android, reused from Benro-Polaris-Controller). window.StNative calls go through app/shared/native.js. Elsewhere
 * (Android, a plain browser) this file does nothing.
 */
(function () {
  if (window.StNative || location.hostname !== '127.0.0.1' || location.port !== '5570') return;
  window.ST_PLATFORM = 'windows';
  function call(method, args) {
    var x = new XMLHttpRequest();
    x.open('POST', '/bridge/camera/' + method, false);
    x.setRequestHeader('Content-Type', 'application/json');
    x.setRequestHeader('X-StarTracker', '1');
    x.send(JSON.stringify(args));
    var r = JSON.parse(x.responseText || '{}');
    if (x.status !== 200) throw new Error(r.error || ('HTTP ' + x.status));
    return r.result === null || r.result === undefined ? undefined : r.result;
  }
  var methods = ['connect', 'disconnect', 'status', 'refresh', 'step', 'set', 'shoot', 'startInterval', 'startPanorama', 'startHdr',
    'startFocusStack', 'startPathLapse', 'startScheduled', 'startPeopleRemover', 'liveStart', 'liveStop', 'liveFrame', 'focus', 'autofocus',
    'stopJob', 'diagnostics', 'gallery', 'galleryThumb', 'galleryOpen', 'startSolve', 'lastSolve', 'startTrails', 'trailsFrame', 'startAstro',
    'startDarks', 'startVideo', 'startHolyGrail', 'startSphere', 'startMixedPanorama', 'startHeadJob'];
  var o = {};
  methods.forEach(function (m) { o[m] = function () { return call(m, Array.prototype.slice.call(arguments)); }; });
  window.CameraNative = o;
})();
