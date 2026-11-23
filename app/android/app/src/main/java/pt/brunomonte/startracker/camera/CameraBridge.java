package pt.brunomonte.startracker.camera;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.webkit.JavascriptInterface;

import org.json.JSONObject;

/**
 * window.CameraNative: what www/apps/camera.html needs to find the camera
 * on USB, ask for permission, and drive SonyCamera.
 */
public class CameraBridge {

    private static final String ACTION_USB_PERMISSION = "pt.brunomonte.startracker.USB_PERMISSION";
    private static final int SONY_VENDOR_ID = 0x054C;

    private static boolean receiverRegistered;

    private final Activity a;
    private final SonyCamera camera;
    private final UsbManager usb;
    private final Gallery gallery;

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            UsbDevice device = usbDevice(intent);
            if (ACTION_USB_PERMISSION.equals(intent.getAction())) {
                if (device != null && intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                    camera.connect(device);
                }
            } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(intent.getAction())) {
                if (device != null && PtpUsb.findPtpInterface(device) != null) camera.detached();
            }
        }
    };

    public CameraBridge(Activity activity) {
        this.a = activity;
        this.camera = SonyCamera.get(activity);
        this.usb = (UsbManager) activity.getSystemService(Context.USB_SERVICE);
        this.gallery = new Gallery(activity);
        registerOnce(activity.getApplicationContext());
    }

    private void registerOnce(Context app) {
        synchronized (CameraBridge.class) {
            if (receiverRegistered) return;
            receiverRegistered = true;
        }
        IntentFilter f = new IntentFilter();
        f.addAction(ACTION_USB_PERMISSION);
        f.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            app.registerReceiver(receiver, f, Context.RECEIVER_NOT_EXPORTED);
        } else {
            app.registerReceiver(receiver, f);
        }
    }

    /** The camera was plugged in and the user chose Star Tracker: permission is already granted. */
    public void onIntent(Intent intent) {
        if (intent != null && UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(intent.getAction())) {
            UsbDevice d = usbDevice(intent);
            if (d != null && PtpUsb.findPtpInterface(d) != null) camera.connect(d);
        }
    }

    @SuppressWarnings("deprecation")
    private static UsbDevice usbDevice(Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return intent.getParcelableExtra(UsbManager.EXTRA_DEVICE, UsbDevice.class);
        }
        return intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
    }

    /** Finds a camera on USB (a Sony first) and connects. Returns "ok", "asking" or "none". */
    @JavascriptInterface
    public String connect() {
        if (camera.isConnected()) return "ok";
        UsbDevice found = null;
        for (UsbDevice d : usb.getDeviceList().values()) {
            if (PtpUsb.findPtpInterface(d) == null) continue;
            if (found == null || d.getVendorId() == SONY_VENDOR_ID) found = d;
        }
        if (found == null) return "none";
        if (usb.hasPermission(found)) {
            camera.connect(found);
            return "ok";
        }
        int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ? PendingIntent.FLAG_MUTABLE : 0;
        PendingIntent pi = PendingIntent.getBroadcast(a, 0,
                new Intent(ACTION_USB_PERMISSION).setPackage(a.getPackageName()), flags);
        usb.requestPermission(found, pi);
        return "asking";
    }

    @JavascriptInterface
    public void disconnect() {
        camera.disconnect();
    }

    @JavascriptInterface
    public String status() {
        return camera.status();
    }

    @JavascriptInterface
    public void refresh() {
        camera.refresh();
    }

    /** Turns a setting one notch, like the camera's dial. direction: 1 or -1. */
    @JavascriptInterface
    public void step(int code, int direction) {
        camera.step(code, direction);
    }

    /** value is a decimal string (JavaScript numbers cannot hold every 64-bit value). */
    @JavascriptInterface
    public void set(int code, String value) {
        try {
            camera.set(code, Long.parseLong(value));
        } catch (NumberFormatException ignored) {
        }
    }

    @JavascriptInterface
    public boolean shoot(String json) {
        return camera.shootOnce(parse(json));
    }

    @JavascriptInterface
    public boolean startInterval(String json) {
        return camera.startInterval(parse(json));
    }

    /** Star Tracker: a head job (poses, path-lapse, astro) shot by this camera (D73). */
    @JavascriptInterface
    public boolean startHeadJob(String json) {
        return camera.startHeadJob(parse(json));
    }

    @JavascriptInterface
    public boolean startSolve(String json) {
        return camera.startSolve(parse(json));
    }

    @JavascriptInterface
    public String lastSolve() {
        return camera.lastSolve();
    }

    @JavascriptInterface
    public boolean startTrails(String json) {
        return camera.startTrails(parse(json));
    }

    @JavascriptInterface
    public String trailsFrame(int since) {
        return camera.trailsFrame(since);
    }

    @JavascriptInterface
    public boolean startAstro(String json) {
        return camera.startAstro(parse(json));
    }

    @JavascriptInterface
    public boolean startDarks(String json) {
        return camera.startDarks(parse(json));
    }

    @JavascriptInterface
    public boolean startVideo(String json) {
        return camera.startVideo(parse(json));
    }

    @JavascriptInterface
    public boolean startHolyGrail(String json) {
        return camera.startHolyGrail(parse(json));
    }

    @JavascriptInterface
    public boolean startSphere(String json) {
        return camera.startSphere(parse(json));
    }

    @JavascriptInterface
    public boolean startMixedPanorama(String json) {
        return camera.startMixedPanorama(parse(json));
    }

    @JavascriptInterface
    public boolean startPanorama(String json) {
        return camera.startPanorama(parse(json));
    }

    @JavascriptInterface
    public boolean startHdr(String json) {
        return camera.startHdr(parse(json));
    }

    @JavascriptInterface
    public boolean startFocusStack(String json) {
        return camera.startFocusStack(parse(json));
    }

    @JavascriptInterface
    public boolean startPathLapse(String json) {
        return camera.startPathLapse(parse(json));
    }

    @JavascriptInterface
    public boolean startPeopleRemover(String json) {
        return camera.startPeopleRemover(parse(json));
    }

    @JavascriptInterface
    public boolean startScheduled(String json) {
        return camera.startScheduled(parse(json));
    }

    /** Pictures saved in Pictures/Star Tracker, newest first (JSON array). */
    @JavascriptInterface
    public String gallery() {
        return gallery.list();
    }

    @JavascriptInterface
    public String galleryThumb(String id) {
        return gallery.thumb(Long.parseLong(id));
    }

    @JavascriptInterface
    public String galleryOpen(String id, String mime) {
        return gallery.open(Long.parseLong(id), mime);
    }

    @JavascriptInterface
    public void liveStart() {
        camera.liveStart();
    }

    @JavascriptInterface
    public void liveStop() {
        camera.liveStop();
    }

    /** Newest live-view frame as "seq,base64-jpeg", or "" when nothing newer than since. */
    @JavascriptInterface
    public String liveFrame(int since) {
        return camera.liveFrame(since);
    }

    /** Focus drive: -7…+7, negative nearer, positive farther; 1 small, 3 medium, 7 large. */
    @JavascriptInterface
    public void focus(int steps) {
        camera.focus(steps);
    }

    @JavascriptInterface
    public void autofocus() {
        camera.autofocus();
    }

    @JavascriptInterface
    public void stopJob() {
        camera.stopJob();
    }

    @JavascriptInterface
    public String diagnostics() {
        return camera.diagnostics();
    }

    private static JSONObject parse(String json) {
        try {
            return new JSONObject(json == null ? "{}" : json);
        } catch (Exception e) {
            return new JSONObject();
        }
    }
}
