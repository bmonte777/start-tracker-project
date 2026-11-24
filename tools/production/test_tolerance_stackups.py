"""Self-test for tolerance_stackups.py: recomputes key numbers by hand."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import tolerance_stackups as T  # noqa: E402

P = T.P
ok = 0


def check(name, cond):
    global ok
    assert cond, name
    ok += 1


r = T.run()
# 1 encoder gap nominal: board 2.0 above the magnet seat top; magnet top 0.08 below the tube end; chip 1.00; solder 0.05
check("gap nominal", abs(r["cases"]["P1"]["S1-17"]["nominal"] - (2.0 + 0.08 - 1.00 - 0.05)) < 1e-6)
# 2 worst case = sum of tolerances (P1, size 17): 0.1+0.3+0.3+0.16+0.15+0.03+0.1+0.3+0.02+0.05+0.01
wc = 0.1 + 0.3 + 0.3 + 0.16 + 0.15 + 0.03 + 0.1 + 0.3 + 0.02 + 0.05 + 0.01
check("gap wc", abs(r["cases"]["P1"]["S1-17"]["wc"][0] - (1.03 - wc)) < 1e-3)
# 3 RSS
rss = math.sqrt(sum(t * t for t in (0.1, 0.3, 0.3, 0.16, 0.15, 0.03, 0.1, 0.3, 0.02, 0.05, 0.01)))
check("gap rss", abs(r["cases"]["P1"]["S1-17"]["rss"][1] - (1.03 + rss)) < 1e-3)
# 4 fix gap centred on 1.5
check("fix nominal", abs(r["cases"]["FIX"]["S1-17"]["nominal"] - 1.5) < 1e-9)
# 5 belt centre from params (spec 3.5: 58.62)
check("belt C", abs(P.BELT_C - 58.62) < 0.01)
# 6 V-ring azimuth: 46.5 - 39.8
check("vring az", abs(r["single"]["vrings"][0]["available"] - 6.7) < 1e-6)
# 7 V-ring altitude: 46 - 43.5
check("vring alt", abs(r["single"]["vrings"][2]["available"] - 2.5) < 1e-6)
check("vring az rev D", abs(r["single"]["vrings"][1]["available"] - 9.0) < 1e-6)
# 8 H7/m6 clearance for 4 mm: H7 0/+12, m6 +4/+12 um
check("dowel", r["single"]["S8"]["as_designed"]["clearance"] == [-0.012, 0.008])
# 9 O-ring 3.0 squeeze inside 15-30 % in the FIX case
check("oring", r["cases"]["FIX"]["S12b"]["pass_wc"])
# 10 OLED vertical nominal margin (18 - 14.70)/2 = 1.65
check("oled", abs(r["cases"]["P1"]["S10"]["vertical"]["nominal"] - 1.65) < 1e-6)
# 11 pulley budget: 0.071 TIR -> 0.26 * 0.071 / 0.04
check("runout", abs(r["cases"]["P1"]["S6"]["extra"]["belt_term_rms_arcsec"] - 0.26 * 0.071 / 0.04) < 1e-3)
print(f"{ok}/12 checks passed")
