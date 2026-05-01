#!/usr/bin/env python3
"""天地货物流转行为回归脚本。

说明：
- 当前环境没有可直接执行模组 Lua 的解释器，因此这里分两层验证：
  1. 用完整流程模型校验下投/上传的期望结果；
  2. 用源码结构断言确认 `cargo_pods.lua` 已接入对应实现。
- 它不是 Factorio 实机测试，不能替代游戏内验证。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CARGO_PODS = ROOT / "ups_saving_quality_ships" / "src" / "scripts" / "cargo_pods.lua"
CONTROL = ROOT / "ups_saving_quality_ships" / "src" / "control.lua"


@dataclass(frozen=True)
class DownwardScenario:
    system_delivery: int
    multiplier: int
    cached_extra: int
    spaceship_have_surface: bool
    expected_total_delivery: int
    expected_extra_delivery: int
    expected_return_to_hub: int
    expected_return_to_cache: int


@dataclass(frozen=True)
class UpwardScenario:
    pod_count: int
    cached_before: int
    multiplier: int
    expected_ship_keep: int
    expected_removed_from_pod: int
    expected_cache_after: int


def split_extra_into_hub_and_cache(extra_count: int, multiplier: int, hub_capacity: int | None = None) -> tuple[int, int]:
    if extra_count <= 0:
        return 0, 0
    return_count = extra_count // multiplier
    cache_count = extra_count - return_count * multiplier
    real_insert = return_count if hub_capacity is None else min(return_count, hub_capacity)
    failed_return = return_count - real_insert
    if failed_return > 0:
        cache_count += failed_return * multiplier
    return real_insert, cache_count


def expected_downward_flow(s: DownwardScenario) -> tuple[int, int, int, int]:
    simulated_extra = s.system_delivery * (s.multiplier - 1) + s.cached_extra
    if s.spaceship_have_surface:
        returned_to_hub, returned_to_cache = split_extra_into_hub_and_cache(simulated_extra, s.multiplier)
        return s.system_delivery, 0, returned_to_hub, returned_to_cache
    return s.system_delivery + simulated_extra, simulated_extra, 0, 0


def expected_upward_flow(s: UpwardScenario) -> tuple[int, int, int]:
    total_count = s.pod_count + s.cached_before
    ship_keep = total_count // s.multiplier
    cache_after = total_count - ship_keep * s.multiplier
    removed_from_pod = s.pod_count - ship_keep
    return ship_keep, removed_from_pod, cache_after


def assert_source_shape() -> None:
    cargo_source = CARGO_PODS.read_text(encoding="utf-8")
    control_source = CONTROL.read_text(encoding="utf-8")

    required_tokens = [
        "return_extra_to_hub_or_cache",
        "local simulated_extra_count = item.count * (multiplier - 1) + cached_extra_count",
        "if spaceship_have_surface then",
        "extra_delivery_count = 0",
        "else",
        "extra_delivery_count = simulated_extra_count",
    ]
    for token in required_tokens:
        assert token in cargo_source, f"缺少关键实现标记: {token}"

    forbidden_tokens = [
        "get_requested_delivery_gap",
        "get_capped_extra_delivery_count",
        "reserve_extra_delivery",
        "release_extra_delivery_reservations",
        "storage.usqs.extra_delivery_reservations",
        "storage.usqs.extra_delivery_reservations_by_pod",
    ]
    for token in forbidden_tokens:
        assert token not in cargo_source, f"旧的按缺口封顶/预留逻辑仍然存在: {token}"

    assert "on_cargo_pod_delivered_cargo" in control_source, "control.lua 未显式分流已交付事件"
    assert "cargo_pods.on_cargo_pod_delivered" not in control_source, "交付事件不应再依赖额外下投预留释放"


def main() -> None:
    downward_scenarios = [
        DownwardScenario(
            system_delivery=100,
            multiplier=5,
            cached_extra=0,
            spaceship_have_surface=True,
            expected_total_delivery=100,
            expected_extra_delivery=0,
            expected_return_to_hub=80,
            expected_return_to_cache=0,
        ),
        DownwardScenario(
            system_delivery=101,
            multiplier=5,
            cached_extra=0,
            spaceship_have_surface=True,
            expected_total_delivery=101,
            expected_extra_delivery=0,
            expected_return_to_hub=80,
            expected_return_to_cache=4,
        ),
        DownwardScenario(
            system_delivery=100,
            multiplier=5,
            cached_extra=0,
            spaceship_have_surface=False,
            expected_total_delivery=500,
            expected_extra_delivery=400,
            expected_return_to_hub=0,
            expected_return_to_cache=0,
        ),
    ]

    for index, scenario in enumerate(downward_scenarios, start=1):
        actual = expected_downward_flow(scenario)
        expected = (
            scenario.expected_total_delivery,
            scenario.expected_extra_delivery,
            scenario.expected_return_to_hub,
            scenario.expected_return_to_cache,
        )
        assert actual == expected, f"下投模型自检失败: case {index}, actual={actual}, expected={expected}"

    upward_scenarios = [
        UpwardScenario(
            pod_count=100,
            cached_before=0,
            multiplier=5,
            expected_ship_keep=20,
            expected_removed_from_pod=80,
            expected_cache_after=0,
        ),
        UpwardScenario(
            pod_count=100,
            cached_before=1,
            multiplier=3,
            expected_ship_keep=33,
            expected_removed_from_pod=67,
            expected_cache_after=2,
        ),
        UpwardScenario(
            pod_count=100,
            cached_before=2,
            multiplier=3,
            expected_ship_keep=34,
            expected_removed_from_pod=66,
            expected_cache_after=0,
        ),
    ]

    for index, scenario in enumerate(upward_scenarios, start=1):
        actual = expected_upward_flow(scenario)
        expected = (
            scenario.expected_ship_keep,
            scenario.expected_removed_from_pod,
            scenario.expected_cache_after,
        )
        assert actual == expected, f"上传模型自检失败: case {index}, actual={actual}, expected={expected}"

    assert_source_shape()
    print("OK")


if __name__ == "__main__":
    main()
