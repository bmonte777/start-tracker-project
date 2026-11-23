/* Star Tracker RP2354A — MT6835 encoders on SPI1 (mode 3), shared MISO, one chip select per axis.
 * Protocol (MagnTek MT6835 datasheet rev 1.3, 7.6): 24-bit frames of command[4] | address[12] | data[8].
 *   read register 0x3, write 0x6, program EEPROM 0xC, auto-zero 0x5, burst-read angle 0xA from 0x003.
 *   0x003 ANGLE[20:13], 0x004 ANGLE[12:5], 0x005 ANGLE[4:0] | STATUS[2:0], 0x006 CRC[7:0]
 *   STATUS bit0 over-speed, bit1 weak field, bit2 under-voltage. CRC-8 x^8+x^2+x+1 over the 24 bits.
 */
#include "hw.h"
#include "hardware/gpio.h"
#include "hardware/spi.h"

static const uint CS_PIN[ST_AXES] = {RP_GPIO_CS_AZ_M, RP_GPIO_CS_ALT_M, RP_GPIO_CS_ROLL_M};

void hw_enc_init(uint32_t baud)
{
    spi_init(spi1, baud);                                  /* 8 MHz to start (hand-off 10.3) */
    spi_set_format(spi1, 8, SPI_CPOL_1, SPI_CPHA_1, SPI_MSB_FIRST);
    gpio_set_function(RP_GPIO_ENC_SCK_M, GPIO_FUNC_SPI);
    gpio_set_function(RP_GPIO_ENC_MOSI_M, GPIO_FUNC_SPI);
    gpio_set_function(RP_GPIO_ENC_MISO, GPIO_FUNC_SPI);
    gpio_pull_up(RP_GPIO_ENC_MISO);                        /* idle high when no chip drives it */
    for (int i = 0; i < ST_AXES; i++) {
        gpio_init(CS_PIN[i]);
        gpio_put(CS_PIN[i], 1);
        gpio_set_dir(CS_PIN[i], GPIO_OUT);
    }
}

uint8_t hw_enc_crc8(const uint8_t *p, int n)
{
    uint8_t crc = 0x00;
    for (int i = 0; i < n; i++) {
        crc ^= p[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
    }
    return crc;
}

static void xfer(int axis, const uint8_t *tx, uint8_t *rx, size_t n)
{
    gpio_put(CS_PIN[axis], 0);
    spi_write_read_blocking(spi1, tx, rx, n);
    gpio_put(CS_PIN[axis], 1);
}

bool hw_enc_read(int axis, enc_sample_t *s)
{
    const uint8_t tx[6] = {0xA0, 0x03, 0, 0, 0, 0};       /* burst read from 0x003 */
    uint8_t rx[6];
    xfer(axis, tx, rx, 6);
    const uint8_t *d = rx + 2;
    s->raw = ((uint32_t)d[0] << 13) | ((uint32_t)d[1] << 5) | (d[2] >> 3);
    s->status = d[2] & 0x07;
    s->crc_ok = hw_enc_crc8(d, 3) == d[3];
    /* all-ones = nobody answered (MISO pulled up): treat as a CRC failure */
    if (d[0] == 0xFF && d[1] == 0xFF && d[2] == 0xFF && d[3] == 0xFF) s->crc_ok = false;
    return s->crc_ok;
}

bool hw_enc_reg_read(int axis, uint16_t reg, uint8_t *val)
{
    uint8_t tx[3] = {(uint8_t)(0x30 | ((reg >> 8) & 0x0F)), (uint8_t)reg, 0}, rx[3];
    xfer(axis, tx, rx, 3);
    *val = rx[2];
    return true;
}

bool hw_enc_reg_write(int axis, uint16_t reg, uint8_t val)
{
    uint8_t tx[3] = {(uint8_t)(0x60 | ((reg >> 8) & 0x0F)), (uint8_t)reg, val}, rx[3];
    xfer(axis, tx, rx, 3);
    uint8_t back = 0;
    hw_enc_reg_read(axis, reg, &back);
    return back == val;
}
