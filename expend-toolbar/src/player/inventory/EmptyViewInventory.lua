import("player.inventory.ViewInventory")

---@class EmptyViewInventory : ViewInventory
EmptyViewInventory = ViewInventory:extendAs("player.inventory.EmptyViewInventory")

---@public
---@param player Player
---@param initialContent Content
---@return EmptyViewInventory
function EmptyViewInventory.new(player, initialContent)
    return EmptyViewInventory:super(ViewInventory.new(player, initialContent, {}, {}))
end
