# RP2354A images are copied into main/embed by the build workflow (.github/workflows/firmware.yml);
# empty placeholders keep a stand-alone ESP32 build working (the menu then says "no image embedded").
set(EMBED ${CMAKE_CURRENT_LIST_DIR}/../../main/embed)
foreach(f rp_bringup.bin rp_motion.bin rp_flashstub.bin)
  if(NOT EXISTS ${EMBED}/${f})
    file(WRITE ${EMBED}/${f} "")
  endif()
endforeach()
idf_component_register(SRCS "bringup.cpp" "swd.cpp"
                       INCLUDE_DIRS "include"
                       REQUIRES st_hal st_common esp_driver_usb_serial_jtag esp_driver_gpio esp_partition esp_app_format esp_timer
                       EMBED_FILES "${EMBED}/rp_bringup.bin" "${EMBED}/rp_motion.bin" "${EMBED}/rp_flashstub.bin")
