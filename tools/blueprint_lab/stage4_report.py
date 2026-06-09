from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .knowledge import KNOWLEDGE_LAYERS, OFFICIAL_SOURCES
from .learn import learn_library
from .production_dag import template_options_from_mappings
from .prototypes import load_data_raw
from .template_knowledge import map_template_library


def category_index(learning: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["category"]): item
        for item in learning.get("category_summaries") or []
    }


def compactness_profile(learning: dict[str, Any]) -> dict[str, Any]:
    categories = category_index(learning)
    profile: dict[str, Any] = {}
    for category in ("science", "space_platform", "quality", "smelting", "balancer", "mall", "logistics"):
        item = categories.get(category)
        if not item:
            continue
        profile[category] = {
            "blueprint_count": item["blueprint_count"],
            "median_area": item["median_area"],
            "median_density": item["median_density"],
            "median_aspect_ratio": item["median_aspect_ratio"],
            "lesson": item["lesson"],
        }
    return profile


def design_decisions(learning: dict[str, Any]) -> list[dict[str, Any]]:
    categories = category_index(learning)
    science = categories.get("science", {})
    platform = categories.get("space_platform", {})
    quality = categories.get("quality", {})
    smelting = categories.get("smelting", {})
    balancer = categories.get("balancer", {})
    return [
        {
            "decision": "ship_tileable_single_recipe_modules_first",
            "why": (
                "Single-recipe modules have a narrow contract: recipe, machine count, local input/output lanes, "
                "copy direction, and full-belt target. They can be verified with data.raw rates plus runtime probes "
                "before being used as black-box building blocks."
            ),
            "corpus_evidence": {
                "smelting_blueprints": smelting.get("blueprint_count", 0),
                "smelting_median_aspect_ratio": smelting.get("median_aspect_ratio", 0),
                "lesson": smelting.get("lesson", ""),
            },
            "generator_action": "Treat learned recipe templates as copyable atoms; reject layouts whose per-lane load exceeds belt capacity even when total output capacity looks sufficient.",
        },
        {
            "decision": "compose_end_to_end_blackboxes_from_verified_modules",
            "why": (
                "Integrated science, platform, and quality blueprints are not one family. They mix production DAGs, "
                "recycle loops, requester patterns, platform tiles, circuit control, and boundary buses. A single "
                "from-scratch placer would hide too many unverified assumptions."
            ),
            "corpus_evidence": {
                "science_blueprints": science.get("blueprint_count", 0),
                "space_platform_blueprints": platform.get("blueprint_count", 0),
                "quality_blueprints": quality.get("blueprint_count", 0),
            },
            "generator_action": "Plan the recipe DAG first, pack verified modules into a rectangle second, then route boundary buses and byproduct/recycle lanes with explicit audits.",
        },
        {
            "decision": "keep_boundary_contract_separate_from_internal_lanes",
            "why": (
                "The corpus uses long straight lanes and edge buses to keep throughput visible. Current generator "
                "experiments show the same lesson: internal machine-output lanes can be sufficient while a final "
                "external compressor still fails at runtime."
            ),
            "corpus_evidence": {
                "balancer_blueprints": balancer.get("blueprint_count", 0),
                "cross_corpus_lesson": (learning.get("lessons") or {}).get("route_first", ""),
            },
            "generator_action": "Report internal-output lanes, external-output lanes, contract exactness, structural capacity, proven capacity, and unresolved capacity separately.",
        },
        {
            "decision": "prefer_runtime_proof_over_visual_compactness",
            "why": (
                "A generic 3-to-2 compressor can look compact and exact offline while delivering only about one turbo "
                "belt in the live probe. Compactness is useful only after placement, inserter targets, splitter filters, "
                "byproduct handling, and boundary throughput are proven."
            ),
            "corpus_evidence": {
                "known_negative_case": "generic output-boundary compressor: exact 2x turbo contract, unresolved capacity, runtime around 3540-3600/min",
            },
            "generator_action": "Score unresolved runtime capacity worse than an over-provisioned but proven boundary; require explicit force flags for known-insufficient experiments.",
        },
    ]


def production_module_library(
    blueprint_paths: list[Path],
    *,
    data_raw_json: Path,
    top: int = 8,
    cell_size: int = 16,
) -> dict[str, Any]:
    knowledge = load_data_raw(data_raw_json)
    template_summary = map_template_library(blueprint_paths, knowledge=knowledge, top=top, cell_size=cell_size)
    options_by_item = template_options_from_mappings(template_summary.get("mappings") or [])
    items: list[dict[str, Any]] = []
    for item_name, options in sorted(options_by_item.items()):
        option_entries: list[dict[str, Any]] = []
        for option in options[:3]:
            option_entries.append(
                {
                    "recipe": option.recipe,
                    "fingerprint": option.fingerprint,
                    "label": option.label,
                    "source": option.source,
                    "occurrence_count": option.occurrence_count,
                    "net_target_rate_per_instance": option.net_target_rate_per_instance,
                    "output_rate_per_instance": option.output_rate_per_instance,
                    "target_input_rate_per_instance": option.target_input_rate_per_instance,
                    "rate_basis": option.rate_basis,
                    "input_rates_per_instance": option.input_rates_per_instance,
                    "product_rates_per_instance": option.product_rates_per_instance,
                    "rate_module_effects": option.rate_module_effects,
                    "rate_module_items": option.rate_module_items,
                }
            )
        items.append(
            {
                "item": item_name,
                "option_count": len(options),
                "best_options": option_entries,
            }
        )
    items.sort(
        key=lambda item: (
            item["best_options"][0]["net_target_rate_per_instance"] if item["best_options"] else 0,
            item["option_count"],
        ),
        reverse=True,
    )
    return {
        "data_raw_json": str(data_raw_json),
        "template_count": template_summary["template_count"],
        "status_counts": template_summary["status_counts"],
        "recipe_count": template_summary["recipe_count"],
        "crafting_entity_count": template_summary["crafting_entity_count"],
        "produced_item_count": len(items),
        "produced_items": items,
        "lessons": [
            "A produced item enters the generator only after a recipe-bearing template resolves against data.raw.",
            "The best option is ranked by net target output per copied template instance, not by visual density alone.",
            "Items absent from this library remain external boundary inputs or require more template extraction.",
        ],
    }


def build_stage4_report(
    blueprint_paths: list[Path],
    *,
    top: int = 8,
    data_raw_json: Path | None = None,
    cell_size: int = 16,
) -> dict[str, Any]:
    learning = learn_library(blueprint_paths, top=top)
    report = {
        "stage": "stage4-compact-blueprint-generation",
        "goal": "Use corpus lessons, game/prototype knowledge, and runtime probes to move from tileable recipe modules toward compact rectangular black-box generators.",
        "inputs": {
            "file_count": learning["file_count"],
            "blueprint_count": learning["blueprint_count"],
            "failed_files": learning["failed_files"],
        },
        "knowledge_sources": [
            {
                "name": source.name,
                "url": source.url,
                "use": source.use,
            }
            for source in OFFICIAL_SOURCES
        ],
        "knowledge_layers": KNOWLEDGE_LAYERS,
        "compactness_profile": compactness_profile(learning),
        "blackbox_candidates": learning.get("blackbox_candidates") or [],
        "design_decisions": design_decisions(learning),
        "next_generator_milestones": [
            {
                "name": "tileable-single-recipe-module",
                "acceptance": [
                    "recipe and target belt count derive machine count from data.raw",
                    "copied module exposes explicit input/output boundaries",
                    "lane load audit is sufficient",
                    "runtime probe reaches target throughput with invalid_output_inserters=0",
                ],
            },
            {
                "name": "module-to-blackbox-packing",
                "acceptance": [
                    "production DAG lists all internal and external items",
                    "each DAG node references a verified module template",
                    "rectangle packing reports boundary buses and byproduct/recycle lanes separately",
                    "generated blueprint imports and builds in Factorio runtime validation",
                ],
            },
            {
                "name": "strict-external-boundary-compression",
                "acceptance": [
                    "external boundary contract is exact for the requested belt count",
                    "internal lanes remain below per-belt capacity",
                    "compressor capacity is proven by runtime throughput, not only offline belt flow",
                    "known-insufficient generic balancers remain marked unresolved",
                ],
            },
        ],
    }
    if data_raw_json is not None:
        report["module_library"] = production_module_library(
            blueprint_paths,
            data_raw_json=data_raw_json,
            top=top,
            cell_size=cell_size,
        )
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Lab Stage 4 Report",
        "",
        f"- Goal: {report['goal']}",
        f"- Scanned text files: {report['inputs']['file_count']}",
        f"- Decoded blueprints: {report['inputs']['blueprint_count']}",
        f"- Failed files: {len(report['inputs']['failed_files'])}",
        "",
        "## Knowledge Sources",
        "",
    ]
    for source in report["knowledge_sources"]:
        lines.append(f"- {source['name']}: {source['url']} ({source['use']})")

    lines.extend(["", "## Knowledge Layers", ""])
    for layer, entries in report["knowledge_layers"].items():
        lines.append(f"- {layer}: " + ", ".join(entries))

    lines.extend(["", "## Compactness Profile", ""])
    for category, item in report["compactness_profile"].items():
        lines.append(
            f"- {category}: blueprints={item['blueprint_count']} "
            f"median_area={item['median_area']:.1f} median_density={item['median_density']:.3f} "
            f"median_aspect={item['median_aspect_ratio']:.2f}"
        )
        lines.append(f"  lesson={item['lesson']}")

    lines.extend(["", "## Black-Box Candidates", ""])
    for item in report["blackbox_candidates"][:12]:
        lines.append(
            f"- {item['label'] or '<unnamed>'}: category={item['category']} "
            f"entities={item['entity_count']} tiles={item['tile_count']} "
            f"size={item['width']:.1f}x{item['height']:.1f} "
            f"density={item['density']:.3f} aspect={item['aspect_ratio']:.2f}"
        )

    if report.get("module_library"):
        library = report["module_library"]
        lines.extend(["", "## Production Module Library", ""])
        lines.append(
            f"- data_raw={library['data_raw_json']} templates={library['template_count']} "
            f"status_counts={library['status_counts']} produced_items={library['produced_item_count']}"
        )
        for item in library["produced_items"][:12]:
            lines.append(f"### {item['item']}")
            lines.append(f"- options={item['option_count']}")
            for option in item["best_options"]:
                lines.append(
                    f"- recipe={option['recipe']} rate={option['net_target_rate_per_instance']:g}/min "
                    f"basis={option['rate_basis']} occurrences={option['occurrence_count']} "
                    f"label={option['label'] or '<unnamed>'}"
                )
        lines.extend(["", "### Module Library Lessons"])
        for lesson in library["lessons"]:
            lines.append(f"- {lesson}")

    lines.extend(["", "## Design Decisions", ""])
    for item in report["design_decisions"]:
        lines.append(f"### {item['decision']}")
        lines.append(f"- why: {item['why']}")
        lines.append(f"- generator_action: {item['generator_action']}")
        lines.append(f"- corpus_evidence: {json.dumps(item['corpus_evidence'], ensure_ascii=False, sort_keys=True)}")
        lines.append("")

    lines.extend(["## Next Generator Milestones", ""])
    for item in report["next_generator_milestones"]:
        lines.append(f"### {item['name']}")
        for acceptance in item["acceptance"]:
            lines.append(f"- {acceptance}")
        lines.append("")

    if report["inputs"]["failed_files"]:
        lines.extend(["## Failed Files", ""])
        for failure in report["inputs"]["failed_files"][:50]:
            lines.append(f"- {failure['path']}: {failure['error']}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the stage-4 compact blueprint generation strategy report.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--data-raw-json", type=Path)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    report = build_stage4_report(files, top=args.top, data_raw_json=args.data_raw_json, cell_size=args.cell_size)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(report), encoding="utf-8")

    print(render_markdown_report(report))
    return 0 if not report["inputs"]["failed_files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
