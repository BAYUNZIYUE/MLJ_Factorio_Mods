local constants = require("constants")

local autocraft = {}

local function starts_with(value, prefix)
  return string.sub(value, 1, #prefix) == prefix
end

local function get_player_data(player)
  storage.data = storage.data or {}
  storage.missing_section_players = storage.missing_section_players or {}
  storage.data[player.index] = storage.data[player.index] or {
    enabled = constants.AUTOCRAFT_DEFAULT_ENABLED,
    missing_section_name = nil,
  }
  return storage.data[player.index]
end

local function get_configured_prefix(player)
  return player.mod_settings[constants.AUTOCRAFT_PREFIX_SETTING].value or ""
end

local function get_match_mode(player)
  return player.mod_settings[constants.AUTOCRAFT_MATCH_MODE_SETTING].value
end

local function get_display_prefix(player)
  local configured_prefix = get_configured_prefix(player)
  if configured_prefix == "" then
    return constants.AUTOCRAFT_DEFAULT_PREFIX_RICH_TEXT
  end
  return configured_prefix
end

local function get_missing_materials_section_name(player)
  local display_prefix = get_display_prefix(player)
  if player.locale and starts_with(player.locale, "zh") then
    return "[自动]自动手搓" .. display_prefix .. player.name .. "-缺失材料"
  end
  return "[Auto]Autocraft" .. display_prefix .. player.name .. "-Missing materials"
end

local function find_missing_materials_section(player)
  local logistic_point = player.get_requester_point()
  if not logistic_point or not logistic_point.valid then
    return nil
  end

  local data = get_player_data(player)
  local current_name = get_missing_materials_section_name(player)
  local stored_name = data.missing_section_name

  for _, section in pairs(logistic_point.sections) do
    if section.is_manual and (section.group == current_name or (stored_name and section.group == stored_name)) then
      return section
    end
  end

  return nil
end

local function ensure_missing_materials_section(player)
  local logistic_point = player.get_requester_point()
  if not logistic_point then
    return nil
  end

  local data = get_player_data(player)
  local section_name = get_missing_materials_section_name(player)
  local section = find_missing_materials_section(player)

  if section then
    if section.group ~= section_name then
      section.group = section_name
    end
    section.active = true
    data.missing_section_name = section_name
    storage.missing_section_players[player.index] = true
    return section
  end

  section = logistic_point.add_section(section_name)
  if section then
    section.active = true
    data.missing_section_name = section_name
    storage.missing_section_players[player.index] = true
  end

  return section
end

local function remove_missing_materials_section(player)
  local logistic_point = player.get_requester_point()
  local data = get_player_data(player)
  if not logistic_point then
    data.missing_section_name = nil
    return
  end

  local section = find_missing_materials_section(player)
  if section and section.valid then
    logistic_point.remove_section(section.index)
  end

  data.missing_section_name = nil
  storage.missing_section_players[player.index] = nil
end

local function write_missing_materials_section(player, requests)
  local request_list = {}
  for item_name, count in pairs(requests) do
    if count > 0 then
      request_list[#request_list + 1] = {
        name = item_name,
        count = math.ceil(count),
      }
    end
  end

  if #request_list == 0 then
    remove_missing_materials_section(player)
    return
  end

  table.sort(request_list, function(a, b)
    return a.name < b.name
  end)

  local section = ensure_missing_materials_section(player)
  if not section or not section.valid then
    return
  end

  section.active = true
  for slot_index, request in ipairs(request_list) do
    section.set_slot(slot_index, {
      value = { type = "item", name = request.name },
      min = request.count,
    })
  end

  for slot_index = #request_list + 1, #section.filters do
    section.clear_slot(slot_index)
  end
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

local function should_include_section(player, section, missing_section_index)
  if not autocraft.is_enabled(player) then
    return false
  end

  if missing_section_index and section.index == missing_section_index then
    return false
  end

  return section.active and section_has_autocraft_ability(player, section)
end

local function get_requested_items(player)
  local requested_items = {}
  local logistic_point = player.get_requester_point()
  if not logistic_point or not logistic_point.valid then
    return requested_items
  end

  local missing_section = find_missing_materials_section(player)
  local missing_section_index = missing_section and missing_section.valid and missing_section.index or nil

  -- 先筛出本次应参与自动手搓的物流分组，再把同类物品的最小保有量汇总成一个总需求。
  for _, section in pairs(logistic_point.sections) do
    if should_include_section(player, section, missing_section_index) then
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
    remove_missing_materials_section(player)
    return
  end

  local queue_index, queue_item = get_module_queue_index(player)
  if queue_index and queue_item then
    player.cancel_crafting({ index = queue_index, count = queue_item.count })
  end

  data.active_item_name = nil
  data.active_recipe_name = nil
  remove_missing_materials_section(player)
end

function autocraft.clear_active_state(player)
  local data = storage.data and storage.data[player.index] or nil
  if not data then
    remove_missing_materials_section(player)
    return
  end

  data.active_item_name = nil
  data.active_recipe_name = nil
  remove_missing_materials_section(player)
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

local function recipe_for_item_any(player, item_name)
  local recipes = storage.recipes and storage.recipes[item_name]
  if not recipes then
    return nil
  end

  for recipe_name in pairs(recipes) do
    local recipe = player.force.recipes[recipe_name]
    if recipe and not recipe.hidden and recipe.enabled then
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

local item_id_to_name

local function get_hand_item_name(player)
  if player.cursor_stack and player.cursor_stack.valid_for_read then
    return player.cursor_stack.name
  end

  if player.cursor_ghost then
    return item_id_to_name(player.cursor_ghost.name)
  end

  return nil
end

item_id_to_name = function(item)
  if type(item) == "string" then
    return item
  end

  return item.name
end

local function get_recipe_output_amount(recipe, item_name)
  for _, product in pairs(recipe.products) do
    if product.type == "item" and product.name == item_name then
      if product.amount then
        return product.amount
      end
      if product.amount_min then
        return product.amount_min
      end
    end
  end

  return 1
end

local function accumulate_missing_materials(player, item_name, needed_count, requests, visiting, logistic_network)
  if needed_count <= 0 then
    return
  end

  requests[item_name] = (requests[item_name] or 0) + needed_count

  local logistic_network_count = logistic_network and logistic_network.get_item_count(item_name) or 0
  local unresolved_count = needed_count - logistic_network_count
  if unresolved_count <= 0 then
    return
  end

  if visiting[item_name] then
    return
  end

  local recipe_name = recipe_for_item_any(player, item_name)
  if not recipe_name then
    return
  end

  local recipe = player.force.recipes[recipe_name]
  if not recipe then
    return
  end

  visiting[item_name] = true
  local crafts_needed = math.ceil(unresolved_count / get_recipe_output_amount(recipe, item_name))

  for _, ingredient in pairs(recipe.ingredients) do
    if ingredient.type == "item" then
      local inventory_count = player.get_item_count(ingredient.name)
      local missing_count = ingredient.amount * crafts_needed - inventory_count
      if missing_count > 0 then
        accumulate_missing_materials(player, ingredient.name, missing_count, requests, visiting, logistic_network)
      end
    end
  end

  visiting[item_name] = nil
end

local function update_missing_materials_section(player, target_item_name, target_recipe_name)
  if not autocraft.is_enabled(player) then
    remove_missing_materials_section(player)
    return
  end

  if not target_item_name or not target_recipe_name then
    remove_missing_materials_section(player)
    return
  end

  local recipe = player.force.recipes[target_recipe_name]
  if not recipe then
    remove_missing_materials_section(player)
    return
  end

  local logistic_point = player.get_requester_point()
  local logistic_network = nil
  if logistic_point and logistic_point.valid then
    local candidate_network = logistic_point.logistic_network
    if candidate_network and candidate_network.valid then
      logistic_network = candidate_network
    end
  end

  local missing_requests = {}
  local has_missing_materials = false

  for _, ingredient in pairs(recipe.ingredients) do
    if ingredient.type == "item" then
      local inventory_count = player.get_item_count(ingredient.name)
      local missing_count = ingredient.amount - inventory_count
      if missing_count > 0 then
        has_missing_materials = true
        accumulate_missing_materials(player, ingredient.name, missing_count, missing_requests, {}, logistic_network)
      end
    end
  end

  if not has_missing_materials then
    remove_missing_materials_section(player)
    return
  end

  write_missing_materials_section(player, missing_requests)
end

local function sort_item_requests(item_requests)
  table.sort(item_requests, function(a, b)
    if a.ratio ~= b.ratio then
      return a.ratio < b.ratio
    end

    if a.missing ~= b.missing then
      return a.missing > b.missing
    end

    return a.name < b.name
  end)
end

local function pick_recipe_from_requests(player, item_requests, hand_item_name, recipe_picker)
  if hand_item_name then
    for _, item_request in pairs(item_requests) do
      if item_request.name == hand_item_name then
        local recipe_name = recipe_picker(player, hand_item_name)
        if recipe_name then
          return hand_item_name, recipe_name
        end
        break
      end
    end
  end

  for _, item_request in pairs(item_requests) do
    local recipe_name = recipe_picker(player, item_request.name)
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
    remove_missing_materials_section(player)
    return
  end

  local item_requests = get_item_requests(player, crafting_complete, completed_item_name)
  if #item_requests == 0 then
    remove_missing_materials_section(player)
    return
  end

  sort_item_requests(item_requests)

  local hand_item_name = get_hand_item_name(player)
  local target_item_name, target_recipe_name =
    pick_recipe_from_requests(player, item_requests, hand_item_name, recipe_for_item_any)
  update_missing_materials_section(player, target_item_name, target_recipe_name)

  local allowed_queue_length = crafting_complete and 0 or 1
  if player.crafting_queue and #player.crafting_queue > allowed_queue_length then
    return
  end

  storage.data = storage.data or {}
  local data = storage.data[player.index] or {}

  local item_name, recipe_name =
    pick_recipe_from_requests(player, item_requests, hand_item_name, recipe_for_item)
  if recipe_name then
    data.active_item_name = item_name
    data.active_recipe_name = recipe_name
    storage.data[player.index] = data
    player.begin_crafting({ count = 1, recipe = recipe_name, silent = true })
  end
end

function autocraft.keep_missing_materials_section_enabled(player)
  local section = find_missing_materials_section(player)
  if section and section.valid then
    section.active = true
  end
end

return autocraft
