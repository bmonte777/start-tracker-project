"""Minimal KiCad S-expression reader / writer (KiCad 9 file formats)."""


class Q(str):
    """A quoted string atom."""
    __slots__ = ()


def parse(text):
    i, n = 0, len(text)
    stack, cur = [], None
    root = None
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            new = []
            if cur is not None:
                cur.append(new)
                stack.append(cur)
            cur = new
            i += 1
        elif c == ")":
            if stack:
                cur = stack.pop()
            else:
                root = cur
                cur = None
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    nx = text[j + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r"}.get(nx, nx))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            cur.append(Q("".join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            cur.append(text[i:j])
            i = j
    return root


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dump(node, ind=0):
    if not isinstance(node, list):
        return _atom(node)
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(_atom(x) for x in node) + ")"
    flat = "(" + " ".join(dump(x) if not isinstance(x, list) else dump(x, 0) for x in node) + ")"
    if len(flat) < 100 and "\n" not in flat:
        return flat
    pad = "\t" * (ind + 1)
    head = []
    k = 0
    while k < len(node) and not isinstance(node[k], list):
        head.append(_atom(node[k]))
        k += 1
    out = "(" + " ".join(head)
    for x in node[k:]:
        out += "\n" + pad + (dump(x, ind + 1) if isinstance(x, list) else _atom(x))
    return out + "\n" + "\t" * ind + ")"


def find(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
