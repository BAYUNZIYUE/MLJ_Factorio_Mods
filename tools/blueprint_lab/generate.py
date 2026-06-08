from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .codec import encode_blueprint_string, make_blueprint_wrapper, save_blueprint_file


DIR_NORTH = 0
DIR_EAST = 2
DIR_SOUTH = 4
DIR_WEST = 6


class EntityBuilder:
    def __init__(self) -> None:
        self.entities: list[dict[str, Any]] = []

    def add(self, name: str, x: float, y: float, *, direction: int | None = None, **extra: Any) -> None:
        entity: dict[str, Any] = {
            "entity_number": len(self.entities) + 1,
            "name": name,
            "position": {"x": x, "y": y},
        }
        if direction is not None:
            entity["direction"] = direction
        entity.update(extra)
        self.entities.append(entity)


def icon(name: str, index: int = 1, signal_type: str = "item") -> dict[str, Any]:
    return {"index": index, "signal": {"type": signal_type, "name": name}}


def generate_iron_plate_blackbox_seed(furnace_pairs: int = 8) -> dict[str, Any]:
    """Generate a rectangular ore-to-plate seed blueprint.

    This is intentionally a seed, not an optimized final factory. It gives later
    optimization passes a stable black-box boundary: ore enters on the left,
    plates leave on the right, and repeated furnace pairs fill the rectangle.
    """

    if furnace_pairs < 1:
        raise ValueError("furnace_pairs must be positive")

    b = EntityBuilder()
    height = furnace_pairs * 3 + 1
    for y in range(height):
        b.add("transport-belt", -2, y, direction=DIR_SOUTH)
        b.add("transport-belt", 7, y, direction=DIR_SOUTH)

    for index in range(furnace_pairs):
        y = index * 3 + 1
        for x in (-1, 6):
            b.add("small-electric-pole", x, y)

        b.add("inserter", -1, y, direction=DIR_EAST)
        b.add("stone-furnace", 1, y)
        b.add("inserter", 3, y, direction=DIR_EAST)
        b.add("transport-belt", 4, y, direction=DIR_EAST)
        b.add("transport-belt", 5, y, direction=DIR_EAST)

        b.add("inserter", 6, y + 1, direction=DIR_WEST)
        b.add("stone-furnace", 4, y + 1)
        b.add("inserter", 2, y + 1, direction=DIR_WEST)
        b.add("transport-belt", 0, y + 1, direction=DIR_WEST)
        b.add("transport-belt", 1, y + 1, direction=DIR_WEST)

    return make_blueprint_wrapper(
        "blackbox-seed-iron-plate",
        b.entities,
        icons=[icon("iron-plate")],
        description=(
            "Blueprint Lab seed: rectangular ore-to-plate black-box boundary. "
            "Generated offline; run an in-game import/build test before treating it as production-ready."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate seed Factorio blueprints.")
    sub = parser.add_subparsers(dest="command", required=True)

    iron = sub.add_parser("iron-plate-seed", help="Generate a rectangular ore-to-plate seed blueprint.")
    iron.add_argument("--furnace-pairs", type=int, default=8)
    iron.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "iron-plate-seed":
        wrapper = generate_iron_plate_blackbox_seed(args.furnace_pairs)
        save_blueprint_file(args.output, wrapper)
        print(f"Wrote {args.output} ({len(encode_blueprint_string(wrapper))} chars)")
        return 0

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

