// Star Tracker — astronomy. See st_astro.h for the formulas used and their sources.
#include "st_astro.h"

namespace st {

Mat rot_x(double a) { Mat r; double c = std::cos(a), s = std::sin(a); r.m[1][1] = c; r.m[1][2] = -s; r.m[2][1] = s; r.m[2][2] = c; return r; }
Mat rot_y(double a) { Mat r; double c = std::cos(a), s = std::sin(a); r.m[0][0] = c; r.m[0][2] = s; r.m[2][0] = -s; r.m[2][2] = c; return r; }
Mat rot_z(double a) { Mat r; double c = std::cos(a), s = std::sin(a); r.m[0][0] = c; r.m[0][1] = -s; r.m[1][0] = s; r.m[1][1] = c; return r; }

double wrap_2pi(double a) { a = std::fmod(a, 2 * PI); return a < 0 ? a + 2 * PI : a; }
double wrap_pi(double a) { a = wrap_2pi(a); return a > PI ? a - 2 * PI : a; }

void vec_radec(const Vec &v, double &ra, double &dec)
{
    double r = norm(v);
    dec = std::asin(std::fmax(-1.0, std::fmin(1.0, v.z / r)));
    ra = wrap_2pi(std::atan2(v.y, v.x));
}

double jd_from_unix(double unix_s) { return unix_s / 86400.0 + 2440587.5; }
double tt_centuries(double jd_utc) { return (jd_utc + (TAI_UTC + 32.184) / 86400.0 - 2451545.0) / 36525.0; }

double gmst(double jd_ut1)
{
    double d = jd_ut1 - 2451545.0, t = d / 36525.0;
    double g = 280.46061837 + 360.98564736629 * d + 0.000387933 * t * t - t * t * t / 38710000.0;   // Meeus 12.4
    return wrap_2pi(g * D2R);
}

double gast(double jd_ut1, double t_tt)
{
    double dpsi, deps, eps0;
    nutation(t_tt, dpsi, deps, eps0);
    return wrap_2pi(gmst(jd_ut1) + dpsi * std::cos(eps0 + deps));   // equation of the equinoxes
}

Mat precession_matrix(double t)
{
    // IAU 1976 (Lieske et al. 1977), from J2000.0: arcseconds
    double zeta = (2306.2181 + (0.30188 + 0.017998 * t) * t) * t * AS2R;
    double z = (2306.2181 + (1.09468 + 0.018203 * t) * t) * t * AS2R;
    double theta = (2004.3109 - (0.42665 + 0.041833 * t) * t) * t * AS2R;
    return rot_z(z) * rot_y(-theta) * rot_z(zeta);
}

void nutation(double t, double &dpsi, double &deps, double &eps0)
{
    // fundamental arguments (degrees), IAU 1980 / Meeus 22
    double D = 297.85036 + 445267.111480 * t, M = 357.52772 + 35999.050340 * t, Mp = 134.96298 + 477198.867398 * t;
    double F = 93.27191 + 483202.017538 * t, Om = 125.04452 - 1934.136261 * t;
    struct T { int d, m, mp, f, om; double ps, pst, ec, ect; };
    static const T tab[] = {   // 0.0001" units
        {0, 0, 0, 0, 1, -171996, -174.2, 92025, 8.9}, {-2, 0, 0, 2, 2, -13187, -1.6, 5736, -3.1},
        {0, 0, 0, 2, 2, -2274, -0.2, 977, -0.5},      {0, 0, 0, 0, 2, 2062, 0.2, -895, 0.5},
        {0, 1, 0, 0, 0, 1426, -3.4, 54, -0.1},        {0, 0, 1, 0, 0, 712, 0.1, -7, 0},
        {-2, 1, 0, 2, 2, -517, 1.2, 224, -0.6},       {0, 0, 0, 2, 1, -386, -0.4, 200, 0},
        {0, 0, 1, 2, 2, -301, 0, 129, -0.1},          {-2, -1, 0, 2, 2, 217, -0.5, -95, 0.3},
        {-2, 0, 1, 0, 0, -158, 0, 0, 0},              {-2, 0, 0, 2, 1, 129, 0.1, -70, 0},
        {0, 0, -1, 2, 2, 123, 0, -53, 0},
    };
    dpsi = deps = 0;
    for (const T &e : tab) {
        double a = (e.d * D + e.m * M + e.mp * Mp + e.f * F + e.om * Om) * D2R;
        dpsi += (e.ps + e.pst * t) * std::sin(a);
        deps += (e.ec + e.ect * t) * std::cos(a);
    }
    dpsi *= 1e-4 * AS2R;
    deps *= 1e-4 * AS2R;
    eps0 = (84381.448 - 46.8150 * t - 0.00059 * t * t + 0.001813 * t * t * t) * AS2R;
}

Mat nutation_matrix(double t)
{
    double dpsi, deps, eps0;
    nutation(t, dpsi, deps, eps0);
    return rot_x(eps0 + deps) * rot_z(dpsi) * rot_x(-eps0);     // = R1(-(eps+deps)) R3(-dpsi) R1(eps) in coordinate-rotation form
}

Vec aberrate(const Vec &v, double t)
{
    // Earth's velocity from the Sun's true longitude (circular approximation, Meeus 23.3 without e-terms)
    double L0 = 280.46646 + 36000.76983 * t, M = 357.52911 + 35999.05029 * t;
    double C = (1.914602 - 0.004817 * t) * std::sin(M * D2R) + 0.019993 * std::sin(2 * M * D2R);
    double sun = (L0 + C) * D2R;
    double dpsi, deps, eps0;
    nutation(t, dpsi, deps, eps0);
    double eps = eps0 + deps, k = 20.49552 * AS2R;
    // Earth velocity / c in the equatorial of-date frame: direction of longitude sun - 90 deg... (= -d(sun vector)/dt)
    Vec ve = {k * std::sin(sun), -k * std::cos(sun) * std::cos(eps), -k * std::cos(sun) * std::sin(eps)};
    return unit(add(v, ve));
}

void j2000_to_apparent(double ra, double dec, double t, double &ra_a, double &dec_a)
{
    Vec v = nutation_matrix(t) * (precession_matrix(t) * radec_vec(ra, dec));
    v = aberrate(v, t);
    vec_radec(v, ra_a, dec_a);
}

void apparent_to_j2000(double ra_a, double dec_a, double t, double &ra, double &dec)
{
    Vec target = radec_vec(ra_a, dec_a);
    Vec v = target;
    for (int i = 0; i < 3; i++) {            // undo aberration iteratively, then rotate back
        Vec ab = aberrate(v, t);
        v = unit(add(v, sub(target, ab)));
    }
    v = precession_matrix(t).t() * (nutation_matrix(t).t() * v);
    vec_radec(v, ra, dec);
}

Vec apparent_to_nwu(double ra, double dec, double lst, double lat)
{
    double ha = lst - ra;
    // equatorial (HA, dec) -> horizon: x north, y west, z up
    Vec e = {std::cos(dec) * std::cos(ha), -std::cos(dec) * std::sin(ha), std::sin(dec)};   // x toward meridian, y toward east?
    // e: x = toward (HA=0, dec=0), y = toward HA = -90 deg (east), z = celestial pole
    // rotate about the east-west axis by (90 - lat): pole -> up-north
    double c = std::sin(lat), s = std::cos(lat);
    // south (x_eq at lat) : components in NWU
    Vec h;
    h.x = -e.x * c + e.z * s;      // north
    h.y = -e.y;                    // west = -east
    h.z = e.x * s + e.z * c;       // up
    return h;
}

void nwu_to_apparent(const Vec &h, double lst, double lat, double &ra, double &dec)
{
    double c = std::sin(lat), s = std::cos(lat);
    Vec e;
    e.x = -h.x * c + h.z * s;
    e.y = -h.y;
    e.z = h.x * s + h.z * c;
    dec = std::asin(std::fmax(-1.0, std::fmin(1.0, e.z)));
    double ha = std::atan2(-e.y, e.x);
    ra = wrap_2pi(lst - ha);
}

double lst_at(double unix_s, const Site &s)
{
    double jd = jd_from_unix(unix_s);
    double t = tt_centuries(jd);
    return wrap_2pi(gast(jd + s.dut1_s / 86400.0, t) + s.lon * D2R);
}

double refraction_true(double h, double p, double tc)
{
    double hd = h * R2D;
    if (hd < -1.0) return 0.0;
    double r_arcmin = 1.02 / std::tan((hd + 10.3 / (hd + 5.11)) * D2R);   // Saemundsson
    return r_arcmin / 60.0 * D2R * (p / 1010.0) * (283.0 / (273.0 + tc));
}

double refraction_apparent(double h, double p, double tc)
{
    double hd = h * R2D;
    if (hd < -1.0) return 0.0;
    double r_arcmin = 1.0 / std::tan((hd + 7.31 / (hd + 4.4)) * D2R);     // Bennett
    return r_arcmin / 60.0 * D2R * (p / 1010.0) * (283.0 / (273.0 + tc));
}

static Vec with_alt(const Vec &v, double alt)
{
    double az = std::atan2(v.y, v.x);
    return {std::cos(alt) * std::cos(az), std::cos(alt) * std::sin(az), std::sin(alt)};
}

Vec refract_nwu(const Vec &d, const Site &s)
{
    if (!s.refraction) return d;
    double alt = std::asin(std::fmax(-1.0, std::fmin(1.0, d.z)));
    return with_alt(d, alt + refraction_true(alt, s.pressure_hpa, s.temp_c));
}

Vec unrefract_nwu(const Vec &d, const Site &s)
{
    if (!s.refraction) return d;
    // exact inverse of refract_nwu (Saemundsson), so syncs and reported positions agree to well under 0.01"
    double app = std::asin(std::fmax(-1.0, std::fmin(1.0, d.z)));
    double tr = app - refraction_apparent(app, s.pressure_hpa, s.temp_c);   // Bennett as the first guess
    for (int i = 0; i < 4; i++) tr = app - refraction_true(tr, s.pressure_hpa, s.temp_c);
    return with_alt(d, tr);
}

static void ecl_to_eq(double lam, double beta, double t, double &ra, double &dec)
{
    double dpsi, deps, eps0;
    nutation(t, dpsi, deps, eps0);
    double eps = eps0 + deps;
    ra = wrap_2pi(std::atan2(std::sin(lam) * std::cos(eps) - std::tan(beta) * std::sin(eps), std::cos(lam)));
    dec = std::asin(std::sin(beta) * std::cos(eps) + std::cos(beta) * std::sin(eps) * std::sin(lam));
}

void sun_apparent(double t, double &ra, double &dec)
{
    double L0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t, M = (357.52911 + 35999.05029 * t - 0.0001537 * t * t) * D2R;
    double C = (1.914602 - 0.004817 * t - 0.000014 * t * t) * std::sin(M) + (0.019993 - 0.000101 * t) * std::sin(2 * M) + 0.000289 * std::sin(3 * M);
    double om = (125.04 - 1934.136 * t) * D2R;
    double lam = (L0 + C - 0.00569 - 0.00478 * std::sin(om)) * D2R;
    ecl_to_eq(lam, 0.0, t, ra, dec);
}

void moon_apparent(double t, double &ra, double &dec, double &dist)
{
    double Lp = 218.3164477 + 481267.88123421 * t, D = 297.8501921 + 445267.1114034 * t, M = 357.5291092 + 35999.0502909 * t;
    double Mp = 134.9633964 + 477198.8675055 * t, F = 93.2720950 + 483202.0175233 * t, E = 1.0 - 0.002516 * t;
    double A1 = 119.75 + 131.849 * t, A2 = 53.09 + 479264.290 * t, A3 = 313.45 + 481266.484 * t;
    struct L { int d, m, mp, f; double l, r; };
    static const L lt[] = {   // Meeus table 47.A, largest terms (1e-6 deg, 1e-3 km)
        {0, 0, 1, 0, 6288774, -20905355}, {2, 0, -1, 0, 1274027, -3699111}, {2, 0, 0, 0, 658314, -2955968},
        {0, 0, 2, 0, 213618, -569925},    {0, 1, 0, 0, -185116, 48888},     {0, 0, 0, 2, -114332, -3149},
        {2, 0, -2, 0, 58793, 246158},     {2, -1, -1, 0, 57066, -152138},   {2, 0, 1, 0, 53322, -170733},
        {2, -1, 0, 0, 45758, -204586},    {0, 1, -1, 0, -40923, -129620},   {1, 0, 0, 0, -34720, 108743},
        {0, 1, 1, 0, -30383, 104755},     {2, 0, 0, -2, 15327, 10321},      {0, 0, 1, 2, -12528, 0},
        {0, 0, 1, -2, 10980, 79661},      {4, 0, -1, 0, 10675, -34782},     {0, 0, 3, 0, 10034, -23210},
        {4, 0, -2, 0, 8548, -21636},      {2, 1, -1, 0, -7888, 24208},      {2, 1, 0, 0, -6766, 30824},
        {1, 0, -1, 0, -5163, -8379},      {1, 1, 0, 0, 4987, -16675},       {2, -1, 1, 0, 4036, -12831},
    };
    struct B { int d, m, mp, f; double b; };
    static const B bt[] = {   // Meeus table 47.B, largest terms (1e-6 deg)
        {0, 0, 0, 1, 5128122}, {0, 0, 1, 1, 280602}, {0, 0, 1, -1, 277693}, {2, 0, 0, -1, 173237},
        {2, 0, -1, 1, 55413},  {2, 0, -1, -1, 46271}, {2, 0, 0, 1, 32573},  {0, 0, 2, 1, 17198},
        {2, 0, 1, -1, 9266},   {0, 0, 2, -1, 8822},   {2, -1, 0, -1, 8216}, {2, 0, -2, -1, 4324}, {2, 0, 1, 1, 4200},
    };
    double sl = 0, sr = 0, sb = 0;
    for (const L &e : lt) {
        double a = (e.d * D + e.m * M + e.mp * Mp + e.f * F) * D2R;
        double ef = std::abs(e.m) == 1 ? E : (std::abs(e.m) == 2 ? E * E : 1.0);
        sl += e.l * ef * std::sin(a);
        sr += e.r * ef * std::cos(a);
    }
    for (const B &e : bt) {
        double a = (e.d * D + e.m * M + e.mp * Mp + e.f * F) * D2R;
        double ef = std::abs(e.m) == 1 ? E : 1.0;
        sb += e.b * ef * std::sin(a);
    }
    sl += 3958 * std::sin(A1 * D2R) + 1962 * std::sin((Lp - F) * D2R) + 318 * std::sin(A2 * D2R);
    sb += -2235 * std::sin(Lp * D2R) + 382 * std::sin(A3 * D2R) + 175 * std::sin((A1 - F) * D2R) + 175 * std::sin((A1 + F) * D2R) +
          127 * std::sin((Lp - Mp) * D2R) - 115 * std::sin((Lp + Mp) * D2R);
    double dpsi, deps, eps0;
    nutation(t, dpsi, deps, eps0);
    double lam = (Lp + sl * 1e-6) * D2R + dpsi, beta = sb * 1e-6 * D2R;
    dist = 385000.56 + sr / 1000.0;
    ecl_to_eq(lam, beta, t, ra, dec);
}

void moon_topocentric(double t, double lst, const Site &s, double &ra, double &dec)
{
    double dist;
    moon_apparent(t, ra, dec, dist);
    // geocentric observer (WGS84 approx.), Meeus ch. 11 rho cos phi', rho sin phi'
    double lat = s.lat * D2R, u = std::atan(0.99664719 * std::tan(lat));
    double rs = 0.99664719 * std::sin(u) + s.elev_m / 6378140.0 * std::sin(lat);
    double rc = std::cos(u) + s.elev_m / 6378140.0 * std::cos(lat);
    Vec moon = scale(radec_vec(ra, dec), dist / 6378.14);
    Vec obs = {rc * std::cos(lst), rc * std::sin(lst), rs};
    vec_radec(sub(moon, obs), ra, dec);
}

void hours_to_hms(double h, int &hh, int &mm, double &ss)
{
    h = std::fmod(h, 24.0);
    if (h < 0) h += 24.0;
    hh = (int)h;
    mm = (int)((h - hh) * 60);
    ss = ((h - hh) * 60 - mm) * 60;
}

void deg_to_dms(double d, int &sign, int &dd, int &mm, double &ss)
{
    sign = d < 0 ? -1 : 1;
    d = std::fabs(d);
    dd = (int)d;
    mm = (int)((d - dd) * 60);
    ss = ((d - dd) * 60 - mm) * 60;
}

}  // namespace st
