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
    section_status_snapshot = {},
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
    return "[自动]" .. display_prefix .. player.name .. "-缺失材料"
  end
  return "[Auto]" .. display_prefix .. player.name .. "-Missing materials"
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

local function build_missing_material_slot(request)
  -- Factorio 2.0 要求非零 min 的物流请求使用“简单物品”格式，直接传物品名即可。
  return {
    value = request.name,
    min = request.count,
  }
end

local function count_item_partial_space(main_inventory, item_name)
  local partial_space = 0
  for slot_index = 1, #main_inventory do
    local stack = main_inventory[slot_index]
    if stack.valid_for_read and stack.name == item_name then
      partial_space = partial_space + math.max(0, stack.prototype.stack_size - stack.count)
    end
  end

  return partial_space
end

local function cap_requests_to_main_inventory_capacity(player, request_list)
  local main_inventory = player.get_main_inventory()
  if not main_inventory or not main_inventory.valid then
    return request_list
  end

  local remaining_empty_stacks = main_inventory.count_empty_stacks(false, false)
  local capped_requests = {}

  -- 多种缺料会竞争同一批空格，所以这里按当前排序顺序共享分配空栈容量。
  for _, request in ipairs(request_list) do
    local prototype = prototypes.item[request.name]
    if not prototype then
      capped_requests[#capped_requests + 1] = request
    else
      local stack_size = prototype.stack_size
      local current_count = main_inventory.get_item_count(request.name)
      local partial_space = count_item_partial_space(main_inventory, request.name)
      local max_target_count = current_count + partial_space + remaining_empty_stacks * stack_size
      local capped_count = math.min(request.count, max_target_count)
      capped_count = math.max(capped_count, current_count)

      if capped_count > 0 then
        capped_requests[#capped_requests + 1] = {
          name = request.name,
          count = capped_count,
        }
      end

      local extra_reserved = math.max(0, capped_count - current_count)
      local extra_from_empty = math.max(0, extra_reserved - partial_space)
      local empty_stacks_used = stack_size > 0 and math.ceil(extra_from_empty / stack_size) or 0
      remaining_empty_stacks = math.max(0, remaining_empty_stacks - empty_stacks_used)
    end
  end

  return capped_requests
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

  request_list = cap_requests_to_main_inventory_capacity(player, request_list)

  local section = ensure_missing_materials_section(player)
  if not section or not section.valid then
    return
  end

  section.active = true
  for slot_index, request in ipairs(request_list) do
    section.set_slot(slot_index, build_missing_material_slot(request))
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

local function get_section_message_name(section_name)
  if section_name and section_name ~= "" then
    return section_name
  end

  return { "autocraft-message.autocraft-toggle-status-unnamed-group" }
end

local function build_section_status_snapshot(player)
  local snapshot = {}
  local logistic_point = player.get_requester_point()
  if not logistic_point or not logistic_point.valid then
    return snapshot
  end

  local missing_section = find_missing_materials_section(player)
  local missing_section_index = missing_section and missing_section.valid and missing_section.index or nil

  -- 这里保存“当前真正生效的自动手搓分组”，后续统一通过快照 diff 决定是否提示。
  for _, section in pairs(logistic_point.sections) do
    if should_include_section(player, section, missing_section_index) then
      snapshot[section.index] = {
        name = section.group or "",
      }
    end
  end

  return snapshot
end

local function build_section_status_lines(previous_snapshot, next_snapshot)
  local changed_sections = {}
  local indexes = {}

  for section_index in pairs(previous_snapshot) do
    indexes[section_index] = true
  end
  for section_index in pairs(next_snapshot) do
    indexes[section_index] = true
  end

  for section_index in pairs(indexes) do
    local previous_entry = previous_snapshot[section_index]
    local next_entry = next_snapshot[section_index]
    local previous_enabled = previous_entry ~= nil
    local next_enabled = next_entry ~= nil

    if previous_enabled ~= next_enabled then
      local entry = next_entry or previous_entry
      changed_sections[#changed_sections + 1] = {
        name = entry and entry.name or "",
        enabled = next_enabled,
      }
    end
  end

  table.sort(changed_sections, function(a, b)
    if a.name ~= b.name then
      return a.name < b.name
    end

    if a.enabled ~= b.enabled then
      return a.enabled and not b.enabled
    end

    return false
  end)

  local section_lines = {}
  for _, change in ipairs(changed_sections) do
    local action_key = change.enabled and "autocraft-toggle-status-enabled" or "autocraft-toggle-status-disabled"
    section_lines[#section_lines + 1] = {
      "autocraft-message.autocraft-toggle-status-line",
      get_section_message_name(change.name),
      { "autocraft-message." .. action_key },
    }
  end

  return section_lines
end

local function notify_section_status_lines(player, section_lines)
  local message = { "" }
  for index, line in ipairs(section_lines) do
    if index > 1 then
      message[#message + 1] = "\n"
    end
    message[#message + 1] = line
  end

  player.print(message)
end

local function sync_section_status_notifications(player, trigger_mode)
  local data = get_player_data(player)
  local previous_snapshot = data.section_status_snapshot or {}
  local next_snapshot = build_section_status_snapshot(player)
  data.section_status_snapshot = next_snapshot

  if trigger_mode == nil then
    return
  end

  local section_lines = build_section_status_lines(previous_snapshot, next_snapshot)
  if trigger_mode == "shortcut" then
    if #section_lines == 0 then
      player.print({ "autocraft-message.autocraft-toggle-status-empty" })
      return
    end

    notify_section_status_lines(player, section_lines)
    return
  end

  if trigger_mode == "logistics" then
    for _, section_line in ipairs(section_lines) do
      notify_section_status_lines(player, { section_line })
    end
  end
end

autocraft.sync_section_status_notifications = sync_section_status_notifications

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
  if not data or not data.active_recipe_name or not data.active_queue_index or not player.crafting_queue then
    return nil
  end

  local queue_item = player.crafting_queue[data.active_queue_index]
  if not queue_item or queue_item.prerequisite then
    return nil
  end

  local recipe_name = type(queue_item.recipe) == "string" and queue_item.recipe or queue_item.recipe.name
  if recipe_name ~= data.active_recipe_name then
    return nil
  end

  return data.active_queue_index, queue_item
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
  data.active_queue_index = nil
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
  data.active_queue_index = nil
  data.active_recipe_name = nil
  remove_missing_materials_section(player)
end

local function get_sorted_recipe_names(recipes)
  local recipe_names = {}
  for recipe_name in pairs(recipes) do
    recipe_names[#recipe_names + 1] = recipe_name
  end

  table.sort(recipe_names)
  return recipe_names
end

local function recipe_for_item(player, item_name)
  local recipes = storage.recipes and storage.recipes[item_name]
  if not recipes then
    return nil
  end

  for _, recipe_name in ipairs(get_sorted_recipe_names(recipes)) do
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

  for _, recipe_name in ipairs(get_sorted_recipe_names(recipes)) do
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

local function consume_available_item_count(available_items, item_name, needed_count)
  local available_count = available_items[item_name] or 0
  local consumed_count = math.min(available_count, needed_count)
  available_items[item_name] = available_count - consumed_count
  return consumed_count
end

local function accumulate_missing_materials(
  player,
  item_name,
  required_count,
  requests,
  visiting,
  logistic_network,
  available_inventory_counts,
  available_network_counts
)
  if required_count <= 0 then
    return
  end

  requests[item_name] = (requests[item_name] or 0) + required_count

  if available_inventory_counts[item_name] == nil then
    available_inventory_counts[item_name] = player.get_item_count(item_name)
  end

  local inventory_count = consume_available_item_count(available_inventory_counts, item_name, required_count)
  local missing_count = required_count - inventory_count
  if missing_count <= 0 then
    return
  end

  if available_network_counts[item_name] == nil then
    available_network_counts[item_name] = logistic_network and logistic_network.get_item_count(item_name) or 0
  end

  local logistic_network_count = consume_available_item_count(available_network_counts, item_name, missing_count)
  local unresolved_count = missing_count - logistic_network_count
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
      if available_inventory_counts[ingredient.name] == nil then
        available_inventory_counts[ingredient.name] = player.get_item_count(ingredient.name)
      end

      -- 所有递归分支共享同一份背包库存，避免同一个材料被重复抵扣。
      local required_count = ingredient.amount * crafts_needed
      if required_count > 0 then
        accumulate_missing_materials(
          player,
          ingredient.name,
          required_count,
          requests,
          visiting,
          logistic_network,
          available_inventory_counts,
          available_network_counts
        )
      end
    end
  end

  visiting[item_name] = nil
end

local function update_missing_materials_section(player, target_item_name, target_recipe_name, target_missing_count)
  if not autocraft.is_enabled(player) then
    remove_missing_materials_section(player)
    return
  end

  if not target_item_name or not target_recipe_name or not target_missing_count or target_missing_count <= 0 then
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
  local available_inventory_counts = {}
  local available_network_counts = {}
  local crafts_needed = math.ceil(target_missing_count / get_recipe_output_amount(recipe, target_item_name))

  for _, ingredient in pairs(recipe.ingredients) do
    if ingredient.type == "item" then
      local required_count = ingredient.amount * crafts_needed
      if required_count > 0 then
        has_missing_materials = true
        accumulate_missing_materials(
          player,
          ingredient.name,
          required_count,
          missing_requests,
          {},
          logistic_network,
          available_inventory_counts,
          available_network_counts
        )
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
          return item_request, recipe_name
        end
        break
      end
    end
  end

  for _, item_request in pairs(item_requests) do
    local recipe_name = recipe_picker(player, item_request.name)
    if recipe_name then
      return item_request, recipe_name
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
  local target_item_request, target_recipe_name =
    pick_recipe_from_requests(player, item_requests, hand_item_name, recipe_for_item_any)
  local target_item_name = target_item_request and target_item_request.name or nil
  update_missing_materials_section(
    player,
    target_item_name,
    target_recipe_name,
    target_item_request and target_item_request.missing or nil
  )

  local allowed_queue_length = crafting_complete and 0 or 1
  if player.crafting_queue and #player.crafting_queue > allowed_queue_length then
    return
  end

  storage.data = storage.data or {}
  local data = storage.data[player.index] or {}

  local item_request, recipe_name =
    pick_recipe_from_requests(player, item_requests, hand_item_name, recipe_for_item)
  local item_name = item_request and item_request.name or nil
  if recipe_name then
    data.active_item_name = item_name
    data.active_queue_index = player.crafting_queue and (#player.crafting_queue + 1) or 1
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
