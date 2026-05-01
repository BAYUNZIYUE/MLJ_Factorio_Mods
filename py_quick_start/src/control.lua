require("utils")

function giveStartItem(player)
    -- 过场动画播放过程中，由于player.character为nil，无法添加物品
    -- Can't add items due to player.character is nil during the transient animation.
    if (player.controller_type ~= defines.controllers.character) then
        print("player" .. player.name .. " is not character")
        return
    end

    -- 获取storage["playerWithEquipment"]
    if (storage["playerWithEquipment"] == nil) then
        print("storage[\"playerWithEquipment\"] == nil, init to {}")
        storage["playerWithEquipment"] = {}
    end
    local tbl = storage["playerWithEquipment"]
    print("storage[\"playerWithEquipment\"]:")
    print(tbl)

    -- 避免重复给予装备
    if (tbl[player.name] == true) then
        print("Items already given to " .. player.name .. ", shouldn't give again")
        return
    end

    -- 获取玩家背包，添加物品。此处不考虑品质，全部使用最低品质
    -- not consider quality
    playerInventory = player.character.get_inventory(defines.inventory.character_main)
    -- 由于本身py会给10个热能采矿机，100铁板，50铜板，所以此处不再给予物品
    -- 铁箱*1组
    --playerInventory.insert({ name = "iron-chest", count = prototypes.item["iron-chest"].stack_size * 1 })
    -- 传送带*5组
    --playerInventory.insert({ name = "transport-belt", count = prototypes.item["transport-belt"].stack_size * 5 })
    -- 地下传送带*2组
    --playerInventory.insert({ name = "underground-belt", count = prototypes.item["underground-belt"].stack_size * 2 })
    -- 工业机械臂*2组
    --playerInventory.insert({ name = "burner-inseter", count = prototypes.item["iron-chest"].stack_size * 2 })
    -- 热能采矿机*1组
    --playerInventory.insert({ name = "burner-mining-drill", count = prototypes.item["burner-mining-drill"].stack_size * 1 })
    -- 石炉*1组
    --playerInventory.insert({ name = "stone-furnace", count = prototypes.item["stone-furnace"].stack_size * 1 })
    -- 原煤*5组
    --playerInventory.insert({ name = "raw-coal", count = prototypes.item["raw-coal"].stack_size * 5 })
    -- py高科技建设机器人*100个
    playerInventory.insert({ name = "py-construction-robot-mk04", count = 100 })

    -- 能量装甲MK2*1，直接装备到装甲栏
    player.insert({ name = "power-armor-mk2", count = 1 })
    -- 装甲内插入以下模块
    local armor = player.get_inventory(5)[1].grid
    -- 夜视模块*1
    armor.put({ name = "night-vision-equipment" })
    -- 锚定模块*1
    armor.put({ name = "belt-immunity-equipment" })
    -- 太阳能模块*55（太阳能不需要消耗燃料）
    for _ = 1, 55 do
        armor.put({ name = "solar-panel-equipment" })
    end
    -- 机械外骨骼*2（PY的移速加成非常高，有200%，两个已经非常快了）
    for _ = 1, 2 do
        armor.put({ name = "exoskeleton-equipment" })
    end
    -- 机器人指令模块MK2*4
    for _ = 1, 4 do
        armor.put({ name = "personal-roboport-mk2-equipment" })
    end
    -- 量子电池*2（注意，背包中是乏有机量子电池used-quantum-battery，装甲内是量子电池quantum-battery）
    for _ = 1, 2 do
        armor.put({ name = "quantum-battery" })
    end

    tbl[player.name] = true

    print("Items already given to " .. player.name)
    print("storage[\"playerWithEquipment\"]:")
    print(tbl)
end

-- mod列表更新等情况可能遇到
script.on_init(function(_)
    print("on_init")
    for _, player in pairs(game.players) do
        if player and player.connected then
            giveStartItem(player)
        end
    end
end)
-- 多人游戏加入时（虽然单人也会触发，但是处于过场动画中的角色无法给予物品）
script.on_event(defines.events.on_player_joined_game, function(event)
    print("defines.events.on_player_joined_game")
    giveStartItem(game.get_player(event.player_index))
end)
-- 没触发，感觉API有问题
script.on_event(defines.events.on_cutscene_finished, function(event)
    print("defines.events.on_cutscene_finished")
    giveStartItem(game.get_player(event.player_index))
end)
-- 单人游戏过场动画结束时（无论是自动播放完还是手动跳过，都会进这个）
script.on_event(defines.events.on_cutscene_cancelled, function(event)
    print("defines.events.on_cutscene_cancelled")
    giveStartItem(game.get_player(event.player_index))
end)
