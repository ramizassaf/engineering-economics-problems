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
| `text_en`, `title_en`, `options_en` | optional English statement for a future English button on the site; same placeholders as `text`. Not used yet. |

The same templates are evaluated by `ee/engine.py` (print) and `assets/ee-engine.js` (website).
`tools/check_js.mjs` renders every item with both engines, with the fixed numbers and 25 random draws, and fails on any difference.
That proves only that the two engines agree. Correctness is checked separately (see Checks below).
No answer in the book is typed by hand.

Expressions are evaluated with Python `eval` and JavaScript `new Function`. The bank is a trusted source written by the authors; never let readers type expressions into it.

Formats: `2` decimals with separators, `0`, `4`, `%` percent, `%2` percent with 2 decimals, `f4` table factor, `g` whole or 2 decimals, `n` integer, `r` plain number for code, `d2` 2 decimals without separators.
Helpers: `FP PF PA AP FA AF PG AG PGEO`, `RATE RATEF YTM GROWTH NPV IRR NORMS sqrt`, `r4` (round like the tables), `ln abs max min floor ceil`, `pick(cond, a, b)`, `yrs(n)` (Arabic year count with correct agreement).

## Layout rule

Arabic text runs right to left. Equations, Excel formulas, factor notation and code run left to right, so each goes on its own line, never inside an Arabic sentence. `tools/lint_rtl.py` enforces this on every build.

## Build

Requirements: Quarto 1.11+, Python 3 with `requirements.txt`, Node 18+, LuaLaTeX with the Arabic packages and the Amiri and Noto Naskh Arabic fonts.

```bash
pip install -r requirements.txt
python3 tools/glossary.py       # glossary and references appendices, references section per chapter
python3 tools/build.py          # bank -> chapters, solutions, website bank
python3 tools/tables.py         # factor tables appendix
quarto render                   # site in _book/ and the PDF
tools/check_all.sh              # every check below
```

## Checks

`tools/check_all.sh` runs, in order, and stops at the first failure:

| Check | What it proves |
| --- | --- |
| `validate_bank.py` | unique ids, parts, MCQ answer index, random ranges, every `@example` placed once |
| `test_factors.py`, `test_factors.mjs` | every factor equals its year-by-year sum, at 0%, near 0 and with i close to g; root finders refuse to answer when the range holds no root |
| `lint_rtl.py` | no equation or code inside an Arabic sentence |
| `dump_py.py` + `check_js.mjs` | Python and JavaScript render every item identically (consistency, not correctness) |
| `check_equations.py` | every printed step `... = number` in every solution is recomputed from the numbers shown, with factors from `numpy_financial`, not from the engine |
| `verify_answers.py` | answers recomputed independently with `numpy_financial` and `scipy`; prints coverage of both checks and writes the unchecked list to `tools/coverage.txt` |
| `scan_ranges.py` | solved rates and year counts stay realistic over many random draws |

Rate solvers (`RATE`, `RATEF`, `YTM`, `GROWTH`, `IRR`) use bisection only when the ends bracket a root. Otherwise they try one wider range, then raise an error instead of returning an end point. Negative rates are allowed. Flows that change sign more than once can have several rates; give `IRR` a range that holds only the one you want.

`chapters/chNN.qmd`, `appendices/` and `assets/bank/` are generated. Edit `chapters/src/` and `bank/` instead.

`selnolig.sty` is an empty stub on purpose: the real package breaks Arabic text under LuaLaTeX.

## Layout

```
bank/chNN/          question bank (single source)
glossary/terms.yaml Arabic-English glossary (single source)
references/books.yaml the three textbooks and the matching chapter of each
chapters/src/       hand-written explanations with @example(id) and @problems markers
chapters/           generated chapters
appendices/         generated solutions and factor tables
ee/engine.py        template engine, Python
assets/             website engine, random-number widget, KaTeX, marked
tex/                LaTeX preamble and the site script loader
tools/              build, lint, cross-engine check
```
