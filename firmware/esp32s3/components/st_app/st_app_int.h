// Star Tracker ESP32-S3 — internals shared by the system-firmware files.
#pragma once
#include <string>
#include "esp_http_server.h"
#include "st_head.h"
#include "st_proto.h"

namespace st {
Head *app_head();
void net_wifi_start(const std::string &ssid, const std::string &psk);
void net_servers_start(Head &head);
const char *net_ap_ssid();
const char *net_ap_pass();
std::string net_sta_ip();
esp_err_t ota_upload_handler(httpd_req_t *req);
void ota_boot_check();
void ble_start(Head &head, const std::string &name);
uint32_t ble_passkey();
void settings_save(const Settings &s, const std::string &ssid, const std::string &psk);
}  // namespace st
