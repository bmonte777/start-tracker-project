"""People Remover merge: the per-pixel median of a burst of JPEGs, so
anything that moved between shots disappears. Each shot is decoded once
into a memory-mapped temporary file, then merged a strip at a time, so a
burst of 61 MP images does not need gigabytes of RAM."""
import os
import tempfile

import numpy as np
from PIL import Image


def merge(paths, sample=2, progress=None):
    n = len(paths)
    if n < 3:
        raise ValueError("People Remover needs at least 3 JPEG shots")
    first = Image.open(paths[0])
    w, h = first.size
    w, h = (w + sample - 1) // sample, (h + sample - 1) // sample
    fd, tmp = tempfile.mkstemp(suffix=".stack")
    os.close(fd)
    try:
        stack = np.memmap(tmp, dtype=np.uint8, mode="w+", shape=(n, h, w, 3))
        for i, p in enumerate(paths):
            im = Image.open(p)
            if sample > 1:
                im.draft("RGB", (w, h))
            im = im.convert("RGB")
            if im.size != (w, h):
                im = im.resize((w, h))
            stack[i] = np.asarray(im)
            if progress:
                progress(int(50 * (i + 1) / n))
        out = np.empty((h, w, 3), dtype=np.uint8)
        rows = 128
        for y in range(0, h, rows):
            part = np.asarray(stack[:, y:y + rows])
            out[y:y + rows] = np.partition(part, n // 2, axis=0)[n // 2]
            if progress:
                progress(50 + int(50 * min(h, y + rows) / h))
        del stack
        return Image.fromarray(out)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
