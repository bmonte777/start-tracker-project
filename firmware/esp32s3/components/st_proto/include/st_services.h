// Star Tracker — Phase 6 head services behind WebSocket API 1.1 (docs/06-apps.md section 4):
// motion jobs (job.*), PEC training (pec.*), encoder calibration and balance check (cal.*), limits, health.
// Portable C++17 on top of the Head model, so the ESP32 firmware and the simulator run the same code.
// Ticked at 10 Hz from Head::on_tick (outside the Head's lock). Lock order everywhere: Services, then Head.
#pragma once
#include <cmath>
#include <cstdint>
#include <functional>
#include <mutex>
#include <string>
#include <vector>
#include "cJSON.h"
#include "st_head.h"

namespace st {

constexpr const char *API_MINOR = "1.1";
constexpr const char *FW_VERSION = "0.2.0";      // ESP32 system firmware version reported to the apps
constexpr int PEC_BINS = 1024;                    // MOTION_PEC_N: positions over three motor turns
constexpr double PEC_PERIOD_DEG = 3.6;            // output degrees per three motor turns (300:1, D2) = one wave-generator turn
constexpr int ENC_HARM = 8, ENC_GRID = 721;       // MOTION_ENC_HARM, MOTION_ENC_GRID_N (0.5 deg grid)
constexpr int JOB_MAX_POSES = 400;

class Services {
public:
    explicit Services(Head &h);
    void tick();                                  // 10 Hz

    // jobs ----------------------------------------------------------------------------------------------
    std::string job_start(cJSON *args, cJSON *result);
    std::string job_pause();
    std::string job_resume();
    std::string job_stop();
    std::string job_ack(int job_id, int frame);
    void job_json(cJSON *o);                      // fills an object; {"state":"none"} when no job ran yet
    bool job_active();

    // PEC -----------------------------------------------------------------------------------------------
    std::string pec_record(int axis, int cycles);
    std::string pec_stop();
    std::string pec_play(bool on);
    std::string pec_save();
    std::string pec_clear(int axis);
    void pec_json(cJSON *o);
    std::string pec_curve(int axis, cJSON *o);

    // calibration ---------------------------------------------------------------------------------------
    std::string cal_encoder_start(int axis, double speed_dps);
    std::string cal_abort();
    std::string cal_encoder_apply();
    std::string cal_balance(double swing_d);
    void cal_json(cJSON *o);

    // queries -------------------------------------------------------------------------------------------
    void limits_json(cJSON *o);
    void health_json(cJSON *o);

    // platform hooks (set by the ESP32 app or the simulator)
    std::function<bool(const std::string &key, const std::vector<int16_t> &data)> store;   // flash (D78); nullptr = RAM only
    std::function<bool(const std::string &key, std::vector<int16_t> &data)> load;          // read back what store wrote
    std::function<bool(const std::string &key)> erase;                                     // pec.clear
    bool faults_persistent = false;               // true when the platform keeps the fault log in flash (D78)
    void restore_saved();                         // load saved PEC tables and encoder maps; sent on every motion link-up
    std::function<void(cJSON *)> update_status;   // fills update.status
    std::string platform = "head";                // "head" or "simulator"
    uint32_t boot_id = 0;

private:
    // jobs
    enum class JState { None, Moving, Settling, Exposing, WaitAck, Interval, Paused, Done, Stopped, Failed };
    struct Pose { double az = 0, alt = 0, roll = NAN, ra = NAN, dec = NAN; };
    struct Job {
        int id = 0; std::string type, shutter = "port"; JState st = JState::None, resume_to = JState::Moving;
        std::vector<Pose> poses;                  // poses; pathlapse: computed per frame
        std::vector<std::pair<double, Pose>> keys;   // pathlapse keys (t_s, pose)
        int frames = 0, frame = 0;                // frame = 1-based current frame
        double exposure_s = 1, interval_s = 0, settle_s = 1, focus_s = 0.3, ack_timeout_s = 30;
        double dither_as = 0; int dither_every = 1;
        double t_start = 0, t_phase = 0, t_frame0 = 0;
        std::string reason;
    } job_;
    int next_job_id_ = 1;
    void job_begin_frame(double now);
    void job_tick(double now, const HeadState &s);
    void job_fire(double now);
    static const char *jname(JState s);

    // PEC
    enum class PState { Idle, Recording, Ready, Playing };
    PState pst_ = PState::Idle;
    int pec_axis_ = 0, pec_cycles_ = 2, pec_cycle_ = 0;
    double pec_phase_prev_ = NAN, pec_travel_ = 0;
    std::vector<double> pec_sum_, pec_n_;
    std::vector<int16_t> pec_table_[ST_AXES];     // 0.01 arcsec, offsets for motion.c pec_offset
    std::vector<double> pec_raw_;                 // binned mean residual (arcsec) of the last recording
    double pec_pp_ = 0, pec_rms_ = 0, pec_resid_rms_ = 0;
    bool pec_saved_ = false, pec_playing_ = false;
    void pec_finish();
    void send_table(uint8_t table, int axis, const std::vector<int16_t> &v);

    // calibration
    enum class CState { Idle, ToStart, Sweep, Done, Applied, Failed, BalUp, BalDown, BalBack };
    std::string cal_routine_;
    CState cst_ = CState::Idle;
    int cal_axis_ = 0;
    double cal_speed_ = 0.5, cal_start_ = 0, cal_end_ = 0, cal_t0_ = 0;
    std::vector<double> cal_th_, cal_r_;
    std::vector<int16_t> enc_map_[ST_AXES];
    std::vector<int16_t> pending_map_;            // result of the last run, until cal.encoder.apply       // last applied map per axis (harm a, harm b, grid)
    cJSON *cal_result_ = nullptr;
    std::string cal_reason_;
    double bal_alt0_ = 0, bal_swing_ = 5;
    std::vector<double> bal_up_, bal_down_, bal_iu_, bal_id_;
    void cal_tick(double now, const HeadState &s);
    void cal_fit();
    void cal_restore();
    void move_axis_to(int axis, double deg, double dps);

    // saved tables are (re)sent to the RP2354A whenever its link comes up (start-up, RP2354A update or reset)
    bool link_was_ok_ = false;
    void send_saved_tables();

    // health: residual statistics while holding or tracking
    std::vector<double> hres_[ST_AXES];

    std::recursive_mutex mu_;
    Head &head_;
};

}  // namespace st
