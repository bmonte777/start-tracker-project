#!/usr/bin/env python3
"""Draw the Phase 5 firmware diagrams (Graphviz) into docs/img/05-*.svg and .png."""
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parents[2] / "docs/img"
FONT = 'fontname="Helvetica"'
BASE = f'graph [{FONT} fontsize=11 bgcolor=white pad=0.2]; node [{FONT} fontsize=10 shape=box style="rounded,filled" fillcolor="#f4f6fa" color="#4a5a75"]; edge [{FONT} fontsize=9 color="#4a5a75"];'

DIAGRAMS = {
"05-firmware-overview": f"""
digraph G {{ {BASE} rankdir=LR; compound=true; newrank=true;
 subgraph cluster_app {{ label="ESP32-S3 — application (ESP-IDF 5.5, C++17)"; style="rounded"; color="#2f6db5";
   subgraph cluster_c0 {{ label="core 0: radio and network"; style=dashed;
     wifi [label="Wi-Fi STA / AP\\nmDNS startracker.local"]; ble [label="BLE set-up\\n(NimBLE GATT)"];
     http [label="HTTP :80 / :32323\\nAlpaca Telescope + Rotator\\nweb UI, /api/update"]; ws [label="WebSocket /ws/v1\\nJSON API (apps)"];
     lx [label="LX200 TCP :4030"]; disc [label="Alpaca discovery\\nUDP 32227"]; }}
   subgraph cluster_c1 {{ label="core 1: head logic"; style=dashed;
     head [label="Head model\\n(state, settings, faults)" fillcolor="#e3ecf9"];
     trk [label="tracker 10 Hz\\nastro · kinematics · pointing\\nPEC · jobs"]; pwr [label="power 2 Hz\\nPD A/B · charger · gauge\\npack budget · sleep"];
     sens [label="sensors\\nGNSS · RTC · IMU · mag"]; ui [label="UI 10 Hz\\nOLED · 4 buttons · 3 LEDs"];
     shut [label="shutter / intervalometer\\n(esp_timer)"]; lnk [label="link task\\nCOBS frames · time sync"];
     sys [label="system\\nOTA · SWD flasher · NVS"]; }}
 }}
 subgraph cluster_mot {{ label="RP2354A — motion (Pico SDK 2.3, C11)"; style="rounded"; color="#b5602f";
   c0 [label="core 0\\nlink · encoders 1 kHz (SPI1)\\ncorrection loop 5 Hz · drivers UART\\nsafety · ADC · watchdog"];
   c1 [label="core 1\\nmotion tick 1 kHz\\nprofiles · tracking · PEC\\nstep planning" fillcolor="#fbeee4"];
   pio [label="PIO0: 3 step generators\\nPIO1: PPS / SYNC timestamps"];
 }}
 hw1 [label="3 × TMC2209\\n(UART addr 0,1,2)" shape=component]; hw2 [label="3 × MT6835\\n(SPI, 3 CS)" shape=component];
 hw3 [label="motor rail\\nsoft start · boost 10/16 V" shape=component];
 hw4 [label="TPS25751 / TPS25752\\nBQ40Z50 · sensors · OLED" shape=component];
 apps [label="apps (Phase 6)\\nN.I.N.A., Stellarium, SkySafari" shape=note fillcolor="#fff8dc"];
 apps -> http; apps -> ws; apps -> lx; apps -> ble;
 http -> head; ws -> head; lx -> head; ble -> head; head -> trk; trk -> lnk; pwr -> lnk [label="budget"]; sens -> trk; ui -> head; head -> ui;
 lnk -> c0 [label="UART 921 600 bd\\nLINK_SYNC · 1 PPS" dir=both color="#b5602f" penwidth=1.6];
 c0 -> c1 [label="setpoints,\\nencoder data" dir=both]; c1 -> pio; pio -> hw1 [label="STEP/DIR"]; c0 -> hw1 [label="UART"]; c0 -> hw2; c0 -> hw3; pwr -> hw4; sens -> hw4; ui -> hw4;
 sys -> c0 [label="SWD (IO38/39)\\nRUN (IO40)" style=dashed];
}}""",

"05-rp2354a-timing": f"""
digraph G {{ {BASE} rankdir=TB;
 tick [label="1 kHz alarm (core 1)\\n= motion tick, budget 1000 µs" fillcolor="#fbeee4"];
 a [label="read encoder snapshot (seqlock)\\nread commanded mode per axis  ≈ 3 µs"];
 b [label="per axis: target angle at tick end\\nS-curve / setpoint polynomial + PEC + correction  ≈ 10 µs × 3"];
 c [label="angle → microsteps (×15 360 000 / 2^32)\\nlimit clamp, max 400 steps per tick"];
 d [label="push segment to PIO FIFO\\n(dir | count, half-period)  ≈ 1 µs × 3"];
 e [label="publish state (seqlock)\\ntotal ≈ 45 µs = 4.5 % of core 1" fillcolor="#e3f3e3"];
 tick -> a -> b -> c -> d -> e;
 c0 [label="core 0 main loop" fillcolor="#e3ecf9"]; f [label="every 1 ms: burst-read 3 × MT6835\\n(48 bits @ 8 MHz, ≈ 25 µs)"];
 g [label="every 10 ms: ADC (3 NTC + VMOT), STATE frame,\\nfault checks"]; h [label="every 100 ms: TMC2209 DRV_STATUS / SG_RESULT\\n(1 driver per 33 ms)"];
 i [label="every 200 ms: encoder correction + slip check"]; j [label="link RX (UART IRQ → ring) · watchdog feed"];
 c0 -> f; c0 -> g; c0 -> h; c0 -> i; c0 -> j;
}}""",

"05-system-states": f"""
digraph G {{ {BASE} rankdir=LR;
 off [label="Off / deep sleep" shape=ellipse fillcolor="#e9e9e9"]; boot [label="Boot\\n(rails up, RP in reset)"]; st [label="Self-test\\nI²C, PD, gauge, link, encoders"];
 idle [label="Idle\\nmotor rail off" fillcolor="#e3f3e3"]; op [label="Operating\\nrail 10 V (16 V while slewing)\\naxes: hold · move · track" fillcolor="#e3ecf9"];
 park [label="Parking\\nroll 0°, then park pose"]; flt [label="Fault\\nramp to rest, report" fillcolor="#f8dddd"]; upd [label="Updating\\nESP32 / RP2354A"];
 off -> boot [label="button · RTC alarm · USB/PD event"]; boot -> st; st -> idle [label="pass"]; st -> flt [label="fail"];
 idle -> op [label="go-to / track / jog"]; op -> idle [label="stop + 30 s hold"]; op -> park [label="park · battery 5 % or 6.2 V (D25)"];
 park -> idle; idle -> off [label="sleep timer · power button"]; op -> flt [label="fault"]; flt -> st [label="clear (always via self-test)"];
 idle -> upd; upd -> boot [label="reboot"];
}}""",

"05-axis-states": f"""
digraph G {{ {BASE} rankdir=LR;
 dis [label="Disabled\\nDRV_EN_N high"]; hold [label="Holding\\nI_hold, StealthChop"]; mov [label="Moving\\nS-curve, 16 V, SpreadCycle above TPWMTHRS"];
 trk [label="Tracking\\nsetpoint polynomial + PEC\\nI_track, 10 V, StealthChop"]; stp [label="Stopping\\nramp to rest"]; flt [label="Fault" fillcolor="#f8dddd"];
 dis -> hold [label="rail OK, drivers set"]; hold -> mov [label="MOVE"]; mov -> hold [label="done"]; hold -> trk [label="SETPOINT"]; trk -> hold [label="STOP"];
 mov -> stp [label="STOP · limit · link lost"]; trk -> stp [label="limit · stale 60 s"]; stp -> hold; mov -> flt [label="stall · slip > 0.05°"]; trk -> flt [label="slip · 95 °C"];
 flt -> hold [label="re-sync from encoder"]; hold -> dis [label="rail off"];
}}""",

"05-power-states": f"""
digraph G {{ {BASE} rankdir=TB;
 pack [label="Pack only\\nVSYS = pack 6.0–8.4 V"]; chg [label="USB-C A sink\\ncharging (PD contract 15/20 V)"]; src [label="USB-C A source\\n(phone / camera from pack)"];
 b5 [label="Port B 5 V / 3 A"]; b9 [label="Port B 9 V / 3 A (27 W)"]; b15 [label="Port B re-advertised 15 W\\n(budget exceeded)" fillcolor="#fff3d6"];
 low [label="Low battery: 5 % or 6.2 V\\nfinish exposure → park → sleep" fillcolor="#f8dddd"];
 pack -> chg [label="charger plugged"]; chg -> pack [label="unplugged"]; pack -> src [label="sink device plugged, SoC > 20 %"]; src -> pack;
 b5 -> b9 [label="camera asks 9 V"]; b9 -> b15 [label="P_motion + P_camera > 6 A × V_pack\\nafter slew current already lowered"]; b15 -> b9 [label="slew finished"];
 pack -> low;
 rail [label="Motor rail (RP2354A)\\nMOTOR_PWR_EN → 5 ms → BOOST_EN → 10 ms → VMOT ≈ 10 V ✓ → drivers set → DRV_EN_N low\\nVM_SEL high only while slewing"];
}}""",

"05-update-flow": f"""
digraph G {{ {BASE} rankdir=TB;
 up [label=".stfw bundle uploaded\\n(head web page, app, or web flasher)"]; ver [label="check manifest + SHA-256 of both images"];
 wesp [label="write ESP32 image to the idle OTA slot"]; wrp [label="store RP2354A image in 'rp_new'"]; rb [label="reboot into new ESP32 image (pending verify)"];
 flash [label="SWD: hold RUN, write RP flash, release RUN"]; hello [label="RP HELLO within 3 s\\nand self-test passes?" shape=diamond fillcolor="#fff8dc"];
 ok [label="mark ESP32 slot valid\\nrp_new → rp_good" fillcolor="#e3f3e3"]; bad [label="reflash rp_good over SWD\\nroll ESP32 back to the old slot" fillcolor="#f8dddd"];
 up -> ver -> wesp -> wrp -> rb -> flash -> hello; hello -> ok [label="yes"]; hello -> bad [label="no"];
 note [label="Always available: ESP32 ROM loader over USB (web flasher in Chrome) and the RP2354A Debug Probe pads J6" shape=note fillcolor="#fff8dc"];
}}""",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, src in DIAGRAMS.items():
        for fmt in ("svg", "png"):
            args = ["dot", f"-T{fmt}", "-o", str(OUT / f"{name}.{fmt}")]
            if fmt == "png":
                args.insert(1, "-Gdpi=130")
            subprocess.run(args, input=src.encode(), check=True)
        print("drew", name)


if __name__ == "__main__":
    main()
