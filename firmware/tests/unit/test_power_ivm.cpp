// Pack-current budget (Phase 4 section 10.7 and the "Pack current" calculation) and the intervalometer.
#include "st_head.h"
#include "tst.h"
using namespace st;

TEST(power_budget_cases_from_phase4)
{
    PowerInputs in;
    in.pack_ok = true;
    in.pack_v = 6.0;
    in.soc = 50;
    // tracking (3 W) + camera at 27 W at 6.0 V: 5.27 A, inside 6 A -> no change to port B
    in.portb_w = 27;
    PowerDecision d = power_policy(in, 3.0);
    CHECK(!d.portb_15w);
    NOTE("6.0 V, camera 27 W: motion budget %.1f W", d.motion_budget_mw / 1000.0);
    CHECK_NEAR(d.motion_budget_mw / 1000.0, 6.0 * 6.0 - 1.2 - 27.0, 0.01);
    // slew peak (20.1 W) + camera 27 W at 6.0 V: over 6 A -> slew current lowered first; budget < 1/4 of peak -> port B to 15 W
    d = power_policy(in, 20.1);
    CHECK(d.portb_15w);
    CHECK_NEAR(d.motion_budget_mw / 1000.0, 36.0 - 1.2 - 15.0, 0.01);
    // at 7.2 V the same slew keeps port B at 27 W (budget 15.0 W = 75 % of peak: current scaled, no re-advertising)
    in.pack_v = 7.2;
    d = power_policy(in, 20.1);
    CHECK(!d.portb_15w);
    // low battery (D25): 5 % or 6.2 V
    in.soc = 5;
    CHECK(power_policy(in, 0).low_battery);
    in.soc = 40; in.pack_v = 6.1;
    CHECK(power_policy(in, 0).low_battery);
    in.charging = true;
    CHECK(!power_policy(in, 0).low_battery);
    in.inside_temp_c = 36;
    CHECK(power_policy(in, 0).charge_ma == 3000);
}

TEST(intervalometer_timing)
{
    Intervalometer iv;
    iv.count = 3; iv.exposure_s = 2; iv.interval_s = 3; iv.focus_s = 0.5;
    iv.start(100.0);
    iv.tick(100.2); CHECK(iv.focus && !iv.release);
    iv.tick(100.6); CHECK(iv.focus && iv.release);
    iv.tick(102.6); CHECK(!iv.focus && !iv.release);
    iv.tick(103.7); CHECK(iv.release && iv.done == 1);
    iv.tick(109.1); CHECK(!iv.running && iv.done == 3);
}
