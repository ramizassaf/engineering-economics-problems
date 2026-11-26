"""Enforce the book's layout rule: nothing that reads left to right inside an Arabic line.

Equations, Excel formulas, code and factor notation go on their own line
($$ display math or a fenced code block). A line that mixes Arabic text with
any of these renders reversed in right-to-left layout.

Checks chapters/src/*.qmd, index.qmd, appendices/derivations.qmd and every text field in bank/*/*.yaml.
Exit code 1 if anything is found.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARABIC = re.compile(r"[؀-ۿ]")
TOKEN = re.compile(r"\[\[.+?\]\]")       # template placeholders count as plain numbers

RULES = [
    (re.compile(r"(?<!\$)\$(?!\$)"), "inline math ($)"),
    (re.compile(r"`"), "inline code (backtick)"),
    (re.compile(r"[A-Za-z0-9)]\s*[=^]\s*[A-Za-z0-9(]"), "equation (= or ^)"),
    (re.compile(r"\*\*?\s*[A-Za-z0-9(]|[A-Za-z0-9)]\s*\*"), "operator *"),
    (re.compile(r"[A-Za-z0-9)]\s*[×÷]\s*[A-Za-z0-9(]"), "operator × or ÷"),
    (re.compile(r"[A-Za-z][A-Za-z0-9]*\s*[+−]\s*[A-Za-z0-9(]|[A-Za-z0-9)]\s*[+−]\s*[A-Za-z(]"), "operator + or −"),
    (re.compile(r"\([^()؀-ۿ]*[A-Za-z][^()؀-ۿ]*[,+\-*/][^()؀-ۿ]*\)"), "Latin expression in parentheses"),
    (re.compile(r"\d\s*-\s*[A-Za-z]|[A-Za-z]\d*\s*-\s*\d"), "subtraction with a cell or symbol"),
]


def check_text(text: str, where: str):
    problems = []
    in_math = in_code = False
    for k, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if s == "$$":
            in_math = not in_math
            continue
        if in_code or in_math or s.startswith("$$"):
            continue
        if not ARABIC.search(s):
            continue
        plain = TOKEN.sub("0", s)
        plain = re.sub(r"\{[#.][^}]*\}", "", plain)                # heading ids and classes
        plain = re.sub(r"\*\*([^*]+)\*\*", r"\1", plain)          # bold markers
        if plain.startswith("|"):                                  # table: check cells one by one
            cells = [c.strip() for c in plain.strip("|").split("|")]
            for c in cells:
                if c.startswith("$") and c.endswith("$"):          # a cell that is only math is fine
                    continue
                for rx, why in RULES:
                    if ARABIC.search(c) and rx.search(c):
                        problems.append((where, k, why, s))
                        break
                    if c.startswith("="):
                        problems.append((where, k, "Excel formula in a table cell", s))
                        break
            continue
        for rx, why in RULES:
            if rx.search(plain):
                problems.append((where, k, why, s))
                break
    return problems


def main():
    found = []
    for f in sorted((ROOT / "chapters" / "src").glob("*.qmd")) + [ROOT / "index.qmd", ROOT / "appendices" / "derivations.qmd", ROOT / "appendices" / "excel-functions.qmd", ROOT / "appendices" / "tax-countries.qmd"]:
        if f.exists():
            found += check_text(f.read_text(encoding="utf-8"), f.relative_to(ROOT).as_posix())
    for f in sorted((ROOT / "bank").glob("*/*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for it in data.get("items", []):
            for fld in ("title", "text", "solution", "answer"):
                if it.get(fld):
                    found += check_text(it[fld], f"{f.relative_to(ROOT).as_posix()}:{it['id']}:{fld}")
            for o in it.get("options", []) or []:
                found += check_text(o, f"{f.relative_to(ROOT).as_posix()}:{it['id']}:option")
    for where, k, why, s in found:
        print(f"{where}:{k}: {why}\n    {s}")
    print(f"{len(found)} lines break the right-to-left rule")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
