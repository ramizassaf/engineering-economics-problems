import sys, fitz
doc = fitz.open(sys.argv[1])
W = doc[0].rect.width
lim_r, lim_l = W - 2.2/2.54*72 + 1.5, 2.2/2.54*72 - 1.5
hits = []
for pno, page in enumerate(doc):
    if page.rect.width > page.rect.height: continue  # landscape pages
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if "Mono" in s["font"] and (s["bbox"][2] > lim_r or s["bbox"][0] < lim_l) and s["text"].strip():
                    hits.append((pno + 1, round(s["bbox"][2] - lim_r, 1), s["text"][:60]))
print(len(hits), "monospace spans past the margin on", len({h[0] for h in hits}), "pages")
for h in hits[:int(sys.argv[2]) if len(sys.argv) > 2 else 15]: print(h)
