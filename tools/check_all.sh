#!/usr/bin/env bash
# Run every check: bank structure, factor reference tests, layout rule,
# Python vs JavaScript engines (consistency only), independent answers and their coverage.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/validate_bank.py
python3 tools/test_factors.py
node tools/test_factors.mjs /tmp/ee-factor-cases.json
python3 tools/lint_rtl.py
python3 tools/dump_py.py > /tmp/ee-py.json
node tools/check_js.mjs /tmp/ee-py.json
python3 tools/verify_answers.py
python3 tools/scan_ranges.py
# Text inside display math follows the Arabic direction in the PDF and prints reversed.
if grep -rn '\\text{' bank chapters/src appendices/*.qmd index.qmd | grep -v 'appendices/solutions-'; then
  echo "Use \\mathrm{...} instead of \\text{...} inside math"; exit 1
fi
echo "no \\text{} inside math"
