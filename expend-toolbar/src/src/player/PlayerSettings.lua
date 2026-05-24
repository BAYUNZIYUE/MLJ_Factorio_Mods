import("factorio.events.settings.PlayerSettingChanged")
import("player.events.settings.ShowVehicleInventoriesContentSettingChanged")
import("player.events.settings.ShowLogisticNetworksContentSettingChanged")

---@class PlayerSettings : Object
---@field private _luaPlayer LuaPlayer
---@field private _eventBus EventBus
---@field private _crafting boolean
---@field private _tooltipDelay number
---@field private _tooltipRefreshInterval number
---@field private _showControlsInTheTooltip boolean
---@field private _characterInventoriesContentRefreshInterval number
---@field private _showVehicleInventoriesContent boolean
---@field private _vehicleInventoriesContentRefreshInterval number
---@field private _showLogisticNetworksContent boolean
---@field private _logisticNetworksContentRefreshInterval number
PlayerSettings = Object:extendAs("player.PlayerSettings")

---@return Settings
---@param luaPlayer LuaPlayer
---@param eventBus EventBus
function PlayerSettings.new(luaPlayer, eventBus)
    local this = PlayerSettings:super(Object.new())
    this._luaPlayer = luaPlayer
    this._eventBus = eventBus

    this:updateCrafting()
    this:updateTooltipDelay()
    this:updateTooltipRefreshInterval()
    this:updateShowControlsInTheTooltip()

    this:updateCharacterInventoriesContentRefreshInterval()

    this:updateShowVehicleInventoriesContent()
    this:updateVehicleInventoriesContentRefreshInterval()

    this:updateShowLogisticNetworksContent()
    this:updateLogisticNetworksContentRefreshInterval()

    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.crafting), this, function()
        this:updateCrafting()
    end)
    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.tooltipDelay), this, function()
        this:updateTooltipDelay()
    end)
    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.tooltipRefreshInterval), this, function()
        this:updateTooltipRefreshInterval()
    end)
    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.showControlsInTheTooltip), this, function()
        this:updateShowControlsInTheTooltip()
    end)

    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.characterInventoriesContentRefreshInterval), this, function()
        this:updateCharacterInventoriesContentRefreshInterval()
    end)

    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.showVehicleInventoriesContent), this, function()
        this:updateShowVehicleInventoriesContent()
    end)
    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.vehicleInventoriesContentRefreshInterval), this,
                         function()
                             this:updateVehicleInventoriesContentRefreshInterval()
                         end)

    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.showLogisticNetworksContent), this, function()
        this:updateShowLogisticNetworksContent()
    end)
    eventBus:subscribeTo(PlayerSettingChanged.new(Toolbars.settings.logisticNetworksContentRefreshInterval), this,
                         function()
                             this:updateLogisticNetworksContentRefreshInterval()
                         end)
    return this
end

---@public
---@return boolean
function PlayerSettings:crafting()
    return self._crafting
end

---@private
function PlayerSettings:updateCrafting()
    self._crafting = self._luaPlayer.mod_settings[Toolbars.settings.crafting].value
end

---@public
---@return number in ticks
function PlayerSettings:tooltipDelay()
    return self._tooltipDelay
end

---@private
function PlayerSettings:updateTooltipDelay()
    self._tooltipDelay = Time.millisToTicks(self._luaPlayer.mod_settings[Toolbars.settings.tooltipDelay].value)
end

---@public
---@return number in ticks
function PlayerSettings:tooltipRefreshInterval()
    return self._tooltipRefreshInterval
end

---@private
function PlayerSettings:updateTooltipRefreshInterval()
    self._tooltipRefreshInterval = math.floor(self._luaPlayer.mod_settings[Toolbars.settings.tooltipRefreshInterval].value)
end

---@public
---@return boolean
function PlayerSettings:showControlsInTheTooltip()
    return self._showControlsInTheTooltip
end

---@private
function PlayerSettings:updateShowControlsInTheTooltip()
    self._showControlsInTheTooltip = self._luaPlayer.mod_settings[Toolbars.settings.showControlsInTheTooltip].value
end

---@public
---@return number ticks
function PlayerSettings:characterInventoriesContentRefreshInterval()
    return self._characterInventoriesContentRefreshInterval
end

---@private
function PlayerSettings:updateCharacterInventoriesContentRefreshInterval()
    self._characterInventoriesContentRefreshInterval = self._luaPlayer.mod_settings[Toolbars.settings.characterInventoriesContentRefreshInterval].value
end

---@public
---@return boolean
function PlayerSettings:showVehicleInventoriesContent()
    return self._showVehicleInventoriesContent
end

---@private
function PlayerSettings:updateShowVehicleInventoriesContent()
    self._showVehicleInventoriesContent = self._luaPlayer.mod_settings[Toolbars.settings.showVehicleInventoriesContent].value
    self._eventBus:publish(ShowVehicleInventoriesContentSettingChanged)
end

---@public
---@return number ticks
function PlayerSettings:vehicleInventoriesContentRefreshInterval()
    return self._vehicleInventoriesContentRefreshInterval
end

---@private
function PlayerSettings:updateVehicleInventoriesContentRefreshInterval()
    self._vehicleInventoriesContentRefreshInterval = self._luaPlayer.mod_settings[Toolbars.settings.vehicleInventoriesContentRefreshInterval].value
end

---@public
---@return boolean
function PlayerSettings:showLogisticNetworksContent()
    return self._showLogisticNetworksContent
end

---@private
function PlayerSettings:updateShowLogisticNetworksContent()
    self._showLogisticNetworksContent = self._luaPlayer.mod_settings[Toolbars.settings.showLogisticNetworksContent].value
    self._eventBus:publish(ShowLogisticNetworksContentSettingChanged)
end

---@public
---@return number ticks
function PlayerSettings:logisticNetworksContentRefreshInterval()
    return self._logisticNetworksContentRefreshInterval
end

---@private
function PlayerSettings:updateLogisticNetworksContentRefreshInterval()
    self._logisticNetworksContentRefreshInterval = self._luaPlayer.mod_settings[Toolbars.settings.logisticNetworksContentRefreshInterval].value
end
