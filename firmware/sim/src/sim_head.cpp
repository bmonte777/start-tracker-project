// Star Tracker simulator — see sim_head.h.
#include "sim_head.h"
#include <cmath>
#include <cstring>

namespace sim {

static SimHead *g_sim = nullptr;
static double g_usteps_per_rev[ST_AXES] = {15360000.0, 15360000.0, 15360000.0};

}  // namespace sim

extern "C" void hal_step_segment(int axis, int32_t steps, uint32_t tick_us)
{
    (void)tick_us;
    if (!sim::g_sim || axis < 0 || axis >= ST_AXES) return;
    sim::SimAxis &a = sim::g_sim->axis[axis];
    bool inv = sim::g_sim->motion().cfg[axis].dir_invert;
    double d = inv ? -steps : steps;                      // the driver undoes the direction inversion
    a.motor_usteps += d;
    double L = a.lost_motion_as / 3600.0 / 360.0 * sim::g_usteps_per_rev[axis];
    a.backlash_state = std::fmax(-L / 2, std::fmin(L / 2, a.backlash_state + d));
    double motor_turns = a.motor_usteps / (200.0 * 256.0);
    double pe = a.pe_amp_as / 3600.0 * std::sin(2.0 * 3.14159265358979 * motor_turns / 3.0 * 2.0);   // twice per wave-generator turn
    a.out_deg = (a.motor_usteps - a.backlash_state) * 360.0 / sim::g_usteps_per_rev[axis] + pe;
}

namespace sim {

SimHead::SimHead(double start_unix_s, const st::Settings &s)
    : t_us_((int64_t)(start_unix_s * 1e6)), head_(*this, [this] { return t_us_.load(); })
{
    g_sim = this;
    motion_init(&m_);
    m_.sys = ST_MS_IDLE;
    st_link_rx_init(&rx_mot_, [](void *ctx, uint8_t type, uint8_t, const uint8_t *pl, size_t len) {
        SimHead *h = (SimHead *)ctx;
        h->link_frames_mot++;
        motion_handle(&h->m_, type, pl, len, (uint64_t)h->t_us_.load());
    }, this);
    st_link_rx_init(&rx_app_, [](void *ctx, uint8_t type, uint8_t, const uint8_t *pl, size_t len) {
        SimHead *h = (SimHead *)ctx;
        h->link_frames_app++;
        h->head_.on_motion(type, pl, len);
    }, this);
    for (auto &a : axis) { a.enc_inl_as[0] = 0; a.enc_inl_as[1] = 0; }   // assume a mapped encoder (calibration is done once per head)
    head_.apply_settings(s);
    st::PowerInputs pin;
    pin.pack_ok = true; pin.pack_v = pack_v; pin.soc = (int)soc; pin.inside_temp_c = 20;
    head_.on_power(pin);
}

bool SimHead::send(uint8_t type, const void *payload, size_t len)
{
    uint8_t f[ST_LINK_MAX_FRAME + 8];
    size_t n = st_link_build(type, seq_app_++, payload, len, f);
    if (!n) return false;
    to_mot_.put(f, n);
    return true;
}

void SimHead::encoder_feed()
{
    std::normal_distribution<double> noise(0.0, 1.0);
    for (int i = 0; i < ST_AXES; i++) {
        SimAxis &a = axis[i];
        double th = a.out_deg + a.enc_offset_deg;
        double thr = th * 3.14159265358979 / 180.0;
        th += (a.enc_inl_as[0] * std::sin(thr + 0.7) + a.enc_inl_as[1] * std::sin(2 * thr + 1.9) + a.enc_noise_as * noise(rng_)) / 3600.0;
        double f = std::fmod(th, 360.0);
        if (f < 0) f += 360.0;
        uint32_t raw = (uint32_t)(f / 360.0 * 2097152.0) & 0x1FFFFF;
        motion_feed_encoder(&m_, i, raw, 0, true);
    }
}

void SimHead::tick_1ms()
{
    t_us_ += 1000;
    ms_++;
    // application -> motion bytes (the "UART")
    uint8_t buf[512];
    size_t n;
    while ((n = to_mot_.take(buf, sizeof buf)) > 0) st_link_rx_feed(&rx_mot_, buf, n);
    encoder_feed();
    if (ms_ % 200 == 0) {                                  // 5 Hz: temperatures, drivers, rail, slow loop
        for (int i = 0; i < ST_AXES; i++) { motion_feed_temp(&m_, i, 25.0f); motion_feed_driver(&m_, i, 300, false, 0); }
        uint8_t rail = motion_rail_wanted(&m_);
        motion_feed_rail(&m_, rail, rail == 2 ? 16040 : rail == 1 ? 10040 : 0);
        motion_slow_loop(&m_);
    }
    motion_tick(&m_, (uint64_t)t_us_.load());
    for (int i = 0; i < ST_AXES; i++) g_usteps_per_rev[i] = m_.cfg[i].usteps_per_rev;
    if (ms_ % 10 == 0) {                                   // 100 Hz STATE, events, heartbeat
        st_state_t st;
        motion_fill_state(&m_, &st);
        uint8_t f[ST_LINK_MAX_FRAME + 8];
        size_t k = st_link_build(ST_MSG_STATE, seq_mot_++, &st, sizeof st, f);
        to_app_.put(f, k);
        st_event_t ev;
        while (motion_pop_event(&m_, &ev)) { k = st_link_build(ST_MSG_EVENT, seq_mot_++, &ev, sizeof ev, f); to_app_.put(f, k); }
    }
    if (ms_ % 100 == 0) {                                  // application side: heartbeat to motion, tracker tick
        st_heartbeat_t hb = {ms_, 0, 0};
        send(ST_MSG_HEARTBEAT, &hb, sizeof hb);
    }
    while ((n = to_app_.take(buf, sizeof buf)) > 0) st_link_rx_feed(&rx_app_, buf, n);
    if (ms_ % 100 == 0) head_.tick();
    if (ms_ % 2000 == 0) {                                 // battery model: drain by the motion power
        double w = 3.0 + (m_.rail_now == 2 ? 15.0 : 0.0) + portb_w;
        soc = std::fmax(0.0, soc - w / 72.0 / 3600.0 * 2.0 * 100.0 * (charger ? -1.5 : 1.0));
        if (soc > 100) soc = 100;
        pack_v = 6.0 + 2.4 * soc / 100.0;
        st::PowerInputs pin;
        pin.pack_ok = true; pin.pack_v = pack_v; pin.soc = (int)soc; pin.inside_temp_c = 20; pin.portb_w = portb_w; pin.charging = charger;
        head_.on_power(pin);
    }
    link_errors = rx_app_.crc_errors + rx_mot_.crc_errors;
}

void SimHead::advance(double seconds)
{
    std::lock_guard<std::mutex> l(sim_mu);
    int64_t n = (int64_t)std::llround(seconds * 1000.0);
    for (int64_t i = 0; i < n; i++) tick_1ms();
}

}  // namespace sim
