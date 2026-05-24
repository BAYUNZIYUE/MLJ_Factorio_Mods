---@class Event : Object
---@field private _category string
Event = Object:extendAs("Event")

---@public
---@param category string optional
---@return Event
function Event.new(category)
    local this = Event:super(Object.new())
    this._category = category and category or nil
    return this
end

---@public
---@return string
function Event:topic()
    return self:className() .. (self._category and "_" .. self._category or "")
end
