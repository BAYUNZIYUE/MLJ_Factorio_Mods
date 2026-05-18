#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = ROOT / "quality-cycler"
SRC = MOD_ROOT / "src"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_binary_file(path: Path) -> bytes:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_bytes()


def require_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(f"{label} missing {needle!r}")


def main() -> int:
    info_text = require_file(SRC / "info.json")
    info = json.loads(info_text)
    if info.get("name") != "quality-cycler":
        fail("info.json name must be quality-cycler")
    if info.get("title") != "Blueprint & Upgrade Planner Quality Cycler":
        fail("info.json title must be Blueprint & Upgrade Planner Quality Cycler")
    thumbnail = require_binary_file(SRC / "thumbnail.png")
    if not thumbnail.startswith(b"\x89PNG\r\n\x1a\n"):
        fail("thumbnail.png must be a PNG file")

    require_file(MOD_ROOT / "AGENTS.md")
    require_file(MOD_ROOT / "README.md")
    require_file(SRC / "locale" / "en" / "locale.cfg")
    require_file(SRC / "locale" / "zh-CN" / "locale.cfg")

    data_lua = require_file(SRC / "data.lua")
    require_contains(data_lua, 'linked_game_control = "cycle-quality-up"', "data.lua")
    require_contains(data_lua, 'linked_game_control = "cycle-quality-down"', "data.lua")
    require_contains(data_lua, "include_selected_prototype = true", "data.lua")
    settings_lua = require_file(SRC / "settings.lua")
    require_contains(settings_lua, 'name = prefix .. "ignore-list"', "settings.lua")
    require_contains(settings_lua, 'setting_type = "runtime-per-user"', "settings.lua")
    require_contains(settings_lua, 'type = "string-setting"', "settings.lua")
    require_contains(settings_lua, "allow_blank = true", "settings.lua")

    control_lua = require_file(SRC / "control.lua")
    require_contains(control_lua, "prototypes.quality", "control.lua")
    require_contains(control_lua, "quality.next", "control.lua")
    require_contains(control_lua, "previous_quality", "control.lua")
    require_contains(control_lua, "first_target_quality", "control.lua")
    require_contains(control_lua, "mapper_count", "control.lua")
    require_contains(control_lua, "get_mapper", "control.lua")
    require_contains(control_lua, "set_mapper", "control.lua")
    require_contains(control_lua, '"to"', "control.lua")
    require_contains(control_lua, "update_blueprint", "control.lua")
    require_contains(control_lua, "set_blueprint_entities", "control.lua")
    require_contains(control_lua, "update_blueprint_book", "control.lua")
    require_contains(control_lua, "blueprint_entities", "control.lua")
    require_contains(control_lua, "blueprint_items", "control.lua")
    require_contains(control_lua, "upgrade_rules", "control.lua")
    require_contains(control_lua, "localize_text", "control.lua")
    require_contains(control_lua, "normalize_stored_quality(shifted)", "control.lua")
    require_contains(control_lua, "品质上/下切换操作", "control.lua")
    require_contains(control_lua, "event.element", "control.lua")
    require_contains(control_lua, "opened_self", "control.lua")
    require_contains(control_lua, "player.gui.screen.children", "control.lua")
    require_contains(control_lua, "mapper_target_is_allowed", "control.lua")
    require_contains(control_lua, "values_differ", "control.lua")
    require_contains(control_lua, "method_value_changes_with_quality", "control.lua")
    require_contains(control_lua, "custom_tooltip_changes_with_quality", "control.lua")
    require_contains(control_lua, "entity_quality_affects_properties", "control.lua")
    require_contains(control_lua, "item_quality_affects_properties", "control.lua")
    require_contains(control_lua, "quality_for_affect_check", "control.lua")
    require_contains(control_lua, "excluded_entity_types", "control.lua")
    require_contains(control_lua, '"transport-belt"', "control.lua")
    require_contains(control_lua, '"underground-belt"', "control.lua")
    require_contains(control_lua, '"splitter"', "control.lua")
    require_contains(control_lua, "included_entity_types", "control.lua")
    require_contains(control_lua, '"cargo-bay"', "control.lua")
    require_contains(control_lua, '"ammo-turret"', "control.lua")
    require_contains(control_lua, '"electric-turret"', "control.lua")
    require_contains(control_lua, '"fluid-turret"', "control.lua")
    require_contains(control_lua, "custom_tooltip_fields", "control.lua")
    require_contains(control_lua, "quality_values", "control.lua")
    require_contains(control_lua, 'included_entity_types[entity_prototype.type]', "control.lua")
    require_contains(control_lua, "get_inventory_size", "control.lua")
    require_contains(control_lua, "get_crafting_speed", "control.lua")
    require_contains(control_lua, "get_module_effects", "control.lua")
    require_contains(control_lua, "build_ignored_names", "control.lua")
    require_contains(control_lua, "settings.get_player_settings", "control.lua")
    require_contains(control_lua, "is_ignored_name", "control.lua")
    require_contains(control_lua, 'string.gsub(raw_value, "，", ",")', "control.lua")
    require_contains(control_lua, "ignored_names", "control.lua")
    require_contains(control_lua, "is_upgrade_item", "control.lua")
    require_contains(control_lua, "player.opened", "control.lua")
    require_contains(control_lua, "cursor_record", "control.lua")
    require_contains(control_lua, "valid_for_write", "control.lua")
    require_contains(control_lua, "read-only", "control.lua")
    require_contains(control_lua, 'quality == "any"', "control.lua")

    if "for index = 1, 24 do" in control_lua:
        fail("control.lua must use mapper_count instead of a hard-coded 24 mapper limit")
    if "cursor_record.valid_for_write\n            and cursor_record.type" in control_lua:
        fail("control.lua must detect read-only upgrade-planner records separately from missing planners")
    if 'local mapper_sides = { "from", "to" }' in control_lua:
        fail("control.lua must update only target mappers, not source mappers")
    if "get_max_health" in control_lua:
        fail("control.lua must not treat health-only quality changes as functional quality changes")
    if "entity_quality_affects_properties(prototypes.entity[entity_name], shifted)" in control_lua:
        fail("downgrades to normal must test the current non-normal quality, not normal-vs-normal")
    if "item_quality_affects_properties(prototypes.item[item_name], shifted)" in control_lua:
        fail("item downgrades to normal must test the current non-normal quality, not normal-vs-normal")
    if "mapper_target_is_allowed(mapper, shifted, ignored_names)" in control_lua:
        fail("mapper downgrades to normal must test the current non-normal quality, not normal-vs-normal")

    print("quality-cycler simple guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
