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


def main() -> int:
    autocraft_text = AUTOCRAFT.read_text(encoding="utf-8")
    control_text = CONTROL.read_text(encoding="utf-8")

    try:
        assert_contains(
            r"function autocraft\.start_profile\(\).*?game\.create_profiler\(\)",
            autocraft_text,
            "FAIL: autocraft.lua 缺少按需创建 LuaProfiler 的入口。",
        )
        assert_contains(
            r"storage\.autocraft_performance_debug_enabled ~= false",
            autocraft_text,
            "FAIL: profile 必须默认持续开启，除非用户显式 off。",
        )
        assert_contains(
            r"function autocraft\.record_profile\(scope_name, profiler, details\).*?"
            r"profile_state\.scopes|function autocraft\.record_profile\(scope_name, profiler, details\).*?"
            r"performance_profile_state\.scopes",
            autocraft_text,
            "FAIL: autocraft.lua 缺少 profile 聚合记录入口。",
        )
        assert_contains(
            r"\[section-autocraft-profile\].*?scope=.*?avg=.*?total=",
            autocraft_text,
            "FAIL: profile 日志必须输出 scope、avg 和 total。",
        )
        assert_contains(
            r"local function find_missing_materials_section\(player\).*?"
            r"autocraft\.start_profile\(\).*?"
            r"scanned_sections",
            autocraft_text,
            "FAIL: find_missing_materials_section 必须记录扫描编组数量。",
        )
        assert_contains(
            r"local function build_requested_items\(player\).*?"
            r"scanned_sections.*?scanned_filters",
            autocraft_text,
            "FAIL: build_requested_items 必须记录扫描编组和过滤槽数量。",
        )
        assert_contains(
            r"local function update_missing_materials_section\(player, target_item_name, target_recipe_name, target_missing_count\).*?"
            r"top_level_ingredients.*?missing_request_kinds",
            autocraft_text,
            "FAIL: update_missing_materials_section 必须记录缺料递归规模。",
        )
        assert_contains(
            r"function autocraft\.do_crafting\(player, crafting_complete, completed_item_name\).*?"
            r"autocraft\.record_profile\(\"do_crafting\"",
            autocraft_text,
            "FAIL: do_crafting 必须记录主流程耗时。",
        )
        assert_contains(
            r"function autocraft\.do_crafting\(player, crafting_complete, completed_item_name\).*?"
            r"do_crafting\.get_item_requests.*?"
            r"do_crafting\.sort_item_requests.*?"
            r"do_crafting\.pick_craftable_recipe.*?"
            r"do_crafting\.begin_crafting_api",
            autocraft_text,
            "FAIL: do_crafting 必须拆分记录请求计算、排序、配方选择和 begin_crafting API 耗时。",
        )
        assert_contains(
            r"local function get_recipe_pick_stats_details\(stats, item_request_count, recipe_found\).*?"
            r"get_craftable_count_calls.*?"
            r"recipe_checks.*?"
            r"cached_pick_hits",
            autocraft_text,
            "FAIL: 配方选择 profile 必须输出 recipe_checks、get_craftable_count_calls 和 cached_pick_hits。",
        )
        assert_contains(
            r"local function get_item_requests\(player, crafting_complete, completed_item_name\).*?"
            r"autocraft\.record_profile\(\"get_item_requests\"",
            autocraft_text,
            "FAIL: get_item_requests 必须单独记录缺口计算规模。",
        )
        assert_contains(
            r"commands\.add_command\(\s*\"section-autocraft-profile\"",
            control_text,
            "FAIL: control.lua 必须注册 /section-autocraft-profile 调试命令。",
        )
        assert_contains(
            r"local function keep_missing_sections_enabled\(\).*?"
            r"autocraft\.record_profile\(\"control\.keep_missing_sections_enabled\"",
            control_text,
            "FAIL: keep_missing_sections_enabled 必须记录每 tick 保活耗时。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 性能 profile 日志入口和关键阶段埋点已满足。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
