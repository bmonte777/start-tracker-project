| Item | Source | Expected | In the firmware | Result |
|---|---|---|---|---|
| All ESP32-S3 and RP2354A pins, TMC2209 address straps, PD ADCIN straps, LSM6DSV SA0, R29 not fitted | st-501.model.json vs Phase 4 hand-off 10.1-10.3 | match | match | ok |
| VSYS monitor scale | 100 k / 33 k (model) ; hand-off x4.03 | 4.03 | 4.03 | ok |
| VMOT monitor scale | 100 k / 15 k ; hand-off x7.67 | 7.67 | 7.67 | ok |
| TMC2209 full scale vsense=0 (A) | phase4_results.json driver.i_fs_vsense0 | 1.352 | 1.352 | ok |
| TMC2209 full scale vsense=1 (A) | phase4_results.json driver.i_fs_vsense1 | 0.749 | 0.749 | ok |
| Driver current before set-up (A) | phase4_results.json driver.i_default | 0.34 | 0.34 | ok |
| Thermistor voltage at 80 C (V) | Phase 4 calc: 0.372 V | 0.372 | 0.372 | ok |
| Thermal derate / stop (C) | Phase 4 10.7 (80 C), spec 7.3 (95 C) | 80/95 | 80/95 | ok |
| VMOT under-voltage stops (mV) | Phase 4 calc: 14.0 V on 16 V, 8.8 V on 10 V | 14000/8800 | 14000/8800 | ok |
| Motor rail low level (V) | 0.6 x (1 + 365k/23.2k) | 10.04 | 10.04 | ok |
| Motor rail high level (V) | 0.6 x (1 + 365k/(23.2k||36.5k)) | 16.04 | 16.04 | ok |
| Soft-start wait / boost wait (ms) | Phase 4 10.5 step 5: 5 ms, 10 ms | 5/10 | 5/10 | ok |
| Microsteps per output turn | D2/D23: 200 steps x 256 x 3 (belt) x 100 (reducer) | 15360000 | 15360000 | ok |
| Steps per 1 ms tick at 8 deg/s (cap 400) | D42 | <= 400 | 341.3 | ok |
| PIO half-period at 8 deg/s (cycles, min 16) | stepgen.pio: 2N+7 cycles per step at 150 MHz | >= 16 | 209 | ok |
| Sidereal step rate (steps/s) | 360 deg / 86164.0905 s | 178.3 | 178.3 | ok |
| Altitude soft limits (deg) | params.py ALT_MIN / ALT_MAX | -10.0/95.0 | -10.0/95.0 | ok |
| P1 roll limits toward tower / away (deg) | 03-mechanical-design.md payload table | +9/-175 | +9/-175 | ok |
| P2 roll limits toward tower / away (deg) | 03-mechanical-design.md payload table | +9/-130 | +9/-130 | ok |
| P3 roll limits toward tower / away (deg) | 03-mechanical-design.md payload table | +8/-150 | +8/-150 | ok |
| P4 roll limits toward tower / away (deg) | 03-mechanical-design.md payload table | +15/-150 | +15/-150 | ok |
| P5 roll limits toward tower / away (deg) | 03-mechanical-design.md payload table | +8/-155 | +8/-155 | ok |
| Alpaca port / discovery port | spec 7.2 | 32323/32227 | 32323/32227 | ok |
| LX200 port | spec 7.2: TCP 4030 | 4030 | 4030 | ok |
| Link baud | hand-off 10.3: 921 600 suggested | 921600 | 921600 | ok |
| Driver UART baud | hand-off 10.3: 115 200 | 115200 | 115200 | ok |
| GNSS baud | hand-off 10.3: 38 400 (module default) | 38400 | 38400 | ok |
| Encoder SPI clock / mode | hand-off 10.3: up to 8 MHz, mode 3 | 8000000/mode 3 | 8000000/mode 3 | ok |
| TMC2209 GCONF | datasheet: pdn_disable(6), mstep_reg_select(7), multistep_filt(8), I_scale_analog(0)=0 | 0x1c0 | 0x1c0 | ok |
| TMC2209 CHOPCONF base (TBL=0, MRES=256) | datasheet default 0x10000053 = toff 3, hstrt 5, TBL 0, intpol | 0x10000053 | 0x10000053 | ok |
| TMC2209 PWMCONF (pwm_freq=0) | datasheet default 0xC10D0024 with pwm_freq 01 -> 00 (Phase 4 calc 23.4 kHz) | 0xc10c0024 | 0xc10c0024 | ok |
| TMC2209 current 830 mA (az slew 20 C) -> CS 19, vsense 0 | I = (CS+1)/32 x I_FS, rounded up | >= 830 | 845 | ok |
| TMC2209 current 320 mA (az track) -> CS 13, vsense 1 | I = (CS+1)/32 x I_FS, rounded up | >= 320 | 328 | ok |
| TMC2209 current 180 mA (alt/roll track) -> CS 7, vsense 1 | I = (CS+1)/32 x I_FS, rounded up | >= 180 | 187 | ok |
| TMC2209 current 150 mA (hold) -> CS 6, vsense 1 | I = (CS+1)/32 x I_FS, rounded up | >= 150 | 164 | ok |
| TMC2209 current 1260 mA (az slew -20 C) -> CS 29, vsense 0 | I = (CS+1)/32 x I_FS, rounded up | >= 1260 | 1268 | ok |
| RV-3028 backup register 0x37 | app manual: TCE b5, FEDE b4, BSM b3:2 = 11 (LSM), TCR b1:0 = 11 (11 k) | 0x3f | 0x3f | ok |
| MT6835 burst read command | datasheet 7.6.9: 0xA + address 0x003 | 0xa003 | 0xa003 | ok |
| Partition table fits 16 MB, no overlaps | partitions.csv | ok | ok | ok |
| pd_cfg offset used by the web flasher | partitions.csv | 0x920000 | 0x920000 | ok |

40 of 40 checks agree.
