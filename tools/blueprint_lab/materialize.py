from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .analysis import blueprint_metrics, iter_blueprint_text_files
from .codec import make_blueprint_wrapper, save_blueprint_file
from .directions import DIR_EAST
from .generate import icon
from .layout_plan import build_layout_plan, mapping_by_fingerprint
from .production_dag import (
    build_production_plan,
    default_boundary_items,
    template_options_from_mappings,
)
from .prototypes import load_data_raw, target_rate_basis_from_args
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
            "belt_flow_audit": [],
        }

    root = layout_plan["nodes"][0]
    default_y = round(float(root["y"]) + float(root["source_height"]) / 2, 3)

    def add_positions(
        positions: list[RoutePosition],
        *,
        record_collisions: bool = True,
    ) -> tuple[int, list[dict[str, Any]]]:
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

    def add_positions_reusing_existing_belts(positions: list[RoutePosition]) -> tuple[int, list[dict[str, Any]], int]:
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
                existing_belts_used += 1
                continue
            collision = {"x": key[0], "y": key[1], "reason": reason}
            route_collisions.append(collision)
        if route_collisions:
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
    ) -> tuple[int, list[dict[str, Any]], dict[str, Any] | None, str | None, list[dict[str, Any]]]:
        blocked_attempts: list[dict[str, Any]] = []
        for port, route_kind, positions in candidates:
            belts_added, route_collisions = add_positions(positions, record_collisions=False)
            if not route_collisions:
                return belts_added, route_collisions, port, route_kind, blocked_attempts
            blocked_attempts.append(
                {
                    "port": port,
                    "route_kind": route_kind,
                    "collisions": route_collisions,
                }
            )
        if not blocked_attempts:
            return 0, [], None, None, blocked_attempts
        last = blocked_attempts[-1]
        collisions.extend(last["collisions"])
        return 0, list(last["collisions"]), dict(last["port"]), str(last["route_kind"]), blocked_attempts

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

    def ports_by_distance(ports: list[dict[str, Any]], y: float, side: str) -> list[dict[str, Any]]:
        role_priority = {"input": 0, "output": 0, "edge-bus": 1, "boundary": 2}
        if side == "right":
            return sorted(ports, key=lambda port: (abs(float(port["y"]) - y), role_priority.get(str(port.get("role")), 9), -float(port["x"])))
        return sorted(ports, key=lambda port: (abs(float(port["y"]) - y), role_priority.get(str(port.get("role")), 9), float(port["x"])))

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

    def add_inter_instance_bridges() -> int:
        before = len(connectors)
        for node in layout_plan.get("nodes") or []:
            instances = int(node.get("instances") or 1)
            columns = max(1, int(node.get("columns") or 1))
            if instances < 2 or columns < 2:
                continue
            for instance in range(instances - 1):
                col = instance % columns
                next_instance = instance + 1
                if next_instance >= instances or next_instance // columns != instance // columns:
                    continue
                if col + 1 >= columns:
                    continue
                right_ports = port_by_y(
                    ports_for_instance(node, instance, "right", {"output", "edge-bus", "boundary"}),
                    prefer="rightmost",
                )
                left_ports = port_by_y(
                    ports_for_instance(node, next_instance, "left", {"input", "edge-bus", "boundary"}),
                    prefer="leftmost",
                )
                for y, right_port in sorted(right_ports.items()):
                    if not can_start_horizontal_flow(right_port):
                        continue
                    left_port = left_ports.get(y)
                    if left_port is None:
                        continue
                    if not can_end_horizontal_flow(left_port):
                        continue
                    start_x = float(right_port["x"]) + 1.0
                    end_x = float(left_port["x"]) - 1.0
                    if start_x > end_x:
                        continue
                    belt_name = connector_belt_name_for_port(right_port)
                    reason = f"bridge:{node.get('item')}:{instance}->{next_instance}:{y:g}"
                    positions = horizontal_positions(start_x, end_x, y, reason, belt_name)
                    belts_added, route_collisions = add_positions(positions, record_collisions=False)
                    status = "connected" if not route_collisions else "blocked"
                    if route_collisions:
                        collisions.extend(route_collisions)
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
                            "collisions": route_collisions,
                            "route_kind": "inter-instance-direct",
                        }
                    )
        return len(connectors) - before

    bridges_added = add_inter_instance_bridges()

    def node_by_fingerprint() -> dict[str, dict[str, Any]]:
        return {
            str(node.get("fingerprint")): node
            for node in layout_plan.get("nodes") or []
            if node.get("fingerprint") is not None
        }

    for boundary in layout_plan.get("boundary_inputs") or []:
        ports = ports_by_distance(
            candidate_ports("left", {"input", "edge-bus", "boundary"}),
            default_y,
            "left",
        )
        if not ports:
            left_end = int(max(0, float(root["x"]) - 1))
            positions = [
                (float(x), default_y, f"input:{boundary['item']}", DIR_EAST, "transport-belt")
                for x in range(0, left_end + 1)
            ]
            belts_added, route_collisions = add_positions(positions)
            routes.append(
                {
                    "boundary": f"input:{boundary['item']}",
                    "status": "stub-only" if not route_collisions else "blocked",
                    "belts_added": belts_added,
                    "collisions": route_collisions,
                    "reason": "no-left-port",
                }
            )
            continue

        candidates: list[tuple[dict[str, Any], str, list[RoutePosition]]] = []
        reason = f"input:{boundary['item']}"
        for port in ports:
            start_x = 0.5
            end_x = float(port["x"]) - 0.5
            belt_name = connector_belt_name_for_port(port)
            candidates.append(
                (
                    port,
                    *route_candidate(
                        start_x=start_x,
                        end_x=end_x,
                        y=float(port["y"]),
                        reason=reason,
                        belt_name=belt_name,
                    ),
                )
            )
        belts_added, route_collisions, port, route_kind, blocked_attempts = add_first_clear_route(candidates)
        routes.append(
            {
                "boundary": f"input:{boundary['item']}",
                "status": "connected" if not route_collisions else "blocked",
                "belts_added": belts_added,
                "collisions": route_collisions,
                "port": port,
                "route_kind": route_kind,
                "blocked_attempts": blocked_attempts,
            }
        )

    for boundary in layout_plan.get("boundary_outputs") or []:
        ports = ports_by_distance(
            candidate_ports("right", {"output", "edge-bus", "boundary"}),
            default_y,
            "right",
        )
        if not ports:
            right_start = int(float(root["x"]) + float(root["planned_width"]) + 1)
            right_end = int(max(right_start - 1, float(layout_plan["estimated_width"]) - 1))
            positions = [
                (float(x), default_y, f"output:{boundary['item']}", DIR_EAST, "transport-belt")
                for x in range(right_start, right_end + 1)
            ]
            belts_added, route_collisions = add_positions(positions)
            routes.append(
                {
                    "boundary": f"output:{boundary['item']}",
                    "status": "stub-only" if not route_collisions else "blocked",
                    "belts_added": belts_added,
                    "collisions": route_collisions,
                    "reason": "no-right-port",
                }
            )
            continue

        candidates = []
        reason = f"output:{boundary['item']}"
        end_x = float(layout_plan["estimated_width"]) - 0.5
        for port in ports:
            start_x = float(port["x"]) + 1.0
            belt_name = connector_belt_name_for_port(port)
            candidates.append(
                (
                    port,
                    *route_candidate(
                        start_x=start_x,
                        end_x=end_x,
                        y=float(port["y"]),
                        reason=reason,
                        belt_name=belt_name,
                    ),
                )
            )
        belts_added, route_collisions, port, route_kind, blocked_attempts = add_first_clear_route(candidates)
        routes.append(
            {
                "boundary": f"output:{boundary['item']}",
                "status": "connected" if not route_collisions else "blocked",
                "belts_added": belts_added,
                "collisions": route_collisions,
                "port": port,
                "route_kind": route_kind,
                "blocked_attempts": blocked_attempts,
            }
        )

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
                    ports_for_instance(node, next_instance, "left", {"input", "edge-bus", "boundary"}),
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
        boundary = str(route.get("boundary") or "")
        if boundary.startswith("output:"):
            item = boundary.split(":", 1)[1]
            for output in layout_plan.get("boundary_outputs") or []:
                if str(output.get("item")) == item:
                    rate = output.get("rate_per_minute")
                    return float(rate) if isinstance(rate, (int, float)) else None
        if boundary.startswith("input:"):
            item = boundary.split(":", 1)[1]
            for input_item in layout_plan.get("boundary_inputs") or []:
                if str(input_item.get("item")) == item:
                    rate = input_item.get("rate_per_minute")
                    return float(rate) if isinstance(rate, (int, float)) else None
        return None

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
        positions = horizontal_span_positions(start_x, end_x, y)
        last_index = len(positions) - 1
        for index, (x, belt_y) in enumerate(positions):
            entity = occupied_entities.get((x, belt_y))
            if entity is None:
                failures.append({"x": x, "y": belt_y, "reason": "missing-belt"})
                continue
            entity_name = str(entity.get("name") or "")
            if not is_belt_like_entity_name(entity_name):
                failures.append({"x": x, "y": belt_y, "entity_name": entity_name, "reason": "non-belt-entity"})
                continue
            if canonical_transport_belt_name(entity_name) != belt_name:
                failures.append({"x": x, "y": belt_y, "entity_name": entity_name, "reason": "belt-tier-mismatch"})
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
                continue
            if entity_name.endswith("splitter"):
                unresolved.append({"x": x, "y": belt_y, "entity_name": entity_name, "reason": "splitter-semantics"})
                continue
            if entity_name.endswith("underground-belt"):
                underground_type = entity.get("type")
                if underground_type == "output" and index == 0:
                    continue
                if underground_type == "input" and index == last_index:
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
        status = "failed" if failures else "unresolved" if unresolved else "pass"
        result: dict[str, Any] = {
            "segment_type": segment_type,
            "status": status,
            "belt_name": belt_name,
            "start_x": round(start_x, 3),
            "end_x": round(end_x, 3),
            "y": round(y, 3),
            "positions_checked": len(positions),
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

    def belt_flow_audit() -> list[dict[str, Any]]:
        audit: list[dict[str, Any]] = []
        for route in routes:
            if route.get("status") != "connected" or not route.get("port"):
                continue
            port = route["port"]
            boundary = str(route.get("boundary") or "")
            belt_name = connector_belt_name_for_port(port)
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
        coverage: list[dict[str, Any]] = []
        for route in routes:
            port = route.get("port") or {}
            fingerprint = str(port.get("node_fingerprint") or "")
            node = node_index.get(fingerprint)
            if route.get("status") != "connected" or not node:
                coverage.append(
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
            coverage_status = "covered" if len(covered_instances) >= instances else "partial"
            item: dict[str, Any] = {
                "boundary": route.get("boundary"),
                "status": coverage_status,
                "direction": direction,
                "route_y": route_y,
                "node_item": node.get("item"),
                "node_recipe": node.get("recipe"),
                "node_fingerprint": fingerprint,
                "start_instance": start_instance,
                "covered_instances": covered_instances,
                "covered_instance_count": len(covered_instances),
                "total_instances": instances,
            }
            required_rate = route_boundary_rate(route)
            if required_rate is not None:
                item["required_rate_per_minute"] = required_rate
            if boundary.startswith("output:"):
                planned_net = float(node.get("planned_net_output_per_minute") or 0.0)
                per_instance = planned_net / instances if instances else 0.0
                covered_rate = per_instance * len(covered_instances)
                item["covered_rate_per_minute"] = covered_rate
                item["per_instance_net_output_per_minute"] = per_instance
                if required_rate is not None:
                    item["meets_required_rate"] = covered_rate >= required_rate
            coverage.append(item)
        return coverage

    coverage = boundary_coverage()
    flow_audit = belt_flow_audit()
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
        "belt_flow_audit": flow_audit,
    }


def materialize_layout_with_summary(
    layout_plan: dict[str, Any],
    mappings: list[dict[str, Any]],
    *,
    label: str | None = None,
    connect_boundaries: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping_index = mapping_by_fingerprint(mappings)
    entities: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    tile_positions: set[tuple[str, float, float]] = set()
    for node in layout_plan["nodes"]:
        mapping = mapping_index.get(str(node["fingerprint"])) or {}
        layout = mapping.get("layout") or {}
        template_entities = layout.get("entities") or []
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
        "belt_flow_audit": [],
    }
    if connect_boundaries:
        occupied_entities = {entity_position_key(entity): entity for entity in entities}
        occupied = set(occupied_entities)
        connector_result = add_boundary_connectors(
            entities,
            layout_plan,
            occupied=occupied,
            occupied_entities=occupied_entities,
        )

    target_item = str(layout_plan["target_item"])
    wrapper = make_blueprint_wrapper(
        label or f"blueprint-lab-{target_item}-{layout_plan['target_rate_per_minute']:g}-per-min",
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
) -> dict[str, Any]:
    wrapper, _ = materialize_layout_with_summary(
        layout_plan,
        mappings,
        label=label,
        connect_boundaries=connect_boundaries,
    )
    return wrapper


def build_materialized_blueprint(
    mappings: list[dict[str, Any]],
    *,
    target_item: str,
    target_rate_per_minute: float,
    target_rate_basis: dict[str, Any] | None = None,
    target_recipe: str | None = None,
    max_depth: int = 4,
    boundary_items: set[str] | None = None,
    max_columns: int = 8,
    spacing: float = 2.0,
    lane_width: float = 4.0,
    label: str | None = None,
    connect_boundaries: bool = False,
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
    return materialize_layout(layout, mappings, label=label, connect_boundaries=connect_boundaries)


def render_summary(wrapper: dict[str, Any], layout: dict[str, Any], connector_summary: dict[str, Any] | None = None) -> dict[str, Any]:
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
        "belt_flow_audit": [],
    }
    route_status_counts = Counter(route.get("status", "unknown") for route in summary.get("routes") or [])
    layout_nodes = [
        {
            "item": node.get("item"),
            "recipe": node.get("recipe"),
            "fingerprint": node.get("fingerprint"),
            "instances": node.get("instances"),
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
        "connector_summary": summary,
        "route_status_counts": dict(route_status_counts),
        "lessons": [
            "Materialization copies learned local template geometry into the planned rectangle instead of inventing machines from scratch.",
            "Boundary connectors are generated only in reserved lanes and checked for exact entity-position collisions.",
            "The generated blueprint is still not production-ready: pipe routing, power, full belt routing, cross-template beacon modeling, and in-game validation remain separate steps.",
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
        f"- Blueprint bounds: {summary['width']:g} x {summary['height']:g}",
        f"- Layout estimate: {summary['layout_estimated_width']:g} x {summary['layout_estimated_height']:g}",
        f"- Density: {summary['density']:g}",
        "",
        "## Boundary Inputs",
        "",
    ]
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
    parser.add_argument("--max-columns", type=int, default=8)
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
    wrapper, connector_summary = materialize_layout_with_summary(
        layout,
        template_summary["mappings"],
        label=args.label,
        connect_boundaries=args.connect_boundaries,
    )
    save_blueprint_file(args.output, wrapper)
    summary = render_summary(wrapper, layout, connector_summary)
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
