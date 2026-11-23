// Star Tracker simulator — small shims so the portable firmware sources build with MSVC (StarTrackerSim.exe).
// Force-included by CMake on MSVC only; the firmware itself never sees this file.
#pragma once
#ifdef _MSC_VER
#include <time.h>
#include <stddef.h>
static __inline struct tm *gmtime_r(const time_t *t, struct tm *r) { return gmtime_s(r, t) == 0 ? r : NULL; }
#endif
