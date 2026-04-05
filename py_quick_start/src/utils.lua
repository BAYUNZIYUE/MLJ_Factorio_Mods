--[[
常用调试指令（参考https://wiki.factorio.com/Console）：
/c function p(str) return game.print(str) end
/c game.player.force.research_all_technologies()
/c game.player.cheat_mode=true
/c game.player.insert{name="infinity-chest", count=10}
]]

local debug = false

function print(x)
    if not debug then
        return
    end
    if type(x) == "table" then
        printTable(x, "")
    else
        -- 似乎重复的字符串不会再次显示
        game.print(tostring(x))
    end
end

-- 假定key不会出现特殊类型
function printTable(table, space)
    print(space .. "{")
    for k, v in pairs(table) do
        if type(v) ~= "table" then
            print(space .. tostring(k) .. " = " .. tostring(v))
        else
            print(space .. tostring(k) .. " = ")
            printTable(v, space .. "  ")
        end
    end
    print(space .. "}")
end

--function str2tbl(str)
--    local tbl = {}
--    if str ~= nil then
--        for word in string.gmatch(str, "[^,]+") do
--            table.insert(tbl, word)
--        end
--    end
--    return tbl
--end

--如何查看物品的name（例如iron-chest）：
--    F4->DEBUG->勾选show-debug-info-in-tooltips->F5切换至debug模式->鼠标移动到物品上
--如何查看所有物品：
--    使用地图编辑，将存档转为场景
--    或者，使用控制台解锁全部科技，指令如下
--    /command for n,t in pairs(game.player.force.technologies) do t.researched=t.enabled end

--how to find item name (such as iron-chest):
--    F4->DEBUG->enable show-debug-info-in-tooltips->F5 to debug mode->move mouse on item
--how to show all items (select one way):
--    use the map editor to turn the save into a scenario
--    or, use the console to unlock all technologies, the command is as follows
--    /command for n,t in pairs(game.player.force.technologies) do t.researched=t.enabled end
