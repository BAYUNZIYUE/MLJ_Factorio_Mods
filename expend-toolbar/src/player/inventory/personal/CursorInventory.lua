import("factorio.Icon")
import("player.events.CursorStackChanged")
import("player.inventory.Inventory")

---@class CursorInventory : Inventory
---@field private __icon Icon
---@field private _player Player
---@field private _upToDate boolean
CursorInventory = Inventory:extendAs("player.inventory.personal.CursorInventory")
CursorInventory.__icon = Icon.new("img", "utility/hand")
---@public
---@return CursorInventory
---@param player Player
function CursorInventory.new(player)
    local this = CursorInventory:super(Inventory.new(player))
    this._player = player
    this._upToDate = false
    this._content = Content.empty()
    this._player:eventBus():subscribeTo(CursorStackChanged, this, function()
        this:invalidate()
    end)
    return this
end

function CursorInventory:icon()
    return CursorInventory.__icon
end

---@private
function CursorInventory:invalidate()
    self._upToDate = false
end

function CursorInventory:refresh()
    if not self._upToDate and game.tick % self._player:settings():characterInventoriesContentRefreshInterval() == 0 then
        self:forceRefresh()
        return true
    else
        return false
    end
end

function CursorInventory:forceRefresh()
    self._content = self:freshContent()
    self._upToDate = true
end

---@private
---@return Content
function CursorInventory:freshContent()
    if self._player:cursor():holdsItem() then
        if self._player:cursor():currentThingCount() > 0 then
            local item = self._player:cursor():item()
            return Content.new()
                          :add({ name = item:name(),
                                 quality = item:quality(),
                                 count = self._player:cursor():currentThingCount() })
        else
            return Content.empty()
        end
    else
        return Content.empty()
    end
end
