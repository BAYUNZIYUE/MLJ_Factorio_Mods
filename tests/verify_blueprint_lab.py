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

    print("PASS: blueprint_lab encodes, decodes, analyzes, learns, decomposes, templates, maps knowledge, estimates base throughput, and generates a seed blueprint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
