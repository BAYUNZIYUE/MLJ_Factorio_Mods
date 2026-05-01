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
            r'setting_type = "runtime-global".*?'
            r"default_value = 1.*?"
            r"minimum_value = 1.*?"
            r"maximum_value = 10000",
            settings_text,
            "FAIL: settings.lua 必须定义默认 1、最小 1、最大 10000 的 runtime-global double-setting。",
        )
        assert_contains(
            r"local function sync_manual_crafting_speed_modifier\(\).*?"
            r"local modifier = multiplier - 1.*?"
            r"for _, force in pairs\(game\.forces\) do.*?"
            r"force\.manual_crafting_speed_modifier = modifier",
            control_text,
            "FAIL: control.lua 必须把倍数转换为 force.manual_crafting_speed_modifier。",
        )
        assert_contains(
            r"function on_runtime_mod_setting_changed|local function on_runtime_mod_setting_changed",
            control_text,
            "FAIL: control.lua 缺少 runtime 设置变更入口。",
        )
        assert_contains(
            r"event\.setting == constants\.AUTOCRAFT_CRAFTING_SPEED_MULTIPLIER_SETTING.*?"
            r"sync_manual_crafting_speed_modifier\(\).*?"
            r"return",
            control_text,
            "FAIL: 手搓速度设置变更时必须立即同步并提前返回。",
        )
        assert_contains(
            r"local function on_configuration_changed\(\).*?sync_force_runtime_state\(\)",
            control_text,
            "FAIL: 配置变更后必须恢复手搓速度倍数。",
        )
        assert_contains(
            r"local function sync_player_state\(event\).*?sync_manual_crafting_speed_modifier\(\)",
            control_text,
            "FAIL: 玩家进入或控制器变化时必须补同步手搓速度倍数。",
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
