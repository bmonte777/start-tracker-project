package pt.brunomonte.startracker.camera;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * One CSV line per photo in Documents/Star Tracker/shot-log-YYYY-MM-DD.csv:
 * time, job, file, shutter, aperture, ISO, where the head pointed. Opens
 * in a spreadsheet and helps sort the frames out later (panorama panels,
 * timelapse settings, what was shot where).
 */
final class ShotLog {

    private static final String FOLDER = Environment.DIRECTORY_DOCUMENTS + "/Canopus/";
    private static final String HEADER = "time,job,step,file,shutter,aperture,iso,polaris_azimuth,polaris_altitude\n";

    private ShotLog() {
    }

    static synchronized void add(Context ctx, String job, String step, String file, String shutter,
                                 String aperture, String iso, double az, double alt) {
        try {
            Date now = new Date();
            String name = "shot-log-" + new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(now) + ".csv";
            ContentResolver cr = ctx.getContentResolver();
            Uri files = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
            Uri uri = null;
            try (Cursor c = cr.query(files, new String[]{MediaStore.MediaColumns._ID},
                    MediaStore.MediaColumns.RELATIVE_PATH + "=? AND " + MediaStore.MediaColumns.DISPLAY_NAME + "=?",
                    new String[]{FOLDER, name}, null)) {
                if (c != null && c.moveToFirst()) uri = Uri.withAppendedPath(files, String.valueOf(c.getLong(0)));
            }
            boolean fresh = uri == null;
            if (fresh) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                v.put(MediaStore.MediaColumns.MIME_TYPE, "text/csv");
                v.put(MediaStore.MediaColumns.RELATIVE_PATH, FOLDER);
                uri = cr.insert(files, v);
                if (uri == null) return;
            }
            String line = csv(new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ROOT).format(now)) + ","
                    + csv(job) + "," + csv(step) + "," + csv(file) + "," + csv(shutter) + "," + csv(aperture) + ","
                    + csv(iso) + "," + num(az) + "," + num(alt) + "\n";
            try (OutputStream os = cr.openOutputStream(uri, "wa")) {
                if (os == null) return;
                if (fresh) os.write(HEADER.getBytes(StandardCharsets.UTF_8));
                os.write(line.getBytes(StandardCharsets.UTF_8));
            }
        } catch (Exception ignored) {
            // The log is a convenience; a failure must never stop the shooting.
        }
    }

    private static String num(double v) {
        return Double.isNaN(v) ? "" : String.format(Locale.ROOT, "%.2f", v);
    }

    private static String csv(String s) {
        if (s == null) return "";
        return s.matches(".*[,\"\n].*") ? "\"" + s.replace("\"", "\"\"") + "\"" : s;
    }
}
