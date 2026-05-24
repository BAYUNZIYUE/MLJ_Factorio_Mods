import("player.inventory.Content")
import("player.inventory.Inventory")
import("player.inventory.InventoryChanged")
import("player.inventory.ViewInventoryItemCountChanged")

---@class ViewInventory : Inventory
---@field private _player Player
---@field private _initiated boolean
---@field private _oldContent Content
---@field private _mains Inventory[]
---@field private _sides Inventory[]
---@field private _all Inventory[]
ViewInventory = Inventory:extendAs("player.inventory.ViewInventory")

---@public
---@param player Player
---@param mains Inventory[] sum to the total content
---@param sides Inventory[] doesn't sum to the total content
---@param initialContent Content
---@return ViewInventory
function ViewInventory.new(player, initialContent, mains, sides)
    local this = ViewInventory:super(Inventory.new(player))
    this._player = player
    this:setContent(initialContent)
    this._mains = mains
    this._sides = sides
    return this
end

function ViewInventory:delete()
    for _, main in ipairs(self._mains) do
        main:delete()
    end
    for _, side in ipairs(self._sides) do
        side:delete()
    end
end

function ViewInventory:refresh()
    local mainsChanged = self:refreshMains()
    local sidesChanged = self:refreshSides()

    if mainsChanged or sidesChanged then
        self._player:eventBus():publish(InventoryChanged)
    end

    if mainsChanged then
        return self:refreshView()
    else
        return false
    end
end

---@private
---@return boolean changed
function ViewInventory:refreshMains()
    local mainChanged = false
    for _, main in ipairs(self._mains) do
        local changed = main:refresh()
        mainChanged = mainChanged or changed
    end
    return mainChanged
end

---@private
---@return boolean changed
function ViewInventory:refreshSides()
    local sideChanged = false
    for _, side in ipairs(self._sides) do
        local changed = side:refresh()
        sideChanged = sideChanged or changed
    end
    return sideChanged
end

function ViewInventory:forceRefresh()
    self:forceRefreshMains()
    self:forceRefreshSides()
    self._player:eventBus():publish(InventoryChanged)
    self:refreshView()
end

---@private
function ViewInventory:forceRefreshMains()
    for _, main in ipairs(self._mains) do
        main:forceRefresh()
    end
end

---@private
function ViewInventory:forceRefreshSides()
    for _, side in ipairs(self._sides) do
        side:refresh()
    end
end

---@private
---@return boolean changed
function ViewInventory:refreshView()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    local change = oldContent:changedIn(freshContent)
    self:setContent(freshContent)

    for name, qualitiesCount in pairs(change:map()) do
        self._player:eventBus():publish(ViewInventoryItemCountChanged.new(name, qualitiesCount))
    end

    return not change:isEmpty()
end

---@private
---@return Content
function ViewInventory:freshContent()
    local content = Content.new()
    for _, main in ipairs(self._mains) do
        content:merge(main:content())
    end
    return content
end

function ViewInventory:pick(item)
    for i = #self._sides, 1, -1 do
        local side = self._sides[i]
        if side:pick(item) then return end
    end
    for i = #self._mains, 1, -1 do
        local main = self._mains[i]
        if main:pick(item) then return end
    end
    self._player:cursor():pickGhost(item)
end

---@public
---@return Inventory[]
function ViewInventory:mains()
    return self._mains
end

---@public
---@return Inventory[]
function ViewInventory:sides()
    return self._sides
end
