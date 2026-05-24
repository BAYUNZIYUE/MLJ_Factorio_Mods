import("factorio.Icon")
import("player.inventory.Content")
import("player.inventory.Inventory")

---@class VehicleTrashInventory : Inventory
---@field private __carTrashIcon Icon
---@field private __tankTrashIcon Icon
---@field private __spidertronTrashIcon Icon
---@field private _icon Icon
---@field private _player Player
VehicleTrashInventory = Inventory:extendAs("player.inventory.personal.VehicleTrashInventory")
VehicleTrashInventory.__carTrashIcon = Icon.new("img", Toolbars.icons.carTrash)
VehicleTrashInventory.__tankTrashIcon = Icon.new("img", Toolbars.icons.tankTrash)
VehicleTrashInventory.__spidertronTrashIcon = Icon.new("img", Toolbars.icons.spidertronTrash)

---@public
---@param player Player
---@return VehicleTrashInventory
function VehicleTrashInventory.new(player)
    local this = VehicleTrashInventory:super(Inventory.new(player))
    this._player = player
    this._icon = VehicleTrashInventory.__carTrashIcon
    return this
end

function VehicleTrashInventory:icon()
    return self._icon
end

function VehicleTrashInventory:refresh()
    if game.tick % self._player:settings():vehicleInventoriesContentRefreshInterval() == 0 then
        return self:forceRefresh()
    else
        return false
    end
end

function VehicleTrashInventory:forceRefresh()
    local oldContent = self:content()
    local freshContent = self:freshContent()
    self:setContent(freshContent)
    return not oldContent:equals(freshContent)
end

---@private
---@return Content
function VehicleTrashInventory:freshContent()
    if self:inventory() then
        return Content.new():addAll(self:inventory().get_contents())
    else
        return Content.empty()
    end
end

function VehicleTrashInventory:pick(item)
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
function VehicleTrashInventory:inventory()
    ---@type LuaEntity
    local vehicle = self._player:luaPlayer().vehicle
    if vehicle then
        if vehicle.name == "car" then
            self._icon = VehicleTrashInventory.__carTrashIcon
        elseif vehicle.name == "tank" then
            self._icon = VehicleTrashInventory.__tankTrashIcon
        elseif vehicle.name == "spidertron" then
            self._icon = VehicleTrashInventory.__spidertronTrashIcon
        else
            self._icon = VehicleTrashInventory.__carTrashIcon
        end
    end
    return vehicle and vehicle.get_inventory(defines.inventory.car_trash) or nil
end
