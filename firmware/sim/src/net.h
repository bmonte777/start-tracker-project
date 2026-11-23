// Star Tracker simulator — minimal TCP/UDP servers: HTTP/1.1 (Alpaca and the web page), WebSocket, LX200, discovery.
#pragma once
#include <functional>
#include <string>
#include "st_proto.h"

namespace net {
using HttpFn = std::function<st::HttpResponse(const st::HttpRequest &)>;
using WsFn = std::function<std::string(const std::string &)>;     // request -> reply
using WsEventFn = std::function<std::string()>;                   // periodic event text
void startup();
void serve_http(int port, HttpFn fn, WsFn ws, WsEventFn ev, int ev_period_ms);   // runs in its own threads
void serve_lx200_sessions(int port, std::function<void *()> make, std::function<std::string(void *, const std::string &)> feed);
void serve_discovery(int udp_port, int alpaca_port);
std::string sha1_base64(const std::string &s);
}  // namespace net
