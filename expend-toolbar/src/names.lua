local M = {}

M.mod = "expend-toolbar"

function M.id(part)
  return M.mod .. "_" .. part
end

M.input = {
  make = M.id("create-toolbar"),
  flip_all = M.id("toggle-toolbars"),
  factoriopedia = M.id("open-factoriopedia"),
  grade_up = M.id("increase-quality"),
  grade_down = M.id("decrease-quality"),
}

M.setting = {
  wide = "columns",
  hint_keys = "show-controls-in-the-tooltip",
  vehicle_on = "show-vehicle-inventories-content",
  network_on = "show-logistic-networks-content",
}

M.sprite = {
  cancel = M.id("cancel"),
  ok = M.id("confirm"),
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
  rename = M.id("rename"),
  confirm = M.id("confirm"),
}

M.action = {
  move = "move",
  pick_page = "pick_page",
  rename_page = "rename_page",
  confirm_rename_page = "confirm_rename_page",
  cancel_rename_page = "cancel_rename_page",
  choose_item = "choose_item",
  take_item = "take_item",
}

return M
