#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD_ROOT = ROOT / "expend-toolbar"
SRC = MOD_ROOT / "src"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_contains(path: Path, text: str) -> None:
    content = read(path)
    if text not in content:
        raise AssertionError(f"{path.relative_to(ROOT)} must contain: {text}")


def assert_not_contains(path: Path, text: str) -> None:
    content = read(path)
    if text in content:
        raise AssertionError(f"{path.relative_to(ROOT)} must not contain: {text}")


def main() -> int:
    info = json.loads(read(SRC / "info.json"))
    if info["name"] != "expend-toolbar":
        raise AssertionError("expend-toolbar/src/info.json name must stay expend-toolbar")

    if not (MOD_ROOT / "README.md").is_file() or not (MOD_ROOT / "AGENTS.md").is_file():
        raise AssertionError("expend-toolbar must keep root README.md and AGENTS.md")

    for path in SRC.rglob("*"):
        if path.is_file() and path.suffix in {".lua", ".json", ".cfg"}:
            assert_not_contains(path, "toolbars-mod")
            assert_not_contains(path, "__toolbars-mod__")

    assert_contains(SRC / "Toolbars.lua", 'Toolbars.name = "expend-toolbar"')
    assert_contains(SRC / "src/player/inventory/ViewInventory.lua", "return sideChanged")
    assert_contains(SRC / "src/gui/toolbar/content/sections/section/content/table/slots/item/QualitySprite.lua", "if quality and quality.draw_sprite_by_default then")

    print("PASS: expend-toolbar identity, docs, quality guard, and side refresh are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
