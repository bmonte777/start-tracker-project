// Star Tracker — mount kinematics (head axis angles <-> sky) and the pointing model. Portable C++.
//
// Head frame (docs/05-firmware.md 3.6): x = lens direction at az = alt = 0, z = azimuth axis, y = z cross x.
// Lens direction L(az, alt) = Rz(-az) Ry(-alt) x  -> az increases clockwise seen from above, alt upward.
// Mount matrix R: head frame -> local horizon frame (x north, y west, z up).
//   alt-az:  R = Rz(-az0) * tilt(IMU)
//   EQ on the wedge (D39): R = Rz(-az0) * Ry(wedge) with wedge = 90 deg - |latitude| (az0 = 180 deg south of the equator)
#pragma once
#include "st_astro.h"

namespace st {

enum class MountMode { AltAz = 0, Equatorial = 1 };

struct HeadAngles { double az = 0, alt = 0, roll = 0; };   // degrees, output side of each axis

class Kinematics {
public:
    void set_altaz(double az0_deg, double tilt_x_deg, double tilt_y_deg);
    void set_equatorial(double lat_deg, double wedge_deg, double az0_deg, double polar_err_alt_deg = 0, double polar_err_az_deg = 0);
    MountMode mode() const { return mode_; }
    const Mat &R() const { return R_; }
    // horizon direction (NWU) -> head az/alt (deg); continuity: az chosen nearest to az_hint (unlimited azimuth)
    void to_head(const Vec &nwu, double az_hint, double &az, double &alt) const;
    Vec to_nwu(double az, double alt) const;
    // camera "up" direction (roll = 0) and the roll that gives sky position angle pa_deg (east of north) at the lens direction
    double roll_for_pa(double az, double alt, const Vec &pole_nwu, double pa_deg) const;
    double pa_for_roll(double az, double alt, const Vec &pole_nwu, double roll_deg) const;
private:
    MountMode mode_ = MountMode::AltAz;
    Mat R_;
};

// Pointing model in head-angle space (degrees). mech = ideal + correction(ideal).
// Terms: IA, IE index offsets; CA collimation; NP axis non-perpendicularity; AN, AW tilts of the first axis
// (north-south / east-west, or their EQ equivalents); TF tube flexure.
struct PointingModel {
    enum { IA, IE, CA, NP, AN, AW, TF, N_TERMS };
    double p[N_TERMS] = {0, 0, 0, 0, 0, 0, 0};   // degrees
    int n_points = 0;
    double rms_arcsec = 0;
    void ideal_to_mech(double a1, double a2, double &m1, double &m2) const;
    void mech_to_ideal(double m1, double m2, double &a1, double &a2) const;
};

struct SyncPoint { double ideal_a1, ideal_a2, mech_a1, mech_a2; };   // degrees
// Least-squares fit. Terms used grow with the number of points: 1-2 -> IA, IE; 3-5 -> + AN, AW; 6+ -> all.
bool fit_pointing(const SyncPoint *pts, int n, PointingModel &out);

}  // namespace st
