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
  { type = "custom-input", name = names.input.factoriopedia, linked_game_control = "open-factoriopedia", key_sequence = "" },
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
  gui_sprite(names.sprite.cancel, "_graphics/icons/cancel.png"),
  gui_sprite(names.sprite.ok, "_graphics/icons/confirm.png"),
  gui_sprite(names.sprite.blank, "_graphics/icons/empty.png", 64),
})

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
  vertical_align = "center",
}
styles.expend_toolbar_title = {
  type = "label_style",
  parent = "heading_2_label",
  width = 90,
  single_line = true,
}
styles.expend_toolbar_page = {
  type = "frame_style",
  parent = "inside_shallow_frame",
  padding = 0,
  vertical_flow_style = { type = "vertical_flow_style", vertical_spacing = 2 },
}
styles.expend_toolbar_slot_table = {
  type = "table_style",
  horizontal_spacing = 0,
  vertical_spacing = 0,
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
styles.expend_toolbar_slot_box = {
  type = "empty_widget_style",
  size = 40,
}
styles.expend_toolbar_quality_box = {
  type = "horizontal_flow_style",
  width = 36,
  height = 38,
  left_padding = 4,
  bottom_padding = 2,
  horizontal_align = "left",
  vertical_align = "bottom",
}
styles.expend_toolbar_quality = {
  type = "image_style",
  size = 15,
  stretch_image_to_widget_size = true,
}
