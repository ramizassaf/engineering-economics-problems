"""One-off: give every symbol a single meaning across the book (Park's choices where
Park has one). Edits only math ($...$ and $$...$$) outside [[...]] templates and
outside code fences, in the chapter sources and the bank. Prose is edited by hand."""
import glob
import re
import sys

L = r"(?<![A-Za-z\\'])"       # no letter, backslash or prime before
R = r"(?![A-Za-z'])"          # no letter or prime after

RULES = {
    # year index t -> k (t is the tax rate everywhere)
    "ch02": [(r"_t\b", "_k"), (r"\(t - 1\)", "(k - 1)"), (r"\^\{t-1\}", "^{k-1}"), (r"\^t\b", "^k")],
    "ch03": [(r"\\sum_\{t=", r"\\sum_{k="), (r"_t\b", "_k"), (r"\^t\b", "^k")],
    "ch04": [(r"\\sum_\{t=", r"\\sum_{k="), (r"_t\b", "_k"), (r"\^t\b", "^k")],
    "ch10": [(r"\\sum_\{t=", r"\\sum_{k="), (r"_t\b", "_k"), (r"\^\{2t\}", "^{2k}"), (r"\^t\b", "^k")],
    # basis B -> I (Park); gain G -> word; fixed cost F -> FC; size S -> Q; break-even sales S* -> R*
    "ch05": [(L + "B" + R + r"(?!V)", "I"), (L + "G = M - BV", r"\\mathrm{gain} = M - BV")],
    "ch06": [(r"\\sum_\{t=", r"\\sum_{k="), (r",\\ t\)", r",\\ k)"),
             (r"S\^\*", "R^*"), (r"S_([AB12])\b", r"Q_\1"),
             (r"(?<![A-Za-z\\/'])F(?![A-Za-z/'])", "FC"),
             (r"(?<![A-Za-z\\])b = \\frac\{\\sum", r"b_1 = \\frac{\\sum"), (r"a = \\bar\{y\} - b\\,", r"b_0 = \\bar{y} - b_1\\,"),
             (r"C = a \+ b\\,x", r"C = b_0 + b_1\\,x")],
    "ch07": [(r"T_t = t", "T_k = t"), (r"I_t\b", "I_k"), (L + "B" + R + r"(?!V)", "I"),
             (r"\(p - v\) - F\\right\)", r"(p - v) - FC\\right)"),
             (r"r_\{after\} = r\\,\(1 - t\)", r"k_d\\,(1 - t)"),
             (r"\[S - t\\,\(S - BV\)\]", r"[M - t\\,(M - BV)]"), (r"S - t\\,\(S - 0\)", r"M - t\\,(M - 0)")],
    # market and real rate -> Park's i and i'
    "ch08": [(r"i_\{m(\d)\}", r"i_\1"), (r"i_\{r(\d)\}", r"i'_\1"), (r"i_\{?m\}?" + R + r"(?!\d)", "i"), (r"i_\{?r\}?" + R, "i'")],
    # budget B_t -> C_k, coupon C -> A, dividends D -> Div, debt/equity D, E -> V_d, V_e, flotation f -> f_c
    "ch11": [(r"c_\{jt\}", "c_{jk}"), (r"B_t\b", "C_k"), (r"^C = ", "A = "),
             (r"D_([01p])\b", r"\\mathrm{Div}_\1"), (r"\\frac\{D\}\{E\}", r"\\frac{V_d}{V_e}"), (r"D/E", "V_d/V_e"),
             (r"(?<![A-Za-z\\'_])f(?![A-Za-z'_])", "f_c")],
    # O&M M -> C' (Park), disbenefits D -> Dis
    "ch12": [(L + "M" + R, "C'"), (L + "D" + r"(?![A-Za-z_'])", r"\\mathrm{Dis}"), (r"D_([12])\b", r"\\mathrm{Dis}_\1")],
    # total score S -> U
    "ch13": [(r"(?<![A-Za-z\\])S_", "U_"), (r"(?<![A-Za-z\\])s(?![A-Za-z])", "u")],
}

TEMPLATE = re.compile(r"\[\[.*?\]\]")
FENCE = re.compile(r"```.*?```", re.S)
MATH = re.compile(r"\$\$(.+?)\$\$|(?<!\$)\$([^$\n]+?)\$(?!\$)", re.S)


def apply(seg, rules):
    keep = []
    def hide(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"
    s = TEMPLATE.sub(hide, seg)
    for pat, rep in rules:
        s = re.sub(pat, rep, s, flags=re.M)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def main(dry):
    changed = 0
    only = [a for a in sys.argv[1:] if a.startswith("ch")]
    for ch, rules in RULES.items():
        if only and ch not in only:
            continue
        for f in sorted(glob.glob(f"chapters/src/{ch}.qmd") + glob.glob(f"bank/{ch}/*.yaml")):
            s = open(f, encoding="utf-8").read()
            fences = [m.span() for m in FENCE.finditer(s)]
            out, last = [], 0
            for m in MATH.finditer(s):
                if any(a <= m.start() < b for a, b in fences):
                    continue
                new = apply(m.group(0), rules)
                if new != m.group(0):
                    changed += 1
                    if dry:
                        print(f"{f}:{s.count(chr(10), 0, m.start()) + 1}\n   - {m.group(0)[:150]!r}\n   + {new[:150]!r}")
                out.append(s[last:m.start()]); out.append(new); last = m.end()
            out.append(s[last:])
            if not dry:
                open(f, "w", encoding="utf-8").write("".join(out))
    print(changed, "math segments", "would change" if dry else "changed")


if __name__ == "__main__":
    main("--dry" in sys.argv)
