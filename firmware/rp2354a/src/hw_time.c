/* Star Tracker RP2354A — head time. LINK_SYNC (GPIO2) and GNSS 1 PPS (GPIO3) rising edges are time-stamped in
 * a GPIO interrupt against the 1 MHz system timer. Each TIMESYNC message pairs the last LINK_SYNC edge with its
 * head time; head = a + b x local is fitted over the last 16 pairs (b tracks the crystal's drift). */
#include "hw.h"
#include <string.h>
#include "hardware/gpio.h"
#include "hardware/sync.h"
#include "pico/time.h"

#define NPAIR 16
static volatile uint64_t sync_local, pps_local, pps_prev;
static volatile uint32_t pps_count;
static double pl[NPAIR], ph[NPAIR];
static int npair, ipair;
static volatile double fit_a, fit_b = 1.0;           /* head = fit_a + fit_b * (local - local0) */
static volatile uint64_t local0;
static volatile uint32_t fit_seq;
static double ppm;

static void edge_isr(uint gpio, uint32_t events)
{
    uint64_t t = time_us_64();
    (void)events;
    if (gpio == RP_GPIO_LINK_SYNC) sync_local = t;
    else if (gpio == RP_GPIO_GNSS_PPS) {
        if (pps_local) {
            uint64_t d = t - pps_local;
            if (d > 999000 && d < 1001000) ppm = ((double)d - 1e6);   /* us per second = ppm */
        }
        pps_prev = pps_local;
        pps_local = t;
        pps_count++;
    }
}

void hw_time_init(void)
{
    gpio_init(RP_GPIO_LINK_SYNC);
    gpio_set_dir(RP_GPIO_LINK_SYNC, GPIO_IN);
    gpio_pull_down(RP_GPIO_LINK_SYNC);
    gpio_init(RP_GPIO_GNSS_PPS);
    gpio_set_dir(RP_GPIO_GNSS_PPS, GPIO_IN);
    gpio_set_irq_enabled_with_callback(RP_GPIO_LINK_SYNC, GPIO_IRQ_EDGE_RISE, true, edge_isr);
    gpio_set_irq_enabled(RP_GPIO_GNSS_PPS, GPIO_IRQ_EDGE_RISE, true);
    local0 = time_us_64();
    fit_a = (double)local0;                               /* until synced, head time = local time */
}

void hw_time_on_timesync(const st_timesync_t *ts)
{
    uint64_t sl = sync_local;
    if (!sl) return;
    if (npair == 0) local0 = sl;
    pl[ipair] = (double)(int64_t)(sl - local0);
    ph[ipair] = (double)ts->t_edge_us;
    ipair = (ipair + 1) % NPAIR;
    if (npair < NPAIR) npair++;
    /* least squares h = a + b l, centred for precision */
    double ml = 0, mh = 0;
    for (int i = 0; i < npair; i++) { ml += pl[i]; mh += ph[i] - ph[0]; }
    ml /= npair; mh /= npair;
    double sxy = 0, sxx = 0;
    for (int i = 0; i < npair; i++) { double dx = pl[i] - ml; sxx += dx * dx; sxy += dx * ((ph[i] - ph[0]) - mh); }
    double b = (npair >= 2 && sxx > 0) ? sxy / sxx : 1.0;
    if (b < 0.9999 || b > 1.0001) b = 1.0;                /* reject nonsense (> 100 ppm) */
    double a = ph[0] + mh - b * ml;
    uint32_t irq = save_and_disable_interrupts();
    fit_seq++;
    fit_a = a;
    fit_b = b;
    fit_seq++;
    restore_interrupts(irq);
}

uint64_t hw_head_from_local(uint64_t local_us)
{
    double a, b;
    uint64_t l0;
    uint32_t s;
    do { s = fit_seq; a = fit_a; b = fit_b; l0 = local0; } while (s != fit_seq || (s & 1));
    return (uint64_t)(a + b * (double)(int64_t)(local_us - l0));
}

uint64_t hw_head_us(void) { return hw_head_from_local(time_us_64()); }
double hw_time_ppm(void) { return ppm; }
uint32_t hw_time_pps_count(void) { return pps_count; }
