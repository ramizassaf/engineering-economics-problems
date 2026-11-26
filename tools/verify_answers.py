"""Independent check of answers: recompute with numpy_financial, not with the bank's own calc lines.

Each check names an item, the variable in its computed environment, and an
independent formula. Run for the fixed numbers and for random draws."""
import math
import random
import sys
from pathlib import Path

import numpy_financial as npf
from datetime import date
from scipy.optimize import brentq
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
    # ---------------------------------------------------------------- chapter 2
    "c02-ex-ap-loan": {"A": lambda v: npf.pmt(v["i"], v["n"], -v["P"])},
    "c02-ex-amort": {"I3": lambda v: npf.ipmt(v["i"], 3, 5, -v["P"]), "Q4": lambda v: npf.ppmt(v["i"], 4, 5, -v["P"])},
    "c02-ex-pa-car": {"P": lambda v: npf.pv(v["i"], v["n"], -v["A"])},
    "c02-ex-fa-saving": {"F": lambda v: npf.fv(v["i"], v["n"], -v["A"], 0)},
    "c02-ex-af-retire": {"A": lambda v: npf.pmt(v["i"], v["n"], 0, -v["F"])},
    "c02-ex-deferred-pv": {"P0": lambda v: npf.npv(v["i"], [0] * v["s"] + [v["A"]] * (v["e"] - v["s"] + 1))},
    "c02-ex-machine-salvage": {"N": lambda v: -v["C"] + npf.pv(v["i"], v["n"], -v["S"], -v["R"])},
    "c02-ex-annuity-due": {"P": lambda v: npf.pv(v["i"], v["n"], -v["A"], 0, "begin")},
    "c02-ex-find-n": {"n": lambda v: npf.nper(v["i"], -v["A"], v["P"])},
    "c02-ex-gradient": {"P": lambda v: npf.npv(v["i"], [0] + [v["A1"] + v["G"] * (t - 1) for t in range(1, v["n"] + 1)])},
    "c02-ex-gradient-shift": {"P0": lambda v: npf.npv(v["i"], [0] * v["s"] + [v["A1"] + v["G"] * k for k in range(v["n"])])},
    "c02-ex-geometric": {"P": lambda v: npf.npv(v["i"], [0] + [v["A1"] * (1 + v["g"]) ** (t - 1) for t in range(1, v["n"] + 1)])},
    "c02-ex-irregular": {"P": lambda v: npf.npv(v["i"], [v["c0"], v["c1"], v["c2"], v["c3"], v["c4"], v["c5"]])},
    "c02-b-13": {"B": lambda v: npf.pv(v["i"], v["n"] - v["k"], -npf.pmt(v["i"], v["n"], -v["P"]))},
    "c02-b-18": {"RATEX": lambda v: npf.rate(v["n"], -v["A1"], v["P"], 0)},
    "c02-c-06": {"n": lambda v: npf.nper(v["i"], -v["A"], 0, v["F"])},
    "c02-c-10": {"r": lambda v: npf.rate(v["n"], -v["A"], 0, v["F"])},
    "c02-c-12": {"A": lambda v: npf.pmt(v["i"], v["n"], v["P"], -v["F"])},
    "c02-d-05": {"P": lambda v: npf.npv(v["i"], [0] + [v["A"]] * v["k"] + [v["B"]] * (v["n"] - v["k"]))},
    "c02-d-07": {"A": lambda v: npf.pmt(v["i"], v["n"], -npf.fv(v["i"], v["g"], 0, -v["P"]))},
    "c02-d-14": {"W": lambda v: npf.pmt(v["i"], v["n"], -npf.fv(v["i"], v["k"], 0, -npf.fv(v["i"], v["n"], -v["A"], 0)))},
    "c02-d-16": {"Bk": lambda v: last_payment(v["P"], v["A"], v["i"])},
    "c02-e-07": {"G": lambda v: solve_linear(lambda G: npf.npv(v["i"], [0] + [v["A1"] + G * (t - 1) for t in range(1, v["n"] + 1)]) - v["P"])},
    "c02-e-13": {"P": lambda v: npf.npv(v["i"], [-v["C"]] + [v["A1"] - v["G"] * (t - 1) for t in range(1, v["n"] + 1)])},
    "c02-f-08": {"A1": lambda v: solve_linear(lambda a: npf.npv(v["i"], [0] + [a * (1 + v["g"]) ** (t - 1) for t in range(1, v["n"] + 1)]) - v["P"])},
    "c02-g-07": {"r": lambda v: npf.irr([-v["C"]] + [v["A"]] * v["n"])},
    "c02-i-01": {"A1": lambda v: npf.pmt(0.08, 5, -30000, 10000)},
    "c02-i-02": {"N": lambda v: npf.npv(0.09, [-95000] + [14000 * (1.05 * 0.993) ** (t - 1) - (1500 + 100 * (t - 1)) for t in range(1, 21)])},
    "c02-i-03": {"W": lambda v: npf.pmt(0.06, 20, -npf.fv(0.06, 25, 0, -npf.npv(0.06, [0] + [1200 * 1.03 ** (t - 1) for t in range(1, 26)])))},
    # ---------------------------------------------------------------- chapter 3
    "c03-ex-monthly-payment": {"A": lambda v: npf.pmt(v["r"] / 12, 12 * v["y"], -v["P"])},
    "c03-ex-monthly-deposit": {"A": lambda v: npf.pmt((1 + v["ia"]) ** (1 / 12) - 1, 12 * v["y"], 0, -v["F"])},
    "c03-ex-pw-project": {"PW": lambda v: npf.npv(v["i"], [-v["C"]] + [v["R"]] * (v["n"] - 1) + [v["R"] + v["S"]])},
    "c03-ex-pw-cost": {"PW": lambda v: -npf.npv(v["i"], [-v["C"], -v["O"], -v["O"], -v["O"], -v["O"] - v["H"], -v["O"], -v["O"], -v["O"], -v["O"] + v["S"]])},
    "c03-ex-lcm": {"Pa": lambda v: -npf.npv(v["i"], lcm_flows(v["Ca"], v["Oa"], v["Sa"], 3, 12)),
                   "AWa": lambda v: -npf.pmt(v["i"], 12, -npf.npv(v["i"], lcm_flows(v["Ca"], v["Oa"], v["Sa"], 3, 12)))},
    "c03-ex-aw-project": {"AW": lambda v: npf.pmt(v["i"], v["n"], -npf.npv(v["i"], [-v["C"]] + [v["R"]] * (v["n"] - 1) + [v["R"] + v["S"]]))},
    "c03-ex-capital-recovery": {"CR2": lambda v: npf.pmt(v["i"], v["n"], -v["P"], v["S"])},
    "c03-ex-aw-irregular": {"AW": lambda v: npf.pmt(v["i"], 5, -npf.npv(v["i"], [-v["c0"], v["c1"], v["c2"], v["c3"], v["c4"], v["c5"]]))},
    "c03-ex-capcost-periodic": {"CC": lambda v: v["C"] + (v["M"] + npf.pmt(v["i"], v["k"], 0, -v["R"])) / v["i"]},
    "c03-ex-payback": {"nd": lambda v: npf.nper(v["i"], v["R"], -v["C"])},
    "c03-ex-breakeven": {"R": lambda v: npf.pmt(v["i"], v["n"], -v["C"], v["S"])},
    "c03-ex-monthly-project": {"PW": lambda v: npf.npv((1 + v["ia"]) ** (1 / 12) - 1, [-v["C"]] + [v["rent"]] * 119 + [v["rent"] + v["S"]])},
    "c03-b-10": {"B": lambda v: npf.fv(v["r"] / 12, 12 * v["k"], npf.pmt(v["r"] / 12, 12 * v["y"], -v["P"]), -v["P"])},
    "c03-b-11": {"im": lambda v: npf.rate(12 * v["y"], -v["A"], v["P"], 0)},
    "c03-c-04": {"PW": lambda v: npf.npv(v["i"], [-v["C"]] + [v["A1"] + v["G"] * (t - 1) for t in range(1, v["n"] + 1)])},
    "c03-c-10": {"PW": lambda v: npf.npv(v["i"], [-v["C"]] + [0] * v["d"] + [v["R"]] * v["n"])},
    "c03-d-05": {"R": lambda v: solve_linear(lambda X: npf.pv(v["i"], 8, -X, 0, "begin") - (v["C"] + npf.pv(v["i"], 8, -v["O"])))},
    "c03-e-03": {"Pb": lambda v: -npf.npv(v["i"], lcm_flows(v["Cb"], v["Ob"], v["Sb"], 6, 24))},
    "c03-f-04": {"AW": lambda v: npf.pmt(v["i"], v["n"], -npf.npv(v["i"], [v["C"]] + [v["O1"] + v["G"] * (t - 1) for t in range(1, v["n"] + 1)]))},
    "c03-f-08": {"AW": lambda v: npf.pmt(v["i"], 8, -npf.npv(v["i"], [v["C"]] + [v["O"]] * 3 + [v["O"] + v["H"]] + [v["O"]] * 3 + [v["O"] - v["S"]]))},
    "c03-g-08": {"CC": lambda v: v["C"] + npf.npv(v["i"], [0] + [v["M1"]] * 10) + v["M2"] / v["i"] / (1 + v["i"]) ** 10},
    "c03-h-05": {"x": lambda v: solve_linear(lambda x: npf.pmt(v["i"], v["n"], -v["Fa"]) + v["va"] * x - npf.pmt(v["i"], v["n"], -v["Fb"]) - v["vb"] * x)},
    "c03-i-08": {"r": lambda v: npf.rate(v["n"], v["Oa"] - v["Ob"], -(v["Cb"] - v["Ca"]), 0)},
    "c03-k-02": {"kmx": lambda v: solve_linear(lambda x: npf.pmt(0.10, 8, -140000, 20000) + 0.42 * x - npf.pmt(0.10, 10, -220000, 30000) - 4000 - 0.144 * x)},
    # ---------------------------------------------------------------- chapter 4
    "c04-ex-irr-trial": {"r": lambda v: npf.irr([-v["C"]] + [v["R"]] * 5 + [v["R"] + v["S"]])},
    "c04-ex-irr-annuity": {"r": lambda v: npf.irr([-v["C"]] + [v["R"]] * v["n"])},
    "c04-ex-irr-decision": {"r": lambda v: npf.irr([-v["C"]] + [v["R"]] * 7 + [v["R"] + v["S"]])},
    "c04-ex-irr-gradient": {"r": lambda v: npf.irr([-v["C"]] + [v["A1"] + v["G"] * k for k in range(5)])},
    "c04-ex-incremental-two": {"rdd": lambda v: npf.rate(8, v["dR"], -v["dC"], 0)},
    "c04-ex-incremental-three": {"r32": lambda v: npf.irr([-15000] + [3000] * 8)},
    "c04-ex-sign-test": {"r": lambda v: npf.irr([-20000, 8000, 9000, 10000, -4000])},
    "c04-ex-mirr": {"M": lambda v: npf.mirr([-v["c0"], v["c1"], v["c2"], v["c3"], v["c4"], v["c5"]], v["rr"], v["rr"])},
    "c04-ex-mirr-multiple": {"M": lambda v: npf.mirr([-1000, 2300, -1320], v["i"], v["i"])},
    "c04-ex-irr-monthly": {"im": lambda v: npf.rate(v["N"], v["A"], -v["P"], 0)},
    "c04-ex-loan-fees": {"re": lambda v: npf.rate(v["n"], npf.pmt(v["r"], v["n"], -v["L"]), -v["L"] * (1 - v["f"]), 0)},
    "c04-b-07": {"r": lambda v: npf.irr([-v["C"]] + [v["A1"] * (1 + v["g"]) ** k for k in range(8)])},
    "c04-b-10": {"r": lambda v: npf.rate(10, v["A"], -v["P"], 1000)},
    "c04-b-12": {"r": lambda v: npf.irr([-v["C"], 0, 0] + [v["R"]] * 6)},
    "c04-d-04": {"rd": lambda v: npf.irr([-v["dC"]] + [v["dO"]] * 5 + [v["dO"] + v["dS"]])},
    "c04-d-13": {"rd": lambda v: npf.irr([-(v["C"] - v["L"])] + [v["L"]] * 4 + [v["S"]])},
    "c04-f-06": {"M": lambda v: npf.mirr([-30000, 18000, -10000, 20000, 12000], v["fr"], v["rr"])},
    "c04-f-07": {"r": lambda v: npf.irr([-50000, 20000, 20000, 20000, 20000, -15000])},
    "c04-h-06": {"r": lambda v: brentq(lambda r: sum(x / (1 + r) ** ((d - date(2026, 1, 1)).days / 365) for x, d in [(-10000, date(2026, 1, 1)), (2750, date(2026, 3, 1)), (4250, date(2026, 10, 30)), (3250, date(2027, 2, 15)), (2750, date(2027, 4, 1))]), -0.5, 2)},
    "c04-j-01": {"rd": lambda v: npf.irr([-80000, 2000, 7000, 12000, 17000] + [22000] * 6),
                 "MB": lambda v: npf.mirr([-200000, 30000, 35000, 40000, 45000] + [50000] * 6, 0.12, 0.12)},
    "c04-j-02": {"im2": lambda v: npf.rate(36, npf.pmt(0.085 / 12, 36, -4500), -4410, 0)},
}


def lcm_flows(C, O, S, life, L):
    """Cost flows, costs positive, for an asset renewed every `life` years over L years."""
    f = [C] + [O] * L
    for t in range(life, L + 1, life):
        f[t] -= S
        if t < L:
            f[t] += C
    return [-x for x in f]


def last_payment(P, A, i):
    """Simulate the loan year by year and return the final, smaller payment."""
    b = P
    while True:
        b *= 1 + i
        if b <= A:
            return b
        b -= A


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
