/* Star Tracker RP2354A — three TMC2209 on one PDN_UART wire (UART1: GPIO4 TX through 1 k, GPIO5 RX).
 * Datagrams (TMC2209 datasheet rev 1.09, section 4): write = 0x05, addr, reg|0x80, data[31:24..7:0], CRC;
 * read request = 0x05, addr, reg, CRC; reply = 0x05, 0xFF, reg, data x4, CRC. On one wire every byte we
 * send is echoed back on RX and must be skipped.
 */
#include "hw.h"
#include <math.h>
#include "hardware/gpio.h"
#include "hardware/uart.h"
#include "pico/time.h"

#define TMC_UART  uart1
#define TMC_BAUD  115200
#define FCLK      12000000.0      /* TMC2209 internal clock, typ. */

tmc_t hw_tmc[ST_AXES] = {{TMC_ADDR_AZ}, {TMC_ADDR_ALT}, {TMC_ADDR_ROLL}};
static const uint DIAG_PIN[ST_AXES] = {RP_GPIO_DIAG_AZ, RP_GPIO_DIAG_ALT, RP_GPIO_DIAG_ROLL};

void hw_tmc_init(void)
{
    uart_init(TMC_UART, TMC_BAUD);
    gpio_set_function(RP_GPIO_TMC_TX, GPIO_FUNC_UART);
    gpio_set_function(RP_GPIO_TMC_UART, GPIO_FUNC_UART);
    gpio_init(RP_GPIO_DRV_EN_N);
    gpio_put(RP_GPIO_DRV_EN_N, 1);                         /* drivers off (also pulled high on the board) */
    gpio_set_dir(RP_GPIO_DRV_EN_N, GPIO_OUT);
    for (int i = 0; i < ST_AXES; i++) {
        gpio_init(DIAG_PIN[i]);
        gpio_set_dir(DIAG_PIN[i], GPIO_IN);
        gpio_pull_down(DIAG_PIN[i]);
    }
}

uint8_t hw_tmc_crc(const uint8_t *p, int n)
{
    uint8_t crc = 0;
    for (int i = 0; i < n; i++) {
        uint8_t b = p[i];
        for (int j = 0; j < 8; j++) {
            if ((crc >> 7) ^ (b & 0x01)) crc = (uint8_t)((crc << 1) ^ 0x07);
            else crc = (uint8_t)(crc << 1);
            b >>= 1;
        }
    }
    return crc;
}

static void drain(void) { while (uart_is_readable(TMC_UART)) (void)uart_getc(TMC_UART); }

static bool rx_bytes(uint8_t *p, int n, uint32_t timeout_us)
{
    absolute_time_t end = make_timeout_time_us(timeout_us);
    for (int i = 0; i < n; i++) {
        while (!uart_is_readable(TMC_UART))
            if (absolute_time_diff_us(get_absolute_time(), end) < 0) return false;
        p[i] = (uint8_t)uart_getc(TMC_UART);
    }
    return true;
}

bool hw_tmc_write(uint8_t addr, uint8_t reg, uint32_t val)
{
    uint8_t d[8] = {0x05, addr, (uint8_t)(reg | 0x80), (uint8_t)(val >> 24), (uint8_t)(val >> 16), (uint8_t)(val >> 8), (uint8_t)val, 0};
    d[7] = hw_tmc_crc(d, 7);
    drain();
    uart_write_blocking(TMC_UART, d, 8);
    uint8_t echo[8];
    return rx_bytes(echo, 8, 2000);                        /* 8 bytes at 115 200 = 0.7 ms */
}

bool hw_tmc_read(uint8_t addr, uint8_t reg, uint32_t *val)
{
    uint8_t q[4] = {0x05, addr, reg, 0};
    q[3] = hw_tmc_crc(q, 3);
    drain();
    uart_write_blocking(TMC_UART, q, 4);
    uint8_t echo[4], r[8];
    if (!rx_bytes(echo, 4, 1500)) return false;
    if (!rx_bytes(r, 8, 3000)) return false;               /* reply after SENDDELAY (8 bit times) */
    if (r[0] != 0x05 || r[1] != 0xFF || r[2] != reg || hw_tmc_crc(r, 7) != r[7]) return false;
    *val = ((uint32_t)r[3] << 24) | ((uint32_t)r[4] << 16) | ((uint32_t)r[5] << 8) | r[6];
    return true;
}

static bool write_checked(tmc_t *t, uint8_t reg, uint32_t val)
{
    uint32_t before = 0, after = 0;
    if (!hw_tmc_read(t->addr, TMC_IFCNT, &before)) { t->errors++; return false; }
    hw_tmc_write(t->addr, reg, val);
    if (!hw_tmc_read(t->addr, TMC_IFCNT, &after)) { t->errors++; return false; }
    if (((after - before) & 0xFF) != 1) { t->errors++; return false; }   /* IFCNT counts good writes */
    return true;
}

/* GCONF: I_scale_analog=0 (internal reference, Phase 4 calc), internal_Rsense=0, en_SpreadCycle=0,
 * pdn_disable=1 (UART on PDN_UART), mstep_reg_select=1 (MRES from CHOPCONF; MS1/MS2 are addresses),
 * multistep_filt=1. */
#define GCONF_VAL   ((1u << 6) | (1u << 7) | (1u << 8))
/* CHOPCONF: toff=3, hstrt=5, hend=0, TBL=0 (16 clocks, as in the StealthChop-floor calc), MRES=0 (256), intpol=1 */
#define CHOP_BASE   (0x03u | (5u << 4) | (0u << 7) | (0u << 15) | (0u << 24) | (1u << 28))
#define CHOP_VSENSE (1u << 17)
/* PWMCONF: datasheet default 0xC10D0024 with pwm_freq=0 (2/1024 fCLK = 23.4 kHz, as in the calc) */
#define PWMCONF_VAL 0xC10C0024u

bool hw_tmc_setup(int axis)
{
    tmc_t *t = &hw_tmc[axis];
    uint32_t ioin = 0;
    t->ok = false;
    if (!hw_tmc_read(t->addr, TMC_IOIN, &ioin) || (ioin >> 24) != 0x21) { t->errors++; return false; }  /* VERSION 0x21 */
    bool ok = write_checked(t, TMC_GCONF, GCONF_VAL);
    ok &= write_checked(t, TMC_GSTAT, 0x7);                /* clear reset / drv_err / uv_cp */
    ok &= write_checked(t, TMC_CHOPCONF, CHOP_BASE | CHOP_VSENSE);
    ok &= write_checked(t, TMC_PWMCONF, PWMCONF_VAL);
    ok &= write_checked(t, TMC_TPOWERDOWN, 20);
    ok &= write_checked(t, TMC_TPWMTHRS, 0);               /* StealthChop at all speeds until Stage D says otherwise */
    ok &= write_checked(t, TMC_TCOOLTHRS, 0);
    ok &= write_checked(t, TMC_SGTHRS, 0);                 /* stall output off until tuned on P0 */
    ok &= write_checked(t, TMC_COOLCONF, 0);
    t->ma = 0;
    ok &= hw_tmc_set_current(axis, 300);                   /* 0.3 A, the Stage D starting value */
    uint32_t g = 0;
    ok &= hw_tmc_read(t->addr, TMC_GCONF, &g) && (g & 0x3FF) == GCONF_VAL;
    t->ok = ok;
    return ok;
}

bool hw_tmc_set_current(int axis, uint16_t ma)
{
    tmc_t *t = &hw_tmc[axis];
    if (ma == t->ma) return true;
    /* vsense=1 (0.749 A full scale, finer steps) up to 0.70 A, else vsense=0 (1.352 A) */
    bool vs = ma <= 700;
    float ifs = vs ? TMC_IFS_VSENSE1 : TMC_IFS_VSENSE0;
    int cs = (int)lroundf(ma / 1000.0f / ifs * 32.0f) - 1;
    if (cs < 0) cs = 0;
    if (cs > 31) cs = 31;
    bool ok = true;
    if (vs != t->vsense || t->ma == 0) {
        ok &= hw_tmc_write(t->addr, TMC_CHOPCONF, CHOP_BASE | (vs ? CHOP_VSENSE : 0));
        t->vsense = vs;
    }
    /* IHOLD = IRUN: the motion core chooses the current per mode itself; IHOLDDELAY = 1 */
    ok &= hw_tmc_write(t->addr, TMC_IHOLD_IRUN, (uint32_t)cs | ((uint32_t)cs << 8) | (1u << 16));
    if (ok) t->ma = ma;
    return ok;
}

static uint32_t tstep_for(float dps, double usteps_per_rev)
{
    double f = dps / 360.0 * usteps_per_rev;               /* microsteps per second at 256 */
    if (f < 1.0) return 0xFFFFF;
    double ts = FCLK / f;
    return ts > 0xFFFFF ? 0xFFFFF : (uint32_t)ts;
}

bool hw_tmc_set_spread_above(int axis, float dps, double usteps_per_rev)
{
    /* SpreadCycle when TSTEP < TPWMTHRS; 0 = StealthChop always */
    return hw_tmc_write(hw_tmc[axis].addr, TMC_TPWMTHRS, dps <= 0 ? 0 : tstep_for(dps, usteps_per_rev));
}

bool hw_tmc_set_stall(int axis, uint8_t sgthrs, float min_dps, double usteps_per_rev)
{
    /* DIAG reports a stall when SG_RESULT <= 2 x SGTHRS and TCOOLTHRS >= TSTEP (StealthChop only) */
    bool ok = hw_tmc_write(hw_tmc[axis].addr, TMC_TCOOLTHRS, tstep_for(min_dps, usteps_per_rev));
    ok &= hw_tmc_write(hw_tmc[axis].addr, TMC_SGTHRS, sgthrs);
    return ok;
}

void hw_tmc_enable(bool on) { gpio_put(RP_GPIO_DRV_EN_N, on ? 0 : 1); }
bool hw_tmc_diag(int axis) { return gpio_get(DIAG_PIN[axis]); }
