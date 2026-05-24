import("player.inventory.personal.MainInventory")

---@class EditorMainInventory : MainInventory
EditorMainInventory = MainInventory:extendAs("player.inventory.personal.editor.EditorMainInventory")

---@public
---@return EditorMainInventory
---@param player Player
function EditorMainInventory.new(player)
    return EditorMainInventory:super(MainInventory.new(player))
end
