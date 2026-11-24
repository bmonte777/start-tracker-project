// Star Tracker — WebSocket JSON API v1 for the apps (Phase 6). Documented in docs/05-firmware.md section 6.
// Request:  {"v":1,"id":17,"op":"goto","args":{...}}     Reply: {"v":1,"id":17,"ok":true[,"result":{...}]}
// Error:    {"v":1,"id":18,"ok":false,"err":{"code":"limit","msg":"altitude limit 95"}}
// Event:    {"v":1,"ev":"state",...} five times a second.
#include <cmath>
#include <cstdio>
#include "cJSON.h"
#include "st_proto.h"

namespace st {

static const char *activity_name(Activity a)
{
    switch (a) {
    case Activity::Idle: return "idle";
    case Activity::Slewing: return "slewing";
    case Activity::Tracking: return "tracking";
    case Activity::Moving: return "moving";
    case Activity::Parking: return "parking";
    case Activity::Parked: return "parked";
    default: return "fault";
    }
}

static std::string print(cJSON *o)
{
    char *s = cJSON_PrintUnformatted(o);
    std::string r = s ? s : "{}";
    cJSON_free(s);
    cJSON_Delete(o);
    return r;
}

static std::string code_of(const std::string &e)
{
    if (e.rfind("invalid state", 0) == 0) return "state";
    if (e.find("limit") != std::string::npos) return "limit";
    if (e == "parked") return "parked";
    if (e.find("invalid") != std::string::npos || e.find("range") != std::string::npos) return "invalid";
    if (e.find("not tracking") != std::string::npos) return "state";
    return "error";
}

static double num(cJSON *args, const char *k, double def, bool *found = nullptr)
{
    cJSON *v = args ? cJSON_GetObjectItemCaseSensitive(args, k) : nullptr;
    if (found) *found = cJSON_IsNumber(v);
    return cJSON_IsNumber(v) ? v->valuedouble : def;
}

static void settings_json(cJSON *o, const Settings &s)
{
    cJSON_AddStringToObject(o, "name", s.name.c_str());
    cJSON_AddStringToObject(o, "mode", s.mode == MountMode::Equatorial ? "eq" : "altaz");
    cJSON_AddNumberToObject(o, "lat", s.site.lat);
    cJSON_AddNumberToObject(o, "lon", s.site.lon);
    cJSON_AddNumberToObject(o, "elev_m", s.site.elev_m);
    cJSON_AddNumberToObject(o, "pressure_hpa", s.site.pressure_hpa);
    cJSON_AddNumberToObject(o, "temp_c", s.site.temp_c);
    cJSON_AddBoolToObject(o, "refraction", s.site.refraction);
    cJSON_AddNumberToObject(o, "wedge_deg", s.wedge_deg);
    cJSON_AddNumberToObject(o, "payload", s.payload);
    cJSON_AddBoolToObject(o, "wedge_fitted", s.wedge_fitted);
    cJSON_AddBoolToObject(o, "pier_extension", s.pier_extension);
    cJSON_AddBoolToObject(o, "roll_derotate", s.roll_derotate);
    cJSON_AddNumberToObject(o, "slew_dps", s.slew_dps);
    cJSON_AddNumberToObject(o, "guide_rate", s.guide_rate);
    cJSON_AddNumberToObject(o, "park_az", s.park_az);
    cJSON_AddNumberToObject(o, "park_alt", s.park_alt);
}

WsApi::WsApi(Head &h) : head_(h), svc_(h)
{
    boot_us_ = 0;
    head_.on_tick = [this] { svc_.tick(); };
}

static const char *OPS_11[] = {"goto", "sync", "track", "stop", "park", "unpark", "park.set", "jog", "guide", "rotator.pa", "rotator.roll",
    "align.clear", "time.set", "config.get", "config.set", "ivm.start", "ivm.stop", "state", "hello", "limits.get", "faults.get",
    "faults.clear", "health.get", "pec.status", "pec.record", "pec.stop", "pec.play", "pec.save", "pec.clear", "pec.get", "job.start",
    "job.pause", "job.resume", "job.stop", "job.status", "job.ack", "cal.status", "cal.encoder.start", "cal.encoder.status",
    "cal.encoder.abort", "cal.encoder.apply", "cal.balance", "update.status"};

std::string WsApi::info_json(int http_port, int alpaca_port, int lx200_port)
{
    cJSON *o = cJSON_CreateObject();
    Settings s = head_.settings();
    cJSON_AddStringToObject(o, "name", s.name.c_str());
    cJSON_AddStringToObject(o, "model", "Canopus P1");
    cJSON_AddStringToObject(o, "fw", FW_VERSION);
    cJSON_AddStringToObject(o, "api", API_MINOR);
    cJSON_AddNumberToObject(o, "http_port", http_port);
    cJSON_AddNumberToObject(o, "ws_port", http_port);
    cJSON_AddStringToObject(o, "ws_path", "/ws/v1");
    cJSON_AddStringToObject(o, "op_path", "/startracker/v1/op");
    cJSON_AddNumberToObject(o, "alpaca_port", alpaca_port);
    cJSON_AddNumberToObject(o, "lx200_port", lx200_port);
    cJSON_AddStringToObject(o, "platform", svc_.platform.c_str());
    return print(o);
}

std::string WsApi::handle(const std::string &text)
{
    cJSON *req = cJSON_Parse(text.c_str());
    cJSON *rep = cJSON_CreateObject();
    cJSON_AddNumberToObject(rep, "v", 1);
    if (!req) {
        cJSON_AddBoolToObject(rep, "ok", false);
        cJSON *e = cJSON_AddObjectToObject(rep, "err");
        cJSON_AddStringToObject(e, "code", "parse");
        cJSON_AddStringToObject(e, "msg", "request is not JSON");
        return print(rep);
    }
    cJSON *id = cJSON_GetObjectItemCaseSensitive(req, "id");
    if (cJSON_IsNumber(id)) cJSON_AddNumberToObject(rep, "id", id->valuedouble);
    cJSON *opj = cJSON_GetObjectItemCaseSensitive(req, "op");
    cJSON *args = cJSON_GetObjectItemCaseSensitive(req, "args");
    std::string op = cJSON_IsString(opj) ? opj->valuestring : "";
    std::string e;
    cJSON *result = nullptr;
    bool f1, f2;

    if (op == "goto") {
        cJSON *body = args ? cJSON_GetObjectItemCaseSensitive(args, "body") : nullptr;
        if (cJSON_IsString(body)) {
            std::string b = body->valuestring;
            e = b == "sun" ? head_.goto_body(TargetKind::Sun) : b == "moon" ? head_.goto_body(TargetKind::Moon) : "invalid body";
        } else if (args && cJSON_GetObjectItemCaseSensitive(args, "az_d")) {
            e = head_.goto_altaz(num(args, "az_d", 0), num(args, "alt_d", 0));
        } else {
            double ra = num(args, "ra_h", 0, &f1), dec = num(args, "dec_d", 0, &f2);
            cJSON *ep = args ? cJSON_GetObjectItemCaseSensitive(args, "epoch") : nullptr;
            bool j2000 = !cJSON_IsString(ep) || std::string(ep->valuestring) != "JNow";
            e = (f1 && f2) ? head_.goto_radec(ra, dec, j2000) : "invalid arguments: ra_h and dec_d";
        }
    } else if (op == "sync") {
        double ra = num(args, "ra_h", 0, &f1), dec = num(args, "dec_d", 0, &f2);
        cJSON *ep = args ? cJSON_GetObjectItemCaseSensitive(args, "epoch") : nullptr;
        bool j2000 = !cJSON_IsString(ep) || std::string(ep->valuestring) != "JNow";
        e = (f1 && f2) ? head_.sync_radec(ra, dec, j2000) : "invalid arguments: ra_h and dec_d";
    } else if (op == "track") {
        cJSON *on = args ? cJSON_GetObjectItemCaseSensitive(args, "on") : nullptr;
        cJSON *rate = args ? cJSON_GetObjectItemCaseSensitive(args, "rate") : nullptr;
        if (cJSON_IsString(rate)) {
            std::string r = rate->valuestring;
            head_.set_rate(r == "lunar" ? TrackRate::Lunar : r == "solar" ? TrackRate::Solar : r == "king" ? TrackRate::King : TrackRate::Sidereal);
        }
        e = head_.set_tracking(!cJSON_IsFalse(on));
    } else if (op == "stop") {
        head_.abort();
    } else if (op == "park") {
        e = head_.park();
    } else if (op == "unpark") {
        e = head_.unpark();
    } else if (op == "park.set") {
        head_.set_park_here();
    } else if (op == "jog") {
        e = head_.move_axis((int)num(args, "axis", -1), num(args, "dps", 0));
    } else if (op == "guide") {
        cJSON *d = args ? cJSON_GetObjectItemCaseSensitive(args, "dir") : nullptr;
        std::string ds = cJSON_IsString(d) ? d->valuestring : "";
        int dir = ds == "n" ? 0 : ds == "s" ? 1 : ds == "e" ? 2 : ds == "w" ? 3 : -1;
        e = head_.pulse_guide(dir, (int)num(args, "ms", 0));
    } else if (op == "rotator.pa") {
        e = head_.rotator_to_pa(num(args, "pa_d", 0));
    } else if (op == "rotator.roll") {
        e = head_.roll_to(num(args, "roll_d", 0));
    } else if (op == "align.clear") {
        head_.clear_model();
    } else if (op == "time.set") {
        double t = num(args, "unix_s", 0, &f1);
        if (f1) head_.set_time_unix(t); else e = "invalid arguments: unix_s";
    } else if (op == "config.get") {
        result = cJSON_CreateObject();
        settings_json(result, head_.settings());
    } else if (op == "config.set") {
        Settings s = head_.settings();
        if (!cJSON_IsObject(args)) e = "invalid arguments";
        else {
            cJSON *it;
            cJSON_ArrayForEach(it, args) {
                std::string k = it->string ? it->string : "";
                if (k == "lat" && cJSON_IsNumber(it)) s.site.lat = it->valuedouble;
                else if (k == "lon" && cJSON_IsNumber(it)) s.site.lon = it->valuedouble;
                else if (k == "elev_m" && cJSON_IsNumber(it)) s.site.elev_m = it->valuedouble;
                else if (k == "pressure_hpa" && cJSON_IsNumber(it)) s.site.pressure_hpa = it->valuedouble;
                else if (k == "temp_c" && cJSON_IsNumber(it)) s.site.temp_c = it->valuedouble;
                else if (k == "refraction" && cJSON_IsBool(it)) s.site.refraction = cJSON_IsTrue(it);
                else if (k == "mode" && cJSON_IsString(it)) s.mode = std::string(it->valuestring) == "eq" ? MountMode::Equatorial : MountMode::AltAz;
                else if (k == "wedge_deg" && cJSON_IsNumber(it)) s.wedge_deg = it->valuedouble;
                else if (k == "payload" && cJSON_IsNumber(it)) s.payload = it->valueint;
                else if (k == "wedge_fitted" && cJSON_IsBool(it)) s.wedge_fitted = cJSON_IsTrue(it);
                else if (k == "pier_extension" && cJSON_IsBool(it)) s.pier_extension = cJSON_IsTrue(it);
                else if (k == "roll_derotate" && cJSON_IsBool(it)) s.roll_derotate = cJSON_IsTrue(it);
                else if (k == "slew_dps" && cJSON_IsNumber(it)) s.slew_dps = it->valuedouble;
                else if (k == "guide_rate" && cJSON_IsNumber(it)) s.guide_rate = it->valuedouble;
                else if (k == "name" && cJSON_IsString(it)) s.name = it->valuestring;
                else { e = "invalid key " + k; break; }
            }
            if (s.payload < 1 || s.payload > 5) e = "invalid payload (1-5)";
            if (std::fabs(s.site.lat) > 90 || std::fabs(s.site.lon) > 180) e = "invalid site";
            if (e.empty()) head_.apply_settings(s);
        }
    } else if (op == "ivm.start") {
        Intervalometer &iv = head_.intervalometer();
        iv.count = (int)num(args, "count", 0);
        iv.exposure_s = num(args, "exposure_s", 1);
        iv.interval_s = num(args, "interval_s", 2);
        iv.focus_s = num(args, "focus_s", 0.3);
        iv.delay_s = num(args, "delay_s", 0);
        if (iv.exposure_s <= 0 || iv.exposure_s > 3600 || iv.count < 0) e = "invalid intervalometer settings";
        else iv.start(head_.now_s());
    } else if (op == "ivm.stop") {
        head_.intervalometer().stop();
    } else if (op == "state") {
        // Phase 6 fix: the reply is a state event that also carries the request's id (1.0 sent it without)
        std::string ev = state_event();
        if (cJSON_IsNumber(id)) ev.insert(ev.size() - 1, ",\"id\":" + std::to_string((long long)id->valuedouble));
        cJSON_Delete(rep);
        cJSON_Delete(req);
        return ev;
    } else if (op == "hello") {
        result = cJSON_CreateObject();
        Settings st = head_.settings();
        cJSON_AddStringToObject(result, "api", API_MINOR);
        cJSON_AddStringToObject(result, "fw", FW_VERSION);
        cJSON_AddStringToObject(result, "name", st.name.c_str());
        cJSON_AddStringToObject(result, "platform", svc_.platform.c_str());
        cJSON_AddNumberToObject(result, "boot_id", svc_.boot_id);
        cJSON_AddNumberToObject(result, "seq", (double)event_seq());
        cJSON_AddNumberToObject(result, "faults_seq", head_.fault_seq());
        cJSON *caps = cJSON_AddArrayToObject(result, "ops");
        for (const char *o : OPS_11) cJSON_AddItemToArray(caps, cJSON_CreateString(o));
        svc_.job_json(cJSON_AddObjectToObject(result, "job"));
    } else if (op == "limits.get") {
        result = cJSON_CreateObject();
        svc_.limits_json(result);
    } else if (op == "faults.get") {
        result = cJSON_CreateObject();
        cJSON *arr = cJSON_AddArrayToObject(result, "entries");
        for (auto &f : head_.fault_log((uint32_t)num(args, "since", 0))) {
            cJSON *x = cJSON_CreateObject();
            cJSON_AddNumberToObject(x, "seq", f.seq);
            cJSON_AddStringToObject(x, "t", iso8601(f.t_us).c_str());
            cJSON_AddStringToObject(x, "level", f.level >= 2 ? "fault" : "warning");
            cJSON_AddStringToObject(x, "msg", f.msg.c_str());
            cJSON_AddItemToArray(arr, x);
        }
        cJSON_AddNumberToObject(result, "seq", head_.fault_seq());
        cJSON_AddBoolToObject(result, "persistent", svc_.faults_persistent);
    } else if (op == "faults.clear") {
        head_.clear_faults();
    } else if (op == "health.get") {
        result = cJSON_CreateObject();
        svc_.health_json(result);
    } else if (op == "pec.status") {
        result = cJSON_CreateObject();
        svc_.pec_json(result);
    } else if (op == "pec.record") {
        e = svc_.pec_record((int)num(args, "axis", 0), (int)num(args, "cycles", 2));
    } else if (op == "pec.stop") {
        e = svc_.pec_stop();
    } else if (op == "pec.play") {
        cJSON *on = args ? cJSON_GetObjectItemCaseSensitive(args, "on") : nullptr;
        e = svc_.pec_play(!cJSON_IsFalse(on));
    } else if (op == "pec.save") {
        e = svc_.pec_save();
    } else if (op == "pec.clear") {
        e = svc_.pec_clear((int)num(args, "axis", 0));
    } else if (op == "pec.get") {
        result = cJSON_CreateObject();
        e = svc_.pec_curve((int)num(args, "axis", 0), result);
    } else if (op == "job.start") {
        result = cJSON_CreateObject();
        e = svc_.job_start(args, result);
    } else if (op == "job.pause") {
        e = svc_.job_pause();
    } else if (op == "job.resume") {
        e = svc_.job_resume();
    } else if (op == "job.stop") {
        e = svc_.job_stop();
    } else if (op == "job.status") {
        result = cJSON_CreateObject();
        svc_.job_json(result);
    } else if (op == "job.ack") {
        e = svc_.job_ack((int)num(args, "job_id", -1), (int)num(args, "frame", -1));
    } else if (op == "cal.status" || op == "cal.encoder.status") {
        result = cJSON_CreateObject();
        svc_.cal_json(result);
    } else if (op == "cal.encoder.start") {
        e = svc_.cal_encoder_start((int)num(args, "axis", 0), num(args, "speed_dps", 0.5));
    } else if (op == "cal.encoder.abort") {
        e = svc_.cal_abort();
    } else if (op == "cal.encoder.apply") {
        e = svc_.cal_encoder_apply();
    } else if (op == "cal.balance") {
        e = svc_.cal_balance(num(args, "swing_d", 5));
    } else if (op == "update.status") {
        result = cJSON_CreateObject();
        cJSON_AddStringToObject(result, "fw", FW_VERSION);
        cJSON_AddStringToObject(result, "api", API_MINOR);
        if (svc_.update_status) svc_.update_status(result);
    } else {
        e = "invalid op " + op;
    }
    cJSON_AddBoolToObject(rep, "ok", e.empty());
    if (!e.empty()) {
        cJSON *er = cJSON_AddObjectToObject(rep, "err");
        cJSON_AddStringToObject(er, "code", e.rfind("not implemented yet", 0) == 0 ? "notimpl" : code_of(e).c_str());
        cJSON_AddStringToObject(er, "msg", e.c_str());
    }
    if (result) cJSON_AddItemToObject(rep, "result", result);
    cJSON_Delete(req);
    return print(rep);
}

std::string WsApi::state_event()
{
    HeadState s = head_.state();
    cJSON *o = cJSON_CreateObject();
    cJSON_AddNumberToObject(o, "v", 1);
    cJSON_AddStringToObject(o, "ev", "state");
    cJSON_AddNumberToObject(o, "seq", (double)event_seq());
    cJSON_AddStringToObject(o, "t", iso8601(s.t_us).c_str());
    cJSON_AddStringToObject(o, "mode", activity_name(s.activity));
    cJSON_AddStringToObject(o, "frame", head_.settings().mode == MountMode::Equatorial ? "eq" : "altaz");
    cJSON_AddBoolToObject(o, "tracking", s.tracking);
    cJSON_AddBoolToObject(o, "parked", s.at_park);
    cJSON *ax = cJSON_AddObjectToObject(o, "axes");
    const char *names[3] = {"az", "alt", "roll"};
    for (int i = 0; i < ST_AXES; i++) {
        cJSON *a = cJSON_AddObjectToObject(ax, names[i]);
        cJSON_AddNumberToObject(a, "pos_d", std::round(s.ax[i].cmd_deg * 1e6) / 1e6);
        cJSON_AddNumberToObject(a, "enc_d", std::round(s.ax[i].enc_deg * 1e6) / 1e6);
        cJSON_AddNumberToObject(a, "rate_dps", s.ax[i].rate_dps);
        cJSON_AddNumberToObject(a, "i_ma", s.ax[i].i_ma);
        cJSON_AddNumberToObject(a, "load", s.ax[i].sg);
        cJSON_AddNumberToObject(a, "temp_c", s.ax[i].temp_c);
        cJSON_AddNumberToObject(a, "flags", s.ax[i].flags);
    }
    cJSON *rd = cJSON_AddObjectToObject(o, "radec");
    cJSON_AddNumberToObject(rd, "ra_h", s.ra2000_h);
    cJSON_AddNumberToObject(rd, "dec_d", s.dec2000_d);
    cJSON_AddNumberToObject(rd, "ra_now_h", s.ra_h);
    cJSON_AddNumberToObject(rd, "dec_now_d", s.dec_d);
    cJSON_AddNumberToObject(rd, "rot_d", s.pa_deg);
    cJSON *hz = cJSON_AddObjectToObject(o, "altaz");
    cJSON_AddNumberToObject(hz, "az_d", s.az_deg);
    cJSON_AddNumberToObject(hz, "alt_d", s.alt_deg);
    cJSON *b = cJSON_AddObjectToObject(o, "batt");
    cJSON_AddNumberToObject(b, "soc", s.soc);
    cJSON_AddNumberToObject(b, "v", s.pack_v);
    cJSON_AddNumberToObject(b, "temp_c", s.pack_temp_c);
    cJSON_AddBoolToObject(b, "ext", s.ext_power);
    cJSON_AddNumberToObject(b, "motion_budget_w", s.power.motion_budget_mw / 1000.0);
    cJSON *m = cJSON_AddObjectToObject(o, "motor");
    cJSON_AddNumberToObject(m, "vmot", s.vmot);
    cJSON_AddNumberToObject(m, "rail", s.rail);
    cJSON_AddNumberToObject(m, "faults", s.motion_faults);
    cJSON_AddBoolToObject(m, "link", s.link_ok);
    cJSON *pm = cJSON_AddObjectToObject(o, "model");
    cJSON_AddNumberToObject(pm, "points", s.model.n_points);
    cJSON_AddNumberToObject(pm, "rms_as", s.model.rms_arcsec);
    cJSON *iv = cJSON_AddObjectToObject(o, "ivm");
    Intervalometer &ivm = head_.intervalometer();
    cJSON_AddBoolToObject(iv, "running", ivm.running);
    cJSON_AddNumberToObject(iv, "done", ivm.done);
    cJSON_AddNumberToObject(iv, "count", ivm.count);
    if (svc_.job_active()) svc_.job_json(cJSON_AddObjectToObject(o, "job")); else cJSON_AddNullToObject(o, "job");
    svc_.pec_json(cJSON_AddObjectToObject(o, "pec"));
    svc_.cal_json(cJSON_AddObjectToObject(o, "cal"));
    cJSON *fl = cJSON_AddArrayToObject(o, "faults");
    for (auto &f : s.faults) cJSON_AddItemToArray(fl, cJSON_CreateString(f.c_str()));
    return print(o);
}

}  // namespace st
