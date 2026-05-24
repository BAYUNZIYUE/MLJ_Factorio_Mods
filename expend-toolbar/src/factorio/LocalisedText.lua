---@class LocalisedText : Object
---@field private __empty LocalisedText
---@field private _localisedString table
LocalisedText = Object:extendAs("factorio.LocalisedText")

function LocalisedText.new()
    local this = LocalisedText:super(Object.new())
    this._localisedString = { "" }
    return this
end

---@public
---@return LocalisedText
function LocalisedText.empty()
    return LocalisedText.__empty
end
LocalisedText.__empty = LocalisedText.new()

---@public
---@return self
function LocalisedText:appendNewLine()
    return self:append("\n")
end

---@public
---@return self
---@param localisedText LocalisedText
function LocalisedText:concat(localisedText)
    self:append(localisedText._localisedString)
    return self
end

---@public
---@return self
---@param text string|table
function LocalisedText:append(text)
    if #self._localisedString > 20 then
        self._localisedString = { "", self._localisedString }
    end
    table.insert(self._localisedString, text)
    return self
end

---@public
---@return LocalisedString
function LocalisedText:localisedString()
    return self._localisedString
end
