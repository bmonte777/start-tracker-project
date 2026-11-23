package pt.brunomonte.startracker.camera;

import android.app.Activity;
import android.content.ContentUris;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.net.Uri;
import android.provider.MediaStore;
import android.util.Base64;
import android.util.Size;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;

/**
 * The pictures downloaded from the camera (Pictures/Star Tracker,
 * plus Pictures/Polaris Suite from before the app was renamed), newest first,
 * with thumbnails, opened in the tablet's photo viewer.
 */
final class Gallery {

    private static final String FOLDER = "Pictures/Star Tracker/";
    private static final String OLD_FOLDER = "Pictures/Polaris Suite/";

    private final Activity a;

    Gallery(Activity a) {
        this.a = a;
    }

    private static Uri collection() {
        return MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY);
    }

    /** JSON array of {id, name, size, date (ms), mime}, newest first, at most 500. */
    String list() {
        JSONArray out = new JSONArray();
        String[] cols = {MediaStore.MediaColumns._ID, MediaStore.MediaColumns.DISPLAY_NAME,
                MediaStore.MediaColumns.SIZE, MediaStore.MediaColumns.DATE_ADDED, MediaStore.MediaColumns.MIME_TYPE};
        try (Cursor c = a.getContentResolver().query(collection(), cols,
                "(" + MediaStore.MediaColumns.RELATIVE_PATH + " = ? OR " + MediaStore.MediaColumns.RELATIVE_PATH + " = ?) AND "
                        + MediaStore.MediaColumns.IS_PENDING + " = 0",
                new String[]{FOLDER, OLD_FOLDER}, MediaStore.MediaColumns.DATE_ADDED + " DESC")) {
            while (c != null && c.moveToNext() && out.length() < 500) {
                JSONObject o = new JSONObject();
                o.put("id", c.getLong(0));
                o.put("name", c.getString(1));
                o.put("size", c.getLong(2));
                o.put("date", c.getLong(3) * 1000);
                o.put("mime", c.getString(4));
                out.put(o);
            }
        } catch (Exception e) {
            return "[]";
        }
        return out.toString();
    }

    /** Small JPEG thumbnail as base64, or "" (RAW files the tablet cannot preview). */
    String thumb(long id) {
        try {
            Bitmap b = a.getContentResolver().loadThumbnail(ContentUris.withAppendedId(collection(), id),
                    new Size(320, 320), null);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            b.compress(Bitmap.CompressFormat.JPEG, 80, out);
            return Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP);
        } catch (Exception e) {
            return "";
        }
    }

    /** Opens the picture in the tablet's viewer (or an app that handles the file). */
    String open(long id, String mime) {
        try {
            Uri uri = ContentUris.withAppendedId(collection(), id);
            Intent i = new Intent(Intent.ACTION_VIEW).setDataAndType(uri, mime)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            a.startActivity(Intent.createChooser(i, "Open with"));
            return "ok";
        } catch (Exception e) {
            return String.valueOf(e.getMessage());
        }
    }
}
