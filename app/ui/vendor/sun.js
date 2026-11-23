/*
 * Sun position and the day's sun events for a place, using the NOAA
 * solar equations (good to about 0.01° and a minute). Events are found by
 * scanning the day: sunrise/sunset at -0.833° (refraction and the Sun's
 * radius), golden hour below 6°, blue hour between -4° and -6°.
 */
(function (root) {
  var RAD = Math.PI / 180;

  function position(date, lat, lon) {
    var jd = date.getTime() / 86400000 + 2440587.5;
    var t = (jd - 2451545) / 36525;
    var L0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360;
    var M = 357.52911 + t * (35999.05029 - 0.0001537 * t);
    var e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
    var C = Math.sin(M * RAD) * (1.914602 - t * (0.004817 + 0.000014 * t)) +
      Math.sin(2 * M * RAD) * (0.019993 - 0.000101 * t) + Math.sin(3 * M * RAD) * 0.000289;
    var trueLong = L0 + C;
    var omega = 125.04 - 1934.136 * t;
    var lambda = trueLong - 0.00569 - 0.00478 * Math.sin(omega * RAD);
    var eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
    var eps = eps0 + 0.00256 * Math.cos(omega * RAD);
    var decl = Math.asin(Math.sin(eps * RAD) * Math.sin(lambda * RAD));
    var y = Math.pow(Math.tan(eps * RAD / 2), 2);
    var eqTime = 4 / RAD * (y * Math.sin(2 * L0 * RAD) - 2 * e * Math.sin(M * RAD) +
      4 * e * y * Math.sin(M * RAD) * Math.cos(2 * L0 * RAD) -
      0.5 * y * y * Math.sin(4 * L0 * RAD) - 1.25 * e * e * Math.sin(2 * M * RAD));
    var minutes = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
    var trueSolar = (minutes + eqTime + 4 * lon) % 1440;
    var ha = trueSolar / 4 < 0 ? trueSolar / 4 + 180 : trueSolar / 4 - 180;
    var phi = lat * RAD, h = ha * RAD;
    var cosZ = Math.sin(phi) * Math.sin(decl) + Math.cos(phi) * Math.cos(decl) * Math.cos(h);
    var zen = Math.acos(Math.max(-1, Math.min(1, cosZ)));
    var az = Math.atan2(Math.sin(h), Math.cos(h) * Math.sin(phi) - Math.tan(decl) * Math.cos(phi)) / RAD + 180;
    return { az: (az + 360) % 360, alt: 90 - zen / RAD };
  }

  /** Times (Date) when the Sun's altitude crosses level on day, rising and setting. */
  function crossings(day, lat, lon, level) {
    var start = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
    var step = 120000, out = { rise: null, set: null };
    var prev = position(new Date(start), lat, lon).alt - level;
    for (var t = start + step; t <= start + 86400000; t += step) {
      var cur = position(new Date(t), lat, lon).alt - level;
      if ((prev < 0) !== (cur < 0)) {
        var lo = t - step, hi = t;
        for (var k = 0; k < 20; k++) {
          var mid = (lo + hi) / 2, m = position(new Date(mid), lat, lon).alt - level;
          if ((m < 0) === (prev < 0)) lo = mid; else hi = mid;
        }
        var when = new Date(Math.round((lo + hi) / 2));
        if (prev < 0 && !out.rise) out.rise = when;
        if (prev >= 0 && !out.set) out.set = when;
      }
      prev = cur;
    }
    return out;
  }

  function day(dayDate, lat, lon) {
    var sun = crossings(dayDate, lat, lon, -0.833);
    var golden = crossings(dayDate, lat, lon, 6);
    var blue = crossings(dayDate, lat, lon, -4);
    var dark = crossings(dayDate, lat, lon, -6);
    function at(d) { return d ? { time: d, az: position(d, lat, lon).az } : null; }
    return {
      sunrise: at(sun.rise), sunset: at(sun.set),
      goldenMorningEnd: golden.rise, goldenEveningStart: golden.set,
      blueMorning: [dark.rise, blue.rise], blueEvening: [blue.set, dark.set]
    };
  }

  root.Sun = { position: position, day: day, crossings: crossings };
})(typeof window !== 'undefined' ? window : globalThis);
