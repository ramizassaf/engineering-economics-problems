"""Independent check of answers: recompute with numpy_financial, not with the bank's own calc lines.

Each check names an item, the variable in its computed environment, and an
independent formula. Run for the fixed numbers and for random draws."""
import math
import random
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm
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
    # ---------------------------------------------------------------- chapter 5
    "c05-ex-ddb-switch": {"D3": lambda v: ddb_sched(v["B"], v["S"], 6)[2], "b6": lambda v: v["B"] - sum(ddb_sched(v["B"], v["S"], 6))},
    "c05-ex-syd": {"D2": lambda v: syd_sched(v["B"], v["S"], 5)[1]},
    "c05-ex-compare-pv": {"TD": lambda v: v["t"] * npf.npv(v["i"], [0] + ddb_sched(v["B"], 0, 5)),
                          "TY": lambda v: v["t"] * npf.npv(v["i"], [0] + syd_sched(v["B"], 0, 5))},
    "c05-ex-tax-basic": {"CF": lambda v: (v["R"] - v["O"]) * (1 - v["t"]) + v["t"] * v["B"] / 5},
    "c05-ex-tax-shield": {"P": lambda v: npf.pv(v["i"], v["n"], -v["t"] * v["B"] / v["n"])},
    "c05-ex-disposal-gain": {"net": lambda v: v["M"] - v["t"] * (v["M"] - (v["B"] - v["k"] * v["B"] / v["n"]))},
    "c05-c-07": {"D4": lambda v: ddb_sched(v["B"], 0, 5)[3]},
    "c05-c-09": {"dd": lambda v: npf.npv(v["i"], [0] + ddb_sched(v["B"], 0, 5))},
    "c05-e-02": {"half": lambda v: npf.npv(v["i"], [0, v["B"] / v["n"] / 2] + [v["B"] / v["n"]] * (v["n"] - 1) + [v["B"] / v["n"] / 2])},
    "c05-j-01": {"Pdd": lambda v: 0.15 * npf.npv(0.10, [0] + ddb_sched(165000, 0, 6))},
    # ---------------------------------------------------------------- chapter 6
    "c06-ex-breakeven": {"Q": lambda v: solve_linear(lambda q: v["p"] * q - v["F"] - v["v"] * q)},
    "c06-ex-target-profit": {"Q": lambda v: solve_linear(lambda q: (v["p"] - v["v"]) * q - v["F"] - v["T"])},
    "c06-ex-high-low": {"F": lambda v: np.polyfit([v["h1"], v["h2"]], [v["c1"], v["c2"]], 1)[1]},
    "c06-ex-two-processes": {"x": lambda v: solve_linear(lambda q: v["F1"] + v["v1"] * q - v["F2"] - v["v2"] * q)},
    "c06-ex-lcc": {"Pb": lambda v: v["Cb"] - npf.pv(v["i"], 10, v["Eb"] + v["M"])},
    "c06-ex-unit-lcc": {"u": lambda v: (npf.pmt(v["i"], v["n"], -v["C"]) + v["O"]) / v["U"]},
    "c06-c-12": {"Q": lambda v: v["F"] / (v["s"] * (v["pa"] - v["va"]) + (1 - v["s"]) * (v["pb"] - v["vb"]))},
    "c06-h-06": {"x": lambda v: solve_linear(lambda k: v["Cd"] - npf.pv(v["i"], 10, v["Fd"] * k) - v["Ce"] + npf.pv(v["i"], 10, v["Fe"] * k + v["M"]))},
    "c06-k-03": {"Pb": lambda v: 32000 - npf.pv(0.10, 8, 450 + 600) - 4000 / 1.1 ** 8},
    # ch07: project cash flows, rebuilt year by year from an income statement
    "c07-ex-operating": {"CF": lambda v: inc_cf(v["R"], v["O"], v["C"] / 5, v["t"])},
    "c07-ex-simple": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"], 0, v["t"], [v["C"] / 3] * 3))},
    "c07-ex-salvage": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"], v["M"], v["t"], [v["C"] / 3] * 3))},
    "c07-ex-working-capital": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], v["W"], v["R"], v["O"], v["M"], v["t"], [v["C"] / 3] * 3))},
    "c07-ex-full": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], v["W"], v["R"], v["O"], v["M"], v["t"], [v["C"] / 5] * 5)),
                    "r": lambda v: npf.irr(proj(v["C"], v["W"], v["R"], v["O"], v["M"], v["t"], [v["C"] / 5] * 5))},
    "c07-ex-ddb": {"P_dd": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"], 0, v["t"], ddb_sched(v["C"], 0, 5)))},
    "c07-ex-loan": {"PWe": lambda v: npf.npv(v["i"], equity(v["C"], v["L"], v["r"], v["R"], v["O"], v["t"], 3))},
    "c07-ex-cost-saving": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["Sv"], 0, 0, v["t"], [v["C"] / v["n"]] * int(v["n"])))},
    "c07-ex-two-machines": {"Aa": lambda v: npf.pmt(v["i"], 4, npf.npv(v["i"], proj(v["Ca"], 0, 0, v["Oa"], 0, v["t"], [v["Ca"] / 4] * 4))),
                            "Ab": lambda v: npf.pmt(v["i"], 6, npf.npv(v["i"], proj(v["Cb"], 0, 0, v["Ob"], 0, v["t"], [v["Cb"] / 6] * 6)))},
    "c07-ex-irr-tax": {"ra": lambda v: npf.irr(proj(v["C"], 0, v["R"], 0, 0, v["t"], [v["C"] / v["n"]] * int(v["n"])))},
    "c07-ex-breakeven": {"R": lambda v: solve_linear(lambda R: npf.npv(v["i"], proj(v["C"], 0, R, v["O"], 0, v["t"], [v["C"] / v["n"]] * int(v["n"]))))},
    "c07-ex-sensitivity": {"xR": lambda v: brentq(lambda x: npf.npv(v["i"], proj(v["C"], v["W"], v["R"] * (1 + x), v["O"], v["M"], v["t"], [v["C"] / 5] * 5)), -5, 5),
                           "xC": lambda v: brentq(lambda x: npf.npv(v["i"], proj(v["C"] * (1 + x), v["W"], v["R"], v["O"], v["M"], v["t"], [v["C"] * (1 + x) / 5] * 5)), -5, 5)},
    "c07-ex-scenarios": {"Pp": lambda v: npf.npv(v["i"], proj(v["C"], v["W"], 0.85 * v["R"], 1.1 * v["O"], 0.5 * v["M"], v["t"], [v["C"] / 5] * 5))},
    "c07-d-17": {"xO": lambda v: brentq(lambda x: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"] * (1 + x), 0, v["t"], [v["C"] / v["n"]] * int(v["n"]))), -50, 50)},
    "c07-d-19": {"r": lambda v: npf.irr(proj(v["C"], 0, v["R"], v["O"], 0, v["t"], [v["C"] / v["n"]] * int(v["n"])))},
    "c07-b-05": {"Dx": lambda v: v["D"]},
    "c07-b-12": {"CF": lambda v: inc_cf(v["R"], v["O"], v["D"], v["t"])},
    "c07-c-03": {"NS": lambda v: v["M"] - v["t"] * (v["M"] - (v["C"] - v["k"] * v["C"] / v["N"]))},
    "c07-c-04": {"NS": lambda v: v["M"] - v["t"] * (v["M"] - (v["C"] - sum(ddb_plain(v["C"], v["n"])[:int(v["k"])])))},
    "c07-c-13": {"M": lambda v: solve_linear(lambda M: M - v["t"] * (M - v["B"]) - v["X"])},
    "c07-d-04": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], v["W"], v["R"], v["O"], v["M"], v["t"], [v["C"] / 5] * 5)),
                 "r": lambda v: npf.irr(proj(v["C"], v["W"], v["R"], v["O"], v["M"], v["t"], [v["C"] / 5] * 5))},
    "c07-d-06": {"PW": lambda v: npf.npv(v["i"], [-v["C"]] + [inc_cf(v["R"] * (1 + v["g"]) ** k, v["O"] * (1 + v["h"]) ** k, v["C"] / 4, v["t"]) for k in range(4)])},
    "c07-d-07": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"], 0, v["t"], ddb_sched(v["C"], 0, 4)))},
    "c07-d-09": {"P": lambda v: npf.npv(v["i"], [0] + [v["t"] * d for d in syd_sched(v["C"], 0, 5)])},
    "c07-d-10": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"], v["M"], v["t"], [(v["C"] - v["S"]) / 5] * 5))},
    "c07-d-11": {"PW": lambda v: npf.npv(v["i"], proj(v["C"], 0, v["R"], v["O"], v["M"], v["t"], [v["C"] / v["N"]] * 4))},
    "c07-d-13": {"p": lambda v: solve_linear(lambda p: npf.npv(v["i"], proj(v["C"], 0, v["Q"] * p, v["Q"] * v["v"] + v["F"], 0, v["t"], [v["C"] / v["n"]] * int(v["n"]))))},
    "c07-d-14": {"C": lambda v: solve_linear(lambda C: npf.npv(v["i"], proj(C, 0, v["R"], v["O"], 0, v["t"], [C / v["n"]] * int(v["n"]))))},
    "c07-e-02": {"I2": lambda v: -npf.ipmt(v["r"], 2, 3, v["L"]), "I3": lambda v: -npf.ipmt(v["r"], 3, 3, v["L"])},
    "c07-e-05": {"P": lambda v: npf.npv(v["i"], [v["L"]] + [npf.pmt(v["r"], 3, v["L"]) - v["t"] * npf.ipmt(v["r"], k, 3, v["L"]) for k in (1, 2, 3)])},
    "c07-e-06": {"PWe": lambda v: npf.npv(v["i"], equity_bullet(v["C"], v["L"], v["r"], v["R"], v["O"], v["t"], 3))},
    "c07-e-07": {"k": lambda v: npf.irr([-v["L"] * (1 - v["fee"])] + [v["L"] * v["r"] * (1 - v["t"])] * 4 + [v["L"] * v["r"] * (1 - v["t"]) + v["L"]])},
    "c07-e-08": {"I": lambda v: sum(v["L"] * (1 - k / v["n"]) * v["r"] for k in range(int(v["n"])))},
    "c07-e-09": {"re": lambda v: npf.irr([-(v["C"] - v["L"])] + [v["CF"] - v["L"] * v["r"] * (1 - v["t"])] * 4 + [v["CF"] - v["L"] * v["r"] * (1 - v["t"]) - v["L"]])},
    "c07-f-03": {"Sv": lambda v: solve_linear(lambda s: npf.npv(v["i"], proj(v["C"], 0, s, 0, 0, v["t"], [v["C"] / v["n"]] * int(v["n"]))))},
    "c07-f-08": {"Ao": lambda v: npf.pmt(v["i"], v["n"], npf.npv(v["i"], [-(v["M"] - v["t"] * (v["M"] - v["B"]))] + [-v["Oo"] * (1 - v["t"]) + v["t"] * v["B"] / v["n"]] * int(v["n"]))),
                 "An": lambda v: npf.pmt(v["i"], v["n"], npf.npv(v["i"], proj(v["C"], 0, 0, v["Onw"], 0, v["t"], [v["C"] / v["n"]] * int(v["n"]))))},
    "c07-f-10": {"r": lambda v: npf.irr(proj(v["C"], 0, v["Sv"], 0, 0, v["t"], [v["C"] / v["n"]] * int(v["n"])))},
    "c07-f-12": {"C": lambda v: solve_linear(lambda C: npf.npv(v["i"], proj(C, 0, v["Sv"], 0, 0, v["t"], [C / v["n"]] * int(v["n"]))))},
    "c07-g-04": {"R": lambda v: solve_linear(lambda R: npf.npv(v["i"], proj(v["C"], v["W"], R, v["O"], v["M"], v["t"], [v["C"] / 5] * 5)))},
    "c07-i-01": {"PW": lambda v: npf.npv(0.11, proj(96000, 8000, 75000, 32000, 10000, 0.15, [19200] * 5)),
                 "r": lambda v: npf.irr(proj(96000, 8000, 75000, 32000, 10000, 0.15, [19200] * 5)),
                 "Rb": lambda v: solve_linear(lambda R: npf.npv(0.11, proj(96000, 8000, R, 32000, 10000, 0.15, [19200] * 5)))},
    "c07-i-02": {"Cmax": lambda v: solve_linear(lambda C: npf.pmt(0.10, 5, npf.npv(0.10, proj(C, 0, 0, 14000, 0, 0.2, [C / 5] * 5)))
                 - npf.pmt(0.10, 5, npf.npv(0.10, [-(9000 + 0.2 * 3000)] + [-28000 * 0.8 + 0.2 * 2400] * 5)))},
    "c07-i-03": {"PWe": lambda v: npf.npv(0.10, [-15000] + [11000 * 1.04 ** k * 0.8 + 0.2 * 45000 / 8 - (npf.pmt(0.06, 4, -30000) + 0.2 * npf.ipmt(0.06, k + 1, 4, 30000) if k < 4 else 0) for k in range(8)])},

    # ch08: inflation and exchange rates, rebuilt from actual-dinar flows
    "c08-ex-index": {"fa": lambda v: npf.rate(3, 0, -100, v["I3"])},
    "c08-ex-purchasing": {"R": lambda v: pv(v["f"], v["n"], v["F"])},
    "c08-ex-market-rate": {"im": lambda v: npf.rate(1, 0, -1, (1 + v["ir"]) * (1 + v["f"]))},
    "c08-ex-two-ways": {"P1": lambda v: npf.npv(v["im"], [-v["C"]] + [v["R"] * (1 + v["f"]) ** k for k in range(1, 5)])},
    "c08-ex-fixed-contract": {"P": lambda v: npf.npv(v["ir"], [0] + [v["A"] / (1 + v["f"]) ** k for k in range(1, int(v["n"]) + 1)])},
    "c08-ex-growing-cost": {"P1": lambda v: npf.npv(v["im"], [0] + [v["A1"] * (1 + v["f"]) ** (k - 1) for k in range(1, int(v["n"]) + 1)])},
    "c08-ex-differential": {"P": lambda v: npf.npv(v["im"], [-v["C"]] + [v["R"] * (1 + v["f"]) ** k - v["E"] * (1 + v["g"]) ** k for k in range(1, 6)])},
    "c08-ex-tax": {"P1": lambda v: npf.npv(v["im"], [-v["C"]] + [inc_cf(v["X"] * (1 + v["f"]) ** k, 0, v["C"] / v["n"], v["t"]) for k in range(1, int(v["n"]) + 1)])},
    "c08-ex-loan": {"rr": lambda v: npf.irr([-v["L"]] + [v["A"] / (1 + v["f"]) ** k for k in (1, 2, 3)])},
    "c08-ex-savings": {"R": lambda v: fv(v["r"], v["n"], v["P"]) / (1 + v["f"]) ** v["n"]},
    "c08-ex-exchange": {"P": lambda v: npf.npv(v["im"], [-v["C"]] + [v["U"] * v["e0"] * (1 + v["d"]) ** k - v["O"] for k in (1, 2, 3)])},
    "c08-ex-currency-rate": {"iu": lambda v: brentq(lambda x: (1 + x) * (1 + v["d"]) - (1 + v["idn"]), -0.5, 1.0)},
    "c08-b-02": {"fa": lambda v: npf.rate(v["n"], 0, -100, v["In"])},
    "c08-b-10": {"k": lambda v: npf.nper(v["f"], 0, -1, 2)},
    "c08-c-06": {"im": lambda v: npf.rate(v["n"], 0, -v["P"], v["X"] * (1 + v["f"]) ** v["n"])},
    "c08-c-11": {"A": lambda v: npf.pmt(v["im"], v["n"], 0, -v["X"] * (1 + v["f"]) ** v["n"])},
    "c08-c-12": {"A1": lambda v: solve_linear(lambda a: sum(a * (1 + v["f"]) ** (k - 1) * (1 + v["im"]) ** (v["n"] - k) for k in range(1, int(v["n"]) + 1)) - v["X"] * (1 + v["f"]) ** v["n"])},
    "c08-d-04": {"P": lambda v: npf.npv(v["im"], [0] + [v["A1"] * (1 + v["f"]) ** (k - 1) for k in range(1, int(v["n"]) + 1)])},
    "c08-d-05": {"PW": lambda v: npf.npv(v["im"], [-v["C"]] + [v["R"] - v["O"] * (1 + v["f"]) ** k for k in range(1, 5)])},
    "c08-d-09": {"rm": lambda v: npf.irr([-v["C"]] + [v["R"] * (1 + v["f"]) ** k for k in range(1, int(v["n"]) + 1)])},
    "c08-d-11": {"P1": lambda v: perpetuity_growing(v["A1"], v["f"], v["im"])},
    "c08-e-02": {"P1": lambda v: npf.npv(v["im"], [0] + [v["E1"] * (1 + v["g"]) ** (k - 1) for k in range(1, int(v["n"]) + 1)])},
    "c08-e-05": {"k": lambda v: brentq(lambda k: v["R"] * (1 + v["f"]) ** k - v["E"] * (1 + v["g"]) ** k, 0, 500)},
    "c08-e-11": {"g": lambda v: brentq(lambda g: npf.npv(v["im"], [-v["C"]] + [v["S1"] * (1 + g) ** (k - 1) for k in range(1, int(v["n"]) + 1)]), -0.5, 1.0)},
    "c08-f-02": {"PW": lambda v: npf.npv(v["im"], [-v["C"]] + [inc_cf(v["X"] * (1 + v["f"]) ** k, 0, v["C"] / 3, v["t"]) for k in (1, 2, 3)])},
    "c08-f-03": {"rr": lambda v: npf.irr([-v["C"]] + [inc_cf(v["X"] * (1 + v["f"]) ** k, 0, v["C"] / 3, v["t"]) / (1 + v["f"]) ** k for k in (1, 2, 3)])},
    "c08-f-06": {"G": lambda v: v["L"] - npf.pv(v["im"], v["n"], -npf.pmt(v["r"], v["n"], -v["L"]))},
    "c08-f-08": {"R": lambda v: (v["C"] * (1 + v["f"]) ** v["n"] - v["t"] * (v["C"] * (1 + v["f"]) ** v["n"] - v["C"])) / (1 + v["f"]) ** v["n"]},
    "c08-g-05": {"P1": lambda v: npf.npv(v["idn"], [-v["C"] * v["e0"]] + [v["U"] * v["e0"] * (1 + v["d"]) ** k for k in (1, 2, 3)])},
    "c08-g-09": {"k": lambda v: npf.irr([-1, (1 + v["ru"]) * (1 + v["d"])])},
    "c08-h-02": {"p6": lambda v: npf.npv(v["ir"] + 0.06 + v["ir"] * 0.06, [-v["C"]] + [inc_cf(v["X"] * 1.06 ** k, 0, v["C"] / v["n"], v["t"]) for k in range(1, int(v["n"]) + 1)])},
    "c08-j-01": {"PW": lambda v: npf.npv(1.07 * 1.06 - 1, [-120000] + [inc_cf(70000 * 1.06 ** k - 15000 * 1.1 ** k - 18000 * 1.05 ** k, 0, 24000, 0.15) for k in range(1, 6)]) + 20000 * 1.06 ** 5 * 0.85 / (1.07 * 1.06) ** 5},
    "c08-j-02": {"A1": lambda v: solve_linear(lambda a: sum(a * 1.05 ** (k - 1) * 1.08 ** (6 - k) for k in range(1, 7)) - 30000 * 1.05 ** 6)},
    "c08-j-03": {"Pi": lambda v: 90000 * 0.71 + npf.npv(0.12, [0] + [6000 * 1.08 ** k + 2000 * 0.71 * 1.02 ** k for k in range(1, 7)])},

    # ch09: replacement, rebuilt from cash flows with numpy_financial
    "c09-ex-outsider": {"Ad": lambda v: npf.pmt(v["i"], v["nd"], -v["M"], v["Sd"]) + v["Od"],
                        "Ac": lambda v: npf.pmt(v["i"], v["nc"], -v["C"], v["Sc"]) + v["Oc"]},
    "c09-ex-esl": {"m": lambda v: min(esl_aw(v["C"], [v["C"] * (v["a"] - v["b"] * k) for k in range(6)], v["O1"], v["G"], v["i"]))},
    "c09-ex-marginal": {"c3": lambda v: v["M0"] * (1 - v["d"]) ** 2 * (1 + v["i"]) - v["M0"] * (1 - v["d"]) ** 3 + v["Od"] + 2 * v["G"]},
    "c09-ex-study": {"Pb": lambda v: npf.npv(v["i"], [v["M"], v["Od"], v["Od"] + v["G"] - v["Sd2"] + v["C"], v["Oc"], v["Oc"], v["Oc"] - v["S3"]])},
    "c09-ex-tax": {"Ad": lambda v: -npf.pmt(v["i"], v["n"], npf.npv(v["i"], [v["M"] - v["t"] * (v["M"] - v["B"])] + [v["Od"] * (1 - v["t"]) - v["t"] * v["B"] / v["n"]] * int(v["n"])))},
    "c09-c-05": {"Ad": lambda v: npf.pmt(v["i"], v["n"], -v["M"]) - npf.pmt(v["i"], v["n"], npf.npv(v["i"], [0] + [v["Od"] + v["G"] * k for k in range(int(v["n"]))]))},
    "c09-c-09": {"Pd": lambda v: npf.npv(v["i"], [v["M"]] + [v["Od"]] * int(v["nd"]) + [0] * int(6 - v["nd"])) + (v["C"] + npf.pv(v["i"], 6 - v["nd"], -v["Oc"])) / (1 + v["i"]) ** v["nd"]},
    "c09-d-05": {"m": lambda v: min(esl_aw(v["C"], [0] * 8, v["O1"], v["G"], v["i"]))},
    "c09-d-07": {"t5": lambda v: esl_aw(v["C"], [v["C"] * (v["a"] - v["b"] * k) for k in range(5)], v["O1"], v["G"], v["i"])[4]},
    "c09-d-09": {"t4": lambda v: -npf.pmt(v["i"], 4, npf.npv(v["i"], [v["C"], v["O1"], v["O2"], v["O3"], v["O4"] - v["M4"]]))},
    "c09-e-07": {"Pw": lambda v: v["mc"] / (1 + v["i"]) + perpetuity_growing(v["Ac"], 0, v["i"], 6000) / (1 + v["i"])},
    "c09-f-02": {"Pb": lambda v: npf.npv(v["i"], [v["M"], v["Od"] - v["S1"] + v["C"], v["Oc"], v["Oc"], v["Oc"], v["Oc"] - v["S4"]])},
    "c09-f-06": {"n2": lambda v: v["R1"] * (1 - v["h"]) - v["O1"] - v["G"] + v["M0"] * (1 - v["d"]) ** 2 - v["M0"] * (1 - v["d"]) * (1 + v["i"])},
    "c09-g-05": {"P": lambda v: npf.npv(v["i"], [-(v["C"] - (v["M"] - v["t"] * (v["M"] - v["B"])))] + [inc_cf(v["Od"] - v["Oc"], 0, (v["C"] - v["B"]) / v["n"], v["t"])] * int(v["n"]))},
    "c09-g-08": {"Mx": lambda v: brentq(lambda M: -npf.pmt(v["i"], v["n"], npf.npv(v["i"], [M - v["t"] * (M - v["B"])] + [v["Od"] * (1 - v["t"]) - v["t"] * v["B"] / v["n"]] * int(v["n"]))) - (-npf.pmt(v["i"], v["n"], npf.npv(v["i"], [v["C"]] + [v["Oc"] * (1 - v["t"]) - v["t"] * v["C"] / v["n"]] * int(v["n"])))), -1e7, 1e7)},
    "c09-j-01": {"Ac": lambda v: min(esl_aw(120000, [90000, 78000, 66000, 54000, 42000], 15000, 7000, 0.10))},
    "c09-j-02": {"Ao": lambda v: -npf.pmt(0.10, 5, npf.npv(0.10, [10400 + 18000] + [13000 * 0.8 - 0.2 * 34000 / 5] * 5))},
    "c09-j-03": {"Pc": lambda v: npf.npv(0.10, [14000, 11000, 11000 - 9000 + 60000, 2500, 2500 - 42000])},

    # ch10: risk, rebuilt with numpy averages, explicit Bayes tables and scipy.stats.norm
    "c10-ex-expected": {"sd": lambda v: wstd([v["x1"], v["x2"], v["x3"]], [v["p1"], v["p2"], 1 - v["p1"] - v["p2"]])},
    "c10-ex-epw": {"m": lambda v: float(np.dot([v["p1"], v["p2"], v["p3"]], [npf.npv(v["i"], [-v["C"]] + [a] * int(v["n"])) for a in (v["A1"], v["A2"], v["A3"])]))},
    "c10-ex-nonlinear": {"m": lambda v: v["p"] * npf.npv(v["i"], [-v["C"]] + [v["A"]] * int(v["na"])) + (1 - v["p"]) * npf.npv(v["i"], [-v["C"]] + [v["A"]] * int(v["nb"]))},
    "c10-ex-independent": {"pl": lambda v: norm.cdf(0, npf.npv(v["i"], [-v["C"], v["m1"], v["m2"], v["m3"]]), np.sqrt(sum((s / (1 + v["i"]) ** t) ** 2 for t, s in enumerate([v["s1"], v["s2"], v["s3"]], 1))))},
    "c10-ex-compare": {"sb": lambda v: wstd([v["b1"], v["b2"], v["b3"]], [v["p1"], v["p2"], 1 - v["p1"] - v["p2"]])},
    "c10-ex-tree": {"EL": lambda v: tree_ev([[v["LH"], v["LL"]]], [v["p"], 1 - v["p"]])},
    "c10-ex-expand": {"ES2": lambda v: v["p"] * max(v["SH"], v["SH"] + v["X"]) + (1 - v["p"]) * v["SL"]},
    "c10-ex-evpi": {"V": lambda v: evpi([[v["LH"], v["LL"]], [v["SH"], v["SL"]]], [v["p"], 1 - v["p"]])},
    "c10-ex-survey": {"V": lambda v: survey_value([[v["LH"], v["LL"]], [v["SH"], v["SL"]]], v["p"], v["a"])},
    "c10-ex-normal": {"pl": lambda v: norm.cdf(v["F"] / (v["p"] - v["v"]), v["mu"], v["s"])},
    "c10-b-02": {"sd": lambda v: wstd([v["x1"], v["x2"], v["x3"]], [v["p1"], v["p2"], 1 - v["p1"] - v["p2"]])},
    "c10-b-04": {"m": lambda v: v["c"] * float(np.dot([0, 1, 2, 3], [v["q0"], v["q1"], v["q2"], 1 - v["q0"] - v["q1"] - v["q2"]]))},
    "c10-b-09": {"s": lambda v: float(np.std(np.add.outer([-v["s1"], v["s1"]], [-v["s2"], v["s2"]]).ravel()))},
    "c10-b-12": {"v": lambda v: wstd([v["x1"], v["x2"], v["x3"]], [v["p1"], v["p2"], 1 - v["p1"] - v["p2"]]) ** 2},
    "c10-c-06": {"m": lambda v: sum(pa * pn * npf.npv(v["i"], [-v["C"]] + [A] * int(n))
                                    for A, pa in ((v["A1"], v["pa"]), (v["A2"], 1 - v["pa"]))
                                    for n, pn in ((v["n1"], v["pn"]), (v["n2"], 1 - v["pn"])))},
    "c10-c-08": {"pl": lambda v: norm.cdf(0, npf.npv(v["i"], [-v["C"], v["m1"], v["m2"]]), np.hypot(v["s1"] / (1 + v["i"]), v["s2"] / (1 + v["i"]) ** 2))},
    "c10-c-10": {"s": lambda v: -v["m"] / norm.ppf(0.05)},
    "c10-c-14": {"si": lambda v: np.sqrt(sum((v["s"] / (1 + v["i"]) ** t) ** 2 for t in range(1, int(v["n"]) + 1)))},
    "c10-d-07": {"p2": lambda v: norm.cdf(0, 2 * v["m"], np.sqrt(2) * v["s"])},
    "c10-d-09": {"mb": lambda v: max(max(a, b) - b for a, b in ((v["a1"], v["b1"]), (v["a2"], v["b2"]), (v["a3"], v["b3"])))},
    "c10-e-06": {"E": lambda v: -v["c1"] + v["ps"] * max(0, v["ph"] * v["H"] + (1 - v["ph"]) * v["L"])},
    "c10-f-05": {"V": lambda v: survey_value([[v["G"], v["L"]], [0, 0]], v["p"], v["a"])},
    "c10-g-03": {"P": lambda v: norm.sf(v["K"], v["m"], v["s"])},
    "c10-g-06": {"q": lambda v: norm.ppf(0.05, v["m"], v["s"])},
    "c10-g-09": {"P": lambda v: norm.sf(v["K"], 4 * v["m"], np.sqrt(4) * v["s"])},
    "c10-j-01": {"Es": lambda v: survey_value([[700000, -200000], [350000, 80000], [0, 0]], 0.5, 0.85) + max(250000, 215000)},
    "c10-j-03": {"m": lambda v: min(600 * sum(p * max(k - d, 0) for d, p in enumerate([0.2, 0.35, 0.25, 0.15, 0.05]))
                                    + 5000 * sum(p * max(d - k, 0) for d, p in enumerate([0.2, 0.35, 0.25, 0.15, 0.05])) for k in range(5))},

}



def inc_cf(R, O, D, t):
    """Operating cash flow from an income statement: net income plus depreciation."""
    taxable = R - O - D
    return taxable - t * taxable + D


def proj(C, W, R, O, M, t, dep):
    """Project flows from year 0, with net salvage on the book value left after `dep`."""
    n = len(dep)
    flows = [-C - W] + [inc_cf(R, O, d, t) for d in dep]
    bv = C - sum(dep)
    flows[n] += M - t * (M - bv) + W
    return flows


def ddb_plain(B, n):
    """Double declining balance without a switch."""
    out, bv = [], B
    for _ in range(n):
        out.append(bv * 2 / n)
        bv -= out[-1]
    return out


def equity(C, L, r, R, O, t, n):
    """Equity flows with an equal-payment loan; interest is deductible."""
    A = -npf.pmt(r, n, L)
    out = [-(C - L)]
    for k in range(1, n + 1):
        I = -npf.ipmt(r, k, n, L)
        out.append(R - O - t * (R - O - C / n - I) - A)
    return out


def equity_bullet(C, L, r, R, O, t, n):
    """Equity flows with an interest-only loan repaid at the end."""
    out = [-(C - L)] + [R - O - t * (R - O - C / n - L * r) - L * r for _ in range(n)]
    out[n] -= L
    return out

def perpetuity_growing(A1, g, i, terms=5000):
    """Sum a growing perpetuity term by term until the terms vanish."""
    total, term = 0.0, A1 / (1 + i)
    for _ in range(terms):
        total += term
        term *= (1 + g) / (1 + i)
    return total


def esl_aw(C, market, O1, G, i):
    """Annual worth for each life n, from year-by-year flows."""
    out = []
    for n in range(1, len(market) + 1):
        flows = [C] + [O1 + G * k for k in range(n)]
        flows[n] -= market[n - 1]
        out.append(-npf.pmt(i, n, npf.npv(i, flows)))
    return out


def wstd(x, p):
    """Standard deviation of a discrete distribution, with numpy."""
    x, p = np.array(x, float), np.array(p, float)
    mu = np.average(x, weights=p)
    return float(np.sqrt(np.average((x - mu) ** 2, weights=p)))


def tree_ev(payoff, p):
    """Best expected value over alternatives (rows) and states (columns)."""
    return float(max(np.array(payoff, float) @ np.array(p, float)))


def evpi(payoff, p):
    payoff, p = np.array(payoff, float), np.array(p, float)
    return float(payoff.max(axis=0) @ p - max(payoff @ p))


def survey_value(payoff, p_high, acc):
    """Value of a two-state study that is right with probability acc, from the joint table."""
    payoff = np.array(payoff, float)
    prior = np.array([p_high, 1 - p_high])
    like = np.array([[acc, 1 - acc], [1 - acc, acc]])     # rows: state, cols: report
    joint = prior[:, None] * like
    value = 0.0
    for r in range(2):
        post = joint[:, r] / joint[:, r].sum()
        value += joint[:, r].sum() * max(max(payoff @ post), 0)
    return value - max(max(payoff @ prior), 0)


def ddb_sched(B, S, n):
    """Double declining balance with the switch to straight line, written independently."""
    out, bv = [], B
    for t in range(n):
        left = n - t
        dep = min(max(bv * 2 / n, (bv - S) / left), bv - S)
        out.append(dep)
        bv -= dep
    return out


def syd_sched(B, S, n):
    tot = n * (n + 1) / 2
    return [(B - S) * (n - t) / tot for t in range(n)]


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
    coverage(items)
    sys.exit(1 if bad else 0)


def coverage(items):
    """Report which items with a calculation have an independent check.

    The cross-engine test proves only that Python and JavaScript agree.
    This report shows how much of the bank is also checked against a
    separate calculation, chapter by chapter, and writes the list of
    unchecked items to tools/coverage.txt."""
    by_ch = {}
    for iid, it in items.items():
        if not it.get("calc"):
            continue
        ch = iid[:3]
        tot, cov = by_ch.get(ch, (0, 0))
        by_ch[ch] = (tot + 1, cov + (iid in CHECKS))
    lines = [f"{ch}: {cov} of {tot} items with a calculation have an independent check"
             for ch, (tot, cov) in sorted(by_ch.items())]
    missing = sorted(i for i, it in items.items() if it.get("calc") and i not in CHECKS)
    T = sum(t for t, _ in by_ch.values())
    C = sum(c for _, c in by_ch.values())
    (ROOT / "tools" / "coverage.txt").write_text(
        "\n".join(lines) + "\n\nItems without an independent check:\n" + "\n".join(missing) + "\n",
        encoding="utf-8")
    print(f"coverage: {C} of {T} items with a calculation ({C / T:.0%}); details in tools/coverage.txt")


if __name__ == "__main__":
    main()
