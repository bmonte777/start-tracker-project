# Star Tracker — ESP32-S3 firmware (ESP-IDF 5.5). Two images from one source:
#   default                      the system firmware
#   -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.bringup"   the bring-up image (CONFIG_ST_BRINGUP=y)
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(star_tracker_esp32s3)
