/* Star Tracker RP2354A — glue between main.c and the bring-up test runner. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "st_link.h"

#ifndef RP_IS_BRINGUP
#define RP_IS_BRINGUP 0
#endif

bool rp_post(uint8_t type, const void *pl, size_t len);     /* queue a message to the motion core (core 1) */
void rp_snapshot(st_state_t *st, uint32_t *ticks);

/* bring-up tests (bringup/tests.c; stubs in the release image) */
void rp_test_request(const uint8_t *pl, size_t len);
void rp_test_poll(void);
bool rp_test_active(void);
bool rp_test_owns_rail(void);

/* test numbers, shared with the ESP32 menu (firmware/esp32s3/components/st_sys/bringup.cpp) */
enum {
    RT_INFO = 1, RT_NTC = 2, RT_DRV_UART = 3, RT_RAIL = 4, RT_RAIL_LOAD = 5, RT_ENC = 6, RT_ENC_NOISE = 7,
    RT_ENC_SWEEP = 8, RT_STEP = 9, RT_TRACK = 10, RT_SLEW = 11, RT_FIELD = 12, RT_STEPGEN = 13,
    RT_LOST = 14, RT_SLEWLOG = 15,                  /* Phase 7: lost motion at reversals (T1), slew current + StallGuard log (T6) */
    RT_ABORT = 99,
};
