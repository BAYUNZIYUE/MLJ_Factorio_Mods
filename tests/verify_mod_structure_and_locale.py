#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


OWNED_MODS = {
    "DynamicInventory",
    "expend-toolbar",
    "py_quick_start",
    "quality-cycler",
    "section-autocraft",
    "ups_saving_quality_ships",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    for mod_dir in sorted(OWNED_MODS):
        info_path = ROOT / mod_dir / "src" / "info.json"
        if not info_path.is_file():
            return fail(f"{mod_dir} must keep info.json under src/")

        for lang in ("en", "zh-CN"):
            locale_path = ROOT / mod_dir / "src" / "locale" / lang / "locale.cfg"
            if mod_dir == "section-autocraft":
                locale_path = ROOT / mod_dir / "src" / "locale" / lang / "autocraft.cfg"
            if not locale_path.is_file():
                return fail(f"{mod_dir} missing {lang} locale file")
            locale = read(locale_path)
            if "[mod-name]" not in locale or "[mod-description]" not in locale:
                return fail(f"{locale_path.relative_to(ROOT)} must define [mod-name] and [mod-description]")

    py_info = json.loads(read(ROOT / "py_quick_start" / "src" / "info.json"))
    py_description = py_info.get("description", "")
    if "\n" in py_description or "给予" in py_description:
        return fail("py_quick_start info.json description must be a short English fallback")

    expected_optional = {"? DynamicInventory", "? Kux-PersonalTeleport", "? far-reach", "? section-autocraft"}
    dependencies = set(py_info.get("dependencies", []))
    missing = sorted(expected_optional - dependencies)
    if missing:
        return fail(f"py_quick_start missing recommended optional dependencies: {missing}")

    py_locale = read(ROOT / "py_quick_start" / "src" / "locale" / "en" / "locale.cfg")
    if "my-mod-string-test-setting" in py_locale:
        return fail("py_quick_start still contains old test setting locale keys")

    for stale_path in (ROOT / "more-quality-scaling", ROOT / "toolbars-mod_2.38.3"):
        if stale_path.exists():
            return fail(f"reference mod still lives at project root: {stale_path.name}")

    references_mods = ROOT / "references" / "mods"
    if references_mods.exists():
        for reference in ("more-quality-scaling", "toolbars-mod_2.38.3"):
            if not (references_mods / reference / "info.json").is_file():
                return fail(f"missing moved reference mod: references/mods/{reference}")

    gitignore = read(ROOT / ".gitignore")
    if "references/" not in gitignore:
        return fail(".gitignore must ignore references/")

    print("PASS: mod structure, locale ownership, and reference directory rules are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
