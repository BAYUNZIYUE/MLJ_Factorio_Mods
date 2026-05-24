import("factorio.events.events")
import("player.Player")

---@param event EventData
script.on_nth_tick(1, function(event)
    if not Toolbars.loaded then
        Player.loadAll()
        Toolbars.loaded = true
    end

    for _, player in ipairs(Player.allLoaded()) do
        player:viewInventory():refresh()
        player:eventBus():publish(Tick.new(event.tick))
    end
end)

---@param event EventData
script.on_event(defines.events.on_player_controller_changed, function(event)
    Player.get(event.player_index):eventBus():publish(ControllerChanged)
end)

---@param event EventData
script.on_event(defines.events.on_player_changed_surface, function(event)
    Player.get(event.player_index):eventBus():publish(SurfaceChanged)
end)
