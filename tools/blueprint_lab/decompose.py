from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .analysis import BELT_LIKE, blueprint_metrics, iter_blueprint_text_files
from .codec import load_blueprint_file, walk_nodes
from .directions import belt_boundary_role, direction_name
from .learn import learn_library


@dataclass(frozen=True)
class BoundaryPort:
    side: str
    role: str
    entity_name: str
    direction: str
    x: float
    y: float


@dataclass(frozen=True)
class RepeatedModule:
    signature: str
    count: int
    sample_cells: list[tuple[int, int]]
    dominant_families: list[tuple[str, int]]


@dataclass(frozen=True)
class BlueprintDecomposition:
    source: str
    path: str
    label: str
    category: str
    width: float
    height: float
    entity_count: int
    tile_count: int
    density: float
    aspect_ratio: float
    orientation: str
    cell_size: int
    grid_width: int
    grid_height: int
    occupied_cells: int
    boundary_ports: list[BoundaryPort]
    repeated_modules: list[RepeatedModule]
    lessons: list[str]


def entity_family(name: str) -> str:
    if name in BELT_LIKE:
        if "splitter" in name:
            return "splitter"
        if "underground" in name:
            return "underground-belt"
        return "transport-belt"
    if "inserter" in name:
        return "inserter"
    if "pipe" in name or name in {"pump", "offshore-pump"}:
        return "fluid"
    if "rail" in name or name in {"train-stop", "rail-signal", "rail-chain-signal"}:
        return "rail"
    if "combinator" in name or "lamp" in name or "speaker" in name:
        return "circuit"
    if "chest" in name or "cargo" in name or "warehouse" in name:
        return "logistics-storage"
    if "furnace" in name or name in {"foundry"}:
        return "smelting-machine"
    if "assembling-machine" in name or name in {
        "chemical-plant",
        "oil-refinery",
        "biochamber",
        "electromagnetic-plant",
        "cryogenic-plant",
        "crusher",
        "recycler",
        "lab",
        "biolab",
        "rocket-silo",
    }:
        return "production-machine"
    if "beacon" in name:
        return "beacon"
    if name in {"substation", "small-electric-pole", "medium-electric-pole", "big-electric-pole"}:
        return "power-pole"
    if name in {"solar-panel", "accumulator", "nuclear-reactor", "heat-pipe", "steam-turbine", "fusion-reactor", "fusion-generator"}:
        return "power-production"
    if "turret" in name or "wall" in name or "gate" in name:
        return "defense"
    if "space-platform" in name or name in {"asteroid-collector", "thruster"}:
        return "space-platform"
    return "other"


def all_positions(blueprint: dict[str, Any]) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for item in [*(blueprint.get("entities") or []), *(blueprint.get("tiles") or [])]:
        position = item.get("position") or {}
        xs.append(float(position.get("x", 0)))
        ys.append(float(position.get("y", 0)))
    return xs, ys


def boundary_side(x: float, y: float, min_x: float, max_x: float, min_y: float, max_y: float, margin: float) -> str | None:
    if x <= min_x + margin:
        return "left"
    if x >= max_x - margin:
        return "right"
    if y <= min_y + margin:
        return "top"
    if y >= max_y - margin:
        return "bottom"
    return None


def belt_role(side: str, direction: int | None) -> str:
    return belt_boundary_role(side, direction)


def boundary_ports(blueprint: dict[str, Any], margin: float = 1.0) -> list[BoundaryPort]:
    xs, ys = all_positions(blueprint)
    if not xs or not ys:
        return []
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    ports: list[BoundaryPort] = []
    port_families = {"transport-belt", "underground-belt", "splitter", "fluid", "rail", "logistics-storage"}
    for entity in blueprint.get("entities") or []:
        position = entity.get("position") or {}
        x = float(position.get("x", 0))
        y = float(position.get("y", 0))
        side = boundary_side(x, y, min_x, max_x, min_y, max_y, margin)
        if side is None:
            continue
        name = str(entity.get("name") or "")
        family = entity_family(name)
        if family not in port_families:
            continue
        direction = entity.get("direction")
        role = belt_role(side, int(direction) if isinstance(direction, int) else None) if family in {
            "transport-belt",
            "underground-belt",
            "splitter",
        } else "boundary"
        ports.append(
            BoundaryPort(
                side=side,
                role=role,
                entity_name=name,
                direction=direction_name(direction if isinstance(direction, int) else None),
                x=x,
                y=y,
            )
        )
    return ports


def cell_signatures(blueprint: dict[str, Any], cell_size: int) -> tuple[dict[tuple[int, int], Counter[str]], int, int]:
    xs, ys = all_positions(blueprint)
    if not xs or not ys:
        return {}, 0, 0
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    grid_width = max(1, math.ceil((max_x - min_x + 1) / cell_size))
    grid_height = max(1, math.ceil((max_y - min_y + 1) / cell_size))
    cells: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)

    for entity in blueprint.get("entities") or []:
        position = entity.get("position") or {}
        cx = int((float(position.get("x", 0)) - min_x) // cell_size)
        cy = int((float(position.get("y", 0)) - min_y) // cell_size)
        cells[(cx, cy)][entity_family(str(entity.get("name") or ""))] += 1

    for tile in blueprint.get("tiles") or []:
        position = tile.get("position") or {}
        cx = int((float(position.get("x", 0)) - min_x) // cell_size)
        cy = int((float(position.get("y", 0)) - min_y) // cell_size)
        cells[(cx, cy)]["tile"] += 1

    return cells, grid_width, grid_height


def signature_from_counter(counter: Counter[str]) -> str:
    return "|".join(f"{key}:{value}" for key, value in sorted(counter.items()) if value)


def repeated_modules(blueprint: dict[str, Any], cell_size: int, limit: int = 8) -> tuple[list[RepeatedModule], int, int, int]:
    cells, grid_width, grid_height = cell_signatures(blueprint, cell_size)
    grouped: dict[str, list[tuple[tuple[int, int], Counter[str]]]] = defaultdict(list)
    for cell, counter in cells.items():
        signature = signature_from_counter(counter)
        if signature:
            grouped[signature].append((cell, counter))

    modules: list[RepeatedModule] = []
    for signature, items in grouped.items():
        if len(items) < 2:
            continue
        aggregate: Counter[str] = Counter()
        for _, counter in items:
            aggregate.update(counter)
        modules.append(
            RepeatedModule(
                signature=signature,
                count=len(items),
                sample_cells=[cell for cell, _ in items[:6]],
                dominant_families=aggregate.most_common(6),
            )
        )

    modules = sorted(modules, key=lambda item: (item.count, sum(value for _, value in item.dominant_families)), reverse=True)
    return modules[:limit], grid_width, grid_height, len(cells)


def orientation(width: float, height: float) -> str:
    if not width or not height:
        return "empty"
    ratio = max(width, height) / min(width, height)
    if ratio < 1.25:
        return "square-ish"
    if width > height:
        return "horizontal-rectangle"
    return "vertical-rectangle"


def decompose_blueprint(
    source: str,
    node_path: str,
    blueprint: dict[str, Any],
    *,
    category: str = "unknown",
    cell_size: int = 16,
) -> BlueprintDecomposition:
    metrics = blueprint_metrics(node_path, blueprint)
    ports = boundary_ports(blueprint)
    modules, grid_width, grid_height, occupied_cells = repeated_modules(blueprint, cell_size)
    aspect = max(metrics.width, metrics.height) / min(metrics.width, metrics.height) if metrics.width and metrics.height else 0.0
    lessons = [
        f"boundary has {len(ports)} logistics/fluid/rail-like ports",
        f"grid {grid_width}x{grid_height} has {occupied_cells} occupied cells at cell_size={cell_size}",
    ]
    if aspect >= 1.5:
        lessons.append("rectangle favors long straight routing lanes")
    if modules:
        lessons.append(f"found {len(modules)} repeated cell signatures; repeated cells are likely module candidates")
    if metrics.tile_count > metrics.entity_count:
        lessons.append("tile footprint dominates, so compactness must include platform/foundation area")

    return BlueprintDecomposition(
        source=source,
        path=node_path,
        label=str(blueprint.get("label") or ""),
        category=category,
        width=metrics.width,
        height=metrics.height,
        entity_count=metrics.entity_count,
        tile_count=metrics.tile_count,
        density=metrics.density,
        aspect_ratio=aspect,
        orientation=orientation(metrics.width, metrics.height),
        cell_size=cell_size,
        grid_width=grid_width,
        grid_height=grid_height,
        occupied_cells=occupied_cells,
        boundary_ports=ports,
        repeated_modules=modules,
        lessons=lessons,
    )


def blueprint_by_path(source: Path, node_path: str) -> dict[str, Any] | None:
    wrapper = load_blueprint_file(source)
    for node in walk_nodes(wrapper):
        if node.kind == "blueprint" and node.path == node_path:
            return node.payload
    return None


def decompose_library(paths: list[Path], *, top: int = 8, cell_size: int = 16) -> dict[str, Any]:
    learning = learn_library(paths, top=top)
    decompositions: list[BlueprintDecomposition] = []
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
        decompositions.append(
            decompose_blueprint(
                str(source),
                candidate["path"],
                blueprint,
                category=str(candidate["category"]),
                cell_size=cell_size,
            )
        )

    return {
        "file_count": len(paths),
        "candidate_count": len(decompositions),
        "failed_files": [*learning["failed_files"], *failures],
        "decompositions": [asdict(item) for item in decompositions],
        "lessons": [
            "Black-box candidates become useful generator templates only after their edge ports and repeated cells are known.",
            "A generated black box should choose ports first, reserve long routing lanes second, and pack repeated modules last.",
            "Repeated grid signatures are not final recipe modules yet; they are evidence for where to inspect or extract templates next.",
        ],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Decomposition Report",
        "",
        f"- Scanned text files: {summary['file_count']}",
        f"- Decomposed candidates: {summary['candidate_count']}",
        f"- Failed files: {len(summary['failed_files'])}",
        "",
        "## Candidate Decompositions",
        "",
    ]
    for item in summary["decompositions"]:
        lines.append(f"### {item['label'] or '<unnamed>'}")
        lines.append(
            f"- category={item['category']} source={item['source']} path={item['path']}"
        )
        lines.append(
            f"- size={item['width']:.1f}x{item['height']:.1f} orientation={item['orientation']} "
            f"density={item['density']:.3f} entities={item['entity_count']} tiles={item['tile_count']}"
        )
        lines.append(
            f"- grid={item['grid_width']}x{item['grid_height']} occupied_cells={item['occupied_cells']} cell_size={item['cell_size']}"
        )
        port_counts = Counter(f"{port['side']}:{port['role']}" for port in item["boundary_ports"])
        lines.append(f"- boundary_ports={dict(sorted(port_counts.items()))}")
        lines.append("- repeated module signatures:")
        for module in item["repeated_modules"][:5]:
            families = ", ".join(f"{name}:{count}" for name, count in module["dominant_families"][:4])
            lines.append(
                f"  - count={module['count']} cells={module['sample_cells'][:4]} dominant={families}"
            )
        if not item["repeated_modules"]:
            lines.append("  - none detected at this grid size")
        lines.append("- lessons:")
        for lesson in item["lessons"]:
            lines.append(f"  - {lesson}")
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
    parser = argparse.ArgumentParser(description="Decompose learned black-box blueprint candidates.")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--cell-size", type=int, default=16)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_blueprint_text_files(path))

    summary = decompose_library(files, top=args.top, cell_size=args.cell_size)
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
