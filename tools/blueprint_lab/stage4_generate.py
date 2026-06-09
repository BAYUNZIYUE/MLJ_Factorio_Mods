from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .codec import save_blueprint_file
from .layout_plan import build_layout_plan
from .materialize import render_markdown_report as render_materialize_markdown_report
from .materialize import render_summary, select_best_materialized_layout
from .production_dag import build_production_plan, default_boundary_items, template_options_from_mappings
from .prototypes import load_data_raw, target_rate_basis_from_args
from .runtime_proof import build_runtime_proof, render_markdown_report as render_runtime_proof_markdown_report
from .stage4_report import build_stage4_report, render_markdown_report as render_stage4_markdown_report
from .template_knowledge import map_template_library


def build_stage4_generation_package(
    blueprint_paths: list[Path],
    *,
    data_raw_json: Path,
    target_item: str,
    target_rate_per_minute: float | None = None,
    target_belt: str | None = None,
    target_belt_count: int = 1,
    target_recipe: str | None = None,
    external_items: list[str] | None = None,
    no_default_boundary_items: bool = False,
    top: int = 8,
    cell_size: int = 16,
    max_depth: int = 4,
    max_columns: int = 12,
    spacing: float = 2.0,
    row_spacing: float | None = None,
    lane_width: float = 4.0,
    label: str | None = None,
    connect_boundaries: bool = True,
    allow_new_drop_belts: bool = False,
    max_output_expansions_per_machine: int = 4,
    force_columns: int | None = None,
    output_separation_min_distance: float = 1.0,
    compress_output_boundary: bool = False,
    runtime_log: Path | None = None,
) -> dict[str, Any]:
    knowledge = load_data_raw(data_raw_json)
    target_rate, target_rate_basis = target_rate_basis_from_args(
        knowledge,
        target_rate_per_minute=target_rate_per_minute,
        target_belt=target_belt,
        target_belt_count=target_belt_count,
    )
    stage4_report = build_stage4_report(
        blueprint_paths,
        top=top,
        data_raw_json=data_raw_json,
        cell_size=cell_size,
    )
    template_summary = map_template_library(blueprint_paths, knowledge=knowledge, top=top, cell_size=cell_size)
    options_by_item = template_options_from_mappings(template_summary["mappings"])
    boundary_items = set(external_items or [])
    if not no_default_boundary_items:
        boundary_items.update(default_boundary_items(options_by_item))

    production_plan = build_production_plan(
        template_summary["mappings"],
        target_item=target_item,
        target_rate_per_minute=target_rate,
        target_rate_basis=target_rate_basis,
        target_recipe=target_recipe,
        max_depth=max_depth,
        boundary_items=boundary_items,
    )
    layout = build_layout_plan(
        production_plan,
        template_summary["mappings"],
        max_columns=max_columns,
        spacing=spacing,
        row_spacing=row_spacing,
        lane_width=lane_width,
    )
    wrapper, connector_summary, selected_layout = select_best_materialized_layout(
        layout,
        template_summary["mappings"],
        label=label,
        connect_boundaries=connect_boundaries,
        knowledge=knowledge,
        allow_new_drop_belts=allow_new_drop_belts,
        max_output_expansions_per_machine=max_output_expansions_per_machine,
        force_columns=force_columns,
        output_separation_min_distance=output_separation_min_distance,
        compress_output_boundary=compress_output_boundary,
    )
    materialized_summary = render_summary(wrapper, selected_layout, connector_summary, knowledge=knowledge)
    materialized_summary["template_mapping_status_counts"] = template_summary["status_counts"]
    materialized_summary["template_mapping_failed_files"] = template_summary["failed_files"]
    package = {
        "stage4_report": stage4_report,
        "blueprint": wrapper,
        "materialized_summary": materialized_summary,
        "template_mapping_status_counts": template_summary["status_counts"],
        "template_mapping_failed_files": template_summary["failed_files"],
    }
    if runtime_log is not None:
        package["runtime_proof"] = build_runtime_proof(
            runtime_log,
            target_item=target_item,
            target_rate_per_minute=target_rate,
        )
    return package


def package_summary(package: dict[str, Any], *, blueprint_output: Path | None = None) -> dict[str, Any]:
    materialized = package["materialized_summary"]
    stage4 = package["stage4_report"]
    summary = {
        "target_item": materialized["target_item"],
        "target_rate_per_minute": materialized["target_rate_per_minute"],
        "target_rate_basis": materialized["target_rate_basis"],
        "blueprint_output": str(blueprint_output) if blueprint_output else None,
        "entity_count": materialized["entity_count"],
        "tile_count": materialized["tile_count"],
        "width": materialized["width"],
        "height": materialized["height"],
        "route_status_counts": materialized["route_status_counts"],
        "boundary_contract_audit": materialized["connector_summary"].get("boundary_contract_audit") or [],
        "boundary_capacity_audit": materialized["connector_summary"].get("boundary_capacity_audit") or [],
        "output_lane_load_audit": materialized["connector_summary"].get("output_lane_load_audit") or [],
        "output_preseparation_exposure_audit": materialized["connector_summary"].get("output_preseparation_exposure_audit") or [],
        "module_library": stage4.get("module_library"),
        "runtime_proof": package.get("runtime_proof"),
        "stage4_design_decisions": stage4.get("design_decisions") or [],
    }
    return summary


def render_package_markdown(package: dict[str, Any], *, blueprint_output: Path | None = None) -> str:
    summary = package_summary(package, blueprint_output=blueprint_output)
    lines = [
        "# Blueprint Lab Stage 4 Generation Package",
        "",
        f"- Target item: {summary['target_item']}",
        f"- Target rate: {summary['target_rate_per_minute']:g}/min",
        f"- Blueprint output: {summary['blueprint_output'] or 'not-written'}",
        f"- Entities: {summary['entity_count']}",
        f"- Tiles: {summary['tile_count']}",
        f"- Bounds: {summary['width']:g} x {summary['height']:g}",
        f"- Route status counts: {summary['route_status_counts']}",
        "",
        "## Boundary Contract",
        "",
    ]
    for item in summary["boundary_contract_audit"]:
        lines.append(
            f"- {item.get('boundary')}: status={item.get('status')} "
            f"expected={item.get('expected_belt_count')}x {item.get('expected_belt_name')} "
            f"routes={item.get('route_count')}"
        )
    lines.extend(["", "## Boundary Capacity", ""])
    for item in summary["boundary_capacity_audit"]:
        lines.append(
            f"- {item.get('boundary')}: status={item.get('status')} "
            f"proven={item.get('proven_capacity_per_minute', 0):g}/min "
            f"required={item.get('required_rate_per_minute', 0):g}/min"
        )
    if summary["output_preseparation_exposure_audit"]:
        lines.extend(["", "## Output Pre-separation Exposure", ""])
        for item in summary["output_preseparation_exposure_audit"]:
            lines.append(
                f"- {item.get('boundary')} y={item.get('route_y')}: status={item.get('status')} "
                f"instances={item.get('covered_instances')} fanins={item.get('fanin_segment_count')} "
                f"separator_x={item.get('separator_x')} lane_load={item.get('lane_load_status')}"
            )
    lines.extend(["", "## Module Library", ""])
    module_library = summary.get("module_library") or {}
    lines.append(
        f"- produced_items={module_library.get('produced_item_count', 0)} "
        f"status_counts={module_library.get('status_counts', {})}"
    )
    for item in (module_library.get("produced_items") or [])[:8]:
        best = (item.get("best_options") or [{}])[0]
        lines.append(
            f"- {item.get('item')}: options={item.get('option_count')} "
            f"best={best.get('recipe')} rate={best.get('net_target_rate_per_instance', 0):g}/min"
        )
    runtime_proof = summary.get("runtime_proof")
    if runtime_proof:
        throughput = runtime_proof.get("throughput_summary") or {}
        lane_summary = runtime_proof.get("throughput_lane_summary") or {}
        cleanliness = runtime_proof.get("right_boundary_cleanliness") or {}
        invalid_output = runtime_proof.get("invalid_output_inserters") or {}
        lines.extend(
            [
                "",
                "## Runtime Proof",
                "",
                f"- status={runtime_proof.get('status')} target_rate={runtime_proof.get('target_rate_per_minute'):g}/min",
                f"- throughput={throughput.get('target_per_minute', 'unknown')}/min windows={throughput.get('windows', 'unknown')}",
                f"- throughput_lane_count={lane_summary.get('line_count', 'unknown')} spread={lane_summary.get('spread_target_items', 'unknown')}",
                f"- right_boundary_cleanliness={cleanliness.get('status', 'unknown')}",
                f"- invalid_output_inserters={invalid_output.get('count', 'unknown')}",
            ]
        )
    lines.extend(["", "## Design Decisions", ""])
    for item in summary["stage4_design_decisions"]:
        lines.append(f"- {item['decision']}: {item['generator_action']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a stage-4 package: corpus strategy report plus materialized blueprint.")
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
    parser.add_argument("--row-spacing", type=float)
    parser.add_argument("--lane-width", type=float, default=4.0)
    parser.add_argument("--label")
    parser.add_argument("--no-connect-boundaries", action="store_true")
    parser.add_argument("--allow-new-drop-belts", action="store_true")
    parser.add_argument("--max-output-expansions-per-machine", type=int, default=4)
    parser.add_argument("--force-columns", type=int)
    parser.add_argument("--output-separation-min-distance", type=float, default=1.0)
    parser.add_argument("--compress-output-boundary", action="store_true")
    parser.add_argument("--blueprint-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--stage4-json-output", type=Path)
    parser.add_argument("--stage4-markdown-output", type=Path)
    parser.add_argument("--materialize-json-output", type=Path)
    parser.add_argument("--materialize-markdown-output", type=Path)
    parser.add_argument("--runtime-log", type=Path)
    parser.add_argument("--runtime-proof-json-output", type=Path)
    parser.add_argument("--runtime-proof-markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    try:
        package = build_stage4_generation_package(
            files,
            data_raw_json=args.data_raw_json,
            target_item=args.target_item,
            target_rate_per_minute=args.target_rate_per_minute,
            target_belt=args.target_belt,
            target_belt_count=args.target_belt_count,
            target_recipe=args.target_recipe,
            external_items=args.external_item,
            no_default_boundary_items=args.no_default_boundary_items,
            top=args.top,
            cell_size=args.cell_size,
            max_depth=args.max_depth,
            max_columns=args.max_columns,
            spacing=args.spacing,
            row_spacing=args.row_spacing,
            lane_width=args.lane_width,
            label=args.label,
            connect_boundaries=not args.no_connect_boundaries,
            allow_new_drop_belts=args.allow_new_drop_belts,
            max_output_expansions_per_machine=args.max_output_expansions_per_machine,
            force_columns=args.force_columns,
            output_separation_min_distance=args.output_separation_min_distance,
            compress_output_boundary=args.compress_output_boundary,
            runtime_log=args.runtime_log,
        )
    except ValueError as error:
        parser.error(str(error))

    save_blueprint_file(args.blueprint_output, package["blueprint"])
    package["materialized_summary"]["output"] = str(args.blueprint_output)
    summary = package_summary(package, blueprint_output=args.blueprint_output)

    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_package_markdown(package, blueprint_output=args.blueprint_output), encoding="utf-8")
    if args.stage4_json_output:
        args.stage4_json_output.parent.mkdir(parents=True, exist_ok=True)
        args.stage4_json_output.write_text(json.dumps(package["stage4_report"], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stage4_markdown_output:
        args.stage4_markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.stage4_markdown_output.write_text(render_stage4_markdown_report(package["stage4_report"]), encoding="utf-8")
    if args.materialize_json_output:
        args.materialize_json_output.parent.mkdir(parents=True, exist_ok=True)
        args.materialize_json_output.write_text(json.dumps(package["materialized_summary"], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.materialize_markdown_output:
        args.materialize_markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.materialize_markdown_output.write_text(render_materialize_markdown_report(package["materialized_summary"]), encoding="utf-8")
    if args.runtime_proof_json_output and package.get("runtime_proof"):
        args.runtime_proof_json_output.parent.mkdir(parents=True, exist_ok=True)
        args.runtime_proof_json_output.write_text(json.dumps(package["runtime_proof"], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.runtime_proof_markdown_output and package.get("runtime_proof"):
        args.runtime_proof_markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.runtime_proof_markdown_output.write_text(render_runtime_proof_markdown_report(package["runtime_proof"]), encoding="utf-8")

    print(render_package_markdown(package, blueprint_output=args.blueprint_output))
    print(f"Wrote {args.blueprint_output}")
    failed_files = [
        *((package["stage4_report"].get("inputs") or {}).get("failed_files") or []),
        *(package.get("template_mapping_failed_files") or []),
    ]
    return 0 if not failed_files else 2


if __name__ == "__main__":
    raise SystemExit(main())
