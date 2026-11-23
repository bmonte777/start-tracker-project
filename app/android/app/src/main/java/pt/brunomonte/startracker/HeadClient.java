package pt.brunomonte.startracker;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * The Star Tracker head for the reused camera code (it used to talk to the Polaris driver): the same method names,
 * answered by the head's one-shot HTTP transport POST /startracker/v1/op (API 1.1, docs/06-apps.md section 4).
 * Works with the screen off, where the WebView's WebSocket does not. The UI sets the head's address on connect.
 */
public final class HeadClient {

    private static volatile String base = null;          // e.g. http://192.168.4.1
    private static int id;
    private long guideUntil;
    private final List<double[]> panels = new ArrayList<>();

    public static void setBase(String httpBase) { base = httpBase; }
    public static String base() { return base; }

    /** One request, one reply: returns the result object (empty when the head sends none). */
    public synchronized JSONObject op(String op, JSONObject args) throws IOException {
        if (base == null) throw new IOException("No head connected");
        try {
            JSONObject req = new JSONObject().put("v", 1).put("id", ++id).put("op", op).put("args", args == null ? new JSONObject() : args);
            HttpURLConnection c = (HttpURLConnection) new URL(base + "/startracker/v1/op").openConnection();
            c.setConnectTimeout(3000);
            c.setReadTimeout(15000);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json");
            try (OutputStream out = c.getOutputStream()) { out.write(req.toString().getBytes(StandardCharsets.UTF_8)); }
            InputStream in = c.getResponseCode() < 400 ? c.getInputStream() : c.getErrorStream();
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] b = new byte[8192];
            int n;
            while (in != null && (n = in.read(b)) > 0) buf.write(b, 0, n);
            JSONObject rep = new JSONObject(buf.toString("UTF-8"));
            if (rep.has("ev")) return rep;                                     // the state op answers with a state event
            if (!rep.optBoolean("ok", false)) {
                JSONObject e = rep.optJSONObject("err");
                throw new IOException("Head: " + (e != null ? e.optString("msg") + " (" + e.optString("code") + ")" : "error"));
            }
            JSONObject r = rep.optJSONObject("result");
            return r != null ? r : new JSONObject();
        } catch (JSONException e) {
            throw new IOException("Head answer not understood: " + e.getMessage());
        }
    }

    private JSONObject args(Object... kv) throws IOException {
        try {
            JSONObject o = new JSONObject();
            for (int i = 0; i + 1 < kv.length; i += 2) o.put((String) kv[i], kv[i + 1]);
            return o;
        } catch (JSONException e) { throw new IOException(e.getMessage()); }
    }

    public JSONObject state() throws IOException { return op("state", null); }

    public JSONObject status() throws IOException { return state(); }

    /** {azimuth, altitude} in degrees. */
    public double[] position() throws IOException {
        JSONObject a = state().optJSONObject("altaz");
        return a == null ? new double[]{Double.NaN, Double.NaN} : new double[]{a.optDouble("az_d"), a.optDouble("alt_d")};
    }

    public void slewAltAz(double az, double alt) throws IOException { op("goto", args("az_d", ((az % 360) + 360) % 360, "alt_d", alt)); }

    /** {RA hours, Dec degrees} of date (JNow). */
    public double[] raDec() throws IOException {
        JSONObject r = state().optJSONObject("radec");
        return r == null ? new double[]{Double.NaN, Double.NaN} : new double[]{r.optDouble("ra_now_h"), r.optDouble("dec_now_d")};
    }

    public void j2000Sync(double raHours, double decDeg) throws IOException { op("sync", args("ra_h", raHours, "dec_d", decDeg, "epoch", "J2000")); }

    public void j2000Goto(String name, double raHours, double decDeg) throws IOException { op("goto", args("ra_h", raHours, "dec_d", decDeg, "epoch", "J2000")); }

    public boolean tracking() throws IOException { return state().optBoolean("tracking", false); }

    public void setTracking(boolean on) throws IOException { op("track", args("on", on)); }

    /** 0 N, 1 S, 2 E, 3 W (ASCOM order), at the guide rate. */
    public void pulseGuide(int direction, int ms) throws IOException {
        String[] d = {"n", "s", "e", "w"};
        op("guide", args("dir", d[Math.max(0, Math.min(3, direction))], "ms", Math.max(1, Math.min(10000, ms))));
        guideUntil = android.os.SystemClock.elapsedRealtime() + ms;
    }

    /** The head does not report pulse guiding in its state: the pulse is over when its time is. */
    public boolean pulseGuiding() { return android.os.SystemClock.elapsedRealtime() < guideUntil + 100; }

    public void trackOrbital(String name) throws IOException {
        String n = name.toLowerCase(java.util.Locale.ROOT);
        if (n.equals("sun") || n.equals("moon")) op("goto", args("body", n));
        else throw new IOException("Pick " + name + " on the Sky screen: the app computes planets");
    }

    public boolean slewing() throws IOException {
        String m = state().optString("mode");
        return m.equals("slewing") || m.equals("moving") || m.equals("parking");
    }

    public void abortSlew() { try { op("stop", null); } catch (IOException ignored) { } }

    public boolean waitWhileSlewing(java.util.function.BooleanSupplier stop, long timeoutMs) throws IOException {
        android.os.SystemClock.sleep(500);
        long deadline = android.os.SystemClock.elapsedRealtime() + timeoutMs;
        while (slewing()) {
            if (stop.getAsBoolean()) { abortSlew(); return false; }
            if (android.os.SystemClock.elapsedRealtime() > deadline) throw new IOException("The head did not finish moving");
            android.os.SystemClock.sleep(300);
        }
        return !stop.getAsBoolean();
    }

    /** Manual move: 0 azimuth, 1 altitude, 2 roll, degrees per second (0 stops). */
    public void move(int axis, double dps) throws IOException { op("jog", args("axis", axis, "dps", dps)); }

    public void moveRaDec(int axis, double dps) throws IOException { move(axis, dps); }

    public void home() throws IOException { op("park", null); }

    /** Panorama panels for the reused code: a list of {az, alt} poses ("poses":[{az_d,alt_d},…]). The Star Tracker's
     *  own panorama planner sends whole jobs to the head instead (startHeadJob). */
    public void panoGrid(String json) throws IOException {
        try {
            panels.clear();
            org.json.JSONArray a = new JSONObject(json).optJSONArray("poses");
            if (a == null) throw new IOException("Use the Star Tracker panorama planner (Camera & jobs)");
            for (int i = 0; i < a.length(); i++) panels.add(new double[]{a.getJSONObject(i).getDouble("az_d"), a.getJSONObject(i).getDouble("alt_d")});
        } catch (JSONException e) { throw new IOException(e.getMessage()); }
    }

    public int panelCount() { return Math.max(1, panels.size()); }

    public void slewToPanel(int panel) throws IOException {
        if (panels.isEmpty()) throw new IOException("No panorama planned");
        double[] p = panels.get(Math.max(0, Math.min(panels.size() - 1, panel - 1)));
        slewAltAz(p[0], p[1]);
    }
}
