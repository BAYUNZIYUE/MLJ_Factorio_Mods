#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_VERSIONS = {
    "DynamicInventory": "1.0.5",
    "expend-toolbar": "1.0.1",
    "py_quick_start": "3.0.3",
    "quality-cycler": "1.0.2",
    "section-autocraft": "1.0.7",
    "ups_saving_quality_ships": "1.1.5",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def discover_mod_infos() -> list[Path]:
    return sorted(
        path
        for path in ROOT.glob("*/src/info.json")
        if path.parts[-3] in EXPECTED_VERSIONS
    )


def changelog_top_version(mod_root: Path) -> str | None:
    changelog = mod_root / "src" / "changelog.txt"
    text = changelog.read_text(encoding="utf-8")
    match = re.search(r"^Version:\s+([0-9]+\.[0-9]+\.[0-9]+)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def main() -> int:
    info_paths = discover_mod_infos()
    discovered_mod_roots = {path.parts[-3] for path in info_paths}
    missing = sorted(set(EXPECTED_VERSIONS) - discovered_mod_roots)
    if missing:
        return fail(f"missing expected mod info.json files: {missing}")

    for info_path in info_paths:
        mod_root = info_path.parents[1]
        mod_dir = mod_root.name
        info = json.loads(info_path.read_text(encoding="utf-8"))
        expected_version = EXPECTED_VERSIONS[mod_dir]

        if info.get("factorio_version") != "2.1":
            return fail(f"{info_path.relative_to(ROOT)} factorio_version must be 2.1")
        if info.get("version") != expected_version:
            return fail(f"{info_path.relative_to(ROOT)} version must be {expected_version}")
        if changelog_top_version(mod_root) != expected_version:
            return fail(f"{mod_dir}/src/changelog.txt top version must be {expected_version}")

    expend_info = json.loads((ROOT / "expend-toolbar" / "src" / "info.json").read_text(encoding="utf-8"))
    if "base >= 2.1" not in expend_info.get("dependencies", []):
        return fail("expend-toolbar must require base >= 2.1")

    ships_info = json.loads((ROOT / "ups_saving_quality_ships" / "src" / "info.json").read_text(encoding="utf-8"))
    ships_dependencies = ships_info.get("dependencies", [])
    if "space-age" not in ships_dependencies or "quality" not in ships_dependencies:
        return fail("ups_saving_quality_ships must explicitly depend on both space-age and quality")

    autocraft = (ROOT / "section-autocraft" / "src" / "autocraft.lua").read_text(encoding="utf-8")
    if "section.set_slot(build_missing_material_slot(request), slot_index)" not in autocraft:
        return fail("section-autocraft must use the Factorio 2.1 LuaLogisticSection.set_slot(filter, slot_index) signature")
    if "section.set_slot(slot_index, build_missing_material_slot(request))" in autocraft:
        return fail("section-autocraft still uses the old LuaLogisticSection.set_slot(slot_index, filter) order")

    print("PASS: all packaged mods declare Factorio 2.1 support and 2.1 API guards are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
