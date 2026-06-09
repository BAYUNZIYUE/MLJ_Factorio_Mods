from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .prototypes import load_data_raw, target_rate_basis_from_args
from .template_knowledge import map_template_library


DEFAULT_BOUNDARY_ITEMS = {
    "coal",
    "copper-ore",
    "crude-oil",
    "iron-ore",
    "stone",
    "uranium-ore",
    "water",
}


@dataclass(frozen=True)
class TemplateOption:
    target_item: str
    recipe: str
    fingerprint: str
    label: str
    source: str
    path: str
    occurrence_count: int
    module_items: list[str]
    output_rate_per_instance: float
    target_input_rate_per_instance: float
    net_target_rate_per_instance: float
    input_rates_per_instance: list[tuple[str, float]]
    product_rates_per_instance: list[tuple[str, float]]
    machine_speeds: list[tuple[str, float]]
    rate_basis: str
    direct_module_effects: list[tuple[str, float]]
    direct_module_items: list[tuple[str, str, int]]
    rate_module_effects: list[tuple[str, float]]
    rate_module_items: list[tuple[str, str, int]]


@dataclass(frozen=True)
class ExternalInput:
    item: str
    rate_per_minute: float
    reason: str


@dataclass(frozen=True)
class ProductionPlanNode:
    item: str
    required_rate_per_minute: float
    recipe: str
    fingerprint: str
    label: str
    source: str
    path: str
    occurrence_count: int
    output_rate_per_instance: float
    target_input_rate_per_instance: float
    net_target_rate_per_instance: float
    instances_exact: float
    instances: int
    planned_net_output_per_minute: float
    input_rates_per_instance: list[tuple[str, float]]
    planned_input_rates_per_minute: list[tuple[str, float]]
    module_items: list[str]
    machine_speeds: list[tuple[str, float]]
    rate_basis: str
    direct_module_effects: list[tuple[str, float]]
    direct_module_items: list[tuple[str, str, int]]
    rate_module_effects: list[tuple[str, float]]
    rate_module_items: list[tuple[str, str, int]]
    children: list["ProductionPlanNode"]
    external_inputs: list[ExternalInput]


def pair_rate(pairs: list[Any], item_name: str) -> float:
    total = 0.0
    for pair in pairs:
        if len(pair) < 2:
            continue
        name, amount = pair[0], pair[1]
        if str(name) == item_name and isinstance(amount, (int, float)):
            total += float(amount)
    return total


def normalize_pairs(pairs: list[Any]) -> list[tuple[str, float]]:
    normalized: list[tuple[str, float]] = []
    for pair in pairs:
        if len(pair) < 2:
            continue
        name, amount = pair[0], pair[1]
        if isinstance(amount, (int, float)):
            normalized.append((str(name), float(amount)))
    return normalized


def recipe_rate_basis(
    recipe_mapping: dict[str, Any],
) -> tuple[str, list[tuple[str, float]], list[tuple[str, float]], float | None, list[tuple[str, float]], list[tuple[str, str, int]]]:
    with_beacons_crafts = recipe_mapping.get("effective_with_beacons_crafts_per_minute")
    if with_beacons_crafts is not None:
        return (
            "effective-with-beacons",
            normalize_pairs(recipe_mapping.get("effective_with_beacons_ingredients_per_minute") or []),
            normalize_pairs(recipe_mapping.get("effective_with_beacons_products_per_minute") or []),
            float(with_beacons_crafts),
            normalize_pairs(recipe_mapping.get("effective_with_beacons_effects") or []),
            [
                (str(name), str(quality), int(count))
                for name, quality, count in recipe_mapping.get("effective_with_beacons_module_items") or []
            ],
        )
    effective_crafts = recipe_mapping.get("effective_crafts_per_minute")
    if effective_crafts is not None:
        return (
            "effective-direct-modules",
            normalize_pairs(recipe_mapping.get("effective_ingredients_per_minute") or []),
            normalize_pairs(recipe_mapping.get("effective_products_per_minute") or []),
            float(effective_crafts),
            normalize_pairs(recipe_mapping.get("direct_module_effects") or []),
            [
                (str(name), str(quality), int(count))
                for name, quality, count in recipe_mapping.get("direct_module_items") or []
            ],
        )
    base_crafts = recipe_mapping.get("base_crafts_per_minute")
    if base_crafts is not None:
        return (
            "base-without-modules",
            normalize_pairs(recipe_mapping.get("base_ingredients_per_minute") or []),
            normalize_pairs(recipe_mapping.get("base_products_per_minute") or []),
            float(base_crafts),
            [],
            [],
        )
    return "", [], [], None, [], []


def template_options_from_mappings(
    mappings: list[dict[str, Any]],
    *,
    target_recipe: str | None = None,
) -> dict[str, list[TemplateOption]]:
    by_item: dict[str, list[TemplateOption]] = defaultdict(list)
    for template in mappings:
        if template.get("candidate_role") != "production-template":
            continue
        for recipe_mapping in template.get("recipe_mappings") or []:
            if recipe_mapping.get("status") != "resolved":
                continue
            if target_recipe and recipe_mapping.get("recipe") != target_recipe:
                continue
            rate_basis, inputs, products, crafts_per_minute, rate_module_effects, rate_module_items = recipe_rate_basis(recipe_mapping)
            if crafts_per_minute is None:
                continue

            for product_name, output_rate in products:
                target_input_rate = pair_rate(inputs, product_name)
                net_rate = output_rate - target_input_rate
                if net_rate <= 0:
                    continue
                by_item[product_name].append(
                    TemplateOption(
                        target_item=product_name,
                        recipe=str(recipe_mapping["recipe"]),
                        fingerprint=str(template["fingerprint"]),
                        label=str(template.get("label") or ""),
                        source=str(template.get("source") or ""),
                        path=str(template.get("path") or ""),
                        occurrence_count=int(template.get("occurrence_count") or 0),
                        module_items=[str(item) for item in template.get("module_items") or []],
                        output_rate_per_instance=output_rate,
                        target_input_rate_per_instance=target_input_rate,
                        net_target_rate_per_instance=net_rate,
                        input_rates_per_instance=inputs,
                        product_rates_per_instance=products,
                        machine_speeds=normalize_pairs(recipe_mapping.get("machine_speeds") or []),
                        rate_basis=rate_basis,
                        direct_module_effects=normalize_pairs(recipe_mapping.get("direct_module_effects") or []),
                        direct_module_items=[
                            (str(name), str(quality), int(count))
                            for name, quality, count in recipe_mapping.get("direct_module_items") or []
                        ],
                        rate_module_effects=rate_module_effects,
                        rate_module_items=rate_module_items,
                    )
                )

    for options in by_item.values():
        options.sort(
            key=lambda item: (
                item.net_target_rate_per_instance,
                item.occurrence_count,
                item.output_rate_per_instance,
            ),
            reverse=True,
        )
    return dict(by_item)


def plan_node(
    item: str,
    required_rate: float,
    options_by_item: dict[str, list[TemplateOption]],
    *,
    max_depth: int,
    boundary_items: set[str],
    target_rate_basis: dict[str, Any] | None = None,
    depth: int = 0,
    stack: tuple[str, ...] = (),
) -> ProductionPlanNode | ExternalInput:
    if depth > max_depth:
        return ExternalInput(item=item, rate_per_minute=required_rate, reason="max-depth")
    if depth > 0 and item in boundary_items:
        return ExternalInput(item=item, rate_per_minute=required_rate, reason="boundary-input")
    if item in stack:
        return ExternalInput(item=item, rate_per_minute=required_rate, reason="cycle-seed-or-recycle-input")

    options = options_by_item.get(item) or []
    if not options:
        return ExternalInput(item=item, rate_per_minute=required_rate, reason="no-production-template")

    option = options[0]
    instances_exact = required_rate / option.net_target_rate_per_instance
    instances = max(1, math.ceil(instances_exact))
    if depth == 0 and (target_rate_basis or {}).get("kind") == "full-belt":
        belt_count = int((target_rate_basis or {}).get("belt_count") or 0)
        items_per_second = (target_rate_basis or {}).get("items_per_second_per_belt")
        if belt_count > 0 and isinstance(items_per_second, (int, float)):
            per_belt_rate = float(items_per_second) * 60
            instances_per_belt = max(1, math.ceil(per_belt_rate / option.net_target_rate_per_instance))
            instances = max(instances, belt_count * instances_per_belt)
    planned_inputs = [(name, rate * instances) for name, rate in option.input_rates_per_instance]
    children: list[ProductionPlanNode] = []
    external_inputs: list[ExternalInput] = []

    for input_name, input_rate in planned_inputs:
        planned = plan_node(
            input_name,
            input_rate,
            options_by_item,
            max_depth=max_depth,
            boundary_items=boundary_items,
            target_rate_basis=None,
            depth=depth + 1,
            stack=(*stack, item),
        )
        if isinstance(planned, ExternalInput):
            external_inputs.append(planned)
        else:
            children.append(planned)

    return ProductionPlanNode(
        item=item,
        required_rate_per_minute=required_rate,
        recipe=option.recipe,
        fingerprint=option.fingerprint,
        label=option.label,
        source=option.source,
        path=option.path,
        occurrence_count=option.occurrence_count,
        output_rate_per_instance=option.output_rate_per_instance,
        target_input_rate_per_instance=option.target_input_rate_per_instance,
        net_target_rate_per_instance=option.net_target_rate_per_instance,
        instances_exact=instances_exact,
        instances=instances,
        planned_net_output_per_minute=option.net_target_rate_per_instance * instances,
        input_rates_per_instance=option.input_rates_per_instance,
        planned_input_rates_per_minute=planned_inputs,
        module_items=option.module_items,
        machine_speeds=option.machine_speeds,
        rate_basis=option.rate_basis,
        direct_module_effects=option.direct_module_effects,
        direct_module_items=option.direct_module_items,
        rate_module_effects=option.rate_module_effects,
        rate_module_items=option.rate_module_items,
        children=children,
        external_inputs=external_inputs,
    )


def collect_external_inputs(node: ProductionPlanNode | ExternalInput) -> list[ExternalInput]:
    if isinstance(node, ExternalInput):
        return [node]
    inputs = [*node.external_inputs]
    for child in node.children:
        inputs.extend(collect_external_inputs(child))
    return inputs


def aggregate_external_inputs(inputs: list[ExternalInput]) -> list[dict[str, Any]]:
    rates: dict[tuple[str, str], float] = defaultdict(float)
    for item in inputs:
        rates[(item.item, item.reason)] += item.rate_per_minute
    return [
        {"item": item, "rate_per_minute": rate, "reason": reason}
        for (item, reason), rate in sorted(rates.items())
    ]


def count_nodes(node: ProductionPlanNode | ExternalInput) -> int:
    if isinstance(node, ExternalInput):
        return 0
    return 1 + sum(count_nodes(child) for child in node.children)


def build_production_plan(
    mappings: list[dict[str, Any]],
    *,
    target_item: str,
    target_rate_per_minute: float,
    target_rate_basis: dict[str, Any] | None = None,
    max_depth: int = 4,
    target_recipe: str | None = None,
    boundary_items: set[str] | None = None,
) -> dict[str, Any]:
    options_by_item = template_options_from_mappings(mappings, target_recipe=target_recipe)
    effective_boundary_items = default_boundary_items(options_by_item) if boundary_items is None else boundary_items
    root = plan_node(
        target_item,
        target_rate_per_minute,
        options_by_item,
        max_depth=max_depth,
        boundary_items=effective_boundary_items,
        target_rate_basis=target_rate_basis,
    )
    external_inputs = collect_external_inputs(root)
    return {
        "target_item": target_item,
        "target_rate_per_minute": target_rate_per_minute,
        "target_rate_basis": target_rate_basis or {
            "kind": "explicit-rate",
            "rate_per_minute": target_rate_per_minute,
        },
        "target_recipe": target_recipe,
        "max_depth": max_depth,
        "boundary_items": sorted(effective_boundary_items),
        "available_product_count": len(options_by_item),
        "node_count": count_nodes(root),
        "root": asdict(root),
        "external_inputs": aggregate_external_inputs(external_inputs),
        "lessons": [
            "The planner treats a learned production template as the smallest copyable unit, so required instances are rounded up to whole templates.",
            "Template selection prefers the strongest positive net output for the requested item; recipes that consume more of the target item than they produce are ignored as sources.",
            "External inputs mark the current black-box boundary: either the item is configured as raw/base input, the corpus has not yielded a usable production template for it yet, or recursion hit a cycle/depth guard.",
            "Rate basis prefers effective same-template beacon estimates, then effective direct modules, then base rates, so copied machine quality and module stacks affect template count before layout.",
            "This is a production-DAG seed, not final routing or placement; rectangle packing and belt/pipe routing must consume this plan next.",
        ],
    }


def default_boundary_items(options_by_item: dict[str, list[TemplateOption]]) -> set[str]:
    items = set(DEFAULT_BOUNDARY_ITEMS)
    for item_name in options_by_item:
        if item_name.endswith("-asteroid-chunk"):
            items.add(item_name)
    for options in options_by_item.values():
        for option in options:
            for input_name, _ in option.input_rates_per_instance:
                if input_name.endswith("-asteroid-chunk"):
                    items.add(input_name)
    return items


def render_node(node: dict[str, Any], lines: list[str], indent: int = 0) -> None:
    prefix = "  " * indent
    lines.append(
        f"{prefix}- {node['item']}: require={node['required_rate_per_minute']:g}/min "
        f"recipe={node['recipe']} template={node['fingerprint']} instances={node['instances']} "
        f"net={node['planned_net_output_per_minute']:g}/min"
    )
    lines.append(
        f"{prefix}  per_instance net={node['net_target_rate_per_instance']:g}/min "
        f"gross={node['output_rate_per_instance']:g}/min basis={node['rate_basis']} "
        f"occurrence_count={node['occurrence_count']}"
    )
    if node["machine_speeds"]:
        speeds = ", ".join(f"{name}@{speed:g}" for name, speed in node["machine_speeds"])
        lines.append(f"{prefix}  machines={speeds}")
    if node["module_items"]:
        lines.append(f"{prefix}  modules/items={', '.join(node['module_items'][:8])}")
    if node.get("rate_module_items"):
        modules = ", ".join(
            f"{count}x {quality} {name}"
            for name, quality, count in node["rate_module_items"]
        )
        lines.append(f"{prefix}  rate_modules={modules}")
    if node.get("rate_module_effects"):
        effects = ", ".join(
            f"{name}:{value:g}"
            for name, value in node["rate_module_effects"]
        )
        lines.append(f"{prefix}  rate_module_effects={effects}")
    if node["planned_input_rates_per_minute"]:
        inputs = ", ".join(
            f"{name}:{rate:g}/min"
            for name, rate in node["planned_input_rates_per_minute"]
        )
        lines.append(f"{prefix}  planned_inputs={inputs}")
    lines.append(f"{prefix}  source={node['source']} path={node['path']}")
    for external in node["external_inputs"]:
        lines.append(
            f"{prefix}  - external {external['item']}: {external['rate_per_minute']:g}/min reason={external['reason']}"
        )
    for child in node["children"]:
        render_node(child, lines, indent + 1)


def render_markdown_report(summary: dict[str, Any]) -> str:
    target_rate_basis = summary.get("target_rate_basis") or {}
    lines = [
        "# Blueprint Production DAG Seed Report",
        "",
        f"- Target item: {summary['target_item']}",
        f"- Target rate: {summary['target_rate_per_minute']:g}/min",
        f"- Target rate basis: {render_target_rate_basis(target_rate_basis)}",
        f"- Target recipe filter: {summary['target_recipe'] or 'none'}",
        f"- Max depth: {summary['max_depth']}",
        f"- Boundary inputs: {', '.join(summary['boundary_items']) or 'none'}",
        f"- Available produced items from templates: {summary['available_product_count']}",
        f"- Planned production nodes: {summary['node_count']}",
        "",
        "## Plan Tree",
        "",
    ]
    root = summary["root"]
    if root.get("reason"):
        lines.append(
            f"- external {root['item']}: {root['rate_per_minute']:g}/min reason={root['reason']}"
        )
    else:
        render_node(root, lines)

    lines.extend(["", "## External Inputs", ""])
    if summary["external_inputs"]:
        for item in summary["external_inputs"]:
            lines.append(
                f"- {item['item']}: {item['rate_per_minute']:g}/min reason={item['reason']}"
            )
    else:
        lines.append("- none")

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
    parser = argparse.ArgumentParser(description="Plan a production DAG from learned blueprint templates.")
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
    summary = build_production_plan(
        template_summary["mappings"],
        target_item=args.target_item,
        target_rate_per_minute=target_rate_per_minute,
        target_rate_basis=target_rate_basis,
        target_recipe=args.target_recipe,
        max_depth=args.max_depth,
        boundary_items=boundary_items,
    )
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
