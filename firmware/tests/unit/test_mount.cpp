// Kinematics, roll de-rotation and the pointing-model fit.
#include <random>
#include "st_mount.h"
#include "tst.h"
using namespace st;

TEST(mount_altaz_round_trip_and_compass)
{
    Kinematics k;
    k.set_altaz(0, 0, 0);
    Vec east = k.to_nwu(90, 0);
    CHECK_NEAR(east.y, -1, 1e-12);                 // azimuth 90 = east = -west
    for (double az = -170; az < 540; az += 37)
        for (double alt = -10; alt <= 89; alt += 11) {
            double a, e;
            k.to_head(k.to_nwu(az, alt), az, a, e);
            CHECK_NEAR(a, az, 1e-9);
            CHECK_NEAR(e, alt, 1e-9);
        }
}

TEST(mount_eq_wedge_dec_equals_altitude)
{
    double lat = 38.72;
    Kinematics k;
    k.set_equatorial(lat, 90 - lat, 0);
    double lst = 2.0;
    for (double dec = -30; dec <= 85; dec += 23) {
        Vec v = apparent_to_nwu(0.7, dec * D2R, lst, lat * D2R);
        double az, alt;
        k.to_head(v, 0, az, alt);
        CHECK_NEAR(alt, dec, 1e-9);
    }
    // sidereal motion turns only the azimuth (polar) axis, at the sidereal rate
    double az0, alt0, az1, alt1;
    k.to_head(apparent_to_nwu(0.7, 0.3, lst, lat * D2R), 0, az0, alt0);
    k.to_head(apparent_to_nwu(0.7, 0.3, lst + 1e-3, lat * D2R), az0, az1, alt1);
    CHECK_NEAR(alt1, alt0, 1e-9);
    CHECK_NEAR(std::fabs(az1 - az0), 1e-3 * R2D, 1e-9);
}

TEST(mount_roll_derotation_holds_position_angle)
{
    double lat = 38.72 * D2R;
    Kinematics k;
    k.set_altaz(0, 0, 0);
    double ra = 1.0, dec = 0.5, pa_want = 30.0, worst = 0, roll_min = 1e9, roll_max = -1e9;
    for (double lst = ra - 1.5; lst <= ra + 1.5; lst += 0.05) {
        Vec v = apparent_to_nwu(ra, dec, lst, lat);
        Vec pole = apparent_to_nwu(0, PI / 2, lst, lat);
        double az, alt;
        k.to_head(v, 0, az, alt);
        double roll = k.roll_for_pa(az, alt, pole, pa_want);
        double pa = k.pa_for_roll(az, alt, pole, roll);
        worst = std::fmax(worst, std::fabs(pa - pa_want));
        roll_min = std::fmin(roll_min, roll);
        roll_max = std::fmax(roll_max, roll);
    }
    NOTE("field rotation over +/-5.7 h at dec 28.6 deg needs roll %.1f..%.1f deg; PA held to %.2e deg", roll_min, roll_max, worst);
    CHECK(worst < 1e-6);
}

TEST(mount_pointing_fit_recovers_terms)
{
    PointingModel truth;
    double t[] = {0.12, -0.05, 0.03, -0.02, 0.015, -0.01, 0.02};   // degrees
    for (int i = 0; i < PointingModel::N_TERMS; i++) truth.p[i] = t[i];
    std::mt19937 rng(3);
    std::normal_distribution<double> noise(0, 5.0 / 3600);
    std::vector<SyncPoint> pts;
    for (int i = 0; i < 24; i++) {
        SyncPoint s;
        s.ideal_a1 = i * 47.0;
        s.ideal_a2 = 10 + (i * 13) % 70;
        truth.ideal_to_mech(s.ideal_a1, s.ideal_a2, s.mech_a1, s.mech_a2);
        s.mech_a1 += noise(rng) / std::cos(s.ideal_a2 * D2R);
        s.mech_a2 += noise(rng);
        pts.push_back(s);
    }
    PointingModel fit;
    CHECK(fit_pointing(pts.data(), (int)pts.size(), fit));
    for (int i = 0; i < PointingModel::N_TERMS; i++) CHECK_NEAR(fit.p[i], t[i], 15.0 / 3600);
    NOTE("24 points, 5\" noise: fit RMS %.1f\"", fit.rms_arcsec);
    CHECK(fit.rms_arcsec < 9);
    double a1, a2, m1, m2;
    fit.ideal_to_mech(123, 45, m1, m2);
    fit.mech_to_ideal(m1, m2, a1, a2);
    CHECK_NEAR(a1, 123, 1e-6);
    CHECK_NEAR(a2, 45, 1e-6);
    PointingModel one;                                       // a single star gives the index terms only
    CHECK(fit_pointing(pts.data(), 1, one));
    CHECK(one.p[PointingModel::CA] == 0 && one.p[PointingModel::TF] == 0);
}
