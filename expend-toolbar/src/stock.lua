local names = require("names")

local M = {}

local quality_cache = nil
local quality_rank_cache = nil

local function quality_order()
  if quality_cache then
    return quality_cache
  end
  local list = {}
  for name, quality in pairs(prototypes.quality) do
    list[#list + 1] = { name = name, level = quality.level or 0, order = quality.order or name }
  end
  table.sort(list, function(a, b)
    if a.level ~= b.level then
      return a.level < b.level
    end
    return a.order < b.order
  end)
  quality_cache = list
  quality_rank_cache = {}
  for index, row in ipairs(list) do
    quality_rank_cache[row.name] = index
  end
  return quality_cache
end

local function quality_rank()
  quality_order()
  return quality_rank_cache or {}
end

local function wanted_names(wanted)
  local list = {}
  for name in pairs(wanted or {}) do
    list[#list + 1] = name
  end
  return list
end

local function sane_quality(quality)
  if type(quality) == "table" then
    quality = quality.name
  end
  if not quality or quality == "" or quality == "quality-unknown" or not prototypes.quality[quality] then
    return "normal"
  end
  return quality
end

local function add_bucket(box, stack, wanted)
  if not stack or not stack.name or not stack.count then
    return
  end
  if wanted and not wanted[stack.name] then
    return
  end
  local grade = sane_quality(stack.quality)
  box[stack.name] = box[stack.name] or {}
  box[stack.name][grade] = (box[stack.name][grade] or 0) + stack.count
end

local function add_quality_counts(box, name, counts)
  if not counts then
    return
  end
  for grade, count in pairs(counts) do
    if count > 0 then
      add_bucket(box, { name = name, quality = grade, count = count })
    end
  end
end

local function pour_inventory(box, inventory, wanted)
  if inventory and inventory.valid then
    if wanted then
      for name in pairs(wanted) do
        if prototypes.item[name] then
          add_quality_counts(box, name, inventory.get_item_quality_counts(name))
        end
      end
      return
    end
    for _, row in pairs(inventory.get_contents()) do
      add_bucket(box, row, wanted)
    end
  end
end

local function pour_stack(box, stack, wanted)
  if stack and stack.valid_for_read then
    add_bucket(box, { name = stack.name, quality = stack.quality and stack.quality.name or "normal", count = stack.count }, wanted)
  end
end

local function pour_network_item(box, network, name, grades)
  for _, row in ipairs(grades) do
    local grade = row.name
    local count = network.get_item_count({ name = name, quality = grade })
    if count > 0 then
      add_bucket(box, { name = name, quality = grade, count = count })
    end
  end
end

local function pour_networks(box, player, skip_character_network, wanted)
  if not player.surface or not player.position or not player.force then
    return
  end
  local wanted_list = wanted and wanted_names(wanted) or nil
  local grades = quality_order()
  local directed_queries = wanted_list and (#wanted_list * math.max(#grades, 1)) or 0
  local own_network = skip_character_network and player.character and player.character.logistic_network or nil
  for _, network in ipairs(player.surface.find_logistic_networks_by_construction_area(player.position, player.force)) do
    if network ~= own_network then
      -- 少量物品走定向查询；大量物品保留一次全量读取，避免网络调用次数反而膨胀。
      if wanted_list and directed_queries <= 96 then
        for _, name in ipairs(wanted_list) do
          pour_network_item(box, network, name, grades)
        end
      else
        for _, row in pairs(network.get_contents()) do
          add_bucket(box, row, wanted)
        end
      end
    end
  end
end

local function pour_vehicle(box, player, wanted)
  if not settings.get_player_settings(player)[names.setting.vehicle_on].value then
    return
  end
  local vehicle = player.vehicle
  if not vehicle or not vehicle.valid then
    return
  end
  pour_inventory(box, vehicle.get_inventory(defines.inventory.car_trunk), wanted)
  pour_inventory(box, vehicle.get_inventory(defines.inventory.car_trash), wanted)
end

local function pour_platform(box, player, wanted)
  local platform = player.surface and player.surface.platform or nil
  local hub = platform and platform.hub or nil
  if not hub then
    return
  end
  pour_inventory(box, hub.get_inventory(defines.inventory.hub_main), wanted)
  pour_inventory(box, hub.get_inventory(defines.inventory.hub_trash), wanted)
end

local function read_player_bags(player, wanted)
  local main = {}
  local side = {}

  pour_inventory(main, player.get_main_inventory(), wanted)
  pour_stack(main, player.cursor_stack, wanted)
  if player.character then
    pour_inventory(main, player.character.get_inventory(defines.inventory.character_trash), wanted)
  end
  pour_vehicle(main, player, wanted)

  if settings.get_player_settings(player)[names.setting.network_on].value then
    -- 普通角色视图下，附近物流网络只作为提示列，不参与槽位主数字。
    pour_networks(side, player, true, wanted)
  end

  return main, side
end

local function read_remote_place(player, wanted)
  local main = {}
  if player.surface and player.surface.platform then
    pour_platform(main, player, wanted)
  elseif settings.get_player_settings(player)[names.setting.network_on].value then
    -- 远程星球视图没有玩家背包语义，物流网络就是当前页面的主库存。
    pour_networks(main, player, false, wanted)
  end
  return main, {}
end

function M.snapshot(player, wanted)
  if player.controller_type == defines.controllers.remote then
    return read_remote_place(player, wanted)
  end
  return read_player_bags(player, wanted)
end

function M.amount(pool, item, grade)
  local by_grade = pool[item]
  return by_grade and by_grade[grade or "normal"] or 0
end

function M.grade_list(main, side, item)
  local seen = {}
  local out = {}
  local function mark(pool)
    for grade in pairs(pool[item] or {}) do
      if prototypes.quality[grade] and not seen[grade] then
        seen[grade] = true
        out[#out + 1] = grade
      end
    end
  end
  mark(main)
  mark(side)
  local rank = quality_rank()
  table.sort(out, function(a, b)
    return (rank[a] or 0) < (rank[b] or 0)
  end)
  return out
end

local function next_grade(current, step)
  local list = quality_order()
  if #list == 0 then
    return "normal"
  end
  current = sane_quality(current)
  local found = 1
  for i, row in ipairs(list) do
    if row.name == current then
      found = i
      break
    end
  end
  local target = math.min(#list, math.max(1, found + step))
  return list[target].name
end

function M.raise_grade(current)
  return next_grade(current or "normal", 1)
end

function M.lower_grade(current)
  return next_grade(current or "normal", -1)
end

function M.item_known(name)
  return prototypes.item[name] or prototypes.fluid[name]
end

local function transfer_from(player, inventory, slot)
  if not inventory or not inventory.valid then
    return false
  end
  local stack = inventory.find_item_stack({ name = slot.name, quality = sane_quality(slot.grade) })
  if not stack then
    return false
  end
  return player.cursor_stack.transfer_stack(stack)
end

function M.lift_to_cursor(player, slot)
  if transfer_from(player, player.get_main_inventory(), slot) then
    return true
  end
  local vehicle = player.vehicle
  if vehicle and vehicle.valid and settings.get_player_settings(player)[names.setting.vehicle_on].value then
    if transfer_from(player, vehicle.get_inventory(defines.inventory.car_trunk), slot) then
      return true
    end
  end
  return false
end

return M
