local constants = require("constants")

local autocraft = {}

local function starts_with(value, prefix)
  return string.sub(value, 1, #prefix) == prefix
end

local function get_player_data(player)
  storage.data = storage.data or {}
  storage.data[player.index] = storage.data[player.index] or {
    enabled = constants.AUTOCRAFT_DEFAULT_ENABLED,
  }
  return storage.data[player.index]
end

local function get_configured_prefix(player)
  return player.mod_settings[constants.AUTOCRAFT_PREFIX_SETTING].value or ""
end

local function get_match_mode(player)
  return player.mod_settings[constants.AUTOCRAFT_MATCH_MODE_SETTING].value
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

function autocraft.is_enabled(player)
  return get_player_data(player).enabled
end

function autocraft.set_enabled(player, enabled)
  get_player_data(player).enabled = enabled and true or false
end

local function section_has_autocraft_ability(player, section)
  local section_name = section.group or ""
  local player_name = player.name
  local configured_prefix = get_configured_prefix(player)
  local match_mode = get_match_mode(player)

  if match_mode == constants.AUTOCRAFT_MATCH_MODE_FULL then
    return true
  end

  if match_mode == constants.AUTOCRAFT_MATCH_MODE_PREFIX then
    return configured_prefix ~= "" and starts_with(section_name, configured_prefix)
  end

  if match_mode == constants.AUTOCRAFT_MATCH_MODE_PLAYER_NAME then
    return starts_with(section_name, player_name)
  end

  if match_mode == constants.AUTOCRAFT_MATCH_MODE_PREFIX_AND_PLAYER_NAME then
    return configured_prefix ~= "" and starts_with(section_name, configured_prefix .. player_name)
  end

  return false
end

local function should_include_section(player, section)
  if not autocraft.is_enabled(player) then
    return false
  end

  return section.active and section_has_autocraft_ability(player, section)
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

local function get_module_queue_index(player)
  local data = storage.data and storage.data[player.index] or nil
  if not data or not data.active_recipe_name or not player.crafting_queue then
    return nil
  end

  for index, queue_item in pairs(player.crafting_queue) do
    local recipe_name = type(queue_item.recipe) == "string" and queue_item.recipe or queue_item.recipe.name
    if recipe_name == data.active_recipe_name and not queue_item.prerequisite then
      return index, queue_item
    end
  end

  return nil
end

function autocraft.cancel_active_crafting(player)
  local data = storage.data and storage.data[player.index] or nil
  if not data then
    return
  end

  local queue_index, queue_item = get_module_queue_index(player)
  if queue_index and queue_item then
    player.cancel_crafting({ index = queue_index, count = queue_item.count })
  end

  data.active_item_name = nil
  data.active_recipe_name = nil
end

function autocraft.clear_active_state(player)
  local data = storage.data and storage.data[player.index] or nil
  if not data then
    return
  end

  data.active_item_name = nil
  data.active_recipe_name = nil
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
  local logistic_network = nil
  if logistic_point and logistic_point.valid then
    local candidate_network = logistic_point.logistic_network
    if candidate_network and candidate_network.valid then
      logistic_network = candidate_network
    end
  end

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

  if not autocraft.is_enabled(player) then
    return
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
