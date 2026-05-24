import("player.inventory.ViewInventory")
import("player.inventory.remote.planet.AllLogisticNetworksInventory")

---@class PlanetViewInventory : ViewInventory
---@field private _player Player
PlanetViewInventory = ViewInventory:extendAs("player.inventory.remote.platform.PlanetViewInventory")

---@public
---@param player Player
---@param initialContent Content
---@return PlanetViewInventory
function PlanetViewInventory.new(player, initialContent)
    return PlanetViewInventory:super(
            ViewInventory.new(
                    player,
                    initialContent,
                    PlanetViewInventory.newMains(player),
                    {}
            )
    )
end

---@private
---@param player Player
---@return Inventory[]
function PlanetViewInventory.newMains(player)
    local mains = {}

    if player:settings():showLogisticNetworksContent() then
        table.insert(mains, AllLogisticNetworksInventory.new(player))
    end

    return mains
end
