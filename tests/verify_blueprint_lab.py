#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.blueprint_lab.analysis import blueprint_metrics, summarize_library
from tools.blueprint_lab.codec import decode_blueprint_string, encode_blueprint_string, walk_nodes
from tools.blueprint_lab.decompose import decompose_blueprint
from tools.blueprint_lab.generate import generate_iron_plate_blackbox_seed
from tools.blueprint_lab.learn import learn_library
from tools.blueprint_lab.templates import extract_templates_from_blueprint
from tools.blueprint_lab.prototypes import load_data_raw, target_rate_basis_from_args
from tools.blueprint_lab.template_knowledge import map_template
from tools.blueprint_lab.production_dag import build_production_plan
from tools.blueprint_lab.layout_plan import build_layout_plan
from tools.blueprint_lab.materialize import build_materialized_blueprint, materialize_layout_with_summary


def main() -> int:
    wrapper = generate_iron_plate_blackbox_seed(furnace_pairs=4)
    encoded = encode_blueprint_string(wrapper)
    decoded = decode_blueprint_string(encoded)
    if decoded != wrapper:
        print("FAIL: generated blueprint did not round-trip through Factorio string encoding")
        return 1

    nodes = list(walk_nodes(decoded))
    blueprints = [node for node in nodes if node.kind == "blueprint"]
    if len(blueprints) != 1:
        print(f"FAIL: expected 1 generated blueprint, got {len(blueprints)}")
        return 1

    metrics = blueprint_metrics("/", blueprints[0].payload)
    if metrics.entity_count != 2 * (4 * 3 + 1) + 4 * 12:
        print(f"FAIL: unexpected entity count {metrics.entity_count}")
        return 1
    if metrics.width <= 0 or metrics.height <= 0 or metrics.density <= 0:
        print(f"FAIL: invalid metrics {metrics}")
        return 1

    tmp = ROOT / ".codex" / "tests" / "blueprint_lab_seed.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(encoded, encoding="utf-8")
    summary = summarize_library([tmp])
    if summary["decoded_files"] != 1 or summary["blueprint_count"] != 1:
        print(f"FAIL: generated seed summary is wrong: {summary}")
        return 1

    learned = learn_library([tmp])
    categories = {item["category"]: item for item in learned["category_summaries"]}
    if "smelting" not in categories:
        print(f"FAIL: expected generated seed to classify as smelting: {learned}")
        return 1
    if not learned["blackbox_candidates"]:
        print(f"FAIL: expected generated seed to be a black-box candidate: {learned}")
        return 1

    decomposition = decompose_blueprint("generated", "/", blueprints[0].payload, category="smelting", cell_size=4)
    port_roles = {port.role for port in decomposition.boundary_ports}
    if "edge-bus" not in port_roles:
        print(f"FAIL: expected generated seed to expose edge buses: {decomposition}")
        return 1
    if not decomposition.repeated_modules:
        print(f"FAIL: expected generated seed to expose repeated module signatures: {decomposition}")
        return 1

    templates = extract_templates_from_blueprint("generated", "/", blueprints[0].payload, category="smelting", cell_size=4)
    if not templates:
        print("FAIL: expected generated seed to expose template candidates")
        return 1
    if not all(template.fingerprint for template in templates):
        print(f"FAIL: expected template candidates to have fingerprints: {templates}")
        return 1

    recipe_blueprint = {
        "entities": [
            {
                "entity_number": 1,
                "name": "assembling-machine-3",
                "position": {"x": 1, "y": 1},
                "recipe": "iron-gear-wheel",
                "items": [{"id": {"name": "speed-module-3"}, "items": {"in_inventory": [{"inventory": 4, "stack": 0}]}}],
            },
            {
                "entity_number": 2,
                "name": "assembling-machine-3",
                "position": {"x": 5, "y": 1},
                "recipe": "iron-gear-wheel",
                "items": [{"id": {"name": "speed-module-3"}, "items": {"in_inventory": [{"inventory": 4, "stack": 0}]}}],
            },
        ]
    }
    recipe_templates = extract_templates_from_blueprint("fixture", "/", recipe_blueprint, category="science", cell_size=4)
    if not recipe_templates or recipe_templates[0].recipes != ["iron-gear-wheel"]:
        print(f"FAIL: expected recipe-bearing template: {recipe_templates}")
        return 1

    data_raw_path = ROOT / ".codex" / "tests" / "blueprint_lab_data_raw_fixture.json"
    data_raw_path.write_text(
        """
{
  "recipe": {
    "iron-gear-wheel": {
      "category": "crafting",
      "energy_required": 0.5,
      "ingredients": [["iron-plate", 2]],
      "result": "iron-gear-wheel"
    }
  },
  "assembling-machine": {
    "assembling-machine-3": {
      "crafting_categories": ["crafting"],
      "crafting_speed": 1.25,
      "module_slots": 4
    }
  },
  "module": {
    "speed-module-3": {
      "category": "speed",
      "effect": {"speed": 0.5, "consumption": 0.7, "quality": -0.25}
    }
  },
  "quality": {
    "normal": {"level": 0},
    "legendary": {"level": 5}
  },
  "transport-belt": {
    "transport-belt": {"speed": 0.03125},
    "turbo-transport-belt": {"speed": 0.125}
  }
}
""",
        encoding="utf-8",
    )
    knowledge = load_data_raw(data_raw_path)
    if knowledge.quality_effect_multiplier("legendary") != 2.5:
        print(f"FAIL: expected legendary quality to scale positive module effects by 2.5: {knowledge.qualities}")
        return 1
    target_rate, target_rate_basis = target_rate_basis_from_args(
        knowledge,
        target_rate_per_minute=None,
        target_belt="turbo-transport-belt",
        target_belt_count=2,
    )
    if target_rate != 7200 or target_rate_basis["items_per_second_per_belt"] != 60:
        print(f"FAIL: expected full-belt target to derive from data.raw belt speed: {target_rate_basis}")
        return 1
    mapped = map_template(recipe_templates[0], knowledge)
    if not mapped.recipe_mappings or mapped.recipe_mappings[0].status != "resolved":
        print(f"FAIL: expected recipe mapping to resolve: {mapped}")
        return 1
    if mapped.recipe_mappings[0].ingredients != [("iron-plate", 2.0)]:
        print(f"FAIL: expected recipe ingredients to normalize: {mapped.recipe_mappings[0]}")
        return 1
    if recipe_templates[0].occurrence_count != 2:
        print(f"FAIL: expected recipe template to record two observed occurrences: {recipe_templates[0]}")
        return 1
    if mapped.recipe_mappings[0].machine_speeds != [("1x assembling-machine-3", 1.25)]:
        print(f"FAIL: expected recipe machine speeds to normalize: {mapped.recipe_mappings[0]}")
        return 1
    if mapped.recipe_mappings[0].base_crafts_per_minute != 150:
        print(f"FAIL: expected base crafts/min to be 150 per template instance: {mapped.recipe_mappings[0]}")
        return 1
    if mapped.recipe_mappings[0].base_ingredients_per_minute != [("iron-plate", 300.0)]:
        print(f"FAIL: expected base input rate to normalize: {mapped.recipe_mappings[0]}")
        return 1
    if mapped.recipe_mappings[0].base_products_per_minute != [("iron-gear-wheel", 150.0)]:
        print(f"FAIL: expected base output rate to normalize: {mapped.recipe_mappings[0]}")
        return 1
    if not mapped.layout.entities[0].items or mapped.layout.entities[0].items[0]["id"]["name"] != "speed-module-3":
        print(f"FAIL: expected template layout to preserve raw module item stacks: {mapped.layout.entities[0]}")
        return 1
    if mapped.recipe_mappings[0].effective_crafts_per_minute != 225:
        print(f"FAIL: expected direct speed module to raise effective crafts/min to 225: {mapped.recipe_mappings[0]}")
        return 1
    if mapped.recipe_mappings[0].effective_ingredients_per_minute != [("iron-plate", 450.0)]:
        print(f"FAIL: expected direct speed module to raise effective input rate: {mapped.recipe_mappings[0]}")
        return 1
    if mapped.recipe_mappings[0].direct_module_effects != [("consumption", 0.7), ("quality", -0.25), ("speed", 0.5)]:
        print(f"FAIL: expected direct module effects to normalize: {mapped.recipe_mappings[0]}")
        return 1

    dag_mappings = [
        {
            "candidate_role": "production-template",
            "fingerprint": "gear-template",
            "label": "gear",
            "source": "fixture",
            "path": "/gear",
            "occurrence_count": 2,
            "module_items": ["speed-module-3"],
            "layout": {
                "width": 3.0,
                "height": 3.0,
                "entity_count": 1,
                "tile_count": 0,
                "entities": [
                    {
                        "name": "assembling-machine-3",
                        "x": 0,
                        "y": 0,
                        "direction": None,
                        "recipe": "iron-gear-wheel",
                        "recipe_quality": None,
                        "quality": None,
                        "items": [{"id": {"name": "speed-module-3"}, "items": {"in_inventory": [{"inventory": 4, "stack": 0}]}}],
                    }
                ],
                "tiles": [],
                "ports": [],
                "port_counts": [],
            },
            "recipe_mappings": [
                {
                    "recipe": "iron-gear-wheel",
                    "status": "resolved",
                    "base_crafts_per_minute": 150.0,
                    "base_ingredients_per_minute": [("iron-plate", 300.0)],
                    "base_products_per_minute": [("iron-gear-wheel", 150.0)],
                    "machine_speeds": [("1x assembling-machine-3", 1.25)],
                }
            ],
        },
        {
            "candidate_role": "production-template",
            "fingerprint": "plate-template",
            "label": "plate",
            "source": "fixture",
            "path": "/plate",
            "occurrence_count": 16,
            "module_items": [],
            "layout": {
                "width": 2.0,
                "height": 2.0,
                "entity_count": 1,
                "tile_count": 1,
                "entities": [
                    {
                        "name": "stone-furnace",
                        "x": 0,
                        "y": 0,
                        "direction": None,
                        "recipe": "iron-plate",
                        "recipe_quality": None,
                        "quality": None,
                    }
                ],
                "tiles": [{"name": "stone-path", "x": 0, "y": 1}],
                "ports": [{"side": "left", "role": "input", "entity_name": "transport-belt"}],
                "port_counts": [("left:input", 1)],
            },
            "recipe_mappings": [
                {
                    "recipe": "iron-plate",
                    "status": "resolved",
                    "base_crafts_per_minute": 18.75,
                    "base_ingredients_per_minute": [("iron-ore", 18.75)],
                    "base_products_per_minute": [("iron-plate", 18.75)],
                    "machine_speeds": [("1x stone-furnace", 1.0)],
                }
            ],
        },
        {
            "candidate_role": "production-template",
            "fingerprint": "gear-sink",
            "label": "gear sink",
            "source": "fixture",
            "path": "/gear-sink",
            "occurrence_count": 1,
            "module_items": [],
            "layout": {
                "width": 3.0,
                "height": 3.0,
                "entity_count": 1,
                "tile_count": 0,
                "entities": [
                    {
                        "name": "assembling-machine-3",
                        "x": 0,
                        "y": 0,
                        "direction": None,
                        "recipe": "gear-reprocessing",
                        "recipe_quality": None,
                        "quality": None,
                    }
                ],
                "tiles": [],
                "ports": [],
                "port_counts": [],
            },
            "recipe_mappings": [
                {
                    "recipe": "gear-reprocessing",
                    "status": "resolved",
                    "base_crafts_per_minute": 5.0,
                    "base_ingredients_per_minute": [("iron-gear-wheel", 10.0)],
                    "base_products_per_minute": [("iron-gear-wheel", 5.0)],
                    "machine_speeds": [("1x assembling-machine-3", 1.25)],
                }
            ],
        },
    ]
    dag = build_production_plan(
        dag_mappings,
        target_item="iron-gear-wheel",
        target_rate_per_minute=150,
        target_rate_basis={"kind": "explicit-rate", "rate_per_minute": 150},
        max_depth=4,
    )
    if dag["target_rate_basis"] != {"kind": "explicit-rate", "rate_per_minute": 150}:
        print(f"FAIL: expected DAG to retain target rate basis: {dag}")
        return 1
    if dag["node_count"] != 2:
        print(f"FAIL: expected gear and plate nodes in DAG: {dag}")
        return 1
    if dag["root"]["recipe"] != "iron-gear-wheel" or dag["root"]["instances"] != 1:
        print(f"FAIL: expected one gear template instance: {dag}")
        return 1
    if dag["root"]["children"][0]["recipe"] != "iron-plate" or dag["root"]["children"][0]["instances"] != 16:
        print(f"FAIL: expected sixteen plate template instances: {dag}")
        return 1
    if dag["external_inputs"] != [{"item": "iron-ore", "rate_per_minute": 300.0, "reason": "boundary-input"}]:
        print(f"FAIL: expected iron ore to become black-box boundary input: {dag}")
        return 1
    layout = build_layout_plan(dag, dag_mappings, max_columns=8, spacing=1, lane_width=4)
    if layout["layout_node_count"] != 2:
        print(f"FAIL: expected two layout nodes: {layout}")
        return 1
    if layout["nodes"][1]["item"] != "iron-plate" or layout["nodes"][1]["columns"] != 8 or layout["nodes"][1]["rows"] != 2:
        print(f"FAIL: expected plate node to pack as 8x2 repeated templates: {layout}")
        return 1
    if layout["boundary_inputs"] != [{"item": "iron-ore", "rate_per_minute": 300.0, "side": "left", "reason": "boundary-input"}]:
        print(f"FAIL: expected layout boundary input on the left side: {layout}")
        return 1
    if layout["boundary_outputs"] != [{"item": "iron-gear-wheel", "rate_per_minute": 150, "side": "right"}]:
        print(f"FAIL: expected layout boundary output on the right side: {layout}")
        return 1
    materialized = build_materialized_blueprint(
        dag_mappings,
        target_item="iron-gear-wheel",
        target_rate_per_minute=150,
        max_depth=4,
        max_columns=8,
        spacing=1,
        lane_width=4,
        label="fixture-materialized",
    )
    materialized_blueprint = materialized["blueprint"]
    if materialized_blueprint["label"] != "fixture-materialized":
        print(f"FAIL: expected materialized blueprint label: {materialized}")
        return 1
    if len(materialized_blueprint["entities"]) != 17:
        print(f"FAIL: expected one gear machine plus sixteen plate furnaces: {materialized}")
        return 1
    if len(materialized_blueprint.get("tiles") or []) != 16:
        print(f"FAIL: expected materialized blueprint to copy repeated template tiles: {materialized}")
        return 1
    if materialized_blueprint["entities"][0].get("recipe") != "iron-gear-wheel":
        print(f"FAIL: expected materialized blueprint to preserve recipe: {materialized}")
        return 1
    if materialized_blueprint["entities"][0].get("items", [{}])[0].get("id", {}).get("name") != "speed-module-3":
        print(f"FAIL: expected materialized blueprint to preserve module item stacks: {materialized}")
        return 1
    if decode_blueprint_string(encode_blueprint_string(materialized)) != materialized:
        print("FAIL: materialized blueprint did not round-trip through Factorio string encoding")
        return 1
    connected, connector_summary = materialize_layout_with_summary(
        layout,
        dag_mappings,
        label="fixture-connected",
        connect_boundaries=True,
    )
    if connector_summary["connectors_added"] != 27 or connector_summary["collisions"]:
        print(f"FAIL: expected connector belts without collisions: {connector_summary}")
        return 1
    if [route["status"] for route in connector_summary["routes"]] != ["connected", "stub-only"]:
        print(f"FAIL: expected input connected and output stub-only route states: {connector_summary}")
        return 1
    if connector_summary["routes"][0]["port"]["node_item"] != "iron-plate":
        print(f"FAIL: expected input route to choose the plate template port: {connector_summary}")
        return 1
    if len(connected["blueprint"]["entities"]) != 44:
        print(f"FAIL: expected connected blueprint to add connector belts: {connected}")
        return 1
    if "blueprint_lab_connector_summary" in connected["blueprint"]:
        print(f"FAIL: connector summary must not be written into importable blueprint JSON: {connected}")
        return 1
    if decode_blueprint_string(encode_blueprint_string(connected)) != connected:
        print("FAIL: connected blueprint did not round-trip through Factorio string encoding")
        return 1

    detour_layout = {
        "target_item": "copper-plate",
        "target_rate_per_minute": 60,
        "spacing": 1,
        "estimated_width": 10,
        "estimated_height": 10,
        "boundary_inputs": [],
        "boundary_outputs": [{"item": "copper-plate", "rate_per_minute": 60, "side": "right"}],
        "nodes": [
            {
                "item": "copper-plate",
                "recipe": "fixture-copper",
                "fingerprint": "detour-template",
                "instances": 1,
                "source_width": 4,
                "source_height": 3,
                "source_entity_count": 2,
                "source_tile_count": 0,
                "columns": 1,
                "rows": 1,
                "planned_width": 4,
                "planned_height": 3,
                "x": 4,
                "y": 4,
                "ports": [
                    {"side": "right", "role": "output", "entity_name": "transport-belt", "x": 1, "y": 1},
                    {"side": "right", "role": "output", "entity_name": "fast-transport-belt", "x": 1, "y": 2},
                ],
                "port_counts": [("right:output", 2)],
                "source": "fixture",
                "path": "/detour",
            }
        ],
    }
    detour_mappings = [
        {
            "fingerprint": "detour-template",
            "layout": {
                "entities": [
                    {"name": "transport-belt", "x": 1, "y": 1, "direction": 2, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "stone-furnace", "x": 2, "y": 1, "direction": None, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "fast-transport-belt", "x": 1, "y": 2, "direction": 2, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    detoured, detour_summary = materialize_layout_with_summary(
        detour_layout,
        detour_mappings,
        label="fixture-detoured",
        connect_boundaries=True,
    )
    detour_route = detour_summary["routes"][0]
    if detour_route["status"] != "connected" or detour_route["route_kind"] != "direct":
        print(f"FAIL: expected output route to pick an alternate direct port around a blocked port: {detour_summary}")
        return 1
    if not detour_route["blocked_attempts"] or detour_route["blocked_attempts"][0]["route_kind"] != "direct":
        print(f"FAIL: expected alternate-port report to retain the blocked first port: {detour_summary}")
        return 1
    if detour_summary["collisions"]:
        print(f"FAIL: successful alternate direct route should not keep collisions in the connector summary: {detour_summary}")
        return 1
    if detour_route["port"]["entity_name"] != "fast-transport-belt":
        print(f"FAIL: expected alternate route to choose the fast belt port: {detour_summary}")
        return 1
    if sum(1 for entity in detoured["blueprint"]["entities"] if entity["name"] == "fast-transport-belt") <= 1:
        print(f"FAIL: expected generated connector belts to preserve selected port belt tier: {detoured}")
        return 1
    if decode_blueprint_string(encode_blueprint_string(detoured)) != detoured:
        print("FAIL: detoured blueprint did not round-trip through Factorio string encoding")
        return 1

    replicated_layout = {
        "target_item": "iron-ore",
        "target_rate_per_minute": 3600,
        "spacing": 4,
        "estimated_width": 17,
        "estimated_height": 10,
        "boundary_inputs": [{"item": "metallic-asteroid-chunk", "rate_per_minute": 120, "side": "left", "reason": "boundary-input"}],
        "boundary_outputs": [{"item": "iron-ore", "rate_per_minute": 3600, "side": "right"}],
        "nodes": [
            {
                "item": "iron-ore",
                "recipe": "fixture-crushing",
                "fingerprint": "replicated-port-template",
                "instances": 2,
                "source_width": 4,
                "source_height": 3,
                "source_entity_count": 1,
                "source_tile_count": 0,
                "columns": 2,
                "rows": 1,
                "planned_width": 12,
                "planned_height": 3,
                "planned_net_output_per_minute": 3600,
                "x": 4,
                "y": 4,
                "ports": [
                    {"side": "left", "role": "edge-bus", "entity_name": "turbo-transport-belt", "x": 0, "y": 1},
                    {"side": "left", "role": "input", "entity_name": "turbo-transport-belt", "x": 0, "y": 2},
                    {"side": "right", "role": "output", "entity_name": "turbo-transport-belt", "x": 1, "y": 1},
                ],
                "port_counts": [("left:edge-bus", 1), ("left:input", 1), ("right:output", 1)],
                "source": "fixture",
                "path": "/replicated",
            }
        ],
    }
    replicated_mappings = [
        {
            "fingerprint": "replicated-port-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 1, "y": 1, "direction": 2, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    replicated, replicated_summary = materialize_layout_with_summary(
        replicated_layout,
        replicated_mappings,
        label="fixture-replicated",
        connect_boundaries=True,
    )
    replicated_routes = {route["boundary"]: route for route in replicated_summary["routes"]}
    replicated_route = replicated_routes["output:iron-ore"]
    if replicated_route["status"] != "connected" or replicated_route["port"]["node_instance"] != 1:
        print(f"FAIL: expected output route to use the rightmost replicated template port: {replicated_summary}")
        return 1
    if replicated_summary["collisions"]:
        print(f"FAIL: expected replicated-port routing to avoid collisions: {replicated_summary}")
        return 1
    if replicated_summary["bridges_added"] != 6 or replicated_summary["bridges"][0]["status"] != "connected":
        print(f"FAIL: expected replicated-port routing to bridge adjacent template instances: {replicated_summary}")
        return 1
    replicated_coverage = {item["boundary"]: item for item in replicated_summary["boundary_coverage"]}
    if replicated_coverage["output:iron-ore"]["status"] != "covered" or replicated_coverage["output:iron-ore"]["covered_instances"] != [0, 1] or not replicated_coverage["output:iron-ore"]["meets_required_rate"]:
        print(f"FAIL: expected replicated output coverage to cover both instances and meet the boundary rate: {replicated_summary}")
        return 1
    if replicated_coverage["input:metallic-asteroid-chunk"]["status"] != "partial" or replicated_coverage["input:metallic-asteroid-chunk"]["covered_instances"] != [0]:
        print(f"FAIL: expected lane-aware input coverage to avoid crossing unrelated output bridges: {replicated_summary}")
        return 1
    if sum(1 for entity in replicated["blueprint"]["entities"] if entity["name"] == "turbo-transport-belt") != 15:
        print(f"FAIL: expected replicated-port route and bridge to add turbo belts: {replicated}")
        return 1
    if decode_blueprint_string(encode_blueprint_string(replicated)) != replicated:
        print("FAIL: replicated-port blueprint did not round-trip through Factorio string encoding")
        return 1

    print("PASS: blueprint_lab encodes, decodes, analyzes, learns, decomposes, templates, maps knowledge, estimates base throughput, plans a production DAG and layout, materializes a blueprint skeleton, and generates a seed blueprint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
