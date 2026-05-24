import("factorio.Icon")
import("player.inventory.Content")
import("player.inventory.Inventory")

---@class VehicleTrunkInventory : Inventory
---@field private __carIcon Icon
---@field private __tankIcon Icon
---@field private __spidertronIcon Icon
---@field private _icon Icon
---@field private _player Player
VehicleTrunkInventory = Inventory:extendAs("player.inventory.personal.VehicleTrunkInventory")
VehicleTrunkInventory.__carIcon = Icon.new("item", "car")
VehicleTrunkInventory.__tankIcon = Icon.new("item", "tank")
VehicleTrunkInventory.__spidertronIcon = Icon.new("item", "spidertron")

---@public
---@param player Player
---@return VehicleTrunkInventory
function VehicleTrunkInventory.new(player)
    local this = VehicleTrunkInventory:super(Inventory.new(player))
    this._player = player
    this._icon = VehicleTrunkInventory.__carIcon
    return this
end

function VehicleTrunkInventory:icon()
    return self._icon
end

function VehicleTrunkInventory:refresh()
    if game.tick % self._player:settings():vehicleInventoriesContentRefreshInterval() == 0 then
        return self:forceRefresh()
    else
        return false
    end
end

function VehicleTrunkInventory:forceRefresh()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    self:setContent(freshContent)
    return not oldContent:equals(freshContent)
end

---@private
---@return Content
function VehicleTrunkInventory:freshContent()
    if self:inventory() then
        return Content.new():addAll(self:inventory().get_contents())
    else
        return Content.empty()
    end
end

function VehicleTrunkInventory:pick(item)
    local inventory = self:inventory()
    if inventory then
        local stack, slotIndex = inventory.find_item_stack(item:nameQualityPair())
        if stack then
            return self._player:cursor():pickStack(stack)
        else
            return false
        end
    else
        return false
    end
end

---@private
---@return LuaInventory
function VehicleTrunkInventory:inventory()
    ---@type LuaEntity
    local vehicle = self._player:luaPlayer().vehicle
    if vehicle then
        if vehicle.name == "car" then
            self._icon = VehicleTrunkInventory.__carIcon
        elseif vehicle.name == "tank" then
            self._icon = VehicleTrunkInventory.__tankIcon
        elseif vehicle.name == "spidertron" then
            self._icon = VehicleTrunkInventory.__spidertronIcon
        else
            self._icon = VehicleTrunkInventory.__carIcon
        end
    end
    return vehicle and vehicle.get_inventory(defines.inventory.car_trunk) or nil
end
