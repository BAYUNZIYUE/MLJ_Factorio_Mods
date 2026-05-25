local M = {}

M.mod = "expend-toolbar"

function M.id(part)
  return M.mod .. "_" .. part
end

M.input = {
  make = M.id("create-toolbar"),
  flip_all = M.id("toggle-toolbars"),
  fold_header = M.id("toggle-toolbar-header"),
  pipette = M.id("pipette"),
  clear = M.id("toggle-filter"),
  factoriopedia = M.id("open-factoriopedia"),
  grade_up = M.id("increase-quality"),
  grade_down = M.id("decrease-quality"),
}

M.setting = {
  wide = "columns",
  hint_wait = "tooltip-delay",
  hint_step = "tooltip-refresh-interval",
  hint_keys = "show-controls-in-the-tooltip",
  body_step = "character-inventories-content-refresh-interval",
  vehicle_on = "show-vehicle-inventories-content",
  vehicle_step = "vehicle-inventories-content-refresh-interval",
  network_on = "show-logistic-networks-content",
  network_step = "logistic-networks-content-refresh-interval",
}

M.sprite = {
  add = M.id("1"),
  top = M.id("align-toolbar-top"),
  bottom = M.id("align-toolbar-bottom"),
  cancel = M.id("cancel"),
  ok = M.id("confirm"),
  open = M.id("expand"),
  up = M.id("collapse-upward"),
  down = M.id("collapse-downward"),
  tab_left = M.id("move-section-up"),
  tab_right = M.id("move-section-down"),
  lock = M.id("padlock-closed"),
  unlock = M.id("padlock-open"),
  blank = M.id("empty"),
}

M.gui = {
  root = M.id("root"),
  bar = M.id("bar"),
  head = M.id("head"),
  body = M.id("body"),
  pages = M.id("pages"),
  cells = M.id("cells"),
  pick = M.id("pick"),
}

M.action = {
  move = "move",
  add_bar = "add_bar",
  add_page = "add_page",
  pick_page = "pick_page",
  erase_page = "erase_page",
  rename_page = "rename_page",
  lock_bar = "lock_bar",
  fold_bar = "fold_bar",
  flip_side = "flip_side",
  choose_item = "choose_item",
  take_item = "take_item",
  clear_item = "clear_item",
}

return M
