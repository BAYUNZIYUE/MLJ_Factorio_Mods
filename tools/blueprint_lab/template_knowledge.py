from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .prototypes import PrototypeKnowledge, empty_knowledge, load_data_raw
from .templates import TemplateCandidate, extract_template_library


@dataclass(frozen=True)
class RecipeMapping:
    recipe: str
    status: str
    category: str | None
    energy_required: float | None
    ingredients: list[tuple[str, float]]
    products: list[tuple[str, float]]
    machine_names: list[str]
    machine_count: int


@dataclass(frozen=True)
class TemplateKnowledgeMapping:
    fingerprint: str
    label: str
    category: str
    source: str
    path: str
    occurrence_count: int
    lesson: str
    recipe_mappings: list[RecipeMapping]
    module_items: list[str]
    requests: list[str]
    unresolved_recipes: list[str]
    candidate_role: str


def recipe_machines(template: TemplateCandidate, recipe: str) -> list[str]:
    return sorted(
        {
            entity.name
            for entity in template.normalized_entities
            if entity.recipe == recipe
        }
    )


def map_template(template: TemplateCandidate, knowledge: PrototypeKnowledge) -> TemplateKnowledgeMapping:
    mappings: list[RecipeMapping] = []
    unresolved: list[str] = []
    for recipe_name in template.recipes:
        recipe = knowledge.recipe(recipe_name)
        machine_names = recipe_machines(template, recipe_name)
        machine_count = sum(1 for entity in template.normalized_entities if entity.recipe == recipe_name)
        if recipe is None:
            unresolved.append(recipe_name)
            mappings.append(
                RecipeMapping(
                    recipe=recipe_name,
                    status="unresolved",
                    category=None,
                    energy_required=None,
                    ingredients=[],
                    products=[],
                    machine_names=machine_names,
                    machine_count=machine_count,
                )
            )
        else:
            mappings.append(
                RecipeMapping(
                    recipe=recipe_name,
                    status="resolved",
                    category=recipe.category,
                    energy_required=recipe.energy_required,
                    ingredients=[(item.name, item.amount) for item in recipe.ingredients],
                    products=[(item.name, item.amount * item.probability) for item in recipe.products],
                    machine_names=machine_names,
                    machine_count=machine_count,
                )
            )

    if template.recipes:
        role = "production-template"
    elif template.item_modules:
        role = "support-template"
    elif any(name in {"transport-belt", "underground-belt", "splitter"} for name, _ in template.top_families):
        role = "routing-template"
    else:
        role = "structure-template"

    return TemplateKnowledgeMapping(
        fingerprint=template.fingerprint,
        label=template.label,
        category=template.category,
        source=template.source,
        path=template.path,
        occurrence_count=template.occurrence_count,
        lesson=template.lesson,
        recipe_mappings=mappings,
        module_items=template.item_modules,
        requests=template.requests,
        unresolved_recipes=unresolved,
        candidate_role=role,
    )


def map_template_library(
    paths: list[Path],
    *,
    knowledge: PrototypeKnowledge,
    top: int = 8,
    cell_size: int = 16,
) -> dict[str, Any]:
    template_summary = extract_template_library(paths, top=top, cell_size=cell_size)
    # dataclasses nested through asdict become dictionaries; restore only fields
    # needed by the mapper.
    restored: list[TemplateCandidate] = []
    from .templates import NormalizedEntity

    for raw in template_summary["templates"]:
        restored.append(
            TemplateCandidate(
                source=raw["source"],
                path=raw["path"],
                label=raw["label"],
                category=raw["category"],
                signature=raw["signature"],
                fingerprint=raw["fingerprint"],
                occurrence_count=raw["occurrence_count"],
                sample_cell=tuple(raw["sample_cell"]),
                cell_size=raw["cell_size"],
                entity_count=raw["entity_count"],
                tile_count=raw["tile_count"],
                top_families=[tuple(item) for item in raw["top_families"]],
                top_entities=[tuple(item) for item in raw["top_entities"]],
                recipes=raw["recipes"],
                item_modules=raw["item_modules"],
                requests=raw["requests"],
                control_behavior_count=raw["control_behavior_count"],
                connection_count=raw["connection_count"],
                normalized_entities=[NormalizedEntity(**entity) for entity in raw["normalized_entities"]],
                lesson=raw["lesson"],
            )
        )

    mappings = [map_template(template, knowledge) for template in restored]
    status_counts = Counter(
        "resolved" if not item.unresolved_recipes and item.recipe_mappings else
        "unresolved" if item.unresolved_recipes else
        "no-recipe"
        for item in mappings
    )
    return {
        "file_count": len(paths),
        "template_count": len(mappings),
        "status_counts": dict(status_counts),
        "recipe_count": len(knowledge.recipes),
        "crafting_entity_count": len(knowledge.crafting_entities),
        "failed_files": template_summary["failed_files"],
        "mappings": [asdict(item) for item in mappings],
        "lessons": [
            "Templates with resolved recipes can be checked against production DAG requirements.",
            "Templates without recipes are still useful as support, routing, platform, or power fill material.",
            "Unresolved recipes mean data.raw knowledge is missing or stale; import the current game/mod data before claiming throughput.",
        ],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Template Knowledge Report",
        "",
        f"- Scanned text files: {summary['file_count']}",
        f"- Template mappings: {summary['template_count']}",
        f"- data.raw recipes: {summary['recipe_count']}",
        f"- data.raw crafting entities: {summary['crafting_entity_count']}",
        f"- Status counts: {summary['status_counts']}",
        f"- Failed files: {len(summary['failed_files'])}",
        "",
        "## Template Recipe Mappings",
        "",
    ]
    for item in summary["mappings"][:80]:
        lines.append(f"### {item['label'] or '<unnamed>'} / {item['fingerprint']}")
        lines.append(
            f"- role={item['candidate_role']} occurrences={item['occurrence_count']} "
            f"lesson={item['lesson']}"
        )
        if item["module_items"]:
            lines.append(f"- modules/items={', '.join(item['module_items'][:8])}")
        if item["requests"]:
            lines.append(f"- requests={', '.join(item['requests'][:8])}")
        if not item["recipe_mappings"]:
            lines.append("- recipes=none")
        for mapping in item["recipe_mappings"]:
            machines = ", ".join(mapping["machine_names"]) or "unknown-machine"
            lines.append(
                f"- recipe={mapping['recipe']} status={mapping['status']} machines={mapping['machine_count']}x {machines}"
            )
            if mapping["status"] == "resolved":
                ingredients = ", ".join(f"{name}:{amount:g}" for name, amount in mapping["ingredients"]) or "none"
                products = ", ".join(f"{name}:{amount:g}" for name, amount in mapping["products"]) or "none"
                lines.append(
                    f"  category={mapping['category']} time={mapping['energy_required']:g} ingredients=[{ingredients}] products=[{products}]"
                )
        lines.append(f"- source={item['source']} path={item['path']}")
        lines.append("")

    lines.extend(["## Generator Implications", ""])
    for lesson in summary["lessons"]:
        lines.append(f"- {lesson}")

    if summary["failed_files"]:
        lines.extend(["", "## Failed Files", ""])
        for failure in summary["failed_files"][:50]:
            lines.append(f"- {failure['path']}: {failure['error']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Map template candidates to data.raw recipe knowledge.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--data-raw-json", type=Path)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    knowledge = load_data_raw(args.data_raw_json) if args.data_raw_json else empty_knowledge()
    summary = map_template_library(files, knowledge=knowledge, top=args.top, cell_size=args.cell_size)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(summary), encoding="utf-8")

    print(render_markdown_report(summary))
    return 0 if not summary["failed_files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
