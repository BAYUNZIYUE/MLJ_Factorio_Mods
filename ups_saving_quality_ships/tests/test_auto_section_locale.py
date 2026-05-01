#!/usr/bin/env python3
"""自动物流编组名称与删除行为回归脚本。

说明：
- 当前环境无法直接执行 Factorio Lua 运行时，所以这里校验的是
  1. 行为模型；
  2. 源码结构是否已经接入对应实现。
- 不能替代游戏内实机验证。
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOGISTIC = ROOT / "ups_saving_quality_ships" / "src" / "scripts" / "logistic_section_change.lua"
CONTROL = ROOT / "ups_saving_quality_ships" / "src" / "control.lua"


def expected_group_name(locale: str, index: int) -> str:
    if locale.startswith("zh"):
        return f"[自动]UPS友好型品质飞船-{index}"
    return f"[Auto]UPS Saving Quality Ships-{index}"


def simulate_auto_section_dedup(existing_groups: list[str], desired_group: str) -> tuple[str | None, list[int]]:
    kept_group = None
    duplicate_indexes: list[int] = []
    for index, group in enumerate(existing_groups, start=1):
        if kept_group is None or group == desired_group:
            if kept_group is not None:
                duplicate_indexes.append(kept_group[0])
            kept_group = (index, group)
        else:
            duplicate_indexes.append(index)
    if kept_group is None:
        return None, duplicate_indexes
    return desired_group, duplicate_indexes


def assert_source_shape() -> None:
    logistic_source = LOGISTIC.read_text(encoding="utf-8")
    control_source = CONTROL.read_text(encoding="utf-8")

    required_tokens = [
        "build_auto_section_name",
        "is_auto_section_name",
        "remove_auto_section",
        "set_locale",
        "storage.usqs.logistic_locale",
        ".index",
        "logistic_sections.remove_section",
    ]
    for token in required_tokens:
        assert token in logistic_source, f"缺少关键实现标记: {token}"

    assert 'local section_usqs_name = "[Auto]UPS Saving Quality Ships-" .. tostring(platform.index)' not in logistic_source, (
        "仍在使用固定英文自动编组名"
    )
    assert "section.section_index" not in logistic_source, "错误地使用了不存在的 LuaLogisticSection.section_index"
    assert "clear_auto_section" not in logistic_source, "旧的清空保留空编组逻辑仍然存在"
    assert "on_player_locale_changed" in control_source, "control.lua 未监听玩家语言变化"
    assert "logistic_section_change.set_locale" in control_source, "control.lua 未把玩家语言同步给物流模块"


def main() -> None:
    assert expected_group_name("zh-CN", 12) == "[自动]UPS友好型品质飞船-12"
    assert expected_group_name("en", 12) == "[Auto]UPS Saving Quality Ships-12"

    zh_group = expected_group_name("zh-CN", 12)
    en_group = expected_group_name("en", 12)
    assert simulate_auto_section_dedup([en_group], zh_group) == (zh_group, [])
    assert simulate_auto_section_dedup([zh_group], en_group) == (en_group, [])
    assert simulate_auto_section_dedup([en_group, zh_group], zh_group) == (zh_group, [1])
    assert simulate_auto_section_dedup([zh_group, en_group], zh_group) == (zh_group, [2])
    assert simulate_auto_section_dedup([en_group, en_group], zh_group) == (zh_group, [2])
    assert simulate_auto_section_dedup([zh_group, zh_group], en_group) == (en_group, [2])

    assert_source_shape()
    print("OK")


if __name__ == "__main__":
    main()
