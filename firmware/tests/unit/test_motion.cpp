// Motion core (firmware/rp2354a/motion) driven through the real link framing on the simulated axes.
#include <cstring>
#include "sim_head.h"
#include "tst.h"
using namespace st;

static const double U = 15360000.0;                         // microsteps per output turn (D2/D23)
static int64_t ang(double deg) { return (int64_t)(deg / 360.0 * 4294967296.0); }
static Settings base() { Settings s; s.site.lat = 38.72; s.site.lon = -9.14; return s; }

static void power(sim::SimHead &h, uint8_t req) { st_power_t p = {req, 0, 36000}; h.send(ST_MSG_POWER, &p, sizeof p); }
static void move(sim::SimHead &h, int axis, double deg, double dps, bool rel = true)
{
    st_move_t m;
    memset(&m, 0, sizeof m);
    m.axis_mask = (uint8_t)(1 << axis);
    m.flags = (uint8_t)(1 | (rel ? 2 : 0));
    m.vmax_mdeg_s = (uint16_t)(dps * 1000);
    m.target[axis] = ang(deg);
    h.send(ST_MSG_MOVE, &m, sizeof m);
}

TEST(motion_slew_90deg_at_8dps_exact_steps)
{
    sim::SimHead h(1.8e9, base());
    h.advance(0.5);
    power(h, 2);
    double start = h.axis[0].motor_usteps;
    move(h, 0, 90.0, 8.0);
    double peak_rate = 0, last = start, max_pos = 0;
    int t_ms = 0;
    for (; t_ms < 30000; t_ms++) {
        h.advance(0.001);
        double p = h.axis[0].motor_usteps;
        peak_rate = std::fmax(peak_rate, std::fabs(p - last));
        max_pos = std::fmax(max_pos, p - start);
        last = p;
        if (t_ms > 500 && h.motion().ax[0].mode == ST_AX_HOLDING) break;
    }
    double moved = h.axis[0].motor_usteps - start;
    NOTE("90 deg: %.0f microsteps (want %.0f), %.2f s, peak %.0f steps/ms = %.2f deg/s, overshoot %.1f steps, rail %d during the slew",
         moved, U / 4, t_ms / 1000.0, peak_rate, peak_rate * 1000 * 360 / U, max_pos - U / 4, 2);
    CHECK_NEAR(moved, U / 4, 0.5);
    CHECK(peak_rate <= 342 + 1);                                  // 8 deg/s = 341.3 steps per ms
    CHECK(peak_rate >= 330);
    CHECK(max_pos - U / 4 <= 0.5);                                // no overshoot
    CHECK(t_ms < 90.0 / 8.0 * 1000 + 3500);
}

TEST(motion_short_move_and_reversal)
{
    sim::SimHead h(1.8e9, base());
    h.advance(0.5);
    power(h, 2);
    double start = h.axis[1].motor_usteps;
    move(h, 1, 10.0, 8.0);
    h.advance(1.0);
    move(h, 1, -20.0, 8.0);                                       // retarget while moving: relative to where it is now
    h.advance(15.0);
    double p_now = h.axis[1].motor_usteps - start;
    CHECK(h.motion().ax[1].mode == ST_AX_HOLDING);
    double cmd = h.motion().ax[1].p;
    CHECK_NEAR(h.axis[1].motor_usteps, cmd + h.motion().ax[1].corr + h.motion().ax[1].step_off, 0.51);
    NOTE("after +10 deg then -20 deg retarget: axis at %.4f deg", p_now * 360 / U);
    double t0 = h.axis[1].motor_usteps;
    move(h, 1, 0.01, 8.0);                                        // 0.01 deg = 427 microsteps
    h.advance(2.0);
    CHECK_NEAR(h.axis[1].motor_usteps - t0, 0.01 / 360 * U, 0.5);
}

TEST(motion_sidereal_tracking_rate_is_exact)
{
    sim::SimHead h(1.8e9, base());
    h.axis[0].pe_amp_as = 0;                                      // look at the step train and the correction loop only
    h.advance(0.5);
    power(h, 1);
    double rate_dps = 360.0 / 86164.0905;
    double start = h.axis[0].motor_usteps;
    st_setpoint_t sp;
    double worst = 0, sum2 = 0;
    int n = 0;
    for (int k = 0; k < 6000; k++) {                              // 600 s at 10 setpoints per second, like the ESP32
        memset(&sp, 0, sizeof sp);
        int64_t t = h.now_us() + 200000;
        double el = (t - 1.8e15 - 500000) / 1e6;
        sp.t_us = (uint64_t)t;
        sp.valid_ms = 500;
        sp.axis_mask = 1;
        sp.flags = 2;                                             // encoder correction on, as the ESP32 sends it
        sp.ax[0].pos = ang(start * 360 / U + rate_dps * el);
        sp.ax[0].rate = (int64_t)(rate_dps / 360 * (double)ST_RATE_ONE_REV_S);
        h.send(ST_MSG_SETPOINT, &sp, sizeof sp);
        h.advance(0.1);
        double tnow = (h.now_us() - 1.8e15 - 500000) / 1e6;
        double ideal = start + rate_dps * tnow / 360 * U;
        double err = h.axis[0].out_deg / 360 * U - ideal;            // the OUTPUT, after the 12" lost motion and the encoder loop
        if (k > 150) { worst = std::fmax(worst, std::fabs(err)); sum2 += err * err; n++; }   // after 15 s: the correction moves at 1"/s
    }
    double rms_as = std::sqrt(sum2 / n) * 360 / U * 3600;
    NOTE("600 s sidereal: output vs ideal %.2f\" RMS, worst %.2f\" (12\" lost motion taken out by the encoder loop, 2\" deadband)", rms_as, worst * 360 / U * 3600);
    CHECK(worst * 360 / U * 3600 < 3.5);
    CHECK(rms_as < 2.5);
}

TEST(motion_soft_limit_clamps)
{
    sim::SimHead h(1.8e9, base());
    h.advance(0.5);
    power(h, 2);
    move(h, 1, 120.0, 8.0, false);                                // beyond +95 deg (altitude max, params.py)
    h.advance(25.0);
    double alt = h.motion().ax[1].p * 360 / U;
    NOTE("asked for +120 deg altitude, stopped at %.3f deg", alt);
    CHECK(alt <= 95.0 + 1e-6 && alt > 94.0);
    CHECK(h.motion().ax[1].flags & ST_AXF_AT_MAX);
}

TEST(motion_link_loss_stops_slew_and_coasts_tracking)
{
    sim::SimHead h(1.8e9, base());
    h.advance(1.0);
    power(h, 2);
    move(h, 0, 90, 8);
    h.advance(1.0);
    // stop sending heartbeats: the sim sends them every 100 ms, so cut the link by forcing the timeout short
    st_cfg_t c = {ST_CFG_HB_TIMEOUT_MS, 0xFF, 0, 1};
    h.send(ST_MSG_CFG_SET, &c, sizeof c);
    h.advance(3.0);
    CHECK(h.motion().faults & ST_F_LINK_LOST);
    CHECK(h.motion().ax[0].mode == ST_AX_HOLDING);
    double at = h.motion().ax[0].p * 360 / U;
    NOTE("link lost during a slew: axis ramped to rest at %.2f deg (of 90)", at);
    CHECK(at < 60);
}

TEST(motion_slip_detected_and_resynced)
{
    sim::SimHead h(1.8e9, base());
    h.advance(1.0);
    power(h, 1);
    move(h, 2, -5, 2);
    h.advance(4.0);
    h.axis[2].motor_usteps += 0.2 / 360 * U;                      // the output is pushed by 0.2 deg (lost steps)
    hal_step_segment(2, 0, 1000);
    h.advance(1.0);
    CHECK(h.motion().faults & ST_F_SLIP);
    double cmd = h.motion().ax[2].p * 360 / U, truth = h.axis[2].out_deg;
    NOTE("after a 0.2 deg slip: command re-synced to %.4f deg, axis really at %.4f deg", cmd, truth);
    CHECK_NEAR(cmd, truth, 0.01);
}
