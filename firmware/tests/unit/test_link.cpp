// Link framing: CRC-16/CCITT-FALSE check value, COBS round trips, corrupted frames rejected.
#include <cstring>
#include <random>
#include "st_link.h"
#include "tst.h"

TEST(link_crc16_check_value)
{
    const char *s = "123456789";
    CHECK(st_crc16((const uint8_t *)s, 9, 0xFFFF) == 0x29B1);   // CRC-16/CCITT-FALSE check value
}

static int got_frames;
static uint8_t got_type;
static std::vector<uint8_t> got;
static void cb(void *, uint8_t type, uint8_t, const uint8_t *p, size_t n) { got_frames++; got_type = type; got.assign(p, p + n); }

TEST(link_round_trip_random_payloads)
{
    std::mt19937 rng(7);
    st_link_rx_t rx;
    st_link_rx_init(&rx, cb, nullptr);
    for (int k = 0; k < 2000; k++) {
        size_t n = rng() % (ST_LINK_MAX_PAYLOAD + 1);
        std::vector<uint8_t> p(n);
        for (auto &b : p) b = (rng() % 4 == 0) ? 0 : (uint8_t)rng();   // many zero bytes
        uint8_t f[ST_LINK_MAX_FRAME + 8];
        size_t fl = st_link_build((uint8_t)(k & 0x7F), (uint8_t)k, p.data(), n, f);
        CHECK(fl > 0 && fl <= ST_LINK_MAX_FRAME + 2);
        for (size_t i = 0; i + 1 < fl; i++) CHECK(f[i] != 0);           // only the delimiter is zero
        got_frames = 0;
        st_link_rx_feed(&rx, f, fl);
        CHECK(got_frames == 1 && got == p && got_type == (uint8_t)(k & 0x7F));
    }
    CHECK(rx.crc_errors == 0 && rx.seq_gaps == 0);
}

TEST(link_rejects_corruption)
{
    st_link_rx_t rx;
    st_link_rx_init(&rx, cb, nullptr);
    st_state_t s;
    memset(&s, 0x5A, sizeof s);
    uint8_t f[ST_LINK_MAX_FRAME + 8];
    size_t fl = st_link_build(ST_MSG_STATE, 1, &s, sizeof s, f);
    f[10] ^= 0x01;
    got_frames = 0;
    st_link_rx_feed(&rx, f, fl);
    CHECK(got_frames == 0 && rx.crc_errors + rx.cobs_errors == 1);
    NOTE("STATE frame %zu bytes on the wire (%zu payload); 100 Hz = %.1f %% of 921 600 baud", fl, sizeof s, fl * 10.0 * 100 / 921600 * 100);
}
