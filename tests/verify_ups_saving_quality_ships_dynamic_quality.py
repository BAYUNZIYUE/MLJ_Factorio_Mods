#!/usr/bin/env python3
from __future__ import annotations

import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "ups_saving_quality_ships" / "src" / "scripts"
LOCALE_DIR = ROOT / "ups_saving_quality_ships" / "src" / "locale"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(f"{label} missing {needle!r}")


def main() -> int:
    info = require_file(ROOT / "ups_saving_quality_ships" / "src" / "info.json")
    hub_quality = require_file(SCRIPT_DIR / "hub_quality_change.lua")
    cargo_pods = require_file(SCRIPT_DIR / "cargo_pods.lua")
    logistics = require_file(SCRIPT_DIR / "logistic_section_change.lua")
    multiplier = require_file(SCRIPT_DIR / "quality_multiplier.lua")
    locale_en = require_file(LOCALE_DIR / "en" / "locale.cfg")
    locale_zh = require_file(LOCALE_DIR / "zh-CN" / "locale.cfg")

    require_contains(hub_quality, "prototypes.quality", "hub_quality_change.lua")
    require_contains(hub_quality, "quality.next", "hub_quality_change.lua")
    require_contains(hub_quality, "next_quality", "hub_quality_change.lua")
    require_contains(hub_quality, "highest quality", "hub_quality_change.lua")
    require_contains(hub_quality, "hub_quality_changed", "hub_quality_change.lua")
    require_contains(hub_quality, 'MQS_ENTITY_CLONES_DATA_NAME = "entity-clones"', "hub_quality_change.lua")
    require_contains(hub_quality, 'HUB_ENTITY_NAME = "space-platform-hub"', "hub_quality_change.lua")
    require_contains(hub_quality, "prototypes.mod_data", "hub_quality_change.lua")
    require_contains(hub_quality, "mod_data.get(HUB_ENTITY_NAME)", "hub_quality_change.lua")
    require_contains(hub_quality, "clone_quality_from_hub_entity_name", "hub_quality_change.lua")
    require_contains(hub_quality, "hub_entity_name_for_quality(target_quality)", "hub_quality_change.lua")
    require_contains(hub_quality, "bp_entity.name = hub_entity_name_for_quality(target_quality)", "hub_quality_change.lua")
    require_contains(info, "? more-quality-scaling", "info.json")

    if 'bp_entity.quality = "uncommon"' in hub_quality:
        fail("hub_quality_change.lua must not hard-code vanilla quality steps")
    if 'bp_entity.quality = "normal"' in hub_quality:
        fail("hub_quality_change.lua must not wrap maximum quality back to normal")
    if 'elseif bp_entity.quality == "legendary"' in hub_quality:
        fail("hub_quality_change.lua must not special-case legendary as the maximum")
    if 'bp_entity.name == "space-platform-hub"' in hub_quality:
        fail("hub_quality_change.lua must not only recognize the base hub entity name")

    for label, text in (
        ("cargo_pods.lua", cargo_pods),
        ("logistic_section_change.lua", logistics),
    ):
        require_contains(text, "quality_multiplier", label)
        if "* 0.79" in text or "0.79" in text:
            fail(f"{label} must not use the old 0.79 multiplier formula")

    require_contains(multiplier, "+ 1", "quality_multiplier.lua")
    require_contains(multiplier, "quality.level", "quality_multiplier.lua")

    for label, text in (
        ("locale/en/locale.cfg", locale_en),
        ("locale/zh-CN/locale.cfg", locale_zh),
    ):
        if re.search(r"^hub_quality_\d+_\d+=", text, re.MULTILINE):
            fail(f"{label} must not keep fixed vanilla hub quality locale keys")

    print("ups_saving_quality_ships dynamic quality guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
