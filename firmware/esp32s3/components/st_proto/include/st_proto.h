// Star Tracker — protocol handlers, independent of the transport (ESP-IDF httpd on the head, a small socket server in
// the simulator): ASCOM Alpaca (Telescope + Rotator, Platform 7 interfaces), LX200 over TCP, WebSocket JSON API v1.
#pragma once
#include <map>
#include <string>
#include "st_head.h"

namespace st {

// --------------------------------------------------------------- ASCOM Alpaca (port 32323, discovery UDP 32227)
struct HttpRequest {
    std::string method;                         // GET / PUT
    std::string path;                           // /api/v1/telescope/0/rightascension
    std::map<std::string, std::string> params;  // query (GET) or form (PUT); keys as received
};
struct HttpResponse { int status = 200; std::string type = "application/json"; std::string body; };

class Alpaca {
public:
    explicit Alpaca(Head &h) : head_(h) {}
    HttpResponse handle(const HttpRequest &r);
    static std::string discovery_reply(int port) { return "{\"AlpacaPort\":" + std::to_string(port) + "}"; }
    static constexpr const char *DISCOVERY_QUERY = "alpacadiscovery1";
private:
    HttpResponse telescope(const std::string &m, const std::string &verb, const HttpRequest &r, uint32_t ctid);
    HttpResponse rotator(const std::string &m, const std::string &verb, const HttpRequest &r, uint32_t ctid);
    HttpResponse management(const std::string &m, uint32_t ctid);
    Head &head_;
    uint32_t stid_ = 0;
    bool connected_[2] = {false, false};
    bool target_ra_set_ = false, target_dec_set_ = false;
    double target_ra_ = 0, target_dec_ = 0;
    double slew_settle_ = 0;
    double rot_offset_ = 0, rot_target_ = 0;
    bool rot_reverse_ = false;
};

// --------------------------------------------------------------- LX200 (TCP 4030)
class Lx200 {
public:
    explicit Lx200(Head &h) : head_(h) {}
    std::string feed(const std::string &in);    // returns the bytes to send back
private:
    std::string command(const std::string &c);
    Head &head_;
    std::string buf_;
    bool high_precision_ = true;
    double tra_h_ = 0, tdec_d_ = 0;
    int utc_offset_h_ = 0;
    double move_rate_dps_ = 1.0;
};

// --------------------------------------------------------------- WebSocket JSON API v1 (ws://<head>/ws/v1)
class WsApi {
public:
    explicit WsApi(Head &h) : head_(h) {}
    std::string handle(const std::string &text);   // one request -> one reply
    std::string state_event();                     // {"v":1,"ev":"state",...}, sent 5 times a second
private:
    Head &head_;
};

std::string iso8601(int64_t unix_us);

}  // namespace st
