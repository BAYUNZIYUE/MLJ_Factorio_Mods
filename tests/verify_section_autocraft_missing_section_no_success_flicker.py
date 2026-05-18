#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTOCRAFT_LUA = ROOT / "section-autocraft" / "src" / "autocraft.lua"


def extract_function_body(source: str, marker: str, next_marker: str) -> str:
    start = source.find(marker)
    if start == -1:
      raise AssertionError(f"missing function marker {marker}")

    end = source.find(next_marker, start + len(marker))
    if end == -1:
      raise AssertionError(f"could not find end marker {next_marker}")

    return source[start:end]


def main() -> int:
    source = AUTOCRAFT_LUA.read_text(encoding="utf-8")
    body = extract_function_body(
        source,
        "function autocraft.do_crafting(",
        "\nfunction autocraft.keep_missing_materials_section_enabled(",
    )

    success_start = body.find("if recipe_name then")
    begin_index = body.find("player.begin_crafting")
    if success_start == -1 or begin_index == -1 or begin_index <= success_start:
        print("FAIL: could not find successful crafting branch.")
        return 1

    success_before_begin = body[success_start:begin_index]
    if "remove_missing_materials_section(player)" in success_before_begin:
        print(
            "FAIL: successful crafting must not delete the missing-materials "
            "section before begin_crafting, because that causes visible section flicker."
        )
        return 1

    print("PASS: Section Autocraft keeps the missing-materials section stable while crafting starts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
