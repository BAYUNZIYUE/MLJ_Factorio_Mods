from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .production_dag import (
    build_production_plan,
    default_boundary_items,
    template_options_from_mappings,
)
from .prototypes import load_data_raw
from .prototypes import target_rate_basis_from_args
from .template_knowledge import map_template_library


@dataclass(frozen=True)
class LayoutNode:
    item: str
    recipe: str
    fingerprint: str
    instances: int
    source_width: float
    source_height: float
    source_entity_count: int
    source_tile_count: int
    columns: int
    rows: int
    planned_width: float
    planned_height: float
    x: float
    y: float
    ports: list[dict[str, Any]]
    port_counts: list[tuple[str, int]]
    source: str
    path: str
    rate_basis: str
    planned_net_output_per_minute: float
    direct_module_effects: list[tuple[str, float]]
    direct_module_items: list[tuple[str, str, int]]
    rate_module_effects: list[tuple[str, float]]
    rate_module_items: list[tuple[str, str, int]]


def mapping_by_fingerprint(mappings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(mapping["fingerprint"]): mapping for mapping in mappings}


def flatten_plan_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    if node.get("reason"):
        return []
    nodes = [node]
    for child in node.get("children") or []:
        nodes.extend(flatten_plan_nodes(child))
    return nodes


def choose_repeated_columns(
    *,
    instances: int,
    max_columns: int,
    source_width: float,
    source_height: float,
    spacing: float,
    row_spacing: float | None = None,
    lane_width: float = 4.0,
) -> int:
    """Pick a copy grid that favors reusable straight buses over sparse tail rows."""
    effective_row_spacing = spacing if row_spacing is None else row_spacing
    max_candidate = max(1, min(max_columns, instances))
    best: tuple[float, float, float, int] | None = None
    best_columns = max_candidate
    for columns in range(1, max_candidate + 1):
        rows = max(1, math.ceil(instances / columns))
        row_counts = [min(columns, max(0, instances - row * columns)) for row in range(rows)]
        empty_cells = columns * rows - instances
        bridge_segments = sum(max(0, count - 1) for count in row_counts)
        boundary_routes = rows * 2
        incomplete_output_span = sum((columns - count) * (source_width + spacing) for count in row_counts if count)
        connector_estimate = bridge_segments * 2 + boundary_routes * lane_width + incomplete_output_span
        planned_width = columns * source_width + max(0, columns - 1) * spacing
        planned_height = rows * source_height + max(0, rows - 1) * effective_row_spacing
        area = (planned_width + lane_width * 2) * (planned_height + lane_width)
        score = (
            connector_estimate,
            empty_cells,
            area,
            rows,
        )
        if best is None or score < best:
            best = score
            best_columns = columns
    return best_columns


def node_layout(
    node: dict[str, Any],
    mapping: dict[str, Any],
    *,
    x: float,
    y: float,
    max_columns: int,
    spacing: float,
    row_spacing: float | None = None,
    lane_width: float = 4.0,
) -> LayoutNode:
    effective_row_spacing = spacing if row_spacing is None else row_spacing
    layout = mapping.get("layout") or {}
    source_width = float(layout.get("width") or mapping.get("cell_size") or 1)
    source_height = float(layout.get("height") or mapping.get("cell_size") or 1)
    instances = int(node["instances"])
    columns = choose_repeated_columns(
        instances=instances,
        max_columns=max_columns,
        source_width=source_width,
        source_height=source_height,
        spacing=spacing,
        row_spacing=effective_row_spacing,
        lane_width=lane_width,
    )
    rows = max(1, math.ceil(instances / columns))
    planned_width = columns * source_width + max(0, columns - 1) * spacing
    planned_height = rows * source_height + max(0, rows - 1) * effective_row_spacing
    return LayoutNode(
        item=str(node["item"]),
        recipe=str(node["recipe"]),
        fingerprint=str(node["fingerprint"]),
        instances=instances,
        source_width=source_width,
        source_height=source_height,
        source_entity_count=int(layout.get("entity_count") or 0),
        source_tile_count=int(layout.get("tile_count") or 0),
        columns=columns,
        rows=rows,
        planned_width=round(planned_width, 3),
        planned_height=round(planned_height, 3),
        x=round(x, 3),
        y=round(y, 3),
        ports=list(layout.get("ports") or []),
        port_counts=[tuple(item) for item in layout.get("port_counts") or []],
        source=str(node.get("source") or ""),
        path=str(node.get("path") or ""),
        rate_basis=str(node.get("rate_basis") or ""),
        planned_net_output_per_minute=float(node.get("planned_net_output_per_minute") or 0.0),
        direct_module_effects=[tuple(item) for item in node.get("direct_module_effects") or []],
        direct_module_items=[tuple(item) for item in node.get("direct_module_items") or []],
        rate_module_effects=[tuple(item) for item in node.get("rate_module_effects") or []],
        rate_module_items=[tuple(item) for item in node.get("rate_module_items") or []],
    )


def build_layout_plan(
    production_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    max_columns: int = 12,
    spacing: float = 2.0,
    row_spacing: float | None = None,
    lane_width: float = 4.0,
) -> dict[str, Any]:
    effective_row_spacing = spacing if row_spacing is None else row_spacing
    mapping_index = mapping_by_fingerprint(mappings)
    nodes = flatten_plan_nodes(production_plan["root"])
    layout_nodes: list[LayoutNode] = []
    cursor_y = lane_width
    content_width = 0.0
    for node in nodes:
        mapping = mapping_index.get(str(node["fingerprint"])) or {}
        planned = node_layout(
            node,
            mapping,
            x=lane_width,
            y=cursor_y,
            max_columns=max_columns,
            spacing=spacing,
            row_spacing=effective_row_spacing,
            lane_width=lane_width,
        )
        layout_nodes.append(planned)
        cursor_y += planned.planned_height + effective_row_spacing
        content_width = max(content_width, planned.planned_width)

    content_height = max(0.0, cursor_y - effective_row_spacing)
    overall_width = content_width + lane_width * 2
    overall_height = content_height + lane_width
    external_inputs = production_plan.get("external_inputs") or []
    output_item = production_plan["target_item"]
    return {
        "target_item": production_plan["target_item"],
        "target_rate_per_minute": production_plan["target_rate_per_minute"],
        "target_rate_basis": production_plan.get("target_rate_basis") or {
            "kind": "explicit-rate",
            "rate_per_minute": production_plan["target_rate_per_minute"],
        },
        "max_columns": max_columns,
        "spacing": spacing,
        "row_spacing": effective_row_spacing,
        "lane_width": lane_width,
        "layout_node_count": len(layout_nodes),
        "estimated_width": round(overall_width, 3),
        "estimated_height": round(overall_height, 3),
        "estimated_area": round(overall_width * overall_height, 3),
        "nodes": [asdict(node) for node in layout_nodes],
        "boundary_inputs": [
            {
                "item": item["item"],
                "rate_per_minute": item["rate_per_minute"],
                "side": "left",
                "reason": item["reason"],
            }
            for item in external_inputs
        ],
        "boundary_outputs": [
            {
                "item": output_item,
                "rate_per_minute": production_plan["target_rate_per_minute"],
                "side": "right",
            }
        ],
        "lessons": [
            "The first layout pass stacks DAG units into a long rectangle because the corpus black boxes favored long straight buses over square packing.",
            "Each production node is packed as repeated copies of one learned template; this preserves local proven geometry before solving global routing.",
            "Left boundary inputs and right boundary outputs make the black-box contract explicit before belt, pipe, and power routing are generated.",
            "This is still a layout plan, not a final blueprint: it estimates module rectangles and boundary lanes, but does not place connecting belts or resolve collisions.",
        ],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    target_rate_basis = summary.get("target_rate_basis") or {}
    lines = [
        "# Blueprint Layout Plan Report",
        "",
        f"- Target item: {summary['target_item']}",
        f"- Target rate: {summary['target_rate_per_minute']:g}/min",
        f"- Target rate basis: {render_target_rate_basis(target_rate_basis)}",
        f"- Estimated rectangle: {summary['estimated_width']:g} x {summary['estimated_height']:g}",
        f"- Estimated area: {summary['estimated_area']:g}",
        f"- Layout nodes: {summary['layout_node_count']}",
        "",
        "## Layout Nodes",
        "",
    ]
    for node in summary["nodes"]:
        lines.append(
            f"- {node['item']} / {node['recipe']} template={node['fingerprint']} "
            f"instances={node['instances']} grid={node['columns']}x{node['rows']} "
            f"unit={node['source_width']:g}x{node['source_height']:g} "
            f"planned={node['planned_width']:g}x{node['planned_height']:g} at=({node['x']:g},{node['y']:g}) "
            f"basis={node['rate_basis']} planned_net={node['planned_net_output_per_minute']:g}/min"
        )
        if node["port_counts"]:
            ports = ", ".join(f"{name}:{count}" for name, count in node["port_counts"])
            lines.append(f"  ports={ports}")
        if node["rate_module_items"]:
            modules = ", ".join(
                f"{count}x {quality} {name}"
                for name, quality, count in node["rate_module_items"]
            )
            lines.append(f"  rate_modules={modules}")
        if node["rate_module_effects"]:
            effects = ", ".join(f"{name}:{value:g}" for name, value in node["rate_module_effects"])
            lines.append(f"  rate_module_effects={effects}")
        lines.append(f"  source={node['source']} path={node['path']}")

    lines.extend(["", "## Boundary Inputs", ""])
    if summary["boundary_inputs"]:
        for item in summary["boundary_inputs"]:
            lines.append(
                f"- {item['item']}: {item['rate_per_minute']:g}/min side={item['side']} reason={item['reason']}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Boundary Outputs", ""])
    for item in summary["boundary_outputs"]:
        lines.append(f"- {item['item']}: {item['rate_per_minute']:g}/min side={item['side']}")

    lines.extend(["", "## Generator Implications", ""])
    for lesson in summary["lessons"]:
        lines.append(f"- {lesson}")
    return "\n".join(lines) + "\n"


def render_target_rate_basis(target_rate_basis: dict[str, Any]) -> str:
    if target_rate_basis.get("kind") == "full-belt":
        return (
            f"{target_rate_basis['belt_count']}x {target_rate_basis['belt_name']} full belt "
            f"({target_rate_basis['items_per_second_per_belt']:g}/s each)"
        )
    return "explicit rate"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn a production DAG seed into a rectangular layout plan.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--data-raw-json", type=Path, required=True)
    parser.add_argument("--target-item", required=True)
    parser.add_argument("--target-rate-per-minute", type=float)
    parser.add_argument("--target-belt")
    parser.add_argument("--target-belt-count", type=int, default=1)
    parser.add_argument("--target-recipe")
    parser.add_argument("--external-item", action="append", default=[])
    parser.add_argument("--no-default-boundary-items", action="store_true")
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--max-columns", type=int, default=12)
    parser.add_argument("--spacing", type=float, default=2.0)
    parser.add_argument("--row-spacing", type=float, help="Vertical spacing between repeated template rows. Defaults to --spacing.")
    parser.add_argument("--lane-width", type=float, default=4.0)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    knowledge = load_data_raw(args.data_raw_json)
    try:
        target_rate_per_minute, target_rate_basis = target_rate_basis_from_args(
            knowledge,
            target_rate_per_minute=args.target_rate_per_minute,
            target_belt=args.target_belt,
            target_belt_count=args.target_belt_count,
        )
    except ValueError as error:
        parser.error(str(error))
    template_summary = map_template_library(files, knowledge=knowledge, top=args.top, cell_size=args.cell_size)
    boundary_items = set(args.external_item)
    if not args.no_default_boundary_items:
        boundary_items.update(default_boundary_items(template_options_from_mappings(template_summary["mappings"])))
    production_plan = build_production_plan(
        template_summary["mappings"],
        target_item=args.target_item,
        target_rate_per_minute=target_rate_per_minute,
        target_rate_basis=target_rate_basis,
        target_recipe=args.target_recipe,
        max_depth=args.max_depth,
        boundary_items=boundary_items,
    )
    summary = build_layout_plan(
        production_plan,
        template_summary["mappings"],
        max_columns=args.max_columns,
        spacing=args.spacing,
        row_spacing=args.row_spacing,
        lane_width=args.lane_width,
    )
    summary["production_node_count"] = production_plan["node_count"]
    summary["template_mapping_status_counts"] = template_summary["status_counts"]
    summary["template_mapping_failed_files"] = template_summary["failed_files"]
    summary["template_count"] = template_summary["template_count"]
    summary["file_count"] = template_summary["file_count"]

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(summary), encoding="utf-8")

    print(render_markdown_report(summary))
    return 0 if not template_summary["failed_files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
