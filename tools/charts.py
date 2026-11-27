"""Factor charts: a visual companion to the factor tables.

One landscape page per factor. One curve per interest rate, i = 2% to 20%.
The horizontal axis lists n = 2 to 25, then 30, 36, 48 and 60, evenly
spaced, so every period gets the same room. Each curve carries its rate
label on the line, and the factor value is printed on the line at every
n where it fits without covering another label. Where curves bunch
together (small n), values that would overlap are left out; the tables
give them.

Every value comes from the book's own engine (ee/engine.py), so the
charts and the tables can never disagree.

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
from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, MultipleLocator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import FP, PF, PA, AP, FA, AF, PG, AG  # noqa: E402

OUT = ROOT / "_generated" / "charts"
RATES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20]          # percent
NS = list(range(2, 26)) + [30, 36, 48, 60]
X = list(range(len(NS)))                                     # even spacing, one slot per n
BREAK = NS.index(25) + 0.5                                   # the scale changes after n = 25
PAGE = (11.69, 8.27)                                         # A4 landscape, inches
INK, GRID_MAJOR, GRID_MINOR = "#1b2a38", "#b9c6d1", "#e6ebef"

# name, function, title, formula, y scale
FACTORS = [
    ("FP", FP, "F/P  single-payment compound amount", r"$(F/P,\,i,\,n) = (1+i)^n$", "log"),
    ("PF", PF, "P/F  single-payment present worth", r"$(P/F,\,i,\,n) = (1+i)^{-n}$", "linear"),
    ("PA", PA, "P/A  uniform-series present worth", r"$(P/A,\,i,\,n) = \frac{(1+i)^n - 1}{i\,(1+i)^n}$", "linear"),
    ("AP", AP, "A/P  capital recovery", r"$(A/P,\,i,\,n) = \frac{i\,(1+i)^n}{(1+i)^n - 1}$", "log"),
    ("FA", FA, "F/A  uniform-series compound amount", r"$(F/A,\,i,\,n) = \frac{(1+i)^n - 1}{i}$", "log"),
    ("AF", AF, "A/F  sinking fund", r"$(A/F,\,i,\,n) = \frac{i}{(1+i)^n - 1}$", "log"),
    ("PG", PG, "P/G  arithmetic-gradient present worth", r"$(P/G,\,i,\,n) = \frac{(1+i)^n - i\,n - 1}{i^2\,(1+i)^n}$", "log"),
    ("AG", AG, "A/G  arithmetic-gradient uniform series", r"$(A/G,\,i,\,n) = \frac{1}{i} - \frac{n}{(1+i)^n - 1}$", "linear"),
]


def colour(k):
    """Dark blue to green along the rates: neighbours differ, order is visible."""
    return plt.get_cmap("viridis")(0.02 + 0.80 * k / (len(RATES) - 1))


def fmt(v):
    """Four significant figures, like a careful reading of a table."""
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:.1f}"
    if v >= 10:
        return f"{v:.2f}"
    if v >= 1:
        return f"{v:.3f}"
    return f"{v:.4f}"


def spread(ys, gap):
    """Move label positions apart, keeping their order, at least gap apart."""
    order = sorted(range(len(ys)), key=lambda k: ys[k])
    out = list(ys)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def overlaps(box, boxes, pad=0.6):
    return any(box.x0 - pad < b.x1 and b.x0 - pad < box.x1 and box.y0 - pad < b.y1 and b.y0 - pad < box.y1
               for b in boxes)


def axes_style(ax, scale, values):
    lo, hi = min(values), max(values)
    ax.set_yscale(scale)
    if scale == "log":
        ax.set_ylim(lo / 1.15, hi * 1.15)
        ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
        ax.yaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(FuncFormatter(
            lambda v, _: f"{v:g}" if round(v / 10 ** math.floor(math.log10(v))) in (2, 3, 5) else ""))
    else:
        top = hi * 1.04
        ax.set_ylim(0, top)
        major = next(st for st in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50) if top / st <= 14)
        ax.yaxis.set_major_locator(MultipleLocator(major))
        ax.yaxis.set_minor_locator(MultipleLocator(major / 5))
    ax.set_xlim(-0.6, X[-1] + 0.6)
    ax.xaxis.set_major_locator(FixedLocator(X))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: str(NS[int(round(v))]) if 0 <= round(v) < len(NS) else ""))
    ax.grid(which="major", color=GRID_MAJOR, lw=0.55)
    ax.grid(which="minor", axis="y", color=GRID_MINOR, lw=0.35)
    ax.axvline(BREAK, color=INK, lw=0.6, ls=(0, (4, 3)))
    ax.text(BREAK + 0.1, 1.005, "step changes", transform=ax.get_xaxis_transform(), fontsize=6, color=INK, va="bottom")
    ax.tick_params(labelsize=7, colors=INK)
    ax.set_xlabel("n (periods)", fontsize=8, color=INK)
    for sp in ax.spines.values():
        sp.set_color(INK)
        sp.set_linewidth(0.7)


def page(name, f, title, formula, scale):
    fig = plt.figure(figsize=PAGE)
    fig.text(0.045, 0.952, title, fontsize=13, color=INK, weight="bold")
    fig.text(0.045, 0.905, formula, fontsize=11, color=INK)
    fig.text(0.955, 0.952, "Each curve is one interest rate per period. The number on the line is the factor.",
             fontsize=7.5, color=INK, ha="right")
    fig.text(0.955, 0.93, "Where curves bunch together, read the factor tables.",
             fontsize=7.5, color=INK, ha="right")
    ax = fig.add_axes([0.055, 0.075, 0.885, 0.80])

    table = {r: [f(r / 100, n) for n in NS] for r in RATES}
    axes_style(ax, scale, [v for vs in table.values() for v in vs])
    for k, r in enumerate(RATES):
        ax.plot(X, table[r], color=colour(k), lw=1.1, zorder=2)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    placed = []

    # rate labels: outside the plot at the right, pushed apart so none overlap
    inv, data = ax.transAxes.inverted(), ax.transData
    ends = [inv.transform(data.transform((X[-1], table[r][-1])))[1] for r in RATES]
    for k, (r, y0, yl) in enumerate(zip(RATES, ends, spread(ends, 0.028))):
        ax.annotate(f"{r}%", xy=(1.0, y0), xycoords="axes fraction", xytext=(1.012, yl),
                    textcoords="axes fraction", fontsize=6.5, color="white", weight="bold", va="center",
                    bbox=dict(boxstyle="round,pad=0.18", fc=colour(k), ec="none"),
                    arrowprops=dict(arrowstyle="-", color=colour(k), lw=0.5))
    # and inside the plot, in the empty column where the step changes
    for k, r in enumerate(RATES):
        y = table[r][NS.index(25)]
        y2 = table[r][NS.index(30)]
        ym = math.sqrt(y * y2) if scale == "log" else (y + y2) / 2
        t = ax.text(BREAK, ym, f"{r}%", fontsize=5.6, color="white", weight="bold",
                    ha="center", va="center", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.14", fc=colour(k), ec="none"))
        box = t.get_window_extent(renderer)
        if overlaps(box, placed):
            t.remove()
        else:
            placed.append(box)

    # factor values on the lines: high rates first, they spread out most
    shown = total = 0
    for k in reversed(range(len(RATES))):
        r = RATES[k]
        for xi in X:
            total += 1
            v = table[r][xi]
            t = ax.text(xi, v, fmt(v), fontsize=4.6, color=colour(k), ha="center", va="center", zorder=4,
                        bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none", alpha=0.9))
            box = t.get_window_extent(renderer)
            if overlaps(box, placed):
                t.remove()
                ax.plot([xi], [v], "o", ms=1.4, color=colour(k), zorder=3)
            else:
                placed.append(box)
                shown += 1
    return fig, shown, total


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    with PdfPages(OUT / "preview.pdf") as pdf:
        for name, f, title, formula, scale in FACTORS:
            fig, shown, total = page(name, f, title, formula, scale)
            fig.savefig(OUT / f"{name}.pdf")
            fig.savefig(OUT / f"{name}.svg")
            pdf.savefig(fig)
            plt.close(fig)
            report.append(f"{name}: {shown} of {total} values printed ({shown / total:.0%})")
    print("\n".join(report))


if __name__ == "__main__":
    main()
