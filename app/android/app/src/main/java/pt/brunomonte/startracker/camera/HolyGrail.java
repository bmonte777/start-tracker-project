package pt.brunomonte.startracker.camera;

/**
 * The arithmetic of the Holy Grail (day-to-night) timelapse, kept free of
 * Android so it can be checked on its own.
 *
 * Each frame's brightness is measured from the picture itself and turned
 * into the brightness of the scene, independent of the camera settings:
 * scene = picture EV - log2(shutter x ISO / 100). The scene value is
 * smoothed so a passing car does not change the exposure. The wanted
 * picture brightness is the first frame's (the user sets a good exposure
 * before starting), made darker as the Sun goes down: nights should look
 * like nights. From those two the needed exposure follows; the camera is
 * moved in 1/3-stop notches, at most two per frame, and only when the
 * error is larger than the dead band, so it does not hunt.
 */
final class HolyGrail {

    /** Stops of error tolerated before the exposure is changed. */
    static final double DEAD_BAND = 0.4;
    /** Sun altitude (degrees) above which it counts as day, and below which as full night. */
    static final double DAY_ALT = 6, NIGHT_ALT = -12;

    private final double nightDarker;      // how many stops darker the night looks than the day
    private double sceneSmoothed = Double.NaN;
    private double pictureRef = Double.NaN;
    private double trendAtStart = Double.NaN;

    HolyGrail(double nightDarkerStops) {
        this.nightDarker = Math.max(0, Math.min(6, nightDarkerStops));
    }

    /** Exposure value of the camera settings: log2(seconds x ISO / 100). */
    static double exposureEv(double seconds, double iso) {
        return Math.log(seconds * iso / 100.0) / Math.log(2);
    }

    /** 0 by day, -nightDarker at full night, linear through twilight. */
    double trend(double sunAltitude) {
        if (Double.isNaN(sunAltitude)) return 0;
        if (sunAltitude >= DAY_ALT) return 0;
        if (sunAltitude <= NIGHT_ALT) return -nightDarker;
        return -nightDarker * (DAY_ALT - sunAltitude) / (DAY_ALT - NIGHT_ALT);
    }

    /** Result of one frame. */
    static final class Step {
        double scene;          // smoothed scene brightness
        double wanted;         // wanted picture brightness
        double error;          // stops: + means the next frame should be brighter
        int notches;           // 1/3-stop notches to move: + brighter, - darker
    }

    /**
     * Feeds one frame: its measured picture brightness (log2 of mean linear
     * luminance), the settings it was shot with and the Sun's altitude.
     */
    Step frame(double pictureEv, double seconds, double iso, double sunAltitude) {
        double settings = exposureEv(seconds, iso);
        double scene = pictureEv - settings;
        sceneSmoothed = Double.isNaN(sceneSmoothed) ? scene : 0.6 * sceneSmoothed + 0.4 * scene;
        double tr = trend(sunAltitude);
        if (Double.isNaN(pictureRef)) {
            pictureRef = pictureEv;
            trendAtStart = tr;
        }
        Step s = new Step();
        s.scene = sceneSmoothed;
        s.wanted = pictureRef + (tr - trendAtStart);
        double neededSettings = s.wanted - sceneSmoothed;
        s.error = neededSettings - settings;
        if (Math.abs(s.error) > DEAD_BAND) {
            int n = (int) Math.round(s.error * 3);
            s.notches = Math.max(-2, Math.min(2, n));
        }
        return s;
    }

    // -----------------------------------------------------------------
    // Brightness of a picture
    // -----------------------------------------------------------------

    private static final double[] LINEAR = new double[256];

    static {
        for (int i = 0; i < 256; i++) {
            double c = i / 255.0;
            LINEAR[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        }
    }

    /**
     * log2 of the mean linear luminance of ARGB pixels, leaving out the
     * brightest 2% (the Sun, street lights) so they don't drive the exposure.
     */
    static double pictureEv(int[] argb) {
        if (argb.length == 0) return Double.NaN;
        int bins = 4096;
        int[] hist = new int[bins];
        for (int p : argb) {
            double y = 0.2126 * LINEAR[(p >> 16) & 0xFF] + 0.7152 * LINEAR[(p >> 8) & 0xFF] + 0.0722 * LINEAR[p & 0xFF];
            hist[Math.min(bins - 1, (int) (y * bins))]++;
        }
        long keep = Math.max(1, Math.round(argb.length * 0.98));
        double sum = 0;
        long n = 0;
        for (int i = 0; i < bins && n < keep; i++) {
            long take = Math.min(hist[i], keep - n);
            sum += take * ((i + 0.5) / bins);
            n += take;
        }
        double mean = Math.max(1e-6, sum / n);
        return Math.log(mean) / Math.log(2);
    }

    // -----------------------------------------------------------------
    // Sun altitude (NOAA low-precision formulas, about 0.1° accuracy)
    // -----------------------------------------------------------------

    static double sunAltitude(double latDeg, double lonDeg, long epochMillis) {
        double jd = epochMillis / 86400000.0 + 2440587.5;
        double t = (jd - 2451545.0) / 36525.0;
        double l0 = norm360(280.46646 + t * (36000.76983 + t * 0.0003032));
        double m = 357.52911 + t * (35999.05029 - 0.0001537 * t);
        double mr = Math.toRadians(m);
        double c = Math.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
                + Math.sin(2 * mr) * (0.019993 - 0.000101 * t) + Math.sin(3 * mr) * 0.000289;
        double trueLong = l0 + c;
        double omega = 125.04 - 1934.136 * t;
        double lambda = trueLong - 0.00569 - 0.00478 * Math.sin(Math.toRadians(omega));
        double eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
        double eps = eps0 + 0.00256 * Math.cos(Math.toRadians(omega));
        double decl = Math.asin(Math.sin(Math.toRadians(eps)) * Math.sin(Math.toRadians(lambda)));
        double ra = Math.atan2(Math.cos(Math.toRadians(eps)) * Math.sin(Math.toRadians(lambda)), Math.cos(Math.toRadians(lambda)));
        double gmst = norm360(280.46061837 + 360.98564736629 * (jd - 2451545.0) + t * t * (0.000387933 - t / 38710000.0));
        double ha = Math.toRadians(norm360(gmst + lonDeg - Math.toDegrees(ra)));
        double lat = Math.toRadians(latDeg);
        double alt = Math.asin(Math.sin(lat) * Math.sin(decl) + Math.cos(lat) * Math.cos(decl) * Math.cos(ha));
        return Math.toDegrees(alt);
    }

    private static double norm360(double a) {
        a %= 360;
        return a < 0 ? a + 360 : a;
    }
}
