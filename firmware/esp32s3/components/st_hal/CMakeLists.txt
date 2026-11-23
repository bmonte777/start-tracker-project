idf_component_register(SRCS "i2c.cpp" "power_chips.cpp" "sensors.cpp" "oled_io.cpp" "link_clock.cpp"
                       INCLUDE_DIRS "include"
                       REQUIRES st_common esp_driver_i2c esp_driver_uart esp_driver_gpio esp_driver_ledc esp_adc esp_timer)
