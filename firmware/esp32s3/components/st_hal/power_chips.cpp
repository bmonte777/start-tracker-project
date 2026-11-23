// Star Tracker ESP32-S3 — TPS25751D / TPS25752A PD controllers, the BQ25792 charger behind port A, BQ40Z50-R2 gauge.
//
// Sources:
//  TPS25751 Technical Reference Manual SLVUCR8B (register map 3.2; 4CC tasks 4.x: I2Cr, I2Cw, PBMs, PBMc, PBMe, FLad,
//    FLwd, FLvy; MODE values 'APP ', 'BOOT', 'PTCH'); TPS25750 patch-loading note SLVAFV8 (PBMs DATA1 layout).
//  BQ25792 datasheet SLUSE22 (REG03 ICHG, REG1C charger status, REG2E ADC control, REG31.. ADC results).
//  BQ40Z50-R2 TRM SLUUBK0 (SBS commands 0x08-0x4F, ManufacturerBlockAccess 0x44).
#include <cstring>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "st_hal.h"

namespace st {

PdController pd_a(I2C_ADDR_TPS25751), pd_b(I2C_ADDR_TPS25752);

enum : uint8_t {
    PD_MODE = 0x03, PD_CMD1 = 0x08, PD_DATA1 = 0x09, PD_INT_EVENT1 = 0x14, PD_INT_CLEAR1 = 0x18,
    PD_STATUS = 0x1A, PD_POWER_PATH = 0x26, PD_BOOT_FLAGS = 0x2D, PD_ACTIVE_PDO = 0x34, PD_ACTIVE_RDO = 0x35,
};

bool PdController::read(uint8_t reg, uint8_t *buf, size_t n)
{
    uint8_t tmp[66];
    if (n + 1 > sizeof tmp) return false;
    if (!i2c_main.read_reg(addr_, reg, tmp, n + 1)) return false;
    size_t got = tmp[0] < n ? tmp[0] : n;
    memset(buf, 0, n);
    memcpy(buf, tmp + 1, got);
    return true;
}

bool PdController::write(uint8_t reg, const uint8_t *buf, size_t n)
{
    uint8_t tmp[66];
    if (n + 1 > sizeof tmp) return false;
    tmp[0] = (uint8_t)n;
    memcpy(tmp + 1, buf, n);
    return i2c_main.write_reg(addr_, reg, tmp, n + 1);
}

bool PdController::mode(char out[5])
{
    uint8_t m[4];
    if (!read(PD_MODE, m, 4)) { strcpy(out, "----"); return false; }
    memcpy(out, m, 4);
    out[4] = 0;
    return true;
}

// Returns -1 on bus error, -2 on '!CMD' (unknown task), -3 on timeout, else DATA1 byte 1 (task return code).
int PdController::cmd(const char *fourcc, const uint8_t *in, size_t nin, uint8_t *out, size_t nout, uint32_t timeout_ms)
{
    if (nin && !write(PD_DATA1, in, nin)) return -1;
    if (!write(PD_CMD1, (const uint8_t *)fourcc, 4)) return -1;
    TickType_t end = xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);
    uint8_t c[4];
    do {
        vTaskDelay(pdMS_TO_TICKS(2));
        if (!read(PD_CMD1, c, 4)) return -1;
        if (!memcmp(c, "!CMD", 4)) return -2;
        if (!c[0] && !c[1] && !c[2] && !c[3]) {
            uint8_t d[64] = {};
            size_t want = nout > 0 ? (nout < 64 ? nout : 64) : 1;
            if (!read(PD_DATA1, d, want)) return -1;
            if (out && nout) memcpy(out, d, want);
            return d[0] & 0x0F;
        }
    } while (xTaskGetTickCount() < end);
    return -3;
}

bool PdController::status(PdStatus &s)
{
    s.ok = mode(s.mode);
    if (!s.ok) return false;
    uint8_t st[5] = {}, bf[5] = {};
    read(PD_BOOT_FLAGS, bf, 5);
    s.boot_flags = bf[0] | (bf[1] << 8) | (bf[2] << 16) | ((uint32_t)bf[3] << 24);
    if (strcmp(s.mode, "APP ") != 0) return true;       // only MODE, CMD, DATA, INT and BOOT_FLAGS outside APP
    if (read(PD_STATUS, st, 5)) {
        s.plug = st[0] & 0x01;                           // PlugPresent
        s.conn_state = (st[0] >> 1) & 0x07;              // ConnState
        s.source = (st[0] >> 5) & 0x01;                  // PortRole: 1 = source
    }
    uint8_t pdo[6] = {};
    if (s.plug && read(PD_ACTIVE_PDO, pdo, 6)) {
        uint32_t p = pdo[0] | (pdo[1] << 8) | (pdo[2] << 16) | ((uint32_t)pdo[3] << 24);
        if ((p >> 30) == 0) {                            // fixed supply PDO (USB PD 3.x)
            s.contract_v = ((p >> 10) & 0x3FF) * 0.05f;
            s.contract_a = (p & 0x3FF) * 0.01f;
        }
    }
    return true;
}

bool PdController::clear_irq()
{
    uint8_t ones[11];
    memset(ones, 0xFF, sizeof ones);
    return write(PD_INT_CLEAR1, ones, sizeof ones);
}

bool PdController::remote_read(uint8_t addr7, uint8_t reg, uint8_t *buf, uint8_t n)
{
    uint8_t in[3] = {addr7, reg, n}, out[65];
    int r = cmd("I2Cr", in, 3, out, (size_t)n + 1);
    if (r != 0) return false;
    memcpy(buf, out + 1, n);
    return true;
}

bool PdController::remote_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, uint8_t n)
{
    if (n > 11) return false;
    uint8_t in[14] = {addr7, n, reg};
    memcpy(in + 3, buf, n);
    return cmd("I2Cw", in, (size_t)3 + n, nullptr, 1) == 0;
}

// Patch bundle over I2C (TRM 5.2 "Loading a Patch Bundle"): only accepted in 'PTCH' / 'BOOT' mode.
bool PdController::load_patch(const uint8_t *img, size_t n, std::string &log)
{
    char m[5];
    mode(m);
    if (!strcmp(m, "APP ")) { log += "controller already in APP mode; no patch needed\n"; return true; }
    const uint8_t burst_addr = 0x30;                     // second target address used only during the burst
    uint8_t in[6] = {(uint8_t)n, (uint8_t)(n >> 8), (uint8_t)(n >> 16), (uint8_t)(n >> 24), burst_addr, 0x32};  // 5 s timeout
    uint8_t out[4];
    int r = cmd("PBMs", in, 6, out, 1);
    if (r != 0) { log += "PBMs rejected\n"; return false; }
    vTaskDelay(pdMS_TO_TICKS(10));
    for (size_t off = 0; off < n; off += 64) {           // raw burst writes to the second address
        size_t k = n - off < 64 ? n - off : 64;
        if (!i2c_main.write(burst_addr, img + off, k)) { log += "burst write failed\n"; cmd("PBMe", nullptr, 0, nullptr, 1); return false; }
    }
    vTaskDelay(pdMS_TO_TICKS(20));
    uint8_t res[40];
    r = cmd("PBMc", nullptr, 0, res, 40, 3000);
    mode(m);
    log += std::string("PBMc result ") + std::to_string(res[0]) + ", mode now '" + m + "'\n";
    return !strcmp(m, "APP ");
}

// EEPROM write through the controller (TRM 4.x 'FLad' / 'FLwd' / 'FLvy'), 32-byte chunks (EEPROM page size).
bool PdController::write_eeprom(const uint8_t *img, size_t n, std::string &log)
{
    uint8_t a[4] = {0, 0, 0, 0}, out[2];
    if (cmd("FLad", a, 4, out, 1) != 0) { log += "FLad failed\n"; return false; }
    for (size_t off = 0; off < n; off += 32) {
        size_t k = n - off < 32 ? n - off : 32;
        uint8_t ret[1];
        if (cmd("FLwd", img + off, k, ret, 1, 2000) < 0 || ret[0] != 0) { log += "FLwd failed at " + std::to_string(off) + "\n"; return false; }
    }
    uint8_t v[1];
    if (cmd("FLvy", a, 4, v, 1, 3000) < 0 || v[0] != 0) { log += "FLvy: image not valid\n"; return false; }
    log += "EEPROM written and verified (" + std::to_string(n) + " bytes)\n";
    return true;
}

// ---------------------------------------------------------------- BQ25792 behind port A (address 0x6B)
static bool chg_rd16(uint8_t reg, uint16_t &v)
{
    uint8_t b[2];
    if (!pd_a.remote_read(PDA_ADDR_BQ25792, reg, b, 2)) return false;
    v = (uint16_t)((b[0] << 8) | b[1]);                  // BQ25792 16-bit registers: MSB at the lower address
    return true;
}

bool charger_read(ChargerStatus &c)
{
    uint8_t adc = 0x80;                                  // REG2E ADC_EN = 1, continuous
    pd_a.remote_write(PDA_ADDR_BQ25792, 0x2E, &adc, 1);
    uint8_t s1 = 0;
    if (!pd_a.remote_read(PDA_ADDR_BQ25792, 0x1C, &s1, 1)) { c.ok = false; return false; }
    c.chg_stat = (s1 >> 5) & 0x07;                       // REG1C CHG_STAT[2:0]
    uint16_t v;
    if (chg_rd16(0x31, v)) c.ibus_ma = (int16_t)v;       // IBUS_ADC, 1 mA
    if (chg_rd16(0x33, v)) c.ibat_ma = (int16_t)v;       // IBAT_ADC, 1 mA
    if (chg_rd16(0x35, v)) c.vbus_mv = v;                // VBUS_ADC, 1 mV
    if (chg_rd16(0x3B, v)) c.vbat_mv = v;                // VBAT_ADC
    if (chg_rd16(0x3D, v)) c.vsys_mv = v;                // VSYS_ADC
    if (chg_rd16(0x41, v)) c.tdie_c = (int16_t)v * 0.5f; // TDIE_ADC, 0.5 C
    if (chg_rd16(0x03, v)) c.ichg_ma = (uint16_t)((v & 0x01FF) * 10);   // REG03 ICHG, 10 mA
    c.ok = true;
    return true;
}

bool charger_set_ichg(uint16_t ma)
{
    uint16_t code = ma / 10;
    uint8_t b[2] = {(uint8_t)(code >> 8), (uint8_t)code};
    return pd_a.remote_write(PDA_ADDR_BQ25792, 0x03, b, 2);
}

const char *charger_state_name(uint8_t s)
{
    static const char *n[8] = {"not charging", "trickle", "pre-charge", "fast (CC)", "taper (CV)", "-", "top-off", "done"};
    return n[s & 7];
}

// ---------------------------------------------------------------- BQ40Z50-R2 (SMBus 0x0B, 100 kHz)
static bool sbs16(uint8_t cmd, uint16_t &v)
{
    uint8_t b[2];
    if (!i2c_pack.read_reg(SMB_ADDR_BQ40Z50, cmd, b, 2)) return false;
    v = (uint16_t)(b[0] | (b[1] << 8));                  // SMBus words are little-endian
    return true;
}

bool gauge_mac_read(uint16_t mac, uint8_t *buf, size_t n)
{
    uint8_t w[3] = {2, (uint8_t)mac, (uint8_t)(mac >> 8)};          // block write: count, command LE
    if (!i2c_pack.write_reg(SMB_ADDR_BQ40Z50, 0x44, w, 3)) return false;
    uint8_t r[36];
    if (!i2c_pack.read_reg(SMB_ADDR_BQ40Z50, 0x44, r, n + 3 > sizeof r ? sizeof r : n + 3)) return false;
    // r[0] = count, r[1..2] = echo of the command, then data
    if (r[1] != (uint8_t)mac || r[2] != (uint8_t)(mac >> 8)) return false;
    memcpy(buf, r + 3, n);
    return true;
}

bool gauge_read(PackStatus &p)
{
    uint16_t v;
    p.ok = sbs16(0x09, v);                               // Voltage, mV
    if (!p.ok) return false;
    p.mv = v;
    if (sbs16(0x0A, v)) p.ma = (int16_t)v;               // Current, mA (+ = charging)
    if (sbs16(0x0B, v)) p.avg_ma = (int16_t)v;           // AverageCurrent
    if (sbs16(0x08, v)) p.temp_c = v * 0.1f - 273.15f;   // Temperature, 0.1 K
    if (sbs16(0x0D, v)) p.soc = (uint8_t)v;              // RelativeStateOfCharge, %
    if (sbs16(0x0F, v)) p.rem_mah = v;                   // RemainingCapacity
    if (sbs16(0x10, v)) p.full_mah = v;                  // FullChargeCapacity
    if (sbs16(0x12, v)) p.tte_min = v;                   // AverageTimeToEmpty
    if (sbs16(0x13, v)) p.ttf_min = v;                   // AverageTimeToFull
    if (sbs16(0x16, v)) p.batt_status = v;               // BatteryStatus
    if (sbs16(0x17, v)) p.cycles = v;                    // CycleCount
    if (sbs16(0x18, v)) p.design_mah = v;                // DesignCapacity
    if (sbs16(0x3F, v)) p.cell1_mv = v;                  // CellVoltage1
    if (sbs16(0x3E, v)) p.cell2_mv = v;                  // CellVoltage2
    if (sbs16(0x4F, v)) p.soh = (uint8_t)v;              // StateOfHealth
    uint8_t b[4];
    if (gauge_mac_read(0x0051, b, 4)) p.safety_status = b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24);
    if (gauge_mac_read(0x0054, b, 4)) p.op_status = b[0] | (b[1] << 8) | (b[2] << 16) | ((uint32_t)b[3] << 24);
    return true;
}

}  // namespace st
