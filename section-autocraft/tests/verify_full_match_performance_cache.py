#!/usr/bin/env python3
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
AUTOCRAFT = ROOT / "src" / "autocraft.lua"
CONTROL = ROOT / "src" / "control.lua"


def assert_contains(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.S):
        raise AssertionError(message)


def assert_ordered(text: str, first: str, second: str, message: str) -> None:
    first_index = text.find(first)
    second_index = text.find(second)
    if first_index < 0 or second_index < 0 or first_index > second_index:
        raise AssertionError(message)


def assert_ordered_after(text: str, anchor: str, first: str, second: str, message: str) -> None:
    anchor_index = text.find(anchor)
    if anchor_index < 0:
        raise AssertionError(message)

    assert_ordered(text[anchor_index:], first, second, message)


def main() -> int:
    autocraft_text = AUTOCRAFT.read_text(encoding="utf-8")
    control_text = CONTROL.read_text(encoding="utf-8")

    try:
        assert_contains(
            r"request_cache_dirty = true",
            autocraft_text,
            "FAIL: 玩家数据必须默认把物流请求缓存标记为 dirty。",
        )
        assert_contains(
            r"local function mark_sections_dirty\(player\).*?"
            r"data\.request_cache_dirty = true.*?"
            r"data\.requested_items_cache = nil.*?"
            r"data\.section_status_dirty = true",
            autocraft_text,
            "FAIL: mark_sections_dirty 必须同时失效请求缓存和状态快照。",
        )
        assert_contains(
            r"function autocraft\.mark_sections_dirty\(player\)",
            autocraft_text,
            "FAIL: control.lua 需要可调用的编组缓存失效入口。",
        )
        assert_contains(
            r"local function build_requested_items\(player\)",
            autocraft_text,
            "FAIL: 全量扫描物流编组的逻辑必须和缓存读取入口分离。",
        )
        assert_contains(
            r"local function get_requested_items\(player\).*?"
            r"not data\.request_cache_dirty and data\.requested_items_cache.*?"
            r"return data\.requested_items_cache.*?"
            r"build_requested_items\(player\)",
            autocraft_text,
            "FAIL: get_requested_items 必须优先复用缓存，避免背包变化时全量扫编组。",
        )
        assert_contains(
            r"if not data\.section_status_dirty and trigger_mode ~= \"shortcut\" then\s+return\s+end",
            autocraft_text,
            "FAIL: 30 tick 状态同步必须在无 dirty 标记时快速返回。",
        )
        assert_contains(
            r"local function get_crafting_queue_item_counts\(player\).*?"
            r"queued_counts\[product\.name\]",
            autocraft_text,
            "FAIL: 手搓队列成品数量必须单次汇总，不能按每个请求重复扫描队列。",
        )
        assert_contains(
            r"missing_section_index = nil",
            autocraft_text,
            "FAIL: 玩家数据必须记录缺料编组 index，用于避免保活轮询反复扫描全部编组。",
        )
        assert_contains(
            r"local cached_section = data\.missing_section_index and logistic_point\.sections\[data\.missing_section_index\] or nil.*?"
            r"cached_section and cached_section\.valid and is_missing_materials_section\(cached_section, context\)",
            autocraft_text,
            "FAIL: find_missing_materials_section 必须优先使用缓存的缺料编组 index。",
        )
        assert_contains(
            r"event\.name == defines\.events\.on_gui_closed.*?"
            r"event\.gui_type == defines\.gui_type\.controller.*?"
            r"autocraft\.mark_sections_dirty\(player\).*?"
            r"autocraft\.sync_section_status_notifications\(player,\s*\"logistics\"\)",
            control_text,
            "FAIL: 关闭物流界面后必须失效编组缓存并同步状态。",
        )
        assert_contains(
            r"event\.setting == constants\.AUTOCRAFT_PREFIX_SETTING or event\.setting == constants\.AUTOCRAFT_MATCH_MODE_SETTING.*?"
            r"autocraft\.mark_sections_dirty\(player\)",
            control_text,
            "FAIL: 匹配规则变化后必须失效编组缓存。",
        )
        assert_contains(
            r"script\.on_nth_tick\(60,\s*keep_missing_sections_enabled\)",
            control_text,
            "FAIL: 缺料编组保活不能每 tick 执行，必须降到低频轮询。",
        )
        assert_ordered_after(
            autocraft_text,
            "function autocraft.do_crafting(player, crafting_complete, completed_item_name)",
            "if player.crafting_queue and #player.crafting_queue > allowed_queue_length then",
            "update_missing_materials_section(",
            "FAIL: 队列忙时必须先返回，不能继续递归计算缺料编组。",
        )
        assert_ordered_after(
            autocraft_text,
            "function autocraft.do_crafting(player, crafting_complete, completed_item_name)",
            "if player.crafting_queue and #player.crafting_queue > allowed_queue_length then",
            "local item_requests = get_item_requests(player, crafting_complete, completed_item_name)",
            "FAIL: 队列忙判断必须早于请求缺口计算，避免高频背包变化反复扫描请求。",
        )
        assert_ordered_after(
            autocraft_text,
            "function autocraft.do_crafting(player, crafting_complete, completed_item_name)",
            "pick_recipe_from_requests(player, item_requests, recipe_for_item, recipe_pick_stats)",
            "update_missing_materials_section(",
            "FAIL: 仍能手搓时必须先开始制作，缺料递归只能在无可搓配方时执行。",
        )
        assert_contains(
            r"local function pick_cached_recipe_from_requests\(player, item_requests, cached_item_name, cached_recipe_name, stats\).*?"
            r"is_recipe_craftable\(player, cached_recipe_name, stats\).*?"
            r"cached_pick_hits",
            autocraft_text,
            "FAIL: 配方选择必须优先复用上一轮可搓配方，并记录 cached_pick_hits。",
        )
        assert_ordered_after(
            autocraft_text,
            "function autocraft.do_crafting(player, crafting_complete, completed_item_name)",
            "pick_cached_recipe_from_requests(",
            "pick_recipe_from_requests(player, item_requests, recipe_for_item, recipe_pick_stats)",
            "FAIL: 上一轮可搓配方缓存失败后，必须回退到完整配方扫描。",
        )
        assert_contains(
            r"local function remove_missing_materials_section\(player\).*?"
            r"not data\.missing_section_index and not data\.missing_section_name.*?"
            r"return",
            autocraft_text,
            "FAIL: 没有缺料编组记录时，移除逻辑必须快速返回，避免无意义扫描。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 全匹配模式的编组扫描缓存与状态同步短路约束已满足。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
