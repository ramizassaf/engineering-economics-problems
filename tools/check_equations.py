"""Check the arithmetic that the reader sees in every solution.

This check does not use the bank's calc lines. It renders each solution,
reads every display equation, and recomputes each step "left side = number"
from the numbers printed on the left. Factor notation such as (P/A, 10%, 5)
is evaluated with numpy_financial, not with the book's engine. A step is
skipped when its left side still holds a symbol (a letter); it counts only
when it is pure arithmetic on printed numbers.

Printed numbers are rounded, so a step passes when the recomputed value
agrees with the printed result to the precision the inputs allow.

Output: the number of steps checked, any that disagree, and per chapter
how many items have at least one checked step and none that disagree.
"""
import math
import random
import warnings
import re
import sys
from pathlib import Path

import numpy as np
import numpy_financial as npf
import yaml

warnings.filterwarnings("ignore", category=SyntaxWarning)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import compute, draw, render  # noqa: E402


def f_pa(i, n):
    return float(-npf.pv(i, n, 1, 0)) if i else n


def f_fa(i, n):
    return float(-npf.fv(i, n, 1, 0)) if i else n


FACTORS = {
    "P/F": lambda i, n: (1 + i) ** -n,
    "F/P": lambda i, n: (1 + i) ** n,
    "P/A": f_pa,
    "A/P": lambda i, n: 1 / f_pa(i, n),
    "F/A": f_fa,
    "A/F": lambda i, n: 1 / f_fa(i, n),
    "P/G": lambda i, n: sum((k - 1) * (1 + i) ** -k for k in range(1, int(round(n)) + 1)),
    "A/G": lambda i, n: sum((k - 1) * (1 + i) ** -k for k in range(1, int(round(n)) + 1)) / f_pa(i, n),
}
NUM = r"-?\d+(?:\.\d+)?"


def factor_sub(m):
    name, rate, n = m.group(1), float(m.group(2)) / 100, float(m.group(3))
    return f"({FACTORS[name](rate, n)!r})"


def geo_sub(m):
    g, i, n = float(m.group(1)) / 100, float(m.group(2)) / 100, int(m.group(3))
    v = sum((1 + g) ** (k - 1) * (1 + i) ** -k for k in range(1, n + 1))
    return f"({v!r})"


def frac(s):
    """Replace \\frac{a}{b} (and \\dfrac) with ((a)/(b)), innermost first."""
    pat = re.compile(r"\\d?frac\{([^{}]*)\}\{([^{}]*)\}")
    while True:
        new = pat.sub(r"((\1)/(\2))", s)
        if new == s:
            return s
        s = new


def to_python(expr):
    s = expr
    s = s.replace(r"\mathord{,}", "").replace("{,}", "")
    s = re.sub(r"\\(?:left|right|Big|big|bigg)", "", s)
    s = s.replace(r"\,", " ").replace(r"\ ", " ").replace(r"\qquad", " ").replace(r"\quad", " ")
    s = re.sub(r"\(P/A_1,\s*(" + NUM + r")\\%,\s*(" + NUM + r")\\%,\s*(\d+)\)", geo_sub, s)
    s = re.sub(r"\(([PFAG]/[PFAG]),\s*(" + NUM + r")\\%,\s*(" + NUM + r")\)", factor_sub, s)
    s = s.replace(r"\times", "*").replace(r"\cdot", "*")
    s = re.sub(r"\\sqrt\{([^{}]*)\}", r"((\1)**0.5)", s)
    s = frac(s)
    s = re.sub(r"(" + NUM + r")\\%", r"(\1/100)", s)
    s = re.sub(r"\^\{([^{}]*)\}", r"**(\1)", s)
    s = re.sub(r"\^(" + NUM + r")", r"**\1", s)
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("−", "-")
    # implicit multiplication: 5 (..), ) (..), ) 5
    s = re.sub(r"(\d|\))\s*\(", r"\1*(", s)
    s = re.sub(r"\)\s*(\d)", r")*\1", s)
    return s


def decimals(token):
    return len(token.split(".")[1]) if "." in token else 0


def check_step(lhs, rhs):
    """Return None if skipped, True if it agrees, False if not."""
    rhs = rhs.strip().rstrip(",").strip()
    rhs_c = rhs.replace(r"\mathord{,}", "").replace("{,}", "")
    pct = rhs_c.endswith(r"\%")
    rhs_n = rhs_c[:-2] if pct else rhs_c
    if not re.fullmatch(NUM, rhs_n.strip()):
        return None
    if re.match(r"^[-+−]\s", lhs):
        return None          # continuation of an equation split over lines
    py = to_python(lhs)
    if re.search(r"[A-Za-z\\_]", py) or not re.search(r"\d", py):
        return None
    if not re.search(r"[*/+\-]", py.strip().lstrip("-")):
        return None          # a bare number, nothing to compute
    try:
        got = eval(py, {"__builtins__": {}}, {})
    except Exception:
        return None
    want = float(rhs_n)
    if pct:
        got *= 100
    # tolerance: rounding of the printed inputs and of the result
    ins = re.findall(NUM, lhs.replace(r"\mathord{,}", "").replace("{,}", ""))
    rel, absum = 0.0, 0.0
    for t in ins:
        v = abs(float(t))
        if v:
            rel = max(rel, 0.5 * 10 ** -decimals(t) / v)
            absum += 0.5 * 10 ** -decimals(t)
    tol = abs(want) * (3 * rel + 1e-9) + 0.6 * 10 ** -decimals(rhs_n) + absum + 1e-9
    if want == 0:
        # "... = 0" after a rounded rate: the residual scales with the terms
        tol = max(tol, 2e-3 * max((abs(float(t)) for t in ins), default=0))
    return abs(got - want) <= max(tol, 1e-6)


def steps(solution):
    for block in re.findall(r"\$\$(.*?)\$\$", solution, flags=re.S):
        for part in re.split(r"\\qquad|\\\\", block):
            pieces = part.split("=")
            if len(pieces) < 2:
                continue
            yield pieces[-2].strip(), pieces[-1].strip(), part.strip()


def main():
    rng = random.Random(3)
    total = bad = 0
    per_ch = {}
    good_items = set()
    for f in sorted((ROOT / "bank").glob("ch*/*.yaml")):
        for it in yaml.safe_load(f.read_text(encoding="utf-8")).get("items") or []:
            if not it.get("calc") or not it.get("solution"):
                continue
            ch = it["id"][:3]
            ok_item, fail_item = False, False
            runs = [{}] + [draw(it, rng) for _ in range(8 if it.get("random") else 0)]
            for vals in runs:
                env = compute(it, vals)
                sol = render(it["solution"], env)
                for lhs, rhs, whole in steps(sol):
                    r = check_step(lhs, rhs)
                    if r is None:
                        continue
                    total += 1
                    if r:
                        ok_item = True
                    else:
                        bad += 1
                        fail_item = True
                        print(f"{it['id']} {vals}: {whole[:160]}")
            tot, ok = per_ch.get(ch, (0, 0))
            per_ch[ch] = (tot + 1, ok + (ok_item and not fail_item))
            if ok_item and not fail_item:
                good_items.add(it["id"])
    (ROOT / "tools" / "equation_items.txt").write_text("\n".join(sorted(good_items)) + "\n", encoding="utf-8")
    for ch, (tot, ok) in sorted(per_ch.items()):
        print(f"{ch}: {ok} of {tot} items have printed steps that recompute correctly")
    print(f"{total} printed steps recomputed from the numbers shown, {bad} disagree")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
