// End-to-end on the simulator: Head + link + motion core + simulated axes, and the protocol handlers in-process.
#include <cstring>
#include "sim_head.h"
#include "st_proto.h"
#include "tst.h"
using namespace st;

static Settings site(bool eq)
{
    Settings s;
    s.site.lat = 38.7223; s.site.lon = -9.1393; s.site.elev_m = 50;
    s.mode = eq ? MountMode::Equatorial : MountMode::AltAz;
    s.wedge_deg = 90 - 38.7223;
    s.payload = 3;
    return s;
}
static const double T0 = 1795478400.0;   // 2026-11-23 22:00 UTC: Vega low in the north-west, Capella rising

static double sep_arcsec(double ra1_h, double dec1, double ra2_h, double dec2)
{
    Vec a = radec_vec(ra1_h * 15 * D2R, dec1 * D2R), b = radec_vec(ra2_h * 15 * D2R, dec2 * D2R);
    return std::acos(std::fmin(1.0, dot(a, b))) / AS2R;
}

static void goto_and_track(bool eq, double ra_h, double dec_d, const char *name)
{
    sim::SimHead h(T0, site(eq));
    h.advance(1.0);
    std::string e = h.head().goto_radec(ra_h, dec_d, true);
    CHECK(e.empty());
    if (!e.empty()) { NOTE("goto refused: %s", e.c_str()); return; }
    double t = 0;
    while (h.head().state().slewing && t < 120) { h.advance(0.5); t += 0.5; }
    h.advance(5.0);
    HeadState s = h.head().state();
    double err = sep_arcsec(s.ra2000_h, s.dec2000_d, ra_h, dec_d);
    NOTE("%s %s: slew %.1f s, commanded pointing error %.2f\" (alt %.1f deg, az %.1f deg)", eq ? "EQ" : "alt-az", name, t, err, s.alt_deg, s.az_deg);
    CHECK(s.tracking);
    CHECK(err < 1.0);
    // track 10 minutes; check the commanded pointing stays on the star, and the encoder agrees within the reducer error
    double worst = 0, worst_enc = 0, pa0 = s.pa_deg, worst_pa = 0;
    for (int k = 0; k < 600; k++) {
        h.advance(1.0);
        HeadState q = h.head().state();
        worst = std::fmax(worst, sep_arcsec(q.ra2000_h, q.dec2000_d, ra_h, dec_d));
        for (int i = 0; i < 2; i++) worst_enc = std::fmax(worst_enc, std::fabs(q.ax[i].enc_deg - h.axis[i].out_deg) * 3600);
        double dpa = std::fabs(q.pa_deg - pa0);
        if (dpa > 180) dpa = 360 - dpa;
        worst_pa = std::fmax(worst_pa, dpa);
    }
    NOTE("  10 min tracking: commanded error worst %.2f\", encoder vs true output worst %.1f\", image angle drift %.3f deg", worst, worst_enc, worst_pa);
    CHECK(worst < 1.0);
    CHECK(worst_enc < 25.0);                     // MT6835 noise 5.4" RMS on one sample
}

TEST(sim_goto_track_altaz_capella) { goto_and_track(false, 5.27815, 45.99799, "Capella"); }
TEST(sim_goto_track_eq_capella) { goto_and_track(true, 5.27815, 45.99799, "Capella"); }

TEST(sim_roll_derotation_altaz)
{
    sim::SimHead h(T0, site(false));
    h.advance(1.0);
    h.head().goto_radec(5.27815, 45.99799, true);
    for (int i = 0; i < 60 && h.head().state().slewing; i++) h.advance(1.0);
    h.advance(2.0);
    double pa_want = h.head().state().pa_deg + 5.0;
    CHECK(h.head().rotator_to_pa(pa_want).empty());
    h.advance(10.0);
    double worst = 0;
    double r0 = h.head().current_roll();
    for (int k = 0; k < 60; k++) {
        h.advance(30.0);
        worst = std::fmax(worst, std::fabs(h.head().state().pa_deg - pa_want));
    }
    NOTE("30 min with roll de-rotation: image angle within %.3f deg of the set angle; roll moved %.2f deg", worst, h.head().current_roll() - r0);
    CHECK(worst < 0.05);
}

TEST(sim_limits_refuse_below_horizon_and_payload_roll)
{
    sim::SimHead h(T0, site(false));
    h.advance(1.0);
    std::string e = h.head().goto_radec(18.0, -80.0, true);       // far below the horizon from Lisbon
    NOTE("goto below the horizon: '%s'", e.c_str());
    CHECK(e.find("limit") != std::string::npos);
    CHECK(!h.head().roll_to(-149).empty());                        // P3: -150 deg minus the 3 deg margin, tripod at alt 0: -117
    CHECK(h.head().roll_to(-60).empty());
}

TEST(sim_low_battery_parks)
{
    sim::SimHead h(T0, site(false));
    h.advance(1.0);
    h.head().goto_radec(5.27815, 45.99799, true);
    h.advance(30.0);
    h.soc = 4.0;                                                    // D25: 5 %
    h.advance(60.0);
    HeadState s = h.head().state();
    NOTE("battery at 4 %%: activity %d, parked %d, roll %.2f deg", (int)s.activity, s.at_park, s.ax[2].cmd_deg);
    CHECK(s.at_park);
    CHECK(std::fabs(s.ax[2].cmd_deg) < 0.01);
}

TEST(proto_alpaca_basic_flow)
{
    sim::SimHead h(T0, site(false));
    h.advance(1.0);
    Alpaca a(h.head());
    auto call = [&](const char *verb, const std::string &path, std::map<std::string, std::string> p = {}) {
        HttpRequest r; r.method = verb; r.path = path; r.params = p; p["ClientTransactionID"] = "5";
        return a.handle(r);
    };
    HttpResponse r = call("GET", "/api/v1/telescope/0/rightascension");
    CHECK(r.body.find("\"ErrorNumber\":1031") != std::string::npos);   // 0x407 not connected
    CHECK(call("PUT", "/api/v1/telescope/0/connected", {{"Connected", "True"}}).body.find("\"ErrorNumber\":0") != std::string::npos);
    CHECK(call("GET", "/api/v1/telescope/0/interfaceversion").body.find("\"Value\":4") != std::string::npos);
    CHECK(call("GET", "/api/v1/telescope/0/targetrightascension").body.find("\"ErrorNumber\":1026") != std::string::npos);   // value not set
    CHECK(call("PUT", "/api/v1/telescope/0/sitelatitude", {{"SiteLatitude", "91"}}).body.find("\"ErrorNumber\":1025") != std::string::npos);
    CHECK(call("PUT", "/api/v1/telescope/0/slewtocoordinatesasync", {{"RightAscension", "5.27815"}, {"Declination", "45.99799"}}).body.find("\"ErrorNumber\":1035") != std::string::npos);   // tracking off
    call("PUT", "/api/v1/telescope/0/tracking", {{"Tracking", "True"}});
    h.advance(1.0);
    r = call("PUT", "/api/v1/telescope/0/slewtocoordinatesasync", {{"RightAscension", "5.27815"}, {"Declination", "45.99799"}});
    CHECK(r.body.find("\"ErrorNumber\":0") != std::string::npos);
    h.advance(0.5);
    CHECK(call("GET", "/api/v1/telescope/0/slewing").body.find("\"Value\":true") != std::string::npos);
    for (int i = 0; i < 120 && call("GET", "/api/v1/telescope/0/slewing").body.find("true") != std::string::npos; i++) h.advance(1.0);
    h.advance(3.0);
    HeadState s = h.head().state();
    NOTE("Alpaca slew done: RA %.6f h Dec %.5f deg (JNow), Alpaca reports %s", s.ra_h, s.dec_d, call("GET", "/api/v1/telescope/0/rightascension").body.c_str());
    CHECK(sep_arcsec(s.ra_h, s.dec_d, 5.27815, 45.99799) < 1.0);   // the Alpaca coordinates are JNow
    CHECK(call("GET", "/management/v1/configureddevices").body.find("Rotator") != std::string::npos);
    CHECK(call("GET", "/api/v1/telescope/0/notamember").status == 400);
    CHECK(call("GET", "/api/v1/telescope/1/rightascension").status == 400);
}

TEST(proto_lx200_stellarium_sequence)
{
    sim::SimHead h(T0, site(false));
    h.advance(1.0);
    Lx200 lx(h.head());
    std::string r = lx.feed(":GR#:GD#");
    NOTE("LX200 :GR#:GD# -> %s", r.c_str());
    CHECK(r.size() >= 18 && r[2] == ':' && r.back() == '#');
    CHECK(lx.feed(":Sr 05:16:41#") == "1");
    CHECK(lx.feed(":Sd +45*59:53#") == "1");
    CHECK(lx.feed(":Sd +95*00:00#") == "0");
    CHECK(lx.feed(":MS#") == "0");
    for (int i = 0; i < 90 && h.head().state().slewing; i++) h.advance(1.0);
    h.advance(3.0);
    r = lx.feed(":GR#:GD#");
    NOTE("after :MS# -> %s", r.c_str());
    CHECK(r.substr(0, 9) == "05:16:41#");
    CHECK(r.substr(9, 7) == "+45*59:" || r.substr(9, 7) == "+45*59:");
    CHECK(lx.feed(":CM#").find("matched") != std::string::npos);
    CHECK(lx.feed(std::string(1, '\x06')) == "A");
    lx.feed(":Q#");
    h.advance(3.0);
    CHECK(!h.head().state().tracking);
}

TEST(proto_websocket_api)
{
    sim::SimHead h(T0, site(false));
    h.advance(1.0);
    WsApi ws(h.head());
    std::string r = ws.handle("{\"v\":1,\"id\":17,\"op\":\"goto\",\"args\":{\"ra_h\":5.27815,\"dec_d\":45.99799,\"epoch\":\"J2000\"}}");
    CHECK(r.find("\"id\":17") != std::string::npos && r.find("\"ok\":true") != std::string::npos);
    r = ws.handle("{\"v\":1,\"id\":18,\"op\":\"goto\",\"args\":{\"ra_h\":18,\"dec_d\":-80}}");
    NOTE("below-horizon goto -> %s", r.c_str());
    CHECK(r.find("\"code\":\"limit\"") != std::string::npos);
    r = ws.handle("{\"v\":1,\"id\":19,\"op\":\"config.set\",\"args\":{\"payload\":7}}");
    CHECK(r.find("\"ok\":false") != std::string::npos);
    r = ws.handle("not json");
    CHECK(r.find("\"code\":\"parse\"") != std::string::npos);
    h.advance(20.0);
    std::string ev = ws.state_event();
    CHECK(ev.find("\"ev\":\"state\"") != std::string::npos && ev.find("\"axes\"") != std::string::npos);
    NOTE("state event: %zu bytes", ev.size());
}
