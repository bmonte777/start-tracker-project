/*
 * Moon position and phase (Paul Schlyter's method with the main lunar
 * perturbations: about 2' in position), topocentric altitude (parallax
 * included, which moves the Moon by up to 1°), plus a helper for fixed
 * stars and the galactic centre. Used by the Night planner.
 */
(function (root) {
  var RAD = Math.PI / 180;
  function rev(x) { return x - Math.floor(x / 360) * 360; }
  function sind(x) { return Math.sin(x * RAD); }
  function cosd(x) { return Math.cos(x * RAD); }

  /** Days since 2000 Jan 0.0 UT (Schlyter's epoch). */
  function dayNumber(date) { return date.getTime() / 86400000 + 2440587.5 - 2451543.5; }

  function sunEcliptic(d) {
    var w = 282.9404 + 4.70935e-5 * d, e = 0.016709 - 1.151e-9 * d, M = rev(356.0470 + 0.9856002585 * d);
    var E = M + e / RAD * sind(M) * (1 + e * cosd(M));
    var xv = cosd(E) - e, yv = Math.sqrt(1 - e * e) * sind(E);
    return { lon: rev(Math.atan2(yv, xv) / RAD + w), M: M, L: rev(M + w) };
  }

  function moonEcliptic(d) {
    var N = rev(125.1228 - 0.0529538083 * d), i = 5.1454, w = rev(318.0634 + 0.1643573223 * d);
    var a = 60.2666, e = 0.054900, M = rev(115.3654 + 13.0649929509 * d);
    var E = M + e / RAD * sind(M) * (1 + e * cosd(M));
    for (var k = 0; k < 5; k++) E = E - (E - e / RAD * sind(E) - M) / (1 - e * cosd(E));
    var xv = a * (cosd(E) - e), yv = a * Math.sqrt(1 - e * e) * sind(E);
    var v = Math.atan2(yv, xv) / RAD, r = Math.sqrt(xv * xv + yv * yv);
    var xh = r * (cosd(N) * cosd(v + w) - sind(N) * sind(v + w) * cosd(i));
    var yh = r * (sind(N) * cosd(v + w) + cosd(N) * sind(v + w) * cosd(i));
    var zh = r * (sind(v + w) * sind(i));
    var lon = Math.atan2(yh, xh) / RAD, lat = Math.atan2(zh, Math.sqrt(xh * xh + yh * yh)) / RAD;
    // Main perturbations
    var sun = sunEcliptic(d), Ls = sun.L, Ms = sun.M, Lm = rev(N + w + M), Mm = M;
    var D = rev(Lm - Ls), F = rev(Lm - N);
    lon += -1.274 * sind(Mm - 2 * D) + 0.658 * sind(2 * D) - 0.186 * sind(Ms) - 0.059 * sind(2 * Mm - 2 * D)
      - 0.057 * sind(Mm - 2 * D + Ms) + 0.053 * sind(Mm + 2 * D) + 0.046 * sind(2 * D - Ms)
      + 0.041 * sind(Mm - Ms) - 0.035 * sind(D) - 0.031 * sind(Mm + Ms) - 0.015 * sind(2 * F - 2 * D)
      + 0.011 * sind(Mm - 4 * D);
    lat += -0.173 * sind(F - 2 * D) - 0.055 * sind(Mm - F - 2 * D) - 0.046 * sind(Mm + F - 2 * D)
      + 0.033 * sind(F + 2 * D) + 0.017 * sind(2 * Mm + F);
    r += -0.58 * cosd(Mm - 2 * D) - 0.46 * cosd(2 * D);
    return { lon: rev(lon), lat: lat, r: r, sunLon: sun.lon, sunL: Ls };
  }

  function eclToEq(lon, lat, d) {
    var ecl = 23.4393 - 3.563e-7 * d;
    var x = cosd(lon) * cosd(lat), y = sind(lon) * cosd(lat), z = sind(lat);
    var ye = y * cosd(ecl) - z * sind(ecl), ze = y * sind(ecl) + z * cosd(ecl);
    return { ra: rev(Math.atan2(ye, x) / RAD), dec: Math.atan2(ze, Math.sqrt(x * x + ye * ye)) / RAD };
  }

  /** Local sidereal time in degrees. */
  function lst(date, lon) {
    var jd = date.getTime() / 86400000 + 2440587.5, t = (jd - 2451545) / 36525;
    return rev(280.46061837 + 360.98564736629 * (jd - 2451545) + t * t * (0.000387933 - t / 38710000) + lon);
  }

  /** Altitude and azimuth (degrees, azimuth from north through east) of RA/Dec of date. */
  function altaz(raDeg, decDeg, date, lat, lon) {
    var ha = rev(lst(date, lon) - raDeg);
    var alt = Math.asin(sind(lat) * sind(decDeg) + cosd(lat) * cosd(decDeg) * cosd(ha)) / RAD;
    var az = Math.atan2(-sind(ha) * cosd(decDeg), cosd(lat) * sind(decDeg) - sind(lat) * cosd(decDeg) * cosd(ha)) / RAD;
    return { alt: alt, az: rev(az) };
  }

  /** J2000 RA/Dec moved to the date (precession only, enough for planning). */
  function precess(raDeg, decDeg, date) {
    var years = (date.getTime() - Date.UTC(2000, 0, 1, 12)) / 31557600000;
    var m = 3.07496 + 0.00186 * years / 100, n = 1.33621 - 0.00057 * years / 100;   // s/yr, "/yr
    var dra = (m + n * sind(raDeg) * Math.tan(decDeg * RAD)) * years * 15 / 3600;
    var ddec = n * 15 * cosd(raDeg) * years / 3600;
    return { ra: rev(raDeg + dra), dec: decDeg + ddec };
  }

  function position(date, lat, lon) {
    var d = dayNumber(date), m = moonEcliptic(d), eq = eclToEq(m.lon, m.lat, d);
    var h = altaz(eq.ra, eq.dec, date, lat, lon);
    var hp = Math.asin(1 / m.r) / RAD;                     // horizontal parallax
    var alt = h.alt - hp * cosd(h.alt);                     // seen from the ground
    var elong = Math.acos(cosd(m.lon - m.sunLon) * cosd(m.lat)) / RAD;
    var illum = (1 - cosd(elong)) / 2;                      // phase angle ≈ 180° - elongation
    var waxing = rev(m.lon - m.sunLon) < 180;
    return { alt: alt, az: h.az, ra: eq.ra, dec: eq.dec, illum: illum, waxing: waxing,
      phase: phaseName(illum, waxing), km: m.r * 6378.14 };
  }

  function phaseName(k, waxing) {
    if (k < 0.03) return 'New Moon';
    if (k > 0.97) return 'Full Moon';
    if (Math.abs(k - 0.5) < 0.06) return waxing ? 'First quarter' : 'Last quarter';
    return (waxing ? 'Waxing ' : 'Waning ') + (k < 0.5 ? 'crescent' : 'gibbous');
  }

  /** Times the Moon rises and sets between from and to (5-minute scan, refined to ~1 min). */
  function events(from, to, lat, lon) {
    var out = [], level = -0.583 - 0.25;  // refraction + semi-diameter
    var step = 5 * 60000, prev = position(from, lat, lon).alt - level;
    for (var t = from.getTime() + step; t <= to.getTime(); t += step) {
      var cur = position(new Date(t), lat, lon).alt - level;
      if ((prev < 0) !== (cur < 0)) {
        var lo = t - step, hi = t;
        for (var k = 0; k < 6; k++) {
          var mid = (lo + hi) / 2, v = position(new Date(mid), lat, lon).alt - level;
          if ((v < 0) === (prev < 0)) lo = mid; else hi = mid;
        }
        var when = new Date((lo + hi) / 2);
        out.push({ type: cur > 0 ? 'rise' : 'set', time: when, az: position(when, lat, lon).az });
      }
      prev = cur;
    }
    return out;
  }

  // Galactic centre (Sgr A*), J2000
  var CORE = { ra: 266.4168, dec: -29.0078 };

  root.Moon = { position: position, events: events };
  root.Sky = { altaz: altaz, lst: lst, precess: precess, CORE: CORE };
})(typeof window !== 'undefined' ? window : globalThis);
