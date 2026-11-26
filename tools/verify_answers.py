"""Independent check of answers: recompute with numpy_financial, not with the bank's own calc lines.

Each check names an item, the variable in its computed environment, and an
independent formula. Run for the fixed numbers and for random draws."""
import math
import random
import sys
from pathlib import Path

import numpy_financial as npf
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import compute, draw  # noqa: E402

fv = lambda i, n, p: npf.fv(i, n, 0, -p)
pv = lambda i, n, f: npf.pv(i, n, 0, -f)

CHECKS = {
    "c01-ex-simple-compound": {"B3": lambda v: fv(v["i"], 3, v["P"]), "S": lambda v: v["P"] * (1 + 3 * v["i"])},
    "c01-ex-fp-saving": {"F": lambda v: fv(v["i"], v["n"], v["P"])},
    "c01-ex-pf-target": {"P": lambda v: pv(v["i"], v["n"], v["F"])},
    "c01-ex-pf-line": {"P": lambda v: pv(v["i"], v["n"], v["F"])},
    "c01-ex-cfd-two-deposits": {"F": lambda v: fv(v["i"], v["n"], v["A"]) + fv(v["i"], v["n"] - v["t"], v["B"])},
    "c01-ex-pv-several": {"P": lambda v: npf.npv(v["i"], [0, v["A"], 0, v["B"], 0, v["C"]])},
    "c01-ex-loan-second": {"x": lambda v: pv(v["i"], v["n"] - v["t"], v["R"]) - fv(v["i"], v["t"], v["L"])},
    "c01-ex-equiv-table": {"P2": lambda v: npf.npv(v["i"], [v["a0"], v["a1"], v["a2"], 0, 0, v["a5"], v["a6"]]) * (1 + v["i"]) ** 2,
                           "P5": lambda v: npf.npv(v["i"], [v["a0"], v["a1"], v["a2"], 0, 0, v["a5"], v["a6"]]) * (1 + v["i"]) ** 5},
    "c01-ex-two-payments": {"X": lambda v: solve_linear(lambda X: pv(v["i"], v["t1"], X / 2) + pv(v["i"], v["t2"], X) - v["L"])},
    "c01-ex-find-i": {"i": lambda v: npf.rate(v["n"], 0, -v["P"], v["F"])},
    "c01-ex-double": {"n": lambda v: npf.nper(v["i"], 0, -1, 2)},
    "c01-ex-find-n": {"n": lambda v: npf.nper(v["i"], 0, -v["P"], v["F"])},
    "c01-b-02": {"F": lambda v: fv(v["i"], v["n"], v["P"])},
    "c01-b-13": {"B3": lambda v: v["P"] * (1 + v["i1"]) ** 2 * (1 + v["i2"])},
    "c01-c-04": {"r": lambda v: npf.rate(v["n"], 0, -v["P"], v["S"])},
    "c01-c-16": {"PV": lambda v: pv(v["i"], v["n"], v["F"])},
    "c01-d-03": {"X": lambda v: fv(v["i"], 4, fv(v["i"], 1, v["L"]) - v["a"])},
    "c01-d-04": {"X": lambda v: solve_linear(lambda X: pv(v["i"], v["a"], X / 2) + pv(v["i"], v["b"], X) - v["L"])},
    "c01-d-05": {"X": lambda v: solve_linear(lambda X: pv(v["i"], 3, X / 2) + pv(v["i"], 6, X) + pv(v["i"], 9, X / 2) - v["L"])},
    "c01-d-07": {"X": lambda v: solve_linear(lambda X: fv(v["i"], v["n"], v["A"]) + fv(v["i"], v["n"] - v["t"], X) - v["F"])},
    "c01-d-08": {"P3": lambda v: npf.npv(v["i"], [v["c0"], v["c1"], v["c2"], 0, 0, v["c5"], v["c6"], v["c7"], 0, v["c9"]]) * (1 + v["i"]) ** 3},
    "c01-d-14": {"Y": lambda v: solve_linear(lambda Y: pv(v["i"], v["a"], v["x"]) + pv(v["i"], v["b"], Y) - v["L"])},
    "c01-d-17": {"X": lambda v: solve_linear(lambda X: pv(v["i"], v["a"], X) + pv(v["i"], v["b"], X) - (v["P"] - v["D0"]))},
    "c01-d-19": {"X": lambda v: solve_linear(lambda X: npf.npv(v["i"], [0, 0, X, 0, X, 0, X]) - v["L"])},
    "c01-d-20": {"X": lambda v: solve_linear(lambda X: fv(v["i"], 8, X) + fv(v["i"], 6, X) + fv(v["i"], 4, X) - v["F"])},
    "c01-d-21": {"N": lambda v: npf.npv(v["i"], [-v["C"], v["R1"], v["R2"], v["R3"]])},
    "c01-d-25": {"F": lambda v: fv(v["i"], 6, v["P"]) + fv(v["i"], 4, v["a"]) - fv(v["i"], 1, v["b"])},
    "c01-e-01": {"i": lambda v: npf.rate(v["n"], 0, -v["P"], v["F"])},
    "c01-e-02": {"n": lambda v: npf.nper(v["i"], 0, -1, 3)},
    "c01-e-07": {"n": lambda v: npf.nper(v["i"], 0, -v["P"], v["F"])},
    "c01-f-05": {"P": lambda v: npf.npv(v["i"], [v["c0"], v["c1"], v["c2"], v["c3"], v["c4"], v["c5"]])},
    "c01-f-08": {"X": lambda v: solve_linear(lambda X: pv(v["i"], v["a"], X / 2) + pv(v["i"], v["b"], X) - v["L"])},
    "c01-h-01": {"B4": lambda v: sum(fv(0.05, k, 4000) for k in (1, 2, 3, 4)),
                 "Y": lambda v: solve_linear(lambda Y: pv(0.08, 1, Y / 2) + pv(0.08, 3, Y) - sum(fv(0.05, k, 4000) for k in (1, 2, 3, 4)))},
    "c01-h-02": {"r": lambda v: npf.rate(3, 0, -60000, 75000)},
    "c01-h-03": {"F10": lambda v: fv(0.07, 6, fv(0.05, 4, 20000))},
}


def solve_linear(f):
    """Root of a function that is linear in its argument."""
    a, b = f(0.0), f(1.0)
    return -a / (b - a)


def main():
    items = {}
    for f in sorted((ROOT / "bank").glob("ch*/*.yaml")):
        for it in yaml.safe_load(f.read_text(encoding="utf-8")).get("items", []):
            items[it["id"]] = it
    rng = random.Random(7)
    bad = n = 0
    for iid, checks in CHECKS.items():
        it = items[iid]
        runs = [{}] + [draw(it, rng) for _ in range(20 if it.get("random") else 0)]
        for vals in runs:
            env = compute(it, vals)
            for var, f in checks.items():
                n += 1
                got, exp = env[var], float(f(env))
                if not math.isclose(got, exp, rel_tol=1e-9, abs_tol=1e-6):
                    bad += 1
                    print(f"{iid} {var}: bank {got} vs independent {exp}  values={vals}")
    print(f"{len(CHECKS)} items, {n} answers checked independently, {bad} differ")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
