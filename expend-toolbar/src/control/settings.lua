import("factorio.events.settings.PlayerSettingChanged")

---@param event EventData
script.on_event(defines.events.on_runtime_mod_setting_changed, function(event)
    if event.player_index then
        Player.get(event.player_index):eventBus():publish(PlayerSettingChanged.new(event.setting))
    end
end)
