-- Colors for the book, PDF and website.
--   * Worked examples (div.ee-item with data-kind="example") sit in a shaded box.
--   * Display equations in the chapter text, outside examples and problems,
--     sit in a small framed box in the accent color.
-- Solutions appendices and the derivations appendix are left plain: they are
-- chains of calculation steps, and boxing every step hides the main formulas.

local function is_plain_file()
  local f = (quarto and quarto.doc and quarto.doc.input_file) or ""
  return f:match("solutions%-ch") or f:match("derivations")
end

local function only_display_math(para)
  if #para.content ~= 1 then return nil end
  local el = para.content[1]
  if el.t == "Math" and el.mathtype == "DisplayMath" then return el.text end
  return nil
end

local function box_equation(tex)
  if FORMAT:match("latex") then
    return pandoc.RawBlock("latex",
      "\\begin{center}\\eqbox{$\\displaystyle " .. tex .. "$}\\end{center}")
  end
  return pandoc.Div({ pandoc.Para({ pandoc.Math("DisplayMath", tex) }) },
    pandoc.Attr("", { "ee-eqbox" }))
end

local function example_box(div)
  if FORMAT:match("latex") then
    local anchor = ""
    if div.identifier ~= "" then
      anchor = "\\phantomsection\\hypertarget{" .. div.identifier .. "}{}\\label{" .. div.identifier .. "}"
    end
    local out = { pandoc.RawBlock("latex", "\\begin{exbox}" .. anchor) }
    for _, b in ipairs(div.content) do table.insert(out, b) end
    table.insert(out, pandoc.RawBlock("latex", "\\end{exbox}"))
    return out
  end
  return div
end

function Pandoc(doc)
  local plain = is_plain_file()
  local blocks = {}
  for _, b in ipairs(doc.blocks) do
    if b.t == "Div" and b.classes:includes("ee-item") and b.attributes["data-kind"] == "example" then
      local r = example_box(b)
      if r.t then table.insert(blocks, r) else for _, x in ipairs(r) do table.insert(blocks, x) end end
    elseif b.t == "Para" and not plain and only_display_math(b) then
      table.insert(blocks, box_equation(only_display_math(b)))
    else
      table.insert(blocks, b)
    end
  end
  doc.blocks = blocks
  return doc
end
