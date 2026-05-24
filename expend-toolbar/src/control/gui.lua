import("factorio.events.events")

---@param event EventData
script.on_event(defines.events.on_player_created, function(event)
    Player.get(event.player_index):turnOnToolbars()
end)

script.on_event(defines.events.on_player_display_resolution_changed, function(event)
    Player.reload(event.player_index)
end)

script.on_event(defines.events.on_player_display_scale_changed, function(event)
    Player.reload(event.player_index)
end)

---@param event EventData
script.on_event(defines.events.on_gui_opened, function(event)
    if event.gui_type == defines.gui_type.entity and event.entity.name == "locomotive" then
        Player.get(event.player_index):hideToolbars()
    end
end)

---@param event EventData
script.on_event(defines.events.on_gui_closed, function(event)
    if event.gui_type == defines.gui_type.entity and event.entity.name == "locomotive" then
        Player.get(event.player_index):showToolbars()
    end
end)

---@param event EventData
script.on_event(defines.events.on_gui_click, function(event)
    local click = Click.new(event)
    if click:isForModElement() then
        Player.get(event.player_index):gui():handleClick(click)
    end
end)

---@param event EventData
script.on_event(defines.events.on_gui_elem_changed, function(event)
    local elementChanged = ElementChanged.new(event)
    if elementChanged:isForModElement() then
        Player.get(event.player_index):gui():handleElementChanged(elementChanged)
    end
end)

---@param event EventData
script.on_event(defines.events.on_gui_location_changed, function(event)
    local elementLocationChanged = ElementLocationChanged.new(event)
    if elementLocationChanged:isForModElement() then
        Player.get(event.player_index):gui():handleElementLocationChanged(elementLocationChanged)
    end
end)

---@param event EventData
script.on_event(defines.events.on_gui_hover, function(event)
    local hovered = Hovered.new(event)
    if hovered:isForModElement() then
        Player.get(event.player_index):gui():handleHover(hovered)
    end
end)

---@param event EventData
script.on_event(defines.events.on_gui_leave, function(event)
    local left = Left.new(event)
    if left:isForModElement() then
        Player.get(event.player_index):gui():handleLeave(left)
    end
end)
