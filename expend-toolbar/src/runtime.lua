local names = require("names")
local panel = require("panel")

local M = {}

local function player_of(event)
  return event.player_index and game.get_player(event.player_index) or nil
end

local function repaint_connected()
  panel.ensure_storage()
  panel.paint_all()
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
  elseif event.input_name == names.input.fold_header then
    local state = storage.expend_toolbar and storage.expend_toolbar.players and storage.expend_toolbar.players[player.index]
    local bar = state and state.bars and state.bars[1]
    if bar then
      bar.folded = not bar.folded
      panel.paint(player)
    end
  elseif event.input_name == names.input.pipette then
    panel.place_cursor(player)
  elseif event.input_name == names.input.grade_up then
    panel.adjust_grade(player, 1)
  elseif event.input_name == names.input.grade_down then
    panel.adjust_grade(player, -1)
  elseif event.input_name == names.input.clear then
    panel.clear_focused(player)
  elseif event.input_name == names.input.factoriopedia then
    panel.open_focused_factoriopedia(player)
  end
end

function M.attach()
  script.on_init(function()
    storage.expend_toolbar = { next_id = 1, players = {} }
  end)

  script.on_configuration_changed(function()
    storage.expend_toolbar = { next_id = 1, players = {} }
    repaint_connected()
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
  script.on_event(defines.events.on_gui_hover, panel.remember_hover)
  script.on_event(defines.events.on_gui_location_changed, panel.remember_place)

  script.on_event(defines.events.on_runtime_mod_setting_changed, function(event)
    local player = player_of(event)
    if player then
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
    local player = player_of(event)
    if player then
      panel.paint(player)
    end
  end)

  script.on_nth_tick(30, repaint_connected)

  script.on_event({
    names.input.make,
    names.input.flip_all,
    names.input.fold_header,
    names.input.pipette,
    names.input.clear,
    names.input.factoriopedia,
    names.input.grade_up,
    names.input.grade_down,
  }, on_custom)
end

return M
