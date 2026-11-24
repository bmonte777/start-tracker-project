// Star Tracker — ASCOM Alpaca: Telescope (ITelescopeV4) and Rotator (IRotatorV4) on one device, plus management.
// Specification: ASCOM Alpaca API v1 (https://ascom-standards.org/api/), Platform 7 interface members
// (Connect, Disconnect, Connecting, DeviceState). Error numbers: 0x400 not implemented, 0x401 invalid value,
// 0x402 value not set, 0x407 not connected, 0x408 invalid while parked, 0x40B invalid operation.
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <chrono>
#include <ctime>
#include <thread>
#include "st_proto.h"

namespace st {

enum : int { E_OK = 0, E_NOTIMPL = 0x400, E_INVALID = 0x401, E_NOTSET = 0x402, E_NOTCONN = 0x407, E_PARKED = 0x408, E_INVOP = 0x40B, E_DRIVER = 0x500 };

static std::string lower(std::string s) { for (char &c : s) c = (char)std::tolower((unsigned char)c); return s; }
static std::string jstr(const std::string &s)
{
    std::string o = "\"";
    for (char c : s) { if (c == '"' || c == '\\') o += '\\'; if ((unsigned char)c >= 32) o += c; }
    return o + "\"";
}
static std::string jnum(double v) { char b[40]; snprintf(b, sizeof b, "%.12g", std::isfinite(v) ? v : 0.0); return b; }
static std::string jbool(bool b) { return b ? "true" : "false"; }

std::string iso8601(int64_t unix_us)
{
    time_t t = (time_t)(unix_us / 1000000);
    struct tm g;
#ifdef _WIN32
    gmtime_s(&g, &t);
#else
    gmtime_r(&t, &g);
#endif
    char b[64];
    snprintf(b, sizeof b, "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ", g.tm_year + 1900, g.tm_mon + 1, g.tm_mday, g.tm_hour, g.tm_min, g.tm_sec,
             (int)((unix_us / 1000) % 1000));
    return b;
}

static bool parse_iso(const std::string &s, double &unix_s)
{
    int Y, M, D, h, m;
    double sec;
    if (sscanf(s.c_str(), "%d-%d-%dT%d:%d:%lf", &Y, &M, &D, &h, &m, &sec) != 6) return false;
    int y = Y - (M <= 2);
    long era = (y >= 0 ? y : y - 399) / 400;
    unsigned yoe = (unsigned)(y - era * 400), doy = (153 * (M + (M > 2 ? -3 : 9)) + 2) / 5 + D - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    long days = era * 146097 + (long)doe - 719468;
    unix_s = days * 86400.0 + h * 3600 + m * 60 + sec;
    return true;
}

namespace {
struct Ctx {
    const HttpRequest &r;
    uint32_t ctid, stid;
    bool find(const char *name, std::string &v) const {
        std::string n = lower(name);
        for (auto &kv : r.params) if (lower(kv.first) == n) { v = kv.second; return true; }
        return false;
    }
};
HttpResponse ok_body(uint32_t ctid, uint32_t stid, const std::string &value_json)
{
    HttpResponse h;
    h.body = "{" + (value_json.empty() ? std::string() : "\"Value\":" + value_json + ",") + "\"ClientTransactionID\":" +
             std::to_string(ctid) + ",\"ServerTransactionID\":" + std::to_string(stid) + ",\"ErrorNumber\":0,\"ErrorMessage\":\"\"}";
    return h;
}
HttpResponse err_body(uint32_t ctid, uint32_t stid, int code, const std::string &msg)
{
    HttpResponse h;
    h.body = "{\"ClientTransactionID\":" + std::to_string(ctid) + ",\"ServerTransactionID\":" + std::to_string(stid) +
             ",\"ErrorNumber\":" + std::to_string(code) + ",\"ErrorMessage\":" + jstr(msg) + "}";
    return h;
}
HttpResponse bad_request(const std::string &msg) { HttpResponse h; h.status = 400; h.type = "text/plain"; h.body = msg; return h; }
}  // namespace

static bool get_num(const HttpRequest &r, const char *name, double &v)
{
    std::string n = lower(name);
    for (auto &kv : r.params)
        if (lower(kv.first) == n) {
            char *end = nullptr;
            v = strtod(kv.second.c_str(), &end);
            return end && *end == 0 && !kv.second.empty() && std::isfinite(v);
        }
    return false;
}
static bool get_bool(const HttpRequest &r, const char *name, bool &v)
{
    std::string n = lower(name);
    for (auto &kv : r.params)
        if (lower(kv.first) == n) {
            std::string s = lower(kv.second);
            if (s == "true") { v = true; return true; }
            if (s == "false") { v = false; return true; }
            return false;
        }
    return false;
}

HttpResponse Alpaca::handle(const HttpRequest &r)
{
    // ClientTransactionID: optional unsigned integer; ClientID likewise. Bad values -> treat as 0 (spec: 0 when absent)
    uint32_t ctid = 0;
    for (auto &kv : r.params)
        if (lower(kv.first) == "clienttransactionid") { char *e; unsigned long v = strtoul(kv.second.c_str(), &e, 10); if (*e == 0 && v <= 0xFFFFFFFFul) ctid = (uint32_t)v; }
    std::string p = lower(r.path);
    if (p.rfind("/management/", 0) == 0) return management(p, ctid);
    // /api/v1/{type}/{n}/{member}
    char type[32] = {0}, member[64] = {0};
    int n = -1;
    if (sscanf(p.c_str(), "/api/v1/%31[^/]/%d/%63s", type, &n, member) != 3) return bad_request("unknown path " + r.path);
    std::string t = type, m = member;
    if (n != 0) return bad_request("device number " + std::to_string(n) + " does not exist");
    if (r.method != "GET" && r.method != "PUT") { HttpResponse h; h.status = 405; h.type = "text/plain"; h.body = "method not allowed"; return h; }
    if (t == "telescope") return telescope(m, r.method, r, ctid);
    if (t == "rotator") return rotator(m, r.method, r, ctid);
    return bad_request("unknown device type " + t);
}

HttpResponse Alpaca::management(const std::string &m, uint32_t ctid)
{
    uint32_t s = ++stid_;
    if (m == "/management/apiversions") return ok_body(ctid, s, "[1]");
    if (m == "/management/v1/description")
        return ok_body(ctid, s, "{\"ServerName\":\"Canopus\",\"Manufacturer\":\"Canopus (open source)\",\"ManufacturerVersion\":\"0.1.0\",\"Location\":" +
                                    jstr(head_.settings().name) + "}");
    if (m == "/management/v1/configureddevices")
        return ok_body(ctid, s, "[{\"DeviceName\":\"Canopus head\",\"DeviceType\":\"Telescope\",\"DeviceNumber\":0,\"UniqueID\":\"5f1c0e2a-7a5d-4c49-9d2e-st000telescope\"},"
                                "{\"DeviceName\":\"Canopus roll axis\",\"DeviceType\":\"Rotator\",\"DeviceNumber\":0,\"UniqueID\":\"5f1c0e2a-7a5d-4c49-9d2e-st0000rotator\"}]");
    return bad_request("unknown management path");
}

// members every device has
static bool common(const std::string &m, const std::string &verb, const HttpRequest &r, uint32_t ctid, uint32_t stid, bool &conn,
                   const char *desc, int ifver, HttpResponse &out)
{
    bool get = verb == "GET";
    if (m == "connected") {
        if (get) { out = ok_body(ctid, stid, jbool(conn)); return true; }
        bool v;
        if (!get_bool(r, "Connected", v)) { out = bad_request("Connected must be True or False"); return true; }
        conn = v;
        out = ok_body(ctid, stid, "");
        return true;
    }
    if (m == "connect" && !get) { conn = true; out = ok_body(ctid, stid, ""); return true; }
    if (m == "disconnect" && !get) { conn = false; out = ok_body(ctid, stid, ""); return true; }
    if (m == "connecting" && get) { out = ok_body(ctid, stid, "false"); return true; }
    if (m == "description" && get) { out = ok_body(ctid, stid, jstr(desc)); return true; }
    if (m == "driverinfo" && get) { out = ok_body(ctid, stid, jstr("Canopus head firmware (ESP32-S3 + RP2354A), written from scratch")); return true; }
    if (m == "driverversion" && get) { out = ok_body(ctid, stid, jstr("0.1")); return true; }
    if (m == "interfaceversion" && get) { out = ok_body(ctid, stid, std::to_string(ifver)); return true; }
    if (m == "name" && get) { out = ok_body(ctid, stid, jstr(desc)); return true; }
    if (m == "supportedactions" && get) { out = ok_body(ctid, stid, "[]"); return true; }
    if ((m == "action" || m == "commandblind" || m == "commandbool" || m == "commandstring") && !get) {
        out = err_body(ctid, stid, conn ? E_NOTIMPL : E_NOTCONN, m + " is not implemented");
        return true;
    }
    return false;
}

static int map_error(const std::string &e)
{
    if (e.empty()) return E_OK;
    if (e == "parked") return E_PARKED;
    if (e.find("limit") != std::string::npos || e.find("invalid") != std::string::npos || e.find("range") != std::string::npos) return E_INVALID;
    if (e.find("not tracking") != std::string::npos) return E_INVOP;
    return E_DRIVER;
}

HttpResponse Alpaca::telescope(const std::string &m, const std::string &verb, const HttpRequest &r, uint32_t ctid)
{
    uint32_t s = ++stid_;
    HttpResponse out;
    if (common(m, verb, r, ctid, s, connected_[0], "Canopus head", 4, out)) return out;
    bool get = verb == "GET";
    auto ok = [&](const std::string &v) { return ok_body(ctid, s, v); };
    auto err = [&](int c, const std::string &msg) { return err_body(ctid, s, c, msg); };
    auto from = [&](const std::string &e) { return e.empty() ? ok("") : err(map_error(e), e); };
    auto notimpl = [&]() { return err(E_NOTIMPL, m + " is not implemented"); };

    // capability flags and fixed values are readable without a connection? Platform 7: all but the common members need one
    if (!connected_[0]) return err(E_NOTCONN, "not connected");
    HeadState st = head_.state();
    Settings set = head_.settings();
    bool eq = set.mode == MountMode::Equatorial;

    if (get) {
        if (m == "alignmentmode") return ok(eq ? "1" : "0");
        if (m == "altitude") return ok(jnum(st.alt_deg));
        if (m == "azimuth") return ok(jnum(st.az_deg));
        if (m == "aperturearea" || m == "aperturediameter" || m == "focallength") return notimpl();
        if (m == "athome") return ok("false");
        if (m == "atpark") return ok(jbool(st.at_park));
        if (m == "canfindhome" || m == "cansetpierside" || m == "cansyncaltaz") return ok("false");
        if (m == "canpark" || m == "canpulseguide" || m == "cansetdeclinationrate" || m == "cansetguiderates" || m == "cansetpark" ||
            m == "cansetrightascensionrate" || m == "cansettracking" || m == "canslew" || m == "canslewaltaz" || m == "canslewaltazasync" ||
            m == "canslewasync" || m == "cansync" || m == "canunpark")
            return ok("true");
        if (m == "canmoveaxis") {
            double a;
            if (!get_num(r, "Axis", a)) return bad_request("Axis missing");
            if (a < 0 || a > 2 || a != std::floor(a)) return err(E_INVALID, "Axis must be 0, 1 or 2");
            return ok(a < 2 ? "true" : "false");
        }
        if (m == "axisrates") {
            double a;
            if (!get_num(r, "Axis", a)) return bad_request("Axis missing");
            if (a < 0 || a > 2 || a != std::floor(a)) return err(E_INVALID, "Axis must be 0, 1 or 2");
            return ok(a < 2 ? "[{\"Minimum\":0,\"Maximum\":" + jnum(set.slew_dps) + "}]" : "[]");
        }
        if (m == "declination") return ok(jnum(st.dec_d));
        if (m == "rightascension") return ok(jnum(st.ra_h));
        if (m == "declinationrate") return ok("0");
        if (m == "rightascensionrate") return ok("0");
        if (m == "doesrefraction") return ok(jbool(set.site.refraction));
        if (m == "equatorialsystem") return ok("1");   // topocentric (JNow)
        if (m == "guideratedeclination" || m == "guideraterightascension") return ok(jnum(set.guide_rate * SIDEREAL_RATE_DPS));
        if (m == "ispulseguiding") return ok(jbool(head_.is_pulse_guiding()));
        if (m == "sideofpier" || m == "destinationsideofpier") return notimpl();
        if (m == "siderealtime") return ok(jnum(st.lst_h));
        if (m == "siteelevation") return ok(jnum(set.site.elev_m));
        if (m == "sitelatitude") return ok(jnum(set.site.lat));
        if (m == "sitelongitude") return ok(jnum(set.site.lon));
        if (m == "slewing") return ok(jbool(st.slewing || st.activity == Activity::Moving));
        if (m == "slewsettletime") return ok(jnum(slew_settle_));
        if (m == "targetdeclination") return target_dec_set_ ? ok(jnum(target_dec_)) : err(E_NOTSET, "target declination not set");
        if (m == "targetrightascension") return target_ra_set_ ? ok(jnum(target_ra_)) : err(E_NOTSET, "target right ascension not set");
        if (m == "tracking") return ok(jbool(st.tracking));
        if (m == "trackingrate") return ok(std::to_string((int)st.rate));
        if (m == "trackingrates") return ok("[0,1,2,3]");
        if (m == "utcdate") return ok(jstr(iso8601(st.t_us)));
        if (m == "devicestate") {
            auto item = [](const char *n, const std::string &v) { return std::string("{\"Name\":\"") + n + "\",\"Value\":" + v + "}"; };
            return ok("[" + item("Altitude", jnum(st.alt_deg)) + "," + item("AtHome", "false") + "," + item("AtPark", jbool(st.at_park)) + "," +
                      item("Azimuth", jnum(st.az_deg)) + "," + item("Declination", jnum(st.dec_d)) + "," +
                      item("IsPulseGuiding", jbool(head_.is_pulse_guiding())) + "," + item("RightAscension", jnum(st.ra_h)) + "," +
                      item("SiderealTime", jnum(st.lst_h)) + "," + item("Slewing", jbool(st.slewing)) + "," + item("Tracking", jbool(st.tracking)) + "," +
                      item("UTCDate", jstr(iso8601(st.t_us))) + "," + item("TimeStamp", jstr(iso8601(st.t_us))) + "]");
        }
        return bad_request("unknown telescope member " + m);
    }

    // ---- PUT ----
    double a, b;
    bool v;
    if (m == "abortslew") { if (st.at_park) return err(E_PARKED, "parked"); head_.abort(); return ok(""); }
    if (m == "findhome") return notimpl();
    if (m == "park") { head_.park(); return ok(""); }
    if (m == "unpark") { head_.unpark(); return ok(""); }
    if (m == "setpark") { head_.set_park_here(); return ok(""); }
    if (m == "moveaxis") {
        if (!get_num(r, "Axis", a) || !get_num(r, "Rate", b)) return bad_request("Axis and Rate required");
        if (a < 0 || a > 2 || a != std::floor(a)) return err(E_INVALID, "Axis must be 0, 1 or 2");
        if (a == 2) return err(E_NOTIMPL, "the roll axis moves through the Rotator device");
        if (st.at_park) return err(E_PARKED, "parked");
        if (std::fabs(b) > set.slew_dps) return err(E_INVALID, "Rate outside AxisRates");
        return from(head_.move_axis((int)a, b));
    }
    if (m == "pulseguide") {
        if (!get_num(r, "Direction", a) || !get_num(r, "Duration", b)) return bad_request("Direction and Duration required");
        if (a < 0 || a > 3 || a != std::floor(a)) return err(E_INVALID, "Direction must be 0-3");
        if (b < 0 || b > 60000) return err(E_INVALID, "Duration out of range");
        if (st.at_park) return err(E_PARKED, "parked");
        return from(head_.pulse_guide((int)a, (int)b));
    }
    auto wait_slew = [&]() {                      // synchronous members return when the slew has finished
        for (int i = 0; i < 3000; i++) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            if (!head_.state().slewing) break;
        }
    };
    auto slew_radec = [&](double ra, double dec, bool async) -> HttpResponse {
        if (ra < 0 || ra >= 24) return err(E_INVALID, "RightAscension out of range");
        if (dec < -90 || dec > 90) return err(E_INVALID, "Declination out of range");
        if (st.at_park) return err(E_PARKED, "parked");
        if (!st.tracking) return err(E_INVOP, "tracking must be on to slew to RA/Dec");
        target_ra_ = ra; target_dec_ = dec; target_ra_set_ = target_dec_set_ = true;
        std::string e = head_.goto_radec(ra, dec, false);
        if (!e.empty()) return err(map_error(e), e);
        if (!async) wait_slew();
        return ok("");
    };
    if (m == "slewtocoordinates" || m == "slewtocoordinatesasync") {
        if (!get_num(r, "RightAscension", a) || !get_num(r, "Declination", b)) return bad_request("RightAscension and Declination required");
        return slew_radec(a, b, m == "slewtocoordinatesasync");
    }
    if (m == "slewtotarget" || m == "slewtotargetasync") {
        if (!target_ra_set_ || !target_dec_set_) return err(E_NOTSET, "target not set");
        return slew_radec(target_ra_, target_dec_, m == "slewtotargetasync");
    }
    if (m == "slewtoaltaz" || m == "slewtoaltazasync") {
        if (!get_num(r, "Azimuth", a) || !get_num(r, "Altitude", b)) return bad_request("Azimuth and Altitude required");
        if (a < 0 || a >= 360 || b < -90 || b > 90) return err(E_INVALID, "Azimuth or Altitude out of range");
        if (st.at_park) return err(E_PARKED, "parked");
        if (st.tracking) return err(E_INVOP, "tracking must be off to slew to Alt/Az");
        std::string e = head_.goto_altaz(a, b);
        if (e.empty() && m == "slewtoaltaz") wait_slew();
        return e.empty() ? ok("") : err(map_error(e), e);
    }
    if (m == "synctocoordinates" || m == "synctotarget") {
        if (m == "synctocoordinates") {
            if (!get_num(r, "RightAscension", a) || !get_num(r, "Declination", b)) return bad_request("RightAscension and Declination required");
            if (a < 0 || a >= 24) return err(E_INVALID, "RightAscension out of range");
            if (b < -90 || b > 90) return err(E_INVALID, "Declination out of range");
            target_ra_ = a; target_dec_ = b; target_ra_set_ = target_dec_set_ = true;
        } else if (!target_ra_set_ || !target_dec_set_) return err(E_NOTSET, "target not set");
        if (st.at_park) return err(E_PARKED, "parked");
        if (!st.tracking) return err(E_INVOP, "tracking must be on to sync");
        return from(head_.sync_radec(target_ra_, target_dec_, false));
    }
    if (m == "synctoaltaz") return notimpl();
    if (m == "tracking") {
        if (!get_bool(r, "Tracking", v)) return bad_request("Tracking must be True or False");
        if (st.at_park && v) return err(E_PARKED, "parked");
        return from(head_.set_tracking(v));
    }
    if (m == "trackingrate") {
        if (!get_num(r, "TrackingRate", a)) return bad_request("TrackingRate required");
        if (a < 0 || a > 3 || a != std::floor(a)) return err(E_INVALID, "TrackingRate must be 0-3");
        head_.set_rate((TrackRate)(int)a);
        return ok("");
    }
    if (m == "rightascensionrate" || m == "declinationrate") {
        if (!get_num(r, m == "rightascensionrate" ? "RightAscensionRate" : "DeclinationRate", a)) return bad_request("rate required");
        if (std::fabs(a) > 1000) return err(E_INVALID, "rate out of range");
        if (m == "rightascensionrate") head_.set_rate_offsets(a, 0); else head_.set_rate_offsets(0, a);
        return ok("");
    }
    if (m == "guideratedeclination" || m == "guideraterightascension") {
        if (!get_num(r, m == "guideratedeclination" ? "GuideRateDeclination" : "GuideRateRightAscension", a)) return bad_request("rate required");
        if (a <= 0 || a > SIDEREAL_RATE_DPS * 2) return err(E_INVALID, "guide rate must be 0-2x sidereal");
        set.guide_rate = a / SIDEREAL_RATE_DPS;
        head_.apply_settings(set);
        return ok("");
    }
    if (m == "doesrefraction") {
        if (!get_bool(r, "DoesRefraction", v)) return bad_request("DoesRefraction must be True or False");
        set.site.refraction = v;
        head_.apply_settings(set);
        return ok("");
    }
    if (m == "sitelatitude" || m == "sitelongitude" || m == "siteelevation") {
        const char *pn = m == "sitelatitude" ? "SiteLatitude" : m == "sitelongitude" ? "SiteLongitude" : "SiteElevation";
        if (!get_num(r, pn, a)) return bad_request(std::string(pn) + " required");
        if (m == "sitelatitude") { if (a < -90 || a > 90) return err(E_INVALID, "latitude out of range"); set.site.lat = a; }
        if (m == "sitelongitude") { if (a < -180 || a > 180) return err(E_INVALID, "longitude out of range"); set.site.lon = a; }
        if (m == "siteelevation") { if (a < -300 || a > 10000) return err(E_INVALID, "elevation out of range"); set.site.elev_m = a; }
        head_.apply_settings(set);
        return ok("");
    }
    if (m == "slewsettletime") {
        if (!get_num(r, "SlewSettleTime", a)) return bad_request("SlewSettleTime required");
        if (a < 0 || a > 100) return err(E_INVALID, "settle time out of range");
        slew_settle_ = a;
        return ok("");
    }
    if (m == "targetrightascension") {
        if (!get_num(r, "TargetRightAscension", a)) return bad_request("TargetRightAscension required");
        if (a < 0 || a >= 24) return err(E_INVALID, "out of range");
        target_ra_ = a; target_ra_set_ = true;
        return ok("");
    }
    if (m == "targetdeclination") {
        if (!get_num(r, "TargetDeclination", a)) return bad_request("TargetDeclination required");
        if (a < -90 || a > 90) return err(E_INVALID, "out of range");
        target_dec_ = a; target_dec_set_ = true;
        return ok("");
    }
    if (m == "utcdate") {
        std::string sv;
        Ctx c{r, ctid, s};
        if (!c.find("UTCDate", sv)) return bad_request("UTCDate required");
        double t;
        if (!parse_iso(sv, t)) return err(E_INVALID, "UTCDate is not ISO 8601");
        head_.set_time_unix(t);
        return ok("");
    }
    if (m == "sideofpier") return notimpl();
    return bad_request("unknown telescope member " + m);
}

HttpResponse Alpaca::rotator(const std::string &m, const std::string &verb, const HttpRequest &r, uint32_t ctid)
{
    uint32_t s = ++stid_;
    HttpResponse out;
    if (common(m, verb, r, ctid, s, connected_[1], "Canopus roll axis", 4, out)) return out;
    auto ok = [&](const std::string &v) { return ok_body(ctid, s, v); };
    auto err = [&](int c, const std::string &msg) { return err_body(ctid, s, c, msg); };
    if (!connected_[1]) return err(E_NOTCONN, "not connected");
    HeadState st = head_.state();
    auto wrap = [](double x) { x = std::fmod(x, 360.0); return x < 0 ? x + 360.0 : x; };
    double mech = wrap(rot_reverse_ ? -st.ax[2].cmd_deg : st.ax[2].cmd_deg);
    bool moving = st.ax[2].mode == ST_AX_MOVING || st.ax[2].mode == ST_AX_STOPPING;
    auto move_mech = [&](double target_mech) -> HttpResponse {
        double t = wrap(target_mech);
        double roll = t > 180 ? t - 360 : t;
        if (rot_reverse_) roll = -roll;
        rot_target_ = wrap(target_mech + rot_offset_);
        std::string e = head_.roll_to(roll);
        return e.empty() ? ok("") : err(E_INVALID, e);
    };
    if (verb == "GET") {
        if (m == "canreverse") return ok("true");
        if (m == "ismoving") return ok(jbool(moving));
        if (m == "mechanicalposition") return ok(jnum(mech));
        if (m == "position") return ok(jnum(wrap(mech + rot_offset_)));
        if (m == "reverse") return ok(jbool(rot_reverse_));
        if (m == "stepsize") return ok(jnum(360.0 / 15360000.0));
        if (m == "targetposition") return ok(jnum(rot_target_));
        if (m == "devicestate")
            return ok("[{\"Name\":\"IsMoving\",\"Value\":" + jbool(moving) + "},{\"Name\":\"MechanicalPosition\",\"Value\":" + jnum(mech) +
                      "},{\"Name\":\"Position\",\"Value\":" + jnum(wrap(mech + rot_offset_)) + "},{\"Name\":\"TimeStamp\",\"Value\":" +
                      jstr(iso8601(st.t_us)) + "}]");
        return bad_request("unknown rotator member " + m);
    }
    double a;
    bool v;
    if (m == "halt") { head_.roll_to(st.ax[2].cmd_deg); return ok(""); }
    if (m == "reverse") { if (!get_bool(r, "Reverse", v)) return bad_request("Reverse must be True or False"); rot_reverse_ = v; return ok(""); }
    if (m == "move") {
        if (!get_num(r, "Position", a)) return bad_request("Position required");
        if (std::fabs(a) >= 360) return err(E_INVALID, "relative move must be within +/-360");
        return move_mech(mech + a);
    }
    if (m == "moveabsolute") {
        if (!get_num(r, "Position", a)) return bad_request("Position required");
        if (a < 0 || a >= 360) return err(E_INVALID, "Position must be 0-360");
        return move_mech(a - rot_offset_);
    }
    if (m == "movemechanical") {
        if (!get_num(r, "Position", a)) return bad_request("Position required");
        if (a < 0 || a >= 360) return err(E_INVALID, "Position must be 0-360");
        return move_mech(a);
    }
    if (m == "sync") {
        if (!get_num(r, "Position", a)) return bad_request("Position required");
        if (a < 0 || a >= 360) return err(E_INVALID, "Position must be 0-360");
        rot_offset_ = a - mech;
        rot_target_ = a;
        return ok("");
    }
    return bad_request("unknown rotator member " + m);
}

}  // namespace st
