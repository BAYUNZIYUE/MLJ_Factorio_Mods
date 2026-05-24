import("Item")
import("EventBus")
import("player.Resolution")

---@class Display : Object
---@field private _resolution Resolution
---@field private _scale number
Display = Object:extendAs("player.Display")

---@return Display
---@param resolution Resolution
---@param scale number
function Display.new(resolution, scale)
    local this = Display:super(Object.new())
    this._resolution = resolution
    this._scale =  scale
    return this
end

---@public
---@param size number
---@return number
function Display:scale(size)
    return math.floor(size * self._scale)
end

---@public
---@return Resolution
function Display:resolution()
    return self._resolution
end

---@public
---@return number
function Display:scaleValue()
    return self._scale
end
