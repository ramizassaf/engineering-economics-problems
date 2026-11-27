"""Build the glossary and references appendices from their single sources.

  glossary/terms.yaml      ->  appendices/glossary.qmd
  references/books.yaml    ->  appendices/references.qmd
                               _generated/refs/<key>.md  (one section per chapter or appendix)

Checks: no duplicate Arabic or English term, a known chapter for every term,
and every chapter in the references map has its book chapters listed. Prints
the Arabic terms that the book's text does not use yet.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
APPS = {"acc": ("ملحق المحاسبة", "sec-accounting"),
        "est": ("ملحق تقدير التكاليف", "sec-cost-estimation"),
        "cb": ("ملحق الميزانية المحدودة", "sec-capital-budgeting")}
BOOK_ORDER = ["park", "blank", "sullivan"]


def sort_key(ar):
    """Arabic dictionary order: ignore the article on the first word and hamza forms."""
    s = ar.strip()
    if s.startswith("ال") and len(s) > 3:
        s = s[2:]
    s = (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
          .replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي"))
    return s


def en(x):
    """English text inside Arabic: an isolated left-to-right run (tex/en-ltr.lua for the PDF)."""
    return f'[{x}]{{.en dir="ltr"}}'


def where(ch):
    if isinstance(ch, int):
        return f"[{ch}](#sec-ch{ch})"
    name, sec = APPS[ch]
    return f"[{name}](#{sec})"


def glossary():
    terms = yaml.safe_load((ROOT / "glossary" / "terms.yaml").read_text(encoding="utf-8"))["terms"]
    errors = []
    seen_ar, seen_en = set(), set()
    for t in terms:
        for k in ("ar", "en", "ch", "def"):
            if not t.get(k):
                errors.append(f"{t}: missing {k}")
        if t["ar"] in seen_ar:
            errors.append(f"duplicate Arabic term {t['ar']}")
        if t["en"].lower() in seen_en:
            errors.append(f"duplicate English term {t['en']}")
        seen_ar.add(t["ar"])
        seen_en.add(t["en"].lower())
        if not (isinstance(t["ch"], int) or t["ch"] in APPS):
            errors.append(f"{t['ar']}: unknown chapter {t['ch']!r}")
        if "—" in t["def"] or "|" in t["def"]:
            errors.append(f"{t['ar']}: no dash or bar in a definition")
    if errors:
        raise SystemExit("\n".join(errors))

    out = ["# مسرد المصطلحات {#sec-glossary}", "",
           "كل مصطلح في الكتاب مع مقابله الإنجليزي كما يرد في كتب Park وBlank & Tarquin وSullivan. "
           "العمود الأخير يدلك على الفصل الذي يظهر فيه المصطلح أول مرة. "
           "إذا قرأت أحد هذه الكتب، استعمل المسرد لتعرف المصطلح العربي المقابل.", "",
           "الترتيب أبجدي، بدون أل التعريف في أول كلمة.", "",
           "## من العربية إلى الإنجليزية {.unnumbered}", ""]
    letter = None
    for t in sorted(terms, key=lambda t: sort_key(t["ar"])):
        first = sort_key(t["ar"])[0]
        if first != letter:
            if letter is not None:
                out.append("")
            letter = first
            out += [f"### {first} {{.unnumbered}}", "",
                    "| المصطلح | English | التعريف | الفصل |",
                    "| ---------------- | ---------------- | ---------------------------------- | ------ |"]
        out.append(f"| {t['ar']} | {en(t['en'])} | {t['def']} | {where(t['ch'])} |")
    out += ["", "## من الإنجليزية إلى العربية {.unnumbered}", "",
            "| English | المصطلح |",
            "| --- | --- |"]
    for t in sorted(terms, key=lambda t: t["en"].lower()):
        out.append(f"| {en(t['en'])} | {t['ar']} |")
    out.append("")
    (ROOT / "appendices" / "glossary.qmd").write_text("\n".join(out), encoding="utf-8")

    # which terms the book's text does not use yet
    texts = []
    for p in list((ROOT / "chapters" / "src").glob("*.qmd")) + list((ROOT / "bank").glob("ch*/*.yaml")) + \
            [ROOT / "appendices" / f"{a}.qmd" for a in ("accounting", "cost-estimation", "capital-budgeting", "derivations", "tables")]:
        if p.exists():
            texts.append(p.read_text(encoding="utf-8"))
    corpus = "\n".join(texts)
    unused = [t["ar"] for t in terms if t["ar"] not in corpus]
    print(f"glossary: {len(terms)} terms")
    if unused:
        print(f"  {len(unused)} terms not used in the text yet: " + "، ".join(unused))


def references():
    data = yaml.safe_load((ROOT / "references" / "books.yaml").read_text(encoding="utf-8"))
    books, titles, mapping = data["books"], data["titles"], data["map"]
    rdir = ROOT / "_generated" / "refs"
    rdir.mkdir(parents=True, exist_ok=True)
    for key, m in mapping.items():
        rows = []
        for b in BOOK_ORDER:
            for c in m.get(b, []):
                if c not in titles[b]:
                    raise SystemExit(f"references: {key}: {b} has no chapter {c}")
                label = f"Appendix {c}" if isinstance(c, str) else str(c)
                rows.append(f"| {en(books[b]['short'])} | {en(label)} | {en(titles[b][c])} |")
        what = "هذا الفصل" if key.startswith("ch") else "هذا الملحق"
        md = [f"## المراجع {{.unnumbered #refs-{key}}}", "",
              f"{what} يقابل الفصول التالية في الكتب الثلاثة. تفاصيل الطبعات في @sec-references.", "",
              "| الكتاب | الفصل | عنوان الفصل |",
              "| --- | --- | --- |", *rows, ""]
        (rdir / f"{key}.md").write_text("\n".join(md), encoding="utf-8")

    out = ["# المراجع {#sec-references}", "",
           "الكتاب يتبع أسلوب ثلاثة كتب منهجية معروفة في الاقتصاد الهندسي. أرقام الفصول في قسم المراجع آخر كل فصل حسب هذه الطبعات:", ""]
    for b in BOOK_ORDER:
        out.append(f"- {en(books[b]['cite'])}")
    out += ["", "## الفصول المقابلة في كل كتاب {.unnumbered}", "",
            "| في هذا الكتاب | " + " | ".join(en(books[b]["short"]) for b in BOOK_ORDER) + " |",
            "| --- | --- | --- | --- |"]
    names = {"capital-budgeting": "[ملحق الميزانية المحدودة](#sec-capital-budgeting)",
             "cost-estimation": "[ملحق تقدير التكاليف](#sec-cost-estimation)",
             "accounting": "[ملحق المحاسبة](#sec-accounting)"}
    for key, m in mapping.items():
        name = f"[الفصل {int(key[2:])}](#sec-ch{int(key[2:])})" if key.startswith("ch") else names[key]
        cells = ["، ".join(en(f"App. {c}") if isinstance(c, str) else str(c) for c in m.get(b, [])) or "" for b in BOOK_ORDER]
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    out.append("")
    (ROOT / "appendices" / "references.qmd").write_text("\n".join(out), encoding="utf-8")
    print(f"references: {len(mapping)} chapter sections")


if __name__ == "__main__":
    glossary()
    references()
