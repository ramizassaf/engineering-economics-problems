"""Check the question bank before building. Stops with the file, item and field.

Checks: unique ids; known kinds; parts listed in the chapter meta; every
@example(id) exists and is an example; every example is used once; each
chapter has @problems; MCQ options and answer index; random ranges with a
positive step that divides the range; random names that also have a fixed
value in vars; calc lines of the form name = expression.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"example", "concept", "problem", "mcq", "case"}
TOKEN = re.compile(r"\[\[.+?\]\]")
ARABIC = re.compile(r"[\u0600-\u06FF]")
errors = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


ids = {}
for chdir in sorted((ROOT / "bank").glob("ch*")):
    ch = chdir.name
    meta, items = None, []
    for f in sorted(chdir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if "meta" in data:
            meta = data["meta"]
        for it in data.get("items") or []:
            items.append((f.name, it))
    if meta is None:
        err(ch, "no 00-meta.yaml with a meta block")
        continue
    parts = {p["key"] for p in meta.get("parts", [])}
    for fname, it in items:
        iid = it.get("id", "?")
        where = f"{ch}/{fname} {iid}"
        if iid in ids:
            err(where, f"duplicate id, also in {ids[iid]}")
        ids[iid] = f"{ch}/{fname}"
        kind = it.get("kind")
        if kind not in KINDS:
            err(where, f"unknown kind {kind!r}")
        if kind != "example" and it.get("part") not in parts:
            err(where, f"part {it.get('part')!r} is not in the chapter meta {sorted(parts)}")
        if kind == "mcq":
            opts = it.get("options") or []
            if len(opts) < 2:
                err(where, "an MCQ needs at least 2 options")
            c = it.get("correct")
            if not isinstance(c, int) or not 0 <= c < len(opts):
                err(where, f"correct={c!r} is not an index into {len(opts)} options")
        for name, spec in (it.get("random") or {}).items():
            if not (isinstance(spec, list) and len(spec) == 3):
                err(where, f"random.{name} must be [min, max, step]")
                continue
            lo, hi, st = spec
            if not st > 0:
                err(where, f"random.{name} step must be positive")
                continue
            if hi < lo:
                err(where, f"random.{name} max below min")
            k = (hi - lo) / st
            if abs(k - round(k)) > 1e-6:
                err(where, f"random.{name} step {st} does not divide {lo}..{hi}")
            if name not in (it.get("vars") or {}):
                err(where, f"random.{name} has no fixed value in vars for the printed book")
        for line in it.get("calc") or []:
            if not re.match(r"^\s*[A-Za-z_]\w*\s*=(?!=)", str(line)):
                err(where, f"calc line is not 'name = expression': {line!r}")
        if not it.get("text") and kind != "example":
            err(where, "no text")
        if not it.get("solution"):
            err(where, "no solution")
        # English text: same placeholders as the Arabic, so the same numbers show
        if meta.get("bilingual") and not it.get("text_en"):
            err(where, "the chapter is bilingual but the item has no text_en")
        if it.get("text_en"):
            ar_t = it.get("text") or ""
            if sorted(TOKEN.findall(ar_t)) != sorted(TOKEN.findall(it["text_en"])):
                err(where, "text_en placeholders differ from text: "
                    f"{sorted(set(TOKEN.findall(ar_t)) ^ set(TOKEN.findall(it['text_en'])))}")
            if ARABIC.search(it["text_en"]):
                err(where, "Arabic letters in text_en")
            if kind == "example" and it.get("title") and not it.get("title_en"):
                err(where, "example has text_en but no title_en")
            if kind == "mcq":
                oe = it.get("options_en") or []
                if len(oe) != len(it.get("options") or []):
                    err(where, "options_en must have one entry per option")
                for a, b in zip(it.get("options") or [], oe):
                    if sorted(TOKEN.findall(str(a))) != sorted(TOKEN.findall(str(b))):
                        err(where, f"options_en placeholders differ: {a!r} / {b!r}")

    src = ROOT / "chapters" / "src" / f"{ch}.qmd"
    if not src.exists():
        err(ch, f"no chapter source {src.name}")
        continue
    text = src.read_text(encoding="utf-8")
    if "@problems" not in text:
        err(src.name, "no @problems marker")
    used = re.findall(r"^@example\(([\w-]+)\)\s*$", text, flags=re.M)
    by_id = {it.get("id"): it for _, it in items}
    for u in used:
        if u not in by_id:
            err(src.name, f"@example({u}) is not in the bank")
        elif by_id[u].get("kind") != "example":
            err(src.name, f"@example({u}) is a {by_id[u].get('kind')}, not an example")
    for dup in {u for u in used if used.count(u) > 1}:
        err(src.name, f"@example({dup}) is used more than once")
    for iid, it in by_id.items():
        if it.get("kind") == "example" and iid not in used:
            err(src.name, f"example {iid} is in the bank but not placed in the chapter")

if errors:
    print("\n".join(errors))
    raise SystemExit(f"{len(errors)} problems in the bank")
print(f"bank valid: {len(ids)} items")
