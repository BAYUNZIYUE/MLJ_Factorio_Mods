#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROL_LUA = ROOT / "section-autocraft" / "src" / "control.lua"


def extract_function_body(source: str, function_name: str) -> str:
    marker = f"local function {function_name}("
    start = source.find(marker)
    if start == -1:
        raise AssertionError(f"missing function {function_name}")

    next_function = source.find("\nlocal function ", start + len(marker))
    if next_function == -1:
        raise AssertionError(f"could not find end of function {function_name}")

    return source[start:next_function]


def main() -> int:
    source = CONTROL_LUA.read_text(encoding="utf-8")
    body = extract_function_body(source, "sync_player_crafting_speed_modifier")
    assignment_index = body.find("player.character_crafting_speed_modifier")

    if assignment_index == -1:
        print("FAIL: sync_player_crafting_speed_modifier no longer writes character crafting speed.")
        return 1

    guard_region = body[:assignment_index]
    if "not player.character" not in guard_region:
        print(
            "FAIL: sync_player_crafting_speed_modifier must return before writing "
            "character_crafting_speed_modifier when player.character is nil."
        )
        return 1

    if "defines.events.on_player_controller_changed, sync_player_state" not in source:
        print(
            "FAIL: skipped character-speed sync needs on_player_controller_changed "
            "to retry after Factorio attaches a character."
        )
        return 1

    print("PASS: Section Autocraft guards character crafting speed sync for no-character players.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
