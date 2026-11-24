// Star Tracker — persistent head data in plain files (decision D78): PEC tables, encoder maps and the fault log.
// Portable C++17 over stdio, so the same code runs on the head (LittleFS mounted at /storage, partition "storage")
// and in the simulator (a folder given with --data). Settings stay in NVS on the head.
//
// Tables: <dir>/<key>.tbl = "STT1" | u32 count | count x int16 (little-endian) | u32 checksum (sum of the bytes).
//         Written to <key>.tmp first, then renamed, so a power cut never leaves half a table.
// Faults: <dir>/faults.log, one line per entry: seq \t t_us \t level \t message. Appended as faults happen; at start
//         the last FAULT_LOG_N entries are read back and the file is rewritten with only those.
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "st_head.h"

namespace st {

class FileStore {
public:
    explicit FileStore(std::string dir) : dir_(std::move(dir)) {}
    const std::string &dir() const { return dir_; }

    bool put(const std::string &key, const std::vector<int16_t> &v);
    bool get(const std::string &key, std::vector<int16_t> &v);   // false when missing or damaged
    bool remove(const std::string &key);

    bool append_fault(const FaultEntry &e);
    std::vector<FaultEntry> load_faults(size_t keep = FAULT_LOG_N);   // also compacts the file
    bool clear_faults();

private:
    std::string path(const std::string &name) const { return dir_ + "/" + name; }
    std::string dir_;
};

}  // namespace st
