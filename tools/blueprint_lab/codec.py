from __future__ import annotations

import base64
import json
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_VERSION = 562949958402048


class BlueprintCodecError(ValueError):
    """Raised when a blueprint string cannot be decoded as Factorio JSON."""


@dataclass(frozen=True)
class BlueprintNode:
    path: str
    kind: str
    payload: dict[str, Any]


def decode_blueprint_string(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        raise BlueprintCodecError("empty blueprint string")

    if text[0] == "{":
        obj = json.loads(text)
    elif text[0] == "0":
        try:
            data = base64.b64decode(text[1:])
            obj = json.loads(zlib.decompress(data))
        except Exception as exc:  # noqa: BLE001
            raise BlueprintCodecError(f"invalid compressed blueprint string: {exc}") from exc
    else:
        raise BlueprintCodecError("blueprint string must start with '0' or '{'")

    if not isinstance(obj, dict) or not any(
        key in obj for key in ("blueprint", "blueprint_book", "upgrade_planner", "deconstruction_planner")
    ):
        raise BlueprintCodecError("decoded JSON is not a blueprint wrapper")
    return obj


def encode_blueprint_string(obj: dict[str, Any]) -> str:
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")
    return "0" + base64.b64encode(zlib.compress(body, level=9)).decode("ascii")


def load_blueprint_file(path: Path) -> dict[str, Any]:
    return decode_blueprint_string(path.read_text(encoding="utf-8-sig", errors="strict"))


def save_blueprint_file(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encode_blueprint_string(obj), encoding="utf-8")


def walk_nodes(wrapper: dict[str, Any], path: str = "") -> Iterator[BlueprintNode]:
    if "blueprint" in wrapper:
        yield BlueprintNode(path=path or "/", kind="blueprint", payload=wrapper["blueprint"])
        return

    if "upgrade_planner" in wrapper:
        yield BlueprintNode(path=path or "/", kind="upgrade_planner", payload=wrapper["upgrade_planner"])
        return

    if "deconstruction_planner" in wrapper:
        yield BlueprintNode(path=path or "/", kind="deconstruction_planner", payload=wrapper["deconstruction_planner"])
        return

    book = wrapper.get("blueprint_book")
    if not isinstance(book, dict):
        return

    yield BlueprintNode(path=path or "/", kind="blueprint_book", payload=book)
    for child in book.get("blueprints") or []:
        if not isinstance(child, dict):
            continue
        child_payload = (
            child.get("blueprint")
            or child.get("blueprint_book")
            or child.get("upgrade_planner")
            or child.get("deconstruction_planner")
            or {}
        )
        label = child_payload.get("label") if isinstance(child_payload, dict) else ""
        child_path = f"{path}/{child.get('index')}:{label or ''}"
        yield from walk_nodes(child, child_path)


def make_blueprint_wrapper(
    label: str,
    entities: list[dict[str, Any]],
    *,
    tiles: list[dict[str, Any]] | None = None,
    icons: list[dict[str, Any]] | None = None,
    description: str | None = None,
    version: int = DEFAULT_VERSION,
) -> dict[str, Any]:
    blueprint: dict[str, Any] = {
        "item": "blueprint",
        "label": label,
        "version": version,
        "entities": entities,
    }
    if tiles:
        blueprint["tiles"] = tiles
    if icons:
        blueprint["icons"] = icons
    if description:
        blueprint["description"] = description
    return {"blueprint": blueprint}

