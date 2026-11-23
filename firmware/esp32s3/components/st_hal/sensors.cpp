// Star Tracker ESP32-S3 — GNSS (MAX-M10S, UBX), clock (RV-3028), IMU (LSM6DSV), magnetometer (MMC5983MA).
//
// Sources: u-blox M10 SPG 5.10 Interface Description (UBX framing and checksum, UBX-CFG-VALSET 0x06 0x8A,
//   UBX-NAV-PVT 0x01 0x07, UBX-RXM-PMREQ 0x02 0x41, configuration keys CFG-UART1OUTPROT-NMEA 0x10740002,
//   CFG-MSGOUT-UBX_NAV_PVT_UART1 0x20910007, CFG-TP-TIMEGRID_TP1 0x2005000C);
//   Micro Crystal RV-3028-C7 Application Manual (registers 0x00-0x06, 0x0E status, 0x0F control 1, 0x10 control 2,
//   0x1B-0x1E UNIX time, 0x27 EECMD, 0x37 EEPROM backup register: TCE bit 5, FEDE bit 4, BSM bits 3:2, TCR bits 1:0;
//   trickle charger has a series Schottky diode, so the MS621FE charges to about VDD - 0.25 V = 3.08 V);
//   ST LSM6DSV datasheet DS13510 (WHO_AM_I 0x0F = 0x70, CTRL1 0x10, CTRL3 0x12, CTRL8 0x17, OUT_TEMP 0x20, OUTX_A 0x28);
//   MEMSIC MMC5983MA datasheet (Product ID 0x2F = 0x30, Xout 0x00-0x06, status 0x08, control 0 0x09).
#include <cmath>
#include <cstring>
#include <ctime>
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "st_hal.h"

namespace st {

// ================================================================ GNSS
static GnssFix fix;
static const uart_port_t GNSS_UART = UART_NUM_2;
static uint8_t ubx[256];
static int ubx_n = 0, ubx_len = 0;

static void ubx_send(uint8_t cls, uint8_t id, const uint8_t *p, uint16_t n)
{
    uint8_t h[6] = {0xB5, 0x62, cls, id, (uint8_t)n, (uint8_t)(n >> 8)};
    uint8_t a = 0, b = 0;
    for (int i = 2; i < 6; i++) { a += h[i]; b += a; }
    for (int i = 0; i < n; i++) { a += p[i]; b += a; }
    uint8_t ck[2] = {a, b};
    uart_write_bytes(GNSS_UART, h, 6);
    if (n) uart_write_bytes(GNSS_UART, p, n);
    uart_write_bytes(GNSS_UART, ck, 2);
}

static void valset_u8(uint32_t key, uint8_t v)
{
    uint8_t p[9] = {0x00, 0x01, 0, 0, (uint8_t)key, (uint8_t)(key >> 8), (uint8_t)(key >> 16), (uint8_t)(key >> 24), v};  // RAM layer
    ubx_send(0x06, 0x8A, p, 9);
}

static void IRAM_ATTR pps_isr(void *)
{
    fix.local_us_at_pps = esp_timer_get_time();
    fix.pps_count++;
}

void gnss_init()
{
    uart_config_t c = {};
    c.baud_rate = 38400;                         // module default (hand-off 10.3)
    c.data_bits = UART_DATA_8_BITS;
    c.parity = UART_PARITY_DISABLE;
    c.stop_bits = UART_STOP_BITS_1;
    c.source_clk = UART_SCLK_DEFAULT;
    uart_driver_install(GNSS_UART, 2048, 512, 0, nullptr, 0);
    uart_param_config(GNSS_UART, &c);
    uart_set_pin(GNSS_UART, ESP_GPIO_GNSS_RXD, ESP_GPIO_GNSS_TXD, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);  // TX IO48, RX IO47
    gpio_config_t g = {};
    g.pin_bit_mask = 1ULL << ESP_GPIO_GNSS_PPS;
    g.mode = GPIO_MODE_INPUT;
    g.intr_type = GPIO_INTR_POSEDGE;
    gpio_config(&g);
    gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    gpio_isr_handler_add((gpio_num_t)ESP_GPIO_GNSS_PPS, pps_isr, nullptr);
    valset_u8(0x10740002, 0);                    // CFG-UART1OUTPROT-NMEA off
    valset_u8(0x10740001, 1);                    // CFG-UART1OUTPROT-UBX on
    valset_u8(0x20910007, 1);                    // NAV-PVT every epoch on UART1
    valset_u8(0x2005000C, 0);                    // time pulse aligned to UTC
}

static int64_t days_from_civil(int y, unsigned m, unsigned d)
{
    y -= m <= 2;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (int64_t)doe - 719468;
}

static void on_ubx(uint8_t cls, uint8_t id, const uint8_t *p, int n)
{
    if (cls == 0x01 && id == 0x07 && n >= 92) {
        fix.nav_pvt++;
        uint16_t year = p[4] | (p[5] << 8);
        uint8_t valid = p[11];
        int32_t nano;
        memcpy(&nano, p + 16, 4);
        uint32_t tacc;
        memcpy(&tacc, p + 12, 4);
        fix.fix_type = p[20];
        fix.fix = (p[21] & 1) && fix.fix_type >= 2;
        fix.num_sv = p[23];
        int32_t lon, lat, hmsl;
        memcpy(&lon, p + 24, 4);
        memcpy(&lat, p + 28, 4);
        memcpy(&hmsl, p + 36, 4);
        fix.lon = lon * 1e-7;
        fix.lat = lat * 1e-7;
        fix.h_msl = hmsl * 1e-3;
        fix.tacc_ns = (float)tacc;
        bool tv = (valid & 0x07) == 0x07;        // validDate, validTime, fullyResolved
        if (tv) {
            int64_t secs = days_from_civil(year, p[6], p[7]) * 86400 + p[8] * 3600 + p[9] * 60 + p[10];
            int64_t us = secs * 1000000 + nano / 1000;
            // the navigation epoch is on the whole second; its PPS edge came shortly before this message
            int64_t since_edge = esp_timer_get_time() - fix.local_us_at_pps;
            if (fix.pps_count && since_edge < 900000 && llabs(nano) < 1000000) {
                fix.unix_us_at_pps = (us + 500000) / 1000000 * 1000000;
                fix.time_valid = true;
            }
        }
    }
}

void gnss_poll()
{
    uint8_t buf[128];
    int n;
    while ((n = uart_read_bytes(GNSS_UART, buf, sizeof buf, 0)) > 0) {
        fix.bytes += n;
        for (int i = 0; i < n; i++) {
            uint8_t b = buf[i];
            if (ubx_n == 0 && b != 0xB5) continue;
            if (ubx_n == 1 && b != 0x62) { ubx_n = 0; continue; }
            ubx[ubx_n++] = b;
            if (ubx_n == 6) { ubx_len = ubx[4] | (ubx[5] << 8); if (ubx_len > 240) ubx_n = 0; }
            if (ubx_n >= 8 && ubx_n == ubx_len + 8) {
                uint8_t a = 0, c = 0;
                for (int k = 2; k < ubx_len + 6; k++) { a += ubx[k]; c += a; }
                if (a == ubx[ubx_len + 6] && c == ubx[ubx_len + 7]) on_ubx(ubx[2], ubx[3], ubx + 6, ubx_len);
                ubx_n = 0;
            }
        }
    }
}

const GnssFix &gnss() { return fix; }

void gnss_backup()
{
    // UBX-RXM-PMREQ, 16-byte version: duration 0 (until woken), flags backup (bit 1), wake on UART RX (bit 3)
    uint8_t p[16] = {0};
    p[8] = 0x02;
    p[12] = 0x08;
    ubx_send(0x02, 0x41, p, 16);
}

// ================================================================ RV-3028
bool rtc_get_unix(uint32_t &t)
{
    uint8_t b[4];
    if (!i2c_main.read_reg(I2C_ADDR_RV3028, 0x1B, b, 4)) return false;
    t = b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24);
    return true;
}

bool rtc_set_unix(uint32_t t)
{
    uint8_t b[4] = {(uint8_t)t, (uint8_t)(t >> 8), (uint8_t)(t >> 16), (uint8_t)(t >> 24)};
    return i2c_main.write_reg(I2C_ADDR_RV3028, 0x1B, b, 4);
}

uint8_t rtc_backup_reg()
{
    uint8_t v = 0;
    i2c_main.read_reg(I2C_ADDR_RV3028, 0x37, &v, 1);
    return v;
}

static bool rtc_wait_ee()
{
    for (int i = 0; i < 100; i++) {
        uint8_t s = 0;
        if (!i2c_main.read_reg(I2C_ADDR_RV3028, 0x0E, &s, 1)) return false;
        if (!(s & 0x80)) return true;                    // EEbusy clear
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    return false;
}

// Factory default 0x37 = 0x10: switchover DISABLED, so the backup cell would never be used. Set
// TCE = 1 (trickle on), TCR = 11 (11 k, gentle for the MS621FE), BSM = 11 (level switching), FEDE = 1.
bool rtc_setup_backup(std::string &log)
{
    const uint8_t want = (1u << 5) | (1u << 4) | (3u << 2) | 3u;   // 0x3F
    uint8_t c1 = 0;
    if (!i2c_main.read_reg(I2C_ADDR_RV3028, 0x0F, &c1, 1)) { log += "clock does not answer\n"; return false; }
    uint8_t cur = rtc_backup_reg();
    log += "backup register was 0x" + std::to_string(cur) + "\n";
    if ((cur & 0x3F) == want) { log += "already set\n"; return true; }
    uint8_t c1e = c1 | 0x08;                             // EERD = 1: stop the automatic refresh during the update
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x0F, &c1e, 1);
    uint8_t v = (uint8_t)((cur & 0xC0) | want);
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x37, &v, 1);
    rtc_wait_ee();
    uint8_t z = 0x00, upd = 0x11;
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x27, &z, 1);    // EECMD: 0x00 first
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x27, &upd, 1);  // then 0x11 = copy configuration RAM to EEPROM
    bool ok = rtc_wait_ee();
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x0F, &c1, 1);   // refresh back on
    uint8_t after = rtc_backup_reg();
    log += "backup register now 0x" + std::to_string(after) + (ok && (after & 0x3F) == want ? " (ok)\n" : " (FAILED)\n");
    return ok && (after & 0x3F) == want;
}

bool rtc_set_wake(uint32_t seconds)
{
    // countdown timer at 1 Hz (TD = 10), single shot, interrupt on INT (WAKE_IRQ_N, IO6)
    if (seconds > 4095) seconds = 4095;
    uint8_t t[2] = {(uint8_t)seconds, (uint8_t)((seconds >> 8) & 0x0F)};
    uint8_t c1 = 0, c2 = 0, st = 0;
    i2c_main.read_reg(I2C_ADDR_RV3028, 0x0F, &c1, 1);
    i2c_main.read_reg(I2C_ADDR_RV3028, 0x10, &c2, 1);
    i2c_main.read_reg(I2C_ADDR_RV3028, 0x0E, &st, 1);
    st &= (uint8_t)~0x08;                                // clear TF
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x0E, &st, 1);
    c1 &= (uint8_t)~0x87;                                // TE off, TRPT off, TD cleared
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x0F, &c1, 1);
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x0A, t, 2);
    c2 |= 0x10;                                          // TIE
    i2c_main.write_reg(I2C_ADDR_RV3028, 0x10, &c2, 1);
    c1 |= 0x02 | 0x04;                                   // TD = 10 (1 Hz), TE = 1
    return i2c_main.write_reg(I2C_ADDR_RV3028, 0x0F, &c1, 1);
}

// ================================================================ LSM6DSV
bool imu_init()
{
    uint8_t who = 0;
    if (!i2c_main.read_reg(I2C_ADDR_LSM6DSV, 0x0F, &who, 1) || who != 0x70) return false;
    uint8_t ctrl3 = 0x44;                                // BDU = 1, IF_INC = 1
    i2c_main.write_reg(I2C_ADDR_LSM6DSV, 0x12, &ctrl3, 1);
    uint8_t ctrl8 = 0x00;                                // +/-2 g, 0.061 mg/LSB
    i2c_main.write_reg(I2C_ADDR_LSM6DSV, 0x17, &ctrl8, 1);
    uint8_t ctrl1 = 0x05;                                // accelerometer 60 Hz, high-performance mode
    return i2c_main.write_reg(I2C_ADDR_LSM6DSV, 0x10, &ctrl1, 1);
}

bool imu_read(Vec3 &a, float &temp_c)
{
    uint8_t b[14];
    if (!i2c_main.read_reg(I2C_ADDR_LSM6DSV, 0x20, b, 14)) return false;   // OUT_TEMP .. OUTZ_A (gyro in between)
    int16_t t = (int16_t)(b[0] | (b[1] << 8));
    temp_c = 25.0f + t / 256.0f;
    int16_t x = (int16_t)(b[8] | (b[9] << 8)), y = (int16_t)(b[10] | (b[11] << 8)), z = (int16_t)(b[12] | (b[13] << 8));
    a.x = x * 0.061e-3f;
    a.y = y * 0.061e-3f;
    a.z = z * 0.061e-3f;
    return true;
}

// ================================================================ MMC5983MA
bool mag_init()
{
    uint8_t id = 0;
    if (!i2c_main.read_reg(I2C_ADDR_MMC5983MA, 0x2F, &id, 1) || id != 0x30) return false;
    uint8_t c0 = 0x08;                                   // SET pulse, clears offset after power-up
    i2c_main.write_reg(I2C_ADDR_MMC5983MA, 0x09, &c0, 1);
    return true;
}

bool mag_read(Vec3 &g)
{
    uint8_t c0 = 0x01;                                   // TM_M: one measurement
    if (!i2c_main.write_reg(I2C_ADDR_MMC5983MA, 0x09, &c0, 1)) return false;
    for (int i = 0; i < 20; i++) {
        uint8_t s = 0;
        vTaskDelay(pdMS_TO_TICKS(2));
        i2c_main.read_reg(I2C_ADDR_MMC5983MA, 0x08, &s, 1);
        if (s & 0x01) break;
    }
    uint8_t b[7];
    if (!i2c_main.read_reg(I2C_ADDR_MMC5983MA, 0x00, b, 7)) return false;
    uint32_t x = ((uint32_t)b[0] << 10) | ((uint32_t)b[1] << 2) | ((b[6] >> 6) & 3);
    uint32_t y = ((uint32_t)b[2] << 10) | ((uint32_t)b[3] << 2) | ((b[6] >> 4) & 3);
    uint32_t z = ((uint32_t)b[4] << 10) | ((uint32_t)b[5] << 2) | ((b[6] >> 2) & 3);
    g.x = ((int32_t)x - 131072) / 16384.0f;              // 18-bit, 16384 counts per gauss
    g.y = ((int32_t)y - 131072) / 16384.0f;
    g.z = ((int32_t)z - 131072) / 16384.0f;
    return true;
}

}  // namespace st
