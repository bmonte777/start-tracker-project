package pt.brunomonte.startracker.camera;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Plate solving with a hint: finds exactly where a photo of the night sky
 * points. Unlike a blind solver it is told roughly where to look (the
 * Polaris pointing) and roughly how wide the frame is (the lens), so it
 * only matches against the catalogue stars near the hint. Free of Android
 * so it can be tested on synthetic star fields.
 *
 * Steps: detect stars (local maxima over a background, centroided);
 * project the catalogue around the hint onto a tangent plane; match
 * triangles of bright stars, which keep their shape under rotation and
 * scale; check each candidate transform by counting how many detected
 * stars land on catalogue stars; refine the best one with all its matches,
 * twice (the second time projected around the solved centre).
 *
 * Coordinates: RA/Dec J2000 in degrees. Image x to the right, y down.
 */
final class PlateSolver {

    // Pattern settings: triangle sides up to PAT_SIDE x frame width, each
    // catalogue star with its PAT_K brightest neighbours, the PAT_N brightest
    // detected stars.
    static double PAT_SIDE = Double.parseDouble(System.getProperty("ps.side", "0.4"));
    static int PAT_K = Integer.getInteger("ps.k", 14);
    static int PAT_N = Integer.getInteger("ps.n", 25);
    /** Largest fit residual (pixels rms) accepted as a solve. */
    static double MAX_RMS_PX = 3.0;

    // ------------------------------------------------------------------
    // Catalogue
    // ------------------------------------------------------------------

    /** Stars sorted by magnitude (brightest first): ra, dec in degrees; mag. */
    static final class Catalog {
        final float[] ra, dec, mag;
        final double[] x, y, z;           // unit vectors, for fast cone searches

        Catalog(float[] ra, float[] dec, float[] mag) {
            this.ra = ra;
            this.dec = dec;
            this.mag = mag;
            int n = ra.length;
            x = new double[n];
            y = new double[n];
            z = new double[n];
            for (int i = 0; i < n; i++) {
                double a = Math.toRadians(ra[i]), d = Math.toRadians(dec[i]);
                x[i] = Math.cos(d) * Math.cos(a);
                y[i] = Math.cos(d) * Math.sin(a);
                z[i] = Math.sin(d);
            }
        }

        /** Reads stars8.bin or stars11.bin (D74): "STR1", count, then (float ra, float dec, short mag*100) little-endian. */
        static Catalog read(InputStream in) throws IOException {
            byte[] all;
            try (DataInputStream d = new DataInputStream(in)) {
                java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
                byte[] b = new byte[65536];
                int k;
                while ((k = d.read(b)) > 0) bos.write(b, 0, k);
                all = bos.toByteArray();
            }
            ByteBuffer bb = ByteBuffer.wrap(all).order(ByteOrder.LITTLE_ENDIAN);
            if (bb.getInt() != 0x31525453) throw new IOException("Not a star catalogue");   // "STR1"
            int n = bb.getInt();
            float[] ra = new float[n], dec = new float[n], mag = new float[n];
            for (int i = 0; i < n; i++) {
                ra[i] = bb.getFloat();
                dec[i] = bb.getFloat();
                mag[i] = bb.getShort() / 100f;
            }
            return new Catalog(ra, dec, mag);
        }

        /** Faintest magnitude in the catalogue: 8 for stars8.bin, 10.5 for stars11.bin. */
        float magMax() { return mag.length > 0 ? mag[mag.length - 1] : 8f; }

        /** Indices of stars within radius (degrees) of ra0/dec0, brightest first. */
        int[] cone(double ra0, double dec0, double radiusDeg, float magLimit) {
            double a = Math.toRadians(ra0), d = Math.toRadians(dec0);
            double cx = Math.cos(d) * Math.cos(a), cy = Math.cos(d) * Math.sin(a), cz = Math.sin(d);
            double minDot = Math.cos(Math.toRadians(radiusDeg));
            int[] tmp = new int[ra.length];
            int n = 0;
            for (int i = 0; i < ra.length; i++) {
                if (mag[i] > magLimit) break;                 // sorted by magnitude
                if (x[i] * cx + y[i] * cy + z[i] * cz >= minDot) tmp[n++] = i;
            }
            return Arrays.copyOf(tmp, n);
        }
    }

    // ------------------------------------------------------------------
    // Star detection
    // ------------------------------------------------------------------

    /** A detected star: centroid in image pixels and its summed brightness above the background. */
    static final class Star {
        final double x, y, flux;

        Star(double x, double y, double flux) {
            this.x = x;
            this.y = y;
            this.flux = flux;
        }
    }

    /**
     * Finds stars in a luminance image (0..255 per pixel, row-major).
     * The background is estimated per 32x32 block (median), the noise from
     * the spread of the block medians and pixels; a star is a local maximum
     * well above it. Returns at most maxStars, brightest first.
     */
    static List<Star> detect(float[] lum, int w, int h, int maxStars) {
        int bs = 32, bw = (w + bs - 1) / bs, bh = (h + bs - 1) / bs;
        float[] bg = new float[bw * bh], noise = new float[bw * bh];
        float[] block = new float[bs * bs];
        for (int by = 0; by < bh; by++) for (int bx = 0; bx < bw; bx++) {
            int n = 0;
            for (int y = by * bs; y < Math.min(h, by * bs + bs); y++)
                for (int x = bx * bs; x < Math.min(w, bx * bs + bs); x++) block[n++] = lum[y * w + x];
            Arrays.sort(block, 0, n);
            float med = block[n / 2];
            // Noise from the lower half (stars only brighten): median-to-16th-percentile ≈ 1 sigma
            float sig = Math.max(0.8f, med - block[Math.max(0, (int) (n * 0.16))]);
            bg[by * bw + bx] = med;
            noise[by * bw + bx] = sig;
        }
        List<Star> found = new ArrayList<>();
        int r = 3;
        for (int y = r; y < h - r; y++) {
            for (int x = r; x < w - r; x++) {
                int bi = Math.min(bh - 1, y / bs) * bw + Math.min(bw - 1, x / bs);
                float v = lum[y * w + x], b = bg[bi], t = b + Math.max(6 * noise[bi], 12);
                if (v < t) continue;
                // local maximum in a 5x5 window (ties: first wins)
                boolean max = true;
                for (int dy = -2; dy <= 2 && max; dy++) for (int dx = -2; dx <= 2; dx++) {
                    if (dx == 0 && dy == 0) continue;
                    float u = lum[(y + dy) * w + x + dx];
                    if (u > v || (u == v && (dy < 0 || (dy == 0 && dx < 0)))) { max = false; break; }
                }
                if (!max) continue;
                // centroid over a 7x7 window, background removed
                double sx = 0, sy = 0, sf = 0;
                int bright = 0;
                for (int dy = -r; dy <= r; dy++) for (int dx = -r; dx <= r; dx++) {
                    double f = lum[(y + dy) * w + x + dx] - b;
                    if (f <= 0) continue;
                    if (f > 2 * noise[bi]) bright++;
                    sx += f * (x + dx);
                    sy += f * (y + dy);
                    sf += f;
                }
                if (sf <= 0 || bright < 2) continue;                 // a single hot pixel
                found.add(new Star(sx / sf, sy / sf, sf));
            }
        }
        found.sort((a, c) -> Double.compare(c.flux, a.flux));
        // A saturated star has a flat top and can give several maxima: keep the brightest of
        // any detections closer than 8 px. Big bright areas (Moon, lights) give many: drop them.
        List<Star> kept = new ArrayList<>();
        for (Star st : found) {
            int close = 0;
            for (Star k : kept) if (Math.abs(k.x - st.x) < 8 && Math.abs(k.y - st.y) < 8) close++;
            if (close == 0) kept.add(st);
            if (kept.size() >= maxStars * 3) break;
        }
        return kept.size() > maxStars ? new ArrayList<>(kept.subList(0, maxStars)) : kept;
    }

    // ------------------------------------------------------------------
    // Projection
    // ------------------------------------------------------------------

    /** Gnomonic projection around ra0/dec0: returns {xi, eta} in degrees (xi east, eta north), or null behind. */
    static double[] project(double ra, double dec, double ra0, double dec0) {
        double a = Math.toRadians(ra - ra0), d = Math.toRadians(dec), d0 = Math.toRadians(dec0);
        double cosc = Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a);
        if (cosc <= 0.1) return null;
        double xi = Math.cos(d) * Math.sin(a) / cosc;
        double eta = (Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a)) / cosc;
        return new double[]{Math.toDegrees(xi), Math.toDegrees(eta)};
    }

    /** Inverse gnomonic: tangent-plane degrees back to RA/Dec. */
    static double[] unproject(double xiDeg, double etaDeg, double ra0, double dec0) {
        double xi = Math.toRadians(xiDeg), eta = Math.toRadians(etaDeg), d0 = Math.toRadians(dec0);
        double rho = Math.hypot(xi, eta);
        if (rho == 0) return new double[]{ra0, dec0};
        double c = Math.atan(rho);
        double dec = Math.asin(Math.cos(c) * Math.sin(d0) + eta * Math.sin(c) * Math.cos(d0) / rho);
        double ra = ra0 + Math.toDegrees(Math.atan2(xi * Math.sin(c), rho * Math.cos(d0) * Math.cos(c) - eta * Math.sin(d0) * Math.sin(c)));
        return new double[]{(ra % 360 + 360) % 360, Math.toDegrees(dec)};
    }

    // ------------------------------------------------------------------
    // Solving
    // ------------------------------------------------------------------

    /** The answer. */
    static final class Solution {
        double ra, dec;          // image centre, J2000 degrees
        double roll;             // degrees: angle of the image's up direction east of north
        double scale;            // degrees per pixel
        double fovW, fovH;       // degrees
        boolean mirrored;
        int matched, used;       // stars matched / detected stars used
        double rmsArcsec;
        long millis;

        @Override
        public String toString() {
            return String.format(java.util.Locale.ROOT, "RA %.4f° Dec %+.4f° roll %.1f° field %.2f°×%.2f° (%.2f\"/px) %d/%d stars, rms %.1f\"%s, %d ms",
                    ra, dec, roll, fovW, fovH, scale * 3600, matched, used, rmsArcsec, mirrored ? " mirrored" : "", millis);
        }
    }

    /** Similarity transform from image (x, -y) to tangent plane: xi = a*x - b*y' + c ; eta = b*x + a*y' + d (y' = -y or y). */
    private static final class Fit {
        double a, b, c, d;
        double k, norm2 = 1;     // radial distortion: points scaled by (1 + k r²/norm2) first
        boolean mirror;
        int matched;
        double rms;

        double[] apply(double x, double y) {
            double f = 1 + k * (x * x + y * y) / norm2;
            x *= f;
            y *= f;
            double yy = mirror ? y : -y;
            return new double[]{a * x - b * yy + c, b * x + a * yy + d};
        }

        double scale() {
            return Math.hypot(a, b);
        }
    }

    private static final class Tri {
        final int i, j, k;        // vertices ordered: i opposite the shortest side… (see build)
        final double r1, r2, longest;

        Tri(int i, int j, int k, double r1, double r2, double longest) {
            this.i = i;
            this.j = j;
            this.k = k;
            this.r1 = r1;
            this.r2 = r2;
            this.longest = longest;
        }
    }

    /**
     * Builds a triangle from three points with its vertices in a canonical
     * order: A is opposite the shortest side, B opposite the middle, C
     * opposite the longest; the ratios short/long and middle/long describe
     * its shape whatever the rotation, scale or mirroring.
     */
    private static Tri triangle(int p, int q, int s, double[] px, double[] py) {
        int[] v = {p, q, s};
        double[] side = new double[3];          // side[n] = length opposite v[n]
        for (int n = 0; n < 3; n++) {
            int u = v[(n + 1) % 3], w = v[(n + 2) % 3];
            side[n] = Math.hypot(px[u] - px[w], py[u] - py[w]);
        }
        Integer[] o = {0, 1, 2};
        Arrays.sort(o, Comparator.comparingDouble(n -> side[n]));
        double longest = side[o[2]];
        if (longest <= 0 || side[o[0]] < longest * 0.08) return null;     // degenerate / too flat
        return new Tri(v[o[0]], v[o[1]], v[o[2]], side[o[0]] / longest, side[o[1]] / longest, longest);
    }

    /**
     * Solves. stars: detected (brightest first). w,h: image size. hint: rough
     * centre (degrees, J2000), hintRadius: how far off it may be (degrees).
     * fovW: rough frame width (degrees), fovTolerance: e.g. 0.25 for ±25 %.
     * Returns null when no convincing match is found.
     */
    static Solution solve(Catalog cat, List<Star> stars, int w, int h,
                          double hintRa, double hintDec, double hintRadius, double fovW, double fovTolerance) {
        long t0 = System.currentTimeMillis();
        int nImg = Math.min(stars.size(), 40);
        if (nImg < 6) return null;
        double[] ix = new double[nImg], iy = new double[nImg];
        for (int i = 0; i < nImg; i++) {
            ix[i] = stars.get(i).x - w / 2.0;
            iy[i] = stars.get(i).y - h / 2.0;
        }
        double scale0 = fovW / w;                          // degrees per pixel
        double norm2 = (w * (double) w + h * (double) h) / 4;  // half-diagonal squared
        double fovDiag = Math.hypot(w, h) * scale0 * (1 + fovTolerance);

        // Catalogue around the hint. Magnitude limit: about 3x as many stars per frame area as detected.
        double radius = Math.min(85, hintRadius + fovDiag / 2);
        double frameArea = w * h * scale0 * scale0;
        double regionArea = Math.PI * radius * radius;
        int[] all = cat.cone(hintRa, hintDec, radius, cat.magMax());   // whole depth; 'want' keeps the density right
        int want = (int) Math.max(30, Math.min(all.length, 3.0 * nImg * regionArea / frameArea));
        int[] region = Arrays.copyOf(all, Math.min(all.length, want));
        // For verification a deeper list (some detected stars are fainter than the pattern set)
        int[] deep = Arrays.copyOf(all, Math.min(all.length, (int) (want * 2.5)));
        if (region.length < 6) return null;

        double[] cx = new double[deep.length], cy = new double[deep.length];
        int nOk = 0;
        int[] deepIdx = new int[deep.length];
        for (int n = 0; n < deep.length; n++) {
            double[] p = project(cat.ra[deep[n]], cat.dec[deep[n]], hintRa, hintDec);
            if (p == null) continue;
            cx[nOk] = p[0];
            cy[nOk] = p[1];
            deepIdx[nOk] = deep[n];
            nOk++;
        }
        int nRegion = 0;
        for (int n = 0; n < nOk; n++) if (cat.mag[deepIdx[n]] <= cat.mag[region[region.length - 1]]) nRegion++;
        if (nRegion < 6) return null;

        // Catalogue triangles: each region star with its brightest neighbours within
        // about half a frame width, so a triangle's stars are usually in the photo together.
        double maxSide = PAT_SIDE * w * scale0 * (1 + fovTolerance);
        Map<Long, List<Tri>> table = new HashMap<>();
        java.util.HashSet<Long> seen = new java.util.HashSet<>();
        int K = PAT_K;
        for (int p = 0; p < nRegion; p++) {
            int[] near = new int[K];
            int nn = 0;
            for (int q = 0; q < nRegion && nn < K; q++) {
                if (q == p) continue;
                if (Math.hypot(cx[p] - cx[q], cy[p] - cy[q]) <= maxSide) near[nn++] = q;
            }
            for (int u = 0; u < nn; u++) for (int v = u + 1; v < nn; v++) {
                int q = near[u], s = near[v];
                if (Math.hypot(cx[q] - cx[s], cy[q] - cy[s]) > maxSide) continue;
                int lo = Math.min(p, Math.min(q, s)), hi = Math.max(p, Math.max(q, s)), mid = p + q + s - lo - hi;
                if (!seen.add(((long) lo * 100000 + mid) * 100000 + hi)) continue;     // each triangle once
                Tri t = triangle(p, q, s, cx, cy);
                if (t == null) continue;
                table.computeIfAbsent(key(t.r1, t.r2), x -> new ArrayList<>()).add(t);
            }
        }

        // Image triangles from the brightest image stars, matched against the table.
        int nPat = Math.min(nImg, PAT_N);
        double maxSidePix = PAT_SIDE * w;
        Fit best = null;
        double tolPix = 2.5;
        int tried = 0;
        for (int p = 0; p < nPat; p++) for (int q = p + 1; q < nPat; q++) for (int s = q + 1; s < nPat; s++) {
            Tri ti = triangle(p, q, s, ix, iy);
            if (ti == null || ti.longest < 0.05 * w || ti.longest > maxSidePix) continue;
            double expected = ti.longest * scale0;
            for (int dr1 = -1; dr1 <= 1; dr1++) for (int dr2 = -1; dr2 <= 1; dr2++) {
                List<Tri> cands = table.get(key(ti.r1 + dr1 * 0.01, ti.r2 + dr2 * 0.01));
                if (cands == null) continue;
                for (Tri tc : cands) {
                    if (Math.abs(tc.r1 - ti.r1) > 0.008 || Math.abs(tc.r2 - ti.r2) > 0.008) continue;
                    double ratio = tc.longest / expected;
                    if (ratio < 1 - fovTolerance || ratio > 1 + fovTolerance) continue;
                    if (++tried > 400000) break;
                    for (int m = 0; m < 2; m++) {
                        boolean mirror = m == 1;
                        Fit f = fitPairs(new double[]{ix[ti.i], ix[ti.j], ix[ti.k]}, new double[]{iy[ti.i], iy[ti.j], iy[ti.k]},
                                new double[]{cx[tc.i], cx[tc.j], cx[tc.k]}, new double[]{cy[tc.i], cy[tc.j], cy[tc.k]}, mirror);
                        if (f == null) continue;
                        f.norm2 = norm2;
                        double tolDeg = tolPix * f.scale();
                        f.matched = countMatches(f, ix, iy, nImg, cx, cy, nOk, tolDeg, 5, null, null);
                        if (best == null || f.matched > best.matched) best = f;
                    }
                }
            }
            if (best != null && best.matched >= Math.max(10, nImg * 0.6)) break;   // clearly found
        }
        if (best == null) return null;
        int need = Math.max(6, (int) Math.ceil(nImg * 0.3));
        if (best.matched < need) return null;

        // Refine with all matches; then re-project the catalogue around the
        // solved centre and fit the same pairs again there (near the pole the
        // plane also turns when its centre moves), and repeat.
        double ra0 = hintRa, dec0 = hintDec;
        int[] slotCat = Arrays.copyOf(deepIdx, nOk);           // catalogue index of each projected slot
        Fit fit = best;
        for (int pass = 0; pass < 3; pass++) {
            int[] mi = new int[nImg], mc = new int[nImg];
            int nm = countMatches(fit, ix, iy, nImg, cx, cy, nOk, tolPix * fit.scale(), pass == 0 ? 5 : 2, mi, mc);
            if (nm < need) return null;
            double[] ax = new double[nm], ay = new double[nm], bx = new double[nm], by = new double[nm];
            int[] pairCat = new int[nm];
            for (int n = 0; n < nm; n++) {
                ax[n] = ix[mi[n]];
                ay[n] = iy[mi[n]];
                bx[n] = cx[mc[n]];
                by[n] = cy[mc[n]];
                pairCat[n] = slotCat[mc[n]];
            }
            Fit nf = fitDistorted(ax, ay, bx, by, fit.mirror, norm2);
            if (nf == null) return null;
            double[] centre = unproject(nf.c, nf.d, ra0, dec0);
            ra0 = centre[0];
            dec0 = centre[1];
            // The whole deep list around the new centre
            nOk = 0;
            slotCat = new int[deep.length];
            for (int n = 0; n < deep.length; n++) {
                double[] p = project(cat.ra[deep[n]], cat.dec[deep[n]], ra0, dec0);
                if (p == null) continue;
                cx[nOk] = p[0];
                cy[nOk] = p[1];
                slotCat[nOk] = deep[n];
                nOk++;
            }
            // The same pairs in the new plane
            for (int n = 0; n < nm; n++) {
                double[] p = project(cat.ra[pairCat[n]], cat.dec[pairCat[n]], ra0, dec0);
                bx[n] = p[0];
                by[n] = p[1];
            }
            nf = fitDistorted(ax, ay, bx, by, fit.mirror, norm2);
            if (nf == null) return null;
            double ss = 0;
            for (int n = 0; n < nm; n++) {
                double[] t = nf.apply(ax[n], ay[n]);
                ss += (t[0] - bx[n]) * (t[0] - bx[n]) + (t[1] - by[n]) * (t[1] - by[n]);
            }
            nf.rms = Math.sqrt(ss / nm);
            nf.matched = nm;
            // the fitted centre is now (almost exactly) the origin; take the tiny rest into the centre too
            double[] fine = unproject(nf.c, nf.d, ra0, dec0);
            ra0 = fine[0];
            dec0 = fine[1];
            fit = nf;
        }

        // A loose fit (over MAX_RMS_PX pixels rms) is not trusted: syncing on it
        // would move the alignment by a fraction of a degree at wide angles.
        if (fit.rms / fit.scale() > MAX_RMS_PX) return null;

        Solution s = new Solution();
        s.ra = ra0;
        s.dec = dec0;
        s.scale = fit.scale();
        s.fovW = w * s.scale;
        s.fovH = h * s.scale;
        s.mirrored = fit.mirror;
        // Image "up" is (0, -1) in pixels -> direction in the tangent plane
        double[] up = fit.apply(0, -100);
        s.roll = (Math.toDegrees(Math.atan2(up[0], up[1])) + 360) % 360;   // from north towards east
        s.matched = fit.matched;
        s.used = nImg;
        s.rmsArcsec = fit.rms * 3600;
        s.millis = System.currentTimeMillis() - t0;
        return s;
    }

    private static long key(double r1, double r2) {
        return Math.round(r1 * 100) * 1000 + Math.round(r2 * 100);
    }

    /**
     * Similarity fit plus one radial distortion coefficient (barrel or
     * pincushion of wide lenses), found by a golden-section search on the
     * residual. Needs enough pairs; with few it stays at 0.
     */
    private static Fit fitDistorted(double[] ax, double[] ay, double[] bx, double[] by, boolean mirror, double norm2) {
        int n = ax.length;
        if (n < 10) {
            Fit f = fitPairs(ax, ay, bx, by, mirror);
            if (f != null) f.norm2 = norm2;
            return f;
        }
        double lo = -0.12, hi = 0.12, g = (Math.sqrt(5) - 1) / 2;
        double k1 = hi - g * (hi - lo), k2 = lo + g * (hi - lo);
        double r1 = residual(ax, ay, bx, by, mirror, norm2, k1), r2 = residual(ax, ay, bx, by, mirror, norm2, k2);
        for (int it = 0; it < 30; it++) {
            if (r1 < r2) { hi = k2; k2 = k1; r2 = r1; k1 = hi - g * (hi - lo); r1 = residual(ax, ay, bx, by, mirror, norm2, k1); }
            else { lo = k1; k1 = k2; r1 = r2; k2 = lo + g * (hi - lo); r2 = residual(ax, ay, bx, by, mirror, norm2, k2); }
        }
        double k = (lo + hi) / 2;
        Fit f = fitWithK(ax, ay, bx, by, mirror, norm2, k);
        return f;
    }

    private static Fit fitWithK(double[] ax, double[] ay, double[] bx, double[] by, boolean mirror, double norm2, double k) {
        int n = ax.length;
        double[] dx = new double[n], dy = new double[n];
        for (int i = 0; i < n; i++) {
            double f = 1 + k * (ax[i] * ax[i] + ay[i] * ay[i]) / norm2;
            dx[i] = ax[i] * f;
            dy[i] = ay[i] * f;
        }
        Fit fit = fitPairs(dx, dy, bx, by, mirror);
        if (fit != null) {
            fit.k = k;
            fit.norm2 = norm2;
        }
        return fit;
    }

    private static double residual(double[] ax, double[] ay, double[] bx, double[] by, boolean mirror, double norm2, double k) {
        Fit f = fitWithK(ax, ay, bx, by, mirror, norm2, k);
        if (f == null) return Double.MAX_VALUE;
        double ss = 0;
        for (int i = 0; i < ax.length; i++) {
            double[] t = f.apply(ax[i], ay[i]);
            ss += (t[0] - bx[i]) * (t[0] - bx[i]) + (t[1] - by[i]) * (t[1] - by[i]);
        }
        return ss;
    }

    /** Least-squares similarity (optionally mirrored) mapping image points to tangent-plane points. */
    private static Fit fitPairs(double[] ax, double[] ay, double[] bx, double[] by, boolean mirror) {
        int n = ax.length;
        double mx = 0, my = 0, nx = 0, ny = 0;
        for (int i = 0; i < n; i++) {
            double yy = mirror ? ay[i] : -ay[i];
            mx += ax[i];
            my += yy;
            nx += bx[i];
            ny += by[i];
        }
        mx /= n; my /= n; nx /= n; ny /= n;
        double sxx = 0, sab = 0, sba = 0;
        for (int i = 0; i < n; i++) {
            double px = ax[i] - mx, py = (mirror ? ay[i] : -ay[i]) - my, qx = bx[i] - nx, qy = by[i] - ny;
            sxx += px * px + py * py;
            sab += px * qx + py * qy;
            sba += px * qy - py * qx;
        }
        if (sxx <= 0) return null;
        Fit f = new Fit();
        f.mirror = mirror;
        f.a = sab / sxx;
        f.b = sba / sxx;
        f.c = nx - (f.a * mx - f.b * my);
        f.d = ny - (f.b * mx + f.a * my);
        return f;
    }

    /** Counts image stars landing within tol of a catalogue star (one-to-one); fills the pairs if asked. */
    private static int countMatches(Fit f, double[] ix, double[] iy, int nImg, double[] cx, double[] cy, int nCat,
                                    double tol0, double widen, int[] outImg, int[] outCat) {
        int n = 0;
        boolean[] used = new boolean[nCat];
        for (int i = 0; i < nImg; i++) {
            double[] t = f.apply(ix[i], iy[i]);
            // more room towards the corners, where lens distortion moves stars most
            double tol = tol0 * (1 + widen * (ix[i] * ix[i] + iy[i] * iy[i]) / f.norm2);
            int bestJ = -1;
            double bestD = tol * tol;
            for (int j = 0; j < nCat; j++) {
                if (used[j]) continue;
                double dx = cx[j] - t[0];
                if (dx > tol || dx < -tol) continue;
                double dy = cy[j] - t[1];
                double d2 = dx * dx + dy * dy;
                if (d2 < bestD) { bestD = d2; bestJ = j; }
            }
            if (bestJ >= 0) {
                used[bestJ] = true;
                if (outImg != null) { outImg[n] = i; outCat[n] = bestJ; }
                n++;
            }
        }
        return n;
    }
}
