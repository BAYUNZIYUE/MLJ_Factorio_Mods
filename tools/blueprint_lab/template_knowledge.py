from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .analysis import iter_blueprint_text_files
from .directions import belt_boundary_role
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
    machine_speeds: list[tuple[str, float]]
    unknown_machine_names: list[str]
    base_crafts_per_minute: float | None
    base_ingredients_per_minute: list[tuple[str, float]]
    base_products_per_minute: list[tuple[str, float]]
    direct_module_effects: list[tuple[str, float]]
    direct_module_items: list[tuple[str, str, int]]
    effective_crafts_per_minute: float | None
    effective_ingredients_per_minute: list[tuple[str, float]]
    effective_products_per_minute: list[tuple[str, float]]
    effective_with_beacons_effects: list[tuple[str, float]]
    effective_with_beacons_module_items: list[tuple[str, str, int]]
    effective_with_beacons_crafts_per_minute: float | None
    effective_with_beacons_ingredients_per_minute: list[tuple[str, float]]
    effective_with_beacons_products_per_minute: list[tuple[str, float]]


@dataclass(frozen=True)
class TemplatePortHint:
    side: str
    role: str
    entity_name: str
    direction: int | None
    x: float
    y: float


@dataclass(frozen=True)
class TemplateEntityHint:
    name: str
    x: float
    y: float
    direction: int | None
    entity_type: str | None
    recipe: str | None
    recipe_quality: str | None
    quality: str | None
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TemplateTileHint:
    name: str
    x: float
    y: float


@dataclass(frozen=True)
class TemplateLayoutHint:
    width: float
    height: float
    entity_count: int
    tile_count: int
    cell_size: int
    ports: list[TemplatePortHint]
    port_counts: list[tuple[str, int]]
    entities: list[TemplateEntityHint]
    tiles: list[TemplateTileHint]


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
    layout: TemplateLayoutHint


def recipe_machines(template: TemplateCandidate, recipe: str) -> list[str]:
    return sorted(
        {
            entity.name
            for entity in template.normalized_entities
            if entity.recipe == recipe
        }
    )


def recipe_machine_speed_sum(
    template: TemplateCandidate,
    recipe: str,
    knowledge: PrototypeKnowledge,
) -> tuple[list[tuple[str, float]], list[str], float]:
    speed_counts: Counter[tuple[str, float]] = Counter()
    unknown: Counter[str] = Counter()
    total_speed = 0.0
    for entity in template.normalized_entities:
        if entity.recipe != recipe:
            continue
        prototype = knowledge.entity(entity.name)
        if prototype is None:
            unknown[entity.name] += 1
            continue
        speed_counts[(entity.name, prototype.crafting_speed)] += 1
        total_speed += prototype.crafting_speed

    machine_speeds = [
        (f"{count}x {name}", speed)
        for (name, speed), count in sorted(speed_counts.items(), key=lambda item: item[0][0])
    ]
    unknown_names = [
        f"{count}x {name}"
        for name, count in sorted(unknown.items())
    ]
    return machine_speeds, unknown_names, total_speed


def item_stack_count(item: dict[str, Any]) -> int:
    item_payload = item.get("items")
    if not isinstance(item_payload, dict):
        return 1
    inventory = item_payload.get("in_inventory")
    if isinstance(inventory, list):
        return len(inventory)
    return 1


def entity_module_items(entity: Any) -> list[tuple[str, str, int]]:
    items: list[tuple[str, str, int]] = []
    for item in entity.item_stacks:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item_id, dict) or not item_id.get("name"):
            continue
        items.append(
            (
                str(item_id["name"]),
                str(item_id.get("quality") or "normal"),
                item_stack_count(item),
            )
        )
    return items


def direct_module_effects_for_entity(entity: Any, knowledge: PrototypeKnowledge) -> tuple[Counter[str], list[tuple[str, str, int]]]:
    effects: Counter[str] = Counter()
    module_items = entity_module_items(entity)
    for module_name, quality_name, count in module_items:
        module = knowledge.module(module_name)
        if module is None:
            continue
        quality_multiplier = knowledge.quality_effect_multiplier(quality_name)
        for effect_name, effect_value in module.effects.items():
            value = effect_value * quality_multiplier if effect_value > 0 else effect_value
            effects[effect_name] += value * count
    return effects, module_items


def module_effects_for_beacon(entity: Any, knowledge: PrototypeKnowledge) -> tuple[Counter[str], list[tuple[str, str, int]]]:
    effects, module_items = direct_module_effects_for_entity(entity, knowledge)
    beacon = knowledge.beacon(entity.name)
    if beacon is None or not beacon.allowed_effects:
        return effects, module_items
    allowed = set(beacon.allowed_effects)
    return Counter({name: value for name, value in effects.items() if name in allowed}), module_items


def beacon_profile_factor(profile: list[float], beacon_count: int) -> float:
    if beacon_count <= 0:
        return 0.0
    if not profile:
        return 1.0
    index = min(beacon_count - 1, len(profile) - 1)
    return profile[index]


def entity_in_beacon_range(machine: Any, beacon_entity: Any, knowledge: PrototypeKnowledge) -> bool:
    beacon = knowledge.beacon(beacon_entity.name)
    if beacon is None:
        return False
    return (
        abs(float(machine.x) - float(beacon_entity.x)) <= beacon.supply_area_distance
        and abs(float(machine.y) - float(beacon_entity.y)) <= beacon.supply_area_distance
    )


def beacon_effects_for_machine(
    machine: Any,
    template: TemplateCandidate,
    knowledge: PrototypeKnowledge,
) -> tuple[Counter[str], list[tuple[str, str, int]]]:
    beacons = [
        entity
        for entity in template.normalized_entities
        if knowledge.beacon(entity.name) is not None and entity_in_beacon_range(machine, entity, knowledge)
    ]
    beacon_count = len(beacons)
    total_effects: Counter[str] = Counter()
    module_items: Counter[tuple[str, str]] = Counter()
    for beacon_entity in beacons:
        beacon = knowledge.beacon(beacon_entity.name)
        if beacon is None:
            continue
        profile_factor = beacon_profile_factor(beacon.profile, beacon_count)
        effects, items = module_effects_for_beacon(beacon_entity, knowledge)
        for effect_name, effect_value in effects.items():
            total_effects[effect_name] += effect_value * beacon.distribution_effectivity * profile_factor
        for module_name, quality_name, count in items:
            module_items[(module_name, quality_name)] += count
    return (
        total_effects,
        [(name, quality, count) for (name, quality), count in sorted(module_items.items())],
    )


def effective_recipe_rates(
    template: TemplateCandidate,
    recipe: str,
    knowledge: PrototypeKnowledge,
    recipe_energy_required: float,
    *,
    include_beacons: bool = False,
) -> tuple[float | None, list[tuple[str, float]], list[tuple[str, str, int]]]:
    if recipe_energy_required <= 0:
        return None, [], []

    total_crafts = 0.0
    total_effects: Counter[str] = Counter()
    module_items: Counter[tuple[str, str]] = Counter()
    for entity in template.normalized_entities:
        if entity.recipe != recipe:
            continue
        prototype = knowledge.entity(entity.name)
        if prototype is None:
            return None, [], []
        machine_quality_multiplier = knowledge.quality_effect_multiplier(entity.quality)
        direct_effects, direct_items = direct_module_effects_for_entity(entity, knowledge)
        combined_effects: Counter[str] = Counter(direct_effects)
        for module_name, quality_name, count in direct_items:
            module_items[(module_name, quality_name)] += count
        if include_beacons:
            beacon_effects, beacon_items = beacon_effects_for_machine(entity, template, knowledge)
            combined_effects.update(beacon_effects)
            for module_name, quality_name, count in beacon_items:
                module_items[(module_name, quality_name)] += count
        total_effects.update(combined_effects)
        speed_bonus = combined_effects.get("speed", 0.0)
        entity_speed = prototype.crafting_speed * machine_quality_multiplier * max(0.0, 1.0 + speed_bonus)
        total_crafts += entity_speed * 60 / recipe_energy_required

    return (
        total_crafts,
        sorted(total_effects.items()),
        [(name, quality, count) for (name, quality), count in sorted(module_items.items())],
    )


def scaled_rates(items: list[tuple[str, float]], crafts_per_minute: float) -> list[tuple[str, float]]:
    return [(name, amount * crafts_per_minute) for name, amount in items]


def template_side(x: float, y: float, min_x: float, max_x: float, min_y: float, max_y: float, margin: float = 1.0) -> str | None:
    if x <= min_x + margin:
        return "left"
    if x >= max_x - margin:
        return "right"
    if y <= min_y + margin:
        return "top"
    if y >= max_y - margin:
        return "bottom"
    return None


def template_port_role(side: str, direction: int | None) -> str:
    return belt_boundary_role(side, direction)


def template_layout_hint(template: TemplateCandidate) -> TemplateLayoutHint:
    entities = template.normalized_entities
    if not entities:
        return TemplateLayoutHint(
            width=float(template.cell_size),
            height=float(template.cell_size),
            entity_count=template.entity_count,
            tile_count=template.tile_count,
            cell_size=template.cell_size,
            ports=[],
            port_counts=[],
            entities=[],
            tiles=[],
        )

    min_x = min(entity.x for entity in entities)
    max_x = max(entity.x for entity in entities)
    min_y = min(entity.y for entity in entities)
    max_y = max(entity.y for entity in entities)
    width = max(1.0, max_x - min_x + 1)
    height = max(1.0, max_y - min_y + 1)
    port_families = {"transport-belt", "underground-belt", "splitter", "fluid", "rail", "logistics-storage"}
    ports: list[TemplatePortHint] = []
    for entity in entities:
        if entity.family not in port_families:
            continue
        side = template_side(entity.x, entity.y, min_x, max_x, min_y, max_y)
        if side is None:
            continue
        role = template_port_role(side, entity.direction) if entity.family in {
            "transport-belt",
            "underground-belt",
            "splitter",
        } else "boundary"
        ports.append(
            TemplatePortHint(
                side=side,
                role=role,
                entity_name=entity.name,
                direction=entity.direction,
                x=entity.x,
                y=entity.y,
            )
        )
    counts = Counter(f"{port.side}:{port.role}" for port in ports)
    return TemplateLayoutHint(
        width=round(width, 3),
        height=round(height, 3),
        entity_count=template.entity_count,
        tile_count=template.tile_count,
        cell_size=template.cell_size,
        ports=ports,
        port_counts=sorted(counts.items()),
        entities=[
            TemplateEntityHint(
                name=entity.name,
                x=entity.x,
                y=entity.y,
                direction=entity.direction,
                entity_type=entity.entity_type,
                recipe=entity.recipe,
                recipe_quality=entity.recipe_quality,
                quality=entity.quality,
                items=entity.item_stacks,
            )
            for entity in entities
        ],
        tiles=[
            TemplateTileHint(
                name=tile.name,
                x=tile.x,
                y=tile.y,
            )
            for tile in template.normalized_tiles
        ],
    )


def map_template(template: TemplateCandidate, knowledge: PrototypeKnowledge) -> TemplateKnowledgeMapping:
    mappings: list[RecipeMapping] = []
    unresolved: list[str] = []
    for recipe_name in template.recipes:
        recipe = knowledge.recipe(recipe_name)
        machine_names = recipe_machines(template, recipe_name)
        machine_count = sum(1 for entity in template.normalized_entities if entity.recipe == recipe_name)
        machine_speeds, unknown_machine_names, base_speed_sum = recipe_machine_speed_sum(
            template,
            recipe_name,
            knowledge,
        )
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
                    machine_speeds=machine_speeds,
                    unknown_machine_names=unknown_machine_names,
                    base_crafts_per_minute=None,
                    base_ingredients_per_minute=[],
                    base_products_per_minute=[],
                    direct_module_effects=[],
                    direct_module_items=[],
                    effective_crafts_per_minute=None,
                    effective_ingredients_per_minute=[],
                    effective_products_per_minute=[],
                    effective_with_beacons_effects=[],
                    effective_with_beacons_module_items=[],
                    effective_with_beacons_crafts_per_minute=None,
                    effective_with_beacons_ingredients_per_minute=[],
                    effective_with_beacons_products_per_minute=[],
                )
            )
        else:
            ingredients = [(item.name, item.amount) for item in recipe.ingredients]
            products = [(item.name, item.amount * item.probability) for item in recipe.products]
            base_crafts = None
            base_ingredients: list[tuple[str, float]] = []
            base_products: list[tuple[str, float]] = []
            if recipe.energy_required > 0 and base_speed_sum > 0 and not unknown_machine_names:
                base_crafts = base_speed_sum * 60 / recipe.energy_required
                base_ingredients = scaled_rates(ingredients, base_crafts)
                base_products = scaled_rates(products, base_crafts)
            effective_crafts, direct_module_effects, direct_module_items = effective_recipe_rates(
                template,
                recipe_name,
                knowledge,
                recipe.energy_required,
            )
            effective_with_beacons_crafts, effective_with_beacons_effects, effective_with_beacons_module_items = effective_recipe_rates(
                template,
                recipe_name,
                knowledge,
                recipe.energy_required,
                include_beacons=True,
            )
            if (
                effective_with_beacons_crafts == effective_crafts
                and effective_with_beacons_effects == direct_module_effects
                and effective_with_beacons_module_items == direct_module_items
            ):
                effective_with_beacons_crafts = None
                effective_with_beacons_effects = []
                effective_with_beacons_module_items = []
            effective_ingredients: list[tuple[str, float]] = []
            effective_products: list[tuple[str, float]] = []
            if effective_crafts is not None:
                productivity_bonus = max(
                    0.0,
                    dict(direct_module_effects).get("productivity", 0.0),
                )
                effective_ingredients = scaled_rates(ingredients, effective_crafts)
                effective_products = [
                    (name, amount * effective_crafts * (1.0 + productivity_bonus))
                    for name, amount in products
                ]
            effective_with_beacons_ingredients: list[tuple[str, float]] = []
            effective_with_beacons_products: list[tuple[str, float]] = []
            if effective_with_beacons_crafts is not None:
                productivity_bonus = max(
                    0.0,
                    dict(effective_with_beacons_effects).get("productivity", 0.0),
                )
                effective_with_beacons_ingredients = scaled_rates(ingredients, effective_with_beacons_crafts)
                effective_with_beacons_products = [
                    (name, amount * effective_with_beacons_crafts * (1.0 + productivity_bonus))
                    for name, amount in products
                ]
            mappings.append(
                RecipeMapping(
                    recipe=recipe_name,
                    status="resolved",
                    category=recipe.category,
                    energy_required=recipe.energy_required,
                    ingredients=ingredients,
                    products=products,
                    machine_names=machine_names,
                    machine_count=machine_count,
                    machine_speeds=machine_speeds,
                    unknown_machine_names=unknown_machine_names,
                    base_crafts_per_minute=base_crafts,
                    base_ingredients_per_minute=base_ingredients,
                    base_products_per_minute=base_products,
                    direct_module_effects=direct_module_effects,
                    direct_module_items=direct_module_items,
                    effective_crafts_per_minute=effective_crafts,
                    effective_ingredients_per_minute=effective_ingredients,
                    effective_products_per_minute=effective_products,
                    effective_with_beacons_effects=effective_with_beacons_effects,
                    effective_with_beacons_module_items=effective_with_beacons_module_items,
                    effective_with_beacons_crafts_per_minute=effective_with_beacons_crafts,
                    effective_with_beacons_ingredients_per_minute=effective_with_beacons_ingredients,
                    effective_with_beacons_products_per_minute=effective_with_beacons_products,
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
        layout=template_layout_hint(template),
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
    from .templates import NormalizedEntity, NormalizedTile

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
                normalized_tiles=[NormalizedTile(**tile) for tile in raw.get("normalized_tiles") or []],
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
            "Base throughput is computed from recipe time and machine crafting speed only.",
            "Effective throughput applies machine quality, direct module effects, and a conservative same-template beacon estimate.",
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
        layout = item["layout"]
        lines.append(
            f"- layout={layout['width']:g}x{layout['height']:g} entities={layout['entity_count']} tiles={layout['tile_count']}"
        )
        if layout["port_counts"]:
            port_counts = ", ".join(f"{name}:{count}" for name, count in layout["port_counts"])
            lines.append(f"- ports={port_counts}")
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
                if mapping["machine_speeds"]:
                    speeds = ", ".join(f"{name}@{speed:g}" for name, speed in mapping["machine_speeds"])
                    lines.append(f"  base_machine_speeds={speeds}")
                if mapping["base_crafts_per_minute"] is not None:
                    base_inputs = (
                        ", ".join(
                            f"{name}:{amount:g}/min"
                            for name, amount in mapping["base_ingredients_per_minute"]
                        )
                        or "none"
                    )
                    base_outputs = (
                        ", ".join(
                            f"{name}:{amount:g}/min"
                            for name, amount in mapping["base_products_per_minute"]
                        )
                        or "none"
                    )
                    lines.append(
                        f"  base_without_modules={mapping['base_crafts_per_minute']:g} crafts/min inputs=[{base_inputs}] outputs=[{base_outputs}]"
                    )
                if mapping.get("direct_module_items"):
                    modules = ", ".join(
                        f"{count}x {quality} {name}"
                        for name, quality, count in mapping["direct_module_items"]
                    )
                    lines.append(f"  direct_modules={modules}")
                if mapping.get("direct_module_effects"):
                    effects = ", ".join(
                        f"{name}:{value:g}"
                        for name, value in mapping["direct_module_effects"]
                    )
                    lines.append(f"  direct_module_effects={effects}")
                if mapping.get("effective_crafts_per_minute") is not None:
                    effective_inputs = (
                        ", ".join(
                            f"{name}:{amount:g}/min"
                            for name, amount in mapping["effective_ingredients_per_minute"]
                        )
                        or "none"
                    )
                    effective_outputs = (
                        ", ".join(
                            f"{name}:{amount:g}/min"
                            for name, amount in mapping["effective_products_per_minute"]
                        )
                        or "none"
                    )
                    lines.append(
                        f"  effective_direct_modules={mapping['effective_crafts_per_minute']:g} crafts/min inputs=[{effective_inputs}] outputs=[{effective_outputs}]"
                    )
                if mapping.get("effective_with_beacons_module_items"):
                    modules = ", ".join(
                        f"{count}x {quality} {name}"
                        for name, quality, count in mapping["effective_with_beacons_module_items"]
                    )
                    lines.append(f"  effective_with_beacons_modules={modules}")
                if mapping.get("effective_with_beacons_effects"):
                    effects = ", ".join(
                        f"{name}:{value:g}"
                        for name, value in mapping["effective_with_beacons_effects"]
                    )
                    lines.append(f"  effective_with_beacons_effects={effects}")
                if mapping.get("effective_with_beacons_crafts_per_minute") is not None:
                    effective_inputs = (
                        ", ".join(
                            f"{name}:{amount:g}/min"
                            for name, amount in mapping["effective_with_beacons_ingredients_per_minute"]
                        )
                        or "none"
                    )
                    effective_outputs = (
                        ", ".join(
                            f"{name}:{amount:g}/min"
                            for name, amount in mapping["effective_with_beacons_products_per_minute"]
                        )
                        or "none"
                    )
                    lines.append(
                        f"  effective_with_beacons={mapping['effective_with_beacons_crafts_per_minute']:g} crafts/min inputs=[{effective_inputs}] outputs=[{effective_outputs}]"
                    )
                elif mapping["unknown_machine_names"]:
                    lines.append(
                        f"  base_without_modules=unknown unknown_machines={', '.join(mapping['unknown_machine_names'])}"
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
