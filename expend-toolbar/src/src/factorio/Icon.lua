import("factorio.RichText")

---@class Icon : Object
---@field private __EMPTY Icon
---@field private _richText string
Icon = Object:extendAs("factorio.Icon")

---@public
---@param type string
---@param name string
---@return Icon
function Icon.new(type, name)
    local this = Icon:super(Object.new())
    this._richText = RichText.icon(type, name)
    return this
end

---@public
---@return string
function Icon:richText()
    return self._richText
end

---@public
---@return Icon
function Icon.empty()
    return Icon.__EMPTY
end

Icon.__EMPTY = Icon.new("img", Toolbars.icons.empty)
