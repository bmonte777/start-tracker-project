#!/usr/bin/env python3
"""Make a Star Tracker update bundle (.stfw) from the ESP32-S3 app image and/or the RP2354A motion image.
Format: see firmware/esp32s3/components/st_app/ota.cpp. Used by the GitHub Actions workflow.

    make_bundle.py --esp star_tracker_esp32s3.bin --rp st_rp2354a_motion.bin -o star-tracker-0.1.0.stfw
"""
import argparse
import hashlib
import struct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esp")
    ap.add_argument("--rp")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    parts = []
    if a.esp:
        parts.append((1, open(a.esp, "rb").read()))
    if a.rp:
        parts.append((2, open(a.rp, "rb").read()))
    if not parts:
        raise SystemExit("nothing to bundle")
    hdr = bytearray(64)
    hdr[0:4] = b"STFW"
    struct.pack_into("<III", hdr, 4, 1, len(parts), 0)
    off = 64
    body = b""
    for i, (typ, data) in enumerate(parts):
        sha = hashlib.sha256(data).digest()
        struct.pack_into("<B3xII12s", hdr, 16 + 24 * i, typ, off, len(data), sha[:12])
        body += data
        off += len(data)
    with open(a.out, "wb") as f:
        f.write(bytes(hdr) + body)
    print(f"{a.out}: {len(parts)} image(s), {off} bytes")


if __name__ == "__main__":
    main()
