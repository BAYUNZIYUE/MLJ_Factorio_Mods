import("factorio.Icon")
import("factorio.events.inventory.PlayerTrashInventoryChanged")
import("player.inventory.Content")
import("player.inventory.Inventory")

---@class CharacterTrashInventory : Inventory
---@field private __icon Icon
---@field private _player Player
---@field private _upToDate boolean
---@field private _craftingCategories table<string, boolean>
CharacterTrashInventory = Inventory:extendAs("player.inventory.personal.CharacterTrashInventory")
CharacterTrashInventory.__icon = Icon.new("img", Toolbars.icons.characterTrash)

---@public
---@return CharacterTrashInventory
---@param player Player
function CharacterTrashInventory.new(player)
    local this = CharacterTrashInventory:super(Inventory.new(player))
    this._player = player
    this._upToDate = false
    this._player:eventBus():subscribeTo(PlayerTrashInventoryChanged, this, function()
        this:invalidate()
    end)
    return this
end

function CharacterTrashInventory:icon()
    return CharacterTrashInventory.__icon
end

---@private
function CharacterTrashInventory:invalidate()
    self._upToDate = false
end

function CharacterTrashInventory:refresh()
    if not self._upToDate and game.tick % self._player:settings():characterInventoriesContentRefreshInterval() == 0 then
        self:forceRefresh()
        return true
    else
        return false
    end
end

function CharacterTrashInventory:forceRefresh()
    self._content = self:freshContent()
    self._upToDate = true
end

---@private
---@return Content
function CharacterTrashInventory:freshContent()
    local inventory = self:inventory()
    if inventory then
        return Content.new():addAll(inventory.get_contents())
    else
        return Content.empty()
    end
end

function CharacterTrashInventory:pick(item)
    local inventory = self:inventory()
    if inventory then
        local stack, slotIndex = self:inventory().find_item_stack(item:nameQualityPair())
        if stack then
            local successful = self._player:cursor():pickStack(stack)
            if successful then
                if not stack.valid_for_read then -- is empty
                    self._player:luaPlayer().hand_location = { inventory = inventory.index, slot = slotIndex }
                end
                return true
            else
                return false
            end
        else
            self:invalidate()
            return false
        end
    else
        return false
    end
end

---@private
---@return LuaInventory
function CharacterTrashInventory:inventory()
    return self._player:luaPlayer().get_inventory(defines.inventory.character_trash)
end
