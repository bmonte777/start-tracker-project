// Star Tracker ESP32-S3 — updates for both processors (Q49).
//
// Bundle (.stfw, made by firmware/tools/make_bundle.py):
//   header 64 bytes: "STFW" | u32 version 1 | u32 entries | u32 reserved | then per entry (up to 2, 24 bytes each):
//   u8 type (1 = ESP32 app, 2 = RP2354A image) | u8[3] pad | u32 offset | u32 size | u8[12] first 12 bytes of SHA-256
//   followed by the images; a full SHA-256 of each image is checked while it is written.
// rp_img partition (1 MB): 0x00000 "good" slot, 0x80000 "new" slot; each slot = u32 magic 'RPIM', u32 size, u32 crc32,
// then the image at +0x1000.
#include "st_app_int.h"
#include <cstring>
#include "esp_app_desc.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mbedtls/sha256.h"
#include "st_link_esp.h"
#include "st_swd.h"

extern const uint8_t rp_motion_bin_start[] asm("_binary_rp_motion_bin_start");
extern const uint8_t rp_motion_bin_end[] asm("_binary_rp_motion_bin_end");
extern const uint8_t rp_flashstub_bin_start[] asm("_binary_rp_flashstub_bin_start");
extern const uint8_t rp_flashstub_bin_end[] asm("_binary_rp_flashstub_bin_end");

namespace st {

static const char *TAG = "ota";
static const uint32_t RPIM = 0x4D495052u, GOOD = 0x00000, NEW = 0x80000;

static const esp_partition_t *rp_part()
{
    return esp_partition_find_first(ESP_PARTITION_TYPE_DATA, (esp_partition_subtype_t)0x41, "rp_img");
}

static uint32_t crc32(const uint8_t *p, size_t n, uint32_t c = 0xFFFFFFFFu)
{
    while (n--) { c ^= *p++; for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u))); }
    return c;
}

esp_err_t ota_upload_handler(httpd_req_t *req)
{
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");   // the apps upload from their own pages (API 1.1)
    uint8_t hdr[64];
    int got = 0;
    while (got < 64) { int n = httpd_req_recv(req, (char *)hdr + got, 64 - got); if (n <= 0) return ESP_FAIL; got += n; }
    uint32_t ver, entries;
    memcpy(&ver, hdr + 4, 4);
    memcpy(&entries, hdr + 8, 4);
    if (memcmp(hdr, "STFW", 4) || ver != 1 || entries == 0 || entries > 2) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "not a Star Tracker bundle");
        return ESP_FAIL;
    }
    struct E { uint8_t type; uint32_t off, size; uint8_t sha12[12]; } e[2] = {};
    for (uint32_t i = 0; i < entries; i++) {
        const uint8_t *p = hdr + 16 + 24 * i;
        e[i].type = p[0];
        memcpy(&e[i].off, p + 4, 4);
        memcpy(&e[i].size, p + 8, 4);
        memcpy(e[i].sha12, p + 12, 12);
    }
    size_t pos = 64;
    std::string buf(4096, '\0');
    bool ok = true;
    for (uint32_t i = 0; i < entries && ok; i++) {
        while (pos < e[i].off) { int n = httpd_req_recv(req, &buf[0], std::min<size_t>(4096, e[i].off - pos)); if (n <= 0) return ESP_FAIL; pos += n; }
        mbedtls_sha256_context sha;
        mbedtls_sha256_init(&sha);
        mbedtls_sha256_starts(&sha, 0);
        esp_ota_handle_t oh = 0;
        const esp_partition_t *next = nullptr;
        const esp_partition_t *rp = rp_part();
        uint32_t crc = 0xFFFFFFFFu;
        if (e[i].type == 1) {
            next = esp_ota_get_next_update_partition(nullptr);
            if (!next || esp_ota_begin(next, e[i].size, &oh) != ESP_OK) ok = false;
        } else if (e[i].type == 2) {
            if (!rp || e[i].size > 0x7F000 || esp_partition_erase_range(rp, NEW, 0x80000) != ESP_OK) ok = false;
        }
        size_t done = 0;
        while (ok && done < e[i].size) {
            int n = httpd_req_recv(req, &buf[0], std::min<size_t>(4096, e[i].size - done));
            if (n <= 0) { ok = false; break; }
            mbedtls_sha256_update(&sha, (const uint8_t *)buf.data(), n);
            if (e[i].type == 1) ok = esp_ota_write(oh, buf.data(), n) == ESP_OK;
            else { ok = esp_partition_write(rp, NEW + 0x1000 + done, buf.data(), n) == ESP_OK; crc = crc32((const uint8_t *)buf.data(), n, crc); }
            done += n;
            pos += n;
        }
        uint8_t dig[32];
        mbedtls_sha256_finish(&sha, dig);
        mbedtls_sha256_free(&sha);
        if (ok && memcmp(dig, e[i].sha12, 12)) { ok = false; ESP_LOGE(TAG, "SHA-256 mismatch on entry %u", (unsigned)i); }
        if (e[i].type == 1) {
            if (ok) ok = esp_ota_end(oh) == ESP_OK && esp_ota_set_boot_partition(next) == ESP_OK;
            else if (oh) esp_ota_abort(oh);
        } else if (ok) {
            uint32_t h[3] = {RPIM, e[i].size, ~crc};
            ok = esp_partition_write(rp, NEW, h, sizeof h) == ESP_OK;
        }
    }
    if (!ok) { httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "update failed; nothing changed"); return ESP_FAIL; }
    httpd_resp_sendstr(req, "update stored; the head restarts and checks both processors");
    vTaskDelay(pdMS_TO_TICKS(500));
    esp_restart();
    return ESP_OK;
}

// update.status (API 1.1): which slot runs, whether the previous one can be returned to, the RP2354A copies
void ota_status_json(cJSON *o)
{
    const esp_partition_t *run = esp_ota_get_running_partition();
    const esp_partition_t *last = esp_ota_get_last_invalid_partition();
    esp_ota_img_states_t st = ESP_OTA_IMG_UNDEFINED;
    if (run) esp_ota_get_state_partition(run, &st);
    cJSON_AddStringToObject(o, "running_slot", run ? run->label : "?");
    cJSON_AddStringToObject(o, "running_state", st == ESP_OTA_IMG_VALID ? "valid" : st == ESP_OTA_IMG_PENDING_VERIFY ? "pending_verify" : "undefined");
    cJSON_AddBoolToObject(o, "rollback_possible", esp_ota_check_rollback_is_possible());
    cJSON_AddStringToObject(o, "last_invalid_slot", last ? last->label : "");
    const esp_partition_t *rp = rp_part();
    uint32_t g[3] = {}, n[3] = {};
    if (rp) { esp_partition_read(rp, GOOD, g, sizeof g); esp_partition_read(rp, NEW, n, sizeof n); }
    cJSON_AddBoolToObject(o, "rp_good_copy", g[0] == RPIM);
    cJSON_AddNumberToObject(o, "rp_good_size", g[0] == RPIM ? g[1] : 0);
    cJSON_AddBoolToObject(o, "rp_new_pending", n[0] == RPIM);
    const esp_app_desc_t *d = esp_app_get_description();
    cJSON_AddStringToObject(o, "esp_build", d ? d->version : "");
}

static bool flash_rp_from_slot(uint32_t slot, std::string &log)
{
    const esp_partition_t *rp = rp_part();
    uint32_t h[3] = {};
    if (!rp || esp_partition_read(rp, slot, h, sizeof h) != ESP_OK || h[0] != RPIM || h[1] == 0 || h[1] > 0x7F000) return false;
    std::string img(h[1], '\0');
    esp_partition_read(rp, slot + 0x1000, &img[0], h[1]);
    if (~crc32((const uint8_t *)img.data(), img.size()) != h[2]) { log += "stored RP2354A image is damaged\n"; return false; }
    return swd.flash(rp_flashstub_bin_start, rp_flashstub_bin_end - rp_flashstub_bin_start, (const uint8_t *)img.data(), img.size(), nullptr, log);
}

static bool wait_hello(int ms)
{
    st_hello_t q = {ST_LINK_VERSION, 0, 1, 0, 0, {'A', 'P', 'P', 'R'}};
    for (int t = 0; t < ms; t += 100) {
        if (t % 1000 == 0) link_send(ST_MSG_HELLO, &q, sizeof q);
        vTaskDelay(pdMS_TO_TICKS(100));
        if (link_stats().have_hello && link_stats().hello.proto == ST_LINK_VERSION && link_stats().rp_alive) return true;
    }
    return false;
}

// Called once at start-up, after the link is running.
void ota_boot_check()
{
    std::string log;
    const esp_partition_t *rp = rp_part();
    uint32_t hn[3] = {};
    bool have_new = rp && esp_partition_read(rp, NEW, hn, sizeof hn) == ESP_OK && hn[0] == RPIM;
    esp_ota_img_states_t st = ESP_OTA_IMG_VALID;
    esp_ota_get_state_partition(esp_ota_get_running_partition(), &st);
    bool pending = st == ESP_OTA_IMG_PENDING_VERIFY;
    if (have_new) {
        ESP_LOGI(TAG, "new RP2354A image waiting: flashing it");
        bool ok = flash_rp_from_slot(NEW, log) && wait_hello(3000);
        if (ok) {                                             // promote new -> good
            std::string img(hn[1] + 0x1000, '\0');
            esp_partition_read(rp, NEW, &img[0], img.size());
            esp_partition_erase_range(rp, GOOD, 0x80000);
            esp_partition_write(rp, GOOD, img.data(), img.size());
            esp_partition_erase_range(rp, NEW, 0x1000);
        } else {
            ESP_LOGE(TAG, "new RP2354A image failed: restoring the last good one\n%s", log.c_str());
            esp_partition_erase_range(rp, NEW, 0x1000);
            flash_rp_from_slot(GOOD, log);
            if (pending) { esp_ota_mark_app_invalid_rollback_and_reboot(); }
        }
    } else if (!wait_hello(3000)) {
        ESP_LOGW(TAG, "RP2354A silent: rewriting its last good image");
        if (!flash_rp_from_slot(GOOD, log)) {                 // first start: no good slot yet -> the image built into this firmware
            size_t n = rp_motion_bin_end - rp_motion_bin_start;
            if (n > 1024) swd.flash(rp_flashstub_bin_start, rp_flashstub_bin_end - rp_flashstub_bin_start, rp_motion_bin_start, n, nullptr, log);
        }
        wait_hello(3000);
    }
    if (pending) {
        if (link_stats().rp_alive) esp_ota_mark_app_valid_cancel_rollback();
        else esp_ota_mark_app_invalid_rollback_and_reboot();
    }
}

}  // namespace st
