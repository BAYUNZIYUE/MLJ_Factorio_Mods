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


def is_belt_like_entity_name(name: str) -> bool:
    return name.endswith("transport-belt") or name.endswith("underground-belt") or name.endswith("splitter")


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


def point_in_entity_box(point: tuple[float, float], entity: dict[str, Any], knowledge: PrototypeKnowledge) -> bool:
    box = knowledge.entity_box(str(entity.get("name") or ""))
    if box is None:
        return False
    entity_x, entity_y = entity_position(entity)
    (min_x, min_y), (max_x, max_y) = box.selection_box
    point_x, point_y = point
    tolerance = 0.05
    return (
        entity_x + min_x - tolerance <= point_x <= entity_x + max_x + tolerance
        and entity_y + min_y - tolerance <= point_y <= entity_y + max_y + tolerance
    )


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
        if role is None or not point_in_entity_box(point, entity, knowledge):
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


def materialized_tile(raw: dict[str, Any], *, x: float, y: float) -> dict[str, Any]:
    return {
        "name": raw["name"],
        "position": {
            "x": round(x + float(raw["x"]), 3),
            "y": round(y + float(raw["y"]), 3),
        },
    }


def add_boundary_connectors(
    entities: list[dict[str, Any]],
    layout_plan: dict[str, Any],
    *,
    occupied: set[tuple[float, float]],
    occupied_entities: dict[tuple[float, float], dict[str, Any]],
    knowledge: PrototypeKnowledge | None = None,
) -> dict[str, Any]:
    connectors: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    bridges: list[dict[str, Any]] = []
    input_fanouts: list[dict[str, Any]] = []
    if not layout_plan.get("nodes"):
        return {
            "connectors_added": 0,
            "bridges_added": 0,
            "input_fanouts_added": 0,
            "collisions": collisions,
            "routes": routes,
            "bridges": bridges,
            "input_fanouts": input_fanouts,
            "boundary_coverage": [],
            "boundary_capacity_audit": [],
            "belt_flow_audit": [],
        }

    root = layout_plan["nodes"][0]
    default_y = round(float(root["y"]) + float(root["source_height"]) / 2, 3)

    def add_positions(
        positions: list[RoutePosition],
        *,
        record_collisions: bool = True,
    ) -> tuple[int, list[dict[str, Any]]]:
        positions = visible_route_positions(positions)
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            if key in seen:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"}
                route_collisions.append(collision)
                continue
            seen.add(key)
            if key in occupied:
                collision = {"x": key[0], "y": key[1], "reason": reason}
                route_collisions.append(collision)
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
    ) -> tuple[int, list[dict[str, Any]], int]:
        positions = visible_route_positions(positions)
        route_collisions: list[dict[str, Any]] = []
        seen: set[tuple[float, float]] = set()
        existing_belts_used = 0
        for x, belt_y, reason, direction, belt_name in positions:
            key = (round(x, 3), round(belt_y, 3))
            if key in seen:
                collision = {"x": key[0], "y": key[1], "reason": f"{reason}:duplicate-route-position"}
                route_collisions.append(collision)
                continue
            seen.add(key)
            existing = occupied_entities.get(key)
            if existing is None:
                continue
            existing_name = str(existing.get("name") or "")
            if is_belt_like_entity_name(existing_name) and canonical_transport_belt_name(existing_name) == belt_name:
                if (
                    reason.endswith("machine-output-side-load")
                    or reason.endswith("machine-input-right-feed")
                ) and existing.get("direction") != direction:
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

    def horizontal_positions(start_x: float, end_x: float, y: float, reason: str, belt_name: str) -> list[RoutePosition]:
        positions: list[RoutePosition] = []
        x = start_x
        while x <= end_x:
            positions.append((round(x, 3), y, reason, DIR_EAST, belt_name))
            x += 1.0
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

    def ports_for_instance(node: dict[str, Any], instance: int, side: str, roles: set[str]) -> list[dict[str, Any]]:
        ports: list[dict[str, Any]] = []
        spacing = float(layout_plan.get("spacing") or 0)
        columns = max(1, int(node.get("columns") or 1))
        source_width = float(node.get("source_width") or 0)
        source_height = float(node.get("source_height") or 0)
        col = instance % columns
        row = instance // columns
        origin_x = float(node["x"]) + col * (source_width + spacing)
        origin_y = float(node["y"]) + row * (source_height + spacing)
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
                -bridge_lane_score(port),
                machine_output_drop_priority(port),
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
            ys = {
                round(float(port.get("y") or 0.0), 3)
                for port in ports_for_instance(node, 0, "right", {"output", "edge-bus", "boundary"})
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
            route_kind.startswith("machine-input-side-load")
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
        for port in ports:
            belt_name = connector_belt_name_for_port(port)
            if side == "left":
                start_x = 0.5
                end_x = float(port["x"]) - 0.5
                if port.get("role") == "machine-input" and port.get("direction") in {DIR_NORTH, DIR_SOUTH}:
                    if port.get("direction") == DIR_SOUTH:
                        feed_y = float(port["y"]) + 1.0
                        feed_x = float(port["x"]) + 1.0
                        horizontal_end_x = float(port["x"])
                        if start_x <= horizontal_end_x:
                            positions = horizontal_positions(
                                start_x,
                                horizontal_end_x,
                                feed_y,
                                f"{boundary_label}:machine-input-right-feed",
                                belt_name,
                            )
                            positions.append(
                                (
                                    round(feed_x, 3),
                                    round(feed_y, 3),
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
                            candidates.append((port, "machine-input-right-feed-1", positions))
                    offsets = range(1, 7)
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

    def route_boundary_rate(route: dict[str, Any]) -> float | None:
        return boundary_required_rate(str(route.get("boundary") or ""))

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
        for route in routes:
            if route.get("status") != "connected" or not route.get("port"):
                continue
            boundary = str(route.get("boundary") or "")
            port = route["port"]
            fingerprint = str(port.get("node_fingerprint") or "")
            instance = int(port.get("node_instance") or 0)
            route_y = round(float(port.get("y") or 0.0), 3)
            flow_status = flow_status_by_route.get((boundary, fingerprint, instance, route_y), "unknown")
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
                unresolved.append({"x": key[0], "y": key[1], "entity_name": entity_name, "reason": "splitter-semantics"})
        status = "failed" if failures else "unresolved" if unresolved else "pass"
        port = route.get("port") or {}
        first = positions[0] if positions else (0.0, 0.0, "", DIR_EAST, "transport-belt")
        last = positions[-1] if positions else first
        return {
            "segment_type": segment_type,
            "status": status,
            "boundary": route.get("boundary"),
            "node_fingerprint": str(port.get("node_fingerprint") or ""),
            "from_instance": int(port.get("node_instance") or 0),
            "belt_name": connector_belt_name_for_port(port),
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
        for route in routes:
            port = route.get("port") or {}
            fingerprint = str(port.get("node_fingerprint") or "")
            node = node_index.get(fingerprint)
            if route.get("status") != "connected" or not node:
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

    coverage = boundary_coverage()
    flow_audit = belt_flow_audit()
    capacity_audit = boundary_capacity_audit(flow_audit)
    entities.extend(connectors)
    return {
        "connectors_added": len(connectors),
        "bridges_added": bridges_added,
        "input_fanouts_added": input_fanouts_added,
        "collisions": collisions,
        "routes": routes,
        "bridges": bridges,
        "input_fanouts": input_fanouts,
        "boundary_coverage": coverage,
        "boundary_capacity_audit": capacity_audit,
        "belt_flow_audit": flow_audit,
    }


def materialize_layout_with_summary(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
    knowledge: PrototypeKnowledge | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping_index = mapping_by_fingerprint(mappings)
    working_layout = copy.deepcopy(layout_plan)
    entities: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    tile_positions: set[tuple[str, float, float]] = set()
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
        for instance in range(int(node["instances"])):
            col = instance % int(node["columns"])
            row = instance // int(node["columns"])
            origin_x = float(node["x"]) + col * (source_width + spacing)
            origin_y = float(node["y"]) + row * (source_height + spacing)
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
        "bridges_added": 0,
        "input_fanouts_added": 0,
        "collisions": [],
        "routes": [],
        "bridges": [],
        "input_fanouts": [],
        "boundary_coverage": [],
        "boundary_capacity_audit": [],
        "belt_flow_audit": [],
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
) -> dict[str, Any]:
    wrapper, _ = materialize_layout_with_summary(
        layout_plan,
        mappings,
        label=label,
        connect_boundaries=connect_boundaries,
        knowledge=knowledge,
    )
    return wrapper


def layout_with_single_node_columns(layout_plan: dict[str, Any], columns: int) -> dict[str, Any]:
    layout = copy.deepcopy(layout_plan)
    if len(layout.get("nodes") or []) != 1:
        return layout
    node = layout["nodes"][0]
    instances = max(1, int(node.get("instances") or 1))
    columns = max(1, min(columns, instances))
    rows = max(1, math.ceil(instances / columns))
    source_width = float(node.get("source_width") or 1.0)
    source_height = float(node.get("source_height") or 1.0)
    spacing = float(layout.get("spacing") or 0.0)
    lane_width = float(layout.get("lane_width") or 0.0)
    planned_width = columns * source_width + max(0, columns - 1) * spacing
    planned_height = rows * source_height + max(0, rows - 1) * spacing
    node["columns"] = columns
    node["rows"] = rows
    node["planned_width"] = round(planned_width, 3)
    node["planned_height"] = round(planned_height, 3)
    layout["estimated_width"] = round(planned_width + lane_width * 2, 3)
    layout["estimated_height"] = round(planned_height + lane_width * 2, 3)
    layout["estimated_area"] = round(layout["estimated_width"] * layout["estimated_height"], 3)
    layout["layout_selection"] = {
        "strategy": "forced-single-node-columns",
        "columns": columns,
        "rows": rows,
    }
    return layout


def materialized_layout_score(summary: dict[str, Any]) -> tuple[float, ...]:
    connector_summary = summary["connector_summary"]
    flow_statuses = Counter(item.get("status", "unknown") for item in connector_summary.get("belt_flow_audit") or [])
    capacity_statuses = Counter(item.get("status", "unknown") for item in connector_summary.get("boundary_capacity_audit") or [])
    output_capacity = [
        item
        for item in connector_summary.get("boundary_capacity_audit") or []
        if str(item.get("boundary") or "").startswith("output:")
    ]
    output_not_sufficient = sum(1 for item in output_capacity if item.get("status") != "sufficient")
    bad_capacity = capacity_statuses.get("failed", 0) + capacity_statuses.get("insufficient", 0)
    unresolved_capacity = capacity_statuses.get("unresolved", 0)
    width = float(summary.get("width") or 0.0)
    height = float(summary.get("height") or 0.0)
    area = width * height
    horizontal_penalty = max(0.0, height - width)
    return (
        float(len(connector_summary.get("collisions") or [])),
        float(output_not_sufficient),
        float(bad_capacity),
        float(flow_statuses.get("failed", 0)),
        float(unresolved_capacity),
        float(flow_statuses.get("unresolved", 0)),
        horizontal_penalty,
        area,
        float(connector_summary.get("connectors_added", 0)),
        float(summary.get("entity_count") or 0),
    )


def select_best_materialized_layout(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
    knowledge: PrototypeKnowledge | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not connect_boundaries or knowledge is None or len(layout_plan.get("nodes") or []) != 1:
        wrapper, connector_summary = materialize_layout_with_summary(
            layout_plan,
            mappings,
            label=label,
            connect_boundaries=connect_boundaries,
            knowledge=knowledge,
        )
        return wrapper, connector_summary, layout_plan

    node = layout_plan["nodes"][0]
    instances = max(1, int(node.get("instances") or 1))
    max_columns = max(1, min(int(layout_plan.get("max_columns") or instances), instances))
    best: tuple[tuple[float, ...], dict[str, Any], dict[str, Any], dict[str, Any]] | None = None
    candidate_count = 0
    for columns in range(1, max_columns + 1):
        candidate_count += 1
        candidate_layout = layout_with_single_node_columns(layout_plan, columns)
        wrapper, connector_summary = materialize_layout_with_summary(
            candidate_layout,
            mappings,
            label=label,
            connect_boundaries=connect_boundaries,
            knowledge=knowledge,
        )
        summary = render_summary(wrapper, candidate_layout, connector_summary, knowledge=knowledge)
        score = materialized_layout_score(summary)
        if best is None or score < best[0]:
            best = (score, wrapper, connector_summary, candidate_layout)
    assert best is not None
    score, wrapper, connector_summary, selected_layout = best
    selected_layout["layout_selection"] = {
        "strategy": "post-materialize-column-search",
        "candidate_count": candidate_count,
        "selected_columns": selected_layout["nodes"][0]["columns"],
        "selected_rows": selected_layout["nodes"][0]["rows"],
        "score": list(score),
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
        "collisions": [],
        "routes": [],
        "bridges": [],
        "input_fanouts": [],
        "boundary_coverage": [],
        "boundary_capacity_audit": [],
        "belt_flow_audit": [],
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
        "connector_summary": summary,
        "route_status_counts": dict(route_status_counts),
        "machine_io_audit": audit_machine_io(wrapper, knowledge),
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
        f"- Connector collisions: {len(summary['connector_summary']['collisions'])}",
        f"- Route status counts: {summary['route_status_counts']}",
        f"- Belt flow status counts: {dict(Counter(item.get('status', 'unknown') for item in summary['connector_summary'].get('belt_flow_audit') or []))}",
        f"- Boundary capacity status counts: {dict(Counter(item.get('status', 'unknown') for item in summary['connector_summary'].get('boundary_capacity_audit') or []))}",
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
    parser.add_argument("--lane-width", type=float, default=4.0)
    parser.add_argument("--label")
    parser.add_argument("--connect-boundaries", action="store_true")
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
        lane_width=args.lane_width,
    )
    wrapper, connector_summary, layout = select_best_materialized_layout(
        layout,
        template_summary["mappings"],
        label=args.label,
        connect_boundaries=args.connect_boundaries,
        knowledge=knowledge,
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
