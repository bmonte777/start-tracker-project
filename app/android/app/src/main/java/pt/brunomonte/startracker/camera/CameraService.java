package pt.brunomonte.startracker.camera;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;


import pt.brunomonte.startracker.MainActivity;
import pt.brunomonte.startracker.R;

/**
 * Keeps the app awake while a camera job (interval or panorama) runs, so
 * it continues with the screen off. Started and stopped by SonyCamera.
 */
public class CameraService extends Service {

    private static final String ACTION_STOP_JOB = "pt.brunomonte.startracker.camera.STOP_JOB";
    private static final String EXTRA_JOB = "job";
    private static final String CHANNEL = "camera";
    private static final int NOTIFICATION_ID = 8;

    private PowerManager.WakeLock wakeLock;
    private android.net.wifi.WifiManager.WifiLock wifiLock;   // keeps the link to the head up with the screen off (Phase 6)

    public static void start(Context ctx, String job) {
        Intent i = new Intent(ctx, CameraService.class).putExtra(EXTRA_JOB, job);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) ctx.startForegroundService(i);
            else ctx.startService(i);
        } catch (Exception ignored) {
            // Started from the background on a restricted device: the job still runs.
        }
    }

    public static void stop(Context ctx) {
        ctx.stopService(new Intent(ctx, CameraService.class));
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP_JOB.equals(intent.getAction())) {
            SonyCamera.get(this).stopJob();
            return START_NOT_STICKY;
        }
        String job = intent != null ? intent.getStringExtra(EXTRA_JOB) : null;
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Camera jobs", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Shown while the camera is shooting an interval or panorama");
            nm.createNotificationChannel(ch);
        }
        int immutable = PendingIntent.FLAG_IMMUTABLE;
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), immutable);
        PendingIntent stop = PendingIntent.getService(this, 1,
                new Intent(this, CameraService.class).setAction(ACTION_STOP_JOB), immutable);
        Notification n = new Notification.Builder(this, CHANNEL)
                .setSmallIcon(R.drawable.ic_stat)
                .setContentTitle((job == null ? "Star Tracker job" : job))
                .setContentText("Keeps the job and the link to the head running with the screen off")
                .setOngoing(true)
                .setContentIntent(open)
                .addAction(new Notification.Action.Builder(null, "Stop", stop).build())
                .build();
        startForeground(NOTIFICATION_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        if (wakeLock == null) {
            PowerManager pm = getSystemService(PowerManager.class);
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "StarTracker:Camera");
            wakeLock.acquire(12 * 60 * 60 * 1000L);
        }
        if (wifiLock == null) {
            android.net.wifi.WifiManager wm = getApplicationContext().getSystemService(android.net.wifi.WifiManager.class);
            wifiLock = wm.createWifiLock(Build.VERSION.SDK_INT >= 29 ? android.net.wifi.WifiManager.WIFI_MODE_FULL_HIGH_PERF
                    : android.net.wifi.WifiManager.WIFI_MODE_FULL, "StarTracker:Head");
            wifiLock.acquire();
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        if (wifiLock != null && wifiLock.isHeld()) wifiLock.release();
        super.onDestroy();
    }
}
