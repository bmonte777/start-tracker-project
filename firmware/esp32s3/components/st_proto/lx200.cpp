// Star Tracker — LX200 command set over TCP port 4030 (Meade "Telescope Serial Command Protocol", the subset used by
// Stellarium, SkySafari and INDI's LX200 Basic driver). Coordinates are JNow (apparent), like a real LX200.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "st_proto.h"

namespace st {

std::string Lx200::feed(const std::string &in)
{
    std::string out;
    for (char c : in) {
        if (c == 0x06 && buf_.empty()) {                 // ACK: alignment query
            out += head_.settings().mode == MountMode::Equatorial ? "P" : "A";
            continue;
        }
        if (c == ':' && buf_.empty()) { buf_ = ":"; continue; }   // ':' inside :Sd+45*59:53# is data
        if (buf_.empty()) continue;
        if (c == '#') { out += command(buf_.substr(1)); buf_.clear(); continue; }
        buf_ += c;
        if (buf_.size() > 64) buf_.clear();
    }
    return out;
}

static std::string fmt_ra(double h, bool hi)
{
    int hh, mm;
    double ss;
    hours_to_hms(h, hh, mm, ss);
    char b[24];
    if (hi) {
        int s = (int)std::lround(ss);
        if (s == 60) { s = 0; if (++mm == 60) { mm = 0; hh = (hh + 1) % 24; } }
        snprintf(b, sizeof b, "%02d:%02d:%02d#", hh, mm, s);
    } else {
        double m = mm + ss / 60.0;
        snprintf(b, sizeof b, "%02d:%04.1f#", hh, std::floor(m * 10) / 10);
    }
    return b;
}

static std::string fmt_dec(double d, bool hi, char sep = '*')
{
    int sg, dd, mm;
    double ss;
    deg_to_dms(d, sg, dd, mm, ss);
    char b[24];
    if (hi) {
        int s = (int)std::lround(ss);
        if (s == 60) { s = 0; if (++mm == 60) { mm = 0; dd++; } }
        snprintf(b, sizeof b, "%c%02d%c%02d:%02d#", sg < 0 ? '-' : '+', dd, sep, mm, s);
    } else {
        snprintf(b, sizeof b, "%c%02d%c%02d#", sg < 0 ? '-' : '+', dd, sep, mm);
    }
    return b;
}

static bool parse_hms(const std::string &s, double &h)
{
    int a = 0, b = 0;
    double c = 0;
    if (sscanf(s.c_str(), "%d:%d:%lf", &a, &b, &c) == 3) { h = a + b / 60.0 + c / 3600.0; return h >= 0 && h < 24; }
    double m;
    if (sscanf(s.c_str(), "%d:%lf", &a, &m) == 2) { h = a + m / 60.0; return h >= 0 && h < 24; }
    return false;
}

static bool parse_dms(const std::string &s0, double &d)
{
    std::string s = s0;
    for (char &c : s) if (c == '*' || c == '\xdf' || c == '\'' || c == ':') c = ' ';
    int sign = 1;
    size_t i = s.find_first_not_of(' ');
    if (i == std::string::npos) return false;
    if (s[i] == '-') { sign = -1; s[i] = ' '; } else if (s[i] == '+') s[i] = ' ';
    int a = 0, b = 0;
    double c = 0;
    int n = sscanf(s.c_str(), "%d %d %lf", &a, &b, &c);
    if (n < 2) return false;
    d = sign * (a + b / 60.0 + c / 3600.0);
    return true;
}

std::string Lx200::command(const std::string &c)
{
    HeadState st = head_.state();
    Settings set = head_.settings();
    auto starts = [&](const char *p) { return c.compare(0, strlen(p), p) == 0; };
    if (c == "GR") return fmt_ra(st.ra_h, high_precision_);
    if (c == "GD") return fmt_dec(st.dec_d, high_precision_);
    if (c == "GA") return fmt_dec(st.alt_deg, high_precision_);
    if (c == "GZ") { char b[24]; int sg, dd, mm; double ss; deg_to_dms(st.az_deg, sg, dd, mm, ss); snprintf(b, sizeof b, "%03d*%02d:%02d#", dd, mm, (int)ss); return b; }
    if (c == "Gr") return fmt_ra(tra_h_, high_precision_);
    if (c == "Gd") return fmt_dec(tdec_d_, high_precision_);
    if (c == "U") { high_precision_ = !high_precision_; return ""; }
    if (c == "GVP") return "Star Tracker#";
    if (c == "GVN") return "0.1#";
    if (c == "GVD") return "Nov 23 2026#";
    if (c == "GVT") return "00:00:00#";
    if (c == "Gt") return fmt_dec(set.site.lat, false);
    if (c == "Gg") { double w = -set.site.lon; if (w < 0) w += 360; char b[16]; snprintf(b, sizeof b, "%03d*%02d#", (int)w, (int)((w - (int)w) * 60)); return b; }  // LX200: west positive
    if (c == "GG") { char b[24]; snprintf(b, sizeof b, "%+03d#", -utc_offset_h_); return b; }
    if (c == "GS") return fmt_ra(st.lst_h, true);
    if (c == "GL" || c == "GC") {
        time_t t = (time_t)(st.t_us / 1000000 + utc_offset_h_ * 3600);
        struct tm g;
#ifdef _WIN32
        gmtime_s(&g, &t);
#else
        gmtime_r(&t, &g);
#endif
        char b[48];
        if (c == "GL") snprintf(b, sizeof b, "%02d:%02d:%02d#", g.tm_hour, g.tm_min, g.tm_sec);
        else snprintf(b, sizeof b, "%02d/%02d/%02d#", g.tm_mon + 1, g.tm_mday, g.tm_year % 100);
        return b;
    }
    if (c == "D") return st.slewing ? "\x7f#" : "#";      // "distance bars": something while slewing
    if (starts("Sr")) { double h; if (!parse_hms(c.substr(2), h)) return "0"; tra_h_ = h; return "1"; }
    if (starts("Sd")) { double d; if (!parse_dms(c.substr(2), d) || d < -90 || d > 90) return "0"; tdec_d_ = d; return "1"; }
    if (starts("St")) { double d; if (!parse_dms(c.substr(2), d) || std::fabs(d) > 90) return "0"; set.site.lat = d; head_.apply_settings(set); return "1"; }
    if (starts("Sg")) { double d; if (!parse_dms(c.substr(2), d) || d < 0 || d > 360) return "0"; set.site.lon = d > 180 ? 360 - d : -d; head_.apply_settings(set); return "1"; }
    if (starts("SG")) { utc_offset_h_ = -atoi(c.c_str() + 2); return "1"; }
    if (starts("SL") || starts("SC")) return c[1] == 'C' ? "1Updating Planetary Data#                              #" : "1";
    if (c == "MS") {
        std::string e = head_.goto_radec(tra_h_, tdec_d_, false);
        if (e.empty()) return "0";
        return e.find("limit") != std::string::npos ? "1Below horizon or outside the limits#" : "2" + e + "#";
    }
    if (c == "CM" || c == "CMR") { head_.sync_radec(tra_h_, tdec_d_, false); return "Coordinates     matched.        #"; }
    if (c == "Q") { head_.abort(); return ""; }
    if (c == "Qn" || c == "Qs") { head_.move_axis(1, 0); return ""; }
    if (c == "Qe" || c == "Qw") { head_.move_axis(0, 0); return ""; }
    bool eq = set.mode == MountMode::Equatorial;
    (void)eq;
    if (c == "Mn") { head_.move_axis(1, move_rate_dps_); return ""; }
    if (c == "Ms") { head_.move_axis(1, -move_rate_dps_); return ""; }
    if (c == "Me") { head_.move_axis(0, move_rate_dps_); return ""; }
    if (c == "Mw") { head_.move_axis(0, -move_rate_dps_); return ""; }
    if (c == "RG") { move_rate_dps_ = SIDEREAL_RATE_DPS * set.guide_rate; return ""; }
    if (c == "RC") { move_rate_dps_ = 0.1; return ""; }
    if (c == "RM") { move_rate_dps_ = 1.0; return ""; }
    if (c == "RS") { move_rate_dps_ = set.slew_dps; return ""; }
    if (starts("Mg") && c.size() >= 4) {                  // :Mgdnnnn# pulse guide
        int dir = c[2] == 'n' ? 0 : c[2] == 's' ? 1 : c[2] == 'e' ? 2 : c[2] == 'w' ? 3 : -1;
        if (dir >= 0) head_.pulse_guide(dir, atoi(c.c_str() + 3));
        return "";
    }
    if (c == "AP") { head_.set_tracking(true); return ""; }
    if (c == "AL") { head_.set_tracking(false); return ""; }
    if (c == "AA") return "";
    if (c == "TQ") { head_.set_rate(TrackRate::Sidereal); return ""; }
    if (c == "TL") { head_.set_rate(TrackRate::Lunar); return ""; }
    if (c == "TS") { head_.set_rate(TrackRate::Solar); return ""; }
    if (c == "hP") { head_.park(); return ""; }
    if (c == "hW" || c == "hR") { head_.unpark(); return ""; }
    if (c == "GW") return std::string(set.mode == MountMode::Equatorial ? "P" : "A") + (st.tracking ? "T" : "N") + "1#";
    return "";                                            // unknown commands are ignored, as on a real LX200
}

}  // namespace st
