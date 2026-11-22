"""Read KiCad symbol libraries: flatten derived symbols and list their pins."""
import copy
import os
from kisx import Q, parse, find, findall

KICAD_SYM = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
_cache = {}


def _lib(path):
    if path not in _cache:
        with open(path, encoding="utf-8") as f:
            root = parse(f.read())
        _cache[path] = {s[1]: s for s in findall(root, "symbol")}
    return _cache[path]


def lib_path(lib, extra_dirs=()):
    for d in list(extra_dirs) + [KICAD_SYM]:
        p = os.path.join(d, lib + ".kicad_sym")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(lib)


def load(lib_id, extra_dirs=()):
    """Return (flattened symbol s-expr named 'Lib:Name', pins) for lib_id 'Lib:Name'.
    pins: list of dict(num, name, x, y, ang, type, unit)."""
    lib, name = lib_id.split(":", 1)
    syms = _lib(lib_path(lib, extra_dirs))
    s = copy.deepcopy(syms[name])
    ext = find(s, "extends")
    if ext is not None:
        parent = copy.deepcopy(syms[ext[1]])
        pname = parent[1]
        props = {p[1]: p for p in findall(s, "property")}
        merged = [parent[0], Q(name)]
        for item in parent[2:]:
            if isinstance(item, list) and item[0] == "property" and item[1] in props:
                merged.append(props.pop(item[1]))
            elif isinstance(item, list) and item[0] == "symbol":
                item[1] = Q(name + item[1][len(pname):])
                merged.append(item)
            else:
                merged.append(item)
        k = max(i for i, it in enumerate(merged) if isinstance(it, list) and it[0] == "property") + 1
        for p in props.values():
            merged.insert(k, p)
        s = merged
    pins = []
    for sub in findall(s, "symbol"):
        tail = sub[1][len(name) + 1:].split("_")
        unit, style = int(tail[0]), int(tail[1])
        if style > 1:
            continue
        for p in findall(sub, "pin"):
            at = find(p, "at")
            pins.append(dict(num=str(find(p, "number")[1]), name=str(find(p, "name")[1]), x=float(at[1]), y=float(at[2]),
                             ang=int(float(at[3])) if len(at) > 3 else 0, type=p[1], unit=unit,
                             hidden=any(isinstance(z, list) and z[0] == "hide" and z[1] == "yes" for z in p) or "hide" in p))
    s[1] = Q(lib_id)
    return s, pins


def prop(sym, key):
    for p in findall(sym, "property"):
        if p[1] == key:
            return p
    return None
