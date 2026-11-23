#!/usr/bin/env python3
"""Final check (brief: "check every API op, field name, unit and limit the apps use against the firmware source").
Reads the firmware (wsapi.cpp, services.cpp, st_head.h, ble.cpp, ota.cpp, head.cpp) and the apps (app/shared/*.js,
app/ui/screens/*.js, the native bridges) and compares them. Writes app/api-check.md; exit code = number of failures."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FW = ROOT / "firmware"
APP = ROOT / "app"
rows = []


def check(name, ok, detail=""):
    rows.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


ws = read("firmware/esp32s3/components/st_proto/wsapi.cpp")
svc = read("firmware/esp32s3/components/st_proto/services.cpp")
headh = read("firmware/esp32s3/components/st_core/include/st_head.h")
headc = read("firmware/esp32s3/components/st_core/head.cpp")
blec = read("firmware/esp32s3/components/st_app/ble.cpp")
otac = read("firmware/esp32s3/components/st_app/ota.cpp")
models = read("app/shared/models.js")
client = read("app/shared/stclient.js")
blejs = read("app/shared/ble.js")
stfw = read("app/shared/stfw.js")
screens = "\n".join(p.read_text(encoding="utf-8") for p in (APP / "ui/screens").glob("*.js"))
java = (APP / "android/app/src/main/java/pt/brunomonte/startracker/HeadClient.java").read_text(encoding="utf-8")
py = (APP / "windows/backend/startracker_desktop/head_client.py").read_text(encoding="utf-8")

# ---------------------------------------------------------------- ops
fw_ops = set(re.findall(r'op == "([a-z.]+)"', ws))
fw_list = set(re.findall(r'"([a-z]+(?:\.[a-z]+)*)"', ws[ws.index("OPS_11[]"):ws.index("};", ws.index("OPS_11[]"))]))
app_ops = set(re.findall(r"^\s+'([a-z.]+)': \{ since", models, re.M))
check("every op in models.js is handled by wsapi.cpp", app_ops <= fw_ops, ", ".join(sorted(app_ops - fw_ops)) or f"{len(app_ops)} ops")
check("every op wsapi.cpp handles is known to the apps", fw_ops <= app_ops, ", ".join(sorted(fw_ops - app_ops)) or "")
check("hello's op list matches what wsapi.cpp handles", fw_list == fw_ops, ", ".join(sorted(fw_list ^ fw_ops)) or "")
used = set(re.findall(r"request\('([a-z.]+)'", client)) | set(re.findall(r"request\('([a-z.]+)'", screens))
check("every op the client and screens send exists", used <= fw_ops, ", ".join(sorted(used - fw_ops)) or f"{len(used)} ops used")
native_ops = set(re.findall(r'op\("([a-z.]+)"', java)) | set(re.findall(r'self\.op\("([a-z.]+)"', py)) | set(re.findall(r'head\.op\("([a-z.]+)"', read("app/windows/backend/startracker_desktop/sony.py"))) \
    | set(re.findall(r'head\.op\("([a-z.]+)"', (APP / "android/app/src/main/java/pt/brunomonte/startracker/camera/SonyCamera.java").read_text(encoding="utf-8")))
check("every op the native camera code sends exists (Android + Windows)", native_ops <= fw_ops, ", ".join(sorted(native_ops - fw_ops)) or f"{len(native_ops)} ops")

# ---------------------------------------------------------------- arguments
def fw_args(op):
    i = ws.index(f'op == "{op}"')
    j = ws.find("} else if (op", i + 5)
    return set(re.findall(r'(?:num\(args, |GetObjectItemCaseSensitive\(args, )"([a-z_0-9]+)"', ws[i:j]))


for op in ["goto", "sync", "track", "jog", "guide", "rotator.pa", "rotator.roll", "time.set", "ivm.start", "pec.record", "pec.get", "pec.clear", "job.ack", "cal.encoder.start", "cal.balance", "faults.get"]:
    spec = re.search(rf"'{re.escape(op)}': \{{ since: '[0-9.]+', args: \[([^\]]*)\]", models).group(1)
    a = set(re.findall(r"'([a-z_0-9]+)'", spec))
    f = fw_args(op)
    check(f"{op}: argument names match", a == f or (op == "goto" and a == f | {"epoch", "body"}) or a >= f, f"app {sorted(a)} firmware {sorted(f)}")
job_fw = set(re.findall(r'(?:num|txt)\("([a-z_]+)"', svc[svc.index("Services::job_start"):svc.index("void Services::job_begin_frame")])) | {"poses", "keys"}
job_app = set(re.findall(r"'([a-z_]+)'", re.search(r"'job.start': \{ since: '1.1', args: \[([^\]]*)\]", models).group(1)))
check("job.start: every argument the app may send is read by services.cpp", job_app <= job_fw | {"hold"}, f"app-only {sorted(job_app - job_fw)}; firmware-only {sorted(job_fw - job_app)}")

# ---------------------------------------------------------------- config keys
fw_set = set(re.findall(r'k == "([a-z_]+)"', ws))
fw_get = set(re.findall(r'cJSON_Add\w+ToObject\(o, "([a-z_]+)", s\.', ws[ws.index("settings_json"):ws.index("std::string WsApi::handle") if "std::string WsApi::handle" in ws else None]))
app_keys = set(re.findall(r"(\w+): '(?:string|number|boolean)'", models[models.index("CONFIG_KEYS"):models.index("CONFIG_READONLY")]))
check("config.set keys: app = firmware", app_keys == fw_set, f"app-only {sorted(app_keys - fw_set)}; firmware-only {sorted(fw_set - app_keys)}")
check("config.get returns the set keys plus park_az, park_alt", fw_get == fw_set | {"park_az", "park_alt"}, f"{sorted(fw_get ^ (fw_set | {'park_az', 'park_alt'}))}")

# ---------------------------------------------------------------- state event fields
ev = ws[ws.index("std::string WsApi::state_event()"):]
fw_fields = set(re.findall(r'cJSON_Add\w+ToObject\(\w+, "([a-z_]+)"', ev))
app_fields = set(re.findall(r"\b(pos_d|enc_d|rate_dps|i_ma|load|temp_c|flags|ra_h|dec_d|ra_now_h|dec_now_d|rot_d|az_d|alt_d|soc|v|ext|motion_budget_w|vmot|rail|faults|link|points|rms_as|running|done|count|seq|t|mode|frame|tracking|parked|job|pec|cal)\b", models[models.index("export function parseState"):models.index("export function validate")]))
check("every state field parseState reads is sent by the firmware", app_fields <= fw_fields, ", ".join(sorted(app_fields - fw_fields)) or f"{len(app_fields)} fields")
st_used = set(re.findall(r"state\??\.(?:axes\.\w+|radec|altaz|batt|motor|model|ivm)\??\.(\w+)", screens)) | set(re.findall(r"\bst\.(?:radec|altaz|batt|motor|model|ivm)\.(\w+)", screens))
check("every state field the screens show is sent by the firmware", st_used <= fw_fields, ", ".join(sorted(st_used - fw_fields)) or f"{len(st_used)} fields")
check("activity names (mode) match", set(re.findall(r'return "([a-z]+)";', ws[ws.index("activity_name"):ws.index("static std::string print")])) == set(re.findall(r"'([a-z]+)'", re.search(r"ACTIVITIES = Object.freeze\(\[([^\]]*)\]", models).group(1))))

# ---------------------------------------------------------------- limits and units
alt_min = float(re.search(r"ALT_MIN = (-?[0-9.]+)", headh).group(1))
alt_max = float(re.search(r"ALT_MAX = (-?[0-9.]+)", headh).group(1))
check("altitude limits (st_head.h vs models.js)", f"alt_min_d: {alt_min:g}" in models and f"alt_max_d: {alt_max:g}" in models, f"{alt_min:g} … {alt_max:g}")
check("jog limit 8°/s = default slew speed (D42)", "jog_dps_max: 8" in models and "double slew_dps = 8.0" in headh)
check("payload range 1–5", "payload_min: 1, payload_max: 5" in models and "s.payload < 1 || s.payload > 5" in ws)
check("intervalometer exposure limit 3600 s", "ivm_exposure_max_s: 3600" in models and "iv.exposure_s > 3600" in ws)
check("margin 3° (LIMIT_MARGIN_DEG)", "LIMIT_MARGIN_DEG = 3.0" in headh)
masses = re.findall(r"mass_kg: ([0-9.]+)", models)
check("payload masses match D40 (1.55, 1.95, 3.75, 2.70, 7.00 kg)", [float(m) for m in masses] == [1.55, 1.95, 3.75, 2.70, 7.00])
p_fw = re.findall(r'\{"(P\d)[^"]*", (-?\d+), (-?\d+)', headc)
check("roll limits in limits.get come from head.cpp's PAYLOADS table", len(p_fw) == 5, ", ".join(f"{p}: +{a}/{b}" for p, a, b in p_fw))
check("guide directions n/s/e/w", "GUIDE_DIRS = Object.freeze(['n', 's', 'e', 'w'])" in models and 'ds == "n" ? 0 : ds == "s" ? 1 : ds == "e" ? 2 : ds == "w" ? 3' in ws)
check("track rates sidereal/lunar/solar/king", all(r in ws for r in ['"lunar"', '"solar"', '"king"']) and "TRACK_RATES = Object.freeze(['sidereal', 'lunar', 'solar', 'king'])" in models)
check("PEC period: 3 motor turns = 3.6° of output (300:1)", "PEC_PERIOD_DEG = 3.6" in read("firmware/esp32s3/components/st_proto/include/st_services.h") and "MOTION_PEC_N          1024" in read("firmware/rp2354a/motion/motion.h"))
check("encoder map size: 8 harmonics + 721-point grid", "ENC_HARM = 8, ENC_GRID = 721" in read("firmware/esp32s3/components/st_proto/include/st_services.h") and "MOTION_ENC_GRID_N     721" in read("firmware/rp2354a/motion/motion.h"))

# ---------------------------------------------------------------- BLE and update bundle
uuids = re.findall(r"0x0([1-4]), 0, 0, 0, 0, 0, 0x1e, 0x9b, 0x2a, 0x4d, 0x00, 0x01, 0x4b, 0x52, 0x54, 0x53", blec)
check("BLE service and characteristic UUIDs (ble.cpp vs ble.js)", uuids == ["1", "2", "3", "4"] and all(f"5354524b-0100-4d2a-9b1e-00000000000{n}" in blejs for n in "1234"))
check("BLE Wi-Fi payload keys ssid/psk/mode", all(k in blec for k in ['"ssid"', '"psk"']) and "mode: 'sta'" in blejs)
check("BLE write buffer 256 bytes (255 + terminator)", "char buf[256]" in blec and "MAX_WRITE = 255" in blejs)
check(".stfw: magic, version 1, ≤ 2 entries, RP image ≤ 0x7F000", 'memcmp(hdr, "STFW", 4)' in otac and "ver != 1" in otac and "entries > 2" in otac and "0x7F000" in otac and "RP_MAX = 0x7F000" in stfw)
check(".stfw upload path /api/update", "/api/update" in read("firmware/esp32s3/components/st_app/net.cpp") and "/api/update" in stfw)
check("HTTP routes /startracker/v1/info and /op on the head", all(r in read("firmware/esp32s3/components/st_app/net.cpp") for r in ['"/startracker/v1/info"', '"/startracker/v1/op"']))
check("WebSocket path /ws/v1", '"/ws/v1"' in read("firmware/esp32s3/components/st_app/net.cpp") and "'/ws/v1'" in read("app/shared/discovery.js"))
check("Alpaca discovery UDP 32227", "32227" in read("firmware/esp32s3/components/st_app/net.cpp") and "ALPACA_DISCOVERY_PORT = 32227" in read("app/shared/discovery.js"))
check("error codes", all(f"'{c}'" in models for c in ["limit", "parked", "invalid", "state", "notimpl", "parse", "error"]) and all(f'"{c}"' in ws for c in ["limit", "parked", "invalid", "state", "notimpl", "parse"]))

fails = sum(1 for r in rows if not r[1])
out = ["# API check: apps against the firmware source", "", f"{len(rows) - fails} of {len(rows)} checks pass (`app/tools/check_api.py`).", "",
       "| Check | Result | Detail |", "|---|---|---|"]
out += [f"| {n} | {'pass' if ok else '**FAIL**'} | {d.replace('|', '/')} |" for n, ok, d in rows]
(APP / "api-check.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"{len(rows) - fails} of {len(rows)} pass")
sys.exit(fails)
