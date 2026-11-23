/* Star Tracker RP2354A — hardware layer. Pins come only from st_board.h (generated from the schematic). */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "st_board.h"
#include "st_link.h"

/* ---- step generators (PIO0, stepgen.pio) ---- */
void     hw_stepgen_init(void);
bool     hw_stepgen_push(int axis, int32_t steps, uint32_t tick_us);   /* false if the FIFO was full */
uint32_t hw_stepgen_overflows(void);

/* ---- MT6835 encoders on SPI1, shared MISO, CS per axis ---- */
typedef struct { uint32_t raw; uint8_t status; bool crc_ok; } enc_sample_t;
void     hw_enc_init(uint32_t baud);
bool     hw_enc_read(int axis, enc_sample_t *s);          /* burst read 0x003..0x006 */
bool     hw_enc_reg_read(int axis, uint16_t reg, uint8_t *val);
bool     hw_enc_reg_write(int axis, uint16_t reg, uint8_t val);
uint8_t  hw_enc_crc8(const uint8_t *p, int n);

/* ---- TMC2209 drivers on UART1, one wire, addresses 0/1/2 ---- */
#define TMC_GCONF      0x00
#define TMC_GSTAT      0x01
#define TMC_IFCNT      0x02
#define TMC_SLAVECONF  0x03
#define TMC_IOIN       0x06
#define TMC_IHOLD_IRUN 0x10
#define TMC_TPOWERDOWN 0x11
#define TMC_TSTEP      0x12
#define TMC_TPWMTHRS   0x13
#define TMC_TCOOLTHRS  0x14
#define TMC_SGTHRS     0x40
#define TMC_SG_RESULT  0x41
#define TMC_COOLCONF   0x42
#define TMC_MSCNT      0x6A
#define TMC_CHOPCONF   0x6C
#define TMC_DRV_STATUS 0x6F
#define TMC_PWMCONF    0x70
#define TMC_PWM_SCALE  0x71
typedef struct { uint8_t addr; bool ok; uint16_t ma; bool vsense; uint32_t errors; } tmc_t;
void     hw_tmc_init(void);
uint8_t  hw_tmc_crc(const uint8_t *p, int n);
bool     hw_tmc_write(uint8_t addr, uint8_t reg, uint32_t val);
bool     hw_tmc_read(uint8_t addr, uint8_t reg, uint32_t *val);
bool     hw_tmc_setup(int axis);                          /* full register set-up, verified */
bool     hw_tmc_set_current(int axis, uint16_t ma);       /* picks vsense and CS */
bool     hw_tmc_set_spread_above(int axis, float dps, double usteps_per_rev);
bool     hw_tmc_set_stall(int axis, uint8_t sgthrs, float min_dps, double usteps_per_rev);
void     hw_tmc_enable(bool on);                          /* DRV_EN_N */
bool     hw_tmc_diag(int axis);
extern tmc_t hw_tmc[ST_AXES];

/* ---- motor rail (D43, D45, Phase 4 section 10.5) and ADC ---- */
typedef enum { RAIL_OFF = 0, RAIL_10V = 1, RAIL_16V = 2 } rail_level_t;
void     hw_rail_init(void);
bool     hw_rail_set(rail_level_t lvl);                   /* runs the soft-start sequence; checks VMOT */
rail_level_t hw_rail_get(void);
float    hw_adc_volts(int ch);                            /* ch 0..3 = GPIO26..29 */
float    hw_vmot(void);
float    hw_ntc_c(int axis);
float    hw_ntc_from_volts(float v);

/* ---- time base: 1 PPS (GPIO3) and LINK_SYNC (GPIO2) edges ---- */
void     hw_time_init(void);
uint64_t hw_head_us(void);                                /* head time now */
uint64_t hw_head_from_local(uint64_t local_us);
void     hw_time_on_timesync(const st_timesync_t *ts);    /* pairs the last LINK_SYNC edge with its head time */
double   hw_time_ppm(void);                               /* crystal error measured on PPS */
uint32_t hw_time_pps_count(void);

/* ---- link UART0 ---- */
void     hw_link_init(st_link_frame_cb cb, void *ctx);
void     hw_link_poll(void);                              /* drain the RX ring into the frame decoder */
bool     hw_link_send(uint8_t type, const void *payload, size_t len);
st_link_rx_t *hw_link_rx(void);

/* ---- heartbeat LED ---- */
void     hw_led_init(void);
void     hw_led_set(bool on);
