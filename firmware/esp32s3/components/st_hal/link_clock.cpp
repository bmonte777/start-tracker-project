// Star Tracker ESP32-S3 — link to the RP2354A (UART1, IO17 TX / IO18 RX, 921 600 baud) and head time.
#include "st_link_esp.h"
#include <cstring>
#include "driver/uart.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "st_hal.h"

namespace st {

// ================================================================ head time
// unix_us = anchor_unix + (local - anchor_local) * (1 + drift). Anchored on GNSS PPS edges when available,
// else on the RTC's whole seconds, else boot time (quality 0).
static int64_t anchor_local = 0, anchor_unix = 0;
static double drift = 0.0;
static uint8_t quality = 0;
static uint32_t last_pps_used = 0;

void clock_update()
{
    const GnssFix &g = gnss();
    if (g.time_valid && g.pps_count != last_pps_used && g.unix_us_at_pps) {
        if (quality >= 2 && anchor_local) {
            double dl = (double)(g.local_us_at_pps - anchor_local), du = (double)(g.unix_us_at_pps - anchor_unix);
            if (dl > 5e5) { double d = du / dl - 1.0; if (d > -1e-4 && d < 1e-4) drift = 0.9 * drift + 0.1 * d; }
        }
        anchor_local = g.local_us_at_pps;
        anchor_unix = g.unix_us_at_pps;
        last_pps_used = g.pps_count;
        quality = 3;
        rtc_set_unix((uint32_t)(anchor_unix / 1000000));          // keep the clock chip right
        return;
    }
    if (quality == 0) {
        uint32_t t;
        if (rtc_get_unix(t) && t > 1700000000u) {                 // sane (after Nov 2023)
            anchor_local = esp_timer_get_time();
            anchor_unix = (int64_t)t * 1000000;
            quality = 1;
        }
    }
}

uint64_t head_us_from_local(int64_t local)
{
    if (!anchor_local) return (uint64_t)local;
    return (uint64_t)(anchor_unix + (int64_t)((double)(local - anchor_local) * (1.0 + drift)));
}
uint64_t head_us() { return head_us_from_local(esp_timer_get_time()); }
uint8_t head_time_quality() { return quality; }
void clock_set_unix(int64_t unix_us)                                // from the app, when there is no GNSS
{
    if (quality >= 2) return;
    anchor_local = esp_timer_get_time();
    anchor_unix = unix_us;
    quality = 1;
    rtc_set_unix((uint32_t)(unix_us / 1000000));
}

// ================================================================ link
static const uart_port_t LINK_UART = UART_NUM_1;
static st_link_rx_t rx;
static SemaphoreHandle_t tx_lock;
static uint8_t tx_seq;
static LinkHandler handler;
static LinkStats stats;

static void on_frame(void *, uint8_t type, uint8_t seq, const uint8_t *pl, size_t len)
{
    (void)seq;
    stats.last_rx_us = esp_timer_get_time();
    if (type == ST_MSG_HEARTBEAT) stats.rp_alive = true;
    if (type == ST_MSG_HELLO && len >= sizeof(st_hello_t)) { memcpy(&stats.hello, pl, sizeof(st_hello_t)); stats.have_hello = true; }
    if (type == ST_MSG_STATE && len >= sizeof(st_state_t)) { memcpy(&stats.state, pl, sizeof(st_state_t)); stats.states++; }
    if (handler) handler(type, pl, len);
}

static void rx_task(void *)
{
    uint8_t buf[256];
    int64_t t_sync = 0, t_hb = 0;
    for (;;) {
        int n = uart_read_bytes(LINK_UART, buf, sizeof buf, pdMS_TO_TICKS(5));
        if (n > 0) st_link_rx_feed(&rx, buf, (size_t)n);
        int64_t now = esp_timer_get_time();
        if (now - t_sync >= 1000000) {                              // once a second: LINK_SYNC edge + TIMESYNC
            t_sync = now;
            clock_update();
            int64_t edge = esp_timer_get_time();
            link_sync_pulse();
            st_timesync_t ts = {head_us_from_local(edge), stats.syncs++, head_time_quality(), 0};
            link_send(ST_MSG_TIMESYNC, &ts, sizeof ts);
        }
        if (now - t_hb >= 100000) {
            t_hb = now;
            st_heartbeat_t hb = {(uint32_t)(now / 1000), 0, (uint16_t)rx.crc_errors};
            link_send(ST_MSG_HEARTBEAT, &hb, sizeof hb);
        }
        stats.crc_errors = rx.crc_errors;
        stats.frames = rx.frames_ok;
        if (stats.rp_alive && now - stats.last_rx_us > 500000) stats.rp_alive = false;
    }
}

void link_init(LinkHandler h)
{
    handler = h;
    tx_lock = xSemaphoreCreateMutex();
    uart_config_t c = {};
    c.baud_rate = ST_LINK_BAUD;
    c.data_bits = UART_DATA_8_BITS;
    c.parity = UART_PARITY_DISABLE;
    c.stop_bits = UART_STOP_BITS_1;
    c.source_clk = UART_SCLK_DEFAULT;
    uart_driver_install(LINK_UART, 4096, 2048, 0, nullptr, 0);
    uart_param_config(LINK_UART, &c);
    uart_set_pin(LINK_UART, ESP_GPIO_LINK_TX, ESP_GPIO_LINK_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    st_link_rx_init(&rx, on_frame, nullptr);
    xTaskCreatePinnedToCore(rx_task, "link", 4096, nullptr, 20, nullptr, 1);
}

bool link_send(uint8_t type, const void *payload, size_t len)
{
    uint8_t f[ST_LINK_MAX_FRAME + 8];
    xSemaphoreTake(tx_lock, portMAX_DELAY);
    size_t n = st_link_build(type, tx_seq++, payload, len, f);
    if (n) uart_write_bytes(LINK_UART, f, n);
    xSemaphoreGive(tx_lock);
    return n != 0;
}

const LinkStats &link_stats() { return stats; }
void link_set_handler(LinkHandler h) { handler = h; }

}  // namespace st
