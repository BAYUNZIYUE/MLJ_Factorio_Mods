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

    if "AUTOCRAFT_NO_CRAFTABLE_RETRY_TICKS" not in source:
        print("FAIL: missing no-craftable retry interval constant.")
        return 1

    get_requests_index = body.find("local item_requests = get_item_requests(")
    if get_requests_index == -1:
        print("FAIL: do_crafting no longer builds item requests.")
        return 1

    pick_index = body.find("pick_recipe_for_item_request(player, item_requests")
    if pick_index == -1:
        print("FAIL: do_crafting no longer performs recipe picking.")
        return 1

    guard_region = body[:get_requests_index]
    if (
        "data.next_no_craftable_retry_tick" not in guard_region
        or "game.tick < data.next_no_craftable_retry_tick" not in guard_region
        or "no_craftable_retry_wait" not in guard_region
    ):
        print(
            "FAIL: do_crafting must skip item request and recipe scans while "
            "waiting for the no-craftable retry tick."
        )
        return 1

    if (
        "data.last_no_craftable_missing_requests" not in guard_region
        or "build_missing_material_availability_signature(player, data.last_no_craftable_missing_requests)" not in guard_region
        or "no_craftable_materials_unchanged" not in guard_region
    ):
        print(
            "FAIL: do_crafting must skip full recipe scans when the cached "
            "missing-material availability signature is unchanged."
        )
        return 1

    if "local function build_missing_material_availability_signature(" not in source:
        print("FAIL: missing material availability signature helper is required.")
        return 1

    if "AUTOCRAFT_NO_CRAFTABLE_RETRY_TICKS = 180" not in source:
        print("FAIL: no-craftable retry interval must be 180 ticks.")
        return 1

    failure_region_start = body.find("local target_item_request, target_recipe_name")
    if failure_region_start == -1:
        print("FAIL: missing no-craftable fallback branch.")
        return 1

    failure_region = body[failure_region_start:]
    if "data.next_no_craftable_retry_tick = game.tick + AUTOCRAFT_NO_CRAFTABLE_RETRY_TICKS" not in failure_region:
        print("FAIL: no-craftable branch must set the next retry tick.")
        return 1

    if (
        "data.last_no_craftable_missing_requests = missing_requests" not in failure_region
        or "data.last_no_craftable_material_signature = build_missing_material_availability_signature(" not in failure_region
    ):
        print("FAIL: no-craftable branch must cache missing material availability.")
        return 1

    success_region_start = body.find("if recipe_name then")
    success_region_end = body.find("local target_item_request, target_recipe_name")
    success_region = body[success_region_start:success_region_end]
    if (
        "data.next_no_craftable_retry_tick = nil" not in success_region
        or "data.last_no_craftable_missing_requests = nil" not in success_region
        or "data.last_no_craftable_material_signature = nil" not in success_region
    ):
        print("FAIL: successful crafting must clear stale no-craftable state.")
        return 1

    print("PASS: Section Autocraft throttles repeated no-craftable recipe scans.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
