package pt.brunomonte.startracker.camera;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Sony camera properties as read with SDIO GetAllExtDevicePropInfo
 * (operation 0x9209), and how to show them. Property codes and value
 * encodings follow libgphoto2's Sony support.
 *
 * Plain Java, no Android classes, so it can be tested off-device.
 */
final class SonyProps {

    static final int WHITE_BALANCE = 0x5005;
    static final int F_NUMBER = 0x5007;
    static final int FOCUS_MODE = 0x500A;
    static final int EXPOSURE_PROGRAM = 0x500E;
    static final int EXPOSURE_COMP = 0x5010;
    static final int COLOR_TEMP = 0xD20F;
    static final int SHUTTER = 0xD20D;
    static final int OBJECT_IN_MEMORY = 0xD215;
    static final int BATTERY = 0xD218;
    static final int ISO = 0xD21E;
    static final int SAVE_DESTINATION = 0xD222;
    static final int AUTOFOCUS_BUTTON = 0xD2C1;
    static final int SHUTTER_BUTTON = 0xD2C2;
    /** Movie record button: 2 starts recording, 1 stops (as libgphoto2). */
    static final int MOVIE_BUTTON = 0xD2C8;
    /** Manual focus drive: -7…+7, sign = near/far, size = step (libgphoto2 "manualfocus"). */
    static final int NEAR_FAR = 0xD2D1;

    /** Save destination values (libgphoto2 "capturetarget"). */
    static final int DEST_TABLET = 0x01;
    static final int DEST_CARD = 0x10;
    static final int DEST_BOTH = 0x11;

    static final int TYPE_STRING = 0xFFFF;

    static final class Prop {
        int code;
        int type;
        boolean writable;
        boolean enabled;
        long value;
        String text;
        List<Long> choices = new ArrayList<>();
    }

    final Map<Integer, Prop> props = new LinkedHashMap<>();
    /** Set when parsing stopped early; the properties before it are kept. */
    String parseProblem;

    static SonyProps parse(byte[] data) {
        SonyProps sp = new SonyProps();
        ByteBuffer b = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
        if (data.length < 8) {
            sp.parseProblem = "empty property list";
            return sp;
        }
        long count = b.getLong();
        for (long i = 0; i < count && b.remaining() > 0; i++) {
            int start = b.position();
            try {
                Prop p = readProp(b);
                sp.props.put(p.code, p);
            } catch (RuntimeException e) {
                sp.parseProblem = String.format(Locale.ROOT, "stopped at entry %d (offset %d): %s", i, start, e);
                break;
            }
        }
        return sp;
    }

    private static Prop readProp(ByteBuffer b) {
        Prop p = new Prop();
        p.code = b.getShort() & 0xFFFF;
        p.type = b.getShort() & 0xFFFF;
        p.writable = b.get() != 0;
        p.enabled = b.get() != 0;
        skipValue(b, p.type);                       // factory default
        if (p.type == TYPE_STRING) {
            p.text = readString(b);
        } else {
            p.value = readNumber(b, p.type);
        }
        int form = b.get() & 0xFF;
        if (form == 1) {                            // range: min, max, step
            for (int k = 0; k < 3; k++) skipValue(b, p.type);
        } else if (form == 2) {                     // enumeration
            readEnum(b, p);
            // Newer Sony protocols send a second list (values that can be
            // set, after values that can be read). Read it only when the
            // bytes after the first list do not look like the next property.
            if (b.remaining() > 0 && !looksLikeProp(b, b.position())) {
                int mark = b.position();
                try {
                    Prop second = new Prop();
                    second.type = p.type;
                    readEnum(b, second);
                    if (b.remaining() == 0 || looksLikeProp(b, b.position())) {
                        p.choices = second.choices;
                    } else {
                        b.position(mark);
                    }
                } catch (RuntimeException e) {
                    b.position(mark);
                }
            }
        }
        return p;
    }

    private static void readEnum(ByteBuffer b, Prop p) {
        int n = b.getShort() & 0xFFFF;
        List<Long> list = new ArrayList<>(n);
        for (int k = 0; k < n; k++) {
            if (p.type == TYPE_STRING) {
                readString(b);
            } else {
                list.add(readNumber(b, p.type));
            }
        }
        p.choices = list;
    }

    static boolean looksLikeProp(ByteBuffer b, int off) {
        if (off + 6 > b.limit()) return false;
        int code = b.getShort(off) & 0xFFFF;
        int type = b.getShort(off + 2) & 0xFFFF;
        boolean codeOk = (code >= 0x5000 && code <= 0x5FFF) || (code >= 0xD000 && code <= 0xDFFF);
        boolean typeOk = (type >= 1 && type <= 10) || (type >= 0x4001 && type <= 0x400A) || type == TYPE_STRING;
        return codeOk && typeOk;
    }

    private static int size(int type) {
        switch (type & 0xFFF) {
            case 1: case 2: return 1;
            case 3: case 4: return 2;
            case 5: case 6: return 4;
            case 7: case 8: return 8;
            case 9: case 10: return 16;
            default: throw new IllegalArgumentException("unknown data type 0x" + Integer.toHexString(type));
        }
    }

    private static void skipValue(ByteBuffer b, int type) {
        if (type == TYPE_STRING) {
            readString(b);
        } else if ((type & 0x4000) != 0) {
            int n = b.getInt();
            b.position(b.position() + n * size(type));
        } else {
            b.position(b.position() + size(type));
        }
    }

    private static long readNumber(ByteBuffer b, int type) {
        if ((type & 0x4000) != 0) {                 // arrays are skipped, value 0
            skipValue(b, type);
            return 0;
        }
        switch (type) {
            case 1: return b.get();
            case 2: return b.get() & 0xFF;
            case 3: return b.getShort();
            case 4: return b.getShort() & 0xFFFF;
            case 5: return b.getInt();
            case 6: return b.getInt() & 0xFFFFFFFFL;
            case 7: case 8: return b.getLong();
            default:
                b.position(b.position() + size(type));
                return 0;
        }
    }

    /** PTP string: character count (including the final 0), then UTF-16LE. */
    static String readString(ByteBuffer b) {
        int n = b.get() & 0xFF;
        StringBuilder sb = new StringBuilder();
        for (int k = 0; k < n; k++) {
            char c = (char) (b.getShort() & 0xFFFF);
            if (c != 0) sb.append(c);
        }
        return sb.toString();
    }

    long get(int code, long fallback) {
        Prop p = props.get(code);
        return p == null ? fallback : p.value;
    }

    // ---------------------------------------------------------------------
    // Display
    // ---------------------------------------------------------------------

    static String format(int code, long v) {
        switch (code) {
            case SHUTTER: return shutter(v);
            case ISO: return iso(v);
            case F_NUMBER: return v == 0 ? "--" : String.format(Locale.ROOT, "f/%s", trim(v / 100.0));
            case BATTERY: return v < 0 ? "--" : v + "%";
            case EXPOSURE_PROGRAM: return program(v);
            case SAVE_DESTINATION: return destination(v);
            case EXPOSURE_COMP: return v == 0 ? "±0 EV" : String.format(Locale.ROOT, "%+.1f EV", v / 1000.0);
            case WHITE_BALANCE: return whiteBalance(v);
            case COLOR_TEMP: return v + " K";
            case FOCUS_MODE: return focusMode(v);
            default: return "0x" + Long.toHexString(v);
        }
    }

    static boolean isBulb(long shutter) {
        return shutter == 0;
    }

    static String shutter(long v) {
        if (v == 0) return "BULB";
        long num = (v >> 16) & 0xFFFF, den = v & 0xFFFF;
        if (den == 0) return "0x" + Long.toHexString(v);
        if (num == 1 && den > 1) return "1/" + den;
        return trim((double) num / den) + "\"";
    }

    static String iso(long v) {
        long iso = v & 0xFFFFFF;
        if (iso == 0xFFFFFF || iso == 0) return "ISO AUTO";
        return "ISO " + iso;
    }

    static String program(long v) {
        switch ((int) v) {
            case 1: return "M";
            case 2: return "P";
            case 3: return "A";
            case 4: return "S";
            default: return "mode 0x" + Long.toHexString(v);
        }
    }

    /** White balance names, as in libgphoto2's Sony table. */
    static String whiteBalance(long v) {
        switch ((int) v) {
            case 0x0002: return "Auto";
            case 0x0004: return "Daylight";
            case 0x8011: return "Shade";
            case 0x8010: return "Cloudy";
            case 0x0006: return "Tungsten";
            case 0x8001: return "Fluor. warm white";
            case 0x8002: return "Fluor. cool white";
            case 0x8003: return "Fluor. day white";
            case 0x8004: return "Fluor. daylight";
            case 0x0007: return "Flash";
            case 0x8012: return "Colour temp.";
            case 0x8020: return "Custom 1";
            case 0x8021: return "Custom 2";
            case 0x8022: return "Custom 3";
            case 0x8023: return "Custom";
            case 0x8030: return "Underwater auto";
            default: return "WB 0x" + Long.toHexString(v);
        }
    }

    static String focusMode(long v) {
        switch ((int) v) {
            case 0x0001: return "MF";
            case 0x0002: return "AF-S";
            case 0x8004: return "AF-C";
            case 0x8005: return "AF-A";
            case 0x8006: return "DMF";
            default: return "focus 0x" + Long.toHexString(v);
        }
    }

    static String destination(long v) {
        switch ((int) v) {
            case DEST_TABLET: return "Tablet only";
            case DEST_CARD: return "Camera card";
            case DEST_BOTH: return "Card + tablet";
            default: return "0x" + Long.toHexString(v);
        }
    }

    private static String trim(double d) {
        if (d == Math.rint(d)) return String.valueOf((long) d);
        return String.format(Locale.ROOT, "%.1f", d);
    }
}
