import("core.Event")

---@class ViewInventoryItemCountChanged : Event
---@field private _qualitiesCount table<string,number>
ViewInventoryItemCountChanged = Event:extendAs("player.inventory.Inventory.ViewInventoryItemCountChanged")

---@param name string
---@param qualitiesCount table<string,number>
function ViewInventoryItemCountChanged.new(name, qualitiesCount)
    local this = ViewInventoryItemCountChanged:super(Event.new(name))
    this._qualitiesCount = qualitiesCount
    return this
end

---@public
---@param quality string
---@return number
function ViewInventoryItemCountChanged:count(quality)
    return self._qualitiesCount[quality]
end
