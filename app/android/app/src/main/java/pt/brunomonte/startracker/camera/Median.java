package pt.brunomonte.startracker.camera;

import android.content.ContentResolver;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.BitmapRegionDecoder;
import android.graphics.Rect;
import android.net.Uri;
import android.os.Build;
import android.os.ParcelFileDescriptor;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * People Remover merge: for each pixel, the median of the same pixel in
 * every shot of a burst, so anything that moves between shots (people,
 * cars) disappears and the still scene stays. Works in horizontal strips,
 * decoding only that strip of each JPEG, so a 61 MP burst fits in memory.
 * sample 2 gives a quarter-size (half width and height) result.
 */
final class Median {

    interface Progress {
        void at(int percent);
    }

    private Median() {
    }

    @SuppressWarnings("deprecation")
    private static BitmapRegionDecoder open(ParcelFileDescriptor pfd) throws IOException {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) return BitmapRegionDecoder.newInstance(pfd);
        return BitmapRegionDecoder.newInstance(pfd.getFileDescriptor(), false);
    }

    static Bitmap merge(ContentResolver cr, List<Uri> jpegs, int sample, Progress progress) throws IOException {
        int n = jpegs.size();
        if (n < 3) throw new IOException("People Remover needs at least 3 JPEG shots");
        List<ParcelFileDescriptor> files = new ArrayList<>();
        List<BitmapRegionDecoder> decoders = new ArrayList<>();
        try {
            for (Uri u : jpegs) {
                ParcelFileDescriptor pfd = cr.openFileDescriptor(u, "r");
                if (pfd == null) throw new IOException("Cannot open " + u);
                files.add(pfd);
                decoders.add(open(pfd));
            }
            int w = decoders.get(0).getWidth(), h = decoders.get(0).getHeight();
            for (BitmapRegionDecoder d : decoders) {
                if (d.getWidth() != w || d.getHeight() != h) throw new IOException("The shots have different sizes");
            }
            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inSampleSize = sample;
            opts.inPreferredConfig = Bitmap.Config.ARGB_8888;
            int outW = (w + sample - 1) / sample, outH = (h + sample - 1) / sample;
            Bitmap out = Bitmap.createBitmap(outW, outH, Bitmap.Config.ARGB_8888);
            int stripRows = 64 * sample;
            int[][] px = new int[n][];
            int[] r = new int[n], g = new int[n], b = new int[n];
            int yOut = 0;
            for (int y0 = 0; y0 < h; y0 += stripRows) {
                Rect rect = new Rect(0, y0, w, Math.min(h, y0 + stripRows));
                int bw = 0, bh = 0;
                for (int k = 0; k < n; k++) {
                    Bitmap strip = decoders.get(k).decodeRegion(rect, opts);
                    bw = strip.getWidth();
                    bh = strip.getHeight();
                    if (px[k] == null || px[k].length < bw * bh) px[k] = new int[bw * bh];
                    strip.getPixels(px[k], 0, bw, 0, 0, bw, bh);
                    strip.recycle();
                }
                bh = Math.min(bh, outH - yOut);
                int[] merged = new int[bw * bh];
                for (int i = 0; i < bw * bh; i++) {
                    for (int k = 0; k < n; k++) {
                        int c = px[k][i];
                        r[k] = (c >> 16) & 0xFF;
                        g[k] = (c >> 8) & 0xFF;
                        b[k] = c & 0xFF;
                    }
                    merged[i] = 0xFF000000 | (median(r, n) << 16) | (median(g, n) << 8) | median(b, n);
                }
                out.setPixels(merged, 0, bw, 0, yOut, Math.min(bw, outW), bh);
                yOut += bh;
                if (progress != null) progress.at((int) (100L * Math.min(h, y0 + stripRows) / h));
                if (yOut >= outH) break;
            }
            return out;
        } finally {
            for (BitmapRegionDecoder d : decoders) d.recycle();
            for (ParcelFileDescriptor f : files) {
                try {
                    f.close();
                } catch (IOException ignored) {
                }
            }
        }
    }

    /** Median of the first n values (insertion sort; n is small). Reorders a. */
    static int median(int[] a, int n) {
        for (int i = 1; i < n; i++) {
            int v = a[i], j = i - 1;
            while (j >= 0 && a[j] > v) {
                a[j + 1] = a[j];
                j--;
            }
            a[j + 1] = v;
        }
        return a[n / 2];
    }
}
