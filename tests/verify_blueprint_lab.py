#!/usr/bin/env python3
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.blueprint_lab.analysis import blueprint_metrics, summarize_library
from tools.blueprint_lab.codec import decode_blueprint_string, encode_blueprint_string, walk_nodes
from tools.blueprint_lab.decompose import decompose_blueprint
from tools.blueprint_lab.directions import DIR_EAST, DIR_SOUTH, DIR_WEST
from tools.blueprint_lab.generate import generate_iron_plate_blackbox_seed
from tools.blueprint_lab.learn import learn_library
from tools.blueprint_lab.templates import extract_templates_from_blueprint
from tools.blueprint_lab.prototypes import load_data_raw, target_rate_basis_from_args
from tools.blueprint_lab.template_knowledge import map_template
from tools.blueprint_lab.production_dag import build_production_plan
from tools.blueprint_lab.layout_plan import build_layout_plan
from tools.blueprint_lab.materialize import audit_machine_io, build_materialized_blueprint, materialize_layout_with_summary, prune_template_entities_for_recipe, select_best_materialized_layout
from tools.blueprint_lab.factorio_validate import render_control_lua, write_factorio_config, write_server_settings


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

    validation_lua = render_control_lua(encoded)
    for expected in [
        "stack.import_stack(blueprint_string)",
        "force_unlocks=all_recipes,all_technologies",
        "game.forces.player.create_space_platform",
        "surface.set_tiles(platform_tiles",
        "stack.build_blueprint",
        "manual_fallback=start",
        "surface.create_entity",
        "manual_underground_types=",
        "manual_modules_inserted=",
        "manual_splitter_settings=",
        "created.splitter_filter",
        "created.splitter_input_priority",
        "created.splitter_output_priority",
        "created.set_recipe(entity.recipe, entity.recipe_quality)",
        "runtime_audit_wait_ticks=",
        "recipe_machine_audit",
        "recipe_machine_runtime",
        "recipe_machine_output_items",
        "input_probe_mode",
        'input_probe_mode == "left"',
        'input_probe_mode == "pickup"',
        "input_injection items=",
        "line.force_insert_at",
        "machine_pickup_injection",
        "inserter.pickup_target",
        "inserter.drop_target",
        "pickup_target.get_item_insert_specification",
        "transport_item_audit",
        "transport_item_extents",
        "transport_item_y_distribution",
        "transport_item_samples",
        "right_boundary_transport_item_audit",
        "right_boundary_item_samples",
        "right_boundary_cleanliness",
        "script.on_event(defines.events.on_tick",
    ]:
        if expected not in validation_lua:
            print(f"FAIL: expected Factorio validation scenario to contain {expected}")
            return 1
    server_settings_path = ROOT / ".codex" / "tests" / "blueprint_lab_server_settings_fixture.json"
    server_settings = write_server_settings(server_settings_path).read_text(encoding="utf-8")
    if '"auto_pause": false' not in server_settings or '"visibility"' not in server_settings:
        print(f"FAIL: expected Factorio validation server settings to disable auto-pause: {server_settings}")
        return 1
    factorio_config = write_factorio_config(ROOT / ".codex" / "tests" / "factorio_validation_fixture").read_text(encoding="utf-8")
    if "write-data=" not in factorio_config or "enable-blueprint-storage-cloud-sync=false" not in factorio_config:
        print(f"FAIL: expected Factorio validation config to pin isolated write-data: {factorio_config}")
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
	    },
	    "fixture-byproduct-crushing": {
	      "category": "crushing",
	      "energy_required": 2,
	      "ingredients": [["metallic-asteroid-chunk", 1]],
	      "results": [
	        {"type": "item", "name": "iron-ore", "amount": 20},
	        {"type": "item", "name": "metallic-asteroid-chunk", "amount": 1, "probability": 0.2}
	      ]
	    }
	  },
  "assembling-machine": {
    "assembling-machine-3": {
      "crafting_categories": ["crafting"],
      "crafting_speed": 1.25,
      "module_slots": 4,
      "selection_box": [[-0.5, -0.5], [0.5, 0.5]]
    }
  },
  "inserter": {
    "fast-inserter": {
      "pickup_position": [0, -1],
      "insert_position": [0, 1],
      "selection_box": [[-0.4, -0.4], [0.4, 0.4]]
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
	    "transport-belt": {"speed": 0.03125, "selection_box": [[-0.5, -0.5], [0.5, 0.5]]},
	    "turbo-transport-belt": {"speed": 0.125, "selection_box": [[-0.5, -0.5], [0.5, 0.5]]}
	  },
	  "splitter": {
	    "turbo-splitter": {"speed": 0.125, "selection_box": [[-1, -0.5], [1, 0.5]]}
	  },
	  "underground-belt": {
    "turbo-underground-belt": {"speed": 0.125, "max_distance": 11, "selection_box": [[-0.5, -0.5], [0.5, 0.5]]}
  }
}
""",
        encoding="utf-8",
    )
    knowledge = load_data_raw(data_raw_path)
    if knowledge.quality_effect_multiplier("legendary") != 2.5:
        print(f"FAIL: expected legendary quality to scale positive module effects by 2.5: {knowledge.qualities}")
        return 1
    if knowledge.inserter("fast-inserter") is None or knowledge.entity_box("assembling-machine-3") is None:
        print(f"FAIL: expected data.raw fixture to import inserter endpoints and entity boxes: {knowledge}")
        return 1
    if knowledge.belt("turbo-underground-belt") is None or knowledge.belt("turbo-underground-belt").max_underground_distance != 11:
        print(f"FAIL: expected data.raw fixture to import underground belt max_distance: {knowledge.belts}")
        return 1
    io_audit = audit_machine_io(
        {
            "blueprint": {
                "entities": [
                    {"entity_number": 1, "name": "transport-belt", "position": {"x": 2, "y": 0}, "direction": DIR_EAST},
                    {"entity_number": 2, "name": "fast-inserter", "position": {"x": 2, "y": 1}, "direction": 0},
                    {"entity_number": 3, "name": "assembling-machine-3", "position": {"x": 2, "y": 2}, "recipe": "iron-gear-wheel"},
                    {"entity_number": 4, "name": "fast-inserter", "position": {"x": 2, "y": 3}, "direction": 0},
                    {"entity_number": 5, "name": "transport-belt", "position": {"x": 2, "y": 4}, "direction": DIR_EAST},
                ]
            }
        },
        knowledge,
    )
    if io_audit != [
        {
            "recipe": "iron-gear-wheel",
            "status": "covered",
            "machine_count": 1,
            "input_required": True,
            "output_required": True,
            "machines_with_input": 1,
            "machines_with_output": 1,
            "input_inserter_count": 1,
            "output_inserter_count": 1,
        }
    ]:
        print(f"FAIL: expected inserter endpoint audit to prove one machine input and output: {io_audit}")
        return 1
    pickup_port_layout = {
        "target_item": "iron-gear-wheel",
        "target_rate_per_minute": 150,
        "spacing": 1,
        "estimated_width": 13,
        "estimated_height": 10,
        "boundary_inputs": [{"item": "iron-plate", "rate_per_minute": 300, "side": "left", "reason": "boundary-input"}],
        "boundary_outputs": [],
        "nodes": [
            {
                "item": "iron-gear-wheel",
                "recipe": "iron-gear-wheel",
                "fingerprint": "pickup-port-template",
                "instances": 2,
                "source_width": 3,
                "source_height": 3,
                "source_entity_count": 3,
                "source_tile_count": 0,
                "columns": 2,
                "rows": 1,
                "planned_width": 7,
                "planned_height": 3,
                "planned_net_output_per_minute": 150,
                "x": 4,
                "y": 4,
                "ports": [],
                "port_counts": [],
                "source": "fixture",
                "path": "/pickup-port",
            }
        ],
    }
    pickup_port_mappings = [
        {
            "fingerprint": "pickup-port-template",
            "layout": {
                "entities": [
                    {"name": "transport-belt", "x": 0, "y": 0, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "fast-inserter", "x": 0, "y": 1, "direction": 0, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "assembling-machine-3", "x": 0, "y": 2, "direction": None, "recipe": "iron-gear-wheel", "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, pickup_port_summary = materialize_layout_with_summary(
        pickup_port_layout,
        pickup_port_mappings,
        label="fixture-pickup-port",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    pickup_routes = pickup_port_summary["routes"]
    if (
        len(pickup_routes) != 2
        or any(route["status"] != "connected" for route in pickup_routes)
        or any(route["port"]["role"] != "machine-input" for route in pickup_routes)
        or any(route["port"]["source"] != "machine-io" for route in pickup_routes)
    ):
        print(f"FAIL: expected input boundary route to use a machine I/O pickup belt port: {pickup_port_summary}")
        return 1
    if (
        pickup_port_summary["connectors_added"] != 8
        or pickup_port_summary["input_fanouts_added"] != 0
        or pickup_port_summary["input_fanouts"]
    ):
        print(f"FAIL: expected machine-input routing to connect each copied pickup lane directly without fanout: {pickup_port_summary}")
        return 1
    pickup_coverage = {item["boundary"]: item for item in pickup_port_summary["boundary_coverage"]}
    if pickup_coverage["input:iron-plate"]["status"] != "covered" or pickup_coverage["input:iron-plate"]["covered_instances"] != [0, 1]:
        print(f"FAIL: expected machine-input route to cover both copied machine instances: {pickup_port_summary}")
        return 1
    pickup_flow_counts = Counter(item["status"] for item in pickup_port_summary["belt_flow_audit"])
    if pickup_flow_counts != {"pass": 2}:
        print(f"FAIL: expected machine-input boundary routes to pass belt flow audit: {pickup_port_summary}")
        return 1
    output_port_layout = {
        "target_item": "iron-gear-wheel",
        "target_rate_per_minute": 150,
        "spacing": 1,
        "estimated_width": 14,
        "estimated_height": 14,
        "boundary_inputs": [],
        "boundary_outputs": [{"item": "iron-gear-wheel", "rate_per_minute": 150, "side": "right"}],
        "nodes": [
            {
                "item": "iron-gear-wheel",
                "recipe": "iron-gear-wheel",
                "fingerprint": "output-port-template",
                "instances": 1,
                "source_width": 3,
                "source_height": 6,
                "source_entity_count": 3,
                "source_tile_count": 0,
                "columns": 1,
                "rows": 1,
                "planned_width": 3,
                "planned_height": 6,
                "planned_net_output_per_minute": 150,
                "x": 4,
                "y": 4,
                "ports": [],
                "port_counts": [],
                "source": "fixture",
                "path": "/output-port",
            }
        ],
    }
    output_port_mappings = [
        {
            "fingerprint": "output-port-template",
            "layout": {
                "entities": [
                    {"name": "assembling-machine-3", "x": 0, "y": 2, "direction": None, "recipe": "iron-gear-wheel", "recipe_quality": None, "quality": None},
                    {"name": "fast-inserter", "x": 0, "y": 3, "direction": 0, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "transport-belt", "x": 0, "y": 4, "direction": DIR_SOUTH, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, output_port_summary = materialize_layout_with_summary(
        output_port_layout,
        output_port_mappings,
        label="fixture-output-port",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    output_routes = output_port_summary["routes"]
    if (
        len(output_routes) != 1
        or output_routes[0]["status"] != "connected"
        or output_routes[0]["port"]["role"] != "machine-output"
        or output_routes[0]["route_kind"] != "machine-output-side-load-0"
        or output_routes[0]["port"]["source"] != "machine-io"
    ):
        print(f"FAIL: expected output boundary route to use a machine I/O drop belt port: {output_port_summary}")
        return 1
    output_flow_counts = Counter(item["status"] for item in output_port_summary["belt_flow_audit"])
    if output_flow_counts != {"pass": 1}:
        print(f"FAIL: expected machine-output side-load route to pass belt flow audit: {output_port_summary}")
        return 1
    pruned_entities = prune_template_entities_for_recipe(
        [
            {"name": "transport-belt", "x": 2, "y": 0, "direction": DIR_EAST},
            {"name": "fast-inserter", "x": 2, "y": 1, "direction": 0},
            {"name": "assembling-machine-3", "x": 2, "y": 2, "recipe": "iron-gear-wheel"},
            {"name": "fast-inserter", "x": 2, "y": 3, "direction": 0},
            {"name": "transport-belt", "x": 2, "y": 4, "direction": DIR_EAST},
            {"name": "transport-belt", "x": 12, "y": 8, "direction": DIR_EAST},
            {"name": "fast-inserter", "x": 8, "y": 1, "direction": 0},
            {"name": "assembling-machine-3", "x": 8, "y": 2, "recipe": "gear-reprocessing"},
            {"name": "beacon", "x": 4, "y": 2},
        ],
        target_recipe="iron-gear-wheel",
        knowledge=knowledge,
    )
    pruned_counts = Counter(entity["name"] for entity in pruned_entities)
    pruned_recipes = Counter(entity.get("recipe") for entity in pruned_entities if entity.get("recipe"))
    if pruned_recipes != {"iron-gear-wheel": 1} or pruned_counts["fast-inserter"] != 2 or pruned_counts["transport-belt"] != 2 or pruned_counts["beacon"] != 1:
        print(f"FAIL: expected target-recipe pruning to keep target machine, target inserters, belts, and support entities: {pruned_entities}")
        return 1
    port_lane_pruned = prune_template_entities_for_recipe(
        [
            {"name": "transport-belt", "x": 2, "y": 0, "direction": DIR_EAST},
            {"name": "fast-inserter", "x": 2, "y": 1, "direction": 0},
            {"name": "assembling-machine-3", "x": 2, "y": 2, "recipe": "iron-gear-wheel"},
            {"name": "fast-inserter", "x": 2, "y": 3, "direction": 0},
            {"name": "transport-belt", "x": 2, "y": 4, "direction": DIR_EAST},
            {"name": "turbo-transport-belt", "x": 0, "y": 5, "direction": DIR_EAST},
            {"name": "turbo-underground-belt", "x": 2, "y": 5, "direction": DIR_EAST, "entity_type": "output"},
            {"name": "turbo-transport-belt", "x": 4, "y": 5, "direction": DIR_EAST},
            {"name": "turbo-transport-belt", "x": 0, "y": 7, "direction": DIR_EAST},
        ],
        target_recipe="iron-gear-wheel",
        knowledge=knowledge,
        layout_ports=[
            {"side": "left", "role": "edge-bus", "entity_name": "turbo-transport-belt", "x": 0, "y": 5},
        ],
    )
    port_lane_counts = Counter(entity["name"] for entity in port_lane_pruned)
    if port_lane_counts["turbo-transport-belt"] != 2 or port_lane_counts["turbo-underground-belt"] != 1:
        print(f"FAIL: expected target-recipe pruning to keep the learned boundary port belt lane: {port_lane_pruned}")
        return 1
    if any(entity["name"] == "turbo-transport-belt" and entity.get("y") == 7 for entity in port_lane_pruned):
        print(f"FAIL: expected target-recipe pruning to remove unrelated belt lanes: {port_lane_pruned}")
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
    compact_layout_9 = build_layout_plan(
        {
            "target_item": "iron-plate",
            "target_rate_per_minute": 168.75,
            "root": {
                "item": "iron-plate",
                "recipe": "iron-plate",
                "fingerprint": "plate-template",
                "instances": 9,
                "source": "fixture",
                "path": "/plate",
                "planned_net_output_per_minute": 168.75,
                "rate_basis": "fixture",
            },
            "external_inputs": [{"item": "iron-ore", "rate_per_minute": 168.75, "reason": "boundary-input"}],
        },
        dag_mappings,
        max_columns=12,
        spacing=1,
        lane_width=4,
    )
    if compact_layout_9["nodes"][0]["columns"] != 9 or compact_layout_9["nodes"][0]["rows"] != 1:
        print(f"FAIL: expected compact column choice to keep nine copied modules on one bus row: {compact_layout_9}")
        return 1
    compact_layout_16 = build_layout_plan(
        {
            "target_item": "iron-plate",
            "target_rate_per_minute": 300,
            "root": {
                "item": "iron-plate",
                "recipe": "iron-plate",
                "fingerprint": "plate-template",
                "instances": 16,
                "source": "fixture",
                "path": "/plate",
                "planned_net_output_per_minute": 300,
                "rate_basis": "fixture",
            },
            "external_inputs": [{"item": "iron-ore", "rate_per_minute": 300, "reason": "boundary-input"}],
        },
        dag_mappings,
        max_columns=12,
        spacing=1,
        lane_width=4,
    )
    if compact_layout_16["nodes"][0]["columns"] != 8 or compact_layout_16["nodes"][0]["rows"] != 2:
        print(f"FAIL: expected compact column choice to avoid a sparse 12x2 tail row: {compact_layout_16}")
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
    if connector_summary["connectors_added"] != 59 or connector_summary["collisions"]:
        print(f"FAIL: expected connector belts without collisions: {connector_summary}")
        return 1
    if connector_summary["input_fanouts_added"] != 28:
        print(f"FAIL: expected input fanout belts across both repeated rows: {connector_summary}")
        return 1
    if len(connector_summary["input_fanouts"]) != 14 or any(fanout["status"] != "connected" for fanout in connector_summary["input_fanouts"]):
        print(f"FAIL: expected fourteen connected input fanout segments: {connector_summary}")
        return 1
    if [route["status"] for route in connector_summary["routes"]] != ["connected", "connected", "stub-only"]:
        print(f"FAIL: expected two input connected routes and one output stub-only route: {connector_summary}")
        return 1
    connected_input_routes = [route for route in connector_summary["routes"] if route["boundary"] == "input:iron-ore"]
    if [route["port"]["node_instance"] for route in connected_input_routes] != [0, 8]:
        print(f"FAIL: expected input routes to start each repeated plate row: {connector_summary}")
        return 1
    if any(route["port"]["node_item"] != "iron-plate" for route in connected_input_routes):
        print(f"FAIL: expected input routes to choose plate template ports: {connector_summary}")
        return 1
    connector_coverage = {item["boundary"]: item for item in connector_summary["boundary_coverage"]}
    input_coverage = connector_coverage["input:iron-ore"]
    if (
        input_coverage["status"] != "covered"
        or input_coverage["covered_instances"] != list(range(16))
        or input_coverage["route_count"] != 2
        or input_coverage["start_instances"] != [0, 8]
    ):
        print(f"FAIL: expected input fanout to cover both repeated rows: {connector_summary}")
        return 1
    if connector_coverage["output:iron-gear-wheel"]["status"] != "uncovered":
        print(f"FAIL: expected output route without a learned port to stay uncovered: {connector_summary}")
        return 1
    flow_counts = Counter(item["status"] for item in connector_summary["belt_flow_audit"])
    if flow_counts != {"pass": 2, "failed": 14}:
        print(f"FAIL: expected fixture fanouts to expose non-belt endpoints in belt flow audit: {connector_summary}")
        return 1
    if len(connected["blueprint"]["entities"]) != 76:
        print(f"FAIL: expected connected blueprint to add connector belts: {connected}")
        return 1
    if any(entity["name"] == "transport-belt" and entity.get("direction") != DIR_EAST for entity in connected["blueprint"]["entities"]):
        print(f"FAIL: expected generated connector belts to use Factorio 2.x east direction {DIR_EAST}: {connected}")
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
                    {"name": "transport-belt", "x": 1, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "stone-furnace", "x": 2, "y": 1, "direction": None, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "fast-transport-belt", "x": 1, "y": 2, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
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
                    {"name": "turbo-transport-belt", "x": 0, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 0, "y": 2, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 1, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
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
    if replicated_summary["connectors_added"] != 13 or replicated_summary["input_fanouts_added"] != 0:
        print(f"FAIL: expected replicated routing to reuse the bridge lane for input fanout: {replicated_summary}")
        return 1
    if replicated_summary["bridges_added"] != 6 or replicated_summary["bridges"][0]["status"] != "connected":
        print(f"FAIL: expected replicated-port routing to bridge adjacent template instances: {replicated_summary}")
        return 1
    if (
        len(replicated_summary["input_fanouts"]) != 1
        or replicated_summary["input_fanouts"][0]["status"] != "connected"
        or replicated_summary["input_fanouts"][0]["existing_belts_used"] != 7
    ):
        print(f"FAIL: expected replicated-port routing to fan out through existing bridge-lane belts: {replicated_summary}")
        return 1
    if (
        len(replicated_summary["output_fanins"]) != 1
        or replicated_summary["output_fanins"][0]["status"] != "connected"
        or replicated_summary["output_fanins"][0]["existing_belts_used"] != 7
    ):
        print(f"FAIL: expected replicated-port routing to fan in output through existing bridge-lane belts: {replicated_summary}")
        return 1
    replicated_coverage = {item["boundary"]: item for item in replicated_summary["boundary_coverage"]}
    if replicated_coverage["output:iron-ore"]["status"] != "covered" or replicated_coverage["output:iron-ore"]["covered_instances"] != [0, 1] or not replicated_coverage["output:iron-ore"]["meets_required_rate"]:
        print(f"FAIL: expected replicated output coverage to cover both instances and meet the boundary rate: {replicated_summary}")
        return 1
    if replicated_coverage["input:metallic-asteroid-chunk"]["status"] != "covered" or replicated_coverage["input:metallic-asteroid-chunk"]["covered_instances"] != [0, 1]:
        print(f"FAIL: expected input fanout to cover both replicated input ports: {replicated_summary}")
        return 1
    replicated_flow_counts = Counter(item["status"] for item in replicated_summary["belt_flow_audit"])
    if replicated_flow_counts != {"pass": 5}:
        print(f"FAIL: expected replicated route, bridge, and fanout to pass belt flow audit: {replicated_summary}")
        return 1
    if sum(1 for entity in replicated["blueprint"]["entities"] if entity["name"] == "turbo-transport-belt") != 19:
        print(f"FAIL: expected replicated-port route and bridge to add turbo belts: {replicated}")
        return 1
    if decode_blueprint_string(encode_blueprint_string(replicated)) != replicated:
        print("FAIL: replicated-port blueprint did not round-trip through Factorio string encoding")
        return 1
    capacity_limited_layout = deepcopy(replicated_layout)
    capacity_limited_layout["target_rate_per_minute"] = 7200
    capacity_limited_layout["boundary_outputs"] = [{"item": "iron-ore", "rate_per_minute": 7200, "side": "right"}]
    capacity_limited_layout["nodes"][0]["planned_net_output_per_minute"] = 7200
    _, capacity_limited_summary = materialize_layout_with_summary(
        capacity_limited_layout,
        replicated_mappings,
        label="fixture-capacity-limited",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    capacity_audit = {item["boundary"]: item for item in capacity_limited_summary["boundary_capacity_audit"]}
    if capacity_audit["output:iron-ore"]["status"] != "insufficient" or capacity_audit["output:iron-ore"]["capacity_per_minute"] != 3600:
        print(f"FAIL: expected boundary capacity audit to reject 2x full-belt demand on one turbo belt route: {capacity_limited_summary}")
        return 1
    if capacity_audit["input:metallic-asteroid-chunk"]["status"] != "sufficient":
        print(f"FAIL: expected input boundary capacity audit to pass when one turbo belt covers the input rate: {capacity_limited_summary}")
        return 1
    capacity_multi_lane_layout = deepcopy(capacity_limited_layout)
    capacity_multi_lane_layout["nodes"][0]["source_height"] = 4
    capacity_multi_lane_layout["nodes"][0]["planned_height"] = 4
    capacity_multi_lane_layout["nodes"][0]["ports"] = [
        *capacity_multi_lane_layout["nodes"][0]["ports"],
        {"side": "left", "role": "edge-bus", "entity_name": "turbo-transport-belt", "x": 0, "y": 3},
        {"side": "right", "role": "output", "entity_name": "turbo-transport-belt", "x": 1, "y": 3},
    ]
    capacity_multi_lane_mappings = deepcopy(replicated_mappings)
    capacity_multi_lane_mappings[0]["layout"]["entities"].extend(
        [
            {"name": "turbo-transport-belt", "x": 0, "y": 3, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
            {"name": "turbo-transport-belt", "x": 1, "y": 3, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
        ]
    )
    _, capacity_multi_lane_summary = materialize_layout_with_summary(
        capacity_multi_lane_layout,
        capacity_multi_lane_mappings,
        label="fixture-capacity-multi-lane",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    multi_lane_capacity = {item["boundary"]: item for item in capacity_multi_lane_summary["boundary_capacity_audit"]}
    output_routes = [route for route in capacity_multi_lane_summary["routes"] if route["boundary"] == "output:iron-ore"]
    if (
        multi_lane_capacity["output:iron-ore"]["status"] != "sufficient"
        or multi_lane_capacity["output:iron-ore"]["capacity_per_minute"] != 7200
        or multi_lane_capacity["output:iron-ore"]["proven_capacity_per_minute"] != 7200
        or multi_lane_capacity["output:iron-ore"]["route_count"] != 2
        or len(output_routes) != 2
    ):
        print(f"FAIL: expected 2x full-belt demand to generate two output boundary lanes: {capacity_multi_lane_summary}")
        return 1
    if capacity_multi_lane_summary["collisions"]:
        print(f"FAIL: expected multi-lane boundary routing to avoid connector collisions: {capacity_multi_lane_summary}")
        return 1
    byproduct_layout = {
        "target_item": "iron-ore",
        "target_rate_per_minute": 3600,
        "target_rate_basis": {"kind": "full-belt", "belt_name": "turbo-transport-belt", "belt_count": 1, "items_per_second_per_belt": 60},
        "spacing": 2,
        "estimated_width": 20,
        "estimated_height": 12,
        "boundary_inputs": [{"item": "metallic-asteroid-chunk", "rate_per_minute": 180, "side": "left", "reason": "fixture-input"}],
        "boundary_outputs": [{"item": "iron-ore", "rate_per_minute": 3600, "side": "right"}],
        "nodes": [
            {
                "item": "iron-ore",
                "recipe": "fixture-byproduct-crushing",
                "fingerprint": "byproduct-template",
                "instances": 1,
                "source_width": 4,
                "source_height": 4,
                "source_entity_count": 1,
                "source_tile_count": 0,
                "columns": 1,
                "rows": 1,
                "planned_width": 4,
                "planned_height": 4,
                "planned_net_output_per_minute": 3600,
                "x": 4,
                "y": 4,
                "ports": [{"side": "right", "role": "output", "entity_name": "turbo-transport-belt", "x": 2, "y": 1}],
                "port_counts": [("right:output", 1)],
                "source": "fixture",
                "path": "/byproduct",
            }
        ],
    }
    byproduct_mappings = [
        {
            "fingerprint": "byproduct-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 2, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    byproduct_wrapper, byproduct_summary = materialize_layout_with_summary(
        byproduct_layout,
        byproduct_mappings,
        label="fixture-byproduct-separation",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    byproduct_splitters = [
        entity
        for entity in byproduct_wrapper["blueprint"]["entities"]
        if entity["name"] == "turbo-splitter"
    ]
    byproduct_audit = byproduct_summary["output_byproduct_audit"][0]
    byproduct_item = byproduct_audit["byproducts"][0]
    byproduct_separation = byproduct_summary["output_separations"][0]
    if (
        byproduct_summary["output_separation_splitters"] != 1
        or byproduct_summary["output_separation_overflow_belts"] != 0
        or byproduct_summary["output_separation_recycle_belts"] <= 0
        or len(byproduct_splitters) != 1
        or byproduct_splitters[0].get("filter", {}).get("name") != "iron-ore"
        or byproduct_splitters[0].get("output_priority") != "left"
        or byproduct_separation["status"] != "connected"
        or byproduct_audit["recommended_handling"] != "recycle-to-input-boundary"
        or byproduct_audit["recyclable_byproducts"] != ["metallic-asteroid-chunk"]
        or byproduct_item["same_recipe_input"] is not True
        or byproduct_item["recipe_input_amount"] != 1
        or byproduct_item["input_boundary_rate_per_minute"] != 180
        or byproduct_item["input_boundary_side"] != "left"
        or byproduct_separation["recommended_handling"] != "recycle-to-input-boundary"
        or byproduct_separation["current_handling"] != "recycle-return-to-input-boundary"
        or byproduct_separation["recyclable_byproducts"] != ["metallic-asteroid-chunk"]
        or byproduct_separation["recycle_belts_added"] <= 0
        or byproduct_separation["overflow_belts_added"] != 0
        or byproduct_separation["recycle_exit"]["side"] != "left"
        or byproduct_separation["recycle_flow_audit"]["status"] != "pass"
        or byproduct_separation["recycle_flow_audit"]["positions_checked"] != byproduct_separation["recycle_belts_added"]
        or Counter(item["status"] for item in byproduct_summary["belt_flow_audit"]) != {"pass": 1}
    ):
        print(f"FAIL: expected byproduct output route to build a recycle return route for byproduct-as-input: {byproduct_summary} {byproduct_wrapper}")
        return 1
    capacity_unresolved_lane_mappings = deepcopy(capacity_multi_lane_mappings)
    capacity_unresolved_lane_mappings[0]["layout"]["entities"][-1] = {
        "name": "turbo-splitter",
        "x": 1,
        "y": 3,
        "direction": DIR_EAST,
        "recipe": None,
        "recipe_quality": None,
        "quality": None,
    }
    capacity_unresolved_lane_layout = deepcopy(capacity_multi_lane_layout)
    capacity_unresolved_lane_layout["nodes"][0]["ports"][-1] = {
        "side": "right",
        "role": "output",
        "entity_name": "turbo-splitter",
        "x": 1,
        "y": 3,
    }
    _, capacity_unresolved_lane_summary = materialize_layout_with_summary(
        capacity_unresolved_lane_layout,
        capacity_unresolved_lane_mappings,
        label="fixture-capacity-unresolved-lane",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    unresolved_lane_capacity = {item["boundary"]: item for item in capacity_unresolved_lane_summary["boundary_capacity_audit"]}
    unresolved_output = unresolved_lane_capacity["output:iron-ore"]
    if (
        unresolved_output["status"] != "unresolved"
        or unresolved_output["capacity_per_minute"] != 7200
        or unresolved_output["proven_capacity_per_minute"] != 3600
        or unresolved_output["unresolved_capacity_per_minute"] != 3600
        or not unresolved_output["structural_meets_required_rate"]
        or unresolved_output["meets_required_rate"]
    ):
        print(f"FAIL: expected structural 2x capacity with one unresolved lane to stay unresolved, not sufficient: {capacity_unresolved_lane_summary}")
        return 1
    selection_layout = {
        "target_item": "iron-ore",
        "target_rate_per_minute": 7200,
        "target_rate_basis": {"kind": "full-belt", "belt_name": "turbo-transport-belt", "belt_count": 2, "items_per_second_per_belt": 60},
        "max_columns": 5,
        "spacing": 2,
        "lane_width": 4,
        "estimated_width": 96,
        "estimated_height": 23.5,
        "boundary_inputs": [{"item": "metallic-asteroid-chunk", "rate_per_minute": 120, "side": "left", "reason": "boundary-input"}],
        "boundary_outputs": [{"item": "iron-ore", "rate_per_minute": 7200, "side": "right"}],
        "nodes": [
            {
                "item": "iron-ore",
                "recipe": "fixture-crushing",
                "fingerprint": "selection-template",
                "instances": 5,
                "source_width": 16,
                "source_height": 15.5,
                "source_entity_count": 3,
                "source_tile_count": 0,
                "columns": 5,
                "rows": 1,
                "planned_width": 88,
                "planned_height": 15.5,
                "planned_net_output_per_minute": 7875,
                "x": 4,
                "y": 4,
                "ports": [
                    {"side": "left", "role": "input", "entity_name": "turbo-transport-belt", "x": 0, "y": 1},
                    {"side": "right", "role": "output", "entity_name": "turbo-transport-belt", "x": 15, "y": 1},
                    {"side": "right", "role": "output", "entity_name": "turbo-underground-belt", "entity_type": "input", "x": 15, "y": 0},
                ],
                "port_counts": [("left:input", 1), ("right:output", 2)],
                "source": "fixture",
                "path": "/selection",
            }
        ],
    }
    selection_mappings = [
        {
            "fingerprint": "selection-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 0, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 15, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-underground-belt", "x": 15, "y": 0, "direction": DIR_EAST, "entity_type": "input", "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, selected_summary, selected_layout = select_best_materialized_layout(
        selection_layout,
        selection_mappings,
        label="fixture-selected-layout",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    selected_flow_counts = Counter(item["status"] for item in selected_summary["belt_flow_audit"])
    selected_capacity = {item["boundary"]: item for item in selected_summary["boundary_capacity_audit"]}
    selected_contract = {item["boundary"]: item for item in selected_summary["boundary_contract_audit"]}
    if (
        selected_layout["nodes"][0]["columns"] != 3
        or selected_layout["nodes"][0]["rows"] != 2
        or selected_flow_counts != {"pass": 13}
        or selected_capacity["output:iron-ore"]["status"] != "sufficient"
        or selected_capacity["output:iron-ore"]["proven_capacity_per_minute"] != 7200
        or selected_contract["output:iron-ore"]["status"] != "exact"
        or selected_contract["output:iron-ore"]["route_count"] != 2
        or selected_summary["output_fanins_added"] <= 0
    ):
        print(f"FAIL: expected post-materialize layout selection to prefer the tightest exact 2-belt proven-flow grid over unresolved or over-provisioned layouts: {selected_layout} {selected_summary}")
        return 1

    semantic_fail_mappings = [
        {
            "fingerprint": "replicated-port-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 0, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 0, "y": 2, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 1, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 2, "y": 2, "direction": DIR_WEST, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    semantic_fail_layout = deepcopy(replicated_layout)
    semantic_fail_layout["boundary_outputs"] = []
    semantic_fail_layout["nodes"][0]["ports"] = [
        port for port in semantic_fail_layout["nodes"][0]["ports"]
        if not (port["side"] == "right" and port["role"] == "output")
    ]
    _, semantic_fail_summary = materialize_layout_with_summary(
        semantic_fail_layout,
        semantic_fail_mappings,
        label="fixture-semantic-fail",
        connect_boundaries=True,
    )
    failed_flow = [item for item in semantic_fail_summary["belt_flow_audit"] if item["status"] == "failed"]
    if not failed_flow or not any(failure.get("reason") == "wrong-flow-direction" for item in failed_flow for failure in item["failures"]):
        print(f"FAIL: expected belt flow audit to fail when an existing fanout belt points west: {semantic_fail_summary}")
        return 1

    underground_mappings = [
        {
            "fingerprint": "replicated-port-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 0, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 0, "y": 2, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-underground-belt", "x": 1, "y": 1, "direction": DIR_EAST, "entity_type": "output", "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    underground, underground_summary = materialize_layout_with_summary(
        replicated_layout,
        underground_mappings,
        label="fixture-underground",
        connect_boundaries=True,
    )
    if not any(entity["name"] == "turbo-underground-belt" and entity.get("type") == "output" for entity in underground["blueprint"]["entities"]):
        print(f"FAIL: expected materializer to preserve underground-belt type: {underground}")
        return 1
    underground_flow_counts = Counter(item["status"] for item in underground_summary["belt_flow_audit"])
    if underground_flow_counts != {"pass": 3, "unresolved": 2}:
        print(f"FAIL: expected middle underground output to stay unresolved in reused fanout audit: {underground_summary}")
        return 1

    underground_input_mappings = [
        {
            "fingerprint": "replicated-port-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 0, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 0, "y": 2, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-underground-belt", "x": 1, "y": 1, "direction": DIR_EAST, "entity_type": "input", "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, underground_input_summary = materialize_layout_with_summary(
        replicated_layout,
        underground_input_mappings,
        label="fixture-underground-input",
        connect_boundaries=True,
    )
    if not any(item["status"] == "unresolved" and any(entry.get("reason") == "underground-belt-endpoint-not-proven" for entry in item["unresolved"]) for item in underground_input_summary["belt_flow_audit"]):
        print(f"FAIL: expected east-facing underground input to remain unresolved without pair tracing: {underground_input_summary}")
        return 1
    underground_pair_layout = deepcopy(replicated_layout)
    underground_pair_layout["estimated_width"] = 25
    underground_pair_layout["nodes"][0]["source_width"] = 8
    underground_pair_layout["nodes"][0]["planned_width"] = 20
    underground_pair_mappings = [
        {
            "fingerprint": "replicated-port-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 0, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 1, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-underground-belt", "x": 2, "y": 1, "direction": DIR_EAST, "entity_type": "input", "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-underground-belt", "x": 6, "y": 1, "direction": DIR_EAST, "entity_type": "output", "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, underground_pair_summary = materialize_layout_with_summary(
        underground_pair_layout,
        underground_pair_mappings,
        label="fixture-underground-pair",
        connect_boundaries=True,
    )
    pair_audit = [
        item
        for item in underground_pair_summary["belt_flow_audit"]
        if item["segment_type"] == "inter-instance-bridge" and item.get("underground_pairs")
    ]
    if not pair_audit or any(item["status"] != "pass" for item in pair_audit):
        print(f"FAIL: expected explicit underground input/output pair to pass belt flow audit: {underground_pair_summary}")
        return 1
    pair_positions = pair_audit[0]["underground_pairs"][0]
    if pair_positions["input_x"] != 6.0 or pair_positions["output_x"] != 10.0 or pair_positions["hidden_positions"] != 3:
        print(f"FAIL: expected underground pair tracing to record hidden span: {underground_pair_summary}")
        return 1

    splitter_mapping = [
        {
            "fingerprint": "splitter-template",
            "layout": {
                "entities": [
                    {
                        "name": "turbo-splitter",
                        "x": 0,
                        "y": 0,
                        "direction": DIR_EAST,
                        "filter": {"name": "iron-ore", "quality": "normal", "comparator": "="},
                        "output_priority": "left",
                        "input_priority": "right",
                    },
                ],
                "tiles": [],
            },
        }
    ]
    splitter_layout = deepcopy(replicated_layout)
    splitter_layout["nodes"][0]["fingerprint"] = "splitter-template"
    splitter_layout["nodes"][0]["instances"] = 1
    splitter_layout["nodes"][0]["columns"] = 1
    splitter_layout["nodes"][0]["rows"] = 1
    splitter_layout["boundary_inputs"] = []
    splitter_layout["boundary_outputs"] = []
    splitter_wrapper, _ = materialize_layout_with_summary(
        splitter_layout,
        splitter_mapping,
        label="fixture-splitter-fields",
        connect_boundaries=False,
    )
    splitter_entity = splitter_wrapper["blueprint"]["entities"][0]
    if (
        splitter_entity.get("filter", {}).get("name") != "iron-ore"
        or splitter_entity.get("output_priority") != "left"
        or splitter_entity.get("input_priority") != "right"
    ):
        print(f"FAIL: expected materializer to preserve splitter filter and priorities: {splitter_wrapper}")
        return 1

    print("PASS: blueprint_lab encodes, decodes, analyzes, learns, decomposes, templates, maps knowledge, estimates base throughput, plans a production DAG and layout, materializes a blueprint skeleton, and generates a seed blueprint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
