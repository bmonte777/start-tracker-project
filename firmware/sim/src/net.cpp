// Star Tracker simulator — minimal servers. One thread per connection; fine for a handful of clients.
#include "net.h"
#include <atomic>
#include <chrono>
#include <cstring>
#include <map>
#include <sstream>
#include <thread>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET sock_t;
#define CLOSESOCK closesocket
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <csignal>
#include <sys/socket.h>
#include <unistd.h>
typedef int sock_t;
#define CLOSESOCK close
#endif

namespace net {

void startup()
{
#ifdef _WIN32
    WSADATA w;
    WSAStartup(MAKEWORD(2, 2), &w);
#else
    // A client that vanishes mid-send (an app killed, a browser closed) must not kill the simulator: without this, Linux
    // and macOS end the process with SIGPIPE on the next send (found by the Phase 6 screenshot runs).
    signal(SIGPIPE, SIG_IGN);
#endif
}

static sock_t listen_tcp(int port)
{
    sock_t s = socket(AF_INET, SOCK_STREAM, 0);
    int one = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (const char *)&one, sizeof one);
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    a.sin_port = htons((uint16_t)port);
    if (bind(s, (sockaddr *)&a, sizeof a) != 0 || listen(s, 16) != 0) { fprintf(stderr, "cannot listen on port %d\n", port); exit(1); }
    return s;
}

static bool send_all(sock_t c, const std::string &d)
{
    size_t off = 0;
    while (off < d.size()) {
        int n = send(c, d.data() + off, (int)(d.size() - off), 0);
        if (n <= 0) return false;
        off += (size_t)n;
    }
    return true;
}

// ---------------------------------------------------------------- SHA-1 + base64 (WebSocket handshake, RFC 6455)
std::string sha1_base64(const std::string &msg)
{
    uint32_t h[5] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0};
    std::string m = msg;
    uint64_t bits = (uint64_t)m.size() * 8;
    m += (char)0x80;
    while (m.size() % 64 != 56) m += (char)0;
    for (int i = 7; i >= 0; i--) m += (char)((bits >> (i * 8)) & 0xFF);
    for (size_t off = 0; off < m.size(); off += 64) {
        uint32_t w[80];
        for (int i = 0; i < 16; i++)
            w[i] = ((uint32_t)(uint8_t)m[off + 4 * i] << 24) | ((uint32_t)(uint8_t)m[off + 4 * i + 1] << 16) |
                   ((uint32_t)(uint8_t)m[off + 4 * i + 2] << 8) | (uint8_t)m[off + 4 * i + 3];
        for (int i = 16; i < 80; i++) { uint32_t x = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]; w[i] = (x << 1) | (x >> 31); }
        uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4];
        for (int i = 0; i < 80; i++) {
            uint32_t f, k;
            if (i < 20) { f = (b & c) | (~b & d); k = 0x5A827999; }
            else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1; }
            else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
            else { f = b ^ c ^ d; k = 0xCA62C1D6; }
            uint32_t t = ((a << 5) | (a >> 27)) + f + e + k + w[i];
            e = d; d = c; c = (b << 30) | (b >> 2); b = a; a = t;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e;
    }
    uint8_t dig[20];
    for (int i = 0; i < 5; i++) for (int j = 0; j < 4; j++) dig[i * 4 + j] = (uint8_t)(h[i] >> (24 - 8 * j));
    static const char *T = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string o;
    for (int i = 0; i < 20; i += 3) {
        uint32_t v = (uint32_t)dig[i] << 16 | (i + 1 < 20 ? (uint32_t)dig[i + 1] << 8 : 0) | (i + 2 < 20 ? dig[i + 2] : 0);
        o += T[(v >> 18) & 63];
        o += T[(v >> 12) & 63];
        o += i + 1 < 20 ? T[(v >> 6) & 63] : '=';
        o += i + 2 < 20 ? T[v & 63] : '=';
    }
    return o;
}

static std::string url_decode(const std::string &s)
{
    std::string o;
    for (size_t i = 0; i < s.size(); i++) {
        if (s[i] == '+') o += ' ';
        else if (s[i] == '%' && i + 2 < s.size()) { o += (char)strtol(s.substr(i + 1, 2).c_str(), nullptr, 16); i += 2; }
        else o += s[i];
    }
    return o;
}

static void parse_params(const std::string &q, std::map<std::string, std::string> &out)
{
    std::stringstream ss(q);
    std::string kv;
    while (std::getline(ss, kv, '&')) {
        if (kv.empty()) continue;
        size_t e = kv.find('=');
        out[url_decode(kv.substr(0, e))] = e == std::string::npos ? "" : url_decode(kv.substr(e + 1));
    }
}

static void ws_session(sock_t c, WsFn ws, WsEventFn ev, int period_ms)
{
    std::atomic<bool> alive{true};
    std::mutex tx;
    auto frame = [](const std::string &p, uint8_t op = 0x1) {
        std::string f;
        f += (char)(0x80 | op);
        if (p.size() < 126) f += (char)p.size();
        else if (p.size() < 65536) { f += (char)126; f += (char)(p.size() >> 8); f += (char)(p.size() & 0xFF); }
        else { f += (char)127; for (int i = 7; i >= 0; i--) f += (char)((uint64_t)p.size() >> (8 * i)); }
        return f + p;
    };
    std::thread evt([&] {
        while (alive && ev) {
            std::this_thread::sleep_for(std::chrono::milliseconds(period_ms));
            std::lock_guard<std::mutex> l(tx);
            if (!send_all(c, frame(ev()))) alive = false;
        }
    });
    std::string buf;
    char tmp[4096];
    while (alive) {
        int n = recv(c, tmp, sizeof tmp, 0);
        if (n <= 0) break;
        buf.append(tmp, (size_t)n);
        while (buf.size() >= 2) {
            uint8_t b0 = (uint8_t)buf[0], b1 = (uint8_t)buf[1];
            size_t len = b1 & 0x7F, hdr = 2;
            if (len == 126) { if (buf.size() < 4) break; len = ((uint8_t)buf[2] << 8) | (uint8_t)buf[3]; hdr = 4; }
            else if (len == 127) { if (buf.size() < 10) break; len = 0; for (int i = 0; i < 8; i++) len = (len << 8) | (uint8_t)buf[2 + i]; hdr = 10; }
            bool masked = b1 & 0x80;
            size_t total = hdr + (masked ? 4 : 0) + len;
            if (buf.size() < total) break;
            std::string pl = buf.substr(hdr + (masked ? 4 : 0), len);
            if (masked) for (size_t i = 0; i < len; i++) pl[i] ^= buf[hdr + (i & 3)];
            buf.erase(0, total);
            uint8_t op = b0 & 0x0F;
            std::lock_guard<std::mutex> l(tx);
            if (op == 0x8) { send_all(c, frame("", 0x8)); alive = false; break; }
            if (op == 0x9) { send_all(c, frame(pl, 0xA)); continue; }
            if (op == 0x1) send_all(c, frame(ws(pl)));
        }
    }
    alive = false;
    evt.join();
    CLOSESOCK(c);
}

static void http_conn(sock_t c, HttpFn fn, WsFn ws, WsEventFn ev, int period)
{
    std::string buf;
    char tmp[4096];
    for (;;) {
        size_t he;
        while ((he = buf.find("\r\n\r\n")) == std::string::npos) {
            int n = recv(c, tmp, sizeof tmp, 0);
            if (n <= 0) { CLOSESOCK(c); return; }
            buf.append(tmp, (size_t)n);
        }
        std::string head = buf.substr(0, he);
        std::istringstream hs(head);
        std::string method, target, ver, line;
        hs >> method >> target >> ver;
        std::getline(hs, line);
        std::map<std::string, std::string> hdr;
        while (std::getline(hs, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            size_t k = line.find(':');
            if (k == std::string::npos) continue;
            std::string name = line.substr(0, k), val = line.substr(k + 1);
            while (!val.empty() && val[0] == ' ') val.erase(0, 1);
            for (char &ch : name) ch = (char)tolower(ch);
            hdr[name] = val;
        }
        size_t clen = hdr.count("content-length") ? (size_t)atol(hdr["content-length"].c_str()) : 0;
        while (buf.size() < he + 4 + clen) {
            int n = recv(c, tmp, sizeof tmp, 0);
            if (n <= 0) { CLOSESOCK(c); return; }
            buf.append(tmp, (size_t)n);
        }
        std::string body = buf.substr(he + 4, clen);
        buf.erase(0, he + 4 + clen);
        if (hdr.count("upgrade") && ws) {
            std::string acc = sha1_base64(hdr["sec-websocket-key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11");
            send_all(c, "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + acc + "\r\n\r\n");
            ws_session(c, ws, ev, period);
            return;
        }
        if (method == "OPTIONS") {   // CORS preflight from the apps' pages (file:// or the Windows window)
            std::string out = "HTTP/1.1 204 No Content\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, PUT, POST, OPTIONS\r\n"
                              "Access-Control-Allow-Headers: Content-Type\r\nAccess-Control-Max-Age: 600\r\nContent-Length: 0\r\nConnection: keep-alive\r\n\r\n";
            if (!send_all(c, out)) { CLOSESOCK(c); return; }
            continue;
        }
        st::HttpRequest r;
        r.method = method;
        size_t q = target.find('?');
        r.path = url_decode(target.substr(0, q));
        if (q != std::string::npos) parse_params(target.substr(q + 1), r.params);
        if (method == "PUT" || (method == "POST" && body.size() < 4096 && body.find('{') == std::string::npos)) parse_params(body, r.params);
        r.body = body;
        st::HttpResponse resp = fn(r);
        static const std::map<int, const char *> reason = {{200, "OK"}, {400, "Bad Request"}, {403, "Forbidden"}, {404, "Not Found"}, {405, "Method Not Allowed"}, {500, "Internal Server Error"}};
        std::string out = "HTTP/1.1 " + std::to_string(resp.status) + " " + (reason.count(resp.status) ? reason.at(resp.status) : "OK") +
                          "\r\nContent-Type: " + resp.type + "; charset=utf-8\r\nContent-Length: " + std::to_string(resp.body.size()) +
                          "\r\nAccess-Control-Allow-Origin: *\r\nConnection: keep-alive\r\n\r\n" + resp.body;
        if (!send_all(c, out)) { CLOSESOCK(c); return; }
    }
}

void serve_http(int port, HttpFn fn, WsFn ws, WsEventFn ev, int period)
{
    sock_t s = listen_tcp(port);
    std::thread([=] {
        for (;;) {
            sock_t c = accept(s, nullptr, nullptr);
            if (c < 0) continue;
            int one = 1;
            setsockopt(c, IPPROTO_TCP, TCP_NODELAY, (const char *)&one, sizeof one);
            std::thread(http_conn, c, fn, ws, ev, period).detach();
        }
    }).detach();
}

void serve_lx200_sessions(int port, std::function<void *()> make, std::function<std::string(void *, const std::string &)> feed)
{
    sock_t s = listen_tcp(port);
    std::thread([=] {
        for (;;) {
            sock_t c = accept(s, nullptr, nullptr);
            if (c < 0) continue;
            std::thread([=] {
                void *sess = make();
                char tmp[512];
                for (;;) {
                    int n = recv(c, tmp, sizeof tmp, 0);
                    if (n <= 0) break;
                    std::string out = feed(sess, std::string(tmp, (size_t)n));
                    if (!out.empty() && !send_all(c, out)) break;
                }
                CLOSESOCK(c);
            }).detach();
        }
    }).detach();
}

void serve_discovery(int udp_port, int alpaca_port)
{
    std::thread([=] {
        sock_t s = socket(AF_INET, SOCK_DGRAM, 0);
        int one = 1;
        setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (const char *)&one, sizeof one);
        setsockopt(s, SOL_SOCKET, SO_BROADCAST, (const char *)&one, sizeof one);
        sockaddr_in a{};
        a.sin_family = AF_INET;
        a.sin_addr.s_addr = htonl(INADDR_ANY);
        a.sin_port = htons((uint16_t)udp_port);
        if (bind(s, (sockaddr *)&a, sizeof a) != 0) { fprintf(stderr, "discovery: cannot bind UDP %d\n", udp_port); return; }
        char buf[256];
        for (;;) {
            sockaddr_in from{};
            socklen_t fl = sizeof from;
            int n = recvfrom(s, buf, sizeof buf - 1, 0, (sockaddr *)&from, &fl);
            if (n <= 0) continue;
            buf[n] = 0;
            if (strncmp(buf, st::Alpaca::DISCOVERY_QUERY, 16) == 0) {
                std::string r = st::Alpaca::discovery_reply(alpaca_port);
                sendto(s, r.data(), (int)r.size(), 0, (sockaddr *)&from, fl);
            }
        }
    }).detach();
}

}  // namespace net
