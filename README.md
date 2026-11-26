# مسائل في الاقتصاد الهندسي

Problems in Engineering Economics, an Arabic book by Ramiz Assaf, An-Najah National University.

Two versions are built from one source:

- **Print (PDF):** fixed numbers, worked examples, end-of-chapter problems, full solutions in the appendices.
- **Website (HTML):** the same content, plus a "أرقام جديدة" button on every example and problem that redraws it with new numbers and its full solution.

## How the book is built

Every example and problem is written once, in `bank/chNN/*.yaml`:

| Field | Purpose |
| --- | --- |
| `vars` | fixed values used in the printed book |
| `random` | `[min, max, step]` per variable, used on the website |
| `calc` | ordered `name = expression` lines |
| `text`, `solution` | Markdown templates; `[[expression|format]]` inserts a computed value |
| `diagram` | optional cash flow diagram |

The same templates are evaluated by `ee/engine.py` (print) and `assets/ee-engine.js` (website).
`tools/check_js.mjs` renders every item with both engines, with the fixed numbers and 25 random draws, and fails on any difference.
No answer in the book is typed by hand.

Formats: `2` decimals with separators, `0`, `4`, `%` percent, `%2` percent with 2 decimals, `f4` table factor, `g` whole or 2 decimals, `n` integer, `r` plain number for code, `d2` 2 decimals without separators.
Helpers: `FP PF PA AP FA AF PG AG`, `r4` (round like the tables), `ln abs max min floor ceil`, `pick(cond, a, b)`, `yrs(n)` (Arabic year count with correct agreement).

## Layout rule

Arabic text runs right to left. Equations, Excel formulas, factor notation and code run left to right, so each goes on its own line, never inside an Arabic sentence. `tools/lint_rtl.py` enforces this on every build.

## Build

Requirements: Quarto 1.11+, Python 3 with `requirements.txt`, Node 18+, LuaLaTeX with the Arabic packages and the Amiri and Noto Naskh Arabic fonts.

```bash
pip install -r requirements.txt
python3 tools/build.py          # bank -> chapters, solutions, website bank
python3 tools/tables.py         # factor tables appendix
quarto render                   # site in _book/ and the PDF
python3 tools/dump_py.py > /tmp/py.json && node tools/check_js.mjs /tmp/py.json
```

`chapters/chNN.qmd`, `appendices/` and `assets/bank/` are generated. Edit `chapters/src/` and `bank/` instead.

`selnolig.sty` is an empty stub on purpose: the real package breaks Arabic text under LuaLaTeX.

## Layout

```
bank/chNN/          question bank (single source)
chapters/src/       hand-written explanations with @example(id) and @problems markers
chapters/           generated chapters
appendices/         generated solutions and factor tables
ee/engine.py        template engine, Python
assets/             website engine, random-number widget, KaTeX, marked
tex/                LaTeX preamble and the site script loader
tools/              build, lint, cross-engine check
```
