"""Reference tests for the interest factors and root finders, independent of the bank.

Every factor is compared with a year-by-year sum written here from its
definition, at ordinary rates, at zero, near zero, and with i close to g.
The root finders are tested for a root inside the range, a root near an end,
no root at all, and flows with two roots. The same cases are written to
JSON so tools/test_factors.mjs can run them on the JavaScript engine.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ee.engine as E  # noqa: E402


def s_pa(i, n):
    return sum((1 + i) ** -k for k in range(1, n + 1))


def s_fa(i, n):
    return sum((1 + i) ** (n - k) for k in range(1, n + 1))


def s_pg(i, n):
    return sum((k - 1) * (1 + i) ** -k for k in range(1, n + 1))


def s_pgeo(g, i, n):
    return sum((1 + g) ** (k - 1) * (1 + i) ** -k for k in range(1, n + 1))


cases, fails = [], []


def check(name, got, want, tol=1e-9, atol=1e-12):
    ok = math.isclose(got, want, rel_tol=tol, abs_tol=atol)
    if not ok:
        fails.append(f"{name}: got {got!r}, want {want!r}")


rates = [0.0, 1e-12, 1e-9, 1e-7, 1e-6, 2e-6, 1e-4, 0.01, 0.05, 0.10, 0.25, -0.05]
for i in rates:
    for n in [1, 2, 5, 10, 25, 60]:
        want = {"PA": s_pa(i, n), "FA": s_fa(i, n), "PG": s_pg(i, n)}
        want["AP"] = 1 / want["PA"]
        want["AF"] = 1 / want["FA"]
        want["AG"] = want["PG"] / want["PA"]
        want["FP"] = (1 + i) ** n
        want["PF"] = (1 + i) ** -n
        for name, w in want.items():
            got = getattr(E, name)(i, n)
            # Closed forms lose about 1e-16 / i of relative precision; allow it just above SMALL.
            tol = 1e-9 if abs(i) >= 1e-4 or abs(i) < E.SMALL else 1e-6
            check(f"{name}({i}, {n})", got, w, tol)
            cases.append({"f": name, "args": [i, n], "want": w, "tol": tol})
        # identities
        check(f"A/P = A/F + i at {i},{n}", E.AP(i, n), E.AF(i, n) + i, 1e-8)
        check(f"F/A = P/A * F/P at {i},{n}", E.FA(i, n), E.PA(i, n) * E.FP(i, n), 1e-8)
        check(f"A/G = P/G / P/A at {i},{n}", E.AG(i, n), E.PG(i, n) / E.PA(i, n), 1e-12)

# limits written out
for n in [1, 4, 10]:
    check(f"PG(0,{n})", E.PG(0, n), n * (n - 1) / 2)
    check(f"AG(0,{n})", E.AG(0, n), (n - 1) / 2)

for g, i in [(0.05, 0.05), (0.05, 0.05 + 1e-9), (0.05, 0.05 - 1e-9), (0.05, 0.05 + 3e-6),
             (0.0, 0.08), (0.08, 0.0), (-0.03, 0.06), (0.12, 0.08)]:
    for n in [1, 5, 20]:
        w = s_pgeo(g, i, n)
        tol = 1e-9 if abs(i - g) < E.SMALL or abs(i - g) > 1e-4 else 1e-6
        check(f"PGEO({g},{i},{n})", E.PGEO(g, i, n), w, tol)
        cases.append({"f": "PGEO", "args": [g, i, n], "want": w, "tol": tol})

# root finders: a root inside, near the lower end, and solved back
for n, A, P in [(5, 3000, 10000), (10, 1200, 10000), (4, 2500.01, 10000), (8, 1250, 10000)]:
    r = E.RATE(n, A, P)
    check(f"RATE({n},{A},{P}) solves", A * E.PA(r, n), P, 1e-9)
    cases.append({"f": "RATE", "args": [n, A, P], "want": r, "tol": 1e-9})
for n, A, F in [(5, 1000, 6000), (10, 500, 8000)]:
    r = E.RATEF(n, A, F)
    check(f"RATEF({n},{A},{F}) solves", A * E.FA(r, n), F, 1e-9)
    cases.append({"f": "RATEF", "args": [n, A, F], "want": r, "tol": 1e-9})
r = E.GROWTH(1000, 9000, 0.08, 10)
check("GROWTH solves", 1000 * E.PGEO(r, 0.08, 10), 9000, 1e-9)
cases.append({"f": "GROWTH", "args": [1000, 9000, 0.08, 10], "want": r, "tol": 1e-9})
flows = [-10000, 3000, 3000, 3000, 3000, 3000]
r = E.IRR(flows)
check("IRR solves", E.NPV(r, flows), 0, 1e-9, 1e-6)
cases.append({"f": "IRR", "args": [flows], "want": r, "tol": 1e-9})
# a rate above 100%, found by the wider range
r = E.RATE(2, 9000, 5000)
check("RATE above 100%", 9000 * E.PA(r, 2), 5000, 1e-9)
# a negative rate: payments add to less than the price
r = E.RATE(5, 1800, 10000)
check("RATE negative", 1800 * E.PA(r, 5), 10000, 1e-9)
if not r < 0:
    fails.append("RATE(5, 1800, 10000) should be negative")

# must raise, not return an end point
must_fail = [
    ("RATE with no root", lambda: E.RATE(5, -100, 10000)),
    ("IRR of flows that never change sign", lambda: E.IRR([1000, 500, 500])),
    ("IRR with two roots and the range around both", lambda: E.IRR([-1000, 3000, -2200], -0.5, 1.0)),
    ("PA at -100%", lambda: E.PA(-1, 5)),
    ("PA with negative n", lambda: E.PA(0.1, -2)),
    ("factor with infinite input", lambda: E.FP(float("inf"), 5)),
]
for name, fn in must_fail:
    try:
        fn()
        fails.append(f"{name}: returned a value instead of raising")
    except ValueError:
        pass
    cases.append({"f": "raises", "name": name})

# two roots: each found when the range holds only one
flows2 = [-1000, 3000, -2200]
for lo, hi in [(0.0, 0.5), (0.5, 1.0)]:
    r = E.IRR(flows2, lo, hi)
    check(f"IRR two roots in [{lo},{hi}]", E.NPV(r, flows2), 0, 1e-6, 1e-6)

from scipy.stats import norm  # noqa: E402
for z in [-9, -8.5, -6, -3.2, -1.96, -1, -0.3, 0, 0.25, 1, 1.645, 2.5, 4, 7.9, 9]:
    w = float(norm.cdf(z))
    check(f"NORMS({z})", E.NORMS(z), w, 1e-12, 1e-15)
    cases.append({"f": "NORMS", "args": [z], "want": w, "tol": 1e-12})

json.dump(cases, open("/tmp/ee-factor-cases.json", "w"))
if fails:
    print("\n".join(fails))
    raise SystemExit(f"{len(fails)} factor tests failed")
print(f"{len(cases)} factor and root cases match their definitions; bad inputs raise")
