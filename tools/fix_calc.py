"""Rewrite one-line `calc: [a = .., b = f(x, y)]` lists as block lists, and one-line text fields as blocks.

YAML treats commas inside function calls as list separators, so long calc
lines are easier to write inline and then normalised with this script."""
import re
import sys
from pathlib import Path


def split_top(s):
    parts, depth, quote, cur = [], 0, None, ""
    for ch in s:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


for f in sys.argv[1:]:
    p = Path(f)
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        t = re.match(r"^(\s*)(text|solution|title|answer): ([^|>'\"].*)$", line)
        if t:
            out.append(f"{t.group(1)}{t.group(2)}: |")
            out.append(f"{t.group(1)}  {t.group(3)}")
            continue
        m = re.match(r"^(\s*)calc: \[(.*)\]\s*$", line)
        if m:
            ind = m.group(1)
            out.append(f"{ind}calc:")
            for e in split_top(m.group(2)):
                out.append(f"{ind}  - {e}")
        else:
            out.append(line)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
