// Star Tracker ESP32-S3 — link to the RP2354A and head time.
#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include "st_link.h"

namespace st {

using LinkHandler = std::function<void(uint8_t type, const uint8_t *payload, size_t len)>;
struct LinkStats {
    bool rp_alive = false, have_hello = false;
    st_hello_t hello = {};
    st_state_t state = {};
    uint32_t states = 0, frames = 0, crc_errors = 0, syncs = 0;
    int64_t last_rx_us = 0;
};
void link_init(LinkHandler h);
void link_set_handler(LinkHandler h);
bool link_send(uint8_t type, const void *payload, size_t len);
const LinkStats &link_stats();

void clock_update();
uint64_t head_us();
uint64_t head_us_from_local(int64_t local_us);
uint8_t head_time_quality();             // 0 boot, 1 RTC / app, 3 GNSS + PPS
void clock_set_unix(int64_t unix_us);

}  // namespace st
