/* Star Tracker RP2354A — main: core 0 does I/O, core 1 owns the motion core and runs the 1 kHz tick.
 *
 * Core 0 -> core 1: link messages and sensor samples through single-producer queues (mailbox below).
 * Core 1 -> core 0: STATE snapshot, wanted rail level and driver currents through a seqlock.
 * Nothing on core 1 ever waits for core 0.
 */
#include <string.h>
#include "pico/multicore.h"
#include "pico/stdlib.h"
#include "hardware/sync.h"
#include "hardware/watchdog.h"
#include "hw.h"
#include "motion.h"
#include "rp_app.h"

#define FW_MAJOR 0
#define FW_MINOR 1
#define FW_PATCH 0

/* ---------------------------------------------------------------- core 0 -> core 1 message queue */
#define MQ 16
typedef struct { uint8_t type; uint8_t len; uint8_t pl[ST_LINK_MAX_PAYLOAD]; } msg_t;
static msg_t mq[MQ];
static volatile uint32_t mq_w, mq_r;

bool rp_post(uint8_t type, const void *pl, size_t len)
{
    uint32_t n = (mq_w + 1) % MQ;
    if (n == mq_r || len > ST_LINK_MAX_PAYLOAD) return false;
    mq[mq_w].type = type;
    mq[mq_w].len = (uint8_t)len;
    memcpy(mq[mq_w].pl, pl, len);
    __dmb();
    mq_w = n;
    return true;
}

/* ---------------------------------------------------------------- sensor mailbox (core 0 writes) */
typedef struct {
    uint32_t seq;
    enc_sample_t enc[ST_AXES];
    uint32_t enc_count;
    float    temp[ST_AXES];
    uint16_t sg[ST_AXES];
    bool     diag[ST_AXES];
    uint32_t drv[ST_AXES];
    uint8_t  rail_now;
    uint16_t vmot_mv;
} sensors_t;
static sensors_t sens;

/* ---------------------------------------------------------------- core 1 -> core 0 snapshot */
typedef struct {
    uint32_t seq;
    st_state_t st;
    uint8_t  rail_wanted;
    bool     drivers_wanted;
    uint16_t ma[ST_AXES];
    bool     spread[ST_AXES];
    uint32_t ticks;
    double   usteps_per_rev[ST_AXES];
} snap_t;
static snap_t snap;

static motion_t M;            /* owned by core 1 */

void hal_step_segment(int axis, int32_t steps, uint32_t tick_us) { hw_stepgen_push(axis, steps, tick_us); }

/* ---------------------------------------------------------------- core 1 */
static volatile bool tick_flag;
static bool alarm_cb(repeating_timer_t *t) { (void)t; tick_flag = true; return true; }

static void core1_main(void)
{
    repeating_timer_t timer;
    motion_init(&M);
    add_repeating_timer_us(-(int64_t)MOTION_TICK_US, alarm_cb, NULL, &timer);   /* fixed-rate, core 1 alarm */
    uint32_t last_enc = 0, slow = 0;
    for (;;) {
        while (!tick_flag) __wfe();
        tick_flag = false;
        uint64_t now = hw_head_us();
        /* 1. messages from core 0 */
        while (mq_r != mq_w) {
            __dmb();
            motion_handle(&M, mq[mq_r].type, mq[mq_r].pl, mq[mq_r].len, now);
            mq_r = (mq_r + 1) % MQ;
        }
        /* 2. sensor samples (seqlock read) */
        sensors_t s;
        uint32_t q;
        do { q = sens.seq; __dmb(); s = sens; __dmb(); } while ((q & 1) || q != sens.seq);
        if (s.enc_count != last_enc) {
            last_enc = s.enc_count;
            for (int i = 0; i < ST_AXES; i++) motion_feed_encoder(&M, i, s.enc[i].raw, s.enc[i].status, s.enc[i].crc_ok);
        }
        if (++slow >= 200) {                                  /* 5 Hz */
            slow = 0;
            for (int i = 0; i < ST_AXES; i++) {
                motion_feed_temp(&M, i, s.temp[i]);
                motion_feed_driver(&M, i, s.sg[i], s.diag[i], s.drv[i]);
            }
            motion_feed_rail(&M, s.rail_now, s.vmot_mv);
            motion_slow_loop(&M);
        }
        /* 3. the tick itself */
        motion_tick(&M, now);
        /* 4. publish */
        snap.seq++;
        __dmb();
        motion_fill_state(&M, &snap.st);
        snap.rail_wanted = motion_rail_wanted(&M);
        snap.drivers_wanted = motion_drivers_wanted(&M);
        for (int i = 0; i < ST_AXES; i++) {
            snap.ma[i] = motion_current_ma(&M, i, &snap.spread[i]);
            snap.usteps_per_rev[i] = M.cfg[i].usteps_per_rev;
        }
        snap.ticks++;
        __dmb();
        snap.seq++;
    }
}

void rp_snapshot(st_state_t *st, uint32_t *ticks)
{
    snap_t c;
    uint32_t q;
    do { q = snap.seq; __dmb(); c = snap; __dmb(); } while ((q & 1) || q != snap.seq);
    if (st) *st = c.st;
    if (ticks) *ticks = c.ticks;
}

bool rp_pop_event(st_event_t *ev) { return motion_pop_event(&M, ev); }   /* SPSC: core 1 writes, core 0 reads */

/* ---------------------------------------------------------------- core 0 */
static void on_frame(void *ctx, uint8_t type, uint8_t seq, const uint8_t *pl, size_t len)
{
    (void)ctx; (void)seq;
    switch (type) {
    case ST_MSG_TIMESYNC:
        if (len >= sizeof(st_timesync_t)) hw_time_on_timesync((const st_timesync_t *)pl);
        break;
    case ST_MSG_HELLO: {
        st_hello_t h = {ST_LINK_VERSION, FW_MAJOR, FW_MINOR, FW_PATCH, 0, {'M', 'O', 'T', RP_IS_BRINGUP ? 'B' : 'R'}};
        hw_link_send(ST_MSG_HELLO, &h, sizeof h);
        break;
    }
    case ST_MSG_TEST:
        rp_test_request(pl, len);
        break;
    case ST_MSG_HEARTBEAT: {
        rp_post(type, pl, len);
        break;
    }
    default:
        rp_post(type, pl, len);
        break;
    }
}

static void sensors_write(void (*fn)(sensors_t *))
{
    sens.seq++;
    __dmb();
    fn(&sens);
    __dmb();
    sens.seq++;
}

static void read_encoders(sensors_t *s)
{
    for (int i = 0; i < ST_AXES; i++) hw_enc_read(i, &s->enc[i]);
    s->enc_count++;
}

static float temps[ST_AXES];
static uint16_t vmot_mv;
static uint32_t drv_status[ST_AXES];
static uint16_t sg[ST_AXES];
static void write_slow(sensors_t *s)
{
    for (int i = 0; i < ST_AXES; i++) {
        s->temp[i] = temps[i];
        s->sg[i] = sg[i];
        s->drv[i] = drv_status[i];
        s->diag[i] = hw_tmc_diag(i);
    }
    s->rail_now = (uint8_t)hw_rail_get();
    s->vmot_mv = vmot_mv;
}

int main(void)
{
    hw_led_init();
    hw_rail_init();                      /* rail off, ADC up */
    hw_tmc_init();                       /* drivers disabled */
    hw_stepgen_init();
    hw_enc_init(8000000);
    hw_time_init();
    hw_link_init(on_frame, NULL);
    /* encoder bandwidth: BW = 3 (register 0x011, bits 2:0); written every boot, never to EEPROM */
    for (int i = 0; i < ST_AXES; i++) {
        uint8_t v = 0;
        if (hw_enc_reg_read(i, 0x011, &v)) hw_enc_reg_write(i, 0x011, (uint8_t)((v & ~0x07) | 0x03));
    }
    multicore_launch_core1(core1_main);
    watchdog_enable(100, true);          /* 100 ms; fed only while core 1 ticks */

    st_hello_t h = {ST_LINK_VERSION, FW_MAJOR, FW_MINOR, FW_PATCH, 0, {'M', 'O', 'T', RP_IS_BRINGUP ? 'B' : 'R'}};
    hw_link_send(ST_MSG_HELLO, &h, sizeof h);
    st_event_t boot = {ST_EV_BOOT, 0xFF, 0, (int32_t)watchdog_caused_reboot()};
    hw_link_send(ST_MSG_EVENT, &boot, sizeof boot);

    uint64_t t_enc = 0, t_10 = 0, t_100 = 0, t_hb = 0, t_led = 0;
    uint32_t last_ticks = 0, drv_rr = 0;
    bool drv_ready[ST_AXES] = {false, false, false};
    bool drv_on = false;
    for (;;) {
        uint64_t t = time_us_64();
        hw_link_poll();
        if (t - t_enc >= 1000) { t_enc = t; sensors_write(read_encoders); }
        if (t - t_10 >= 10000) {                                  /* 100 Hz */
            t_10 = t;
            for (int i = 0; i < ST_AXES; i++) temps[i] = hw_ntc_c(i);
            vmot_mv = (uint16_t)(hw_vmot() * 1000.0f);
            sensors_write(write_slow);
            st_state_t st;
            uint32_t ticks;
            rp_snapshot(&st, &ticks);
            if (!rp_test_active()) hw_link_send(ST_MSG_STATE, &st, sizeof st);
            st_event_t ev;
            while (rp_pop_event(&ev)) hw_link_send(ST_MSG_EVENT, &ev, sizeof ev);
            if (ticks != last_ticks) watchdog_update();            /* core 1 alive */
            last_ticks = ticks;
            /* rail and drivers follow what the motion core wants */
            snap_t c;
            uint32_t q;
            do { q = snap.seq; __dmb(); c = snap; __dmb(); } while ((q & 1) || q != snap.seq);
            if (!rp_test_owns_rail()) {
                rail_level_t want = (rail_level_t)c.rail_wanted;
                if (want != hw_rail_get() && !hw_rail_set(want)) {
                    st_event_t e = {ST_EV_FAULT_SET, 0xFF, 2, (int32_t)ST_F_VMOT_LOW};
                    hw_link_send(ST_MSG_EVENT, &e, sizeof e);
                }
                if (c.drivers_wanted && hw_rail_get() != RAIL_OFF) {
                    for (int i = 0; i < ST_AXES; i++) {
                        if (!drv_ready[i]) drv_ready[i] = hw_tmc_setup(i);
                        if (drv_ready[i]) hw_tmc_set_current(i, c.ma[i]);
                    }
                    bool all = drv_ready[0] && drv_ready[1] && drv_ready[2];
                    if (all && !drv_on) { hw_tmc_enable(true); drv_on = true; }
                } else if (drv_on) {
                    hw_tmc_enable(false);
                    drv_on = false;
                }
                if (hw_rail_get() == RAIL_OFF) drv_ready[0] = drv_ready[1] = drv_ready[2] = false;
            }
        }
        if (t - t_100 >= 33333) {                                  /* one driver every 33 ms */
            t_100 = t;
            int i = (int)(drv_rr++ % ST_AXES);
            uint32_t v;
            if (drv_on && hw_tmc_read(hw_tmc[i].addr, TMC_DRV_STATUS, &v)) drv_status[i] = v;
            if (drv_on && hw_tmc_read(hw_tmc[i].addr, TMC_SG_RESULT, &v)) sg[i] = (uint16_t)v;
        }
        if (t - t_hb >= 100000) {
            t_hb = t;
            st_heartbeat_t hb = {(uint32_t)(t / 1000), 0, (uint16_t)hw_link_rx()->crc_errors};
            hw_link_send(ST_MSG_HEARTBEAT, &hb, sizeof hb);
        }
        if (t - t_led >= 250000) { t_led = t; static bool on; on = !on; hw_led_set(on); }   /* 2 Hz heartbeat */
        rp_test_poll();
    }
}
