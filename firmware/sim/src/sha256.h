// Star Tracker simulator — SHA-256 (FIPS 180-4), for checking update bundles the way the head does (ota.cpp).
#pragma once
#include <cstdint>
#include <cstring>
#include <string>

namespace sim {

inline void sha256(const uint8_t *data, size_t len, uint8_t out[32])
{
    static const uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be,
        0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa,
        0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85,
        0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f,
        0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    auto rr = [](uint32_t x, int n) { return (x >> n) | (x << (32 - n)); };
    uint64_t bits = (uint64_t)len * 8;
    size_t total = ((len + 9 + 63) / 64) * 64;
    uint8_t blk[64];
    for (size_t off = 0; off < total; off += 64) {
        for (int i = 0; i < 64; i++) {
            size_t p = off + i;
            if (p < len) blk[i] = data[p];
            else if (p == len) blk[i] = 0x80;
            else if (p >= total - 8) blk[i] = (uint8_t)(bits >> (8 * (total - 1 - p)));
            else blk[i] = 0;
        }
        uint32_t w[64];
        for (int i = 0; i < 16; i++) w[i] = (uint32_t)blk[4 * i] << 24 | (uint32_t)blk[4 * i + 1] << 16 | (uint32_t)blk[4 * i + 2] << 8 | blk[4 * i + 3];
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = rr(w[i - 15], 7) ^ rr(w[i - 15], 18) ^ (w[i - 15] >> 3), s1 = rr(w[i - 2], 17) ^ rr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
        for (int i = 0; i < 64; i++) {
            uint32_t t1 = hh + (rr(e, 6) ^ rr(e, 11) ^ rr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i];
            uint32_t t2 = (rr(a, 2) ^ rr(a, 13) ^ rr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
            hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }
    for (int i = 0; i < 8; i++) for (int j = 0; j < 4; j++) out[4 * i + j] = (uint8_t)(h[i] >> (24 - 8 * j));
}

// Check a .stfw bundle exactly as ota.cpp does; returns "" or the head's error text.
inline std::string check_bundle(const std::string &b, std::string &summary)
{
    if (b.size() < 64 || memcmp(b.data(), "STFW", 4) != 0) return "not a Canopus bundle";
    uint32_t ver, entries;
    memcpy(&ver, b.data() + 4, 4);
    memcpy(&entries, b.data() + 8, 4);
    if (ver != 1 || entries == 0 || entries > 2) return "not a Canopus bundle";
    summary.clear();
    for (uint32_t i = 0; i < entries; i++) {
        const uint8_t *p = (const uint8_t *)b.data() + 16 + 24 * i;
        uint32_t off, size;
        memcpy(&off, p + 4, 4);
        memcpy(&size, p + 8, 4);
        if ((uint64_t)off + size > b.size() || size == 0) return "update failed; nothing changed";
        if (p[0] == 2 && size > 0x7F000) return "update failed; nothing changed";
        uint8_t dig[32];
        sha256((const uint8_t *)b.data() + off, size, dig);
        if (memcmp(dig, p + 12, 12) != 0) return "update failed; nothing changed";
        summary += (p[0] == 1 ? "ESP32-S3 " : "RP2354A ") + std::to_string(size) + " bytes; ";
    }
    return "";
}

}  // namespace sim
