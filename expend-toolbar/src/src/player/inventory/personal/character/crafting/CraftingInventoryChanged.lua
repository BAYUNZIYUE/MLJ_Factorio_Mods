import("Event")

---@class CraftingInventoryChanged : Event
CraftingInventoryChanged = Event:extendAs("player.inventory.personal.character.crafting.CraftingInventoryChanged")

---@public
---@return CraftingInventoryChanged
function CraftingInventoryChanged.new()
    return CraftingInventoryChanged:super(Event.new())
end
