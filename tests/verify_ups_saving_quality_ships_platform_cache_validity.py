#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "ups_saving_quality_ships" / "src" / "scripts"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def extract_function(text: str, name: str) -> str:
    pattern = re.compile(
        rf"function Public\.{re.escape(name)}\(\)(.*?)(?=\nfunction Public\.|\nreturn Public)",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        fail(f"missing function Public.{name}()")
    return match.group(1)


def require_batch_guard(body: str, function_name: str) -> None:
    if "collect_valid_platform_batch" not in body:
        fail(f"{function_name} must validate fallback platform refs before using platform.index")
    if re.search(r"for _, platform in ipairs\(fallback\) do\s+if #batch >= limit then", body):
        fail(f"{function_name} still iterates fallback platforms before a validity guard")


def main() -> int:
    platform_cache = require_file(SCRIPT_DIR / "platform_cache.lua")
    logistics = require_file(SCRIPT_DIR / "logistic_section_change.lua")

    if "local function collect_valid_platform_batch" not in platform_cache:
        fail("platform_cache.lua must have one shared fallback validity filter")
    if "cache.dirty = true" not in platform_cache:
        fail("platform_cache.lua must mark the cache dirty after seeing stale platform refs")
    require_batch_guard(extract_function(platform_cache, "get_cargo_batch"), "get_cargo_batch")
    require_batch_guard(extract_function(platform_cache, "get_logistic_batch"), "get_logistic_batch")

    if "local function clear_logistic_state(logistic_state, platform)" not in logistics:
        fail("logistic_section_change.lua must centralize state cleanup behind a valid platform guard")
    if re.search(r"else\s+remove_auto_section\(platform\)\s+logistic_state\[platform\.index\] = nil", logistics):
        fail("on_60th_tick_check_logistic_sections() still reads platform.index for invalid platforms")

    print("ups_saving_quality_ships platform cache validity guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
