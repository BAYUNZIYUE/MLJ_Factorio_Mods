local constants = require("constants")
local autocraft = require("autocraft")

local function sync_shortcut_state(player)
  if player and player.valid then
    player.set_shortcut_toggled(constants.AUTOCRAFT_SHORTCUT_NAME, autocraft.is_enabled(player))
  end
end

local function enable_player_force_logistics_requests()
  -- 这里只处理默认 player force，确保角色物流请求能力始终开启。
  local player_force = game.forces["player"]
  player_force.character_logistic_requests = true
end

local function get_player_crafting_speed_multiplier(player)
  local setting = player.mod_settings[constants.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING]
  local multiplier = setting and tonumber(setting.value) or 1
  return math.max(multiplier, 1)
end

local function sync_player_crafting_speed_modifier(player)
  if not player or not player.valid then
    return
  end

  if not player.character then
    -- 新建游戏 tick 0 可能尚未创建角色，直接写角色速度会触发 Factorio 的 "No character"。
    return
  end

  local multiplier = get_player_crafting_speed_multiplier(player)
  local modifier = multiplier - 1
  player.character_crafting_speed_modifier = modifier
end

local function sync_all_player_crafting_speed_modifiers()
  for _, player in pairs(game.players) do
    sync_player_crafting_speed_modifier(player)
  end
end

local function sync_force_runtime_state()
  enable_player_force_logistics_requests()
end

local function on_configuration_changed()
  storage.recipes = autocraft.pre_compute_recipes()
  storage.data = storage.data or {}

  sync_force_runtime_state()
  sync_all_player_crafting_speed_modifiers()

  for _, player in pairs(game.players) do
    autocraft.mark_sections_dirty(player)
    sync_shortcut_state(player)
    autocraft.sync_section_status_notifications(player)
  end
end

local function on_init()
  storage.data = {}
  on_configuration_changed()
end

local function sync_player_state(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end

  sync_player_crafting_speed_modifier(player)
  sync_shortcut_state(player)
  autocraft.mark_sections_dirty(player)
  autocraft.sync_section_status_notifications(player)

  if autocraft.is_enabled(player) then
    autocraft.do_crafting(player)
  end
end

local function keep_missing_sections_enabled()
  local profiler = autocraft.start_profile()
  if not storage.missing_section_players then
    autocraft.record_profile("control.keep_missing_sections_enabled", profiler, { no_players_table = 1 })
    return
  end

  local watched_players = 0
  for player_index in pairs(storage.missing_section_players) do
    watched_players = watched_players + 1
    local player = game.get_player(player_index)
    if player then
      autocraft.keep_missing_materials_section_enabled(player)
    else
      storage.missing_section_players[player_index] = nil
    end
  end
  autocraft.record_profile("control.keep_missing_sections_enabled", profiler, { watched_players = watched_players })
end

local function sync_section_status_notifications_for_connected_players()
  local profiler = autocraft.start_profile()
  local connected_players = 0
  for _, player in pairs(game.connected_players) do
    connected_players = connected_players + 1
    autocraft.sync_section_status_notifications(player, "logistics")
  end
  autocraft.record_profile("control.sync_section_status_notifications", profiler, { connected_players = connected_players })
end

local function trigger_crafting(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end

  if (
    (event.name == defines.events.on_gui_opened or event.name == defines.events.on_gui_closed)
    and event.gui_type ~= defines.gui_type.controller
  ) then
    return
  end

  if event.name == defines.events.on_gui_closed and event.gui_type == defines.gui_type.controller then
    autocraft.mark_sections_dirty(player)
    autocraft.sync_section_status_notifications(player, "logistics")
  end

  autocraft.do_crafting(player)
end

local function on_player_crafted_item(event)
  if not event.item_stack.valid_for_read then
    return
  end

  local player = game.get_player(event.player_index)
  if not player or not player.crafting_queue then
    return
  end

  local crafted_last_item_in_stack = #player.crafting_queue > 0 and player.crafting_queue[1].count == 1
  if not crafted_last_item_in_stack then
    return
  end

  local data = storage.data and storage.data[event.player_index] or nil
  if not data or data.active_recipe_name == nil then
    if player.mod_settings[constants.AUTOCRAFT_SOUND_ENABLED].value then
      player.play_sound({ path = constants.CRAFTING_FINISHED_SOUND })
    end
    return
  end

  local event_quality_name = event.item_stack.quality.name
  local is_active_item =
    data.active_item_name == event.item_stack.name and (data.active_quality_name or "normal") == event_quality_name

  if is_active_item and player.mod_settings[constants.AUTOCRAFT_SOUND_ENABLED].value then
    player.play_sound({ path = constants.CRAFTING_FINISHED_SOUND })
  end

  if is_active_item then
    data.active_item_name = nil
    data.active_quality_name = nil
    data.active_queue_index = nil
    data.active_recipe_name = nil

    if #player.crafting_queue == 1 then
      autocraft.do_crafting(player, false, event.item_stack.name, event_quality_name)
    end
  end
end

local function on_player_cancelled_crafting(event)
  local data = storage.data and storage.data[event.player_index] or nil
  if not data or data.active_recipe_name ~= event.recipe.name then
    return
  end

  local player = game.get_player(event.player_index)
  if not player then
    return
  end

  autocraft.clear_active_state(player)
end

local function on_lua_shortcut(event)
  if event.prototype_name ~= constants.AUTOCRAFT_SHORTCUT_NAME then
    return
  end

  local player = game.get_player(event.player_index)
  if not player then
    return
  end

  local enabled = not autocraft.is_enabled(player)
  autocraft.set_enabled(player, enabled)
  sync_shortcut_state(player)
  autocraft.sync_section_status_notifications(player, "shortcut")

  if enabled then
    autocraft.do_crafting(player)
  else
    autocraft.cancel_active_crafting(player)
  end
end

local function on_runtime_mod_setting_changed(event)
  if event.setting == constants.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING then
    local player = game.get_player(event.player_index)
    sync_player_crafting_speed_modifier(player)
    return
  end

  if not (
    event.setting == constants.AUTOCRAFT_PREFIX_SETTING
    or event.setting == constants.AUTOCRAFT_MATCH_MODE_SETTING
    or event.setting == constants.AUTOCRAFT_SOUND_ENABLED
  ) then
    return
  end

  local player = game.get_player(event.player_index)
  if not player then
    return
  end

  sync_shortcut_state(player)
  if event.setting == constants.AUTOCRAFT_PREFIX_SETTING or event.setting == constants.AUTOCRAFT_MATCH_MODE_SETTING then
    autocraft.mark_sections_dirty(player)
  end
  autocraft.sync_section_status_notifications(player)

  if autocraft.is_enabled(player) then
    autocraft.do_crafting(player)
  end
end

script.on_init(on_init)
script.on_configuration_changed(on_configuration_changed)

script.on_event(defines.events.on_player_crafted_item, on_player_crafted_item)
script.on_event(defines.events.on_player_cancelled_crafting, on_player_cancelled_crafting)
script.on_event(defines.events.on_lua_shortcut, on_lua_shortcut)
script.on_event(defines.events.on_runtime_mod_setting_changed, on_runtime_mod_setting_changed)
script.on_event(defines.events.on_gui_closed, trigger_crafting)
script.on_event(defines.events.on_player_main_inventory_changed, trigger_crafting)
script.on_event(defines.events.on_player_joined_game, sync_player_state)
script.on_event(defines.events.on_player_controller_changed, sync_player_state)
script.on_event(defines.events.on_force_reset, sync_force_runtime_state)
script.on_event(defines.events.on_forces_merged, sync_force_runtime_state)
script.on_event(defines.events.on_technology_effects_reset, sync_force_runtime_state)
script.on_nth_tick(60, keep_missing_sections_enabled)
script.on_nth_tick(30, sync_section_status_notifications_for_connected_players)
