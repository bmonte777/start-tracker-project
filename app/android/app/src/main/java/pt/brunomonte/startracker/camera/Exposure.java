package pt.brunomonte.startracker.camera;

import java.util.ArrayList;
import java.util.List;

/**
 * Shutter-speed arithmetic for brackets. Sony shutter values are
 * numerator << 16 | denominator (0x0001_00FA = 1/250 s, 0x001E_0001 = 30"),
 * and 0 is BULB. Plain Java, so it can be tested off-device.
 */
final class Exposure {

    /** Longest timed shutter speed; anything longer is shot in BULB. */
    static final double LONGEST_TIMED = 30.0;

    private Exposure() {
    }

    /** Seconds for a shutter value; NaN for BULB or an unknown value. */
    static double seconds(long v) {
        long num = (v >> 16) & 0xFFFF, den = v & 0xFFFF;
        if (v == 0 || den == 0) return Double.NaN;
        return (double) num / den;
    }

    /**
     * Bracket order: the metered exposure first, then alternately darker
     * and brighter: 0, -ev, +ev, -2ev, +2ev…
     */
    static List<Double> offsets(int shots, double ev) {
        List<Double> out = new ArrayList<>();
        out.add(0.0);
        for (int k = 1; out.size() < shots; k++) {
            out.add(-k * ev);
            if (out.size() < shots) out.add(k * ev);
        }
        return out;
    }

    /** The listed shutter value closest to target seconds (in stops), ignoring BULB; -1 if none. */
    static long nearest(List<Long> choices, double target) {
        long best = -1;
        double bestDist = Double.MAX_VALUE;
        for (long c : choices) {
            double s = seconds(c);
            if (Double.isNaN(s)) continue;
            double d = Math.abs(Math.log(s / target) / Math.log(2));
            if (d < bestDist) {
                bestDist = d;
                best = c;
            }
        }
        return best;
    }

    /** Stops from a to b (positive when b is longer). */
    static double stops(double a, double b) {
        return Math.log(b / a) / Math.log(2);
    }
}
