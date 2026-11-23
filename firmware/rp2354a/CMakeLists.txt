# Star Tracker — RP2354A firmware (Pico SDK 2.3). Two images from one source:
#   st_rp2354a_motion   the motion firmware
#   st_rp2354a_bringup  the same plus the bring-up tests (docs/04-electronics.md section 11)
cmake_minimum_required(VERSION 3.13)
set(PICO_BOARD st501_rp2354a)
set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
set(PICO_PLATFORM rp2350-arm-s)
include(pico_sdk_import.cmake)
project(st_rp2354a C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

set(COMMON ${CMAKE_CURRENT_LIST_DIR}/../common)
set(SRC
  src/main.c src/hw_stepgen.c src/hw_encoder.c src/hw_tmc2209.c src/hw_rail.c src/hw_time.c src/hw_link.c
  motion/motion.c bringup/tests.c ${COMMON}/src/st_link.c)

foreach(img motion bringup)
  set(t st_rp2354a_${img})
  add_executable(${t} ${SRC})
  pico_generate_pio_header(${t} ${CMAKE_CURRENT_LIST_DIR}/src/stepgen.pio)
  target_include_directories(${t} PRIVATE src motion ${COMMON}/include)
  target_compile_options(${t} PRIVATE -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -O2)
  pico_enable_stdio_uart(${t} 0)
  pico_enable_stdio_usb(${t} 0)
  target_link_libraries(${t} pico_stdlib pico_multicore hardware_pio hardware_spi hardware_uart hardware_adc hardware_watchdog m)
  if(img STREQUAL bringup)
    target_compile_definitions(${t} PRIVATE RP_IS_BRINGUP=1)
  endif()
  pico_set_program_name(${t} "Star Tracker RP2354A ${img}")
  pico_add_extra_outputs(${t})          # .uf2, .bin, .hex, .elf
endforeach()
