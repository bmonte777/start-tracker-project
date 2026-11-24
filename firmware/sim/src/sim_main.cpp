// Star Tracker simulator — runs the real head logic on simulated hardware and serves the real protocols:
//   Alpaca      http://localhost:32323  (discovery on UDP 32227)    -> N.I.N.A., ConformU, ASCOM clients
//   LX200       tcp  localhost:4030                                 -> Stellarium, SkySafari
//   Web + WS    http://localhost:8080   ws://localhost:8080/ws/v1   -> the apps (Phase 6), a test page
// Options: --speed N (simulated seconds per real second), --lat --lon --elev, --eq (equatorial on the wedge),
//          --payload 1..5, --raw-encoder (encoders without their map, for cal.encoder), --soc N (battery at start), --data DIR (keep PEC tables,
//          encoder maps and the fault log in files there, as the head does in flash, D78), --http-port, --alpaca-port, --lx-port, --seconds S (run S simulated seconds and exit).
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <sstream>
#include <thread>
#include "net.h"
#include "sim_head.h"
#include "sha256.h"
#include "st_filestore.h"
#include "st_proto.h"

int main(int argc, char **argv)
{
    double speed = 1.0, lat = 38.7223, lon = -9.1393, elev = 50, run_s = -1;   // default site: Lisbon
    int http_port = 8080, alpaca_port = 32323, lx_port = 4030, payload = 3;
    bool eq = false, raw_enc = false;
    double soc0 = -1;
    std::string data_dir;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        auto next = [&] { return i + 1 < argc ? argv[++i] : (char *)"0"; };
        if (a == "--speed") speed = atof(next());
        else if (a == "--lat") lat = atof(next());
        else if (a == "--lon") lon = atof(next());
        else if (a == "--elev") elev = atof(next());
        else if (a == "--eq") eq = true;
        else if (a == "--raw-encoder") raw_enc = true;
        else if (a == "--soc") soc0 = atof(next());
        else if (a == "--data") data_dir = next();
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
    s.name = "Canopus-SIM";
    double now = std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
    sim::SimHead sim(now, s);
    // start pointing at the horizon to the north, roll level
    if (raw_enc) sim.raw_encoders();
    if (soc0 >= 0) { sim.soc = soc0; sim.pack_v = 6.0 + 2.4 * soc0 / 100.0; }
    st::Alpaca alpaca(sim.head());
    st::WsApi ws(sim.head());
    ws.services().platform = "simulator";
    ws.services().boot_id = (uint32_t)(now * 1000) & 0x7FFFFFFF;
    sim.head().on_set_time = [&sim](double t) { sim.set_time_us((int64_t)(t * 1e6)); };
    // D78: persistent tables and fault log, the same FileStore code the head runs on LittleFS
    std::unique_ptr<st::FileStore> fstore;
    if (!data_dir.empty()) {
        fstore.reset(new st::FileStore(data_dir));
        st::FileStore *fs = fstore.get();
        sim.head().restore_fault_log(fs->load_faults());
        sim.head().on_fault_logged = [fs](const st::FaultEntry &e) { fs->append_fault(e); };
        sim.head().on_faults_cleared = [fs] { fs->clear_faults(); };
        ws.services().store = [fs](const std::string &k, const std::vector<int16_t> &v) { return fs->put(k, v); };
        ws.services().load = [fs](const std::string &k, std::vector<int16_t> &v) { return fs->get(k, v); };
        ws.services().erase = [fs](const std::string &k) { return fs->remove(k); };
        ws.services().faults_persistent = true;
        ws.services().restore_saved();
    }
    std::string last_update = "none";
    ws.services().update_status = [&last_update](cJSON *o) {
        cJSON_AddStringToObject(o, "running_slot", "ota_0 (simulated)");
        cJSON_AddBoolToObject(o, "rollback_possible", true);
        cJSON_AddStringToObject(o, "last_upload", last_update.c_str());
    };
    std::string page = "<html><body>web page not found</body></html>";
    {
        std::ifstream f(WEB_INDEX);
        if (f) { std::stringstream b; b << f.rdbuf(); page = b.str(); }
    }
    std::mutex alp_mu, ws_mu;
    net::startup();
    net::serve_http(alpaca_port, [&](const st::HttpRequest &r) {
        if (r.path == "/startracker/v1/info") { st::HttpResponse h; h.body = ws.info_json(http_port, alpaca_port, lx_port); return h; }
        std::lock_guard<std::mutex> l(alp_mu); return alpaca.handle(r); }, nullptr, nullptr, 0);
    net::serve_http(http_port, [&](const st::HttpRequest &r) {
        st::HttpResponse h;
        if (r.path == "/" || r.path == "/index.html") { h.type = "text/html"; h.body = page; }
        else if (r.path == "/startracker/v1/info") { h.body = ws.info_json(http_port, alpaca_port, lx_port); }
        else if (r.path == "/startracker/v1/op" && r.method == "POST") { std::lock_guard<std::mutex> l(ws_mu); h.body = ws.handle(r.body); }
        else if (r.path == "/api/update" && r.method == "POST") {
            // the simulator checks the bundle like the head (ota.cpp) but does not replace itself
            std::string summary, e = sim::check_bundle(r.body, summary);
            h.type = "text/plain";
            if (!e.empty()) { h.status = e == "not a Canopus bundle" ? 400 : 500; h.body = e; last_update = "refused: " + e; }
            else { h.body = "update stored; the head restarts and checks both processors"; last_update = "accepted (" + summary + "simulator does not restart)"; }
        }
        else if (r.path.rfind("/api/v1/", 0) == 0 || r.path.rfind("/management/", 0) == 0) { std::lock_guard<std::mutex> l(alp_mu); h = alpaca.handle(r); }
        else { h.status = 404; h.type = "text/plain"; h.body = "not found"; }
        return h;
    }, [&](const std::string &t) { std::lock_guard<std::mutex> l(ws_mu); return ws.handle(t); },
       [&] { std::lock_guard<std::mutex> l(ws_mu); return ws.state_event(); }, 200);
    net::serve_lx200_sessions(lx_port, [&]() -> void * { return new st::Lx200(sim.head()); },
                              [](void *p, const std::string &in) { return ((st::Lx200 *)p)->feed(in); });
    net::serve_discovery(32227, alpaca_port);
    printf("Canopus simulator: Alpaca http://localhost:%d, web/WebSocket http://localhost:%d (ws /ws/v1), LX200 tcp %d, speed x%g, %s mode at %.4f %.4f\n",
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
