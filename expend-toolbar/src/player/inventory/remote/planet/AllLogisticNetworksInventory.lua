import("factorio.Icon")
import("player.inventory.Content")
import("player.inventory.Inventory")

---@class AllLogisticNetworksInventory : Inventory
---@field private __icon Icon
---@field private _player Player
AllLogisticNetworksInventory = Inventory:extendAs("player.inventory.remote.planet.AllLogisticNetworksInventory")
AllLogisticNetworksInventory.__icon = Icon.new("item", "construction-robot")

---@private
---@param player Player
---@return AllLogisticNetworksInventory
function AllLogisticNetworksInventory.new(player)
    local this = AllLogisticNetworksInventory:super(Inventory.new(player))
    this._player = player
    return this
end

function AllLogisticNetworksInventory:icon()
    return AllLogisticNetworksInventory.__icon
end

function AllLogisticNetworksInventory:refresh()
    if game.tick % self._player:settings():logisticNetworksContentRefreshInterval() == 0 then
        return self:forceRefresh()
    else
        return false
    end
end

function AllLogisticNetworksInventory:forceRefresh()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    self:setContent(freshContent)
    return not oldContent:equals(freshContent)
end

---@private
---@return Content
function AllLogisticNetworksInventory:freshContent()
    local luaPlayer = self._player:luaPlayer()
    local networks = luaPlayer.surface.find_logistic_networks_by_construction_area(luaPlayer.position, luaPlayer.force)

    local freshContent = Content.new()
    for _, network in ipairs(networks) do
        freshContent:addAll(network.get_contents())
    end
    return freshContent
end
