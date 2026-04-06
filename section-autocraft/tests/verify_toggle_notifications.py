#!/usr/bin/env python3
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
AUTOCRAFT = ROOT / "src" / "autocraft.lua"
CONTROL = ROOT / "src" / "control.lua"
LOCALES = [
    ROOT / "src" / "locale" / "zh-CN" / "autocraft.cfg",
    ROOT / "src" / "locale" / "en" / "autocraft.cfg",
]


def assert_contains(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.S):
        raise AssertionError(message)


def assert_not_contains(pattern: str, text: str, message: str) -> None:
    if re.search(pattern, text, re.S):
        raise AssertionError(message)


def verify_autocraft_source() -> None:
    text = AUTOCRAFT.read_text(encoding="utf-8")
    assert_contains(
        r"local function build_section_status_snapshot\(player\)",
        text,
        "FAIL: autocraft.lua 缺少物流编组状态快照函数。",
    )
    assert_contains(
        r"local function notify_section_status_lines\(player, section_lines\)",
        text,
        "FAIL: autocraft.lua 缺少分组提示输出函数。",
    )
    assert_contains(
        r"local function sync_section_status_notifications\(player, trigger_mode\)",
        text,
        "FAIL: autocraft.lua 缺少分组状态同步入口。",
    )
    assert_contains(
        r"player\.print\(message\)",
        text,
        "FAIL: autocraft.lua 没有通过 player.print 输出提示。",
    )
    assert_not_contains(
        r"game\.print\(",
        text,
        "FAIL: 提示逻辑禁止使用 game.print。",
    )


def verify_control_source() -> None:
    text = CONTROL.read_text(encoding="utf-8")
    assert_contains(
        r"local function sync_section_status_notifications_for_connected_players\(\)",
        text,
        "FAIL: control.lua 缺少分组状态轮询兜底函数。",
    )
    assert_contains(
        r"autocraft\.sync_section_status_notifications\(player,\s*\"shortcut\"\)",
        text,
        "FAIL: control.lua 缺少右下角总开关提示入口。",
    )
    assert_contains(
        r"autocraft\.sync_section_status_notifications\(player,\s*\"logistics\"\)",
        text,
        "FAIL: control.lua 缺少物流界面状态变化提示入口。",
    )
    assert_not_contains(
        r"game\.print\(",
        text,
        "FAIL: control.lua 禁止使用 game.print。",
    )
    assert_contains(
        r"script\.on_nth_tick\(30,\s*sync_section_status_notifications_for_connected_players\)",
        text,
        "FAIL: control.lua 缺少分组状态提示的轮询兜底挂接。",
    )


def verify_locales() -> None:
    required_keys = [
        "autocraft-toggle-status-enabled",
        "autocraft-toggle-status-disabled",
        "autocraft-toggle-status-empty",
        "autocraft-toggle-status-line",
    ]
    for locale_path in LOCALES:
        text = locale_path.read_text(encoding="utf-8")
        for key in required_keys:
            if f"{key}=" not in text:
                raise AssertionError(f"FAIL: {locale_path.name} 缺少 locale 键 {key}。")


def main() -> int:
    try:
        verify_autocraft_source()
        verify_control_source()
        verify_locales()
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 启用/禁用提示逻辑与 locale 约束已满足。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
