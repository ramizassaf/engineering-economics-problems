"""Build generated book files from the question bank.

  bank/chNN/*.yaml        examples, problems, mini cases (single source)
  chapters/src/chNN.qmd   hand-written explanation with @example(id) and @problems
  ->
  chapters/chNN.qmd                 chapter with examples and problems
  appendices/solutions-chNN.qmd     full solutions to every problem
  assets/bank/chNN.json             bank for the website's random numbers
  _generated/fig/*.svg, *.pdf       cash flow diagrams

Run from the project root:  python3 tools/build.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import compute, render, diagram_svg  # noqa: E402

FIG = ROOT / "_generated" / "fig"


def load_bank(ch: str):
    meta, items = {}, []
    for f in sorted((ROOT / "bank" / ch).glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        if "meta" in data:
            meta.update(data["meta"])
        items.extend(data.get("items", []))
    ids = [it["id"] for it in items]
    dup = {x for x in ids if ids.count(x) > 1}
    if dup:
        raise SystemExit(f"duplicate ids: {dup}")
    return meta, items


def figure(item, env, tag):
    spec = item.get("diagram")
    if not spec:
        return ""
    FIG.mkdir(parents=True, exist_ok=True)
    svg = FIG / f"{tag}.svg"
    svg.write_text(diagram_svg(spec, env), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(svg.with_suffix(".pdf")), str(svg)], check=True)
    cap = render(item.get("diagram_caption", "مخطط التدفق النقدي"), env)
    return f"\n\n![{cap}](../_generated/fig/{tag}){{width=70%}}\n"


def mcq_block(item, env):
    letters = ["أ", "ب", "ج", "د", "هـ"]
    lines = [f"{letters[k]}) {render(o, env)}" for k, o in enumerate(item["options"])]
    return "\n\n" + "\\\n".join(lines)


def statement(item, env):
    s = render(item["text"].strip(), env)
    if item.get("kind") == "mcq":
        s += mcq_block(item, env)
    return s


def solution(item, env):
    if item.get("kind") == "mcq":
        letters = ["أ", "ب", "ج", "د", "هـ"]
        k = item["correct"]
        body = render(item["solution"].strip(), env)
        sep = "\n\n" if body.startswith(("```", "$$", "|", "- ")) else " "
        return f"الجواب ({letters[k]})." + sep + body
    return render(item["solution"].strip(), env)


def build_chapter(ch: str):
    meta, items = load_bank(ch)
    num = meta["number"]
    by_id = {it["id"]: it for it in items}
    src = (ROOT / "chapters" / "src" / f"{ch}.qmd").read_text(encoding="utf-8")

    # ---- examples, numbered in order of appearance
    ex_no = {}

    def ex_sub(m):
        iid = m.group(1)
        it = by_id[iid]
        ex_no[iid] = len(ex_no) + 1
        k = ex_no[iid]
        env = compute(it)
        title = render(it.get("title", "").strip(), env)
        head = f"**مثال {num}.{k}: {title}**" if title else f"**مثال {num}.{k}**"
        body = statement(it, env)
        fig = figure(it, env, f"{ch}-ex{k:02d}")
        sol = solution(it, env)
        return (f'::: {{.ee-item #ex-{num}-{k} data-id="{iid}" data-kind="example" data-label="{num}.{k}"}}\n'
                f"{head}\n\n{body}{fig}\n\n**الحل:**\n\n{sol}\n:::\n")

    out = re.sub(r"^@example\(([\w-]+)\)\s*$", ex_sub, src, flags=re.M)

    # ---- end-of-chapter problems
    probs = [it for it in items if it.get("kind") in ("problem", "concept", "mcq", "case")]
    parts = meta["parts"]
    p_lines, s_lines = [], []
    s_lines.append(f"# حلول مسائل الفصل {num_word(num)} {{#sec-sol-{num}}}\n")
    s_lines.append("الحلول التالية محسوبة ببرنامج من نفس بنك الأسئلة الذي ولد نصوص المسائل. "
                   "إذا حللت بالجداول قد يختلف جوابك في الخانة العشرية الأخيرة.\n")
    k = 0
    for part in parts:
        group = [it for it in probs if it["part"] == part["key"]]
        if not group:
            continue
        p_lines.append(f"### {part['title']} {{.unnumbered}}\n")
        if part.get("intro"):
            p_lines.append(part["intro"].strip() + "\n")
        s_lines.append(f"## {part['title']} {{.unnumbered}}\n")
        for it in group:
            k += 1
            env = compute(it)
            tag = f"{num}.{k}"
            st = statement(it, env)
            fig = figure(it, env, f"{ch}-p{k:03d}")
            first, _, rest = st.partition("\n\n")
            p_lines.append(
                f'::: {{.ee-item #prob-{num}-{k} data-id="{it["id"]}" data-kind="problem" data-label="{tag}"}}\n'
                f"**{tag}** {first}" + (f"\n\n{rest}" if rest else "") + fig +
                f"\n\n[[الحل](#sol-{num}-{k})]{{.ee-sol-link .content-visible when-format=\"html\"}}\n:::\n")
            body = solution(it, env)
            # A solution that opens with a block (code, display math, table, list)
            # needs the block on its own line, or Markdown reads it as plain text.
            sep = "\n\n" if body.lstrip().startswith(("```", "$$", "|", "- ")) else " "
            s_lines.append(f"[**{tag}**]{{#sol-{num}-{k}}}" + sep + body + "\n")
    out = out.replace("@problems", "\n".join(p_lines))

    (ROOT / "chapters" / f"{ch}.qmd").write_text(out, encoding="utf-8")
    (ROOT / "appendices").mkdir(exist_ok=True)
    (ROOT / "appendices" / f"solutions-{ch}.qmd").write_text("\n".join(s_lines), encoding="utf-8")

    # ---- website bank: everything needed to redraw an item with new numbers
    keep = ("id", "kind", "title", "vars", "random", "calc", "text", "solution", "options", "correct", "diagram", "diagram_caption")
    web = [{k2: it[k2] for k2 in keep if k2 in it} for it in items if it.get("random")]
    (ROOT / "assets" / "bank").mkdir(parents=True, exist_ok=True)
    (ROOT / "assets" / "bank" / f"{ch}.json").write_text(json.dumps(web, ensure_ascii=False), encoding="utf-8")

    n_ex, n_rand = len(ex_no), len(web)
    print(f"{ch}: {n_ex} examples, {k} problems, {n_rand} items with random numbers")
    unused = [it["id"] for it in items if it.get("kind") == "example" and it["id"] not in ex_no]
    if unused:
        print("  examples in bank but not placed in the chapter:", unused)


WORDS = {1: "الأول", 2: "الثاني", 3: "الثالث", 4: "الرابع", 5: "الخامس", 6: "السادس", 7: "السابع"}


def num_word(n):
    return WORDS.get(n, str(n))


if __name__ == "__main__":
    chapters = sys.argv[1:] or sorted(p.name for p in (ROOT / "bank").iterdir() if p.is_dir())
    for ch in chapters:
        build_chapter(ch)
