from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .analysis import blueprint_metrics, iter_blueprint_text_files
from .codec import make_blueprint_wrapper, save_blueprint_file
from .generate import icon
from .layout_plan import build_layout_plan, mapping_by_fingerprint
from .production_dag import (
    build_production_plan,
    default_boundary_items,
    template_options_from_mappings,
)
from .prototypes import load_data_raw
from .template_knowledge import map_template_library


DIR_EAST = 2


def materialized_entity(raw: dict[str, Any], entity_number: int, *, x: float, y: float) -> dict[str, Any]:
    entity: dict[str, Any] = {
        "entity_number": entity_number,
        "name": raw["name"],
        "position": {
            "x": round(x + float(raw["x"]), 3),
            "y": round(y + float(raw["y"]), 3),
        },
    }
    if raw.get("direction") is not None:
        entity["direction"] = int(raw["direction"])
    if raw.get("recipe"):
        entity["recipe"] = raw["recipe"]
    if raw.get("recipe_quality"):
        entity["recipe_quality"] = raw["recipe_quality"]
    if raw.get("quality"):
        entity["quality"] = raw["quality"]
    return entity


def entity_position_key(entity: dict[str, Any]) -> tuple[float, float]:
    position = entity.get("position") or {}
    return (round(float(position.get("x", 0)), 3), round(float(position.get("y", 0)), 3))


def connector_belt(entity_number: int, x: float, y: float) -> dict[str, Any]:
    return {
        "entity_number": entity_number,
        "name": "transport-belt",
        "position": {"x": round(x, 3), "y": round(y, 3)},
        "direction": DIR_EAST,
    }


def materialized_tile(raw: dict[str, Any], *, x: float, y: float) -> dict[str, Any]:
    return {
        "name": raw["name"],
        "position": {
            "x": round(x + float(raw["x"]), 3),
            "y": round(y + float(raw["y"]), 3),
        },
    }


def add_boundary_connectors(
    entities: list[dict[str, Any]],
    layout_plan: dict[str, Any],
    *,
    occupied: set[tuple[float, float]],
) -> dict[str, Any]:
    connectors: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    if not layout_plan.get("nodes"):
        return {"connectors_added": 0, "collisions": collisions}

    root = layout_plan["nodes"][0]
    y = round(float(root["y"]) + float(root["source_height"]) / 2, 3)
    left_start = 0
    left_end = int(max(0, float(root["x"]) - 1))
    right_start = int(float(root["x"]) + float(root["planned_width"]) + 1)
    right_end = int(max(right_start - 1, float(layout_plan["estimated_width"]) - 1))

    planned_positions: list[tuple[float, float, str]] = []
    for boundary in layout_plan.get("boundary_inputs") or []:
        for x in range(left_start, left_end + 1):
            planned_positions.append((float(x), y, f"input:{boundary['item']}"))
    for boundary in layout_plan.get("boundary_outputs") or []:
        for x in range(right_start, right_end + 1):
            planned_positions.append((float(x), y, f"output:{boundary['item']}"))

    for x, belt_y, reason in planned_positions:
        key = (round(x, 3), round(belt_y, 3))
        if key in occupied:
            collisions.append({"x": key[0], "y": key[1], "reason": reason})
            continue
        belt = connector_belt(len(entities) + len(connectors) + 1, x, belt_y)
        connectors.append(belt)
        occupied.add(key)

    entities.extend(connectors)
    return {"connectors_added": len(connectors), "collisions": collisions}


def materialize_layout_with_summary(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping_index = mapping_by_fingerprint(mappings)
    entities: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    tile_positions: set[tuple[str, float, float]] = set()
    for node in layout_plan["nodes"]:
        mapping = mapping_index.get(str(node["fingerprint"])) or {}
        layout = mapping.get("layout") or {}
        template_entities = layout.get("entities") or []
        template_tiles = layout.get("tiles") or []
        if not template_entities and not template_tiles:
            continue
        source_width = float(node["source_width"])
        source_height = float(node["source_height"])
        spacing = float(layout_plan["spacing"])
        for instance in range(int(node["instances"])):
            col = instance % int(node["columns"])
            row = instance // int(node["columns"])
            origin_x = float(node["x"]) + col * (source_width + spacing)
            origin_y = float(node["y"]) + row * (source_height + spacing)
            for raw in template_entities:
                entities.append(
                    materialized_entity(
                        raw,
                        len(entities) + 1,
                        x=origin_x,
                        y=origin_y,
                    )
                )
            for raw in template_tiles:
                tile = materialized_tile(raw, x=origin_x, y=origin_y)
                position = tile["position"]
                key = (tile["name"], float(position["x"]), float(position["y"]))
                if key in tile_positions:
                    continue
                tile_positions.add(key)
                tiles.append(tile)

    connector_result = {"connectors_added": 0, "collisions": []}
    if connect_boundaries:
        occupied = {entity_position_key(entity) for entity in entities}
        connector_result = add_boundary_connectors(entities, layout_plan, occupied=occupied)

    target_item = str(layout_plan["target_item"])
    wrapper = make_blueprint_wrapper(
        label or f"blueprint-lab-{target_item}-{layout_plan['target_rate_per_minute']:g}-per-min",
        entities,
        tiles=tiles,
        icons=[icon(target_item)],
        description=(
            "Blueprint Lab materialized skeleton from learned templates. "
            "Connector belts, pipes, power, modules, and in-game validation are still required before production use."
        ),
    )
    return wrapper, connector_result


def materialize_layout(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
) -> dict[str, Any]:
    wrapper, _ = materialize_layout_with_summary(
        layout_plan,
        mappings,
        label=label,
        connect_boundaries=connect_boundaries,
    )
    return wrapper


def build_materialized_blueprint(
    mappings: list[dict[str, Any]],
    *,
    target_item: str,
    target_rate_per_minute: float,
    target_recipe: str | None = None,
    max_depth: int = 4,
    boundary_items: set[str] | None = None,
    max_columns: int = 8,
    spacing: float = 2.0,
    lane_width: float = 4.0,
    label: str | None = None,
    connect_boundaries: bool = False,
) -> dict[str, Any]:
    production_plan = build_production_plan(
        mappings,
        target_item=target_item,
        target_rate_per_minute=target_rate_per_minute,
        target_recipe=target_recipe,
        max_depth=max_depth,
        boundary_items=boundary_items,
    )
    layout = build_layout_plan(
        production_plan,
        mappings,
        max_columns=max_columns,
        spacing=spacing,
        lane_width=lane_width,
    )
    return materialize_layout(layout, mappings, label=label, connect_boundaries=connect_boundaries)


def render_summary(wrapper: dict[str, Any], layout: dict[str, Any], connector_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    blueprint = wrapper["blueprint"]
    metrics = blueprint_metrics("/", blueprint)
    return {
        "label": blueprint.get("label"),
        "target_item": layout["target_item"],
        "target_rate_per_minute": layout["target_rate_per_minute"],
        "entity_count": metrics.entity_count,
        "tile_count": metrics.tile_count,
        "width": metrics.width,
        "height": metrics.height,
        "density": metrics.density,
        "layout_estimated_width": layout["estimated_width"],
        "layout_estimated_height": layout["estimated_height"],
        "boundary_inputs": layout["boundary_inputs"],
        "boundary_outputs": layout["boundary_outputs"],
        "connector_summary": connector_summary or {"connectors_added": 0, "collisions": []},
        "lessons": [
            "Materialization copies learned local template geometry into the planned rectangle instead of inventing machines from scratch.",
            "Boundary connectors are generated only in reserved lanes and checked for exact entity-position collisions.",
            "The generated blueprint is still not production-ready: pipe routing, power, module item stacks, full belt routing, and in-game validation remain separate steps.",
        ],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Materialization Report",
        "",
        f"- Label: {summary['label']}",
        f"- Target item: {summary['target_item']}",
        f"- Target rate: {summary['target_rate_per_minute']:g}/min",
        f"- Entities: {summary['entity_count']}",
        f"- Tiles: {summary['tile_count']}",
        f"- Connector belts: {summary['connector_summary']['connectors_added']}",
        f"- Connector collisions: {len(summary['connector_summary']['collisions'])}",
        f"- Blueprint bounds: {summary['width']:g} x {summary['height']:g}",
        f"- Layout estimate: {summary['layout_estimated_width']:g} x {summary['layout_estimated_height']:g}",
        f"- Density: {summary['density']:g}",
        "",
        "## Boundary Inputs",
        "",
    ]
    if summary["boundary_inputs"]:
        for item in summary["boundary_inputs"]:
            lines.append(f"- {item['item']}: {item['rate_per_minute']:g}/min side={item['side']} reason={item['reason']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Boundary Outputs", ""])
    for item in summary["boundary_outputs"]:
        lines.append(f"- {item['item']}: {item['rate_per_minute']:g}/min side={item['side']}")
    if summary["connector_summary"]["collisions"]:
        lines.extend(["", "## Connector Collisions", ""])
        for item in summary["connector_summary"]["collisions"]:
            lines.append(f"- ({item['x']}, {item['y']}) reason={item['reason']}")
    lines.extend(["", "## Generator Implications", ""])
    for lesson in summary["lessons"]:
        lines.append(f"- {lesson}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize a learned-template layout plan into a blueprint skeleton.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--data-raw-json", type=Path, required=True)
    parser.add_argument("--target-item", required=True)
    parser.add_argument("--target-rate-per-minute", type=float, required=True)
    parser.add_argument("--target-recipe")
    parser.add_argument("--external-item", action="append", default=[])
    parser.add_argument("--no-default-boundary-items", action="store_true")
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--max-columns", type=int, default=8)
    parser.add_argument("--spacing", type=float, default=2.0)
    parser.add_argument("--lane-width", type=float, default=4.0)
    parser.add_argument("--label")
    parser.add_argument("--connect-boundaries", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    knowledge = load_data_raw(args.data_raw_json)
    template_summary = map_template_library(files, knowledge=knowledge, top=args.top, cell_size=args.cell_size)
    boundary_items = set(args.external_item)
    if not args.no_default_boundary_items:
        boundary_items.update(default_boundary_items(template_options_from_mappings(template_summary["mappings"])))
    production_plan = build_production_plan(
        template_summary["mappings"],
        target_item=args.target_item,
        target_rate_per_minute=args.target_rate_per_minute,
        target_recipe=args.target_recipe,
        max_depth=args.max_depth,
        boundary_items=boundary_items,
    )
    layout = build_layout_plan(
        production_plan,
        template_summary["mappings"],
        max_columns=args.max_columns,
        spacing=args.spacing,
        lane_width=args.lane_width,
    )
    wrapper, connector_summary = materialize_layout_with_summary(
        layout,
        template_summary["mappings"],
        label=args.label,
        connect_boundaries=args.connect_boundaries,
    )
    save_blueprint_file(args.output, wrapper)
    summary = render_summary(wrapper, layout, connector_summary)
    summary["output"] = str(args.output)
    summary["template_mapping_status_counts"] = template_summary["status_counts"]
    summary["template_mapping_failed_files"] = template_summary["failed_files"]

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(summary), encoding="utf-8")

    print(render_markdown_report(summary))
    print(f"Wrote {args.output}")
    return 0 if not template_summary["failed_files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
