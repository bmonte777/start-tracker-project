package pt.brunomonte.startracker.camera;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;

import pt.brunomonte.startracker.MainActivity;
import pt.brunomonte.startracker.R;

/**
 * Tells the user when a camera job ends by itself: done, or failed (camera
 * unplugged, card full, Polaris not answering…). A separate, audible channel
 * from the quiet "shooting" notification, so it is heard with the screen off.
 * Jobs stopped with the Stop button raise no alert.
 */
final class JobAlerts {

    private static final String CHANNEL = "job-alerts";
    private static int nextId = 100;

    private JobAlerts() {
    }

    static void done(Context ctx, String job, String warning) {
        String text = warning == null || warning.isEmpty() ? "Finished." : "Finished, with a warning: " + warning;
        post(ctx, job + " done", text);
    }

    static void failed(Context ctx, String job, String error) {
        post(ctx, job + " stopped by a problem", error == null || error.isEmpty() ? "See the camera log." : error);
    }

    private static synchronized void post(Context ctx, String title, String text) {
        try {
            NotificationManager nm = ctx.getSystemService(NotificationManager.class);
            NotificationChannel ch = new NotificationChannel(CHANNEL, "Job finished or failed", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("Sound and vibration when an interval, panorama or other camera job ends");
            ch.enableVibration(true);
            nm.createNotificationChannel(ch);
            PendingIntent open = PendingIntent.getActivity(ctx, 0,
                    new Intent(ctx, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK), PendingIntent.FLAG_IMMUTABLE);
            Notification n = new Notification.Builder(ctx, CHANNEL)
                    .setSmallIcon(R.drawable.ic_stat)
                    .setContentTitle(title)
                    .setContentText(text)
                    .setStyle(new Notification.BigTextStyle().bigText(text))
                    .setContentIntent(open)
                    .setAutoCancel(true)
                    .setCategory(Notification.CATEGORY_STATUS)
                    .build();
            nm.notify(nextId++, n);
        } catch (Exception ignored) {
            // No notification permission: the result is still in the camera log.
        }
    }
}
