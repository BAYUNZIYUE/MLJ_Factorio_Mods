import("player.inventory.ViewInventory")
import("player.inventory.CompositeInventory")
import("player.inventory.personal.CursorInventory")
import("player.inventory.personal.VehicleTrunkInventory")
import("player.inventory.personal.character.NonPersonalLogisticNetworksInventory")
import("player.inventory.personal.god.GodMainInventory")

---@class GodViewInventory : ViewInventory
---@field private _player Player
GodViewInventory = ViewInventory:extendAs("player.inventory.personal.editor.GodViewInventory")

---@public
---@param player Player
---@param initialContent Content
---@return GodViewInventory
function GodViewInventory.new(player, initialContent)
    local settings = player:settings()
    return GodViewInventory:super(
            ViewInventory.new(
                    player,
                    initialContent,
                    GodViewInventory.newMains(player),
                    GodViewInventory.newSides(player)
            )
    )
end

---@private
---@param player Player
---@return Inventory[]
function GodViewInventory.newMains(player)
    local mains = {
        CompositeInventory.new(player, {
            GodMainInventory.new(player),
            CursorInventory.new(player)
        })
    }
    return mains
end

---@private
---@param player Player
---@return Inventory[]
function GodViewInventory.newSides(player)
    local sides = {}

    if player:settings():showLogisticNetworksContent() then
        table.insert(sides, NonPersonalLogisticNetworksInventory.new(player))
    end

    return sides
end
