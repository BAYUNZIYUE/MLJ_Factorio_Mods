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
            r"local function accumulate_missing_materials\(\s*player,\s*item_name,\s*required_count,\s*requests,\s*visiting,\s*logistic_network,\s*available_inventory_counts,\s*available_network_counts\s*\)",
            text,
            "FAIL: accumulate_missing_materials 必须按目标持有量 required_count 计算。",
        )
        assert_contains(
            r"requests\[item_name\] = \(requests\[item_name\] or 0\) \+ required_count",
            text,
            "FAIL: 缺料编组写入的必须是目标持有量，而不是纯缺口量。",
        )
        assert_contains(
            r"local inventory_count = consume_available_item_count\(available_inventory_counts, item_name, required_count\)",
            text,
            "FAIL: 目标持有量必须先扣减背包现有数量。",
        )
        assert_contains(
            r"local missing_count = required_count - inventory_count",
            text,
            "FAIL: 缺口应该由目标持有量减去当前库存得到。",
        )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 缺料编组请求的是目标持有量。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
