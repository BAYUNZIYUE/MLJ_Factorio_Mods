import("player.inventory.ViewInventory")
import("player.inventory.CompositeInventory")
import("player.inventory.personal.CursorInventory")
import("player.inventory.personal.VehicleTrunkInventory")
import("player.inventory.personal.character.NonPersonalLogisticNetworksInventory")
import("player.inventory.personal.editor.EditorMainInventory")

---@class EditorViewInventory : ViewInventory
---@field private _player Player
EditorViewInventory = ViewInventory:extendAs("player.inventory.personal.editor.EditorViewInventory")

---@public
---@param player Player
---@param initialContent Content
---@return EditorViewInventory
function EditorViewInventory.new(player, initialContent)
    local settings = player:settings()
    return EditorViewInventory:super(
            ViewInventory.new(
                    player,
                    initialContent,
                    EditorViewInventory.newMains(player),
                    EditorViewInventory.newSides(player)
            )
    )
end

---@private
---@param player Player
---@return Inventory[]
function EditorViewInventory.newMains(player)
    local mains = {
        CompositeInventory.new(player, {
            EditorMainInventory.new(player),
            CursorInventory.new(player)
        })
    }

    if player:settings():showVehicleInventoriesContent() then
        table.insert(mains, VehicleTrunkInventory.new(player))
    end

    return mains
end

---@private
---@param player Player
---@return Inventory[]
function EditorViewInventory.newSides(player)
    local sides = {}

    if player:settings():showLogisticNetworksContent() then
        table.insert(sides, NonPersonalLogisticNetworksInventory.new(player))
    end

    return sides
end
