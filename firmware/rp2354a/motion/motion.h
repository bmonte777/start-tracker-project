/* Star Tracker — portable motion core (runs on the RP2354A and in the PC simulator).
 *
 * The core is fed by the hardware layer (encoder angles, temperatures, rail voltage, link messages) and
 * produces step segments, driver current requests and the rail request. It contains no hardware access:
 * the only outgoing call is hal_step_segment(), implemented by the PIO step generators on the RP2354A
 * and by the simulated axes in firmware/sim.
 *
 * Threading on the RP2354A: motion_tick() runs on core 1 at 1 kHz; every other function runs on core 0.
 * Data crossing the cores goes through the seqlocked blocks in motion.c.
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "st_link.h"

#ifdef __cplusplus
extern "C" {
#endif

#define MOTION_TICK_US        1000u
#define MOTION_MAX_STEPS_TICK 400       /* 400 kHz cap; 8 deg/s needs 342 per tick */
#define MOTION_PEC_N          1024      /* PEC table: positions over 3 motor turns (862 s at sidereal, spec 4.4) */
#define MOTION_ENC_GRID_N     721       /* encoder residual map, 0.5 deg grid over a full turn */
#define MOTION_ENC_HARM       8         /* harmonics of the output angle in the encoder map */
#define USTEPS_PER_MOTOR_REV  (200 * 256)

typedef struct {
    /* mechanics */
    double   usteps_per_rev;      /* microsteps per output revolution: 200 x 256 x 300 = 15 360 000 */
    bool     dir_invert;
    /* limits in degrees of the output; has_limits false = unlimited (azimuth, D19) */
    bool     has_limits;
    double   min_deg, max_deg;
    double   vmax_dps, amax_dps2, jmax_dps3;
    /* currents in mA RMS */
    uint16_t i_run_ma, i_track_ma, i_hold_ma;
    /* encoder */
    bool     enc_invert;
    double   enc_offset_deg;      /* encoder reading at axis zero */
    double   slip_limit_deg;      /* 0.05 deg (spec 7.3) */
    double   corr_deadband_deg;   /* 2 arcsec */
    double   corr_rate_track_dps; /* 1 arcsec/s */
    double   corr_rate_hold_dps;  /* 30 arcsec/s */
    /* thermal */
    float    derate_c, stop_c;    /* 80 / 95 degC (Phase 4 section 10.7, spec 7.3) */
} axis_cfg_t;

typedef struct {
    int32_t  pec[MOTION_PEC_N];        /* 0.01 arcsec position correction vs motor angle over 3 turns */
    bool     pec_valid;
    float    harm_a[MOTION_ENC_HARM], harm_b[MOTION_ENC_HARM]; /* encoder error, arcsec: sum a_k cos(k th) + b_k sin(k th) */
    int16_t  grid[MOTION_ENC_GRID_N];  /* residual, 0.1 arcsec, 0.5 deg grid */
    bool     map_valid;
} axis_tables_t;

typedef struct {
    st_axis_mode_t mode;
    /* planner state, microsteps of the output (double keeps 1e-6 step resolution over 1000 turns) */
    double   p, v, a;              /* position, velocity, acceleration of the plan */
    double   target;               /* MOVE target */
    double   vcap;                 /* per-move speed cap, usteps/s */
    int64_t  emitted;              /* microsteps actually sent to the driver */
    double   step_off;             /* emitted = round(p + step_off) */
    double   corr;                 /* encoder correction added to the plan (usteps) */
    double   corr_goal;
    /* tracking setpoint */
    bool     sp_valid;
    uint64_t sp_t_us;
    uint32_t sp_valid_ms;
    double   sp_pos, sp_rate, sp_acc;  /* usteps, usteps/s, usteps/s^2 */
    bool     sp_pec, sp_corr;
    /* sensors */
    bool     enc_ok;
    uint32_t enc_raw;              /* 21-bit raw */
    uint8_t  enc_status;
    int64_t  enc_turns;            /* multi-turn count */
    uint32_t enc_last_raw;
    double   enc_usteps;           /* linearised encoder position in plan units */
    double   enc_acc; uint32_t enc_acc_n;   /* averaging for the 5 Hz loop */
    float    temp_c;
    uint16_t sg;
    bool     diag;
    uint16_t flags;
    float    i_scale;              /* thermal / budget current scale */
} axis_state_t;

typedef struct {
    axis_cfg_t    cfg[ST_AXES];
    axis_tables_t tab[ST_AXES];
    axis_state_t  ax[ST_AXES];
    st_motion_state_t sys;
    uint32_t faults;
    /* rail */
    uint8_t  rail_req;             /* what the ESP32 allows: 0 off, 1 10 V, 2 10/16 V */
    uint8_t  rail_now;             /* reported by the rail driver: 0 off, 1 10 V, 2 16 V */
    uint16_t vmot_mv;
    uint16_t budget_mw;
    uint64_t last_fast_us;         /* last time an axis needed 16 V */
    /* link supervision */
    uint64_t last_hb_us;
    uint32_t hb_timeout_ms;
    uint32_t coast_s;
    bool     link_lost;
    uint64_t link_lost_at;
    /* time base */
    uint64_t now_us;               /* head time at the current tick */
} motion_t;

/* ---- hardware hooks (implemented by the RP2354A layer or the simulator) ---- */
void hal_step_segment(int axis, int32_t steps, uint32_t tick_us);

/* ---- API ---- */
void motion_init(motion_t *m);
void motion_default_cfg(axis_cfg_t *c, int axis);
void motion_tick(motion_t *m, uint64_t head_us);                 /* core 1, 1 kHz */
void motion_feed_encoder(motion_t *m, int axis, uint32_t raw21, uint8_t status, bool crc_ok);  /* core 0, 1 kHz */
void motion_feed_temp(motion_t *m, int axis, float temp_c);
void motion_feed_driver(motion_t *m, int axis, uint16_t sg, bool diag, uint32_t drv_status);
void motion_feed_rail(motion_t *m, uint8_t rail_now, uint16_t vmot_mv);
void motion_slow_loop(motion_t *m);                              /* core 0, 5 Hz: encoder correction, slip, thermal */
void motion_handle(motion_t *m, uint8_t type, const uint8_t *payload, size_t len, uint64_t now_us);
void motion_fill_state(const motion_t *m, st_state_t *s);
/* what the hardware layer should do now */
uint8_t motion_rail_wanted(const motion_t *m);                   /* 0 off, 1 10 V, 2 16 V */
uint16_t motion_current_ma(const motion_t *m, int axis, bool *spread);
bool motion_drivers_wanted(const motion_t *m);
/* events: the core queues them, the link layer drains them */
bool motion_pop_event(motion_t *m, st_event_t *ev);
/* encoder linearisation (also used by calibration) */
double motion_enc_correction_arcsec(const axis_tables_t *t, double theta_deg);
/* conversions */
static inline double motion_angle_to_usteps(const axis_cfg_t *c, int64_t a) { return (double)a * c->usteps_per_rev / 4294967296.0; }
static inline int64_t motion_usteps_to_angle(const axis_cfg_t *c, double u) { return (int64_t)(u * 4294967296.0 / c->usteps_per_rev); }

#ifdef __cplusplus
}
#endif
