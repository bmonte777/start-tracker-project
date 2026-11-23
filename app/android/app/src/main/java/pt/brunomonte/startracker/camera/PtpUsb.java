package pt.brunomonte.startracker.camera;

import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbRequest;
import android.os.SystemClock;
import android.os.Build;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.concurrent.TimeoutException;

/**
 * PTP (Picture Transfer Protocol) over USB: the standard way cameras are
 * controlled by a computer. Each operation is a command container, an
 * optional data phase in either direction, and a response container,
 * all little-endian, on the camera's bulk endpoints.
 */
final class PtpUsb {

    static final int OK = 0x2001;
    static final int DEVICE_BUSY = 0x2019;

    private static final int TYPE_COMMAND = 1;
    private static final int TYPE_DATA = 2;
    private static final int TYPE_RESPONSE = 3;
    private static final int TIMEOUT_MS = 5000;

    // PTP still-image class requests (USB Still Image Capture Device spec)
    private static final int REQ_CANCEL = 0x64;
    private static final int REQ_DEVICE_RESET = 0x66;
    private static final int REQ_GET_DEVICE_STATUS = 0x67;

    static final class Response {
        int code;
        int[] params = new int[0];
        byte[] data = new byte[0];

        boolean ok() {
            return code == OK;
        }
    }

    private final UsbDeviceConnection conn;
    private final UsbInterface intf;
    private final UsbEndpoint in;
    private final UsbEndpoint out;
    private final int maxPacket;
    private final byte[] readBuf;
    private int transactionId;

    // How the camera's replies are read. Some Android kernels refuse large
    // single bulk reads at once (-1 with no wait), so the size steps down
    // to 16 KB, then one USB packet, then to queued USB requests.
    private int readSize;
    private boolean useRequests;
    private UsbRequest request;
    private final StringBuilder readNotes = new StringBuilder();

    private PtpUsb(UsbDeviceConnection conn, UsbInterface intf, UsbEndpoint in, UsbEndpoint out) {
        this.conn = conn;
        this.intf = intf;
        this.in = in;
        this.out = out;
        this.maxPacket = out.getMaxPacketSize();
        // Before Android 9 a bulk transfer is limited to 16 KB.
        this.readBuf = new byte[Build.VERSION.SDK_INT >= Build.VERSION_CODES.P ? 512 * 1024 : 16 * 1024];
        this.readSize = readBuf.length;
    }

    /** How replies are being read, and any fallbacks taken, for the diagnostics log. */
    String readMode() {
        String mode = useRequests ? "queued USB requests" : "bulk reads of " + readSize + " bytes";
        return readNotes.length() == 0 ? mode : mode + " (" + readNotes + ")";
    }

    /**
     * One read from the camera's bulk-in endpoint into readBuf. Returns the
     * byte count, or -1 on timeout or error. A failure that comes back at
     * once (not after the timeout) means this read size or method is not
     * accepted here, so the next one down is tried.
     */
    private int bulkIn(int timeoutMs) {
        while (true) {
            long t0 = SystemClock.elapsedRealtime();
            int n = useRequests ? requestIn(timeoutMs) : conn.bulkTransfer(in, readBuf, readSize, timeoutMs);
            long took = SystemClock.elapsedRealtime() - t0;
            if (n >= 0 || took >= Math.min(timeoutMs, 1000) / 2) return n;
            if (useRequests) return n;
            if (readNotes.length() > 0) readNotes.append(", ");
            readNotes.append(readSize).append(" B refused in ").append(took).append(" ms");
            if (readSize > 16 * 1024) readSize = 16 * 1024;
            else if (readSize > maxPacket) readSize = maxPacket;
            else useRequests = true;
        }
    }

    /** A read through the asynchronous UsbRequest API. */
    private int requestIn(int timeoutMs) {
        try {
            if (request == null) {
                request = new UsbRequest();
                if (!request.initialize(conn, in)) {
                    request = null;
                    return -1;
                }
            }
            ByteBuffer bb = ByteBuffer.wrap(readBuf, 0, 16 * 1024);
            if (!request.queue(bb)) return -1;
            UsbRequest done = conn.requestWait(timeoutMs);
            if (done != request) return -1;
            return bb.position();
        } catch (TimeoutException e) {
            request.cancel();
            return -1;
        } catch (Exception e) {
            return -1;
        }
    }

    /** The still-image (PTP) interface of a USB device, or null. */
    static UsbInterface findPtpInterface(UsbDevice device) {
        for (int i = 0; i < device.getInterfaceCount(); i++) {
            UsbInterface it = device.getInterface(i);
            if (it.getInterfaceClass() == UsbConstants.USB_CLASS_STILL_IMAGE) return it;
        }
        return null;
    }

    /** Claims the camera's PTP interface. Throws if it has none. */
    static PtpUsb open(UsbDeviceConnection conn, UsbDevice device) throws IOException {
        UsbInterface intf = findPtpInterface(device);
        if (intf == null) throw new IOException("Not a PTP camera (is USB mode set to PC Remote?)");
        UsbEndpoint in = null, out = null;
        for (int i = 0; i < intf.getEndpointCount(); i++) {
            UsbEndpoint e = intf.getEndpoint(i);
            if (e.getType() != UsbConstants.USB_ENDPOINT_XFER_BULK) continue;
            if (e.getDirection() == UsbConstants.USB_DIR_IN) in = e;
            else out = e;
        }
        if (in == null || out == null) throw new IOException("Camera has no bulk endpoints");
        if (!conn.claimInterface(intf, true)) throw new IOException("Could not claim the camera's USB interface");
        return new PtpUsb(conn, intf, in, out);
    }

    /** Endpoint addresses and interface, for the diagnostics log. */
    String describe() {
        return String.format(java.util.Locale.ROOT, "interface %d, in 0x%02x, out 0x%02x, packet %d",
                intf.getId(), in.getAddress(), out.getAddress(), maxPacket);
    }

    /**
     * The camera's PTP status (0x2001 = OK, 0x2019 = busy), or -1 if it
     * did not answer the request.
     */
    int deviceStatus() {
        byte[] b = new byte[16];
        int n = conn.controlTransfer(0xA1, REQ_GET_DEVICE_STATUS, 0, intf.getId(), b, b.length, 1000);
        if (n < 4) return -1;
        return (b[2] & 0xFF) | ((b[3] & 0xFF) << 8);
    }

    /**
     * Brings a camera left in a half-finished transfer (for example by
     * another computer or app) back to a clean state: cancels the pending
     * transaction, resets the PTP device, clears stalled endpoints and
     * throws away any reply still waiting to be read.
     */
    void recover() {
        byte[] cancel = ByteBuffer.allocate(6).order(ByteOrder.LITTLE_ENDIAN)
                .putShort((short) 0x4001).putInt(transactionId).array();
        conn.controlTransfer(0x21, REQ_CANCEL, 0, intf.getId(), cancel, cancel.length, 1000);
        conn.controlTransfer(0x21, REQ_DEVICE_RESET, 0, intf.getId(), null, 0, 2000);
        clearHalt(in);
        clearHalt(out);
        drain();
        startSession();
    }

    /** OpenSession goes out with transaction ID 0, as the PTP standard asks. */
    void startSession() {
        transactionId = -1;
    }

    private void clearHalt(UsbEndpoint e) {
        // CLEAR_FEATURE(ENDPOINT_HALT) on the endpoint
        conn.controlTransfer(0x02, 0x01, 0, e.getAddress(), null, 0, 1000);
    }

    /** Reads and discards anything the camera still has queued. */
    int drain() {
        int total = 0;
        for (int i = 0; i < 64; i++) {
            int n = bulkIn(150);
            if (n <= 0) break;
            total += n;
        }
        return total;
    }

    void close() {
        if (request != null) {
            try {
                request.close();
            } catch (Exception ignored) {
            }
            request = null;
        }
        try {
            conn.releaseInterface(intf);
        } catch (Exception ignored) {
        }
        conn.close();
    }

    Response transact(int op, int... params) throws IOException {
        return transact(op, params, null, null);
    }

    /**
     * Runs one PTP operation. dataOut, if not null, is sent as the data
     * phase. Incoming data goes to sink if given, else into Response.data.
     */
    synchronized Response transact(int op, int[] params, byte[] dataOut, OutputStream sink) throws IOException {
        int tid = ++transactionId;
        ByteBuffer cmd = ByteBuffer.allocate(12 + 4 * params.length).order(ByteOrder.LITTLE_ENDIAN);
        cmd.putInt(12 + 4 * params.length).putShort((short) TYPE_COMMAND).putShort((short) op).putInt(tid);
        for (int p : params) cmd.putInt(p);
        write(cmd.array());

        if (dataOut != null) {
            ByteBuffer data = ByteBuffer.allocate(12 + dataOut.length).order(ByteOrder.LITTLE_ENDIAN);
            data.putInt(12 + dataOut.length).putShort((short) TYPE_DATA).putShort((short) op).putInt(tid);
            data.put(dataOut);
            write(data.array());
        }

        ByteArrayOutputStream collected = sink == null ? new ByteArrayOutputStream() : null;
        OutputStream dest = sink != null ? sink : collected;
        while (true) {
            int n = readPacket();
            ByteBuffer h = ByteBuffer.wrap(readBuf, 0, n).order(ByteOrder.LITTLE_ENDIAN);
            long length = h.getInt() & 0xFFFFFFFFL;
            int type = h.getShort() & 0xFFFF;
            int code = h.getShort() & 0xFFFF;
            h.getInt(); // transaction id

            if (type == TYPE_DATA) {
                long remaining = length - n;
                dest.write(readBuf, 12, n - 12);
                while (remaining > 0) {
                    int m = bulkIn(TIMEOUT_MS);
                    if (m < 0) throw new IOException("USB read failed during data phase");
                    if (m == 0) continue;
                    dest.write(readBuf, 0, m);
                    remaining -= m;
                }
            } else if (type == TYPE_RESPONSE) {
                Response r = new Response();
                r.code = code;
                int count = Math.max(0, (int) Math.min(5, (n - 12) / 4));
                r.params = new int[count];
                for (int i = 0; i < count; i++) r.params[i] = h.getInt();
                if (collected != null) r.data = collected.toByteArray();
                return r;
            } else {
                throw new IOException("Unexpected PTP container type " + type);
            }
        }
    }

    /** Reads one container's first packet, skipping zero-length packets. */
    private int readPacket() throws IOException {
        for (int tries = 0; tries < 4; tries++) {
            int n = bulkIn(TIMEOUT_MS);
            if (n < 0) throw new IOException("Camera did not answer (USB read timeout)");
            if (n >= 12) return n;
        }
        throw new IOException("Camera sent an incomplete PTP packet");
    }

    private void write(byte[] b) throws IOException {
        int chunk = 16 * 1024;
        for (int off = 0; off < b.length; off += chunk) {
            int len = Math.min(chunk, b.length - off);
            int n = conn.bulkTransfer(out, b, off, len, TIMEOUT_MS);
            if (n != len) throw new IOException("USB write failed");
        }
        // A transfer that ends exactly on a packet boundary needs a zero-length packet.
        if (b.length % maxPacket == 0) conn.bulkTransfer(out, b, 0, 0, TIMEOUT_MS);
    }
}
