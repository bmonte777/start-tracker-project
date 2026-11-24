idf_component_register(SRCS "app.cpp" "net.cpp" "ota.cpp" "ble.cpp" "storage.cpp"
                       INCLUDE_DIRS "include" "."
                       REQUIRES st_hal st_sys st_core st_proto st_common json esp_http_server esp_wifi esp_netif nvs_flash app_update
                                esp_partition mbedtls bt esp_timer
                       EMBED_FILES "../../../common/web/index.html")
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-missing-field-initializers)
