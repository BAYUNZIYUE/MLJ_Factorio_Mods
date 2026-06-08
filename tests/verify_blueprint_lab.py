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
from tools.blueprint_lab.prototypes import load_data_raw
from tools.blueprint_lab.template_knowledge import map_template
from tools.blueprint_lab.production_dag import build_production_plan
from tools.blueprint_lab.layout_plan import build_layout_plan
from tools.blueprint_lab.materialize import build_materialized_blueprint


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
  }
}
""",
        encoding="utf-8",
    )
    knowledge = load_data_raw(data_raw_path)
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
        max_depth=4,
    )
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
    if decode_blueprint_string(encode_blueprint_string(materialized)) != materialized:
        print("FAIL: materialized blueprint did not round-trip through Factorio string encoding")
        return 1

    print("PASS: blueprint_lab encodes, decodes, analyzes, learns, decomposes, templates, maps knowledge, estimates base throughput, plans a production DAG and layout, materializes a blueprint skeleton, and generates a seed blueprint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
