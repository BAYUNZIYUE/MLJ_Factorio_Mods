import("player.Player")

---@param event EventData
script.on_event(defines.events.on_lua_shortcut, function(event)
    if event.prototype_name == Toolbars.name .. "_create-toolbar" then
        Player.get(event.player_index):createToolbar()
    elseif event.prototype_name == Toolbars.name .. "_toggle-toolbars" then
        Player.get(event.player_index):toggleToolbars()
    end
end)
