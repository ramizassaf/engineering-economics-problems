-- PDF only: set each number in running text (10%, 7.5%, 2.5, 30,000) as an
-- English run. In Arabic text the percent sign moves to the left (%10) and
-- the Arabic font draws the decimal point and the thousands comma as Arabic
-- marks. The site already shows 10% and 2.5, so the PDF now matches it.
if not FORMAT:match("latex") then
  return {}
end

local function is_digit(c)
  return c ~= "" and c:match("%d") ~= nil
end

-- Return the end index of a number that starts at position a.
local function number_end(s, a)
  local b = a
  while true do
    local c = s:sub(b + 1, b + 1)
    if is_digit(c) then
      b = b + 1
    elseif (c == "." or c == ",") and is_digit(s:sub(b + 2, b + 2)) then
      b = b + 2
    else
      break
    end
  end
  if s:sub(b + 1, b + 1) == "%" then
    b = b + 1
  end
  return b
end

local function wrap(el)
  local s = el.text
  if not s:find("%d") then
    return nil
  end
  local out, pos = {}, 1
  while true do
    local a = s:find("%d", pos)
    if not a then
      break
    end
    local b = number_end(s, a)
    if a > pos then
      table.insert(out, pandoc.Str(s:sub(pos, a - 1)))
    end
    local num = s:sub(a, b):gsub("%%", "\\%%")
    table.insert(out, pandoc.RawInline("latex", "\\babelsublr{\\foreignlanguage{english}{" .. num .. "}}"))
    pos = b + 1
  end
  if pos <= #s then
    table.insert(out, pandoc.Str(s:sub(pos)))
  end
  return out
end

-- Walk the body only. Metadata holds LaTeX options such as font sizes,
-- which must stay plain text.
function Pandoc(doc)
  doc.blocks = doc.blocks:walk({ Str = wrap })
  return doc
end
