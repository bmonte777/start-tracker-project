/* Star Tracker RP2354A — bring-up tests (docs/04-electronics.md section 11, Stages B, C and D).
 *
 * Each test is a small state machine stepped from the core 0 loop (the watchdog must keep being fed), and
 * reports text lines and a final PASS / FAIL through ST_MSG_TEST_RESULT. The ESP32 bring-up menu shows them on
 * its serial console and the OLED. Limits come from the bring-up plan; each one is cited where it is used.
 *
 * Geometry argument (st_test_t.arg bit 15): 0 = encoder on the axis output (cartridge in place),
 * 1 = magnet on the bare motor shaft (Stage D step 1 bench set-up). Axis: 0 az, 1 alt, 2 roll.
 */
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hw.h"
#include "motion.h"
#include "rp_app.h"

#if RP_IS_BRINGUP

#define ARCSEC_PER_COUNT (1296000.0 / 2097152.0)       /* MT6835: 0.618" per count */
#define SIDEREAL_DPS     (360.0 / 86164.0905)

typedef struct {
    bool active, owns_rail;
    uint8_t test, axis;
    uint16_t arg;
    int32_t arg2;
    int phase;
    uint64_t t0, tnext;
    uint32_t n, bad, warn, crc;
    double sum, sum2, mn, mx, a, b, c;
    double last_deg, start_deg, prev_raw;
    int64_t turns;
    bool pass;
    int rep;
} tstate_t;
static tstate_t T;

static void say(const char *fmt, ...)
{
    st_test_result_t r = {T.test, T.axis, 0, 0, {0}};
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(r.text, sizeof r.text, fmt, ap);
    va_end(ap);
    hw_link_send(ST_MSG_TEST_RESULT, &r, sizeof r);
}

static void finish(bool pass, const char *fmt, ...)
{
    st_test_result_t r = {T.test, T.axis, (uint8_t)pass, 1, {0}};
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(r.text, sizeof r.text, fmt, ap);
    va_end(ap);
    hw_link_send(ST_MSG_TEST_RESULT, &r, sizeof r);
    if (T.owns_rail) { hw_rail_set(RAIL_OFF); }
    T.active = T.owns_rail = false;
}

/* ---- helpers to drive the motion core exactly as the ESP32 would ---- */
static void cfg(uint16_t key, uint8_t axis, int64_t v) { st_cfg_t c = {key, axis, 0, v}; rp_post(ST_MSG_CFG_SET, &c, sizeof c); }
static void power(uint8_t req) { st_power_t p = {req, 0, 36000}; rp_post(ST_MSG_POWER, &p, sizeof p); }
static int64_t deg_angle(double d) { return (int64_t)(d / 360.0 * 4294967296.0); }
static void move_rel(uint8_t axis, double deg, double dps, bool fast)
{
    st_move_t m;
    memset(&m, 0, sizeof m);
    m.axis_mask = (uint8_t)(1u << axis);
    m.flags = (uint8_t)(2 | (fast ? 1 : 0));
    m.vmax_mdeg_s = (uint16_t)(dps * 1000.0);
    m.target[axis] = deg_angle(deg);
    rp_post(ST_MSG_MOVE, &m, sizeof m);
}
static void stop_axis(uint8_t axis) { st_stop_t s = {(uint8_t)(1u << axis), 0}; rp_post(ST_MSG_STOP, &s, sizeof s); }

static bool geom_motor(void) { return (T.arg & 0x8000) != 0; }
/* output degrees commanded -> degrees the encoder should see */
static double enc_per_out(void) { return geom_motor() ? 300.0 : 1.0; }

static bool enc_deg(uint8_t axis, double *deg, uint8_t *status)
{
    enc_sample_t s;
    hw_enc_read(axis, &s);
    if (status) *status = s.status;
    if (!s.crc_ok) { T.crc++; return false; }
    double raw = (double)s.raw;
    if (T.n > 0 || T.prev_raw >= 0) {
        double d = raw - T.prev_raw;
        if (d > 1048576.0) T.turns--;
        else if (d < -1048576.0) T.turns++;
    }
    T.prev_raw = raw;
    *deg = (raw + 2097152.0 * (double)T.turns) * 360.0 / 2097152.0;
    return true;
}

static double cmd_deg(uint8_t axis)
{
    st_state_t st;
    rp_snapshot(&st, NULL);
    return (double)st.ax[axis].cmd * 360.0 / 4294967296.0;
}

static void prep_axis_for_bench(uint8_t axis)
{
    /* 0.3 A everywhere (Stage D step 3); with the magnet on the motor shaft the motion core's own encoder checks
     * would see 300x the angle, so they are switched off for the test */
    cfg(ST_CFG_I_RUN_MA, axis, 300);
    cfg(ST_CFG_I_TRACK_MA, axis, 300);
    cfg(ST_CFG_I_HOLD_MA, axis, 300);
    cfg(ST_CFG_LIMIT_MIN, axis, INT64_MIN);
    if (geom_motor()) {
        cfg(ST_CFG_SLIP_LIMIT, axis, deg_angle(90.0));
        cfg(ST_CFG_CORR_DEADBAND, axis, deg_angle(90.0));
    }
}

void rp_test_request(const uint8_t *pl, size_t len)
{
    if (len < sizeof(st_test_t)) return;
    const st_test_t *q = (const st_test_t *)pl;
    if (q->test == RT_ABORT) {
        if (T.active) { stop_axis(T.axis); finish(false, "aborted"); }
        return;
    }
    if (T.active) { say("busy with test %d", T.test); return; }
    memset(&T, 0, sizeof T);
    T.active = true;
    T.test = q->test;
    T.axis = q->axis > 2 ? 0 : q->axis;
    T.arg = q->arg;
    T.arg2 = q->arg2;
    T.prev_raw = -1;
    T.mn = 1e30;
    T.mx = -1e30;
    T.t0 = time_us_64();
}

bool rp_test_active(void) { return T.active; }
bool rp_test_owns_rail(void) { return T.active && T.owns_rail; }

static const char *AX[3] = {"azimuth", "altitude", "roll"};

void rp_test_poll(void)
{
    if (!T.active) return;
    uint64_t now = time_us_64();
    if (now < T.tnext) return;

    switch (T.test) {
    case RT_INFO:
        say("RP2354A bring-up image %d.%d.%d, link protocol %d", 0, 1, 0, ST_LINK_VERSION);
        say("PPS edges seen: %lu, crystal error %.1f ppm", (unsigned long)hw_time_pps_count(), hw_time_ppm());
        finish(true, "info");
        break;

    case RT_STEPGEN: {                                  /* Stage B: PIO alive, no motor needed */
        bool ok = true;
        for (int i = 0; i < ST_AXES; i++) ok &= hw_stepgen_push(i, 10, 1000);
        sleep_ms(3);
        finish(ok && hw_stepgen_overflows() == 0, "step generators: 10 pulses queued on STEP_AZ/ALT/ROLL (GPIO16/18/20); scope them");
        break;
    }

    case RT_NTC: {                                      /* Stage D step 2: room temperature */
        bool pass = true;
        for (int i = 0; i < ST_AXES; i++) {
            float v = hw_adc_volts(i), t = hw_ntc_from_volts(v);
            const char *note = v > 3.28f ? "open (no bead fitted?)" : (v < 0.02f ? "SHORT" : "");
            bool ok = t > 5.0f && t < 45.0f;
            say("%-8s %.3f V  %.1f C  %s %s", AX[i], v, t, ok ? "ok" : "out of 5..45 C", note);
            if (i == T.axis || T.arg == 0xFFFF) pass &= ok;
        }
        finish(pass, "thermistor on the tested axis reads room temperature (limit 5-45 C)");
        break;
    }

    case RT_DRV_UART: {                                 /* Stage B / D: the three drivers answer on the one-wire UART */
        int good = 0;
        T.owns_rail = true;                             /* the TMC2209 logic runs from its own regulator on VS: rail on */
        if (!hw_rail_set(RAIL_10V)) { finish(false, "motor rail did not come up (VMOT %.2f V); drivers need it to answer", hw_vmot()); break; }
        sleep_ms(5);
        for (int i = 0; i < ST_AXES; i++) {
            uint32_t ioin = 0, ifc = 0;
            bool r = hw_tmc_read(hw_tmc[i].addr, TMC_IOIN, &ioin);
            bool v = r && (ioin >> 24) == 0x21;
            hw_tmc_read(hw_tmc[i].addr, TMC_IFCNT, &ifc);
            say("driver %s addr %d: %s, IOIN 0x%08lx (version 0x%02lx, want 0x21), IFCNT %lu", AX[i], hw_tmc[i].addr,
                r ? "answers" : "NO ANSWER", (unsigned long)ioin, (unsigned long)(ioin >> 24), (unsigned long)ifc);
            if (v) {
                bool s = hw_tmc_setup(i);
                say("  set-up %s (GCONF, CHOPCONF, PWMCONF, IHOLD_IRUN written and counted)", s ? "verified" : "FAILED");
                good += s;
            }
        }
        finish(good == 3, "%d of 3 drivers answer and accept set-up (rail at 10 V during the test)", good);
        break;
    }

    case RT_RAIL:                                       /* Stage C step 1: 10.0 V and 16.0 V */
        T.owns_rail = true;
        if (T.phase == 0) {
            if (!hw_rail_set(RAIL_10V)) { finish(false, "rail did not reach 10 V within 15 ms (VMOT %.2f V)", hw_vmot()); break; }
            T.phase = 1; T.tnext = now + 100000;
        } else if (T.phase == 1) {
            T.a = hw_vmot();
            say("10 V level: VMOT %.2f V (limit 9.5-10.5)", T.a);
            hw_rail_set(RAIL_16V);
            T.phase = 2; T.tnext = now + 100000;
        } else {
            T.b = hw_vmot();
            say("16 V level: VMOT %.2f V (limit 15.5-16.5)", T.b);
            hw_rail_set(RAIL_10V);
            bool ok = T.a > 9.5 && T.a < 10.5 && T.b > 15.5 && T.b < 16.5;
            finish(ok, "rail levels; check ripple < 100 mV p-p on TP30 with the oscilloscope");
        }
        break;

    case RT_RAIL_LOAD:                                  /* Stage C step 2: 10 ohm load on VMOT for one minute */
        T.owns_rail = true;
        if (T.phase == 0) {
            if (!hw_rail_set(RAIL_16V)) { finish(false, "rail failed to start"); break; }
            say("16 V on: connect the 10 ohm load now; measuring for 60 s");
            T.phase = 1; T.t0 = now + 2000000; T.tnext = T.t0;
        } else {
            double v = hw_vmot();
            if (v < T.mn) T.mn = v;
            if (v > T.mx) T.mx = v;
            T.tnext = now + 10000;
            if (now - T.t0 > 60000000) {
                bool ok = T.mn > 15.84 && T.mx < 16.24;   /* 16.04 V +/- 0.2 V (plan: holds within 0.2 V) */
                finish(ok, "VMOT min %.2f max %.2f V over 60 s (limit 16.04 +/- 0.2); feel L5 < 70 C", T.mn, T.mx);
            }
        }
        break;

    case RT_ENC: {                                      /* Stage D step 2: angle changes when turned by hand */
        int ok = 0;
        for (int k = 0; k < 10; k++) {
            enc_sample_t s;
            if (hw_enc_read(T.axis, &s) && !(s.status & 0x07)) ok++;
            if (k == 9) say("%s encoder: raw %lu = %.4f deg, status %d%d%d (uv, weak, overspeed), CRC %s", AX[T.axis],
                            (unsigned long)s.raw, s.raw * 360.0 / 2097152.0, (s.status >> 2) & 1, (s.status >> 1) & 1,
                            s.status & 1, s.crc_ok ? "ok" : "BAD");
            sleep_us(500);
        }
        finish(ok == 10, "10 of 10 readings with good CRC and no warning (%d)", ok);
        break;
    }

    case RT_ENC_NOISE: {                                /* Stage D step 8, D48: 1000 readings, shaft still */
        double d;
        uint8_t st;
        if (enc_deg(T.axis, &d, &st)) {
            if (st & 0x02) T.warn++;
            if (st & 0x05) T.bad++;
            double as = d * 3600.0;
            if (T.n == 0) T.a = as;                     /* reference to keep numbers small */
            double x = as - T.a;
            T.sum += x; T.sum2 += x * x;
            if (x < T.mn) T.mn = x;
            if (x > T.mx) T.mx = x;
            T.n++;
        }
        T.tnext = now + 1000;
        if (T.n >= 1000 || T.crc > 50) {
            double mean = T.sum / (T.n ? T.n : 1);
            double rms = sqrt(fmax(0.0, T.sum2 / (T.n ? T.n : 1) - mean * mean));
            /* datasheet: 0.0015 deg RMS = 5.4" at BW=5; this image runs BW=3, so 2x the datasheet figure fails */
            bool ok = T.n >= 1000 && T.warn == 0 && T.crc == 0 && rms <= 10.8;
            finish(ok, "%s: %lu readings, spread %.2f\" RMS, %.1f\" p-p, weak-field %lu, CRC errors %lu (limit 10.8\" RMS = 2x datasheet, no warnings). "
                   "Fail = raise the board 0.5 mm (D48)", AX[T.axis], (unsigned long)T.n, rms, T.mx - T.mn,
                   (unsigned long)T.warn, (unsigned long)T.crc);
        }
        break;
    }

    case RT_ENC_SWEEP: {                                /* Stage D step 8 part 2: one slow revolution of the magnet */
        double sweep_enc = T.arg2 ? T.arg2 : 360.0;     /* degrees as the encoder sees them */
        double out = sweep_enc / enc_per_out();
        if (T.phase == 0) {
            prep_axis_for_bench(T.axis);
            power(1);
            enc_deg(T.axis, &T.start_deg, NULL);
            T.last_deg = T.start_deg;
            T.c = cmd_deg(T.axis);
            move_rel(T.axis, out, fmin(1.0, out / 60.0) , false);   /* about one minute */
            T.phase = 1; T.tnext = now + 300000;
        } else {
            double d;
            uint8_t st;
            if (enc_deg(T.axis, &d, &st)) {
                double step = d - T.last_deg;
                if (step < -0.01) T.bad++;                       /* went backwards by more than noise */
                if (fabs(step) > 0.05) T.warn++;                  /* jump between 1 ms samples */
                if (st & 0x02) T.b++;
                double expect = T.start_deg + (cmd_deg(T.axis) - T.c) * enc_per_out();
                double dev = (d - expect) * 3600.0;
                if (dev < T.mn) T.mn = dev;
                if (dev > T.mx) T.mx = dev;
                if (fabs(step) < 1e-9) T.rep++; else T.rep = 0;
                if (T.rep > 200) T.a++;                            /* flat spot: no change for 200 ms while moving */
                T.last_deg = d;
                T.n++;
            }
            T.tnext = now + 1000;
            st_state_t s;
            rp_snapshot(&s, NULL);
            if (s.ax[T.axis].mode == ST_AX_HOLDING && now - T.t0 > 2000000) {
                bool ok = T.bad == 0 && T.warn == 0 && T.a == 0 && T.b == 0 && T.crc == 0;
                finish(ok, "%s sweep %.0f deg: %lu samples, reversals %lu, jumps %lu, flat spots %.0f, weak-field %.0f, CRC %lu; "
                       "encoder minus steps %.0f..%.0f\" (raw linearity, before the map)", AX[T.axis], sweep_enc,
                       (unsigned long)T.n, (unsigned long)T.bad, (unsigned long)T.warn, T.a, T.b, (unsigned long)T.crc, T.mn, T.mx);
            }
        }
        break;
    }

    case RT_STEP: {                                     /* Stage D step 3: motor holds; step slowly, encoder follows */
        double out = geom_motor() ? 360.0 / 300.0 : 5.0;  /* one motor turn on the bench, 5 deg on the head */
        if (T.phase == 0) {
            prep_axis_for_bench(T.axis);
            power(1);
            T.phase = 1; T.tnext = now + 500000;
        } else if (T.phase == 1) {
            enc_deg(T.axis, &T.start_deg, NULL);
            T.c = cmd_deg(T.axis);
            move_rel(T.axis, out, 0.25, false);
            T.phase = 2; T.tnext = now + 500000;
        } else {
            double d;
            enc_deg(T.axis, &d, NULL);
            st_state_t s;
            rp_snapshot(&s, NULL);
            T.tnext = now + 20000;
            if (s.ax[T.axis].mode == ST_AX_HOLDING) {
                double moved = d - T.start_deg, want = (cmd_deg(T.axis) - T.c) * enc_per_out();
                double err = fabs(moved - want) / fabs(want) * 100.0;
                bool ok = moved * want > 0 && err < 2.0;
                finish(ok, "%s: commanded %+.3f deg, encoder %+.3f deg (%.2f %% difference, limit 2 %%, same direction). "
                       "If the direction is wrong set DIR_INVERT for this axis", AX[T.axis], want, moved, err);
            }
        }
        break;
    }

    case RT_TRACK: {                                    /* Stage D step 4: sidereal for 10 min, log encoder vs command */
        int minutes = T.arg2 ? T.arg2 : 10;
        if (T.phase == 0) {
            prep_axis_for_bench(T.axis);
            power(1);
            T.phase = 1; T.tnext = now + 500000;
        } else if (T.phase == 1) {
            st_setpoint_t sp;
            memset(&sp, 0, sizeof sp);
            st_state_t s;
            rp_snapshot(&s, NULL);
            sp.t_us = s.t_us;
            sp.valid_ms = 65000;
            sp.axis_mask = (uint8_t)(1u << T.axis);
            sp.ax[T.axis].pos = s.ax[T.axis].cmd;
            sp.ax[T.axis].rate = (int64_t)(SIDEREAL_DPS / 360.0 * 1099511627776.0);
            rp_post(ST_MSG_SETPOINT, &sp, sizeof sp);
            enc_deg(T.axis, &T.start_deg, NULL);
            T.c = (double)s.ax[T.axis].cmd * 360.0 / 4294967296.0;
            T.t0 = now;
            say("t_s,cmd_arcsec,enc_arcsec,err_arcsec");
            T.phase = 2; T.tnext = now + 1000000;
        } else {
            double d;
            enc_deg(T.axis, &d, NULL);
            double cmdd = (cmd_deg(T.axis) - T.c) * enc_per_out() * 3600.0;
            double encd = (d - T.start_deg) * 3600.0;
            double e = encd - cmdd;
            T.sum += e; T.sum2 += e * e; T.n++;
            if (e < T.mn) T.mn = e;
            if (e > T.mx) T.mx = e;
            say("%.0f,%.2f,%.2f,%.2f", (now - T.t0) / 1e6, cmdd, encd, e);
            T.tnext += 1000000;
            if (now - T.t0 > (uint64_t)minutes * 60000000ull) {
                stop_axis(T.axis);
                double mean = T.sum / T.n, rms = sqrt(fmax(0, T.sum2 / T.n - mean * mean));
                finish(T.crc == 0, "%s tracking %d min: encoder minus command %.1f\" RMS, %.1f\" p-p (encoder not yet mapped; "
                       "keep this log: first periodic-error number)", AX[T.axis], minutes, rms, T.mx - T.mn);
            } else if ((T.n % 30) == 0) {                   /* refresh the setpoint every 30 s (valid 65 s) */
                st_setpoint_t sp;
                memset(&sp, 0, sizeof sp);
                st_state_t s2;
                rp_snapshot(&s2, NULL);
                double el = (now - T.t0) / 1e6;
                sp.t_us = s2.t_us;
                sp.valid_ms = 65000;
                sp.axis_mask = (uint8_t)(1u << T.axis);
                sp.ax[T.axis].pos = deg_angle(T.c + SIDEREAL_DPS * el);
                sp.ax[T.axis].rate = (int64_t)(SIDEREAL_DPS / 360.0 * 1099511627776.0);
                rp_post(ST_MSG_SETPOINT, &sp, sizeof sp);
            }
        }
        break;
    }

    case RT_SLEW: {                                     /* Stage D step 5: 16 V, 8 deg/s equivalent, 10 times */
        double out = geom_motor() ? 30.0 : 30.0;          /* 30 deg of output = 25 motor turns on the bench */
        if (T.phase == 0) {
            prep_axis_for_bench(T.axis);
            cfg(ST_CFG_I_RUN_MA, T.axis, T.axis == 0 ? 830 : 450);   /* 20 C slew currents (phase4_results.json) */
            power(2);
            T.phase = 1; T.tnext = now + 500000;
        } else if (T.phase == 1) {
            enc_deg(T.axis, &T.start_deg, NULL);
            T.c = cmd_deg(T.axis);
            move_rel(T.axis, (T.rep % 2) ? -out : out, 8.0, true);
            T.phase = 2; T.tnext = now + 300000;
        } else {
            double d;
            enc_deg(T.axis, &d, NULL);              /* keep the unwrap alive (1 kHz is needed above 2 turns/s) */
            if (hw_tmc_diag(T.axis)) T.warn++;
            st_state_t s;
            rp_snapshot(&s, NULL);
            T.tnext = now + 200;
            if (s.ax[T.axis].mode == ST_AX_HOLDING) {
                double moved = d - T.start_deg, want = (cmd_deg(T.axis) - T.c) * enc_per_out();
                double lost = fabs(moved - want);
                if (lost > T.mx) T.mx = lost;
                say("run %d: commanded %+.2f deg, encoder %+.2f deg, difference %.3f deg", T.rep + 1, want, moved, lost);
                if (++T.rep >= 10) {
                    double lim = 0.05 * enc_per_out();
                    finish(T.mx < lim && T.warn == 0, "%s slews at 8 deg/s: worst difference %.3f deg (limit %.2f), DIAG high %lu times (limit 0)",
                           AX[T.axis], T.mx, lim, (unsigned long)T.warn);
                } else {
                    T.phase = 1;
                }
            }
        }
        break;
    }

    case RT_FIELD: {                                    /* Stage D step 6: holding at full current vs zero */
        T.owns_rail = true;
        double d;
        if (T.phase == 0) {
            hw_rail_set(RAIL_10V);
            hw_tmc_setup(T.axis);
            hw_tmc_set_current(T.axis, T.axis == 0 ? 1350 : 1060);   /* the motor's ceiling (spec 3.6) */
            hw_tmc_enable(true);
            T.phase = 1; T.tnext = now + 2000000;
        } else if (T.phase == 1 || T.phase == 3) {
            if (enc_deg(T.axis, &d, NULL)) { T.sum += d * 3600.0; T.n++; }
            T.tnext = now + 1000;
            if (T.n >= 1000) {
                if (T.phase == 1) { T.a = T.sum / T.n; T.sum = 0; T.n = 0; hw_tmc_enable(false); T.phase = 2; T.tnext = now + 1000000; }
                else {
                    T.b = T.sum / T.n;
                    double diff = fabs(T.a - T.b);
                    finish(diff <= 10.0, "%s encoder: mean at full current vs zero current differs by %.1f\" (limit 10\"; above it the "
                           "motor's field reaches the chip and is calibrated out in the map)", AX[T.axis], diff);
                }
            }
        } else {
            T.phase = 3;
        }
        break;
    }

    default:
        finish(false, "unknown test %d", T.test);
        break;
    }
}

#else   /* release image: no tests */

void rp_test_request(const uint8_t *pl, size_t len)
{
    (void)len;
    st_test_result_t r = {pl[0], 0, 0, 1, "this is the motion image; load the bring-up image for tests"};
    hw_link_send(ST_MSG_TEST_RESULT, &r, sizeof r);
}
void rp_test_poll(void) {}
bool rp_test_active(void) { return false; }
bool rp_test_owns_rail(void) { return false; }

#endif
