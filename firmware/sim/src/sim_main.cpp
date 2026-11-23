// Star Tracker simulator — runs the real head logic on simulated hardware and serves the real protocols:
//   Alpaca      http://localhost:32323  (discovery on UDP 32227)    -> N.I.N.A., ConformU, ASCOM clients
//   LX200       tcp  localhost:4030                                 -> Stellarium, SkySafari
//   Web + WS    http://localhost:8080   ws://localhost:8080/ws/v1   -> the apps (Phase 6), a test page
// Options: --speed N (simulated seconds per real second), --lat --lon --elev, --eq (equatorial on the wedge),
//          --payload 1..5, --http-port, --alpaca-port, --lx-port, --seconds S (run S simulated seconds and exit).
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <thread>
#include "net.h"
#include "sim_head.h"
#include "st_proto.h"

int main(int argc, char **argv)
{
    double speed = 1.0, lat = 38.7223, lon = -9.1393, elev = 50, run_s = -1;   // default site: Lisbon
    int http_port = 8080, alpaca_port = 32323, lx_port = 4030, payload = 3;
    bool eq = false;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        auto next = [&] { return i + 1 < argc ? argv[++i] : (char *)"0"; };
        if (a == "--speed") speed = atof(next());
        else if (a == "--lat") lat = atof(next());
        else if (a == "--lon") lon = atof(next());
        else if (a == "--elev") elev = atof(next());
        else if (a == "--eq") eq = true;
        else if (a == "--payload") payload = atoi(next());
        else if (a == "--http-port") http_port = atoi(next());
        else if (a == "--alpaca-port") alpaca_port = atoi(next());
        else if (a == "--lx-port") lx_port = atoi(next());
        else if (a == "--seconds") run_s = atof(next());
        else { printf("unknown option %s\n", a.c_str()); return 2; }
    }
    st::Settings s;
    s.site.lat = lat;
    s.site.lon = lon;
    s.site.elev_m = elev;
    s.mode = eq ? st::MountMode::Equatorial : st::MountMode::AltAz;
    s.wedge_deg = 90.0 - std::fabs(lat);
    s.payload = payload;
    s.name = "StarTracker-SIM";
    double now = std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
    sim::SimHead sim(now, s);
    // start pointing at the horizon to the north, roll level
    st::Alpaca alpaca(sim.head());
    st::WsApi ws(sim.head());
    std::string page = "<html><body>web page not found</body></html>";
    {
        std::ifstream f(WEB_INDEX);
        if (f) { std::stringstream b; b << f.rdbuf(); page = b.str(); }
    }
    std::mutex alp_mu, ws_mu;
    net::startup();
    net::serve_http(alpaca_port, [&](const st::HttpRequest &r) { std::lock_guard<std::mutex> l(alp_mu); return alpaca.handle(r); }, nullptr, nullptr, 0);
    net::serve_http(http_port, [&](const st::HttpRequest &r) {
        st::HttpResponse h;
        if (r.path == "/" || r.path == "/index.html") { h.type = "text/html"; h.body = page; }
        else if (r.path.rfind("/api/v1/", 0) == 0 || r.path.rfind("/management/", 0) == 0) { std::lock_guard<std::mutex> l(alp_mu); h = alpaca.handle(r); }
        else { h.status = 404; h.type = "text/plain"; h.body = "not found"; }
        return h;
    }, [&](const std::string &t) { std::lock_guard<std::mutex> l(ws_mu); return ws.handle(t); },
       [&] { std::lock_guard<std::mutex> l(ws_mu); return ws.state_event(); }, 200);
    net::serve_lx200_sessions(lx_port, [&]() -> void * { return new st::Lx200(sim.head()); },
                              [](void *p, const std::string &in) { return ((st::Lx200 *)p)->feed(in); });
    net::serve_discovery(32227, alpaca_port);
    printf("Star Tracker simulator: Alpaca http://localhost:%d, web/WebSocket http://localhost:%d (ws /ws/v1), LX200 tcp %d, speed x%g, %s mode at %.4f %.4f\n",
           alpaca_port, http_port, lx_port, speed, eq ? "EQ" : "alt-az", lat, lon);
    fflush(stdout);
    auto t0 = std::chrono::steady_clock::now();
    double simulated = 0;
    for (;;) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        double real = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        double want = real * speed;
        if (want - simulated > 0.001) {
            double step = std::fmin(want - simulated, 1.0);
            sim.advance(step);
            simulated += step;
        }
        if (run_s > 0 && simulated >= run_s) break;
    }
    return 0;
}
