// Star Tracker ESP32-S3 — persistent head data (decision D78): LittleFS on the "storage" partition, mounted at /storage.
// PEC tables, encoder maps and the fault log live there as files (st_filestore.h); settings stay in NVS.
// joltwallet/littlefs comes from Espressif's component registry (idf_component.yml); without it the head keeps
// these in RAM as before and says so (faults.get persistent = false, pec.save "no storage").
#include "st_app_int.h"
#include "esp_log.h"
#if __has_include("esp_littlefs.h")
#include "esp_littlefs.h"
#define ST_HAVE_LITTLEFS 1
#endif

namespace st {

static FileStore *g_store = nullptr;

FileStore *storage_start()
{
#ifdef ST_HAVE_LITTLEFS
    esp_vfs_littlefs_conf_t c = {};
    c.base_path = "/storage";
    c.partition_label = "storage";
    c.format_if_mount_failed = true;          // a new board: the partition is blank
    c.dont_mount = false;
    esp_err_t e = esp_vfs_littlefs_register(&c);
    if (e != ESP_OK) { ESP_LOGE("storage", "LittleFS mount failed: %s", esp_err_to_name(e)); return nullptr; }
    size_t total = 0, used = 0;
    esp_littlefs_info("storage", &total, &used);
    ESP_LOGI("storage", "LittleFS /storage: %u of %u bytes used", (unsigned)used, (unsigned)total);
    g_store = new FileStore("/storage");
    return g_store;
#else
    ESP_LOGW("storage", "built without LittleFS: tables and fault log kept in RAM");
    return nullptr;
#endif
}

FileStore *storage() { return g_store; }

}  // namespace st
