"""Template engine shared by the printed book and the website.

Every example and problem in the bank is written once, with:
  vars    fixed values used in the printed book
  random  ranges [min, max, step] used for new numbers on the website
  calc    ordered list of "name = expression"
  text, solution, answer   Markdown templates with [[expression|format]]

Expressions use a small subset that is valid in both Python and JavaScript:
numbers, + - * / ** ( ), comparisons, and the helper functions below.
assets/ee-engine.js implements the same helpers and formats, and
tools/check_js.mjs verifies that both engines give identical output.
"""
from __future__ import annotations

import math
import re

# ---------------------------------------------------------------- factors
#
# Closed forms divide by i (or by i - g). Near zero they lose precision, and at
# zero they fail. Below SMALL, and when n is a whole number, the factors are
# summed year by year instead, which is exact for any rate, zero included.
# The gradient factors P/G and A/G are always summed for a whole n, because
# their closed forms lose precision much earlier (about 1e-16 / i**2).
# The JavaScript twin uses the same rule, in the same order, so the two engines
# still agree digit for digit.

SMALL = 1e-6


def _check(i, n, signed_n=False):
    if not (math.isfinite(i) and math.isfinite(n)):
        raise ValueError(f"factor needs finite inputs, got i={i}, n={n}")
    if i <= -1:
        raise ValueError(f"interest rate must be above -100%, got {i}")
    if n < 0 and not signed_n:
        raise ValueError(f"number of periods cannot be negative, got {n}")


def _whole(n):
    return abs(n - round(n)) < 1e-9


def FP(i, n):
    _check(i, n, signed_n=True)
    return (1 + i) ** n


def PF(i, n):
    _check(i, n, signed_n=True)
    return (1 + i) ** (-n)


def PA(i, n):
    _check(i, n)
    if abs(i) < SMALL:
        if not _whole(n):
            return n
        s = 0.0
        for k in range(1, int(round(n)) + 1):
            s += (1 + i) ** (-k)
        return s
    return ((1 + i) ** n - 1) / (i * (1 + i) ** n)


def AP(i, n):
    return 1 / PA(i, n)


def FA(i, n):
    _check(i, n)
    if abs(i) < SMALL:
        if not _whole(n):
            return n
        s = 0.0
        for k in range(int(round(n))):
            s += (1 + i) ** k
        return s
    return ((1 + i) ** n - 1) / i


def AF(i, n):
    return 1 / FA(i, n)


def PG(i, n):
    """Present worth factor of a gradient 0, G, 2G, ... at the end of years 1 to n.
    The closed form loses about 1e-16 / i**2 of relative precision, so for a
    whole n the factor is summed year by year, which is exact at any rate."""
    _check(i, n)
    if _whole(n):
        s = 0.0
        for k in range(1, int(round(n)) + 1):
            s += (k - 1) * (1 + i) ** (-k)
        return s
    if abs(i) < SMALL:
        return n * (n - 1) / 2
    return ((1 + i) ** n - i * n - 1) / (i * i * (1 + i) ** n)


def AG(i, n):
    return PG(i, n) / PA(i, n)


def PGEO(g, i, n):
    """Present worth factor of a geometric series with first payment 1."""
    _check(i, n)
    if g <= -1:
        raise ValueError(f"growth rate must be above -100%, got {g}")
    if abs(i - g) < SMALL:
        if not _whole(n):
            return n / (1 + i)
        s = 0.0
        for k in range(1, int(round(n)) + 1):
            s += (1 + g) ** (k - 1) * (1 + i) ** (-k)
        return s
    return (1 - ((1 + g) / (1 + i)) ** n) / (i - g)


def _bisect(f, lo, hi, wide=None, what="rate"):
    """Root of f between lo and hi by bisection.

    The ends must bracket a root: f(lo) and f(hi) of opposite sign. If they
    do not, the wider interval `wide` is tried once. If that fails too, the
    function raises instead of returning an end point that looks like an answer.
    """
    flo, fhi = f(lo), f(hi)
    if not (flo * fhi <= 0) and wide is not None:
        lo, hi = wide
        flo, fhi = f(lo), f(hi)
    if not (flo * fhi <= 0):
        raise ValueError(f"no {what} between {lo:g} and {hi:g}: the function does not change sign")
    if flo == 0:
        return lo
    pos = flo > 0
    for _ in range(100):
        mid = (lo + hi) / 2
        fm = f(mid)
        if (fm > 0) if pos else (fm < 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def RATE(n, A, P):
    """Interest rate where P equals the present worth of n payments A."""
    return _bisect(lambda r: A * PA(r, n) - P, 1e-9, 1.0, wide=(-0.95, 10.0))


def NPV(i, flows):
    """Present worth at year 0 of flows listed from year 0."""
    s = 0.0
    for t, c in enumerate(flows):
        s += c / (1 + i) ** t
    return s


def IRR(flows, lo=-0.9, hi=1.0):
    """Rate where NPV is zero, by bisection between lo and hi.
    Raises if NPV has the same sign at both ends. Flows that change sign
    more than once can have several rates; the bank uses conventional flows."""
    return _bisect(lambda r: NPV(r, flows), lo, hi, wide=(-0.95, 10.0), what="IRR")


def RATEF(n, A, F):
    """Interest rate where n payments A grow to F."""
    return _bisect(lambda r: A * FA(r, n) - F, 1e-9, 1.0, wide=(-0.95, 10.0))


def GROWTH(A1, P, i, n):
    """Growth rate g where a geometric series starting at A1 has present worth P."""
    return _bisect(lambda g: A1 * PGEO(g, i, n) - P, -0.5, 1.0, wide=(-0.95, 5.0), what="growth rate")


def ln(x):
    return math.log(x)


def pick(cond, a, b):
    return a if cond else b


def yrs(n):
    """Arabic count of years with correct agreement."""
    n = int(round(n))
    if n == 1:
        return "سنة واحدة"
    if n == 2:
        return "سنتين"
    return f"{n} سنوات" if 3 <= n <= 10 else f"{n} سنة"


def r4(x):
    """Round a factor to 4 decimals, as printed in the tables."""
    return float(f"{x:.4f}")


def r2(x):
    return float(f"{x:.2f}")


HELPERS = {
    "FP": FP, "PF": PF, "PA": PA, "AP": AP, "FA": FA, "AF": AF,
    "PG": PG, "AG": AG, "PGEO": PGEO, "RATE": RATE, "RATEF": RATEF, "NPV": NPV, "IRR": IRR, "GROWTH": GROWTH, "ln": ln, "exp": math.exp, "abs": abs, "max": max, "min": min,
    "pick": pick, "yrs": yrs, "r4": r4, "r2": r2, "floor": math.floor, "ceil": math.ceil,
    "lcm": lambda a, b: math.lcm(int(round(a)), int(round(b))),
}

_SAFE = re.compile(r"^[\w\s.+\-*/(),<>=!'\"؀-ۿ%:\[\]]*$")


def ev(expr: str, env: dict):
    if not _SAFE.match(expr):
        raise ValueError(f"unsupported characters in expression: {expr!r}")
    return eval(expr, {"__builtins__": {}}, {**HELPERS, **env})


def compute(item: dict, values: dict | None = None) -> dict:
    env = dict(item.get("vars", {}))
    if values:
        env.update(values)
    for line in item.get("calc", []) or []:
        name, expr = line.split("=", 1)
        env[name.strip()] = ev(expr.strip(), env)
    return env

# ---------------------------------------------------------------- formats

def _group(intpart: str) -> str:
    out = ""
    while len(intpart) > 3:
        out = "," + intpart[-3:] + out
        intpart = intpart[:-3]
    return intpart + out


def fnum(x: float, d: int) -> str:
    """Fixed decimals with thousands separators. Half away from zero."""
    neg = x < 0
    x = abs(x)
    s = f"{math.floor(x * 10 ** d + 0.5 + 1e-9) / 10 ** d:.{d}f}"
    if "." in s:
        a, b = s.split(".")
        s = _group(a) + "." + b
    else:
        s = _group(s)
    if neg and float(s.replace(",", "")) != 0:
        s = "-" + s
    return s


def fmt(v, f: str) -> str:
    if isinstance(v, str):
        return v
    if f == "" or f is None:
        f = "2"
    if f == "%":            # percent, up to 2 decimals, trailing zeros removed
        s = fnum(v * 100, 2)
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s + "%"
    if f == "%2":           # percent, always 2 decimals
        return fnum(v * 100, 2) + "%"
    if f == "r":            # plain number for code lines: 1400, 0.04
        return str(int(round(v))) if abs(v - round(v)) < 1e-9 else repr(float(v))
    if f == "d2":           # 2 decimals without separators, for code comments
        return f"{math.floor(abs(v) * 100 + 0.5 + 1e-9) / 100:.2f}" if v >= 0 else "-" + fmt(-v, "d2")
    if f == "n":            # integer without separators
        return str(int(round(v)))
    if f == "f4":           # factor, 4 decimals, no separators
        return f"{math.floor(abs(v) * 1e4 + 0.5 + 1e-9) / 1e4:.4f}" if v >= 0 else "-" + fmt(-v, "f4")
    if f == "g":            # whole numbers without decimals, otherwise 2
        return fnum(v, 0) if abs(v - round(v)) < 1e-9 else fnum(v, 2)
    if f.isdigit():
        return fnum(v, int(f))
    raise ValueError(f"unknown format {f!r}")


_TOKEN = re.compile(r"\[\[(.+?)(?:\|([^\]]*))?\]\]")


def render(template: str, env: dict) -> str:
    if not template:
        return ""
    out = _TOKEN.sub(lambda m: fmt(ev(m.group(1), env), m.group(2) or ""), template)
    return math_commas(out)


_DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.S)


def math_commas(text: str) -> str:
    """Inside display math, write 1,234 with a plain comma so no space is added after it."""
    def fix(m):
        body = re.sub(r"(?<=\d),(?=\d)", r"\\mathord{,}", m.group(1))
        body = re.sub(r"(?<!\\)%", r"\\%", body)       # % starts a comment in LaTeX
        return "$$" + body + "$$"
    return _DISPLAY.sub(fix, text)

# ---------------------------------------------------------------- diagram

def _esc(x):
    """Escape text placed inside SVG <text> elements."""
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def diagram_svg(spec: dict, env: dict) -> str:
    """Cash flow diagram. spec: {n, i, flows: [[year, amount, label?], ...]}"""
    n = int(round(ev(str(spec["n"]), env)))
    rate = spec.get("i")
    flows = []
    for f in spec.get("flows", []) or []:
        t = ev(str(f[0]), env)
        a = ev(str(f[1]), env)
        lab = render(f[2], env) if len(f) > 2 else fmt(abs(a), "g")
        flows.append((t, a, lab))
    # series: [from, to, amount, label?]; amount and label may use the year t.
    # Long series without a label show the amount on the first and last arrows only.
    for s in spec.get("series", []) or []:
        t1, t2 = int(round(ev(str(s[0]), env))), int(round(ev(str(s[1]), env)))
        for t in range(t1, t2 + 1):
            e2 = {**env, "t": t}
            a = ev(str(s[2]), e2)
            if len(s) > 3:
                lab = render(s[3], e2)
            elif (t2 - t1 + 1 > 8 or n > 10) and t not in (t1, t2):
                lab = ""
            else:
                lab = fmt(abs(a), "g")
            flows.append((t, a, lab))
    return svg_draw(n, flows, render(rate, env) if rate else "")


def _c(v):
    """Coordinate with 1 decimal, half up, same as the JavaScript engine."""
    return "%.1f" % (math.floor(v * 10 + 0.5) / 10)


def svg_draw(n, flows, rate_label):
    W, H, L, R = 640, 250, 50, 570
    ax = 125
    step = (R - L) / max(n, 1)
    big = max([abs(a) for _, a, _ in flows] + [1])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="DejaVu Sans, Arial, sans-serif" font-size="13">',
             f'<line x1="{L - 15}" y1="{ax}" x2="{R + 15}" y2="{ax}" stroke="#444" stroke-width="1.5"/>']
    for k in range(n + 1):
        x = L + k * step
        parts.append(f'<line x1="{_c(x)}" y1="{ax - 5}" x2="{_c(x)}" y2="{ax + 5}" stroke="#444"/>')
        parts.append(f'<text x="{_c(x + 4)}" y="{ax + 18}" fill="#555" font-size="12">{_esc(k)}</text>')
    if rate_label:
        parts.append(f'<text x="{R + 15}" y="16" text-anchor="end" fill="#222">{_esc(rate_label)}</text>')
    for t, a, lab in flows:
        x = L + t * step
        h = 30 + 50 * abs(a) / big
        up = a > 0
        y2 = ax - h if up else ax + h
        col = "#1b6e3a" if up else "#1f4e8c"
        tip = 8 if up else -8
        parts.append(f'<line x1="{_c(x)}" y1="{ax}" x2="{_c(x)}" y2="{_c(y2 + tip)}" stroke="{col}" stroke-width="2.2"/>')
        parts.append(f'<path d="M{_c(x - 5)} {_c(y2 + tip)} L{_c(x + 5)} {_c(y2 + tip)} L{_c(x)} {_c(y2)} Z" fill="{col}"/>')
        ty = y2 - 6 if up else y2 + 16
        parts.append(f'<text x="{_c(x)}" y="{_c(ty)}" text-anchor="middle" fill="#111" font-weight="bold">{_esc(lab)}</text>')
    parts.append("</svg>")
    return "".join(parts)

# ---------------------------------------------------------------- random

def draw(item: dict, rng) -> dict:
    vals = {}
    for k, (lo, hi, st) in (item.get("random") or {}).items():
        if not st > 0 or hi < lo:
            raise ValueError(f"{item.get('id')}: random.{k} needs min <= max and a positive step")
        steps = int(round((hi - lo) / st))
        vals[k] = round(lo + st * rng.randint(0, steps), 10)
    return vals
