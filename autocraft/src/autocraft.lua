local constants = require("constants")

local autocraft = {}

local function get_autocraft_logistics_section_name(player)
  return constants.AUTOCRAFT_LOGISTICS_SECTION_PREFIX .. "-" .. player.name
end

local function is_named_autocraft_section(section)
  return section.is_manual and (
    section.group == constants.AUTOCRAFT_LOGISTICS_SECTION_PREFIX
    or string.sub(section.group, 1, #constants.AUTOCRAFT_LOGISTICS_SECTION_PREFIX + 1)
      == constants.AUTOCRAFT_LOGISTICS_SECTION_PREFIX .. "-"
  )
end

local function is_players_autocraft_section(player, section)
  return section.is_manual and section.group == get_autocraft_logistics_section_name(player)
end

local function find_autocraft_logistics_section(player)
  local logistic_point = player.get_requester_point()
  if not logistic_point then
    return nil
  end

  for _, section in pairs(logistic_point.sections) do
    if is_players_autocraft_section(player, section) then
      return section
    end
  end

  return nil
end

function autocraft.add_autocraft_logistics_section(player)
  local logistic_point = player.get_requester_point()
  if not logistic_point then
    return nil
  end

  local existing_section = find_autocraft_logistics_section(player)
  if existing_section then
    return existing_section
  end

  local section = logistic_point.add_section(get_autocraft_logistics_section_name(player))
  if section then
    section.active = false
  end

  return section
end

function autocraft.pre_compute_recipes()
  local cache = {}

  for _, recipe in pairs(prototypes.get_recipe_filtered({ { filter = "has-product-item" } })) do
    for _, product in pairs(recipe.products) do
      local recipes = cache[product.name]
      if not recipes then
        recipes = {}
        cache[product.name] = recipes
      end

      recipes[recipe.name] = true
    end
  end

  return cache
end

local function should_include_existing_sections(player)
  return player.mod_settings[constants.AUTOCRAFT_EXISTING_SECTIONS_ENABLED].value
end

local function should_include_section(player, section)
  if not section.active then
    return false
  end

  if is_players_autocraft_section(player, section) then
    return true
  end

  return should_include_existing_sections(player) and not is_named_autocraft_section(section)
end

local function get_requested_items(player)
  local requested_items = {}
  local logistic_point = player.get_requester_point()
  if not logistic_point then
    return requested_items
  end

  -- 先筛出本次应参与自动手搓的物流分组，再把同类物品的最小保有量汇总成一个总需求。
  for _, section in pairs(logistic_point.sections) do
    if should_include_section(player, section) then
      for _, filter in pairs(section.filters) do
        if filter.min and filter.min > 0 then
          local item_name = nil
          if type(filter.value) == "string" then
            item_name = filter.value
          elseif filter.value and filter.value.type == "item" then
            item_name = filter.value.name
          end

          if item_name then
            requested_items[item_name] = (requested_items[item_name] or 0) + filter.min
          end
        end
      end
    end
  end

  return requested_items
end

local function recipe_for_item(player, item_name)
  local recipes = storage.recipes and storage.recipes[item_name]
  if not recipes then
    return nil
  end

  for recipe_name in pairs(recipes) do
    local recipe = player.force.recipes[recipe_name]
    local can_craft = recipe and not recipe.hidden and recipe.enabled
      and player.get_craftable_count(recipe_name) > 0

    if can_craft then
      return recipe_name
    end
  end

  return nil
end

local function get_crafting_queue_item_count(player, item_name)
  local crafting_queue = player.crafting_queue
  if not crafting_queue then
    return 0
  end

  local queued_count = 0
  for _, queue_item in pairs(crafting_queue) do
    if not queue_item.prerequisite then
      local recipe_name = type(queue_item.recipe) == "string" and queue_item.recipe or queue_item.recipe.name
      local recipe = player.force.recipes[recipe_name]

      if recipe then
        for _, product in pairs(recipe.products) do
          if product.type == "item" and product.name == item_name then
            queued_count = queued_count + queue_item.count * (product.amount or 1)
            break
          end
        end
      end
    end
  end

  return queued_count
end

local function get_item_requests(player, crafting_complete, completed_item_name)
  local item_requests = {}
  local requested_items = get_requested_items(player)
  local logistic_point = player.get_requester_point()
  local logistic_network = logistic_point and logistic_point.logistic_network or nil

  -- 实际手搓缺口要同时扣掉玩家已持有、当前物流网络已有，以及已经排进手搓队列的成品数量。
  for item_name, min in pairs(requested_items) do
    local recently_completed_count = 0
    if not crafting_complete and completed_item_name == item_name then
      recently_completed_count = 1
    end

    local inventory_count = player.get_item_count(item_name) + recently_completed_count
    local logistic_network_count = logistic_network and logistic_network.get_item_count(item_name) or 0
    local queued_count = get_crafting_queue_item_count(player, item_name)
    local available = inventory_count + logistic_network_count + queued_count
    local missing = min - available

    if missing > 0 then
      item_requests[#item_requests + 1] = {
        name = item_name,
        min = min,
        available = available,
        missing = missing,
        ratio = available / min,
      }
    end
  end

  return item_requests
end

local function item_id_to_name(item)
  if type(item) == "string" then
    return item
  end

  return item.name
end

local function pick_recipe(player, crafting_complete, completed_item_name)
  local item_requests = get_item_requests(player, crafting_complete, completed_item_name)
  if #item_requests == 0 then
    return nil
  end

  table.sort(item_requests, function(a, b)
    if a.ratio ~= b.ratio then
      return a.ratio < b.ratio
    end

    if a.missing ~= b.missing then
      return a.missing > b.missing
    end

    return a.name < b.name
  end)

  local hand_item_name = nil
  if player.cursor_stack and player.cursor_stack.valid_for_read then
    hand_item_name = player.cursor_stack.name
  elseif player.cursor_ghost then
    hand_item_name = item_id_to_name(player.cursor_ghost.name)
  end

  if hand_item_name then
    for _, item_request in pairs(item_requests) do
      if item_request.name == hand_item_name then
        local recipe_name = recipe_for_item(player, hand_item_name)
        if recipe_name then
          return hand_item_name, recipe_name
        end
        break
      end
    end
  end

  for _, item_request in pairs(item_requests) do
    local recipe_name = recipe_for_item(player, item_request.name)
    if recipe_name then
      return item_request.name, recipe_name
    end
  end

  return nil
end

function autocraft.do_crafting(player, crafting_complete, completed_item_name)
  if crafting_complete == nil then
    crafting_complete = true
  end

  local is_eligible = player.connected
    and player.controller_type == defines.controllers.character
    and player.ticks_to_respawn == nil

  if not is_eligible then
    return
  end

  local allowed_queue_length = crafting_complete and 0 or 1
  if player.crafting_queue and #player.crafting_queue > allowed_queue_length then
    return
  end

  storage.data = storage.data or {}
  local data = storage.data[player.index] or {}

  local item_name, recipe_name = pick_recipe(player, crafting_complete, completed_item_name)
  if recipe_name then
    data.active_item_name = item_name
    data.active_recipe_name = recipe_name
    storage.data[player.index] = data
    player.begin_crafting({ count = 1, recipe = recipe_name, silent = true })
  end
end

return autocraft
