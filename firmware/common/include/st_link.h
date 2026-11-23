/* Star Tracker — link protocol between the ESP32-S3 (application) and the RP2354A (motion).
 *
 * Physical: RP2354A UART0 (GPIO0 TX, GPIO1 RX) <-> ESP32-S3 UART1 (IO18 RX, IO17 TX), 921 600 baud 8N1,
 * plus LINK_SYNC (ESP32 IO16 -> RP GPIO2) and GNSS 1 PPS on both (spec 7.1, Phase 4 section 10.3).
 *
 * Frame on the wire:  COBS( type:u8 | seq:u8 | payload[0..ST_LINK_MAX_PAYLOAD] | crc16:u16le ) 0x00
 *   - crc16 = CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over type, seq and payload.
 *   - seq counts per sender, wraps at 256; the receiver reports gaps (lost frames) in its counters.
 *   - all multi-byte fields little-endian (both processors and every host are little-endian).
 *
 * Units used on the link (axis-agnostic; the RP2354A converts to microsteps with the CONFIG ratio):
 *   angle   int64  in 2^-32 revolution of the axis OUTPUT  (1 LSB = 3.0e-4 arc-second)
 *   rate    int64  in 2^-40 revolution per second          (sidereal = 12 760 828 LSB/s)
 *   accel   int32  in 2^-32 revolution per second^2
 *   time    uint64 head time in microseconds (GNSS-steered, Unix epoch when GNSS/RTC known, else since boot)
 *
 * Status: protocol version 1. Pending approval as Q46.
 */
#pragma once
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ST_LINK_VERSION        1
#define ST_LINK_BAUD           921600
#define ST_LINK_MAX_PAYLOAD    240
#define ST_LINK_MAX_FRAME      (ST_LINK_MAX_PAYLOAD + 4 + 2 + 2)   /* +type,seq,crc +COBS overhead +delimiter */
#define ST_AXES                3

enum st_axis { ST_AZ = 0, ST_ALT = 1, ST_ROLL = 2 };

#define ST_ANGLE_ONE_REV       (1LL << 32)
#define ST_RATE_ONE_REV_S      (1LL << 40)

typedef enum {
    /* both directions */
    ST_MSG_HEARTBEAT   = 0x01,
    ST_MSG_ACK         = 0x02,
    ST_MSG_CONSOLE     = 0x03,   /* free text, bring-up console relay */
    ST_MSG_HELLO       = 0x04,   /* version exchange after reset */
    /* ESP32 -> RP2354A */
    ST_MSG_TIMESYNC    = 0x10,
    ST_MSG_SETPOINT    = 0x11,
    ST_MSG_MOVE        = 0x12,
    ST_MSG_STOP        = 0x13,
    ST_MSG_CFG_SET     = 0x14,
    ST_MSG_CFG_GET     = 0x15,
    ST_MSG_TABLE       = 0x16,   /* PEC or encoder-map chunk */
    ST_MSG_POWER       = 0x17,   /* motor rail / driver enable request, current budget */
    ST_MSG_TEST        = 0x18,   /* run a bring-up test on the RP2354A */
    ST_MSG_SYNC_AXIS   = 0x19,   /* set the commanded position of an axis (plate-solve sync, re-home) */
    /* RP2354A -> ESP32 */
    ST_MSG_STATE       = 0x40,
    ST_MSG_EVENT       = 0x41,
    ST_MSG_CFG_VALUE   = 0x42,
    ST_MSG_TEST_RESULT = 0x43,
} st_msg_type_t;

/* ---- payloads ------------------------------------------------------------------------------- */
#pragma pack(push, 1)

typedef struct { uint32_t uptime_ms; uint16_t flags; uint16_t rx_errors; } st_heartbeat_t;
typedef struct { uint8_t acked_type; uint8_t acked_seq; uint8_t result; } st_ack_t;   /* result: st_result_t */
typedef struct { uint8_t proto; uint8_t fw_major, fw_minor, fw_patch; uint32_t build; char role[4]; } st_hello_t;

/* Sent right after each LINK_SYNC rising edge: "the edge you just latched was at head time t_us". */
typedef struct {
    uint64_t t_edge_us;
    uint32_t sync_count;
    uint8_t  time_quality;   /* 0 none (since boot), 1 RTC, 2 GNSS fix, 3 GNSS + PPS locked */
    int32_t  pps_offset_ns;  /* ESP32's PPS phase error, for logging */
} st_timesync_t;

/* Tracking setpoint: the RP2354A follows angle(t) = pos + rate*(t - t_us) + accel*(t - t_us)^2 / 2,
 * valid until t_us + valid_ms. Sent at 10 Hz; missing setpoints -> see safety (spec 7.3). */
typedef struct {
    uint64_t t_us;
    uint16_t valid_ms;
    uint8_t  axis_mask;
    uint8_t  flags;              /* bit0: apply PEC, bit1: encoder correction on */
    struct { int64_t pos; int64_t rate; int32_t accel; } ax[ST_AXES];
} st_setpoint_t;

/* Point-to-point S-curve move (go-to, park, jog end point). */
typedef struct {
    uint8_t  axis_mask;
    uint8_t  flags;              /* bit0: high-speed rail (16 V) allowed, bit1: relative */
    uint16_t vmax_mdeg_s;        /* per-move speed cap, millidegree/s of the output (8000 = 8 deg/s, D42) */
    uint16_t amax_mdeg_s2;
    uint16_t jerk_deg_s3;
    int64_t  target[ST_AXES];
} st_move_t;

typedef struct { uint8_t axis_mask; uint8_t mode; } st_stop_t;   /* mode 0 ramp, 1 quick (max decel), 2 de-energise */

typedef struct { uint16_t key; uint8_t axis; uint8_t _pad; int64_t value; } st_cfg_t;   /* see st_cfg_key_t */

typedef struct {
    uint8_t  table;              /* 1 PEC (rate correction vs motor angle), 2 encoder map (arcsec vs output angle) */
    uint8_t  axis;
    uint16_t total;              /* entries in the full table */
    uint16_t offset;             /* first entry in this chunk */
    uint8_t  count;              /* entries in this chunk (<= 100) */
    uint8_t  last;
    int16_t  v[100];             /* PEC: 0.01 arcsec; encoder map: 0.1 arcsec */
} st_table_t;

typedef struct {
    uint8_t  request;            /* 0 rail off, 1 rail on (10 V), 2 rail on and allow 16 V for slews */
    uint8_t  _pad;
    uint16_t motion_budget_mw;   /* power the ESP32 allows the motors (section 10.7 pack budget) */
} st_power_t;

typedef struct { uint8_t test; uint8_t axis; uint16_t arg; int32_t arg2; } st_test_t;
typedef struct { uint8_t test; uint8_t axis; uint8_t pass; uint8_t done; char text[200]; } st_test_result_t;

typedef struct { uint8_t axis; uint8_t source; int64_t pos; } st_sync_axis_t;  /* source 0 set, 1 from encoder */

typedef struct {
    int64_t  cmd;                /* commanded output angle */
    int64_t  enc;                /* encoder output angle (multi-turn, linearised) */
    int64_t  rate;               /* commanded rate */
    uint16_t i_ma;               /* driver run current setting */
    uint16_t sg;                 /* StallGuard result (0..510) */
    int16_t  temp_dc;            /* motor temperature, 0.1 degC (thermistor) */
    uint8_t  mode;               /* st_axis_mode_t */
    uint8_t  enc_status;         /* MT6835 STATUS[2:0] | bit7 CRC error */
    uint16_t flags;              /* st_axis_flag_t */
} st_axis_state_t;

typedef struct {
    uint64_t t_us;
    uint16_t vmot_mv;
    uint8_t  rail;               /* 0 off, 1 10 V, 2 16 V */
    uint8_t  sys_state;          /* st_motion_state_t */
    uint32_t faults;             /* st_fault_t bits */
    st_axis_state_t ax[ST_AXES];
} st_state_t;

typedef struct { uint16_t code; uint8_t axis; uint8_t severity; int32_t value; } st_event_t;

#pragma pack(pop)

/* ---- enums ---------------------------------------------------------------------------------- */
typedef enum { ST_OK = 0, ST_ERR_CRC = 1, ST_ERR_UNKNOWN = 2, ST_ERR_STATE = 3, ST_ERR_RANGE = 4, ST_ERR_BUSY = 5 } st_result_t;

typedef enum {
    ST_AX_DISABLED = 0, ST_AX_HOLDING = 1, ST_AX_MOVING = 2, ST_AX_TRACKING = 3, ST_AX_STOPPING = 4, ST_AX_FAULT = 5,
} st_axis_mode_t;

typedef enum {
    ST_MS_BOOT = 0, ST_MS_SELFTEST = 1, ST_MS_IDLE = 2, ST_MS_OPERATING = 3, ST_MS_FAULT = 4, ST_MS_BRINGUP = 5,
} st_motion_state_t;

typedef enum {
    ST_AXF_AT_MIN = 1 << 0, ST_AXF_AT_MAX = 1 << 1, ST_AXF_STALL = 1 << 2, ST_AXF_DIAG = 1 << 3,
    ST_AXF_DERATED = 1 << 4, ST_AXF_ENC_BAD = 1 << 5, ST_AXF_SLIP = 1 << 6, ST_AXF_CORRECTING = 1 << 7,
    ST_AXF_SPREAD = 1 << 8, ST_AXF_CALIBRATED = 1 << 9,
} st_axis_flag_t;

typedef enum {
    ST_F_LINK_LOST = 1u << 0, ST_F_VMOT_LOW = 1u << 1, ST_F_VMOT_HIGH = 1u << 2, ST_F_DRV_UART = 1u << 3,
    ST_F_DRV_OT = 1u << 4, ST_F_DRV_SHORT = 1u << 5, ST_F_ENC = 1u << 6, ST_F_OVERTEMP = 1u << 7,
    ST_F_SLIP = 1u << 8, ST_F_STALL = 1u << 9, ST_F_LIMIT = 1u << 10, ST_F_SETPOINT_STALE = 1u << 11,
    ST_F_TIP = 1u << 12, ST_F_WATCHDOG = 1u << 13, ST_F_BUDGET = 1u << 14,
} st_fault_t;

/* configuration keys for ST_MSG_CFG_SET / CFG_GET (axis = 0..2, or 0xFF for global) */
typedef enum {
    ST_CFG_USTEPS_PER_REV   = 1,   /* microsteps per OUTPUT revolution: 200 x 256 x 300 = 15 360 000 */
    ST_CFG_DIR_INVERT       = 2,
    ST_CFG_I_RUN_MA         = 3,   /* slew current */
    ST_CFG_I_TRACK_MA       = 4,   /* tracking current (10 V rail, StealthChop) */
    ST_CFG_I_HOLD_MA        = 5,
    ST_CFG_LIMIT_MIN        = 6,   /* angle units; INT64_MIN = none (azimuth) */
    ST_CFG_LIMIT_MAX        = 7,
    ST_CFG_ENC_OFFSET       = 8,   /* encoder zero in angle units */
    ST_CFG_ENC_INVERT       = 9,
    ST_CFG_VMAX_MDEG_S      = 10,
    ST_CFG_AMAX_MDEG_S2     = 11,
    ST_CFG_SGTHRS           = 12,
    ST_CFG_SLIP_LIMIT       = 13,  /* angle units, default 0.05 deg */
    ST_CFG_CORR_DEADBAND    = 14,  /* angle units, default 2 arcsec */
    ST_CFG_TPWMTHRS         = 15,
    ST_CFG_THERMAL_DERATE_DC = 16, /* 0.1 degC, default 800 */
    ST_CFG_THERMAL_STOP_DC  = 17,  /* default 950 */
    ST_CFG_HB_TIMEOUT_MS    = 18,  /* default 500 */
    ST_CFG_TRACK_COAST_S    = 19,  /* default 60 */
    ST_CFG_ENC_BW           = 20,  /* MT6835 BW[2:0] */
    ST_CFG_SAVE             = 100, /* write config to the RP2354A's flash */
} st_cfg_key_t;

/* events (ST_MSG_EVENT.code) */
typedef enum {
    ST_EV_BOOT = 1, ST_EV_FAULT_SET = 2, ST_EV_FAULT_CLEAR = 3, ST_EV_MOVE_DONE = 4, ST_EV_LIMIT = 5,
    ST_EV_STALL = 6, ST_EV_SLIP = 7, ST_EV_DERATE = 8, ST_EV_RAIL = 9, ST_EV_RESYNC = 10,
} st_event_code_t;

/* ---- framing API (firmware/common/src/st_link.c) ------------------------------------------- */
uint16_t st_crc16(const uint8_t *p, size_t n, uint16_t crc);       /* CRC-16/CCITT-FALSE; start 0xFFFF */
size_t   st_cobs_encode(const uint8_t *in, size_t n, uint8_t *out); /* out needs n + n/254 + 1 */
size_t   st_cobs_decode(const uint8_t *in, size_t n, uint8_t *out); /* returns 0 on error */

/* Build a complete wire frame (including the trailing 0x00). Returns length, 0 if payload too long. */
size_t st_link_build(uint8_t type, uint8_t seq, const void *payload, size_t len, uint8_t *frame);

/* Byte-wise receiver. Feed bytes; when a valid frame completes, on_frame() is called. */
typedef void (*st_link_frame_cb)(void *ctx, uint8_t type, uint8_t seq, const uint8_t *payload, size_t len);
typedef struct {
    uint8_t  buf[ST_LINK_MAX_FRAME];
    size_t   n;
    uint8_t  last_seq;
    uint8_t  have_seq;
    uint32_t frames_ok, crc_errors, cobs_errors, overruns, seq_gaps;
    st_link_frame_cb cb;
    void    *ctx;
} st_link_rx_t;
void st_link_rx_init(st_link_rx_t *rx, st_link_frame_cb cb, void *ctx);
void st_link_rx_feed(st_link_rx_t *rx, const uint8_t *data, size_t n);

/* compile-time size checks: every payload fits one frame */
#ifdef __cplusplus
static_assert(sizeof(st_state_t) <= ST_LINK_MAX_PAYLOAD, "state too big");
static_assert(sizeof(st_table_t) <= ST_LINK_MAX_PAYLOAD, "table too big");
static_assert(sizeof(st_test_result_t) <= ST_LINK_MAX_PAYLOAD, "test result too big");
#else
_Static_assert(sizeof(st_state_t) <= ST_LINK_MAX_PAYLOAD, "state too big");
_Static_assert(sizeof(st_table_t) <= ST_LINK_MAX_PAYLOAD, "table too big");
_Static_assert(sizeof(st_test_result_t) <= ST_LINK_MAX_PAYLOAD, "test result too big");
#endif

#ifdef __cplusplus
}
#endif
