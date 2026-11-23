// Star Tracker ESP32-S3 — BLE set-up service (spec 7.2): Wi-Fi set-up (write), status (read/notify), command (write,
// limited to stop, park and wifi.*). Pairing with a 6-digit passkey shown on the OLED (D71). NimBLE host.
#include "st_app_int.h"
#include "sdkconfig.h"

#if CONFIG_BT_ENABLED
#include <cstring>
#include "cJSON.h"
#include "esp_random.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

namespace st {

static Head *H;
static uint32_t passkey;
static uint16_t status_handle;
static std::string dev_name;
uint32_t ble_passkey() { return passkey; }

// 128-bit UUIDs: base 5354524b-xxxx-4d2a-9b1e-0000000000xx ("STRK")
static const ble_uuid128_t SVC = BLE_UUID128_INIT(0x01, 0, 0, 0, 0, 0, 0x1e, 0x9b, 0x2a, 0x4d, 0x00, 0x01, 0x4b, 0x52, 0x54, 0x53);
static const ble_uuid128_t CH_WIFI = BLE_UUID128_INIT(0x02, 0, 0, 0, 0, 0, 0x1e, 0x9b, 0x2a, 0x4d, 0x00, 0x01, 0x4b, 0x52, 0x54, 0x53);
static const ble_uuid128_t CH_STATUS = BLE_UUID128_INIT(0x03, 0, 0, 0, 0, 0, 0x1e, 0x9b, 0x2a, 0x4d, 0x00, 0x01, 0x4b, 0x52, 0x54, 0x53);
static const ble_uuid128_t CH_CMD = BLE_UUID128_INIT(0x04, 0, 0, 0, 0, 0, 0x1e, 0x9b, 0x2a, 0x4d, 0x00, 0x01, 0x4b, 0x52, 0x54, 0x53);

static std::string status_json()
{
    HeadState s = H->state();
    char b[160];
    snprintf(b, sizeof b, "{\"ip\":\"%s\",\"ap\":\"%s\",\"soc\":%d,\"mode\":\"%s\",\"fw\":\"0.1.0\"}", net_sta_ip().c_str(), net_ap_ssid(), s.soc,
             s.tracking ? "tracking" : (s.at_park ? "parked" : "idle"));
    return b;
}

static int access(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr;
    int which = (int)(intptr_t)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        std::string s = status_json();
        return os_mbuf_append(ctxt->om, s.data(), s.size()) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    if (ctxt->op != BLE_GATT_ACCESS_OP_WRITE_CHR) return BLE_ATT_ERR_UNLIKELY;
    char buf[256];
    uint16_t n = 0;
    if (ble_hs_mbuf_to_flat(ctxt->om, buf, sizeof buf - 1, &n) != 0) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
    buf[n] = 0;
    cJSON *j = cJSON_Parse(buf);
    if (!j) return BLE_ATT_ERR_UNLIKELY;
    if (which == 1) {                                     // {"ssid":"...","psk":"...","mode":"sta"}
        cJSON *ss = cJSON_GetObjectItem(j, "ssid"), *pk = cJSON_GetObjectItem(j, "psk");
        if (cJSON_IsString(ss)) settings_save(H->settings(), ss->valuestring, cJSON_IsString(pk) ? pk->valuestring : "");
    } else if (which == 3) {                              // WebSocket request format, limited set
        cJSON *op = cJSON_GetObjectItem(j, "op");
        std::string o = cJSON_IsString(op) ? op->valuestring : "";
        if (o == "stop") H->abort();
        else if (o == "park") H->park();
    }
    cJSON_Delete(j);
    return 0;
}

static const struct ble_gatt_chr_def chrs[] = {
    {.uuid = &CH_WIFI.u, .access_cb = access, .arg = (void *)1, .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_ENC | BLE_GATT_CHR_F_WRITE_AUTHEN},
    {.uuid = &CH_STATUS.u, .access_cb = access, .arg = (void *)2, .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY, .val_handle = &status_handle},
    {.uuid = &CH_CMD.u, .access_cb = access, .arg = (void *)3, .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_ENC},
    {},
};
static const struct ble_gatt_svc_def svcs[] = {{.type = BLE_GATT_SVC_TYPE_PRIMARY, .uuid = &SVC.u, .characteristics = chrs}, {}};

static void advertise();
static int gap_event(struct ble_gap_event *e, void *)
{
    if (e->type == BLE_GAP_EVENT_DISCONNECT || (e->type == BLE_GAP_EVENT_CONNECT && e->connect.status != 0)) advertise();
    if (e->type == BLE_GAP_EVENT_PASSKEY_ACTION && e->passkey.params.action == BLE_SM_IOACT_DISP) {
        struct ble_sm_io io = {};
        io.action = BLE_SM_IOACT_DISP;
        io.passkey = passkey;
        ble_sm_inject_io(e->passkey.conn_handle, &io);
    }
    return 0;
}

static void advertise()
{
    struct ble_hs_adv_fields f = {};
    f.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    f.name = (const uint8_t *)dev_name.c_str();
    f.name_len = (uint8_t)dev_name.size();
    f.name_is_complete = 1;
    ble_gap_adv_set_fields(&f);
    struct ble_gap_adv_params p = {};
    p.conn_mode = BLE_GAP_CONN_MODE_UND;
    p.disc_mode = BLE_GAP_DISC_MODE_GEN;
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, nullptr, BLE_HS_FOREVER, &p, gap_event, nullptr);
}

static void on_sync() { advertise(); }
static void host_task(void *) { nimble_port_run(); nimble_port_freertos_deinit(); }

void ble_start(Head &head, const std::string &name)
{
    H = &head;
    dev_name = name;
    passkey = esp_random() % 1000000;
    if (nimble_port_init() != ESP_OK) return;
    ble_hs_cfg.sync_cb = on_sync;
    ble_hs_cfg.sm_io_cap = BLE_SM_IO_CAP_DISP_ONLY;      // the OLED shows the code
    ble_hs_cfg.sm_bonding = 1;
    ble_hs_cfg.sm_mitm = 1;
    ble_hs_cfg.sm_sc = 1;
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_gatts_count_cfg(svcs);
    ble_gatts_add_svcs(svcs);
    ble_svc_gap_device_name_set(name.c_str());
    nimble_port_freertos_init(host_task);
}

}  // namespace st

#else  // Bluetooth off (the bring-up image): no BLE service, no passkey

namespace st {
void ble_start(Head &, const std::string &) {}
uint32_t ble_passkey() { return 0; }
}  // namespace st

#endif
