local constants = require("constants")

local autocraft = {}

local AUTOCRAFT_MAX_CRAFT_BATCH_SIZE = 10000
local AUTOCRAFT_PERFORMANCE_PROFILE_ENABLED = false

local performance_profile_state = {
  next_log_tick = nil,
  scopes = {},
}

local function starts_with(value, prefix)
  return string.sub(value, 1, #prefix) == prefix
end

local function reset_performance_profile_state()
  performance_profile_state.scopes = {}
  performance_profile_state.next_log_tick = game and (game.tick + 60) or nil
end

local function is_performance_debug_enabled()
  return AUTOCRAFT_PERFORMANCE_PROFILE_ENABLED
end

local function build_profile_detail_text(details)
  if not details then
    return ""
  end

  local keys = {}
  for key in pairs(details) do
    keys[#keys + 1] = key
  end
  table.sort(keys)

  local parts = {}
  for _, key in ipairs(keys) do
    parts[#parts + 1] = " " .. key .. "=" .. tostring(details[key])
  end
  return table.concat(parts)
end

local function flush_performance_profile()
  if not is_performance_debug_enabled() then
    reset_performance_profile_state()
    return
  end

  if not performance_profile_state.next_log_tick then
    performance_profile_state.next_log_tick = game.tick + 60
    return
  end

  if game.tick < performance_profile_state.next_log_tick then
    return
  end

  local scope_names = {}
  for scope_name in pairs(performance_profile_state.scopes) do
    scope_names[#scope_names + 1] = scope_name
  end
  table.sort(scope_names)

  for _, scope_name in ipairs(scope_names) do
    local scope = performance_profile_state.scopes[scope_name]
    if scope.calls > 0 then
      local average = game.create_profiler(true)
      average.add(scope.total)
      average.divide(scope.calls)
      log({
        "",
        "[section-autocraft-profile] tick=",
        tostring(game.tick),
        " scope=",
        scope_name,
        " calls=",
        tostring(scope.calls),
        build_profile_detail_text(scope.details),
        " avg=",
        average,
        " total=",
        scope.total,
      })
    end
  end

  performance_profile_state.scopes = {}
  performance_profile_state.next_log_tick = game.tick + 60
end

function autocraft.start_profile()
  if not is_performance_debug_enabled() then
    return nil
  end

  return game.create_profiler()
end

function autocraft.record_profile(scope_name, profiler, details)
  if not profiler then
    return
  end

  profiler.stop()
  local scope = performance_profile_state.scopes[scope_name]
  if not scope then
    scope = {
      calls = 0,
      details = {},
      total = game.create_profiler(true),
    }
    performance_profile_state.scopes[scope_name] = scope
  end

  scope.calls = scope.calls + 1
  scope.total.add(profiler)
  if details then
    for key, value in pairs(details) do
      scope.details[key] = (scope.details[key] or 0) + value
    end
  end

  flush_performance_profile()
end

local function get_player_data(player)
  storage.data = storage.data or {}
  storage.missing_section_players = storage.missing_section_players or {}
  local data = storage.data[player.index] or {
    enabled = constants.AUTOCRAFT_DEFAULT_ENABLED,
    missing_section_index = nil,
    missing_section_name = nil,
    request_cache_dirty = true,
    requested_items_cache = nil,
    section_status_dirty = true,
    section_status_snapshot = {},
  }
  if data.request_cache_dirty == nil then
    data.request_cache_dirty = true
  end
  if data.section_status_dirty == nil then
    data.section_status_dirty = true
  end
  data.section_status_snapshot = data.section_status_snapshot or {}
  storage.data[player.index] = data
  return data
end

local function mark_sections_dirty(player)
  local data = get_player_data(player)
  data.request_cache_dirty = true
  data.requested_items_cache = nil
  data.section_status_dirty = true
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

local function build_section_match_context(player)
  local data = get_player_data(player)
  return {
    enabled = data.enabled,
    configured_prefix = get_configured_prefix(player),
    current_missing_section_name = get_missing_materials_section_name(player),
    match_mode = get_match_mode(player),
    player_name = player.name,
    stored_missing_section_name = data.missing_section_name,
  }
end

local function is_missing_materials_section(section, context)
  return section.is_manual
    and (
      section.group == context.current_missing_section_name
      or (context.stored_missing_section_name and section.group == context.stored_missing_section_name)
    )
end

local function find_missing_materials_section(player)
  local profiler = autocraft.start_profile()
  local scanned_sections = 0
  local logistic_point = player.get_requester_point()
  if not logistic_point or not logistic_point.valid then
    autocraft.record_profile("find_missing_materials_section", profiler, { no_logistic_point = 1 })
    return nil
  end

  local context = build_section_match_context(player)
  local data = get_player_data(player)
  local cached_section = data.missing_section_index and logistic_point.sections[data.missing_section_index] or nil
  if cached_section and cached_section.valid and is_missing_materials_section(cached_section, context) then
    autocraft.record_profile("find_missing_materials_section", profiler, {
      cached = 1,
      found = 1,
    })
    return cached_section
  end

  for _, section in pairs(logistic_point.sections) do
    scanned_sections = scanned_sections + 1
    if is_missing_materials_section(section, context) then
      data.missing_section_index = section.index
      autocraft.record_profile("find_missing_materials_section", profiler, {
        found = 1,
        scanned_sections = scanned_sections,
      })
      return section
    end
  end

  autocraft.record_profile("find_missing_materials_section", profiler, {
    missing = 1,
    scanned_sections = scanned_sections,
  })
  data.missing_section_index = nil
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
    data.missing_section_index = section.index
    data.missing_section_name = section_name
    storage.missing_section_players[player.index] = true
    return section
  end

  section = logistic_point.add_section(section_name)
  if section then
    section.active = true
    data.missing_section_index = section.index
    data.missing_section_name = section_name
    storage.missing_section_players[player.index] = true
  end

  return section
end

local function remove_missing_materials_section(player)
  local logistic_point = player.get_requester_point()
  local data = get_player_data(player)
  if not data.missing_section_index and not data.missing_section_name then
    storage.missing_section_players[player.index] = nil
    return
  end

  if not logistic_point then
    data.missing_section_index = nil
    data.missing_section_name = nil
    return
  end

  local section = find_missing_materials_section(player)
  if section and section.valid then
    logistic_point.remove_section(section.index)
  end

  data.missing_section_index = nil
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
  local data = get_player_data(player)
  local next_enabled = enabled and true or false
  if data.enabled ~= next_enabled then
    data.enabled = next_enabled
    data.section_status_dirty = true
  end
end

function autocraft.mark_sections_dirty(player)
  mark_sections_dirty(player)
end

local function section_has_autocraft_ability(context, section)
  local section_name = section.group or ""

  if context.match_mode == constants.AUTOCRAFT_MATCH_MODE_FULL then
    return true
  end

  if context.match_mode == constants.AUTOCRAFT_MATCH_MODE_PREFIX then
    return context.configured_prefix ~= "" and starts_with(section_name, context.configured_prefix)
  end

  if context.match_mode == constants.AUTOCRAFT_MATCH_MODE_PLAYER_NAME then
    return starts_with(section_name, context.player_name)
  end

  if context.match_mode == constants.AUTOCRAFT_MATCH_MODE_PREFIX_AND_PLAYER_NAME then
    return context.configured_prefix ~= "" and starts_with(section_name, context.configured_prefix .. context.player_name)
  end

  return false
end

local function should_include_section(context, section)
  if not context.enabled then
    return false
  end

  if is_missing_materials_section(section, context) then
    return false
  end

  return section.active and section_has_autocraft_ability(context, section)
end

local function get_section_message_name(section_name)
  if section_name and section_name ~= "" then
    return section_name
  end

  return { "autocraft-message.autocraft-toggle-status-unnamed-group" }
end

local function build_section_status_snapshot(player)
  local profiler = autocraft.start_profile()
  local snapshot = {}
  local included_sections = 0
  local scanned_sections = 0
  local logistic_point = player.get_requester_point()
  if not logistic_point or not logistic_point.valid then
    autocraft.record_profile("build_section_status_snapshot", profiler, { no_logistic_point = 1 })
    return snapshot
  end

  local context = build_section_match_context(player)

  -- 这里保存“当前真正生效的自动手搓分组”，后续统一通过快照 diff 决定是否提示。
  for _, section in pairs(logistic_point.sections) do
    scanned_sections = scanned_sections + 1
    if should_include_section(context, section) then
      included_sections = included_sections + 1
      snapshot[section.index] = {
        name = section.group or "",
      }
    end
  end

  autocraft.record_profile("build_section_status_snapshot", profiler, {
    included_sections = included_sections,
    scanned_sections = scanned_sections,
  })
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
  -- 30 tick 兜底只在已知编组状态变化后重建快照，避免全匹配模式反复扫所有编组。
  if not data.section_status_dirty and trigger_mode ~= "shortcut" then
    return
  end

  local next_snapshot = build_section_status_snapshot(player)
  data.section_status_snapshot = next_snapshot
  data.section_status_dirty = false

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

local function build_requested_items(player)
  local profiler = autocraft.start_profile()
  local requested_items = {}
  local included_sections = 0
  local scanned_filters = 0
  local scanned_sections = 0
  local logistic_point = player.get_requester_point()
  if not logistic_point or not logistic_point.valid then
    autocraft.record_profile("build_requested_items", profiler, { no_logistic_point = 1 })
    return requested_items
  end

  local context = build_section_match_context(player)

  -- 先筛出本次应参与自动手搓的物流分组，再把同类物品的最小保有量汇总成一个总需求。
  for _, section in pairs(logistic_point.sections) do
    scanned_sections = scanned_sections + 1
    if should_include_section(context, section) then
      included_sections = included_sections + 1
      for _, filter in pairs(section.filters) do
        scanned_filters = scanned_filters + 1
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

  autocraft.record_profile("build_requested_items", profiler, {
    included_sections = included_sections,
    requested_items = table_size(requested_items),
    scanned_filters = scanned_filters,
    scanned_sections = scanned_sections,
  })
  return requested_items
end

local function get_requested_items(player)
  local data = get_player_data(player)
  -- 物流编组请求只在编组/匹配规则变化时重建；背包变化会频繁触发，只复用这份缓存。
  if not data.request_cache_dirty and data.requested_items_cache then
    return data.requested_items_cache
  end

  local requested_items = build_requested_items(player)
  data.requested_items_cache = requested_items
  data.request_cache_dirty = false
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
  if recipes.sorted_names then
    return recipes.sorted_names
  end

  local recipe_names = {}
  for recipe_name in pairs(recipes) do
    if recipe_name ~= "sorted_names" then
      recipe_names[#recipe_names + 1] = recipe_name
    end
  end

  table.sort(recipe_names)
  recipes.sorted_names = recipe_names
  return recipe_names
end

local function add_recipe_pick_stat(stats, name, count)
  if not stats then
    return
  end

  stats[name] = (stats[name] or 0) + (count or 1)
end

local function get_recipe_pick_stats_details(stats, item_request_count, recipe_found)
  return {
    cached_pick_attempts = stats.cached_pick_attempts or 0,
    cached_pick_hits = stats.cached_pick_hits or 0,
    cached_pick_misses = stats.cached_pick_misses or 0,
    get_craftable_count_calls = stats.get_craftable_count_calls or 0,
    item_checks = stats.item_checks or 0,
    item_requests = item_request_count,
    recipe_checks = stats.recipe_checks or 0,
    recipe_found = recipe_found and 1 or 0,
  }
end

local function is_recipe_craftable(player, recipe_name, stats)
  add_recipe_pick_stat(stats, "get_craftable_count_calls")
  return player.get_craftable_count(recipe_name) > 0
end

local function recipe_for_item(player, item_name, stats)
  add_recipe_pick_stat(stats, "item_checks")
  local recipes = storage.recipes and storage.recipes[item_name]
  if not recipes then
    return nil
  end

  for _, recipe_name in ipairs(get_sorted_recipe_names(recipes)) do
    add_recipe_pick_stat(stats, "recipe_checks")
    local recipe = player.force.recipes[recipe_name]
    local can_craft = recipe and not recipe.hidden and recipe.enabled
      and is_recipe_craftable(player, recipe_name, stats)

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

local function get_crafting_queue_item_counts(player)
  local crafting_queue = player.crafting_queue
  if not crafting_queue then
    return {}
  end

  local queued_counts = {}
  for _, queue_item in pairs(crafting_queue) do
    if not queue_item.prerequisite then
      local recipe_name = type(queue_item.recipe) == "string" and queue_item.recipe or queue_item.recipe.name
      local recipe = player.force.recipes[recipe_name]

      if recipe then
        for _, product in pairs(recipe.products) do
          if product.type == "item" then
            queued_counts[product.name] = (queued_counts[product.name] or 0) + queue_item.count * (product.amount or 1)
          end
        end
      end
    end
  end

  return queued_counts
end

local function get_item_requests(player, crafting_complete, completed_item_name)
  local profiler = autocraft.start_profile()
  local item_requests = {}
  local requested_items = get_requested_items(player)
  local logistic_point = player.get_requester_point()
  local logistic_network = nil
  local requested_item_count = 0
  local inventory_checks = 0
  local network_checks = 0
  if logistic_point and logistic_point.valid then
    local candidate_network = logistic_point.logistic_network
    if candidate_network and candidate_network.valid then
      logistic_network = candidate_network
    end
  end
  local queued_counts = get_crafting_queue_item_counts(player)

  -- 实际手搓缺口要同时扣掉玩家已持有、当前物流网络已有，以及已经排进手搓队列的成品数量。
  for item_name, min in pairs(requested_items) do
    requested_item_count = requested_item_count + 1
    local recently_completed_count = 0
    if not crafting_complete and completed_item_name == item_name then
      recently_completed_count = 1
    end

    inventory_checks = inventory_checks + 1
    local inventory_count = player.get_item_count(item_name) + recently_completed_count
    local logistic_network_count = 0
    if logistic_network then
      network_checks = network_checks + 1
      logistic_network_count = logistic_network.get_item_count(item_name)
    end
    local queued_count = queued_counts[item_name] or 0
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

  autocraft.record_profile("get_item_requests", profiler, {
    inventory_checks = inventory_checks,
    item_requests = #item_requests,
    network_checks = network_checks,
    requested_items = requested_item_count,
  })
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

local function get_craft_count(player, recipe_name, recipe, item_request)
  local crafts_needed = math.ceil(item_request.missing / get_recipe_output_amount(recipe, item_request.name))
  local craftable_count = player.get_craftable_count(recipe_name)

  return math.min(crafts_needed, craftable_count, AUTOCRAFT_MAX_CRAFT_BATCH_SIZE)
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
  local profiler = autocraft.start_profile()
  if not autocraft.is_enabled(player) then
    remove_missing_materials_section(player)
    autocraft.record_profile("update_missing_materials_section", profiler, { disabled = 1 })
    return
  end

  if not target_item_name or not target_recipe_name or not target_missing_count or target_missing_count <= 0 then
    remove_missing_materials_section(player)
    autocraft.record_profile("update_missing_materials_section", profiler, { no_target = 1 })
    return
  end

  local recipe = player.force.recipes[target_recipe_name]
  if not recipe then
    remove_missing_materials_section(player)
    autocraft.record_profile("update_missing_materials_section", profiler, { no_recipe = 1 })
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
  local top_level_ingredients = 0

  for _, ingredient in pairs(recipe.ingredients) do
    if ingredient.type == "item" then
      top_level_ingredients = top_level_ingredients + 1
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
    autocraft.record_profile("update_missing_materials_section", profiler, {
      no_missing_materials = 1,
      top_level_ingredients = top_level_ingredients,
    })
    return
  end

  write_missing_materials_section(player, missing_requests)
  autocraft.record_profile("update_missing_materials_section", profiler, {
    missing_request_kinds = table_size(missing_requests),
    top_level_ingredients = top_level_ingredients,
  })
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

local function find_item_request(item_requests, item_name)
  if not item_name then
    return nil
  end

  for _, item_request in ipairs(item_requests) do
    if item_request.name == item_name then
      return item_request
    end
  end

  return nil
end

local function pick_recipe_for_item_request(player, item_requests, item_name, recipe_picker, stats)
  local item_request = find_item_request(item_requests, item_name)
  if not item_request then
    return nil
  end

  local recipe_name = recipe_picker(player, item_name, stats)
  if recipe_name then
    return item_request, recipe_name
  end

  return nil
end

local function pick_cached_recipe_from_requests(player, item_requests, cached_item_name, cached_recipe_name, stats)
  if not cached_item_name or not cached_recipe_name then
    return nil
  end

  add_recipe_pick_stat(stats, "cached_pick_attempts")
  local item_request = find_item_request(item_requests, cached_item_name)
  if not item_request then
    add_recipe_pick_stat(stats, "cached_pick_misses")
    return nil
  end

  local recipes = storage.recipes and storage.recipes[cached_item_name]
  if not recipes or not recipes[cached_recipe_name] then
    add_recipe_pick_stat(stats, "cached_pick_misses")
    return nil
  end

  add_recipe_pick_stat(stats, "item_checks")
  add_recipe_pick_stat(stats, "recipe_checks")
  local recipe = player.force.recipes[cached_recipe_name]
  local can_craft = recipe and not recipe.hidden and recipe.enabled
    and is_recipe_craftable(player, cached_recipe_name, stats)
  if can_craft then
    add_recipe_pick_stat(stats, "cached_pick_hits")
    return item_request, cached_recipe_name
  end

  add_recipe_pick_stat(stats, "cached_pick_misses")
  return nil
end

local function pick_recipe_from_requests(player, item_requests, recipe_picker, stats)
  for _, item_request in ipairs(item_requests) do
    local recipe_name = recipe_picker(player, item_request.name, stats)
    if recipe_name then
      return item_request, recipe_name
    end
  end

  return nil
end

function autocraft.do_crafting(player, crafting_complete, completed_item_name)
  local profiler = autocraft.start_profile()
  if crafting_complete == nil then
    crafting_complete = true
  end

  if not autocraft.is_enabled(player) then
    autocraft.record_profile("do_crafting", profiler, { disabled = 1 })
    return
  end

  local is_eligible = player.connected
    and player.controller_type == defines.controllers.character
    and player.ticks_to_respawn == nil

  if not is_eligible then
    remove_missing_materials_section(player)
    autocraft.record_profile("do_crafting", profiler, { ineligible = 1 })
    return
  end

  local allowed_queue_length = crafting_complete and 0 or 1
  if player.crafting_queue and #player.crafting_queue > allowed_queue_length then
    autocraft.record_profile("do_crafting", profiler, {
      queue_busy = 1,
      queue_length = #player.crafting_queue,
    })
    return
  end

  local get_requests_profiler = autocraft.start_profile()
  local item_requests = get_item_requests(player, crafting_complete, completed_item_name)
  autocraft.record_profile("do_crafting.get_item_requests", get_requests_profiler, {
    item_requests = #item_requests,
  })
  if #item_requests == 0 then
    remove_missing_materials_section(player)
    autocraft.record_profile("do_crafting", profiler, { no_item_requests = 1 })
    return
  end

  local sort_profiler = autocraft.start_profile()
  sort_item_requests(item_requests)
  autocraft.record_profile("do_crafting.sort_item_requests", sort_profiler, {
    item_requests = #item_requests,
  })

  storage.data = storage.data or {}
  local data = storage.data[player.index] or {}
  local hand_item_name = get_hand_item_name(player)
  local pick_profiler = autocraft.start_profile()
  local recipe_pick_stats = {}
  local item_request, recipe_name =
    pick_recipe_for_item_request(player, item_requests, hand_item_name, recipe_for_item, recipe_pick_stats)
  if not recipe_name and not crafting_complete and completed_item_name == data.last_craftable_item_name then
    item_request, recipe_name = pick_cached_recipe_from_requests(
      player,
      item_requests,
      data.last_craftable_item_name,
      data.last_craftable_recipe_name,
      recipe_pick_stats
    )
  end
  if not recipe_name then
    item_request, recipe_name = pick_recipe_from_requests(player, item_requests, recipe_for_item, recipe_pick_stats)
  end
  autocraft.record_profile(
    "do_crafting.pick_craftable_recipe",
    pick_profiler,
    get_recipe_pick_stats_details(recipe_pick_stats, #item_requests, recipe_name)
  )
  local item_name = item_request and item_request.name or nil
  if recipe_name then
    local recipe = player.force.recipes[recipe_name]
    local craft_count = recipe and get_craft_count(player, recipe_name, recipe, item_request) or 0
    if craft_count <= 0 then
      autocraft.record_profile("do_crafting", profiler, {
        craft_count_zero = 1,
        item_requests = #item_requests,
      })
      return
    end

    local remove_section_profiler = autocraft.start_profile()
    remove_missing_materials_section(player)
    autocraft.record_profile("do_crafting.remove_missing_section", remove_section_profiler)
    data.active_item_name = item_name
    data.active_queue_index = player.crafting_queue and (#player.crafting_queue + 1) or 1
    data.active_recipe_name = recipe_name
    data.last_craftable_item_name = item_name
    data.last_craftable_recipe_name = recipe_name
    storage.data[player.index] = data
    local begin_crafting_profiler = autocraft.start_profile()
    player.begin_crafting({ count = craft_count, recipe = recipe_name, silent = true })
    autocraft.record_profile("do_crafting.begin_crafting_api", begin_crafting_profiler, {
      begin_crafting = craft_count,
    })
    autocraft.record_profile("do_crafting", profiler, {
      begin_crafting = craft_count,
      item_requests = #item_requests,
    })
    return
  end

  local target_item_request, target_recipe_name =
    pick_recipe_for_item_request(player, item_requests, hand_item_name, recipe_for_item_any)
  if not target_recipe_name then
    target_item_request, target_recipe_name =
      pick_recipe_from_requests(player, item_requests, recipe_for_item_any)
  end
  local target_item_name = target_item_request and target_item_request.name or nil
  update_missing_materials_section(
    player,
    target_item_name,
    target_recipe_name,
    target_item_request and target_item_request.missing or nil
  )

  autocraft.record_profile("do_crafting", profiler, {
    begin_crafting = 0,
    item_requests = #item_requests,
  })
end

function autocraft.keep_missing_materials_section_enabled(player)
  local profiler = autocraft.start_profile()
  local section = find_missing_materials_section(player)
  if section and section.valid then
    section.active = true
  end
  autocraft.record_profile("keep_missing_materials_section_enabled", profiler, {
    found = section and section.valid and 1 or 0,
  })
end

return autocraft
