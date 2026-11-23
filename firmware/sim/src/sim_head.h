// Star Tracker simulator — the simulated head: the real motion core (motion.c) on simulated axes, the real link framing,
// and the real Head model on the application side. Deterministic: advance(dt) steps simulated time in 1 ms ticks.
#pragma once
#include <atomic>
#include <cstdint>
#include <deque>
#include <mutex>
#include <random>
#include <vector>
#include "motion.h"
#include "st_head.h"

namespace sim {

struct SimAxis {
    double motor_usteps = 0;            // microsteps actually made (from the step segments)
    double backlash_state = 0;          // position inside the lost-motion band (usteps)
    double out_deg = 0;                 // true output angle
    double pe_amp_as = 20.0;            // reducer periodic error, +/-20" (spec 4.1)
    double enc_inl_as[2] = {250.0, 60.0};   // encoder non-linearity before the map: 1st and 2nd harmonic (MT6835 +/-0.07 deg class... raw +/-0.5 deg)
    double lost_motion_as = 12.0;       // wind-up at reversal (spec 4.5, size 17)
    double enc_noise_as = 5.4;          // MT6835 transition noise, 0.0015 deg RMS
    double enc_offset_deg = 0;
};

struct Pipe {                           // byte pipe with the real COBS framing on top
    std::mutex mu;
    std::deque<uint8_t> q;
    void put(const uint8_t *p, size_t n) { std::lock_guard<std::mutex> l(mu); q.insert(q.end(), p, p + n); }
    size_t take(uint8_t *p, size_t max) { std::lock_guard<std::mutex> l(mu); size_t n = 0; while (n < max && !q.empty()) { p[n++] = q.front(); q.pop_front(); } return n; }
};

class SimHead : public st::MotionPort {
public:
    SimHead(double start_unix_s, const st::Settings &s);
    bool send(uint8_t type, const void *payload, size_t len) override;   // application -> motion (via the pipe)
    void advance(double seconds);       // run the simulation forward
    int64_t now_us() const { return t_us_.load(); }
    st::Head &head() { return head_; }
    motion_t &motion() { return m_; }
    SimAxis axis[ST_AXES];
    // battery model
    double soc = 85, pack_v = 7.7, portb_w = 0;
    bool charger = false;
    std::mutex sim_mu;                  // held while advancing; protocol threads take the Head's own lock
    uint32_t link_frames_app = 0, link_frames_mot = 0, link_errors = 0;
    void seed(uint32_t s) { rng_.seed(s); }
    void set_time_us(int64_t t) { t_us_ = t; }    // time.set from an app (Phase 6)
    void raw_encoders();                         // encoders without their map (to exercise cal.encoder)
private:
    void tick_1ms();
    void encoder_feed();
    std::atomic<int64_t> t_us_;
    motion_t m_;
    st::Head head_;
    Pipe to_mot_, to_app_;
    st_link_rx_t rx_mot_, rx_app_;
    uint8_t seq_app_ = 0, seq_mot_ = 0;
    uint32_t ms_ = 0;
    std::mt19937 rng_{12345};
};

}  // namespace sim
