import("EventBus")
import("Scheduler")
import("factorio.events.general.ControllerChanged")
import("factorio.events.general.SurfaceChanged")
import("gui.Gui")
import("player.Cursor")
import("player.Display")
import("player.PlayerSettings")
import("player.Recipes")
import("player.events.CharacterControllerActivated")
import("player.events.Picked")
import("player.events.Released")
import("player.events.CursorStackChanged")
import("player.events.ToolbarsToggled")

import("player.events.settings.ShowVehicleInventoriesContentSettingChanged")
import("player.events.settings.ShowLogisticNetworksContentSettingChanged")
import("player.inventory.EmptyViewInventory")
import("player.inventory.personal.character.CharacterViewInventory")
import("player.inventory.personal.god.GodViewInventory")
import("player.inventory.personal.editor.EditorViewInventory")
import("player.inventory.remote.planet.PlanetViewInventory")
import("player.inventory.remote.space_platform.SpacePlatformViewInventory")

---@class Player : Object
---@field private __instances table<number, Player>
---@field private _luaPlayer LuaPlayer
---@field private _settings PlayerSettings
---@field private _eventBus EventBus
---@field private _display Display
---@field private _cursor Cursor
---@field private _gui Gui
---@field private _viewInventory ViewInventory
---@field private _recipes Recipes
Player = Object:extendAs("player.Player")
Player.__instances = {}

---@public
function Player.loadAll()
    for _, luaPlayer in ipairs(game.connected_players) do
        Player.get(luaPlayer.index)
    end
end

---@public
---@param player_index number
function Player.reload(player_index)
    Player.invalidate(player_index)
    Player.get(player_index)
end

---@public
---@param player_index number
function Player.invalidate(player_index)
    Player.__instances[player_index] = nil
end

---@public
---@param player_index number
---@return Player
function Player.get(player_index)
    local current = Player.__instances[player_index]
    if not current or not current._luaPlayer.valid then
        Player.__instances[player_index] = Player.new(game.get_player(player_index))
        Player.__instances[player_index]:load()
    end
    return Player.__instances[player_index]
end

---@public
---@return Player[]
function Player.allLoaded()
    return Player.__instances
end

---@public
---@param luaPlayer LuaPlayer
function Player.new(luaPlayer)
    local this = Player:super(Object.new())
    this._luaPlayer = luaPlayer
    this._eventBus = EventBus.new()
    this._scheduler = Scheduler.new(this._eventBus)
    local resolution = luaPlayer.display_resolution
    this._display = Display.new(Resolution.new(resolution.width, resolution.height), luaPlayer.display_scale)
    this._cursor = Cursor.new(this._luaPlayer)
    this._settings = PlayerSettings.new(this._luaPlayer, this._eventBus)
    this._recipes = Recipes.new(this._luaPlayer)
    this._viewInventory = EmptyViewInventory.new(this, Content.new())

    this:resetViewInventory()
    this._eventBus:subscribeTo(ControllerChanged, this, function()
        this:resetViewInventory()
    end)
    this:eventBus():subscribeTo(SurfaceChanged, this, function()
        this:resetViewInventory()
    end)
    this:eventBus():subscribeTo(ShowVehicleInventoriesContentSettingChanged, this, function()
        this:resetViewInventory()
    end)
    this:eventBus():subscribeTo(ShowLogisticNetworksContentSettingChanged, this, function()
        this:resetViewInventory()
    end)

    this._gui = Gui.new(this)
    return this
end

---@private
function Player:load()
    self._gui:load()
end

---@public
function Player:createToolbar()
    self._gui:createToolbar()
end

---@public
function Player:toggleToolbars()
    if self:toolbarsAreOn() then
        self:turnOffToolbars()
    else
        self:turnOnToolbars()
    end
    self._eventBus:publish(ToolbarsToggled)
end

---@public
function Player:turnOnToolbars()
    self._luaPlayer.set_shortcut_toggled(Toolbars.controls.toggleToolbars, true)
end

---@private
function Player:turnOffToolbars()
    self._luaPlayer.set_shortcut_toggled(Toolbars.controls.toggleToolbars, false)
end

---@public
---@return boolean
function Player:toolbarsAreOn()
    return self._luaPlayer.is_shortcut_toggled(Toolbars.controls.toggleToolbars)
end

---@public
function Player:showToolbars()
    self._gui:show()
end

---@public
function Player:hideToolbars()
    self._gui:hide()
end

---@public
function Player:onCursorChange()
    self._cursor:refresh()
    if not self._cursor:currentThing():equals(self._cursor:previousThing()) then
        self._eventBus:publish(Released.new(self._cursor:previousThing()))
        self._eventBus:publish(Picked.new(self._cursor:currentThing()))
    end

    if self:inPersonalView() then
        if (self._cursor:previousThing():isInstanceOf(Item) and self._cursor:previousThingCount() > 0)
                or (self._cursor:currentThing():isInstanceOf(Item) and self._cursor:currentThingCount() > 0) then
            self._eventBus:publish(CursorStackChanged)
        end
    end
end

---@private
function Player:resetViewInventory()
    local oldViewInventory = self._viewInventory
    self._viewInventory = self:freshViewInventory()
    self._viewInventory:forceRefresh()
    oldViewInventory:delete()
end

---@private
---@return ViewInventory
function Player:freshViewInventory()
    local currentContent = self._viewInventory:content()

    if self:inCharacterView() and self._luaPlayer.character then
        return CharacterViewInventory.new(self, currentContent)
    elseif self:inEditorView() then
        return EditorViewInventory.new(self, currentContent)
    elseif self:inGodView() then
        return GodViewInventory.new(self, currentContent)
    elseif self:inRemoteView() then
        if self:isNotOnPlatform() then
            return PlanetViewInventory.new(self, currentContent)
        elseif self:isOnPlatform() then
            return SpacePlatformViewInventory.new(self, currentContent)
        else
            return EmptyViewInventory.new(self, currentContent)
        end
    else
        return EmptyViewInventory.new(self, currentContent)
    end
end

---@public
---@return boolean
function Player:inPersonalView()
    return self:inCharacterView() or self:inEditorView() or self:inGodView()
end

---@public
---@return boolean
function Player:inCharacterView()
    return self._luaPlayer.controller_type == defines.controllers.character
end

---@public
---@return boolean
function Player:inEditorView()
    return self._luaPlayer.controller_type == defines.controllers.editor
end

---@public
---@return boolean
function Player:inGodView()
    return self._luaPlayer.controller_type == defines.controllers.god
end

---@public
---@return boolean
function Player:inRemoteView()
    return self._luaPlayer.controller_type == defines.controllers.remote
end

---@public
---@param surface LuaSurface
---@param position MapPosition
function Player:openInRemoteView(surface, position)
    self._luaPlayer
        .set_controller({ type = defines.controllers.remote, surface = surface, position = position })
    self._luaPlayer.zoom = 1
end

---@public
---@return LuaPlanet|nil
function Player:planet()
    return self._luaPlayer.surface.planet
end

---@public
---@return LuaSurface
function Player:surface()
    return self._luaPlayer.surface
end

---@public
---@return boolean
function Player:isNotOnPlatform()
    return self._luaPlayer.surface.platform == nil
end

---@public
---@return boolean
function Player:isOnPlatform()
    return self._luaPlayer.surface.platform and self._luaPlayer.surface.platform.hub
end

---@public
---@return ViewInventory
function Player:viewInventory()
    return self._viewInventory
end

---@public
---@return Cursor
function Player:cursor()
    return self._cursor
end

---@public
---@return Gui
function Player:gui()
    return self._gui
end

---@public
---@return EventBus
function Player:eventBus()
    return self._eventBus
end

---@public
---@return Scheduler
function Player:scheduler()
    return self._scheduler
end

---@public
---@return Display
function Player:display()
    return self._display
end

---@public
---@return Recipes
function Player:recipes()
    return self._recipes
end

---@public
---@return PlayerSettings
function Player:settings()
    return self._settings
end

---@public
---@return LuaPlayer
function Player:luaPlayer()
    return self._luaPlayer
end
