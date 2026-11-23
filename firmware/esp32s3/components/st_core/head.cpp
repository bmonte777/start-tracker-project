// Star Tracker — Head model implementation. See st_head.h and docs/05-firmware.md sections 3.6-3.8.
#include "st_head.h"
#include <cstring>

namespace st {

// docs/03-mechanical-design.md, "Payload envelopes" tables (roll: + toward the tower, - away). NAN = never / none.
const PayloadEnvelope PAYLOADS[5] = {
    {"P1 mirrorless + standard zoom", 9, -175, {-135, -110}, {NAN, NAN}, {NAN, NAN}},
    {"P2 70-200 f/2.8 on its collar", 9, -130, {-125, -110}, {-130, -105}, {NAN, NAN}},
    {"P3 150-600 class on its foot", 8, -150, {-120, -105}, {-100, -80}, {NAN, NAN}},
    {"P4 72 mm refractor + astro camera", 15, -150, {-145, -125}, {-85, -65}, {NAN, 68}},
    {"P5 90 mm refractor, 7 kg", 8, -155, {-130, -115}, {-35, 0}, {50, 41}},
};

static const double RATE_ASPS[4] = {15.0410671, 14.685, 15.0, 15.0369};   // ASCOM DriveRates, arcsec/s

PowerDecision power_policy(const PowerInputs &in, double motion_demand_w)
{
    PowerDecision d;
    const double logic_w = 1.2;                                  // Phase 4 calc: system load
    double avail = in.pack_ok ? 6.0 * in.pack_v : 36.0;          // pack blade limit 6 A (section 10.7)
    if (in.charging) avail = std::fmax(avail, 36.0);
    double budget = avail - logic_w - in.portb_w - in.porta_source_w;
    const double slew_peak_w = 20.1;                             // phase4_results.json d33.peak_slew_power_w
    // rule: lower the slew current first (the RP2354A scales it by sqrt(budget / 20.1 W), down to 0.77 x, which keeps the
    // -20 C torque margin of 1.48 above 1.1), then re-advertise port B at 15 W
    if (motion_demand_w > budget && budget < 0.6 * slew_peak_w && in.portb_w > 15.0) {
        d.portb_15w = true;
        budget = avail - logic_w - 15.0 - in.porta_source_w;
    }
    budget = std::fmax(3.0, std::fmin(36.0, budget));
    d.motion_budget_mw = (uint16_t)(budget * 1000.0);
    d.low_battery = in.pack_ok && !in.charging && (in.soc <= 5 || in.pack_v < 6.2);   // D25, spec 7.3
    d.charge_ma = in.inside_temp_c > 35.0 ? 3000 : 4000;         // Phase 4 thermal check
    d.allow_porta_source = !in.pack_ok || in.soc > 20;
    return d;
}

void Intervalometer::tick(double now)
{
    if (!running) { focus = release = false; return; }
    double t = now - t_start - delay_s;
    if (t < 0) { focus = release = false; return; }
    double iv = std::fmax(interval_s, focus_s + exposure_s + 0.2);
    int k = (int)(t / iv);
    if (count > 0 && k >= count) { stop(); done = count; return; }
    done = k;
    double in = t - k * iv;
    focus = in < focus_s + exposure_s;
    release = in >= focus_s && in < focus_s + exposure_s;
}

Head::Head(MotionPort &port, std::function<int64_t()> clock_us) : port_(port), clock_(clock_us) { kin_update(); }

void Head::kin_update()
{
    if (set_.mode == MountMode::Equatorial)
        kin_.set_equatorial(set_.site.lat, set_.wedge_deg, set_.site.lat >= 0 ? set_.az0_deg : 180.0 + set_.az0_deg);
    else
        kin_.set_altaz(set_.az0_deg, set_.tilt_x_deg, set_.tilt_y_deg);
}

void Head::apply_settings(const Settings &s)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    set_ = s;
    if (set_.payload < 1 || set_.payload > 5) set_.payload = 3;
    if (set_.slew_dps > 8.0) set_.slew_dps = 8.0;               // D42
    kin_update();
    push_motion_config();
}

void Head::roll_limits(double alt, double &lo, double &hi)
{
    const PayloadEnvelope &p = PAYLOADS[set_.payload - 1];
    hi = p.roll_toward_tower - LIMIT_MARGIN_DEG;
    lo = p.roll_away + LIMIT_MARGIN_DEG;
    if (!set_.pier_extension) {
        int w = set_.wedge_fitted ? 0 : 1;
        double r0 = p.tripod_roll_alt0[w], r45 = p.tripod_roll_alt45[w];
        if (std::isnan(r45)) r45 = -180.0;
        if (std::isnan(r0)) r0 = -180.0;
        double f = std::fmin(1.0, std::fmax(0.0, alt / 45.0));
        double tr = r0 + (r45 - r0) * f + LIMIT_MARGIN_DEG;
        if (tr > lo) lo = tr;
    }
    if (lo > hi) lo = hi;
}

bool Head::limit_ok(double az, double alt, double roll, std::string *why)
{
    (void)az;
    double amax = ALT_MAX;
    const PayloadEnvelope &p = PAYLOADS[set_.payload - 1];
    double cap = p.alt_cap[set_.wedge_fitted ? 0 : 1];
    if (!set_.pier_extension && !std::isnan(cap)) amax = std::fmin(amax, cap - LIMIT_MARGIN_DEG);
    if (alt < ALT_MIN || alt > amax) {
        if (why) *why = "altitude limit " + std::to_string((int)(alt < ALT_MIN ? ALT_MIN : amax));
        return false;
    }
    double lo, hi;
    roll_limits(alt, lo, hi);
    if (roll < lo - 1e-6 || roll > hi + 1e-6) {
        if (why) *why = "roll limit for " + std::string(p.name);
        return false;
    }
    return true;
}

void Head::push_motion_config()
{
    auto cfg = [&](uint16_t key, uint8_t axis, int64_t v) { st_cfg_t c = {key, axis, 0, v}; port_.send(ST_MSG_CFG_SET, &c, sizeof c); };
    bool cold = pin_.inside_temp_c < 0.0;
    for (int i = 0; i < ST_AXES; i++) {
        cfg(ST_CFG_DIR_INVERT, (uint8_t)i, set_.dir_invert[i]);
        cfg(ST_CFG_ENC_INVERT, (uint8_t)i, set_.enc_invert[i]);
        // interpolate the slew and tracking currents between the 20 C and -20 C values (Phase 4 currents table)
        double f = std::fmin(1.0, std::fmax(0.0, (20.0 - pin_.inside_temp_c) / 40.0));
        cfg(ST_CFG_I_RUN_MA, (uint8_t)i, (int64_t)(set_.i_run_ma[i] + f * (set_.i_run_cold_ma[i] - set_.i_run_ma[i])));
        cfg(ST_CFG_I_TRACK_MA, (uint8_t)i, (int64_t)(set_.i_track_ma[i] + f * (set_.i_track_cold_ma[i] - set_.i_track_ma[i])));
        cfg(ST_CFG_VMAX_MDEG_S, (uint8_t)i, (int64_t)(set_.slew_dps * 1000));
    }
    (void)cold;
    // static envelope for the RP2354A: altitude range and the payload's whole roll range (the tripod limit, which depends on
    // the altitude, is enforced here in planning)
    double amax = ALT_MAX;
    const PayloadEnvelope &p = PAYLOADS[set_.payload - 1];
    double cap = p.alt_cap[set_.wedge_fitted ? 0 : 1];
    if (!set_.pier_extension && !std::isnan(cap)) amax = std::fmin(amax, cap - LIMIT_MARGIN_DEG);
    cfg(ST_CFG_LIMIT_MIN, ST_ALT, to_angle(ALT_MIN));
    cfg(ST_CFG_LIMIT_MAX, ST_ALT, to_angle(amax));
    cfg(ST_CFG_LIMIT_MIN, ST_ROLL, to_angle(p.roll_away + LIMIT_MARGIN_DEG));
    cfg(ST_CFG_LIMIT_MAX, ST_ROLL, to_angle(p.roll_toward_tower - LIMIT_MARGIN_DEG));
    cfg(ST_CFG_LIMIT_MIN, ST_AZ, INT64_MIN);
}

// ------------------------------------------------------------------ targets
void Head::compute_target(double t, double roll_hint, HeadAngles &out, bool &ok)
{
    const Site &s = set_.site;
    double lst = lst_at(t, s), lat = s.lat * D2R, tt = tt_centuries(jd_from_unix(t));
    double ra = t_ra_, dec = t_dec_;
    Vec nwu;
    ok = true;
    double dt = t - t_epoch_s_;
    switch (tk_) {
    case TargetKind::None:
        ok = false;
        return;
    case TargetKind::Fixed:
        nwu = {std::cos(fixed_alt_ * D2R) * std::cos(fixed_az_ * D2R), -std::cos(fixed_alt_ * D2R) * std::sin(fixed_az_ * D2R), std::sin(fixed_alt_ * D2R)};
        break;
    default: {
        if (tk_ == TargetKind::Sun) sun_apparent(tt, ra, dec);
        else if (tk_ == TargetKind::Moon) moon_topocentric(tt, lst, s, ra, dec);
        else {
            // drive rate other than sidereal: the target drifts against the stars; plus ASCOM rate offsets
            double drift_as = (RATE_ASPS[0] - RATE_ASPS[(int)rate_]) * dt;            // arcsec of hour angle
            ra += (drift_as / 15.0 + ra_rate_ * dt * 1.00273791) * 15.0 * AS2R;          // RightAscensionRate in s per sidereal s
            dec += dec_rate_ * dt * AS2R;
            if (tk_ == TargetKind::RaDecJ2000) { double ra2 = ra, d2 = dec; j2000_to_apparent(ra2, d2, tt, ra, dec); }
        }
        ra += guide_ra_as_ * AS2R / std::fmax(0.05, std::cos(dec));
        dec += guide_dec_as_ * AS2R;
        nwu = refract_nwu(apparent_to_nwu(ra, dec, lst, lat), s);
        break;
    }
    }
    double az_i, alt_i;
    kin_.to_head(nwu, roll_hint, az_i, alt_i);   // roll_hint carries the azimuth hint
    model_.ideal_to_mech(az_i, alt_i, out.az, out.alt);
    if (set_.mode == MountMode::AltAz && set_.roll_derotate && pa_valid_) {
        Vec pole = apparent_to_nwu(0, PI / 2, lst, lat);
        out.roll = kin_.roll_for_pa(az_i, alt_i, pole, pa_target_);
    } else {
        out.roll = roll_target_;
    }
    double lo, hi;
    roll_limits(out.alt, lo, hi);
    if (out.roll < lo) out.roll = lo;
    if (out.roll > hi) out.roll = hi;
}

void Head::current_sky(HeadState &st)
{
    double maz = from_angle(ms_.ax[0].cmd), malt = from_angle(ms_.ax[1].cmd);
    double az_i, alt_i;
    model_.mech_to_ideal(maz, malt, az_i, alt_i);
    Vec nwu = unrefract_nwu(kin_.to_nwu(az_i, alt_i), set_.site);
    double t = now_s();
    double lst = lst_at(t, set_.site), lat = set_.site.lat * D2R;
    double ra, dec;
    nwu_to_apparent(nwu, lst, lat, ra, dec);
    st.ra_h = ra * R2D / 15.0;
    st.dec_d = dec * R2D;
    double r2, d2;
    apparent_to_j2000(ra, dec, tt_centuries(jd_from_unix(t)), r2, d2);
    st.ra2000_h = r2 * R2D / 15.0;
    st.dec2000_d = d2 * R2D;
    Vec obs = kin_.to_nwu(az_i, alt_i);
    st.alt_deg = std::asin(std::fmax(-1.0, std::fmin(1.0, obs.z))) * R2D;
    st.az_deg = wrap_2pi(std::atan2(-obs.y, obs.x)) * R2D;
    st.lst_h = lst * R2D / 15.0;
    Vec pole = apparent_to_nwu(0, PI / 2, lst, lat);
    st.pa_deg = kin_.pa_for_roll(az_i, alt_i, pole, from_angle(ms_.ax[2].cmd));
}

// ------------------------------------------------------------------ motion messages
void Head::send_move(const HeadAngles &a, bool use_roll)
{
    st_move_t m;
    memset(&m, 0, sizeof m);
    m.axis_mask = use_roll ? 7 : 3;
    m.flags = 1;                                                  // 16 V allowed
    m.vmax_mdeg_s = (uint16_t)(set_.slew_dps * 1000);
    m.amax_mdeg_s2 = 4000;
    m.target[0] = to_angle(a.az);
    m.target[1] = to_angle(a.alt);
    m.target[2] = to_angle(a.roll);
    st_power_t p = {2, 0, pd_.motion_budget_mw};
    port_.send(ST_MSG_POWER, &p, sizeof p);
    port_.send(ST_MSG_MOVE, &m, sizeof m);
    moving_mask_ = m.axis_mask;
    last_sp_us_ = clock_();
}

void Head::send_setpoint()
{
    double t0 = now_s() + 0.2;
    HeadAngles a0, a1, a2;
    bool ok0, ok1, ok2;
    double hint = from_angle(ms_.ax[0].cmd);
    compute_target(t0, hint, a0, ok0);
    compute_target(t0 + 0.5, a0.az, a1, ok1);
    compute_target(t0 + 1.0, a0.az, a2, ok2);
    if (!(ok0 && ok1 && ok2)) return;
    std::string why;
    if (!limit_ok(a0.az, a0.alt, a0.roll, &why)) {
        add_fault("tracking stopped: " + why);
        abort();
        return;
    }
    st_setpoint_t sp;
    memset(&sp, 0, sizeof sp);
    sp.t_us = (uint64_t)(t0 * 1e6);
    sp.valid_ms = 500;
    sp.axis_mask = 7;
    sp.flags = 1 | 2;                                             // PEC (if a table is loaded) + encoder correction
    double p[3][3] = {{a0.az, a1.az, a2.az}, {a0.alt, a1.alt, a2.alt}, {a0.roll, a1.roll, a2.roll}};
    for (int i = 0; i < ST_AXES; i++) {
        double pos = p[i][0], rate = p[i][2] - p[i][0], acc = (p[i][2] - 2 * p[i][1] + p[i][0]) / 0.25;
        if (move_rate_[i] != 0) {                                 // manual move on this axis
            pos = from_angle(ms_.ax[i].cmd) + move_rate_[i] * 0.2;
            rate = move_rate_[i];
            acc = 0;
        }
        sp.ax[i].pos = to_angle(pos);
        sp.ax[i].rate = (int64_t)(rate / 360.0 * (double)ST_RATE_ONE_REV_S);
        sp.ax[i].accel = (int32_t)to_angle(acc);
    }
    port_.send(ST_MSG_SETPOINT, &sp, sizeof sp);
    last_sp_us_ = clock_();
}

void Head::on_motion(uint8_t type, const uint8_t *pl, size_t len)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (type == ST_MSG_STATE && len >= sizeof(st_state_t)) {
        memcpy(&ms_, pl, sizeof ms_);
        have_ms_ = true;
        ms_rx_us_ = clock_();
    } else if (type == ST_MSG_EVENT && len >= sizeof(st_event_t)) {
        st_event_t e;
        memcpy(&e, pl, sizeof e);
        static const char *ax[] = {"azimuth", "altitude", "roll"};
        const char *an = e.axis < 3 ? ax[e.axis] : "head";
        char b[96];
        switch (e.code) {
        case ST_EV_STALL: snprintf(b, sizeof b, "%s: stall (StallGuard), backed off 1 deg", an); add_fault(b); break;
        case ST_EV_SLIP: snprintf(b, sizeof b, "%s: slip of %ld arcsec, re-synced from the encoder", an, (long)e.value); add_fault(b); break;
        case ST_EV_LIMIT: snprintf(b, sizeof b, "%s: soft limit reached", an); add_fault(b); break;
        case ST_EV_DERATE: snprintf(b, sizeof b, "%s motor at %.1f C: current lowered", an, e.value / 10.0); add_fault(b); break;
        case ST_EV_FAULT_SET: snprintf(b, sizeof b, "motion fault 0x%lx (%s)", (unsigned long)e.value, an); add_fault(b); break;
        default: break;
        }
    }
}

void Head::on_power(const PowerInputs &in)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    pin_ = in;
    double demand = act_ == Activity::Slewing || act_ == Activity::Parking ? 20.1 : 3.0;
    PowerDecision d = power_policy(in, demand);
    bool changed = d.motion_budget_mw != pd_.motion_budget_mw;
    pd_ = d;
    if (changed && act_ != Activity::Idle && act_ != Activity::Parked) {
        st_power_t p = {2, 0, pd_.motion_budget_mw};
        port_.send(ST_MSG_POWER, &p, sizeof p);
    }
}

// ------------------------------------------------------------------ 10 Hz tick
void Head::tick()
{
    tick_locked();
    if (on_tick) on_tick();                                       // services (jobs, PEC, calibration): outside the lock
}

void Head::tick_locked()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    int64_t now = clock_();
    ivm_.tick(now / 1e6);
    // pulse guiding: integrate the guide rate while a pulse lasts
    if (guide_dir_ >= 0) {
        double step = set_.guide_rate * RATE_ASPS[0] * 0.1;
        if (guide_dir_ == 0) guide_dec_as_ += step;
        if (guide_dir_ == 1) guide_dec_as_ -= step;
        if (guide_dir_ == 2) guide_ra_as_ += step;
        if (guide_dir_ == 3) guide_ra_as_ -= step;
        if (now >= guide_until_us_) guide_dir_ = -1;
    }
    bool any_moving = false;
    for (int i = 0; i < ST_AXES; i++)
        if (ms_.ax[i].mode == ST_AX_MOVING || ms_.ax[i].mode == ST_AX_STOPPING) any_moving = true;
    switch (act_) {
    case Activity::Slewing:
    case Activity::Parking:
        if (now - last_sp_us_ > 400000 && !any_moving && have_ms_ && ms_rx_us_ > last_sp_us_ + 300000) {
            if (act_ == Activity::Parking) {
                if (moving_mask_ == 4) {                                  // roll is at 0: now the other two
                    HeadAngles a = {set_.park_az, set_.park_alt, set_.park_roll};
                    send_move(a, false);
                    moving_mask_ = 3;
                } else {
                    act_ = Activity::Parked;
                    parked_ = true;
                    tracking_ = false;
                }
            } else {
                act_ = tracking_ && tk_ != TargetKind::None ? Activity::Tracking : Activity::Idle;
                if (act_ == Activity::Tracking) send_setpoint();
            }
        }
        break;
    case Activity::Tracking:
    case Activity::Moving:
        send_setpoint();
        break;
    default:
        break;
    }
    // low battery (D25): finish the exposure, then park
    if (pd_.low_battery && act_ != Activity::Parking && act_ != Activity::Parked) {
        static int64_t since = 0;
        if (!since) since = now;
        if (!ivm_.release || now - since > 300000000) {
            ivm_.stop();
            add_fault("battery low: parking");
            park();
            since = 0;
        }
    }
}

// ------------------------------------------------------------------ commands
std::string Head::goto_radec(double ra_h, double dec_d, bool j2000)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (parked_) return "parked";
    if (ra_h < 0 || ra_h >= 24 || dec_d < -90 || dec_d > 90) return "invalid coordinates";
    tk_ = j2000 ? TargetKind::RaDecJ2000 : TargetKind::RaDecApparent;
    t_ra_ = ra_h * 15.0 * D2R;
    t_dec_ = dec_d * D2R;
    t_epoch_s_ = now_s();
    guide_ra_as_ = guide_dec_as_ = 0;
    if (!pa_valid_) roll_target_ = from_angle(ms_.ax[2].cmd);
    // predict where the target is when the slew ends (two passes)
    HeadAngles a;
    bool ok;
    double t = now_s();
    compute_target(t, from_angle(ms_.ax[0].cmd), a, ok);
    for (int pass = 0; pass < 2; pass++) {
        double d = std::fmax(std::fabs(a.az - from_angle(ms_.ax[0].cmd)), std::fabs(a.alt - from_angle(ms_.ax[1].cmd)));
        double ts = d / set_.slew_dps + 2.5;                          // cruise + accel/decel
        compute_target(t + ts, from_angle(ms_.ax[0].cmd), a, ok);
    }
    std::string why;
    if (!limit_ok(a.az, a.alt, a.roll, &why)) return why;
    send_move(a, set_.mode == MountMode::AltAz && pa_valid_);
    act_ = Activity::Slewing;
    tracking_ = true;
    return "";
}

std::string Head::goto_altaz(double az, double alt)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (parked_) return "parked";
    tk_ = TargetKind::Fixed;
    fixed_az_ = az;
    fixed_alt_ = alt;
    HeadAngles a;
    bool ok;
    compute_target(now_s(), from_angle(ms_.ax[0].cmd), a, ok);
    std::string why;
    if (!limit_ok(a.az, a.alt, roll_target_, &why)) return why;
    a.roll = from_angle(ms_.ax[2].cmd);
    send_move(a, false);
    act_ = Activity::Slewing;
    tracking_ = false;
    return "";
}

std::string Head::goto_body(TargetKind body)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (parked_) return "parked";
    tk_ = body;
    t_epoch_s_ = now_s();
    HeadAngles a;
    bool ok;
    compute_target(now_s() + 10, from_angle(ms_.ax[0].cmd), a, ok);
    std::string why;
    if (!limit_ok(a.az, a.alt, a.roll, &why)) return why;
    send_move(a, false);
    act_ = Activity::Slewing;
    tracking_ = true;
    return "";
}

std::string Head::sync_radec(double ra_h, double dec_d, bool j2000)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (parked_) return "parked";
    double t = now_s(), tt = tt_centuries(jd_from_unix(t));
    double ra = ra_h * 15 * D2R, dec = dec_d * D2R;
    if (j2000) { double r2 = ra, d2 = dec; j2000_to_apparent(r2, d2, tt, ra, dec); }
    Vec nwu = refract_nwu(apparent_to_nwu(ra, dec, lst_at(t, set_.site), set_.site.lat * D2R), set_.site);
    SyncPoint sp;
    kin_.to_head(nwu, from_angle(ms_.ax[0].cmd), sp.ideal_a1, sp.ideal_a2);
    sp.mech_a1 = from_angle(ms_.ax[0].cmd);
    sp.mech_a2 = from_angle(ms_.ax[1].cmd);
    syncs_.push_back(sp);
    if (syncs_.size() > 40) syncs_.erase(syncs_.begin());
    fit_pointing(syncs_.data(), (int)syncs_.size(), model_);
    if (tk_ == TargetKind::RaDecJ2000 || tk_ == TargetKind::RaDecApparent) {   // keep tracking the synced object
        tk_ = TargetKind::RaDecApparent;
        t_ra_ = ra; t_dec_ = dec; t_epoch_s_ = t;
        guide_ra_as_ = guide_dec_as_ = 0;
    }
    return "";
}

void Head::clear_model() { std::lock_guard<std::recursive_mutex> l(mu_); syncs_.clear(); model_ = PointingModel(); }

std::string Head::set_tracking(bool on)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (on && parked_) return "parked";
    tracking_ = on;
    if (on) {
        if (tk_ == TargetKind::None || tk_ == TargetKind::Fixed) {   // track whatever the lens points at now
            HeadState s;
            current_sky(s);
            tk_ = TargetKind::RaDecApparent;
            t_ra_ = s.ra_h * 15 * D2R;
            t_dec_ = s.dec_d * D2R;
            t_epoch_s_ = now_s();
        }
        if (act_ == Activity::Idle) {
            st_power_t p = {2, 0, pd_.motion_budget_mw};
            port_.send(ST_MSG_POWER, &p, sizeof p);
            act_ = Activity::Tracking;
            send_setpoint();
        }
    } else if (act_ == Activity::Tracking) {
        st_stop_t s = {7, 0};
        port_.send(ST_MSG_STOP, &s, sizeof s);
        act_ = Activity::Idle;
    }
    return "";
}

void Head::set_rate(TrackRate r) { std::lock_guard<std::recursive_mutex> l(mu_); if (tk_ != TargetKind::None) { HeadState s; current_sky(s); t_ra_ = s.ra_h * 15 * D2R; t_dec_ = s.dec_d * D2R; t_epoch_s_ = now_s(); tk_ = TargetKind::RaDecApparent; } rate_ = r; }
void Head::set_rate_offsets(double ra, double dec) { std::lock_guard<std::recursive_mutex> l(mu_); ra_rate_ = ra; dec_rate_ = dec; }

std::string Head::move_axis(int axis, double dps)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (axis < 0 || axis > 2) return "invalid axis";
    if (parked_) return "parked";
    if (std::fabs(dps) > set_.slew_dps) return "rate out of range";
    move_rate_[axis] = dps;
    bool any = move_rate_[0] != 0 || move_rate_[1] != 0 || move_rate_[2] != 0;
    if (any) {
        if (act_ != Activity::Moving) {
            if (tk_ == TargetKind::None) { HeadState s; current_sky(s); tk_ = TargetKind::RaDecApparent; t_ra_ = s.ra_h * 15 * D2R; t_dec_ = s.dec_d * D2R; t_epoch_s_ = now_s(); }
            st_power_t p = {2, 0, pd_.motion_budget_mw};
            port_.send(ST_MSG_POWER, &p, sizeof p);
        }
        act_ = Activity::Moving;
        send_setpoint();
    } else {
        // moves done: track what the lens points at now (or stop)
        HeadState s;
        current_sky(s);
        tk_ = TargetKind::RaDecApparent;
        t_ra_ = s.ra_h * 15 * D2R; t_dec_ = s.dec_d * D2R; t_epoch_s_ = now_s();
        roll_target_ = from_angle(ms_.ax[2].cmd);
        if (tracking_) act_ = Activity::Tracking;
        else { act_ = Activity::Idle; st_stop_t st = {7, 0}; port_.send(ST_MSG_STOP, &st, sizeof st); }
    }
    return "";
}

std::string Head::pulse_guide(int dir, int ms)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    if (dir < 0 || dir > 3 || ms < 0 || ms > 60000) return "invalid pulse";
    if (!tracking_) return "not tracking";
    guide_dir_ = dir;
    guide_until_us_ = clock_() + (int64_t)ms * 1000;
    return "";
}

bool Head::is_pulse_guiding() { std::lock_guard<std::recursive_mutex> l(mu_); return guide_dir_ >= 0; }

std::string Head::park()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    tracking_ = false;
    for (double &r : move_rate_) r = 0;
    HeadAngles a = {from_angle(ms_.ax[0].cmd), from_angle(ms_.ax[1].cmd), 0.0};   // roll to 0 first (P5 holds only within +/-43 deg)
    send_move(a, true);
    moving_mask_ = 4;
    act_ = Activity::Parking;
    return "";
}

std::string Head::unpark() { std::lock_guard<std::recursive_mutex> l(mu_); parked_ = false; if (act_ == Activity::Parked) act_ = Activity::Idle; return ""; }

void Head::set_park_here()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    set_.park_az = from_angle(ms_.ax[0].cmd);
    set_.park_alt = from_angle(ms_.ax[1].cmd);
    set_.park_roll = 0;
}

void Head::abort()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    st_stop_t s = {7, 0};
    port_.send(ST_MSG_STOP, &s, sizeof s);
    for (double &r : move_rate_) r = 0;
    tracking_ = false;
    if (act_ != Activity::Parked) act_ = Activity::Idle;
}

std::string Head::roll_to(double roll)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    double lo, hi;
    roll_limits(from_angle(ms_.ax[1].cmd), lo, hi);
    if (roll < lo || roll > hi) return "roll limit";
    roll_target_ = roll;
    pa_valid_ = false;
    if (act_ == Activity::Tracking || act_ == Activity::Moving) return "";   // the next setpoint carries it
    st_move_t m;
    memset(&m, 0, sizeof m);
    m.axis_mask = 4;
    m.flags = 1;
    m.vmax_mdeg_s = (uint16_t)(set_.slew_dps * 1000);
    m.target[2] = to_angle(roll);
    st_power_t p = {2, 0, pd_.motion_budget_mw};
    port_.send(ST_MSG_POWER, &p, sizeof p);
    port_.send(ST_MSG_MOVE, &m, sizeof m);
    return "";
}

std::string Head::rotator_to_pa(double pa)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    pa_target_ = pa;
    pa_valid_ = true;
    HeadState s;
    current_sky(s);
    double maz = from_angle(ms_.ax[0].cmd), malt = from_angle(ms_.ax[1].cmd), az_i, alt_i;
    model_.mech_to_ideal(maz, malt, az_i, alt_i);
    double t = now_s();
    Vec pole = apparent_to_nwu(0, PI / 2, lst_at(t, set_.site), set_.site.lat * D2R);
    double r = kin_.roll_for_pa(az_i, alt_i, pole, pa);
    std::string e = roll_to(r);
    pa_valid_ = e.empty();
    pa_target_ = pa;
    return e;
}

double Head::current_roll() { std::lock_guard<std::recursive_mutex> l(mu_); return from_angle(ms_.ax[2].cmd); }

HeadState Head::state()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    HeadState s;
    s.activity = act_;
    s.tracking = tracking_ && (act_ == Activity::Tracking || act_ == Activity::Moving || act_ == Activity::Slewing);
    s.at_park = parked_;
    s.slewing = act_ == Activity::Slewing || act_ == Activity::Parking;
    s.rate = rate_;
    current_sky(s);
    for (int i = 0; i < ST_AXES; i++) {
        const st_axis_state_t &a = ms_.ax[i];
        s.ax[i].cmd_deg = from_angle(a.cmd);
        s.ax[i].enc_deg = from_angle(a.enc);
        s.ax[i].rate_dps = (double)a.rate * 360.0 / (double)ST_RATE_ONE_REV_S;
        s.ax[i].i_ma = a.i_ma;
        s.ax[i].sg = a.sg;
        s.ax[i].temp_c = a.temp_dc / 10.0;
        s.ax[i].mode = a.mode;
        s.ax[i].flags = a.flags;
    }
    s.vmot = ms_.vmot_mv / 1000.0;
    s.rail = ms_.rail;
    s.motion_faults = ms_.faults;
    s.link_ok = have_ms_ && clock_() - ms_rx_us_ < 500000;
    s.t_us = clock_();
    s.pack_ok = pin_.pack_ok;
    s.pack_v = pin_.pack_v;
    s.soc = pin_.soc;
    s.pack_temp_c = pin_.pack_temp_c;
    s.ext_power = pin_.charging;
    s.power = pd_;
    s.faults = faults_;
    s.model = model_;
    return s;
}

}  // namespace st

namespace st {

// ---------------------------------------------------------------- Phase 6 additions: fault log, raw motion access
void Head::add_fault(const std::string &msg)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    faults_.push_back(msg);
    if (faults_.size() > 20) faults_.erase(faults_.begin());
    FaultEntry e;
    e.seq = ++fault_seq_;
    e.t_us = clock_();
    e.level = (msg.find("fault") != std::string::npos || msg.find("stall") != std::string::npos || msg.find("slip") != std::string::npos) ? 2 : 1;
    e.msg = msg;
    log_.push_back(e);
    if (log_.size() > FAULT_LOG_N) log_.erase(log_.begin());
}

std::vector<FaultEntry> Head::fault_log(uint32_t since)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    std::vector<FaultEntry> out;
    for (auto &e : log_) if (e.seq > since) out.push_back(e);
    return out;
}

void Head::clear_faults()
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    faults_.clear();
    log_.clear();
}

bool Head::send_motion(uint8_t type, const void *payload, size_t len)
{
    std::lock_guard<std::recursive_mutex> l(mu_);
    return port_.send(type, payload, len);
}

void Head::motion_cfg(uint16_t key, int axis, int64_t value)
{
    st_cfg_t c;
    memset(&c, 0, sizeof c);
    c.key = key;
    c.axis = (uint8_t)axis;
    c.value = value;
    send_motion(ST_MSG_CFG_SET, &c, sizeof c);
}

}  // namespace st
