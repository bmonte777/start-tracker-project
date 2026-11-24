"""Shared helpers for the Phase 7 measurement scripts.

Reads the files Bruno records on the bench:
  * bring-up console logs (.txt) saved by the bench logger page or a serial terminal: the RP2354A tests print CSV
    blocks (a header line, then rows) between the menu text;
  * the bench logger's head recordings (state events at 5 Hz, CSV) and its saved replies (JSON);
  * bench-supply exports (RD6006 software) or hand-written CSVs.

Every spec limit used by the scripts is defined once here, with its source, so a result can always be traced.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------- constants and limits (with sources)
SIDEREAL_DAY_S = 86164.0905
SIDEREAL_ASPS = 1296000.0 / SIDEREAL_DAY_S            # 15.041 arcsec of output per second
RATIO = 300.0                                          # 3:1 belt x 100:1 reducer (D2, D18)
WG_PERIOD_S = SIDEREAL_DAY_S / 100.0                   # wave-generator turn at sidereal: 861.6 s (spec 4.4, pec.status)
MOTOR_PERIOD_S = WG_PERIOD_S / 3.0                     # 287.2 s
FULLSTEP_PERIOD_S = MOTOR_PERIOD_S / 50.0              # one electrical cycle (4 full steps): 5.74 s
ARCSEC_PER_COUNT = 1296000.0 / 2097152.0               # MT6835, 21 bits: 0.618"

LIMITS = {
    "enc_noise_rms": (10.8, 'arcsec RMS, 1000 readings, shaft still: 2 x datasheet 0.0015 deg (Phase 5 sec. 4, test o; D48)'),
    "enc_noise_datasheet": (5.4, 'arcsec RMS, MT6835 datasheet 0.0015 deg'),
    "enc_jump": (0.05 * 3600, 'arcsec between 1 ms samples (Phase 5 sec. 4, test p)'),
    "enc_linearity_pp": (2 * 252.0, 'arcsec p-p raw, MT6835 +/-0.07 deg (spec 4.5); worse means magnet off-centre (R7)'),
    "enc_map_after_rms": (10.0, 'arcsec RMS left after the map: gear-error map term of the go-to budget (spec 4.5)'),
    "pe_half_pp": (20.0, 'arcsec, raw periodic error <= +/-20" (spec 11.2 T2)'),
    "pe_repeat": (3.0, 'arcsec, repeatable turn to turn (spec 11.2 T2)'),
    "pec_rms": (2.0, 'arcsec RMS left after PEC (spec 11.2 T3)'),
    "lost_motion_raw_az_alt": (20.0, 'arcsec raw, azimuth and altitude (spec 1.2, 11.2 T1)'),
    "lost_motion_raw_roll": (30.0, 'arcsec raw, roll (spec 11.2 T1)'),
    "lost_motion_loop": (10.0, 'arcsec with the encoder loop (spec 1.2, 11.2 T1)'),
    "slip": (0.05 * 3600, 'arcsec encoder minus steps = slip (D67, spec 7.3)'),
    "motor_temp": (80.0, 'deg C, current derate threshold (Phase 4 10.7, T10)'),
    "inside_air": (55.0, 'deg C inside the head (spec 11.2 T10)'),
    "power_tol": (0.20, 'fraction: measured power within 20 % of spec 5.1 (spec 11.2 T9)'),
    "track_eq_rms": (3.0, 'arcsec RMS over 5 min, EQ wedge (spec 1.2)'),
    "track_altaz_rms": (5.0, 'arcsec RMS over 5 min, alt-az (spec 1.2)'),
    "settle": (2.0, 's to within 2" after a slew (spec 1.2)'),
}

# Motor winding resistances (spec 3.6) for the power predictions
R_COIL = {"az": 1.4, "alt": 2.3, "roll": 2.3}
LOGIC_W = 0.90          # spec 5.1: electronics 0.90 W
BOOST_EFF = 0.90        # spec 5.1


def lim(key: str) -> float:
    return LIMITS[key][0]


# --------------------------------------------------------------------------- result records
@dataclass
class Result:
    test: str
    quantity: str
    value: float | None
    unit: str
    limit: str
    verdict: str            # pass / fail / info / not run
    source: str             # raw file(s)
    note: str = ""

    def row(self) -> list[str]:
        v = "—" if self.value is None or (isinstance(self.value, float) and math.isnan(self.value)) else f"{self.value:.4g}"
        return [self.test, self.quantity, f"{v} {self.unit}".strip(), self.limit, self.verdict, self.source, self.note]


def verdict(value: float, limit: float, lower_is_better: bool = True) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "not run"
    return "pass" if ((value <= limit) if lower_is_better else (value >= limit)) else "fail"


def write_json(path: Path, obj) -> None:
    def conv(o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, Result):
            return asdict(o)
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, indent=2, default=conv))


# --------------------------------------------------------------------------- console logs
_NUM = re.compile(r"^[\s+-]*[0-9.]")


def csv_blocks(text: str) -> list[dict]:
    """Find every CSV block in a bring-up console log.

    A block starts with a header line of comma-separated names (letters, digits, underscores) and continues with
    rows that have the same number of fields and start with a number. The relay indents lines by two spaces and the
    serial terminal may add a time stamp in square brackets; both are removed. Menu text between rows ends a block.
    Returns [{"header": [...], "rows": [[...], ...], "line": n}].
    """
    blocks, cur = [], None
    for n, raw in enumerate(text.splitlines()):
        line = re.sub(r"^\[[^\]]*\]\s*", "", raw).strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        is_header = len(parts) >= 2 and all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", p) for p in parts)
        if is_header and parts[0] != "summary":
            cur = {"header": parts, "rows": [], "line": n + 1}
            blocks.append(cur)
            continue
        if cur is not None and len(parts) == len(cur["header"]) and _NUM.match(parts[0]):
            try:
                cur["rows"].append([float(p) for p in parts])
                continue
            except ValueError:
                pass
        if parts[0] == "summary":
            blocks.append({"header": ["summary"] + [f"c{i}" for i in range(1, len(parts))], "rows": [[float(p) for p in parts[1:]]], "line": n + 1, "summary": True})
            continue
        # anything else (menu text, PASS/FAIL line) closes the block but keeps it
        if cur is not None and not line.startswith(("PASS", "FAIL")):
            cur = None
    return [b for b in blocks if b["rows"]]


def block(text: str, first_cols: list[str]) -> dict | None:
    """The last CSV block whose header starts with these column names."""
    found = [b for b in csv_blocks(text) if b["header"][: len(first_cols)] == first_cols]
    return found[-1] if found else None


def as_columns(b: dict) -> dict[str, np.ndarray]:
    a = np.array(b["rows"], dtype=float)
    return {h: a[:, i] for i, h in enumerate(b["header"])}


def verdict_lines(text: str) -> list[str]:
    return [re.sub(r"^\[[^\]]*\]\s*", "", l).strip() for l in text.splitlines() if re.search(r"\b(PASS|FAIL)\b", l)]


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------- head recordings (bench logger)
def read_head_csv(path: Path) -> dict[str, np.ndarray]:
    """State events recorded by the bench logger page: one row per event (5 Hz)."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: no rows")
    out: dict[str, np.ndarray] = {}
    for k in rows[0].keys():
        vals = []
        for r in rows:
            v = r.get(k, "")
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                vals.append(np.nan)
        out[k] = np.array(vals)
    out["_text_mode"] = np.array([r.get("mode", "") for r in rows], dtype=object)
    return out


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- maths
def robust_mask(x: np.ndarray, k: float = 10.0) -> np.ndarray:
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med)) * 1.4826
    if not np.isfinite(mad) or mad == 0:
        return np.isfinite(x)
    return np.isfinite(x) & (np.abs(x - med) <= k * mad)


def harmonic_design(t: np.ndarray, period: float, orders, poly_deg: int = 2, t_ref: float | None = None):
    """Columns: polynomial in t (scaled) then cos/sin of each harmonic order."""
    t_ref = float(np.mean(t)) if t_ref is None else t_ref
    span = max(float(np.ptp(t)), 1e-9)
    ts = (t - t_ref) / span
    cols = [ts ** d for d in range(poly_deg + 1)]
    for k in orders:
        w = 2 * np.pi * k / period
        cols += [np.cos(w * t), np.sin(w * t)]
    return np.column_stack(cols)


def fit_harmonics(t, y, period, orders, poly_deg=2):
    A = harmonic_design(t, period, orders, poly_deg)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    npoly = poly_deg + 1
    poly = A[:, :npoly] @ coef[:npoly]
    harm = A[:, npoly:] @ coef[npoly:]
    amps = {}
    for i, k in enumerate(orders):
        c, s = coef[npoly + 2 * i], coef[npoly + 2 * i + 1]
        amps[int(k)] = float(math.hypot(c, s))
    return {"coef": coef, "poly": poly, "harm": harm, "resid": y - poly - harm, "amps": amps}


def window_rms(t, y, window_s=300.0, step_s=30.0):
    """RMS about the mean in sliding windows (spec 4: steady drift counts as d / sqrt(12), i.e. it is kept)."""
    out = []
    t0 = t[0]
    while t0 + window_s <= t[-1] + 1e-9:
        m = (t >= t0) & (t < t0 + window_s)
        if m.sum() > 10:
            yy = y[m]
            out.append(float(np.sqrt(np.mean((yy - yy.mean()) ** 2))))
        t0 += step_s
    return np.array(out)


def spectrum(t, y):
    """Amplitude spectrum of evenly sampled data (resampled to 1 s if needed)."""
    dt = np.median(np.diff(t))
    tt = np.arange(t[0], t[-1], dt)
    yy = np.interp(tt, t, y)
    yy = yy - yy.mean()
    n = len(yy)
    win = np.hanning(n)
    F = np.fft.rfft(yy * win)
    f = np.fft.rfftfreq(n, dt)
    amp = 2 * np.abs(F) / win.sum()
    return f, amp


# --------------------------------------------------------------------------- plotting
def plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as p
    p.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "font.size": 9})
    return p


def out_dir(path: Path, out: Path | None) -> Path:
    d = Path(out) if out else Path(path).with_suffix("")
    if d.suffix:
        d = d.with_suffix("")
    d = Path(str(d) + "_analysis") if out is None else d
    d.mkdir(parents=True, exist_ok=True)
    return d
