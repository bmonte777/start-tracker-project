// Astronomy against worked examples in Meeus, "Astronomical Algorithms" (2nd ed.).
#include "st_astro.h"
#include "tst.h"
using namespace st;

TEST(astro_gmst_meeus_12a)
{
    // 1987 April 10, 0h UT: GMST = 13h10m46.3668s
    double jd = 2446895.5;
    double h = gmst(jd) * R2D / 15.0;
    CHECK_NEAR(h * 3600.0, 13 * 3600 + 10 * 60 + 46.3668, 0.01);
}

TEST(astro_apparent_place_theta_persei_meeus_23a)
{
    // J2000 2h44m11.986s +49d13'42.48", proper motion +0.03425 s/yr, -0.0895"/yr; 2028 Nov 13.19 TD
    double jde = 2462088.69, t = (jde - 2451545.0) / 36525.0, yrs = t * 100.0;
    double ra = (2 + 44 / 60.0 + (11.986 + 0.03425 * yrs) / 3600.0) * 15 * D2R;
    double dec = (49 + 13 / 60.0 + (42.48 - 0.0895 * yrs) / 3600.0) * D2R;
    double ra_a, dec_a;
    j2000_to_apparent(ra, dec, t, ra_a, dec_a);
    double ra_ref = (2 + 46 / 60.0 + 14.390 / 3600.0) * 15, dec_ref = 49 + 21 / 60.0 + 7.45 / 3600.0;
    double dra = (ra_a * R2D - ra_ref) * 3600 * std::cos(dec_ref * D2R), ddec = (dec_a * R2D - dec_ref) * 3600;
    NOTE("apparent place error: %.2f\" in RA (x cos dec), %.2f\" in Dec", dra, ddec);
    CHECK(std::fabs(dra) < 1.5 && std::fabs(ddec) < 1.5);
    double r2, d2;
    apparent_to_j2000(ra_a, dec_a, t, r2, d2);
    CHECK_NEAR(r2, ra, 0.02 * AS2R);
    CHECK_NEAR(d2, dec, 0.02 * AS2R);
}

TEST(astro_sun_meeus_25a)
{
    double t = (2448908.5 - 2451545.0) / 36525.0, ra, dec;   // 1992 Oct 13.0 TD
    sun_apparent(t, ra, dec);
    CHECK_NEAR(ra * R2D, 198.38083, 0.01);
    CHECK_NEAR(dec * R2D, -7.78507, 0.01);
}

TEST(astro_moon_meeus_47a)
{
    double t = (2448724.5 - 2451545.0) / 36525.0, ra, dec, dist;   // 1992 Apr 12.0 TD
    moon_apparent(t, ra, dec, dist);
    NOTE("Moon error: RA %.4f deg, Dec %.4f deg, distance %.0f km", ra * R2D - 134.688470, dec * R2D - 13.768368, dist - 368409.7);
    CHECK_NEAR(ra * R2D, 134.688470, 0.03);
    CHECK_NEAR(dec * R2D, 13.768368, 0.03);
    CHECK_NEAR(dist, 368409.7, 300);
}

TEST(astro_refraction)
{
    // standard refraction about 58" at 45 deg, 34.5' at the horizon (Bennett); true <-> apparent round trip
    CHECK_NEAR(refraction_apparent(45 * D2R, 1010, 10) / AS2R, 58.0, 2.0);
    CHECK_NEAR(refraction_apparent(0.0, 1010, 10) / D2R * 60, 34.5, 0.5);
    Site site;
    double worst = 0;
    for (double h = 0; h <= 90; h += 5) {
        double app = h * D2R + refraction_true(h * D2R, 1010, 10);
        worst = std::fmax(worst, std::fabs(app - refraction_apparent(app, 1010, 10) - h * D2R) / AS2R);   // Saemundsson vs Bennett
        Vec t = {std::cos(h * D2R), 0.3, std::sin(h * D2R)};
        t = unit(t);
        Vec back = unrefract_nwu(refract_nwu(t, site), site);
        CHECK_NEAR(norm(sub(back, t)) / AS2R, 0, 0.01);
    }
    NOTE("Saemundsson and Bennett agree to %.1f\" from the horizon to the zenith", worst);
    CHECK(worst < 6.0);
    CHECK_NEAR(refraction_apparent(45 * D2R, 800, -20) / refraction_apparent(45 * D2R, 1010, 10), (800.0 / 1010) * (283.0 / 253), 1e-9);
}

TEST(astro_horizon_round_trip)
{
    double lat = 38.72 * D2R, lst = 1.234;
    for (double dec = -60; dec <= 85; dec += 15)
        for (double ra = 0; ra < 24; ra += 2.5) {
            Vec v = apparent_to_nwu(ra * 15 * D2R, dec * D2R, lst, lat);
            double r, d;
            nwu_to_apparent(v, lst, lat, r, d);
            CHECK_NEAR(wrap_pi(r - ra * 15 * D2R), 0, 1e-9);
            CHECK_NEAR(d, dec * D2R, 1e-9);
        }
    // the celestial pole is due north at the latitude's altitude
    Vec p = apparent_to_nwu(0, PI / 2, lst, lat);
    CHECK_NEAR(std::asin(p.z), lat, 1e-12);
    CHECK_NEAR(p.y, 0, 1e-12);
    CHECK(p.x > 0);
    // a star on the meridian south of the zenith (dec = 0) is due south at 90 - lat
    Vec s = apparent_to_nwu(lst, 0, lst, lat);
    CHECK_NEAR(std::asin(s.z), PI / 2 - lat, 1e-12);
    CHECK(s.x < 0);
}
