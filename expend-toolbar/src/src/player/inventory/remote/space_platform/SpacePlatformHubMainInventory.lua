import("player.inventory.Content")
import("player.inventory.Inventory")

---@class SpacePlatformHubMainInventory : Inventory
---@field private _player Player
SpacePlatformHubMainInventory = Inventory:extendAs("player.inventory.remote.space_platform.SpacePlatformHubMainInventory")
SpacePlatformHubMainInventory.__icon = Icon.new("item", "space-platform-foundation")

---@private
---@param player Player
---@return SpacePlatformHubMainInventory
function SpacePlatformHubMainInventory.new(player)
    local this = SpacePlatformHubMainInventory:super(Inventory.new(player))
    this._player = player
    return this
end

function SpacePlatformHubMainInventory:icon()
    return SpacePlatformHubMainInventory.__icon
end

function SpacePlatformHubMainInventory:alwaysVisible()
    return true
end

function SpacePlatformHubMainInventory:refresh()
    if game.tick % self._player:settings():logisticNetworksContentRefreshInterval() == 0 then
        return self:forceRefresh()
    else
        return false
    end
end

function SpacePlatformHubMainInventory:forceRefresh()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    self:setContent(freshContent)
    return not oldContent:equals(freshContent)
end

function SpacePlatformHubMainInventory:freshContent()
    local platform = self._player:luaPlayer().surface.platform
    local hub = platform and platform.hub or nil
    return hub
            and Content.new():addAll(hub.get_inventory(defines.inventory.hub_main).get_contents())
            or Content.empty()
end
