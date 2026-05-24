import("player.inventory.CompositeInventory")
import("player.inventory.ViewInventory")
import("player.inventory.personal.CursorInventory")
import("player.inventory.personal.VehicleTrunkInventory")
import("player.inventory.personal.VehicleTrashInventory")
import("player.inventory.personal.character.CharacterMainInventory")
import("player.inventory.personal.character.CharacterTrashInventory")
import("player.inventory.personal.character.NonPersonalLogisticNetworksInventory")

---@class CharacterViewInventory : ViewInventory
---@field private _player Player
CharacterViewInventory = ViewInventory:extendAs("player.inventory.personal.character.CharacterViewInventory")

---@public
---@param player Player
---@param initialContent Content
---@return CharacterViewInventory
function CharacterViewInventory.new(player, initialContent)
    return CharacterViewInventory:super(
            ViewInventory.new(
                    player,
                    initialContent,
                    CharacterViewInventory.newMains(player),
                    CharacterViewInventory.newSides(player)
            )
    )
end

---@private
---@param player Player
---@return Inventory[]
function CharacterViewInventory.newMains(player)
    local mains = {
        CompositeInventory.new(player, {
            CharacterMainInventory.new(player),
            CursorInventory.new(player)
        }),
        CharacterTrashInventory.new(player),
    }

    if player:settings():showVehicleInventoriesContent() then
        table.insert(mains, VehicleTrunkInventory.new(player))
        table.insert(mains, VehicleTrashInventory.new(player))
    end

    return mains
end

---@private
---@param player Player
---@return Inventory[]
function CharacterViewInventory.newSides(player)
    local sides = {}

    if player:settings():showLogisticNetworksContent() then
        table.insert(sides, NonPersonalLogisticNetworksInventory.new(player))
    end

    return sides
end
