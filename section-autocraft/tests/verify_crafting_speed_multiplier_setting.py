#!/usr/bin/env python3
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CONSTANTS = ROOT / "src" / "constants.lua"
SETTINGS = ROOT / "src" / "settings.lua"
CONTROL = ROOT / "src" / "control.lua"
LOCALES = [
    ROOT / "src" / "locale" / "zh-CN" / "autocraft.cfg",
    ROOT / "src" / "locale" / "en" / "autocraft.cfg",
]


def assert_contains(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.S):
        raise AssertionError(message)


def main() -> int:
    constants_text = CONSTANTS.read_text(encoding="utf-8")
    settings_text = SETTINGS.read_text(encoding="utf-8")
    control_text = CONTROL.read_text(encoding="utf-8")

    try:
        assert_contains(
            r'AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING = "autocraft-crafting-speed-multiplier"',
            constants_text,
            "FAIL: constants.lua 缺少手搓速度倍数设置键。",
        )
        assert_contains(
            r'type = "double-setting".*?'
            r"name = constants\.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING.*?"
            r'setting_type = "runtime-per-user".*?'
            r"default_value = 1.*?"
            r"minimum_value = 1.*?"
            r"maximum_value = 10000",
            settings_text,
            "FAIL: settings.lua 必须定义默认 1、最小 1、最大 10000 的 runtime-per-user double-setting。",
        )
        assert_contains(
            r"local function get_player_crafting_speed_multiplier\(player\).*?"
            r"player\.mod_settings\[constants\.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING\].*?"
            r"return math\.max\(multiplier, 1\)",
            control_text,
            "FAIL: control.lua 必须从玩家自己的 mod_settings 读取手搓速度倍数。",
        )
        assert_contains(
            r"local function sync_player_crafting_speed_modifier\(player\).*?"
            r"local modifier = multiplier - 1.*?"
            r"player\.character_crafting_speed_modifier = modifier",
            control_text,
            "FAIL: control.lua 必须把玩家自己的倍数转换为 player.character_crafting_speed_modifier。",
        )
        if "force.manual_crafting_speed_modifier" in control_text:
            raise AssertionError("FAIL: 手搓速度倍数不能再写 force.manual_crafting_speed_modifier。")
        if "settings.global[constants.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING]" in control_text:
            raise AssertionError("FAIL: 手搓速度倍数不能再从 settings.global 读取。")
        assert_contains(
            r"local function sync_all_player_crafting_speed_modifiers\(\).*?"
            r"for _, player in pairs\(game\.players\) do.*?"
            r"sync_player_crafting_speed_modifier\(player\)",
            control_text,
            "FAIL: 配置变更后必须给所有玩家恢复自己的手搓速度倍数。",
        )
        assert_contains(
            r"function on_runtime_mod_setting_changed|local function on_runtime_mod_setting_changed",
            control_text,
            "FAIL: control.lua 缺少 runtime 设置变更入口。",
        )
        assert_contains(
            r"event\.setting == constants\.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING.*?"
            r"local player = game\.get_player\(event\.player_index\).*?"
            r"sync_player_crafting_speed_modifier\(player\).*?"
            r"return",
            control_text,
            "FAIL: 手搓速度设置变更时必须只同步触发设置的玩家并提前返回。",
        )
        assert_contains(
            r"local function on_configuration_changed\(\).*?sync_force_runtime_state\(\)",
            control_text,
            "FAIL: 配置变更后必须恢复运行时状态。",
        )
        assert_contains(
            r"local function sync_player_state\(event\).*?sync_player_crafting_speed_modifier\(player\)",
            control_text,
            "FAIL: 玩家进入或控制器变化时必须补同步该玩家的手搓速度倍数。",
        )

        for locale_path in LOCALES:
            locale_text = locale_path.read_text(encoding="utf-8")
            assert_contains(
                r"autocraft-crafting-speed-multiplier=",
                locale_text,
                f"FAIL: {locale_path.name} 缺少手搓速度倍数 locale。",
            )
    except AssertionError as exc:
        print(exc)
        return 1

    print("PASS: 手搓速度倍数 runtime 设置与同步逻辑已满足。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
