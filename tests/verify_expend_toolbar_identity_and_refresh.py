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
    if "Create movable custom item bars" not in info["description"]:
        raise AssertionError("expend-toolbar/src/info.json description must include a concise English summary")
    if "创建可移动的自定义物品栏" not in info["description"]:
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

    assert_contains(SRC / "names.lua", 'M.mod = "expend-toolbar"')
    assert_contains(SRC / "names.lua", 'wide = "columns"')
    assert_contains(SRC / "settings.lua", "default_value = 10")
    setting_text = read(SRC / "settings.lua")
    if setting_text.count('setting_type = "runtime-per-user"') != 4:
        raise AssertionError("expend-toolbar should keep exactly four runtime-per-user settings")
    assert_contains(SRC / "locale/en/locale.cfg", "[mod-name]")
    assert_contains(SRC / "locale/en/locale.cfg", "expend-toolbar=Expend Toolbar")
    assert_contains(SRC / "locale/en/locale.cfg", "[mod-description]")
    assert_contains(SRC / "locale/zh-CN/locale.cfg", "expend-toolbar=扩展工具栏")
    assert_contains(SRC / "locale/zh-CN/locale.cfg", "创建可移动的自定义物品栏")
    assert_not_contains(SRC / "changelog.txt", "Version: 2.")
    assert_not_contains(SRC / "changelog.txt", "Toolbars")
    assert_contains(SRC / "stock.lua", "附近物流网络只作为提示列，不参与槽位主数字")
    assert_contains(SRC / "stock.lua", "远程星球视图没有玩家背包语义")
    assert_contains(SRC / "panel.lua", "最后一格被占用时立刻追加一行")
    assert_contains(SRC / "panel.lua", "倒数第二行末格也空")
    assert_contains(SRC / "stock.lua", "inventory.get_item_quality_counts(name)")
    assert_contains(SRC / "stock.lua", "network.get_item_count({ name = name, quality = grade })")
    assert_contains(SRC / "stock.lua", "local function quality_order()")
    assert_contains(SRC / "stock.lua", "local function quality_rank()")
    assert_contains(SRC / "stock.lua", "local function wanted_names(wanted)")
    assert_contains(SRC / "stock.lua", "directed_queries <= 96")
    assert_contains(SRC / "panel.lua", "local function wanted_items(state)")
    assert_contains(SRC / "panel.lua", "raise_hover_events = true")
    assert_contains(SRC / "panel.lua", "main, side = stock.snapshot(player, wanted)")
    assert_contains(SRC / "panel.lua", "redraw_bar(player, order, bar, main, side, hint_cache)")
    assert_contains(SRC / "panel.lua", "function M.has_visible_bars(player)")
    assert_contains(SRC / "panel.lua", "function M.forget_hover(event)")
    assert_contains(SRC / "runtime.lua", "local watched_settings = {")
    assert_contains(SRC / "runtime.lua", "local function refresh_now(player)")
    assert_contains(SRC / "runtime.lua", "local function repaint_dirty()")
    assert_contains(SRC / "runtime.lua", "local function mark_polling_players()")
    assert_contains(SRC / "runtime.lua", "panel.refresh(player)")
    assert_contains(SRC / "runtime.lua", "refresh_now(player_of(event))")
    assert_contains(SRC / "runtime.lua", "defines.events.on_gui_leave")
    assert_contains(SRC / "runtime.lua", "if not panel.has_visible_bars(player) then")
    assert_contains(SRC / "runtime.lua", "script.on_nth_tick(30, function()")
    assert_not_contains(SRC / "runtime.lua", "script.on_nth_tick(30, repaint_connected)")
    assert_not_contains(SRC / "runtime.lua", "panel.paint_all()")

    print("PASS: expend-toolbar was rewritten into a compact non-compatible runtime layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
