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
            r"local function consume_available_item_count\(available_items, item_name, needed_count\)",
            text,
            "FAIL: autocraft.lua 缺少共享可用库存消费函数。",
        )
        assert_contains(
            r"local available_inventory_counts = \{\}",
            text,
            "FAIL: update_missing_materials_section 必须维护共享背包库存池。",
        )
        assert_contains(
            r"local available_network_counts = \{\}",
            text,
            "FAIL: update_missing_materials_section 必须维护共享物流网络库存池。",
        )
        assert_contains(
            r"accumulate_missing_materials\(\s*player,\s*ingredient\.name,\s*required_count,\s*missing_requests,\s*\{\},\s*logistic_network,\s*available_inventory_counts,\s*available_network_counts\s*\)",
            text,
            "FAIL: 顶层递归调用必须传入共享库存池。",
        )
        assert_contains(
            r"local inventory_count = consume_available_item_count\(available_inventory_counts, item_name, required_count\)",
            text,
            "FAIL: 共享背包库存必须在递归 helper 内统一消费。",
        )
        assert_contains(
            r"local logistic_network_count = consume_available_item_count\(available_network_counts, item_name, missing_count\)",
            text,
            "FAIL: 共享物流网络库存必须在递归 helper 内统一消费。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 递归缺料请求逻辑已改为共享库存池扣减。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
