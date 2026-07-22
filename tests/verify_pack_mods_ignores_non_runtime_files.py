#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pack_mods


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pack_mods_ignore_") as temp_dir:
        src_dir = Path(temp_dir) / "src"
        tests_dir = src_dir / "tests"
        docs_dir = src_dir / "docs"
        references_dir = src_dir / "references"
        tests_dir.mkdir(parents=True)
        docs_dir.mkdir()
        references_dir.mkdir()

        files = [
            src_dir / "control.lua",
            src_dir / "AGENTS.md",
            src_dir / "README.md",
            tests_dir / "verify_example.py",
            docs_dir / "README.md",
            references_dir / "reference.lua",
        ]
        for file_path in files:
            file_path.write_text("placeholder", encoding="utf-8")

        included = []
        for file_path in sorted(src_dir.rglob("*")):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(src_dir)
            if not pack_mods.should_ignore(relative.parts, file_path.name):
                included.append(relative.as_posix())

    expected = ["control.lua"]
    if included != expected:
        print(f"FAIL: expected packaged files {expected}, got {included}")
        return 1

    print("PASS: pack_mods ignores tests and repository documentation files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
