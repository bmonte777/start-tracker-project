// Star Tracker — the Head model: settings, state, tracker, pointing, power policy, intervalometer.
// Portable C++17. The protocols (Alpaca, LX200, WebSocket, BLE) and the UI call only this class.
// It talks to the motion processor through MotionPort (the real UART link on the ESP32, an in-memory pipe in the
// simulator) and gets time from a clock function (head time in microseconds, Unix epoch).
#pragma once
#include <cstdint>
#include <functional>
#include <mutex>
#include <string>
#include <vector>
#include "st_astro.h"
#include "st_link.h"
#include "st_mount.h"

namespace st {

// ------------------------------------------------------------------ payload envelopes (D40, docs/03-mechanical-design.md)
struct PayloadEnvelope {
    const char *name;
    double roll_toward_tower, roll_away;          // degrees at altitude 0 (CAD result)
    double tripod_roll_alt0[2], tripod_roll_alt45[2];   // roll where the payload passes the tripod top, [wedge on, off]; NAN = never
    double alt_cap[2];                            // altitude above which it hangs below the tripod top, [wedge on, off]; NAN = none
};
extern const PayloadEnvelope PAYLOADS[5];
constexpr double LIMIT_MARGIN_DEG = 3.0;          // "set the soft limits a few degrees inside" (Phase 3 set-up step 4)
constexpr double ALT_MIN = -10.0, ALT_MAX = 95.0; // hardware/cad/stcad/params.py ALT_MIN / ALT_MAX

// ------------------------------------------------------------------ settings (kept in NVS on the head, JSON in the sim)
struct Settings {
    Site site;                                    // lat, lon (deg), elevation, pressure, temperature, refraction
    MountMode mode = MountMode::AltAz;
    double wedge_deg = 51.3;                      // 90 - latitude for EQ
    double az0_deg = 0, tilt_x_deg = 0, tilt_y_deg = 0;   // mount orientation (alignment, IMU)
    int payload = 3;                              // P1..P5 (D40); default P3 = the reference rig
    bool wedge_fitted = true, pier_extension = false;
    double park_az = 0, park_alt = 0, park_roll = 0;
    bool roll_derotate = true;                    // alt-az: roll axis keeps the field orientation
    double slew_dps = 8.0;                        // D42
    double guide_rate = 0.5;                      // x sidereal
    bool dir_invert[ST_AXES] = {false, false, false};
    bool enc_invert[ST_AXES] = {false, false, false};
    uint16_t i_run_ma[ST_AXES] = {830, 450, 450}, i_track_ma[ST_AXES] = {320, 180, 180};       // 20 C (phase4_results.json)
    uint16_t i_run_cold_ma[ST_AXES] = {1260, 890, 890}, i_track_cold_ma[ST_AXES] = {750, 630, 630};   // -20 C
    std::string name = "StarTracker";
};

enum class TrackRate { Sidereal = 0, Lunar = 1, Solar = 2, King = 3 };      // ASCOM DriveRates order
enum class Activity { Idle, Slewing, Tracking, Moving, Parking, Parked, Fault };
enum class TargetKind { None, RaDecJ2000, RaDecApparent, Sun, Moon, Fixed };

struct PowerInputs {
    bool pack_ok = false; double pack_v = 7.4; int soc = 100; double pack_temp_c = 20;
    double inside_temp_c = 25; double portb_w = 0; double porta_source_w = 0; bool charging = false;
};
struct PowerDecision {
    uint16_t motion_budget_mw = 36000; bool portb_15w = false; bool low_battery = false; uint16_t charge_ma = 4000; bool allow_porta_source = true;
};
PowerDecision power_policy(const PowerInputs &in, double motion_demand_w);   // section 10.7 + Phase 4 pack-current rule

struct Intervalometer {
    int count = 0, done = 0;
    double exposure_s = 1, interval_s = 2, focus_s = 0.3, delay_s = 0;
    bool running = false, focus = false, release = false;
    double t_start = 0;
    void start(double now) { running = true; done = 0; t_start = now; }
    void stop() { running = false; focus = release = false; }
    void tick(double now);                        // sets focus / release outputs
};

struct AxisView { double cmd_deg = 0, enc_deg = 0, rate_dps = 0; int i_ma = 0, sg = 0; double temp_c = 0; int mode = 0; uint16_t flags = 0; };
struct HeadState {
    Activity activity = Activity::Idle;
    bool tracking = false, at_park = false, slewing = false;
    TrackRate rate = TrackRate::Sidereal;
    double ra_h = 0, dec_d = 0;                   // apparent (JNow) where the lens points
    double ra2000_h = 0, dec2000_d = 0;
    double az_deg = 0, alt_deg = 0;               // sky azimuth and altitude (observed)
    double pa_deg = 0;                            // image position angle (rotator)
    double lst_h = 0;
    AxisView ax[ST_AXES];
    double vmot = 0; int rail = 0; uint32_t motion_faults = 0;
    bool link_ok = false;
    int64_t t_us = 0; int time_quality = 0;
    // power
    bool pack_ok = false; double pack_v = 0, pack_a = 0, pack_temp_c = 0; int soc = 0; bool ext_power = false;
    PowerDecision power;
    std::vector<std::string> faults;
    PointingModel model;
};

class MotionPort {
public:
    virtual ~MotionPort() = default;
    virtual bool send(uint8_t type, const void *payload, size_t len) = 0;
};

class Head {
public:
    Head(MotionPort &port, std::function<int64_t()> clock_us);
    // configuration
    Settings settings() { std::lock_guard<std::recursive_mutex> l(mu_); return set_; }
    void apply_settings(const Settings &s);
    void push_motion_config();                    // currents, limits, direction, sent at start and on changes
    // the motion processor's messages
    void on_motion(uint8_t type, const uint8_t *pl, size_t len);
    void on_power(const PowerInputs &in);
    void tick();                                  // call every 100 ms (tracker task)
    // commands; return "" on success or a short error text (protocols map it)
    std::string goto_radec(double ra_h, double dec_d, bool j2000);
    std::string goto_altaz(double az_deg, double alt_deg);
    std::string goto_body(TargetKind body);
    std::string sync_radec(double ra_h, double dec_d, bool j2000);
    std::string set_tracking(bool on);
    void set_rate(TrackRate r);
    void set_rate_offsets(double ra_s_per_s, double dec_as_per_s);
    std::string move_axis(int axis, double dps);  // 0 az / primary, 1 alt / secondary, 2 roll; 0 = stop
    std::string pulse_guide(int dir, int ms);     // ASCOM GuideDirections: 0 N, 1 S, 2 E, 3 W
    std::string park();
    std::string unpark();
    void set_park_here();
    void abort();
    std::string roll_to(double roll_deg);         // rotator mechanical position
    std::string rotator_to_pa(double pa_deg);
    void clear_model();
    // queries
    HeadState state();
    bool is_pulse_guiding();
    bool limit_ok(double az, double alt, double roll, std::string *why = nullptr);
    double current_roll();
    Intervalometer &intervalometer() { return ivm_; }
    double now_s() { return clock_() / 1e6; }
    void set_time_unix(double s) { time_offset_s_ = s - clock_() / 1e6; }
private:
    void compute_target(double t, double roll_hint, HeadAngles &out, bool &ok);
    void current_sky(HeadState &st);
    void send_setpoint();
    void send_move(const HeadAngles &a, bool use_roll);
    void kin_update();
    void roll_limits(double alt, double &lo, double &hi);
    static int64_t to_angle(double deg) { return (int64_t)(deg / 360.0 * 4294967296.0); }
    static double from_angle(int64_t a) { return (double)a * 360.0 / 4294967296.0; }

    std::recursive_mutex mu_;
    MotionPort &port_;
    std::function<int64_t()> clock_;
    double time_offset_s_ = 0;
    Settings set_;
    Kinematics kin_;
    PointingModel model_;
    std::vector<SyncPoint> syncs_;
    Activity act_ = Activity::Idle;
    bool tracking_ = false, parked_ = false;
    TrackRate rate_ = TrackRate::Sidereal;
    double ra_rate_ = 0, dec_rate_ = 0;           // ASCOM RightAscensionRate (s/s), DeclinationRate ("/s)
    TargetKind tk_ = TargetKind::None;
    double t_ra_ = 0, t_dec_ = 0, t_epoch_s_ = 0; // target (radians), time it was set
    double fixed_az_ = 0, fixed_alt_ = 0;
    double guide_ra_as_ = 0, guide_dec_as_ = 0;   // accumulated pulse-guide offsets (arcsec)
    int64_t guide_until_us_ = 0; int guide_dir_ = -1;
    double move_rate_[ST_AXES] = {0, 0, 0};
    double roll_target_ = 0; bool roll_hold_ = true; double pa_target_ = 0; bool pa_valid_ = false;
    uint8_t moving_mask_ = 0;
    st_state_t ms_ = {};
    bool have_ms_ = false; int64_t ms_rx_us_ = 0;
    PowerDecision pd_;
    PowerInputs pin_;
    Intervalometer ivm_;
    std::vector<std::string> faults_;
    int64_t last_sp_us_ = 0;
};

}  // namespace st
