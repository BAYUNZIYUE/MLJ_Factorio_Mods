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
            r"local function get_sorted_recipe_names\(recipes\)",
            text,
            "FAIL: autocraft.lua 缺少确定性配方排序函数。",
        )
        assert_contains(
            r"table\.sort\(recipe_names\)",
            text,
            "FAIL: 配方排序函数必须显式排序 recipe_names。",
        )
        assert_contains(
            r"for _, recipe_name in ipairs\(get_sorted_recipe_names\(recipes\)\) do",
            text,
            "FAIL: recipe_for_item / recipe_for_item_any 必须按确定性顺序遍历配方。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 配方选择顺序已固定。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
