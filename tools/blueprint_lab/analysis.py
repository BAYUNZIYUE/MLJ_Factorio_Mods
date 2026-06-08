from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .codec import BlueprintCodecError, load_blueprint_file, walk_nodes


BELT_LIKE = {
    "transport-belt",
    "fast-transport-belt",
    "express-transport-belt",
    "turbo-transport-belt",
    "underground-belt",
    "fast-underground-belt",
    "express-underground-belt",
    "turbo-underground-belt",
    "splitter",
    "fast-splitter",
    "express-splitter",
    "turbo-splitter",
}


@dataclass(frozen=True)
class BlueprintMetrics:
    label: str
    path: str
    entity_count: int
    tile_count: int
    width: float
    height: float
    area: float
    density: float
    top_entities: list[tuple[str, int]]
    edge_belt_like: int


@dataclass(frozen=True)
class FileSummary:
    path: str
    kind_counts: dict[str, int]
    blueprint_count: int
    entity_count: int
    tile_count: int
    largest_blueprints: list[BlueprintMetrics]
    densest_blueprints: list[BlueprintMetrics]


def iter_blueprint_text_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".bp", ".blueprint"}
    )


def blueprint_metrics(node_path: str, blueprint: dict[str, Any]) -> BlueprintMetrics:
    entities = blueprint.get("entities") or []
    tiles = blueprint.get("tiles") or []
    xs: list[float] = []
    ys: list[float] = []
    for item in [*entities, *tiles]:
        position = item.get("position") or {}
        xs.append(float(position.get("x", 0)))
        ys.append(float(position.get("y", 0)))

    if xs and ys:
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        width = max_x - min_x + 1
        height = max_y - min_y + 1
    else:
        min_x = max_x = min_y = max_y = width = height = 0.0

    counter = Counter(entity.get("name", "") for entity in entities)
    edge_belt_like = 0
    for entity in entities:
        if entity.get("name") not in BELT_LIKE:
            continue
        position = entity.get("position") or {}
        x = float(position.get("x", 0))
        y = float(position.get("y", 0))
        if x in (min_x, max_x) or y in (min_y, max_y):
            edge_belt_like += 1

    area = width * height if width and height else 0.0
    density = (len(entities) + len(tiles)) / area if area else 0.0
    return BlueprintMetrics(
        label=str(blueprint.get("label") or ""),
        path=node_path,
        entity_count=len(entities),
        tile_count=len(tiles),
        width=width,
        height=height,
        area=area,
        density=density,
        top_entities=counter.most_common(8),
        edge_belt_like=edge_belt_like,
    )


def summarize_file(path: Path) -> FileSummary:
    wrapper = load_blueprint_file(path)
    kind_counts: Counter[str] = Counter()
    metrics: list[BlueprintMetrics] = []
    for node in walk_nodes(wrapper):
        kind_counts[node.kind] += 1
        if node.kind == "blueprint":
            metrics.append(blueprint_metrics(node.path, node.payload))

    largest = sorted(metrics, key=lambda item: item.entity_count, reverse=True)[:10]
    densest = sorted(
        [item for item in metrics if item.entity_count >= 30 and item.area >= 30],
        key=lambda item: item.density,
        reverse=True,
    )[:10]
    return FileSummary(
        path=str(path),
        kind_counts=dict(kind_counts),
        blueprint_count=len(metrics),
        entity_count=sum(item.entity_count for item in metrics),
        tile_count=sum(item.tile_count for item in metrics),
        largest_blueprints=largest,
        densest_blueprints=densest,
    )


def summarize_library(paths: list[Path]) -> dict[str, Any]:
    summaries: list[FileSummary] = []
    failures: list[dict[str, str]] = []
    for path in paths:
        try:
            summaries.append(summarize_file(path))
        except (BlueprintCodecError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append({"path": str(path), "error": str(exc)})

    total_kinds: defaultdict[str, int] = defaultdict(int)
    for summary in summaries:
        for kind, count in summary.kind_counts.items():
            total_kinds[kind] += count

    return {
        "file_count": len(paths),
        "decoded_files": len(summaries),
        "failed_files": failures,
        "kind_counts": dict(total_kinds),
        "blueprint_count": sum(summary.blueprint_count for summary in summaries),
        "entity_count": sum(summary.entity_count for summary in summaries),
        "tile_count": sum(summary.tile_count for summary in summaries),
        "top_files_by_entities": [asdict(item) for item in sorted(summaries, key=lambda item: item.entity_count, reverse=True)[:12]],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Corpus Report",
        "",
        f"- Scanned text files: {summary['file_count']}",
        f"- Decoded blueprint files: {summary['decoded_files']}",
        f"- Failed text files: {len(summary['failed_files'])}",
        f"- Node counts: {summary['kind_counts']}",
        f"- Blueprints: {summary['blueprint_count']}",
        f"- Entities: {summary['entity_count']}",
        f"- Tiles: {summary['tile_count']}",
        "",
        "## Top Files By Entities",
        "",
    ]
    for file_summary in summary["top_files_by_entities"]:
        lines.append(f"### {file_summary['path']}")
        lines.append(
            f"- blueprints={file_summary['blueprint_count']} entities={file_summary['entity_count']} tiles={file_summary['tile_count']}"
        )
        lines.append("- largest blueprints:")
        for item in file_summary["largest_blueprints"][:5]:
            lines.append(
                f"  - {item['label'] or '<unnamed>'}: entities={item['entity_count']} tiles={item['tile_count']} "
                f"size={item['width']:.1f}x{item['height']:.1f} density={item['density']:.3f}"
            )
        lines.append("- densest nontrivial blueprints:")
        for item in file_summary["densest_blueprints"][:5]:
            lines.append(
                f"  - {item['label'] or '<unnamed>'}: entities={item['entity_count']} tiles={item['tile_count']} "
                f"size={item['width']:.1f}x{item['height']:.1f} density={item['density']:.3f} edge_belt_like={item['edge_belt_like']}"
            )
        lines.append("")

    if summary["failed_files"]:
        lines.extend(["## Failed Files", ""])
        for failure in summary["failed_files"][:50]:
            lines.append(f"- {failure['path']}: {failure['error']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze Factorio blueprint strings.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--limit", type=int, default=0, help="Limit the number of text files scanned.")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))
    if args.limit:
        files = files[: args.limit]

    summary = summarize_library(files)
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

