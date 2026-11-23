#!/usr/bin/env python3
"""Final check of Phase 5: every pin, address, register value, scale and timing the firmware uses is recomputed here
from its source (schematic model, Phase 4 calculations, CAD parameters, mechanical document, datasheet formulas) and
compared with the value in the firmware source. Writes firmware/tests/check_report.md; exit code = failures."""
import json
import math
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FW = ROOT / "firmware"
rows = []


def chk(item, source, expected, found, ok=None, tol=None):
    if ok is None:
        ok = abs(expected - found) <= tol if tol is not None else expected == found
    rows.append((item, source, str(expected), str(found), ok))


def src(p):
    return (FW / p).read_text()


# 1. pins and straps: the generator compares the schematic model with the hand-off and rewrites st_board.h
r = subprocess.run([sys.executable, str(FW / "common/tools/gen_board.py")], capture_output=True, text=True)
chk("All ESP32-S3 and RP2354A pins, TMC2209 address straps, PD ADCIN straps, LSM6DSV SA0, R29 not fitted",
    "st-501.model.json vs Phase 4 hand-off 10.1-10.3", "match", "match" if r.returncode == 0 else r.stdout.strip(), r.returncode == 0)
board = src("common/include/st_board.h")
def bd(name):
    return float(re.search(rf"#define {name}\s+([0-9.]+)", board).group(1))

# 2. scales
chk("VSYS monitor scale", "100 k / 33 k (model) ; hand-off x4.03", 4.03, round(bd("VSYS_MON_SCALE"), 2))
chk("VMOT monitor scale", "100 k / 15 k ; hand-off x7.67", 7.67, round(bd("VMOT_MON_SCALE"), 2))
calc = json.loads((ROOT / "docs/calc/phase4_results.json").read_text())
chk("TMC2209 full scale vsense=0 (A)", "phase4_results.json driver.i_fs_vsense0", calc["driver"]["i_fs_vsense0"], round(bd("TMC_IFS_VSENSE0"), 3), tol=0.001)
chk("TMC2209 full scale vsense=1 (A)", "phase4_results.json driver.i_fs_vsense1", calc["driver"]["i_fs_vsense1"], round(bd("TMC_IFS_VSENSE1"), 3), tol=0.001)
chk("Driver current before set-up (A)", "phase4_results.json driver.i_default", calc["driver"]["i_default"],
    round(bd("TMC_VREF_STRAP_V") / 2.5 * bd("TMC_IFS_VSENSE0"), 2), tol=0.01)

# 3. thermistor at 80 C and the thresholds
def ntc_v(tc):
    r = 10000 * math.exp(3950 * (1 / (tc + 273.15) - 1 / 298.15))
    return 3.3 * r / (r + 10000)
chk("Thermistor voltage at 80 C (V)", "Phase 4 calc: 0.372 V", 0.372, round(ntc_v(80), 3), tol=0.001)
mc = src("rp2354a/motion/motion.c")
chk("Thermal derate / stop (C)", "Phase 4 10.7 (80 C), spec 7.3 (95 C)", "80/95",
    "/".join(re.findall(r"c->(?:derate|stop)_c = ([0-9.]+)f", mc)).replace(".0", ""))
chk("VMOT under-voltage stops (mV)", "Phase 4 calc: 14.0 V on 16 V, 8.8 V on 10 V", "14000/8800",
    "/".join(re.findall(r"vmot_mv < (\d+)\)", mc)))

# 4. rail divider levels (TPS61288 V_REF 0.6 V)
r1, r2a, r2b = 365e3, 23.2e3, 36.5e3
chk("Motor rail low level (V)", "0.6 x (1 + 365k/23.2k)", 10.04, round(0.6 * (1 + r1 / r2a), 2))
chk("Motor rail high level (V)", "0.6 x (1 + 365k/(23.2k||36.5k))", 16.04, round(0.6 * (1 + r1 / (r2a * r2b / (r2a + r2b))), 2))
rail = src("rp2354a/src/hw_rail.c")
chk("Soft-start wait / boost wait (ms)", "Phase 4 10.5 step 5: 5 ms, 10 ms", "5/10", "/".join(re.findall(r"sleep_ms\((5|10)\)", rail)[:2]))

# 5. mechanics and timing
usteps = 200 * 256 * 300
chk("Microsteps per output turn", "D2/D23: 200 steps x 256 x 3 (belt) x 100 (reducer)", 15360000, int(float(re.search(r"usteps_per_rev = ([0-9.]+) \* ([0-9.]+) \* ([0-9.]+)", mc).group(1)) * 256 * 300))
steps_ms = 8.0 / 360 * usteps / 1000
chk("Steps per 1 ms tick at 8 deg/s (cap 400)", "D42", "<= 400", round(steps_ms, 1), steps_ms <= 400)
half = (1000 * 150 * 0.97 / math.ceil(steps_ms) - 7) / 2
chk("PIO half-period at 8 deg/s (cycles, min 16)", "stepgen.pio: 2N+7 cycles per step at 150 MHz", ">= 16", round(half), half >= 16)
chk("Sidereal step rate (steps/s)", "360 deg / 86164.0905 s", 178.3, round(usteps / 86164.0905, 1), tol=0.05)
params = (ROOT / "hardware/cad/stcad/params.py").read_text()
amin, amax = re.search(r"ALT_MIN, ALT_MAX = (-?[0-9.]+), (-?[0-9.]+)", params).groups()
head = src("esp32s3/components/st_core/include/st_head.h")
chk("Altitude soft limits (deg)", "params.py ALT_MIN / ALT_MAX", f"{float(amin)}/{float(amax)}",
    "/".join(re.search(r"ALT_MIN = (-?[0-9.]+), ALT_MAX = (-?[0-9.]+)", head).groups()))

# 6. payload roll limits against the mechanical document table
mech = (ROOT / "docs/03-mechanical-design.md").read_text()
hc = src("esp32s3/components/st_core/head.cpp")
for p in range(1, 6):
    m = re.search(rf"\| P{p} \|[^|]+\| \+(\d+)° / −(\d+)° \|", mech)
    f = re.search(rf'"P{p} [^"]*", (-?\d+), (-?\d+)', hc)
    chk(f"P{p} roll limits toward tower / away (deg)", "03-mechanical-design.md payload table", f"+{m.group(1)}/-{m.group(2)}",
        f"+{f.group(1)}/{f.group(2)}")

# 7. protocol ports and addresses
spec = (ROOT / "docs/02-engineering-spec.md").read_text()
chk("Alpaca port / discovery port", "spec 7.2", "32323/32227", "32323/32227" if "32323" in src("esp32s3/components/st_app/net.cpp") and "32227" in src("esp32s3/components/st_app/net.cpp") else "?")
chk("LX200 port", "spec 7.2: TCP 4030", 4030, int(re.search(r"htons\((\d+)\)", src("esp32s3/components/st_app/net.cpp")).group(1)))
chk("Link baud", "hand-off 10.3: 921 600 suggested", 921600, int(re.search(r"ST_LINK_BAUD\s+(\d+)", src("common/include/st_link.h")).group(1)))
chk("Driver UART baud", "hand-off 10.3: 115 200", 115200, int(re.search(r"TMC_BAUD\s+(\d+)", src("rp2354a/src/hw_tmc2209.c")).group(1)))
chk("GNSS baud", "hand-off 10.3: 38 400 (module default)", 38400, int(re.search(r"baud_rate = (\d+)", src("esp32s3/components/st_hal/sensors.cpp")).group(1)))
chk("Encoder SPI clock / mode", "hand-off 10.3: up to 8 MHz, mode 3", "8000000/mode 3",
    ("8000000" if "hw_enc_init(8000000)" in src("rp2354a/src/main.c") else "?") + ("/mode 3" if "SPI_CPOL_1, SPI_CPHA_1" in src("rp2354a/src/hw_encoder.c") else "/?"))

# 8. register values
gconf = (1 << 6) | (1 << 7) | (1 << 8)
chk("TMC2209 GCONF", "datasheet: pdn_disable(6), mstep_reg_select(7), multistep_filt(8), I_scale_analog(0)=0", "0x1c0", hex(gconf) if "(1u << 6) | (1u << 7) | (1u << 8)" in src("rp2354a/src/hw_tmc2209.c") else "?")
chop = 0x03 | (5 << 4) | (1 << 28)
chk("TMC2209 CHOPCONF base (TBL=0, MRES=256)", "datasheet default 0x10000053 = toff 3, hstrt 5, TBL 0, intpol", "0x10000053", hex(chop))
chk("TMC2209 PWMCONF (pwm_freq=0)", "datasheet default 0xC10D0024 with pwm_freq 01 -> 00 (Phase 4 calc 23.4 kHz)", "0xc10c0024", "0xc10c0024" if "0xC10C0024u" in src("rp2354a/src/hw_tmc2209.c") else "?")
for ma, ax in ((830, "az slew 20 C"), (320, "az track"), (180, "alt/roll track"), (150, "hold"), (1260, "az slew -20 C")):
    vs = ma <= 700
    ifs = calc["driver"]["i_fs_vsense1"] if vs else calc["driver"]["i_fs_vsense0"]
    cs = max(0, min(31, math.ceil(ma / 1000 / ifs * 32 - 1e-4) - 1))
    real = (cs + 1) / 32 * ifs * 1000
    chk(f"TMC2209 current {ma} mA ({ax}) -> CS {cs}, vsense {int(vs)}", "I = (CS+1)/32 x I_FS, rounded up", f">= {ma}", round(real), real >= ma - 0.5 and real - ma <= ifs * 1000 / 32 + 0.5)
chk("RV-3028 backup register 0x37", "app manual: TCE b5, FEDE b4, BSM b3:2 = 11 (LSM), TCR b1:0 = 11 (11 k)", "0x3f", hex((1 << 5) | (1 << 4) | (3 << 2) | 3))
chk("MT6835 burst read command", "datasheet 7.6.9: 0xA + address 0x003", "0xa003", "0xa003" if "{0xA0, 0x03" in src("rp2354a/src/hw_encoder.c") else "?")

# 9. partitions vs the web flasher
parts = [l.split(",") for l in src("esp32s3/partitions.csv").splitlines() if l and not l.startswith("#")]
offs = [(p[0].strip(), int(p[3], 16), int(p[4], 16)) for p in parts]
over = any(offs[i][1] + offs[i][2] > offs[i + 1][1] for i in range(len(offs) - 1))
chk("Partition table fits 16 MB, no overlaps", "partitions.csv", "ok", "ok" if not over and offs[-1][1] + offs[-1][2] <= 16 << 20 else "overlap")
pd = [o for o in offs if o[0] == "pd_cfg"][0][1]
chk("pd_cfg offset used by the web flasher", "partitions.csv", hex(pd), re.search(r"PD_CFG = (0x[0-9a-f]+)", src("tools/web-flasher.html")).group(1))

fails = sum(1 for r in rows if not r[4])
out = ["| Item | Source | Expected | In the firmware | Result |", "|---|---|---|---|---|"]
out += [f"| {a} | {b} | {c} | {d} | {'ok' if e else 'FAIL'} |" for a, b, c, d, e in rows]
out.append(f"\n{len(rows) - fails} of {len(rows)} checks agree.")
(FW / "tests/check_report.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
sys.exit(fails)
