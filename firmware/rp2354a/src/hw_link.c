/* Star Tracker RP2354A — link UART0 (GPIO0 TX, GPIO1 RX) at 921 600 baud, interrupt-driven receive ring. */
#include "hw.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/uart.h"

#define RING 2048
static volatile uint8_t ring[RING];
static volatile uint16_t rw, rr;
static st_link_rx_t rx;
static uint8_t tx_seq;

static void uart_isr(void)
{
    while (uart_is_readable(uart0)) {
        uint8_t b = (uint8_t)uart_getc(uart0);
        uint16_t n = (uint16_t)((rw + 1) % RING);
        if (n != rr) { ring[rw] = b; rw = n; }
    }
}

void hw_link_init(st_link_frame_cb cb, void *ctx)
{
    uart_init(uart0, ST_LINK_BAUD);
    gpio_set_function(RP_GPIO_LINK_RX, GPIO_FUNC_UART);    /* net LINK_RX = RP2354A TX (GPIO0) */
    gpio_set_function(RP_GPIO_LINK_TX, GPIO_FUNC_UART);    /* net LINK_TX = RP2354A RX (GPIO1) */
    uart_set_fifo_enabled(uart0, true);
    irq_set_exclusive_handler(UART0_IRQ, uart_isr);
    irq_set_enabled(UART0_IRQ, true);
    uart_set_irq_enables(uart0, true, false);
    st_link_rx_init(&rx, cb, ctx);
}

void hw_link_poll(void)
{
    uint8_t buf[64];
    for (;;) {
        size_t n = 0;
        while (rr != rw && n < sizeof buf) { buf[n++] = ring[rr]; rr = (uint16_t)((rr + 1) % RING); }
        if (!n) break;
        st_link_rx_feed(&rx, buf, n);
    }
}

bool hw_link_send(uint8_t type, const void *payload, size_t len)
{
    uint8_t frame[ST_LINK_MAX_FRAME + 8];
    size_t n = st_link_build(type, tx_seq++, payload, len, frame);
    if (!n) return false;
    uart_write_blocking(uart0, frame, n);                  /* 260 bytes max = 2.8 ms at 921 600 */
    return true;
}

st_link_rx_t *hw_link_rx(void) { return &rx; }

void hw_led_init(void) { gpio_init(RP_GPIO_LED_RP); gpio_set_dir(RP_GPIO_LED_RP, GPIO_OUT); }
void hw_led_set(bool on) { gpio_put(RP_GPIO_LED_RP, on); }
