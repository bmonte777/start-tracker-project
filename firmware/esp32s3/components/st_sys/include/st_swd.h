// Star Tracker ESP32-S3 — RP2354A programmer over SWD.
#pragma once
#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>

namespace st {
class SwdFlasher {
public:
    bool connect(std::string &log);
    bool flash(const uint8_t *stub, size_t stub_n, const uint8_t *img, size_t n, std::function<void(int)> progress, std::string &log);
private:
    bool connected_ = false;
};
extern SwdFlasher swd;
}  // namespace st
