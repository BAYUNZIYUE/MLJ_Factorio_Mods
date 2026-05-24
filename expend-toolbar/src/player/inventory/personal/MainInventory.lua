import("factorio.Icon")
import("factorio.events.inventory.PlayerMainInventoryChanged")
import("player.inventory.Content")
import("player.inventory.Inventory")

---@class MainInventory : Inventory
---@field private __icon Icon
---@field private _player Player
---@field private _upToDate boolean
MainInventory = Inventory:extendAs("player.inventory.personal.editor.MainInventory")
MainInventory.__icon = Icon.new("entity", "character")

---@public
---@return MainInventory
---@param player Player
function MainInventory.new(player)
    local this = MainInventory:super(Inventory.new(player))
    this._player = player
    this._upToDate = false
    this._player:eventBus():subscribeTo(PlayerMainInventoryChanged, this, function()
        this:invalidate()
    end)
    return this
end

function MainInventory:icon()
    return MainInventory.__icon
end

function MainInventory:alwaysVisible()
    return true
end

---@private
function MainInventory:invalidate()
    self._upToDate = false
end

function MainInventory:refresh()
    if not self._upToDate and game.tick % self._player:settings():characterInventoriesContentRefreshInterval() == 0 then
        self:forceRefresh()
        return true
    else
        return false
    end
end

function MainInventory:forceRefresh()
    self:setContent(self:freshContent())
    self._upToDate = true
end

---@private
---@return Content
function MainInventory:freshContent()
    if self:inventory() then
        return Content.new():addAll(self:inventory().get_contents())
    else
        return Content.empty()
    end
end

function MainInventory:pick(item)
    local inventory = self:inventory()
    if inventory then
        local stack, slotIndex = inventory.find_item_stack(item:nameQualityPair())
        if stack then
            local successful = self._player:cursor():pickStack(stack)
            if successful then
                if not stack.valid_for_read then -- is empty
                    self._player:luaPlayer().hand_location = { inventory = inventory.index, slot = slotIndex }
                end
                return true
            end
            return false
        else
            return false
        end
    else
        return false
    end
end

---@private
---@return LuaInventory
function MainInventory:inventory()
    return self._player:luaPlayer().get_main_inventory()
end
