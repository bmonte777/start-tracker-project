// Star Tracker ESP32-S3 — entry point: the bring-up menu or the system firmware (CONFIG_ST_BRINGUP).
#include "sdkconfig.h"
#include "st_bringup.h"
#include "st_app.h"

extern "C" void app_main(void)
{
#if CONFIG_ST_BRINGUP
    st::bringup_run();
#else
    st::app_run();
#endif
}
