import("Event")

---@class SpidertronDeleted : Event
---@field private _unitNumber number
SpidertronDeleted = Event:extendAs("factorio.events.entities.SpidertronDeleted")

---@public
---@param unitNumber number
---@return SpidertronDeleted
function SpidertronDeleted.new(unitNumber)
    local instance = SpidertronDeleted:super(Event.new(unitNumber))
    instance._unitNumber = unitNumber
    return instance
end

---@public
---@return number
function SpidertronDeleted:unitNumber()
    return self._unitNumber
end
