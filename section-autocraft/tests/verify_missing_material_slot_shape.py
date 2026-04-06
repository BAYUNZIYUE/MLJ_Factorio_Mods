#!/usr/bin/env python3
from pathlib import Path
import re
import sys


SOURCE = Path(__file__).resolve().parents[1] / "src" / "autocraft.lua"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")

    helper_pattern = re.compile(
        r"local function build_missing_material_slot\(request\)\s+"
        r"-- .*?简单物品.*?\s+"
        r"return \{\s+"
        r"value = request\.name,\s+"
        r"min = request\.count,\s+"
        r"\}\s+"
        r"end",
        re.S,
    )
    if not helper_pattern.search(text):
        print("FAIL: build_missing_material_slot 必须返回简单物品请求格式。")
        return 1

    setter_pattern = re.compile(
        r"section\.set_slot\(slot_index,\s*build_missing_material_slot\(request\)\s*\)"
    )
    if not setter_pattern.search(text):
        print("FAIL: write_missing_materials_section 必须通过 helper 写入缺料槽位。")
        return 1

    legacy_pattern = re.compile(
        r"section\.set_slot\(slot_index,\s*\{\s*value\s*=\s*\{\s*type\s*=\s*\"item\"",
        re.S,
    )
    if legacy_pattern.search(text):
        print("FAIL: 仍然存在旧的表结构 item filter 写法，会重新触发 1.0.0 崩溃。")
        return 1

    print("PASS: 缺料槽位使用简单物品请求格式。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
