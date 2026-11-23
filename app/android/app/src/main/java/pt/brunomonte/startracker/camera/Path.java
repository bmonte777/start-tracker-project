package pt.brunomonte.startracker.camera;

import java.util.ArrayList;
import java.util.List;

/**
 * Positions for a path-lapse: shots spread evenly along a path through
 * keyframes {azimuth, altitude}, so the head moves at a steady speed.
 * Azimuth takes the short way round between two keyframes (add a middle
 * keyframe for turns over 180°). Plain Java, testable off-device.
 */
final class Path {

    private Path() {
    }

    /** Signed azimuth change from a to b, the short way (-180…180). */
    static double azDelta(double a, double b) {
        return ((b - a + 540) % 360 + 360) % 360 - 180;
    }

    static List<double[]> positions(List<double[]> keys, int shots) {
        List<double[]> out = new ArrayList<>();
        if (keys.isEmpty() || shots < 1) return out;
        if (keys.size() == 1 || shots == 1) {
            for (int i = 0; i < shots; i++) out.add(keys.get(0).clone());
            return out;
        }
        int n = keys.size() - 1;
        double[] len = new double[n];
        double total = 0;
        for (int i = 0; i < n; i++) {
            double dAz = azDelta(keys.get(i)[0], keys.get(i + 1)[0]);
            double dAlt = keys.get(i + 1)[1] - keys.get(i)[1];
            len[i] = Math.hypot(dAz, dAlt);
            total += len[i];
        }
        for (int s = 0; s < shots; s++) {
            double d = total * s / (shots - 1);
            int seg = 0;
            while (seg < n - 1 && d > len[seg]) {
                d -= len[seg];
                seg++;
            }
            double t = len[seg] == 0 ? 0 : Math.min(1, d / len[seg]);
            double[] a = keys.get(seg), b = keys.get(seg + 1);
            double az = a[0] + azDelta(a[0], b[0]) * t;
            out.add(new double[]{((az % 360) + 360) % 360, a[1] + (b[1] - a[1]) * t});
        }
        return out;
    }
}
