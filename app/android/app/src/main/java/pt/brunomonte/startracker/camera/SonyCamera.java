package pt.brunomonte.startracker.camera;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbManager;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.SystemClock;
import android.provider.MediaStore;

import org.json.JSONArray;
import pt.brunomonte.startracker.HeadClient;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Controls a Sony camera (A7R V and other recent Alphas) over USB in
 * "PC Remote" mode: Sony's SDIO extensions to PTP, as used by libgphoto2.
 *
 * One instance for the app. Camera commands run on a single worker
 * thread; jobs (interval, panorama) run on their own thread and share the
 * same USB connection, which serialises each PTP transaction.
 */
public final class SonyCamera {

    // Standard PTP operations
    private static final int OP_OPEN_SESSION = 0x1002;
    private static final int OP_CLOSE_SESSION = 0x1003;
    private static final int OP_GET_STORAGE_IDS = 0x1004;
    private static final int OP_GET_STORAGE_INFO = 0x1005;
    private static final int OP_GET_OBJECT_INFO = 0x1008;
    private static final int OP_GET_OBJECT = 0x1009;
    // Sony SDIO operations
    private static final int OP_SDIO_CONNECT = 0x9201;
    private static final int OP_SDIO_GET_EXT_DEVICE_INFO = 0x9202;
    private static final int OP_SDIO_SET_VALUE = 0x9205;     // set a property to a value
    private static final int OP_SDIO_CONTROL = 0x9207;       // press buttons, step a property
    private static final int OP_SDIO_GET_ALL_PROPS = 0x9209;
    /** Handle of the newest shot waiting in the camera's memory. */
    private static final int SHOT_IN_MEMORY = 0xFFFFC001;
    /** Handle of the current live-view frame. */
    private static final int LIVE_VIEW = 0xFFFFC002;

    private static SonyCamera instance;

    private final Context ctx;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final ArrayDeque<String> log = new ArrayDeque<>();

    private volatile PtpUsb ptp;
    private String model = "";
    private volatile SonyProps props = new SonyProps();
    private volatile String state = "disconnected";
    private volatile String error = "";
    private byte[] lastDeviceInfo = new byte[0];
    private byte[] lastProps = new byte[0];
    private int shots;
    private String lastFile = "";
    /** The newest file downloaded to the tablet (any type), for brightness measuring. */
    private volatile Uri lastUri;
    /** JPEGs downloaded during the current job (for People Remover). */
    private final java.util.List<Uri> jobJpegs = new java.util.ArrayList<>();
    private volatile String card = "";

    // Live view
    private volatile boolean liveWanted;
    private Thread liveThread;
    private volatile byte[] liveJpeg;
    private volatile int liveSeq;
    private volatile String liveError = "";

    // Job state
    private volatile Thread job;
    private volatile boolean stopJob;
    private volatile String jobName = "";
    private volatile String jobStep = "";

    public static synchronized SonyCamera get(Context ctx) {
        if (instance == null) instance = new SonyCamera(ctx.getApplicationContext());
        return instance;
    }

    private SonyCamera(Context ctx) {
        this.ctx = ctx;
    }

    // ---------------------------------------------------------------------
    // Connection
    // ---------------------------------------------------------------------

    public boolean isConnected() {
        return ptp != null;
    }

    /** Opens the camera; permission must already be granted. Runs on the worker. */
    public void connect(UsbDevice device) {
        worker.execute(() -> {
            if (ptp != null) return;
            state = "connecting";
            error = "";
            try {
                UsbManager um = (UsbManager) ctx.getSystemService(Context.USB_SERVICE);
                UsbDeviceConnection conn = um.openDevice(device);
                if (conn == null) throw new IOException("Android refused to open the camera");
                ptp = PtpUsb.open(conn, device);
                model = device.getProductName() != null ? device.getProductName() : "Sony camera";
                log("USB opened: " + model + String.format(Locale.ROOT, " (%04x:%04x)",
                        device.getVendorId(), device.getProductId()));
                handshake();
                state = "connected";
                refreshNow();
                readCard();
            } catch (Exception e) {
                fail("Connect failed", e);
                closeQuietly();
            }
        });
    }

    /**
     * Opens a PTP session and Sony's remote-control mode. The three
     * SDIO Connect phases and the device-info request follow libgphoto2.
     */
    private void handshake() throws IOException {
        int status = ptp.deviceStatus();
        log(String.format(Locale.ROOT, "USB %s, camera status %s", ptp.describe(),
                status < 0 ? "no answer" : String.format(Locale.ROOT, "0x%04x", status)));
        int stale = ptp.drain();
        if (stale > 0) log("Discarded " + stale + " bytes left over from an earlier connection");
        PtpUsb.Response r;
        ptp.startSession();
        try {
            r = ptp.transact(OP_OPEN_SESSION, 1);
        } catch (IOException first) {
            // A camera left mid-transfer by another computer or app answers
            // nothing until its PTP state is reset.
            log("No answer to OpenSession (" + first.getMessage() + "); resetting the camera's USB link and trying again");
            ptp.recover();
            status = ptp.deviceStatus();
            log("After reset, camera status " + (status < 0 ? "no answer" : String.format(Locale.ROOT, "0x%04x", status)));
            try {
                r = ptp.transact(OP_OPEN_SESSION, 1);
            } catch (IOException second) {
                log("USB replies: " + ptp.readMode());
                throw new IOException(second.getMessage() + ". Close any other app using the camera (Gallery, Files import) "
                        + "and turn the camera off and on");
            }
        }
        if (!r.ok() && r.code != 0x201E) {          // 0x201E: session already open
            throw new IOException(String.format(Locale.ROOT, "OpenSession refused (0x%04x)", r.code));
        }
        log("Session open; USB replies: " + ptp.readMode());
        sdio(OP_SDIO_CONNECT, 1, 0, 0);
        sdio(OP_SDIO_CONNECT, 2, 0, 0);
        r = ptp.transact(OP_SDIO_GET_EXT_DEVICE_INFO, 0xC8);
        lastDeviceInfo = r.data;
        if (r.data.length >= 2) {
            int version = (r.data[0] & 0xFF) | ((r.data[1] & 0xFF) << 8);
            log(String.format(Locale.ROOT, "Sony remote protocol %d.%02d", version / 100, version % 100));
        }
        sdio(OP_SDIO_CONNECT, 3, 0, 0);
        log("Remote control mode on");
    }

    private void sdio(int op, int... params) throws IOException {
        PtpUsb.Response r = ptp.transact(op, params);
        if (!r.ok()) throw new IOException(String.format(Locale.ROOT, "Camera refused 0x%04x (0x%04x)", op, r.code));
    }

    public void disconnect() {
        stopJob();
        worker.execute(() -> {
            if (ptp != null) {
                try {
                    ptp.transact(OP_CLOSE_SESSION);
                } catch (Exception ignored) {
                }
            }
            closeQuietly();
            state = "disconnected";
            log("Disconnected");
        });
    }

    /** USB cable pulled. */
    public void detached() {
        stopJob = true;
        closeQuietly();
        state = "disconnected";
        log("Camera unplugged");
    }

    private synchronized void closeQuietly() {
        if (ptp != null) ptp.close();
        ptp = null;
    }

    // ---------------------------------------------------------------------
    // Properties
    // ---------------------------------------------------------------------

    public void refresh() {
        worker.execute(() -> {
            try {
                if (ptp != null && job == null) refreshNow();
            } catch (Exception e) {
                fail("Reading settings failed", e);
            }
        });
    }

    private void refreshNow() throws IOException {
        PtpUsb.Response r = ptp.transact(OP_SDIO_GET_ALL_PROPS);
        if (!r.ok()) throw new IOException(String.format(Locale.ROOT, "Camera refused settings read (0x%04x)", r.code));
        lastProps = r.data;
        SonyProps p = SonyProps.parse(r.data);
        if (p.parseProblem != null && props.parseProblem == null) log("Settings list: " + p.parseProblem);
        props = p;
    }

    /** Steps ISO, shutter or aperture one notch (+1 / -1), like turning a dial. */
    public void step(int code, int direction) {
        worker.execute(() -> {
            try {
                byte[] v = {(byte) (direction > 0 ? 0x01 : 0xFF)};
                PtpUsb.Response r = ptp.transact(OP_SDIO_CONTROL, new int[]{code}, v, null);
                if (!r.ok()) log(String.format(Locale.ROOT, "Step 0x%04x refused (0x%04x)", code, r.code));
                SystemClock.sleep(150);
                refreshNow();
            } catch (Exception e) {
                fail("Change failed", e);
            }
        });
    }

    /** Sets a property to one of its listed values. */
    public void set(int code, long value) {
        worker.execute(() -> {
            try {
                setNow(code, value);
                SystemClock.sleep(150);
                refreshNow();
            } catch (Exception e) {
                fail("Change failed", e);
            }
        });
    }

    private void setNow(int code, long value) throws IOException {
        SonyProps.Prop p = props.props.get(code);
        int type = p != null ? p.type : 4;
        PtpUsb.Response r = ptp.transact(OP_SDIO_SET_VALUE, new int[]{code}, encode(type, value), null);
        if (!r.ok()) log(String.format(Locale.ROOT, "Set 0x%04x refused (0x%04x)", code, r.code));
    }

    private static byte[] encode(int type, long v) {
        int size;
        switch (type) {
            case 1: case 2: size = 1; break;
            case 3: case 4: size = 2; break;
            case 7: case 8: size = 8; break;
            default: size = 4;
        }
        ByteBuffer b = ByteBuffer.allocate(size).order(ByteOrder.LITTLE_ENDIAN);
        if (size == 1) b.put((byte) v);
        else if (size == 2) b.putShort((short) v);
        else if (size == 8) b.putLong(v);
        else b.putInt((int) v);
        return b.array();
    }

    private void button(int code, int value) throws IOException {
        byte[] v = encode(4, value);
        PtpUsb.Response r = ptp.transact(OP_SDIO_CONTROL, new int[]{code}, v, null);
        if (!r.ok()) throw new IOException(String.format(Locale.ROOT, "Button 0x%04x refused (0x%04x)", code, r.code));
    }

    /**
     * Free space on the camera's memory cards, from the standard PTP
     * storage queries. Left empty when the camera does not report it in
     * remote mode.
     */
    private void readCard() {
        if (ptp == null) return;
        try {
            PtpUsb.Response ids = ptp.transact(OP_GET_STORAGE_IDS);
            if (!ids.ok() || ids.data.length < 4) return;
            ByteBuffer b = ByteBuffer.wrap(ids.data).order(ByteOrder.LITTLE_ENDIAN);
            int n = b.getInt();
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < n && b.remaining() >= 4; i++) {
                int id = b.getInt();
                if ((id & 0xFFFF) == 0) continue;               // slot without a card
                PtpUsb.Response r = ptp.transact(OP_GET_STORAGE_INFO, id);
                if (!r.ok() || r.data.length < 26) continue;
                ByteBuffer d = ByteBuffer.wrap(r.data).order(ByteOrder.LITTLE_ENDIAN);
                long capacity = d.getLong(6);
                long free = d.getLong(14);
                long shotsLeft = d.getInt(22) & 0xFFFFFFFFL;
                if (capacity <= 0) continue;
                if (sb.length() > 0) sb.append(" · ");
                sb.append(String.format(Locale.ROOT, "Card %d: %.1f of %.0f GB free", (id >> 16) & 0xFFFF,
                        free / 1e9, capacity / 1e9));
                if (shotsLeft > 0 && shotsLeft != 0xFFFFFFFFL) sb.append(", ").append(shotsLeft).append(" shots");
            }
            card = sb.toString();
        } catch (Exception e) {
            log("Card info not available: " + e.getMessage());
        }
    }

    // ---------------------------------------------------------------------
    // Shooting
    // ---------------------------------------------------------------------

    /** What one press of the shutter does. */
    public static final class ShotSettings {
        double bulbSeconds = 30;
        boolean autofocus = false;

        static ShotSettings from(JSONObject o) {
            ShotSettings s = new ShotSettings();
            s.bulbSeconds = Math.max(0.1, o.optDouble("bulbSeconds", 30));
            s.autofocus = o.optBoolean("autofocus", false);
            return s;
        }
    }

    public boolean shootOnce(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        return runJob("Single shot", () -> shoot(s));
    }

    /**
     * Takes one picture. In BULB the shutter is held for bulbSeconds.
     * Shots the camera keeps for the tablet are downloaded.
     */
    private void shoot(ShotSettings s) throws Exception {
        refreshNow();
        boolean bulb = SonyProps.isBulb(props.get(SonyProps.SHUTTER, -1));
        long dest = props.get(SonyProps.SAVE_DESTINATION, SonyProps.DEST_CARD);
        if (s.autofocus) {
            button(SonyProps.AUTOFOCUS_BUTTON, 2);
            SystemClock.sleep(700);
        }
        button(SonyProps.SHUTTER_BUTTON, 2);
        if (bulb) {
            long until = SystemClock.elapsedRealtime() + (long) (s.bulbSeconds * 1000);
            while (SystemClock.elapsedRealtime() < until && !stopJob) {
                long left = until - SystemClock.elapsedRealtime();
                jobStep = String.format(Locale.ROOT, "Exposing… %.0f s left", Math.max(0, left / 1000.0));
                SystemClock.sleep(Math.min(250, Math.max(1, left)));
            }
        } else {
            SystemClock.sleep(200);
        }
        button(SonyProps.SHUTTER_BUTTON, 1);
        if (s.autofocus) button(SonyProps.AUTOFOCUS_BUTTON, 1);
        shots++;
        log("Shot " + shots + (bulb ? String.format(Locale.ROOT, " (bulb %.1f s)", s.bulbSeconds) : ""));
        String stepNow = jobStep, fileBefore = lastFile;
        if (dest == SonyProps.DEST_TABLET || dest == SonyProps.DEST_BOTH) {
            downloadWaiting(bulb ? 30_000 : 15_000 + exposureMillis());
        } else {
            // Card only: let the camera finish the exposure and write the file.
            jobStep = "Camera saving to card…";
            SystemClock.sleep(bulb ? 1000 : 600 + exposureMillis());
        }
        logShot(stepNow, lastFile.equals(fileBefore) ? "on camera card" : lastFile,
                bulb ? String.format(Locale.ROOT, "bulb %.1f s", s.bulbSeconds) : SonyProps.shutter(props.get(SonyProps.SHUTTER, 0)));
    }

    /** One line in the day's shot log (Documents/Star Tracker). */
    private void logShot(String step, String file, String shutter) {
        double az = Double.NaN, alt = Double.NaN;
        try {
            double[] p = new HeadClient().position();
            az = p[0];
            alt = p[1];
        } catch (Exception ignored) {
            // Driver not running: the shot is logged without the pointing.
        }
        ShotLog.add(ctx, jobName.isEmpty() ? "Single shot" : jobName, step, file, shutter,
                SonyProps.format(SonyProps.F_NUMBER, props.get(SonyProps.F_NUMBER, 0)),
                SonyProps.iso(props.get(SonyProps.ISO, 0)), az, alt);
    }

    /** Where the head points now, to come back to after a job (null if unknown). */
    private static double[] startPosition(HeadClient polaris) {
        try {
            double[] p = polaris.position();
            return Double.isNaN(p[0]) || Double.isNaN(p[1]) ? null : p;
        } catch (Exception e) {
            return null;
        }
    }

    /** Moves the head back to where the job started (also after Stop). */
    private void returnTo(HeadClient polaris, double[] start) {
        if (start == null) return;
        try {
            jobStep = "Returning to the start position";
            polaris.setTracking(false);
            polaris.slewAltAz(start[0], start[1]);
            polaris.waitWhileSlewing(() -> false, 180_000);
            log(String.format(Locale.ROOT, "Back at the start position (%.1f° / %.1f°)", start[0], start[1]));
        } catch (Exception e) {
            log("Could not return to the start position: " + e.getMessage());
        }
    }

    private long exposureMillis() {
        long v = props.get(SonyProps.SHUTTER, 0);
        long num = (v >> 16) & 0xFFFF, den = v & 0xFFFF;
        return den == 0 ? 0 : num * 1000 / den;
    }

    /** Downloads every shot the camera holds for the tablet (RAW + JPEG are two). */
    private void downloadWaiting(long waitMs) throws Exception {
        long deadline = SystemClock.elapsedRealtime() + waitMs;
        int got = 0;
        while (SystemClock.elapsedRealtime() < deadline) {
            refreshNow();
            long pending = props.get(SonyProps.OBJECT_IN_MEMORY, 0);
            if ((pending & 0x8000) != 0) {
                download();
                got++;
                deadline = SystemClock.elapsedRealtime() + 3000;   // a second file (RAW+JPEG) follows quickly
                continue;
            }
            if (got > 0 && pending == 0) return;
            jobStep = got == 0 ? "Waiting for the camera…" : jobStep;
            SystemClock.sleep(200);
        }
        if (got == 0) log("No image arrived from the camera (check Save destination)");
    }

    private void download() throws Exception {
        PtpUsb.Response info = ptp.transact(OP_GET_OBJECT_INFO, SHOT_IN_MEMORY);
        if (!info.ok()) throw new IOException(String.format(Locale.ROOT, "GetObjectInfo refused (0x%04x)", info.code));
        ByteBuffer b = ByteBuffer.wrap(info.data).order(ByteOrder.LITTLE_ENDIAN);
        long size = info.data.length >= 12 ? b.getInt(8) & 0xFFFFFFFFL : 0;
        String name = "";
        if (info.data.length > 52) {
            b.position(52);
            name = SonyProps.readString(b);
        }
        if (name.isEmpty()) name = "DSC" + System.currentTimeMillis() + ".JPG";
        name = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.ROOT).format(new Date()) + "_" + name;
        jobStep = String.format(Locale.ROOT, "Downloading %s (%.1f MB)", name, size / 1e6);
        try (Saved out = Saved.create(ctx, name)) {
            PtpUsb.Response r = ptp.transact(OP_GET_OBJECT, new int[]{SHOT_IN_MEMORY}, null, out.stream);
            if (!r.ok()) throw new IOException(String.format(Locale.ROOT, "GetObject refused (0x%04x)", r.code));
            out.commit();
            lastUri = out.uri;
            if (out.uri != null && name.toLowerCase(Locale.ROOT).matches(".*\\.jpe?g")) {
                synchronized (jobJpegs) {
                    jobJpegs.add(out.uri);
                }
            }
        }
        lastFile = name;
        log("Saved Pictures/Star Tracker/" + name);
    }

    /** A file in Pictures/Star Tracker, visible in the Gallery once complete. */
    static final class Saved implements AutoCloseable {
        final OutputStream stream;
        private final ContentResolver resolver;
        final Uri uri;
        private boolean done;

        private Saved(OutputStream stream, ContentResolver resolver, Uri uri) {
            this.stream = stream;
            this.resolver = resolver;
            this.uri = uri;
        }

        static Saved create(Context ctx, String name) throws IOException {
            String lower = name.toLowerCase(Locale.ROOT);
            String mime = lower.endsWith(".jpg") || lower.endsWith(".jpeg") ? "image/jpeg"
                    : lower.endsWith(".heif") || lower.endsWith(".hif") ? "image/heif"
                    : lower.endsWith(".arw") ? "image/x-sony-arw" : "application/octet-stream";
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ContentResolver cr = ctx.getContentResolver();
                ContentValues v = new ContentValues();
                v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                v.put(MediaStore.MediaColumns.MIME_TYPE, mime);
                v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Star Tracker");
                v.put(MediaStore.MediaColumns.IS_PENDING, 1);
                Uri collection = mime.startsWith("image/jpeg") || mime.startsWith("image/heif")
                        ? MediaStore.Images.Media.EXTERNAL_CONTENT_URI
                        : MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
                Uri uri = cr.insert(collection, v);
                if (uri == null) throw new IOException("No storage available for " + name);
                OutputStream os = cr.openOutputStream(uri);
                if (os == null) throw new IOException("Could not open " + name);
                return new Saved(os, cr, uri);
            }
            File dir = new File(ctx.getExternalFilesDir(Environment.DIRECTORY_PICTURES), "Star Tracker");
            if (!dir.exists() && !dir.mkdirs()) throw new IOException("Could not create " + dir);
            return new Saved(new FileOutputStream(new File(dir, name)), null, null);
        }

        void commit() {
            done = true;
        }

        @Override
        public void close() throws IOException {
            stream.close();
            if (resolver == null) return;
            if (done) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.MediaColumns.IS_PENDING, 0);
                resolver.update(uri, v, null, null);
            } else {
                resolver.delete(uri, null, null);
            }
        }
    }

    // ---------------------------------------------------------------------
    // Live view
    // ---------------------------------------------------------------------

    /**
     * Starts fetching live-view frames (about 10 per second). Frames are
     * paused while a job is shooting, so they never delay an exposure.
     */
    public synchronized void liveStart() {
        liveWanted = true;
        liveError = "";
        if (liveThread != null && liveThread.isAlive()) return;
        liveThread = new Thread(this::liveLoop, "camera-live");
        liveThread.start();
    }

    public void liveStop() {
        liveWanted = false;
    }

    /** The newest frame as "seq,base64-jpeg", or "" when there is none newer than since. */
    public String liveFrame(int since) {
        byte[] j = liveJpeg;
        int seq = liveSeq;
        if (j == null || seq == since) return "";
        return seq + "," + android.util.Base64.encodeToString(j, android.util.Base64.NO_WRAP);
    }

    private void liveLoop() {
        int failures = 0;
        while (liveWanted) {
            PtpUsb p = ptp;
            if (p == null) {
                liveError = "Camera not connected";
                break;
            }
            if (job != null) {
                SystemClock.sleep(300);
                continue;
            }
            long t0 = SystemClock.elapsedRealtime();
            try {
                PtpUsb.Response r = p.transact(OP_GET_OBJECT, LIVE_VIEW);
                byte[] jpeg = r.ok() ? liveJpegFrom(r.data) : null;
                if (jpeg != null) {
                    liveJpeg = jpeg;
                    liveSeq++;
                    failures = 0;
                    liveError = "";
                } else {
                    failures++;
                    liveError = r.ok() ? "No picture in the live-view data"
                            : String.format(Locale.ROOT, "Camera refused live view (0x%04x)", r.code);
                    SystemClock.sleep(200);
                }
            } catch (IOException e) {
                failures++;
                liveError = "Live view: " + e.getMessage();
                SystemClock.sleep(300);
            }
            if (failures >= 25) {
                log("Live view stopped: " + liveError);
                liveWanted = false;
                break;
            }
            long spent = SystemClock.elapsedRealtime() - t0;
            if (spent < 100) SystemClock.sleep(100 - spent);
        }
    }

    /**
     * The JPEG inside Sony's live-view data. Newer bodies start with a
     * header giving the image offset and size; otherwise the JPEG is found
     * by its start (FFD8) and end (FFD9) markers, as libgphoto2 does.
     */
    static byte[] liveJpegFrom(byte[] d) {
        if (d.length >= 8) {
            ByteBuffer b = ByteBuffer.wrap(d).order(ByteOrder.LITTLE_ENDIAN);
            long off = b.getInt(0) & 0xFFFFFFFFL, len = b.getInt(4) & 0xFFFFFFFFL;
            if (off >= 8 && len > 2 && off + len <= d.length
                    && d[(int) off] == (byte) 0xFF && d[(int) off + 1] == (byte) 0xD8) {
                return java.util.Arrays.copyOfRange(d, (int) off, (int) (off + len));
            }
        }
        int start = -1;
        for (int i = 0; i + 1 < d.length; i++) {
            if (d[i] == (byte) 0xFF && d[i + 1] == (byte) 0xD8) {
                start = i;
                break;
            }
        }
        if (start < 0) return null;
        for (int i = d.length - 2; i > start; i--) {
            if (d[i] == (byte) 0xFF && d[i + 1] == (byte) 0xD9) {
                return java.util.Arrays.copyOfRange(d, start, i + 2);
            }
        }
        return null;
    }

    // ---------------------------------------------------------------------
    // Focus
    // ---------------------------------------------------------------------

    /**
     * Moves the focus: steps -7…+7, negative = nearer, positive = farther;
     * 1 is the smallest step, 3 medium, 7 large. Needs MF or DMF focus mode.
     */
    public void focus(int steps) {
        int v = Math.max(-7, Math.min(7, steps));
        if (v == 0) return;
        worker.execute(() -> {
            try {
                PtpUsb.Response r = ptp.transact(OP_SDIO_CONTROL, new int[]{SonyProps.NEAR_FAR}, encode(3, v), null);
                if (!r.ok()) {
                    error = String.format(Locale.ROOT, "Focus refused (0x%04x): set the lens to MF or DMF", r.code);
                }
            } catch (Exception e) {
                fail("Focus failed", e);
            }
        });
    }

    /** Half-presses the shutter for about a second to autofocus. */
    public void autofocus() {
        worker.execute(() -> {
            try {
                button(SonyProps.AUTOFOCUS_BUTTON, 2);
                SystemClock.sleep(1000);
                button(SonyProps.AUTOFOCUS_BUTTON, 1);
            } catch (Exception e) {
                fail("Autofocus failed", e);
            }
        });
    }

    // ---------------------------------------------------------------------
    // Exposure brackets (HDR)
    // ---------------------------------------------------------------------

    public boolean startHdr(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int shots = Math.max(1, o.optInt("hdrShots", 3));
        double ev = Math.max(0.3, o.optDouble("hdrEv", 1));
        return runJob("HDR", () -> bracket(s, shots, ev));
    }

    /**
     * Shoots shots exposures ev stops apart around the current shutter
     * speed (aperture and ISO stay as they are), then puts the shutter
     * back. Exposures longer than 30 s are shot in BULB.
     */
    private void bracket(ShotSettings s, int shots, double ev) throws Exception {
        refreshNow();
        long original = props.get(SonyProps.SHUTTER, -1);
        double base = SonyProps.isBulb(original) ? s.bulbSeconds : Exposure.seconds(original);
        if (Double.isNaN(base)) throw new IOException("Unknown shutter speed: set it on the camera first");
        java.util.List<Double> offsets = Exposure.offsets(shots, ev);
        try {
            for (int i = 0; i < offsets.size() && !stopJob; i++) {
                double target = base * Math.pow(2, offsets.get(i));
                String step = String.format(Locale.ROOT, "Bracket %d of %d (%+.1f EV)", i + 1, offsets.size(), offsets.get(i));
                jobStep = step + ": setting shutter";
                ShotSettings shot = setExposure(target, s);
                jobStep = step;
                shoot(shot);
            }
        } finally {
            // Put the shutter back, even after Stop.
            boolean stopped = stopJob;
            stopJob = false;
            try {
                if (original >= 0) seekShutter(original);
            } catch (Exception e) {
                log("Could not restore the shutter speed: " + e.getMessage());
            } finally {
                stopJob = stopped;
            }
        }
    }

    /** Sets the shutter as close as possible to target seconds; returns the settings to shoot with. */
    private ShotSettings setExposure(double target, ShotSettings s) throws Exception {
        ShotSettings shot = new ShotSettings();
        shot.autofocus = s.autofocus;
        shot.bulbSeconds = s.bulbSeconds;
        if (target > Exposure.LONGEST_TIMED + 0.5) {
            shot.bulbSeconds = target;
            seekShutter(0);
            if (!SonyProps.isBulb(props.get(SonyProps.SHUTTER, -1))) {
                throw new IOException("Could not set BULB for a " + Math.round(target) + " s exposure");
            }
            return shot;
        }
        SonyProps.Prop p = props.props.get(SonyProps.SHUTTER);
        long want = p == null ? -1 : Exposure.nearest(p.choices, target);
        if (want >= 0) {
            seekShutter(want);
        } else {
            seekShutterBySteps(target);
        }
        double got = Exposure.seconds(props.get(SonyProps.SHUTTER, 0));
        if (!Double.isNaN(got) && Math.abs(Exposure.stops(target, got)) > 0.4) {
            log(String.format(Locale.ROOT, "Bracket: wanted %.4g s, camera is at %s",
                    target, SonyProps.shutter(props.get(SonyProps.SHUTTER, 0))));
        }
        return shot;
    }

    /** Sets the shutter to an exact value: directly if the camera accepts it, else dial step by step. */
    private void seekShutter(long value) throws Exception {
        if (props.get(SonyProps.SHUTTER, -1) == value) return;
        setNow(SonyProps.SHUTTER, value);
        SystemClock.sleep(150);
        refreshNow();
        if (props.get(SonyProps.SHUTTER, -1) == value) return;
        // Not accepted directly: turn the dial, learning which way it goes.
        double target = value == 0 ? Double.POSITIVE_INFINITY : Exposure.seconds(value);
        seekShutterBySteps(target);
    }

    /** Turns the shutter dial one click at a time toward target seconds (∞ = BULB). */
    private void seekShutterBySteps(double target) throws Exception {
        int dir = 1;
        boolean learned = false;
        for (int i = 0; i < 60 && !stopJob; i++) {
            long now = props.get(SonyProps.SHUTTER, -1);
            double cur = SonyProps.isBulb(now) ? Double.POSITIVE_INFINITY : Exposure.seconds(now);
            if (Double.isInfinite(target) && Double.isInfinite(cur)) return;
            if (!Double.isInfinite(target) && !Double.isNaN(cur) && !Double.isInfinite(cur)
                    && Math.abs(Exposure.stops(cur, target)) < 0.17) return;
            boolean needLonger = Double.isInfinite(target) || (!Double.isInfinite(cur) && target > cur);
            PtpUsb.Response r = ptp.transact(OP_SDIO_CONTROL, new int[]{SonyProps.SHUTTER},
                    new byte[]{(byte) ((needLonger ? dir : -dir) > 0 ? 0x01 : 0xFF)}, null);
            if (!r.ok()) throw new IOException(String.format(Locale.ROOT, "Shutter step refused (0x%04x)", r.code));
            SystemClock.sleep(120);
            refreshNow();
            if (!learned) {
                long after = props.get(SonyProps.SHUTTER, -1);
                double a = SonyProps.isBulb(after) ? Double.POSITIVE_INFINITY : Exposure.seconds(after);
                if (after == now) return;                       // dial did not move: give up
                boolean wentLonger = a > cur;
                if (wentLonger != needLonger) dir = -dir;       // +1 turns the other way on this body
                learned = true;
            }
        }
    }

    // ---------------------------------------------------------------------
    // Jobs
    // ---------------------------------------------------------------------

    interface Work {
        void run() throws Exception;
    }

    private synchronized boolean runJob(String name, Work work) {
        if (ptp == null) {
            error = "Camera not connected";
            return false;
        }
        if (job != null) {
            error = "Already running: " + jobName;
            return false;
        }
        stopJob = false;
        jobName = name;
        jobStep = "";
        error = "";
        CameraService.start(ctx, name);
        job = new Thread(() -> {
            try {
                work.run();
                log(name + (stopJob ? " stopped" : " done"));
                // Stopped on purpose: no alert. Finished by itself: tell the user.
                if (!stopJob) JobAlerts.done(ctx, name, error);
            } catch (Exception e) {
                fail(name + " failed", e);
                JobAlerts.failed(ctx, name, error);
            } finally {
                readCard();
                synchronized (SonyCamera.this) {
                    job = null;
                    jobName = "";
                    jobStep = "";
                }
                CameraService.stop(ctx);
            }
        }, "camera-job");
        job.start();
        return true;
    }

    public void stopJob() {
        stopJob = true;
    }

    /** Waits while checking for Stop. False when stopped. */
    private boolean pause(long ms, String what) {
        long until = SystemClock.elapsedRealtime() + ms;
        while (!stopJob) {
            long left = until - SystemClock.elapsedRealtime();
            if (left <= 0) return true;
            if (what != null) jobStep = String.format(Locale.ROOT, "%s %.0f s", what, Math.ceil(left / 1000.0));
            SystemClock.sleep(Math.min(250, left));
        }
        return false;
    }

    /**
     * Interval shooting. count 0 = until stopped. intervalSeconds runs from
     * the start of one shot to the next; if a shot takes longer, the next
     * one starts right after.
     */
    public boolean startInterval(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int count = Math.max(0, o.optInt("count", 10));
        double interval = Math.max(0, o.optDouble("intervalSeconds", 5));
        return runJob("Interval", () -> {
            for (int i = 1; (count == 0 || i <= count) && !stopJob; i++) {
                long started = SystemClock.elapsedRealtime();
                jobStep = count == 0 ? "Shot " + i : "Shot " + i + " of " + count;
                shoot(s);
                if (count != 0 && i == count) break;
                long wait = (long) (interval * 1000) - (SystemClock.elapsedRealtime() - started);
                if (wait > 0 && !pause(wait, "Next shot in")) break;
            }
        });
    }

    // ---------------------------------------------------------------------
    // Star Tracker head jobs with the camera on USB-C (decision D73): the head moves and waits at each frame
    // ("waiting_ack"); this side shoots and downloads, then answers job.ack. If this side stops answering, the head
    // pauses with tracking kept. The ack goes over the head's one-shot HTTP op, so it works with the screen off.
    // ---------------------------------------------------------------------

    public boolean startHeadJob(JSONObject o) {
        JSONObject job = o.optJSONObject("job");
        if (job == null) return false;
        ShotSettings s = ShotSettings.from(o.optJSONObject("shot") != null ? o.optJSONObject("shot") : job);
        return runJob("Head job", () -> {
            HeadClient head = new HeadClient();
            JSONObject start = head.op("job.start", job);
            int id = start.optInt("job_id", -1), frames = start.optInt("frames", 0);
            log("Head job " + id + ": " + frames + " frames");
            while (!stopJob) {
                JSONObject st = head.op("job.status", new JSONObject());
                String state = st.optString("state");
                if ("done".equals(state) || "stopped".equals(state) || "failed".equals(state)) {
                    log("Head job " + state + (st.has("reason") ? ": " + st.optString("reason") : ""));
                    break;
                }
                if ("waiting_ack".equals(state)) {
                    int frame = st.optInt("frame");
                    jobStep = "Frame " + frame + " of " + frames;
                    shoot(s);
                    head.op("job.ack", new JSONObject().put("job_id", id).put("frame", frame));
                } else {
                    SystemClock.sleep(250);
                }
            }
            if (stopJob) { try { head.op("job.stop", new JSONObject()); } catch (Exception ignored) { } }
        });
    }

    // ---------------------------------------------------------------------
    // Holy Grail: day-to-night timelapse with automatic exposure ramping
    // ---------------------------------------------------------------------

    /**
     * Interval shooting that keeps the exposure right through sunset or
     * sunrise. After each frame the picture's brightness is measured (from
     * the file downloaded to the tablet, else from live view) and the
     * shutter or ISO moves by 1/3-stop notches: darker scene -> longer
     * shutter up to maxShutter, then higher ISO up to maxIso; brighter scene
     * -> lower ISO first, then shorter shutter. The night is made
     * nightDarker stops darker than the day (by the Sun's altitude), so it
     * looks like night. Aperture is never touched. Deflicker afterwards in
     * LRTimelapse or similar.
     */
    public boolean startHolyGrail(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int count = Math.max(0, o.optInt("count", 0));
        double interval = Math.max(1, o.optDouble("intervalSeconds", 10));
        double maxShutter = Math.max(0.01, Math.min(Exposure.LONGEST_TIMED, o.optDouble("maxShutter", 15)));
        double minIso = Math.max(50, o.optDouble("minIso", 100));
        double maxIso = Math.max(minIso, o.optDouble("maxIso", 3200));
        double nightDarker = o.optDouble("nightDarker", 2);
        double lat = o.optDouble("lat", Double.NaN), lon = o.optDouble("lon", Double.NaN);
        return runJob("Holy Grail", () -> {
            refreshNow();
            if (SonyProps.isBulb(props.get(SonyProps.SHUTTER, -1)))
                throw new IOException("Set a shutter speed (not BULB) and ISO in the camera's M mode first");
            if (isoNow() <= 0) throw new IOException("Set ISO to a number (not AUTO) in the camera's M mode first");
            long dest = props.get(SonyProps.SAVE_DESTINATION, SonyProps.DEST_CARD);
            boolean fromFiles = dest == SonyProps.DEST_TABLET || dest == SonyProps.DEST_BOTH;
            log("Holy Grail: measuring brightness from " + (fromFiles ? "each downloaded picture"
                    : "live view (less exact at night: set Save destination to Tablet + card)")
                    + (Double.isNaN(lat) ? "; no location, so the night is not darkened" : ""));
            HolyGrail hg = new HolyGrail(Double.isNaN(lat) ? 0 : nightDarker);
            for (int i = 1; (count == 0 || i <= count) && !stopJob; i++) {
                long started = SystemClock.elapsedRealtime();
                jobStep = (count == 0 ? "Frame " + i : "Frame " + i + " of " + count) + " · " + settingsText();
                double seconds = Exposure.seconds(props.get(SonyProps.SHUTTER, 0));
                double iso = isoNow();
                lastUri = null;
                shoot(s);
                double ev = fromFiles ? measureFile(lastUri) : Double.NaN;
                if (Double.isNaN(ev)) ev = measureLiveView();
                if (Double.isNaN(ev)) {
                    log("Frame " + i + ": brightness not measured, exposure unchanged");
                } else {
                    double alt = Double.isNaN(lat) ? Double.NaN : HolyGrail.sunAltitude(lat, lon, System.currentTimeMillis());
                    HolyGrail.Step st = hg.frame(ev, seconds, iso, alt);
                    String moved = st.notches == 0 ? "" : moveExposure(st.notches, maxShutter, minIso, maxIso);
                    log(String.format(Locale.ROOT, "Frame %d: %s, error %+.2f EV%s%s", i, settingsText(), st.error,
                            Double.isNaN(alt) ? "" : String.format(Locale.ROOT, ", Sun %.1f°", alt), moved));
                }
                if (count != 0 && i == count) break;
                long wait = (long) (interval * 1000) - (SystemClock.elapsedRealtime() - started);
                if (wait > 0 && !pause(wait, "Next frame in")) break;
            }
        });
    }

    /**
     * Video: starts the camera's movie recording, keeps it running for
     * minutes (0 = until Stop), then stops it. The clip stays on the
     * camera's card.
     */
    public boolean startVideo(JSONObject o) {
        double minutes = Math.max(0, o.optDouble("minutes", 0));
        return runJob("Video", () -> {
            button(SonyProps.MOVIE_BUTTON, 2);
            log("Recording started" + (minutes > 0 ? String.format(Locale.ROOT, " for %.1f min", minutes) : ""));
            long t0 = SystemClock.elapsedRealtime();
            long until = minutes > 0 ? t0 + (long) (minutes * 60000) : Long.MAX_VALUE;
            try {
                while (!stopJob && SystemClock.elapsedRealtime() < until) {
                    long s = (SystemClock.elapsedRealtime() - t0) / 1000;
                    jobStep = String.format(Locale.ROOT, "Recording %d:%02d", s / 60, s % 60);
                    SystemClock.sleep(500);
                }
            } finally {
                button(SonyProps.MOVIE_BUTTON, 1);
                long s = (SystemClock.elapsedRealtime() - t0) / 1000;
                log(String.format(Locale.ROOT, "Recording stopped after %d:%02d (clip on the camera's card)", s / 60, s % 60));
            }
        });
    }

    /**
     * Astro sequence: count exposures of a tracked sky target (exposure as
     * set on the camera; BULB uses bulbSeconds). Every ditherEvery frames
     * the head is nudged a few arcseconds in a random direction (pulse
     * guiding), so noise and hot pixels land on different stars and stack
     * away; then it waits settleSeconds.
     */
    public boolean startAstro(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int count = Math.max(1, o.optInt("count", 30));
        double gap = Math.max(0, o.optDouble("gapSeconds", 2));
        int ditherEvery = Math.max(0, o.optInt("ditherEvery", 3));
        int ditherMs = Math.max(200, Math.min(8000, o.optInt("ditherMs", 2000)));
        double settle = Math.max(0, o.optDouble("settleSeconds", 5));
        HeadClient polaris = new HeadClient();
        java.util.Random rnd = new java.util.Random();
        return runJob("Astro sequence", () -> {
            boolean canDither = ditherEvery > 0;
            if (canDither) {
                try {
                    if (!polaris.tracking()) {
                        log("The head is not tracking: no dithering (and stars will trail). Go to the target first.");
                        canDither = false;
                    }
                } catch (Exception e) {
                    log("The head is not reachable: no dithering");
                    canDither = false;
                }
            }
            for (int i = 1; i <= count && !stopJob; i++) {
                jobStep = "Frame " + i + " of " + count;
                shoot(s);
                if (i == count) break;
                if (canDither && i % ditherEvery == 0) {
                    jobStep = "Dithering";
                    try {
                        // One move in RA and one in Dec, random directions and lengths
                        int ra = (int) (ditherMs * (0.5 + rnd.nextDouble())), dec = (int) (ditherMs * (0.5 + rnd.nextDouble()));
                        polaris.pulseGuide(rnd.nextBoolean() ? 2 : 3, ra);
                        waitPulse(polaris, ra);
                        polaris.pulseGuide(rnd.nextBoolean() ? 0 : 1, dec);
                        waitPulse(polaris, dec);
                        if (!pause((long) (settle * 1000), "Settling after dither")) break;
                    } catch (Exception e) {
                        log("Dither failed: " + e.getMessage());
                    }
                }
                if (gap > 0 && !pause((long) (gap * 1000), "Next frame in")) break;
            }
        });
    }

    private void waitPulse(HeadClient polaris, int ms) throws Exception {
        long until = SystemClock.elapsedRealtime() + ms + 15000;
        SystemClock.sleep(ms);
        while (polaris.pulseGuiding() && SystemClock.elapsedRealtime() < until && !stopJob) SystemClock.sleep(100);
    }

    /** Dark frames: the same exposure with the lens covered, no Polaris movement. */
    public boolean startDarks(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int count = Math.max(1, o.optInt("count", 20));
        double gap = Math.max(0, o.optDouble("gapSeconds", 2));
        return runJob("Dark frames", () -> {
            for (int i = 1; i <= count && !stopJob; i++) {
                jobStep = "Dark " + i + " of " + count;
                shoot(s);
                if (i < count && gap > 0 && !pause((long) (gap * 1000), "Next dark in")) break;
            }
        });
    }

    // Star trails: the latest blend as JPEG for the screen, and a counter
    private volatile byte[] trailsJpeg;
    private volatile int trailsSeq;

    /**
     * Star trails: interval shots that the tablet blends as they arrive,
     * keeping the brightest value of every pixel (lighten), so the trails
     * grow on the screen. Needs JPEGs on the tablet (Save destination
     * Tablet + card, JPEG or RAW+JPEG). The blend is saved at the end;
     * the single frames stay too, for a full-size stack on the PC.
     */
    public boolean startTrails(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int count = Math.max(2, o.optInt("count", 120));
        double interval = Math.max(0, o.optDouble("intervalSeconds", 0));
        return runJob("Star trails", () -> {
            int[] blend = null;
            int w = 0, h = 0, used = 0;
            trailsJpeg = null;
            synchronized (jobJpegs) {
                jobJpegs.clear();
            }
            try {
                for (int i = 1; i <= count && !stopJob; i++) {
                    long started = SystemClock.elapsedRealtime();
                    jobStep = "Frame " + i + " of " + count + (used > 0 ? " · " + used + " blended" : "");
                    int jpegsBefore;
                    synchronized (jobJpegs) {
                        jpegsBefore = jobJpegs.size();
                    }
                    shoot(s);
                    int jpegsAfter;
                    synchronized (jobJpegs) {
                        jpegsAfter = jobJpegs.size();
                    }
                    android.graphics.Bitmap bm = jpegsAfter > jpegsBefore ? decodeLastJpeg(2000) : null;
                    if (bm == null) {
                        if (i == 1) log("Star trails: no JPEG reached the tablet, nothing to blend (set Save destination to Tablet + card, with JPEG)");
                    } else {
                        if (blend == null) {
                            w = bm.getWidth();
                            h = bm.getHeight();
                            blend = new int[w * h];
                        }
                        if (bm.getWidth() == w && bm.getHeight() == h) {
                            int[] px = new int[w * h];
                            bm.getPixels(px, 0, w, 0, 0, w, h);
                            for (int k = 0; k < px.length; k++) {
                                int a = blend[k], b = px[k];
                                blend[k] = 0xFF000000 | Math.max(a & 0xFF0000, b & 0xFF0000)
                                        | Math.max(a & 0xFF00, b & 0xFF00) | Math.max(a & 0xFF, b & 0xFF);
                            }
                            used++;
                            if (used % 3 == 1 || i == count) publishTrails(blend, w, h);
                        }
                        bm.recycle();
                    }
                    if (i == count) break;
                    long wait = (long) (interval * 1000) - (SystemClock.elapsedRealtime() - started);
                    if (wait > 0 && !pause(wait, "Next frame in")) break;
                }
            } finally {
                if (blend != null && used > 1) {
                    android.graphics.Bitmap out = android.graphics.Bitmap.createBitmap(blend, w, h, android.graphics.Bitmap.Config.ARGB_8888);
                    String name = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.ROOT).format(new Date()) + "_StarTrails_" + used + ".jpg";
                    try (Saved f = Saved.create(ctx, name)) {
                        out.compress(android.graphics.Bitmap.CompressFormat.JPEG, 95, f.stream);
                        f.commit();
                    }
                    log("Saved Pictures/Star Tracker/" + name + " (" + used + " frames blended)");
                }
            }
        });
    }

    /** The latest blend, as "seq,base64-jpeg", or "" when there is none newer than since. */
    public String trailsFrame(int since) {
        byte[] j = trailsJpeg;
        int seq = trailsSeq;
        if (j == null || seq == since) return "";
        return seq + "," + android.util.Base64.encodeToString(j, android.util.Base64.NO_WRAP);
    }

    private void publishTrails(int[] blend, int w, int h) {
        int step = Math.max(1, w / 900);
        android.graphics.Bitmap full = android.graphics.Bitmap.createBitmap(blend, w, h, android.graphics.Bitmap.Config.ARGB_8888);
        android.graphics.Bitmap small = android.graphics.Bitmap.createScaledBitmap(full, w / step, h / step, true);
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        small.compress(android.graphics.Bitmap.CompressFormat.JPEG, 80, bos);
        trailsJpeg = bos.toByteArray();
        trailsSeq++;
        if (small != full) small.recycle();
        full.recycle();
    }

    /** The newest downloaded JPEG, scaled so its long side is at most maxSide; null if the shot was not a JPEG. */
    private android.graphics.Bitmap decodeLastJpeg(int maxSide) {
        // RAW+JPEG arrive as two files: the JPEG is in jobJpegs.
        Uri uri;
        synchronized (jobJpegs) {
            uri = jobJpegs.isEmpty() ? null : jobJpegs.get(jobJpegs.size() - 1);
        }
        if (uri == null) return null;
        try {
            android.graphics.BitmapFactory.Options op = new android.graphics.BitmapFactory.Options();
            op.inJustDecodeBounds = true;
            try (java.io.InputStream in = ctx.getContentResolver().openInputStream(uri)) {
                android.graphics.BitmapFactory.decodeStream(in, null, op);
            }
            int sample = 1;
            while (Math.max(op.outWidth, op.outHeight) / (sample * 2) >= maxSide) sample *= 2;
            op = new android.graphics.BitmapFactory.Options();
            op.inSampleSize = sample;
            try (java.io.InputStream in = ctx.getContentResolver().openInputStream(uri)) {
                return android.graphics.BitmapFactory.decodeStream(in, null, op);
            }
        } catch (Exception e) {
            log("Could not read the JPEG for blending: " + e.getMessage());
            return null;
        }
    }

    // ---------------------------------------------------------------------
    // Plate solving
    // ---------------------------------------------------------------------

    private PlateSolver.Catalog starCatalog;
    private volatile String lastSolve = "";

    private synchronized PlateSolver.Catalog catalog() throws IOException {
        if (starCatalog == null) starCatalog = PlateSolver.Catalog.read(ctx.getAssets().open("stars8.bin"));
        return starCatalog;
    }

    /** The last solve as JSON ("" before the first). */
    public String lastSolve() {
        return lastSolve;
    }

    /**
     * Plate solving. action: "solve" (shoot a frame and find where it
     * points), "sync" (and tell the driver), "goto" (sync, then go to the
     * target given as targetRa hours / targetDec degrees J2000, or else back
     * to where the head thought it pointed), "align" (solve and sync at
     * three sky positions: a multi-point alignment). Needs a JPEG on the
     * tablet and the lens's focal length (sensorWidth in mm, default 36).
     */
    public boolean startSolve(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        String action = o.optString("action", "solve");
        double focal = o.optDouble("focal", 0), sensorW = o.optDouble("sensorWidth", 36);
        double radius = Math.max(3, Math.min(25, o.optDouble("searchRadius", 8)));
        double targetRa = o.optDouble("targetRa", Double.NaN), targetDec = o.optDouble("targetDec", Double.NaN);
        if (!(focal > 0)) {
            error = "Set the lens focal length (Live view → Lens) first";
            return false;
        }
        double planeW = Math.toDegrees(sensorW / focal);       // tangent-plane width of the frame
        HeadClient polaris = new HeadClient();
        String name = action.equals("align") ? "Auto-align" : "Plate solve";
        return runJob(name, () -> {
            if (action.equals("align")) {
                autoAlign(polaris, s, planeW, radius);
                return;
            }
            double[] hint = hintJ2000(polaris);
            PlateSolver.Solution sol = shootAndSolve(s, hint, planeW, radius);
            if (sol == null) return;
            if (action.equals("sync") || action.equals("goto")) {
                polaris.j2000Sync(sol.ra / 15, sol.dec);
                log("Synced the head to the solved position");
                if (action.equals("goto")) {
                    double ra = Double.isNaN(targetRa) ? hint[0] / 15 : targetRa, dec = Double.isNaN(targetDec) ? hint[1] : targetDec;
                    jobStep = "Going to the target";
                    polaris.setTracking(true);
                    polaris.j2000Goto("target", ra, dec);
                    SystemClock.sleep(1000);
                    polaris.waitWhileSlewing(() -> stopJob, 180_000);
                    log(String.format(Locale.ROOT, "Re-centred on RA %.4fh Dec %+.3f°", ra, dec));
                }
            }
        });
    }

    /** The head pointing as J2000 {RA degrees, Dec degrees}. */
    private double[] hintJ2000(HeadClient polaris) throws IOException {
        double[] rd = polaris.raDec();
        if (Double.isNaN(rd[0]) || Double.isNaN(rd[1])) throw new IOException("The head position is not known (head connected?)");
        return toJ2000(rd[0] * 15, rd[1], System.currentTimeMillis());
    }

    /** Precession of date back to J2000 (enough for a search hint). */
    static double[] toJ2000(double raDeg, double decDeg, long epochMillis) {
        double years = (epochMillis - 946728000000L) / 31557600000.0;          // since J2000.0
        double m = 3.07496, n = 1.33621;                                       // s/yr and ″/yr
        double ra = raDeg, dec = decDeg;
        for (int it = 0; it < 2; it++) {                                        // apply the rate at the J2000 position
            double dra = (m + n * Math.sin(Math.toRadians(ra)) * Math.tan(Math.toRadians(dec))) * years * 15 / 3600;
            double ddec = n * 15 * Math.cos(Math.toRadians(ra)) * years / 3600;
            ra = raDeg - dra;
            dec = decDeg - ddec;
        }
        return new double[]{(ra % 360 + 360) % 360, dec};
    }

    /** Shoots a frame, solves it, logs and remembers the answer. Null (and a log line) when it fails. */
    private PlateSolver.Solution shootAndSolve(ShotSettings s, double[] hint, double planeW, double radius) throws Exception {
        int before;
        synchronized (jobJpegs) {
            before = jobJpegs.size();
        }
        jobStep = "Plate solve: taking the picture";
        shoot(s);
        int after;
        synchronized (jobJpegs) {
            after = jobJpegs.size();
        }
        if (after <= before) throw new IOException("No JPEG reached the tablet: set Save destination to Tablet + card, with JPEG or RAW+JPEG");
        jobStep = "Plate solve: finding stars";
        android.graphics.Bitmap bm = decodeLastJpeg(3000);
        if (bm == null) throw new IOException("Could not read the picture");
        int w = bm.getWidth(), h = bm.getHeight();
        int[] px = new int[w * h];
        bm.getPixels(px, 0, w, 0, 0, w, h);
        bm.recycle();
        float[] lum = new float[w * h];
        for (int i = 0; i < px.length; i++) {
            int p = px[i];
            lum[i] = 0.2126f * ((p >> 16) & 0xFF) + 0.7152f * ((p >> 8) & 0xFF) + 0.0722f * (p & 0xFF);
        }
        java.util.List<PlateSolver.Star> stars = PlateSolver.detect(lum, w, h, 60);
        log("Plate solve: " + stars.size() + " stars found in the picture");
        if (stars.size() < 8) {
            log("Too few stars: expose longer or raise ISO (and check focus and clouds)");
            return null;
        }
        jobStep = "Plate solve: matching the catalogue";
        PlateSolver.Catalog cat = catalog();
        PlateSolver.Solution sol = PlateSolver.solve(cat, stars, w, h, hint[0], hint[1], radius, planeW, 0.25);
        if (sol == null && radius < 15) {
            jobStep = "Plate solve: searching wider";
            sol = PlateSolver.solve(cat, stars, w, h, hint[0], hint[1], 15, planeW, 0.3);
        }
        if (sol == null) {
            log("Not solved. Check the lens focal length, that the head is roughly aligned (within ~10°), and that stars are sharp");
            lastSolve = "{\"ok\":false,\"time\":" + System.currentTimeMillis() + "}";
            return null;
        }
        double[] off = PlateSolver.project(sol.ra, sol.dec, hint[0], hint[1]);
        double offDeg = off == null ? Double.NaN : Math.hypot(off[0], off[1]);
        log(String.format(Locale.ROOT, "Solved: RA %s Dec %s, field %.2f°×%.2f°, %d stars matched, %.1f\" rms; the head was %.2f° off",
                hms(sol.ra / 15), dms(sol.dec), sol.fovW, sol.fovH, sol.matched, sol.rmsArcsec, offDeg));
        JSONObject j = new JSONObject();
        j.put("ok", true).put("time", System.currentTimeMillis()).put("ra", sol.ra / 15).put("dec", sol.dec)
                .put("raText", hms(sol.ra / 15)).put("decText", dms(sol.dec)).put("roll", sol.roll)
                .put("fovW", sol.fovW).put("fovH", sol.fovH).put("matched", sol.matched).put("stars", stars.size())
                .put("rms", sol.rmsArcsec).put("offset", offDeg).put("ms", sol.millis);
        lastSolve = j.toString();
        return sol;
    }

    /**
     * Auto-align: solve and sync at three positions (the current one, then
     * 60° either side in azimuth at a safe altitude), which gives the
     * driver a multi-point alignment; then returns to the start, tracking.
     */
    private void autoAlign(HeadClient polaris, ShotSettings s, double planeW, double radius) throws Exception {
        double[] start = startPosition(polaris);
        if (start == null) throw new IOException("The head position is not known (head connected?)");
        double alt = Math.max(30, Math.min(65, start[1]));
        double[][] points = {{start[0], start[1]}, {start[0] + 60, alt}, {start[0] - 60, alt}};
        int synced = 0;
        for (int i = 0; i < points.length && !stopJob; i++) {
            if (i > 0) {
                jobStep = String.format(Locale.ROOT, "Auto-align %d of 3: moving", i + 1);
                polaris.setTracking(false);
                polaris.slewAltAz(points[i][0], points[i][1]);
                SystemClock.sleep(800);
                if (!polaris.waitWhileSlewing(() -> stopJob, 180_000)) break;
            }
            polaris.setTracking(true);
            if (!pause(3000, "Settling")) break;
            double[] hint = hintJ2000(polaris);
            PlateSolver.Solution sol = shootAndSolve(s, hint, planeW, radius);
            if (sol == null) {
                log("Auto-align point " + (i + 1) + " not solved: skipped");
                continue;
            }
            polaris.j2000Sync(sol.ra / 15, sol.dec);
            synced++;
            log("Auto-align point " + (i + 1) + " synced");
        }
        log("Auto-align: " + synced + " of 3 points synced" + (synced >= 2 ? " (multi-point alignment)" : ""));
        if (!stopJob) {
            polaris.setTracking(false);
            polaris.slewAltAz(start[0], start[1]);
            SystemClock.sleep(800);
            polaris.waitWhileSlewing(() -> stopJob, 180_000);
            polaris.setTracking(true);
        }
    }

    private static String hms(double hours) {
        double h = (hours % 24 + 24) % 24;
        int hh = (int) h, mm = (int) ((h - hh) * 60);
        double ss = ((h - hh) * 60 - mm) * 60;
        return String.format(Locale.ROOT, "%02dh%02dm%04.1fs", hh, mm, ss);
    }

    private static String dms(double deg) {
        double a = Math.abs(deg);
        int d = (int) a, m = (int) ((a - d) * 60);
        double sec = ((a - d) * 60 - m) * 60;
        return String.format(Locale.ROOT, "%s%02d°%02d′%02.0f″", deg < 0 ? "−" : "+", d, m, sec);
    }

    private double isoNow() {
        long v = props.get(SonyProps.ISO, 0);
        return v == 0xFFFFFF || v <= 0 ? -1 : v;
    }

    private String settingsText() {
        return SonyProps.shutter(props.get(SonyProps.SHUTTER, 0)) + " " + SonyProps.iso(props.get(SonyProps.ISO, 0));
    }

    /**
     * Moves the exposure by notches (1/3 stop each; + brighter). Brighter:
     * shutter first (less noise), then ISO. Darker: ISO first, then shutter.
     * Returns a note for the log.
     */
    private String moveExposure(int notches, double maxShutter, double minIso, double maxIso) throws Exception {
        StringBuilder note = new StringBuilder();
        for (int k = 0; k < Math.abs(notches) && !stopJob; k++) {
            boolean brighter = notches > 0;
            refreshNow();
            double sec = Exposure.seconds(props.get(SonyProps.SHUTTER, 0));
            double iso = isoNow();
            boolean done;
            if (brighter) {
                done = sec * Math.pow(2, 1 / 3.0) <= maxShutter * 1.05 && nudgeShutter(true);
                if (!done) done = iso * Math.pow(2, 1 / 3.0) <= maxIso * 1.05 && nudgeIso(true);
            } else {
                done = iso / Math.pow(2, 1 / 3.0) >= minIso * 0.95 && nudgeIso(false);
                if (!done) done = nudgeShutter(false);
            }
            if (!done) {
                note.append(brighter ? "; at the limit (max shutter and ISO)" : "; at the limit (shortest shutter, lowest ISO)");
                break;
            }
        }
        refreshNow();
        return note.length() == 0 ? " -> " + settingsText() : note.toString();
    }

    /**
     * Shutter to the next listed speed longer or shorter (else one dial step
     * towards 1/3 stop away). False when it could not move.
     */
    private boolean nudgeShutter(boolean longer) throws Exception {
        long now = props.get(SonyProps.SHUTTER, -1);
        double cur = Exposure.seconds(now);
        if (Double.isNaN(cur)) return false;
        double target = cur * Math.pow(2, (longer ? 1 : -1) / 3.0);
        if (target > Exposure.LONGEST_TIMED + 0.5) return false;
        SonyProps.Prop p = props.props.get(SonyProps.SHUTTER);
        long next = -1;
        double nextSec = Double.NaN;
        if (p != null) {
            for (long c : p.choices) {
                if (SonyProps.isBulb(c)) continue;
                double sec = Exposure.seconds(c);
                if (Double.isNaN(sec)) continue;
                boolean ok = longer ? sec > cur * 1.02 && (next < 0 || sec < nextSec)
                        : sec < cur / 1.02 && (next < 0 || sec > nextSec);
                if (ok) {
                    next = c;
                    nextSec = sec;
                }
            }
        }
        if (next >= 0) {
            if (nextSec > Exposure.LONGEST_TIMED + 0.5) return false;
            seekShutter(next);
        } else {
            seekShutterBySteps(target);
        }
        return props.get(SonyProps.SHUTTER, -1) != now;
    }

    private int isoDialDir = 1;

    /** ISO one notch up or down. False when it could not move. */
    private boolean nudgeIso(boolean higher) throws Exception {
        long now = props.get(SonyProps.ISO, -1);
        SonyProps.Prop p = props.props.get(SonyProps.ISO);
        if (p != null && !p.choices.isEmpty()) {
            long best = -1;
            for (long c : p.choices) {
                if (c == 0xFFFFFF || c <= 0) continue;
                if (higher ? c > now && (best < 0 || c < best) : c < now && (best < 0 || c > best)) best = c;
            }
            if (best < 0) return false;
            setNow(SonyProps.ISO, best);
            SystemClock.sleep(150);
            refreshNow();
            if (props.get(SonyProps.ISO, -1) != now) return true;
        }
        // No list or not accepted: turn the ISO dial, learning its direction.
        long orig = now;
        for (int attempt = 0; attempt < 3; attempt++) {
            byte b = (byte) ((higher ? isoDialDir : -isoDialDir) > 0 ? 0x01 : 0xFF);
            PtpUsb.Response r = ptp.transact(OP_SDIO_CONTROL, new int[]{SonyProps.ISO}, new byte[]{b}, null);
            if (!r.ok()) return false;
            SystemClock.sleep(150);
            refreshNow();
            long after = props.get(SonyProps.ISO, -1);
            if (after == now) return false;
            if (after != 0xFFFFFF && (higher ? after > orig : after < orig)) return true;
            if ((after > now) != higher) isoDialDir = -isoDialDir;   // this body turns the other way
            now = after;
        }
        return false;
    }

    /** Brightness (log2 mean linear luminance) of a downloaded picture, or NaN. */
    private double measureFile(Uri uri) {
        if (uri == null) return Double.NaN;
        try {
            android.graphics.Bitmap bm = null;
            try (java.io.InputStream in = ctx.getContentResolver().openInputStream(uri)) {
                // The embedded thumbnail works for JPEG and Sony ARW alike.
                if (in != null) bm = new android.media.ExifInterface(in).getThumbnailBitmap();
            }
            if (bm == null) {
                android.graphics.BitmapFactory.Options op = new android.graphics.BitmapFactory.Options();
                op.inSampleSize = 16;
                try (java.io.InputStream in = ctx.getContentResolver().openInputStream(uri)) {
                    bm = android.graphics.BitmapFactory.decodeStream(in, null, op);
                }
            }
            return bitmapEv(bm);
        } catch (Exception e) {
            log("Brightness from file failed: " + e.getMessage());
            return Double.NaN;
        }
    }

    /** Brightness from one live-view frame, or NaN. */
    private double measureLiveView() {
        try {
            PtpUsb.Response r = ptp.transact(OP_GET_OBJECT, LIVE_VIEW);
            byte[] jpeg = r.ok() ? liveJpegFrom(r.data) : null;
            if (jpeg == null) return Double.NaN;
            return bitmapEv(android.graphics.BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length));
        } catch (Exception e) {
            return Double.NaN;
        }
    }

    private static double bitmapEv(android.graphics.Bitmap bm) {
        if (bm == null) return Double.NaN;
        int w = bm.getWidth(), h = bm.getHeight();
        int step = Math.max(1, Math.max(w, h) / 240);
        android.graphics.Bitmap small = step > 1 ? android.graphics.Bitmap.createScaledBitmap(bm, w / step, h / step, true) : bm;
        int[] px = new int[small.getWidth() * small.getHeight()];
        small.getPixels(px, 0, small.getWidth(), 0, 0, small.getWidth(), small.getHeight());
        return HolyGrail.pictureEv(px);
    }

    /**
     * Panorama: for each panel of the driver's grid (Alpaca Pilot →
     * Settings → Panorama), move the head, let it settle, then take
     * shotsPerPanel pictures. Panel numbers follow the grid's First Panel
     * and Panel Order settings, so the driver decides the path.
     */
    public boolean startPanorama(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int shotsPerPanel = Math.max(1, o.optInt("shotsPerPanel", 1));
        double settle = Math.max(0, o.optDouble("settleSeconds", 3));
        double gap = Math.max(0, o.optDouble("gapSeconds", 1));
        int firstPanel = Math.max(1, o.optInt("firstPanel", 1));
        int lastPanelWanted = Math.max(0, o.optInt("lastPanel", 0));     // 0 = to the end of the grid
        int hdrShots = Math.max(1, o.optInt("hdrShots", 1));
        double hdrEv = Math.max(0.3, o.optDouble("hdrEv", 1));
        boolean back = o.optBoolean("returnToStart", false);
        HeadClient polaris = new HeadClient();
        return runJob("Panorama", () -> {
            double[] start = back ? startPosition(polaris) : null;
            try {
                panorama(polaris, s, firstPanel, lastPanelWanted, shotsPerPanel, settle, gap, hdrShots, hdrEv);
            } finally {
                returnTo(polaris, start);
            }
        });
    }

    /**
     * Sphere (720°) panorama: moves the head through a list of
     * azimuth/altitude points planned on the Camera page (rows of fewer
     * frames towards the zenith, zenith last) and shoots at each, tracking
     * off. HDR brackets per point if asked.
     */
    public boolean startSphere(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        double settle = Math.max(0, o.optDouble("settleSeconds", 2));
        int hdrShots = Math.max(1, o.optInt("hdrShots", 1));
        double hdrEv = Math.max(0.3, o.optDouble("hdrEv", 1));
        boolean back = o.optBoolean("returnToStart", true);
        java.util.List<double[]> pts = new java.util.ArrayList<>();
        JSONArray a = o.optJSONArray("points");
        for (int i = 0; a != null && i < a.length(); i++) {
            JSONArray p = a.optJSONArray(i);
            if (p != null && p.length() >= 2) pts.add(new double[]{p.optDouble(0), p.optDouble(1)});
        }
        if (pts.isEmpty()) {
            error = "Plan the sphere first";
            return false;
        }
        HeadClient polaris = new HeadClient();
        return runJob("Sphere panorama", () -> {
            double[] start = back ? startPosition(polaris) : null;
            try {
                polaris.setTracking(false);
                for (int i = 0; i < pts.size() && !stopJob; i++) {
                    double[] p = pts.get(i);
                    jobStep = String.format(Locale.ROOT, "Frame %d of %d: moving to %.0f° / %.0f°", i + 1, pts.size(), p[0], p[1]);
                    polaris.slewAltAz(p[0], p[1]);
                    SystemClock.sleep(500);
                    if (!polaris.waitWhileSlewing(() -> stopJob, 180_000)) break;
                    if (!pause((long) (settle * 1000), "Settling")) break;
                    jobStep = String.format(Locale.ROOT, "Frame %d of %d", i + 1, pts.size());
                    if (hdrShots > 1) bracket(s, hdrShots, hdrEv);
                    else shoot(s);
                }
            } finally {
                returnTo(polaris, start);
            }
        });
    }

    /**
     * Two-pass panorama on the same anchored grid: the foreground panels
     * untracked (grid tracking 0), then the sky panels tracked (1 =
     * horizon-locked, 2 = celestial), straight after or at skyAt (epoch
     * ms, e.g. full darkness). Only the grid's tracking is changed between
     * passes, so its position stays.
     */
    public boolean startMixedPanorama(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int shotsPerPanel = Math.max(1, o.optInt("shotsPerPanel", 1));
        double settle = Math.max(0, o.optDouble("settleSeconds", 3));
        double gap = Math.max(0, o.optDouble("gapSeconds", 1));
        int hdrShots = Math.max(1, o.optInt("hdrShots", 1));
        double hdrEv = Math.max(0.3, o.optDouble("hdrEv", 1));
        int fgFirst = Math.max(1, o.optInt("fgFirst", 1)), fgLast = Math.max(0, o.optInt("fgLast", 0));
        int skyFirst = Math.max(1, o.optInt("skyFirst", 1)), skyLast = Math.max(0, o.optInt("skyLast", 0));
        int skyTrack = o.optInt("skyTrack", 1) == 2 ? 2 : 1;
        long skyAt = o.optLong("skyAt", 0);
        boolean back = o.optBoolean("returnToStart", false);
        HeadClient polaris = new HeadClient();
        return runJob("Two-pass panorama", () -> {
            double[] start = back ? startPosition(polaris) : null;
            try {
                log("Pass 1: foreground, untracked");
                polaris.panoGrid("{\"track\":0}");
                panorama(polaris, s, fgFirst, fgLast, shotsPerPanel, settle, gap, hdrShots, hdrEv);
                if (stopJob) return;
                long wait = skyAt - System.currentTimeMillis();
                if (wait > 0) {
                    String at = new SimpleDateFormat("HH:mm", Locale.ROOT).format(new Date(skyAt));
                    log("Sky pass at " + at);
                    if (!pause(wait, "Sky pass at " + at + " ·")) return;
                }
                log("Pass 2: sky, " + (skyTrack == 2 ? "celestial" : "horizon-locked") + " tracking");
                polaris.panoGrid("{\"track\":" + skyTrack + "}");
                panorama(polaris, s, skyFirst, skyLast, shotsPerPanel, settle, gap, hdrShots, hdrEv);
            } finally {
                returnTo(polaris, start);
            }
        });
    }

    private void panorama(HeadClient polaris, ShotSettings s, int firstPanel, int lastPanelWanted, int shotsPerPanel,
                          double settle, double gap, int hdrShots, double hdrEv) throws Exception {
        {
            int panels = polaris.panelCount();
            int lastPanel = lastPanelWanted == 0 ? panels : Math.min(panels, lastPanelWanted);
            if (firstPanel > lastPanel) throw new IOException("Start panel " + firstPanel + " is after the stop panel " + lastPanel);
            log("Panorama: panels " + firstPanel + "–" + lastPanel + " of " + panels + ", " + shotsPerPanel + " shot(s) each");
            for (int panel = firstPanel; panel <= lastPanel && !stopJob; panel++) {
                jobStep = "Moving to panel " + panel + " of " + panels;
                polaris.slewToPanel(panel);
                SystemClock.sleep(500);
                long deadline = SystemClock.elapsedRealtime() + 180_000;
                while (polaris.slewing() && !stopJob) {
                    if (SystemClock.elapsedRealtime() > deadline) throw new IOException("Polaris did not finish moving to panel " + panel);
                    SystemClock.sleep(300);
                }
                if (stopJob) {
                    polaris.abortSlew();
                    break;
                }
                if (!pause((long) (settle * 1000), "Panel " + panel + ": settling")) break;
                for (int k = 1; k <= shotsPerPanel && !stopJob; k++) {
                    jobStep = "Panel " + panel + " of " + panels + ": shot " + k + " of " + shotsPerPanel;
                    if (hdrShots > 1) bracket(s, hdrShots, hdrEv);
                    else shoot(s);
                    if (k < shotsPerPanel && !pause((long) (gap * 1000), "Next shot in")) break;
                }
                log("Panel " + panel + " done");
            }
        }
    }

    /** Moves the focus now (job thread). Same values as focus(). */
    private void focusNow(int v) throws IOException {
        PtpUsb.Response r = ptp.transact(OP_SDIO_CONTROL, new int[]{SonyProps.NEAR_FAR}, encode(3, v), null);
        if (!r.ok()) throw new IOException(String.format(Locale.ROOT, "Focus refused (0x%04x): set the lens to MF or DMF", r.code));
    }

    /**
     * Focus stack: a shot, then the focus moves pulses × size toward far
     * (direction 1) or near (-1), and so on. Start with the focus on the
     * first subject. Optionally drives the focus back afterwards.
     */
    public boolean startFocusStack(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int shots = Math.max(2, o.optInt("shots", 10));
        int size = Math.max(1, Math.min(7, o.optInt("size", 1)));
        int pulses = Math.max(1, o.optInt("pulses", 2));
        int dir = o.optInt("direction", 1) < 0 ? -1 : 1;
        boolean back = o.optBoolean("returnToStart", true);
        long settle = (long) (Math.max(0, o.optDouble("settleSeconds", 0.5)) * 1000);
        return runJob("Focus stack", () -> {
            int moved = 0;
            try {
                for (int i = 1; i <= shots && !stopJob; i++) {
                    jobStep = "Focus stack: shot " + i + " of " + shots;
                    shoot(s);
                    if (i == shots) break;
                    jobStep = "Focus stack: moving focus";
                    for (int k = 0; k < pulses && !stopJob; k++) {
                        focusNow(dir * size);
                        moved++;
                        SystemClock.sleep(120);
                    }
                    SystemClock.sleep(settle);
                }
            } finally {
                if (back && moved > 0 && ptp != null) {
                    jobStep = "Returning focus";
                    try {
                        for (int k = 0; k < moved; k++) {
                            focusNow(-dir * size);
                            SystemClock.sleep(120);
                        }
                    } catch (IOException e) {
                        log("Could not return the focus: " + e.getMessage());
                    }
                }
            }
        });
    }

    /**
     * Path-lapse: shots spread evenly along a path through keyframes
     * ({"points":[[az,alt],…]}). For each shot the head moves, settles,
     * then shoots; intervalSeconds runs from one shot to the next.
     */
    public boolean startPathLapse(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int shots = Math.max(2, o.optInt("shots", 60));
        double interval = Math.max(0, o.optDouble("intervalSeconds", 5));
        long settle = (long) (Math.max(0, o.optDouble("settleSeconds", 1)) * 1000);
        java.util.List<double[]> keys = new java.util.ArrayList<>();
        JSONArray pts = o.optJSONArray("points");
        for (int i = 0; pts != null && i < pts.length(); i++) {
            JSONArray p = pts.optJSONArray(i);
            if (p != null && p.length() >= 2) keys.add(new double[]{p.optDouble(0), p.optDouble(1)});
        }
        if (keys.size() < 2) {
            error = "Add at least two positions for a path-lapse";
            return false;
        }
        java.util.List<double[]> path = Path.positions(keys, shots);
        boolean back = o.optBoolean("returnToStart", false);
        HeadClient polaris = new HeadClient();
        return runJob("Path-lapse", () -> {
            double[] start = back ? startPosition(polaris) : null;
            try {
                pathLapse(polaris, s, path, interval, settle);
            } finally {
                returnTo(polaris, start);
            }
        });
    }

    private void pathLapse(HeadClient polaris, ShotSettings s, java.util.List<double[]> path, double interval, long settle)
            throws Exception {
        {
            polaris.setTracking(false);
            for (int i = 0; i < path.size() && !stopJob; i++) {
                long started = SystemClock.elapsedRealtime();
                double[] p = path.get(i);
                jobStep = String.format(Locale.ROOT, "Shot %d of %d: moving to %.1f° / %.1f°", i + 1, path.size(), p[0], p[1]);
                polaris.slewAltAz(p[0], p[1]);
                if (!polaris.waitWhileSlewing(() -> stopJob, 120_000)) break;
                if (!pause(settle, null)) break;
                jobStep = "Shot " + (i + 1) + " of " + path.size();
                shoot(s);
                long wait = (long) (interval * 1000) - (SystemClock.elapsedRealtime() - started);
                if (i + 1 < path.size() && wait > 0 && !pause(wait, "Next shot in")) break;
            }
        }
    }

    /**
     * Scheduled interval shooting (Sun mode): optionally moves to a
     * position first, waits until startAt (epoch ms), optionally follows
     * the Sun, then shoots every intervalSeconds until endAt.
     */
    public boolean startScheduled(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        long startAt = o.optLong("startAt", System.currentTimeMillis());
        long endAt = o.optLong("endAt", startAt + 3600_000);
        double interval = Math.max(1, o.optDouble("intervalSeconds", 10));
        boolean trackSun = o.optBoolean("trackSun", false);
        double az = o.optDouble("az", Double.NaN), alt = o.optDouble("alt", Double.NaN);
        HeadClient polaris = new HeadClient();
        if (endAt <= startAt) {
            error = "The end time must be after the start time";
            return false;
        }
        return runJob("Sun timelapse", () -> {
            if (!Double.isNaN(az) && !Double.isNaN(alt) && !trackSun) {
                jobStep = "Moving into position";
                polaris.setTracking(false);
                polaris.slewAltAz(az, alt);
                if (!polaris.waitWhileSlewing(() -> stopJob, 180_000)) return;
            }
            while (!stopJob && System.currentTimeMillis() < startAt) {
                long left = startAt - System.currentTimeMillis();
                jobStep = "Starts in " + clock(left);
                SystemClock.sleep(Math.min(1000, Math.max(1, left)));
            }
            if (stopJob) return;
            if (trackSun) {
                jobStep = "Moving to the Sun";
                polaris.trackOrbital("Sun");
                SystemClock.sleep(1000);
                polaris.waitWhileSlewing(() -> stopJob, 180_000);
            }
            int i = 0;
            while (!stopJob && System.currentTimeMillis() < endAt) {
                long started = SystemClock.elapsedRealtime();
                i++;
                jobStep = "Shot " + i + " · ends in " + clock(endAt - System.currentTimeMillis());
                shoot(s);
                long wait = (long) (interval * 1000) - (SystemClock.elapsedRealtime() - started);
                if (wait > 0 && !pause(Math.min(wait, Math.max(0, endAt - System.currentTimeMillis())), "Next shot in")) break;
            }
        });
    }

    /**
     * People Remover: a burst from the same spot, then (optionally) the
     * median of all shots, which removes anything that moved. Needs JPEG
     * (or RAW+JPEG) and Save to "Card + tablet" or "Tablet only".
     */
    public boolean startPeopleRemover(JSONObject o) {
        ShotSettings s = ShotSettings.from(o);
        int shots = Math.max(3, Math.min(30, o.optInt("shots", 10)));
        double interval = Math.max(0, o.optDouble("intervalSeconds", 3));
        int sample = o.optInt("sample", 2) == 1 ? 1 : 2;
        boolean merge = o.optBoolean("merge", true);
        long dest = props.get(SonyProps.SAVE_DESTINATION, SonyProps.DEST_CARD);
        if (merge && dest != SonyProps.DEST_TABLET && dest != SonyProps.DEST_BOTH) {
            error = "People Remover merges on the tablet: set Save to “Card + tablet” first";
            return false;
        }
        return runJob("People Remover", () -> {
            synchronized (jobJpegs) {
                jobJpegs.clear();
            }
            for (int i = 1; i <= shots && !stopJob; i++) {
                long started = SystemClock.elapsedRealtime();
                jobStep = "Shot " + i + " of " + shots + " · keep the camera still";
                shoot(s);
                long wait = (long) (interval * 1000) - (SystemClock.elapsedRealtime() - started);
                if (i < shots && wait > 0 && !pause(wait, "Next shot in")) break;
            }
            if (!merge || stopJob) return;
            java.util.List<Uri> jpegs;
            synchronized (jobJpegs) {
                jpegs = new java.util.ArrayList<>(jobJpegs);
            }
            if (jpegs.size() < 3) {
                throw new IOException("Only " + jpegs.size() + " JPEGs arrived: set the camera to JPEG or RAW+JPEG");
            }
            jobStep = "Merging " + jpegs.size() + " shots…";
            android.graphics.Bitmap result = Median.merge(ctx.getContentResolver(), jpegs, sample,
                    pct -> jobStep = "Merging " + jpegs.size() + " shots… " + pct + "%");
            int outW = result.getWidth(), outH = result.getHeight();
            String name = new SimpleDateFormat("yyyyMMdd-HHmmss", Locale.ROOT).format(new Date()) + "_PEOPLE-REMOVED.JPG";
            jobStep = "Saving " + name;
            try (Saved out = Saved.create(ctx, name)) {
                result.compress(android.graphics.Bitmap.CompressFormat.JPEG, 95, out.stream);
                out.commit();
            } finally {
                result.recycle();
            }
            lastFile = name;
            log(String.format(Locale.ROOT, "People Remover: saved %s (%d × %d)", name, outW, outH));
        });
    }

    private static String clock(long ms) {
        long sec = Math.max(0, ms / 1000);
        return String.format(Locale.ROOT, "%d:%02d:%02d", sec / 3600, sec / 60 % 60, sec % 60);
    }

    // ---------------------------------------------------------------------
    // Status and diagnostics
    // ---------------------------------------------------------------------

    private void fail(String what, Exception e) {
        // A button pressed while no camera is connected
        String msg = (e instanceof NullPointerException && ptp == null) ? "Camera not connected" : e.getMessage();
        error = what + ": " + msg;
        log(error);
    }

    private synchronized void log(String line) {
        String t = new SimpleDateFormat("HH:mm:ss", Locale.ROOT).format(new Date());
        log.addLast(t + " " + line);
        while (log.size() > 200) log.removeFirst();
    }

    public synchronized String status() {
        try {
            JSONObject o = new JSONObject();
            o.put("state", state);
            o.put("model", model);
            o.put("error", error);
            o.put("job", jobName);
            o.put("step", jobStep);
            o.put("shots", shots);
            o.put("lastFile", lastFile);
            o.put("card", card);
            o.put("live", liveWanted);
            o.put("liveError", liveError);
            SonyProps p = props;
            JSONObject settings = new JSONObject();
            for (int code : new int[]{SonyProps.EXPOSURE_PROGRAM, SonyProps.SHUTTER, SonyProps.F_NUMBER,
                    SonyProps.ISO, SonyProps.FOCUS_MODE, SonyProps.EXPOSURE_COMP, SonyProps.WHITE_BALANCE, SonyProps.COLOR_TEMP,
                    SonyProps.BATTERY, SonyProps.SAVE_DESTINATION}) {
                SonyProps.Prop pr = p.props.get(code);
                if (pr == null) continue;
                JSONObject s = new JSONObject();
                s.put("code", code);
                s.put("value", pr.value);
                s.put("text", SonyProps.format(code, pr.value));
                s.put("writable", pr.writable);
                JSONArray choices = new JSONArray();
                for (Long c : pr.choices) {
                    choices.put(new JSONArray().put(c).put(SonyProps.format(code, c)));
                }
                s.put("choices", choices);
                settings.put(Integer.toString(code), s);
            }
            o.put("settings", settings);
            o.put("bulb", SonyProps.isBulb(p.get(SonyProps.SHUTTER, -1)));
            JSONArray l = new JSONArray();
            for (String line : log) l.put(line);
            o.put("log", l);
            return o.toString();
        } catch (Exception e) {
            return "{\"state\":\"error\",\"error\":" + JSONObject.quote(String.valueOf(e)) + "}";
        }
    }

    /** Text to send to the developer when a camera behaves unexpectedly. */
    public synchronized String diagnostics() {
        StringBuilder sb = new StringBuilder();
        sb.append("Star Tracker camera diagnostics\nModel: ").append(model).append('\n');
        sb.append("Android ").append(Build.VERSION.RELEASE).append(", ").append(Build.MANUFACTURER)
                .append(' ').append(Build.MODEL).append('\n');
        sb.append("Settings parse: ").append(props.parseProblem == null ? "ok" : props.parseProblem).append('\n');
        sb.append("Properties:\n");
        for (SonyProps.Prop p : props.props.values()) {
            sb.append(String.format(Locale.ROOT, "  %04x type %04x %s%s = %s (%s) choices %d\n", p.code, p.type,
                    p.writable ? "rw" : "r-", p.enabled ? "" : " disabled",
                    p.text != null ? p.text : Long.toString(p.value),
                    SonyProps.format(p.code, p.value), p.choices.size()));
        }
        sb.append("Log:\n");
        for (String line : log) sb.append("  ").append(line).append('\n');
        sb.append("ExtDeviceInfo (").append(lastDeviceInfo.length).append(" bytes):\n").append(hex(lastDeviceInfo, 512));
        sb.append("AllProps (").append(lastProps.length).append(" bytes):\n").append(hex(lastProps, 8192));
        return sb.toString();
    }

    private static String hex(byte[] d, int max) {
        StringBuilder sb = new StringBuilder();
        int n = Math.min(d.length, max);
        for (int i = 0; i < n; i++) {
            if (i % 32 == 0) sb.append(String.format(Locale.ROOT, "  %05x ", i));
            sb.append(String.format(Locale.ROOT, "%02x", d[i]));
            sb.append(i % 32 == 31 || i == n - 1 ? '\n' : ' ');
        }
        if (d.length > max) sb.append("  …\n");
        return sb.toString();
    }
}
