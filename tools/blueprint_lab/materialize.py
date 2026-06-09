from __future__ import annotations

import argparse
import copy
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from .analysis import blueprint_metrics, iter_blueprint_text_files
from .codec import make_blueprint_wrapper, save_blueprint_file
from .directions import DIR_EAST, DIR_NORTH, DIR_SOUTH, DIR_WEST
from .generate import icon
from .layout_plan import build_layout_plan, mapping_by_fingerprint
from .production_dag import (
    build_production_plan,
    default_boundary_items,
    template_options_from_mappings,
)
from .prototypes import PrototypeKnowledge, load_data_raw, target_rate_basis_from_args
from .template_knowledge import map_template_library


RoutePosition = tuple[float, float, str, int, str]
RouteEntitySpec = dict[str, Any]


def materialized_entity(raw: dict[str, Any], entity_number: int, *, x: float, y: float) -> dict[str, Any]:
    entity: dict[str, Any] = {
        "entity_number": entity_number,
        "name": raw["name"],
        "position": {
            "x": round(x + float(raw["x"]), 3),
            "y": round(y + float(raw["y"]), 3),
        },
    }
    if raw.get("direction") is not None:
        entity["direction"] = int(raw["direction"])
    entity_type = raw.get("type") or raw.get("entity_type")
    if entity_type:
        entity["type"] = str(entity_type)
    if raw.get("recipe"):
        entity["recipe"] = raw["recipe"]
    if raw.get("recipe_quality"):
        entity["recipe_quality"] = raw["recipe_quality"]
    if raw.get("quality"):
        entity["quality"] = raw["quality"]
    if raw.get("items"):
        entity["items"] = copy.deepcopy(raw["items"])
    for field in ("filter", "input_priority", "output_priority"):
        if raw.get(field) is not None:
            entity[field] = copy.deepcopy(raw[field])
    return entity


def entity_position_key(entity: dict[str, Any]) -> tuple[float, float]:
    position = entity.get("position") or {}
    return (round(float(position.get("x", 0)), 3), round(float(position.get("y", 0)), 3))


def connector_belt(entity_number: int, x: float, y: float, *, direction: int = DIR_EAST, name: str = "transport-belt") -> dict[str, Any]:
    return {
        "entity_number": entity_number,
        "name": name,
        "position": {"x": round(x, 3), "y": round(y, 3)},
        "direction": direction,
    }


def connector_belt_from_spec(entity_number: int, spec: RouteEntitySpec) -> dict[str, Any]:
    entity = connector_belt(
        entity_number,
        float(spec["x"]),
        float(spec["y"]),
        direction=int(spec.get("direction", DIR_EAST)),
        name=str(spec.get("name") or "transport-belt"),
    )
    if spec.get("entity_type"):
        entity["type"] = str(spec["entity_type"])
    return entity


def connector_belt_name_for_port(port: dict[str, Any] | None) -> str:
    if not port:
        return "transport-belt"
    entity_name = str(port.get("entity_name") or "")
    if entity_name.endswith("transport-belt"):
        return entity_name
    if entity_name.endswith("underground-belt"):
        return entity_name.replace("underground-belt", "transport-belt")
    if entity_name.endswith("splitter"):
        return entity_name.replace("splitter", "transport-belt")
    return "transport-belt"


def splitter_name_for_belt_name(belt_name: str) -> str:
    if belt_name == "transport-belt":
        return "splitter"
    if belt_name.endswith("transport-belt"):
        return belt_name.replace("transport-belt", "splitter")
    return "splitter"


def is_belt_like_entity_name(name: str) -> bool:
    return name.endswith("transport-belt") or name.endswith("underground-belt") or name.endswith("splitter")


def is_plain_transport_belt_entity_name(name: str) -> bool:
    return name.endswith("transport-belt")


def canonical_transport_belt_name(name: str) -> str:
    return connector_belt_name_for_port({"entity_name": name})


def rotate_vector(vector: tuple[float, float], direction: int | None) -> tuple[float, float]:
    angle = (int(direction or 0) % 16) * math.pi / 8
    x, y = vector
    return (
        round(x * math.cos(angle) - y * math.sin(angle), 3),
        round(x * math.sin(angle) + y * math.cos(angle), 3),
    )


def entity_position(entity: dict[str, Any]) -> tuple[float, float]:
    position = entity.get("position")
    if isinstance(position, dict):
        return (float(position.get("x", 0.0)), float(position.get("y", 0.0)))
    return (float(entity.get("x", 0.0)), float(entity.get("y", 0.0)))


def entity_collision_box(entity: dict[str, Any], knowledge: PrototypeKnowledge) -> tuple[float, float, float, float] | None:
    box = knowledge.entity_box(str(entity.get("name") or ""))
    if box is None:
        return None
    entity_x, entity_y = entity_position(entity)
    (min_x, min_y), (max_x, max_y) = box.collision_box or box.selection_box
    return (
        round(entity_x + min_x, 3),
        round(entity_y + min_y, 3),
        round(entity_x + max_x, 3),
        round(entity_y + max_y, 3),
    )


def boxes_overlap(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
    *,
    tolerance: float = 0.001,
) -> bool:
    left_min_x, left_min_y, left_max_x, left_max_y = left
    right_min_x, right_min_y, right_max_x, right_max_y = right
    return not (
        left_max_x <= right_min_x + tolerance
        or right_max_x <= left_min_x + tolerance
        or left_max_y <= right_min_y + tolerance
        or right_max_y <= left_min_y + tolerance
    )


def placement_collisions(
    candidate: dict[str, Any],
    entities: list[dict[str, Any]],
    knowledge: PrototypeKnowledge,
    *,
    tolerance: float = 0.001,
) -> list[dict[str, Any]]:
    candidate_box = entity_collision_box(candidate, knowledge)
    if candidate_box is None:
        return []
    collisions: list[dict[str, Any]] = []
    candidate_x, candidate_y = entity_position(candidate)
    for entity in entities:
        entity_box = entity_collision_box(entity, knowledge)
        if entity_box is None:
            continue
        if not boxes_overlap(candidate_box, entity_box, tolerance=tolerance):
            continue
        collisions.append(
            {
                "entity_number": int(entity.get("entity_number") or 0),
                "entity_name": str(entity.get("name") or ""),
                "x": round(candidate_x, 3),
                "y": round(candidate_y, 3),
                "collision_x": round(entity_position(entity)[0], 3),
                "collision_y": round(entity_position(entity)[1], 3),
            }
        )
    return collisions


def point_in_entity_box(
    point: tuple[float, float],
    entity: dict[str, Any],
    knowledge: PrototypeKnowledge,
    *,
    reject_corner_touch: bool = False,
) -> bool:
    box = knowledge.entity_box(str(entity.get("name") or ""))
    if box is None:
        return False
    entity_x, entity_y = entity_position(entity)
    (min_x, min_y), (max_x, max_y) = box.selection_box
    point_x, point_y = point
    tolerance = 0.05
    if not (
        entity_x + min_x - tolerance <= point_x <= entity_x + max_x + tolerance
        and entity_y + min_y - tolerance <= point_y <= entity_y + max_y + tolerance
    ):
        return False
    if reject_corner_touch:
        on_vertical_edge = (
            abs(point_x - (entity_x + min_x)) <= tolerance
            or abs(point_x - (entity_x + max_x)) <= tolerance
        )
        on_horizontal_edge = (
            abs(point_y - (entity_y + min_y)) <= tolerance
            or abs(point_y - (entity_y + max_y)) <= tolerance
        )
        if on_vertical_edge and on_horizontal_edge:
            return False
    return True


def endpoint_targets(
    point: tuple[float, float],
    entities: list[dict[str, Any]],
    *,
    source_entity_number: int,
    knowledge: PrototypeKnowledge,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for entity in entities:
        if int(entity.get("entity_number") or 0) == source_entity_number:
            continue
        name = str(entity.get("name") or "")
        role = None
        if entity.get("recipe") and knowledge.entity(name):
            role = "machine"
        elif is_belt_like_entity_name(name):
            role = "belt"
        if role is None or not point_in_entity_box(point, entity, knowledge, reject_corner_touch=role == "machine"):
            continue
        targets.append(
            {
                "entity_number": int(entity.get("entity_number") or 0),
                "name": name,
                "role": role,
                "recipe": entity.get("recipe"),
                "entity_type": entity.get("type") or entity.get("entity_type"),
                "direction": entity.get("direction"),
                "x": entity_position(entity)[0],
                "y": entity_position(entity)[1],
            }
        )
    return targets


def machine_io_port_hints(
    template_entities: list[dict[str, Any]],
    *,
    target_recipe: str | None,
    knowledge: PrototypeKnowledge | None,
) -> list[dict[str, Any]]:
    if knowledge is None or not target_recipe:
        return []
    local_entities = [dict(entity, entity_number=index + 1) for index, entity in enumerate(template_entities)]
    target_machine_numbers = {
        int(entity["entity_number"])
        for entity in local_entities
        if entity.get("recipe") == target_recipe and knowledge.entity(str(entity.get("name") or "")) is not None
    }
    if not target_machine_numbers:
        return []

    ports_by_key: dict[tuple[str, str, int, float, float], dict[str, Any]] = {}
    for entity in local_entities:
        name = str(entity.get("name") or "")
        inserter = knowledge.inserter(name)
        if inserter is None:
            continue
        number = int(entity.get("entity_number") or 0)
        origin_x, origin_y = entity_position(entity)
        pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, entity.get("direction"))
        insert_dx, insert_dy = rotate_vector(inserter.insert_position, entity.get("direction"))
        pickup_targets = endpoint_targets(
            (round(origin_x + pickup_dx, 3), round(origin_y + pickup_dy, 3)),
            local_entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        insert_targets = endpoint_targets(
            (round(origin_x + insert_dx, 3), round(origin_y + insert_dy, 3)),
            local_entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        insert_machines = [target for target in insert_targets if target["role"] == "machine" and target["entity_number"] in target_machine_numbers]
        pickup_machines = [target for target in pickup_targets if target["role"] == "machine" and target["entity_number"] in target_machine_numbers]
        pickup_belts = [target for target in pickup_targets if target["role"] == "belt"]
        insert_belts = [target for target in insert_targets if target["role"] == "belt"]
        for belt in pickup_belts:
            if not insert_machines:
                continue
            belt_direction = belt.get("direction")
            key = ("left", str(belt["name"]), int(belt_direction) if belt_direction is not None else -1, round(float(belt["x"]), 3), round(float(belt["y"]), 3))
            ports_by_key[key] = {
                "side": "left",
                "role": "machine-input",
                "entity_name": belt["name"],
                "entity_type": belt.get("entity_type"),
                "direction": belt.get("direction"),
                "x": round(float(belt["x"]), 3),
                "y": round(float(belt["y"]), 3),
                "source": "machine-io",
                "inserter_entity_number": number,
                "machine_entity_numbers": sorted(target["entity_number"] for target in insert_machines),
            }
        for belt in insert_belts:
            if not pickup_machines:
                continue
            belt_direction = belt.get("direction")
            key = ("right", str(belt["name"]), int(belt_direction) if belt_direction is not None else -1, round(float(belt["x"]), 3), round(float(belt["y"]), 3))
            ports_by_key[key] = {
                "side": "right",
                "role": "machine-output",
                "entity_name": belt["name"],
                "entity_type": belt.get("entity_type"),
                "direction": belt.get("direction"),
                "x": round(float(belt["x"]), 3),
                "y": round(float(belt["y"]), 3),
                "source": "machine-io",
                "inserter_entity_number": number,
                "machine_entity_numbers": sorted(target["entity_number"] for target in pickup_machines),
            }
    return sorted(ports_by_key.values(), key=lambda port: (port["side"], port["y"], port["x"], port["entity_name"]))


def audit_machine_io(wrapper: dict[str, Any], knowledge: PrototypeKnowledge | None) -> list[dict[str, Any]]:
    if knowledge is None:
        return []
    entities = list((wrapper.get("blueprint") or {}).get("entities") or [])
    if not entities:
        return []

    machine_state: dict[int, dict[str, Any]] = {}
    for entity in entities:
        name = str(entity.get("name") or "")
        if not entity.get("recipe") or knowledge.entity(name) is None:
            continue
        number = int(entity.get("entity_number") or 0)
        recipe_name = str(entity.get("recipe") or "")
        recipe = knowledge.recipe(recipe_name)
        machine_state[number] = {
            "entity_number": number,
            "name": name,
            "recipe": recipe_name,
            "input_inserters": set(),
            "output_inserters": set(),
            "input_required": True if recipe is None else any(item.type == "item" and item.amount > 0 for item in recipe.ingredients),
            "output_required": True if recipe is None else any(item.type == "item" and item.amount > 0 for item in recipe.products),
        }

    unresolved_inserters: list[dict[str, Any]] = []
    for entity in entities:
        name = str(entity.get("name") or "")
        inserter = knowledge.inserter(name)
        if inserter is None:
            continue
        number = int(entity.get("entity_number") or 0)
        origin_x, origin_y = entity_position(entity)
        pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, entity.get("direction"))
        insert_dx, insert_dy = rotate_vector(inserter.insert_position, entity.get("direction"))
        pickup_targets = endpoint_targets(
            (round(origin_x + pickup_dx, 3), round(origin_y + pickup_dy, 3)),
            entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        insert_targets = endpoint_targets(
            (round(origin_x + insert_dx, 3), round(origin_y + insert_dy, 3)),
            entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        pickup_machines = [target for target in pickup_targets if target["role"] == "machine" and target["entity_number"] in machine_state]
        insert_machines = [target for target in insert_targets if target["role"] == "machine" and target["entity_number"] in machine_state]
        pickup_belts = [target for target in pickup_targets if target["role"] == "belt"]
        insert_belts = [target for target in insert_targets if target["role"] == "belt"]
        for machine in insert_machines:
            if pickup_belts:
                machine_state[machine["entity_number"]]["input_inserters"].add(number)
        for machine in pickup_machines:
            if insert_belts:
                machine_state[machine["entity_number"]]["output_inserters"].add(number)
        if not ((pickup_machines and insert_belts) or (pickup_belts and insert_machines)):
            unresolved_inserters.append(
                {
                    "entity_number": number,
                    "name": name,
                    "pickup_targets": pickup_targets,
                    "insert_targets": insert_targets,
                }
            )

    grouped: dict[str, list[dict[str, Any]]] = {}
    for state in machine_state.values():
        grouped.setdefault(str(state["recipe"]), []).append(state)

    audit: list[dict[str, Any]] = []
    for recipe, machines in sorted(grouped.items()):
        input_required = any(bool(machine["input_required"]) for machine in machines)
        output_required = any(bool(machine["output_required"]) for machine in machines)
        machines_with_input = sum(1 for machine in machines if machine["input_inserters"])
        machines_with_output = sum(1 for machine in machines if machine["output_inserters"])
        input_covered = not input_required or machines_with_input == len(machines)
        output_covered = not output_required or machines_with_output == len(machines)
        audit.append(
            {
                "recipe": recipe,
                "status": "covered" if input_covered and output_covered else "partial",
                "machine_count": len(machines),
                "input_required": input_required,
                "output_required": output_required,
                "machines_with_input": machines_with_input,
                "machines_with_output": machines_with_output,
                "input_inserter_count": sum(len(machine["input_inserters"]) for machine in machines),
                "output_inserter_count": sum(len(machine["output_inserters"]) for machine in machines),
            }
        )
    if unresolved_inserters:
        audit.append(
            {
                "recipe": "__unresolved_inserters__",
                "status": "unresolved",
                "machine_count": 0,
                "unresolved_inserter_count": len(unresolved_inserters),
                "samples": unresolved_inserters[:8],
            }
        )
    return audit


def nearest_half_tile(value: float) -> float:
    return round(round(value * 2.0) / 2.0, 3)


def audit_machine_output_expansion(
    wrapper: dict[str, Any],
    knowledge: PrototypeKnowledge | None,
    *,
    inserter_name: str = "stack-inserter",
) -> list[dict[str, Any]]:
    per_machine = machine_output_expansion_candidates(wrapper, knowledge, inserter_name=inserter_name)
    grouped: dict[str, dict[str, Any]] = {}
    for machine in per_machine:
        recipe = str(machine.get("recipe") or "")
        recipe_item = grouped.setdefault(
            recipe,
            {
                "recipe": recipe,
                "machine_count": 0,
                "machines_with_existing_output": 0,
                "existing_output_inserter_count": 0,
                "expandable_machine_count": 0,
                "candidate_count": 0,
                "blocked_candidate_count": 0,
                "invalid_endpoint_count": 0,
                "samples": [],
                "blocked_samples": [],
            },
        )
        recipe_item["machine_count"] += 1
        recipe_item["machines_with_existing_output"] += 1 if machine.get("existing_output_inserter_count") else 0
        recipe_item["existing_output_inserter_count"] += int(machine.get("existing_output_inserter_count") or 0)
        recipe_item["candidate_count"] += len(machine.get("candidates") or [])
        recipe_item["blocked_candidate_count"] += len(machine.get("blocked_candidates") or [])
        recipe_item["invalid_endpoint_count"] += int(machine.get("invalid_endpoint_count") or 0)
        candidates = machine.get("candidates") or []
        blocked = machine.get("blocked_candidates") or []
        if candidates:
            recipe_item["expandable_machine_count"] += 1
            recipe_item["samples"].extend(candidates[: max(0, 8 - len(recipe_item["samples"]))])
        if blocked:
            recipe_item["blocked_samples"].extend(blocked[: max(0, 8 - len(recipe_item["blocked_samples"]))])

    audits = list(grouped.values())
    for item in audits:
        item["status"] = "expandable" if item["expandable_machine_count"] else "blocked"
    return sorted(audits, key=lambda item: item["recipe"])


def machine_output_expansion_candidates(
    wrapper: dict[str, Any],
    knowledge: PrototypeKnowledge | None,
    *,
    inserter_name: str = "stack-inserter",
) -> list[dict[str, Any]]:
    if knowledge is None or knowledge.inserter(inserter_name) is None:
        return []
    entities = list((wrapper.get("blueprint") or {}).get("entities") or [])
    if not entities:
        return []

    machine_entities = [
        entity
        for entity in entities
        if entity.get("recipe") and knowledge.entity(str(entity.get("name") or "")) is not None
    ]
    if not machine_entities:
        return []

    existing_output_by_machine: dict[int, set[int]] = {int(entity.get("entity_number") or 0): set() for entity in machine_entities}
    machine_numbers = set(existing_output_by_machine)
    for entity in entities:
        inserter = knowledge.inserter(str(entity.get("name") or ""))
        if inserter is None:
            continue
        number = int(entity.get("entity_number") or 0)
        origin_x, origin_y = entity_position(entity)
        pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, entity.get("direction"))
        insert_dx, insert_dy = rotate_vector(inserter.insert_position, entity.get("direction"))
        pickup_targets = endpoint_targets(
            (round(origin_x + pickup_dx, 3), round(origin_y + pickup_dy, 3)),
            entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        insert_targets = endpoint_targets(
            (round(origin_x + insert_dx, 3), round(origin_y + insert_dy, 3)),
            entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        pickup_machines = [target for target in pickup_targets if target["role"] == "machine" and target["entity_number"] in machine_numbers]
        pickup_belts = [target for target in pickup_targets if target["role"] == "belt"]
        insert_belts = [target for target in insert_targets if target["role"] == "belt"]
        if not insert_belts or pickup_belts:
            continue
        for machine in pickup_machines:
            existing_output_by_machine[int(machine["entity_number"])].add(number)

    inserter = knowledge.inserter(inserter_name)
    assert inserter is not None
    candidate_offsets = [offset / 2.0 for offset in range(-6, 7)]
    per_machine: list[dict[str, Any]] = []
    for machine in machine_entities:
        machine_number = int(machine.get("entity_number") or 0)
        machine_x, machine_y = entity_position(machine)
        recipe = str(machine.get("recipe") or "")
        existing_outputs = existing_output_by_machine.get(machine_number, set())
        candidates: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        invalid_endpoint_count = 0
        for direction in (DIR_NORTH, DIR_EAST, DIR_SOUTH, DIR_WEST):
            pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, direction)
            insert_dx, insert_dy = rotate_vector(inserter.insert_position, direction)
            for offset_x in candidate_offsets:
                for offset_y in candidate_offsets:
                    candidate_x = round(machine_x + offset_x, 3)
                    candidate_y = round(machine_y + offset_y, 3)
                    candidate_inserter = {
                        "entity_number": -1,
                        "name": inserter_name,
                        "position": {"x": candidate_x, "y": candidate_y},
                        "direction": direction,
                    }
                    inserter_collisions = placement_collisions(candidate_inserter, entities, knowledge)
                    pickup_point = (round(candidate_x + pickup_dx, 3), round(candidate_y + pickup_dy, 3))
                    insert_point = (round(candidate_x + insert_dx, 3), round(candidate_y + insert_dy, 3))
                    pickup_targets = endpoint_targets(
                        pickup_point,
                        entities,
                        source_entity_number=-1,
                        knowledge=knowledge,
                    )
                    pickup_machines = [
                        target
                        for target in pickup_targets
                        if target["role"] == "machine" and target["entity_number"] == machine_number
                    ]
                    pickup_belts = [target for target in pickup_targets if target["role"] == "belt"]
                    if not pickup_machines or pickup_belts:
                        invalid_endpoint_count += 1
                        continue
                    insert_targets = endpoint_targets(
                        insert_point,
                        entities,
                        source_entity_number=-1,
                        knowledge=knowledge,
                    )
                    insert_belts = [target for target in insert_targets if target["role"] == "belt"]
                    if insert_belts:
                        if (
                            round(float(insert_belts[0]["y"]), 3) > round(machine_y, 3)
                            or round(float(insert_belts[0]["x"]), 3) < round(machine_x, 3)
                        ):
                            invalid_endpoint_count += 1
                            continue
                        if inserter_collisions:
                            blocked.append(
                                {
                                    "machine_entity_number": machine_number,
                                    "candidate_x": candidate_x,
                                    "candidate_y": candidate_y,
                                    "direction": direction,
                                    "drop": "existing-belt",
                                    "collisions": inserter_collisions[:3],
                                }
                            )
                            continue
                        candidates.append(
                            {
                                "machine_entity_number": machine_number,
                                "candidate_x": candidate_x,
                                "candidate_y": candidate_y,
                                "direction": direction,
                                "drop": "existing-belt",
                                "drop_x": round(float(insert_belts[0]["x"]), 3),
                                "drop_y": round(float(insert_belts[0]["y"]), 3),
                                "drop_belt_name": insert_belts[0]["name"],
                            }
                        )
                        continue

                    belt_x = nearest_half_tile(insert_point[0])
                    belt_y = nearest_half_tile(insert_point[1])
                    if belt_y > round(machine_y, 3) or belt_x < round(machine_x, 3):
                        invalid_endpoint_count += 1
                        continue
                    belt_name = "transport-belt"
                    existing_belt_names = [
                        str(entity.get("name") or "")
                        for entity in entities
                        if is_belt_like_entity_name(str(entity.get("name") or ""))
                    ]
                    if "turbo-transport-belt" in existing_belt_names:
                        belt_name = "turbo-transport-belt"
                    proposed_belt = connector_belt(-2, belt_x, belt_y, direction=DIR_EAST, name=belt_name)
                    if not point_in_entity_box(insert_point, proposed_belt, knowledge):
                        invalid_endpoint_count += 1
                        continue
                    belt_collisions = placement_collisions(proposed_belt, entities, knowledge)
                    if inserter_collisions or belt_collisions:
                        blocked.append(
                            {
                                "machine_entity_number": machine_number,
                                "candidate_x": candidate_x,
                                "candidate_y": candidate_y,
                                "direction": direction,
                                "drop": "new-belt",
                                "drop_x": belt_x,
                                "drop_y": belt_y,
                                "collisions": (inserter_collisions + belt_collisions)[:3],
                            }
                        )
                        continue
                    candidates.append(
                        {
                            "machine_entity_number": machine_number,
                            "candidate_x": candidate_x,
                            "candidate_y": candidate_y,
                            "direction": direction,
                            "drop": "new-belt",
                            "drop_x": belt_x,
                            "drop_y": belt_y,
                            "drop_belt_name": belt_name,
                        }
                    )

        per_machine.append(
            {
                "recipe": recipe,
                "machine_entity_number": machine_number,
                "machine_x": round(machine_x, 3),
                "machine_y": round(machine_y, 3),
                "existing_output_inserter_count": len(existing_outputs),
                "candidates": candidates,
                "blocked_candidates": blocked,
                "invalid_endpoint_count": invalid_endpoint_count,
            }
        )
    return per_machine


def materialize_machine_output_expansions(
    entities: list[dict[str, Any]],
    knowledge: PrototypeKnowledge | None,
    *,
    inserter_name: str = "stack-inserter",
    max_per_machine: int = 4,
    allow_new_drop_belts: bool = False,
    target_item: str | None = None,
) -> dict[str, Any]:
    if knowledge is None or max_per_machine <= 0:
        return {
            "enabled": False,
            "inserters_added": 0,
            "drop_belts_added": 0,
            "machines_expanded": 0,
            "skipped_new_drop_belt_candidates": 0,
            "blocked_candidate_count": 0,
            "selected": [],
            "blocked": [],
        }

    wrapper = {"blueprint": {"entities": entities}}
    per_machine = machine_output_expansion_candidates(wrapper, knowledge, inserter_name=inserter_name)
    selected: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    skipped_new_drop_belt_candidates = 0
    inserters_added = 0
    drop_belts_added = 0

    def candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, float, float, float]:
        drop_priority = 0 if candidate.get("drop") == "existing-belt" else 1
        return (
            drop_priority,
            float(candidate.get("drop_y") or 0.0),
            -float(candidate.get("drop_x") or 0.0),
            float(candidate.get("candidate_x") or 0.0),
        )

    def next_entity_number() -> int:
        return max((int(entity.get("entity_number") or 0) for entity in entities), default=0) + 1

    for machine in per_machine:
        added_for_machine = 0
        for candidate in sorted(machine.get("candidates") or [], key=candidate_sort_key):
            if added_for_machine >= max_per_machine:
                break
            if candidate.get("drop") == "new-belt" and not allow_new_drop_belts:
                skipped_new_drop_belt_candidates += 1
                continue

            candidate_inserter = {
                "entity_number": next_entity_number(),
                "name": inserter_name,
                "position": {
                    "x": round(float(candidate["candidate_x"]), 3),
                    "y": round(float(candidate["candidate_y"]), 3),
                },
                "direction": int(candidate["direction"]),
            }
            if target_item:
                candidate_inserter["filters"] = [
                    {
                        "index": 1,
                        "name": target_item,
                        "quality": "normal",
                        "comparator": "=",
                    }
                ]
                candidate_inserter["use_filters"] = True
            proposed_entities = [candidate_inserter]
            if candidate.get("drop") == "new-belt":
                proposed_entities.append(
                    connector_belt(
                        candidate_inserter["entity_number"] + 1,
                        float(candidate["drop_x"]),
                        float(candidate["drop_y"]),
                        direction=DIR_EAST,
                        name=str(candidate.get("drop_belt_name") or "transport-belt"),
                    )
                )

            candidate_collisions: list[dict[str, Any]] = []
            for proposed in proposed_entities:
                candidate_collisions.extend(placement_collisions(proposed, entities, knowledge))
            if candidate_collisions:
                blocked.append(
                    {
                        "recipe": machine.get("recipe"),
                        "machine_entity_number": machine.get("machine_entity_number"),
                        "candidate": candidate,
                        "collisions": candidate_collisions[:3],
                    }
                )
                continue

            for proposed in proposed_entities:
                proposed["entity_number"] = next_entity_number()
                entities.append(proposed)
                if proposed["name"] == inserter_name:
                    inserters_added += 1
                elif is_belt_like_entity_name(str(proposed.get("name") or "")):
                    drop_belts_added += 1
            selected.append(
                {
                    "recipe": machine.get("recipe"),
                    "machine_entity_number": machine.get("machine_entity_number"),
                    "inserter_name": inserter_name,
                    "inserter_x": candidate_inserter["position"]["x"],
                    "inserter_y": candidate_inserter["position"]["y"],
                    "direction": candidate_inserter["direction"],
                    "drop": candidate.get("drop"),
                    "drop_x": candidate.get("drop_x"),
                    "drop_y": candidate.get("drop_y"),
                    "drop_belt_name": candidate.get("drop_belt_name"),
                }
            )
            added_for_machine += 1

    return {
        "enabled": True,
        "inserters_added": inserters_added,
        "drop_belts_added": drop_belts_added,
        "machines_expanded": len({item["machine_entity_number"] for item in selected}),
        "skipped_new_drop_belt_candidates": skipped_new_drop_belt_candidates,
        "blocked_candidate_count": len(blocked),
        "selected": selected,
        "blocked": blocked,
        "strategy": "prefer-existing-drop-belt",
        "allow_new_drop_belts": allow_new_drop_belts,
        "target_item_filter": target_item,
    }


def prune_template_entities_for_recipe(
    template_entities: list[dict[str, Any]],
    *,
    target_recipe: str | None,
    knowledge: PrototypeKnowledge | None,
    layout_ports: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if knowledge is None or not target_recipe:
        return template_entities

    local_entities = [dict(entity, entity_number=index + 1) for index, entity in enumerate(template_entities)]
    target_machine_numbers = {
        int(entity["entity_number"])
        for entity in local_entities
        if entity.get("recipe") == target_recipe and knowledge.entity(str(entity.get("name") or "")) is not None
    }
    if not target_machine_numbers:
        return template_entities

    belt_entities: dict[int, dict[str, Any]] = {
        int(entity["entity_number"]): entity
        for entity in local_entities
        if is_belt_like_entity_name(str(entity.get("name") or ""))
    }
    belt_positions: dict[tuple[float, float], list[int]] = {}
    for number, entity in belt_entities.items():
        x, y = entity_position(entity)
        belt_positions.setdefault((round(x, 3), round(y, 3)), []).append(number)

    selected_inserters: set[int] = set()
    selected_belts: set[int] = set()
    for entity in local_entities:
        name = str(entity.get("name") or "")
        inserter = knowledge.inserter(name)
        if inserter is None:
            continue
        number = int(entity["entity_number"])
        origin_x, origin_y = entity_position(entity)
        pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, entity.get("direction"))
        insert_dx, insert_dy = rotate_vector(inserter.insert_position, entity.get("direction"))
        pickup_targets = endpoint_targets(
            (round(origin_x + pickup_dx, 3), round(origin_y + pickup_dy, 3)),
            local_entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        insert_targets = endpoint_targets(
            (round(origin_x + insert_dx, 3), round(origin_y + insert_dy, 3)),
            local_entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        pickup_target_machine = any(target["role"] == "machine" and target["entity_number"] in target_machine_numbers for target in pickup_targets)
        insert_target_machine = any(target["role"] == "machine" and target["entity_number"] in target_machine_numbers for target in insert_targets)
        pickup_belt = any(target["role"] == "belt" for target in pickup_targets)
        insert_belt = any(target["role"] == "belt" for target in insert_targets)
        if (pickup_belt and insert_target_machine) or (pickup_target_machine and insert_belt):
            selected_inserters.add(number)
            selected_belts.update(target["entity_number"] for target in pickup_targets if target["role"] == "belt")
            selected_belts.update(target["entity_number"] for target in insert_targets if target["role"] == "belt")

    for port in layout_ports or []:
        if not is_belt_like_entity_name(str(port.get("entity_name") or "")):
            continue
        port_key = (round(float(port.get("x") or 0.0), 3), round(float(port.get("y") or 0.0), 3))
        port_belt_name = canonical_transport_belt_name(str(port.get("entity_name") or ""))
        port_entity_type = port.get("entity_type")
        for number in belt_positions.get(port_key, []):
            entity = belt_entities[number]
            if canonical_transport_belt_name(str(entity.get("name") or "")) != port_belt_name:
                continue
            if port_entity_type and (entity.get("type") or entity.get("entity_type")) != port_entity_type:
                continue
            selected_belts.add(number)

    preserved_belt_lanes = {
        (
            round(entity_position(entity)[1], 3),
            canonical_transport_belt_name(str(entity.get("name") or "")),
        )
        for number, entity in belt_entities.items()
        if number in selected_belts
    }

    pruned: list[dict[str, Any]] = []
    for entity in local_entities:
        number = int(entity["entity_number"])
        name = str(entity.get("name") or "")
        if entity.get("recipe"):
            if entity.get("recipe") == target_recipe:
                pruned.append({key: value for key, value in entity.items() if key != "entity_number"})
            continue
        if knowledge.inserter(name) is not None:
            if number in selected_inserters:
                pruned.append({key: value for key, value in entity.items() if key != "entity_number"})
            continue
        if is_belt_like_entity_name(name):
            lane = (round(entity_position(entity)[1], 3), canonical_transport_belt_name(name))
            if number in selected_belts or lane in preserved_belt_lanes:
                pruned.append({key: value for key, value in entity.items() if key != "entity_number"})
            continue
        pruned.append({key: value for key, value in entity.items() if key != "entity_number"})
    return pruned


def upgraded_output_inserter_name(name: str, knowledge: PrototypeKnowledge) -> str | None:
    current = knowledge.inserter(name)
    if current is None:
        return None
    if name in {"bulk-inserter", "stack-inserter"}:
        return None
    for candidate_name in ("stack-inserter", "bulk-inserter"):
        candidate = knowledge.inserter(candidate_name)
        if candidate is None:
            continue
        if candidate.pickup_position == current.pickup_position and candidate.insert_position == current.insert_position:
            return candidate_name
    return None


def upgrade_output_inserters_for_recipe(
    template_entities: list[dict[str, Any]],
    *,
    target_recipe: str | None,
    knowledge: PrototypeKnowledge | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if knowledge is None or not target_recipe:
        return template_entities, []
    local_entities = [dict(entity, entity_number=index + 1) for index, entity in enumerate(template_entities)]
    target_machine_numbers = {
        int(entity["entity_number"])
        for entity in local_entities
        if entity.get("recipe") == target_recipe and knowledge.entity(str(entity.get("name") or "")) is not None
    }
    if not target_machine_numbers:
        return template_entities, []

    upgrade_by_number: dict[int, str] = {}
    for entity in local_entities:
        name = str(entity.get("name") or "")
        inserter = knowledge.inserter(name)
        if inserter is None:
            continue
        number = int(entity["entity_number"])
        origin_x, origin_y = entity_position(entity)
        pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, entity.get("direction"))
        insert_dx, insert_dy = rotate_vector(inserter.insert_position, entity.get("direction"))
        pickup_targets = endpoint_targets(
            (round(origin_x + pickup_dx, 3), round(origin_y + pickup_dy, 3)),
            local_entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        insert_targets = endpoint_targets(
            (round(origin_x + insert_dx, 3), round(origin_y + insert_dy, 3)),
            local_entities,
            source_entity_number=number,
            knowledge=knowledge,
        )
        pickup_target_machine = any(target["role"] == "machine" and target["entity_number"] in target_machine_numbers for target in pickup_targets)
        insert_belt = any(target["role"] == "belt" for target in insert_targets)
        if not (pickup_target_machine and insert_belt):
            continue
        upgraded_name = upgraded_output_inserter_name(name, knowledge)
        if upgraded_name is not None:
            upgrade_by_number[number] = upgraded_name

    if not upgrade_by_number:
        return template_entities, []

    upgraded_entities: list[dict[str, Any]] = []
    upgrade_counts: Counter[tuple[str, str]] = Counter()
    for entity in local_entities:
        number = int(entity["entity_number"])
        clean_entity = {key: value for key, value in entity.items() if key != "entity_number"}
        upgraded_name = upgrade_by_number.get(number)
        if upgraded_name is not None:
            old_name = str(clean_entity.get("name") or "")
            clean_entity["name"] = upgraded_name
            upgrade_counts[(old_name, upgraded_name)] += 1
        upgraded_entities.append(clean_entity)

    return upgraded_entities, [
        {"from": source, "to": target, "template_count": count}
        for (source, target), count in sorted(upgrade_counts.items())
    ]


def materialized_tile(raw: dict[str, Any], *, x: float, y: float) -> dict[str, Any]:
    return {
        "name": raw["name"],
        "position": {
            "x": round(x + float(raw["x"]), 3),
            "y": round(y + float(raw["y"]), 3),
        },
    }


def entity_foundation_tile_key(entity: dict[str, Any]) -> tuple[float, float]:
    x, y = entity_position(entity)
    return (float(math.floor(x)), float(math.floor(y)))


def add_boundary_connectors(
    entities: list[dict[str, Any]],
    layout_plan: dict[str, Any],
    *,
    occupied: set[tuple[float, float]],
    occupied_entities: dict[tuple[float, float], dict[str, Any]],
    knowledge: PrototypeKnowledge | None = None,
    output_separation_min_distance: float = 1.0,
    compress_output_boundary: bool = False,
    preseparate_output_before_fanin: bool = False,
    experimental_prefanin_input_sideload: bool = False,
) -> dict[str, Any]:
    connectors: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    bridges: list[dict[str, Any]] = []
    input_fanouts: list[dict[str, Any]] = []
    output_fanins: list[dict[str, Any]] = []
    output_boundary_compressors: list[dict[str, Any]] = []
    if not layout_plan.get("nodes"):
        return {
            "connectors_added": 0,
            "bridges_added": 0,
            "input_fanouts_added": 0,
            "output_fanins_added": 0,
            "output_separation_splitters": 0,
            "output_separation_overflow_belts": 0,
            "output_separation_recycle_belts": 0,
            "output_separation_merge_belts": 0,
            "collisions": collisions,
            "routes": routes,
            "bridges": bridges,
            "input_fanouts": input_fanouts,
            "output_fanins": output_fanins,
            "output_separations": [],
            "output_boundary_compressors": [],
            "boundary_coverage": [],
            "boundary_capacity_audit": [],
            "boundary_contract_audit": [],
            "output_preseparation_exposure_audit": [],
            "output_lane_load_audit": [],
            "output_byproduct_audit": [],
            "belt_flow_audit": [],
            "output_inserter_upgrades": [],
            "machine_output_expansions": {},
        }

    root = layout_plan["nodes"][0]
    default_y = round(float(root["y"]) + float(root["source_height"]) / 2, 3)

    def machine_output_pickup_blockers() -> set[tuple[float, float]]:
        if knowledge is None:
            return set()
        blockers: set[tuple[float, float]] = set()
        for entity in entities:
            name = str(entity.get("name") or "")
            inserter = knowledge.inserter(name)
            if inserter is None:
                continue
            number = int(entity.get("entity_number") or 0)
            origin_x, origin_y = entity_position(entity)
            pickup_dx, pickup_dy = rotate_vector(inserter.pickup_position, entity.get("direction"))
            insert_dx, insert_dy = rotate_vector(inserter.insert_position, entity.get("direction"))
            pickup_point = (round(origin_x + pickup_dx, 3), round(origin_y + pickup_dy, 3))
            insert_point = (round(origin_x + insert_dx, 3), round(origin_y + insert_dy, 3))
            pickup_targets = endpoint_targets(
                pickup_point,
                entities,
                source_entity_number=number,
                knowledge=knowledge,
            )
            insert_targets = endpoint_targets(
                insert_point,
                entities,
                source_entity_number=number,
                knowledge=knowledge,
            )
            pickup_machines = [target for target in pickup_targets if target["role"] == "machine"]
            insert_belts = [target for target in insert_targets if target["role"] == "belt"]
            if pickup_machines and insert_belts:
                blockers.add(pickup_point)
        return blockers

    output_pickup_blockers = machine_output_pickup_blockers()

    def connector_placement_collisions(
        candidate: dict[str, Any],
        reason: str,
        proposed_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if knowledge is None:
            return []
        candidate_box = knowledge.entity_box(str(candidate.get("name") or ""))
        if candidate_box is None or candidate_box.collision_box is None:
            return []
        route_collisions: list[dict[str, Any]] = []
        comparable_entities = [
            entity
            for entity in [*entities, *connectors, *proposed_entities]
            if (box := knowledge.entity_box(str(entity.get("name") or ""))) is not None and box.collision_box is not None
        ]
        for collision in placement_collisions(candidate, comparable_entities, knowledge, tolerance=0.0):
            route_collisions.append(
                {
                    "x": round(entity_position(candidate)[0], 3),
                    "y": round(entity_position(candidate)[1], 3),
                    "reason": f"{reason}:placement-collision",
                    "entity_name": collision.get("entity_name"),
                    "collision_x": collision.get("collision_x"),
                    "collision_y": collision.get("collision_y"),
                }
            )
        return route_collisions

    def add_positions(
        positions: list[RoutePosition],
        *,
        record_collisions: bool = True,
    ) -> tuple[int, list[dict[str, Any]]]:
        positions = visible_route_positions(positions)
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        proposed_entities: list[dict[str, Any]] = []
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            is_fanin_source_route = reason.startswith("fanin-source:")
            is_fanin_route = reason.startswith("fanin:") or is_fanin_source_route
            if is_fanin_route and key in output_pickup_blockers:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:machine-output-pickup-position"}
                route_collisions.append(collision)
                continue
            if key in seen:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"}
                route_collisions.append(collision)
                continue
            seen.add(key)
            if key in occupied:
                collision = {"x": key[0], "y": key[1], "reason": reason}
                route_collisions.append(collision)
                continue
            candidate = connector_belt(-1, x, belt_y, direction=direction, name=belt_name)
            placement = connector_placement_collisions(candidate, reason, proposed_entities)
            if placement:
                route_collisions.extend(placement)
                continue
            proposed_entities.append(candidate)
        if route_collisions:
            if record_collisions:
                collisions.extend(route_collisions)
            return 0, route_collisions

        before = len(connectors)
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            belt = connector_belt(
                len(entities) + len(connectors) + 1,
                x,
                belt_y,
                direction=direction,
                name=belt_name,
            )
            connectors.append(belt)
            occupied.add(key)
            occupied_entities[key] = belt
        return len(connectors) - before, route_collisions

    def add_positions_reusing_existing_belts(
        positions: list[RoutePosition],
        *,
        record_collisions: bool = True,
        reuse_existing_plain_belts_only: bool = False,
    ) -> tuple[int, list[dict[str, Any]], int]:
        positions = visible_route_positions(positions)
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        existing_belts_used = 0
        proposed_entities: list[dict[str, Any]] = []
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            is_fanin_source_route = reason.startswith("fanin-source:")
            is_fanin_route = reason.startswith("fanin:") or is_fanin_source_route
            if is_fanin_route and key in output_pickup_blockers:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:machine-output-pickup-position"}
                route_collisions.append(collision)
                continue
            if key in seen:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"}
                route_collisions.append(collision)
                continue
            seen.add(key)
            existing = occupied_entities.get(key)
            if existing is None:
                candidate = connector_belt(-1, x, belt_y, direction=direction, name=belt_name)
                placement = connector_placement_collisions(candidate, reason, proposed_entities)
                if placement:
                    route_collisions.extend(placement)
                    continue
                proposed_entities.append(candidate)
                continue
            existing_name = str(existing.get("name") or "")
            if reuse_existing_plain_belts_only:
                if (
                    is_plain_transport_belt_entity_name(existing_name)
                    and existing_name == belt_name
                    and existing.get("direction") == direction
                ):
                    existing_belts_used += 1
                    continue
                collision = {
                    "x": key[0],
                    "y": key[1],
                    "reason": f"{reason}:existing-belt-not-reusable",
                    "entity_name": existing_name,
                    "direction": existing.get("direction"),
                    "expected_direction": direction,
                }
                route_collisions.append(collision)
                continue
            if is_belt_like_entity_name(existing_name) and canonical_transport_belt_name(existing_name) == belt_name:
                existing_is_connector = any(existing is connector for connector in connectors)
                is_machine_feed_route = (
                    reason.endswith("machine-output-side-load")
                    or reason.endswith("machine-input-right-feed")
                )
                is_plain_transport_belt = canonical_transport_belt_name(existing_name) == existing_name
                if (is_fanin_route or is_machine_feed_route) and existing.get("direction") != direction:
                    if (
                        existing_is_connector
                        or not is_plain_transport_belt
                        or (is_fanin_route and not is_fanin_source_route and existing.get("direction") is not None)
                    ):
                        collision = {"x": key[0], "y": key[1], "reason": f"{reason}:connector-direction-conflict"}
                        route_collisions.append(collision)
                        continue
                    existing["direction"] = direction
                existing_belts_used += 1
                continue
            collision = {"x": key[0], "y": key[1], "reason": reason}
            route_collisions.append(collision)
        if route_collisions:
            if record_collisions:
                collisions.extend(route_collisions)
            return 0, route_collisions, existing_belts_used

        before = len(connectors)
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            if key in occupied_entities:
                continue
            belt = connector_belt(
                len(entities) + len(connectors) + 1,
                x,
                belt_y,
                direction=direction,
                name=belt_name,
            )
            connectors.append(belt)
            occupied.add(key)
            occupied_entities[key] = belt
        return len(connectors) - before, route_collisions, existing_belts_used

    def add_entity_specs_reusing_existing_belts(
        specs: list[RouteEntitySpec],
        *,
        record_collisions: bool = True,
        reuse_existing_plain_belts_only: bool = False,
    ) -> tuple[int, list[dict[str, Any]], int]:
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        existing_belts_used = 0
        proposed_entities: list[dict[str, Any]] = []
        for spec in specs:
            key = (round(float(spec["x"]), 3), round(float(spec["y"]), 3))
            reason = str(spec.get("reason") or "connector")
            name = str(spec.get("name") or "transport-belt")
            direction = int(spec.get("direction", DIR_EAST))
            entity_type = spec.get("entity_type")
            if key in seen:
                route_collisions.append({"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"})
                continue
            seen.add(key)
            existing = occupied_entities.get(key)
            if existing is None:
                candidate = connector_belt_from_spec(-1, spec)
                placement = connector_placement_collisions(candidate, reason, proposed_entities)
                if placement:
                    route_collisions.extend(placement)
                    continue
                proposed_entities.append(candidate)
                continue
            existing_name = str(existing.get("name") or "")
            if reuse_existing_plain_belts_only and not entity_type:
                if is_plain_transport_belt_entity_name(existing_name) and existing_name == name and existing.get("direction") == direction:
                    existing_belts_used += 1
                    continue
                route_collisions.append(
                    {
                        "x": key[0],
                        "y": key[1],
                        "reason": f"{reason}:existing-belt-not-reusable",
                        "entity_name": existing_name,
                        "direction": existing.get("direction"),
                        "expected_direction": direction,
                    }
                )
                continue
            route_collisions.append({"x": key[0], "y": key[1], "reason": reason, "entity_name": existing_name})
        if route_collisions:
            if record_collisions:
                collisions.extend(route_collisions)
            return 0, route_collisions, existing_belts_used

        before = len(connectors)
        for spec in specs:
            key = (round(float(spec["x"]), 3), round(float(spec["y"]), 3))
            if key in occupied_entities:
                continue
            entity = connector_belt_from_spec(len(entities) + len(connectors) + 1, spec)
            connectors.append(entity)
            occupied.add(key)
            occupied_entities[key] = entity
        return len(connectors) - before, route_collisions, existing_belts_used

    def horizontal_positions(start_x: float, end_x: float, y: float, reason: str, belt_name: str) -> list[RoutePosition]:
        positions: list[RoutePosition] = []
        x = start_x
        while x <= end_x:
            positions.append((round(x, 3), y, reason, DIR_EAST, belt_name))
            x += 1.0
        return positions

    def directional_horizontal_positions(
        start_x: float,
        end_x: float,
        y: float,
        reason: str,
        direction: int,
        belt_name: str,
    ) -> list[RoutePosition]:
        positions: list[RoutePosition] = []
        step = 1.0 if start_x <= end_x else -1.0
        x = start_x
        while (step > 0 and x <= end_x) or (step < 0 and x >= end_x):
            positions.append((round(x, 3), round(y, 3), reason, direction, belt_name))
            x += step
        return positions

    def vertical_positions(x: float, start_y: float, end_y: float, reason: str, direction: int, belt_name: str) -> list[RoutePosition]:
        positions: list[RoutePosition] = []
        step = 1.0 if start_y <= end_y else -1.0
        y = start_y
        while (step > 0 and y <= end_y) or (step < 0 and y >= end_y):
            positions.append((round(x, 3), round(y, 3), reason, direction, belt_name))
            y += step
        return positions

    def visible_route_positions(positions: list[RoutePosition]) -> list[RoutePosition]:
        visible: list[RoutePosition] = []
        index = 0
        def underground_pair_within_distance(entity_name: str, input_x: float, output_x: float) -> bool:
            if knowledge is None:
                return True
            belt = knowledge.belt(entity_name)
            if belt is None or belt.max_underground_distance is None:
                return True
            return abs(output_x - input_x) <= belt.max_underground_distance + 1

        while index < len(positions):
            position = positions[index]
            x, belt_y, _reason, direction, belt_name = position
            visible.append(position)
            entity = occupied_entities.get((round(x, 3), round(belt_y, 3)))
            if (
                entity is not None
                and str(entity.get("name") or "").endswith("underground-belt")
                and entity.get("type") == "input"
                and entity.get("direction") == direction
                and canonical_transport_belt_name(str(entity.get("name") or "")) == belt_name
            ):
                for pair_index in range(index + 1, len(positions)):
                    pair_x, pair_y, _pair_reason, pair_direction, _pair_belt_name = positions[pair_index]
                    pair_entity = occupied_entities.get((round(pair_x, 3), round(pair_y, 3)))
                    if pair_entity is None:
                        continue
                    if str(pair_entity.get("name") or "") != str(entity.get("name") or ""):
                        continue
                    if pair_entity.get("type") != "output" or pair_entity.get("direction") != pair_direction:
                        continue
                    if canonical_transport_belt_name(str(pair_entity.get("name") or "")) != belt_name:
                        continue
                    if not underground_pair_within_distance(str(entity.get("name") or ""), float(x), float(pair_x)):
                        continue
                    index = pair_index
                    break
            index += 1
        return visible

    def route_candidate(
        *,
        start_x: float,
        end_x: float,
        y: float,
        reason: str,
        belt_name: str,
    ) -> tuple[str, list[RoutePosition]]:
        return "direct", horizontal_positions(start_x, end_x, y, reason, belt_name)

    def add_first_clear_route(
        candidates: list[tuple[dict[str, Any], str, list[RoutePosition]]],
    ) -> tuple[int, list[dict[str, Any]], dict[str, Any] | None, str | None, list[dict[str, Any]], list[RoutePosition]]:
        blocked_attempts: list[dict[str, Any]] = []
        for port, route_kind, positions in candidates:
            belts_added, route_collisions, _existing_belts_used = add_positions_reusing_existing_belts(positions, record_collisions=False)
            if not route_collisions:
                return belts_added, route_collisions, port, route_kind, blocked_attempts, positions
            blocked_attempts.append(
                {
                    "port": port,
                    "route_kind": route_kind,
                    "collisions": route_collisions,
                }
            )
        if not blocked_attempts:
            return 0, [], None, None, blocked_attempts, []
        last = blocked_attempts[-1]
        collisions.extend(last["collisions"])
        return 0, list(last["collisions"]), dict(last["port"]), str(last["route_kind"]), blocked_attempts, []

    def add_positions_without_reuse(
        positions: list[RoutePosition],
        *,
        record_collisions: bool = True,
    ) -> tuple[int, list[dict[str, Any]]]:
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        proposed_entities: list[dict[str, Any]] = []
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            if key in seen:
                route_collisions.append({"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"})
                continue
            seen.add(key)
            if key in occupied_entities:
                route_collisions.append(
                    {
                        "x": key[0],
                        "y": key[1],
                        "reason": reason,
                        "entity_name": str(occupied_entities[key].get("name") or ""),
                    }
                )
                continue
            candidate = connector_belt(-1, x, belt_y, direction=direction, name=belt_name)
            placement = connector_placement_collisions(candidate, reason, proposed_entities)
            if placement:
                route_collisions.extend(placement)
                continue
            proposed_entities.append(candidate)
        if route_collisions:
            if record_collisions:
                collisions.extend(route_collisions)
            return 0, route_collisions

        before = len(connectors)
        for x, belt_y, _reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            belt = connector_belt(
                len(entities) + len(connectors) + 1,
                x,
                belt_y,
                direction=direction,
                name=belt_name,
            )
            connectors.append(belt)
            occupied.add(key)
            occupied_entities[key] = belt
        return len(connectors) - before, route_collisions

    def audit_exact_route_positions(segment_type: str, positions: list[RoutePosition]) -> dict[str, Any]:
        failures: list[dict[str, Any]] = []
        for x, belt_y, _reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            entity = occupied_entities.get(key)
            if entity is None:
                failures.append({"x": key[0], "y": key[1], "reason": "missing-belt"})
                continue
            entity_name = str(entity.get("name") or "")
            if not is_belt_like_entity_name(entity_name):
                failures.append({"x": key[0], "y": key[1], "entity_name": entity_name, "reason": "non-belt-entity"})
                continue
            if canonical_transport_belt_name(entity_name) != belt_name:
                failures.append({"x": key[0], "y": key[1], "entity_name": entity_name, "reason": "belt-tier-mismatch"})
                continue
            if entity.get("direction") != direction:
                failures.append(
                    {
                        "x": key[0],
                        "y": key[1],
                        "entity_name": entity_name,
                        "direction": entity.get("direction"),
                        "expected_direction": direction,
                        "reason": "wrong-flow-direction",
                    }
                )
        return {
            "segment_type": segment_type,
            "status": "failed" if failures else "pass",
            "positions_checked": len(positions),
            "failures": failures,
        }

    def ports_for_instance(node: dict[str, Any], instance: int, side: str, roles: set[str]) -> list[dict[str, Any]]:
        ports: list[dict[str, Any]] = []
        spacing = float(layout_plan.get("spacing") or 0)
        row_spacing = float(layout_plan.get("row_spacing", spacing))
        columns = max(1, int(node.get("columns") or 1))
        source_width = float(node.get("source_width") or 0)
        source_height = float(node.get("source_height") or 0)
        col = instance % columns
        row = instance // columns
        origin_x = float(node["x"]) + col * (source_width + spacing)
        origin_y = float(node["y"]) + row * (source_height + row_spacing)
        for port in node.get("ports") or []:
            if port.get("side") != side or port.get("role") not in roles:
                continue
            ports.append(
                {
                    "node_item": node.get("item"),
                    "node_recipe": node.get("recipe"),
                    "node_fingerprint": node.get("fingerprint"),
                    "node_instance": instance,
                    "node_column": col,
                    "node_row": row,
                    "side": port.get("side"),
                    "role": port.get("role"),
                    "entity_name": port.get("entity_name"),
                    "entity_type": port.get("entity_type"),
                    "direction": port.get("direction"),
                    "source": port.get("source"),
                    "inserter_entity_number": port.get("inserter_entity_number"),
                    "machine_entity_numbers": port.get("machine_entity_numbers"),
                    "x": round(origin_x + float(port.get("x") or 0), 3),
                    "y": round(origin_y + float(port.get("y") or 0), 3),
                }
            )
        return ports

    def candidate_ports(side: str, roles: set[str]) -> list[dict[str, Any]]:
        ports: list[dict[str, Any]] = []
        for node in layout_plan.get("nodes") or []:
            for instance in range(int(node.get("instances") or 1)):
                ports.extend(ports_for_instance(node, instance, side, roles))
        return ports

    def port_groups_by_row(ports: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
        for port in ports:
            key = (str(port.get("node_fingerprint") or ""), int(port.get("node_row") or 0))
            groups.setdefault(key, []).append(port)
        return [
            groups[key]
            for key in sorted(
                groups,
                key=lambda item: (
                    min(float(port["y"]) for port in groups[item]),
                    min(float(port["x"]) for port in groups[item]),
                ),
            )
        ]

    def ports_by_distance(ports: list[dict[str, Any]], y: float, side: str) -> list[dict[str, Any]]:
        role_priority = {"machine-input": 0, "machine-output": 0, "input": 1, "output": 1, "edge-bus": 2, "boundary": 3}
        def bridge_lane_score(port: dict[str, Any]) -> int:
            fingerprint = str(port.get("node_fingerprint") or "")
            port_y = round(float(port.get("y") or 0.0), 3)
            return sum(
                1
                for bridge in bridges
                if bridge.get("status") == "connected"
                and str(bridge.get("node_fingerprint") or "") == fingerprint
                and round(float(bridge.get("bridge_y") or 0.0), 3) == port_y
            )

        def belt_surface_priority(port: dict[str, Any]) -> int:
            entity_name = str(port.get("entity_name") or "")
            if entity_name.endswith("transport-belt") and not entity_name.endswith("underground-belt"):
                return 0
            if entity_name.endswith("splitter"):
                return 1
            if entity_name.endswith("underground-belt"):
                return 2
            return 3

        def machine_output_drop_priority(port: dict[str, Any]) -> int:
            if str(port.get("role")) != "machine-output":
                return 2
            if port.get("direction") in {DIR_NORTH, DIR_SOUTH}:
                return 0
            return 1

        if side == "left":
            return sorted(
                ports,
                key=lambda port: (
                    0 if str(port.get("role")) == "machine-input" else 1,
                    -bridge_lane_score(port),
                    belt_surface_priority(port),
                    role_priority.get(str(port.get("role")), 9),
                    abs(float(port["y"]) - y),
                    float(port["x"]),
                ),
            )
        return sorted(
            ports,
            key=lambda port: (
                machine_output_drop_priority(port),
                -bridge_lane_score(port),
                belt_surface_priority(port),
                role_priority.get(str(port.get("role")), 9),
                -float(port["y"]) if str(port.get("role")) == "machine-output" else 0.0,
                abs(float(port["y"]) - y),
                -float(port["x"]),
            ),
        )

    def port_by_y(ports: list[dict[str, Any]], *, prefer: str) -> dict[float, dict[str, Any]]:
        selected: dict[float, dict[str, Any]] = {}
        for port in ports:
            y = round(float(port["y"]), 3)
            current = selected.get(y)
            if current is None:
                selected[y] = port
                continue
            if prefer == "rightmost" and float(port["x"]) > float(current["x"]):
                selected[y] = port
            if prefer == "leftmost" and float(port["x"]) < float(current["x"]):
                selected[y] = port
        return selected

    def port_by_y_matching(
        ports: list[dict[str, Any]],
        *,
        prefer: str,
        predicate,
    ) -> dict[float, dict[str, Any]]:
        return port_by_y([port for port in ports if predicate(port)], prefer=prefer)

    def can_start_horizontal_flow(port: dict[str, Any]) -> bool:
        entity_name = str(port.get("entity_name") or "")
        if entity_name.endswith("underground-belt") and port.get("entity_type") == "input":
            return False
        return True

    def can_end_horizontal_flow(port: dict[str, Any]) -> bool:
        entity_name = str(port.get("entity_name") or "")
        if entity_name.endswith("underground-belt") and port.get("entity_type") == "output":
            return False
        return True

    def is_simple_surface_belt_port(port: dict[str, Any]) -> bool:
        entity_name = str(port.get("entity_name") or "")
        return entity_name.endswith("transport-belt") and not entity_name.endswith("underground-belt")

    def bridge_already_recorded(node: dict[str, Any], instance: int, next_instance: int, y: float) -> bool:
        fingerprint = str(node.get("fingerprint") or "")
        def bridge_instance(bridge: dict[str, Any], key: str) -> int:
            value = bridge.get(key)
            return int(value) if isinstance(value, int) else -1
        return any(
            str(bridge.get("node_fingerprint") or "") == fingerprint
            and bridge_instance(bridge, "from_instance") == instance
            and bridge_instance(bridge, "to_instance") == next_instance
            and round(float(bridge.get("bridge_y") or 0.0), 3) == round(y, 3)
            for bridge in bridges
        )

    def add_inter_instance_bridge_lane(node: dict[str, Any], y: float, *, require_simple_surface: bool) -> int:
        before = len(connectors)
        instances = int(node.get("instances") or 1)
        columns = max(1, int(node.get("columns") or 1))
        if instances < 2 or columns < 2:
            return 0
        for instance in range(instances - 1):
            col = instance % columns
            next_instance = instance + 1
            if next_instance >= instances or next_instance // columns != instance // columns:
                continue
            if col + 1 >= columns:
                continue
            if bridge_already_recorded(node, instance, next_instance, y):
                continue

            def bridge_port_filter(port: dict[str, Any], endpoint_check) -> bool:
                if round(float(port.get("y") or 0.0), 3) != round(y, 3):
                    return False
                if not endpoint_check(port):
                    return False
                if require_simple_surface and not is_simple_surface_belt_port(port):
                    return False
                return True

            right_ports = port_by_y_matching(
                ports_for_instance(node, instance, "right", {"output", "edge-bus", "boundary"}),
                prefer="rightmost",
                predicate=lambda port: bridge_port_filter(port, can_start_horizontal_flow),
            )
            left_ports = port_by_y_matching(
                ports_for_instance(node, next_instance, "left", {"input", "edge-bus", "boundary"}),
                prefer="leftmost",
                predicate=lambda port: bridge_port_filter(port, can_end_horizontal_flow),
            )
            right_port = right_ports.get(round(y, 3))
            left_port = left_ports.get(round(y, 3))
            if right_port is None or left_port is None:
                continue
            start_x = float(right_port["x"]) + 1.0
            end_x = float(left_port["x"]) - 1.0
            if start_x > end_x:
                continue
            belt_name = connector_belt_name_for_port(right_port)
            reason = f"bridge:{node.get('item')}:{instance}->{next_instance}:{y:g}"
            positions = horizontal_positions(start_x, end_x, y, reason, belt_name)
            belts_added, route_collisions, existing_belts_used = add_positions_reusing_existing_belts(positions)
            status = "connected" if not route_collisions else "blocked"
            bridges.append(
                {
                    "node_item": node.get("item"),
                    "node_recipe": node.get("recipe"),
                    "node_fingerprint": node.get("fingerprint"),
                    "from_instance": instance,
                    "to_instance": next_instance,
                    "bridge_y": y,
                    "from_port": right_port,
                    "to_port": left_port,
                    "status": status,
                    "belts_added": belts_added,
                    "existing_belts_used": existing_belts_used,
                    "collisions": route_collisions,
                    "route_kind": "inter-instance-direct",
                }
            )
        return len(connectors) - before

    def add_inter_instance_bridges() -> int:
        before = len(connectors)
        for node in layout_plan.get("nodes") or []:
            instances = max(1, int(node.get("instances") or 1))
            columns = max(1, int(node.get("columns") or 1))
            for row_start in range(0, instances, columns):
                ys = {
                    round(float(port.get("y") or 0.0), 3)
                    for port in ports_for_instance(node, row_start, "right", {"output", "edge-bus", "boundary"})
                    if can_start_horizontal_flow(port) and is_simple_surface_belt_port(port)
                }
                for y in sorted(ys):
                    add_inter_instance_bridge_lane(node, y, require_simple_surface=True)
        return len(connectors) - before

    bridges_added = add_inter_instance_bridges()

    def node_by_fingerprint() -> dict[str, dict[str, Any]]:
        return {
            str(node.get("fingerprint")): node
            for node in layout_plan.get("nodes") or []
            if node.get("fingerprint") is not None
        }

    def boundary_required_rate(boundary_label: str) -> float | None:
        if boundary_label.startswith("output:"):
            item = boundary_label.split(":", 1)[1]
            for output in layout_plan.get("boundary_outputs") or []:
                if str(output.get("item")) == item:
                    rate = output.get("rate_per_minute")
                    return float(rate) if isinstance(rate, (int, float)) else None
        if boundary_label.startswith("input:"):
            item = boundary_label.split(":", 1)[1]
            for input_item in layout_plan.get("boundary_inputs") or []:
                if str(input_item.get("item")) == item:
                    rate = input_item.get("rate_per_minute")
                    return float(rate) if isinstance(rate, (int, float)) else None
        return None

    def route_capacity_for_port(port: dict[str, Any] | None) -> float | None:
        if knowledge is None or not port:
            return None
        belt = knowledge.belt(connector_belt_name_for_port(port))
        return float(belt.items_per_minute) if belt is not None else None

    def connected_boundary_capacity(boundary_label: str, fingerprint: str) -> float | None:
        if knowledge is None:
            return None
        total = 0.0
        for route in routes:
            if route.get("status") != "connected":
                continue
            if str(route.get("boundary") or "") != boundary_label:
                continue
            port = route.get("port") or {}
            if str(port.get("node_fingerprint") or "") != fingerprint:
                continue
            capacity = route_capacity_for_port(port)
            if capacity is None:
                return None
            total += capacity
        return total

    def used_boundary_route_lanes(boundary_label: str, fingerprint: str) -> set[float]:
        lanes: set[float] = set()
        for route in routes:
            if str(route.get("boundary") or "") != boundary_label:
                continue
            port = route.get("port") or {}
            if str(port.get("node_fingerprint") or "") != fingerprint:
                continue
            if port.get("y") is not None:
                lanes.add(round(float(port["y"]), 3))
        return lanes

    def add_boundary_route_from_candidates(
        boundary_label: str,
        candidates: list[tuple[dict[str, Any], str, list[RoutePosition]]],
    ) -> dict[str, Any]:
        belts_added, route_collisions, port, route_kind, blocked_attempts, route_positions = add_first_clear_route(candidates)
        status = "connected" if port is not None and not route_collisions else "blocked"
        route = {
            "boundary": boundary_label,
            "status": status,
            "belts_added": belts_added,
            "collisions": route_collisions,
            "port": port,
            "route_kind": route_kind,
            "blocked_attempts": blocked_attempts,
        }
        if route_positions and route_kind and (
            boundary_label.startswith("input:")
            or route_kind.startswith("machine-input-side-load")
            or route_kind.startswith("machine-input-right-feed")
            or route_kind.startswith("machine-output-side-load")
        ):
            route["route_positions"] = route_positions
        routes.append(route)
        return route

    def boundary_route_candidates(
        row_ports: list[dict[str, Any]],
        *,
        side: str,
        boundary_label: str,
    ) -> list[tuple[dict[str, Any], str, list[RoutePosition]]]:
        row_y = min(float(port["y"]) for port in row_ports)
        ports = ports_by_distance(row_ports, row_y, side)
        candidates: list[tuple[dict[str, Any], str, list[RoutePosition]]] = []
        def left_boundary_start_x(target_x: float) -> float:
            return round(target_x - math.floor(target_x), 3)

        for port in ports:
            belt_name = connector_belt_name_for_port(port)
            if side == "left":
                start_x = left_boundary_start_x(float(port["x"]))
                end_x = float(port["x"]) - 1.0
                if port.get("role") == "machine-input" and port.get("direction") in {DIR_NORTH, DIR_SOUTH}:
                    if port.get("direction") == DIR_SOUTH:
                        for offset in range(1, 13):
                            feed_y = float(port["y"]) + offset
                            feed_x = float(port["x"]) + 1.0
                            horizontal_end_x = float(port["x"])
                            if start_x > horizontal_end_x:
                                continue
                            positions = horizontal_positions(
                                start_x,
                                horizontal_end_x,
                                feed_y,
                                f"{boundary_label}:machine-input-right-feed",
                                belt_name,
                            )
                            positions.extend(
                                vertical_positions(
                                    feed_x,
                                    feed_y,
                                    float(port["y"]) + 1.0,
                                    f"{boundary_label}:machine-input-right-feed",
                                    DIR_NORTH,
                                    belt_name,
                                )
                            )
                            positions.append(
                                (
                                    round(feed_x, 3),
                                    round(float(port["y"]), 3),
                                    f"{boundary_label}:machine-input-right-feed",
                                    DIR_WEST,
                                    belt_name,
                                )
                            )
                            candidates.append((port, f"machine-input-right-feed-{offset}", positions))
                    offsets = range(1, 13)
                    for offset in offsets:
                        feeder_y = float(port["y"]) - offset if port.get("direction") == DIR_SOUTH else float(port["y"]) + offset
                        horizontal_end_x = float(port["x"]) - 1.0
                        if start_x > horizontal_end_x:
                            continue
                        positions = horizontal_positions(
                            start_x,
                            horizontal_end_x,
                            feeder_y,
                            f"{boundary_label}:machine-input-side-load",
                            belt_name,
                        )
                        positions.extend(
                            vertical_positions(
                                float(port["x"]),
                                feeder_y,
                                float(port["y"]),
                                f"{boundary_label}:machine-input-side-load",
                                int(port["direction"]),
                                belt_name,
                            )
                        )
                        candidates.append((port, f"machine-input-side-load-{offset}", positions))
            else:
                start_x = float(port["x"]) + 1.0
                end_x = float(layout_plan["estimated_width"]) - 0.5
                if port.get("role") == "machine-output" and port.get("direction") in {DIR_NORTH, DIR_SOUTH}:
                    offsets = range(0, 9)
                    for offset in offsets:
                        if port.get("direction") == DIR_SOUTH:
                            turn_y = float(port["y"]) + offset
                            vertical_start_y = float(port["y"])
                            vertical_end_y = turn_y - 1.0
                        else:
                            turn_y = float(port["y"]) - offset
                            vertical_start_y = float(port["y"])
                            vertical_end_y = turn_y + 1.0
                        positions = []
                        if offset > 0:
                            positions = vertical_positions(
                                float(port["x"]),
                                vertical_start_y,
                                vertical_end_y,
                                f"{boundary_label}:machine-output-side-load",
                                int(port["direction"]),
                                belt_name,
                            )
                        positions.extend(
                            horizontal_positions(
                                float(port["x"]),
                                end_x,
                                turn_y,
                                f"{boundary_label}:machine-output-side-load",
                                belt_name,
                            )
                        )
                        candidates.append((port, f"machine-output-side-load-{offset}", positions))
            candidates.append(
                (
                    port,
                    *route_candidate(
                        start_x=start_x,
                        end_x=end_x,
                        y=float(port["y"]),
                        reason=boundary_label,
                        belt_name=belt_name,
                    ),
                )
            )
        return candidates

    def add_boundary_routes(
        boundary_label: str,
        *,
        side: str,
        row_groups: list[list[dict[str, Any]]],
    ) -> None:
        candidates_by_fingerprint: dict[str, list[tuple[dict[str, Any], str, list[RoutePosition]]]] = {}
        if side == "left":
            machine_input_candidates_by_instance: dict[tuple[str, int], list[tuple[dict[str, Any], str, list[RoutePosition]]]] = {}
            for row_ports in row_groups:
                for candidate in boundary_route_candidates(row_ports, side=side, boundary_label=boundary_label):
                    port = candidate[0]
                    if port.get("role") != "machine-input":
                        continue
                    key = (str(port.get("node_fingerprint") or ""), int(port.get("node_instance") or 0))
                    machine_input_candidates_by_instance.setdefault(key, []).append(candidate)
            if machine_input_candidates_by_instance:
                for key in sorted(machine_input_candidates_by_instance, key=lambda item: (item[0], item[1])):
                    add_boundary_route_from_candidates(boundary_label, machine_input_candidates_by_instance[key])
                return

        for row_ports in row_groups:
            candidates = boundary_route_candidates(row_ports, side=side, boundary_label=boundary_label)
            if not candidates:
                continue
            fingerprint = str(candidates[0][0].get("node_fingerprint") or "")
            candidates_by_fingerprint.setdefault(fingerprint, []).extend(candidates)
            add_boundary_route_from_candidates(boundary_label, candidates)

        required_rate = boundary_required_rate(boundary_label)
        if required_rate is None or knowledge is None:
            return
        for fingerprint, candidates in candidates_by_fingerprint.items():
            while True:
                current_capacity = connected_boundary_capacity(boundary_label, fingerprint)
                if current_capacity is None or current_capacity >= required_rate:
                    break
                used_lanes = used_boundary_route_lanes(boundary_label, fingerprint)
                remaining = [
                    candidate
                    for candidate in candidates
                    if round(float(candidate[0].get("y") or 0.0), 3) not in used_lanes
                ]
                if not remaining:
                    break
                route = add_boundary_route_from_candidates(boundary_label, remaining)
                if route.get("status") != "connected":
                    break

    for boundary in layout_plan.get("boundary_inputs") or []:
        boundary_label = f"input:{boundary['item']}"
        row_groups = port_groups_by_row(candidate_ports("left", {"machine-input", "input", "edge-bus", "boundary"}))
        if not row_groups:
            left_end = int(max(0, float(root["x"]) - 1))
            positions = [
                (float(x), default_y, boundary_label, DIR_EAST, "transport-belt")
                for x in range(0, left_end + 1)
            ]
            belts_added, route_collisions = add_positions(positions)
            routes.append(
                {
                    "boundary": boundary_label,
                    "status": "stub-only" if not route_collisions else "blocked",
                    "belts_added": belts_added,
                    "collisions": route_collisions,
                    "reason": "no-left-port",
                }
            )
            continue

        add_boundary_routes(boundary_label, side="left", row_groups=row_groups)

    for boundary in layout_plan.get("boundary_outputs") or []:
        boundary_label = f"output:{boundary['item']}"
        row_groups = port_groups_by_row(candidate_ports("right", {"machine-output", "output", "edge-bus", "boundary"}))
        if not row_groups:
            right_start = int(float(root["x"]) + float(root["planned_width"]) + 1)
            right_end = int(max(right_start - 1, float(layout_plan["estimated_width"]) - 1))
            positions = [
                (float(x), default_y, boundary_label, DIR_EAST, "transport-belt")
                for x in range(right_start, right_end + 1)
            ]
            belts_added, route_collisions = add_positions(positions)
            routes.append(
                {
                    "boundary": boundary_label,
                    "status": "stub-only" if not route_collisions else "blocked",
                    "belts_added": belts_added,
                    "collisions": route_collisions,
                    "reason": "no-right-port",
                }
            )
            continue

        add_boundary_routes(boundary_label, side="right", row_groups=row_groups)

    def add_bridges_for_selected_boundary_routes() -> int:
        before = len(connectors)
        node_index = node_by_fingerprint()
        for route in routes:
            if route.get("status") != "connected":
                continue
            boundary = str(route.get("boundary") or "")
            if not boundary.startswith("output:"):
                continue
            port = route.get("port") or {}
            node = node_index.get(str(port.get("node_fingerprint") or ""))
            if not node:
                continue
            add_inter_instance_bridge_lane(
                node,
                round(float(port.get("y") or 0.0), 3),
                require_simple_surface=False,
            )
        return len(connectors) - before

    bridges_added += add_bridges_for_selected_boundary_routes()

    def add_input_fanouts() -> int:
        before = len(connectors)
        node_index = node_by_fingerprint()
        for route in routes:
            if route.get("status") != "connected":
                continue
            boundary = str(route.get("boundary") or "")
            if not boundary.startswith("input:"):
                continue
            port = route.get("port") or {}
            if port.get("role") == "machine-input":
                continue
            node = node_index.get(str(port.get("node_fingerprint") or ""))
            if not node:
                continue
            current_instance = int(port.get("node_instance") or 0)
            route_y = round(float(port.get("y") or 0.0), 3)
            instances = int(node.get("instances") or 1)
            columns = max(1, int(node.get("columns") or 1))
            while current_instance + 1 < instances:
                next_instance = current_instance + 1
                if next_instance // columns != current_instance // columns:
                    break
                next_ports = port_by_y(
                    ports_for_instance(node, next_instance, "left", {"machine-input", "input", "edge-bus", "boundary"}),
                    prefer="leftmost",
                )
                next_port = next_ports.get(route_y)
                if next_port is None:
                    input_fanouts.append(
                        {
                            "boundary": boundary,
                            "node_item": node.get("item"),
                            "node_recipe": node.get("recipe"),
                            "node_fingerprint": node.get("fingerprint"),
                            "from_instance": current_instance,
                            "to_instance": next_instance,
                            "fanout_y": route_y,
                            "from_port": port,
                            "to_port": None,
                            "status": "blocked",
                            "belts_added": 0,
                            "collisions": [],
                            "reason": "no-next-left-port-on-route-y",
                            "route_kind": "input-fanout-direct",
                        }
                    )
                    break
                start_x = float(port["x"]) + 1.0
                end_x = float(next_port["x"]) - 1.0
                if start_x > end_x:
                    input_fanouts.append(
                        {
                            "boundary": boundary,
                            "node_item": node.get("item"),
                            "node_recipe": node.get("recipe"),
                            "node_fingerprint": node.get("fingerprint"),
                            "from_instance": current_instance,
                            "to_instance": next_instance,
                            "fanout_y": route_y,
                            "from_port": port,
                            "to_port": next_port,
                            "status": "blocked",
                            "belts_added": 0,
                            "collisions": [],
                            "reason": "no-horizontal-gap",
                            "route_kind": "input-fanout-direct",
                        }
                    )
                    break
                belt_name = connector_belt_name_for_port(port)
                reason = f"fanout:{boundary}:{current_instance}->{next_instance}:{route_y:g}"
                positions = horizontal_positions(start_x, end_x, route_y, reason, belt_name)
                belts_added, route_collisions, existing_belts_used = add_positions_reusing_existing_belts(positions)
                status = "connected" if not route_collisions else "blocked"
                input_fanouts.append(
                    {
                        "boundary": boundary,
                        "node_item": node.get("item"),
                        "node_recipe": node.get("recipe"),
                        "node_fingerprint": node.get("fingerprint"),
                        "from_instance": current_instance,
                        "to_instance": next_instance,
                        "fanout_y": route_y,
                        "from_port": port,
                        "to_port": next_port,
                        "status": status,
                        "belts_added": belts_added,
                        "existing_belts_used": existing_belts_used,
                        "collisions": route_collisions,
                        "route_kind": "input-fanout-direct",
                    }
                )
                if route_collisions:
                    break
                port = next_port
                current_instance = next_instance
        return len(connectors) - before

    input_fanouts_added = add_input_fanouts()

    def add_output_fanins() -> int:
        before = len(connectors)
        node_index = node_by_fingerprint()
        for route in routes:
            if route.get("status") != "connected":
                continue
            boundary = str(route.get("boundary") or "")
            if not boundary.startswith("output:"):
                continue
            port = route.get("port") or {}
            node = node_index.get(str(port.get("node_fingerprint") or ""))
            if not node:
                continue
            current_instance = int(port.get("node_instance") or 0)
            route_y = round(float(port.get("y") or 0.0), 3)
            columns = max(1, int(node.get("columns") or 1))
            row_start = (current_instance // columns) * columns
            current_port = port
            while current_instance - 1 >= row_start:
                previous_instance = current_instance - 1
                previous_ports = port_by_y(
                    ports_for_instance(node, previous_instance, "right", {"machine-output", "output", "edge-bus", "boundary"}),
                    prefer="rightmost",
                )
                previous_port = previous_ports.get(route_y)
                if previous_port is None:
                    output_fanins.append(
                        {
                            "boundary": boundary,
                            "node_item": node.get("item"),
                            "node_recipe": node.get("recipe"),
                            "node_fingerprint": node.get("fingerprint"),
                            "from_instance": previous_instance,
                            "to_instance": current_instance,
                            "fanin_y": route_y,
                            "from_port": None,
                            "to_port": current_port,
                            "status": "blocked",
                            "belts_added": 0,
                            "collisions": [],
                            "reason": "no-previous-right-port-on-route-y",
                            "route_kind": "output-fanin-direct",
                        }
                    )
                    break
                source_x = round(float(previous_port["x"]), 3)
                start_x = round(source_x + 1.0, 3)
                end_x = float(current_port["x"]) - 1.0
                if start_x > end_x:
                    output_fanins.append(
                        {
                            "boundary": boundary,
                            "node_item": node.get("item"),
                            "node_recipe": node.get("recipe"),
                            "node_fingerprint": node.get("fingerprint"),
                            "from_instance": previous_instance,
                            "to_instance": current_instance,
                            "fanin_y": route_y,
                            "from_port": previous_port,
                            "to_port": current_port,
                            "status": "blocked",
                            "belts_added": 0,
                            "collisions": [],
                            "reason": "no-horizontal-gap",
                            "route_kind": "output-fanin-direct",
                        }
                    )
                    break
                source_belt_name = connector_belt_name_for_port(previous_port)
                belt_name = connector_belt_name_for_port(current_port)
                reason = f"fanin:{boundary}:{previous_instance}->{current_instance}:{route_y:g}"
                source_position: RoutePosition = (
                    source_x,
                    route_y,
                    f"fanin-source:{boundary}:{previous_instance}->{current_instance}:{route_y:g}",
                    DIR_EAST,
                    source_belt_name,
                )
                positions = [source_position]
                positions.extend(horizontal_positions(start_x, end_x, route_y, reason, belt_name))
                belts_added, route_collisions, existing_belts_used = add_positions_reusing_existing_belts(positions, record_collisions=False)
                route_kind = "output-fanin-direct"
                if route_collisions:
                    blocked_direct = route_collisions
                    detour_attempts: list[dict[str, Any]] = []
                    merge_x = round(float(current_port["x"]), 3)
                    protected_xs = sorted(
                        x
                        for x, y in output_pickup_blockers
                        if round(y, 3) == route_y and start_x <= x <= end_x
                    )
                    entry_x = round((protected_xs[0] - 1.0) if protected_xs else (end_x - 1.0), 3)
                    for detour_offset in (-1.0, 1.0, -2.0, 2.0):
                        detour_y = round(route_y + detour_offset, 3)
                        if start_x > entry_x:
                            continue
                        vertical_direction = DIR_NORTH if detour_y < route_y else DIR_SOUTH
                        merge_direction = DIR_SOUTH if detour_y < route_y else DIR_NORTH
                        detour_positions: list[RoutePosition] = [source_position]
                        if start_x <= round(entry_x - 1.0, 3):
                            detour_positions.extend(horizontal_positions(start_x, round(entry_x - 1.0, 3), route_y, reason, belt_name))
                        detour_positions.append((entry_x, route_y, reason, vertical_direction, belt_name))
                        detour_positions.append((entry_x, detour_y, reason, DIR_EAST, belt_name))
                        if round(entry_x + 1.0, 3) <= round(merge_x - 1.0, 3):
                            detour_positions.extend(horizontal_positions(round(entry_x + 1.0, 3), round(merge_x - 1.0, 3), detour_y, reason, belt_name))
                        detour_positions.append((merge_x, detour_y, reason, merge_direction, belt_name))
                        candidate_added, candidate_collisions, candidate_existing = add_positions_reusing_existing_belts(detour_positions, record_collisions=False)
                        if not candidate_collisions:
                            positions = detour_positions
                            belts_added = candidate_added
                            route_collisions = []
                            existing_belts_used = candidate_existing
                            route_kind = f"output-fanin-detour-{detour_offset:g}"
                            break
                        detour_attempts.append({"offset": detour_offset, "collisions": candidate_collisions})
                    if route_collisions:
                        collisions.extend(route_collisions)
                        route_collisions = blocked_direct
                    else:
                        blocked_direct = []
                status = "connected" if not route_collisions else "blocked"
                output_fanins.append(
                    {
                        "route_positions": positions,
                        "boundary": boundary,
                        "node_item": node.get("item"),
                        "node_recipe": node.get("recipe"),
                        "node_fingerprint": node.get("fingerprint"),
                        "from_instance": previous_instance,
                        "to_instance": current_instance,
                        "fanin_y": route_y,
                        "from_port": previous_port,
                        "to_port": current_port,
                        "status": status,
                        "belts_added": belts_added,
                        "existing_belts_used": existing_belts_used,
                        "collisions": route_collisions,
                        "route_kind": route_kind,
                    }
                )
                if route_collisions:
                    break
                current_port = previous_port
                current_instance = previous_instance
        return len(connectors) - before

    output_fanins_added = add_output_fanins()

    def build_output_byproduct_audit() -> list[dict[str, Any]]:
        if knowledge is None:
            return []
        target_item = str(layout_plan.get("target_item") or "")
        boundary_inputs_by_item = {
            str(item.get("item") or ""): item
            for item in layout_plan.get("boundary_inputs") or []
            if item.get("item")
        }
        audits: list[dict[str, Any]] = []
        seen: set[str] = set()
        for node in layout_plan.get("nodes") or []:
            recipe_name = str(node.get("recipe") or "")
            if not recipe_name or recipe_name in seen:
                continue
            seen.add(recipe_name)
            recipe = knowledge.recipe(recipe_name)
            if recipe is None:
                continue
            ingredient_by_item = {
                ingredient.name: ingredient
                for ingredient in recipe.ingredients
                if ingredient.type == "item"
            }
            byproducts = []
            for product in recipe.products:
                if product.type != "item" or product.name == target_item:
                    continue
                same_recipe_input = ingredient_by_item.get(product.name)
                boundary_input = boundary_inputs_by_item.get(product.name)
                byproducts.append(
                    {
                        "item": product.name,
                        "amount": product.amount,
                        "probability": product.probability,
                        "same_recipe_input": same_recipe_input is not None,
                        "recipe_input_amount": same_recipe_input.amount if same_recipe_input is not None else None,
                        "input_boundary_rate_per_minute": (
                            float(boundary_input["rate_per_minute"])
                            if isinstance((boundary_input or {}).get("rate_per_minute"), (int, float))
                            else None
                        ),
                        "input_boundary_side": str((boundary_input or {}).get("side") or "") or None,
                    }
                )
            if not byproducts:
                continue
            recyclable_byproducts = [
                item["item"]
                for item in byproducts
                if item.get("same_recipe_input")
            ]
            non_recyclable_byproducts = [
                item["item"]
                for item in byproducts
                if not item.get("same_recipe_input")
            ]
            if recyclable_byproducts and not non_recyclable_byproducts:
                recommended_handling = "recycle-to-input-boundary"
            elif recyclable_byproducts:
                recommended_handling = "mixed-recycle-and-separate"
            else:
                recommended_handling = "separate-or-export"
            audits.append(
                {
                    "recipe": recipe_name,
                    "target_item": target_item,
                    "status": "requires-separation",
                    "recommended_handling": recommended_handling,
                    "recyclable_byproducts": recyclable_byproducts,
                    "non_recyclable_byproducts": non_recyclable_byproducts,
                    "byproducts": byproducts,
                }
            )
        return audits

    def add_output_byproduct_separation(byproduct_audit: list[dict[str, Any]]) -> tuple[int, int, int, int, list[dict[str, Any]]]:
        if not byproduct_audit:
            return 0, 0, 0, 0, []
        target_items = {
            str(item.get("target_item") or "")
            for item in byproduct_audit
            if item.get("target_item")
        }
        if not target_items:
            return 0, 0, 0, 0, []
        right_boundary_x = round(float(layout_plan["estimated_width"]) - 0.5, 3)
        left_boundary_x = 0.5
        min_y = 0.5
        max_y = round(float(layout_plan["estimated_height"]) - 0.5, 3)
        splitters_added = 0
        overflow_belts_added = 0
        recycle_belts_added = 0
        merge_belts_added = 0
        separations: list[dict[str, Any]] = []

        def recyclable_input_sides(audits: list[dict[str, Any]]) -> list[str]:
            sides = {
                str(byproduct.get("input_boundary_side") or "")
                for audit in audits
                for byproduct in audit.get("byproducts") or []
                if byproduct.get("same_recipe_input") and byproduct.get("input_boundary_side")
            }
            return sorted(side for side in sides if side)

        def route_from_splitter_side_output(
            *,
            splitter_x: float,
            overflow_y: float,
            target_x: float,
            target_y: float,
            final_direction: int,
            belt_name: str,
            boundary: str,
            route_reason: str,
        ) -> list[RoutePosition]:
            turn_x = round(min(right_boundary_x, splitter_x + 2.0), 3)
            if turn_x <= splitter_x or target_x >= turn_x:
                return []
            vertical_direction = DIR_SOUTH if target_y > overflow_y else DIR_NORTH
            horizontal_start_x = round(splitter_x + 2.0, 3)
            horizontal_end_x = round(turn_x - 1.0, 3)
            positions: list[RoutePosition] = []
            if horizontal_start_x <= horizontal_end_x:
                positions.extend(
                    directional_horizontal_positions(
                        horizontal_start_x,
                        horizontal_end_x,
                        overflow_y,
                        f"{boundary}:{route_reason}",
                        DIR_EAST,
                        belt_name,
                    )
                )
            positions.extend(
                vertical_positions(
                    turn_x,
                    overflow_y,
                    target_y,
                    f"{boundary}:{route_reason}",
                    vertical_direction,
                    belt_name,
                )
            )
            positions.extend(
                directional_horizontal_positions(
                    round(turn_x - 1.0, 3),
                    round(target_x + 1.0, 3),
                    target_y,
                    f"{boundary}:{route_reason}",
                    DIR_WEST,
                    belt_name,
                )
            )
            positions.append(
                (
                    round(target_x, 3),
                    round(target_y, 3),
                    f"{boundary}:{route_reason}",
                    final_direction,
                    belt_name,
                )
            )
            return positions

        def input_merge_targets(byproducts: list[str], belt_name: str) -> list[dict[str, Any]]:
            targets: list[dict[str, Any]] = []
            seen: set[tuple[float, float, float]] = set()
            for byproduct in byproducts:
                input_boundary = f"input:{byproduct}"
                for input_route in routes:
                    if input_route.get("status") != "connected" or str(input_route.get("boundary") or "") != input_boundary:
                        continue
                    for x, y, _reason, direction, route_belt_name in input_route.get("route_positions") or []:
                        if direction != DIR_EAST or route_belt_name != belt_name:
                            continue
                        if float(x) > 8.5:
                            continue
                        target_key = (round(float(x), 3), round(float(y), 3))
                        entity = occupied_entities.get(target_key)
                        if entity is None or str(entity.get("name") or "") != belt_name or entity.get("direction") != DIR_EAST:
                            continue
                        for side_y, merge_direction in ((round(float(y) - 1.0, 3), DIR_SOUTH), (round(float(y) + 1.0, 3), DIR_NORTH)):
                            if side_y < min_y or side_y > max_y:
                                continue
                            key = (round(float(x), 3), side_y, float(y))
                            if key in seen:
                                continue
                            seen.add(key)
                            targets.append(
                                {
                                    "item": byproduct,
                                    "input_x": round(float(x), 3),
                                    "input_y": round(float(y), 3),
                                    "merge_x": round(float(x), 3),
                                    "merge_y": side_y,
                                    "merge_direction": merge_direction,
                                }
                            )
            return sorted(targets, key=lambda item: (item["input_y"], item["input_x"], item["merge_y"]))

        def recycle_merge_candidates(
            splitter_x: float,
            overflow_y: float,
            belt_name: str,
            boundary: str,
            recyclable_byproducts: list[str],
        ) -> list[tuple[dict[str, Any], list[RoutePosition]]]:
            candidates: list[tuple[dict[str, Any], list[RoutePosition]]] = []
            for target in input_merge_targets(recyclable_byproducts, belt_name):
                positions = route_from_splitter_side_output(
                    splitter_x=splitter_x,
                    overflow_y=overflow_y,
                    target_x=float(target["merge_x"]),
                    target_y=float(target["merge_y"]),
                    final_direction=int(target["merge_direction"]),
                    belt_name=belt_name,
                    boundary=boundary,
                    route_reason="output-byproduct-recycle-merge",
                )
                if positions:
                    candidates.append((target, positions))
            return candidates

        def recycle_return_candidates(splitter_x: float, overflow_y: float, belt_name: str, boundary: str) -> list[list[RoutePosition]]:
            turn_x = round(min(right_boundary_x, splitter_x + 2.0), 3)
            if turn_x <= splitter_x:
                return []
            candidate_offsets = [2, 3, 4, 5, 6, 7, 8, -2, -3, -4, -5, -6, -7, -8]
            candidates: list[list[RoutePosition]] = []
            for offset in candidate_offsets:
                recycle_y = round(overflow_y + offset, 3)
                if recycle_y < min_y or recycle_y > max_y:
                    continue
                positions = route_from_splitter_side_output(
                    splitter_x=splitter_x,
                    overflow_y=overflow_y,
                    target_x=left_boundary_x,
                    target_y=recycle_y,
                    final_direction=DIR_WEST,
                    belt_name=belt_name,
                    boundary=boundary,
                    route_reason="output-byproduct-recycle-return",
                )
                if positions:
                    candidates.append(positions)
            return candidates

        def pre_fanin_input_sideload_candidate(
            fanin: dict[str, Any],
            splitter_x: float,
            overflow_y: float,
            belt_name: str,
            boundary: str,
        ) -> tuple[dict[str, Any], list[RoutePosition]] | None:
            from_port = fanin.get("from_port") or {}
            feed_x = round(float(from_port.get("x") or 0.0) + 1.0, 3)
            input_y = round(overflow_y + 1.0, 3)
            feed_key = (feed_x, input_y)
            feed_entity = occupied_entities.get(feed_key)
            if (
                feed_entity is None
                or str(feed_entity.get("name") or "") != belt_name
                or feed_entity.get("direction") != DIR_NORTH
            ):
                return None
            first_x = round(splitter_x + 1.0, 3)
            side_load_x = round(feed_x + 1.0, 3)
            reason = f"{boundary}:pre-fanin-output-byproduct-recycle-sideload-input-lane"
            for offset in range(4, 16):
                turn_x = round(first_x + float(offset), 3)
                if turn_x > right_boundary_x:
                    break
                positions: list[RoutePosition] = []
                positions.extend(directional_horizontal_positions(first_x, round(turn_x - 1.0, 3), overflow_y, reason, DIR_EAST, belt_name))
                positions.append((turn_x, overflow_y, reason, DIR_SOUTH, belt_name))
                positions.append((turn_x, input_y, reason, DIR_WEST, belt_name))
                positions.extend(directional_horizontal_positions(round(turn_x - 1.0, 3), side_load_x, input_y, reason, DIR_WEST, belt_name))
                if positions:
                    return (
                        {
                            "item": "",
                            "input_x": feed_x,
                            "input_y": input_y,
                            "merge_x": feed_x,
                            "merge_y": input_y,
                            "sideload_x": side_load_x,
                            "sideload_y": input_y,
                            "merge_direction": DIR_NORTH,
                        },
                        positions,
                    )
            return None

        def specs_to_route_positions(specs: list[RouteEntitySpec], belt_name: str) -> list[RoutePosition]:
            return [
                (
                    round(float(spec["x"]), 3),
                    round(float(spec["y"]), 3),
                    str(spec.get("reason") or "connector"),
                    int(spec.get("direction", DIR_EAST)),
                    belt_name,
                )
                for spec in specs
            ]

        def pre_fanin_underground_corridor_candidates(
            splitter_x: float,
            overflow_y: float,
            belt_name: str,
            boundary: str,
            recyclable_byproducts: list[str],
        ) -> list[tuple[dict[str, Any], list[RouteEntitySpec], list[RoutePosition]]]:
            underground_name = belt_name.replace("transport-belt", "underground-belt")
            if underground_name == belt_name:
                return []
            candidates: list[tuple[dict[str, Any], list[RouteEntitySpec], list[RoutePosition]]] = []
            targets = [
                target
                for target in input_merge_targets(recyclable_byproducts, belt_name)
                if float(target["merge_y"]) > overflow_y
                and float(target["merge_y"]) - overflow_y <= 8.0
            ]
            for target in targets:
                merge_y = round(float(target["merge_y"]), 3)
                corridor_y = round(merge_y + 1.0, 3)
                underground_input_y = round(overflow_y + 1.0, 3)
                underground_output_y = round(corridor_y - 1.0, 3)
                if corridor_y > max_y or underground_output_y <= underground_input_y:
                    continue
                for offset in range(3, 36):
                    turn_x = round(splitter_x + float(offset), 3)
                    if turn_x >= right_boundary_x:
                        break
                    reason = f"{boundary}:pre-fanin-output-byproduct-recycle-underground-corridor"
                    specs: list[RouteEntitySpec] = []
                    for x, y, _route_reason, direction, _route_belt in directional_horizontal_positions(
                        round(splitter_x + 2.0, 3),
                        round(turn_x - 1.0, 3),
                        overflow_y,
                        reason,
                        DIR_EAST,
                        belt_name,
                    ):
                        specs.append({"x": x, "y": y, "reason": reason, "direction": direction, "name": belt_name})
                    specs.append({"x": turn_x, "y": overflow_y, "reason": reason, "direction": DIR_SOUTH, "name": belt_name})
                    specs.append({"x": turn_x, "y": underground_input_y, "reason": reason, "direction": DIR_SOUTH, "name": underground_name, "entity_type": "input"})
                    specs.append({"x": turn_x, "y": underground_output_y, "reason": reason, "direction": DIR_SOUTH, "name": underground_name, "entity_type": "output"})
                    for x, y, _route_reason, direction, _route_belt in directional_horizontal_positions(
                        turn_x,
                        1.5,
                        corridor_y,
                        reason,
                        DIR_WEST,
                        belt_name,
                    ):
                        specs.append({"x": x, "y": y, "reason": reason, "direction": direction, "name": belt_name})
                    for x, y, _route_reason, direction, _route_belt in vertical_positions(
                        0.5,
                        corridor_y,
                        merge_y,
                        reason,
                        DIR_NORTH,
                        belt_name,
                    ):
                        specs.append({"x": x, "y": y, "reason": reason, "direction": direction, "name": belt_name})
                    merge_target = dict(target)
                    merge_target["corridor_y"] = corridor_y
                    merge_target["underground_x"] = turn_x
                    route_positions = specs_to_route_positions(specs, belt_name)
                    candidates.append((merge_target, specs, route_positions))
            return candidates

        def blocked_recycle_attempt(
            route_kind: str,
            collisions: list[dict[str, Any]],
            merge_target: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            attempt: dict[str, Any] = {
                "route_kind": route_kind,
                "collision_count": len(collisions),
                "collisions": collisions[:5],
            }
            if merge_target is not None:
                attempt["recycle_merge_target"] = merge_target
            return attempt

        def recycle_corridor_probe(blocked_attempts: list[dict[str, Any]]) -> dict[str, Any] | None:
            if not blocked_attempts:
                return None
            reason_counts: Counter[str] = Counter()
            entity_counts: Counter[str] = Counter()
            direction_conflicts = 0
            duplicate_positions = 0
            for attempt in blocked_attempts:
                for collision in attempt.get("collisions") or []:
                    reason = str(collision.get("reason") or "unknown")
                    reason_tail = reason.rsplit(":", 1)[-1]
                    reason_counts[reason_tail] += 1
                    entity_name = str(collision.get("entity_name") or "")
                    if entity_name:
                        entity_counts[entity_name] += 1
                    if reason_tail in {"existing-belt-not-reusable", "connector-direction-conflict"}:
                        direction_conflicts += 1
                    if reason_tail == "duplicate-route-position":
                        duplicate_positions += 1
            recommendation = "inspect-blocked-recycle-attempts"
            if direction_conflicts:
                recommendation = "reserve-dedicated-recycle-corridor-or-underground-crossing"
            elif duplicate_positions:
                recommendation = "separate-recycle-route-from-current-overflow-lane"
            return {
                "status": "surface-corridor-blocked",
                "attempt_count": len(blocked_attempts),
                "top_collision_reasons": reason_counts.most_common(5),
                "top_collision_entities": entity_counts.most_common(5),
                "direction_conflict_count": direction_conflicts,
                "duplicate_position_count": duplicate_positions,
                "recommendation": recommendation,
            }

        def matching_audits_for_target(target_item: str) -> list[dict[str, Any]]:
            return [
                item
                for item in byproduct_audit
                if str(item.get("target_item") or "") == target_item
            ]

        def add_pre_fanin_separations() -> None:
            nonlocal splitters_added, overflow_belts_added, recycle_belts_added, merge_belts_added
            if not preseparate_output_before_fanin:
                return
            for fanin in output_fanins:
                if fanin.get("status") != "connected":
                    continue
                boundary = str(fanin.get("boundary") or "")
                if not boundary.startswith("output:"):
                    continue
                target_item = boundary.split(":", 1)[1]
                if target_item not in target_items:
                    continue
                matching_audits = matching_audits_for_target(target_item)
                if not matching_audits:
                    continue
                route_positions = [tuple(position) for position in fanin.get("route_positions") or []]
                if len(route_positions) < 2:
                    separations.append(
                        {
                            "boundary": boundary,
                            "scope": "output-fanin",
                            "status": "blocked",
                            "reason": "fanin-route-has-no-removable-segment",
                            "current_handling": "none",
                            "route_y": fanin.get("fanin_y"),
                            "from_instance": fanin.get("from_instance"),
                            "to_instance": fanin.get("to_instance"),
                        }
                    )
                    continue
                port = fanin.get("from_port") or {}
                belt_name = connector_belt_name_for_port(port)
                splitter_name = splitter_name_for_belt_name(belt_name)
                route_y = round(float(fanin.get("fanin_y") or 0.0), 3)
                splitter_x: float | None = None
                for x, y, _reason, direction, route_belt_name in route_positions[1:]:
                    candidate_x = round(float(x), 3)
                    candidate_y = round(float(y), 3)
                    if candidate_y != route_y or direction != DIR_EAST or route_belt_name != belt_name:
                        continue
                    existing = occupied_entities.get((candidate_x, candidate_y))
                    existing_name = str((existing or {}).get("name") or "")
                    if (
                        existing is not None
                        and any(existing is connector for connector in connectors)
                        and existing_name.endswith("transport-belt")
                        and canonical_transport_belt_name(existing_name) == belt_name
                        and existing.get("direction") == DIR_EAST
                    ):
                        splitter_x = candidate_x
                        break
                if splitter_x is None:
                    separations.append(
                        {
                            "boundary": boundary,
                            "scope": "output-fanin",
                            "status": "blocked",
                            "reason": "no-removable-east-connector-belt-before-fanin",
                            "current_handling": "none",
                            "route_y": route_y,
                            "from_instance": fanin.get("from_instance"),
                            "to_instance": fanin.get("to_instance"),
                        }
                    )
                    continue

                route_key = (splitter_x, route_y)
                existing = occupied_entities.get(route_key)
                if existing is None:
                    separations.append(
                        {
                            "boundary": boundary,
                            "scope": "output-fanin",
                            "status": "blocked",
                            "reason": "pre-fanin-splitter-input-missing",
                            "current_handling": "none",
                            "route_y": route_y,
                            "splitter_x": splitter_x,
                            "from_instance": fanin.get("from_instance"),
                            "to_instance": fanin.get("to_instance"),
                        }
                    )
                    continue
                connectors.remove(existing)
                occupied.discard(route_key)
                occupied_entities.pop(route_key, None)

                splitter_y = round(route_y + 0.5, 3)
                splitter_key = (splitter_x, splitter_y)
                if splitter_key in occupied_entities:
                    connectors.append(existing)
                    occupied.add(route_key)
                    occupied_entities[route_key] = existing
                    separations.append(
                        {
                            "boundary": boundary,
                            "scope": "output-fanin",
                            "status": "blocked",
                            "reason": "pre-fanin-splitter-center-position-occupied",
                            "current_handling": "none",
                            "route_y": route_y,
                            "splitter_x": splitter_x,
                            "splitter_y": splitter_y,
                            "from_instance": fanin.get("from_instance"),
                            "to_instance": fanin.get("to_instance"),
                            "entity_name": str(occupied_entities[splitter_key].get("name") or ""),
                        }
                    )
                    continue

                splitter = connector_belt(
                    len(entities) + len(connectors) + 1,
                    splitter_x,
                    splitter_y,
                    direction=DIR_EAST,
                    name=splitter_name,
                )
                splitter["filter"] = {"name": target_item, "quality": "normal", "comparator": "="}
                splitter["output_priority"] = "left"
                connectors.append(splitter)
                occupied.add(splitter_key)
                occupied_entities[splitter_key] = splitter
                splitters_added += 1

                overflow_y = round(route_y + 1.0, 3)
                current_handling = "pre-fanin-finite-overflow-buffer"
                route_kind = "pre-fanin-output-byproduct-filter-splitter-overflow"
                route_collisions: list[dict[str, Any]] = []
                existing_belts_used = 0
                belts_added = 0
                recycle_exit: dict[str, Any] | None = None
                recycle_flow_audit: dict[str, Any] | None = None
                recycle_merge_target: dict[str, Any] | None = None
                blocked_recycle_attempts: list[dict[str, Any]] = []
                recyclable_byproducts = sorted(
                    {
                        str(byproduct)
                        for audit in matching_audits
                        for byproduct in audit.get("recyclable_byproducts") or []
                    }
                )
                recommended_handling = (
                    str(matching_audits[0].get("recommended_handling") or "separate-or-export")
                    if matching_audits
                    else "separate-or-export"
                )
                input_sides = recyclable_input_sides(matching_audits)
                if recommended_handling == "recycle-to-input-boundary" and "left" in input_sides:
                    sideload_candidate = (
                        pre_fanin_input_sideload_candidate(fanin, splitter_x, overflow_y, belt_name, boundary)
                        if experimental_prefanin_input_sideload
                        else None
                    )
                    if sideload_candidate is not None:
                        merge_target, recycle_positions = sideload_candidate
                        (
                            candidate_belts_added,
                            candidate_collisions,
                            candidate_existing_belts_used,
                        ) = add_positions_reusing_existing_belts(
                            recycle_positions,
                            record_collisions=False,
                            reuse_existing_plain_belts_only=True,
                        )
                        if not candidate_collisions:
                            belts_added = candidate_belts_added
                            existing_belts_used = candidate_existing_belts_used
                            recycle_belts_added += candidate_belts_added
                            merge_belts_added += candidate_belts_added
                            current_handling = "pre-fanin-recycle-sideload-to-input-lane"
                            route_kind = "pre-fanin-output-byproduct-filter-splitter-recycle-sideload-input-lane"
                            last = recycle_positions[-1] if recycle_positions else (merge_target["sideload_x"], merge_target["sideload_y"], "", DIR_WEST, belt_name)
                            recycle_exit = {"x": round(float(last[0]), 3), "y": round(float(last[1]), 3), "side": "input-lane"}
                            recycle_merge_target = merge_target
                            recycle_flow_audit = audit_exact_route_positions("pre-fanin-output-byproduct-recycle-sideload-input-lane", recycle_positions)
                        else:
                            blocked_recycle_attempts.append(
                                blocked_recycle_attempt(
                                    "pre-fanin-output-byproduct-filter-splitter-recycle-sideload-input-lane",
                                    candidate_collisions,
                                    merge_target,
                                )
                            )
                    if current_handling != "pre-fanin-recycle-sideload-to-input-lane":
                        for merge_target, recycle_specs, recycle_positions in pre_fanin_underground_corridor_candidates(
                            splitter_x,
                            overflow_y,
                            belt_name,
                            boundary,
                            recyclable_byproducts,
                        ):
                            (
                                candidate_belts_added,
                                candidate_collisions,
                                candidate_existing_belts_used,
                            ) = add_entity_specs_reusing_existing_belts(
                                recycle_specs,
                                record_collisions=False,
                                reuse_existing_plain_belts_only=True,
                            )
                            if not candidate_collisions:
                                belts_added = candidate_belts_added
                                existing_belts_used = candidate_existing_belts_used
                                recycle_belts_added += candidate_belts_added
                                merge_belts_added += candidate_belts_added
                                current_handling = "pre-fanin-recycle-underground-corridor-to-input-boundary"
                                route_kind = "pre-fanin-output-byproduct-filter-splitter-recycle-underground-corridor"
                                last = recycle_positions[-1] if recycle_positions else (left_boundary_x, overflow_y, "", DIR_WEST, belt_name)
                                recycle_exit = {"x": round(float(last[0]), 3), "y": round(float(last[1]), 3), "side": "input-bus"}
                                recycle_merge_target = merge_target
                                recycle_flow_audit = audit_exact_route_positions("pre-fanin-output-byproduct-recycle-underground-corridor", recycle_positions)
                                break
                            blocked_recycle_attempts.append(
                                blocked_recycle_attempt(
                                    "pre-fanin-output-byproduct-filter-splitter-recycle-underground-corridor",
                                    candidate_collisions,
                                    merge_target,
                                )
                            )
                    if current_handling not in {"pre-fanin-recycle-sideload-to-input-lane", "pre-fanin-recycle-underground-corridor-to-input-boundary"}:
                        for merge_target, recycle_positions in recycle_merge_candidates(
                            splitter_x,
                            overflow_y,
                            belt_name,
                            boundary,
                            recyclable_byproducts,
                        ):
                            (
                                candidate_belts_added,
                                candidate_collisions,
                                candidate_existing_belts_used,
                            ) = add_positions_reusing_existing_belts(
                                recycle_positions,
                                record_collisions=False,
                                reuse_existing_plain_belts_only=True,
                            )
                            if not candidate_collisions:
                                belts_added = candidate_belts_added
                                existing_belts_used = candidate_existing_belts_used
                                recycle_belts_added += candidate_belts_added
                                merge_belts_added += candidate_belts_added
                                current_handling = "pre-fanin-recycle-merge-to-input-boundary"
                                route_kind = "pre-fanin-output-byproduct-filter-splitter-recycle-merge"
                                last = recycle_positions[-1] if recycle_positions else (left_boundary_x, overflow_y, "", DIR_WEST, belt_name)
                                recycle_exit = {"x": round(float(last[0]), 3), "y": round(float(last[1]), 3), "side": "input-bus"}
                                recycle_merge_target = merge_target
                                recycle_flow_audit = audit_exact_route_positions("pre-fanin-output-byproduct-recycle-merge", recycle_positions)
                                break
                            blocked_recycle_attempts.append(
                                blocked_recycle_attempt(
                                    "pre-fanin-output-byproduct-filter-splitter-recycle-merge",
                                    candidate_collisions,
                                    merge_target,
                                )
                            )
                    if current_handling not in {"pre-fanin-recycle-sideload-to-input-lane", "pre-fanin-recycle-underground-corridor-to-input-boundary", "pre-fanin-recycle-merge-to-input-boundary"}:
                        for recycle_positions in recycle_return_candidates(splitter_x, overflow_y, belt_name, boundary):
                            candidate_belts_added, candidate_collisions = add_positions_without_reuse(recycle_positions, record_collisions=False)
                            if not candidate_collisions:
                                belts_added = candidate_belts_added
                                recycle_belts_added += candidate_belts_added
                                current_handling = "pre-fanin-recycle-return-to-input-boundary"
                                route_kind = "pre-fanin-output-byproduct-filter-splitter-recycle-return"
                                last = recycle_positions[-1] if recycle_positions else (left_boundary_x, overflow_y, "", DIR_WEST, belt_name)
                                recycle_exit = {"x": round(float(last[0]), 3), "y": round(float(last[1]), 3), "side": "left"}
                                recycle_flow_audit = audit_exact_route_positions("pre-fanin-output-byproduct-recycle-return", recycle_positions)
                                break
                            blocked_recycle_attempts.append(
                                blocked_recycle_attempt(
                                    "pre-fanin-output-byproduct-filter-splitter-recycle-return",
                                    candidate_collisions,
                                )
                            )
                        if current_handling == "pre-fanin-finite-overflow-buffer" and blocked_recycle_attempts:
                            route_collisions = blocked_recycle_attempts[-1]["collisions"]
                if current_handling == "pre-fanin-finite-overflow-buffer":
                    fanin_target_x = float((fanin.get("to_port") or {}).get("x") or splitter_x + 5.0)
                    max_overflow_x = round(min(fanin_target_x - 1.0, splitter_x + 4.0), 3)
                    overflow_positions: list[RoutePosition] = []
                    overflow_x = round(splitter_x + 2.0, 3)
                    while overflow_x <= max_overflow_x:
                        overflow_positions.append(
                            (
                                overflow_x,
                                overflow_y,
                                f"{boundary}:pre-fanin-output-byproduct-overflow",
                                DIR_EAST,
                                belt_name,
                            )
                        )
                        overflow_x = round(overflow_x + 1.0, 3)
                    belts_added, route_collisions, existing_belts_used = add_positions_reusing_existing_belts(overflow_positions)
                    overflow_belts_added += belts_added
                separations.append(
                    {
                        "boundary": boundary,
                        "scope": "output-fanin",
                        "status": "connected" if not route_collisions else "blocked",
                        "target_item": target_item,
                        "splitter_name": splitter_name,
                        "splitter_x": splitter_x,
                        "splitter_y": splitter_y,
                        "recommended_handling": "pre-fanin-separate-before-output-merge",
                        "current_handling": current_handling,
                        "experimental": current_handling == "pre-fanin-recycle-sideload-to-input-lane",
                        "recyclable_byproducts": recyclable_byproducts,
                        "route_y": route_y,
                        "overflow_y": overflow_y,
                        "overflow_belts_added": belts_added if current_handling == "pre-fanin-finite-overflow-buffer" else 0,
                        "recycle_belts_added": belts_added if current_handling == "pre-fanin-recycle-return-to-input-boundary" else 0,
                        "merge_belts_added": belts_added
                        if current_handling in {"pre-fanin-recycle-merge-to-input-boundary", "pre-fanin-recycle-sideload-to-input-lane", "pre-fanin-recycle-underground-corridor-to-input-boundary"}
                        else 0,
                        "recycle_exit": recycle_exit,
                        "recycle_merge_target": recycle_merge_target,
                        "recycle_flow_audit": recycle_flow_audit,
                        "recycle_corridor_probe": recycle_corridor_probe(blocked_recycle_attempts)
                        if current_handling == "pre-fanin-finite-overflow-buffer"
                        else None,
                        "blocked_recycle_attempt_count": len(blocked_recycle_attempts),
                        "blocked_recycle_attempts": blocked_recycle_attempts[:3],
                        "from_instance": fanin.get("from_instance"),
                        "to_instance": fanin.get("to_instance"),
                        "existing_belts_used": existing_belts_used,
                        "collisions": route_collisions,
                        "route_kind": route_kind,
                    }
                )

        add_pre_fanin_separations()

        for route in routes:
            if route.get("status") != "connected":
                continue
            boundary = str(route.get("boundary") or "")
            if not boundary.startswith("output:"):
                continue
            target_item = boundary.split(":", 1)[1]
            if target_item not in target_items:
                continue
            matching_audits = matching_audits_for_target(target_item)
            recommended_handling = (
                str(matching_audits[0].get("recommended_handling") or "separate-or-export")
                if matching_audits
                else "separate-or-export"
            )
            input_sides = recyclable_input_sides(matching_audits)
            recyclable_byproducts = sorted(
                {
                    str(byproduct)
                    for audit in matching_audits
                    for byproduct in audit.get("recyclable_byproducts") or []
                }
            )
            port = route.get("port") or {}
            belt_name = connector_belt_name_for_port(port)
            splitter_name = splitter_name_for_belt_name(belt_name)
            route_y = round(float(port.get("y") or 0.0), 3)
            port_x = round(float(port.get("x") or 0.0), 3)
            min_splitter_x = round(port_x + max(1.0, float(output_separation_min_distance)), 3)
            splitter_x: float | None = None
            probe_x = min_splitter_x
            while right_boundary_x - probe_x - 1.0 >= 1.0:
                route_key = (probe_x, route_y)
                existing = occupied_entities.get(route_key)
                existing_name = str((existing or {}).get("name") or "")
                if (
                    existing is not None
                    and any(existing is connector for connector in connectors)
                    and existing_name.endswith("transport-belt")
                    and canonical_transport_belt_name(existing_name) == belt_name
                    and existing.get("direction") == DIR_EAST
                ):
                    splitter_x = probe_x
                    break
                probe_x = round(probe_x + 1.0, 3)
            if splitter_x is None:
                separations.append(
                    {
                        "boundary": boundary,
                        "status": "blocked",
                        "reason": "no-removable-east-connector-belt-for-separation",
                        "recommended_handling": recommended_handling,
                        "current_handling": "none",
                        "recyclable_byproducts": recyclable_byproducts,
                        "route_y": route_y,
                        "min_splitter_x": min_splitter_x,
                    }
                )
                continue
            available_overflow = int(math.floor(right_boundary_x - splitter_x - 1.0))
            overflow_length = available_overflow
            route_key = (splitter_x, route_y)
            existing = occupied_entities.get(route_key)
            existing_name = str((existing or {}).get("name") or "")
            if (
                existing is None
                or not any(existing is connector for connector in connectors)
                or not existing_name.endswith("transport-belt")
                or canonical_transport_belt_name(existing_name) != belt_name
                or existing.get("direction") != DIR_EAST
            ):
                separations.append(
                    {
                        "boundary": boundary,
                        "status": "blocked",
                        "reason": "splitter-input-position-not-removable-east-connector-belt",
                        "recommended_handling": recommended_handling,
                        "current_handling": "none",
                        "recyclable_byproducts": recyclable_byproducts,
                        "route_y": route_y,
                        "splitter_x": splitter_x,
                        "entity_name": existing_name,
                    }
                )
                continue
            connectors.remove(existing)
            occupied.discard(route_key)
            occupied_entities.pop(route_key, None)

            splitter_y = round(route_y + 0.5, 3)
            splitter_key = (splitter_x, splitter_y)
            if splitter_key in occupied_entities:
                separations.append(
                    {
                        "boundary": boundary,
                        "status": "blocked",
                        "reason": "splitter-center-position-occupied",
                        "recommended_handling": recommended_handling,
                        "current_handling": "none",
                        "recyclable_byproducts": recyclable_byproducts,
                        "route_y": route_y,
                        "splitter_x": splitter_x,
                        "splitter_y": splitter_y,
                        "entity_name": str(occupied_entities[splitter_key].get("name") or ""),
                    }
                )
                continue
            splitter = connector_belt(
                len(entities) + len(connectors) + 1,
                splitter_x,
                splitter_y,
                direction=DIR_EAST,
                name=splitter_name,
            )
            splitter["filter"] = {"name": target_item, "quality": "normal", "comparator": "="}
            splitter["output_priority"] = "left"
            connectors.append(splitter)
            occupied.add(splitter_key)
            occupied_entities[splitter_key] = splitter
            splitters_added += 1

            overflow_y = round(route_y + 1.0, 3)
            route_collisions: list[dict[str, Any]] = []
            existing_belts_used = 0
            belts_added = 0
            current_handling = "finite-overflow-buffer"
            recycle_exit: dict[str, Any] | None = None
            recycle_flow_audit: dict[str, Any] | None = None
            recycle_merge_target: dict[str, Any] | None = None
            blocked_recycle_attempts: list[dict[str, Any]] = []
            if recommended_handling == "recycle-to-input-boundary" and "left" in input_sides:
                for merge_target, recycle_positions in recycle_merge_candidates(
                    splitter_x,
                    overflow_y,
                    belt_name,
                    boundary,
                    recyclable_byproducts,
                ):
                    (
                        candidate_belts_added,
                        candidate_collisions,
                        candidate_existing_belts_used,
                    ) = add_positions_reusing_existing_belts(
                        recycle_positions,
                        record_collisions=False,
                        reuse_existing_plain_belts_only=True,
                    )
                    if not candidate_collisions:
                        belts_added = candidate_belts_added
                        existing_belts_used = candidate_existing_belts_used
                        recycle_belts_added += candidate_belts_added
                        merge_belts_added += candidate_belts_added
                        current_handling = "recycle-merge-to-input-boundary"
                        last = recycle_positions[-1] if recycle_positions else (left_boundary_x, overflow_y, "", DIR_WEST, belt_name)
                        recycle_exit = {"x": round(float(last[0]), 3), "y": round(float(last[1]), 3), "side": "input-bus"}
                        recycle_merge_target = merge_target
                        recycle_flow_audit = audit_exact_route_positions("output-byproduct-recycle-merge", recycle_positions)
                        break
                    blocked_recycle_attempts.append(
                        blocked_recycle_attempt(
                            "output-byproduct-filter-splitter-recycle-merge",
                            candidate_collisions,
                            merge_target,
                        )
                    )
                if current_handling != "recycle-merge-to-input-boundary":
                    for recycle_positions in recycle_return_candidates(splitter_x, overflow_y, belt_name, boundary):
                        candidate_belts_added, candidate_collisions = add_positions_without_reuse(recycle_positions, record_collisions=False)
                        if not candidate_collisions:
                            belts_added = candidate_belts_added
                            recycle_belts_added += candidate_belts_added
                            current_handling = "recycle-return-to-input-boundary"
                            last = recycle_positions[-1] if recycle_positions else (left_boundary_x, overflow_y, "", DIR_WEST, belt_name)
                            recycle_exit = {"x": round(float(last[0]), 3), "y": round(float(last[1]), 3), "side": "left"}
                            recycle_flow_audit = audit_exact_route_positions("output-byproduct-recycle-return", recycle_positions)
                            break
                        blocked_recycle_attempts.append(
                            blocked_recycle_attempt(
                                "output-byproduct-filter-splitter-recycle-return",
                                candidate_collisions,
                            )
                        )
                if current_handling == "finite-overflow-buffer":
                    route_collisions = blocked_recycle_attempts[-1]["collisions"] if blocked_recycle_attempts else []

            if current_handling == "finite-overflow-buffer":
                overflow_positions = [
                    (
                        round(splitter_x + offset, 3),
                        overflow_y,
                        f"{boundary}:output-byproduct-overflow",
                        DIR_EAST,
                        belt_name,
                    )
                    for offset in range(2, overflow_length + 1)
                ]
                belts_added, route_collisions, existing_belts_used = add_positions_reusing_existing_belts(overflow_positions)
                overflow_belts_added += belts_added
            separations.append(
                {
                    "boundary": boundary,
                    "status": "connected" if not route_collisions else "blocked",
                    "target_item": target_item,
                    "splitter_name": splitter_name,
                    "splitter_x": splitter_x,
                    "splitter_y": splitter_y,
                    "recommended_handling": recommended_handling,
                    "current_handling": current_handling,
                    "recyclable_byproducts": recyclable_byproducts,
                    "route_y": route_y,
                    "overflow_y": overflow_y,
                    "overflow_belts_added": belts_added if current_handling == "finite-overflow-buffer" else 0,
                    "recycle_belts_added": belts_added if current_handling == "recycle-return-to-input-boundary" else 0,
                    "merge_belts_added": belts_added if current_handling == "recycle-merge-to-input-boundary" else 0,
                    "recycle_exit": recycle_exit,
                    "recycle_merge_target": recycle_merge_target,
                    "recycle_flow_audit": recycle_flow_audit,
                    "blocked_recycle_attempt_count": len(blocked_recycle_attempts),
                    "blocked_recycle_attempts": blocked_recycle_attempts[:3],
                    "existing_belts_used": existing_belts_used,
                    "collisions": route_collisions,
                    "route_kind": (
                        "output-byproduct-filter-splitter-recycle-merge"
                        if current_handling == "recycle-merge-to-input-boundary"
                        else "output-byproduct-filter-splitter-recycle-return"
                        if current_handling == "recycle-return-to-input-boundary"
                        else "output-byproduct-filter-splitter-overflow"
                    ),
                }
            )
        return splitters_added, overflow_belts_added, recycle_belts_added, merge_belts_added, separations

    pending_byproduct_audit = build_output_byproduct_audit()
    (
        output_separation_splitters,
        output_separation_overflow_belts,
        output_separation_recycle_belts,
        output_separation_merge_belts,
        output_separations,
    ) = add_output_byproduct_separation(pending_byproduct_audit)

    def add_output_boundary_compressor() -> list[dict[str, Any]]:
        target_rate_basis = layout_plan.get("target_rate_basis") or {}
        if not compress_output_boundary or target_rate_basis.get("kind") != "full-belt":
            return []
        expected_belt_count = int(target_rate_basis.get("belt_count") or 0)
        expected_belt_name = str(target_rate_basis.get("belt_name") or "")
        target_item = str(layout_plan.get("target_item") or "")
        boundary = f"output:{target_item}"
        if expected_belt_count != 2 or not expected_belt_name:
            return []

        selected_routes = [
            route
            for route in routes
            if route.get("status") == "connected"
            and str(route.get("boundary") or "") == boundary
            and route.get("port")
            and connector_belt_name_for_port(route.get("port") or {}) == expected_belt_name
        ]
        selected_routes = sorted(selected_routes, key=lambda route: round(float((route.get("port") or {}).get("y") or 0.0), 3))
        if len(selected_routes) != 3:
            return []

        right_boundary_x = round(float(layout_plan["estimated_width"]) - 0.5, 3)
        middle_y = round(float((selected_routes[1].get("port") or {}).get("y") or 0.0), 3)
        origin_x = round(right_boundary_x + 7.0, 3)
        origin_y = round(middle_y - 2.0, 3)
        input_ys = [round(origin_y + offset, 3) for offset in (1.0, 2.0, 3.0)]
        output_ys = [round(origin_y + offset, 3) for offset in (2.0, 3.0)]
        input_x = origin_x
        output_x = round(origin_x + 7.0, 3)
        final_x = round(output_x + 6.0, 3)
        turn_x = round(right_boundary_x + 3.0, 3)

        transport_name = expected_belt_name
        splitter_name = splitter_name_for_belt_name(transport_name)
        underground_name = transport_name.replace("transport-belt", "underground-belt")
        template_entities = [
            (2.0, 0.0, transport_name, DIR_SOUTH, None, None),
            (3.0, 0.0, transport_name, DIR_WEST, None, None),
            (4.0, 0.0, transport_name, DIR_WEST, None, None),
            (5.0, 0.0, transport_name, DIR_WEST, None, None),
            (6.0, 0.0, transport_name, DIR_WEST, None, None),
            (0.0, 1.0, transport_name, DIR_EAST, None, None),
            (1.0, 1.0, underground_name, DIR_EAST, "input", None),
            (2.0, 1.0, transport_name, DIR_EAST, None, None),
            (4.0, 1.0, underground_name, DIR_EAST, "output", None),
            (6.0, 1.0, transport_name, DIR_NORTH, None, None),
            (3.0, 1.5, splitter_name, DIR_EAST, None, None),
            (5.0, 1.5, splitter_name, DIR_EAST, None, "right"),
            (0.0, 2.0, transport_name, DIR_EAST, None, None),
            (1.0, 2.0, transport_name, DIR_EAST, None, None),
            (4.0, 2.0, transport_name, DIR_EAST, None, None),
            (7.0, 2.0, transport_name, DIR_EAST, None, None),
            (2.0, 2.5, splitter_name, DIR_EAST, None, "right"),
            (6.0, 2.5, splitter_name, DIR_EAST, None, None),
            (0.0, 3.0, transport_name, DIR_EAST, None, None),
            (1.0, 3.0, transport_name, DIR_EAST, None, None),
            (3.0, 3.0, transport_name, DIR_EAST, None, None),
            (4.0, 3.0, transport_name, DIR_EAST, None, None),
            (5.0, 3.0, transport_name, DIR_EAST, None, None),
            (7.0, 3.0, transport_name, DIR_EAST, None, None),
        ]

        proposed_entities: list[dict[str, Any]] = []
        proposed_positions: set[tuple[float, float]] = set()
        route_records: list[dict[str, Any]] = []

        def compressor_route_positions(route: dict[str, Any], target_y: float) -> list[RoutePosition]:
            port = route.get("port") or {}
            source_y = round(float(port.get("y") or 0.0), 3)
            positions: list[RoutePosition] = []
            if source_y == target_y:
                positions.extend(directional_horizontal_positions(round(right_boundary_x + 1.0, 3), round(input_x - 1.0, 3), source_y, f"{boundary}:compressor-input", DIR_EAST, transport_name))
                return positions
            positions.extend(directional_horizontal_positions(round(right_boundary_x + 1.0, 3), round(turn_x - 1.0, 3), source_y, f"{boundary}:compressor-input", DIR_EAST, transport_name))
            vertical_direction = DIR_SOUTH if target_y > source_y else DIR_NORTH
            positions.extend(vertical_positions(turn_x, source_y, target_y, f"{boundary}:compressor-input", vertical_direction, transport_name))
            positions.extend(directional_horizontal_positions(round(turn_x + 1.0, 3), round(input_x - 1.0, 3), target_y, f"{boundary}:compressor-input", DIR_EAST, transport_name))
            return positions

        for route, target_y in zip(selected_routes, input_ys, strict=True):
            positions = compressor_route_positions(route, target_y)
            route_records.append(
                {
                    "route": route,
                    "target_y": target_y,
                    "positions": positions,
                }
            )
            for x, y, _reason, _direction, _belt_name in visible_route_positions(positions):
                key = (round(float(x), 3), round(float(y), 3))
                if key in proposed_positions:
                    return [
                        {
                            "status": "blocked",
                            "reason": "duplicate-compressor-input-route-position",
                            "x": key[0],
                            "y": key[1],
                        }
                    ]
                proposed_positions.add(key)

        for rel_x, rel_y, name, direction, entity_type, output_priority in template_entities:
            entity = connector_belt(
                len(entities) + len(connectors) + len(proposed_entities) + 1,
                round(origin_x + rel_x, 3),
                round(origin_y + rel_y, 3),
                direction=direction,
                name=name,
            )
            if entity_type:
                entity["type"] = entity_type
            if output_priority:
                entity["output_priority"] = output_priority
            key = entity_position_key(entity)
            if key in proposed_positions:
                return [{"status": "blocked", "reason": "compressor-template-overlaps-input-route", "x": key[0], "y": key[1], "entity_name": name}]
            proposed_entities.append(entity)
            proposed_positions.add(key)

        output_positions: list[RoutePosition] = []
        for output_y in output_ys:
            output_positions.extend(
                directional_horizontal_positions(round(output_x + 1.0, 3), final_x, output_y, f"{boundary}:compressor-output", DIR_EAST, transport_name)
            )

        all_positions = [position for record in route_records for position in record["positions"]]
        all_positions.extend(output_positions)
        _added, route_collisions, _existing = add_positions_reusing_existing_belts(all_positions, record_collisions=False)
        entity_collisions: list[dict[str, Any]] = []
        if not route_collisions:
            for proposed in proposed_entities:
                key = entity_position_key(proposed)
                if key in occupied_entities:
                    entity_collisions.append({"x": key[0], "y": key[1], "reason": "compressor-template-collision", "entity_name": str(occupied_entities[key].get("name") or "")})
                    continue
                connectors.append(proposed)
                occupied.add(key)
                occupied_entities[key] = proposed

        if route_collisions or entity_collisions:
            collisions.extend(route_collisions + entity_collisions)
            return [
                {
                    "boundary": boundary,
                    "status": "blocked",
                    "reason": "compressor-collision",
                    "route_collisions": route_collisions,
                    "entity_collisions": entity_collisions,
                }
            ]

        for route_record in route_records:
            route = route_record["route"]
            route["boundary_role"] = "internal-output"
            route["compressor_input_y"] = route_record["target_y"]

        node_fingerprint = str(((selected_routes[0].get("port") or {}).get("node_fingerprint")) or "")
        for index, output_y in enumerate(output_ys):
            output_route_positions = directional_horizontal_positions(output_x, final_x, output_y, f"{boundary}:compressor-output-boundary", DIR_EAST, transport_name)
            routes.append(
                {
                    "boundary": boundary,
                    "boundary_role": "external-output",
                    "status": "connected",
                    "belts_added": len(output_route_positions),
                    "collisions": [],
                    "port": {
                        "node_item": target_item,
                        "node_recipe": "output-boundary-compressor",
                        "node_fingerprint": node_fingerprint,
                        "node_instance": index,
                        "side": "right",
                        "role": "boundary-compressor-output",
                        "entity_name": transport_name,
                        "entity_type": None,
                        "direction": DIR_EAST,
                        "source": "output-boundary-compressor",
                        "x": output_x,
                        "y": output_y,
                    },
                    "route_kind": "output-boundary-compressor-output",
                    "capacity_proof": "runtime-unproven-compressor",
                    "capacity_proof_reason": "generic-3-to-2-compressor-collapsed-three-internal-lanes-to-about-one-turbo-belt-in-runtime-probe",
                    "route_positions": output_route_positions,
                }
            )

        return [
            {
                "boundary": boundary,
                "status": "connected",
                "strategy": "corpus-3-to-2-throughput-balancer",
                "source": "raynquist-fall-2024-3_2_tu_balancer-rotated",
                "runtime_status": "known-insufficient",
                "runtime_evidence": "right-boundary windows stabilized near 3540-3600/min; probe x=111.5 showed the generic compressor entry already collapsed to one turbo belt",
                "capacity_proof": "unresolved",
                "input_route_ys": [round(float((route.get("port") or {}).get("y") or 0.0), 3) for route in selected_routes],
                "compressor_input_ys": input_ys,
                "compressor_output_ys": output_ys,
                "expected_belt_name": expected_belt_name,
                "internal_route_count": len(selected_routes),
                "external_route_count": expected_belt_count,
                "origin_x": origin_x,
                "origin_y": origin_y,
                "output_x": output_x,
                "final_x": final_x,
            }
        ]

    output_boundary_compressors = add_output_boundary_compressor()

    def route_boundary_rate(route: dict[str, Any]) -> float | None:
        return boundary_required_rate(str(route.get("boundary") or ""))

    def routes_for_boundary_audit(boundary: str) -> list[dict[str, Any]]:
        connected_routes = [
            route
            for route in routes
            if route.get("status") == "connected"
            and str(route.get("boundary") or "") == boundary
            and route.get("port")
        ]
        external_routes = [
            route
            for route in connected_routes
            if route.get("boundary_role") == "external-output"
        ]
        if external_routes:
            return external_routes
        return [
            route
            for route in connected_routes
            if route.get("boundary_role") != "internal-output"
        ]

    def routes_for_production_audit(boundary: str) -> list[dict[str, Any]]:
        connected_routes = [
            route
            for route in routes
            if route.get("status") == "connected"
            and str(route.get("boundary") or "") == boundary
            and route.get("port")
        ]
        internal_routes = [
            route
            for route in connected_routes
            if route.get("boundary_role") == "internal-output"
        ]
        if internal_routes:
            return internal_routes
        return [
            route
            for route in connected_routes
            if route.get("boundary_role") != "external-output"
        ]

    def target_output_splitter_for_route(x: float, y: float, boundary: str | None) -> dict[str, Any] | None:
        if not boundary or not boundary.startswith("output:"):
            return None
        target_item = boundary.split(":", 1)[1]
        entity = occupied_entities.get((round(float(x), 3), round(float(y) + 0.5, 3)))
        if entity is None:
            return None
        entity_name = str(entity.get("name") or "")
        splitter_filter = entity.get("filter") or {}
        if (
            entity_name.endswith("splitter")
            and entity.get("direction") == DIR_EAST
            and splitter_filter.get("name") == target_item
            and entity.get("output_priority") == "left"
        ):
            return entity
        return None

    def boundary_capacity_audit(flow_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if knowledge is None:
            return []
        flow_status_by_route = {
            (
                str(item.get("boundary") or ""),
                str(item.get("node_fingerprint") or ""),
                int(item.get("from_instance") or 0),
                round(float(item.get("y") or 0.0), 3),
            ): str(item.get("status") or "unknown")
            for item in flow_audit
            if item.get("segment_type") == "boundary-route"
        }
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for boundary in sorted({str(route.get("boundary") or "") for route in routes if route.get("status") == "connected" and route.get("port")}):
            for route in routes_for_boundary_audit(boundary):
                port = route["port"]
                fingerprint = str(port.get("node_fingerprint") or "")
                instance = int(port.get("node_instance") or 0)
                route_y = round(float(port.get("y") or 0.0), 3)
                flow_status = flow_status_by_route.get((boundary, fingerprint, instance, route_y), "unknown")
                flow_reason = None
                if (
                    route.get("route_kind") == "output-boundary-compressor-output"
                    and route.get("capacity_proof") != "proven"
                ):
                    flow_status = "unresolved"
                    flow_reason = str(route.get("capacity_proof_reason") or "compressor-runtime-capacity-unproven")
                belt_name = connector_belt_name_for_port(port)
                belt = knowledge.belt(belt_name)
                key = (boundary, fingerprint)
                item = grouped.setdefault(
                    key,
                    {
                        "boundary": boundary,
                        "node_fingerprint": fingerprint,
                        "status": "unknown",
                        "route_count": 0,
                        "belt_capacities": [],
                        "capacity_per_minute": 0.0,
                        "proven_capacity_per_minute": 0.0,
                        "unresolved_capacity_per_minute": 0.0,
                        "failed_capacity_per_minute": 0.0,
                    },
                )
                item["route_count"] += 1
                if belt is None:
                    item["belt_capacities"].append(
                        {
                            "belt_name": belt_name,
                            "flow_status": flow_status,
                            "capacity_per_minute": None,
                            "reason": "unknown-belt-prototype",
                        }
                    )
                    continue
                capacity = float(belt.items_per_minute)
                item["capacity_per_minute"] += capacity
                if flow_status == "pass":
                    item["proven_capacity_per_minute"] += capacity
                elif flow_status == "failed":
                    item["failed_capacity_per_minute"] += capacity
                else:
                    item["unresolved_capacity_per_minute"] += capacity
                item["belt_capacities"].append(
                    {
                        "belt_name": belt_name,
                        "flow_status": flow_status,
                        "capacity_per_minute": capacity,
                        **({"flow_reason": flow_reason} if flow_reason else {}),
                    }
                )
                required_rate = route_boundary_rate(route)
                if required_rate is not None:
                    item["required_rate_per_minute"] = required_rate

        audits = list(grouped.values())
        for item in audits:
            if any(capacity.get("capacity_per_minute") is None for capacity in item["belt_capacities"]):
                item["status"] = "unknown"
                continue
            required_rate = item.get("required_rate_per_minute")
            if required_rate is None:
                item["status"] = "unknown"
                continue
            item["structural_meets_required_rate"] = float(item["capacity_per_minute"]) >= float(required_rate)
            item["meets_required_rate"] = float(item["proven_capacity_per_minute"]) >= float(required_rate)
            if item["meets_required_rate"]:
                item["status"] = "sufficient"
            elif not item["structural_meets_required_rate"]:
                item["status"] = "insufficient"
            elif item["failed_capacity_per_minute"]:
                item["status"] = "failed"
            else:
                item["status"] = "unresolved"
        return audits

    def boundary_contract_audit() -> list[dict[str, Any]]:
        target_rate_basis = layout_plan.get("target_rate_basis") or {}
        if target_rate_basis.get("kind") != "full-belt":
            return []
        target_item = str(layout_plan.get("target_item") or "")
        expected_boundary = f"output:{target_item}"
        expected_belt_count = int(target_rate_basis.get("belt_count") or 0)
        expected_belt_name = str(target_rate_basis.get("belt_name") or "")
        if expected_belt_count <= 0 or not expected_belt_name:
            return []

        connected_routes = routes_for_boundary_audit(expected_boundary)
        belt_names = [connector_belt_name_for_port(route["port"]) for route in connected_routes]
        route_ys = sorted({round(float((route.get("port") or {}).get("y") or 0.0), 3) for route in connected_routes})
        wrong_belts = sorted({name for name in belt_names if name != expected_belt_name})
        route_count = len(connected_routes)
        if wrong_belts:
            status = "wrong-belt"
        elif route_count < expected_belt_count:
            status = "under-provisioned"
        elif route_count > expected_belt_count:
            status = "over-provisioned"
        else:
            status = "exact"
        return [
            {
                "boundary": expected_boundary,
                "status": status,
                "expected_belt_name": expected_belt_name,
                "expected_belt_count": expected_belt_count,
                "route_count": route_count,
                "route_ys": route_ys,
                "wrong_belts": wrong_belts,
            }
        ]

    def output_byproduct_audit() -> list[dict[str, Any]]:
        return pending_byproduct_audit

    def bridge_edges_for_node(fingerprint: str, y: float) -> list[tuple[int, int]]:
        edges: list[tuple[int, int]] = []
        for bridge in bridges:
            if bridge.get("status") != "connected":
                continue
            if str(bridge.get("node_fingerprint") or "") != fingerprint:
                continue
            if round(float(bridge.get("bridge_y") or 0.0), 3) != round(y, 3):
                continue
            edges.append((int(bridge["from_instance"]), int(bridge["to_instance"])))
        for fanout in input_fanouts:
            if fanout.get("status") != "connected":
                continue
            if str(fanout.get("node_fingerprint") or "") != fingerprint:
                continue
            if round(float(fanout.get("fanout_y") or 0.0), 3) != round(y, 3):
                continue
            edges.append((int(fanout["from_instance"]), int(fanout["to_instance"])))
        for fanin in output_fanins:
            if fanin.get("status") != "connected":
                continue
            if str(fanin.get("node_fingerprint") or "") != fingerprint:
                continue
            if round(float(fanin.get("fanin_y") or 0.0), 3) != round(y, 3):
                continue
            edges.append((int(fanin["from_instance"]), int(fanin["to_instance"])))
        return edges

    def horizontal_span_positions(start_x: float, end_x: float, y: float) -> list[tuple[float, float]]:
        positions: list[tuple[float, float]] = []
        x = min(start_x, end_x)
        last_x = max(start_x, end_x)
        while x <= last_x:
            positions.append((round(x, 3), round(y, 3)))
            x += 1.0
        return positions

    def audit_horizontal_belt_flow(
        *,
        segment_type: str,
        boundary: str | None = None,
        node_fingerprint: str | None = None,
        from_instance: int | None = None,
        to_instance: int | None = None,
        start_x: float,
        end_x: float,
        y: float,
        belt_name: str,
    ) -> dict[str, Any]:
        unresolved: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        underground_pairs: list[dict[str, Any]] = []
        positions = horizontal_span_positions(start_x, end_x, y)
        last_index = len(positions) - 1

        def find_underground_output_pair(start_index: int, entity_name: str) -> int | None:
            def within_distance(input_x: float, output_x: float) -> bool:
                if knowledge is None:
                    return True
                belt = knowledge.belt(entity_name)
                if belt is None or belt.max_underground_distance is None:
                    return True
                return abs(output_x - input_x) <= belt.max_underground_distance + 1

            input_x, _input_y = positions[start_index]
            for pair_index in range(start_index + 1, len(positions)):
                pair_x, pair_y = positions[pair_index]
                pair_entity = occupied_entities.get((pair_x, pair_y))
                if pair_entity is None:
                    continue
                if str(pair_entity.get("name") or "") != entity_name:
                    continue
                if pair_entity.get("direction") != DIR_EAST:
                    continue
                if pair_entity.get("type") == "output" and within_distance(input_x, pair_x):
                    return pair_index
            return None

        index = 0
        while index < len(positions):
            x, belt_y = positions[index]
            entity = occupied_entities.get((x, belt_y))
            if entity is None:
                if target_output_splitter_for_route(x, belt_y, boundary) is not None:
                    index += 1
                    continue
                failures.append({"x": x, "y": belt_y, "reason": "missing-belt"})
                index += 1
                continue
            entity_name = str(entity.get("name") or "")
            if not is_belt_like_entity_name(entity_name):
                failures.append({"x": x, "y": belt_y, "entity_name": entity_name, "reason": "non-belt-entity"})
                index += 1
                continue
            if canonical_transport_belt_name(entity_name) != belt_name:
                failures.append({"x": x, "y": belt_y, "entity_name": entity_name, "reason": "belt-tier-mismatch"})
                index += 1
                continue
            direction = entity.get("direction")
            if direction != DIR_EAST:
                failures.append(
                    {
                        "x": x,
                        "y": belt_y,
                        "entity_name": entity_name,
                        "direction": direction,
                        "reason": "wrong-flow-direction",
                    }
                )
                index += 1
                continue
            if entity_name.endswith("splitter"):
                target_item = boundary.split(":", 1)[1] if boundary and boundary.startswith("output:") else ""
                splitter_filter = entity.get("filter") or {}
                if target_item and splitter_filter.get("name") == target_item and entity.get("output_priority") == "left":
                    index += 1
                    continue
                unresolved.append({"x": x, "y": belt_y, "entity_name": entity_name, "reason": "splitter-semantics"})
                index += 1
                continue
            if entity_name.endswith("underground-belt"):
                underground_type = entity.get("type")
                if underground_type == "output" and index == 0:
                    index += 1
                    continue
                if underground_type == "input" and index == last_index:
                    index += 1
                    continue
                if underground_type == "input":
                    pair_index = find_underground_output_pair(index, entity_name)
                    if pair_index is not None:
                        pair_x, pair_y = positions[pair_index]
                        underground_pairs.append(
                            {
                                "input_x": x,
                                "input_y": belt_y,
                                "output_x": pair_x,
                                "output_y": pair_y,
                                "entity_name": entity_name,
                                "hidden_positions": max(0, pair_index - index - 1),
                            }
                        )
                        index = pair_index + 1
                        continue
                unresolved.append(
                    {
                        "x": x,
                        "y": belt_y,
                        "entity_name": entity_name,
                        "type": underground_type,
                        "position_in_segment": "start" if index == 0 else "end" if index == last_index else "middle",
                        "reason": "underground-belt-endpoint-not-proven",
                    }
                )
                index += 1
                continue
            index += 1
        status = "failed" if failures else "unresolved" if unresolved else "pass"
        result: dict[str, Any] = {
            "segment_type": segment_type,
            "status": status,
            "belt_name": belt_name,
            "start_x": round(start_x, 3),
            "end_x": round(end_x, 3),
            "y": round(y, 3),
            "positions_checked": len(positions),
            "underground_pairs": underground_pairs,
            "unresolved": unresolved,
            "failures": failures,
        }
        if boundary is not None:
            result["boundary"] = boundary
        if node_fingerprint is not None:
            result["node_fingerprint"] = node_fingerprint
        if from_instance is not None:
            result["from_instance"] = from_instance
        if to_instance is not None:
            result["to_instance"] = to_instance
        return result

    def audit_position_belt_flow(
        *,
        segment_type: str,
        route: dict[str, Any],
        positions: list[RoutePosition],
    ) -> dict[str, Any]:
        unresolved: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for x, belt_y, _reason, direction, belt_name in positions:
            key = (round(float(x), 3), round(float(belt_y), 3))
            entity = occupied_entities.get(key)
            if entity is None:
                if target_output_splitter_for_route(key[0], key[1], str(route.get("boundary") or "")) is not None:
                    continue
                failures.append({"x": key[0], "y": key[1], "reason": "missing-belt"})
                continue
            entity_name = str(entity.get("name") or "")
            if not is_belt_like_entity_name(entity_name):
                failures.append({"x": key[0], "y": key[1], "entity_name": entity_name, "reason": "non-belt-entity"})
                continue
            if canonical_transport_belt_name(entity_name) != belt_name:
                failures.append({"x": key[0], "y": key[1], "entity_name": entity_name, "reason": "belt-tier-mismatch"})
                continue
            if entity.get("direction") != direction:
                failures.append(
                    {
                        "x": key[0],
                        "y": key[1],
                        "entity_name": entity_name,
                        "direction": entity.get("direction"),
                        "expected_direction": direction,
                        "reason": "wrong-flow-direction",
                    }
                )
                continue
            if entity_name.endswith("splitter"):
                boundary = str(route.get("boundary") or "")
                target_item = boundary.split(":", 1)[1] if boundary.startswith("output:") else ""
                splitter_filter = entity.get("filter") or {}
                if target_item and splitter_filter.get("name") == target_item and entity.get("output_priority") == "left":
                    continue
                unresolved.append({"x": key[0], "y": key[1], "entity_name": entity_name, "reason": "splitter-semantics"})
        status = "failed" if failures else "unresolved" if unresolved else "pass"
        port = route.get("port") or {}
        if not port:
            port = route.get("from_port") or route.get("to_port") or {}
        first = positions[0] if positions else (0.0, 0.0, "", DIR_EAST, "transport-belt")
        last = positions[-1] if positions else first
        belt_names = [str(position[4]) for position in positions]
        unique_belt_names = sorted(set(belt_names))
        return {
            "segment_type": segment_type,
            "status": status,
            "boundary": route.get("boundary"),
            "node_fingerprint": str(port.get("node_fingerprint") or ""),
            "from_instance": int(port.get("node_instance") or 0),
            "belt_name": unique_belt_names[0] if len(unique_belt_names) == 1 else "mixed:" + ",".join(unique_belt_names),
            "route_kind": route.get("route_kind"),
            "start_x": round(float(first[0]), 3),
            "end_x": round(float(last[0]), 3),
            "y": round(float(port.get("y") or first[1]), 3),
            "positions_checked": len(positions),
            "unresolved": unresolved,
            "failures": failures,
        }

    def belt_flow_audit() -> list[dict[str, Any]]:
        audit: list[dict[str, Any]] = []
        for route in routes:
            if route.get("status") != "connected" or not route.get("port"):
                continue
            port = route["port"]
            boundary = str(route.get("boundary") or "")
            belt_name = connector_belt_name_for_port(port)
            if route.get("route_positions"):
                audit.append(
                    audit_position_belt_flow(
                        segment_type="boundary-route",
                        route=route,
                        positions=[tuple(position) for position in route["route_positions"]],
                    )
                )
                continue
            if boundary.startswith("input:"):
                start_x = 0.5
                end_x = float(port["x"])
            elif boundary.startswith("output:"):
                start_x = float(port["x"])
                end_x = float(layout_plan["estimated_width"]) - 0.5
            else:
                continue
            audit.append(
                audit_horizontal_belt_flow(
                    segment_type="boundary-route",
                    boundary=boundary,
                    node_fingerprint=str(port.get("node_fingerprint") or ""),
                    from_instance=int(port.get("node_instance") or 0),
                    start_x=start_x,
                    end_x=end_x,
                    y=float(port["y"]),
                    belt_name=belt_name,
                )
            )
        for bridge in bridges:
            if bridge.get("status") != "connected" or not bridge.get("from_port") or not bridge.get("to_port"):
                continue
            from_port = bridge["from_port"]
            to_port = bridge["to_port"]
            audit.append(
                audit_horizontal_belt_flow(
                    segment_type="inter-instance-bridge",
                    node_fingerprint=str(bridge.get("node_fingerprint") or ""),
                    from_instance=int(bridge["from_instance"]),
                    to_instance=int(bridge["to_instance"]),
                    start_x=float(from_port["x"]),
                    end_x=float(to_port["x"]),
                    y=float(bridge.get("bridge_y") or from_port["y"]),
                    belt_name=connector_belt_name_for_port(from_port),
                )
            )
        for fanout in input_fanouts:
            if fanout.get("status") != "connected" or not fanout.get("from_port") or not fanout.get("to_port"):
                continue
            from_port = fanout["from_port"]
            to_port = fanout["to_port"]
            audit.append(
                audit_horizontal_belt_flow(
                    segment_type="input-fanout",
                    boundary=str(fanout.get("boundary") or ""),
                    node_fingerprint=str(fanout.get("node_fingerprint") or ""),
                    from_instance=int(fanout["from_instance"]),
                    to_instance=int(fanout["to_instance"]),
                    start_x=float(from_port["x"]),
                    end_x=float(to_port["x"]),
                    y=float(fanout.get("fanout_y") or from_port["y"]),
                    belt_name=connector_belt_name_for_port(from_port),
                )
            )
        for fanin in output_fanins:
            if fanin.get("status") != "connected" or not fanin.get("from_port") or not fanin.get("to_port"):
                continue
            if fanin.get("route_positions"):
                audit.append(
                    audit_position_belt_flow(
                        segment_type="output-fanin",
                        route=fanin,
                        positions=[tuple(position) for position in fanin["route_positions"]],
                    )
                )
                continue
            from_port = fanin["from_port"]
            to_port = fanin["to_port"]
            audit.append(
                audit_horizontal_belt_flow(
                    segment_type="output-fanin",
                    boundary=str(fanin.get("boundary") or ""),
                    node_fingerprint=str(fanin.get("node_fingerprint") or ""),
                    from_instance=int(fanin["from_instance"]),
                    to_instance=int(fanin["to_instance"]),
                    start_x=float(from_port["x"]),
                    end_x=float(to_port["x"]),
                    y=float(fanin.get("fanin_y") or from_port["y"]),
                    belt_name=connector_belt_name_for_port(from_port),
                )
            )
        return audit

    def reachable_instances(start: int, edges: list[tuple[int, int]], *, direction: str) -> list[int]:
        adjacency: dict[int, set[int]] = {}
        for from_instance, to_instance in edges:
            if direction == "forward":
                adjacency.setdefault(from_instance, set()).add(to_instance)
            else:
                adjacency.setdefault(to_instance, set()).add(from_instance)
        seen = {start}
        frontier = [start]
        while frontier:
            current = frontier.pop()
            for next_instance in adjacency.get(current, set()):
                if next_instance in seen:
                    continue
                seen.add(next_instance)
                frontier.append(next_instance)
        return sorted(seen)

    def boundary_coverage() -> list[dict[str, Any]]:
        node_index = {
            str(node.get("fingerprint")): node
            for node in layout_plan.get("nodes") or []
            if node.get("fingerprint") is not None
        }
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        uncovered: list[dict[str, Any]] = []
        coverage_routes: list[dict[str, Any]] = []
        for boundary in sorted({str(route.get("boundary") or "") for route in routes if route.get("boundary")}):
            coverage_routes.extend(routes_for_production_audit(boundary))
        coverage_route_ids = {id(route) for route in coverage_routes}
        for route in routes:
            if id(route) in coverage_route_ids or route.get("boundary_role") == "external-output":
                continue
            if route.get("status") == "connected":
                continue
            uncovered.append(
                {
                    "boundary": route.get("boundary"),
                    "status": "uncovered",
                    "reason": "route-not-connected-or-node-missing",
                }
            )
        for route in coverage_routes:
            port = route.get("port") or {}
            fingerprint = str(port.get("node_fingerprint") or "")
            node = node_index.get(fingerprint)
            if not node:
                uncovered.append(
                    {
                        "boundary": route.get("boundary"),
                        "status": "uncovered",
                        "reason": "route-not-connected-or-node-missing",
                    }
                )
                continue
            start_instance = int(port.get("node_instance") or 0)
            route_y = round(float(port.get("y") or 0.0), 3)
            boundary = str(route.get("boundary") or "")
            direction = "reverse" if boundary.startswith("output:") else "forward"
            instances = max(1, int(node.get("instances") or 1))
            covered_instances = reachable_instances(
                start_instance,
                bridge_edges_for_node(fingerprint, route_y),
                direction=direction,
            )
            key = (boundary, fingerprint)
            item = grouped.setdefault(
                key,
                {
                    "boundary": route.get("boundary"),
                    "status": "partial",
                    "direction": direction,
                    "route_ys": [],
                    "node_item": node.get("item"),
                    "node_recipe": node.get("recipe"),
                    "node_fingerprint": fingerprint,
                    "start_instances": [],
                    "covered_instances": [],
                    "covered_instance_count": 0,
                    "total_instances": instances,
                    "route_count": 0,
                },
            )
            item["route_count"] += 1
            item["route_ys"].append(route_y)
            item["start_instances"].append(start_instance)
            item["covered_instances"] = sorted(set(item["covered_instances"]) | set(covered_instances))
            item["covered_instance_count"] = len(item["covered_instances"])
            required_rate = route_boundary_rate(route)
            if required_rate is not None:
                item["required_rate_per_minute"] = required_rate
            if boundary.startswith("output:"):
                planned_net = float(node.get("planned_net_output_per_minute") or 0.0)
                per_instance = planned_net / instances if instances else 0.0
                covered_rate = per_instance * len(item["covered_instances"])
                item["covered_rate_per_minute"] = covered_rate
                item["per_instance_net_output_per_minute"] = per_instance
                if required_rate is not None:
                    item["meets_required_rate"] = covered_rate >= required_rate
        coverage = list(grouped.values())
        for item in coverage:
            item["route_ys"] = sorted(set(item["route_ys"]))
            item["start_instances"] = sorted(set(item["start_instances"]))
            item["status"] = "covered" if item["covered_instance_count"] >= item["total_instances"] else "partial"
            if item["boundary"].startswith("output:") and item.get("required_rate_per_minute") is not None:
                item["meets_required_rate"] = item.get("covered_rate_per_minute", 0.0) >= item["required_rate_per_minute"]
        covered_boundaries = {item["boundary"] for item in coverage}
        coverage.extend(item for item in uncovered if item["boundary"] not in covered_boundaries)
        return coverage

    def output_lane_load_audit() -> list[dict[str, Any]]:
        if knowledge is None:
            return []
        node_index = {
            str(node.get("fingerprint")): node
            for node in layout_plan.get("nodes") or []
            if node.get("fingerprint") is not None
        }
        audits: list[dict[str, Any]] = []
        load_routes: list[dict[str, Any]] = []
        for boundary in sorted({str(route.get("boundary") or "") for route in routes if str(route.get("boundary") or "").startswith("output:")}):
            load_routes.extend(routes_for_production_audit(boundary))
        for route in load_routes:
            boundary = str(route.get("boundary") or "")
            if not boundary.startswith("output:"):
                continue
            port = route["port"]
            fingerprint = str(port.get("node_fingerprint") or "")
            node = node_index.get(fingerprint)
            if node is None:
                continue
            belt_name = connector_belt_name_for_port(port)
            belt = knowledge.belt(belt_name)
            if belt is None:
                continue
            instances = max(1, int(node.get("instances") or 1))
            planned_net = float(node.get("planned_net_output_per_minute") or 0.0)
            per_instance = planned_net / instances if instances else 0.0
            start_instance = int(port.get("node_instance") or 0)
            route_y = round(float(port.get("y") or 0.0), 3)
            covered_instances = reachable_instances(
                start_instance,
                bridge_edges_for_node(fingerprint, route_y),
                direction="reverse",
            )
            load_rate = per_instance * len(covered_instances)
            capacity = float(belt.items_per_minute)
            audits.append(
                {
                    "boundary": boundary,
                    "status": "overloaded" if load_rate > capacity else "sufficient",
                    "node_item": node.get("item"),
                    "node_recipe": node.get("recipe"),
                    "node_fingerprint": fingerprint,
                    "route_y": route_y,
                    "route_kind": route.get("route_kind"),
                    "start_instance": start_instance,
                    "covered_instances": covered_instances,
                    "covered_instance_count": len(covered_instances),
                    "per_instance_net_output_per_minute": per_instance,
                    "load_rate_per_minute": load_rate,
                    "belt_name": belt_name,
                    "lane_capacity_per_minute": capacity,
                    "overload_per_minute": max(0.0, load_rate - capacity),
                }
            )
        return audits

    def output_preseparation_exposure_audit(lane_load_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if knowledge is None or not pending_byproduct_audit:
            return []
        node_index = {
            str(node.get("fingerprint")): node
            for node in layout_plan.get("nodes") or []
            if node.get("fingerprint") is not None
        }
        byproducts_by_target = {
            str(item.get("target_item") or ""): [
                str(byproduct.get("item") or "")
                for byproduct in item.get("byproducts") or []
                if byproduct.get("item")
            ]
            for item in pending_byproduct_audit
            if item.get("target_item")
        }
        separator_by_route: dict[tuple[str, float], dict[str, Any]] = {}
        for separation in output_separations:
            boundary = str(separation.get("boundary") or "")
            route_y = separation.get("route_y")
            if not boundary or route_y is None:
                continue
            separator_by_route[(boundary, round(float(route_y), 3))] = separation
        lane_load_by_route = {
            (str(item.get("boundary") or ""), round(float(item.get("route_y") or 0.0), 3)): item
            for item in lane_load_audit
            if item.get("boundary") and item.get("route_y") is not None
        }
        preseparator_instances_by_route: dict[tuple[str, float], set[int]] = {}
        for separation in output_separations:
            if separation.get("scope") != "output-fanin" or separation.get("status") != "connected":
                continue
            boundary = str(separation.get("boundary") or "")
            route_y = separation.get("route_y")
            from_instance = separation.get("from_instance")
            if not boundary or route_y is None or from_instance is None:
                continue
            preseparator_instances_by_route.setdefault((boundary, round(float(route_y), 3)), set()).add(int(from_instance))

        audits: list[dict[str, Any]] = []
        for boundary in sorted(byproducts_by_target):
            if not boundary:
                continue
            output_boundary = f"output:{boundary}"
            for route in routes_for_production_audit(output_boundary):
                if route.get("status") != "connected" or not route.get("port"):
                    continue
                port = route["port"]
                fingerprint = str(port.get("node_fingerprint") or "")
                node = node_index.get(fingerprint)
                if node is None:
                    continue
                start_instance = int(port.get("node_instance") or 0)
                route_y = round(float(port.get("y") or 0.0), 3)
                covered_instances = reachable_instances(
                    start_instance,
                    bridge_edges_for_node(fingerprint, route_y),
                    direction="reverse",
                )
                fanin_segments = [
                    item
                    for item in output_fanins
                    if item.get("status") == "connected"
                    and str(item.get("boundary") or "") == output_boundary
                    and str(item.get("node_fingerprint") or "") == fingerprint
                    and round(float(item.get("fanin_y") or 0.0), 3) == route_y
                ]
                separator = separator_by_route.get((output_boundary, route_y))
                lane_load = lane_load_by_route.get((output_boundary, route_y)) or {}
                lane_capacity = lane_load.get("lane_capacity_per_minute")
                per_instance_rate = lane_load.get("per_instance_net_output_per_minute")
                max_safe_instances = None
                if isinstance(lane_capacity, (int, float)) and isinstance(per_instance_rate, (int, float)) and per_instance_rate > 0:
                    max_safe_instances = max(1, int(math.floor(float(lane_capacity) / float(per_instance_rate))))
                preseparator_instances = sorted(preseparator_instances_by_route.get((output_boundary, route_y), set()))
                fanin_source_instances = sorted(set(covered_instances) - {start_instance})
                fanin_preseparated = bool(fanin_source_instances) and set(fanin_source_instances).issubset(set(preseparator_instances))
                status = (
                    "target-overloaded-after-pre-fanin-separation"
                    if len(covered_instances) > 1 and separator is not None and fanin_preseparated and lane_load.get("status") == "overloaded"
                    else "preseparated-before-fanin"
                    if len(covered_instances) > 1 and separator is not None and fanin_preseparated
                    else
                    "mixed-overloaded-before-separation"
                    if len(covered_instances) > 1 and separator is not None and lane_load.get("status") == "overloaded"
                    else "mixed-before-separation"
                    if len(covered_instances) > 1 and separator is not None
                    else "single-source-before-separation"
                    if separator is not None
                    else "no-target-separator"
                )
                recommendation = (
                    "target-output-still-exceeds-one-lane-after-preseparation-use-lane-aware-target-compression"
                    if len(covered_instances) > 1 and fanin_preseparated and lane_load.get("status") == "overloaded"
                    else "pre-fanin-separation-removes-mixed-byproducts-but-still-needs-runtime-proof"
                    if len(covered_instances) > 1 and fanin_preseparated
                    else
                    "split-target-and-byproduct-before-output-fanin-or-use-runtime-proven-lane-aware-compression"
                    if len(covered_instances) > 1 and lane_load.get("status") == "overloaded"
                    else "mixed-route-is-within-lane-capacity-but-still-needs-runtime-proof"
                    if len(covered_instances) > 1
                    else "current-separator-is-after-a-single-source-output-route"
                )
                audits.append(
                    {
                        "boundary": output_boundary,
                        "status": status,
                        "node_item": node.get("item"),
                        "node_recipe": node.get("recipe"),
                        "node_fingerprint": fingerprint,
                        "route_y": route_y,
                        "start_instance": start_instance,
                        "covered_instances": covered_instances,
                        "covered_instance_count": len(covered_instances),
                        "fanin_source_instances": fanin_source_instances,
                        "preseparator_instances": preseparator_instances,
                        "fanin_preseparated": fanin_preseparated,
                        "fanin_segment_count": len(fanin_segments),
                        "byproducts": byproducts_by_target[boundary],
                        "lane_load_status": lane_load.get("status"),
                        "lane_load_rate_per_minute": lane_load.get("load_rate_per_minute"),
                        "per_instance_net_output_per_minute": per_instance_rate,
                        "lane_capacity_per_minute": lane_load.get("lane_capacity_per_minute"),
                        "lane_overload_per_minute": lane_load.get("overload_per_minute"),
                        "max_safe_instances_before_separation": max_safe_instances,
                        "separator_x": separator.get("splitter_x") if separator else None,
                        "separator_handling": separator.get("current_handling") if separator else None,
                        "recommendation": recommendation,
                    }
                )
        return audits

    coverage = boundary_coverage()
    flow_audit = belt_flow_audit()
    capacity_audit = boundary_capacity_audit(flow_audit)
    contract_audit = boundary_contract_audit()
    lane_load_audit = output_lane_load_audit()
    preseparation_exposure_audit = output_preseparation_exposure_audit(lane_load_audit)
    byproduct_audit = output_byproduct_audit()
    entities.extend(connectors)
    return {
        "connectors_added": len(connectors),
        "bridges_added": bridges_added,
        "input_fanouts_added": input_fanouts_added,
        "output_fanins_added": output_fanins_added,
        "output_separation_splitters": output_separation_splitters,
        "output_separation_overflow_belts": output_separation_overflow_belts,
        "output_separation_recycle_belts": output_separation_recycle_belts,
        "output_separation_merge_belts": output_separation_merge_belts,
        "collisions": collisions,
        "routes": routes,
        "bridges": bridges,
        "input_fanouts": input_fanouts,
        "output_fanins": output_fanins,
        "output_separations": output_separations,
        "output_boundary_compressors": output_boundary_compressors,
        "boundary_coverage": coverage,
        "boundary_capacity_audit": capacity_audit,
        "boundary_contract_audit": contract_audit,
        "output_preseparation_exposure_audit": preseparation_exposure_audit,
        "output_lane_load_audit": lane_load_audit,
        "output_byproduct_audit": byproduct_audit,
        "belt_flow_audit": flow_audit,
    }


def materialize_layout_with_summary(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
    knowledge: PrototypeKnowledge | None = None,
    allow_new_drop_belts: bool = False,
    max_output_expansions_per_machine: int = 4,
    output_separation_min_distance: float = 1.0,
    compress_output_boundary: bool = False,
    preseparate_output_before_fanin: bool = False,
    experimental_prefanin_input_sideload: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping_index = mapping_by_fingerprint(mappings)
    working_layout = copy.deepcopy(layout_plan)
    entities: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    tile_positions: set[tuple[str, float, float]] = set()
    output_inserter_upgrades: list[dict[str, Any]] = []
    for node in working_layout["nodes"]:
        mapping = mapping_index.get(str(node["fingerprint"])) or {}
        layout = mapping.get("layout") or {}
        template_entities = layout.get("entities") or []
        template_entities = prune_template_entities_for_recipe(
            template_entities,
            target_recipe=str(node.get("recipe") or ""),
            knowledge=knowledge,
            layout_ports=layout.get("ports") or [],
        )
        template_entities, node_upgrades = upgrade_output_inserters_for_recipe(
            template_entities,
            target_recipe=str(node.get("recipe") or ""),
            knowledge=knowledge,
        )
        for upgrade in node_upgrades:
            output_inserter_upgrades.append(
                {
                    "node_item": node.get("item"),
                    "node_recipe": node.get("recipe"),
                    "node_fingerprint": node.get("fingerprint"),
                    "from": upgrade["from"],
                    "to": upgrade["to"],
                    "template_count": upgrade["template_count"],
                    "instances": node.get("instances"),
                    "materialized_count": int(upgrade["template_count"]) * int(node.get("instances") or 1),
                }
            )
        machine_ports = machine_io_port_hints(
            template_entities,
            target_recipe=str(node.get("recipe") or ""),
            knowledge=knowledge,
        )
        if machine_ports:
            existing_port_keys = {
                (
                    str(port.get("side") or ""),
                    str(port.get("role") or ""),
                    str(port.get("entity_name") or ""),
                    round(float(port.get("x") or 0.0), 3),
                    round(float(port.get("y") or 0.0), 3),
                )
                for port in node.get("ports") or []
            }
            for port in machine_ports:
                key = (
                    str(port.get("side") or ""),
                    str(port.get("role") or ""),
                    str(port.get("entity_name") or ""),
                    round(float(port.get("x") or 0.0), 3),
                    round(float(port.get("y") or 0.0), 3),
                )
                if key in existing_port_keys:
                    continue
                node.setdefault("ports", []).append(port)
                existing_port_keys.add(key)
        template_tiles = layout.get("tiles") or []
        if not template_entities and not template_tiles:
            continue
        source_width = float(node["source_width"])
        source_height = float(node["source_height"])
        spacing = float(layout_plan["spacing"])
        row_spacing = float(layout_plan.get("row_spacing", spacing))
        for instance in range(int(node["instances"])):
            col = instance % int(node["columns"])
            row = instance // int(node["columns"])
            origin_x = float(node["x"]) + col * (source_width + spacing)
            origin_y = float(node["y"]) + row * (source_height + row_spacing)
            for raw in template_entities:
                entities.append(
                    materialized_entity(
                        raw,
                        len(entities) + 1,
                        x=origin_x,
                        y=origin_y,
                    )
                )
            for raw in template_tiles:
                tile = materialized_tile(raw, x=origin_x, y=origin_y)
                position = tile["position"]
                key = (tile["name"], float(position["x"]), float(position["y"]))
                if key in tile_positions:
                    continue
                tile_positions.add(key)
                tiles.append(tile)

    connector_result = {
        "connectors_added": 0,
        "connector_foundation_tiles_added": 0,
        "bridges_added": 0,
        "input_fanouts_added": 0,
        "output_fanins_added": 0,
        "output_separation_splitters": 0,
        "output_separation_overflow_belts": 0,
        "output_separation_recycle_belts": 0,
        "output_separation_merge_belts": 0,
        "collisions": [],
        "routes": [],
        "bridges": [],
        "input_fanouts": [],
        "output_fanins": [],
        "output_separations": [],
        "output_boundary_compressors": [],
        "boundary_coverage": [],
        "boundary_capacity_audit": [],
        "boundary_contract_audit": [],
        "output_preseparation_exposure_audit": [],
        "output_lane_load_audit": [],
        "output_byproduct_audit": [],
        "belt_flow_audit": [],
        "output_inserter_upgrades": output_inserter_upgrades,
        "machine_output_expansions": {},
    }
    if connect_boundaries:
        occupied_entities = {entity_position_key(entity): entity for entity in entities}
        occupied = set(occupied_entities)
        connector_result = add_boundary_connectors(
            entities,
            working_layout,
            occupied=occupied,
            occupied_entities=occupied_entities,
            knowledge=knowledge,
            output_separation_min_distance=output_separation_min_distance,
            compress_output_boundary=compress_output_boundary,
            preseparate_output_before_fanin=preseparate_output_before_fanin,
            experimental_prefanin_input_sideload=experimental_prefanin_input_sideload,
        )
        connector_result["output_inserter_upgrades"] = output_inserter_upgrades
    connector_result.setdefault("connector_foundation_tiles_added", 0)

    foundation_tile_name = next((tile["name"] for tile in tiles if tile.get("name") == "space-platform-foundation"), None)
    if foundation_tile_name:
        for entity in entities:
            tile_x, tile_y = entity_foundation_tile_key(entity)
            key = (foundation_tile_name, tile_x, tile_y)
            if key in tile_positions:
                continue
            tile_positions.add(key)
            tiles.append({"name": foundation_tile_name, "position": {"x": tile_x, "y": tile_y}})
            connector_result["connector_foundation_tiles_added"] = int(connector_result.get("connector_foundation_tiles_added") or 0) + 1

    connector_result["machine_output_expansions"] = materialize_machine_output_expansions(
        entities,
        knowledge,
        max_per_machine=max_output_expansions_per_machine,
        allow_new_drop_belts=allow_new_drop_belts,
        target_item=str(working_layout.get("target_item") or ""),
    )

    target_item = str(working_layout["target_item"])
    wrapper = make_blueprint_wrapper(
        label or f"blueprint-lab-{target_item}-{working_layout['target_rate_per_minute']:g}-per-min",
        entities,
        tiles=tiles,
        icons=[icon(target_item)],
        description=(
            "Blueprint Lab materialized skeleton from learned templates. "
            "Connector belts, pipes, power, beacon effects, and in-game validation are still required before production use."
        ),
    )
    return wrapper, connector_result


def materialize_layout(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
    knowledge: PrototypeKnowledge | None = None,
    allow_new_drop_belts: bool = False,
    max_output_expansions_per_machine: int = 4,
) -> dict[str, Any]:
    wrapper, _ = materialize_layout_with_summary(
        layout_plan,
        mappings,
        label=label,
        connect_boundaries=connect_boundaries,
        knowledge=knowledge,
        allow_new_drop_belts=allow_new_drop_belts,
        max_output_expansions_per_machine=max_output_expansions_per_machine,
    )
    return wrapper


def layout_with_single_node_columns(layout_plan: dict[str, Any], columns: int, *, lane_width: float | None = None) -> dict[str, Any]:
    layout = copy.deepcopy(layout_plan)
    if len(layout.get("nodes") or []) != 1:
        return layout
    if lane_width is not None:
        layout["lane_width"] = lane_width
    node = layout["nodes"][0]
    instances = max(1, int(node.get("instances") or 1))
    columns = max(1, min(columns, instances))
    rows = max(1, math.ceil(instances / columns))
    source_width = float(node.get("source_width") or 1.0)
    source_height = float(node.get("source_height") or 1.0)
    spacing = float(layout.get("spacing") or 0.0)
    row_spacing = float(layout.get("row_spacing", spacing))
    effective_lane_width = float(layout.get("lane_width") or 0.0)
    planned_width = columns * source_width + max(0, columns - 1) * spacing
    planned_height = rows * source_height + max(0, rows - 1) * row_spacing
    node["columns"] = columns
    node["rows"] = rows
    node["x"] = round(effective_lane_width, 3)
    node["y"] = round(effective_lane_width, 3)
    node["planned_width"] = round(planned_width, 3)
    node["planned_height"] = round(planned_height, 3)
    layout["estimated_width"] = round(planned_width + effective_lane_width * 2, 3)
    layout["estimated_height"] = round(planned_height + effective_lane_width * 2, 3)
    layout["estimated_area"] = round(layout["estimated_width"] * layout["estimated_height"], 3)
    layout["layout_selection"] = {
        "strategy": "forced-single-node-columns",
        "columns": columns,
        "rows": rows,
        "lane_width": effective_lane_width,
        "row_spacing": row_spacing,
    }
    return layout


def output_preseparation_safe_width_constraint(
    layout_plan: dict[str, Any],
    knowledge: PrototypeKnowledge | None,
) -> dict[str, Any] | None:
    if knowledge is None or len(layout_plan.get("nodes") or []) != 1:
        return None
    target_rate_basis = layout_plan.get("target_rate_basis") or {}
    if target_rate_basis.get("kind") != "full-belt":
        return None
    target_item = str(layout_plan.get("target_item") or "")
    belt_name = str(target_rate_basis.get("belt_name") or "")
    node = layout_plan["nodes"][0]
    recipe_name = str(node.get("recipe") or "")
    recipe = knowledge.recipe(recipe_name)
    if recipe is None:
        return None
    byproducts = sorted(
        {
            product.name
            for product in recipe.products
            if product.type == "item"
            and product.name != target_item
            and product.amount * product.probability > 0
        }
    )
    if not byproducts:
        return None

    instances = max(1, int(node.get("instances") or 1))
    columns = max(1, int(node.get("columns") or instances))
    planned_net = float(node.get("planned_net_output_per_minute") or 0.0)
    per_instance_rate = planned_net / instances if instances else 0.0
    belt = knowledge.belt(belt_name)
    lane_capacity = float(belt.items_per_minute) if belt is not None else None
    max_safe_instances = None
    if lane_capacity is not None and per_instance_rate > 0:
        max_safe_instances = max(1, int(math.floor(lane_capacity / per_instance_rate)))
    status = "unknown"
    if max_safe_instances is not None:
        status = "over-limit" if columns > max_safe_instances else "within-limit"
    return {
        "status": status,
        "strategy": "limit-row-fanin-before-target-byproduct-separation",
        "target_item": target_item,
        "recipe": recipe_name,
        "byproducts": byproducts,
        "columns": columns,
        "per_instance_net_output_per_minute": per_instance_rate,
        "lane_capacity_per_minute": lane_capacity,
        "max_safe_instances_before_separation": max_safe_instances,
        "recommendation": (
            "reduce-row-width-or-add-pre-fanin-separation"
            if status == "over-limit"
            else "row-width-is-within-preseparation-lane-capacity"
            if status == "within-limit"
            else "cannot-compute-preseparation-safe-width"
        ),
    }


def materialized_layout_score(summary: dict[str, Any]) -> tuple[float, ...]:
    connector_summary = summary["connector_summary"]
    safe_width_constraint = summary.get("output_preseparation_safe_width_constraint") or {}
    flow_statuses = Counter(item.get("status", "unknown") for item in connector_summary.get("belt_flow_audit") or [])
    capacity_statuses = Counter(item.get("status", "unknown") for item in connector_summary.get("boundary_capacity_audit") or [])
    contract_statuses = Counter(item.get("status", "unknown") for item in connector_summary.get("boundary_contract_audit") or [])
    lane_load_statuses = Counter(item.get("status", "unknown") for item in connector_summary.get("output_lane_load_audit") or [])
    output_separations = connector_summary.get("output_separations") or []
    output_boundary_compressors = connector_summary.get("output_boundary_compressors") or []
    preseparation_exposure = connector_summary.get("output_preseparation_exposure_audit") or []
    output_capacity = [
        item
        for item in connector_summary.get("boundary_capacity_audit") or []
        if str(item.get("boundary") or "").startswith("output:")
    ]
    output_coverage = [
        item
        for item in connector_summary.get("boundary_coverage") or []
        if str(item.get("boundary") or "").startswith("output:")
    ]
    output_routes = [
        item
        for item in connector_summary.get("routes") or []
        if str(item.get("boundary") or "").startswith("output:")
        and item.get("status") == "connected"
        and item.get("port")
        and item.get("boundary_role") != "external-output"
    ]
    output_not_sufficient = sum(1 for item in output_capacity if item.get("status") != "sufficient")
    output_coverage_not_met = sum(1 for item in output_coverage if not item.get("meets_required_rate", item.get("status") == "covered"))
    output_routes_without_machine_drop = sum(1 for item in output_routes if (item.get("port") or {}).get("role") != "machine-output")
    preseparation_safe_width_over_limit = 1 if safe_width_constraint.get("status") == "over-limit" else 0
    contract_not_exact = sum(1 for item in connector_summary.get("boundary_contract_audit") or [] if item.get("status") != "exact")
    contract_over = contract_statuses.get("over-provisioned", 0)
    bad_capacity = capacity_statuses.get("failed", 0) + capacity_statuses.get("insufficient", 0)
    unresolved_capacity = capacity_statuses.get("unresolved", 0)
    overloaded_output_lanes = lane_load_statuses.get("overloaded", 0)
    mixed_overloaded_preseparation = sum(
        1
        for item in preseparation_exposure
        if item.get("status") == "mixed-overloaded-before-separation"
    )
    finite_or_blocked_output_separations = sum(
        1
        for item in output_separations
        if item.get("status") != "connected" or str(item.get("current_handling") or "").endswith("finite-overflow-buffer")
    )
    experimental_sideload_separations = sum(
        1
        for item in output_separations
        if item.get("current_handling") == "pre-fanin-recycle-sideload-to-input-lane"
    )
    blocked_output_boundary_compressors = sum(
        1
        for item in output_boundary_compressors
        if item.get("status") != "connected"
    )
    width = float(summary.get("width") or 0.0)
    height = float(summary.get("height") or 0.0)
    area = width * height
    horizontal_penalty = max(0.0, height - width)
    return (
        float(len(connector_summary.get("collisions") or [])),
        float(blocked_output_boundary_compressors),
        float(preseparation_safe_width_over_limit),
        float(output_not_sufficient),
        float(output_coverage_not_met),
        float(flow_statuses.get("failed", 0)),
        float(finite_or_blocked_output_separations),
        float(experimental_sideload_separations),
        float(mixed_overloaded_preseparation),
        float(overloaded_output_lanes),
        float(contract_not_exact),
        float(contract_over),
        float(output_routes_without_machine_drop),
        float(bad_capacity),
        float(unresolved_capacity),
        float(flow_statuses.get("unresolved", 0)),
        horizontal_penalty,
        area,
        float(connector_summary.get("connectors_added", 0)),
        float(summary.get("entity_count") or 0),
    )


def layout_candidate_audit(
    summary: dict[str, Any],
    score: tuple[float, ...],
    *,
    compress_output_boundary: bool,
) -> dict[str, Any]:
    connector_summary = summary.get("connector_summary") or {}
    layout_nodes = summary.get("layout_nodes") or []
    node = layout_nodes[0] if layout_nodes else {}
    output_separations = connector_summary.get("output_separations") or []
    return {
        "columns": node.get("columns"),
        "rows": node.get("rows"),
        "compress_output_boundary": compress_output_boundary,
        "width": summary.get("width"),
        "height": summary.get("height"),
        "entity_count": summary.get("entity_count"),
        "score": list(score),
        "safe_width_status": (summary.get("output_preseparation_safe_width_constraint") or {}).get("status"),
        "collision_count": len(connector_summary.get("collisions") or []),
        "route_status_counts": dict(Counter(item.get("status", "unknown") for item in connector_summary.get("routes") or [])),
        "belt_flow_status_counts": dict(Counter(item.get("status", "unknown") for item in connector_summary.get("belt_flow_audit") or [])),
        "boundary_capacity_status_counts": dict(Counter(item.get("status", "unknown") for item in connector_summary.get("boundary_capacity_audit") or [])),
        "boundary_contract_status_counts": dict(Counter(item.get("status", "unknown") for item in connector_summary.get("boundary_contract_audit") or [])),
        "output_lane_load_status_counts": dict(Counter(item.get("status", "unknown") for item in connector_summary.get("output_lane_load_audit") or [])),
        "output_separation_status_counts": dict(Counter(item.get("status", "unknown") for item in output_separations)),
        "output_separation_handling_counts": dict(Counter(str(item.get("current_handling") or "none") for item in output_separations)),
        "selected": False,
    }


def select_best_materialized_layout(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
    knowledge: PrototypeKnowledge | None = None,
    allow_new_drop_belts: bool = False,
    max_output_expansions_per_machine: int = 4,
    force_columns: int | None = None,
    output_separation_min_distance: float = 1.0,
    compress_output_boundary: bool = False,
    preseparate_output_before_fanin: bool = False,
    experimental_prefanin_input_sideload: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not connect_boundaries or knowledge is None or len(layout_plan.get("nodes") or []) != 1:
        wrapper, connector_summary = materialize_layout_with_summary(
            layout_plan,
            mappings,
            label=label,
            connect_boundaries=connect_boundaries,
            knowledge=knowledge,
            allow_new_drop_belts=allow_new_drop_belts,
            max_output_expansions_per_machine=max_output_expansions_per_machine,
            output_separation_min_distance=output_separation_min_distance,
            compress_output_boundary=compress_output_boundary,
            preseparate_output_before_fanin=preseparate_output_before_fanin,
            experimental_prefanin_input_sideload=experimental_prefanin_input_sideload,
        )
        return wrapper, connector_summary, layout_plan

    node = layout_plan["nodes"][0]
    instances = max(1, int(node.get("instances") or 1))
    max_columns = max(1, min(int(layout_plan.get("max_columns") or instances), instances))
    base_lane_width = float(layout_plan.get("lane_width") or 0.0)
    force_lane_width_candidates = [base_lane_width]
    if base_lane_width > 0:
        force_lane_width_candidates.append(round(base_lane_width + 2.0, 3))
    candidate_audits: list[dict[str, Any]] = []

    def materialize_candidate(
        columns: int,
        lane_width: float,
        *,
        candidate_compress_output_boundary: bool,
    ) -> tuple[tuple[float, ...], dict[str, Any], dict[str, Any], dict[str, Any], bool]:
        candidate_layout = layout_with_single_node_columns(layout_plan, columns, lane_width=lane_width)
        safe_width_constraint = output_preseparation_safe_width_constraint(candidate_layout, knowledge)
        if safe_width_constraint is not None:
            candidate_layout["output_preseparation_safe_width_constraint"] = safe_width_constraint
        wrapper, connector_summary = materialize_layout_with_summary(
            candidate_layout,
            mappings,
            label=label,
            connect_boundaries=connect_boundaries,
            knowledge=knowledge,
            allow_new_drop_belts=allow_new_drop_belts,
            max_output_expansions_per_machine=max_output_expansions_per_machine,
            output_separation_min_distance=output_separation_min_distance,
            compress_output_boundary=candidate_compress_output_boundary,
            preseparate_output_before_fanin=preseparate_output_before_fanin,
            experimental_prefanin_input_sideload=experimental_prefanin_input_sideload,
        )
        summary = render_summary(wrapper, candidate_layout, connector_summary, knowledge=knowledge)
        score = materialized_layout_score(summary)
        candidate_audits.append(
            layout_candidate_audit(
                summary,
                score,
                compress_output_boundary=candidate_compress_output_boundary,
            )
        )
        return score, wrapper, connector_summary, candidate_layout, candidate_compress_output_boundary

    if force_columns is not None:
        if force_columns < 1 or force_columns > max_columns:
            raise ValueError(f"force_columns must be between 1 and {max_columns}, got {force_columns}")
        forced_best: tuple[tuple[float, ...], dict[str, Any], dict[str, Any], dict[str, Any], bool] | None = None
        for lane_width in force_lane_width_candidates:
            candidate = materialize_candidate(
                force_columns,
                lane_width,
                candidate_compress_output_boundary=compress_output_boundary,
            )
            if forced_best is None or candidate[0] < forced_best[0]:
                forced_best = candidate
        assert forced_best is not None
        score, wrapper, connector_summary, forced_layout, selected_compress_output_boundary = forced_best
        selected_columns = forced_layout["nodes"][0]["columns"]
        selected_rows = forced_layout["nodes"][0]["rows"]
        for audit in candidate_audits:
            audit["selected"] = (
                audit.get("columns") == selected_columns
                and audit.get("rows") == selected_rows
                and audit.get("compress_output_boundary") == selected_compress_output_boundary
                and audit.get("score") == list(score)
            )
        forced_layout["layout_selection"] = {
            "strategy": "forced-single-node-columns",
            "candidate_count": len(force_lane_width_candidates),
            "selected_columns": selected_columns,
            "selected_rows": selected_rows,
            "selected_lane_width": forced_layout.get("lane_width"),
            "selected_compress_output_boundary": selected_compress_output_boundary,
            "score": list(score),
            "candidates": candidate_audits,
        }
        return wrapper, connector_summary, forced_layout

    best: tuple[tuple[float, ...], dict[str, Any], dict[str, Any], dict[str, Any], bool] | None = None
    candidate_count = 0
    boundary_modes = [False, True] if compress_output_boundary else [False]
    for columns in range(1, max_columns + 1):
        for candidate_compress_output_boundary in boundary_modes:
            candidate_count += 1
            candidate = materialize_candidate(
                columns,
                base_lane_width,
                candidate_compress_output_boundary=candidate_compress_output_boundary,
            )
            if best is None or candidate[0] < best[0]:
                best = candidate
    assert best is not None
    score, wrapper, connector_summary, selected_layout, selected_compress_output_boundary = best
    selected_columns = selected_layout["nodes"][0]["columns"]
    selected_rows = selected_layout["nodes"][0]["rows"]
    for audit in candidate_audits:
        audit["selected"] = (
            audit.get("columns") == selected_columns
            and audit.get("rows") == selected_rows
            and audit.get("compress_output_boundary") == selected_compress_output_boundary
            and audit.get("score") == list(score)
        )
    selected_layout["layout_selection"] = {
        "strategy": "post-materialize-column-search",
        "candidate_count": candidate_count,
        "selected_columns": selected_columns,
        "selected_rows": selected_rows,
        "selected_lane_width": selected_layout.get("lane_width"),
        "selected_compress_output_boundary": selected_compress_output_boundary,
        "score": list(score),
        "candidates": candidate_audits,
    }
    return wrapper, connector_summary, selected_layout


def build_materialized_blueprint(
    mappings: list[dict[str, Any]],
    *,
    target_item: str,
    target_rate_per_minute: float,
    target_rate_basis: dict[str, Any] | None = None,
    target_recipe: str | None = None,
    max_depth: int = 4,
    boundary_items: set[str] | None = None,
    max_columns: int = 12,
    spacing: float = 2.0,
    row_spacing: float | None = None,
    lane_width: float = 4.0,
    label: str | None = None,
    connect_boundaries: bool = False,
    knowledge: PrototypeKnowledge | None = None,
) -> dict[str, Any]:
    production_plan = build_production_plan(
        mappings,
        target_item=target_item,
        target_rate_per_minute=target_rate_per_minute,
        target_rate_basis=target_rate_basis,
        target_recipe=target_recipe,
        max_depth=max_depth,
        boundary_items=boundary_items,
    )
    layout = build_layout_plan(
        production_plan,
        mappings,
        max_columns=max_columns,
        spacing=spacing,
        row_spacing=row_spacing,
        lane_width=lane_width,
    )
    return materialize_layout(layout, mappings, label=label, connect_boundaries=connect_boundaries, knowledge=knowledge)


def render_summary(
    wrapper: dict[str, Any],
    layout: dict[str, Any],
    connector_summary: dict[str, Any] | None = None,
    *,
    knowledge: PrototypeKnowledge | None = None,
) -> dict[str, Any]:
    blueprint = wrapper["blueprint"]
    metrics = blueprint_metrics("/", blueprint)
    summary = connector_summary or {
        "connectors_added": 0,
        "bridges_added": 0,
        "input_fanouts_added": 0,
        "output_fanins_added": 0,
        "output_separation_splitters": 0,
        "output_separation_overflow_belts": 0,
        "output_separation_recycle_belts": 0,
        "output_separation_merge_belts": 0,
        "collisions": [],
        "routes": [],
        "bridges": [],
        "input_fanouts": [],
        "output_fanins": [],
        "output_separations": [],
        "output_boundary_compressors": [],
        "boundary_coverage": [],
        "boundary_capacity_audit": [],
        "boundary_contract_audit": [],
        "output_preseparation_exposure_audit": [],
        "output_lane_load_audit": [],
        "output_byproduct_audit": [],
        "belt_flow_audit": [],
        "output_inserter_upgrades": [],
        "machine_output_expansions": {},
        "machine_output_expansion_audit": [],
    }
    route_status_counts = Counter(route.get("status", "unknown") for route in summary.get("routes") or [])
    layout_nodes = [
        {
            "item": node.get("item"),
            "recipe": node.get("recipe"),
            "fingerprint": node.get("fingerprint"),
            "instances": node.get("instances"),
            "columns": node.get("columns"),
            "rows": node.get("rows"),
            "planned_width": node.get("planned_width"),
            "planned_height": node.get("planned_height"),
            "rate_basis": node.get("rate_basis"),
            "planned_net_output_per_minute": node.get("planned_net_output_per_minute"),
            "direct_module_effects": node.get("direct_module_effects") or [],
            "direct_module_items": node.get("direct_module_items") or [],
            "rate_module_effects": node.get("rate_module_effects") or [],
            "rate_module_items": node.get("rate_module_items") or [],
        }
        for node in layout.get("nodes") or []
    ]
    return {
        "label": blueprint.get("label"),
        "target_item": layout["target_item"],
        "target_rate_per_minute": layout["target_rate_per_minute"],
        "target_rate_basis": layout.get("target_rate_basis") or {
            "kind": "explicit-rate",
            "rate_per_minute": layout["target_rate_per_minute"],
        },
        "entity_count": metrics.entity_count,
        "tile_count": metrics.tile_count,
        "width": metrics.width,
        "height": metrics.height,
        "density": metrics.density,
        "layout_estimated_width": layout["estimated_width"],
        "layout_estimated_height": layout["estimated_height"],
        "boundary_inputs": layout["boundary_inputs"],
        "boundary_outputs": layout["boundary_outputs"],
        "layout_nodes": layout_nodes,
        "layout_selection": layout.get("layout_selection"),
        "output_preseparation_safe_width_constraint": layout.get("output_preseparation_safe_width_constraint"),
        "connector_summary": summary,
        "route_status_counts": dict(route_status_counts),
        "machine_io_audit": audit_machine_io(wrapper, knowledge),
        "machine_output_expansion_audit": audit_machine_output_expansion(wrapper, knowledge),
        "lessons": [
            "Materialization copies learned local template geometry into the planned rectangle instead of inventing machines from scratch.",
            "Boundary connectors are generated only in reserved lanes and checked for exact entity-position collisions.",
            "Machine I/O audit checks inserter endpoints against data.raw entity boxes; it is an adjacency guard, not a full inserter throughput simulation.",
            "The generated blueprint is still not production-ready: pipe routing, power, splitter/lane semantics, cross-template beacon modeling, and in-game validation remain separate steps.",
        ],
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    target_rate_basis = summary.get("target_rate_basis") or {}
    lines = [
        "# Blueprint Materialization Report",
        "",
        f"- Label: {summary['label']}",
        f"- Target item: {summary['target_item']}",
        f"- Target rate: {summary['target_rate_per_minute']:g}/min",
        f"- Target rate basis: {render_target_rate_basis(target_rate_basis)}",
        f"- Entities: {summary['entity_count']}",
        f"- Tiles: {summary['tile_count']}",
        f"- Connector belts: {summary['connector_summary']['connectors_added']}",
        f"- Inter-instance bridge belts: {summary['connector_summary'].get('bridges_added', 0)}",
        f"- Input fanout belts: {summary['connector_summary'].get('input_fanouts_added', 0)}",
        f"- Output fan-in belts: {summary['connector_summary'].get('output_fanins_added', 0)}",
        f"- Output separation splitters: {summary['connector_summary'].get('output_separation_splitters', 0)}",
        f"- Output separation overflow belts: {summary['connector_summary'].get('output_separation_overflow_belts', 0)}",
        f"- Output separation recycle belts: {summary['connector_summary'].get('output_separation_recycle_belts', 0)}",
        f"- Output separation merge belts: {summary['connector_summary'].get('output_separation_merge_belts', 0)}",
        f"- Output boundary compressors: {len(summary['connector_summary'].get('output_boundary_compressors') or [])}",
        f"- Output inserter upgrades: {sum(int(item.get('materialized_count') or 0) for item in summary['connector_summary'].get('output_inserter_upgrades') or [])}",
        f"- Machine output expansion inserters: {int((summary['connector_summary'].get('machine_output_expansions') or {}).get('inserters_added') or 0)}",
        f"- Connector collisions: {len(summary['connector_summary']['collisions'])}",
        f"- Route status counts: {summary['route_status_counts']}",
        f"- Belt flow status counts: {dict(Counter(item.get('status', 'unknown') for item in summary['connector_summary'].get('belt_flow_audit') or []))}",
        f"- Boundary capacity status counts: {dict(Counter(item.get('status', 'unknown') for item in summary['connector_summary'].get('boundary_capacity_audit') or []))}",
        f"- Boundary contract status counts: {dict(Counter(item.get('status', 'unknown') for item in summary['connector_summary'].get('boundary_contract_audit') or []))}",
        f"- Output lane load status counts: {dict(Counter(item.get('status', 'unknown') for item in summary['connector_summary'].get('output_lane_load_audit') or []))}",
        f"- Machine I/O status counts: {dict(Counter(item.get('status', 'unknown') for item in summary.get('machine_io_audit') or []))}",
        f"- Blueprint bounds: {summary['width']:g} x {summary['height']:g}",
        f"- Layout estimate: {summary['layout_estimated_width']:g} x {summary['layout_estimated_height']:g}",
        f"- Density: {summary['density']:g}",
    ]
    if summary.get("layout_selection"):
        selection = summary["layout_selection"]
        lines.append(
            f"- Layout selection: {selection.get('strategy')} "
            f"columns={selection.get('selected_columns', selection.get('columns'))} "
            f"rows={selection.get('selected_rows', selection.get('rows'))}"
        )
    if summary.get("output_preseparation_safe_width_constraint"):
        constraint = summary["output_preseparation_safe_width_constraint"]
        lines.append(
            f"- Output pre-separation safe width: status={constraint.get('status')} "
            f"columns={constraint.get('columns')} "
            f"max_safe_instances={constraint.get('max_safe_instances_before_separation')} "
            f"byproducts={constraint.get('byproducts')} "
            f"next={constraint.get('recommendation')}"
        )
    selection_candidates = (summary.get("layout_selection") or {}).get("candidates") or []
    if selection_candidates:
        lines.extend(["", "## Layout Candidate Audit", ""])
        for item in selection_candidates[:8]:
            marker = "selected" if item.get("selected") else "candidate"
            lines.append(
                f"- {marker}: columns={item.get('columns')} rows={item.get('rows')} "
                f"compress={item.get('compress_output_boundary')} "
                f"safe_width={item.get('safe_width_status')} "
                f"collisions={item.get('collision_count')} "
                f"routes={item.get('route_status_counts')} "
                f"flow={item.get('belt_flow_status_counts')} "
                f"capacity={item.get('boundary_capacity_status_counts')} "
                f"contract={item.get('boundary_contract_status_counts')} "
                f"lane_load={item.get('output_lane_load_status_counts')} "
                f"separations={item.get('output_separation_handling_counts')}"
            )
    lines.extend(["", "## Boundary Inputs", ""])
    if summary["boundary_inputs"]:
        for item in summary["boundary_inputs"]:
            lines.append(f"- {item['item']}: {item['rate_per_minute']:g}/min side={item['side']} reason={item['reason']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Boundary Outputs", ""])
    for item in summary["boundary_outputs"]:
        lines.append(f"- {item['item']}: {item['rate_per_minute']:g}/min side={item['side']}")
    if summary["layout_nodes"]:
        lines.extend(["", "## Layout Nodes", ""])
        for node in summary["layout_nodes"]:
            lines.append(
                f"- {node['item']} / {node['recipe']}: instances={node['instances']} "
                f"grid={node.get('columns')}x{node.get('rows')} "
                f"basis={node['rate_basis']} planned_net={node['planned_net_output_per_minute']:g}/min"
            )
            if node["rate_module_items"]:
                modules = ", ".join(
                    f"{count}x {quality} {name}"
                    for name, quality, count in node["rate_module_items"]
                )
                lines.append(f"  rate_modules={modules}")
            if node["rate_module_effects"]:
                effects = ", ".join(f"{name}:{value:g}" for name, value in node["rate_module_effects"])
                lines.append(f"  rate_module_effects={effects}")
    if summary["connector_summary"]["routes"]:
        lines.extend(["", "## Connector Routes", ""])
        for item in summary["connector_summary"]["routes"]:
            line = f"- {item['boundary']}: status={item['status']} belts={item['belts_added']}"
            if item.get("port"):
                port = item["port"]
                line += (
                    f" port={port['node_item']}/{port['role']}/{port['entity_name']}"
                    f" at=({port['x']},{port['y']})"
                )
            if item.get("route_kind"):
                line += f" route={item['route_kind']}"
            if item.get("blocked_attempts"):
                line += f" blocked_attempts={len(item['blocked_attempts'])}"
            if item.get("reason"):
                line += f" reason={item['reason']}"
            lines.append(line)
    if summary["connector_summary"].get("bridges"):
        lines.extend(["", "## Inter-instance Bridges", ""])
        for item in summary["connector_summary"]["bridges"]:
            line = (
                f"- {item['node_item']}: status={item['status']} belts={item['belts_added']} "
                f"instances={item['from_instance']}->{item['to_instance']}"
            )
            if item.get("from_port") and item.get("to_port"):
                line += (
                    f" from=({item['from_port']['x']},{item['from_port']['y']})"
                    f" to=({item['to_port']['x']},{item['to_port']['y']})"
                )
            if item.get("route_kind"):
                line += f" route={item['route_kind']}"
            lines.append(line)
    if summary["connector_summary"].get("input_fanouts"):
        lines.extend(["", "## Input Fanouts", ""])
        for item in summary["connector_summary"]["input_fanouts"]:
            line = (
                f"- {item['boundary']}: status={item['status']} belts={item['belts_added']} "
                f"instances={item['from_instance']}->{item['to_instance']} y={item.get('fanout_y')}"
            )
            if item.get("existing_belts_used"):
                line += f" existing_belts={item['existing_belts_used']}"
            if item.get("to_port"):
                line += (
                    f" from=({item['from_port']['x']},{item['from_port']['y']})"
                    f" to=({item['to_port']['x']},{item['to_port']['y']})"
                )
            if item.get("reason"):
                line += f" reason={item['reason']}"
            if item.get("route_kind"):
                line += f" route={item['route_kind']}"
            lines.append(line)
    if summary["connector_summary"].get("boundary_coverage"):
        lines.extend(["", "## Boundary Coverage", ""])
        for item in summary["connector_summary"]["boundary_coverage"]:
            line = (
                f"- {item['boundary']}: status={item['status']} "
                f"instances={item.get('covered_instance_count', 0)}/{item.get('total_instances', 0)}"
            )
            if item.get("covered_instances") is not None:
                line += f" covered={item['covered_instances']}"
            if item.get("covered_rate_per_minute") is not None:
                line += f" covered_rate={item['covered_rate_per_minute']:g}/min"
            if item.get("required_rate_per_minute") is not None:
                line += f" required={item['required_rate_per_minute']:g}/min"
            if item.get("meets_required_rate") is not None:
                line += f" meets_required={item['meets_required_rate']}"
            if item.get("reason"):
                line += f" reason={item['reason']}"
            lines.append(line)
    if summary["connector_summary"].get("boundary_capacity_audit"):
        lines.extend(["", "## Boundary Capacity Audit", ""])
        for item in summary["connector_summary"]["boundary_capacity_audit"]:
            line = (
                f"- {item['boundary']}: status={item['status']} "
                f"routes={item.get('route_count', 0)} capacity={item.get('capacity_per_minute', 0):g}/min"
            )
            if item.get("proven_capacity_per_minute") is not None:
                line += f" proven={item.get('proven_capacity_per_minute', 0):g}/min"
            if item.get("unresolved_capacity_per_minute"):
                line += f" unresolved={item.get('unresolved_capacity_per_minute', 0):g}/min"
            if item.get("failed_capacity_per_minute"):
                line += f" failed={item.get('failed_capacity_per_minute', 0):g}/min"
            if item.get("required_rate_per_minute") is not None:
                line += f" required={item['required_rate_per_minute']:g}/min"
            if item.get("structural_meets_required_rate") is not None:
                line += f" structural_meets={item['structural_meets_required_rate']}"
            if item.get("meets_required_rate") is not None:
                line += f" meets_required={item['meets_required_rate']}"
            if item.get("belt_capacities"):
                belts = ", ".join(
                    f"{belt['belt_name']}:{belt.get('capacity_per_minute') if belt.get('capacity_per_minute') is not None else 'unknown'}"
                    f"/{belt.get('flow_status', 'unknown')}"
                    for belt in item["belt_capacities"]
                )
                line += f" belts={belts}"
            lines.append(line)
    if summary["connector_summary"].get("boundary_contract_audit"):
        lines.extend(["", "## Boundary Contract Audit", ""])
        for item in summary["connector_summary"]["boundary_contract_audit"]:
            lines.append(
                f"- {item.get('boundary')}: status={item.get('status')} "
                f"expected={item.get('expected_belt_count')}x {item.get('expected_belt_name')} "
                f"routes={item.get('route_count')} lanes={item.get('route_ys')}"
            )
    if summary["connector_summary"].get("output_lane_load_audit"):
        lines.extend(["", "## Output Lane Load Audit", ""])
        for item in summary["connector_summary"]["output_lane_load_audit"]:
            lines.append(
                f"- {item.get('boundary')} y={item.get('route_y')}: status={item.get('status')} "
                f"instances={item.get('covered_instances')} load={item.get('load_rate_per_minute', 0):g}/min "
                f"capacity={item.get('lane_capacity_per_minute', 0):g}/min "
                f"overload={item.get('overload_per_minute', 0):g}/min"
            )
    if summary["connector_summary"].get("output_preseparation_exposure_audit"):
        lines.extend(["", "## Output Pre-separation Exposure Audit", ""])
        for item in summary["connector_summary"]["output_preseparation_exposure_audit"]:
            byproducts = ",".join(item.get("byproducts") or [])
            lines.append(
                f"- {item.get('boundary')} y={item.get('route_y')}: status={item.get('status')} "
                f"instances={item.get('covered_instances')} fanins={item.get('fanin_segment_count')} "
                f"separator_x={item.get('separator_x')} byproducts={byproducts} "
                f"lane_load={item.get('lane_load_status')} max_safe_instances={item.get('max_safe_instances_before_separation')} "
                f"next={item.get('recommendation')}"
            )
    if summary["connector_summary"].get("output_byproduct_audit"):
        lines.extend(["", "## Output Byproduct Audit", ""])
        for item in summary["connector_summary"]["output_byproduct_audit"]:
            byproducts = ", ".join(
                f"{byproduct['item']}:{byproduct.get('amount', 0):g}"
                + (f"@{byproduct['probability']:g}" if byproduct.get("probability") is not None else "")
                + (" recyclable" if byproduct.get("same_recipe_input") else "")
                for byproduct in item.get("byproducts") or []
            )
            lines.append(
                f"- {item.get('recipe')}: status={item.get('status')} "
                f"target={item.get('target_item')} handling={item.get('recommended_handling')} byproducts={byproducts}"
            )
    if summary["connector_summary"].get("output_separations"):
        lines.extend(["", "## Output Separations", ""])
        for item in summary["connector_summary"]["output_separations"]:
            line = (
                f"- {item.get('boundary')}: status={item.get('status')} "
                f"scope={item.get('scope', 'boundary-route')} "
                f"splitter={item.get('splitter_name')} at=({item.get('splitter_x')},{item.get('splitter_y')}) "
                f"current={item.get('current_handling')} recommended={item.get('recommended_handling')} "
                f"overflow_y={item.get('overflow_y')} overflow_belts={item.get('overflow_belts_added', 0)}"
            )
            if item.get("from_instance") is not None:
                line += f" from={item.get('from_instance')} to={item.get('to_instance')}"
            if item.get("recyclable_byproducts"):
                line += f" recyclable={','.join(item['recyclable_byproducts'])}"
            if item.get("recycle_merge_target"):
                target = item["recycle_merge_target"]
                line += (
                    f" merge_target=({target.get('input_x')},{target.get('input_y')})"
                    f"<-({target.get('merge_x')},{target.get('merge_y')})"
                )
            if item.get("recycle_flow_audit"):
                audit = item["recycle_flow_audit"]
                line += f" recycle_flow={audit.get('status')} recycle_positions={audit.get('positions_checked')}"
            if item.get("blocked_recycle_attempt_count"):
                line += f" blocked_recycle_attempts={item['blocked_recycle_attempt_count']}"
                attempts = item.get("blocked_recycle_attempts") or []
                first_collision = ((attempts[0] or {}).get("collisions") or [None])[0] if attempts else None
                if first_collision:
                    line += (
                        f" first_block=({first_collision.get('x')},{first_collision.get('y')})"
                        f"/{first_collision.get('reason')}"
                    )
            if item.get("recycle_corridor_probe"):
                probe = item["recycle_corridor_probe"]
                line += f" corridor_probe={probe.get('status')} next={probe.get('recommendation')}"
            if item.get("existing_belts_used"):
                line += f" existing_belts={item['existing_belts_used']}"
            if item.get("reason"):
                line += f" reason={item['reason']}"
            lines.append(line)
    if summary["connector_summary"].get("output_boundary_compressors"):
        lines.extend(["", "## Output Boundary Compressors", ""])
        for item in summary["connector_summary"]["output_boundary_compressors"]:
            line = (
                f"- {item.get('boundary')}: status={item.get('status')} "
                f"strategy={item.get('strategy')} internal={item.get('internal_route_count')} "
                f"external={item.get('external_route_count')}"
            )
            if item.get("compressor_input_ys") is not None:
                line += f" input_ys={item.get('compressor_input_ys')}"
            if item.get("compressor_output_ys") is not None:
                line += f" output_ys={item.get('compressor_output_ys')}"
            if item.get("runtime_status"):
                line += f" runtime_status={item.get('runtime_status')}"
            if item.get("capacity_proof"):
                line += f" capacity_proof={item.get('capacity_proof')}"
            if item.get("reason"):
                line += f" reason={item.get('reason')}"
            if item.get("runtime_evidence"):
                line += f" evidence={item.get('runtime_evidence')}"
            lines.append(line)
    if summary["connector_summary"].get("belt_flow_audit"):
        lines.extend(["", "## Belt Flow Audit", ""])
        for item in summary["connector_summary"]["belt_flow_audit"]:
            label = item.get("boundary") or item.get("node_fingerprint") or "segment"
            line = (
                f"- {item['segment_type']} {label}: status={item['status']} "
                f"belt={item['belt_name']} y={item['y']} x={item['start_x']}..{item['end_x']} "
                f"positions={item['positions_checked']}"
            )
            if item.get("from_instance") is not None:
                line += f" from={item['from_instance']}"
            if item.get("to_instance") is not None:
                line += f" to={item['to_instance']}"
            if item.get("failures"):
                line += f" failures={len(item['failures'])}"
            if item.get("unresolved"):
                line += f" unresolved={len(item['unresolved'])}"
            lines.append(line)
    if summary["connector_summary"].get("output_inserter_upgrades"):
        lines.extend(["", "## Output Inserter Upgrades", ""])
        for item in summary["connector_summary"]["output_inserter_upgrades"]:
            lines.append(
                f"- {item.get('node_recipe')}: {item.get('from')} -> {item.get('to')} "
                f"template_count={item.get('template_count')} instances={item.get('instances')} "
                f"materialized={item.get('materialized_count')}"
            )
    output_expansions = summary["connector_summary"].get("machine_output_expansions") or {}
    if output_expansions.get("enabled"):
        lines.extend(["", "## Materialized Machine Output Expansions", ""])
        lines.append(
            f"- strategy={output_expansions.get('strategy')} inserters={output_expansions.get('inserters_added')} "
            f"drop_belts={output_expansions.get('drop_belts_added')} machines={output_expansions.get('machines_expanded')} "
            f"skipped_new_drop_belts={output_expansions.get('skipped_new_drop_belt_candidates')} "
            f"blocked={output_expansions.get('blocked_candidate_count')}"
        )
        for item in (output_expansions.get("selected") or [])[:8]:
            lines.append(
                f"- {item.get('recipe')} machine={item.get('machine_entity_number')} "
                f"inserter=({item.get('inserter_x')},{item.get('inserter_y')}) "
                f"drop={item.get('drop')}@({item.get('drop_x')},{item.get('drop_y')})"
            )
    if summary.get("machine_output_expansion_audit"):
        lines.extend(["", "## Machine Output Expansion Audit", ""])
        for item in summary["machine_output_expansion_audit"]:
            line = (
                f"- {item.get('recipe')}: status={item.get('status')} "
                f"machines={item.get('machine_count')} existing_outputs={item.get('existing_output_inserter_count')} "
                f"expandable={item.get('expandable_machine_count')} candidates={item.get('candidate_count')} "
                f"blocked={item.get('blocked_candidate_count')} invalid_endpoints={item.get('invalid_endpoint_count')}"
            )
            samples = item.get("samples") or []
            if samples:
                sample = samples[0]
                line += (
                    f" sample=({sample.get('candidate_x')},{sample.get('candidate_y')})"
                    f"->{sample.get('drop')}@({sample.get('drop_x')},{sample.get('drop_y')})"
                )
            blocked_samples = item.get("blocked_samples") or []
            if not samples and blocked_samples:
                sample = blocked_samples[0]
                line += (
                    f" blocked_sample=({sample.get('candidate_x')},{sample.get('candidate_y')})"
                    f"->{sample.get('drop')}@({sample.get('drop_x')},{sample.get('drop_y')})"
                    f" collisions={len(sample.get('collisions') or [])}"
                )
            lines.append(line)
    if summary.get("machine_io_audit"):
        lines.extend(["", "## Machine I/O Audit", ""])
        for item in summary["machine_io_audit"]:
            if item.get("recipe") == "__unresolved_inserters__":
                lines.append(
                    f"- unresolved inserters: status={item['status']} count={item.get('unresolved_inserter_count', 0)}"
                )
                continue
            lines.append(
                f"- {item['recipe']}: status={item['status']} machines={item['machine_count']} "
                f"input={item['machines_with_input']}/{item['machine_count']} "
                f"output={item['machines_with_output']}/{item['machine_count']} "
                f"inserters={item['input_inserter_count']} in/{item['output_inserter_count']} out"
            )
    if summary["connector_summary"]["collisions"]:
        lines.extend(["", "## Connector Collisions", ""])
        for item in summary["connector_summary"]["collisions"]:
            lines.append(f"- ({item['x']}, {item['y']}) reason={item['reason']}")
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
    parser = argparse.ArgumentParser(description="Materialize a learned-template layout plan into a blueprint skeleton.")
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
    parser.add_argument("--label")
    parser.add_argument("--connect-boundaries", action="store_true")
    parser.add_argument("--allow-new-drop-belts", action="store_true", help="Experimental: allow generated machine-output expansion inserters to create new drop belts. Default keeps only runtime-proven existing drop belts.")
    parser.add_argument("--max-output-expansions-per-machine", type=int, default=4)
    parser.add_argument("--force-columns", type=int, help="Experimental: force the single-node repeated grid to this column count instead of running post-materialization column search.")
    parser.add_argument("--output-separation-min-distance", type=float, default=1.0, help="Experimental: require this many tiles between the selected machine-output port and the target-item filter splitter.")
    parser.add_argument("--preseparate-output-before-fanin", action="store_true", help="Experimental: insert target/byproduct filter splitters on output fan-in source segments before multiple production instances merge.")
    parser.add_argument("--experimental-prefanin-input-sideload", action="store_true", help="Experimental negative-evidence topology: let pre-fanin byproduct separators side-load recycled chunks into a nearby input lane. Not enabled by default because the real 3x2 crusher probe stayed below target.")
    parser.add_argument("--compress-output-boundary", action="store_true", help="Experimental: try to keep over-provisioned internal output lanes and add a corpus-derived 3-to-2 compressor for a 2-belt full-belt target; generic compressors with known runtime shortfall are reported as unresolved capacity and may be rejected by layout selection.")
    parser.add_argument("--output", type=Path, required=True)
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
    layout = build_layout_plan(
        production_plan,
        template_summary["mappings"],
        max_columns=args.max_columns,
        spacing=args.spacing,
        row_spacing=args.row_spacing,
        lane_width=args.lane_width,
    )
    wrapper, connector_summary, layout = select_best_materialized_layout(
        layout,
        template_summary["mappings"],
        label=args.label,
        connect_boundaries=args.connect_boundaries,
        knowledge=knowledge,
        allow_new_drop_belts=args.allow_new_drop_belts,
        max_output_expansions_per_machine=args.max_output_expansions_per_machine,
        force_columns=args.force_columns,
        output_separation_min_distance=args.output_separation_min_distance,
        compress_output_boundary=args.compress_output_boundary,
        preseparate_output_before_fanin=args.preseparate_output_before_fanin,
        experimental_prefanin_input_sideload=args.experimental_prefanin_input_sideload,
    )
    save_blueprint_file(args.output, wrapper)
    summary = render_summary(wrapper, layout, connector_summary, knowledge=knowledge)
    summary["output"] = str(args.output)
    summary["template_mapping_status_counts"] = template_summary["status_counts"]
    summary["template_mapping_failed_files"] = template_summary["failed_files"]

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(summary), encoding="utf-8")

    print(render_markdown_report(summary))
    print(f"Wrote {args.output}")
    return 0 if not template_summary["failed_files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
