// Star Tracker — mount kinematics and pointing model. See st_mount.h.
#include "st_mount.h"
#include <cstring>

namespace st {

void Kinematics::set_altaz(double az0, double tx, double ty)
{
    mode_ = MountMode::AltAz;
    R_ = rot_z(-az0 * D2R) * rot_y(ty * D2R) * rot_x(tx * D2R);
}

void Kinematics::set_equatorial(double lat, double wedge, double az0, double pe_alt, double pe_az)
{
    mode_ = MountMode::Equatorial;
    (void)lat;
    // the azimuth axis is tipped by the wedge angle toward az0 (north: 0, south: 180); polar error adds to both
    R_ = rot_z(-(az0 + pe_az) * D2R) * rot_y((wedge + pe_alt) * D2R);
}

Vec Kinematics::to_nwu(double az, double alt) const
{
    double a = az * D2R, e = alt * D2R;
    Vec h = {std::cos(e) * std::cos(a), -std::cos(e) * std::sin(a), std::sin(e)};
    return R_ * h;
}

void Kinematics::to_head(const Vec &nwu, double hint, double &az, double &alt) const
{
    Vec h = R_.t() * unit(nwu);
    alt = std::asin(std::fmax(-1.0, std::fmin(1.0, h.z))) * R2D;
    double a = std::atan2(-h.y, h.x) * R2D;
    // unlimited azimuth (D19): pick the turn closest to the hint
    double k = std::round((hint - a) / 360.0);
    az = a + 360.0 * k;
}

// Camera up at roll 0: Rz(-az) Ry(-alt) z = the altitude-axis plane normal side "up" in the image.
static Vec up0(const Mat &R, double az, double alt)
{
    double a = az * D2R, e = alt * D2R;
    Vec u = {-std::sin(e) * std::cos(a), std::sin(e) * std::sin(a), std::cos(e)};
    return R * u;
}

double Kinematics::pa_for_roll(double az, double alt, const Vec &pole, double roll) const
{
    Vec L = to_nwu(az, alt), u = up0(R_, az, alt);
    // north direction on the sky at L: component of the pole perpendicular to L
    Vec n = unit(sub(pole, scale(L, dot(pole, L))));
    Vec e = cross(n, L);                         // NWU (x north, y west, z up): n x L points east on the sky (zenith: x cross z = -y = east)
    // roll rotates the camera up vector about L by +roll
    double r = roll * D2R;
    Vec ur = add(scale(u, std::cos(r)), scale(cross(L, u), std::sin(r)));
    double pa = std::atan2(dot(ur, e), dot(ur, n)) * R2D;   // position angle of image up, east of north
    return pa;
}

double Kinematics::roll_for_pa(double az, double alt, const Vec &pole, double pa) const
{
    double pa0 = pa_for_roll(az, alt, pole, 0.0);
    double d = pa_for_roll(az, alt, pole, 1.0) - pa0;          // +1 or -1 depending on the handedness of the roll axis
    while (d > 180) d -= 360;
    while (d < -180) d += 360;
    double r = (pa - pa0) * (d >= 0 ? 1.0 : -1.0);
    while (r > 180) r -= 360;
    while (r < -180) r += 360;
    return r;
}

// ------------------------------------------------------------------ pointing model
static void terms(double a1, double a2, double row1[PointingModel::N_TERMS], double row2[PointingModel::N_TERMS])
{
    double s1 = std::sin(a1 * D2R), c1 = std::cos(a1 * D2R), c2 = std::cos(a2 * D2R), t2 = std::tan(a2 * D2R);
    if (std::fabs(c2) < 0.05) { c2 = c2 < 0 ? -0.05 : 0.05; t2 = std::sin(a2 * D2R) / c2; }   // keep away from the axis pole
    double r1[] = {1, 0, 1.0 / c2, t2, s1 * t2, -c1 * t2, 0};
    double r2[] = {0, 1, 0, 0, c1, s1, c2};
    memcpy(row1, r1, sizeof r1);
    memcpy(row2, r2, sizeof r2);
}

void PointingModel::ideal_to_mech(double a1, double a2, double &m1, double &m2) const
{
    double r1[N_TERMS], r2[N_TERMS];
    terms(a1, a2, r1, r2);
    m1 = a1;
    m2 = a2;
    for (int k = 0; k < N_TERMS; k++) { m1 += r1[k] * p[k]; m2 += r2[k] * p[k]; }
}

void PointingModel::mech_to_ideal(double m1, double m2, double &a1, double &a2) const
{
    a1 = m1;
    a2 = m2;
    for (int it = 0; it < 4; it++) {           // fixed point: corrections are small (arc-minutes)
        double x1, x2;
        ideal_to_mech(a1, a2, x1, x2);
        a1 += m1 - x1;
        a2 += m2 - x2;
    }
}

// Solve the normal equations A^T W A p = A^T W r by Cholesky (at most 7 unknowns).
bool fit_pointing(const SyncPoint *pts, int n, PointingModel &out)
{
    const int N = PointingModel::N_TERMS;
    bool use[N] = {true, true, false, false, false, false, false};
    if (n >= 3) use[PointingModel::AN] = use[PointingModel::AW] = true;
    if (n >= 6) for (int k = 0; k < N; k++) use[k] = true;
    int idx[N], m = 0;
    for (int k = 0; k < N; k++) if (use[k]) idx[m++] = k;
    double A[N][N] = {}, b[N] = {};
    for (int i = 0; i < n; i++) {
        double r1[N], r2[N];
        terms(pts[i].ideal_a1, pts[i].ideal_a2, r1, r2);
        double d1 = pts[i].mech_a1 - pts[i].ideal_a1;
        d1 -= 360.0 * std::round(d1 / 360.0);
        double d2 = pts[i].mech_a2 - pts[i].ideal_a2;
        double w1 = std::pow(std::cos(pts[i].ideal_a2 * D2R), 2);   // axis-1 residuals count on the sky
        for (int a = 0; a < m; a++) {
            b[a] += w1 * r1[idx[a]] * d1 + r2[idx[a]] * d2;
            for (int c = 0; c < m; c++) A[a][c] += w1 * r1[idx[a]] * r1[idx[c]] + r2[idx[a]] * r2[idx[c]];
        }
    }
    for (int a = 0; a < m; a++) A[a][a] += 1e-9;                   // tiny ridge keeps a singular set solvable
    double L[N][N] = {};
    for (int i = 0; i < m; i++)
        for (int j = 0; j <= i; j++) {
            double s = A[i][j];
            for (int k = 0; k < j; k++) s -= L[i][k] * L[j][k];
            if (i == j) { if (s <= 0) return false; L[i][i] = std::sqrt(s); }
            else L[i][j] = s / L[j][j];
        }
    double y[N], x[N];
    for (int i = 0; i < m; i++) { double s = b[i]; for (int k = 0; k < i; k++) s -= L[i][k] * y[k]; y[i] = s / L[i][i]; }
    for (int i = m - 1; i >= 0; i--) { double s = y[i]; for (int k = i + 1; k < m; k++) s -= L[k][i] * x[k]; x[i] = s / L[i][i]; }
    PointingModel pm;
    for (int a = 0; a < m; a++) pm.p[idx[a]] = x[a];
    pm.n_points = n;
    double ss = 0;
    for (int i = 0; i < n; i++) {
        double m1, m2;
        pm.ideal_to_mech(pts[i].ideal_a1, pts[i].ideal_a2, m1, m2);
        double d1 = (pts[i].mech_a1 - m1) * std::cos(pts[i].ideal_a2 * D2R), d2 = pts[i].mech_a2 - m2;
        d1 -= 360.0 * std::round(d1 / 360.0);
        ss += d1 * d1 + d2 * d2;
    }
    pm.rms_arcsec = n ? std::sqrt(ss / n) * 3600.0 : 0;
    out = pm;
    return true;
}

}  // namespace st
