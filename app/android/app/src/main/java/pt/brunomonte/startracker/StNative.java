package pt.brunomonte.startracker;

import android.annotation.SuppressLint;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.content.Intent;
import android.location.Location;
import android.location.LocationManager;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelUuid;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import pt.brunomonte.startracker.camera.CameraService;

/**
 * window.StNative for the shared UI (app/shared/native.js): call(method, argsJson, callbackId) runs the method off the
 * UI thread and answers through window.__stNativeDone(callbackId, ok, json).
 * Methods: setTheme, setHead, discoverAlpaca, discoverMdns, bleScan, bleConnect, bleWrite, bleRead, bleDisconnect,
 * keepAwake, notify, openSettings, location.
 */
public final class StNative {

    private static final UUID SERVICE = UUID.fromString("5354524b-0100-4d2a-9b1e-000000000001");
    private final MainActivity act;
    private final WebView web;
    private final ExecutorService pool = Executors.newCachedThreadPool();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Map<String, BluetoothGatt> gatts = new ConcurrentHashMap<>();
    private final Map<String, Object[]> pendingIo = new ConcurrentHashMap<>();   // device -> {latch, value}

    StNative(MainActivity a, WebView w) { act = a; web = w; }

    @JavascriptInterface
    public void call(String method, String args, String cb) {
        pool.execute(() -> {
            String json;
            boolean ok = true;
            try {
                Object r = run(method, new JSONObject(args == null || args.isEmpty() ? "{}" : args));
                json = r == null ? "null" : (r instanceof String ? JSONObject.quote((String) r) : r.toString());
            } catch (Exception e) {
                ok = false;
                json = JSONObject.quote(e.getMessage() == null ? e.toString() : e.getMessage());
            }
            final String js = "window.__stNativeDone(" + JSONObject.quote(cb) + "," + ok + "," + JSONObject.quote(json) + ")";
            main.post(() -> web.evaluateJavascript(js, null));
        });
    }

    private Object run(String m, JSONObject a) throws Exception {
        switch (m) {
            case "setTheme": main.post(() -> act.applyTheme(a.optString("t", a.optString("theme", "night")))); return null;
            case "setHead": HeadClient.setBase(a.getString("http")); return null;
            case "discoverAlpaca": return discoverAlpaca(a.optInt("timeoutMs", 2000));
            case "discoverMdns": return discoverMdns(a.optInt("timeoutMs", 2000));
            case "bleScan": return bleScan(a.optInt("ms", 6000));
            case "bleConnect": bleConnect(a.getString("id")); return null;
            case "bleWrite": bleWrite(a.getString("id"), a.getString("ch"), a.getString("text")); return null;
            case "bleRead": return bleRead(a.getString("id"), a.getString("ch"));
            case "bleDisconnect": { BluetoothGatt g = gatts.remove(a.getString("id")); if (g != null) g.close(); return null; }
            case "keepAwake":
                if (a.optBoolean("on")) CameraService.start(act, a.optString("text", "Canopus job"));
                else CameraService.stop(act);
                return null;
            case "notify": notifyUser(a.optString("title"), a.optString("text")); return null;
            case "openSettings": {
                String w = a.optString("what");
                String action = "bluetooth".equals(w) ? Settings.ACTION_BLUETOOTH_SETTINGS : "location".equals(w) ? Settings.ACTION_LOCATION_SOURCE_SETTINGS : Settings.ACTION_WIFI_SETTINGS;
                act.startActivity(new Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                return null;
            }
            case "location": return location();
            default: throw new Exception("unknown call " + m);
        }
    }

    // ---------------------------------------------------------------- discovery (D75)
    private JSONArray discoverAlpaca(int ms) throws Exception {
        JSONArray out = new JSONArray();
        WifiManager wm = act.getApplicationContext().getSystemService(WifiManager.class);
        WifiManager.MulticastLock lock = wm.createMulticastLock("StarTracker:discovery");
        lock.acquire();
        try (DatagramSocket s = new DatagramSocket()) {
            s.setBroadcast(true);
            byte[] q = "alpacadiscovery1".getBytes(StandardCharsets.US_ASCII);
            s.send(new DatagramPacket(q, q.length, InetAddress.getByName("255.255.255.255"), 32227));
            s.setSoTimeout(300);
            long end = System.currentTimeMillis() + ms;
            byte[] buf = new byte[512];
            while (System.currentTimeMillis() < end) {
                DatagramPacket p = new DatagramPacket(buf, buf.length);
                try { s.receive(p); } catch (SocketTimeoutException e) { continue; }
                try {
                    JSONObject j = new JSONObject(new String(p.getData(), 0, p.getLength(), StandardCharsets.UTF_8));
                    if (j.has("AlpacaPort")) out.put(new JSONObject().put("host", p.getAddress().getHostAddress()).put("port", j.getInt("AlpacaPort")));
                } catch (Exception ignored) { /* not an Alpaca answer */ }
            }
        } finally { lock.release(); }
        return out;
    }

    private JSONArray discoverMdns(int ms) throws Exception {
        NsdManager nsd = act.getSystemService(NsdManager.class);
        JSONArray out = new JSONArray();
        CountDownLatch done = new CountDownLatch(1);
        NsdManager.DiscoveryListener l = new NsdManager.DiscoveryListener() {
            @Override public void onStartDiscoveryFailed(String t, int e) { done.countDown(); }
            @Override public void onStopDiscoveryFailed(String t, int e) { }
            @Override public void onDiscoveryStarted(String t) { }
            @Override public void onDiscoveryStopped(String t) { }
            @Override public void onServiceLost(NsdServiceInfo s) { }
            @Override @SuppressWarnings("deprecation") public void onServiceFound(NsdServiceInfo s) {
                nsd.resolveService(s, new NsdManager.ResolveListener() {
                    @Override public void onResolveFailed(NsdServiceInfo i, int e) { }
                    @Override public void onServiceResolved(NsdServiceInfo i) {
                        try { synchronized (out) { out.put(new JSONObject().put("host", i.getHost().getHostAddress()).put("port", i.getPort())); } } catch (Exception ignored) { }
                    }
                });
            }
        };
        nsd.discoverServices("_startracker._tcp", NsdManager.PROTOCOL_DNS_SD, l);
        done.await(ms, TimeUnit.MILLISECONDS);
        try { nsd.stopServiceDiscovery(l); } catch (Exception ignored) { }
        return out;
    }

    // ---------------------------------------------------------------- BLE first set-up (app/shared/ble.js)
    @SuppressLint("MissingPermission")
    private JSONArray bleScan(int ms) throws Exception {
        BluetoothAdapter ad = act.getSystemService(BluetoothManager.class).getAdapter();
        if (ad == null || !ad.isEnabled()) throw new Exception("Bluetooth is off");
        JSONArray out = new JSONArray();
        Map<String, Boolean> seen = new ConcurrentHashMap<>();
        ScanCallback cb = new ScanCallback() {
            @Override public void onScanResult(int type, ScanResult r) {
                String name = r.getScanRecord() != null ? r.getScanRecord().getDeviceName() : null;
                if (name == null) name = r.getDevice().getName();
                boolean svc = r.getScanRecord() != null && r.getScanRecord().getServiceUuids() != null && r.getScanRecord().getServiceUuids().contains(new ParcelUuid(SERVICE));
                if ((name != null && name.startsWith("Canopus-")) || svc) {
                    if (seen.putIfAbsent(r.getDevice().getAddress(), true) == null) {
                        try { synchronized (out) { out.put(new JSONObject().put("id", r.getDevice().getAddress()).put("name", name == null ? r.getDevice().getAddress() : name).put("rssi", r.getRssi())); } } catch (Exception ignored) { }
                    }
                }
            }
        };
        ad.getBluetoothLeScanner().startScan(cb);
        Thread.sleep(ms);
        ad.getBluetoothLeScanner().stopScan(cb);
        return out;
    }

    @SuppressLint("MissingPermission")
    private void bleConnect(String id) throws Exception {
        BluetoothDevice d = act.getSystemService(BluetoothManager.class).getAdapter().getRemoteDevice(id);
        CountDownLatch ready = new CountDownLatch(1);
        BluetoothGatt g = d.connectGatt(act, false, new BluetoothGattCallback() {
            @Override public void onConnectionStateChange(BluetoothGatt gatt, int status, int state) {
                if (state == BluetoothProfile.STATE_CONNECTED) gatt.discoverServices();
                else ready.countDown();
            }
            @Override public void onServicesDiscovered(BluetoothGatt gatt, int status) { ready.countDown(); }
            @Override public void onCharacteristicWrite(BluetoothGatt gatt, BluetoothGattCharacteristic c, int status) { finish(id, status == BluetoothGatt.GATT_SUCCESS ? "ok" : null); }
            @Override @SuppressWarnings("deprecation") public void onCharacteristicRead(BluetoothGatt gatt, BluetoothGattCharacteristic c, int status) {
                finish(id, status == BluetoothGatt.GATT_SUCCESS ? new String(c.getValue(), StandardCharsets.UTF_8) : null);
            }
        }, BluetoothDevice.TRANSPORT_LE);
        if (!ready.await(20, TimeUnit.SECONDS) || g.getService(SERVICE) == null) { g.close(); throw new Exception("could not open the head's set-up service"); }
        // pairing: the head asks for authentication; Android shows its dialog and you type the code on the OLED
        if (d.getBondState() == BluetoothDevice.BOND_NONE) d.createBond();
        gatts.put(id, g);
    }

    private void finish(String id, String value) {
        Object[] p = pendingIo.get(id);
        if (p != null) { p[1] = value; ((CountDownLatch) p[0]).countDown(); }
    }

    @SuppressLint("MissingPermission")
    @SuppressWarnings("deprecation")
    private void bleWrite(String id, String ch, String text) throws Exception {
        BluetoothGatt g = gatts.get(id);
        if (g == null) throw new Exception("not paired: press Pair first");
        BluetoothGattService s = g.getService(SERVICE);
        BluetoothGattCharacteristic c = s.getCharacteristic(UUID.fromString(ch));
        for (int attempt = 0; attempt < 6; attempt++) {           // the first write may wait for the pairing dialog
            Object[] p = {new CountDownLatch(1), null};
            pendingIo.put(id, p);
            c.setValue(text.getBytes(StandardCharsets.UTF_8));
            c.setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT);
            g.writeCharacteristic(c);
            if (((CountDownLatch) p[0]).await(10, TimeUnit.SECONDS) && p[1] != null) return;
            Thread.sleep(2000);
        }
        throw new Exception("the head did not accept the data: check the pairing code");
    }

    @SuppressLint("MissingPermission")
    private String bleRead(String id, String ch) throws Exception {
        BluetoothGatt g = gatts.get(id);
        if (g == null) throw new Exception("not paired");
        Object[] p = {new CountDownLatch(1), null};
        pendingIo.put(id, p);
        g.readCharacteristic(g.getService(SERVICE).getCharacteristic(UUID.fromString(ch)));
        if (!((CountDownLatch) p[0]).await(10, TimeUnit.SECONDS) || p[1] == null) throw new Exception("no answer from the head");
        return (String) p[1];
    }

    // ---------------------------------------------------------------- the rest
    private void notifyUser(String title, String text) {
        NotificationManager nm = act.getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= 26) nm.createNotificationChannel(new NotificationChannel("alerts", "Job alerts", NotificationManager.IMPORTANCE_HIGH));
        nm.notify((int) (System.currentTimeMillis() & 0xFFFF), new Notification.Builder(act, "alerts").setSmallIcon(R.drawable.ic_stat).setContentTitle(title).setContentText(text).build());
    }

    @SuppressLint("MissingPermission")
    private JSONObject location() throws Exception {
        LocationManager lm = act.getSystemService(LocationManager.class);
        Location best = null;
        for (String p : lm.getProviders(true)) {
            Location l = lm.getLastKnownLocation(p);
            if (l != null && (best == null || l.getTime() > best.getTime())) best = l;
        }
        if (best == null) throw new Exception("no location yet: switch location on and try again outdoors");
        return new JSONObject().put("lat", best.getLatitude()).put("lon", best.getLongitude()).put("elev_m", best.hasAltitude() ? best.getAltitude() : 0);
    }
}
