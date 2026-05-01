#!/usr/bin/env python3
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
AUTOCRAFT = ROOT / "src" / "autocraft.lua"


def assert_contains(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.S):
        raise AssertionError(message)


def main() -> int:
    autocraft_text = AUTOCRAFT.read_text(encoding="utf-8")

    try:
        if re.search(r"begin_crafting\(\{\s*count\s*=\s*1\s*,", autocraft_text, re.S):
            raise AssertionError("FAIL: autocraft.lua 不能再固定 begin_crafting count = 1。")

        assert_contains(
            r"AUTOCRAFT_MAX_CRAFT_BATCH_SIZE\s*=\s*10000",
            autocraft_text,
            "FAIL: autocraft.lua 必须保留内部单轮制作数量硬上限 10000。",
        )
        assert_contains(
            r"local function get_craft_count\(player, recipe_name, recipe, item_request\).*?"
            r"item_request\.missing.*?"
            r"get_recipe_output_amount\(recipe, item_request\.name\).*?"
            r"player\.get_craftable_count\(recipe_name\).*?"
            r"math\.min\(crafts_needed, craftable_count, AUTOCRAFT_MAX_CRAFT_BATCH_SIZE\)",
            autocraft_text,
            "FAIL: autocraft.lua 必须根据缺口、配方产出、当前可制作数量和硬上限计算 craft_count。",
        )
        assert_contains(
            r"local craft_count = .*?get_craft_count\(player, recipe_name, recipe, item_request\).*?"
            r"if craft_count <= 0 then.*?return.*?end",
            autocraft_text,
            "FAIL: do_crafting 必须在 craft_count <= 0 时提前返回。",
        )
        assert_contains(
            r"player\.begin_crafting\(\{\s*count\s*=\s*craft_count\s*,\s*recipe\s*=\s*recipe_name",
            autocraft_text,
            "FAIL: do_crafting 必须使用计算出的 craft_count 调用 begin_crafting。",
        )
        assert_contains(
            r"autocraft\.record_profile\(\"do_crafting\.begin_crafting_api\".*?"
            r"begin_crafting = craft_count",
            autocraft_text,
            "FAIL: begin_crafting 性能日志必须记录真实 craft_count。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 自动手搓制作数量会按缺口和可制作数量动态计算。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
