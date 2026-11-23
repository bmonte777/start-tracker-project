// Star Tracker — astronomy: time scales, sidereal time, precession, nutation, aberration, refraction, Sun and Moon.
// Portable C++ (ESP32-S3 and the PC simulator). Angles in radians unless a name says _deg / _h.
//
// Accuracy targets (docs/05-firmware.md 3.6): J2000 <-> apparent better than 1"; Sun 0.01 deg; Moon about 0.02 deg.
// Formulas: IAU 1976 precession (Lieske 1977), IAU 1980 nutation (largest 13 terms), GMST IAU 1982 (Meeus 12.4),
// annual aberration (Meeus 23.3, e-terms neglected), Sun (Meeus ch. 25 low accuracy), Moon (Meeus ch. 47 main terms),
// refraction: Saemundsson 1986 for true -> apparent, Bennett 1982 for apparent -> true, both scaled by P and T.
#pragma once
#include <cmath>
#include <cstdint>

namespace st {

constexpr double PI = 3.14159265358979323846;
constexpr double D2R = PI / 180.0, R2D = 180.0 / PI;
constexpr double AS2R = D2R / 3600.0;
constexpr double SIDEREAL_RATE_DPS = 360.0 / 86164.0905;   // 15.0410671"/s
constexpr double TAI_UTC = 37.0;                           // leap seconds since 2017-01-01 (no change announced to 2026)

struct Vec { double x = 0, y = 0, z = 0; };
inline Vec vec(double x, double y, double z) { return {x, y, z}; }
inline double dot(const Vec &a, const Vec &b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
inline Vec cross(const Vec &a, const Vec &b) { return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x}; }
inline Vec scale(const Vec &a, double k) { return {a.x * k, a.y * k, a.z * k}; }
inline Vec add(const Vec &a, const Vec &b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline Vec sub(const Vec &a, const Vec &b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline double norm(const Vec &a) { return std::sqrt(dot(a, a)); }
inline Vec unit(const Vec &a) { double n = norm(a); return n > 0 ? scale(a, 1.0 / n) : a; }

struct Mat {
    double m[3][3] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};
    Vec operator*(const Vec &v) const {
        return {m[0][0] * v.x + m[0][1] * v.y + m[0][2] * v.z, m[1][0] * v.x + m[1][1] * v.y + m[1][2] * v.z,
                m[2][0] * v.x + m[2][1] * v.y + m[2][2] * v.z};
    }
    Mat operator*(const Mat &b) const {
        Mat r;
        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 3; j++) r.m[i][j] = m[i][0] * b.m[0][j] + m[i][1] * b.m[1][j] + m[i][2] * b.m[2][j];
        return r;
    }
    Mat t() const { Mat r; for (int i = 0; i < 3; i++) for (int j = 0; j < 3; j++) r.m[i][j] = m[j][i]; return r; }
};
Mat rot_x(double a);   // right-handed rotation of the vector by +a about the axis
Mat rot_y(double a);
Mat rot_z(double a);

inline Vec radec_vec(double ra, double dec) { return {std::cos(dec) * std::cos(ra), std::cos(dec) * std::sin(ra), std::sin(dec)}; }
void vec_radec(const Vec &v, double &ra, double &dec);
double wrap_2pi(double a);
double wrap_pi(double a);

// ---- time ----
double jd_from_unix(double unix_s);                 // UTC Julian date
double tt_centuries(double jd_utc);                 // Julian centuries TT since J2000.0
double gmst(double jd_ut1);                         // Greenwich mean sidereal time, radians
double gast(double jd_ut1, double t_tt);            // apparent sidereal time

// ---- precession / nutation / aberration ----
Mat precession_matrix(double t_tt);                 // J2000 mean -> mean of date
void nutation(double t_tt, double &dpsi, double &deps, double &eps0);
Mat nutation_matrix(double t_tt);                   // mean of date -> true of date
Vec aberrate(const Vec &true_of_date, double t_tt); // annual aberration, of-date frame
// J2000 catalogue -> apparent (JNow, topocentric for stars) and back
void j2000_to_apparent(double ra, double dec, double t_tt, double &ra_app, double &dec_app);
void apparent_to_j2000(double ra_app, double dec_app, double t_tt, double &ra, double &dec);

// ---- horizon ----
struct Site { double lat = 0, lon = 0, elev_m = 0; double pressure_hpa = 1010, temp_c = 10; bool refraction = true; double dut1_s = 0; };
// apparent RA/Dec -> horizon unit vector in the frame x = north, y = west, z = up (the head's reference frame)
Vec apparent_to_nwu(double ra, double dec, double lst, double lat);
void nwu_to_apparent(const Vec &v, double lst, double lat, double &ra, double &dec);
double lst_at(double unix_s, const Site &s);
// refraction (radians): R(true altitude) to add; inverse for apparent altitude
double refraction_true(double alt_true, double p_hpa, double t_c);
double refraction_apparent(double alt_app, double p_hpa, double t_c);
Vec refract_nwu(const Vec &true_dir, const Site &s);     // true -> observed (apparent) direction
Vec unrefract_nwu(const Vec &obs_dir, const Site &s);

// ---- Sun and Moon (apparent geocentric; Moon also topocentric) ----
void sun_apparent(double t_tt, double &ra, double &dec);
void moon_apparent(double t_tt, double &ra, double &dec, double &dist_km);
void moon_topocentric(double t_tt, double lst, const Site &s, double &ra, double &dec);

// ---- formatting helpers for LX200 / logs ----
void hours_to_hms(double h, int &hh, int &mm, double &ss);
void deg_to_dms(double d, int &sign, int &dd, int &mm, double &ss);

}  // namespace st
