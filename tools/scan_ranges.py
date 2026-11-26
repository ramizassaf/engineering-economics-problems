"""Random numbers must give realistic problems: solved rates between -20% and 60%,
solved year counts between 0 and 60. Scans 200 random draws per item."""
import glob
import random
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import compute, draw  # noqa: E402

rng = random.Random(11)
bad = checked = 0
for f in sorted(glob.glob(str(ROOT / "bank" / "ch*" / "*.yaml"))):
    for it in yaml.safe_load(open(f, encoding="utf-8")).get("items", []):
        if not it.get("random"):
            continue
        calc = it.get("calc", []) or []
        rates = [l.split("=")[0].strip() for l in calc if re.search(r"\b(RATE|RATEF|GROWTH|IRR)\(|\*\*\(1/", l)]
        years = [l.split("=")[0].strip() for l in calc if "ln(" in l and l.split("=")[0].strip().startswith("n")]
        for _ in range(200):
            env = compute(it, draw(it, rng))
            for k in rates:
                if isinstance(env[k], str):
                    continue
                checked += 1
                if not -0.2 < env[k] < 0.6:
                    bad += 1
                    print(f"{it['id']}: rate {k} = {env[k]:.4f}")
            for k in years:
                checked += 1
                if not 0 < env[k] < 60:
                    bad += 1
                    print(f"{it['id']}: years {k} = {env[k]:.2f}")
print(f"{checked} solved rates and year counts scanned, {bad} unrealistic")
sys.exit(1 if bad else 0)
