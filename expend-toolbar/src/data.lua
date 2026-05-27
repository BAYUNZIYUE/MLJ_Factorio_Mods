local names = require("names")
local styles = data.raw["gui-style"].default

data:extend({
  {
    order = "a1",
    type = "custom-input",
    name = names.input.make,
    localised_name = "Create a toolbar",
    key_sequence = "",
  },
  {
    order = "a2",
    type = "custom-input",
    name = names.input.flip_all,
    localised_name = "Show or hide custom bars",
    key_sequence = "",
  },
  {
    order = "a3",
    type = "custom-input",
    name = names.input.fold_header,
    localised_name = "Toggle toolbar header",
    key_sequence = "",
  },
  { type = "custom-input", name = names.input.pipette, linked_game_control = "pipette", key_sequence = "" },
  { type = "custom-input", name = names.input.factoriopedia, linked_game_control = "open-factoriopedia", key_sequence = "" },
  { type = "custom-input", name = names.input.clear, linked_game_control = "toggle-filter", key_sequence = "" },
  { type = "custom-input", name = names.input.grade_up, linked_game_control = "cycle-quality-up", key_sequence = "" },
  { type = "custom-input", name = names.input.grade_down, linked_game_control = "cycle-quality-down", key_sequence = "" },
})

data:extend({
  {
    type = "shortcut",
    name = names.input.make,
    action = "lua",
    associated_control_input = names.input.make,
    localised_name = "Create Toolbar",
    icons = { { icon = "__expend-toolbar__/_graphics/shortcuts/C.png", icon_size = 56 } },
    small_icons = { { icon = "__expend-toolbar__/_graphics/shortcuts/C.png", icon_size = 56 } },
  },
  {
    type = "shortcut",
    name = names.input.flip_all,
    action = "lua",
    associated_control_input = names.input.flip_all,
    localised_name = "Show or Hide Custom Bars",
    toggleable = true,
    icons = { { icon = "__expend-toolbar__/_graphics/shortcuts/T.png", icon_size = 56 } },
    small_icons = { { icon = "__expend-toolbar__/_graphics/shortcuts/T.png", icon_size = 56 } },
  },
})

local function gui_sprite(id, file, size)
  return {
    type = "sprite",
    name = id,
    filename = "__expend-toolbar__/" .. file,
    priority = "extra-high-no-scale",
    size = size or 16,
    scale = 1,
    flags = { "gui-icon" },
  }
end

data:extend({
  gui_sprite(names.sprite.add, "_graphics/icons/1.png"),
  gui_sprite(names.sprite.top, "_graphics/icons/align-start.png"),
  gui_sprite(names.sprite.bottom, "_graphics/icons/align-end.png"),
  gui_sprite(names.sprite.cancel, "_graphics/icons/cancel.png"),
  gui_sprite(names.sprite.ok, "_graphics/icons/confirm.png"),
  gui_sprite(names.sprite.open, "_graphics/icons/expand.png"),
  gui_sprite(names.sprite.up, "_graphics/icons/collapse-upward.png"),
  gui_sprite(names.sprite.down, "_graphics/icons/collapse-downward.png"),
  gui_sprite(names.sprite.tab_left, "_graphics/icons/move-up.png"),
  gui_sprite(names.sprite.tab_right, "_graphics/icons/move-down.png"),
  gui_sprite(names.sprite.lock, "_graphics/icons/padlock-closed-white.png"),
  gui_sprite(names.sprite.unlock, "_graphics/icons/padlock-open-white.png"),
  gui_sprite(names.sprite.blank, "_graphics/icons/empty.png", 64),
})

styles.expend_toolbar_button = {
  type = "button_style",
  parent = "frame_button",
  size = 20,
  left_click_sound = { { filename = "__core__/sound/gui-click.ogg", volume = 1 } },
}
styles.expend_toolbar_danger = {
  type = "button_style",
  parent = "red_button",
  size = 20,
}
styles.expend_toolbar_head_button = {
  type = "button_style",
  parent = "expend_toolbar_button",
}
styles.expend_toolbar_frame = {
  type = "frame_style",
  padding = 2,
  margin = 0,
  vertical_flow_style = { type = "vertical_flow_style", vertical_spacing = 2 },
}
styles.expend_toolbar_head = {
  type = "horizontal_flow_style",
  horizontal_spacing = 2,
  horizontally_stretchable = "on",
}
styles.expend_toolbar_drag = {
  type = "empty_widget_style",
  parent = "draggable_space",
  horizontally_stretchable = "on",
  vertically_stretchable = "on",
  height = 20,
  minimal_width = 50,
}
styles.expend_toolbar_tab = {
  type = "button_style",
  parent = "button",
  width = 28,
  height = 20,
  left_padding = 4,
  right_padding = 4,
  font = "default-small-bold",
}
styles.expend_toolbar_tab_on = {
  type = "button_style",
  parent = "green_button",
  width = 28,
  height = 20,
  left_padding = 4,
  right_padding = 4,
  font = "default-small-bold",
}
styles.expend_toolbar_cells = {
  type = "frame_style",
  parent = "quick_bar_inner_panel",
  padding = 0,
}
styles.expend_toolbar_slot = {
  type = "button_style",
  parent = "slot_button",
  size = 40,
}
