"""Render every bank item with the Python engine: fixed numbers plus 25 random draws.

Output is JSON for tools/check_js.mjs. Also fails loudly on any item that
cannot be rendered, or whose numbers are not finite."""
import json
import math
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import compute, render, diagram_svg, draw  # noqa: E402

rng = random.Random(2026)
recs = []
for f in sorted((ROOT / "bank").glob("ch*/*.yaml")):
    for it in yaml.safe_load(f.read_text(encoding="utf-8")).get("items", []):
        runs = [("fixed", {})] + [(f"r{k}", draw(it, rng)) for k in range(25 if it.get("random") else 0)]
        for tag, vals in runs:
            env = compute(it, vals)
            for k, v in env.items():
                if isinstance(v, float) and not math.isfinite(v):
                    raise SystemExit(f"{it['id']} [{tag}]: {k} is not finite")
            out = {fld: render(it[fld], env) for fld in ("text", "text_en", "solution", "answer") if it.get(fld)}
            if it.get("diagram"):
                out["diagram"] = diagram_svg(it["diagram"], env)
            recs.append({"tag": tag, "item": it, "values": vals, "out": out})
json.dump(recs, sys.stdout, ensure_ascii=False)
