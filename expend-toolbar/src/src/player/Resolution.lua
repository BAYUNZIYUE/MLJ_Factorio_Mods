---@class Resolution : Object
---@field private _width number
---@field private _height number
Resolution = Object:extendAs("player.Resolution")

---@return Resolution
function Resolution.new(width, height)
    local this = Resolution:super(Object.new())
    this._width = width
    this._height = height
    return this
end

---@public
---@return number
function Resolution:width()
    return self._width
end

---@public
---@return number
function Resolution:height()
    return self._height
end
