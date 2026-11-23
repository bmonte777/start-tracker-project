/* Star Tracker RP2354A — PIO step generators. */
#include "hw.h"
#include "hardware/clocks.h"
#include "hardware/pio.h"
#include "stepgen.pio.h"

static const uint STEP_PIN[ST_AXES] = {RP_GPIO_STEP_AZ, RP_GPIO_STEP_ALT, RP_GPIO_STEP_ROLL};
static const uint DIR_PIN[ST_AXES]  = {RP_GPIO_DIR_AZ, RP_GPIO_DIR_ALT, RP_GPIO_DIR_ROLL};
static uint32_t cycles_per_us;
static uint32_t overflows;

void hw_stepgen_init(void)
{
    cycles_per_us = clock_get_hz(clk_sys) / 1000000u;     /* 150 at the default clock */
    uint offset = pio_add_program(pio0, &stepgen_program);
    for (int i = 0; i < ST_AXES; i++)
        stepgen_program_init(pio0, (uint)i, offset, STEP_PIN[i], DIR_PIN[i]);
}

bool hw_stepgen_push(int axis, int32_t steps, uint32_t tick_us)
{
    if (steps == 0)
        return true;
    uint32_t n = (uint32_t)(steps < 0 ? -steps : steps);
    uint32_t dir = steps < 0 ? 1u : 0u;
    /* spread the steps over 97 % of the tick so the segment always ends before the next one arrives */
    uint32_t cycles = (tick_us * cycles_per_us * 97u) / 100u;
    uint32_t per = cycles / n;
    uint32_t half = per > 7 ? (per - 7) / 2 : 0;
    if (half < 16) half = 16;                              /* STEP high >= 120 ns */
    if (pio_sm_get_tx_fifo_level(pio0, (uint)axis) > 6) {
        overflows++;
        return false;
    }
    pio_sm_put(pio0, (uint)axis, ((n - 1u) << 1) | dir);
    pio_sm_put(pio0, (uint)axis, half);
    return true;
}

uint32_t hw_stepgen_overflows(void) { return overflows; }
