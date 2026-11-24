// Star Tracker ESP32-S3 — bring-up menu: serial console (USB port A) and OLED + buttons.
// Walks Stages B-D of the bring-up plan (docs/04-electronics.md section 11). Every test prints PASS or FAIL against
// the plan's limits. RP2354A tests run on the RP2354A bring-up image and are relayed here (ST_MSG_TEST).
#include "st_bringup.h"
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "driver/usb_serial_jtag.h"
#include "esp_app_desc.h"
#include "esp_partition.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "st_hal.h"
#include "st_link_esp.h"
#include "st_swd.h"

extern const uint8_t rp_bringup_bin_start[] asm("_binary_rp_bringup_bin_start");
extern const uint8_t rp_bringup_bin_end[] asm("_binary_rp_bringup_bin_end");
extern const uint8_t rp_flashstub_bin_start[] asm("_binary_rp_flashstub_bin_start");
extern const uint8_t rp_flashstub_bin_end[] asm("_binary_rp_flashstub_bin_end");

namespace st {

// ---------------------------------------------------------------- output to console + OLED
static std::string oled_title, oled_line[4];
static void out(const char *fmt, ...)
{
    char b[256];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    printf("%s\n", b);
    for (int i = 0; i < 3; i++) oled_line[i] = oled_line[i + 1];
    oled_line[3] = std::string(b).substr(0, 21);
}

static void show(const std::string &status)
{
    oled.clear();
    oled.text(0, 0, oled_title.substr(0, 21).c_str(), true);
    for (int i = 0; i < 4; i++) oled.text(0, 2 + i, oled_line[i].c_str());
    oled.text(0, 7, status.substr(0, 21).c_str());
    oled.flush();
}

struct Result { std::string name; int state = 0; };   // 0 not run, 1 pass, 2 fail
static std::vector<Result> results;

static bool verdict(size_t idx, bool pass, const char *why)
{
    out("%s  %s", pass ? "PASS" : "FAIL", why);
    if (idx < results.size()) results[idx].state = pass ? 1 : 2;
    show(pass ? "PASS" : "FAIL");
    return pass;
}

// ---------------------------------------------------------------- console input
static int read_key(uint32_t timeout_ms)
{
    uint8_t c;
    int n = usb_serial_jtag_read_bytes(&c, 1, pdMS_TO_TICKS(timeout_ms));
    return n == 1 ? c : -1;
}

static std::string read_line(uint32_t timeout_ms)
{
    std::string s;
    int64_t end = esp_timer_get_time() + (int64_t)timeout_ms * 1000;
    while (esp_timer_get_time() < end) {
        int c = read_key(50);
        if (c < 0) { if (buttons()) return std::string(); continue; }
        if (c == '\r' || c == '\n') { printf("\n"); return s; }
        if ((c == 8 || c == 127) && !s.empty()) { s.pop_back(); printf("\b \b"); continue; }
        if (c >= 32 && c < 127) { s += (char)c; printf("%c", c); }
        fflush(stdout);
    }
    return s;
}

static bool confirm(const char *q, uint32_t timeout_ms = 60000)
{
    out("%s  [y = yes / n = no, or button 4 = yes, button 1 = no]", q);
    show("4=yes 1=no");
    int64_t end = esp_timer_get_time() + (int64_t)timeout_ms * 1000;
    while (esp_timer_get_time() < end) {
        int c = read_key(20);
        if (c == 'y' || c == 'Y') return true;
        if (c == 'n' || c == 'N') return false;
        int b = buttons();
        if (b & 8) { while (buttons()) vTaskDelay(10); return true; }
        if (b & 1) { while (buttons()) vTaskDelay(10); return false; }
    }
    return false;
}

static int ask_int(const char *q, int def, int lo, int hi)
{
    out("%s  [Enter = %d]", q, def);
    std::string s = read_line(30000);
    int v = s.empty() ? def : atoi(s.c_str());
    return v < lo || v > hi ? def : v;
}

static int ask_axis()
{
    out("axis? 0 = azimuth (J7), 1 = altitude (J8), 2 = roll (J9)  [default 0]");
    std::string s = read_line(20000);
    int a = s.empty() ? 0 : atoi(s.c_str());
    return a < 0 || a > 2 ? 0 : a;
}

// ---------------------------------------------------------------- RP2354A test relay
static QueueHandle_t rp_q;
struct RpLine { st_test_result_t r; };

static void on_link(uint8_t type, const uint8_t *pl, size_t len)
{
    if (type == ST_MSG_TEST_RESULT && len >= 4) {
        RpLine l;
        memset(&l, 0, sizeof l);
        memcpy(&l.r, pl, len < sizeof l.r ? len : sizeof l.r);
        xQueueSend(rp_q, &l, 0);
    }
}

static bool rp_test(size_t idx, uint8_t test, uint8_t axis, uint16_t arg = 0, int32_t arg2 = 0, uint32_t timeout_s = 120)
{
    if (!link_stats().rp_alive) {
        out("RP2354A not answering on the link. Load its bring-up image first (menu item L) or check LINK_TX/RX.");
        return verdict(idx, false, "no link");
    }
    xQueueReset(rp_q);
    st_test_t t = {test, axis, arg, arg2};
    link_send(ST_MSG_TEST, &t, sizeof t);
    int64_t end = esp_timer_get_time() + (int64_t)timeout_s * 1000000;
    while (esp_timer_get_time() < end) {
        RpLine l;
        if (xQueueReceive(rp_q, &l, pdMS_TO_TICKS(200)) == pdTRUE) {
            if (!l.r.done) { out("  %s", l.r.text); show("running"); continue; }
            return verdict(idx, l.r.pass, l.r.text);
        }
        if (read_key(0) == 'x' || (buttons() & 1)) {
            st_test_t ab = {99, 0, 0, 0};
            link_send(ST_MSG_TEST, &ab, sizeof ab);
        }
    }
    return verdict(idx, false, "timed out waiting for the RP2354A");
}

// ---------------------------------------------------------------- ESP32-side tests
static bool t_rails(size_t i)
{
    float v = vsys_volts();
    out("VSYS from IO7: %.2f V (bench supply 7.4 V -> plan limit 7.3-7.4 V at TP3; ADC accuracy +/-2 %%)", v);
    out("3.3 V is up (this firmware runs). Measure by hand: TP27 3.27-3.39 V, TP28 4.9-5.1 V, TP33 1.05-1.15 V, TP30 0 V.");
    return verdict(i, v > 7.1f && v < 7.6f, "VSYS within 7.1-7.6 V (7.3-7.4 V plus ADC tolerance)");
}

static bool t_i2c(size_t i)
{
    struct { uint8_t a; const char *n; bool req; } dev[] = {
        {I2C_ADDR_TPS25751, "TPS25751D port A", true}, {I2C_ADDR_TPS25752, "TPS25752A port B", true},
        {I2C_ADDR_MMC5983MA, "MMC5983MA magnetometer", true}, {I2C_ADDR_SH1106, "SH1106 OLED (if fitted)", false},
        {I2C_ADDR_RV3028, "RV-3028 clock", true}, {I2C_ADDR_LSM6DSV, "LSM6DSV IMU", true}};
    bool ok = true;
    std::string found;
    for (int a = 0x08; a < 0x78; a++)
        if (i2c_main.probe((uint8_t)a)) { char b[8]; snprintf(b, sizeof b, " 0x%02X", a); found += b; }
    out("main I2C answers at:%s", found.c_str());
    for (auto &d : dev) {
        bool p = i2c_main.probe(d.a);
        out("  0x%02X %-24s %s", d.a, d.n, p ? "present" : (d.req ? "MISSING" : "absent"));
        if (d.req && !p) ok = false;
    }
    bool g = i2c_pack.probe(SMB_ADDR_BQ40Z50);
    out("battery SMBus 0x0B BQ40Z50: %s (needs the pack fitted and woken by a charger)", g ? "present" : "absent");
    return verdict(i, ok, "0x20, 0x21, 0x30, 0x52, 0x6A present (plan Stage B step 7)");
}

static bool t_gnss(size_t i)
{
    out("waiting for UBX data and the 1 PPS pulse (up to 5 minutes; antenna near a window). x or button 1 stops.");
    uint32_t p0 = gnss().pps_count;
    for (int s = 0; s < 300; s++) {
        for (int k = 0; k < 10; k++) { gnss_poll(); vTaskDelay(pdMS_TO_TICKS(100)); }
        const GnssFix &g = gnss();
        if (s % 10 == 0) out("  %3d s: %lu bytes, %lu NAV-PVT, fix %d, %d satellites, PPS edges %lu", s, (unsigned long)g.bytes,
                             (unsigned long)g.nav_pvt, g.fix_type, g.num_sv, (unsigned long)(g.pps_count - p0));
        show("GNSS " + std::to_string(g.num_sv) + " sv");
        if (g.pps_count - p0 >= 3) {
            out("position %.5f, %.5f, %.0f m; time valid %d", g.lat, g.lon, g.h_msl, g.time_valid);
            return verdict(i, true, "1 PPS pulses on IO15 (TP44), plan Stage B step 8");
        }
        if (read_key(0) == 'x' || (buttons() & 1)) break;
    }
    return verdict(i, false, gnss().bytes ? "module talks but no PPS yet (needs a fix)" : "no bytes from the GNSS module");
}

static bool t_rtc(size_t i)
{
    uint32_t t = 0;
    bool ok = rtc_get_unix(t);
    uint8_t st = 0;
    i2c_main.read_reg(I2C_ADDR_RV3028, 0x0E, &st, 1);
    uint8_t br = rtc_backup_reg();
    out("clock: UNIX %lu, status 0x%02X (PORF %d, BSF %d), backup register 0x%02X", (unsigned long)t, st, st & 1, (st >> 5) & 1, br);
    out("backup switchover %s, trickle charge %s", ((br >> 2) & 3) == 3 ? "level mode (ok)" : "OFF (factory default)", (br & 0x20) ? "on" : "off");
    if (((br >> 2) & 3) != 3 || !(br & 0x20)) {
        if (confirm("set switchover + trickle charge for the MS621FE cell (D52) and save in the clock's EEPROM?")) {
            std::string log;
            ok &= rtc_setup_backup(log);
            out("%s", log.c_str());
        }
    }
    return verdict(i, ok && i2c_main.probe(I2C_ADDR_RV3028), "clock answers; backup set");
}

static bool t_imu(size_t i)
{
    bool ok = imu_init();
    Vec3 a;
    float tc = 0;
    vTaskDelay(pdMS_TO_TICKS(100));
    ok = ok && imu_read(a, tc);
    float g = sqrtf(a.x * a.x + a.y * a.y + a.z * a.z);
    out("LSM6DSV WHO_AM_I %s; accel %.3f %.3f %.3f g, |a| = %.3f g, %.1f C", ok ? "0x70" : "wrong", a.x, a.y, a.z, g, tc);
    bool m = mag_init();
    Vec3 b;
    m = m && mag_read(b);
    float f = sqrtf(b.x * b.x + b.y * b.y + b.z * b.z);
    out("MMC5983MA ID %s; field %.3f %.3f %.3f G, |B| = %.3f G", m ? "0x30" : "wrong", b.x, b.y, b.z, f);
    return verdict(i, ok && g > 0.9f && g < 1.1f && m && f > 0.15f && f < 0.8f, "|a| 0.9-1.1 g, |B| 0.15-0.8 G (Earth's field, away from magnets)");
}

static bool t_oled(size_t i)
{
    bool ok = oled.init();
    oled.clear();
    for (int r = 0; r < 8; r++) oled.text(0, r, "0123456789ABCDEFGHIJK", r & 1);
    oled.flush();
    vTaskDelay(pdMS_TO_TICKS(500));
    bool seen = ok && confirm("does the display show 8 lines of characters, every second line inverted?");
    return verdict(i, seen, "display answers at 0x3C and shows the pattern");
}

static void pd_print(const char *name, PdController &pd)
{
    PdStatus s;
    pd.status(s);
    out("%s: mode '%s', boot flags 0x%08lX, plug %d, role %s, contract %.2f V %.2f A", name, s.mode, (unsigned long)s.boot_flags,
        s.plug, s.source ? "source" : "sink", s.contract_v, s.contract_a);
}

static bool t_pd_a(size_t i)
{
    pd_print("port A TPS25751D", pd_a);
    ChargerStatus c;
    bool ok = charger_read(c);
    if (ok) out("charger BQ25792: %s, VBUS %u mV, IBUS %d mA, VBAT %u mV, IBAT %d mA, VSYS %u mV, die %.1f C, ICHG set %u mA",
                charger_state_name(c.chg_stat), c.vbus_mv, c.ibus_ma, c.vbat_mv, c.ibat_ma, c.vsys_mv, c.tdie_c, c.ichg_ma);
    else out("charger not reachable through the controller (needs 'APP ' mode, i.e. a configuration loaded)");
    PdStatus s;
    pd_a.status(s);
    out("plan Stage C step 3: with a 45 W charger and the PD tester, 15 V or 20 V negotiated, TP4 follows");
    bool contract = s.plug && !s.source && (s.contract_v > 14.5f);
    return verdict(i, ok && contract, "15 or 20 V contract and the charger answers");
}

static bool t_gauge(size_t i)
{
    PackStatus p;
    bool ok = gauge_read(p);
    if (ok) {
        out("pack: %u mV (cells %u / %u), %d mA (avg %d), %u %% (%u of %u mAh, design %u), %.1f C, %u cycles, health %u %%",
            p.mv, p.cell1_mv, p.cell2_mv, p.ma, p.avg_ma, p.soc, p.rem_mah, p.full_mah, p.design_mah, p.temp_c, p.cycles, p.soh);
        out("BatteryStatus 0x%04X, SafetyStatus 0x%08lX, OperationStatus 0x%08lX", p.batt_status, (unsigned long)p.safety_status,
            (unsigned long)p.op_status);
    } else {
        out("gauge does not answer: pack fitted? A new 2-cell pack must first be woken by a charger on PACK+ (data sheet)");
    }
    bool plaus = ok && p.mv > 5800 && p.mv < 8500 && p.temp_c > -20 && p.temp_c < 60 && p.safety_status == 0;
    return verdict(i, plaus, "voltage 5.8-8.5 V, temperature -20..60 C, no safety flags");
}

static bool t_portb(size_t i)
{
    portb_enable(true);
    vTaskDelay(pdMS_TO_TICKS(300));
    pd_print("port B TPS25752A", pd_b);
    out("plan Stage C step 4: PD tester + load on port B: 5 V and 9 V must each hold at 3 A for one minute");
    bool ok = confirm("did 5 V and 9 V each hold at 3 A for one minute on the tester?", 600000);
    portb_enable(false);
    return verdict(i, ok, "port B 5 V / 9 V at 3 A");
}

static bool t_buttons_leds(size_t i)
{
    bool ok = true;
    for (int b = 0; b < 4 && ok; b++) {
        out("press button %d (%s) within 20 s", b + 1, b == 0 ? "left" : (b == 3 ? "right" : "middle"));
        show("press " + std::to_string(b + 1));
        int64_t end = esp_timer_get_time() + 20000000;
        bool seen = false;
        while (esp_timer_get_time() < end && !seen) { if (buttons() == (1 << b)) seen = true; vTaskDelay(pdMS_TO_TICKS(10)); }
        while (buttons()) vTaskDelay(pdMS_TO_TICKS(10));
        out("  button %d %s", b + 1, seen ? "ok" : "NOT SEEN");
        ok &= seen;
    }
    const char *names[3] = {"red", "green", "blue"};
    for (int l = 0; l < 3; l++) {
        led_set((Led)l, 255);
        bool lit = confirm((std::string("is the ") + names[l] + " LED lit?").c_str());
        led_set((Led)l, 0);
        ok &= lit;
    }
    return verdict(i, ok, "four buttons read low when pressed; three LEDs light (Stage C step 5)");
}

static bool t_shutter(size_t i)
{
    out("multimeter on continuity across the 2.5 mm jack: tip-sleeve = shutter, ring-sleeve = focus");
    shutter_release(true);
    bool a = confirm("shutter output ON now: does tip-sleeve beep?");
    shutter_release(false);
    shutter_focus(true);
    bool b = confirm("focus output ON now: does ring-sleeve beep?");
    shutter_focus(false);
    return verdict(i, a && b, "opto-couplers switch (Stage C step 6)");
}

static bool t_link(size_t i)
{
    st_hello_t h = {ST_LINK_VERSION, 0, 1, 0, 0, {'A', 'P', 'P', 'B'}};
    link_send(ST_MSG_HELLO, &h, sizeof h);
    vTaskDelay(pdMS_TO_TICKS(300));
    const LinkStats &s = link_stats();
    out("link: %lu good frames, %lu CRC errors, RP2354A %s", (unsigned long)s.frames, (unsigned long)s.crc_errors, s.rp_alive ? "alive" : "silent");
    if (s.have_hello) out("RP2354A firmware %d.%d.%d (%.4s), protocol %d", s.hello.fw_major, s.hello.fw_minor, s.hello.fw_patch, s.hello.role, s.hello.proto);
    return verdict(i, s.rp_alive && s.have_hello && s.hello.proto == ST_LINK_VERSION, "RP2354A answers HELLO with the same protocol version");
}

static bool t_load_rp(size_t i)
{
    size_t n = rp_bringup_bin_end - rp_bringup_bin_start, sn = rp_flashstub_bin_end - rp_flashstub_bin_start;
    if (n < 1024 || sn < 256) return verdict(i, false, "this build has no RP2354A image embedded");
    out("writing the RP2354A bring-up image (%u bytes) over SWD...", (unsigned)n);
    std::string log;
    bool ok = swd.flash(rp_flashstub_bin_start, sn, rp_bringup_bin_start, n, [](int pc) { if (pc % 10 == 0) out("  %d %%", pc); }, log);
    out("%s", log.c_str());
    vTaskDelay(pdMS_TO_TICKS(1500));
    return verdict(i, ok && link_stats().rp_alive, "image written, verified and the RP2354A answers (heartbeat LED blinks)");
}

static bool t_pd_eeprom(size_t i)
{
    const esp_partition_t *p = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, (esp_partition_subtype_t)0x40, "pd_cfg");
    if (!p) return verdict(i, false, "no pd_cfg partition");
    // layout: [0] u32 len A, [4] u32 len B, image A at 0x1000, image B at 0x8000 (written by the web flasher)
    uint32_t len[2] = {0, 0};
    esp_partition_read(p, 0, len, 8);
    bool ok = true;
    PdController *pd[2] = {&pd_a, &pd_b};
    for (int k = 0; k < 2; k++) {
        if (len[k] == 0 || len[k] > 0x7000) { out("no image for port %c in pd_cfg (make it with TI's tool, section 9)", 'A' + k); ok = false; continue; }
        std::string img(len[k], '\0');
        esp_partition_read(p, k ? 0x8000 : 0x1000, &img[0], len[k]);
        if (!confirm((std::string("write ") + std::to_string(len[k]) + " bytes into port " + (char)('A' + k) + "'s EEPROM?").c_str())) continue;
        std::string log;
        ok &= pd[k]->write_eeprom((const uint8_t *)img.data(), img.size(), log);
        out("%s", log.c_str());
    }
    return verdict(i, ok, "both configuration EEPROMs written and verified (D70)");
}

// ---------------------------------------------------------------- menu
struct Item { char key; const char *name; std::function<bool(size_t)> fn; };

void bringup_run()
{
    rp_q = xQueueCreate(128, sizeof(RpLine));   // Phase 7: raw dumps for tools/measure
    usb_serial_jtag_driver_config_t uc = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    usb_serial_jtag_driver_install(&uc);
    io_init();
    i2c_main.init(0, ESP_GPIO_I2C_SDA, ESP_GPIO_I2C_SCL, 400000);
    i2c_pack.init(1, ESP_GPIO_PACK_SDA, ESP_GPIO_PACK_SCL, 100000);
    oled.init();
    gnss_init();
    link_init(on_link);
    oled_title = "Star Tracker bring-up";

    std::vector<Item> items = {
        {'1', "B3  rails (VSYS)", t_rails},
        {'2', "B7  I2C scan", t_i2c},
        {'3', "B8  GNSS + 1 PPS", t_gnss},
        {'4', "B   clock + backup cell", t_rtc},
        {'5', "B   IMU + magnetometer", t_imu},
        {'6', "B   display", t_oled},
        {'L', "B6  load RP2354A bring-up image (SWD)", t_load_rp},
        {'7', "B6  link to the RP2354A", t_link},
        {'8', "B   RP2354A step generators", [](size_t i) { return rp_test(i, 13, 0); }},
        {'9', "C1  motor rail 10 V / 16 V", [](size_t i) { return rp_test(i, 4, 0); }},
        {'a', "C2  motor rail under 10 ohm, 60 s", [](size_t i) { return rp_test(i, 5, 0, 0, 0, 90); }},
        {'b', "C3  port A PD + charger", t_pd_a},
        {'c', "C3  battery gauge", t_gauge},
        {'d', "C4  port B 5 V / 9 V", t_portb},
        {'e', "C5  buttons and LEDs", t_buttons_leds},
        {'f', "C6  shutter port", t_shutter},
        {'P', "C   write PD configuration EEPROMs", t_pd_eeprom},
        {'g', "D2  encoder read-out", [](size_t i) { return rp_test(i, 6, (uint8_t)ask_axis()); }},
        {'h', "D2  motor thermistors", [](size_t i) { return rp_test(i, 2, (uint8_t)ask_axis()); }},
        {'i', "D3  driver UART (addresses 0,1,2)", [](size_t i) { return rp_test(i, 3, 0); }},
        {'j', "D3  step slowly, encoder follows", [](size_t i) { int a = ask_axis(); bool m = confirm("magnet on the bare motor shaft (bench)?"); return rp_test(i, 9, (uint8_t)a, m ? 0x8000 : 0); }},
        {'k', "D4  sidereal tracking (CSV, 10-240 min)", [](size_t i) { int a = ask_axis(); bool m = confirm("magnet on the bare motor shaft (bench)?"); int mins = ask_int("minutes? 10 = Stage D4, 45 = test T2 (three wave-generator turns)", 10, 1, 240); return rp_test(i, 10, (uint8_t)a, m ? 0x8000 : 0, mins, (uint32_t)mins * 60 + 180); }},
        {'m', "D5  slews at 8 deg/s, 10 times", [](size_t i) { int a = ask_axis(); bool m = confirm("magnet on the bare motor shaft (bench)?"); return rp_test(i, 11, (uint8_t)a, m ? 0x8000 : 0, 0, 300); }},
        {'n', "D6  encoder field check", [](size_t i) { return rp_test(i, 12, (uint8_t)ask_axis()); }},
        {'o', "D8  encoder noise, 1000 readings (D48)", [](size_t i) { return rp_test(i, 7, (uint8_t)ask_axis()); }},
        {'p', "D8  encoder sweep, one revolution (D48)", [](size_t i) { int a = ask_axis(); bool m = confirm("magnet on the bare motor shaft (bench)?"); return rp_test(i, 8, (uint8_t)a, m ? 0x8000 : 0, 360, 900); }},   // Phase 7: a full output turn takes 6 min
        {'q', "D5  lost motion at reversals (T1)", [](size_t i) { int a = ask_axis(); bool m = confirm("magnet on the bare motor shaft (bench)?"); int st = ask_int("step in arcsec? (T1 uses 60; 5-600)", 60, 5, 600); return rp_test(i, 14, (uint8_t)a, m ? 0x8000 : 0, st, 900); }},
        {'t', "D5  slew log: current + StallGuard (T6)", [](size_t i) { int a = ask_axis(); int ma = ask_int(a == 0 ? "run current mA? 830 = 20 C, 1260 = -20 C (max 1350)" : "run current mA? 450 = 20 C, 890 = -20 C (max 1060)", a == 0 ? 830 : 450, 100, a == 0 ? 1350 : 1060); return rp_test(i, 15, (uint8_t)a, 0, ma, 600); }},
    };
    for (auto &it : items) results.push_back({it.name, 0});

    const esp_app_desc_t *d = esp_app_get_description();
    int sel = 0;
    bool redraw = true;
    for (;;) {
        if (redraw) {
            printf("\n===== Star Tracker bring-up, ESP32-S3 image %s =====\n", d->version);
            for (size_t k = 0; k < items.size(); k++)
                printf("  %c  %-42s %s\n", items[k].key, items[k].name, results[k].state == 1 ? "PASS" : results[k].state == 2 ? "FAIL" : "");
            printf("  s  summary     r  restart\nchoose: ");
            fflush(stdout);
            oled.clear();
            oled.text(0, 0, "BRING-UP  2/3 4=run", true);
            for (int r = 0; r < 6; r++) {
                int k = sel - 2 + r;
                if (k < 0 || k >= (int)items.size()) continue;
                char line[24];
                snprintf(line, sizeof line, "%c %-16.16s %s", items[k].key, items[k].name, results[k].state == 1 ? "ok" : results[k].state == 2 ? "XX" : "");
                oled.text(0, 1 + r, line, k == sel);
            }
            oled.flush();
            redraw = false;
        }
        int c = read_key(30);
        int b = buttons();
        int run = -1;
        if (c > 0) {
            for (size_t k = 0; k < items.size(); k++) if (items[k].key == c) run = (int)k;
            if (c == 'r') esp_restart();
            if (c == 's') {
                int p = 0, f = 0;
                for (auto &r : results) { p += r.state == 1; f += r.state == 2; printf("  %-42s %s\n", r.name.c_str(), r.state == 1 ? "PASS" : r.state == 2 ? "FAIL" : "-"); }
                printf("%d passed, %d failed, %d not run\n", p, f, (int)results.size() - p - f);
            }
            if (run < 0) redraw = true;
        }
        if (b) {
            if (b & 2) sel = sel > 0 ? sel - 1 : 0;
            if (b & 4) sel = sel < (int)items.size() - 1 ? sel + 1 : sel;
            if (b & 8) run = sel;
            while (buttons()) vTaskDelay(pdMS_TO_TICKS(10));
            redraw = true;
        }
        if (run >= 0) {
            oled_title = items[run].name;
            for (auto &l : oled_line) l.clear();
            printf("\n--- %s ---\n", items[run].name);
            show("running");
            items[run].fn((size_t)run);
            vTaskDelay(pdMS_TO_TICKS(800));
            redraw = true;
        }
        gnss_poll();
    }
}

}  // namespace st
