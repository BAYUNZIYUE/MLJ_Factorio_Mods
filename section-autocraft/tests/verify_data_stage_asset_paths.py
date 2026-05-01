#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
INFO = ROOT / "src" / "info.json"
DATA = ROOT / "src" / "data.lua"


def main() -> int:
    info = json.loads(INFO.read_text(encoding="utf-8"))
    mod_name = info["name"]
    data_text = DATA.read_text(encoding="utf-8")

    asset_paths = re.findall(r'"(__[^"\n]+__/[^"\n]+)"', data_text)
    if not asset_paths:
        print("FAIL: data.lua 没有找到任何 __mod__/path 资源路径。")
        return 1

    for asset_path in asset_paths:
        match = re.match(r"^__([^_]+(?:-[^_]+)*)__/(.+)$", asset_path)
        if not match:
            print(f"FAIL: 非法资源路径格式 {asset_path}")
            return 1

        asset_mod, relative_path = match.groups()
        if asset_mod != mod_name and asset_mod not in {"base", "core"}:
            print(
                "FAIL: data.lua 资源路径前缀与当前模组名不一致，"
                f"期望 __{mod_name}__，实际是 __{asset_mod}__。"
            )
            return 1

        if asset_mod == mod_name and not (ROOT / "src" / relative_path).is_file():
            print(f"FAIL: 当前模组资源文件不存在 {relative_path}")
            return 1

    print("PASS: data.lua 资源路径前缀与文件存在性校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
