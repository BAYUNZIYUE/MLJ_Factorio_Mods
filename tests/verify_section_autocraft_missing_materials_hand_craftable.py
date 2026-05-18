#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOCRAFT_LUA = ROOT / "section-autocraft" / "src" / "autocraft.lua"


def extract_function_body(source: str, marker: str, next_marker: str) -> str:
    start = source.find(marker)
    if start == -1:
        raise AssertionError(f"missing function marker {marker}")

    end = source.find(next_marker, start + len(marker))
    if end == -1:
        raise AssertionError(f"could not find end marker {next_marker}")

    return source[start:end]


def main() -> int:
    source = AUTOCRAFT_LUA.read_text(encoding="utf-8")

    required_helpers = [
        "local function is_recipe_hand_craftable_without_materials(",
        "local function recipe_for_hand_craftable_item(",
        "local function recipe_has_only_item_inputs_and_outputs(",
        "local function recipe_matches_player_hand_crafting_category(",
    ]
    for helper in required_helpers:
        if helper not in source:
            print(f"FAIL: missing hand-craftable recipe helper: {helper}")
            return 1

    helper_body = extract_function_body(
        source,
        "local function is_recipe_hand_craftable_without_materials(",
        "\nlocal function recipe_for_hand_craftable_item(",
    )
    required_checks = [
        "recipe.prototype.hidden_from_player_crafting",
        "player.force.get_hand_crafting_disabled_for_recipe(recipe.name)",
        "recipe_has_only_item_inputs_and_outputs(recipe)",
        "recipe_matches_player_hand_crafting_category(player, recipe)",
    ]
    for check in required_checks:
        if check not in helper_body:
            print(f"FAIL: missing hand-craftable recipe check: {check}")
            return 1

    missing_body = extract_function_body(
        source,
        "local function accumulate_missing_materials(",
        "\nlocal function update_missing_materials_section(",
    )
    if "recipe_for_hand_craftable_item(player, item_name, quality_name)" not in missing_body:
        print("FAIL: recursive missing-material expansion must use hand-craftable recipes only.")
        return 1
    if "recipe_for_item_any(player, item_name)" in missing_body:
        print("FAIL: recursive missing-material expansion still accepts non-hand-craftable recipes.")
        return 1

    do_crafting_body = extract_function_body(
        source,
        "function autocraft.do_crafting(",
        "\nfunction autocraft.keep_missing_materials_section_enabled(",
    )
    if "recipe_for_hand_craftable_item" not in do_crafting_body:
        print("FAIL: no-craftable fallback must choose a hand-craftable target recipe.")
        return 1
    if "recipe_for_item_any" in do_crafting_body:
        print("FAIL: no-craftable fallback still accepts non-hand-craftable target recipes.")
        return 1

    print("PASS: Section Autocraft only expands missing materials through hand-craftable recipes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
