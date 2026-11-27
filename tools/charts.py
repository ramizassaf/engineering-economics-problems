"""Factor charts: a visual companion to the factor tables.

One page per factor, two views of the same factor:
  top     factor against n = 1 to 40, one curve per interest rate
  bottom  factor against i = 0.5% to 30%, one curve per n = 1 to 12
The top view reads long horizons. The bottom view separates the short
horizons, where the top curves crowd, and reads any rate, such as 7.5%,
that no table row holds. Each curve comes from the book's own engine
(ee/engine.py), so the charts and the tables can never disagree.

Output (vector):
  _generated/charts/<name>.pdf   for the printed book
  _generated/charts/<name>.svg   for the website
  _generated/charts/preview.pdf  all pages in one file, for review

Run from the project root:  python3 tools/charts.py
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.ticker import (FixedLocator, LogLocator, MultipleLocator,  # noqa: E402
                               NullFormatter, FuncFormatter)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import FP, PF, PA, AP, FA, AF, PG, AG  # noqa: E402

OUT = ROOT / "_generated" / "charts"
RATES = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30]   # percent
N_FULL = 40
NS = list(range(1, 13))                                  # bottom view: one curve per n
I_LO, I_HI = 0.5, 30.0
PAGE = (8.27, 11.69)          # A4 portrait, inches, like the book
INK, GRID_MAJOR, GRID_MINOR, MARK = "#1b2a38", "#b9c6d1", "#e3e9ee", "#c0392b"

# name, function, title, formula, y scale, worked example (rate %, n)
FACTORS = [
    ("FP", FP, "F/P  single-payment compound amount", r"$(F/P,\,i,\,n) = (1+i)^n$", "log", (8, 10)),
    ("PF", PF, "P/F  single-payment present worth", r"$(P/F,\,i,\,n) = (1+i)^{-n}$", "linear", (8, 10)),
    ("PA", PA, "P/A  uniform-series present worth", r"$(P/A,\,i,\,n) = \frac{(1+i)^n - 1}{i\,(1+i)^n}$", "linear", (8, 10)),
    ("AP", AP, "A/P  capital recovery", r"$(A/P,\,i,\,n) = \frac{i\,(1+i)^n}{(1+i)^n - 1}$", "log", (8, 10)),
    ("FA", FA, "F/A  uniform-series compound amount", r"$(F/A,\,i,\,n) = \frac{(1+i)^n - 1}{i}$", "log", (8, 10)),
    ("AF", AF, "A/F  sinking fund", r"$(A/F,\,i,\,n) = \frac{i}{(1+i)^n - 1}$", "log", (8, 10)),
    ("PG", PG, "P/G  arithmetic-gradient present worth", r"$(P/G,\,i,\,n) = \frac{(1+i)^n - i\,n - 1}{i^2\,(1+i)^n}$", "log", (8, 10)),
    ("AG", AG, "A/G  arithmetic-gradient uniform series", r"$(A/G,\,i,\,n) = \frac{1}{i} - \frac{n}{(1+i)^n - 1}$", "linear", (8, 10)),
]


def colour(k, count):
    """Dark blue to yellow-green along the list: neighbours differ, order is visible."""
    return plt.get_cmap("viridis")(0.05 + 0.85 * k / (count - 1))


def style(k):
    return "-" if k % 2 == 0 else (0, (5, 1.5))


def spread(ys, gap):
    """Move label positions apart, keeping their order, at least gap apart."""
    order = sorted(range(len(ys)), key=lambda k: ys[k])
    out = list(ys)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def axes_style(ax, scale, xlabel):
    ax.set_yscale(scale)
    if scale == "log":
        ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
        ax.yaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)))
        ax.yaxis.set_minor_formatter(FuncFormatter(
            lambda v, _: f"{v:g}" if round(v / 10 ** math.floor(math.log10(v))) in (2, 3, 5) else ""))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    else:
        hi = ax.get_ylim()[1]
        major = next(st for st in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100) if hi / st <= 12)
        ax.set_ylim(0, hi)
        ax.yaxis.set_major_locator(MultipleLocator(major))
        ax.yaxis.set_minor_locator(MultipleLocator(major / 5))
    ax.grid(which="major", color=GRID_MAJOR, lw=0.6)
    ax.grid(which="minor", color=GRID_MINOR, lw=0.4)
    ax.tick_params(labelsize=7, colors=INK)
    ax.set_xlabel(xlabel, fontsize=7.5, color=INK)
    for sp in ax.spines.values():
        sp.set_color(INK)
        sp.set_linewidth(0.7)


def right_labels(ax, ends, xend, gap):
    """Label each curve at the right edge; push labels apart so none overlap."""
    trans, inv = ax.transData, ax.transAxes.inverted()
    ya = [inv.transform(trans.transform((xend, y)))[1] for _, y, _ in ends]
    pos = spread(ya, gap)
    for (text, _, c), y0, p in zip(ends, ya, pos):
        ax.annotate(text, xy=(1.0, y0), xycoords="axes fraction",
                    xytext=(1.035, p), textcoords="axes fraction",
                    fontsize=6.5, color=c, va="center", ha="left",
                    arrowprops=dict(arrowstyle="-", color=c, lw=0.4))


def mark(ax, x, v, scale, text):
    """Worked example: dashed leaders from both axes to the point."""
    x0, y0 = ax.get_xlim()[0], ax.get_ylim()[0]
    ax.plot([x, x], [y0, v], ls=":", color=MARK, lw=0.9)
    ax.plot([x0, x], [v, v], ls=":", color=MARK, lw=0.9)
    ax.plot([x], [v], "o", ms=4, mfc="white", mec=MARK, mew=1.2)
    ax.annotate(text, xy=(x, v), xytext=(8, 10 if scale == "linear" else -26), textcoords="offset points",
                fontsize=6.5, color=MARK, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=MARK, lw=0.5))


def panel_n(ax, f, scale, example):
    """Factor against n, one curve per rate."""
    first = 2 if f in (PG, AG) else 1          # gradient factors are 0 at n = 1
    xs = list(range(first, N_FULL + 1))
    ends = []
    for k, r in enumerate(RATES):
        ys = [f(r / 100, n) for n in xs]
        c = colour(k, len(RATES))
        ax.plot(xs, ys, color=c, lw=1.0, ls=style(k))
        ends.append((f"{r}%", ys[-1], c))
    ax.set_xlim(1, N_FULL)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    axes_style(ax, scale, "n (periods)")
    right_labels(ax, ends, N_FULL, 0.024)
    ri, ni = example
    v = f(ri / 100, ni)
    mark(ax, ni, v, scale, f"i = {ri}%, n = {ni}\nfactor = {v:.4f}")


def panel_i(ax, f, scale, example):
    """Factor against i, one curve per n."""
    steps = 300
    xs = [I_LO + (I_HI - I_LO) * k / steps for k in range(steps + 1)]
    ns = [n for n in NS if not (f in (PG, AG) and n == 1)]
    ends = []
    for k, n in enumerate(ns):
        ys = [f(x / 100, n) for x in xs]
        c = colour(k, len(ns))
        ax.plot(xs, ys, color=c, lw=1.0, ls=style(k))
        ends.append((f"n = {n}", ys[-1], c))
    ax.set_xlim(0, I_HI)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(0.5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    axes_style(ax, scale, "i (interest rate per period)")
    right_labels(ax, ends, I_HI, 0.03)
    ri, ni = example[0] - 0.5, 6               # a rate between two table rows
    v = f(ri / 100, ni)
    mark(ax, ri, v, scale, f"i = {ri:g}%, n = {ni}\nfactor = {v:.4f}")


def page(name, f, title, formula, scale, example):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.08, 0.955, title, fontsize=13, color=INK, weight="bold")
    fig.text(0.08, 0.928, formula, fontsize=11, color=INK)
    top = fig.add_axes([0.10, 0.50, 0.76, 0.39])
    bot = fig.add_axes([0.10, 0.06, 0.76, 0.36])
    panel_n(top, f, scale, example)
    panel_i(bot, f, scale, example)
    top.set_title("By number of periods: one curve per interest rate", fontsize=8, color=INK, loc="left")
    bot.set_title("By interest rate: one curve per number of periods, n = 1 to 12", fontsize=8, color=INK, loc="left")
    return fig


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUT / "preview.pdf") as pdf:
        for name, f, title, formula, scale, example in FACTORS:
            fig = page(name, f, title, formula, scale, example)
            fig.savefig(OUT / f"{name}.pdf")
            fig.savefig(OUT / f"{name}.svg")
            pdf.savefig(fig)
            plt.close(fig)
    print(f"charts: {len(FACTORS)} pages in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
