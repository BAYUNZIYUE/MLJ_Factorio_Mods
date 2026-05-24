import("player.inventory.personal.MainInventory")

---@class GodMainInventory : MainInventory
GodMainInventory = MainInventory:extendAs("player.inventory.personal.editor.GodMainInventory")

---@public
---@return GodMainInventory
---@param player Player
function GodMainInventory.new(player)
    return GodMainInventory:super(MainInventory.new(player))
end
