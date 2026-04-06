function resize_inventory(player)
    if player and player.character then
        local inventory = player.get_main_inventory()
        if inventory == nil then
            return
        end
        local empty_slots = inventory.count_empty_stacks()
        local setting_empty_slots = player.mod_settings['dynamic-inventory-empty-slots'].value
        if empty_slots == setting_empty_slots then
            storage.need_resize[player.name] = false
            return
        end
        local setting_min_slots = player.mod_settings['dynamic-inventory-min-slots'].value
        local exists_item_slots_bonus = player.character_inventory_slots_bonus - empty_slots
        if player.opened_gui_type == defines.gui_type.none then
            -- 未打开任何界面情况下，直接设定为48
            player.character_inventory_slots_bonus = math.max(setting_min_slots, exists_item_slots_bonus + setting_empty_slots)
            storage.need_resize[player.name] = false
        elseif empty_slots < setting_empty_slots / 2 then
            -- 打开任何界面且剩余格子不足一半时，扩充到48*2
            player.character_inventory_slots_bonus = math.max(setting_min_slots, exists_item_slots_bonus + setting_empty_slots * 2)
            storage.need_resize[player.name] = true
        else
            -- 其他情况暂时不修改背包大小
            storage.need_resize[player.name] = true
        end
    end
end

script.on_event(defines.events.on_player_main_inventory_changed, function(event)
    storage.need_resize = storage.need_resize or {}
    resize_inventory(game.players[event.player_index])
end)

script.on_nth_tick(60, function(_)
    storage.need_resize = storage.need_resize or {}
    for playerName, need_resize in pairs(storage.need_resize) do
        if need_resize then
            resize_inventory(game.players[playerName])
        end
    end
end)