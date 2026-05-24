import("factorio.events.inventory.PlayerMainInventoryChanged")
import("factorio.events.inventory.PlayerTrashInventoryChanged")
import("player.Player")

---@param event EventData
script.on_event(defines.events.on_player_cursor_stack_changed, function(event)
    Player.get(event.player_index):onCursorChange()
end)

---@param event EventData
script.on_event(defines.events.on_player_selected_area, function(event)
    if event.item == "spidertron-remote" then
        Player.get(event.player_index):onCursorChange()
    end
end)

---@param event EventData
script.on_event(defines.events.on_player_main_inventory_changed, function(event)
    Player.get(event.player_index):eventBus():publish(PlayerMainInventoryChanged)
end)

---@param event EventData
script.on_event(defines.events.on_player_trash_inventory_changed, function(event)
    Player.get(event.player_index):eventBus():publish(PlayerTrashInventoryChanged)
end)
