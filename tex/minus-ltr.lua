-- HTML only. In right-to-left text a leading minus sign is a neutral
-- character, so the browser shows -2,500 as 2,500- with the sign on the
-- wrong side. A left-to-right mark before the sign keeps it with its number.
-- The PDF does this in percent-ltr.lua instead.
if not FORMAT:match("html") then
  return {}
end

local LRM = "\u{200E}"

function Str(el)
  local s = el.text
  if not s:find("%-%d") then
    return nil
  end
  -- Only a sign: at the start, or after a character that is not a digit or letter (not 3-2 or A-1).
  local out = s:gsub("^%-(%d)", LRM .. "-%1")
  out = out:gsub("([^%w])%-(%d)", "%1" .. LRM .. "-%2")
  out = out:gsub(LRM .. LRM, LRM)
  if out == s then
    return nil
  end
  return pandoc.Str(out)
end
