import("player.inventory.Content")
import("player.inventory.Inventory")

---@class CompositeInventory : Inventory
---@field private _player Player
---@field private _subinventories Inventory[]
CompositeInventory = Inventory:extendAs("player.inventory.CompositeInventory")

---@public
---@param player Player
---@param subinventories Inventory[]
---@return CompositeInventory
function CompositeInventory.new(player, subinventories)
    local this = CompositeInventory:super(Inventory.new(player))
    this._player = player
    this._subinventories = subinventories
    return this
end

function CompositeInventory:delete()
    for _, subinventory in ipairs(self._subinventories) do
        subinventory:delete()
    end
end

function CompositeInventory:icon()
    return self._subinventories[1]:icon()
end

function CompositeInventory:alwaysVisible()
    return self._subinventories[1]:alwaysVisible()
end

function CompositeInventory:refresh()
    local changed = false
    for _, subinventory in ipairs(self._subinventories) do
        local subChanged = subinventory:refresh()
        changed = changed or subChanged
    end

    if changed then
        local freshTotalContent = Content.new()
        for _, subinventory in ipairs(self._subinventories) do
            freshTotalContent:merge(subinventory:content())
        end
        self:setContent(freshTotalContent)
    end

    return changed
end

function CompositeInventory:forceRefresh()
    for _, subinventory in ipairs(self._subinventories) do
        subinventory:refresh()
    end

    local freshTotalContent = Content.new()
    for _, subinventory in ipairs(self._subinventories) do
        freshTotalContent:merge(subinventory:content())
    end
    self:setContent(freshTotalContent)
end

function CompositeInventory:pick(item)
    for i = #self._subinventories, 1, -1 do
        local subinventory = self._subinventories[i]
        if subinventory:pick(item) then
            return true
        end
    end
    return false
end

function CompositeInventory:craftingPlansInDescendingCountOrderForAnItem(itemName)
    ---@type CraftingPlan[]
    local plans = {}
    for _, subinventory in ipairs(self._subinventories) do
        for _, plan in ipairs(subinventory:craftingPlansInDescendingCountOrderForAnItem(itemName)) do
            table.insert(plans, plan)
        end
    end
    table.sort(plans, function(first, second) return first:compareTo(second) end)
    return plans
end

---@public
---@return Inventory[]
function CompositeInventory:subinventories()
    return self._subinventories
end
