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

    if "local DEFAULT_QUALITY_NAME = \"normal\"" not in source:
        print("FAIL: normal quality constant is required for hand-crafting eligibility.")
        return 1

    if "local function recipe_id_with_quality(" in source:
        print("FAIL: hand-crafting must not invent a quality-bearing recipe id.")
        return 1

    is_recipe_craftable = extract_function_body(
        source,
        "local function is_recipe_craftable(",
        "\nlocal function recipe_has_only_item_inputs_and_outputs(",
    )
    if (
        "if not is_default_quality(quality_name) then" not in is_recipe_craftable
        or "return false" not in is_recipe_craftable
        or "player.get_craftable_count(recipe_name) > 0" not in is_recipe_craftable
    ):
        print("FAIL: recipe craftability must reject non-normal quality before querying get_craftable_count.")
        return 1

    recipe_for_hand_craftable_item = extract_function_body(
        source,
        "local function recipe_for_hand_craftable_item(",
        "\nlocal function get_crafting_queue_item_counts(",
    )
    if "if not is_default_quality(quality_name) then" not in recipe_for_hand_craftable_item:
        print("FAIL: missing-material recursion must reject non-normal quality recipes.")
        return 1

    get_craft_count = extract_function_body(
        source,
        "local function get_craft_count(",
        "\nlocal function consume_available_item_count(",
    )
    if (
        "if not is_default_quality(item_request.quality) then" not in get_craft_count
        or "return 0" not in get_craft_count
        or "player.get_craftable_count(recipe_name)" not in get_craft_count
    ):
        print("FAIL: craft count must reject non-normal quality and use plain RecipeID.")
        return 1

    do_crafting = extract_function_body(
        source,
        "function autocraft.do_crafting(",
        "\nfunction autocraft.keep_missing_materials_section_enabled(",
    )
    if "player.begin_crafting({ count = craft_count, recipe = recipe_name, silent = true })" not in do_crafting:
        print("FAIL: begin_crafting must use the plain recipe name RecipeID.")
        return 1

    print("PASS: Section Autocraft excludes non-normal quality requests from hand-crafting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
