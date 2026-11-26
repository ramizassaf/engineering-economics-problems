#!/usr/bin/env bash
# Run every check: layout rule, Python vs JavaScript engines, independent answers.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/lint_rtl.py
python3 tools/dump_py.py > /tmp/ee-py.json
node tools/check_js.mjs /tmp/ee-py.json
python3 tools/verify_answers.py
