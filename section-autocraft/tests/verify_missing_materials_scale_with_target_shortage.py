#!/usr/bin/env python3
from pathlib import Path
import re
import sys


SOURCE = Path(__file__).resolve().parents[1] / "src" / "autocraft.lua"


def assert_contains(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.S):
        raise AssertionError(message)


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")

    try:
        assert_contains(
            r"local function update_missing_materials_section\(player, target_item_name, target_recipe_name, target_missing_count\)",
            text,
            "FAIL: update_missing_materials_section 必须接收当前目标物品的总缺口数量。",
        )
        assert_contains(
            r"local crafts_needed = math\.ceil\(target_missing_count / get_recipe_output_amount\(recipe, target_item_name\)\)",
            text,
            "FAIL: 顶层缺料请求必须按当前目标物品总缺口换算 crafts_needed。",
        )
        assert_contains(
            r"local required_count = ingredient\.amount \* crafts_needed",
            text,
            "FAIL: 顶层原料需求必须按 crafts_needed 放大，而不是只算 1 次配方。",
        )
        assert_contains(
            r"update_missing_materials_section\(\s*player,\s*target_item_name,\s*target_recipe_name,\s*target_item_request and target_item_request\.missing or nil\s*\)",
            text,
            "FAIL: do_crafting 必须把目标物品当前总缺口传给缺料编组逻辑。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 缺料编组已按目标物品总缺口计算。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
