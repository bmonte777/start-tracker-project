/* Star Tracker — RP2354A flash loader, loaded into SRAM over SWD by the ESP32-S3 (firmware/esp32s3/components/st_sys/swd.cpp).
 * Runs from RAM (no_flash binary at 0x20000000). The ESP32 writes data to BUF and a command to the mailbox, then
 * polls the status. Uses the SDK flash functions, which call the RP2350 bootrom (connect, exit XIP, erase, program,
 * flush cache, re-enter XIP). */
#include <string.h>
#include "hardware/flash.h"
#include "hardware/structs/watchdog.h"
#include "hardware/sync.h"
#include "pico/stdlib.h"

#define MBOX ((volatile stub_mbox_t *)0x20060000u)
#define BUF  ((uint8_t *)0x20040000u)              /* 128 KB data buffer */
#define MAGIC 0x4C465453u                           /* 'STFL' */

typedef struct { uint32_t magic, cmd, addr, len, status, result, version; } stub_mbox_t;
enum { CMD_IDLE = 0, CMD_ERASE = 1, CMD_PROGRAM = 2, CMD_CRC = 3 };
enum { ST_BUSY = 0, ST_OK = 1, ST_ERR = 2, ST_READY = 3 };

static uint32_t crc32(const uint8_t *p, uint32_t n)
{
    uint32_t c = 0xFFFFFFFFu;
    while (n--) { c ^= *p++; for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u))); }
    return ~c;
}

int main(void)
{
    hw_clear_bits(&watchdog_hw->ctrl, WATCHDOG_CTRL_ENABLE_BITS);   /* the motion image had armed it */
    MBOX->cmd = CMD_IDLE;
    MBOX->version = 1;
    MBOX->magic = MAGIC;
    MBOX->status = ST_READY;
    for (;;) {
        uint32_t cmd = MBOX->cmd;
        if (cmd == CMD_IDLE) continue;
        uint32_t a = MBOX->addr, n = MBOX->len;
        MBOX->status = ST_BUSY;
        uint32_t irq = save_and_disable_interrupts();
        bool ok = true;
        if (cmd == CMD_ERASE) {
            if ((a % FLASH_SECTOR_SIZE) || (n % FLASH_SECTOR_SIZE) || a + n > PICO_FLASH_SIZE_BYTES) ok = false;
            else flash_range_erase(a, n);
        } else if (cmd == CMD_PROGRAM) {
            if ((a % FLASH_PAGE_SIZE) || (n % FLASH_PAGE_SIZE) || n > 0x20000 || a + n > PICO_FLASH_SIZE_BYTES) ok = false;
            else flash_range_program(a, BUF, n);
        } else if (cmd == CMD_CRC) {
            if (a + n > PICO_FLASH_SIZE_BYTES) ok = false;
            else MBOX->result = crc32((const uint8_t *)(XIP_BASE + a), n);
        } else ok = false;
        restore_interrupts(irq);
        MBOX->cmd = CMD_IDLE;
        MBOX->status = ok ? ST_OK : ST_ERR;
    }
}
