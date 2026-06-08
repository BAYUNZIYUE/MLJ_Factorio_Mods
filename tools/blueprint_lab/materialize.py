from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
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


DIR_NORTH = 0
DIR_EAST = 2
DIR_SOUTH = 4


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
    if raw.get("items"):
        entity["items"] = copy.deepcopy(raw["items"])
    return entity


def entity_position_key(entity: dict[str, Any]) -> tuple[float, float]:
    position = entity.get("position") or {}
    return (round(float(position.get("x", 0)), 3), round(float(position.get("y", 0)), 3))


def connector_belt(entity_number: int, x: float, y: float, *, direction: int = DIR_EAST) -> dict[str, Any]:
    return {
        "entity_number": entity_number,
        "name": "transport-belt",
        "position": {"x": round(x, 3), "y": round(y, 3)},
        "direction": direction,
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
    routes: list[dict[str, Any]] = []
    if not layout_plan.get("nodes"):
        return {"connectors_added": 0, "collisions": collisions, "routes": routes}

    root = layout_plan["nodes"][0]
    default_y = round(float(root["y"]) + float(root["source_height"]) / 2, 3)

    def add_positions(
        positions: list[tuple[float, float, str, int]],
        *,
        record_collisions: bool = True,
    ) -> tuple[int, list[dict[str, Any]]]:
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        for x, belt_y, reason, direction in positions:
            key = (round(x, 3), round(belt_y, 3))
            if key in seen:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"}
                route_collisions.append(collision)
                continue
            seen.add(key)
            if key in occupied:
                collision = {"x": key[0], "y": key[1], "reason": reason}
                route_collisions.append(collision)
        if route_collisions:
            if record_collisions:
                collisions.extend(route_collisions)
            return 0, route_collisions

        before = len(connectors)
        for x, belt_y, reason, direction in positions:
            key = (round(x, 3), round(belt_y, 3))
            belt = connector_belt(len(entities) + len(connectors) + 1, x, belt_y, direction=direction)
            connectors.append(belt)
            occupied.add(key)
        return len(connectors) - before, route_collisions

    def horizontal_positions(start_x: float, end_x: float, y: float, reason: str) -> list[tuple[float, float, str, int]]:
        positions: list[tuple[float, float, str, int]] = []
        x = start_x
        while x <= end_x:
            positions.append((round(x, 3), y, reason, DIR_EAST))
            x += 1.0
        return positions

    def vertical_positions(x: float, start_y: float, end_y: float, reason: str) -> list[tuple[float, float, str, int]]:
        if start_y == end_y:
            return []
        direction = DIR_SOUTH if end_y > start_y else DIR_NORTH
        step = 1.0 if end_y > start_y else -1.0
        positions: list[tuple[float, float, str, int]] = []
        y = start_y + step
        while (step > 0 and y <= end_y) or (step < 0 and y >= end_y):
            positions.append((x, round(y, 3), reason, direction))
            y += step
        return positions

    def route_candidate(
        *,
        side: str,
        start_x: float,
        end_x: float,
        y: float,
        reason: str,
        offset: int | None = None,
    ) -> tuple[str, list[tuple[float, float, str, int]]]:
        if offset is None:
            return "direct", horizontal_positions(start_x, end_x, y, reason)

        detour_y = round(y + float(offset), 3)
        if side == "right":
            positions = vertical_positions(start_x, y, detour_y, reason)
            if positions and positions[-1][0] == start_x and positions[-1][1] == detour_y:
                positions = positions[:-1]
            positions.extend(horizontal_positions(start_x, end_x, detour_y, reason))
            return f"detour-y{offset:+d}", positions

        positions = horizontal_positions(start_x, end_x, detour_y, reason)
        positions.extend(vertical_positions(end_x, detour_y, y, reason))
        return f"detour-y{offset:+d}", positions

    def add_first_clear_route(
        candidates: list[tuple[dict[str, Any], str, list[tuple[float, float, str, int]]]],
    ) -> tuple[int, list[dict[str, Any]], dict[str, Any] | None, str | None, list[dict[str, Any]]]:
        blocked_attempts: list[dict[str, Any]] = []
        for port, route_kind, positions in candidates:
            belts_added, route_collisions = add_positions(positions, record_collisions=False)
            if not route_collisions:
                return belts_added, route_collisions, port, route_kind, blocked_attempts
            blocked_attempts.append(
                {
                    "port": port,
                    "route_kind": route_kind,
                    "collisions": route_collisions,
                }
            )
        if not blocked_attempts:
            return 0, [], None, None, blocked_attempts
        last = blocked_attempts[-1]
        collisions.extend(last["collisions"])
        return 0, list(last["collisions"]), dict(last["port"]), str(last["route_kind"]), blocked_attempts

    def candidate_ports(side: str, roles: set[str]) -> list[dict[str, Any]]:
        ports: list[dict[str, Any]] = []
        for node in layout_plan.get("nodes") or []:
            for port in node.get("ports") or []:
                if port.get("side") != side or port.get("role") not in roles:
                    continue
                ports.append(
                    {
                        "node_item": node.get("item"),
                        "node_recipe": node.get("recipe"),
                        "side": port.get("side"),
                        "role": port.get("role"),
                        "entity_name": port.get("entity_name"),
                        "x": round(float(node["x"]) + float(port.get("x") or 0), 3),
                        "y": round(float(node["y"]) + float(port.get("y") or 0), 3),
                    }
                )
        return ports

    def ports_by_distance(ports: list[dict[str, Any]], y: float) -> list[dict[str, Any]]:
        return sorted(ports, key=lambda port: (abs(float(port["y"]) - y), float(port["x"])))

    for boundary in layout_plan.get("boundary_inputs") or []:
        ports = ports_by_distance(
            candidate_ports("left", {"input", "edge-bus", "boundary"}),
            default_y,
        )
        if not ports:
            left_end = int(max(0, float(root["x"]) - 1))
            positions = [
                (float(x), default_y, f"input:{boundary['item']}", DIR_EAST)
                for x in range(0, left_end + 1)
            ]
            belts_added, route_collisions = add_positions(positions)
            routes.append(
                {
                    "boundary": f"input:{boundary['item']}",
                    "status": "stub-only" if not route_collisions else "blocked",
                    "belts_added": belts_added,
                    "collisions": route_collisions,
                    "reason": "no-left-port",
                }
            )
            continue

        candidates: list[tuple[dict[str, Any], str, list[tuple[float, float, str, int]]]] = []
        reason = f"input:{boundary['item']}"
        for port in ports:
            start_x = 0.5
            end_x = float(port["x"]) - 0.5
            candidates.append((port, *route_candidate(side="left", start_x=start_x, end_x=end_x, y=float(port["y"]), reason=reason)))
            for offset in (-1, 1, -2, 2, -3, 3):
                candidates.append(
                    (port, *route_candidate(side="left", start_x=start_x, end_x=end_x, y=float(port["y"]), reason=reason, offset=offset))
                )
        belts_added, route_collisions, port, route_kind, blocked_attempts = add_first_clear_route(candidates)
        routes.append(
            {
                "boundary": f"input:{boundary['item']}",
                "status": "connected" if not route_collisions else "blocked",
                "belts_added": belts_added,
                "collisions": route_collisions,
                "port": port,
                "route_kind": route_kind,
                "blocked_attempts": blocked_attempts,
            }
        )

    for boundary in layout_plan.get("boundary_outputs") or []:
        ports = ports_by_distance(
            candidate_ports("right", {"output", "edge-bus", "boundary"}),
            default_y,
        )
        if not ports:
            right_start = int(float(root["x"]) + float(root["planned_width"]) + 1)
            right_end = int(max(right_start - 1, float(layout_plan["estimated_width"]) - 1))
            positions = [
                (float(x), default_y, f"output:{boundary['item']}", DIR_EAST)
                for x in range(right_start, right_end + 1)
            ]
            belts_added, route_collisions = add_positions(positions)
            routes.append(
                {
                    "boundary": f"output:{boundary['item']}",
                    "status": "stub-only" if not route_collisions else "blocked",
                    "belts_added": belts_added,
                    "collisions": route_collisions,
                    "reason": "no-right-port",
                }
            )
            continue

        candidates = []
        reason = f"output:{boundary['item']}"
        end_x = float(layout_plan["estimated_width"]) - 0.5
        for port in ports:
            start_x = float(port["x"]) + 1.0
            candidates.append((port, *route_candidate(side="right", start_x=start_x, end_x=end_x, y=float(port["y"]), reason=reason)))
            for offset in (-1, 1, -2, 2, -3, 3):
                candidates.append(
                    (port, *route_candidate(side="right", start_x=start_x, end_x=end_x, y=float(port["y"]), reason=reason, offset=offset))
                )
        belts_added, route_collisions, port, route_kind, blocked_attempts = add_first_clear_route(candidates)
        routes.append(
            {
                "boundary": f"output:{boundary['item']}",
                "status": "connected" if not route_collisions else "blocked",
                "belts_added": belts_added,
                "collisions": route_collisions,
                "port": port,
                "route_kind": route_kind,
                "blocked_attempts": blocked_attempts,
            }
        )

    entities.extend(connectors)
    return {"connectors_added": len(connectors), "collisions": collisions, "routes": routes}


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

    connector_result = {"connectors_added": 0, "collisions": [], "routes": []}
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
    summary = connector_summary or {"connectors_added": 0, "collisions": [], "routes": []}
    route_status_counts = Counter(route.get("status", "unknown") for route in summary.get("routes") or [])
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
        "connector_summary": summary,
        "route_status_counts": dict(route_status_counts),
        "lessons": [
            "Materialization copies learned local template geometry into the planned rectangle instead of inventing machines from scratch.",
            "Boundary connectors are generated only in reserved lanes and checked for exact entity-position collisions.",
            "The generated blueprint is still not production-ready: pipe routing, power, full belt routing, module/beacon effect modeling, and in-game validation remain separate steps.",
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
        f"- Route status counts: {summary['route_status_counts']}",
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
    if summary["connector_summary"]["routes"]:
        lines.extend(["", "## Connector Routes", ""])
        for item in summary["connector_summary"]["routes"]:
            line = f"- {item['boundary']}: status={item['status']} belts={item['belts_added']}"
            if item.get("port"):
                port = item["port"]
                line += (
                    f" port={port['node_item']}/{port['role']}/{port['entity_name']}"
                    f" at=({port['x']},{port['y']})"
                )
            if item.get("route_kind"):
                line += f" route={item['route_kind']}"
            if item.get("blocked_attempts"):
                line += f" blocked_attempts={len(item['blocked_attempts'])}"
            if item.get("reason"):
                line += f" reason={item['reason']}"
            lines.append(line)
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
