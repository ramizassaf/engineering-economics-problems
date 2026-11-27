-- PDF only: a span marked .en is English inside Arabic text. Set it as an
-- English, left-to-right run, so its parentheses and final period stay in
-- place. The site gets the same from dir="ltr" on the span.
if not FORMAT:match("latex") then
  return {}
end

function Span(el)
  if el.classes:includes("en") then
    local out = { pandoc.RawInline("latex", "\\babelsublr{\\foreignlanguage{english}{") }
    for _, x in ipairs(el.content) do
      table.insert(out, x)
    end
    table.insert(out, pandoc.RawInline("latex", "}}"))
    return out
  end
end
