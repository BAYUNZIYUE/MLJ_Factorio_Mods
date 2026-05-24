---@class Inventory : Object
---@field private __emptyPlans CraftingPlan[]
---@field private _player Player
---@field private _content Content
Inventory = Object:extendAs("player.inventory.Inventory")
Inventory.__emptyPlans = {}

---@protected
---@return Inventory
---@param player Player
function Inventory.new(player)
    local this = Inventory:super(Object.new())
    this._player = player
    this._content = Content.new()
    return this
end

---@public
function Inventory:delete()
    self._player:eventBus():unsubscribeFromAll(self)
end

---@public
---@return Icon
function Inventory:icon()
    return Icon.empty()
end

---@public
---@return boolean
function Inventory:alwaysVisible()
    return false
end

---@public
---@return boolean changed
function Inventory:refresh()
    error("Not implemented")
end

---@public
function Inventory:forceRefresh()
    error("Not implemented")
end

---@public
---@param item Item
---@return boolean picked
function Inventory:pick(item)
    return false
end

---@public
---@param itemName string
---@return CraftingPlan[]
function Inventory:craftingPlansInDescendingCountOrderForAnItem(itemName)
    return Inventory.__emptyPlans
end

---@public
---@param content Content
function Inventory:setContent(content)
    self._content = content
end

---@public
---@return Content
function Inventory:content()
    return self._content
end
