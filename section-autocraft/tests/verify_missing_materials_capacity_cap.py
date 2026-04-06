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
            r"local function cap_requests_to_main_inventory_capacity\(player, request_list\)",
            text,
            "FAIL: 缺少按主背包容量裁剪请求量的函数。",
        )
        assert_contains(
            r"local main_inventory = player\.get_main_inventory\(\)",
            text,
            "FAIL: 容量裁剪必须读取玩家主背包。",
        )
        assert_contains(
            r"local remaining_empty_stacks = main_inventory\.count_empty_stacks\(false, false\)",
            text,
            "FAIL: 容量裁剪必须考虑主背包当前空栈数量。",
        )
        assert_contains(
            r"local capped_count = math\.min\(request\.count, max_target_count\)",
            text,
            "FAIL: 请求目标数必须受主背包容量上限限制。",
        )
        assert_contains(
            r"request_list = cap_requests_to_main_inventory_capacity\(player, request_list\)",
            text,
            "FAIL: write_missing_materials_section 必须在写槽位前应用容量裁剪。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 缺料编组请求量已按主背包容量裁剪。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
