from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analysis import BELT_LIKE, BlueprintMetrics, blueprint_metrics, iter_blueprint_text_files
from .codec import BlueprintCodecError, load_blueprint_file, walk_nodes


CATEGORY_ORDER = [
    "balancer",
    "smelting",
    "science",
    "quality",
    "space_platform",
    "rail",
    "power",
    "mall",
    "circuit",
    "logistics",
    "defense",
    "other",
]

LABEL_KEYWORDS = {
    "balancer": ("balancer", "均分", "分流", "to ", " lane "),
    "smelting": ("冶炼", "熔炉", "矿", "plate", "ore", "smelt", "foundry"),
    "science": ("science", "科研", "研究", "瓶", "六色", "万瓶", "science-pack"),
    "quality": ("quality", "品质", "传说", "传奇", "legendary", "五星"),
    "space_platform": ("飞船", "货船", "平台", "太空", "space", "星岩", "黑瓶船"),
    "rail": ("铁路", "火车", "车站", "rail", "train", "station"),
    "power": ("发电", "核电", "聚变", "太阳能", "power", "reactor", "solar"),
    "mall": ("超市", "mall", "万能"),
    "circuit": ("信号", "摇摇乐", "combinator", "电路", "数控"),
    "logistics": ("装卸", "货站", "物流", "rocket", "火箭", "运输"),
    "defense": ("防御", "虫巢", "wall", "炮", "turret"),
}

ENTITY_HINTS = {
    "balancer": ("splitter", "fast-splitter", "express-splitter", "turbo-splitter"),
    "smelting": ("stone-furnace", "steel-furnace", "electric-furnace", "foundry"),
    "science": (
        "lab",
        "biolab",
        "agricultural-tower",
        "electromagnetic-plant",
        "biochamber",
        "cryogenic-plant",
    ),
    "quality": ("recycler", "quality-module", "quality-module-2", "quality-module-3"),
    "space_platform": (
        "space-platform-hub",
        "asteroid-collector",
        "crusher",
        "thruster",
        "space-platform-foundation",
    ),
    "rail": ("straight-rail", "curved-rail-a", "curved-rail-b", "train-stop", "rail-signal", "rail-chain-signal"),
    "power": (
        "solar-panel",
        "accumulator",
        "nuclear-reactor",
        "heat-pipe",
        "steam-turbine",
        "fusion-reactor",
        "fusion-generator",
    ),
    "mall": ("assembling-machine", "assembling-machine-2", "assembling-machine-3", "requester-chest"),
    "circuit": ("constant-combinator", "arithmetic-combinator", "decider-combinator", "selector-combinator"),
    "logistics": ("cargo-bay", "rocket-silo", "loader", "loader-1x1"),
    "defense": ("laser-turret", "gun-turret", "tesla-turret", "rocket-turret"),
}

FAMILY_EXPLANATIONS = {
    "balancer": "I/O contract is explicit, so compactness is mostly width, height, edge lane alignment, and splitter/underground economy.",
    "smelting": "Repeated furnace/foundry rows form natural modules; good layouts keep ore and product lanes straight so the module can be copied to full-belt scale.",
    "science": "Science factories are integrated DAGs; the strong examples place intermediate production near consumers and reserve long lanes for high-volume shared inputs.",
    "quality": "Quality loops are dense because recyclers, combinators, beacons, and platform tiles compete for space; tile footprint and circuit density both matter.",
    "space_platform": "Space-platform blueprints optimize a bounded platform rectangle; long strips reduce route crossings for belts, pipes, power, and asteroid processing.",
    "rail": "Rail geometry has hard shape constraints, so these blueprints are better learned as grid modules than as compact production boxes.",
    "power": "Power blueprints often optimize repeatable heat/pipe/electric lanes; long rectangles make expansion and symmetry easier.",
    "mall": "Mall blueprints trade density for coverage and readability; they are useful examples for black-box input buses and item-request boundaries.",
    "circuit": "Circuit-heavy blueprints reveal control patterns, not recipe throughput; they should be learned as logic modules with preserved wiring.",
    "logistics": "Logistics blueprints expose edge throughput and loading boundaries; they are useful for later black-box I/O port design.",
    "defense": "Defense layouts are dominated by coverage and repair supply rather than production throughput.",
    "other": "Unclassified examples still contribute entity fingerprints and size distributions, but they need manual review before becoming templates.",
}


@dataclass(frozen=True)
class LearnedBlueprint:
    source: str
    path: str
    label: str
    category: str
    entity_count: int
    tile_count: int
    width: float
    height: float
    area: float
    density: float
    aspect_ratio: float
    edge_belt_like: int
    top_entities: list[tuple[str, int]]
    reasons: list[str]


@dataclass(frozen=True)
class CategorySummary:
    category: str
    blueprint_count: int
    entity_count: int
    tile_count: int
    median_area: float
    median_density: float
    median_aspect_ratio: float
    representative: list[LearnedBlueprint]
    lesson: str


def classify_blueprint(source_path: Path, node_path: str, metrics: BlueprintMetrics) -> tuple[str, list[str]]:
    text = f"{source_path} {node_path} {metrics.label}".lower()
    entity_names = {name for name, _ in metrics.top_entities}
    scores: Counter[str] = Counter()
    reasons: defaultdict[str, list[str]] = defaultdict(list)

    for category, keywords in LABEL_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text:
                scores[category] += 3
                reasons[category].append(f"label/path contains {keyword!r}")
                break

    for category, hints in ENTITY_HINTS.items():
        matched = sorted(name for name in entity_names if any(hint in name for hint in hints))
        if matched:
            scores[category] += min(4, len(matched) + 1)
            reasons[category].append("entity hints: " + ", ".join(matched[:5]))

    belt_total = sum(count for name, count in metrics.top_entities if name in BELT_LIKE)
    splitter_total = sum(count for name, count in metrics.top_entities if "splitter" in name)
    if metrics.entity_count and belt_total / metrics.entity_count >= 0.45 and splitter_total:
        scores["balancer"] += 3
        reasons["balancer"].append("belt-heavy blueprint with splitter presence")

    if metrics.tile_count > metrics.entity_count and metrics.tile_count >= 100:
        scores["space_platform"] += 1
        reasons["space_platform"].append("tile-heavy footprint")

    if not scores:
        return "other", ["no strong label or entity hint"]

    category = sorted(scores.items(), key=lambda item: (-item[1], CATEGORY_ORDER.index(item[0])))[0][0]
    return category, reasons[category]


def aspect_ratio(metrics: BlueprintMetrics) -> float:
    if not metrics.width or not metrics.height:
        return 0.0
    return max(metrics.width, metrics.height) / min(metrics.width, metrics.height)


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / 2


def iter_learned_blueprints(paths: list[Path]) -> tuple[list[LearnedBlueprint], list[dict[str, str]]]:
    learned: list[LearnedBlueprint] = []
    failures: list[dict[str, str]] = []
    for source in paths:
        try:
            wrapper = load_blueprint_file(source)
        except (BlueprintCodecError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append({"path": str(source), "error": str(exc)})
            continue

        for node in walk_nodes(wrapper):
            if node.kind != "blueprint":
                continue
            metrics = blueprint_metrics(node.path, node.payload)
            category, reasons = classify_blueprint(source, node.path, metrics)
            learned.append(
                LearnedBlueprint(
                    source=str(source),
                    path=node.path,
                    label=metrics.label,
                    category=category,
                    entity_count=metrics.entity_count,
                    tile_count=metrics.tile_count,
                    width=metrics.width,
                    height=metrics.height,
                    area=metrics.area,
                    density=metrics.density,
                    aspect_ratio=aspect_ratio(metrics),
                    edge_belt_like=metrics.edge_belt_like,
                    top_entities=metrics.top_entities,
                    reasons=reasons,
                )
            )
    return learned, failures


def representative_score(item: LearnedBlueprint) -> tuple[float, float, int]:
    rectangular_bonus = 1.0 if 1.5 <= item.aspect_ratio <= 6.0 else 0.0
    size_score = min(item.entity_count / 5000, 1.0)
    density_score = min(item.density, 1.5) / 1.5
    return (rectangular_bonus + size_score + density_score, item.area, item.entity_count)


def summarize_categories(learned: list[LearnedBlueprint], top: int = 6) -> list[CategorySummary]:
    groups: dict[str, list[LearnedBlueprint]] = {category: [] for category in CATEGORY_ORDER}
    for item in learned:
        groups.setdefault(item.category, []).append(item)

    summaries: list[CategorySummary] = []
    for category in CATEGORY_ORDER:
        items = groups.get(category) or []
        if not items:
            continue
        representatives = sorted(items, key=representative_score, reverse=True)[:top]
        summaries.append(
            CategorySummary(
                category=category,
                blueprint_count=len(items),
                entity_count=sum(item.entity_count for item in items),
                tile_count=sum(item.tile_count for item in items),
                median_area=median([item.area for item in items]),
                median_density=median([item.density for item in items]),
                median_aspect_ratio=median([item.aspect_ratio for item in items]),
                representative=representatives,
                lesson=FAMILY_EXPLANATIONS[category],
            )
        )
    return summaries


def learn_library(paths: list[Path], top: int = 6) -> dict[str, Any]:
    learned, failures = iter_learned_blueprints(paths)
    summaries = summarize_categories(learned, top=top)
    blackbox_candidates = [
        item
        for item in learned
        if item.entity_count >= 50
        and item.area >= 100
        and 1.2 <= item.aspect_ratio <= 8.0
        and item.category not in {"balancer", "rail", "defense", "circuit"}
    ]
    blackbox_candidates = sorted(blackbox_candidates, key=representative_score, reverse=True)[:top * 2]
    return {
        "file_count": len(paths),
        "failed_files": failures,
        "blueprint_count": len(learned),
        "category_summaries": [asdict(summary) for summary in summaries],
        "blackbox_candidates": [asdict(item) for item in blackbox_candidates],
        "lessons": {
            "rectangular_blackbox": (
                "Prefer a rectangular boundary with stable edge I/O, then pack repeated production modules inside it. "
                "The corpus shows dense Space Age examples frequently use long strips, not square blocks."
            ),
            "density_score": (
                "Score entities and tiles together. Space-platform and science blueprints can look sparse by entity count "
                "while actually consuming large tile footprints."
            ),
            "route_first": (
                "For end-to-end factories, route high-volume belts, pipes, heat, and platform lanes before local decoration. "
                "Late routing is what usually destroys compactness."
            ),
        },
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Learning Report",
        "",
        f"- Scanned text files: {summary['file_count']}",
        f"- Decoded blueprints: {summary['blueprint_count']}",
        f"- Failed files: {len(summary['failed_files'])}",
        "",
        "## Category Summaries",
        "",
    ]
    for category in summary["category_summaries"]:
        lines.append(f"### {category['category']}")
        lines.append(
            f"- blueprints={category['blueprint_count']} entities={category['entity_count']} tiles={category['tile_count']} "
            f"median_area={category['median_area']:.1f} median_density={category['median_density']:.3f} "
            f"median_aspect={category['median_aspect_ratio']:.2f}"
        )
        lines.append(f"- lesson: {category['lesson']}")
        lines.append("- representative examples:")
        for item in category["representative"][:5]:
            reasons = "; ".join(item["reasons"])
            lines.append(
                f"  - {item['label'] or '<unnamed>'}: category={item['category']} entities={item['entity_count']} "
                f"tiles={item['tile_count']} size={item['width']:.1f}x{item['height']:.1f} "
                f"density={item['density']:.3f} aspect={item['aspect_ratio']:.2f} reasons={reasons}"
            )
        lines.append("")

    lines.extend(["## Black-Box Candidates", ""])
    for item in summary["blackbox_candidates"]:
        lines.append(
            f"- {item['label'] or '<unnamed>'}: category={item['category']} entities={item['entity_count']} "
            f"tiles={item['tile_count']} size={item['width']:.1f}x{item['height']:.1f} "
            f"density={item['density']:.3f} aspect={item['aspect_ratio']:.2f} source={item['source']}"
        )

    lines.extend(["", "## Cross-Corpus Lessons", ""])
    for name, lesson in summary["lessons"].items():
        lines.append(f"- {name}: {lesson}")

    if summary["failed_files"]:
        lines.extend(["", "## Failed Files", ""])
        for failure in summary["failed_files"][:50]:
            lines.append(f"- {failure['path']}: {failure['error']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Learn blueprint families and representative layout lessons.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--top", type=int, default=6)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    summary = learn_library(files, top=args.top)
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
