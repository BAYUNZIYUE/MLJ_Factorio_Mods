local names = require("names")
local stock = require("stock")

local M = {}

local function setting(player, key)
  return settings.get_player_settings(player)[key].value
end

local function board(player_index)
  storage.expend_toolbar = storage.expend_toolbar or { next_id = 1 }
  storage.expend_toolbar.players = storage.expend_toolbar.players or {}
  local mine = storage.expend_toolbar.players[player_index]
  if not mine then
    mine = { shown = true, bars = {} }
    storage.expend_toolbar.players[player_index] = mine
  end
  return mine
end

local function next_bar_id()
  storage.expend_toolbar = storage.expend_toolbar or { next_id = 1, players = {} }
  local value = storage.expend_toolbar.next_id or 1
  storage.expend_toolbar.next_id = value + 1
  return value
end

local function fresh_page()
  return { title = "1", slots = {} }
end

local function fresh_bar()
  return {
    id = next_bar_id(),
    locked = false,
    folded = false,
    bottom = false,
    active = 1,
    pages = { fresh_page() },
  }
end

local function read_tags(element)
  return element and element.valid and element.tags or {}
end

local function slot_name(bar_id, position)
  return names.gui.pick .. "_" .. tostring(bar_id) .. "_" .. tostring(position)
end

local function nth_bar(state, id)
  for index, bar in ipairs(state.bars) do
    if bar.id == id then
      return bar, index
    end
  end
  return nil, nil
end

local function clamp_page(bar)
  if #bar.pages == 0 then
    bar.pages[1] = fresh_page()
  end
  if not bar.active or not bar.pages[bar.active] then
    bar.active = 1
  end
end

local function wanted_width(player, page)
  local configured = math.max(1, tonumber(setting(player, names.setting.wide)) or 10)
  local rightmost = 0
  for index, slot in pairs(page.slots) do
    if slot and slot.name and index > rightmost then
      rightmost = index
    end
  end
  return math.max(configured, rightmost)
end

local function trim_page(player, page)
  local wide = wanted_width(player, page)
  local function occupied(position)
    local slot = page.slots[position]
    return slot and slot.name
  end

  local rows = math.max(1, math.ceil(math.max(wide, 1) / wide))
  local max_slot = 0
  for index, slot in pairs(page.slots) do
    if slot and slot.name and index > max_slot then
      max_slot = index
    end
  end
  rows = math.max(1, math.ceil(math.max(max_slot, wide) / wide))

  -- 最后一格被占用时立刻追加一行，保证玩家总有继续放置的位置。
  if occupied(rows * wide) then
    rows = rows + 1
  end

  -- 只有末行空且倒数第二行末格也空，才收掉末行；连续满足就连续收。
  while rows > 1 and not occupied(rows * wide) and not occupied((rows - 1) * wide) do
    rows = rows - 1
  end

  return wide, rows
end

local function cell_text(main, name, grade)
  local count = stock.amount(main, name, grade)
  if count <= 0 then
    return ""
  end
  return tostring(count)
end

local function wanted_items(state)
  local wanted = {}
  for _, bar in ipairs(state.bars) do
    if not bar.folded then
      clamp_page(bar)
      local page = bar.pages[bar.active]
      for _, slot in pairs(page.slots) do
        if slot and slot.name and stock.item_known(slot.name) then
          wanted[slot.name] = true
        end
      end
    end
  end
  return next(wanted) and wanted or nil
end

local function hint_text(player, main, side, slot, cache)
  if not slot or not slot.name then
    return nil
  end
  local key = slot.name .. "\t" .. (slot.grade or "normal")
  if cache and cache[key] then
    return cache[key]
  end

  local lines = { { "?", { "item-name." .. slot.name }, " [", slot.grade or "normal", "]" } }
  for _, grade in ipairs(stock.grade_list(main, side, slot.name)) do
    local direct = stock.amount(main, slot.name, grade)
    local nearby = stock.amount(side, slot.name, grade)
    lines[#lines + 1] = "\n"
    lines[#lines + 1] = grade .. ": " .. tostring(direct)
    if nearby > 0 then
      lines[#lines + 1] = " + " .. tostring(nearby)
    end
  end

  if setting(player, names.setting.hint_keys) then
    lines[#lines + 1] = "\n"
    lines[#lines + 1] = { "?", { "controls.cycle-quality-up" }, " / ", { "controls.cycle-quality-down" } }
  end
  if cache then
    cache[key] = lines
  end
  return lines
end

local function item_sprite(name)
  if prototypes.item[name] then
    return "item/" .. name
  end
  if prototypes.fluid[name] then
    return "fluid/" .. name
  end
  return names.sprite.blank
end

local function draw_slot(parent, player, bar, page, position, main, side, hint_cache)
  local slot = page.slots[position]
  if slot and slot.name and not stock.item_known(slot.name) then
    page.slots[position] = nil
    slot = nil
  end

  if slot and slot.name then
    parent.add {
      type = "sprite-button",
      name = slot_name(bar.id, position),
      sprite = item_sprite(slot.name),
      number = tonumber(cell_text(main, slot.name, slot.grade)) or nil,
      tooltip = hint_text(player, main, side, slot, hint_cache),
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.take_item, bar = bar.id, pos = position },
      mouse_button_filter = { "left", "right", "middle" },
      raise_hover_events = true,
    }
  else
    parent.add {
      type = "choose-elem-button",
      name = slot_name(bar.id, position),
      elem_type = "item-with-quality",
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.choose_item, bar = bar.id, pos = position },
    }
  end
end

local function draw_cells(container, player, bar, page, main, side, hint_cache)
  local wide, rows = trim_page(player, page)
  for y = 1, rows do
    local line = container.add { type = "flow", direction = "horizontal" }
    line.style.horizontal_spacing = 0
    for x = 1, wide do
      draw_slot(line, player, bar, page, (y - 1) * wide + x, main, side, hint_cache)
    end
  end
end

local function redraw_bar(player, order, bar, main, side, hint_cache)
  clamp_page(bar)
  local page = bar.pages[bar.active]

  local frame = player.gui.screen.add {
    type = "frame",
    name = names.gui.bar .. "_" .. tostring(bar.id),
    direction = "vertical",
    style = "expend_toolbar_frame",
    tags = { mod = names.mod, act = names.action.move, bar = bar.id },
  }
  frame.auto_center = false
  if bar.place then
    frame.location = bar.place
  else
    frame.location = { 24, 48 + (order - 1) * 56 }
  end

  local head = frame.add { type = "flow", direction = "horizontal", style = "expend_toolbar_head" }
  local drag = head.add {
    type = "empty-widget",
    style = "expend_toolbar_drag",
    tags = { mod = names.mod, act = names.action.move, bar = bar.id },
  }
  if not bar.locked then
    drag.drag_target = frame
  end

  head.add {
    type = "sprite-button",
    sprite = bar.locked and names.sprite.lock or names.sprite.unlock,
    style = "expend_toolbar_head_button",
    tags = { mod = names.mod, act = names.action.lock_bar, bar = bar.id },
  }
  head.add {
    type = "sprite-button",
    sprite = bar.folded and names.sprite.open or (bar.bottom and names.sprite.down or names.sprite.up),
    style = "expend_toolbar_head_button",
    tags = { mod = names.mod, act = names.action.fold_bar, bar = bar.id },
  }
  head.add {
    type = "sprite-button",
    sprite = bar.bottom and names.sprite.top or names.sprite.bottom,
    style = "expend_toolbar_head_button",
    tags = { mod = names.mod, act = names.action.flip_side, bar = bar.id },
  }

  if not bar.folded then
    local tabs = frame.add { type = "flow", direction = "horizontal" }
    tabs.style.horizontal_spacing = 1
    for index, each in ipairs(bar.pages) do
      tabs.add {
        type = "button",
        caption = each.title or tostring(index),
        style = index == bar.active and "expend_toolbar_tab_on" or "expend_toolbar_tab",
        tags = { mod = names.mod, act = names.action.pick_page, bar = bar.id, page = index },
      }
    end
    tabs.add {
      type = "sprite-button",
      sprite = names.sprite.add,
      style = "expend_toolbar_head_button",
      tags = { mod = names.mod, act = names.action.add_page, bar = bar.id },
    }
    tabs.add {
      type = "sprite-button",
      sprite = "utility/trash",
      style = "expend_toolbar_danger",
      tags = { mod = names.mod, act = names.action.erase_page, bar = bar.id },
    }

    local cells = frame.add { type = "frame", direction = "vertical", style = "expend_toolbar_cells" }
    draw_cells(cells, player, bar, page, main, side, hint_cache)
  end
end

function M.ensure_storage()
  storage.expend_toolbar = storage.expend_toolbar or { next_id = 1, players = {} }
  storage.expend_toolbar.players = storage.expend_toolbar.players or {}
  storage.expend_toolbar.next_id = storage.expend_toolbar.next_id or 1
end

function M.new_toolbar(player)
  local state = board(player.index)
  state.bars[#state.bars + 1] = fresh_bar()
  M.paint(player)
end

function M.paint(player)
  M.ensure_storage()
  for _, child in pairs(player.gui.screen.children) do
    local tag = read_tags(child)
    if tag.mod == names.mod then
      child.destroy()
    end
  end

  local state = board(player.index)
  if state.shown == false or #state.bars == 0 then
    return
  end

  local wanted = wanted_items(state)
  local main, side = {}, {}
  if wanted then
    main, side = stock.snapshot(player, wanted)
  end
  local hint_cache = {}
  for order, bar in ipairs(state.bars) do
    redraw_bar(player, order, bar, main, side, hint_cache)
  end
end

function M.paint_all()
  for _, player in pairs(game.connected_players) do
    M.paint(player)
  end
end

function M.has_visible_bars(player)
  M.ensure_storage()
  local state = storage.expend_toolbar.players[player.index]
  return state and state.shown ~= false and #state.bars > 0
end

function M.needs_polling(player)
  M.ensure_storage()
  local state = storage.expend_toolbar.players[player.index]
  if not state or state.shown == false or not wanted_items(state) then
    return false
  end
  if player.controller_type == defines.controllers.remote then
    return true
  end
  local values = settings.get_player_settings(player)
  return values[names.setting.network_on].value and state.focus ~= nil
end

local function update_element(player, state, element, main, side, hint_cache)
  local tag = read_tags(element)
  if tag.mod == names.mod and tag.act == names.action.take_item then
    local bar = nth_bar(state, tag.bar)
    local page = bar and bar.pages[bar.active or 1] or nil
    local slot = page and page.slots[tag.pos] or nil
    if slot and slot.name and stock.item_known(slot.name) then
      element.number = tonumber(cell_text(main, slot.name, slot.grade)) or nil
      element.tooltip = hint_text(player, main, side, slot, hint_cache)
    end
  end
  for _, child in pairs(element.children or {}) do
    update_element(player, state, child, main, side, hint_cache)
  end
end

function M.refresh(player)
  M.ensure_storage()
  local state = storage.expend_toolbar.players[player.index]
  if not state or state.shown == false or #state.bars == 0 then
    return
  end
  local wanted = wanted_items(state)
  if not wanted then
    return
  end
  local main, side = stock.snapshot(player, wanted)
  local hint_cache = {}
  local touched = false
  for _, child in pairs(player.gui.screen.children) do
    local tag = read_tags(child)
    if tag.mod == names.mod then
      touched = true
      update_element(player, state, child, main, side, hint_cache)
    end
  end
  if not touched then
    M.paint(player)
  end
end

function M.toggle_all(player)
  local state = board(player.index)
  state.shown = not state.shown
  player.set_shortcut_toggled(names.input.flip_all, state.shown)
  M.paint(player)
end

local function cursor_item(player)
  local stack = player.cursor_stack
  if stack and stack.valid_for_read and stack.type == "item" then
    return { name = stack.name, grade = stack.quality and stack.quality.name or "normal" }
  end
  local ghost = player.cursor_ghost
  if ghost and ghost.name then
    return { name = ghost.name.name or ghost.name, grade = ghost.quality and ghost.quality.name or "normal" }
  end
  return nil
end

function M.place_cursor(player)
  local picked = cursor_item(player)
  if not picked then
    return
  end
  local state = board(player.index)
  if #state.bars == 0 then
    state.bars[1] = fresh_bar()
  end
  local bar = state.bars[#state.bars]
  clamp_page(bar)
  local page = bar.pages[bar.active]
  local wide, rows = trim_page(player, page)
  page.slots[wide * rows] = picked
  M.paint(player)
end

function M.handle_click(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod then
    return
  end

  local state = board(player.index)
  local bar = nth_bar(state, tag.bar)
  if not bar then
    return
  end
  clamp_page(bar)
  local page = bar.pages[bar.active]

  if tag.act == names.action.lock_bar then
    bar.locked = not bar.locked
  elseif tag.act == names.action.fold_bar then
    bar.folded = not bar.folded
  elseif tag.act == names.action.flip_side then
    bar.bottom = not bar.bottom
  elseif tag.act == names.action.add_page then
    bar.pages[#bar.pages + 1] = fresh_page()
    bar.active = #bar.pages
  elseif tag.act == names.action.pick_page then
    bar.active = tag.page
  elseif tag.act == names.action.erase_page then
    table.remove(bar.pages, bar.active)
    clamp_page(bar)
  elseif tag.act == names.action.take_item then
    if event.button == defines.mouse_button_type.right then
      page.slots[tag.pos] = nil
    elseif page.slots[tag.pos] then
      M.take(player, page.slots[tag.pos])
    end
  end

  M.paint(player)
end

function M.remember_hover(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod or tag.act ~= names.action.take_item then
    return
  end
  local state = board(player.index)
  state.focus = { bar = tag.bar, pos = tag.pos }
  local bar = nth_bar(state, tag.bar)
  local page = bar and bar.pages[bar.active or 1] or nil
  local slot = page and page.slots[tag.pos] or nil
  if slot and slot.name then
    -- 普通视图物流网络只影响提示，悬停时即时刷新这一格即可。
    local main, side = stock.snapshot(player, { [slot.name] = true })
    event.element.number = tonumber(cell_text(main, slot.name, slot.grade)) or nil
    event.element.tooltip = hint_text(player, main, side, slot, {})
  end
end

function M.forget_hover(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod or tag.act ~= names.action.take_item then
    return
  end
  local state = board(player.index)
  if state.focus and state.focus.bar == tag.bar and state.focus.pos == tag.pos then
    state.focus = nil
  end
end

function M.remember_place(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod or tag.act ~= names.action.move then
    return
  end
  local state = board(player.index)
  local bar = nth_bar(state, tag.bar)
  if bar then
    bar.place = event.element.location
  end
end

function M.handle_choice(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod or tag.act ~= names.action.choose_item then
    return
  end
  local value = event.element.elem_value
  if not value then
    return
  end
  local state = board(player.index)
  local bar = nth_bar(state, tag.bar)
  if not bar then
    return
  end
  clamp_page(bar)
  local page = bar.pages[bar.active]
  page.slots[tag.pos] = { name = value.name, grade = value.quality or "normal" }
  event.element.elem_value = nil
  M.paint(player)
end

function M.adjust_grade(player, step)
  local state = board(player.index)
  local focus = state.focus
  local bar = focus and nth_bar(state, focus.bar) or nil
  local page = bar and bar.pages[bar.active or 1] or nil
  local slot = page and page.slots[focus.pos] or nil
  if slot and slot.name then
    slot.grade = step > 0 and stock.raise_grade(slot.grade) or stock.lower_grade(slot.grade)
    M.paint(player)
  end
end

local function focused_slot(player)
  local state = board(player.index)
  local focus = state.focus
  local bar = focus and nth_bar(state, focus.bar) or nil
  local page = bar and bar.pages[bar.active or 1] or nil
  return page, focus and focus.pos, page and focus and page.slots[focus.pos] or nil
end

function M.clear_focused(player)
  local page, position, slot = focused_slot(player)
  if page and position and slot then
    page.slots[position] = nil
    M.paint(player)
  end
end

function M.open_focused_factoriopedia(player)
  local _, _, slot = focused_slot(player)
  if slot and slot.name and stock.item_known(slot.name) then
    player.open_factoriopedia_gui(stock.item_known(slot.name))
  end
end

function M.take(player, slot)
  if not slot or not slot.name then
    return
  end
  if player.cursor_stack and player.cursor_stack.valid_for_read then
    return
  end
  if stock.lift_to_cursor(player, slot) then
    player.play_sound { path = "utility/inventory_click" }
    return
  end
  player.cursor_ghost = { name = slot.name, quality = slot.grade or "normal" }
  player.play_sound { path = "utility/cannot_build" }
end

return M
