import("player.Player")
import("factorio.events.controls.Clear")
import("factorio.events.controls.DecreaseQuality")
import("factorio.events.controls.IncreaseQuality")
import("factorio.events.controls.OpenFactoriopedia")
import("factorio.events.controls.Pick")
import("factorio.events.controls.SearchFactory")
import("factorio.events.controls.ToggleToolbarHeader")

---@param event EventData
script.on_event(Toolbars.controls.createToolbar, function(event)
    Player.get(event.player_index):createToolbar()
end)

---@param event EventData
script.on_event(Toolbars.controls.toggleToolbars, function(event)
    Player.get(event.player_index):toggleToolbars()
end)

---@param event EventData
script.on_event(Toolbars.controls.toggleToolbarHeader, function(event)
    Player.get(event.player_index):eventBus():publish(ToggleToolbarHeader)
end)

---@param event EventData
script.on_event(Toolbars.controls.pipette, function(event)
    Player.get(event.player_index):eventBus():publish(Pick)
end)

---@param event EventData
script.on_event(Toolbars.controls.toggleFilter, function(event)
    Player.get(event.player_index):eventBus():publish(Clear)
end)

---@param event EventData
script.on_event(Toolbars.controls.openFactoriopedia, function(event)
    Player.get(event.player_index):eventBus():publish(OpenFactoriopedia)
end)

---@param event EventData
script.on_event(Toolbars.controls.increaseQuality, function(event)
    Player.get(event.player_index):eventBus():publish(IncreaseQuality)
end)

---@param event EventData
script.on_event(Toolbars.controls.decreaseQuality, function(event)
    Player.get(event.player_index):eventBus():publish(DecreaseQuality)
end)

---@param event EventData
script.on_event(Toolbars.controls.craftOne, function(event)
    Player.get(event.player_index):eventBus():publish(Craft:one())
end)

---@param event EventData
script.on_event(Toolbars.controls.craftFive, function(event)
    Player.get(event.player_index):eventBus():publish(Craft:five())
end)

---@param event EventData
script.on_event(Toolbars.controls.craftStack, function(event)
    Player.get(event.player_index):eventBus():publish(Craft:stack())
end)

---@param event EventData
script.on_event(Toolbars.controls.craftStackHalf, function(event)
    Player.get(event.player_index):eventBus():publish(Craft:stackHalf())
end)

---@param event EventData
script.on_event(Toolbars.controls.craftAll, function(event)
    Player.get(event.player_index):eventBus():publish(Craft:all())
end)

---@param event EventData
script.on_event(Toolbars.controls.craftAllHalf, function(event)
    Player.get(event.player_index):eventBus():publish(Craft:allHalf())
end)

if script.active_mods["FactorySearch"] then
    ---@param event EventData
    script.on_event("open-search-prototype", function(event)
        Player.get(event.player_index):eventBus():publish(SearchFactory)
    end)
end
