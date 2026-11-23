// Star Tracker — Phase 6 head services (see st_services.h and docs/06-apps.md section 4).
#include "st_services.h"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace st {

static const double PI_ = 3.14159265358979323846;
static int64_t ang(double deg) { return (int64_t)std::llround(deg / 360.0 * 4294967296.0); }
static double wrap180(double d) { d = std::fmod(d + 180.0, 360.0); if (d < 0) d += 360.0; return d - 180.0; }
static double frac(double x) { return x - std::floor(x); }
static double mean(const std::vector<double> &v) { if (v.empty()) return 0; double s = 0; for (double x : v) s += x; return s / v.size(); }
static double rms_about_mean(const std::vector<double> &v)
{
    if (v.size() < 2) return 0;
    double m = mean(v), s = 0;
    for (double x : v) s += (x - m) * (x - m);
    return std::sqrt(s / v.size());
}
static double r1(double x, double k = 10) { return std::round(x * k) / k; }

Services::Services(Head &h) : head_(h)
{
    for (int i = 0; i < ST_AXES; i++) pec_table_[i].assign(PEC_BINS, 0);
}

// ====================================================================================================== tick
void Services::tick()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    HeadState s = head_.state();
    double now = head_.now_s();
    // health: encoder minus command while the axis holds or tracks slowly (the noise and wind-up the loop sees)
    for (int i = 0; i < ST_AXES; i++) {
        if (std::fabs(s.ax[i].rate_dps) < 0.02 && cst_ == CState::Idle) {
            hres_[i].push_back(wrap180(s.ax[i].enc_deg - s.ax[i].cmd_deg) * 3600.0);
            if (hres_[i].size() > 300) hres_[i].erase(hres_[i].begin());
        }
    }
    if (job_.st != JState::None) job_tick(now, s);
    if (pst_ == PState::Recording) {
        if (!s.tracking) { pst_ = PState::Idle; head_.add_fault("PEC recording stopped: tracking was turned off"); }
        else {
            const AxisView &a = s.ax[pec_axis_];
            double ph = frac(a.cmd_deg / PEC_PERIOD_DEG);
            if (!std::isnan(pec_phase_prev_)) {
                double d = ph - pec_phase_prev_;
                if (d > 0.5) d -= 1; else if (d < -0.5) d += 1;
                pec_travel_ += std::fabs(d);
            }
            pec_phase_prev_ = ph;
            int b = std::min(PEC_BINS - 1, (int)(ph * PEC_BINS));
            pec_sum_[b] += wrap180(a.enc_deg - a.cmd_deg) * 3600.0;
            pec_n_[b] += 1;
            pec_cycle_ = (int)pec_travel_;
            if (pec_travel_ >= pec_cycles_) pec_finish();
        }
    }
    if (cst_ != CState::Idle && cst_ != CState::Done && cst_ != CState::Applied && cst_ != CState::Failed) cal_tick(now, s);
}

// ====================================================================================================== jobs
const char *Services::jname(JState s)
{
    switch (s) {
    case JState::None: return "none"; case JState::Moving: return "moving"; case JState::Settling: return "settling";
    case JState::Exposing: return "exposing"; case JState::WaitAck: return "waiting_ack"; case JState::Interval: return "interval";
    case JState::Paused: return "paused"; case JState::Done: return "done"; case JState::Stopped: return "stopped";
    default: return "failed";
    }
}

bool Services::job_active()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    return job_.st != JState::None && job_.st != JState::Done && job_.st != JState::Stopped && job_.st != JState::Failed;
}

static bool pose_from(cJSON *p, double &az, double &alt, double &roll, double &ra, double &dec)
{
    auto g = [&](const char *k) { cJSON *v = cJSON_GetObjectItemCaseSensitive(p, k); return cJSON_IsNumber(v) ? v->valuedouble : NAN; };
    az = g("az_d"); alt = g("alt_d"); roll = g("roll_d"); ra = g("ra_h"); dec = g("dec_d");
    return (!std::isnan(az) && !std::isnan(alt)) || (!std::isnan(ra) && !std::isnan(dec));
}

std::string Services::job_start(cJSON *args, cJSON *result)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (job_active()) return "invalid state: a job is already running (job.stop first)";
    if (cst_ != CState::Idle && cst_ != CState::Done && cst_ != CState::Applied && cst_ != CState::Failed) return "invalid state: calibration running";
    if (!cJSON_IsObject(args)) return "invalid arguments";
    auto num = [&](const char *k, double d) { cJSON *v = cJSON_GetObjectItemCaseSensitive(args, k); return cJSON_IsNumber(v) ? v->valuedouble : d; };
    auto txt = [&](const char *k, const char *d) { cJSON *v = cJSON_GetObjectItemCaseSensitive(args, k); return std::string(cJSON_IsString(v) ? v->valuestring : d); };
    Job j;
    j.type = txt("type", "");
    j.shutter = txt("shutter", "port");
    j.exposure_s = num("exposure_s", 1);
    j.interval_s = num("interval_s", 0);
    j.settle_s = num("settle_s", 1);
    j.focus_s = num("focus_s", 0.3);
    j.ack_timeout_s = num("ack_timeout_s", 30);
    j.dither_as = num("dither_as", 0);
    j.dither_every = (int)num("dither_every", 1);
    if (j.shutter != "port" && j.shutter != "app" && j.shutter != "none") return "invalid shutter (port, app or none)";
    if (j.exposure_s <= 0 || j.exposure_s > 3600) return "invalid exposure_s (0-3600)";
    if (j.settle_s < 0 || j.settle_s > 60 || j.interval_s < 0 || j.ack_timeout_s < 2 || j.ack_timeout_s > 3600) return "invalid timing";
    if (j.dither_every < 1) j.dither_every = 1;
    if (j.type == "poses") {
        cJSON *ps = cJSON_GetObjectItemCaseSensitive(args, "poses");
        if (!cJSON_IsArray(ps) || cJSON_GetArraySize(ps) < 1) return "invalid arguments: poses [] required";
        if (cJSON_GetArraySize(ps) > JOB_MAX_POSES) return "invalid arguments: at most 400 poses";
        cJSON *p;
        cJSON_ArrayForEach(p, ps) {
            Pose q;
            if (!pose_from(p, q.az, q.alt, q.roll, q.ra, q.dec)) return "invalid pose: az_d+alt_d or ra_h+dec_d";
            if (std::isnan(q.ra)) {
                double lo, hi;
                head_.roll_limits_at(q.alt, lo, hi);
                std::string why;
                double roll = std::isnan(q.roll) ? std::fmin(hi, std::fmax(lo, head_.current_roll())) : q.roll;
                if (!head_.limit_ok(q.az, q.alt, roll, &why)) return why + " (pose " + std::to_string(j.poses.size() + 1) + ")";
            }
            j.poses.push_back(q);
        }
        j.frames = (int)j.poses.size();
    } else if (j.type == "pathlapse") {
        cJSON *ks = cJSON_GetObjectItemCaseSensitive(args, "keys");
        if (!cJSON_IsArray(ks) || cJSON_GetArraySize(ks) < 1) return "invalid arguments: keys [] required";
        cJSON *k;
        double last_t = -1;
        cJSON_ArrayForEach(k, ks) {
            Pose q;
            cJSON *t = cJSON_GetObjectItemCaseSensitive(k, "t_s");
            if (!cJSON_IsNumber(t) || t->valuedouble <= last_t) return "invalid keys: t_s must increase";
            if (!pose_from(k, q.az, q.alt, q.roll, q.ra, q.dec) || std::isnan(q.az)) return "invalid key: az_d and alt_d";
            std::string why;
            if (!head_.limit_ok(q.az, q.alt, std::isnan(q.roll) ? head_.current_roll() : q.roll, &why)) return why;
            last_t = t->valuedouble;
            j.keys.push_back({last_t, q});
        }
        j.frames = (int)num("frames", 0);
        if (j.frames < 1 || j.frames > 100000) return "invalid frames";
        if (j.interval_s < j.exposure_s + j.settle_s) j.interval_s = j.exposure_s + j.settle_s + 1.0;
    } else if (j.type == "astro") {
        if (!head_.state().tracking) return "invalid state: not tracking (go to a target first)";
        j.frames = (int)num("frames", 0);
        if (j.frames < 1 || j.frames > 100000) return "invalid frames";
        if (j.dither_as < 0 || j.dither_as > 600) return "invalid dither_as (0-600)";
    } else {
        return "invalid type (poses, pathlapse or astro)";
    }
    j.id = next_job_id_++;
    j.frame = 1;
    j.t_start = head_.now_s();
    job_ = j;
    job_begin_frame(j.t_start);
    if (result) { cJSON_AddNumberToObject(result, "job_id", j.id); cJSON_AddNumberToObject(result, "frames", j.frames); }
    return job_.st == JState::Failed ? job_.reason : "";
}

void Services::job_begin_frame(double now)
{
    job_.t_frame0 = now;
    job_.t_phase = now;
    Pose q;
    bool move = false;
    if (job_.type == "poses") { q = job_.poses[job_.frame - 1]; move = true; }
    else if (job_.type == "pathlapse") {
        double t = (job_.frame - 1) * job_.interval_s;
        const auto &K = job_.keys;
        if (K.size() == 1 || t <= K.front().first) q = K.front().second;
        else if (t >= K.back().first) q = K.back().second;
        else for (size_t i = 1; i < K.size(); i++) if (t <= K[i].first) {
            double f = (t - K[i - 1].first) / (K[i].first - K[i - 1].first);
            const Pose &a = K[i - 1].second, &b = K[i].second;
            q.az = a.az + wrap180(b.az - a.az) * f;
            q.alt = a.alt + (b.alt - a.alt) * f;
            if (!std::isnan(a.roll) && !std::isnan(b.roll)) q.roll = a.roll + (b.roll - a.roll) * f;
            break;
        }
        move = true;
    } else if (job_.type == "astro") {
        bool dither = job_.dither_as > 0 && job_.frame > 1 && (job_.frame - 1) % job_.dither_every == 0;
        if (dither) {
            // pulse-guide a random direction: duration = offset / (guide rate x 15.04"/s)
            double rate_as = head_.settings().guide_rate * 15.0410671;
            int ms = (int)std::fmin(10000, job_.dither_as / std::fmax(1, rate_as) * 1000.0);
            int dir = (job_.frame * 7 + job_.id) % 4;
            head_.pulse_guide(dir, ms);
            job_.st = JState::Moving;
        } else {
            job_.st = JState::Settling;
            job_.t_phase = now - job_.settle_s;      // nothing moved: no settling
        }
        return;
    }
    if (move) {
        std::string e = std::isnan(q.ra) ? head_.goto_altaz(q.az, q.alt) : head_.goto_radec(q.ra, q.dec, true);
        if (!e.empty()) { job_.st = JState::Failed; job_.reason = "frame " + std::to_string(job_.frame) + ": " + e; return; }
        if (!std::isnan(q.roll)) head_.roll_to(q.roll);
        job_.st = JState::Moving;
    }
}

void Services::job_fire(double now)
{
    job_.t_phase = now;
    if (job_.shutter == "port") {
        Intervalometer &iv = head_.intervalometer();
        iv.count = 1; iv.exposure_s = job_.exposure_s; iv.focus_s = job_.focus_s; iv.delay_s = 0;
        iv.interval_s = job_.focus_s + job_.exposure_s + 0.2;
        iv.start(now);
        job_.st = JState::Exposing;
    } else if (job_.shutter == "app") {
        job_.st = JState::WaitAck;
    } else {
        job_.st = JState::Interval;
    }
}

void Services::job_tick(double now, const HeadState &s)
{
    switch (job_.st) {
    case JState::Moving:
        if (now - job_.t_phase > 0.3 && s.activity != Activity::Slewing && s.activity != Activity::Moving && !head_.is_pulse_guiding()) {
            job_.st = JState::Settling;
            job_.t_phase = now;
        }
        if (s.activity == Activity::Fault) { job_.st = JState::Failed; job_.reason = "head fault during the move"; }
        break;
    case JState::Settling:
        if (now - job_.t_phase >= job_.settle_s) job_fire(now);
        break;
    case JState::Exposing:
        if (!head_.intervalometer().running) { job_.st = JState::Interval; job_.t_phase = now; }
        break;
    case JState::WaitAck:
        if (now - job_.t_phase > job_.ack_timeout_s) {
            job_.st = JState::Paused;
            job_.resume_to = JState::Settling;
            job_.reason = "no reply from the app within " + std::to_string((int)job_.ack_timeout_s) + " s: paused, tracking kept";
            head_.add_fault("job paused: " + job_.reason);
        }
        break;
    case JState::Interval:
        if (now - job_.t_frame0 >= job_.interval_s) {
            if (job_.frame >= job_.frames) { job_.st = JState::Done; job_.reason = ""; break; }
            job_.frame++;
            job_begin_frame(now);
        }
        break;
    default:
        break;
    }
    if (s.at_park && job_active()) { job_.st = JState::Stopped; job_.reason = "head parked"; head_.intervalometer().stop(); }
}

std::string Services::job_pause()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (!job_active()) return "invalid state: no job running";
    if (job_.st == JState::Paused) return "";
    head_.intervalometer().stop();
    job_.resume_to = JState::Settling;            // the interrupted frame is shot again
    job_.st = JState::Paused;
    job_.reason = "paused by the app";
    return "";
}

std::string Services::job_resume()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (job_.st != JState::Paused) return "invalid state: job is not paused";
    job_.reason = "";
    job_.t_frame0 = head_.now_s();
    if (job_.type == "astro") { job_.st = JState::Settling; job_.t_phase = job_.t_frame0 - job_.settle_s; }
    else job_begin_frame(job_.t_frame0);
    return "";
}

std::string Services::job_stop()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (!job_active()) return "";
    head_.intervalometer().stop();
    if (job_.st == JState::Moving && job_.type != "astro") head_.abort();
    job_.st = JState::Stopped;
    job_.reason = "stopped by the app";
    return "";
}

std::string Services::job_ack(int job_id, int frame)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (job_id != job_.id) return "invalid job_id";
    if (job_.st != JState::WaitAck) return "invalid state: not waiting for the camera";
    if (frame != job_.frame) return "invalid frame: expected " + std::to_string(job_.frame);
    job_.st = JState::Interval;
    job_.t_phase = head_.now_s();
    return "";
}

void Services::job_json(cJSON *o)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    cJSON_AddStringToObject(o, "state", jname(job_.st));
    if (job_.st == JState::None) return;
    cJSON_AddNumberToObject(o, "job_id", job_.id);
    cJSON_AddStringToObject(o, "type", job_.type.c_str());
    cJSON_AddStringToObject(o, "shutter", job_.shutter.c_str());
    cJSON_AddNumberToObject(o, "frame", job_.frame);
    cJSON_AddNumberToObject(o, "frames", job_.frames);
    double el = head_.now_s() - job_.t_start;
    cJSON_AddNumberToObject(o, "elapsed_s", r1(el));
    double per = job_.frame > 1 ? (head_.now_s() - job_.t_start) / (job_.frame - 1) : std::fmax(job_.interval_s, job_.exposure_s + job_.settle_s);
    cJSON_AddNumberToObject(o, "eta_s", job_active() ? r1(per * (job_.frames - job_.frame + 1)) : 0);
    if (!job_.reason.empty()) cJSON_AddStringToObject(o, "reason", job_.reason.c_str());
}

// ====================================================================================================== PEC
std::string Services::pec_record(int axis, int cycles)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (axis < 0 || axis > 2) return "invalid axis";
    if (cycles < 1 || cycles > 10) return "invalid cycles (1-10)";
    if (!head_.state().tracking) return "invalid state: not tracking (PEC is learned while tracking a star)";
    if (pst_ == PState::Recording) return "invalid state: already recording";
    pec_axis_ = axis; pec_cycles_ = cycles; pec_cycle_ = 0; pec_travel_ = 0; pec_phase_prev_ = NAN;
    pec_sum_.assign(PEC_BINS, 0); pec_n_.assign(PEC_BINS, 0);
    pst_ = PState::Recording;
    return "";
}

std::string Services::pec_stop()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (pst_ != PState::Recording) return "";
    if (pec_travel_ >= 0.5) pec_finish();      // keep what was recorded if half a period or more
    else pst_ = PState::Idle;
    return "";
}

void Services::pec_finish()
{
    // binned mean residual over one period, holes filled from neighbours
    pec_raw_.assign(PEC_BINS, NAN);
    for (int i = 0; i < PEC_BINS; i++) if (pec_n_[i] > 0) pec_raw_[i] = pec_sum_[i] / pec_n_[i];
    for (int pass = 0; pass < PEC_BINS; pass++) {
        bool any = false;
        for (int i = 0; i < PEC_BINS; i++) if (std::isnan(pec_raw_[i])) {
            double a = pec_raw_[(i + PEC_BINS - 1) % PEC_BINS], b = pec_raw_[(i + 1) % PEC_BINS];
            if (!std::isnan(a) || !std::isnan(b)) pec_raw_[i] = std::isnan(a) ? b : std::isnan(b) ? a : (a + b) / 2;
            else any = true;
        }
        if (!any) break;
    }
    for (double &x : pec_raw_) if (std::isnan(x)) x = 0;
    double m = mean(pec_raw_);
    // smooth with harmonics 1-12 of the period (wave generator x1, x2; motor x3, x6, ...): the encoder noise drops out
    std::vector<double> sm(PEC_BINS, 0.0);
    for (int k = 1; k <= 12; k++) {
        double a = 0, b = 0;
        for (int i = 0; i < PEC_BINS; i++) { double th = 2 * PI_ * k * i / PEC_BINS; a += (pec_raw_[i] - m) * std::cos(th); b += (pec_raw_[i] - m) * std::sin(th); }
        a *= 2.0 / PEC_BINS; b *= 2.0 / PEC_BINS;
        for (int i = 0; i < PEC_BINS; i++) { double th = 2 * PI_ * k * i / PEC_BINS; sm[i] += a * std::cos(th) + b * std::sin(th); }
    }
    double mx = -1e9, mn = 1e9, ss = 0, rr = 0;
    for (int i = 0; i < PEC_BINS; i++) {
        mx = std::fmax(mx, sm[i]); mn = std::fmin(mn, sm[i]); ss += sm[i] * sm[i];
        double d = pec_raw_[i] - m - sm[i]; rr += d * d;
    }
    pec_pp_ = mx - mn; pec_rms_ = std::sqrt(ss / PEC_BINS); pec_resid_rms_ = std::sqrt(rr / PEC_BINS);
    std::vector<int16_t> &t = pec_table_[pec_axis_];
    t.assign(PEC_BINS, 0);
    for (int i = 0; i < PEC_BINS; i++) t[i] = (int16_t)std::max(-32767.0, std::min(32767.0, std::round(-sm[i] * 100.0)));   // 0.01", cancels the error
    pec_saved_ = false;
    pst_ = PState::Ready;
}

void Services::send_table(uint8_t table, int axis, const std::vector<int16_t> &v)
{
    for (size_t off = 0; off < v.size(); off += 100) {
        st_table_t tb;
        memset(&tb, 0, sizeof tb);
        tb.table = table; tb.axis = (uint8_t)axis; tb.total = (uint16_t)v.size(); tb.offset = (uint16_t)off;
        tb.count = (uint8_t)std::min<size_t>(100, v.size() - off);
        tb.last = off + tb.count >= v.size();
        for (int k = 0; k < tb.count; k++) tb.v[k] = v[off + k];
        head_.send_motion(ST_MSG_TABLE, &tb, sizeof tb);
    }
}

std::string Services::pec_play(bool on)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (pst_ == PState::Recording) return "invalid state: recording";
    if (on) {
        bool any = std::any_of(pec_table_[pec_axis_].begin(), pec_table_[pec_axis_].end(), [](int16_t x) { return x != 0; });
        if (!any) return "invalid state: no PEC table recorded";
        send_table(1, pec_axis_, pec_table_[pec_axis_]);
        pec_playing_ = true; pst_ = PState::Playing;
    } else {
        send_table(1, pec_axis_, std::vector<int16_t>(PEC_BINS, 0));
        pec_playing_ = false; pst_ = PState::Ready;
    }
    return "";
}

std::string Services::pec_save()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (!store) { pec_saved_ = false; return "not implemented yet: no storage on this platform (kept until restart)"; }
    pec_saved_ = store("pec" + std::to_string(pec_axis_), pec_table_[pec_axis_]);
    return pec_saved_ ? "" : "error: could not write the table";
}

std::string Services::pec_clear(int axis)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (axis < 0 || axis > 2) return "invalid axis";
    pec_table_[axis].assign(PEC_BINS, 0);
    send_table(1, axis, pec_table_[axis]);
    if (axis == pec_axis_) { pst_ = PState::Idle; pec_playing_ = false; pec_raw_.clear(); pec_pp_ = pec_rms_ = 0; }
    return "";
}

void Services::pec_json(cJSON *o)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    static const char *n[] = {"idle", "recording", "ready", "playing"};
    cJSON_AddStringToObject(o, "state", n[(int)pst_]);
    cJSON_AddNumberToObject(o, "axis", pec_axis_);
    cJSON_AddNumberToObject(o, "cycle", pec_cycle_);
    cJSON_AddNumberToObject(o, "cycles", pec_cycles_);
    cJSON_AddNumberToObject(o, "progress", pst_ == PState::Recording ? r1(std::fmin(1.0, pec_travel_ / pec_cycles_), 1000) : (pst_ == PState::Idle ? 0 : 1));
    cJSON_AddNumberToObject(o, "period_s", r1(PEC_PERIOD_DEG / (15.0410671 / 3600.0), 1));
    cJSON_AddNumberToObject(o, "pp_as", r1(pec_pp_, 100));
    cJSON_AddNumberToObject(o, "rms_as", r1(pec_rms_, 100));
    cJSON_AddNumberToObject(o, "noise_as", r1(pec_resid_rms_, 100));
    cJSON_AddBoolToObject(o, "playing", pec_playing_);
    cJSON_AddBoolToObject(o, "saved", pec_saved_);
}

std::string Services::pec_curve(int axis, cJSON *o)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (axis < 0 || axis > 2) return "invalid axis";
    cJSON_AddNumberToObject(o, "axis", axis);
    cJSON_AddNumberToObject(o, "n", 128);
    cJSON *c = cJSON_AddArrayToObject(o, "table_as"), *r = cJSON_AddArrayToObject(o, "raw_as");
    double m = pec_raw_.empty() || axis != pec_axis_ ? 0 : mean(pec_raw_);
    for (int i = 0; i < 128; i++) {
        cJSON_AddItemToArray(c, cJSON_CreateNumber(r1(pec_table_[axis][i * 8] / 100.0, 100)));
        if (!pec_raw_.empty() && axis == pec_axis_) {
            double s = 0; for (int k = 0; k < 8; k++) s += pec_raw_[i * 8 + k];
            cJSON_AddItemToArray(r, cJSON_CreateNumber(r1(s / 8 - m, 100)));
        }
    }
    return "";
}

// ====================================================================================================== calibration
void Services::move_axis_to(int axis, double deg, double dps)
{
    st_power_t p = {2, 0, head_.state().power.motion_budget_mw};
    head_.send_motion(ST_MSG_POWER, &p, sizeof p);
    st_move_t m;
    memset(&m, 0, sizeof m);
    m.axis_mask = (uint8_t)(1 << axis);
    m.flags = dps > 2 ? 1 : 0;
    m.vmax_mdeg_s = (uint16_t)std::max(10.0, dps * 1000.0);
    m.amax_mdeg_s2 = 2000;
    m.jerk_deg_s3 = 8;
    HeadState s = head_.state();
    for (int i = 0; i < ST_AXES; i++) m.target[i] = ang(s.ax[i].cmd_deg);
    m.target[axis] = ang(deg);
    head_.send_motion(ST_MSG_MOVE, &m, sizeof m);
}

std::string Services::cal_encoder_start(int axis, double speed_dps)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (axis < 0 || axis > 2) return "invalid axis";
    if (speed_dps < 0.05 || speed_dps > 2) return "invalid speed_dps (0.05-2)";
    HeadState s = head_.state();
    if (s.tracking || s.activity != Activity::Idle) return "invalid state: stop tracking and moves first";
    if (s.at_park) return "parked";
    if (job_active()) return "invalid state: a job is running";
    cal_routine_ = "encoder"; cal_axis_ = axis; cal_speed_ = speed_dps; cal_reason_.clear();
    double now = s.ax[axis].cmd_deg;
    if (axis == 0) { cal_start_ = now; cal_end_ = now + 360.0; }
    else if (axis == 1) { cal_start_ = ALT_MIN + LIMIT_MARGIN_DEG; cal_end_ = 90.0; }
    else { double lo, hi; head_.roll_limits_at(s.ax[1].cmd_deg, lo, hi); cal_start_ = lo; cal_end_ = hi; }
    if (axis == 1) {   // payload altitude cap (P4/P5 without a pier extension)
        std::string why;
        while (cal_end_ > cal_start_ + 10 && !head_.limit_ok(s.ax[0].cmd_deg, cal_end_, s.ax[2].cmd_deg, &why)) cal_end_ -= 1.0;
    }
    cal_th_.clear(); cal_r_.clear();
    if (cal_result_) { cJSON_Delete(cal_result_); cal_result_ = nullptr; }
    // raw encoder for the run: no map, no lost-motion correction, slip check relaxed to 2 deg
    head_.motion_cfg(ST_CFG_SLIP_LIMIT, axis, ang(2.0));
    head_.motion_cfg(ST_CFG_CORR_DEADBAND, axis, ang(1.0));
    send_table(2, axis, std::vector<int16_t>(2 * ENC_HARM + ENC_GRID, 0));
    move_axis_to(axis, cal_start_, 4.0);
    cst_ = CState::ToStart;
    cal_t0_ = head_.now_s();
    return "";
}

void Services::cal_restore()
{
    head_.motion_cfg(ST_CFG_SLIP_LIMIT, cal_axis_, ang(0.05));
    head_.motion_cfg(ST_CFG_CORR_DEADBAND, cal_axis_, ang(2.0 / 3600.0));
}

void Services::cal_tick(double now, const HeadState &s)
{
    const AxisView &a = s.ax[cal_routine_ == "balance" ? 1 : cal_axis_];
    auto arrived = [&](double target) { return std::fabs(a.cmd_deg - target) < 0.005 && std::fabs(a.rate_dps) < 1e-4; };
    if (now - cal_t0_ > 4 * 3600) { cst_ = CState::Failed; cal_reason_ = "took too long"; cal_restore(); return; }
    switch (cst_) {
    case CState::ToStart:
        if (arrived(cal_start_)) { move_axis_to(cal_axis_, cal_end_, cal_speed_); cst_ = CState::Sweep; }
        break;
    case CState::Sweep:
        if (std::fabs(a.rate_dps) > cal_speed_ * 0.5) {          // constant-speed part only
            cal_th_.push_back(a.cmd_deg);
            cal_r_.push_back(wrap180(a.enc_deg - a.cmd_deg) * 3600.0);
        }
        if (arrived(cal_end_)) cal_fit();
        break;
    case CState::BalUp:
        if (std::fabs(a.rate_dps) > 0.5) { bal_up_.push_back(a.sg); bal_iu_.push_back(a.i_ma); }
        if (arrived(bal_alt0_ + bal_swing_)) { move_axis_to(1, bal_alt0_ - bal_swing_, 2.0); cst_ = CState::BalDown; }
        break;
    case CState::BalDown:
        if (std::fabs(a.rate_dps) > 0.5) { bal_down_.push_back(a.sg); bal_id_.push_back(a.i_ma); }
        if (arrived(bal_alt0_ - bal_swing_)) { move_axis_to(1, bal_alt0_, 2.0); cst_ = CState::BalBack; }
        break;
    case CState::BalBack:
        if (arrived(bal_alt0_)) {
            double up = mean(bal_up_), dn = mean(bal_down_);
            double rel = (up + dn) > 0 ? (dn - up) / ((up + dn) / 2) : 0;   // StallGuard: lower = more load
            if (cal_result_) cJSON_Delete(cal_result_);
            cal_result_ = cJSON_CreateObject();
            cJSON_AddNumberToObject(cal_result_, "load_up", r1(up));
            cJSON_AddNumberToObject(cal_result_, "load_down", r1(dn));
            cJSON_AddNumberToObject(cal_result_, "i_up_ma", r1(mean(bal_iu_)));
            cJSON_AddNumberToObject(cal_result_, "i_down_ma", r1(mean(bal_id_)));
            cJSON_AddNumberToObject(cal_result_, "imbalance", r1(rel, 1000));
            const char *v = std::fabs(rel) < 0.08 ? "balanced" : rel > 0 ? "front-heavy: slide the payload back" : "rear-heavy: slide the payload forward";
            cJSON_AddStringToObject(cal_result_, "verdict", v);
            if (platform == "simulator") cJSON_AddStringToObject(cal_result_, "note", "the simulator has no load model, so it always reads balanced");
            cst_ = CState::Done;
        }
        break;
    default:
        break;
    }
}

void Services::cal_fit()
{
    const size_t M = cal_th_.size();
    if (M < 200) { cst_ = CState::Failed; cal_reason_ = "too few samples"; cal_restore(); return; }
    double c0 = mean(cal_r_);
    double ha[ENC_HARM] = {0}, hb[ENC_HARM] = {0};
    bool full = cal_axis_ == 0;
    if (full) {   // a full turn sampled at constant speed: Fourier sums are the least-squares fit
        for (int k = 1; k <= ENC_HARM; k++) {
            double a = 0, b = 0;
            for (size_t i = 0; i < M; i++) { double th = cal_th_[i] * PI_ / 180.0 * k; a += (cal_r_[i] - c0) * std::cos(th); b += (cal_r_[i] - c0) * std::sin(th); }
            ha[k - 1] = a * 2.0 / M; hb[k - 1] = b * 2.0 / M;
        }
    }
    auto harm = [&](double deg) { double e = 0, th = deg * PI_ / 180.0; for (int k = 0; k < ENC_HARM; k++) e += ha[k] * std::cos((k + 1) * th) + hb[k] * std::sin((k + 1) * th); return e; };
    // residual on the 0.5 deg grid: mean over +/-0.9 deg = one period of the reducer's own error (2 per wave-generator
    // turn = 1.8 deg of output), so the reducer error does not end up in the encoder map
    std::vector<double> gs(ENC_GRID, 0), gn(ENC_GRID, 0);
    for (size_t i = 0; i < M; i++) {
        double res = cal_r_[i] - harm(cal_th_[i]);
        double g = std::fmod(cal_th_[i], 360.0); if (g < 0) g += 360.0;
        int lo = (int)std::ceil((g - 0.9) * 2), hi = (int)std::floor((g + 0.9) * 2);
        for (int k = lo; k <= hi; k++) { int idx = ((k % 720) + 720) % 720; gs[idx] += res; gn[idx] += 1; }
    }
    std::vector<double> grid(ENC_GRID, NAN);
    for (int i = 0; i < 720; i++) if (gn[i] > 0) grid[i] = gs[i] / gn[i];
    // outside a partial sweep: hold the nearest edge value
    for (int pass = 0; pass < 720; pass++) {
        bool any = false;
        for (int i = 0; i < 720; i++) if (std::isnan(grid[i])) {
            double a = grid[(i + 719) % 720], b = grid[(i + 1) % 720];
            if (!std::isnan(a)) grid[i] = a; else if (!std::isnan(b)) grid[i] = b; else any = true;
        }
        if (!any) break;
    }
    for (double &x : grid) if (std::isnan(x)) x = c0;
    grid[720] = grid[0];
    std::vector<int16_t> map(2 * ENC_HARM + ENC_GRID);
    auto q = [](double v) { return (int16_t)std::max(-32767.0, std::min(32767.0, std::round(v * 10.0))); };   // 0.1"
    for (int k = 0; k < ENC_HARM; k++) { map[k] = q(ha[k]); map[ENC_HARM + k] = q(hb[k]); }
    for (int i = 0; i < ENC_GRID; i++) map[2 * ENC_HARM + i] = q(grid[i]);
    // what the map leaves: residual after harmonics + grid (the grid, sampled like motion.c, interpolated)
    std::vector<double> after(M), before(cal_r_);
    double hm = 0;
    for (size_t i = 0; i < M; i++) {
        double g = std::fmod(cal_th_[i], 360.0); if (g < 0) g += 360.0;
        double gi = g * 2; int i0 = std::min(719, (int)gi); double f = gi - i0;
        double model = harm(cal_th_[i]) + (grid[i0] * (1 - f) + grid[i0 + 1] * f);
        after[i] = cal_r_[i] - model;
        hm += harm(cal_th_[i]) * harm(cal_th_[i]);
    }
    double mx = *std::max_element(before.begin(), before.end()), mn = *std::min_element(before.begin(), before.end());
    if (cal_result_) cJSON_Delete(cal_result_);
    cal_result_ = cJSON_CreateObject();
    cJSON_AddNumberToObject(cal_result_, "axis", cal_axis_);
    cJSON_AddNumberToObject(cal_result_, "samples", (double)M);
    cJSON_AddNumberToObject(cal_result_, "travel_d", r1(cal_end_ - cal_start_));
    cJSON_AddNumberToObject(cal_result_, "raw_pp_as", r1(mx - mn));
    cJSON_AddNumberToObject(cal_result_, "raw_rms_as", r1(rms_about_mean(before)));
    cJSON_AddNumberToObject(cal_result_, "harmonic_rms_as", r1(std::sqrt(hm / M)));
    cJSON_AddNumberToObject(cal_result_, "after_rms_as", r1(rms_about_mean(after)));
    cJSON_AddBoolToObject(cal_result_, "full_turn", full);
    pending_map_ = map;
    cst_ = CState::Done;
}

std::string Services::cal_encoder_apply()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (cal_routine_ != "encoder" || cst_ != CState::Done || pending_map_.empty()) return "invalid state: no finished calibration run";
    send_table(2, cal_axis_, pending_map_);
    enc_map_[cal_axis_] = pending_map_;
    cal_restore();
    bool saved = store ? store("encmap" + std::to_string(cal_axis_), pending_map_) : false;
    if (cal_result_) cJSON_AddBoolToObject(cal_result_, "saved", saved);
    pending_map_.clear();
    cst_ = CState::Applied;
    return "";
}

std::string Services::cal_abort()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (cst_ == CState::Idle) return "";
    st_stop_t st = {(uint8_t)(1 << (cal_routine_ == "balance" ? 1 : cal_axis_)), 0};
    head_.send_motion(ST_MSG_STOP, &st, sizeof st);
    if (cal_routine_ == "encoder" && cst_ != CState::Applied) {
        // back to the map that was in use before the run (none = zeros)
        send_table(2, cal_axis_, enc_map_[cal_axis_].empty() ? std::vector<int16_t>(2 * ENC_HARM + ENC_GRID, 0) : enc_map_[cal_axis_]);
        cal_restore();
    }
    pending_map_.clear();
    cst_ = CState::Idle;
    cal_reason_ = "aborted";
    return "";
}

std::string Services::cal_balance(double swing_d)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (swing_d < 1 || swing_d > 15) return "invalid swing_d (1-15)";
    HeadState s = head_.state();
    if (s.tracking || s.activity != Activity::Idle) return "invalid state: stop tracking and moves first";
    if (s.at_park) return "parked";
    if (job_active()) return "invalid state: a job is running";
    double a0 = s.ax[1].cmd_deg;
    std::string why;
    if (!head_.limit_ok(s.ax[0].cmd_deg, a0 + swing_d, s.ax[2].cmd_deg, &why) || !head_.limit_ok(s.ax[0].cmd_deg, a0 - swing_d, s.ax[2].cmd_deg, &why))
        return "limit: not enough altitude room for the swing (" + why + ")";
    cal_routine_ = "balance"; cal_axis_ = 1; bal_alt0_ = a0; bal_swing_ = swing_d; cal_reason_.clear();
    bal_up_.clear(); bal_down_.clear(); bal_iu_.clear(); bal_id_.clear();
    if (cal_result_) { cJSON_Delete(cal_result_); cal_result_ = nullptr; }
    move_axis_to(1, a0 + swing_d, 2.0);
    cst_ = CState::BalUp;
    cal_t0_ = head_.now_s();
    return "";
}

void Services::cal_json(cJSON *o)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    static const char *n[] = {"idle", "to_start", "sweeping", "done", "applied", "failed", "swing_up", "swing_down", "returning"};
    cJSON_AddStringToObject(o, "routine", cal_routine_.c_str());
    cJSON_AddStringToObject(o, "state", n[(int)cst_]);
    cJSON_AddNumberToObject(o, "axis", cal_axis_);
    double prog = 0;
    if (cst_ == CState::Sweep && !cal_th_.empty()) prog = std::fmin(1.0, std::fabs(cal_th_.back() - cal_start_) / std::fabs(cal_end_ - cal_start_));
    if (cst_ == CState::Done || cst_ == CState::Applied) prog = 1;
    cJSON_AddNumberToObject(o, "progress", r1(prog, 1000));
    if (!cal_reason_.empty()) cJSON_AddStringToObject(o, "reason", cal_reason_.c_str());
    if (cal_result_) cJSON_AddItemToObject(o, "result", cJSON_Duplicate(cal_result_, true));
}

// ====================================================================================================== queries
void Services::limits_json(cJSON *o)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    Settings st = head_.settings();
    HeadState s = head_.state();
    const PayloadEnvelope &p = PAYLOADS[st.payload - 1];
    double cap = p.alt_cap[st.wedge_fitted ? 0 : 1];
    double amax = ALT_MAX;
    if (!st.pier_extension && !std::isnan(cap)) amax = std::fmin(amax, cap - LIMIT_MARGIN_DEG);
    double lo, hi;
    head_.roll_limits_at(s.ax[1].cmd_deg, lo, hi);
    cJSON_AddNumberToObject(o, "payload", st.payload);
    cJSON_AddStringToObject(o, "payload_name", p.name);
    cJSON_AddNumberToObject(o, "margin_d", LIMIT_MARGIN_DEG);
    cJSON_AddNumberToObject(o, "alt_min_d", ALT_MIN);
    cJSON_AddNumberToObject(o, "alt_max_d", amax);
    if (std::isnan(cap)) cJSON_AddNullToObject(o, "alt_cap_d"); else cJSON_AddNumberToObject(o, "alt_cap_d", cap);
    cJSON_AddNumberToObject(o, "roll_min_d", p.roll_away + LIMIT_MARGIN_DEG);
    cJSON_AddNumberToObject(o, "roll_max_d", p.roll_toward_tower - LIMIT_MARGIN_DEG);
    cJSON_AddNumberToObject(o, "roll_lo_now_d", r1(lo, 100));
    cJSON_AddNumberToObject(o, "roll_hi_now_d", r1(hi, 100));
    cJSON *tr = cJSON_AddObjectToObject(o, "tripod_roll_d");     // where the payload meets the tripod top, wedge on/off
    int w = st.wedge_fitted ? 0 : 1;
    if (std::isnan(p.tripod_roll_alt0[w])) cJSON_AddNullToObject(tr, "alt0"); else cJSON_AddNumberToObject(tr, "alt0", p.tripod_roll_alt0[w]);
    if (std::isnan(p.tripod_roll_alt45[w])) cJSON_AddNullToObject(tr, "alt45"); else cJSON_AddNumberToObject(tr, "alt45", p.tripod_roll_alt45[w]);
    cJSON_AddBoolToObject(o, "wedge_fitted", st.wedge_fitted);
    cJSON_AddBoolToObject(o, "pier_extension", st.pier_extension);
    cJSON_AddNumberToObject(o, "slew_dps_max", 8.0);
    cJSON_AddNumberToObject(o, "az_unlimited", 1);
}

void Services::health_json(cJSON *o)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    HeadState s = head_.state();
    static const char *names[] = {"az", "alt", "roll"};
    cJSON *ax = cJSON_AddArrayToObject(o, "axes");
    for (int i = 0; i < ST_AXES; i++) {
        cJSON *a = cJSON_CreateObject();
        cJSON_AddStringToObject(a, "axis", names[i]);
        cJSON_AddBoolToObject(a, "calibrated", (s.ax[i].flags & ST_AXF_CALIBRATED) != 0);
        cJSON_AddBoolToObject(a, "encoder_ok", (s.ax[i].flags & ST_AXF_ENC_BAD) == 0);
        cJSON_AddNumberToObject(a, "enc_minus_cmd_rms_as", r1(rms_about_mean(hres_[i]), 100));
        cJSON_AddNumberToObject(a, "enc_minus_cmd_mean_as", r1(mean(hres_[i]), 100));
        cJSON_AddNumberToObject(a, "samples", (double)hres_[i].size());
        cJSON_AddNumberToObject(a, "temp_c", s.ax[i].temp_c);
        cJSON_AddNumberToObject(a, "i_ma", s.ax[i].i_ma);
        cJSON_AddNumberToObject(a, "load", s.ax[i].sg);
        cJSON_AddNumberToObject(a, "flags", s.ax[i].flags);
        cJSON_AddItemToArray(ax, a);
    }
    cJSON *b = cJSON_AddObjectToObject(o, "battery");
    cJSON_AddNumberToObject(b, "soc", s.soc);
    cJSON_AddNumberToObject(b, "v", r1(s.pack_v, 1000));
    cJSON_AddNumberToObject(b, "a", r1(s.pack_a, 1000));
    cJSON_AddNumberToObject(b, "temp_c", s.pack_temp_c);
    cJSON_AddBoolToObject(b, "ext", s.ext_power);
    cJSON_AddNumberToObject(b, "motion_budget_w", s.power.motion_budget_mw / 1000.0);
    // the gauge's cycle count, state of health and cell voltages are read by the power task but not passed to the Head yet
    cJSON_AddNullToObject(b, "cycles");
    cJSON_AddNullToObject(b, "soh_pct");
    cJSON_AddNullToObject(b, "cells_v");
    cJSON *m = cJSON_AddObjectToObject(o, "motor");
    cJSON_AddNumberToObject(m, "vmot", s.vmot);
    cJSON_AddNumberToObject(m, "rail", s.rail);
    cJSON_AddNumberToObject(m, "faults", s.motion_faults);
    cJSON_AddBoolToObject(o, "link_ok", s.link_ok);
    cJSON_AddNumberToObject(o, "faults_total", head_.fault_seq());
    cJSON_AddStringToObject(o, "platform", platform.c_str());
}

}  // namespace st
