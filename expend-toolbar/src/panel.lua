local names = require("names")
local stock = require("stock")

local M = {}
local SLOT_SIZE = 40
local PAGE_TITLE_MIN_WIDTH = 72
local SNAP_QUIET_TICKS = 20

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
  return { id = next_bar_id(), active = 1, pages = { fresh_page() } }
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

local function delete_name(bar_id)
  return names.gui.confirm .. "_delete_" .. tostring(bar_id)
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

local function safe_value(reader)
  local ok, value = pcall(reader)
  if ok then
    return value
  end
  return nil
end

local function record_item_name(record_type)
  if record_type == "blueprint" then
    return "blueprint"
  end
  if record_type == "blueprint-book" then
    return "blueprint-book"
  end
  if record_type == "deconstruction-planner" then
    return "deconstruction-planner"
  end
  if record_type == "upgrade-planner" then
    return "upgrade-planner"
  end
  return nil
end

local function record_label(record)
  return safe_value(function() return record.blueprint_description end)
end

local function record_entity_count(record)
  return safe_value(function() return record.get_blueprint_entity_count() end)
end

local function record_active_index(player, record)
  return safe_value(function() return record.get_active_index(player) end)
end

local function record_contents_size(record)
  return safe_value(function() return record.contents_size end)
end

local function record_export(record)
  return safe_value(function() return record.export_record() end)
end

local function nth_bar(state, id)
  for index, bar in ipairs(state.bars) do
    if bar.id == id then
      return bar, index
    end
  end
  return nil, nil
end

local function wanted_width(player)
  return math.max(1, tonumber(setting(player, names.setting.wide)) or 10)
end

local function max_pages(player)
  return wanted_width(player)
end

local function clamp_page(player, bar)
  bar.pages = bar.pages or {}
  if #bar.pages == 0 then
    bar.pages[1] = fresh_page()
  end
  local limit = player and max_pages(player) or #bar.pages
  for index = #bar.pages, limit + 1, -1 do
    local overflow = bar.pages[index]
    if overflow and overflow.slots then
      for position, slot in pairs(overflow.slots) do
        if slot and slot.name and not bar.pages[limit].slots[position] then
          bar.pages[limit].slots[position] = slot
        end
      end
    end
    bar.pages[index] = nil
  end
  for _, page in ipairs(bar.pages) do
    page.slots = page.slots or {}
  end
  if not bar.active or bar.active < 1 or bar.active > #bar.pages then
    bar.active = 1
  end
  if bar.rename and (bar.rename < 1 or bar.rename > #bar.pages) then
    bar.rename = nil
  end
  if bar.deleting and (bar.deleting < 1 or bar.deleting > #bar.pages) then
    bar.deleting = nil
  end
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

local function page_rows(player, page)
  local _, rows = trim_page(player, page)
  return rows
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
  local page = bar.pages[bar.active or 1] or bar.pages[1] or fresh_page()
  local rows = page_rows(player, page)
  return wide, rows
end

local function page_button_width(wide, page_count)
  return math.max(SLOT_SIZE, math.floor((math.max(1, wide) * SLOT_SIZE) / math.max(1, page_count)))
end

local function toolbar_body_width(wide, page_count)
  return math.max(math.max(1, wide) * SLOT_SIZE, page_button_width(wide, page_count) * math.max(1, page_count))
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

local function rich_icon(name)
  if prototypes.fluid[name] then
    return "[fluid=" .. name .. "]"
  end
  return "[item=" .. name .. "]"
end

local function wanted_items(state, player)
  local wanted = {}
  for _, bar in ipairs(state.bars) do
    clamp_page(player, bar)
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

local function add_detail_line(lines, label, value)
  if value == nil or value == "" then
    return
  end
  lines[#lines + 1] = "\n"
  lines[#lines + 1] = dim_text(label .. ": " .. tostring(value))
end

local function add_item_details(lines, slot)
  local prototype = prototypes.item[slot.name] or prototypes.fluid[slot.name]
  add_detail_line(lines, "name", slot.name)
  add_detail_line(lines, "kind", slot.kind or "item")
  if prototype then
    add_detail_line(lines, "type", safe_value(function() return prototype.type end))
    add_detail_line(lines, "stack", safe_value(function() return prototype.stack_size end))
    local place_result = safe_value(function() return prototype.place_result and prototype.place_result.name end)
    local place_tile = safe_value(function() return prototype.place_as_tile and prototype.place_as_tile.result and prototype.place_as_tile.result.name end)
    add_detail_line(lines, "place", place_result or place_tile)
    add_detail_line(lines, "fuel", safe_value(function() return prototype.fuel_category end))
    add_detail_line(lines, "module", safe_value(function() return prototype.category end))
  end
  add_detail_line(lines, "label", slot.label)
  add_detail_line(lines, "record", slot.record_type)
  add_detail_line(lines, "entities", slot.entity_count)
  add_detail_line(lines, "book index", slot.active_index)
  add_detail_line(lines, "book size", slot.contents_size)
  add_detail_line(lines, "export", slot.data and "saved" or nil)
end

local function stack_label(stack)
  return safe_value(function() return stack.label end)
end

local function stack_export(stack)
  return safe_value(function() return stack.export_stack() end)
end

local function stack_entity_count(stack)
  return safe_value(function() return stack.get_blueprint_entity_count() end)
end

local function stack_active_index(stack)
  return safe_value(function() return stack.get_active_index() end)
end

local function slot_from_stack(stack)
  if not stack or not stack.valid_for_read or not stack.name then
    return nil
  end
  local slot = {
    kind = "item",
    name = stack.name,
    grade = normalize_grade(stack.quality),
  }
  if safe_value(function() return stack.is_blueprint end)
      or safe_value(function() return stack.is_blueprint_book end)
      or safe_value(function() return stack.is_deconstruction_item end)
      or safe_value(function() return stack.is_upgrade_item end)
      or safe_value(function() return stack.is_item_with_tags end) then
    slot.kind = "exported-stack"
    slot.data = stack_export(stack)
    slot.label = stack_label(stack)
    slot.entity_count = stack_entity_count(stack)
    slot.active_index = stack_active_index(stack)
  end
  return slot
end

local function slot_from_record(player, record, include_data)
  if not record or record.valid == false then
    return nil
  end
  local record_type = safe_value(function() return record.type end)
  local name = record_item_name(record_type)
  if not name then
    return nil
  end
  local slot = {
    kind = "record",
    name = name,
    grade = "normal",
    record_type = record_type,
    label = record_label(record),
    entity_count = record_entity_count(record),
    active_index = record_active_index(player, record),
    contents_size = record_contents_size(record),
  }
  if include_data then
    slot.data = record_export(record)
  end
  return slot
end

local function hint_text(player, main, side, slot, cache)
  if not slot or not slot.name then
    return nil
  end
  slot.grade = normalize_grade(slot.grade)
  local key = table.concat({
    slot.name,
    slot.grade,
    slot.kind or "",
    slot.data or "",
    slot.record_type or "",
    slot.label or "",
    tostring(slot.entity_count or ""),
    tostring(slot.active_index or ""),
    tostring(slot.contents_size or ""),
  }, "\t")
  if cache and cache[key] then
    return cache[key]
  end

  local lines = { rich_icon(slot.name) .. " " .. slot.name .. " " .. quality_icon(slot.grade) }
  local grades = stock.grade_list(main, side, slot.name)
  for index = #grades, 1, -1 do
    local grade = grades[index]
    local direct = stock.amount(main, slot.name, grade)
    local nearby = stock.amount(side, slot.name, grade)
    local direct_text = short_count(direct) .. quality_icon(grade)
    if grade ~= slot.grade then
      direct_text = dim_text(direct_text)
    end
    lines[#lines + 1] = "\n" .. direct_text
    if nearby > 0 then
      lines[#lines] = lines[#lines] .. " " .. dim_text("+" .. short_count(nearby) .. quality_icon(grade))
    end
  end
  add_item_details(lines, slot)

  if setting(player, names.setting.hint_keys) then
    lines[#lines + 1] = "\n" .. dim_text("cycle-quality-up / cycle-quality-down")
  end
  local text = table.concat(lines)
  if cache then
    cache[key] = text
  end
  return text
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
  return {
    kind = slot.kind or "item",
    name = slot.name,
    grade = normalize_grade(slot.grade),
    data = slot.data,
    label = slot.label,
    record_type = slot.record_type,
    entity_count = slot.entity_count,
    active_index = slot.active_index,
    contents_size = slot.contents_size,
  }
end

local function clone_slots(slots)
  local copy = {}
  for index, slot in pairs(slots or {}) do
    copy[index] = clone_slot(slot)
  end
  return copy
end

local function same_slot(a, b)
  return a and b and a.name == b.name and normalize_grade(a.grade) == normalize_grade(b.grade) and (a.data or "") == (b.data or "")
end

local function same_named_slot(a, b)
  return a and b and a.name == b.name and normalize_grade(a.grade) == normalize_grade(b.grade)
end

local function slot_from_elem_value(value)
  if type(value) == "string" then
    return { kind = "item", name = value, grade = "normal" }
  end
  if value and value.name then
    return { kind = "item", name = value.name, grade = normalize_grade(value.quality) }
  end
  return nil
end

local function slot_row(player, position)
  local wide = wanted_width(player)
  return math.max(1, math.ceil((tonumber(position) or 1) / wide))
end

local function same_place(mark, bar_id, page_index, position)
  return mark and mark.bar == bar_id and mark.page == page_index and mark.pos == position
end

local function ghost_name(ghost)
  if not ghost or not ghost.name then
    return nil
  end
  if type(ghost.name) == "table" then
    return ghost.name.name
  end
  return ghost.name
end

local function ghost_slot(player)
  local ghost = player.cursor_ghost
  local name = ghost_name(ghost)
  if not name then
    return nil
  end
  return { name = name, grade = normalize_grade(ghost.quality) }
end

local function cursor_slot(player, include_record_data)
  local stack = safe_value(function() return player.cursor_stack end)
  local stack_slot = slot_from_stack(stack)
  if stack_slot then
    return stack_slot
  end
  local record_slot = slot_from_record(player, safe_value(function() return player.cursor_record end), include_record_data)
  if record_slot then
    return record_slot
  end
  return ghost_slot(player)
end

local function slot_from_choice(player, value)
  local basic = slot_from_elem_value(value)
  local cursor = cursor_slot(player, true)
  if same_named_slot(cursor, basic) then
    return cursor
  end
  return basic
end

local function cursor_busy(player)
  local stack = safe_value(function() return player.cursor_stack end)
  local ghost = safe_value(function() return player.cursor_ghost end)
  local record = safe_value(function() return player.cursor_record end)
  return (stack and stack.valid_for_read) or ghost ~= nil or record ~= nil
end

local function has_remote_logistic_context(player)
  if not settings.get_player_settings(player)[names.setting.network_on].value then
    return false
  end
  local networks = safe_value(function()
    return player.surface.find_logistic_networks_by_construction_area(player.position, player.force)
  end)
  return networks and #networks > 0
end

local function can_show_in_context(player)
  if player.controller_type ~= defines.controllers.remote then
    return true
  end
  local centered = safe_value(function() return player.centered_on end)
  if centered and centered.valid then
    return true
  end
  local mode = safe_value(function() return player.render_mode end)
  if mode == defines.render_mode.chart then
    -- 远程星图只显示天体/航线总览；没有聚焦实体或物流上下文时隐藏工具栏。
    return has_remote_logistic_context(player)
  end
  if safe_value(function() return player.surface.platform end) then
    return true
  end
  if safe_value(function() return player.surface.planet end) then
    return true
  end
  return has_remote_logistic_context(player)
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

local function frame_size(player, bar)
  local wide, rows = toolbar_rows(player, bar)
  -- 按当前控件树估算：外框 padding、标题行、内容框边、格子表、底部页按钮。
  return math.max(toolbar_body_width(wide, #bar.pages) + 4, 136), rows * SLOT_SIZE + 64
end

local function location_changed(a, b)
  if not a or not b then
    return true
  end
  return (a.x or a[1] or 0) ~= (b.x or b[1] or 0) or (a.y or a[2] or 0) ~= (b.y or b[2] or 0)
end

local function first_place(player, width, height)
  local screen_w, screen_h = screen_size(player)
  local scale = player.display_scale or 1
  local display_w = math.floor((width or 420) * scale)
  local display_h = math.floor((height or 180) * scale)
  return {
    x = math.floor((screen_w - display_w) / 2),
    y = math.floor(screen_h - display_h),
  }
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

local function clear_move_state(state)
  state.moving = nil
end

local function clear_copy_state(state)
  state.copying = nil
end

local function sync_cursor_state(player, state)
  local changed = false
  if state.copying and not cursor_slot(player) then
    clear_copy_state(state)
    changed = true
  end
  return changed
end

local function set_cursor_ghost(player, slot)
  if (slot.kind == "exported-stack" or slot.kind == "record") and slot.data and player.cursor_stack and player.cursor_stack.valid then
    clear_cursor(player)
    local ok, result = pcall(function() return player.cursor_stack.import_stack(slot.data) end)
    if ok and result == 0 then
      return true
    end
  end
  if slot.kind == "record" then
    if player.cursor_stack and player.cursor_stack.valid and prototypes.item[slot.name] then
      clear_cursor(player)
      if player.cursor_stack.set_stack({ name = slot.name, count = 1, quality = normalize_grade(slot.grade) }) then
        return true
      end
    end
  end
  player.cursor_ghost = { name = slot.name, quality = normalize_grade(slot.grade) }
  return true
end

local function selected_slot(state, bar_id, page_index, position, slot)
  return same_place(state.moving, bar_id, page_index, position) and same_slot(state.moving.slot, slot)
end

local function carried_slot(player, state)
  if state.moving then
    return clone_slot(state.moving.slot), "move"
  end
  if state.copying then
    return clone_slot(state.copying.slot), "copy"
  end
  return cursor_slot(player, true), "cursor"
end

local function place_carried_slot(player, state, tag, page)
  if not page then
    return false
  end
  local carried, mode = carried_slot(player, state)
  if not carried or not carried.name then
    return false
  end
  page.slots[tag.pos] = clone_slot(carried)
  if mode == "move" then
    clear_moved_source(state, state.moving)
    clear_cursor(player)
    clear_move_state(state)
  elseif mode == "copy" then
    set_cursor_ghost(player, carried)
  end
  return true
end

local function clear_page_marks(state)
  state.moving = nil
  state.copying = nil
  state.page_focus = nil
  state.row_focus = nil
  state.focus = nil
  state.last_tab_click = nil
end

local function draw_slot(parent, player, state, bar, page, page_index, position, main, side, hint_cache, moving)
  local slot = page.slots[position]
  if slot and slot.name and not stock.item_known(slot.name) then
    page.slots[position] = nil
    slot = nil
  end

  local cell = parent.add { type = "empty-widget", style = "expend_toolbar_slot_box" }
  if slot and slot.name then
    local chosen = selected_slot(state, bar.id, page_index, position, slot)
    cell.add {
      type = "sprite-button",
      name = slot_name(bar.id, position),
      sprite = item_sprite(slot.name),
      number = tonumber(cell_text(main, slot.name, normalize_grade(slot.grade))) or nil,
      tooltip = hint_text(player, main, side, slot, hint_cache),
      style = chosen and "expend_toolbar_slot_selected" or "expend_toolbar_slot",
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
  elseif moving or state.copying or cursor_slot(player) then
    cell.add {
      type = "sprite-button",
      name = slot_name(bar.id, position),
      sprite = names.sprite.blank,
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.choose_item, bar = bar.id, page = page_index, pos = position },
      mouse_button_filter = { "left" },
      raise_hover_events = true,
    }
  else
    cell.add {
      type = "choose-elem-button",
      name = slot_name(bar.id, position),
      elem_type = "item-with-quality",
      style = "expend_toolbar_slot",
      tags = { mod = names.mod, act = names.action.choose_item, bar = bar.id, page = page_index, pos = position },
      raise_hover_events = true,
    }
  end
end

local function draw_cells(container, player, state, bar, page, page_index, rows, main, side, hint_cache, moving)
  local wide = wanted_width(player)
  local table_box = container.add {
    type = "table",
    column_count = wide,
    style = "expend_toolbar_slot_table",
  }
  for position = 1, wide * rows do
    draw_slot(table_box, player, state, bar, page, page_index, position, main, side, hint_cache, moving)
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

local function draw_delete_prompt(player, frame, bar)
  if not bar.deleting then
    return
  end
  local page = bar.pages[bar.deleting]
  if not page then
    bar.deleting = nil
    return
  end
  local location = frame.location or { x = 40, y = 40 }
  local x = location.x or location[1] or 40
  local y = location.y or location[2] or 40
  local prompt = player.gui.screen.add {
    type = "frame",
    direction = "vertical",
    name = delete_name(bar.id),
    caption = ui_text(player, "删除分组", "Delete group"),
    tags = { mod = names.mod, act = names.action.cancel_delete_page, bar = bar.id, page = bar.deleting },
  }
  prompt.auto_center = false
  prompt.location = { x + 28, y + 48 }
  prompt.add {
    type = "label",
    caption = ui_text(
      player,
      "确认删除“" .. page_title(player, page, bar.deleting) .. "”？",
      "Delete \"" .. page_title(player, page, bar.deleting) .. "\"?"
    ),
  }
  local buttons = prompt.add { type = "flow", direction = "horizontal" }
  buttons.style.horizontal_spacing = 8
  local ok = buttons.add {
    type = "sprite-button",
    sprite = names.sprite.trash,
    style = "red_button",
    tooltip = ui_text(player, "确认删除", "Confirm delete"),
    tags = { mod = names.mod, act = names.action.confirm_delete_page, bar = bar.id, page = bar.deleting },
  }
  ok.style.width = 28
  ok.style.height = 28
  local cancel = buttons.add {
    type = "sprite-button",
    sprite = names.sprite.cancel,
    style = "green_button",
    tooltip = ui_text(player, "取消", "Cancel"),
    tags = { mod = names.mod, act = names.action.cancel_delete_page, bar = bar.id, page = bar.deleting },
  }
  cancel.style.width = 28
  cancel.style.height = 28
end

local function draw_page_buttons(parent, player, bar, wide)
  local page_count = math.max(1, #bar.pages)
  local button_width = page_button_width(wide, page_count)
  local show_titles = button_width >= PAGE_TITLE_MIN_WIDTH
  local table_box = parent.add { type = "table", column_count = page_count }
  table_box.style.horizontal_spacing = 0
  table_box.style.vertical_spacing = 0
  for index = 1, page_count do
    local title = page_title(player, bar.pages[index], index)
    local button = table_box.add {
      type = "button",
      caption = show_titles and title or tostring(index),
      tooltip = title,
      style = index == bar.active and "slot_sized_button_blue" or "slot_sized_button",
      tags = { mod = names.mod, act = names.action.pick_page, bar = bar.id, page = index },
      mouse_button_filter = { "left" },
      raise_hover_events = true,
    }
    button.style.width = button_width
    button.style.height = 32
  end
end

local function redraw_bar(player, order, bar, main, side, hint_cache, moving)
  clamp_page(player, bar)
  local state = board(player.index)
  local wide, rows = toolbar_rows(player, bar)

  local frame = player.gui.screen.add {
    type = "frame",
    name = names.gui.bar .. "_" .. tostring(bar.id),
    direction = "vertical",
    style = "expend_toolbar_frame",
    tags = { mod = names.mod, act = names.action.move, bar = bar.id },
  }
  frame.auto_center = false
  local frame_w, frame_h = frame_size(player, bar)
  if bar.place then
    frame.location = edge_place(player, bar.place, frame_w, frame_h)
  else
    frame.location = edge_place(player, first_place(player, frame_w, frame_h), frame_w, frame_h)
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
  drag.style.size = { math.max(40, toolbar_body_width(wide, #bar.pages) - 182), 20 }
  local add = head.add {
    type = "button",
    caption = "+",
    style = "green_button",
    tooltip = ui_text(player, "创建新分组", "Create new group"),
    tags = { mod = names.mod, act = names.action.add_page, bar = bar.id },
    mouse_button_filter = { "left" },
  }
  add.style.width = 28
  add.style.height = 28
  add.enabled = #bar.pages < max_pages(player)
  local delete = head.add {
    type = "sprite-button",
    sprite = names.sprite.trash,
    style = "red_button",
    tooltip = ui_text(player, "删除当前分组", "Delete current group"),
    tags = { mod = names.mod, act = names.action.delete_page, bar = bar.id, page = bar.active },
    mouse_button_filter = { "left" },
  }
  delete.style.width = 28
  delete.style.height = 28
  delete.enabled = #bar.pages > 1

  local content = frame.add { type = "frame", direction = "vertical", style = "expend_toolbar_page" }
  local cells = content.add { type = "frame", direction = "vertical", style = "expend_toolbar_cells" }
  draw_cells(cells, player, state, bar, bar.pages[bar.active], bar.active, rows, main, side, hint_cache, moving)
  draw_page_buttons(content, player, bar, wide)
  draw_rename_prompt(player, frame, bar)
  draw_delete_prompt(player, frame, bar)
end

function M.ensure_storage()
  storage.expend_toolbar = storage.expend_toolbar or { next_id = 1, players = {} }
  storage.expend_toolbar.players = storage.expend_toolbar.players or {}
  storage.expend_toolbar.next_id = storage.expend_toolbar.next_id or 1
end

function M.ensure_default(player)
  local state = board(player.index)
  if #state.bars == 0 then
    state.bars[#state.bars + 1] = fresh_bar()
  end
  if state.shown == nil then
    state.shown = true
  end
  player.set_shortcut_toggled(names.input.flip_all, state.shown ~= false)
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
  player.set_shortcut_toggled(names.input.flip_all, state.shown ~= false)
  if state.shown == false or #state.bars == 0 then
    return
  end
  if not can_show_in_context(player) then
    return
  end

  local wanted = wanted_items(state, player)
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
  if not state or state.shown == false or not can_show_in_context(player) or not wanted_items(state, player) then
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
  if not can_show_in_context(player) then
    M.paint(player)
    return
  end
  local wanted = wanted_items(state, player)
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

function M.sync_cursor(player)
  local state = board(player.index)
  local changed = sync_cursor_state(player, state)
  if changed then
    M.paint(player)
  end
  return changed
end

function M.toggle_all(player)
  local state = board(player.index)
  state.shown = not state.shown
  player.set_shortcut_toggled(names.input.flip_all, state.shown ~= false)
  M.paint(player)
end

function M.copy_hovered(player)
  local state = board(player.index)
  local focus = state.page_focus
  if focus then
    local bar = nth_bar(state, focus.bar)
    local page = bar and bar.pages[focus.page] or nil
    if page then
      state.clipboard = { kind = "page", slots = clone_slots(page.slots) }
      player.play_sound { path = "utility/inventory_click" }
      return true
    end
  end

  focus = state.row_focus
  if focus then
    local bar = nth_bar(state, focus.bar)
    local page = bar and bar.pages[focus.page or (bar and bar.active) or 1] or nil
    if page then
      local wide = wanted_width(player)
      local first = (focus.row - 1) * wide + 1
      local slots = {}
      for offset = 0, wide - 1 do
        slots[offset + 1] = clone_slot(page.slots[first + offset])
      end
      state.clipboard = { kind = "row", width = wide, slots = slots }
      player.play_sound { path = "utility/inventory_click" }
      return true
    end
  end
  return false
end

function M.paste_hovered(player)
  local state = board(player.index)
  local clipboard = state.clipboard
  if not clipboard then
    return false
  end

  if clipboard.kind == "page" and state.page_focus then
    local bar = nth_bar(state, state.page_focus.bar)
    local page = bar and bar.pages[state.page_focus.page] or nil
    if page then
      page.slots = clone_slots(clipboard.slots)
      player.play_sound { path = "utility/inventory_click" }
      M.paint(player)
      return true
    end
  elseif clipboard.kind == "row" and state.row_focus then
    local focus = state.row_focus
    local bar = nth_bar(state, focus.bar)
    local page = bar and bar.pages[focus.page or (bar and bar.active) or 1] or nil
    if page then
      local wide = wanted_width(player)
      local first = (focus.row - 1) * wide + 1
      for offset = 0, wide - 1 do
        page.slots[first + offset] = clone_slot(clipboard.slots[offset + 1])
      end
      player.play_sound { path = "utility/inventory_click" }
      M.paint(player)
      return true
    end
  end
  return false
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
  local bar = nth_bar(state, tag.bar)
  if not bar then
    return
  end
  clamp_page(player, bar)
  local page = bar.pages[tag.page or bar.active]
  local changed = false

  if tag.act == names.action.add_page then
    if #bar.pages < max_pages(player) then
      bar.pages[#bar.pages + 1] = fresh_page()
      bar.active = #bar.pages
      bar.rename = bar.active
      bar.deleting = nil
      clear_page_marks(state)
      changed = true
    end
  elseif tag.act == names.action.delete_page then
    if #bar.pages > 1 then
      bar.deleting = bar.active
      bar.rename = nil
      changed = true
    end
  elseif tag.act == names.action.confirm_delete_page then
    if #bar.pages > 1 then
      local target = math.min(math.max(1, tag.page or bar.active), #bar.pages)
      table.remove(bar.pages, target)
      bar.active = math.min(target, #bar.pages)
      bar.deleting = nil
      bar.rename = nil
      clear_page_marks(state)
      changed = true
    end
  elseif tag.act == names.action.cancel_delete_page then
    bar.deleting = nil
    changed = true
  elseif tag.act == names.action.pick_page and tag.page and bar.pages[tag.page] then
    bar.active = tag.page
    bar.deleting = nil
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
  elseif tag.act == names.action.take_item and page then
    if event.button == defines.mouse_button_type.right or event.button == defines.mouse_button_type.middle then
      page.slots[tag.pos] = nil
      if same_place(state.moving, tag.bar, tag.page or bar.active, tag.pos) then
        clear_move_state(state)
      end
      changed = true
    elseif state.moving and not same_place(state.moving, tag.bar, tag.page or bar.active, tag.pos) then
      place_carried_slot(player, state, tag, page)
      changed = true
    elseif not state.moving and cursor_slot(player) then
      place_carried_slot(player, state, tag, page)
      changed = true
    elseif page.slots[tag.pos] then
      local picked = clone_slot(page.slots[tag.pos])
      if not cursor_busy(player) and M.take(player, picked) then
        state.moving = { bar = tag.bar, page = tag.page or bar.active, pos = tag.pos, slot = picked }
        changed = true
      end
    end
  elseif tag.act == names.action.choose_item and page and (state.moving or cursor_slot(player)) then
    place_carried_slot(player, state, tag, page)
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
  if tag.mod ~= names.mod then
    return
  end
  local state = board(player.index)
  if tag.act == names.action.pick_page then
    state.row_focus = nil
    state.page_focus = { bar = tag.bar, page = tag.page }
    return
  end
  if tag.act ~= names.action.take_item and tag.act ~= names.action.choose_item then
    return
  end
  state.page_focus = nil
  state.row_focus = { bar = tag.bar, page = tag.page, row = slot_row(player, tag.pos) }
  if tag.act ~= names.action.take_item then
    return
  end
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
  if tag.mod ~= names.mod then
    return
  end
  local state = board(player.index)
  if tag.act == names.action.pick_page then
    if state.page_focus and state.page_focus.bar == tag.bar and state.page_focus.page == tag.page then
      state.page_focus = nil
    end
    return
  end
  if tag.act ~= names.action.take_item and tag.act ~= names.action.choose_item then
    return
  end
  local row = slot_row(player, tag.pos)
  if state.row_focus and state.row_focus.bar == tag.bar and state.row_focus.page == tag.page and state.row_focus.row == row then
    state.row_focus = nil
  end
  if tag.act ~= names.action.take_item then
    return
  end
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
  local bar = nth_bar(state, tag.bar)
  if bar then
    local location = event.element.location
    bar.place = { x = location.x or location[1] or 24, y = location.y or location[2] or 48 }
    state.snap = state.snap or {}
    state.snap[bar.id] = { tick = event.tick or game.tick }
  end
end

function M.snap_moved_bars()
  M.ensure_storage()
  for index, state in pairs(storage.expend_toolbar.players or {}) do
    local player = game.get_player(index)
    if player and player.connected and state.snap then
      local changed = false
      for bar_id, snap in pairs(state.snap) do
        local bar = nth_bar(state, bar_id)
        -- Factorio 没有 GUI 拖动释放事件；等待一段没有位置事件的静默窗口，再做一次贴边。
        if game.tick - (snap.tick or 0) >= SNAP_QUIET_TICKS then
          if bar and bar.place then
            local frame_w, frame_h = frame_size(player, bar)
            local next_place = edge_place(player, bar.place, frame_w, frame_h)
            if location_changed(next_place, bar.place) then
              bar.place = next_place
              changed = true
            end
          end
          state.snap[bar_id] = nil
        end
      end
      if changed then
        M.paint(player)
      end
    end
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
  local state = board(player.index)
  local bar = nth_bar(state, tag.bar)
  if not bar then
    return
  end
  clamp_page(player, bar)
  local page = bar.pages[tag.page or bar.active]
  local value = event.element.elem_value
  if value then
    local picked = slot_from_choice(player, value)
    if not picked or not picked.name then
      return
    end
    page.slots[tag.pos] = picked
    if state.moving and not same_place(state.moving, tag.bar, tag.page or bar.active, tag.pos) and same_slot(picked, state.moving.slot) then
      clear_moved_source(state, state.moving)
      clear_cursor(player)
      clear_move_state(state)
    end
    event.element.elem_value = nil
    M.paint(player)
  elseif place_carried_slot(player, state, tag, page) then
    M.paint(player)
  end
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
  if player.controller_type ~= defines.controllers.remote and slot.kind == "item" and stock.lift_to_cursor(player, slot) then
    player.play_sound { path = "utility/inventory_click" }
    return true
  end
  set_cursor_ghost(player, slot)
  player.play_sound { path = "utility/cannot_build" }
  return true
end

function M.copy_focused_to_cursor(player)
  local state = board(player.index)
  if state.moving then
    clear_move_state(state)
    clear_copy_state(state)
    clear_cursor(player)
    M.paint(player)
    return
  end
  if state.copying then
    clear_copy_state(state)
    clear_cursor(player)
    M.paint(player)
    return
  end
  local _, _, slot = focused_slot(player)
  if not slot or not slot.name then
    clear_copy_state(state)
    clear_move_state(state)
    return
  end
  clear_move_state(state)
  clear_cursor(player)
  state.copying = { slot = clone_slot(slot) }
  set_cursor_ghost(player, state.copying.slot)
  player.play_sound { path = "utility/inventory_click" }
  M.paint(player)
end

return M
