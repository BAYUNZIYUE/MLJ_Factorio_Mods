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

local function on_configuration_changed()
  storage.recipes = autocraft.pre_compute_recipes()
  storage.data = storage.data or {}

  enable_player_force_logistics_requests()

  for _, player in pairs(game.players) do
    sync_shortcut_state(player)
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

  sync_shortcut_state(player)

  if autocraft.is_enabled(player) then
    autocraft.do_crafting(player)
  end
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

  if data.active_item_name == event.item_stack.name and player.mod_settings[constants.AUTOCRAFT_SOUND_ENABLED].value then
    player.play_sound({ path = constants.CRAFTING_FINISHED_SOUND })
  end

  if data.active_item_name == event.item_stack.name then
    data.active_item_name = nil
    data.active_recipe_name = nil

    if #player.crafting_queue == 1 then
      autocraft.do_crafting(player, false, event.item_stack.name)
    end
  end
end

local function on_player_cancelled_crafting(event)
  local data = storage.data and storage.data[event.player_index] or nil
  if not data or data.active_recipe_name ~= event.recipe.name then
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

  if enabled then
    autocraft.do_crafting(player)
  else
    autocraft.cancel_active_crafting(player)
  end
end

local function on_runtime_mod_setting_changed(event)
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
script.on_event(defines.events.on_force_reset, enable_player_force_logistics_requests)
script.on_event(defines.events.on_forces_merged, enable_player_force_logistics_requests)
script.on_event(defines.events.on_technology_effects_reset, enable_player_force_logistics_requests)
