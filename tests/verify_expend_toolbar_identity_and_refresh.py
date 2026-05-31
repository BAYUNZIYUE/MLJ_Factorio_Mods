#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = ROOT / "expend-toolbar"
SRC = MOD_ROOT / "src"
ALLOWED_SRC_ROOT_FILES = {
    "changelog.txt",
    "control.lua",
    "data-final-fixes.lua",
    "data.lua",
    "info.json",
    "names.lua",
    "panel.lua",
    "runtime.lua",
    "settings.lua",
    "stock.lua",
    "thumbnail.png",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_contains(path: Path, text: str) -> None:
    content = read(path)
    if text not in content:
        raise AssertionError(f"{path.relative_to(ROOT)} must contain: {text}")


def assert_not_contains(path: Path, text: str) -> None:
    content = read(path)
    if text in content:
        raise AssertionError(f"{path.relative_to(ROOT)} must not contain: {text}")


def main() -> int:
    info = json.loads(read(SRC / "info.json"))
    if info["name"] != "expend-toolbar":
        raise AssertionError("expend-toolbar/src/info.json name must stay expend-toolbar")
    if "ten fixed pages" not in info["description"]:
        raise AssertionError("expend-toolbar/src/info.json description must include a concise English summary")
    if "10 个固定页面" not in info["description"]:
        raise AssertionError("expend-toolbar/src/info.json description must include a concise Chinese summary")

    if not (MOD_ROOT / "README.md").is_file() or not (MOD_ROOT / "AGENTS.md").is_file():
        raise AssertionError("expend-toolbar must keep root README.md and AGENTS.md")

    if (SRC / "src").exists():
        raise AssertionError("expend-toolbar runtime modules must not be nested under src/src")

    removed_files = [
        SRC / "locale/en/AzeretMono-Regular.ttf",
        SRC / "locale/en/OFL.txt",
        SRC / "locale/en/info.json",
        SRC / "data/fonts.lua",
        SRC / "control/remote.lua",
        SRC / "factorio/events/controls/Craft.lua",
        SRC / "factorio/events/controls/Pick.lua",
        SRC / "factorio/events/general/Tick.lua",
        SRC / "factorio/events/gui/Click.lua",
        SRC / "factorio/events/settings/PlayerSettingChanged.lua",
        SRC / "gui/toolbar/header/Lock.lua",
        SRC / "gui/toolbar/header/ToolbarHeaderButton.lua",
        SRC / "gui/toolbar/header/OneSectionMode.lua",
        SRC / "gui/toolbar/content/sections/section/header/DeleteSection.lua",
        SRC / "gui/toolbar/content/sections/section/header/SectionHeaderButton.lua",
        SRC / "_graphics/icons/padlock-closed-black.png",
        SRC / "_graphics/icons/padlock-open-black.png",
    ]
    for path in removed_files:
        if path.exists():
            raise AssertionError(f"{path.relative_to(ROOT)} should stay removed")

    root_files = {path.name for path in SRC.iterdir() if path.is_file()}
    unexpected_root_files = root_files - ALLOWED_SRC_ROOT_FILES
    if unexpected_root_files:
        formatted = ", ".join(sorted(unexpected_root_files))
        raise AssertionError(f"expend-toolbar/src root has unexpected files: {formatted}")

    removed_dirs = [
        SRC / "control",
        SRC / "core",
        SRC / "data",
        SRC / "factorio",
        SRC / "gui",
        SRC / "lang",
        SRC / "model",
        SRC / "player",
        SRC / "settings",
    ]
    for path in removed_dirs:
        if path.exists():
            raise AssertionError(f"{path.relative_to(ROOT)} should stay removed after the runtime rewrite")

    for path in SRC.rglob("*"):
        if path.is_file() and path.suffix in {".lua", ".json", ".cfg"}:
            assert_not_contains(path, "toolbars-mod")
            assert_not_contains(path, "__toolbars-mod__")
            assert_not_contains(path, 'require("src.')
            assert_not_contains(path, "require('src.")
            assert_not_contains(path, "Toolbars")
            assert_not_contains(path, "EventBus")
            assert_not_contains(path, "extendAs")
            assert_not_contains(path, "import(")
            assert_not_contains(path, "ToolbarHeader")
            assert_not_contains(path, "SectionHeader")
            assert_not_contains(path, "QualitySprite")
            assert_not_contains(path, "ViewInventory")
            assert_not_contains(path, "addRowWhenTailFilled")
            assert_not_contains(path, "removeIdleTailRows")
            assert_not_contains(path, "tailHasThing")
            assert_not_contains(path, "tooltip-delay")
            assert_not_contains(path, "tooltip-refresh-interval")
            assert_not_contains(path, "character-inventories-content-refresh-interval")
            assert_not_contains(path, "vehicle-inventories-content-refresh-interval")
            assert_not_contains(path, "logistic-networks-content-refresh-interval")
            assert_not_contains(path, "toggle-filter")

    assert_contains(SRC / "names.lua", 'M.mod = "expend-toolbar"')
    assert_contains(SRC / "names.lua", 'wide = "columns"')
    assert_contains(SRC / "names.lua", 'pipette = M.id("pipette")')
    assert_not_contains(SRC / "names.lua", 'make = M.id("create-toolbar")')
    assert_not_contains(SRC / "names.lua", 'add_bar = "add_bar"')
    assert_not_contains(SRC / "data.lua", "name = names.input.make")
    assert_not_contains(SRC / "data.lua", "associated_control_input = names.input.make")
    assert_not_contains(SRC / "data.lua", "Create Toolbar")
    assert_not_contains(SRC / "data.lua", "names.sprite.add")
    assert_contains(SRC / "settings.lua", "default_value = 10")
    setting_text = read(SRC / "settings.lua")
    if setting_text.count('setting_type = "runtime-per-user"') != 4:
        raise AssertionError("expend-toolbar should keep exactly four runtime-per-user settings")
    assert_contains(SRC / "locale/en/locale.cfg", "[mod-name]")
    assert_contains(SRC / "locale/en/locale.cfg", "expend-toolbar=Expend Toolbar")
    assert_contains(SRC / "locale/en/locale.cfg", "[mod-description]")
    assert_contains(SRC / "locale/zh-CN/locale.cfg", "expend-toolbar=扩展工具栏")
    assert_contains(SRC / "locale/en/locale.cfg", "ten fixed pages")
    assert_contains(SRC / "locale/zh-CN/locale.cfg", "10 个固定页面")
    assert_not_contains(SRC / "changelog.txt", "Version: 2.")
    assert_not_contains(SRC / "changelog.txt", "Toolbars")
    assert_contains(SRC / "stock.lua", "附近物流网络只作为提示列，不参与槽位主数字")
    assert_contains(SRC / "stock.lua", "远程星球视图没有玩家背包语义")
    assert_contains(SRC / "panel.lua", "最后一格被占用时立刻追加一行")
    assert_contains(SRC / "panel.lua", "倒数第二行末格也空")
    assert_contains(SRC / "panel.lua", "return math.max(1, tonumber(setting(player, names.setting.wide)) or 10)")
    assert_not_contains(SRC / "panel.lua", "return math.max(configured, rightmost)")
    assert_contains(SRC / "stock.lua", "inventory.get_item_quality_counts(name)")
    assert_contains(SRC / "stock.lua", "network.get_item_count({ name = name, quality = grade })")
    assert_contains(SRC / "stock.lua", "local function quality_order()")
    assert_contains(SRC / "stock.lua", "local function quality_rank()")
    assert_contains(SRC / "stock.lua", "local function wanted_names(wanted)")
    assert_contains(SRC / "stock.lua", "directed_queries <= 96")
    assert_contains(SRC / "panel.lua", "local function wanted_items(state)")
    assert_contains(SRC / "panel.lua", "raise_hover_events = true")
    assert_contains(SRC / "panel.lua", 'local lines = { "",')
    assert_not_contains(SRC / "panel.lua", 'local lines = { { "?"')
    assert_contains(SRC / "panel.lua", "local PAGE_COUNT = 10")
    assert_contains(SRC / "panel.lua", "for index = 1, PAGE_COUNT do")
    assert_contains(SRC / "panel.lua", "local function draw_page_buttons(parent, player, bar)")
    assert_contains(SRC / "panel.lua", 'caption = tostring(index)')
    assert_contains(SRC / "panel.lua", 'style = index == bar.active and "slot_sized_button_blue" or "slot_sized_button"')
    assert_not_contains(SRC / "panel.lua", "selected_slot_button")
    assert_not_contains(SRC / "panel.lua", 'type = "tabbed-pane"')
    assert_not_contains(SRC / "panel.lua", "tabs.add_tab(tab, content)")
    assert_not_contains(SRC / "panel.lua", "selected_tab_index")
    assert_contains(SRC / "panel.lua", "local function toolbar_rows(player, bar)")
    assert_contains(SRC / "panel.lua", 'type = "table"')
    assert_contains(SRC / "panel.lua", "column_count = wide")
    assert_contains(SRC / "panel.lua", 'style = "draggable_space"')
    assert_contains(SRC / "panel.lua", "drag.drag_target = frame")
    assert_not_contains(SRC / "panel.lua", "local function text_width(text)")
    assert_not_contains(SRC / "panel.lua", "local function trim_text(text, max_width)")
    assert_not_contains(SRC / "panel.lua", "local function tab_width(player, page, index)")
    assert_not_contains(SRC / "panel.lua", "local function tab_window(player, bar, wide)")
    assert_not_contains(SRC / "panel.lua", "local function draw_page_picker(parent, player, bar, tab_start, tab_end)")
    assert_contains(SRC / "panel.lua", "drag.style.size = { math.max(40, wide * 40 - 152), 20 }")
    assert_not_contains(SRC / "panel.lua", "tab.style.width")
    assert_not_contains(SRC / "panel.lua", "local available = math.max(80, wide * 40 - 80)")
    assert_not_contains(SRC / "panel.lua", "tabs.style.width")
    assert_not_contains(SRC / "panel.lua", "local function draw_page_prompt(player, frame, bar)")
    assert_not_contains(SRC / "panel.lua", "chooser_name(bar.id)")
    assert_not_contains(SRC / "panel.lua", "names.action.open_page_chooser")
    assert_not_contains(SRC / "panel.lua", 'type = "drop-down"')
    assert_not_contains(SRC / "panel.lua", "selected_index = bar.active")
    assert_not_contains(SRC / "panel.lua", "bar.tab_start")
    assert_not_contains(SRC / "panel.lua", "names.action.previous_pages")
    assert_not_contains(SRC / "panel.lua", "names.action.next_pages")
    assert_not_contains(SRC / "panel.lua", "names.action.select_page")
    assert_contains(SRC / "panel.lua", "if tag.act == names.action.move then")
    assert_contains(SRC / "panel.lua", 'type = "sprite-button"')
    assert_contains(SRC / "panel.lua", "sprite = names.sprite.blank")
    assert_not_contains(SRC / "panel.lua", "创建新分组")
    assert_not_contains(SRC / "panel.lua", "删除当前分组")
    assert_not_contains(SRC / "panel.lua", "add_head_button(")
    assert_not_contains(SRC / "panel.lua", 'tags = { mod = names.mod, act = names.action.move, bar = bar.id },\n  }\n  drag.drag_target = frame')
    assert_not_contains(SRC / "panel.lua", "head.drag_target = frame")
    assert_not_contains(SRC / "panel.lua", "names.action.lock_bar")
    assert_not_contains(SRC / "panel.lua", "names.action.fold_bar")
    assert_not_contains(SRC / "panel.lua", "names.action.flip_side")
    assert_not_contains(SRC / "runtime.lua", "fold_header")
    assert_contains(SRC / "panel.lua", "local function sync_cursor_state(player, state)")
    assert_not_contains(SRC / "panel.lua", "local function cursor_holds(player, slot)")
    assert_not_contains(SRC / "panel.lua", "not cursor_holds(player, state.moving.slot)")
    assert_contains(SRC / "panel.lua", "if state.copying and not cursor_slot(player) then")
    assert_contains(SRC / "panel.lua", "function M.sync_cursor(player)")
    assert_contains(SRC / "runtime.lua", "panel.sync_cursor(player)")
    assert_contains(SRC / "panel.lua", "state.moving = { bar = tag.bar, page = tag.page or bar.active, pos = tag.pos, slot = picked }")
    assert_contains(SRC / "panel.lua", "state.copying = { slot = clone_slot(slot) }")
    assert_contains(SRC / "panel.lua", "clear_moved_source(state, state.moving)")
    assert_contains(SRC / "panel.lua", "local function clear_copy_state(state)")
    assert_contains(SRC / "panel.lua", "local function carried_slot(player, state)")
    assert_contains(SRC / "panel.lua", 'return clone_slot(state.copying.slot), "copy"')
    assert_contains(SRC / "panel.lua", "local function clear_cursor(player)")
    assert_contains(SRC / "panel.lua", "player.clear_cursor()")
    assert_contains(SRC / "panel.lua", "player.cursor_ghost = nil")
    assert_contains(SRC / "panel.lua", "local function set_cursor_ghost(player, slot)")
    assert_contains(SRC / "panel.lua", "local function ghost_slot(player)")
    assert_contains(SRC / "panel.lua", "local function cursor_slot(player)")
    assert_contains(SRC / "panel.lua", "local function place_carried_slot(player, state, tag, page)")
    assert_contains(SRC / "panel.lua", "elseif moving or state.copying or cursor_slot(player) then")
    assert_contains(SRC / "panel.lua", 'style = chosen and "expend_toolbar_slot_selected" or "expend_toolbar_slot"')
    assert_contains(SRC / "panel.lua", "elseif not state.moving and cursor_slot(player) then")
    assert_contains(SRC / "panel.lua", "elseif tag.act == names.action.choose_item and (state.moving or cursor_slot(player)) then")
    assert_contains(SRC / "panel.lua", "function M.copy_focused_to_cursor(player)")
    assert_contains(SRC / "runtime.lua", "panel.copy_focused_to_cursor(player)")
    assert_contains(SRC / "panel.lua", "mouse_button_filter = { \"left\" }")
    assert_contains(SRC / "panel.lua", "redraw_bar(player, order, bar, main, side, hint_cache, state.moving)")
    assert_contains(SRC / "panel.lua", "event.button == defines.mouse_button_type.right or event.button == defines.mouse_button_type.middle")
    assert_contains(SRC / "panel.lua", "local function edge_place(player, place, width, height)")
    assert_contains(SRC / "panel.lua", "local function frame_size(player, bar)")
    assert_contains(SRC / "panel.lua", "local function first_place(player, width, height)")
    assert_contains(SRC / "panel.lua", "math.floor((screen_w - display_w) / 2)")
    assert_contains(SRC / "panel.lua", "math.floor(screen_h - display_h)")
    assert_contains(SRC / "panel.lua", "function M.ensure_default(player)")
    assert_contains(SRC / "panel.lua", "player.set_shortcut_toggled(names.input.flip_all, state.shown ~= false)")
    assert_contains(SRC / "panel.lua", "复刻旧模组窗口逻辑")
    assert_not_contains(SRC / "panel.lua", "local function clamp_place(player, place, width, height)")
    assert_contains(SRC / "panel.lua", "local resolution = player.display_resolution")
    assert_contains(SRC / "panel.lua", "state.snap[bar.id] = { tick = event.tick or game.tick, stable = 0, last = bar.place }")
    assert_contains(SRC / "panel.lua", "if (snap.stable or 0) >= 8 then")
    assert_contains(SRC / "panel.lua", "function M.snap_moved_bars()")
    assert_contains(SRC / "runtime.lua", "panel.snap_moved_bars()")
    assert_not_contains(SRC / "panel.lua", "event.element.location = bar.place")
    assert_contains(SRC / "panel.lua", "return true")
    assert_not_contains(SRC / "panel.lua", "function M.handle_tab_changed(event)")
    assert_not_contains(SRC / "panel.lua", "function M.handle_selection(event)")
    assert_contains(SRC / "panel.lua", "function M.handle_confirmed(event)")
    assert_contains(SRC / "panel.lua", "bar.rename = tag.page")
    assert_not_contains(SRC / "panel.lua", "names.action.confirm_erase_page")
    assert_contains(SRC / "panel.lua", 'style = "green_button"')
    assert_contains(SRC / "panel.lua", 'style = "red_button"')
    assert_contains(SRC / "panel.lua", "caption = ui_text(player, \"重命名分组\", \"Rename group\")")
    assert_not_contains(SRC / "panel.lua", "caption = ui_text(player, \"删除页面\", \"Delete page\")")
    assert_contains(SRC / "panel.lua", "local function quality_icon(grade)")
    assert_contains(SRC / "panel.lua", "local function short_count(count)")
    assert_contains(SRC / "panel.lua", "local function dim_text(value)")
    assert_contains(SRC / "panel.lua", 'return "[quality=" .. normalize_grade(grade) .. "]"')
    assert_not_contains(SRC / "locale/zh-CN/locale.cfg", "create-group=创建新分组")
    assert_not_contains(SRC / "locale/en/locale.cfg", "create-group=Create new group")
    assert_contains(SRC / "panel.lua", "function M.save_rename(player, bar, page_index, text)")
    assert_contains(SRC / "panel.lua", 'grade == "quality-unknown"')
    assert_contains(SRC / "panel.lua", "local function quality_sprite(grade)")
    assert_contains(SRC / "panel.lua", 'return names.mod .. "_quality_" .. quality.name')
    assert_contains(SRC / "stock.lua", 'quality == "quality-unknown"')
    assert_contains(SRC / "stock.lua", "local normal = prototypes.quality.normal")
    assert_contains(SRC / "stock.lua", 'current == "normal" and normal and normal.next and step > 0')
    assert_not_contains(SRC / "data.lua", 'type = "tabbed_pane_style"')
    assert_contains(SRC / "data.lua", 'type = "table_style"')
    assert_contains(SRC / "data.lua", 'styles.expend_toolbar_quality')
    assert_contains(SRC / "data.lua", "styles.expend_toolbar_slot_selected")
    assert_contains(SRC / "panel.lua", "main, side = stock.snapshot(player, wanted)")
    assert_contains(SRC / "panel.lua", "redraw_bar(player, order, bar, main, side, hint_cache, state.moving)")
    assert_contains(SRC / "panel.lua", "function M.has_visible_bars(player)")
    assert_contains(SRC / "panel.lua", "function M.forget_hover(event)")
    assert_contains(SRC / "runtime.lua", "local watched_settings = {")
    assert_contains(SRC / "runtime.lua", "local function refresh_now(player)")
    assert_contains(SRC / "runtime.lua", "local function repaint_dirty()")
    assert_contains(SRC / "runtime.lua", "local function mark_polling_players()")
    assert_contains(SRC / "runtime.lua", "panel.ensure_default(player)")
    assert_contains(SRC / "runtime.lua", "panel.refresh(player)")
    assert_contains(SRC / "runtime.lua", "refresh_now(player_of(event))")
    assert_contains(SRC / "runtime.lua", "defines.events.on_gui_leave")
    assert_not_contains(SRC / "runtime.lua", "defines.events.on_gui_selected_tab_changed")
    assert_not_contains(SRC / "runtime.lua", "defines.events.on_gui_selection_state_changed")
    assert_contains(SRC / "runtime.lua", "defines.events.on_gui_confirmed")
    assert_contains(SRC / "runtime.lua", "defines.events.on_tick")
    assert_not_contains(SRC / "runtime.lua", "script.on_nth_tick(30, function()")
    assert_not_contains(SRC / "runtime.lua", "event.input_name == names.input.make")
    assert_not_contains(SRC / "runtime.lua", "event.prototype_name == names.input.make")
    assert_contains(MOD_ROOT / "README.md", "ten fixed numbered pages")
    assert_contains(MOD_ROOT / "README.md", "10 个数字页面")
    assert_contains(MOD_ROOT / "README.md", "starts near the bottom center")
    assert_contains(MOD_ROOT / "README.md", "默认出现在屏幕底部中间")
    assert_not_contains(MOD_ROOT / "README.md", "`Create a toolbar`")
    assert_not_contains(MOD_ROOT / "README.md", "Create a toolbar")
    assert_not_contains(MOD_ROOT / "README.md", "header arrows or page selector")
    assert_not_contains(MOD_ROOT / "README.md", "标题栏箭头或页面选择器")
    assert_contains(MOD_ROOT / "README.md", "Middle-click or right-click a slot to clear it.")
    assert_contains(MOD_ROOT / "README.md", "中键或右键点击物品槽可以清空槽位。")
    assert_contains(SRC / "runtime.lua", "if not panel.has_visible_bars(player) then")
    assert_not_contains(SRC / "runtime.lua", "script.on_nth_tick(30, repaint_connected)")
    assert_not_contains(SRC / "runtime.lua", "panel.paint_all()")

    print("PASS: expend-toolbar was rewritten into a compact non-compatible runtime layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
