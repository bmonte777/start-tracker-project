// Star Tracker ESP32-S3 — hardware layer. Pins and addresses only from st_board.h (generated from the schematic).
#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include "st_board.h"

namespace st {

// ---------------------------------------------------------------- I2C (new ESP-IDF i2c_master driver)
class I2CBus {
public:
    bool init(int port, int sda, int scl, uint32_t hz);
    bool probe(uint8_t addr);
    bool write(uint8_t addr, const uint8_t *data, size_t n);
    bool write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, size_t n);
    bool read_reg(uint8_t addr, uint8_t reg, uint8_t *buf, size_t n);
    uint32_t errors() const { return errors_; }
private:
    void *bus_ = nullptr;
    void *dev_[128] = {};
    uint32_t hz_ = 0;
    uint32_t errors_ = 0;
    void *dev(uint8_t addr);
};
extern I2CBus i2c_main;   // IO8/IO9, 400 kHz: PD controllers, magnetometer, OLED, clock, IMU
extern I2CBus i2c_pack;   // IO10/IO11, 100 kHz: battery gauge (SMBus)

// ---------------------------------------------------------------- TPS25751D (port A) / TPS25752A (port B)
// TI host interface (TPS25751 TRM SLVUCR8, section 3): registers are read with a leading byte count.
struct PdStatus {
    char mode[5] = "????";
    bool plug = false, source = false;   // plug present; power role (true = we source)
    uint8_t conn_state = 0;
    float contract_v = 0, contract_a = 0;  // from ACTIVE_PDO
    uint32_t boot_flags = 0;
    bool ok = false;
};
class PdController {
public:
    explicit PdController(uint8_t addr) : addr_(addr) {}
    uint8_t addr() const { return addr_; }
    bool read(uint8_t reg, uint8_t *buf, size_t n);         // strips the count byte
    bool write(uint8_t reg, const uint8_t *buf, size_t n);  // adds the count byte
    bool mode(char out[5]);
    int  cmd(const char *fourcc, const uint8_t *in, size_t nin, uint8_t *out, size_t nout, uint32_t timeout_ms = 1000);
    bool status(PdStatus &s);
    // remote I2C on the controller's own bus ('I2Cr' / 'I2Cw'), e.g. the BQ25792 behind port A
    bool remote_read(uint8_t addr7, uint8_t reg, uint8_t *buf, uint8_t n);
    bool remote_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, uint8_t n);
    // configuration image: patch load over I2C (PBMs/PBMc) and EEPROM write ('FLad'/'FLwd'/'FLvy')
    bool load_patch(const uint8_t *img, size_t n, std::string &log);
    bool write_eeprom(const uint8_t *img, size_t n, std::string &log);
    bool clear_irq();
private:
    uint8_t addr_;
};
extern PdController pd_a;   // 0x20
extern PdController pd_b;   // 0x21

// ---------------------------------------------------------------- BQ25792 charger (behind port A)
struct ChargerStatus { bool ok = false; uint8_t chg_stat = 0; uint16_t vbus_mv = 0, vbat_mv = 0, vsys_mv = 0; int16_t ibus_ma = 0, ibat_ma = 0; float tdie_c = 0; uint16_t ichg_ma = 0; };
bool charger_read(ChargerStatus &c);
bool charger_set_ichg(uint16_t ma);
const char *charger_state_name(uint8_t chg_stat);

// ---------------------------------------------------------------- BQ40Z50-R2 gauge (SMBus 0x0B)
struct PackStatus {
    bool ok = false;
    uint16_t mv = 0, cell1_mv = 0, cell2_mv = 0, rem_mah = 0, full_mah = 0, design_mah = 0, cycles = 0, batt_status = 0;
    int16_t ma = 0, avg_ma = 0;
    uint8_t soc = 0, soh = 0;
    float temp_c = 0;
    uint16_t tte_min = 0xFFFF, ttf_min = 0xFFFF;
    uint32_t safety_status = 0, op_status = 0;
};
bool gauge_read(PackStatus &p);
bool gauge_mac_read(uint16_t cmd, uint8_t *buf, size_t n);

// ---------------------------------------------------------------- MAX-M10S GNSS (UART2 IO47 RX / IO48 TX, PPS IO15)
struct GnssFix {
    bool time_valid = false, fix = false;
    uint8_t num_sv = 0, fix_type = 0;
    double lat = 0, lon = 0, h_msl = 0;
    int64_t unix_us_at_pps = 0;     // UTC of the last PPS edge
    int64_t local_us_at_pps = 0;    // esp_timer time of that edge
    uint32_t pps_count = 0, bytes = 0, nav_pvt = 0;
    float tacc_ns = 0;
};
void gnss_init();
void gnss_poll();                    // parse UART bytes; call often
const GnssFix &gnss();
void gnss_backup();                  // UBX-RXM-PMREQ software backup (V_BCKP is tied to the 3.3 V feed)

// ---------------------------------------------------------------- RV-3028 clock
bool rtc_get_unix(uint32_t &t);
bool rtc_set_unix(uint32_t t);
bool rtc_setup_backup(std::string &log);   // switchover + trickle charge for the MS621FE (D52)
bool rtc_set_wake(uint32_t seconds);
uint8_t rtc_backup_reg();

// ---------------------------------------------------------------- LSM6DSV IMU and MMC5983MA magnetometer
struct Vec3 { float x = 0, y = 0, z = 0; };
bool imu_init();
bool imu_read(Vec3 &acc_g, float &temp_c);
bool mag_init();
bool mag_read(Vec3 &gauss);

// ---------------------------------------------------------------- SH1106 OLED 128x64
class Oled {
public:
    bool init();
    void clear();
    void text(int col, int row, const char *s, bool inverse = false);   // 21 x 8 characters (6x8 font)
    void hline(int row_px);
    void bar(int x, int y, int w, int h, int pct);
    bool flush();
    void contrast(uint8_t c);
    void power(bool on);
private:
    uint8_t fb_[8][128] = {};
    bool ok_ = false;
};
extern Oled oled;

// ---------------------------------------------------------------- simple I/O
enum class Led { R, G, B };
void io_init();
void led_set(Led l, uint8_t level);      // 0..255, LEDC PWM
int  buttons();                          // bit0..3 = BTN1..4 pressed (debounced)
void shutter_focus(bool on);
void shutter_release(bool on);
void portb_enable(bool on);
void rp_reset(bool hold);                // RP_RUN low = reset
float vsys_volts();
void link_sync_pulse();                  // LINK_SYNC high 20 us
int64_t pps_last_local_us();
uint32_t pps_edges();

}  // namespace st
