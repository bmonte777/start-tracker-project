/* Star Tracker — portable motion core. See motion.h and docs/05-firmware.md section 3.2 / 3.5 / 3.8. */
#include "motion.h"
#include <math.h>
#include <string.h>

#define DT            (MOTION_TICK_US * 1e-6)
#define ARCSEC        (1.0 / 3600.0)
#define EVQ           16

static st_event_t evq[EVQ];
static volatile uint8_t evq_w, evq_r;

static void push_event(uint16_t code, uint8_t axis, uint8_t sev, int32_t value)
{
    uint8_t n = (uint8_t)((evq_w + 1) % EVQ);
    if (n == evq_r)
        return;                                   /* full: drop, counters still show the fault */
    evq[evq_w] = (st_event_t){code, axis, sev, value};
    evq_w = n;
}

bool motion_pop_event(motion_t *m, st_event_t *ev)
{
    (void)m;
    if (evq_r == evq_w)
        return false;
    *ev = evq[evq_r];
    evq_r = (uint8_t)((evq_r + 1) % EVQ);
    return true;
}

static void set_fault(motion_t *m, uint32_t f, uint8_t axis, int32_t value)
{
    if (!(m->faults & f))
        push_event(ST_EV_FAULT_SET, axis, 2, (int32_t)f), (void)value;
    m->faults |= f;
}

/* ---- configuration --------------------------------------------------------------------------- */

void motion_default_cfg(axis_cfg_t *c, int axis)
{
    memset(c, 0, sizeof(*c));
    c->usteps_per_rev = 200.0 * 256.0 * 300.0;      /* D2/D23: 200-step motor, 3:1 belt x 100:1 reducer */
    c->vmax_dps = 8.0;                              /* D42 */
    c->amax_dps2 = 4.0;                             /* 2 s to full speed; settle budget spec 3.8 */
    c->jmax_dps3 = 8.0;
    c->slip_limit_deg = 0.05;                       /* spec 7.3 */
    c->corr_deadband_deg = 2.0 * ARCSEC;
    c->corr_rate_track_dps = 1.0 * ARCSEC;
    c->corr_rate_hold_dps = 30.0 * ARCSEC;
    c->derate_c = 80.0f;
    c->stop_c = 95.0f;
    /* currents at 20 C from docs/calc/phase4_results.json (d33.currents); the ESP32 sends cold values */
    if (axis == ST_AZ) {
        c->i_run_ma = 830; c->i_track_ma = 320; c->i_hold_ma = 250;   /* hold >= StealthChop floor 0.16 A at 10 V */
        c->has_limits = false;
    } else if (axis == ST_ALT) {
        c->i_run_ma = 450; c->i_track_ma = 180; c->i_hold_ma = 150;
        c->has_limits = true; c->min_deg = -10.0; c->max_deg = 95.0; /* params.py ALT_MIN/ALT_MAX */
    } else {
        c->i_run_ma = 450; c->i_track_ma = 180; c->i_hold_ma = 150;
        c->has_limits = true; c->min_deg = -130.0; c->max_deg = 8.0; /* tightest payload envelope until the app sets one (D40) */
    }
}

void motion_init(motion_t *m)
{
    memset(m, 0, sizeof(*m));
    for (int i = 0; i < ST_AXES; i++) {
        motion_default_cfg(&m->cfg[i], i);
        m->ax[i].mode = ST_AX_DISABLED;
        m->ax[i].i_scale = 1.0f;
        m->ax[i].temp_c = 25.0f;
    }
    m->sys = ST_MS_IDLE;
    m->hb_timeout_ms = 500;
    m->coast_s = 60;
    m->budget_mw = 36000;   /* 6 A x 6.0 V until the ESP32 says otherwise */
    evq_w = evq_r = 0;
}

static double deg_to_us(const axis_cfg_t *c, double d) { return d * c->usteps_per_rev / 360.0; }
static double us_to_deg(const axis_cfg_t *c, double u) { return u * 360.0 / c->usteps_per_rev; }

/* ---- encoder map ------------------------------------------------------------------------------ */

double motion_enc_correction_arcsec(const axis_tables_t *t, double theta_deg)
{
    if (!t->map_valid)
        return 0.0;
    double th = theta_deg * (M_PI / 180.0), e = 0.0;
    for (int k = 0; k < MOTION_ENC_HARM; k++)
        e += t->harm_a[k] * cos((k + 1) * th) + t->harm_b[k] * sin((k + 1) * th);
    double g = fmod(theta_deg, 360.0);
    if (g < 0) g += 360.0;
    double gi = g * 2.0;                            /* 0.5 deg grid */
    int i0 = (int)gi;
    if (i0 >= MOTION_ENC_GRID_N - 1) i0 = MOTION_ENC_GRID_N - 2;
    double f = gi - i0;
    e += 0.1 * (t->grid[i0] * (1.0 - f) + t->grid[i0 + 1] * f);
    return e;
}

void motion_feed_encoder(motion_t *m, int axis, uint32_t raw21, uint8_t status, bool crc_ok)
{
    axis_state_t *s = &m->ax[axis];
    const axis_cfg_t *c = &m->cfg[axis];
    s->enc_status = (uint8_t)(status | (crc_ok ? 0 : 0x80));
    if (!crc_ok || (status & 0x02)) {               /* CRC error or weak-field warning: do not use */
        s->flags |= ST_AXF_ENC_BAD;
        return;
    }
    s->flags &= (uint16_t)~ST_AXF_ENC_BAD;
    /* multi-turn unwrap: the output moves at most 8 deg/s = 0.008 deg per 1 ms read, far below half a turn */
    if (s->enc_ok) {
        int32_t d = (int32_t)raw21 - (int32_t)s->enc_last_raw;
        if (d > (1 << 20)) s->enc_turns--;
        else if (d < -(1 << 20)) s->enc_turns++;
    }
    s->enc_last_raw = raw21;
    s->enc_raw = raw21;
    double deg = (double)raw21 * 360.0 / 2097152.0;                /* MT6835: 2^21 counts per turn */
    deg -= motion_enc_correction_arcsec(&m->tab[axis], deg) / 3600.0;
    deg += 360.0 * (double)s->enc_turns;
    if (c->enc_invert) deg = -deg;
    deg -= c->enc_offset_deg;
    s->enc_usteps = deg_to_us(c, deg);
    if (s->enc_ok) {
        s->enc_acc += s->p - s->enc_usteps;          /* plan minus encoder, same instant */
        s->enc_acc_n++;
    }
    if (!s->enc_ok) {                               /* first good reading: absolute position at power-up */
        s->enc_ok = true;
        s->p = s->enc_usteps;
        s->target = s->p;
        s->step_off = (double)s->emitted - s->p;
    }
}

void motion_feed_temp(motion_t *m, int axis, float t) { m->ax[axis].temp_c = t; }

void motion_feed_driver(motion_t *m, int axis, uint16_t sg, bool diag, uint32_t drv_status)
{
    axis_state_t *s = &m->ax[axis];
    s->sg = sg;
    s->diag = diag;
    /* DRV_STATUS bits (TMC2209 datasheet 5.5.3): ot 1, s2ga 2, s2gb 3, s2vsa 4, s2vsb 5 */
    if (drv_status & (1u << 1)) set_fault(m, ST_F_DRV_OT, (uint8_t)axis, 0);
    if (drv_status & (0xFu << 2)) set_fault(m, ST_F_DRV_SHORT, (uint8_t)axis, 0);
    if (diag && s->mode == ST_AX_MOVING) {           /* StallGuard via DIAG during a slew (spec 7.3) */
        s->flags |= ST_AXF_STALL;
        set_fault(m, ST_F_STALL, (uint8_t)axis, sg);
        push_event(ST_EV_STALL, (uint8_t)axis, 2, sg);
        /* back off 1 degree from where we are */
        double back = deg_to_us(&m->cfg[axis], 1.0) * (s->v > 0 ? -1.0 : 1.0);
        s->target = s->p + back;
        s->vcap = deg_to_us(&m->cfg[axis], 1.0);
        m->cfg[axis].vmax_dps = fmax(2.0, m->cfg[axis].vmax_dps * 0.75);   /* slow down by itself (D42) */
    }
}

void motion_feed_rail(motion_t *m, uint8_t rail_now, uint16_t vmot_mv)
{
    m->rail_now = rail_now;
    m->vmot_mv = vmot_mv;
    /* under-voltage stop: 14.0 V on 16 V, 8.8 V on 10 V (Phase 4 calc "Motor rail monitor") */
    if ((rail_now == 2 && vmot_mv < 14000) || (rail_now == 1 && vmot_mv < 8800)) {
        set_fault(m, ST_F_VMOT_LOW, 0xFF, vmot_mv);
        for (int i = 0; i < ST_AXES; i++)
            if (m->ax[i].mode == ST_AX_MOVING || m->ax[i].mode == ST_AX_TRACKING)
                m->ax[i].mode = ST_AX_STOPPING;
    }
    if (vmot_mv > 18000)
        set_fault(m, ST_F_VMOT_HIGH, 0xFF, vmot_mv);
}

/* ---- planner ---------------------------------------------------------------------------------- */

static double clampd(double x, double lo, double hi) { return x < lo ? lo : (x > hi ? hi : x); }

/* Online jerk-limited move toward s->target. Re-targetable at any time. Returns true when at rest on target. */
static bool plan_move(axis_state_t *s, const axis_cfg_t *c)
{
    double vmax = fmin(s->vcap, deg_to_us(c, c->vmax_dps));
    double amax = deg_to_us(c, c->amax_dps2), jmax = deg_to_us(c, c->jmax_dps3);
    double d = s->target - s->p;
    double dir = d >= 0 ? 1.0 : -1.0;
    /* distance needed to stop from (v, a) with jerk-limited deceleration (conservative) */
    double vabs = fabs(s->v);
    double s_stop = vabs * vabs / (2.0 * amax) + vabs * amax / (2.0 * jmax);
    double v_des;
    if (fabs(d) < 0.5 && vabs < amax * DT * 2.0) {   /* within half a microstep and slow: arrive */
        s->p = s->target; s->v = 0; s->a = 0;
        return true;
    }
    if (s->v * dir < 0)                               /* moving away: turn round */
        v_des = 0.0;
    else if (fabs(d) <= s_stop + vabs * DT)
        v_des = dir * fmin(vabs, sqrt(fmax(0.0, 2.0 * amax * fabs(d))) );
    else
        v_des = dir * vmax;
    /* acceleration wanted, softened near v_des so the jerk limit can bring a to 0 without overshoot */
    double dv = v_des - s->v;
    double a_des = (dv >= 0 ? 1.0 : -1.0) * amax;
    double a_room = sqrt(2.0 * jmax * fabs(dv));
    if (fabs(a_des) > a_room) a_des = (dv >= 0 ? 1.0 : -1.0) * a_room;
    double da = clampd(a_des - s->a, -jmax * DT, jmax * DT);
    s->a = clampd(s->a + da, -amax, amax);
    double v_new = s->v + s->a * DT;
    if ((dv > 0 && v_new > v_des) || (dv < 0 && v_new < v_des)) { v_new = v_des; s->a = 0; }
    double p_new = s->p + 0.5 * (s->v + v_new) * DT;
    /* never pass the target */
    if ((s->target - p_new) * dir < 0) { p_new = s->target; v_new = 0; s->a = 0; }
    s->v = v_new;
    s->p = p_new;
    return false;
}

/* Evaluate the setpoint polynomial at head time t. */
static void setpoint_eval(const axis_state_t *s, uint64_t t_us, double *pos, double *rate)
{
    double dt = ((double)(int64_t)(t_us - s->sp_t_us)) * 1e-6;
    *pos = s->sp_pos + s->sp_rate * dt + 0.5 * s->sp_acc * dt * dt;
    *rate = s->sp_rate + s->sp_acc * dt;
}

static double pec_offset(const motion_t *m, int axis, double p_us)
{
    const axis_tables_t *t = &m->tab[axis];
    if (!t->pec_valid)
        return 0.0;
    /* motor angle over three turns: the PEC period of spec 4.4 */
    double span = 3.0 * USTEPS_PER_MOTOR_REV;
    double x = fmod(p_us, span);
    if (x < 0) x += span;
    double fi = x * MOTION_PEC_N / span;
    int i0 = (int)fi;
    double f = fi - i0;
    int i1 = (i0 + 1) % MOTION_PEC_N;
    double arcsec = 0.01 * (t->pec[i0 % MOTION_PEC_N] * (1.0 - f) + t->pec[i1] * f);
    return deg_to_us(&m->cfg[axis], arcsec / 3600.0);
}

static void clamp_limits(motion_t *m, int i, double *x)
{
    const axis_cfg_t *c = &m->cfg[i];
    if (!c->has_limits)
        return;
    double lo = deg_to_us(c, c->min_deg), hi = deg_to_us(c, c->max_deg);
    if (*x < lo || *x > hi) {
        *x = clampd(*x, lo, hi);
        if (!(m->ax[i].flags & (ST_AXF_AT_MIN | ST_AXF_AT_MAX)))
            push_event(ST_EV_LIMIT, (uint8_t)i, 1, 0);
        m->ax[i].flags |= (*x <= lo) ? ST_AXF_AT_MIN : ST_AXF_AT_MAX;
    } else {
        m->ax[i].flags &= (uint16_t)~(ST_AXF_AT_MIN | ST_AXF_AT_MAX);
    }
}

void motion_tick(motion_t *m, uint64_t head_us)
{
    m->now_us = head_us;
    /* link supervision (spec 7.3): heartbeat missing 500 ms */
    bool lost = m->last_hb_us && (head_us - m->last_hb_us) > (uint64_t)m->hb_timeout_ms * 1000u;
    if (lost && !m->link_lost) {
        m->link_lost = true;
        m->link_lost_at = head_us;
        set_fault(m, ST_F_LINK_LOST, 0xFF, 0);
        for (int i = 0; i < ST_AXES; i++)
            if (m->ax[i].mode == ST_AX_MOVING) { m->ax[i].target = m->ax[i].p; m->ax[i].mode = ST_AX_STOPPING; }
    } else if (!lost && m->link_lost) {
        m->link_lost = false;
        m->faults &= ~ST_F_LINK_LOST;
        push_event(ST_EV_FAULT_CLEAR, 0xFF, 0, ST_F_LINK_LOST);
    }

    for (int i = 0; i < ST_AXES; i++) {
        axis_state_t *s = &m->ax[i];
        const axis_cfg_t *c = &m->cfg[i];
        double want = s->p;
        switch (s->mode) {
        case ST_AX_DISABLED:
        case ST_AX_FAULT:
            s->v = s->a = 0;
            break;
        case ST_AX_HOLDING:
            s->v = s->a = 0;
            break;
        case ST_AX_MOVING:
        case ST_AX_STOPPING: {
            if (s->mode == ST_AX_STOPPING) {
                /* stop as quickly as the limits allow: target = stopping point */
                double amax = deg_to_us(c, c->amax_dps2);
                double sd = s->v * fabs(s->v) / (2.0 * amax);
                s->target = s->p + sd;
            }
            clamp_limits(m, i, &s->target);
            if (plan_move(s, c)) {
                if (s->mode == ST_AX_MOVING) push_event(ST_EV_MOVE_DONE, (uint8_t)i, 0, 0);
                s->mode = ST_AX_HOLDING;
            }
            if (fabs(s->v) > deg_to_us(c, 0.5)) m->last_fast_us = head_us;
            break;
        }
        case ST_AX_TRACKING: {
            if (!s->sp_valid) { s->mode = ST_AX_HOLDING; break; }
            uint64_t age_ms = (head_us - s->sp_t_us) / 1000u;
            if (age_ms > s->sp_valid_ms) m->faults |= ST_F_SETPOINT_STALE;
            if (m->link_lost && head_us - m->link_lost_at > (uint64_t)m->coast_s * 1000000u) {
                s->mode = ST_AX_STOPPING;                 /* coasted 60 s without the ESP32 */
                break;
            }
            double tp, tr;
            setpoint_eval(s, head_us + MOTION_TICK_US, &tp, &tr);
            if (s->sp_pec) tp += pec_offset(m, i, s->p);
            double unclamped = tp;
            clamp_limits(m, i, &tp);
            if (tp != unclamped) { s->mode = ST_AX_STOPPING; break; }
            /* follow: feed-forward rate + proportional catch-up (tau 50 ms), limited by amax */
            double err = tp - s->p;
            double vcatch = deg_to_us(c, 0.5);
            double v_cmd = tr + clampd(err / 0.05, -vcatch, vcatch);
            double amax = deg_to_us(c, c->amax_dps2);
            v_cmd = clampd(v_cmd, s->v - amax * DT, s->v + amax * DT);
            if (fabs(err) < fabs(v_cmd) * DT && fabs(err) < deg_to_us(c, 1.0 * ARCSEC)) v_cmd = err / DT;
            s->a = (v_cmd - s->v) / DT;
            s->v = v_cmd;
            s->p += v_cmd * DT;
            if (fabs(s->v) > deg_to_us(c, 0.5)) m->last_fast_us = head_us;
            break;
        }
        }
        (void)want;
        /* encoder correction, slewed toward its goal (loop sets the goal at 5 Hz) */
        double crate = deg_to_us(c, s->mode == ST_AX_TRACKING ? c->corr_rate_track_dps : c->corr_rate_hold_dps) * DT;
        if (s->mode == ST_AX_HOLDING || s->mode == ST_AX_TRACKING)
            s->corr += clampd(s->corr_goal - s->corr, -crate, crate);
        /* steps for this tick */
        int64_t goal = (int64_t)llround(s->p + s->corr + s->step_off);
        int64_t n = goal - s->emitted;
        if (n > MOTION_MAX_STEPS_TICK) n = MOTION_MAX_STEPS_TICK;
        if (n < -MOTION_MAX_STEPS_TICK) n = -MOTION_MAX_STEPS_TICK;
        if (s->mode == ST_AX_DISABLED || s->mode == ST_AX_FAULT) n = 0;
        if (n) {
            hal_step_segment(i, (int32_t)(c->dir_invert ? -n : n), MOTION_TICK_US);
            s->emitted += n;
        }
    }
}

/* ---- 5 Hz loop: encoder correction, slip detection, thermal ----------------------------------- */

void motion_slow_loop(motion_t *m)
{
    for (int i = 0; i < ST_AXES; i++) {
        axis_state_t *s = &m->ax[i];
        const axis_cfg_t *c = &m->cfg[i];
        /* thermal (Phase 4 10.7: cut current above 80 C; spec 7.3: stop at 95 C) */
        if (s->temp_c > c->stop_c) {
            if (s->mode != ST_AX_DISABLED && s->mode != ST_AX_FAULT) {
                s->mode = ST_AX_FAULT;
                set_fault(m, ST_F_OVERTEMP, (uint8_t)i, (int32_t)(s->temp_c * 10));
            }
        } else if (s->temp_c > c->derate_c) {
            if (!(s->flags & ST_AXF_DERATED)) push_event(ST_EV_DERATE, (uint8_t)i, 1, (int32_t)(s->temp_c * 10));
            s->flags |= ST_AXF_DERATED;
        } else if (s->temp_c < c->derate_c - 5.0f) {
            s->flags &= (uint16_t)~ST_AXF_DERATED;
        }
        /* power budget: the slew current scales with sqrt(budget / 20.1 W peak), Phase 4 pack-current rule */
        float bud = m->budget_mw / 20100.0f;
        float sc = bud >= 1.0f ? 1.0f : sqrtf(bud > 0.25f ? bud : 0.25f);
        if (s->flags & ST_AXF_DERATED) sc = fminf(sc, 0.7f);
        s->i_scale = sc;

        if (!s->enc_ok || s->enc_acc_n == 0) { s->enc_acc = 0; s->enc_acc_n = 0; continue; }
        /* mean of (plan - encoder) over the last 200 samples: noise 0.0015 deg / sqrt(200) = 0.4" */
        double err = s->enc_acc / s->enc_acc_n;     /* positive: axis is behind the plan */
        s->enc_acc = 0; s->enc_acc_n = 0;
        double actual = s->enc_usteps;
        if (fabs(err) > deg_to_us(c, c->slip_limit_deg) && s->mode != ST_AX_DISABLED) {
            /* slip (spec 7.3): stop, re-sync from the encoder, report */
            s->flags |= ST_AXF_SLIP;
            set_fault(m, ST_F_SLIP, (uint8_t)i, (int32_t)(us_to_deg(c, err) * 3600));
            push_event(ST_EV_SLIP, (uint8_t)i, 2, (int32_t)(us_to_deg(c, err) * 3600));
            double phys = s->p + s->corr + s->step_off;  /* where the steps are */
            s->p = actual;
            s->target = actual;
            s->v = s->a = 0;
            s->corr = s->corr_goal = 0;
            s->step_off = phys - s->p;
            s->mode = ST_AX_HOLDING;
            push_event(ST_EV_RESYNC, (uint8_t)i, 1, 0);
            continue;
        }
        s->flags &= (uint16_t)~ST_AXF_SLIP;
        /* lost-motion correction: only when not slewing, outside the deadband (Q47) */
        if ((s->mode == ST_AX_HOLDING || (s->mode == ST_AX_TRACKING && s->sp_corr)) &&
            fabs(err) > deg_to_us(c, c->corr_deadband_deg)) {
            s->corr_goal = s->corr + err;
            s->flags |= ST_AXF_CORRECTING;
        } else if (fabs(err) < deg_to_us(c, c->corr_deadband_deg) * 0.5) {
            s->flags &= (uint16_t)~ST_AXF_CORRECTING;
        }
    }
}

/* ---- what the hardware layer should do ------------------------------------------------------- */

uint8_t motion_rail_wanted(const motion_t *m)
{
    if (m->rail_req == 0)
        return 0;
    bool any_on = false, fast = false;
    for (int i = 0; i < ST_AXES; i++) {
        if (m->ax[i].mode != ST_AX_DISABLED && m->ax[i].mode != ST_AX_FAULT) any_on = true;
        if (m->ax[i].mode == ST_AX_MOVING) fast = true;
    }
    if (!any_on)
        return 1;                                   /* keep 10 V while enabled-idle: drivers need it to hold */
    /* D43: 16 V for slews, back to 10 V 0.5 s after the last fast movement */
    if (m->rail_req == 2 && (fast || (m->now_us - m->last_fast_us) < 500000u))
        return 2;
    return 1;
}

uint16_t motion_current_ma(const motion_t *m, int axis, bool *spread)
{
    const axis_state_t *s = &m->ax[axis];
    const axis_cfg_t *c = &m->cfg[axis];
    uint16_t ma;
    *spread = false;
    switch (s->mode) {
    case ST_AX_MOVING: case ST_AX_STOPPING:
        ma = (uint16_t)(c->i_run_ma * s->i_scale);
        *spread = true;                              /* SpreadCycle above TPWMTHRS; set by the driver layer */
        break;
    case ST_AX_TRACKING:
        ma = c->i_track_ma; break;
    default:
        ma = c->i_hold_ma; break;
    }
    if (s->flags & ST_AXF_DERATED) ma = (uint16_t)(ma * 0.7f);
    return ma;
}

bool motion_drivers_wanted(const motion_t *m)
{
    if (m->rail_now == 0) return false;
    for (int i = 0; i < ST_AXES; i++)
        if (m->ax[i].mode != ST_AX_DISABLED && m->ax[i].mode != ST_AX_FAULT) return true;
    return false;
}

/* ---- link messages ---------------------------------------------------------------------------- */

static void enable_axes(motion_t *m, uint8_t mask)
{
    for (int i = 0; i < ST_AXES; i++)
        if ((mask & (1u << i)) && m->ax[i].mode == ST_AX_DISABLED)
            m->ax[i].mode = ST_AX_HOLDING;
}

void motion_handle(motion_t *m, uint8_t type, const uint8_t *pl, size_t len, uint64_t now_us)
{
    switch (type) {
    case ST_MSG_HEARTBEAT:
        m->last_hb_us = now_us ? now_us : 1;
        break;
    case ST_MSG_POWER:
        if (len >= sizeof(st_power_t)) {
            const st_power_t *p = (const st_power_t *)pl;
            m->rail_req = p->request;
            m->budget_mw = p->motion_budget_mw;
            if (p->request == 0)
                for (int i = 0; i < ST_AXES; i++) m->ax[i].mode = ST_AX_DISABLED;
        }
        break;
    case ST_MSG_MOVE:
        if (len >= sizeof(st_move_t)) {
            st_move_t mv;
            memcpy(&mv, pl, sizeof mv);
            if (m->rail_req == 0) break;                 /* rail not allowed by the ESP32: ignore */
            enable_axes(m, mv.axis_mask);
            for (int i = 0; i < ST_AXES; i++) {
                if (!(mv.axis_mask & (1u << i))) continue;
                axis_state_t *s = &m->ax[i];
                const axis_cfg_t *c = &m->cfg[i];
                if (s->mode == ST_AX_FAULT) continue;
                double t = motion_angle_to_usteps(c, mv.target[i]);
                if (mv.flags & 2) t += s->p;
                s->target = t;
                double cap = mv.vmax_mdeg_s ? mv.vmax_mdeg_s / 1000.0 : c->vmax_dps;
                if (!(mv.flags & 1)) cap = fmin(cap, 2.0);   /* no 16 V allowed: keep slews gentle */
                s->vcap = deg_to_us(c, fmin(cap, c->vmax_dps));
                s->sp_valid = false;
                s->mode = ST_AX_MOVING;
                s->flags &= (uint16_t)~ST_AXF_STALL;
            }
        }
        break;
    case ST_MSG_STOP:
        if (len >= sizeof(st_stop_t)) {
            const st_stop_t *st = (const st_stop_t *)pl;
            for (int i = 0; i < ST_AXES; i++) {
                if (!(st->axis_mask & (1u << i))) continue;
                axis_state_t *s = &m->ax[i];
                s->sp_valid = false;
                if (st->mode == 2) { s->mode = ST_AX_DISABLED; s->v = s->a = 0; }
                else if (s->mode == ST_AX_MOVING || s->mode == ST_AX_TRACKING) s->mode = ST_AX_STOPPING;
                if (st->mode == 1) m->cfg[i].amax_dps2 = m->cfg[i].amax_dps2;   /* quick = same limits; 4 deg/s^2 is already the hard limit */
            }
        }
        break;
    case ST_MSG_SETPOINT:
        if (len >= sizeof(st_setpoint_t)) {
            st_setpoint_t sp;
            memcpy(&sp, pl, sizeof sp);
            enable_axes(m, sp.axis_mask);
            m->faults &= ~ST_F_SETPOINT_STALE;
            for (int i = 0; i < ST_AXES; i++) {
                if (!(sp.axis_mask & (1u << i))) continue;
                axis_state_t *s = &m->ax[i];
                const axis_cfg_t *c = &m->cfg[i];
                if (s->mode == ST_AX_FAULT || s->mode == ST_AX_MOVING) continue;   /* a move finishes first */
                s->sp_t_us = sp.t_us;
                s->sp_valid_ms = sp.valid_ms;
                s->sp_pos = motion_angle_to_usteps(c, sp.ax[i].pos);
                s->sp_rate = (double)sp.ax[i].rate * c->usteps_per_rev / 1099511627776.0;   /* 2^40 */
                s->sp_acc = motion_angle_to_usteps(c, sp.ax[i].accel);
                s->sp_pec = sp.flags & 1;
                s->sp_corr = (sp.flags & 2) != 0;
                s->sp_valid = true;
                s->mode = ST_AX_TRACKING;
            }
        }
        break;
    case ST_MSG_SYNC_AXIS:
        if (len >= sizeof(st_sync_axis_t)) {
            const st_sync_axis_t *sy = (const st_sync_axis_t *)pl;
            if (sy->axis >= ST_AXES) break;
            axis_state_t *s = &m->ax[sy->axis];
            const axis_cfg_t *c = &m->cfg[sy->axis];
            double phys = s->p + s->corr + s->step_off;
            double newp = sy->source == 1 ? s->enc_usteps : motion_angle_to_usteps(c, sy->pos);
            if (sy->source == 0 && s->enc_ok) {
                /* a sync redefines the axis zero: move the encoder offset with it */
                m->cfg[sy->axis].enc_offset_deg += us_to_deg(c, s->enc_usteps - newp);
                s->enc_usteps = newp;
            }
            s->p = s->target = newp;
            s->corr = s->corr_goal = 0;
            s->step_off = phys - s->p;
        }
        break;
    case ST_MSG_CFG_SET:
        if (len >= sizeof(st_cfg_t)) {
            st_cfg_t cf;
            memcpy(&cf, pl, sizeof cf);
            for (int i = 0; i < ST_AXES; i++) {
                if (cf.axis != 0xFF && cf.axis != i) continue;
                axis_cfg_t *c = &m->cfg[i];
                double deg = (double)cf.value * 360.0 / 4294967296.0;
                switch (cf.key) {
                case ST_CFG_USTEPS_PER_REV: if (cf.value > 0) c->usteps_per_rev = (double)cf.value; break;
                case ST_CFG_DIR_INVERT: c->dir_invert = cf.value != 0; break;
                case ST_CFG_I_RUN_MA: c->i_run_ma = (uint16_t)cf.value; break;
                case ST_CFG_I_TRACK_MA: c->i_track_ma = (uint16_t)cf.value; break;
                case ST_CFG_I_HOLD_MA: c->i_hold_ma = (uint16_t)cf.value; break;
                case ST_CFG_LIMIT_MIN: if (cf.value == INT64_MIN) c->has_limits = false; else { c->has_limits = true; c->min_deg = deg; } break;
                case ST_CFG_LIMIT_MAX: if (cf.value == INT64_MAX) c->has_limits = false; else { c->has_limits = true; c->max_deg = deg; } break;
                case ST_CFG_ENC_OFFSET: c->enc_offset_deg = deg; break;
                case ST_CFG_ENC_INVERT: c->enc_invert = cf.value != 0; break;
                case ST_CFG_VMAX_MDEG_S: c->vmax_dps = fmin(8.0, cf.value / 1000.0); break;
                case ST_CFG_AMAX_MDEG_S2: c->amax_dps2 = cf.value / 1000.0; break;
                case ST_CFG_SLIP_LIMIT: c->slip_limit_deg = deg; break;
                case ST_CFG_CORR_DEADBAND: c->corr_deadband_deg = deg; break;
                case ST_CFG_THERMAL_DERATE_DC: c->derate_c = cf.value / 10.0f; break;
                case ST_CFG_THERMAL_STOP_DC: c->stop_c = cf.value / 10.0f; break;
                case ST_CFG_HB_TIMEOUT_MS: m->hb_timeout_ms = (uint32_t)cf.value; break;
                case ST_CFG_TRACK_COAST_S: m->coast_s = (uint32_t)cf.value; break;
                default: break;
                }
            }
        }
        break;
    case ST_MSG_TABLE:
        if (len >= 8) {
            st_table_t tb;
            memset(&tb, 0, sizeof tb);
            memcpy(&tb, pl, len < sizeof tb ? len : sizeof tb);
            if (tb.axis >= ST_AXES || tb.count > 100) break;
            axis_tables_t *t = &m->tab[tb.axis];
            for (int k = 0; k < tb.count; k++) {
                int idx = tb.offset + k;
                if (tb.table == 1 && idx < MOTION_PEC_N) t->pec[idx] = tb.v[k];
                if (tb.table == 2) {
                    /* encoder map: entries 0..7 harmonic a (0.1"), 8..15 harmonic b, then the grid */
                    if (idx < MOTION_ENC_HARM) t->harm_a[idx] = tb.v[k] * 0.1f;
                    else if (idx < 2 * MOTION_ENC_HARM) t->harm_b[idx - MOTION_ENC_HARM] = tb.v[k] * 0.1f;
                    else if (idx - 2 * MOTION_ENC_HARM < MOTION_ENC_GRID_N) t->grid[idx - 2 * MOTION_ENC_HARM] = tb.v[k];
                }
            }
            if (tb.last) {
                if (tb.table == 1) t->pec_valid = true;
                if (tb.table == 2) { t->map_valid = true; m->ax[tb.axis].flags |= ST_AXF_CALIBRATED; }
            }
        }
        break;
    default:
        break;
    }
}

void motion_fill_state(const motion_t *m, st_state_t *st)
{
    memset(st, 0, sizeof(*st));
    st->t_us = m->now_us;
    st->vmot_mv = m->vmot_mv;
    st->rail = m->rail_now;
    st->sys_state = (uint8_t)m->sys;
    st->faults = m->faults;
    for (int i = 0; i < ST_AXES; i++) {
        const axis_state_t *s = &m->ax[i];
        const axis_cfg_t *c = &m->cfg[i];
        bool spread;
        st->ax[i].cmd = motion_usteps_to_angle(c, s->p);
        st->ax[i].enc = motion_usteps_to_angle(c, s->enc_ok ? s->enc_usteps : s->p);
        st->ax[i].rate = (int64_t)(s->v * 1099511627776.0 / c->usteps_per_rev);
        st->ax[i].i_ma = motion_current_ma(m, i, &spread);
        st->ax[i].sg = s->sg;
        st->ax[i].temp_dc = (int16_t)(s->temp_c * 10.0f);
        st->ax[i].mode = (uint8_t)s->mode;
        st->ax[i].enc_status = s->enc_status;
        st->ax[i].flags = (uint16_t)(s->flags | (spread ? ST_AXF_SPREAD : 0));
    }
}
