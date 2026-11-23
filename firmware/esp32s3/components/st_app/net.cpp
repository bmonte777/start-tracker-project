// Star Tracker ESP32-S3 — network transports for the portable protocol handlers:
// Wi-Fi (access point + station), HTTP on port 80 (web page, WebSocket /ws/v1, Alpaca, update upload),
// HTTP on port 32323 (Alpaca), Alpaca discovery on UDP 32227, LX200 on TCP 4030, BLE set-up (NimBLE GATT).
#include "st_app_int.h"
#include <algorithm>
#include <cstring>
#include <map>
#include <mutex>
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_random.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "nvs_flash.h"

extern const char web_index_html_start[] asm("_binary_index_html_start");
extern const char web_index_html_end[] asm("_binary_index_html_end");

namespace st {

static const char *TAG = "net";
static Alpaca *alpaca;
static WsApi *wsapi;
static std::mutex proto_mu;
static httpd_handle_t web, alp;
static char ap_ssid[33], ap_pass[17];
static std::string sta_ip = "";

const char *net_ap_ssid() { return ap_ssid; }
const char *net_ap_pass() { return ap_pass; }
std::string net_sta_ip() { return sta_ip; }

// ---------------------------------------------------------------- Wi-Fi
static void on_ip(void *, esp_event_base_t, int32_t, void *data)
{
    auto *e = (ip_event_got_ip_t *)data;
    char b[20];
    snprintf(b, sizeof b, IPSTR, IP2STR(&e->ip_info.ip));
    sta_ip = b;
    ESP_LOGI(TAG, "station IP %s", b);
}

void net_wifi_start(const std::string &ssid, const std::string &psk)
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_ap();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, on_ip, nullptr);
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_WIFI_SOFTAP);
    snprintf(ap_ssid, sizeof ap_ssid, "StarTracker-%02X%02X", mac[4], mac[5]);
    // password shown on the OLED (D71): derived from the MAC so it is stable per head, 10 characters
    snprintf(ap_pass, sizeof ap_pass, "st%02x%02x%02x%02x", mac[2] ^ 0x5A, mac[3] ^ 0xA5, mac[4] ^ 0x3C, mac[5] ^ 0xC3);
    wifi_config_t ap = {};
    memcpy(ap.ap.ssid, ap_ssid, strlen(ap_ssid));
    memcpy(ap.ap.password, ap_pass, strlen(ap_pass));
    ap.ap.ssid_len = (uint8_t)strlen(ap_ssid);
    ap.ap.channel = 6;
    ap.ap.max_connection = 4;
    ap.ap.authmode = WIFI_AUTH_WPA2_PSK;
    esp_wifi_set_mode(ssid.empty() ? WIFI_MODE_AP : WIFI_MODE_APSTA);
    esp_wifi_set_config(WIFI_IF_AP, &ap);
    if (!ssid.empty()) {
        wifi_config_t sta = {};
        memcpy(sta.sta.ssid, ssid.data(), std::min(ssid.size(), sizeof sta.sta.ssid));
        memcpy(sta.sta.password, psk.data(), std::min(psk.size(), sizeof sta.sta.password - 1));
        esp_wifi_set_config(WIFI_IF_STA, &sta);
    }
    esp_wifi_start();
    if (!ssid.empty()) esp_wifi_connect();
}

// ---------------------------------------------------------------- HTTP helpers
static void params_from(const std::string &s, std::map<std::string, std::string> &out)
{
    size_t i = 0;
    while (i < s.size()) {
        size_t a = s.find('&', i);
        std::string kv = s.substr(i, a == std::string::npos ? std::string::npos : a - i);
        size_t e = kv.find('=');
        auto dec = [](std::string v) {
            std::string o;
            for (size_t k = 0; k < v.size(); k++) {
                if (v[k] == '+') o += ' ';
                else if (v[k] == '%' && k + 2 < v.size()) { o += (char)strtol(v.substr(k + 1, 2).c_str(), nullptr, 16); k += 2; }
                else o += v[k];
            }
            return o;
        };
        if (!kv.empty()) out[dec(kv.substr(0, e))] = e == std::string::npos ? "" : dec(kv.substr(e + 1));
        if (a == std::string::npos) break;
        i = a + 1;
    }
}

static esp_err_t alpaca_handler(httpd_req_t *req)
{
    HttpRequest r;
    r.method = req->method == HTTP_PUT ? "PUT" : "GET";
    std::string uri = req->uri;
    size_t q = uri.find('?');
    r.path = uri.substr(0, q);
    if (q != std::string::npos) params_from(uri.substr(q + 1), r.params);
    if (req->content_len > 0 && req->content_len < 2048) {
        std::string body(req->content_len, '\0');
        int got = httpd_req_recv(req, &body[0], body.size());
        if (got > 0) { body.resize((size_t)got); params_from(body, r.params); }
    }
    HttpResponse h;
    {
        std::lock_guard<std::mutex> l(proto_mu);
        h = alpaca->handle(r);
    }
    char st[16];
    snprintf(st, sizeof st, "%d %s", h.status, h.status == 200 ? "OK" : "Bad Request");
    httpd_resp_set_status(req, st);
    httpd_resp_set_type(req, h.type.c_str());
    return httpd_resp_send(req, h.body.data(), (ssize_t)h.body.size());
}

static esp_err_t index_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, web_index_html_start, web_index_html_end - web_index_html_start);
}

// ---------------------------------------------------------------- API 1.1 HTTP routes (Phase 6, docs/06-apps.md section 4)
static void cors(httpd_req_t *req)
{
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Headers", "Content-Type");
}

static esp_err_t options_handler(httpd_req_t *req)          // CORS preflight from the apps' pages
{
    cors(req);
    httpd_resp_set_hdr(req, "Access-Control-Max-Age", "600");
    httpd_resp_set_status(req, "204 No Content");
    return httpd_resp_send(req, nullptr, 0);
}

static esp_err_t info_handler(httpd_req_t *req)             // GET /startracker/v1/info on port 80 and 32323
{
    std::string j;
    {
        std::lock_guard<std::mutex> l(proto_mu);
        j = wsapi->info_json(80, 32323, 4030);
    }
    cors(req);
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, j.data(), (ssize_t)j.size());
}

static esp_err_t op_handler(httpd_req_t *req)               // POST /startracker/v1/op: one request, one reply
{
    cors(req);
    if (req->content_len == 0 || req->content_len > 32768) { httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "body 1..32768 bytes"); return ESP_FAIL; }
    std::string body(req->content_len, '\0');
    size_t got = 0;
    while (got < body.size()) { int n = httpd_req_recv(req, &body[got], body.size() - got); if (n <= 0) return ESP_FAIL; got += (size_t)n; }
    std::string reply;
    {
        std::lock_guard<std::mutex> l(proto_mu);
        reply = wsapi->handle(body);
    }
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_send(req, reply.data(), (ssize_t)reply.size());
}

// mDNS (Q51): startracker.local, services _startracker._tcp and _http._tcp on port 80. The component comes from Espressif's
// registry (idf_component.yml), which the workflow can reach; without it the head still answers Alpaca discovery.
#if __has_include("mdns.h")
#include "mdns.h"
static void mdns_start(const std::string &name)
{
    if (mdns_init() != ESP_OK) return;
    mdns_hostname_set("startracker");
    mdns_instance_name_set(name.c_str());
    mdns_txt_item_t txt[] = {{"api", "1.1"}, {"ws", "/ws/v1"}, {"name", name.c_str()}};
    mdns_service_add(name.c_str(), "_startracker", "_tcp", 80, txt, 3);
    mdns_service_add(name.c_str(), "_http", "_tcp", 80, nullptr, 0);
    mdns_service_add(name.c_str(), "_alpaca", "_tcp", 32323, nullptr, 0);
}
#else
static void mdns_start(const std::string &) {}
#endif

// WebSocket: requests answered in the handler; state events pushed by a task to every open socket
static esp_err_t ws_handler(httpd_req_t *req)
{
    if (req->method == HTTP_GET) return ESP_OK;                // handshake done by httpd
    httpd_ws_frame_t f = {};
    f.type = HTTPD_WS_TYPE_TEXT;
    if (httpd_ws_recv_frame(req, &f, 0) != ESP_OK || f.len > 32768) return ESP_FAIL;   // job.start with 400 poses
    std::string text(f.len, '\0');
    f.payload = (uint8_t *)&text[0];
    if (httpd_ws_recv_frame(req, &f, f.len) != ESP_OK) return ESP_FAIL;
    std::string reply;
    {
        std::lock_guard<std::mutex> l(proto_mu);
        reply = wsapi->handle(text);
    }
    httpd_ws_frame_t o = {};
    o.type = HTTPD_WS_TYPE_TEXT;
    o.payload = (uint8_t *)reply.data();
    o.len = reply.size();
    return httpd_ws_send_frame(req, &o);
}

static void ws_push_task(void *)
{
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(200));                        // 5 events per second (spec 7.2)
        size_t n = 8;
        int fds[8];
        if (httpd_get_client_list(web, &n, fds) != ESP_OK || n == 0) continue;
        std::string ev;
        {
            std::lock_guard<std::mutex> l(proto_mu);
            ev = wsapi->state_event();
        }
        for (size_t i = 0; i < n; i++) {
            if (httpd_ws_get_fd_info(web, fds[i]) != HTTPD_WS_CLIENT_WEBSOCKET) continue;
            httpd_ws_frame_t o = {};
            o.type = HTTPD_WS_TYPE_TEXT;
            o.payload = (uint8_t *)ev.data();
            o.len = ev.size();
            httpd_ws_send_frame_async(web, fds[i], &o);
        }
    }
}

// ---------------------------------------------------------------- LX200 and discovery
static void lx200_task(void *)
{
    int s = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in a = {};
    a.sin_family = AF_INET;
    a.sin_port = htons(4030);
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    bind(s, (sockaddr *)&a, sizeof a);
    listen(s, 2);
    for (;;) {
        int c = accept(s, nullptr, nullptr);
        if (c < 0) continue;
        Lx200 lx(*app_head());
        char buf[128];
        for (;;) {
            int n = recv(c, buf, sizeof buf, 0);
            if (n <= 0) break;
            std::string out;
            {
                std::lock_guard<std::mutex> l(proto_mu);
                out = lx.feed(std::string(buf, (size_t)n));
            }
            if (!out.empty() && send(c, out.data(), out.size(), 0) < 0) break;
        }
        close(c);
    }
}

static void discovery_task(void *)
{
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    sockaddr_in a = {};
    a.sin_family = AF_INET;
    a.sin_port = htons(32227);
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    bind(s, (sockaddr *)&a, sizeof a);
    char buf[64];
    for (;;) {
        sockaddr_in from = {};
        socklen_t fl = sizeof from;
        int n = recvfrom(s, buf, sizeof buf - 1, 0, (sockaddr *)&from, &fl);
        if (n >= 16 && !memcmp(buf, Alpaca::DISCOVERY_QUERY, 16)) {
            std::string r = Alpaca::discovery_reply(32323);
            sendto(s, r.data(), r.size(), 0, (sockaddr *)&from, fl);
        }
    }
}

void net_servers_start(Head &head)
{
    alpaca = new Alpaca(head);
    wsapi = new WsApi(head);
    wsapi->services().platform = "head";
    wsapi->services().boot_id = esp_random() & 0x7FFFFFFF;
    wsapi->services().store = [](const std::string &key, const std::vector<int16_t> &v) {   // PEC tables, encoder maps
        nvs_handle_t h;
        if (nvs_open("st_tables", NVS_READWRITE, &h) != ESP_OK) return false;
        bool ok = nvs_set_blob(h, key.c_str(), v.data(), v.size() * sizeof(int16_t)) == ESP_OK && nvs_commit(h) == ESP_OK;
        nvs_close(h);
        return ok;
    };
    wsapi->services().update_status = [](cJSON *o) { ota_status_json(o); };
    mdns_start(head.settings().name);
    httpd_config_t c = HTTPD_DEFAULT_CONFIG();
    c.server_port = 80;
    c.ctrl_port = 32768;
    c.max_uri_handlers = 16;
    c.uri_match_fn = httpd_uri_match_wildcard;
    c.core_id = 0;
    c.stack_size = 8192;
    if (httpd_start(&web, &c) == ESP_OK) {
        httpd_uri_t u[] = {
            {"/", HTTP_GET, index_handler, nullptr, false, false, nullptr},
            {"/ws/v1", HTTP_GET, ws_handler, nullptr, true, false, nullptr},
            {"/api/update", HTTP_POST, ota_upload_handler, nullptr, false, false, nullptr},
            {"/api/v1/*", HTTP_GET, alpaca_handler, nullptr, false, false, nullptr},
            {"/api/v1/*", HTTP_PUT, alpaca_handler, nullptr, false, false, nullptr},
            {"/management/*", HTTP_GET, alpaca_handler, nullptr, false, false, nullptr},
            {"/startracker/v1/info", HTTP_GET, info_handler, nullptr, false, false, nullptr},
            {"/startracker/v1/op", HTTP_POST, op_handler, nullptr, false, false, nullptr},
            {"/startracker/v1/*", HTTP_OPTIONS, options_handler, nullptr, false, false, nullptr},
            {"/api/update", HTTP_OPTIONS, options_handler, nullptr, false, false, nullptr},
        };
        for (auto &h : u) httpd_register_uri_handler(web, &h);
    }
    httpd_config_t c2 = HTTPD_DEFAULT_CONFIG();
    c2.server_port = 32323;                                    // Alpaca (spec 7.2)
    c2.ctrl_port = 32769;
    c2.uri_match_fn = httpd_uri_match_wildcard;
    c2.core_id = 0;
    c2.stack_size = 8192;
    if (httpd_start(&alp, &c2) == ESP_OK) {
        httpd_uri_t u[] = {
            {"/api/v1/*", HTTP_GET, alpaca_handler, nullptr, false, false, nullptr},
            {"/api/v1/*", HTTP_PUT, alpaca_handler, nullptr, false, false, nullptr},
            {"/management/*", HTTP_GET, alpaca_handler, nullptr, false, false, nullptr},
            {"/startracker/v1/info", HTTP_GET, info_handler, nullptr, false, false, nullptr},
        };
        for (auto &h : u) httpd_register_uri_handler(alp, &h);
    }
    xTaskCreatePinnedToCore(ws_push_task, "wspush", 6144, nullptr, 5, nullptr, 0);
    xTaskCreatePinnedToCore(lx200_task, "lx200", 6144, nullptr, 5, nullptr, 0);
    xTaskCreatePinnedToCore(discovery_task, "alpdisc", 3072, nullptr, 5, nullptr, 0);
}

}  // namespace st
