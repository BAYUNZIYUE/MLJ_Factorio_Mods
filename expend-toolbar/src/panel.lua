local names = require("names")
local stock = require("stock")

local M = {}
local PAGE_COUNT = 10

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
  return { slots = {} }
end

local function fresh_bar()
  local bar = {
    id = next_bar_id(),
    active = 1,
    pages = {},
  }
  for index = 1, PAGE_COUNT do
    bar.pages[index] = fresh_page()
  end
  return bar
end

local function read_tags(element)
  return element and element.valid and element.tags or {}
end

local function slot_name(bar_id, position)
  return names.gui.pick .. "_" .. tostring(bar_id) .. "_" .. tostring(position)
end

local function rename_name(bar_id)
  return names.gui.rename .. "_" .. tostring(bar_id)
end

local function normalize_grade(grade)
  if type(grade) == "table" then
    grade = grade.name
  end
  if not grade or grade == "" or grade == "quality-unknown" or not prototypes.quality[grade] then
    return "normal"
  end
  return grade
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
  bar.pages = bar.pages or {}
  for index = 1, PAGE_COUNT do
    if not bar.pages[index] then
      bar.pages[index] = fresh_page()
    end
  end
  for index = #bar.pages, PAGE_COUNT + 1, -1 do
    if bar.pages[index] and bar.pages[index].slots then
      for position, slot in pairs(bar.pages[index].slots) do
        if slot and slot.name then
          local target = ((index - 1) % PAGE_COUNT) + 1
          bar.pages[target].slots[position] = bar.pages[target].slots[position] or slot
        end
      end
    end
    bar.pages[index] = nil
  end
  if not bar.active or bar.active < 1 or bar.active > PAGE_COUNT then
    bar.active = 1
  end
end

local function wanted_width(player)
  return math.max(1, tonumber(setting(player, names.setting.wide)) or 10)
end

local function trim_page(player, page)
  local wide = wanted_width(player)
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

local function page_title(player, page, index)
  if page.title and page.title ~= "" then
    return page.title
  end
  local locale = player.locale or ""
  if string.sub(locale, 1, 2) == "zh" then
    return "分组" .. tostring(index)
  end
  return "Group " .. tostring(index)
end

local function toolbar_rows(player, bar)
  local wide = wanted_width(player)
  local rows = 1
  for _, page in ipairs(bar.pages) do
    local _, page_rows = trim_page(player, page)
    rows = math.max(rows, page_rows)
  end
  return wide, rows
end

local function ui_text(player, zh, en)
  local locale = player and player.locale or ""
  if string.sub(locale, 1, 2) == "zh" then
    return zh
  end
  return en
end

local function cell_text(main, name, grade)
  local count = stock.amount(main, name, normalize_grade(grade))
  if count <= 0 then
    return ""
  end
  return tostring(count)
end

local function quality_icon(grade)
  return "[quality=" .. normalize_grade(grade) .. "]"
end

local function short_count(count)
  count = tonumber(count) or 0
  local suffixes = { "", "k", "M", "G", "T", "P" }
  local index = 1
  while count >= 1000 and index < #suffixes do
    count = count / 1000
    index = index + 1
  end
  if index == 1 then
    return string.format("%4.3g", count)
  end
  if count < 10 then
    return string.format("%3.1f%s", math.floor(count * 10) / 10, suffixes[index])
  end
  return string.format("%3d%s", math.floor(count), suffixes[index])
end

local function dim_text(value)
  return "[color=0.7,0.7,0.7]" .. value .. "[/color]"
end

local function wanted_items(state)
  local wanted = {}
  for _, bar in ipairs(state.bars) do
    clamp_page(bar)
    for _, page in ipairs(bar.pages) do
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
  slot.grade = normalize_grade(slot.grade)
  local key = slot.name .. "\t" .. slot.grade
  if cache and cache[key] then
    return cache[key]
  end

  local lines = { "", { "?", { "item-name." .. slot.name }, slot.name }, " ", quality_icon(slot.grade) }
  local grades = stock.grade_list(main, side, slot.name)
  for index = #grades, 1, -1 do
    local grade = grades[index]
    local direct = stock.amount(main, slot.name, grade)
    local nearby = stock.amount(side, slot.name, grade)
    lines[#lines + 1] = "\n"
    local direct_text = short_count(direct) .. quality_icon(grade)
    if grade ~= slot.grade then
      direct_text = dim_text(direct_text)
    end
    lines[#lines + 1] = direct_text
    if nearby > 0 then
      lines[#lines + 1] = " "
      lines[#lines + 1] = dim_text("+" .. short_count(nearby) .. quality_icon(grade))
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

local function quality_sprite(grade)
  local quality = prototypes.quality[normalize_grade(grade)]
  if not quality or not quality.draw_sprite_by_default then
    return nil
  end
  return names.mod .. "_quality_" .. quality.name
end

local function clone_slot(slot)
  if not slot or not slot.name then
    return nil
  end
  return { name = slot.name, grade = normalize_grade(slot.grade) }
end

local function same_slot(a, b)
  return a and b and a.name == b.name and normalize_grade(a.grade) == normalize_grade(b.grade)
end

local function same_place(mark, bar_id, page_index, position)
  return mark and mark.bar == bar_id and mark.page == page_index and mark.pos == position
end

local function cursor_busy(player)
  local stack = player.cursor_stack
  return (stack and stack.valid_for_read) or player.cursor_ghost ~= nil
end

local function cursor_holds(player, slot)
  local stack = player.cursor_stack
  if stack and stack.valid_for_read and stack.type == "item" then
    return same_slot({ name = stack.name, grade = stack.quality }, slot)
  end
  local ghost = player.cursor_ghost
  if ghost and ghost.name then
    return same_slot({ name = ghost.name.name or ghost.name, grade = ghost.quality }, slot)
  end
  return false
end

local function screen_size(player)
  local resolution = player.display_resolution or { width = 1920, height = 1080 }
  return resolution.width or 1920, resolution.height or 1080
end

local function edge_place(player, place, width, height)
  place = place or { x = 24, y = 48 }
  local x = place.x or place[1] or 24
  local y = place.y or place[2] or 48
  local screen_w, screen_h = screen_size(player)
  local scale = player.display_scale or 1
  width = math.floor((width or 420) * scale)
  height = math.floor((height or 180) * scale)
  x = math.floor(x)
  y = math.floor(y)

  -- 复刻旧模组窗口逻辑：越过边界时贴到对应边，不在正常范围内反复改写坐标。
  if width > screen_w then
    x = math.floor(screen_w - width)
  elseif x <= 0 then
    x = 0
  elseif x + width >= screen_w then
    x = math.floor(screen_w - width)
  end

  if height > screen_h then
    y = 0
  elseif y <= 0 then
    y = 0
  elseif y + height >= screen_h then
    y = math.floor(screen_h - height)
  end

  return { x = x, y = y }
end

local function clear_moved_source(state, mark)
  if not mark then
    return
  end
  local source_bar = nth_bar(state, mark.bar)
  local source_page = source_bar and source_bar.pages[mark.page] or nil
  local source_slot = source_page and source_page.slots[mark.pos] or nil
  if source_page and same_slot(source_slot, mark.slot) then
    source_page.slots[mark.pos] = nil
  end
end

local function clear_cursor(player)
  player.clear_cursor()
  player.cursor_ghost = nil
end

local function draw_slot(parent, player, bar, page, page_index, position, main, side, hint_cache, moving)
  local slot = page.slots[position]
  if slot and slot.name and not stock.item_known(slot.name) then
    page.slots[position] = nil
    slot = nil
  end

  local cell = parent.add { type = "empty-widget", style = "expend_toolbar_slot_box" }
  if slot and slot.name then
    cell.add {
      type = "sprite-button",
      name = slot_name(bar.id, position),
      sprite = item_sprite(slot.name),
      number = tonumber(cell_text(main, slot.name, normalize_grade(slot.grade))) or nil,
      tooltip = hint_text(player, main, side, slot, hint_cache),
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.take_item, bar = bar.id, page = page_index, pos = position },
      mouse_button_filter = { "left", "right", "middle" },
      raise_hover_events = true,
    }
    local quality = quality_sprite(slot.grade)
    if quality then
      local overlay = cell.add {
        type = "flow",
        direction = "horizontal",
        style = "expend_toolbar_quality_box",
        ignored_by_interaction = true,
      }
      overlay.add {
        type = "sprite",
        sprite = quality,
        style = "expend_toolbar_quality",
        ignored_by_interaction = true,
      }
    end
  elseif moving then
    cell.add {
      type = "sprite-button",
      name = slot_name(bar.id, position),
      sprite = names.sprite.blank,
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.choose_item, bar = bar.id, page = page_index, pos = position },
      mouse_button_filter = { "left" },
    }
  else
    cell.add {
      type = "choose-elem-button",
      name = slot_name(bar.id, position),
      elem_type = "item-with-quality",
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.choose_item, bar = bar.id, page = page_index, pos = position },
    }
  end
end

local function draw_cells(container, player, bar, page, page_index, rows, main, side, hint_cache, moving)
  local wide = wanted_width(player)
  local table_box = container.add {
    type = "table",
    column_count = wide,
    style = "expend_toolbar_slot_table",
  }
  for position = 1, wide * rows do
    draw_slot(table_box, player, bar, page, page_index, position, main, side, hint_cache, moving)
  end
end

local function draw_rename_prompt(player, frame, bar)
  if not bar.rename then
    return
  end
  local page = bar.pages[bar.rename]
  if not page then
    bar.rename = nil
    return
  end
  local location = frame.location or { x = 40, y = 40 }
  local x = location.x or location[1] or 40
  local y = location.y or location[2] or 40
  local prompt = player.gui.screen.add {
    type = "frame",
    direction = "vertical",
    name = rename_name(bar.id),
    caption = ui_text(player, "重命名分组", "Rename group"),
    tags = { mod = names.mod, act = names.action.cancel_rename_page, bar = bar.id, page = bar.rename },
  }
  prompt.auto_center = false
  prompt.location = { x + 28, y + 48 }
  local input = prompt.add {
    type = "textfield",
    text = page_title(player, page, bar.rename),
    lose_focus_on_confirm = true,
    tags = { mod = names.mod, act = names.action.confirm_rename_page, bar = bar.id, page = bar.rename },
  }
  input.focus()
  input.select_all()
  local buttons = prompt.add { type = "flow", direction = "horizontal" }
  buttons.style.horizontal_spacing = 8
  local ok = buttons.add {
    type = "sprite-button",
    sprite = names.sprite.ok,
    style = "green_button",
    tooltip = ui_text(player, "确认重命名", "Confirm rename"),
    tags = { mod = names.mod, act = names.action.confirm_rename_page, bar = bar.id, page = bar.rename },
  }
  ok.style.width = 28
  ok.style.height = 28
  local cancel = buttons.add {
    type = "sprite-button",
    sprite = names.sprite.cancel,
    style = "red_button",
    tooltip = ui_text(player, "取消", "Cancel"),
    tags = { mod = names.mod, act = names.action.cancel_rename_page, bar = bar.id, page = bar.rename },
  }
  cancel.style.width = 28
  cancel.style.height = 28
end

local function draw_page_buttons(parent, player, bar)
  local table_box = parent.add { type = "table", column_count = PAGE_COUNT }
  table_box.style.horizontal_spacing = 0
  table_box.style.vertical_spacing = 0
  for index = 1, PAGE_COUNT do
    local button = table_box.add {
      type = "button",
      caption = tostring(index),
      tooltip = page_title(player, bar.pages[index], index),
      style = index == bar.active and "slot_sized_button_blue" or "slot_sized_button",
      tags = { mod = names.mod, act = names.action.pick_page, bar = bar.id, page = index },
      mouse_button_filter = { "left" },
    }
    button.style.width = 40
    button.style.height = 32
  end
end

local function redraw_bar(player, order, bar, main, side, hint_cache, moving)
  clamp_page(bar)
  local wide, rows = toolbar_rows(player, bar)

  local frame = player.gui.screen.add {
    type = "frame",
    name = names.gui.bar .. "_" .. tostring(bar.id),
    direction = "vertical",
    style = "expend_toolbar_frame",
    tags = { mod = names.mod, act = names.action.move, bar = bar.id },
  }
  frame.auto_center = false
  local frame_w = wide * 40 + 150
  local frame_h = rows * 40 + 150
  if bar.place then
    frame.location = edge_place(player, bar.place, frame_w, frame_h)
  else
    frame.location = edge_place(player, { 24, 48 + (order - 1) * 56 }, frame_w, frame_h)
  end

  local head = frame.add { type = "flow", direction = "horizontal", style = "expend_toolbar_head" }
  head.add {
    type = "label",
    caption = { "mod-name." .. names.mod },
    style = "expend_toolbar_title",
  }
  local drag = head.add {
    type = "empty-widget",
    style = "draggable_space",
  }
  drag.drag_target = frame
  drag.style.size = { math.max(40, wide * 40 - 152), 20 }

  local content = frame.add { type = "frame", direction = "vertical", style = "expend_toolbar_page" }
  local cells = content.add { type = "frame", direction = "vertical", style = "expend_toolbar_cells" }
  draw_cells(cells, player, bar, bar.pages[bar.active], bar.active, rows, main, side, hint_cache, moving)
  draw_page_buttons(content, player, bar)
  draw_rename_prompt(player, frame, bar)
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
    redraw_bar(player, order, bar, main, side, hint_cache, state.moving)
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
    local page = bar and bar.pages[tag.page or bar.active or 1] or nil
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

function M.handle_click(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod then
    return
  end
  if tag.act == names.action.move then
    return
  end

  local state = board(player.index)
  if state.moving and not cursor_holds(player, state.moving.slot) then
    state.moving = nil
  end
  local bar = nth_bar(state, tag.bar)
  if not bar then
    return
  end
  clamp_page(bar)
  local page = bar.pages[tag.page or bar.active]
  local changed = false

  if tag.act == names.action.pick_page and tag.page then
    bar.active = tag.page
    local last = state.last_tab_click
    if last and last.bar == tag.bar and last.page == tag.page and event.tick - last.tick <= 30 then
      bar.rename = tag.page
      state.last_tab_click = nil
    else
      state.last_tab_click = { bar = tag.bar, page = tag.page, tick = event.tick }
    end
    changed = true
  elseif tag.act == names.action.confirm_rename_page then
    M.save_rename(player, bar, tag.page)
    return
  elseif tag.act == names.action.cancel_rename_page then
    bar.rename = nil
    changed = true
  elseif tag.act == names.action.take_item then
    if event.button == defines.mouse_button_type.right or event.button == defines.mouse_button_type.middle then
      page.slots[tag.pos] = nil
      if same_place(state.moving, tag.bar, tag.page or bar.active, tag.pos) then
        state.moving = nil
      end
      changed = true
    elseif state.moving and not same_place(state.moving, tag.bar, tag.page or bar.active, tag.pos) then
      page.slots[tag.pos] = clone_slot(state.moving.slot)
      clear_moved_source(state, state.moving)
      clear_cursor(player)
      state.moving = nil
      changed = true
    elseif page.slots[tag.pos] then
      local picked = clone_slot(page.slots[tag.pos])
      if not cursor_busy(player) and M.take(player, picked) then
        state.moving = { bar = tag.bar, page = tag.page or bar.active, pos = tag.pos, slot = picked }
        changed = true
      end
    end
  elseif tag.act == names.action.choose_item and state.moving then
    page.slots[tag.pos] = clone_slot(state.moving.slot)
    clear_moved_source(state, state.moving)
    clear_cursor(player)
    state.moving = nil
    changed = true
  end

  if changed then
    M.paint(player)
  end
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
  state.focus = { bar = tag.bar, page = tag.page, pos = tag.pos }
  local bar = nth_bar(state, tag.bar)
  local page = bar and bar.pages[tag.page or bar.active or 1] or nil
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
  if state.focus and state.focus.bar == tag.bar and state.focus.page == tag.page and state.focus.pos == tag.pos then
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
  if state.moving and not cursor_holds(player, state.moving.slot) then
    state.moving = nil
  end
  local bar = nth_bar(state, tag.bar)
  if bar then
    local wide, rows = toolbar_rows(player, bar)
    bar.place = edge_place(player, event.element.location, wide * 40 + 150, rows * 40 + 150)
    event.element.location = bar.place
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
  local page = bar.pages[tag.page or bar.active]
  local picked = { name = value.name, grade = normalize_grade(value.quality) }
  page.slots[tag.pos] = picked
  if state.moving and not same_place(state.moving, tag.bar, tag.page or bar.active, tag.pos) and same_slot(picked, state.moving.slot) then
    clear_moved_source(state, state.moving)
    clear_cursor(player)
    state.moving = nil
  end
  event.element.elem_value = nil
  M.paint(player)
end

function M.save_rename(player, bar, page_index, text)
  local page = bar and bar.pages[page_index or bar.rename or bar.active]
  if not page then
    return
  end
  if text == nil then
    local prompt = player.gui.screen[rename_name(bar.id)]
    if prompt and prompt.valid then
      for _, child in pairs(prompt.children) do
        if child.valid and child.type == "textfield" then
          text = child.text
          break
        end
      end
    end
  end
  text = text or ""
  page.title = text ~= "" and text or nil
  bar.rename = nil
  M.paint(player)
end

function M.handle_confirmed(event)
  local player = game.get_player(event.player_index)
  if not player then
    return
  end
  local tag = read_tags(event.element)
  if tag.mod ~= names.mod or tag.act ~= names.action.confirm_rename_page then
    return
  end
  local state = board(player.index)
  local bar = nth_bar(state, tag.bar)
  local page = bar and bar.pages[tag.page] or nil
  if page then
    M.save_rename(player, bar, tag.page, event.element.text)
  end
end

function M.adjust_grade(player, step)
  local state = board(player.index)
  local focus = state.focus
  local bar = focus and nth_bar(state, focus.bar) or nil
  local page = bar and bar.pages[focus.page or bar.active or 1] or nil
  local slot = page and page.slots[focus.pos] or nil
  if slot and slot.name then
    local grade = normalize_grade(slot.grade)
    slot.grade = step > 0 and stock.raise_grade(grade) or stock.lower_grade(grade)
    M.paint(player)
  end
end

local function focused_slot(player)
  local state = board(player.index)
  local focus = state.focus
  local bar = focus and nth_bar(state, focus.bar) or nil
  local page = bar and bar.pages[focus.page or bar.active or 1] or nil
  return page, focus and focus.pos, page and focus and page.slots[focus.pos] or nil
end

function M.open_focused_factoriopedia(player)
  local _, _, slot = focused_slot(player)
  if slot and slot.name and stock.item_known(slot.name) then
    player.open_factoriopedia_gui(stock.item_known(slot.name))
  end
end

function M.take(player, slot)
  if not slot or not slot.name then
    return false
  end
  if player.cursor_stack and player.cursor_stack.valid_for_read then
    return false
  end
  if stock.lift_to_cursor(player, slot) then
    player.play_sound { path = "utility/inventory_click" }
    return true
  end
  player.cursor_ghost = { name = slot.name, quality = normalize_grade(slot.grade) }
  player.play_sound { path = "utility/cannot_build" }
  return true
end

return M
