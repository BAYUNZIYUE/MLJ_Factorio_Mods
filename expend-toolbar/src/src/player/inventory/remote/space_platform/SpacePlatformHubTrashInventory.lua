import("player.inventory.Content")
import("player.inventory.Inventory")

---@class SpacePlatformHubTrashInventory : Inventory
---@field private _player Player
SpacePlatformHubTrashInventory = Inventory:extendAs("player.inventory.remote.space_platform.SpacePlatformHubTrashInventory")
SpacePlatformHubTrashInventory.__icon = Icon.new("img", Toolbars.icons.spacePlatformHubTrash)

---@private
---@param player Player
---@return SpacePlatformHubTrashInventory
function SpacePlatformHubTrashInventory.new(player)
    local this = SpacePlatformHubTrashInventory:super(Inventory.new(player))
    this._player = player
    return this
end

function SpacePlatformHubTrashInventory:icon()
    return SpacePlatformHubTrashInventory.__icon
end

function SpacePlatformHubTrashInventory:alwaysVisible()
    return true
end

function SpacePlatformHubTrashInventory:refresh()
    if game.tick % self._player:settings():logisticNetworksContentRefreshInterval() == 0 then
        return self:forceRefresh()
    else
        return false
    end
end

function SpacePlatformHubTrashInventory:forceRefresh()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    self:setContent(freshContent)
    return not oldContent:equals(freshContent)
end

function SpacePlatformHubTrashInventory:freshContent()
    local platform = self._player:luaPlayer().surface.platform
    local hub = platform and platform.hub or nil
    return hub
            and Content.new():addAll(hub.get_inventory(defines.inventory.hub_trash).get_contents())
            or Content.empty()
end
