import("player.inventory.personal.MainInventory")

---@class CharacterMainInventory : MainInventory
CharacterMainInventory = MainInventory:extendAs("player.inventory.personal.character.CharacterMainInventory")

---@public
---@return CharacterMainInventory
---@param player Player
function CharacterMainInventory.new(player)
    return CharacterMainInventory:super(MainInventory.new(player))
end
