#!/usr/bin/env python3
from collections import Counter
from copy import deepcopy
import json
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
from tools.blueprint_lab.runtime_proof import build_runtime_proof, render_markdown_report as render_runtime_proof_markdown_report
from tools.blueprint_lab.stage4_compare import build_comparison, candidate_lessons, candidate_score, summarize_candidate
from tools.blueprint_lab.stage4_report import build_stage4_report, render_markdown_report as render_stage4_markdown_report
from tools.blueprint_lab.stage4_generate import build_stage4_generation_package, package_summary, render_package_markdown
from tools.blueprint_lab.templates import extract_templates_from_blueprint
from tools.blueprint_lab.prototypes import load_data_raw, target_rate_basis_from_args
from tools.blueprint_lab.template_knowledge import map_template
from tools.blueprint_lab.production_dag import build_production_plan
from tools.blueprint_lab.layout_plan import build_layout_plan
from tools.blueprint_lab.materialize import audit_machine_io, audit_machine_output_expansion, build_materialized_blueprint, materialize_layout_with_summary, materialize_machine_output_expansions, materialized_layout_score, prune_template_entities_for_recipe, render_markdown_report as render_materialize_markdown_report, select_best_materialized_layout
from tools.blueprint_lab.factorio_validate import (
    effective_runtime_audit_wait_ticks,
    render_control_lua,
    write_factorio_config,
    write_server_settings,
)


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
        "manual_inserter_filters=",
        "created.splitter_filter",
        "created.splitter_input_priority",
        "created.splitter_output_priority",
        "created.set_filter(target_index, filter)",
        "created.set_recipe(entity.recipe, entity.recipe_quality)",
        "runtime_audit_wait_ticks=",
        "sustained_input_interval_ticks=",
        "sustained_input_injection",
        "throughput_window_ticks=",
        "throughput_probe_x",
        "math.abs(entity.position.x - max_x) <= 0.1",
        "right_boundary_throughput_window",
        "probe_x=",
        "right_boundary_throughput_lane_window",
        "right_boundary_throughput_summary",
        "right_boundary_throughput_lane_summary",
        "line.remove_item",
        "recipe_machine_audit",
        "recipe_machine_runtime",
        "recipe_machine_output_items",
        "output_unload_audit",
        "output_unload_samples",
        "nearest_recipe_machine_to_position",
        "invalid_output_inserters=",
        "machine_output_items=",
        "drop_line_product_items=",
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
    if effective_runtime_audit_wait_ticks(2, 120) != 120 or effective_runtime_audit_wait_ticks(2400, 120) != 2400:
        print("FAIL: expected Factorio validation to wait at least until --until-tick before runtime audit")
        return 1
    sustained_lua = render_control_lua(encoded, input_probe="left", runtime_audit_wait_ticks=2400, sustained_input_interval_ticks=300)
    if "local sustained_input_interval_ticks = 300" not in sustained_lua or "sustained_input_cycles" not in sustained_lua:
        print("FAIL: expected Factorio validation scenario to support sustained left-boundary input injection")
        return 1
    throughput_lua = render_control_lua(encoded, runtime_audit_wait_ticks=2400, throughput_window_ticks=300, throughput_target_item="iron-ore")
    if "local throughput_window_ticks = 300" not in throughput_lua or 'local throughput_target_item_name = [[iron-ore]]' not in throughput_lua:
        print("FAIL: expected Factorio validation scenario to support right-boundary throughput windows")
        return 1
    if "throughput_removed_target_items" not in throughput_lua or "target_per_minute" not in throughput_lua:
        print("FAIL: expected Factorio validation scenario to summarize right-boundary target throughput")
        return 1

    learned = learn_library([tmp])
    categories = {item["category"]: item for item in learned["category_summaries"]}
    if "smelting" not in categories:
        print(f"FAIL: expected generated seed to classify as smelting: {learned}")
        return 1
    if not learned["blackbox_candidates"]:
        print(f"FAIL: expected generated seed to be a black-box candidate: {learned}")
        return 1
    stage4 = build_stage4_report([tmp], top=3)
    stage4_decisions = {item["decision"]: item for item in stage4["design_decisions"]}
    stage4_milestones = {item["name"]: item for item in stage4["next_generator_milestones"]}
    stage4_markdown = render_stage4_markdown_report(stage4)
    if (
        stage4["inputs"]["blueprint_count"] != 1
        or not stage4["knowledge_sources"]
        or "game" not in stage4["knowledge_layers"]
        or "smelting" not in stage4["compactness_profile"]
        or "ship_tileable_single_recipe_modules_first" not in stage4_decisions
        or "strict-external-boundary-compression" not in stage4_milestones
        or "known-insufficient" not in json.dumps(stage4, ensure_ascii=False)
        or "Blueprint Lab Stage 4 Report" not in stage4_markdown
    ):
        print(f"FAIL: expected stage4 report to preserve corpus lessons, knowledge sources, and strict-boundary milestones: {stage4}")
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
    },
    "bulk-inserter": {
      "pickup_position": [0, -1],
      "insert_position": [0, 1],
      "selection_box": [[-0.4, -0.4], [0.4, 0.4]]
    },
    "stack-inserter": {
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
    recipe_tmp = ROOT / ".codex" / "tests" / "blueprint_lab_recipe_template.txt"
    recipe_grid_entities = []
    for row in range(6):
        for column in range(10):
            recipe_grid_entities.append(
                {
                    "entity_number": len(recipe_grid_entities) + 1,
                    "name": "assembling-machine-3",
                    "position": {"x": 1 + column * 4, "y": 1 + row * 4},
                    "recipe": "iron-gear-wheel",
                    "items": [{"id": {"name": "speed-module-3"}, "items": {"in_inventory": [{"inventory": 4, "stack": 0}]}}],
                }
            )
    recipe_tmp.write_text(
        encode_blueprint_string(
            {
                "blueprint": {
                    "item": "blueprint",
                    "label": "fixture-iron-gear-wheel-module",
                    "entities": recipe_grid_entities,
                }
            }
        ),
        encoding="utf-8",
    )
    stage4_with_data = build_stage4_report([recipe_tmp], top=3, data_raw_json=data_raw_path, cell_size=4)
    module_library = stage4_with_data.get("module_library") or {}
    produced_items = {item["item"]: item for item in module_library.get("produced_items") or []}
    gear_options = produced_items.get("iron-gear-wheel", {}).get("best_options") or []
    if (
        module_library.get("produced_item_count", 0) < 1
        or "iron-gear-wheel" not in produced_items
        or gear_options[0]["recipe"] != "iron-gear-wheel"
        or gear_options[0]["net_target_rate_per_instance"] <= 0
    ):
        print(f"FAIL: expected stage4 data.raw module library to expose iron-gear-wheel production options: {stage4_with_data}")
        return 1
    runtime_log_path = ROOT / ".codex" / "tests" / "blueprint_lab_runtime_proof_fixture.log"
    runtime_log_path.write_text(
        """
1.000 Script @__level__/control.lua:1: BLUEPRINT_LAB_VALIDATION import_result=0
1.001 Script @__level__/control.lua:2: BLUEPRINT_LAB_VALIDATION blueprint_entities=10 blueprint_tiles=0
1.002 Script @__level__/control.lua:3: BLUEPRINT_LAB_VALIDATION manual_entities=10 manual_failures=0 manual_recipe_set=1 manual_recipe_failures=0
1.500 Script @__level__/control.lua:4: BLUEPRINT_LAB_VALIDATION right_boundary_throughput_window index=1 tick=300 observed_ticks=300 max_x=10.5 probe_x=nil belts=1 lines=2 target_item=iron-gear-wheel target_removed=80 target_per_minute=160.0 product_items=iron-gear-wheel:80 input_items=
1.501 Script @__level__/control.lua:5: BLUEPRINT_LAB_VALIDATION right_boundary_throughput_lane_window index=1 target_item=iron-gear-wheel target_by_line=x=10.5/y=1.5/line=1:40,x=10.5/y=2.5/line=2:40
1.900 Script @__level__/control.lua:6: BLUEPRINT_LAB_VALIDATION right_boundary_throughput_window index=2 tick=600 observed_ticks=300 max_x=10.5 probe_x=nil belts=1 lines=2 target_item=iron-gear-wheel target_removed=120 target_per_minute=240.0 product_items=iron-gear-wheel:120 input_items=
1.901 Script @__level__/control.lua:7: BLUEPRINT_LAB_VALIDATION right_boundary_throughput_lane_window index=2 target_item=iron-gear-wheel target_by_line=x=10.5/y=1.5/line=1:50,x=10.5/y=2.5/line=2:70
2.000 Script @__level__/control.lua:8: BLUEPRINT_LAB_VALIDATION right_boundary_throughput_summary window_ticks=300 windows=2 observed_ticks=600 probe_x=nil target_item=iron-gear-wheel target_removed=200 target_per_minute=200.0 product_items=iron-gear-wheel:200 input_items=
2.001 Script @__level__/control.lua:9: BLUEPRINT_LAB_VALIDATION right_boundary_cleanliness status=clean product_items=5 input_items=0
2.002 Script @__level__/control.lua:10: BLUEPRINT_LAB_VALIDATION right_boundary_throughput_lane_summary target_item=iron-gear-wheel target_by_line=x=10.5/y=1.5/line=1:90,x=10.5/y=2.5/line=2:110
2.003 Script @__level__/control.lua:11: BLUEPRINT_LAB_VALIDATION invalid_output_inserters=0 samples=
2.004 Script @__level__/control.lua:12: BLUEPRINT_LAB_VALIDATION success
""",
        encoding="utf-8",
    )
    runtime_proof = build_runtime_proof(
        runtime_log_path,
        target_item="iron-gear-wheel",
        target_rate_per_minute=150,
    )
    empty_boundary_log_path = ROOT / ".codex" / "tests" / "blueprint_lab_runtime_empty_boundary_fixture.log"
    empty_boundary_log_path.write_text(
        runtime_log_path.read_text(encoding="utf-8").replace("status=clean product_items=5", "status=empty product_items=0"),
        encoding="utf-8",
    )
    empty_boundary_runtime_proof = build_runtime_proof(
        empty_boundary_log_path,
        target_item="iron-gear-wheel",
        target_rate_per_minute=150,
    )
    if (
        runtime_proof["status"] != "runtime-proven"
        or runtime_proof["throughput_summary"]["target_per_minute"] != 200.0
        or runtime_proof["throughput_lane_summary"]["line_count"] != 2
        or runtime_proof["throughput_lane_summary"]["spread_target_items"] != 20
        or runtime_proof["throughput_lane_summary"]["per_minute_by_line"]["x=10.5/y=1.5/line=1"] != 540.0
        or runtime_proof["throughput_window_diagnostics"]["window_count"] != 2
        or runtime_proof["throughput_window_diagnostics"]["best_window"]["target_per_minute"] != 240.0
        or runtime_proof["throughput_window_diagnostics"]["last_window"]["target_rate_deficit_per_minute"] != 0.0
        or runtime_proof["throughput_window_diagnostics"]["windows_at_or_above_target"] != 2
        or runtime_proof["right_boundary_cleanliness"]["status"] != "clean"
        or runtime_proof["invalid_output_inserters"]["count"] != 0
        or "Best throughput window: 240.0/min" not in render_runtime_proof_markdown_report(runtime_proof)
        or "Blueprint Runtime Proof Report" not in render_runtime_proof_markdown_report(runtime_proof)
    ):
        print(f"FAIL: expected runtime proof parser to mark clean above-target throughput as proven: {runtime_proof}")
        return 1
    if empty_boundary_runtime_proof["status"] != "runtime-proven":
        print(f"FAIL: expected runtime proof parser to accept empty right boundary after throughput drain: {empty_boundary_runtime_proof}")
        return 1
    stage4_package = build_stage4_generation_package(
        [recipe_tmp],
        data_raw_json=data_raw_path,
        target_item="iron-gear-wheel",
        target_rate_per_minute=150,
        external_items=["iron-plate"],
        top=3,
        cell_size=4,
        max_columns=3,
        spacing=1,
        lane_width=4,
        label="fixture-stage4-package",
        runtime_log=runtime_log_path,
    )
    stage4_package_summary = package_summary(stage4_package, blueprint_output=ROOT / ".codex" / "tests" / "fixture-stage4-package.txt")
    stage4_package_markdown = render_package_markdown(stage4_package)
    if (
        "module_library" not in stage4_package["stage4_report"]
        or stage4_package_summary["target_item"] != "iron-gear-wheel"
        or stage4_package_summary["target_rate_per_minute"] != 150
        or stage4_package_summary["module_library"]["produced_item_count"] < 1
        or stage4_package["materialized_summary"]["label"] != "fixture-stage4-package"
        or stage4_package_summary["runtime_proof"]["status"] != "runtime-proven"
        or stage4_package_summary["runtime_proof"]["throughput_lane_summary"]["line_count"] != 2
        or decode_blueprint_string(encode_blueprint_string(stage4_package["blueprint"])) != stage4_package["blueprint"]
        or "Runtime Proof" not in stage4_package_markdown
        or "Blueprint Lab Stage 4 Generation Package" not in stage4_package_markdown
    ):
        print(f"FAIL: expected stage4 generation package to combine report, module library, summary, and blueprint: {stage4_package_summary}")
        return 1
    candidate_a_path = ROOT / ".codex" / "tests" / "blueprint_lab_candidate_a.json"
    candidate_b_path = ROOT / ".codex" / "tests" / "blueprint_lab_candidate_b.json"
    candidate_c_path = ROOT / ".codex" / "tests" / "blueprint_lab_candidate_c.json"
    runtime_proof_path = ROOT / ".codex" / "tests" / "blueprint_lab_runtime_proof_fixture.json"
    below_target_runtime_proof_path = ROOT / ".codex" / "tests" / "blueprint_lab_runtime_below_target_fixture.json"
    candidate_a_path.write_text(
        json.dumps(
            {
                "target_item": "iron-gear-wheel",
                "target_rate_per_minute": 150,
                "entity_count": 10,
                "tile_count": 0,
                "width": 10,
                "height": 10,
                "route_status_counts": {"connected": 3},
                "boundary_contract_audit": [{"boundary": "output:iron-gear-wheel", "status": "over-provisioned", "expected_belt_count": 1, "route_count": 3}],
                "boundary_capacity_audit": [{"boundary": "output:iron-gear-wheel", "status": "sufficient", "proven_capacity_per_minute": 300, "required_rate_per_minute": 150}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_b_path.write_text(
        json.dumps(
            {
                "target_item": "iron-gear-wheel",
                "target_rate_per_minute": 150,
                "entity_count": 8,
                "tile_count": 0,
                "width": 8,
                "height": 8,
                "route_status_counts": {"connected": 1},
                "connector_summary": {
                    "boundary_contract_audit": [{"boundary": "output:iron-gear-wheel", "status": "exact", "expected_belt_count": 1, "route_count": 1}],
                    "boundary_capacity_audit": [{"boundary": "output:iron-gear-wheel", "status": "unresolved", "proven_capacity_per_minute": 0, "required_rate_per_minute": 150}],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    candidate_c_path.write_text(
        json.dumps(
            {
                "target_item": "iron-gear-wheel",
                "target_rate_per_minute": 150,
                "entity_count": 9,
                "tile_count": 0,
                "width": 9,
                "height": 9,
                "route_status_counts": {"connected": 1},
                "boundary_contract_audit": [{"boundary": "output:iron-gear-wheel", "status": "exact", "expected_belt_count": 1, "route_count": 1}],
                "boundary_capacity_audit": [{"boundary": "output:iron-gear-wheel", "status": "sufficient", "proven_capacity_per_minute": 150, "required_rate_per_minute": 150}],
                "output_separations": [{"current_handling": "pre-fanin-finite-overflow-buffer", "status": "connected"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    runtime_proof_path.write_text(json.dumps(runtime_proof, ensure_ascii=False), encoding="utf-8")
    below_target_runtime_proof = deepcopy(runtime_proof)
    below_target_runtime_proof["status"] = "below-target"
    below_target_runtime_proof["reasons"] = ["throughput-below-target"]
    below_target_runtime_proof["throughput_summary"]["target_per_minute"] = 140.0
    below_target_runtime_proof["throughput_window_diagnostics"]["best_window"]["target_per_minute"] = 149.0
    below_target_runtime_proof["throughput_window_diagnostics"]["best_window"]["target_rate_deficit_per_minute"] = 1.0
    below_target_runtime_proof["throughput_window_diagnostics"]["last_window"]["target_per_minute"] = 149.0
    below_target_runtime_proof["throughput_window_diagnostics"]["last_window"]["target_rate_deficit_per_minute"] = 1.0
    below_target_runtime_proof["throughput_window_diagnostics"]["windows_at_or_above_target"] = 0
    below_target_runtime_proof_path.write_text(json.dumps(below_target_runtime_proof, ensure_ascii=False), encoding="utf-8")
    comparison = build_comparison(
        [
            summarize_candidate(label="runtime-over-provisioned", summary_path=candidate_a_path, runtime_proof_path=runtime_proof_path),
            summarize_candidate(label="exact-near-miss", summary_path=candidate_c_path, runtime_proof_path=below_target_runtime_proof_path),
            summarize_candidate(label="exact-unresolved", summary_path=candidate_b_path),
        ]
    )
    if (
        comparison["recommended_label"] != "runtime-over-provisioned"
        or comparison["strict_boundary_candidates"] != ["exact-near-miss", "exact-unresolved"]
        or comparison["runtime_proven_candidates"] != ["runtime-over-provisioned"]
        or comparison["strict_near_miss_candidates"] != ["exact-near-miss"]
        or [item["label"] for item in comparison["candidates"]] != ["runtime-over-provisioned", "exact-near-miss", "exact-unresolved"]
        or "runtime proof outranks" not in comparison["recommended_reason"]
        or "best throughput window reached 240.0/min" not in "\n".join(comparison["candidates"][0]["lessons"])
        or "best throughput window reached 149.0/min with deficit 1.0/min" not in "\n".join(comparison["candidates"][1]["lessons"])
        or comparison["candidates"][1]["runtime_gap_analysis"]["category"] != "strict-near-miss"
        or comparison["candidates"][1]["runtime_gap_analysis"]["next_action"] != "tune-final-two-belt-compression-geometry"
        or "strict near-miss" not in "\n".join(comparison["candidates"][1]["lessons"])
        or comparison["candidates"][1]["output_separation_handling_counts"].get("pre-fanin-finite-overflow-buffer") != 1
        or "pre-fanin byproduct separator" not in "\n".join(comparison["candidates"][1]["lessons"])
    ):
        print(f"FAIL: expected stage4 comparison to prefer runtime-proven candidate over exact unresolved candidate: {comparison}")
        return 1
    sideload_candidate = deepcopy(comparison["candidates"][1])
    sideload_candidate["runtime_proof"] = below_target_runtime_proof
    sideload_candidate["output_separation_handling_counts"] = {"pre-fanin-recycle-sideload-to-input-lane": 1}
    missing_runtime_candidate = deepcopy(comparison["candidates"][2])
    if (
        candidate_score(sideload_candidate) <= candidate_score(missing_runtime_candidate)
        or "side-load into input lanes" not in "\n".join(candidate_lessons(sideload_candidate))
    ):
        print("FAIL: expected below-target pre-fanin sideload candidate to rank as experimental negative evidence")
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
    output_port_wrapper, output_port_summary = materialize_layout_with_summary(
        output_port_layout,
        output_port_mappings,
        label="fixture-output-port",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    if Counter(entity["name"] for entity in output_port_wrapper["blueprint"]["entities"])["stack-inserter"] != 1:
        print(f"FAIL: expected materializer to upgrade target output inserter to stack-inserter: {output_port_wrapper}")
        return 1
    if output_port_summary.get("output_inserter_upgrades", [{}])[0].get("materialized_count") != 1:
        print(f"FAIL: expected output inserter upgrade summary: {output_port_summary}")
        return 1
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
    output_expansion = audit_machine_output_expansion(output_port_wrapper, knowledge)
    expansion_by_recipe = {item["recipe"]: item for item in output_expansion}
    if (
        "iron-gear-wheel" not in expansion_by_recipe
        or expansion_by_recipe["iron-gear-wheel"]["status"] != "expandable"
        or expansion_by_recipe["iron-gear-wheel"]["candidate_count"] <= 0
        or expansion_by_recipe["iron-gear-wheel"]["expandable_machine_count"] != 1
    ):
        print(f"FAIL: expected machine output expansion audit to find safe candidate inserter/drop-belt positions: {output_expansion}")
        return 1
    expansion_fixture_entities = [
        {"entity_number": 1, "name": "assembling-machine-3", "position": {"x": 4, "y": 4}, "recipe": "iron-gear-wheel"},
        {"entity_number": 2, "name": "stack-inserter", "position": {"x": 4, "y": 3}, "direction": DIR_SOUTH},
        {"entity_number": 3, "name": "transport-belt", "position": {"x": 4, "y": 2}, "direction": DIR_EAST},
        {"entity_number": 4, "name": "transport-belt", "position": {"x": 6, "y": 4}, "direction": DIR_EAST},
    ]
    expansion_summary = materialize_machine_output_expansions(expansion_fixture_entities, knowledge)
    if (
        expansion_summary.get("inserters_added") != 2
        or expansion_summary.get("drop_belts_added") != 0
        or expansion_summary.get("machines_expanded") != 1
        or Counter(entity["name"] for entity in expansion_fixture_entities)["stack-inserter"] != 3
    ):
        print(f"FAIL: expected materialized output expansion to add two extra stack inserters to an existing drop belt: {expansion_summary} {expansion_fixture_entities}")
        return 1
    filtered_fixture_entities = [
        {"entity_number": 1, "name": "assembling-machine-3", "position": {"x": 4, "y": 4}, "recipe": "iron-gear-wheel"},
        {"entity_number": 2, "name": "stack-inserter", "position": {"x": 4, "y": 3}, "direction": DIR_SOUTH},
        {"entity_number": 3, "name": "transport-belt", "position": {"x": 4, "y": 2}, "direction": DIR_EAST},
        {"entity_number": 4, "name": "transport-belt", "position": {"x": 6, "y": 4}, "direction": DIR_EAST},
    ]
    materialize_machine_output_expansions(filtered_fixture_entities, knowledge, target_item="iron-gear-wheel")
    added_filtered_inserters = [
        entity
        for entity in filtered_fixture_entities
        if entity["name"] == "stack-inserter" and entity.get("filters")
    ]
    if (
        len(added_filtered_inserters) != 2
        or added_filtered_inserters[0]["filters"][0]["name"] != "iron-gear-wheel"
        or added_filtered_inserters[1]["filters"][0]["name"] != "iron-gear-wheel"
        or added_filtered_inserters[0].get("use_filters") is not True
        or added_filtered_inserters[1].get("use_filters") is not True
    ):
        print(f"FAIL: expected generated output expansion inserters to filter the target product: {filtered_fixture_entities}")
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
    full_belt_overbuild_dag = build_production_plan(
        [
            {
                "fingerprint": "full-belt-overbuild-template",
                "candidate_role": "production-template",
                "label": "full-belt-overbuild",
                "source": "fixture",
                "path": "/full-belt-overbuild",
                "occurrence_count": 1,
                "module_items": [],
                "layout": {"width": 16, "height": 16, "entities": [], "tiles": [], "ports": [], "port_counts": []},
                "recipe_mappings": [
                    {
                        "recipe": "fixture-crushing",
                        "status": "resolved",
                        "base_crafts_per_minute": 1.0,
                        "base_ingredients_per_minute": [("metallic-asteroid-chunk", 52.5)],
                        "base_products_per_minute": [("iron-ore", 1575.0)],
                    }
                ],
            }
        ],
        target_item="iron-ore",
        target_rate_per_minute=7200,
        target_rate_basis={"kind": "full-belt", "belt_name": "turbo-transport-belt", "belt_count": 2, "items_per_second_per_belt": 60},
        boundary_items={"metallic-asteroid-chunk"},
    )
    if full_belt_overbuild_dag["root"]["instances"] != 6 or full_belt_overbuild_dag["root"]["planned_net_output_per_minute"] != 9450:
        print(f"FAIL: expected full-belt root planning to overbuild enough complete templates to feed each target belt: {full_belt_overbuild_dag}")
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
    row_spaced_layout = build_layout_plan(
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
        max_columns=8,
        spacing=1,
        row_spacing=1.5,
        lane_width=4,
    )
    if (
        row_spaced_layout["spacing"] != 1
        or row_spaced_layout["row_spacing"] != 1.5
        or row_spaced_layout["nodes"][0]["planned_width"] != 23
        or row_spaced_layout["nodes"][0]["planned_height"] != 5.5
    ):
        print(f"FAIL: expected row spacing to affect repeated-row height without changing column width: {row_spaced_layout}")
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
        or replicated_summary["output_fanins"][0]["existing_belts_used"] != 8
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
    lane_load_audit = capacity_limited_summary["output_lane_load_audit"]
    if len(lane_load_audit) != 1 or lane_load_audit[0]["status"] != "overloaded" or lane_load_audit[0]["load_rate_per_minute"] != 7200:
        print(f"FAIL: expected output lane load audit to flag one overloaded turbo output lane: {capacity_limited_summary}")
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
    byproduct_replicated_layout = deepcopy(byproduct_layout)
    byproduct_replicated_layout["estimated_width"] = 26
    byproduct_replicated_layout["nodes"][0]["instances"] = 2
    byproduct_replicated_layout["nodes"][0]["columns"] = 2
    byproduct_replicated_layout["nodes"][0]["planned_width"] = 10
    byproduct_replicated_layout["nodes"][0]["planned_net_output_per_minute"] = 3600
    _, byproduct_replicated_summary = materialize_layout_with_summary(
        byproduct_replicated_layout,
        byproduct_mappings,
        label="fixture-byproduct-preseparation-exposure",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    exposure_audit = byproduct_replicated_summary["output_preseparation_exposure_audit"]
    if (
        len(exposure_audit) != 1
        or exposure_audit[0]["status"] != "mixed-before-separation"
        or exposure_audit[0]["covered_instances"] != [0, 1]
        or exposure_audit[0]["fanin_segment_count"] != 1
        or exposure_audit[0]["byproducts"] != ["metallic-asteroid-chunk"]
        or exposure_audit[0]["lane_load_status"] != "sufficient"
        or exposure_audit[0]["max_safe_instances_before_separation"] != 2
        or exposure_audit[0]["recommendation"] != "mixed-route-is-within-lane-capacity-but-still-needs-runtime-proof"
    ):
        print(f"FAIL: expected byproduct fan-in exposure audit to flag mixed output before the target splitter: {byproduct_replicated_summary}")
        return 1
    byproduct_merge_reuse_layout = deepcopy(byproduct_replicated_layout)
    byproduct_merge_reuse_layout["estimated_height"] = 14
    byproduct_merge_reuse_layout["nodes"][0]["source_height"] = 6
    byproduct_merge_reuse_layout["nodes"][0]["source_entity_count"] = 4
    byproduct_merge_reuse_layout["nodes"][0]["planned_height"] = 6
    byproduct_merge_reuse_layout["nodes"][0]["ports"] = [
        {"side": "left", "role": "input", "entity_name": "turbo-transport-belt", "x": 0, "y": 3},
        {"side": "right", "role": "output", "entity_name": "turbo-transport-belt", "x": 2, "y": 1},
    ]
    byproduct_merge_reuse_layout["nodes"][0]["port_counts"] = [("left:input", 1), ("right:output", 1)]
    byproduct_merge_reuse_mappings = [
        {
            "fingerprint": "byproduct-template",
            "layout": {
                "entities": [
                    {"name": "turbo-transport-belt", "x": 0, "y": 3, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 2, "y": 1, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 6, "y": 4, "direction": DIR_WEST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "turbo-transport-belt", "x": 7, "y": 4, "direction": DIR_WEST, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, byproduct_merge_reuse_summary = materialize_layout_with_summary(
        byproduct_merge_reuse_layout,
        byproduct_merge_reuse_mappings,
        label="fixture-byproduct-recycle-merge-reuses-input-belt",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    byproduct_merge_reuse = byproduct_merge_reuse_summary["output_separations"][0]
    byproduct_merge_reuse_audit = byproduct_merge_reuse["recycle_flow_audit"]
    if (
        byproduct_merge_reuse["status"] != "connected"
        or byproduct_merge_reuse["current_handling"] != "recycle-merge-to-input-boundary"
        or byproduct_merge_reuse["merge_belts_added"] != 16
        or byproduct_merge_reuse["existing_belts_used"] != 2
        or byproduct_merge_reuse_summary["output_separation_merge_belts"] != 16
        or byproduct_merge_reuse["recycle_merge_target"]["input_y"] != 7.0
        or byproduct_merge_reuse["recycle_exit"]["side"] != "input-bus"
        or byproduct_merge_reuse_audit["status"] != "pass"
        or byproduct_merge_reuse_audit["positions_checked"] != byproduct_merge_reuse["merge_belts_added"] + byproduct_merge_reuse["existing_belts_used"]
    ):
        print(f"FAIL: expected byproduct recycle merge to safely reuse same-direction existing input-lane belts: {byproduct_merge_reuse_summary}")
        return 1
    _, byproduct_preseparated_summary = materialize_layout_with_summary(
        byproduct_replicated_layout,
        byproduct_mappings,
        label="fixture-byproduct-preseparate-before-fanin",
        connect_boundaries=True,
        knowledge=knowledge,
        preseparate_output_before_fanin=True,
    )
    pre_fanin_separations = [
        item
        for item in byproduct_preseparated_summary["output_separations"]
        if item.get("scope") == "output-fanin"
    ]
    pre_fanin_exposure = byproduct_preseparated_summary["output_preseparation_exposure_audit"]
    if (
        len(pre_fanin_separations) != 1
        or pre_fanin_separations[0]["status"] != "connected"
        or pre_fanin_separations[0]["current_handling"] != "pre-fanin-recycle-return-to-input-boundary"
        or pre_fanin_separations[0]["recycle_flow_audit"]["status"] != "pass"
        or "blocked_recycle_attempt_count" not in pre_fanin_separations[0]
        or pre_fanin_separations[0]["from_instance"] != 0
        or pre_fanin_separations[0]["to_instance"] != 1
        or len(pre_fanin_exposure) != 1
        or pre_fanin_exposure[0]["status"] != "preseparated-before-fanin"
        or pre_fanin_exposure[0]["fanin_preseparated"] is not True
        or pre_fanin_exposure[0]["preseparator_instances"] != [0]
        or pre_fanin_exposure[0]["recommendation"] != "pre-fanin-separation-removes-mixed-byproducts-but-still-needs-runtime-proof"
    ):
        print(f"FAIL: expected pre-fanin separation to mark fan-in sources as separated before mixed output merge: {byproduct_preseparated_summary}")
        return 1
    score_fixture = {
        "width": 10,
        "height": 10,
        "entity_count": 1,
        "connector_summary": {
            "collisions": [],
            "belt_flow_audit": [],
            "boundary_capacity_audit": [],
            "boundary_contract_audit": [],
            "output_lane_load_audit": [],
            "output_boundary_compressors": [],
            "output_preseparation_exposure_audit": [],
            "boundary_coverage": [],
            "routes": [],
            "connectors_added": 0,
            "output_separations": [
                {"status": "connected", "current_handling": "pre-fanin-recycle-merge-to-input-boundary"},
            ],
        },
    }
    sideload_score_fixture = deepcopy(score_fixture)
    sideload_score_fixture["connector_summary"]["output_separations"] = [
        {"status": "connected", "current_handling": "pre-fanin-recycle-sideload-to-input-lane", "experimental": True},
    ]
    finite_score_fixture = deepcopy(score_fixture)
    finite_score_fixture["connector_summary"]["output_separations"] = [
        {
            "boundary": "output:iron-ore",
            "status": "connected",
            "current_handling": "pre-fanin-finite-overflow-buffer",
            "recycle_corridor_probe": {
                "status": "surface-corridor-blocked",
                "recommendation": "reserve-dedicated-recycle-corridor-or-underground-crossing",
            },
        },
    ]
    if materialized_layout_score(sideload_score_fixture) <= materialized_layout_score(score_fixture):
        print("FAIL: expected materialized layout score to penalize experimental pre-fanin input-lane sideload")
        return 1
    if materialized_layout_score(finite_score_fixture) <= materialized_layout_score(sideload_score_fixture):
        print("FAIL: expected materialized layout score to penalize pre-fanin finite overflow buffers")
        return 1
    finite_markdown = render_materialize_markdown_report(
        {
            "label": "fixture-finite",
            "target_item": "iron-ore",
            "target_rate_per_minute": 60,
            "target_rate_basis": {"kind": "explicit"},
            "entity_count": 1,
            "tile_count": 0,
            "connector_summary": finite_score_fixture["connector_summary"],
            "route_status_counts": {},
            "width": 1,
            "height": 1,
            "density": 1,
            "layout_estimated_width": 1,
            "layout_estimated_height": 1,
            "boundary_inputs": [],
            "boundary_outputs": [],
            "layout_nodes": [],
            "lessons": [],
        }
    )
    if "corridor_probe=surface-corridor-blocked" not in finite_markdown or "reserve-dedicated-recycle-corridor-or-underground-crossing" not in finite_markdown:
        print(f"FAIL: expected materialize markdown to include recycle corridor probe: {finite_markdown}")
        return 1
    byproduct_overloaded_layout = deepcopy(byproduct_replicated_layout)
    byproduct_overloaded_layout["target_rate_per_minute"] = 7200
    byproduct_overloaded_layout["boundary_outputs"] = [{"item": "iron-ore", "rate_per_minute": 7200, "side": "right"}]
    byproduct_overloaded_layout["nodes"][0]["planned_net_output_per_minute"] = 7200
    _, byproduct_overloaded_summary = materialize_layout_with_summary(
        byproduct_overloaded_layout,
        byproduct_mappings,
        label="fixture-byproduct-preseparation-overload",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    overloaded_exposure = byproduct_overloaded_summary["output_preseparation_exposure_audit"]
    if (
        len(overloaded_exposure) != 1
        or overloaded_exposure[0]["status"] != "mixed-overloaded-before-separation"
        or overloaded_exposure[0]["lane_load_status"] != "overloaded"
        or overloaded_exposure[0]["lane_overload_per_minute"] != 3600
        or overloaded_exposure[0]["max_safe_instances_before_separation"] != 1
        or overloaded_exposure[0]["recommendation"] != "split-target-and-byproduct-before-output-fanin-or-use-runtime-proven-lane-aware-compression"
    ):
        print(f"FAIL: expected byproduct pre-separation exposure audit to escalate mixed overloaded routes: {byproduct_overloaded_summary}")
        return 1
    preseparation_selector_layout = deepcopy(byproduct_layout)
    preseparation_selector_layout["target_rate_per_minute"] = 7200
    preseparation_selector_layout["target_rate_basis"] = {
        "kind": "full-belt",
        "belt_name": "turbo-transport-belt",
        "belt_count": 2,
        "items_per_second_per_belt": 60,
    }
    preseparation_selector_layout["max_columns"] = 3
    preseparation_selector_layout["estimated_width"] = 32
    preseparation_selector_layout["boundary_outputs"] = [{"item": "iron-ore", "rate_per_minute": 7200, "side": "right"}]
    preseparation_selector_layout["nodes"][0]["instances"] = 3
    preseparation_selector_layout["nodes"][0]["columns"] = 3
    preseparation_selector_layout["nodes"][0]["rows"] = 1
    preseparation_selector_layout["nodes"][0]["planned_width"] = 16
    preseparation_selector_layout["nodes"][0]["planned_net_output_per_minute"] = 5400
    _, selector_summary, selector_layout = select_best_materialized_layout(
        preseparation_selector_layout,
        byproduct_mappings,
        label="fixture-byproduct-safe-width-selector",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    selector_constraint = selector_layout.get("output_preseparation_safe_width_constraint") or {}
    if (
        selector_layout["layout_selection"]["selected_columns"] != 2
        or selector_constraint.get("status") != "within-limit"
        or selector_constraint.get("max_safe_instances_before_separation") != 2
        or selector_summary["output_preseparation_exposure_audit"][0]["max_safe_instances_before_separation"] != 2
    ):
        print(f"FAIL: expected selector to keep byproduct row fan-in within the pre-separation safe width: {selector_layout} {selector_summary}")
        return 1
    _, forced_selector_summary, forced_selector_layout = select_best_materialized_layout(
        preseparation_selector_layout,
        byproduct_mappings,
        label="fixture-byproduct-safe-width-forced",
        connect_boundaries=True,
        knowledge=knowledge,
        force_columns=3,
    )
    forced_constraint = forced_selector_layout.get("output_preseparation_safe_width_constraint") or {}
    if (
        forced_selector_layout["layout_selection"]["selected_columns"] != 3
        or forced_constraint.get("status") != "over-limit"
        or forced_constraint.get("max_safe_instances_before_separation") != 2
        or forced_selector_summary["output_preseparation_exposure_audit"][0]["status"] != "mixed-overloaded-before-separation"
    ):
        print(f"FAIL: expected forced over-wide rows to be marked over the pre-separation safe width: {forced_selector_layout} {forced_selector_summary}")
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
    selected_lane_loads = sorted(
        selected_summary["output_lane_load_audit"],
        key=lambda item: item["route_y"],
    )
    if (
        selected_layout["nodes"][0]["columns"] != 2
        or selected_layout["nodes"][0]["rows"] != 3
        or selected_layout["layout_selection"].get("selected_compress_output_boundary") is not False
        or selected_flow_counts != {"pass": 12}
        or selected_capacity["output:iron-ore"]["status"] != "sufficient"
        or selected_capacity["output:iron-ore"]["proven_capacity_per_minute"] != 10800
        or selected_contract["output:iron-ore"]["status"] != "over-provisioned"
        or selected_contract["output:iron-ore"]["route_count"] != 3
        or selected_summary["output_fanins_added"] <= 0
        or [item["covered_instance_count"] for item in selected_lane_loads] != [2, 2, 1]
        or any(item["status"] == "overloaded" for item in selected_lane_loads)
    ):
        print(f"FAIL: expected post-materialize layout selection to reject overloaded exact grids before preferring a tighter over-provisioned grid: {selected_layout} {selected_summary}")
        return 1

    _, compress_allowed_summary, compress_allowed_layout = select_best_materialized_layout(
        selection_layout,
        selection_mappings,
        label="fixture-compress-allowed-layout",
        connect_boundaries=True,
        knowledge=knowledge,
        compress_output_boundary=True,
    )
    compress_allowed_contract = {item["boundary"]: item for item in compress_allowed_summary["boundary_contract_audit"]}
    compress_allowed_capacity = {item["boundary"]: item for item in compress_allowed_summary["boundary_capacity_audit"]}
    if (
        compress_allowed_layout["nodes"][0]["columns"] != 2
        or compress_allowed_layout["nodes"][0]["rows"] != 3
        or compress_allowed_layout["layout_selection"].get("selected_compress_output_boundary") is not False
        or compress_allowed_layout["layout_selection"].get("candidate_count") != 10
        or compress_allowed_summary["output_boundary_compressors"]
        or compress_allowed_contract["output:iron-ore"]["status"] != "over-provisioned"
        or compress_allowed_capacity["output:iron-ore"]["status"] != "sufficient"
        or compress_allowed_capacity["output:iron-ore"]["proven_capacity_per_minute"] != 10800
    ):
        print(f"FAIL: expected optional compression to keep the better uncompressed sufficient candidate available: {compress_allowed_layout} {compress_allowed_summary}")
        return 1

    compressed_wrapper, compressed_summary, compressed_layout = select_best_materialized_layout(
        selection_layout,
        selection_mappings,
        label="fixture-compressed-layout",
        connect_boundaries=True,
        knowledge=knowledge,
        compress_output_boundary=True,
        force_columns=2,
    )
    compressed_splitter_priorities = [
        entity.get("output_priority")
        for entity in compressed_wrapper["blueprint"].get("entities") or []
        if entity.get("name") == "turbo-splitter" and entity.get("output_priority") == "right"
    ]
    compressed_contract = {item["boundary"]: item for item in compressed_summary["boundary_contract_audit"]}
    compressed_capacity = {item["boundary"]: item for item in compressed_summary["boundary_capacity_audit"]}
    compressed_internal_routes = [
        route
        for route in compressed_summary["routes"]
        if route.get("boundary") == "output:iron-ore" and route.get("boundary_role") == "internal-output"
    ]
    compressed_external_routes = [
        route
        for route in compressed_summary["routes"]
        if route.get("boundary") == "output:iron-ore" and route.get("boundary_role") == "external-output"
    ]
    compressed_lane_loads = [
        item for item in compressed_summary["output_lane_load_audit"] if item.get("boundary") == "output:iron-ore"
    ]
    if (
        compressed_layout["nodes"][0]["columns"] != 2
        or compressed_layout["nodes"][0]["rows"] != 3
        or compressed_layout["layout_selection"].get("selected_compress_output_boundary") is not True
        or compressed_summary["output_boundary_compressors"][0]["status"] != "connected"
        or compressed_summary["output_boundary_compressors"][0].get("runtime_status") != "known-insufficient"
        or compressed_summary["output_boundary_compressors"][0].get("capacity_proof") != "unresolved"
        or compressed_contract["output:iron-ore"]["status"] != "exact"
        or compressed_contract["output:iron-ore"]["route_count"] != 2
        or compressed_capacity["output:iron-ore"]["status"] != "unresolved"
        or compressed_capacity["output:iron-ore"]["proven_capacity_per_minute"] != 0
        or compressed_capacity["output:iron-ore"]["unresolved_capacity_per_minute"] != 7200
        or len(compressed_internal_routes) != 3
        or len(compressed_external_routes) != 2
        or [route["route_kind"] for route in compressed_external_routes] != ["output-boundary-compressor-output", "output-boundary-compressor-output"]
        or any(route.get("capacity_proof") != "runtime-unproven-compressor" for route in compressed_external_routes)
        or len(compressed_splitter_priorities) != 2
        or len(compressed_lane_loads) != 3
        or any(item["status"] == "overloaded" for item in compressed_lane_loads)
    ):
        print(f"FAIL: expected compressed output boundary to expose an exact but runtime-unproven 2-belt boundary: {compressed_layout} {compressed_summary}")
        return 1

    _, forced_summary, forced_layout = select_best_materialized_layout(
        selection_layout,
        selection_mappings,
        label="fixture-forced-layout",
        connect_boundaries=True,
        knowledge=knowledge,
        force_columns=3,
    )
    forced_contract = {item["boundary"]: item for item in forced_summary["boundary_contract_audit"]}
    if (
        forced_layout["layout_selection"]["strategy"] != "forced-single-node-columns"
        or forced_layout["nodes"][0]["columns"] != 3
        or forced_layout["nodes"][0]["rows"] != 2
        or forced_contract["output:iron-ore"]["status"] != "exact"
        or forced_contract["output:iron-ore"]["route_count"] != 2
    ):
        print(f"FAIL: expected force_columns to bypass selector and materialize the requested exact grid: {forced_layout} {forced_summary}")
        return 1

    fanin_pickup_guard_layout = {
        "target_item": "iron-gear-wheel",
        "target_rate_per_minute": 300,
        "target_rate_basis": {"kind": "explicit-rate", "rate_per_minute": 300},
        "max_columns": 2,
        "spacing": 2,
        "lane_width": 4,
        "estimated_width": 20,
        "estimated_height": 14,
        "boundary_inputs": [],
        "boundary_outputs": [{"item": "iron-gear-wheel", "rate_per_minute": 300, "side": "right"}],
        "nodes": [
            {
                "item": "iron-gear-wheel",
                "recipe": "iron-gear-wheel",
                "fingerprint": "fanin-pickup-guard-template",
                "instances": 2,
                "source_width": 6,
                "source_height": 6,
                "source_entity_count": 3,
                "source_tile_count": 0,
                "columns": 2,
                "rows": 1,
                "planned_width": 14,
                "planned_height": 6,
                "planned_net_output_per_minute": 300,
                "x": 4,
                "y": 4,
                "ports": [
                    {"side": "right", "role": "machine-output", "entity_name": "transport-belt", "x": 2, "y": 2, "direction": DIR_EAST, "source": "fixture"},
                ],
                "port_counts": [("right:machine-output", 1)],
                "source": "fixture",
                "path": "/fanin-pickup-guard",
            }
        ],
    }
    fanin_pickup_guard_mappings = [
        {
            "fingerprint": "fanin-pickup-guard-template",
            "layout": {
                "entities": [
                    {"name": "assembling-machine-3", "x": 0, "y": 2, "direction": None, "recipe": "iron-gear-wheel", "recipe_quality": None, "quality": None},
                    {"name": "fast-inserter", "x": 1, "y": 2, "direction": DIR_WEST, "recipe": None, "recipe_quality": None, "quality": None},
                    {"name": "transport-belt", "x": 2, "y": 2, "direction": DIR_EAST, "recipe": None, "recipe_quality": None, "quality": None},
                ],
                "tiles": [],
            },
        }
    ]
    _, fanin_pickup_guard_summary = materialize_layout_with_summary(
        fanin_pickup_guard_layout,
        fanin_pickup_guard_mappings,
        label="fixture-fanin-pickup-guard",
        connect_boundaries=True,
        knowledge=knowledge,
    )
    fanin_routes = fanin_pickup_guard_summary.get("output_fanins") or []
    blocked_pickup = (12.0, 6.0)
    if (
        len(fanin_routes) != 1
        or not str(fanin_routes[0].get("route_kind") or "").startswith("output-fanin-detour")
        or any((float(position[0]), float(position[1])) == blocked_pickup for position in fanin_routes[0].get("route_positions") or [])
    ):
        print(f"FAIL: expected output fan-in to detour around machine-output pickup position {blocked_pickup}: {fanin_pickup_guard_summary}")
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
    if (
        underground_flow_counts.get("unresolved", 0) < 1
        or not any(
            item["status"] == "unresolved"
            and any(entry.get("reason") == "underground-belt-endpoint-not-proven" for entry in item["unresolved"])
            for item in underground_summary["belt_flow_audit"]
        )
    ):
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
