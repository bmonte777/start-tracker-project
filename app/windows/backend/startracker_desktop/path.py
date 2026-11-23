"""Path-lapse positions (port of Path.java): shots spread evenly along a
path through {az, alt} keyframes; azimuth goes the short way round."""
import math


def az_delta(a, b):
    return ((b - a + 540) % 360 + 360) % 360 - 180


def positions(keys, shots):
    if not keys or shots < 1:
        return []
    if len(keys) == 1 or shots == 1:
        return [list(keys[0]) for _ in range(shots)]
    n = len(keys) - 1
    lens = [math.hypot(az_delta(keys[i][0], keys[i + 1][0]), keys[i + 1][1] - keys[i][1]) for i in range(n)]
    total = sum(lens)
    out = []
    for s in range(shots):
        d = total * s / (shots - 1)
        seg = 0
        while seg < n - 1 and d > lens[seg]:
            d -= lens[seg]
            seg += 1
        t = 0 if lens[seg] == 0 else min(1.0, d / lens[seg])
        a, b = keys[seg], keys[seg + 1]
        az = a[0] + az_delta(a[0], b[0]) * t
        out.append([az % 360, a[1] + (b[1] - a[1]) * t])
    return out
