// Star Tracker — persistent head data in plain files (D78). See st_filestore.h for the formats.
#include "st_filestore.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace st {

static void put_u32(std::vector<uint8_t> &b, uint32_t v) { for (int i = 0; i < 4; i++) b.push_back((uint8_t)(v >> (8 * i))); }
static uint32_t get_u32(const uint8_t *p) { return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24); }

bool FileStore::put(const std::string &key, const std::vector<int16_t> &v)
{
    std::vector<uint8_t> b = {'S', 'T', 'T', '1'};
    put_u32(b, (uint32_t)v.size());
    for (int16_t x : v) { b.push_back((uint8_t)(x & 0xFF)); b.push_back((uint8_t)((uint16_t)x >> 8)); }
    uint32_t sum = 0;
    for (uint8_t c : b) sum += c;
    put_u32(b, sum);
    std::string tmp = path(key + ".tmp"), dst = path(key + ".tbl");
    FILE *f = fopen(tmp.c_str(), "wb");
    if (!f) return false;
    bool ok = fwrite(b.data(), 1, b.size(), f) == b.size();
    ok = (fflush(f) == 0) && ok;
    ok = (fclose(f) == 0) && ok;
    if (!ok) { std::remove(tmp.c_str()); return false; }
    std::remove(dst.c_str());                    // Windows' rename does not replace; LittleFS and POSIX do either way
    return std::rename(tmp.c_str(), dst.c_str()) == 0;
}

bool FileStore::get(const std::string &key, std::vector<int16_t> &v)
{
    FILE *f = fopen(path(key + ".tbl").c_str(), "rb");
    if (!f) return false;
    std::vector<uint8_t> b;
    uint8_t buf[512];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) b.insert(b.end(), buf, buf + n);
    fclose(f);
    if (b.size() < 12 || memcmp(b.data(), "STT1", 4) != 0) return false;
    uint32_t count = get_u32(&b[4]);
    if (b.size() != 12 + 2ull * count) return false;
    uint32_t sum = 0;
    for (size_t i = 0; i < b.size() - 4; i++) sum += b[i];
    if (sum != get_u32(&b[b.size() - 4])) return false;
    v.resize(count);
    for (uint32_t i = 0; i < count; i++) v[i] = (int16_t)(b[8 + 2 * i] | (b[9 + 2 * i] << 8));
    return true;
}

bool FileStore::remove(const std::string &key) { return std::remove(path(key + ".tbl").c_str()) == 0; }

static std::string clean(const std::string &s)
{
    std::string o = s;
    for (char &c : o) if (c == '\t' || c == '\n' || c == '\r') c = ' ';
    return o;
}

bool FileStore::append_fault(const FaultEntry &e)
{
    FILE *f = fopen(path("faults.log").c_str(), "ab");
    if (!f) return false;
    int r = fprintf(f, "%lu\t%lld\t%d\t%s\n", (unsigned long)e.seq, (long long)e.t_us, e.level, clean(e.msg).c_str());
    bool ok = r > 0 && fclose(f) == 0;
    return ok;
}

std::vector<FaultEntry> FileStore::load_faults(size_t keep)
{
    std::vector<FaultEntry> out;
    FILE *f = fopen(path("faults.log").c_str(), "rb");
    if (!f) return out;
    char line[512];
    while (fgets(line, sizeof line, f)) {
        char *p = line, *end = nullptr;
        FaultEntry e;
        e.seq = (uint32_t)strtoul(p, &end, 10);
        if (end == p || *end != '\t') continue;
        p = end + 1;
        e.t_us = strtoll(p, &end, 10);
        if (end == p || *end != '\t') continue;
        p = end + 1;
        e.level = (int)strtol(p, &end, 10);
        if (end == p || *end != '\t') continue;
        e.msg = end + 1;
        while (!e.msg.empty() && (e.msg.back() == '\n' || e.msg.back() == '\r')) e.msg.pop_back();
        if (!out.empty() && e.seq <= out.back().seq) out.clear();   // a cleared-and-restarted log: keep the newest run
        out.push_back(e);
    }
    fclose(f);
    if (out.size() > keep) out.erase(out.begin(), out.end() - (long)keep);
    // compact: rewrite with only what is kept
    std::string tmp = path("faults.tmp");
    FILE *w = fopen(tmp.c_str(), "wb");
    if (w) {
        for (auto &e : out) fprintf(w, "%lu\t%lld\t%d\t%s\n", (unsigned long)e.seq, (long long)e.t_us, e.level, clean(e.msg).c_str());
        if (fclose(w) == 0) { std::remove(path("faults.log").c_str()); std::rename(tmp.c_str(), path("faults.log").c_str()); }
    }
    return out;
}

bool FileStore::clear_faults()
{
    std::remove(path("faults.log").c_str());
    return true;
}

}  // namespace st
