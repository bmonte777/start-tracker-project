/* Star Tracker RP2354A — motor rail (soft-start switch Q6, TPS61288 boost, 10/16 V level) and the ADC.
 * Sequence (Phase 4 section 10.5): MOTOR_PWR_EN high, wait 5 ms (soft start 1.4 ms), BOOST_EN high, wait 10 ms,
 * VMOT_MON must read about 10 V; VM_SEL high = 16 V, low = 10 V (D43). Off = reverse order.
 */
#include "hw.h"
#include <math.h>
#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "pico/time.h"

static rail_level_t level = RAIL_OFF;

static void out_low(uint pin) { gpio_init(pin); gpio_put(pin, 0); gpio_set_dir(pin, GPIO_OUT); }

void hw_rail_init(void)
{
    out_low(RP_GPIO_MOTOR_PWR_EN);
    out_low(RP_GPIO_BOOST_EN);
    out_low(RP_GPIO_VM_SEL);
    adc_init();
    adc_gpio_init(RP_GPIO_NTC_AZ_A);
    adc_gpio_init(RP_GPIO_NTC_ALT_A);
    adc_gpio_init(RP_GPIO_NTC_ROLL_A);
    adc_gpio_init(RP_GPIO_VMOT_MON);
}

float hw_adc_volts(int ch)
{
    adc_select_input((uint)ch);
    uint32_t acc = 0;
    for (int i = 0; i < 8; i++) acc += adc_read();
    return (acc / 8.0f) * 3.3f / 4095.0f;                 /* ADC_AVDD = +3V3A */
}

float hw_vmot(void) { return hw_adc_volts(RP_GPIO_VMOT_MON - 26) * VMOT_MON_SCALE; }

float hw_ntc_from_volts(float v)
{
    if (v < 0.02f) return 200.0f;                          /* shorted: report hot so the axis stops */
    if (v > 3.28f) return -100.0f;                         /* open: no thermistor */
    float r = NTC_PULLUP_OHM * v / (3.3f - v);
    float inv_t = 1.0f / 298.15f + logf(r / NTC_R25_OHM) / NTC_BETA;
    return 1.0f / inv_t - 273.15f;
}

float hw_ntc_c(int axis)
{
    static const int ch[ST_AXES] = {RP_GPIO_NTC_AZ_A - 26, RP_GPIO_NTC_ALT_A - 26, RP_GPIO_NTC_ROLL_A - 26};
    return hw_ntc_from_volts(hw_adc_volts(ch[axis]));
}

rail_level_t hw_rail_get(void) { return level; }

bool hw_rail_set(rail_level_t want)
{
    if (want == level) return true;
    if (want == RAIL_OFF) {
        hw_tmc_enable(false);
        gpio_put(RP_GPIO_VM_SEL, 0);
        gpio_put(RP_GPIO_BOOST_EN, 0);
        sleep_ms(2);
        gpio_put(RP_GPIO_MOTOR_PWR_EN, 0);
        level = RAIL_OFF;
        return true;
    }
    if (level == RAIL_OFF) {
        gpio_put(RP_GPIO_MOTOR_PWR_EN, 1);
        sleep_ms(5);
        gpio_put(RP_GPIO_BOOST_EN, 1);
        sleep_ms(10);
        float v = hw_vmot();
        if (v < 9.0f || v > 11.0f) {                       /* 10.04 V expected (Phase 4 divider calc) */
            gpio_put(RP_GPIO_BOOST_EN, 0);
            gpio_put(RP_GPIO_MOTOR_PWR_EN, 0);
            return false;
        }
        level = RAIL_10V;
    }
    if (want == RAIL_16V) {
        gpio_put(RP_GPIO_VM_SEL, 1);
        level = RAIL_16V;
    } else if (want == RAIL_10V) {
        gpio_put(RP_GPIO_VM_SEL, 0);
        level = RAIL_10V;
    }
    return true;
}
