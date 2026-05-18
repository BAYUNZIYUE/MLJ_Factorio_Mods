#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    for mod_root in sorted(ROOT.iterdir(), key=lambda item: item.name.lower()):
        if not mod_root.is_dir() or mod_root.name in {".git", ".codex", "ModZips", "tests"}:
            continue

        src = mod_root / "src"
        info_path = src / "info.json"
        if not info_path.is_file():
            continue

        info = json.loads(info_path.read_text(encoding="utf-8"))
        mod_name = info.get("name", mod_root.name)

        root_changelog = mod_root / "changelog.txt"
        if root_changelog.exists():
            fail(f"{mod_name}: root-level changelog.txt is not allowed; move it to {src.relative_to(ROOT)}/changelog.txt")

        src_changelog = src / "changelog.txt"
        if not src_changelog.is_file():
            fail(f"{mod_name}: missing {src_changelog.relative_to(ROOT)}")

    print("PASS: all mod changelogs live under src.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
