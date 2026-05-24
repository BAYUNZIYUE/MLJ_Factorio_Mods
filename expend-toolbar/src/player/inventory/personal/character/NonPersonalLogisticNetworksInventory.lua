import("factorio.Icon")
import("player.inventory.Content")
import("player.inventory.Inventory")

---@class NonPersonalLogisticNetworksInventory : Inventory
---@field private __icon Icon
---@field private _player Player
NonPersonalLogisticNetworksInventory = Inventory:extendAs("player.inventory.personal.character.NonPersonalLogisticNetworksInventory")
NonPersonalLogisticNetworksInventory.__icon = Icon.new("item", "construction-robot")

---@public
---@return NonPersonalLogisticNetworksInventory
---@param player Player
function NonPersonalLogisticNetworksInventory.new(player)
    local this = NonPersonalLogisticNetworksInventory:super(Inventory.new(player))
    this._player = player
    return this
end

function NonPersonalLogisticNetworksInventory:icon()
    return NonPersonalLogisticNetworksInventory.__icon
end

function NonPersonalLogisticNetworksInventory:refresh()
    if self._player:eventBus():hasSubscribersFor(InventoryChanged)
            and game.tick % self._player:settings():logisticNetworksContentRefreshInterval() == 0 then
        return self:forceRefresh()
    else
        return false
    end
end

function NonPersonalLogisticNetworksInventory:forceRefresh()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    self:setContent(freshContent)
    return not oldContent:equals(freshContent)
end

---@private
---@return Content
function NonPersonalLogisticNetworksInventory:freshContent()
    local luaPlayer = self._player:luaPlayer()
    local networks = luaPlayer.surface.find_logistic_networks_by_construction_area(luaPlayer.position,
                                                                                   luaPlayer.force)
    ---@type LuaEntity
    local character = self._player:luaPlayer().character
    local characterNetwork = character and character.logistic_network or nil

    local freshContent = Content.new()
    for _, network in ipairs(networks) do
        if network ~= characterNetwork then
            freshContent:addAll(network.get_contents())
        end
    end
    return freshContent
end
