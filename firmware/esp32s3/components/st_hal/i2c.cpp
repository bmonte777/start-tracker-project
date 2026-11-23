// Star Tracker ESP32-S3 — I2C buses on the ESP-IDF 5.x i2c_master driver.
#include <cstring>
#include "driver/i2c_master.h"
#include "st_hal.h"

namespace st {

I2CBus i2c_main, i2c_pack;

bool I2CBus::init(int port, int sda, int scl, uint32_t hz)
{
    i2c_master_bus_config_t cfg = {};
    cfg.i2c_port = port;
    cfg.sda_io_num = (gpio_num_t)sda;
    cfg.scl_io_num = (gpio_num_t)scl;
    cfg.clk_source = I2C_CLK_SRC_DEFAULT;
    cfg.glitch_ignore_cnt = 7;
    cfg.flags.enable_internal_pullup = false;     // 2.2 k (main) and 4.7 k (pack) on the board
    i2c_master_bus_handle_t h;
    if (i2c_new_master_bus(&cfg, &h) != ESP_OK) return false;
    bus_ = h;
    hz_ = hz;
    return true;
}

void *I2CBus::dev(uint8_t addr)
{
    if (!bus_ || addr > 127) return nullptr;
    if (!dev_[addr]) {
        i2c_device_config_t d = {};
        d.dev_addr_length = I2C_ADDR_BIT_LEN_7;
        d.device_address = addr;
        d.scl_speed_hz = hz_;
        i2c_master_dev_handle_t h;
        if (i2c_master_bus_add_device((i2c_master_bus_handle_t)bus_, &d, &h) != ESP_OK) return nullptr;
        dev_[addr] = h;
    }
    return dev_[addr];
}

bool I2CBus::probe(uint8_t addr) { return bus_ && i2c_master_probe((i2c_master_bus_handle_t)bus_, addr, 20) == ESP_OK; }

bool I2CBus::write(uint8_t addr, const uint8_t *data, size_t n)
{
    for (int attempt = 0; attempt < 3; attempt++) {
        auto h = (i2c_master_dev_handle_t)dev(addr);
        if (h && i2c_master_transmit(h, data, n, 50) == ESP_OK) return true;
    }
    errors_++;
    return false;
}

bool I2CBus::write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, size_t n)
{
    uint8_t buf[80];
    if (n + 1 > sizeof buf) return false;
    buf[0] = reg;
    if (n) memcpy(buf + 1, data, n);
    return write(addr, buf, n + 1);
}

bool I2CBus::read_reg(uint8_t addr, uint8_t reg, uint8_t *buf, size_t n)
{
    for (int attempt = 0; attempt < 3; attempt++) {
        auto h = (i2c_master_dev_handle_t)dev(addr);
        if (h && i2c_master_transmit_receive(h, &reg, 1, buf, n, 50) == ESP_OK) return true;
    }
    errors_++;
    return false;
}

}  // namespace st
