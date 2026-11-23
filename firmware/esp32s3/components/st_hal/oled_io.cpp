// Star Tracker ESP32-S3 — SH1106 OLED (128 x 64 inside a 132-column RAM, column offset 2), buttons, LEDs, shutter,
// port B enable, RP2354A reset, VSYS monitor, LINK_SYNC pulse.
#include <cstring>
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "font6x8.h"
#include "st_hal.h"

namespace st {

Oled oled;

static bool cmds(const uint8_t *c, size_t n)
{
    uint8_t b[32];
    b[0] = 0x00;                                         // control byte: command stream
    memcpy(b + 1, c, n);
    return i2c_main.write(I2C_ADDR_SH1106, b, n + 1);
}

bool Oled::init()
{
    static const uint8_t seq[] = {
        0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0xAD, 0x8B,  // off, clock, mux 64, offset 0, start 0, DC-DC on
        0xA1, 0xC8, 0xDA, 0x12, 0x81, 0x80, 0xD9, 0x22, 0xDB, 0x35,  // segment remap, COM reverse, pins, contrast, precharge, VCOMH
        0xA4, 0xA6, 0xAF};                                           // follow RAM, normal, on
    ok_ = cmds(seq, sizeof seq);
    clear();
    flush();
    return ok_;
}

void Oled::clear() { memset(fb_, 0, sizeof fb_); }

void Oled::text(int col, int row, const char *s, bool inv)
{
    if (row < 0 || row > 7) return;
    for (int x = col * 6; *s && x <= 122; s++, x += 6) {
        int c = (unsigned char)*s;
        if (c < 32 || c > 126) c = '?';
        for (int k = 0; k < 6; k++) fb_[row][x + k] = inv ? (uint8_t)~FONT6X8[c - 32][k] : FONT6X8[c - 32][k];
    }
}

void Oled::hline(int y)
{
    if (y < 0 || y > 63) return;
    for (int x = 0; x < 128; x++) fb_[y / 8][x] |= (uint8_t)(1u << (y % 8));
}

void Oled::bar(int x, int y, int w, int h, int pct)
{
    int fill = w * pct / 100;
    for (int i = 0; i < w; i++)
        for (int j = 0; j < h; j++) {
            bool on = i == 0 || i == w - 1 || j == 0 || j == h - 1 || i < fill;
            int yy = y + j, xx = x + i;
            if (xx < 128 && yy < 64 && on) fb_[yy / 8][xx] |= (uint8_t)(1u << (yy % 8));
        }
}

bool Oled::flush()
{
    bool ok = true;
    for (int p = 0; p < 8; p++) {
        uint8_t c[3] = {(uint8_t)(0xB0 | p), 0x02, 0x10};   // page, column 2 (SH1106 132-column RAM)
        ok &= cmds(c, 3);
        uint8_t b[129];
        b[0] = 0x40;                                     // control byte: data
        memcpy(b + 1, fb_[p], 128);
        ok &= i2c_main.write(I2C_ADDR_SH1106, b, 129);
    }
    return ok;
}

void Oled::contrast(uint8_t v) { uint8_t c[2] = {0x81, v}; cmds(c, 2); }
void Oled::power(bool on) { uint8_t c = on ? 0xAF : 0xAE; cmds(&c, 1); }

// ---------------------------------------------------------------- I/O
static const int BTN[4] = {ESP_GPIO_BTN1, ESP_GPIO_BTN2, ESP_GPIO_BTN3, ESP_GPIO_BTN4};
static adc_oneshot_unit_handle_t adc1;
static adc_cali_handle_t cali;
static volatile int64_t pps_local;
static volatile uint32_t pps_n;

void io_init()
{
    gpio_config_t in = {};
    for (int b : BTN) in.pin_bit_mask |= 1ULL << b;
    in.mode = GPIO_MODE_INPUT;                           // 10 k pull-ups and 100 nF on the board
    gpio_config(&in);

    gpio_config_t out = {};
    out.pin_bit_mask = (1ULL << ESP_GPIO_SHUT_FOCUS) | (1ULL << ESP_GPIO_SHUT_REL) | (1ULL << ESP_GPIO_PORTB_EN) |
                       (1ULL << ESP_GPIO_LINK_SYNC);
    out.mode = GPIO_MODE_OUTPUT;
    gpio_config(&out);
    gpio_set_level((gpio_num_t)ESP_GPIO_SHUT_FOCUS, 0);
    gpio_set_level((gpio_num_t)ESP_GPIO_SHUT_REL, 0);
    gpio_set_level((gpio_num_t)ESP_GPIO_PORTB_EN, 0);   // strap pin: also pulled down by 100 k
    gpio_set_level((gpio_num_t)ESP_GPIO_LINK_SYNC, 0);

    gpio_config_t od = {};                               // RP_RUN: open drain, 10 k pull-up on the board
    od.pin_bit_mask = 1ULL << ESP_GPIO_RP_RUN;
    od.mode = GPIO_MODE_INPUT_OUTPUT_OD;
    gpio_config(&od);
    gpio_set_level((gpio_num_t)ESP_GPIO_RP_RUN, 1);

    ledc_timer_config_t t = {};
    t.speed_mode = LEDC_LOW_SPEED_MODE;
    t.duty_resolution = LEDC_TIMER_8_BIT;
    t.timer_num = LEDC_TIMER_0;
    t.freq_hz = 5000;
    t.clk_cfg = LEDC_AUTO_CLK;
    ledc_timer_config(&t);
    const int pins[3] = {ESP_GPIO_LED_R, ESP_GPIO_LED_G, ESP_GPIO_LED_B};
    for (int i = 0; i < 3; i++) {
        ledc_channel_config_t c = {};
        c.gpio_num = pins[i];
        c.speed_mode = LEDC_LOW_SPEED_MODE;
        c.channel = (ledc_channel_t)i;
        c.timer_sel = LEDC_TIMER_0;
        c.duty = 0;
        ledc_channel_config(&c);
    }

    adc_oneshot_unit_init_cfg_t u = {};
    u.unit_id = ADC_UNIT_1;
    adc_oneshot_new_unit(&u, &adc1);
    adc_oneshot_chan_cfg_t ch = {};
    ch.atten = ADC_ATTEN_DB_12;
    ch.bitwidth = ADC_BITWIDTH_12;
    adc_oneshot_config_channel(adc1, ADC_CHANNEL_6, &ch);   // GPIO7 = ADC1 channel 6 (VSYS_MON)
    adc_cali_curve_fitting_config_t cc = {};
    cc.unit_id = ADC_UNIT_1;
    cc.chan = ADC_CHANNEL_6;
    cc.atten = ADC_ATTEN_DB_12;
    cc.bitwidth = ADC_BITWIDTH_12;
    adc_cali_create_scheme_curve_fitting(&cc, &cali);
}

void led_set(Led l, uint8_t level)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)l, level);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)l);
}

int buttons()
{
    static int stable = 0, last = 0;
    static int64_t t_change = 0;
    int now = 0;
    for (int i = 0; i < 4; i++)
        if (!gpio_get_level((gpio_num_t)BTN[i])) now |= 1 << i;   // low when pressed
    int64_t t = esp_timer_get_time();
    if (now != last) { last = now; t_change = t; }
    if (t - t_change > 30000) stable = now;              // 30 ms debounce
    return stable;
}

void shutter_focus(bool on) { gpio_set_level((gpio_num_t)ESP_GPIO_SHUT_FOCUS, on); }
void shutter_release(bool on) { gpio_set_level((gpio_num_t)ESP_GPIO_SHUT_REL, on); }
void portb_enable(bool on) { gpio_set_level((gpio_num_t)ESP_GPIO_PORTB_EN, on); }
void rp_reset(bool hold) { gpio_set_level((gpio_num_t)ESP_GPIO_RP_RUN, hold ? 0 : 1); }

float vsys_volts()
{
    int raw = 0, mv = 0, acc = 0;
    for (int i = 0; i < 8; i++) {
        adc_oneshot_read(adc1, ADC_CHANNEL_6, &raw);
        adc_cali_raw_to_voltage(cali, raw, &mv);
        acc += mv;
    }
    return acc / 8.0f / 1000.0f * VSYS_MON_SCALE;
}

void link_sync_pulse()
{
    gpio_set_level((gpio_num_t)ESP_GPIO_LINK_SYNC, 1);
    esp_rom_delay_us(20);
    gpio_set_level((gpio_num_t)ESP_GPIO_LINK_SYNC, 0);
}

int64_t pps_last_local_us() { return gnss().local_us_at_pps; }
uint32_t pps_edges() { return gnss().pps_count; }

}  // namespace st
