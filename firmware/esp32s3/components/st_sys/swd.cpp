// Star Tracker ESP32-S3 — programs the RP2354A over SWD (IO38 SWCLK, IO39 SWDIO, IO40 RUN; D22, Phase 4 section 10.4).
//
// Method: hold RUN low, release, connect SWD (dormant-to-SWD wake + line reset, ADIv6 DP), power up the debug domain,
// halt core 0 through its MEM-AP (AP base 0x2000, as in OpenOCD's rp2350.cfg), load the RAM flash loader
// (st_rp2354a_flashstub, built with the RP2354A firmware) at 0x20000000, start it, then hand it 4 KB sectors through
// a mailbox at 0x20060000 and a buffer at 0x20040000. Finally CRC-check the flash and release RUN.
//
// References: Arm ADIv6.0 (IHI 0074): SWD packet, DP registers DPIDR 0x0, CTRL/STAT 0x4, SELECT 0x8 (ADDR[31:4] |
// DPBANKSEL), RDBUFF 0xC, ABORT 0x0 (write); MEM-AP registers at 0xD00 (CSW), 0xD04 (TAR), 0xD0C (DRW).
// Armv8-M ARM: DHCSR 0xE000EDF0, DCRSR 0xE000EDF4, DCRDR 0xE000EDF8, VTOR 0xE000ED08.
// STATUS: written from the specifications, not yet run against a real RP2354A. The Debug Probe on J6 is the fallback.
#include "st_swd.h"
#include <cstring>
#include "driver/gpio.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "soc/gpio_struct.h"
#include "st_board.h"
#include "st_hal.h"

namespace st {

static const int CLK = ESP_GPIO_SWCLK_E, DIO = ESP_GPIO_SWDIO_E;   // 38, 39: both in GPIO.out1 (pins 32-48)
static inline void clk(int v) { if (v) GPIO.out1_w1ts.val = 1u << (CLK - 32); else GPIO.out1_w1tc.val = 1u << (CLK - 32); }
static inline void dio(int v) { if (v) GPIO.out1_w1ts.val = 1u << (DIO - 32); else GPIO.out1_w1tc.val = 1u << (DIO - 32); }
static inline int  dio_in() { return (GPIO.in1.val >> (DIO - 32)) & 1; }
static inline void dio_out(bool out) { if (out) GPIO.enable1_w1ts.val = 1u << (DIO - 32); else GPIO.enable1_w1tc.val = 1u << (DIO - 32); }
static inline void dly() { esp_rom_delay_us(1); }                  // about 400 kHz SWCLK: safe through 100 ohm and the harness

static void wbit(int b) { dio(b); clk(0); dly(); clk(1); dly(); }
static int  rbit() { clk(0); dly(); int b = dio_in(); clk(1); dly(); return b; }
static void wbits(uint32_t v, int n) { for (int i = 0; i < n; i++) wbit((v >> i) & 1); }
static uint32_t rbits(int n) { uint32_t v = 0; for (int i = 0; i < n; i++) v |= (uint32_t)rbit() << i; return v; }
static void turn() { clk(0); dly(); clk(1); dly(); }

static void line_reset() { dio_out(true); for (int i = 0; i < 56; i++) wbit(1); wbit(0); wbit(0); }

static void dormant_to_swd()
{
    static const uint8_t seq[] = {0xff, 0x92, 0xf3, 0x09, 0x62, 0x95, 0x2d, 0x85, 0x86, 0xe9, 0xaf, 0xdd, 0xe3, 0xa2,
                                  0x0e, 0xbc, 0x19, 0xa0, 0x01};   // 8 x high, 128-bit selection alert, 4 x low, 0x1A
    dio_out(true);
    int bits = 148;
    for (int i = 0; i < bits; i++) wbit((seq[i / 8] >> (i % 8)) & 1);
}

// One SWD transaction. Returns the ACK (1 = OK, 2 = WAIT, 4 = FAULT, 7 = no target).
static int xfer(bool ap, bool rd, uint8_t a32, uint32_t *data)
{
    for (int retry = 0; retry < 50; retry++) {
        int a2 = (a32 >> 2) & 1, a3 = (a32 >> 3) & 1;
        int par = (ap + rd + a2 + a3) & 1;
        uint32_t req = 1 | (ap << 1) | (rd << 2) | (a2 << 3) | (a3 << 4) | (par << 5) | (0 << 6) | (1 << 7);
        dio_out(true);
        wbits(req, 8);
        dio_out(false);
        turn();
        int ack = (int)rbits(3);
        if (ack == 1) {
            if (rd) {
                uint32_t v = rbits(32);
                int p = rbit();
                turn();
                dio_out(true);
                if ((__builtin_popcount(v) & 1) != p) return 8;  // parity error
                *data = v;
            } else {
                turn();
                dio_out(true);
                wbits(*data, 32);
                wbit(__builtin_popcount(*data) & 1);
            }
            wbits(0, 8);                                         // idle cycles
            return 1;
        }
        turn();
        dio_out(true);
        wbits(0, 8);
        if (ack != 2) return ack;                                // FAULT or nothing
    }
    return 2;
}

static uint32_t sel_cache = 0xFFFFFFFF;
static bool dp_w(uint8_t a, uint32_t v) { return xfer(false, false, a, &v) == 1; }
static bool dp_r(uint8_t a, uint32_t *v) { return xfer(false, true, a, v) == 1; }
static bool select(uint32_t s) { if (s == sel_cache) return true; sel_cache = s; return dp_w(0x8, s); }
static bool ap_w(uint32_t addr, uint32_t v) { return select(addr & ~0xFu) && xfer(true, false, (uint8_t)(addr & 0xC), &v) == 1; }
static bool ap_r(uint32_t addr, uint32_t *v)
{
    uint32_t dummy;
    if (!select(addr & ~0xFu) || xfer(true, true, (uint8_t)(addr & 0xC), &dummy) != 1) return false;   // posted read
    return dp_r(0xC, v);                                                                           // RDBUFF
}

static const uint32_t AP0 = 0x2000;                               // core 0 MEM-AP
static bool mem_w(uint32_t a, uint32_t v) { return ap_w(AP0 + 0xD04, a) && ap_w(AP0 + 0xD0C, v); }
static bool mem_r(uint32_t a, uint32_t *v) { return ap_w(AP0 + 0xD04, a) && ap_r(AP0 + 0xD0C, v); }

static bool mem_block(uint32_t a, const uint8_t *p, size_t n)    // n multiple of 4; TAR wraps every 1 KB
{
    size_t i = 0;
    while (i < n) {
        if (!ap_w(AP0 + 0xD04, a + (uint32_t)i)) return false;
        size_t chunk = 1024 - ((a + i) & 1023);
        if (chunk > n - i) chunk = n - i;
        for (size_t k = 0; k < chunk; k += 4) {
            uint32_t w;
            memcpy(&w, p + i + k, 4);
            if (xfer(true, false, 0xC, &w) != 1) return false;   // DRW, auto-increment
        }
        i += chunk;
    }
    return true;
}

bool SwdFlasher::connect(std::string &log)
{
    gpio_config_t g = {};
    g.pin_bit_mask = (1ULL << CLK) | (1ULL << DIO);
    g.mode = GPIO_MODE_INPUT_OUTPUT;
    g.pull_up_en = GPIO_PULLUP_ENABLE;
    gpio_config(&g);
    clk(1);
    dio(1);
    rp_reset(true);
    vTaskDelay(pdMS_TO_TICKS(10));
    rp_reset(false);
    vTaskDelay(pdMS_TO_TICKS(5));
    sel_cache = 0xFFFFFFFF;
    line_reset();
    dormant_to_swd();
    line_reset();
    uint32_t id = 0;
    if (!dp_r(0x0, &id)) { log += "no SWD answer from the RP2354A (check SWCLK/SWDIO, RUN, 3.3 V)\n"; return false; }
    char b[96];
    snprintf(b, sizeof b, "DPIDR 0x%08lx\n", (unsigned long)id);
    log += b;
    dp_w(0x0, 0x1E);                                             // ABORT: clear sticky errors
    dp_w(0x4, 0x50000000);                                       // CSYSPWRUPREQ | CDBGPWRUPREQ
    uint32_t cs = 0;
    for (int i = 0; i < 100 && (cs & 0xA0000000) != 0xA0000000; i++) dp_r(0x4, &cs);
    if ((cs & 0xA0000000) != 0xA0000000) { log += "debug power-up not acknowledged\n"; return false; }
    uint32_t csw = 0;
    if (!ap_r(AP0 + 0xD00, &csw)) { log += "core 0 access port does not answer\n"; return false; }
    ap_w(AP0 + 0xD00, (csw & ~0x3Fu) | 0x12);                    // 32-bit, single auto-increment
    mem_w(0xE000EDF0, 0xA05F0003);                               // DHCSR: debug enable + halt
    uint32_t dh = 0;
    mem_r(0xE000EDF0, &dh);
    if (!(dh & (1u << 17))) { log += "core 0 did not halt\n"; return false; }
    log += "core 0 halted\n";
    connected_ = true;
    return true;
}

static bool core_reg_w(uint32_t reg, uint32_t v)
{
    if (!mem_w(0xE000EDF8, v) || !mem_w(0xE000EDF4, reg | (1u << 16))) return false;
    for (int i = 0; i < 100; i++) { uint32_t dh; mem_r(0xE000EDF0, &dh); if (dh & (1u << 16)) return true; }
    return false;
}

static const uint32_t MBOX = 0x20060000, BUF = 0x20040000;
enum { M_MAGIC = 0, M_CMD = 4, M_ADDR = 8, M_LEN = 12, M_STATUS = 16, M_RESULT = 20 };

static bool stub_cmd(uint32_t cmd, uint32_t a, uint32_t n, uint32_t timeout_ms, uint32_t *result = nullptr)
{
    mem_w(MBOX + M_ADDR, a);
    mem_w(MBOX + M_LEN, n);
    mem_w(MBOX + M_STATUS, 0);
    mem_w(MBOX + M_CMD, cmd);
    for (uint32_t t = 0; t < timeout_ms; t += 5) {
        vTaskDelay(pdMS_TO_TICKS(5));
        uint32_t s = 0;
        mem_r(MBOX + M_STATUS, &s);
        if (s == 1) { if (result) mem_r(MBOX + M_RESULT, result); return true; }
        if (s == 2) return false;
    }
    return false;
}

static uint32_t crc32(const uint8_t *p, size_t n)
{
    uint32_t c = 0xFFFFFFFFu;
    while (n--) { c ^= *p++; for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u))); }
    return ~c;
}

bool SwdFlasher::flash(const uint8_t *stub, size_t stub_n, const uint8_t *img, size_t n,
                       std::function<void(int)> progress, std::string &log)
{
    if (!connected_ && !connect(log)) return false;
    // 1. load and start the RAM loader
    size_t sn = (stub_n + 3) & ~3u;
    std::string pad((const char *)stub, stub_n);
    pad.resize(sn, '\0');
    mem_w(MBOX + M_MAGIC, 0);
    if (!mem_block(0x20000000, (const uint8_t *)pad.data(), sn)) { log += "loading the flash loader failed\n"; return false; }
    uint32_t sp, pc;
    memcpy(&sp, stub, 4);
    memcpy(&pc, stub + 4, 4);
    mem_w(0xE000ED08, 0x20000000);                               // VTOR
    core_reg_w(13, sp);
    core_reg_w(15, pc & ~1u);
    core_reg_w(16, 0x01000000);                                  // xPSR: Thumb
    mem_w(0xE000EDF0, 0xA05F0001);                               // run (debug still enabled)
    uint32_t magic = 0, status = 0;
    for (int i = 0; i < 100 && magic != 0x4C465453u; i++) { vTaskDelay(pdMS_TO_TICKS(5)); mem_r(MBOX + M_MAGIC, &magic); }
    mem_r(MBOX + M_STATUS, &status);
    if (magic != 0x4C465453u || status != 3) { log += "flash loader did not start\n"; return false; }
    log += "flash loader running\n";
    // 2. erase, 3. program sector by sector
    size_t total = (n + 4095) & ~4095u;
    if (!stub_cmd(1, 0, (uint32_t)total, 20000)) { log += "erase failed\n"; return false; }
    std::string sector(4096, '\xff');
    for (size_t off = 0; off < total; off += 4096) {
        size_t k = n - off < 4096 ? n - off : 4096;
        memset(&sector[0], 0xFF, 4096);
        memcpy(&sector[0], img + off, k);
        if (!mem_block(BUF, (const uint8_t *)sector.data(), 4096) || !stub_cmd(2, (uint32_t)off, 4096, 2000)) {
            log += "program failed at offset " + std::to_string(off) + "\n";
            return false;
        }
        if (progress) progress((int)(off * 100 / total));
    }
    // 4. verify
    uint32_t got = 0, want = crc32(img, n);
    if (!stub_cmd(3, 0, (uint32_t)n, 5000, &got) || got != want) { log += "CRC check failed\n"; return false; }
    log += "RP2354A flash written and verified (" + std::to_string(n) + " bytes)\n";
    // 5. reset into the new image
    rp_reset(true);
    vTaskDelay(pdMS_TO_TICKS(10));
    rp_reset(false);
    connected_ = false;
    gpio_set_direction((gpio_num_t)CLK, GPIO_MODE_INPUT);        // leave the lines to a Debug Probe
    gpio_set_direction((gpio_num_t)DIO, GPIO_MODE_INPUT);
    return true;
}

SwdFlasher swd;

}  // namespace st
