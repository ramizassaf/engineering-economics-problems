"""Generate the factor tables appendix: rows are interest rates, columns are years."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ee.engine import PF, PA, PG, PGEO  # noqa: E402

RATES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20]
GROWTHS = [3, 5, 8]
YEARS = [[1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 12, 15, 20, 25]]
TABLES = [
    ("P/F", PF, "معامل القيمة الحالية لمبلغ واحد"),
    ("P/A", PA, "معامل القيمة الحالية لدفعات متساوية"),
    ("P/G", PG, "معامل القيمة الحالية للدفعات المتدرجة خطيا"),
]

out = ["# جداول المعاملات {#sec-tables}", "",
       "في كل جدول: الصف هو نسبة الفائدة، والعمود هو عدد السنوات. ابحث عن صف النسبة، ثم انتقل إلى عمود السنوات. كل جدول مقسوم إلى جزأين حسب عدد السنوات.",
       "",
       "باقي المعاملات تحسبها من هذه الجداول الثلاثة:", "",
       "$$",
       r"(F/P) = \frac{1}{(P/F)} \qquad (A/P) = \frac{1}{(P/A)} \qquad (F/A) = \frac{(P/A)}{(P/F)}",
       "$$", "",
       "$$",
       r"(A/F) = (A/P) - i \qquad (A/G) = \frac{(P/G)}{(P/A)}",
       "$$", "",
       "الجداول تغطي النسب والسنوات الأكثر استخداما في الكتاب فقط. لأي نسبة أو مدة غير موجودة، احسب المعامل من معادلته في الفصلين الأول والثاني، أو بدالة في Excel. لا تستخدم الاستيفاء بين عمودين متباعدين، لأن المعاملات ليست خطية في عدد السنوات.",
       "",
       "صف 0% يعطي قيم المعاملات بدون فائدة: مجموع المبالغ كما هي.", ""]
for name, f, title in TABLES:
    out += [f"## {title} ({name}) {{.unnumbered}}", ""]
    for cols in YEARS:
        out.append("| i \\\\ n | " + " | ".join(str(n) for n in cols) + " |")
        out.append("| --- |" + " --- |" * len(cols))
        for r in RATES:
            vals = [f"{f(r / 100, n):.4f}".replace("-0.0000", "0.0000") for n in cols]
            out.append(f"| {r}% | " + " | ".join(vals) + " |")
        out.append("")
out += ["## معامل القيمة الحالية للسلسلة المتدرجة نسبيا (P/A1) {.unnumbered}", "",
        "الدفعة الأولى في نهاية السنة 1، وتنمو بنسبة ثابتة g كل سنة. القيمة الحالية تساوي الدفعة الأولى مضروبة في المعامل:",
        "",
        "$$",
        r"P = A_1\,(P/A_1,\ g,\ i,\ n)",
        "$$", "",
        "عندما تتساوى النسبتان، كل دفعة تخصم بقدر ما نمت، فيصبح المعامل n مقسومة على واحد زائد i. علامة النجمة في الجدول تدل على هذا الصف.",
        ""]
for g in GROWTHS:
    out += [f"### نسبة النمو {g}% {{.unnumbered}}", ""]
    for cols in YEARS:
        out.append("| i \\\\ n | " + " | ".join(str(n) for n in cols) + " |")
        out.append("| --- |" + " --- |" * len(cols))
        for r in RATES:
            vals = [f"{PGEO(g / 100, r / 100, n):.4f}" for n in cols]
            mark = "*" if r == g else ""
            out.append(f"| {r}%{mark} | " + " | ".join(vals) + " |")
        out.append("")
(ROOT / "appendices").mkdir(exist_ok=True)
(ROOT / "appendices" / "tables.qmd").write_text("\n".join(out), encoding="utf-8")
print("tables: written")
