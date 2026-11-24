// Star Tracker ESP32-S3 — system firmware: wires the hardware layer, the link, the Head model, the protocols, the UI,
// power management and updates together (docs/05-firmware.md section 3.3).
#include "st_app.h"
#include <cmath>
#include <cstring>
#include "cJSON.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "st_app_int.h"
#include "st_hal.h"
#include "st_link_esp.h"

namespace st {

static const char *TAG = "app";

class LinkPort : public MotionPort {
public:
    bool send(uint8_t type, const void *p, size_t n) override { return link_send(type, p, n); }
};
static LinkPort port;
static Head *head;
static std::string wifi_ssid, wifi_psk;
static bool night = false;
Head *app_head() { return head; }

// ---------------------------------------------------------------- settings in NVS (one JSON blob)
static void settings_load(Settings &s)
{
    nvs_handle_t h;
    if (nvs_open("st", NVS_READONLY, &h) != ESP_OK) return;
    size_t n = 0;
    if (nvs_get_str(h, "cfg", nullptr, &n) == ESP_OK && n < 4096) {
        std::string b(n, '\0');
        nvs_get_str(h, "cfg", &b[0], &n);
        cJSON *j = cJSON_Parse(b.c_str());
        auto num = [&](const char *k, double &v) { cJSON *x = cJSON_GetObjectItem(j, k); if (cJSON_IsNumber(x)) v = x->valuedouble; };
        auto bol = [&](const char *k, bool &v) { cJSON *x = cJSON_GetObjectItem(j, k); if (cJSON_IsBool(x)) v = cJSON_IsTrue(x); };
        auto str = [&](const char *k, std::string &v) { cJSON *x = cJSON_GetObjectItem(j, k); if (cJSON_IsString(x)) v = x->valuestring; };
        if (j) {
            num("lat", s.site.lat); num("lon", s.site.lon); num("elev", s.site.elev_m); num("p", s.site.pressure_hpa); num("t", s.site.temp_c);
            bol("refr", s.site.refraction); num("wedge", s.wedge_deg); num("az0", s.az0_deg);
            double m = 0, pl = s.payload; num("mode", m); num("payload", pl);
            s.mode = m > 0.5 ? MountMode::Equatorial : MountMode::AltAz; s.payload = (int)pl;
            bol("wedge_on", s.wedge_fitted); bol("pier", s.pier_extension); bol("derot", s.roll_derotate);
            num("park_az", s.park_az); num("park_alt", s.park_alt); num("guide", s.guide_rate);
            for (int i = 0; i < 3; i++) { char k[8]; snprintf(k, sizeof k, "inv%d", i); bol(k, s.dir_invert[i]); snprintf(k, sizeof k, "einv%d", i); bol(k, s.enc_invert[i]); }
            str("ssid", wifi_ssid); str("psk", wifi_psk); str("name", s.name);
            cJSON_Delete(j);
        }
    }
    nvs_close(h);
}

void settings_save(const Settings &s, const std::string &ssid, const std::string &psk)
{
    wifi_ssid = ssid;
    wifi_psk = psk;
    cJSON *j = cJSON_CreateObject();
    cJSON_AddNumberToObject(j, "lat", s.site.lat); cJSON_AddNumberToObject(j, "lon", s.site.lon); cJSON_AddNumberToObject(j, "elev", s.site.elev_m);
    cJSON_AddNumberToObject(j, "p", s.site.pressure_hpa); cJSON_AddNumberToObject(j, "t", s.site.temp_c); cJSON_AddBoolToObject(j, "refr", s.site.refraction);
    cJSON_AddNumberToObject(j, "wedge", s.wedge_deg); cJSON_AddNumberToObject(j, "az0", s.az0_deg);
    cJSON_AddNumberToObject(j, "mode", s.mode == MountMode::Equatorial ? 1 : 0); cJSON_AddNumberToObject(j, "payload", s.payload);
    cJSON_AddBoolToObject(j, "wedge_on", s.wedge_fitted); cJSON_AddBoolToObject(j, "pier", s.pier_extension); cJSON_AddBoolToObject(j, "derot", s.roll_derotate);
    cJSON_AddNumberToObject(j, "park_az", s.park_az); cJSON_AddNumberToObject(j, "park_alt", s.park_alt); cJSON_AddNumberToObject(j, "guide", s.guide_rate);
    for (int i = 0; i < 3; i++) { char k[8]; snprintf(k, sizeof k, "inv%d", i); cJSON_AddBoolToObject(j, k, s.dir_invert[i]); snprintf(k, sizeof k, "einv%d", i); cJSON_AddBoolToObject(j, k, s.enc_invert[i]); }
    cJSON_AddStringToObject(j, "ssid", ssid.c_str()); cJSON_AddStringToObject(j, "psk", psk.c_str()); cJSON_AddStringToObject(j, "name", s.name.c_str());
    char *t = cJSON_PrintUnformatted(j);
    nvs_handle_t h;
    if (nvs_open("st", NVS_READWRITE, &h) == ESP_OK) { nvs_set_str(h, "cfg", t); nvs_commit(h); nvs_close(h); }
    cJSON_free(t);
    cJSON_Delete(j);
}

// ---------------------------------------------------------------- tasks
static void tracker_task(void *)
{
    head->push_motion_config();
    TickType_t last = xTaskGetTickCount();
    std::string saved;
    int n = 0;
    for (;;) {
        vTaskDelayUntil(&last, pdMS_TO_TICKS(100));
        head->tick();
        if (++n % 100 == 0) {                                     // every 10 s: persist changed settings
            Settings s = head->settings();
            char sig[160];
            snprintf(sig, sizeof sig, "%.5f%.5f%d%d%.2f%.2f%d%d%d", s.site.lat, s.site.lon, (int)s.mode, s.payload, s.park_az, s.park_alt, s.wedge_fitted, s.pier_extension, s.roll_derotate);
            if (saved != sig) { if (!saved.empty()) settings_save(s, wifi_ssid, wifi_psk); saved = sig; }
        }
    }
}

static void power_task(void *)
{
    for (;;) {
        PackStatus p;
        PowerInputs in;
        if (gauge_read(p)) {
            in.pack_ok = true; in.pack_v = p.mv / 1000.0; in.soc = p.soc; in.pack_temp_c = p.temp_c;
            in.cycles = p.cycles; in.soh_pct = p.soh;                // D79: passed on to health.get
            in.cell_v[0] = p.cell1_mv / 1000.0; in.cell_v[1] = p.cell2_mv / 1000.0;
        }
        else { in.pack_v = vsys_volts(); }
        PdStatus a, b;
        pd_a.status(a);
        pd_b.status(b);
        in.charging = a.plug && !a.source && a.contract_v > 4.5f;
        in.porta_source_w = a.plug && a.source ? a.contract_v * a.contract_a : 0;
        in.portb_w = b.plug ? b.contract_v * b.contract_a : 0;   // advertised contract: an upper bound on the camera draw
        Vec3 acc;
        float tc = 25;
        imu_read(acc, tc);
        in.inside_temp_c = tc;                                    // the IMU's die is the inside-air proxy
        head->on_power(in);
        PowerDecision d = head->state().power;
        static uint16_t last_ichg = 0;
        if (in.charging && d.charge_ma != last_ichg && charger_set_ichg(d.charge_ma)) last_ichg = d.charge_ma;
        // port B: on while a sink is attached; the 15 W re-advertising needs the TPS25752 image's second source-PDO set (section 9)
        portb_enable(true);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

static void sensors_task(void *)
{
    Vec3 a0;
    float t;
    bool have0 = false;
    int64_t t0 = 0;
    for (;;) {
        gnss_poll();
        Vec3 a;
        if (imu_read(a, t)) {
            int64_t now = esp_timer_get_time();
            if (!have0 || now - t0 > 500000) { a0 = a; t0 = now; have0 = true; }
            double dot = (a.x * a0.x + a.y * a0.y + a.z * a0.z) / (std::sqrt(a.x * a.x + a.y * a.y + a.z * a.z) * std::sqrt(a0.x * a0.x + a0.y * a0.y + a0.z * a0.z) + 1e-9);
            if (std::acos(std::fmin(1.0, dot)) * 180 / M_PI > 3.0) {   // tripod going over (spec 7.3)
                head->abort();
                ESP_LOGW(TAG, "tilt change > 3 deg in 0.5 s: all axes stopped");
                have0 = false;
            }
        }
        const GnssFix &g = gnss();
        static bool site_set = false;
        if (g.fix && !site_set && g.num_sv >= 6) {               // first fix: take the position
            Settings s = head->settings();
            if (std::fabs(s.site.lat - g.lat) > 0.01 || std::fabs(s.site.lon - g.lon) > 0.01) {
                s.site.lat = g.lat; s.site.lon = g.lon; s.site.elev_m = g.h_msl;
                head->apply_settings(s);
            }
            site_set = true;
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

static void shutter_cb(void *)
{
    Intervalometer &iv = head->intervalometer();
    iv.tick(head_us() / 1e6);
    shutter_focus(iv.focus);
    shutter_release(iv.release);
}

// ---------------------------------------------------------------- UI: OLED, four buttons, three LEDs (D7, D56)
static void ui_task(void *)
{
    int page = 0, held14 = 0, held1 = 0;
    int last_b = 0;
    for (;;) {
        int b = buttons();
        int press = b & ~last_b;
        last_b = b;
        if ((b & 9) == 9) { if (++held14 == 10) head->abort(); } else held14 = 0;    // buttons 1 + 4 held 1 s: stop all
        if (b == 1) { if (++held1 == 30) { night = !night; } } else held1 = 0;       // button 1 held 3 s: night mode
        if (press & 2) page = (page + 3) % 4;
        if (press & 4) page = (page + 1) % 4;
        HeadState s = head->state();
        if (press & 8) {                                          // button 4: action of the page
            if (page == 0) head->set_tracking(!s.tracking);
            if (page == 1) { if (s.at_park) head->unpark(); else head->park(); }
            if (page == 3) { Settings c = head->settings(); c.payload = c.payload % 5 + 1; head->apply_settings(c); }
        }
        oled.contrast(night ? 1 : 0x80);
        oled.clear();
        char l[24];
        static const char *act[] = {"idle", "slewing", "tracking", "moving", "parking", "parked", "FAULT"};
        snprintf(l, sizeof l, "%-9s bat %3d%%", act[(int)s.activity], s.soc);
        oled.text(0, 0, l, true);
        if (page == 0) {
            int hh, mm; double ss; hours_to_hms(s.ra2000_h, hh, mm, ss);
            snprintf(l, sizeof l, "RA  %02dh%02dm%04.1fs", hh, mm, ss); oled.text(0, 2, l);
            int sg, dd, dm; double ds; deg_to_dms(s.dec2000_d, sg, dd, dm, ds);
            snprintf(l, sizeof l, "Dec %c%02d %02d'%02.0f\"", sg < 0 ? '-' : '+', dd, dm, ds); oled.text(0, 3, l);
            snprintf(l, sizeof l, "Az %6.2f Alt %5.2f", s.az_deg, s.alt_deg); oled.text(0, 4, l);
            oled.text(0, 7, s.tracking ? "4: stop tracking" : "4: track here");
        } else if (page == 1) {
            snprintf(l, sizeof l, "roll %7.2f deg", s.ax[2].cmd_deg); oled.text(0, 2, l);
            snprintf(l, sizeof l, "motor rail %4.1f V", s.vmot); oled.text(0, 3, l);
            snprintf(l, sizeof l, "GNSS %d sv %s", gnss().num_sv, head_time_quality() >= 3 ? "PPS" : ""); oled.text(0, 4, l);
            oled.text(0, 7, s.at_park ? "4: unpark" : "4: park");
        } else if (page == 2) {
            oled.text(0, 2, net_ap_ssid());
            snprintf(l, sizeof l, "pw %s", net_ap_pass()); oled.text(0, 3, l);
            snprintf(l, sizeof l, "IP %s", net_sta_ip().empty() ? "192.168.4.1" : net_sta_ip().c_str()); oled.text(0, 4, l);
            snprintf(l, sizeof l, "BLE code %06lu", (unsigned long)ble_passkey()); oled.text(0, 5, l);
        } else {
            Settings c = head->settings();
            snprintf(l, sizeof l, "payload P%d %s", c.payload, c.wedge_fitted ? "wedge" : "no wedge"); oled.text(0, 2, l);
            oled.text(0, 3, PAYLOADS[c.payload - 1].name + 3);
            oled.text(0, 7, "4: next payload");
        }
        if (!s.faults.empty()) oled.text(0, 6, s.faults.back().substr(0, 21).c_str());
        oled.flush();
        // LEDs: red = fault (or the only colour in night mode), green blink = tracking, blue = slewing
        bool blink = (esp_timer_get_time() / 500000) & 1;
        bool fault = s.motion_faults != 0 || !s.link_ok;
        if (night) { led_set(Led::R, fault || (s.tracking && blink) ? 4 : 0); led_set(Led::G, 0); led_set(Led::B, 0); }
        else {
            led_set(Led::R, fault ? 255 : 0);
            led_set(Led::G, s.tracking && blink ? 60 : 0);
            led_set(Led::B, s.slewing ? 60 : 0);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void app_run()
{
    if (nvs_flash_init() != ESP_OK) { nvs_flash_erase(); nvs_flash_init(); }
    io_init();
    i2c_main.init(0, ESP_GPIO_I2C_SDA, ESP_GPIO_I2C_SCL, 400000);
    i2c_pack.init(1, ESP_GPIO_PACK_SDA, ESP_GPIO_PACK_SCL, 100000);
    oled.init();
    oled.text(0, 0, "Canopus", true);
    oled.text(0, 2, "starting...");
    oled.flush();
    imu_init();
    mag_init();
    gnss_init();
    Settings s;
    settings_load(s);
    head = new Head(port, [] { return (int64_t)head_us(); });
    head->on_set_time = [](double s) { clock_set_unix((int64_t)(s * 1e6)); };   // time.set from the apps (Phase 6 fix)
    if (FileStore *fs = storage_start()) {                         // D78: fault log survives a restart
        head->restore_fault_log(fs->load_faults());
        head->on_fault_logged = [fs](const FaultEntry &e) { fs->append_fault(e); };
        head->on_faults_cleared = [fs] { fs->clear_faults(); };
    }
    link_init([](uint8_t type, const uint8_t *p, size_t n) { if (head) head->on_motion(type, p, n); });
    clock_update();
    ota_boot_check();                                             // RP2354A present? pending update to verify?
    head->apply_settings(s);
    net_wifi_start(wifi_ssid, wifi_psk);
    net_servers_start(*head);
    ble_start(*head, s.name);
    xTaskCreatePinnedToCore(tracker_task, "tracker", 8192, nullptr, 18, nullptr, 1);
    xTaskCreatePinnedToCore(power_task, "power", 6144, nullptr, 12, nullptr, 1);
    xTaskCreatePinnedToCore(sensors_task, "sensors", 6144, nullptr, 10, nullptr, 1);
    xTaskCreatePinnedToCore(ui_task, "ui", 6144, nullptr, 8, nullptr, 1);
    esp_timer_create_args_t ta = {};
    ta.callback = shutter_cb;
    ta.name = "shutter";
    esp_timer_handle_t th;
    esp_timer_create(&ta, &th);
    esp_timer_start_periodic(th, 10000);                          // 10 ms shutter resolution
    ESP_LOGI(TAG, "running");
}

// Sleep (Phase 4 section 10.5 step 6): drivers and rail off (POWER 0), RP2354A in reset, GNSS backup, deep sleep.
void app_sleep()
{
    st_power_t p = {0, 0, 0};
    link_send(ST_MSG_POWER, &p, sizeof p);
    vTaskDelay(pdMS_TO_TICKS(100));
    rp_reset(true);
    gnss_backup();
    oled.power(false);
    uint64_t mask = (1ULL << ESP_GPIO_BTN1) | (1ULL << ESP_GPIO_BTN2) | (1ULL << ESP_GPIO_BTN3) | (1ULL << ESP_GPIO_BTN4) |
                    (1ULL << ESP_GPIO_WAKE_IRQ_N) | (1ULL << ESP_GPIO_PWR_IRQ_N);
    esp_sleep_enable_ext1_wakeup(mask, ESP_EXT1_WAKEUP_ANY_LOW);
    esp_deep_sleep_start();
}

}  // namespace st
