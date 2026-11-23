/* Star Tracker ST-501 mainboard, RP2354A (RP2350A + 2 MB stacked flash), 12 MHz crystal Y1. */
#ifndef _BOARDS_ST501_RP2354A_H
#define _BOARDS_ST501_RP2354A_H
pico_board_cmake_set(PICO_PLATFORM, rp2350-arm-s)
#define PICO_RP2350A 1
#define PICO_FLASH_SIZE_BYTES (2 * 1024 * 1024)
#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64
#define PICO_DEFAULT_LED_PIN 9        /* LED_RP (st_board.h RP_GPIO_LED_RP) */
#endif
