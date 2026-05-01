#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pack_mods


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pack_mods_cleanup_") as temp_dir:
        output_dir = Path(temp_dir) / "ModZips"
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "old.zip").write_text("old zip", encoding="utf-8")
        nested_dir = output_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "stale.txt").write_text("stale", encoding="utf-8")

        pack_mods.clear_output_directory(output_dir)

        assert output_dir.is_dir(), "输出目录本身应保留"
        assert list(output_dir.iterdir()) == [], "输出目录中的旧文件和子目录应在打包前清空"

    print("OK")


if __name__ == "__main__":
    main()
