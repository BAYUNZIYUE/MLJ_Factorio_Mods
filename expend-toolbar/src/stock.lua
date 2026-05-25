local names = require("names")

local M = {}

local function add_bucket(box, stack)
  if not stack or not stack.name or not stack.count then
    return
  end
  local grade = stack.quality
  if type(grade) == "table" then
    grade = grade.name
  end
  grade = grade or "normal"
  box[stack.name] = box[stack.name] or {}
  box[stack.name][grade] = (box[stack.name][grade] or 0) + stack.count
end

local function pour_inventory(box, inventory)
  if inventory and inventory.valid then
    for _, row in pairs(inventory.get_contents()) do
      add_bucket(box, row)
    end
  end
end

local function pour_stack(box, stack)
  if stack and stack.valid_for_read then
    add_bucket(box, { name = stack.name, quality = stack.quality and stack.quality.name or "normal", count = stack.count })
  end
end

local function pour_networks(box, player, skip_character_network)
  if not player.surface or not player.position or not player.force then
    return
  end
  local own_network = skip_character_network and player.character and player.character.logistic_network or nil
  for _, network in ipairs(player.surface.find_logistic_networks_by_construction_area(player.position, player.force)) do
    if network ~= own_network then
      for _, row in pairs(network.get_contents()) do
        add_bucket(box, row)
      end
    end
  end
end

local function pour_vehicle(box, player)
  if not settings.get_player_settings(player)[names.setting.vehicle_on].value then
    return
  end
  local vehicle = player.vehicle
  if not vehicle or not vehicle.valid then
    return
  end
  pour_inventory(box, vehicle.get_inventory(defines.inventory.car_trunk))
  pour_inventory(box, vehicle.get_inventory(defines.inventory.car_trash))
end

local function pour_platform(box, player)
  local platform = player.surface and player.surface.platform or nil
  local hub = platform and platform.hub or nil
  if not hub then
    return
  end
  pour_inventory(box, hub.get_inventory(defines.inventory.hub_main))
  pour_inventory(box, hub.get_inventory(defines.inventory.hub_trash))
end

local function read_player_bags(player)
  local main = {}
  local side = {}

  pour_inventory(main, player.get_main_inventory())
  pour_stack(main, player.cursor_stack)
  if player.character then
    pour_inventory(main, player.character.get_inventory(defines.inventory.character_trash))
  end
  pour_vehicle(main, player)

  if settings.get_player_settings(player)[names.setting.network_on].value then
    -- 普通角色视图下，附近物流网络只作为提示列，不参与槽位主数字。
    pour_networks(side, player, true)
  end

  return main, side
end

local function read_remote_place(player)
  local main = {}
  if player.surface and player.surface.platform then
    pour_platform(main, player)
  elseif settings.get_player_settings(player)[names.setting.network_on].value then
    -- 远程星球视图没有玩家背包语义，物流网络就是当前页面的主库存。
    pour_networks(main, player, false)
  end
  return main, {}
end

function M.snapshot(player)
  if player.controller_type == defines.controllers.remote then
    return read_remote_place(player)
  end
  return read_player_bags(player)
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
  table.sort(out, function(a, b)
    local qa = prototypes.quality[a]
    local qb = prototypes.quality[b]
    local la = qa and qa.level or 0
    local lb = qb and qb.level or 0
    if la ~= lb then
      return la < lb
    end
    return a < b
  end)
  return out
end

local function next_grade(current, step)
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
  if #list == 0 then
    return "normal"
  end
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
  local stack = inventory.find_item_stack({ name = slot.name, quality = slot.grade or "normal" })
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
