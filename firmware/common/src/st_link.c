/* Star Tracker — link framing: CRC-16/CCITT-FALSE + COBS. Shared by both processors and the simulator. */
#include "st_link.h"
#include <string.h>

uint16_t st_crc16(const uint8_t *p, size_t n, uint16_t crc)
{
    while (n--) {
        crc ^= (uint16_t)(*p++) << 8;
        for (int i = 0; i < 8; i++)
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
    return crc;
}

size_t st_cobs_encode(const uint8_t *in, size_t n, uint8_t *out)
{
    size_t r = 0, code_at = 0, w = 1;
    uint8_t code = 1;
    for (r = 0; r < n; r++) {
        if (in[r] == 0) {
            out[code_at] = code;
            code_at = w++;
            code = 1;
        } else {
            out[w++] = in[r];
            if (++code == 0xFF) {
                out[code_at] = code;
                code_at = w++;
                code = 1;
            }
        }
    }
    out[code_at] = code;
    return w;
}

size_t st_cobs_decode(const uint8_t *in, size_t n, uint8_t *out)
{
    size_t r = 0, w = 0;
    while (r < n) {
        uint8_t code = in[r++];
        if (code == 0)
            return 0;
        for (uint8_t i = 1; i < code; i++) {
            if (r >= n || in[r] == 0)
                return 0;
            out[w++] = in[r++];
        }
        if (code != 0xFF && r < n)
            out[w++] = 0;
    }
    return w;
}

size_t st_link_build(uint8_t type, uint8_t seq, const void *payload, size_t len, uint8_t *frame)
{
    uint8_t raw[ST_LINK_MAX_PAYLOAD + 4];
    if (len > ST_LINK_MAX_PAYLOAD)
        return 0;
    raw[0] = type;
    raw[1] = seq;
    if (len)
        memcpy(raw + 2, payload, len);
    uint16_t crc = st_crc16(raw, len + 2, 0xFFFF);
    raw[len + 2] = (uint8_t)(crc & 0xFF);
    raw[len + 3] = (uint8_t)(crc >> 8);
    size_t n = st_cobs_encode(raw, len + 4, frame);
    frame[n++] = 0x00;
    return n;
}

void st_link_rx_init(st_link_rx_t *rx, st_link_frame_cb cb, void *ctx)
{
    memset(rx, 0, sizeof(*rx));
    rx->cb = cb;
    rx->ctx = ctx;
}

void st_link_rx_feed(st_link_rx_t *rx, const uint8_t *data, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        uint8_t b = data[i];
        if (b != 0) {
            if (rx->n < sizeof(rx->buf))
                rx->buf[rx->n++] = b;
            else if (rx->n == sizeof(rx->buf)) {
                rx->overruns++;
                rx->n = sizeof(rx->buf) + 1;   /* poisoned: dropped at the next delimiter */
            }
            continue;
        }
        /* delimiter: decode what we have */
        if (rx->n == 0)
            continue;
        if (rx->n > sizeof(rx->buf)) {
            rx->n = 0;
            continue;
        }
        uint8_t raw[ST_LINK_MAX_FRAME];
        size_t m = st_cobs_decode(rx->buf, rx->n, raw);
        rx->n = 0;
        if (m < 4) {
            rx->cobs_errors++;
            continue;
        }
        uint16_t crc = (uint16_t)(raw[m - 2] | (raw[m - 1] << 8));
        if (st_crc16(raw, m - 2, 0xFFFF) != crc) {
            rx->crc_errors++;
            continue;
        }
        uint8_t seq = raw[1];
        if (rx->have_seq && (uint8_t)(rx->last_seq + 1) != seq)
            rx->seq_gaps++;
        rx->last_seq = seq;
        rx->have_seq = 1;
        rx->frames_ok++;
        if (rx->cb)
            rx->cb(rx->ctx, raw[0], seq, raw + 2, m - 4);
    }
}
