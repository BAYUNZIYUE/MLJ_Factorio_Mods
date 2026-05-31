local names = require("names")
local panel = require("panel")

local M = {}

local watched_settings = {
  [names.setting.wide] = true,
  [names.setting.hint_keys] = true,
  [names.setting.vehicle_on] = true,
  [names.setting.network_on] = true,
}

local function player_of(event)
  return event.player_index and game.get_player(event.player_index) or nil
end

local function mark(player)
  if not player then
    return
  end
  if not panel.has_visible_bars(player) then
    return
  end
  panel.ensure_storage()
  storage.expend_toolbar.dirty = storage.expend_toolbar.dirty or {}
  storage.expend_toolbar.dirty[player.index] = true
end

local function refresh_now(player)
  if not player then
    return
  end
  if not panel.has_visible_bars(player) then
    return
  end
  panel.refresh(player)
end

local function mark_polling_players()
  panel.ensure_storage()
  storage.expend_toolbar.dirty = storage.expend_toolbar.dirty or {}
  for _, player in pairs(game.connected_players) do
    if panel.needs_polling(player) then
      storage.expend_toolbar.dirty[player.index] = true
    end
  end
end

local function repaint_dirty()
  panel.ensure_storage()
  local dirty = storage.expend_toolbar.dirty or {}
  storage.expend_toolbar.dirty = {}
  for index in pairs(dirty) do
    local player = game.get_player(index)
    if player and player.connected then
      panel.refresh(player)
    end
  end
end

local function on_shortcut(event)
  local player = player_of(event)
  if not player then
    return
  end
  if event.prototype_name == names.input.make then
    panel.new_toolbar(player)
  elseif event.prototype_name == names.input.flip_all then
    panel.toggle_all(player)
  end
end

local function on_custom(event)
  local player = player_of(event)
  if not player then
    return
  end
  if event.input_name == names.input.make then
    panel.new_toolbar(player)
  elseif event.input_name == names.input.flip_all then
    panel.toggle_all(player)
  elseif event.input_name == names.input.grade_up then
    panel.adjust_grade(player, 1)
  elseif event.input_name == names.input.grade_down then
    panel.adjust_grade(player, -1)
  elseif event.input_name == names.input.factoriopedia then
    panel.open_focused_factoriopedia(player)
  end
end

function M.attach()
  script.on_init(function()
    storage.expend_toolbar = { next_id = 1, players = {}, dirty = {} }
  end)

  script.on_configuration_changed(function()
    storage.expend_toolbar = { next_id = 1, players = {}, dirty = {} }
    for _, player in pairs(game.connected_players) do
      panel.paint(player)
    end
  end)

  script.on_event(defines.events.on_player_joined_game, function(event)
    local player = player_of(event)
    if player then
      panel.paint(player)
    end
  end)

  script.on_event(defines.events.on_lua_shortcut, on_shortcut)

  script.on_event(defines.events.on_gui_click, panel.handle_click)
  script.on_event(defines.events.on_gui_elem_changed, panel.handle_choice)
  script.on_event(defines.events.on_gui_confirmed, panel.handle_confirmed)
  script.on_event(defines.events.on_gui_hover, panel.remember_hover)
  script.on_event(defines.events.on_gui_leave, panel.forget_hover)
  script.on_event(defines.events.on_gui_location_changed, panel.remember_place)

  script.on_event(defines.events.on_runtime_mod_setting_changed, function(event)
    if not watched_settings[event.setting] then
      return
    end
    local player = player_of(event)
    if player and panel.has_visible_bars(player) then
      panel.paint(player)
    end
  end)

  script.on_event({
    defines.events.on_player_main_inventory_changed,
    defines.events.on_player_trash_inventory_changed,
    defines.events.on_player_cursor_stack_changed,
    defines.events.on_player_controller_changed,
    defines.events.on_player_changed_surface,
  }, function(event)
    refresh_now(player_of(event))
  end)

  script.on_nth_tick(30, function()
    mark_polling_players()
    repaint_dirty()
  end)

  script.on_event({
    names.input.make,
    names.input.flip_all,
    names.input.factoriopedia,
    names.input.grade_up,
    names.input.grade_down,
  }, on_custom)
end

return M
