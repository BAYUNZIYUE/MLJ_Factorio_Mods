#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOCRAFT_LUA = ROOT / "section-autocraft" / "src" / "autocraft.lua"
CONTROL_LUA = ROOT / "section-autocraft" / "src" / "control.lua"


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    autocraft = AUTOCRAFT_LUA.read_text(encoding="utf-8")
    control = CONTROL_LUA.read_text(encoding="utf-8")

    required_helpers = [
        "local DEFAULT_QUALITY_NAME = \"normal\"",
        "local function normalise_quality_name(",
        "local function make_item_key(",
        "local function item_count_filter(",
        "local function item_with_quality_id(",
        "local function logistic_signal_filter(",
        "local function parse_logistic_filter_item_request(",
        "local function is_default_quality(",
    ]
    for helper in required_helpers:
        if helper not in autocraft:
            return fail(f"missing quality-aware helper: {helper}")

    required_snippets = [
        "quality = normalise_quality_name(request.quality)",
        "value = logistic_signal_filter(request.name, request.quality)",
        "requested_items[item_key] = item_request",
        "player.get_item_count(item_count_filter(item_name, quality_name))",
        "logistic_network.get_item_count(item_with_quality_id(item_name, quality_name))",
        "queued_counts[item_key] = (queued_counts[item_key] or 0)",
        "recipe_for_item(player, item_name, quality_name, stats)",
        "if not is_default_quality(quality_name) then",
        "return player.get_craftable_count(recipe_name) > 0",
        "player.begin_crafting({ count = craft_count, recipe = recipe_name, silent = true })",
        "recipe_for_hand_craftable_item(player, item_name, quality_name)",
        "data.active_quality_name = quality_name",
        "data.last_craftable_quality_name = quality_name",
    ]
    for snippet in required_snippets:
        if snippet not in autocraft:
            return fail(f"missing quality-aware behavior: {snippet}")

    forbidden_snippets = [
        "value = request.name",
        "requested_items[item_name] = (requested_items[item_name] or 0) + filter.min",
        "player.get_item_count(item_name)",
        "logistic_network.get_item_count(item_name)",
        "recipe_id_with_quality",
        "player.get_craftable_count(recipe_id_with_quality",
        "recipe = recipe_id_with_quality",
        "recipe_for_item_any",
    ]
    for snippet in forbidden_snippets:
        if snippet in autocraft:
            return fail(f"quality-blind behavior still exists: {snippet}")

    control_required = [
        "local event_quality_name = event.item_stack.quality.name",
        "(data.active_quality_name or \"normal\") == event_quality_name",
        "autocraft.do_crafting(player, false, event.item_stack.name, event_quality_name)",
    ]
    for snippet in control_required:
        if snippet not in control:
            return fail(f"control.lua no longer carries crafted item quality: {snippet}")

    print("PASS: Section Autocraft keeps logistics requests and missing materials quality-aware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
