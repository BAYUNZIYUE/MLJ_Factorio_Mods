from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .decompose import cell_signatures, entity_family, signature_from_counter
from .learn import learn_library
from .decompose import blueprint_by_path


@dataclass(frozen=True)
class NormalizedEntity:
    name: str
    family: str
    x: float
    y: float
    direction: int | None
    entity_type: str | None
    recipe: str | None
    recipe_quality: str | None
    quality: str | None
    items: list[str]
    requests: list[str]
    has_control_behavior: bool
    has_connections: bool
    item_stacks: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizedTile:
    name: str
    x: float
    y: float


@dataclass(frozen=True)
class TemplateCandidate:
    source: str
    path: str
    label: str
    category: str
    signature: str
    fingerprint: str
    occurrence_count: int
    sample_cell: tuple[int, int]
    cell_size: int
    entity_count: int
    tile_count: int
    top_families: list[tuple[str, int]]
    top_entities: list[tuple[str, int]]
    recipes: list[str]
    item_modules: list[str]
    requests: list[str]
    control_behavior_count: int
    connection_count: int
    normalized_entities: list[NormalizedEntity]
    normalized_tiles: list[NormalizedTile]
    lesson: str


def item_names(entity: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in entity.get("items") or []:
        item_id = item.get("id") if isinstance(item, dict) else None
        if isinstance(item_id, dict) and item_id.get("name"):
            names.append(str(item_id["name"]))
    return sorted(set(names))


def item_stacks(entity: dict[str, Any]) -> list[dict[str, Any]]:
    stacks = entity.get("items")
    if not isinstance(stacks, list):
        return []
    return copy.deepcopy(stacks)


def request_names(entity: dict[str, Any]) -> list[str]:
    names: list[str] = []
    request_filters = entity.get("request_filters")
    if not isinstance(request_filters, dict):
        return names
    for section in request_filters.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for filter_item in section.get("filters") or []:
            if isinstance(filter_item, dict) and filter_item.get("name"):
                names.append(str(filter_item["name"]))
    return sorted(set(names))


def count_connections(entity: dict[str, Any]) -> int:
    connections = entity.get("connections")
    if not isinstance(connections, dict):
        return 0
    return sum(len(value) if isinstance(value, list) else 1 for value in connections.values())


def cell_entities_and_tiles(
    blueprint: dict[str, Any],
    cell: tuple[int, int],
    cell_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[float, float]]:
    positions = [
        item.get("position") or {}
        for item in [*(blueprint.get("entities") or []), *(blueprint.get("tiles") or [])]
    ]
    min_x = min(float(position.get("x", 0)) for position in positions)
    min_y = min(float(position.get("y", 0)) for position in positions)
    cell_min_x = min_x + cell[0] * cell_size
    cell_min_y = min_y + cell[1] * cell_size
    cell_max_x = cell_min_x + cell_size
    cell_max_y = cell_min_y + cell_size

    entities: list[dict[str, Any]] = []
    for entity in blueprint.get("entities") or []:
        position = entity.get("position") or {}
        x = float(position.get("x", 0))
        y = float(position.get("y", 0))
        if cell_min_x <= x < cell_max_x and cell_min_y <= y < cell_max_y:
            entities.append(entity)

    tiles: list[dict[str, Any]] = []
    for tile in blueprint.get("tiles") or []:
        position = tile.get("position") or {}
        x = float(position.get("x", 0))
        y = float(position.get("y", 0))
        if cell_min_x <= x < cell_max_x and cell_min_y <= y < cell_max_y:
            tiles.append(tile)

    return entities, tiles, (cell_min_x, cell_min_y)


def normalize_entities(entities: list[dict[str, Any]], origin: tuple[float, float]) -> list[NormalizedEntity]:
    normalized: list[NormalizedEntity] = []
    for entity in entities:
        position = entity.get("position") or {}
        direction = entity.get("direction")
        normalized.append(
            NormalizedEntity(
                name=str(entity.get("name") or ""),
                family=entity_family(str(entity.get("name") or "")),
                x=round(float(position.get("x", 0)) - origin[0], 3),
                y=round(float(position.get("y", 0)) - origin[1], 3),
                direction=int(direction) if isinstance(direction, int) else None,
                entity_type=str(entity["type"]) if entity.get("type") else None,
                recipe=str(entity["recipe"]) if entity.get("recipe") else None,
                recipe_quality=str(entity["recipe_quality"]) if entity.get("recipe_quality") else None,
                quality=str(entity["quality"]) if entity.get("quality") else None,
                items=item_names(entity),
                requests=request_names(entity),
                has_control_behavior="control_behavior" in entity,
                has_connections="connections" in entity,
                item_stacks=item_stacks(entity),
            )
        )
    return sorted(normalized, key=lambda item: (item.family, item.name, item.x, item.y, item.direction or -1))


def normalize_tiles(tiles: list[dict[str, Any]], origin: tuple[float, float]) -> list[NormalizedTile]:
    normalized: list[NormalizedTile] = []
    for tile in tiles:
        position = tile.get("position") or {}
        normalized.append(
            NormalizedTile(
                name=str(tile.get("name") or ""),
                x=round(float(position.get("x", 0)) - origin[0], 3),
                y=round(float(position.get("y", 0)) - origin[1], 3),
            )
        )
    return sorted(normalized, key=lambda item: (item.name, item.x, item.y))


def fingerprint_entities(entities: list[NormalizedEntity]) -> str:
    payload = [
        {
            "name": entity.name,
            "family": entity.family,
            "x": entity.x,
            "y": entity.y,
            "direction": entity.direction,
            "entity_type": entity.entity_type,
            "recipe": entity.recipe,
            "recipe_quality": entity.recipe_quality,
            "quality": entity.quality,
            "items": entity.items,
            "requests": entity.requests,
            "has_control_behavior": entity.has_control_behavior,
            "has_connections": entity.has_connections,
        }
        for entity in entities
    ]
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(data).hexdigest()[:16]


def extract_templates_from_blueprint(
    source: str,
    node_path: str,
    blueprint: dict[str, Any],
    *,
    category: str,
    cell_size: int = 16,
    limit: int = 12,
) -> list[TemplateCandidate]:
    cells, _, _ = cell_signatures(blueprint, cell_size)
    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    counters: dict[str, Counter[str]] = {}
    for cell, counter in cells.items():
        signature = signature_from_counter(counter)
        if not signature:
            continue
        grouped[signature].append(cell)
        counters[signature] = counter

    candidates: list[TemplateCandidate] = []
    for signature, cell_list in grouped.items():
        if len(cell_list) < 2:
            continue
        sample_cell = sorted(cell_list)[0]
        entities, tiles, origin = cell_entities_and_tiles(blueprint, sample_cell, cell_size)
        normalized = normalize_entities(entities, origin)
        normalized_tiles = normalize_tiles(tiles, origin)
        family_counts = Counter(entity.family for entity in normalized)
        entity_counts = Counter(entity.name for entity in normalized)
        recipes = sorted({entity.recipe for entity in normalized if entity.recipe})
        modules = sorted({item for entity in normalized for item in entity.items})
        requests = sorted({request for entity in normalized for request in entity.requests})
        control_count = sum(1 for entity in entities if "control_behavior" in entity)
        connection_count = sum(count_connections(entity) for entity in entities)
        lesson = "repeatable layout cell"
        if recipes:
            lesson = "recipe-bearing production template candidate"
        elif modules:
            lesson = "module/beacon support template candidate"
        elif family_counts.get("transport-belt") or family_counts.get("underground-belt"):
            lesson = "routing-lane template candidate"
        elif counters[signature].get("tile", 0) and not normalized:
            lesson = "platform/foundation fill template candidate"

        candidates.append(
            TemplateCandidate(
                source=source,
                path=node_path,
                label=str(blueprint.get("label") or ""),
                category=category,
                signature=signature,
                fingerprint=fingerprint_entities(normalized),
                occurrence_count=len(cell_list),
                sample_cell=sample_cell,
                cell_size=cell_size,
                entity_count=len(entities),
                tile_count=len(tiles),
                top_families=family_counts.most_common(8),
                top_entities=entity_counts.most_common(8),
                recipes=recipes,
                item_modules=modules,
                requests=requests,
                control_behavior_count=control_count,
                connection_count=connection_count,
                normalized_entities=normalized,
                normalized_tiles=normalized_tiles,
                lesson=lesson,
            )
        )

    candidates = sorted(
        candidates,
        key=lambda item: (
            item.occurrence_count,
            len(item.recipes),
            item.entity_count + item.tile_count,
        ),
        reverse=True,
    )
    return candidates[:limit]


def extract_template_library(paths: list[Path], *, top: int = 8, cell_size: int = 16, limit_per_blueprint: int = 8) -> dict[str, Any]:
    learning = learn_library(paths, top=top)
    templates: list[TemplateCandidate] = []
    failures: list[dict[str, str]] = []
    for candidate in learning["blackbox_candidates"][:top]:
        source = Path(candidate["source"])
        try:
            blueprint = blueprint_by_path(source, candidate["path"])
        except Exception as exc:  # noqa: BLE001
            failures.append({"path": str(source), "error": str(exc)})
            continue
        if blueprint is None:
            failures.append({"path": str(source), "error": f"blueprint path not found: {candidate['path']}"})
            continue
        templates.extend(
            extract_templates_from_blueprint(
                str(source),
                candidate["path"],
                blueprint,
                category=str(candidate["category"]),
                cell_size=cell_size,
                limit=limit_per_blueprint,
            )
        )

    return {
        "file_count": len(paths),
        "blueprint_candidates": min(top, len(learning["blackbox_candidates"])),
        "template_count": len(templates),
        "failed_files": [*learning["failed_files"], *failures],
        "templates": [asdict(template) for template in templates],
        "lessons": [
            "Template candidates are normalized entity subgraphs; they can be copied, compared, and later packed into generated black boxes.",
            "Recipe-bearing templates are stronger generation evidence than tile-only or route-only cells.",
            "A repeated cell still needs recipe data and in-game validation before it can be treated as a full production module.",
        ],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Template Report",
        "",
        f"- Scanned text files: {summary['file_count']}",
        f"- Blueprint candidates: {summary['blueprint_candidates']}",
        f"- Template candidates: {summary['template_count']}",
        f"- Failed files: {len(summary['failed_files'])}",
        "",
        "## Template Candidates",
        "",
    ]
    for item in summary["templates"][:80]:
        recipes = ", ".join(item["recipes"][:8]) or "none"
        modules = ", ".join(item["item_modules"][:6]) or "none"
        families = ", ".join(f"{name}:{count}" for name, count in item["top_families"][:5]) or "none"
        lines.append(f"### {item['label'] or '<unnamed>'} / {item['fingerprint']}")
        lines.append(
            f"- category={item['category']} occurrences={item['occurrence_count']} cell={item['sample_cell']} "
            f"entities={item['entity_count']} tiles={item['tile_count']} lesson={item['lesson']}"
        )
        lines.append(f"- families={families}")
        lines.append(f"- recipes={recipes}")
        lines.append(f"- modules/items={modules}")
        if item["requests"]:
            lines.append(f"- requests={', '.join(item['requests'][:8])}")
        if item["control_behavior_count"] or item["connection_count"]:
            lines.append(
                f"- control_behavior={item['control_behavior_count']} connections={item['connection_count']}"
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
    parser = argparse.ArgumentParser(description="Extract normalized template candidates from black-box blueprints.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--limit-per-blueprint", type=int, default=8)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    summary = extract_template_library(
        files,
        top=args.top,
        cell_size=args.cell_size,
        limit_per_blueprint=args.limit_per_blueprint,
    )
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
