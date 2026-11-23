"""Shutter-speed arithmetic for brackets (port of Exposure.java)."""
import math

LONGEST_TIMED = 30.0


def seconds(v):
    num, den = (v >> 16) & 0xFFFF, v & 0xFFFF
    if v == 0 or den == 0:
        return float("nan")
    return num / den


def offsets(shots, ev):
    out = [0.0]
    k = 1
    while len(out) < shots:
        out.append(-k * ev)
        if len(out) < shots:
            out.append(k * ev)
        k += 1
    return out


def nearest(choices, target):
    best, best_d = -1, float("inf")
    for c in choices:
        s = seconds(c)
        if math.isnan(s):
            continue
        d = abs(math.log2(s / target))
        if d < best_d:
            best, best_d = c, d
    return best


def stops(a, b):
    return math.log2(b / a)
