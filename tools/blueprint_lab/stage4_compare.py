from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RUNTIME_STATUS_RANK = {
    "runtime-proven": 0,
    "below-target": 1,
    "runtime-incomplete": 2,
    None: 3,
    "runtime-failed": 4,
}

CAPACITY_STATUS_RANK = {
    "sufficient": 0,
    "unresolved": 1,
    "unknown": 2,
    "failed": 3,
    "insufficient": 4,
}

CONTRACT_STATUS_RANK = {
    "exact": 0,
    "over-provisioned": 1,
    "under-provisioned": 2,
    "wrong-belt": 3,
}


NEAR_MISS_DEFICIT_RATIO = 0.02


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def output_contract(summary: dict[str, Any]) -> dict[str, Any] | None:
    audits = summary.get("boundary_contract_audit")
    if audits is None:
        audits = (summary.get("connector_summary") or {}).get("boundary_contract_audit")
    for audit in audits or []:
        if str(audit.get("boundary") or "").startswith("output:"):
            return audit
    return None


def output_capacity(summary: dict[str, Any]) -> dict[str, Any] | None:
    audits = summary.get("boundary_capacity_audit")
    if audits is None:
        audits = (summary.get("connector_summary") or {}).get("boundary_capacity_audit")
    for audit in audits or []:
        if str(audit.get("boundary") or "").startswith("output:"):
            return audit
    return None


def output_lane_load(summary: dict[str, Any]) -> list[dict[str, Any]]:
    audit = summary.get("output_lane_load_audit")
    if audit is None:
        audit = (summary.get("connector_summary") or {}).get("output_lane_load_audit")
    return list(audit or [])


def output_preseparation_exposure(summary: dict[str, Any]) -> list[dict[str, Any]]:
    audit = summary.get("output_preseparation_exposure_audit")
    if audit is None:
        audit = (summary.get("connector_summary") or {}).get("output_preseparation_exposure_audit")
    return list(audit or [])


def runtime_proof(summary: dict[str, Any], runtime_proof_path: Path | None) -> dict[str, Any] | None:
    if runtime_proof_path is not None:
        return load_json(runtime_proof_path)
    proof = summary.get("runtime_proof")
    return proof if isinstance(proof, dict) else None


def candidate_score(candidate: dict[str, Any]) -> list[float]:
    runtime = candidate.get("runtime_proof") or {}
    contract = candidate.get("output_contract") or {}
    capacity = candidate.get("output_capacity") or {}
    lane_summary = runtime.get("throughput_lane_summary") or {}
    window_diagnostics = runtime.get("throughput_window_diagnostics") or {}
    best_window = window_diagnostics.get("best_window") or {}
    expected_belt_count = int(contract.get("expected_belt_count") or 0)
    route_count = int(contract.get("route_count") or 0)
    route_overage = max(0, route_count - expected_belt_count) if expected_belt_count else route_count
    lane_count = int(lane_summary.get("line_count") or 0)
    runtime_status = runtime.get("status") if runtime else None
    best_window_deficit = float(best_window.get("target_rate_deficit_per_minute") or 0.0) if runtime else 0.0
    return [
        float(RUNTIME_STATUS_RANK.get(runtime_status, 5)),
        best_window_deficit,
        float(CAPACITY_STATUS_RANK.get(capacity.get("status"), 5)),
        float(CONTRACT_STATUS_RANK.get(contract.get("status"), 5)),
        float(route_overage),
        float(lane_count),
        float(candidate.get("area") or 0.0),
        float(candidate.get("entity_count") or 0),
    ]


def runtime_gap_analysis(candidate: dict[str, Any]) -> dict[str, Any]:
    runtime = candidate.get("runtime_proof") or {}
    contract = candidate.get("output_contract") or {}
    capacity = candidate.get("output_capacity") or {}
    lane_summary = runtime.get("throughput_lane_summary") or {}
    window_diagnostics = runtime.get("throughput_window_diagnostics") or {}
    best_window = window_diagnostics.get("best_window") or {}
    cleanliness = runtime.get("right_boundary_cleanliness") or {}
    invalid_output = runtime.get("invalid_output_inserters") or {}
    target_rate = candidate.get("target_rate_per_minute")
    best_deficit = best_window.get("target_rate_deficit_per_minute")
    best_rate = best_window.get("target_per_minute")
    expected_belt_count = int(contract.get("expected_belt_count") or 0)
    expected_transport_lines = expected_belt_count * 2 if expected_belt_count else None
    observed_lines = lane_summary.get("line_count")
    exact_contract = contract.get("status") == "exact"
    clean_boundary = cleanliness.get("status") in {"clean", "empty"}
    invalid_count = int(invalid_output.get("count") or 0) if invalid_output else None
    near_miss = False
    if (
        exact_contract
        and runtime.get("status") == "below-target"
        and capacity.get("status") == "sufficient"
        and clean_boundary
        and invalid_count == 0
        and isinstance(best_deficit, (int, float))
        and isinstance(target_rate, (int, float))
    ):
        near_miss = float(best_deficit) <= max(1.0, float(target_rate) * NEAR_MISS_DEFICIT_RATIO)
    if runtime.get("status") == "runtime-proven":
        category = "runtime-proven"
        next_action = "preserve-runtime-proof-and-reduce-over-provisioning" if contract.get("status") == "over-provisioned" else "accept-strict-runtime-proven-candidate"
    elif near_miss:
        category = "strict-near-miss"
        next_action = "tune-final-two-belt-compression-geometry"
    elif runtime.get("status") == "below-target":
        category = "below-target"
        next_action = "fix-runtime-throughput-before-ranking-as-solved"
    elif runtime:
        category = str(runtime.get("status") or "runtime-unknown")
        next_action = "collect-complete-runtime-proof"
    else:
        category = "missing-runtime-proof"
        next_action = "run-factorio-runtime-proof"
    return {
        "category": category,
        "near_miss": near_miss,
        "best_window_rate_per_minute": best_rate,
        "best_window_deficit_per_minute": best_deficit,
        "target_rate_per_minute": target_rate,
        "windows_at_or_above_target": window_diagnostics.get("windows_at_or_above_target"),
        "window_count": window_diagnostics.get("window_count"),
        "expected_transport_lines": expected_transport_lines,
        "observed_transport_lines": observed_lines,
        "clean_boundary": clean_boundary,
        "invalid_output_inserters": invalid_count,
        "next_action": next_action,
    }


def summarize_candidate(
    *,
    label: str,
    summary_path: Path,
    runtime_proof_path: Path | None = None,
) -> dict[str, Any]:
    summary = load_json(summary_path)
    proof = runtime_proof(summary, runtime_proof_path)
    contract = output_contract(summary) or {}
    capacity = output_capacity(summary) or {}
    lane_load = output_lane_load(summary)
    preseparation_exposure = output_preseparation_exposure(summary)
    width = float(summary.get("width") or 0.0)
    height = float(summary.get("height") or 0.0)
    candidate = {
        "label": label,
        "summary_path": str(summary_path),
        "runtime_proof_path": str(runtime_proof_path) if runtime_proof_path else None,
        "target_item": summary.get("target_item"),
        "target_rate_per_minute": summary.get("target_rate_per_minute"),
        "entity_count": summary.get("entity_count"),
        "tile_count": summary.get("tile_count"),
        "width": width,
        "height": height,
        "area": width * height,
        "route_status_counts": summary.get("route_status_counts"),
        "output_contract": contract,
        "output_capacity": capacity,
        "output_lane_load_status_counts": {
            status: sum(1 for item in lane_load if item.get("status") == status)
            for status in sorted({str(item.get("status") or "unknown") for item in lane_load})
        },
        "output_preseparation_exposure_status_counts": {
            status: sum(1 for item in preseparation_exposure if item.get("status") == status)
            for status in sorted({str(item.get("status") or "unknown") for item in preseparation_exposure})
        },
        "output_preseparation_exposure_audit": preseparation_exposure,
        "runtime_proof": proof,
    }
    candidate["runtime_gap_analysis"] = runtime_gap_analysis(candidate)
    candidate["score"] = candidate_score(candidate)
    candidate["lessons"] = candidate_lessons(candidate)
    return candidate


def candidate_lessons(candidate: dict[str, Any]) -> list[str]:
    lessons: list[str] = []
    contract = candidate.get("output_contract") or {}
    capacity = candidate.get("output_capacity") or {}
    runtime = candidate.get("runtime_proof") or {}
    lane_summary = runtime.get("throughput_lane_summary") or {}
    window_diagnostics = runtime.get("throughput_window_diagnostics") or {}
    best_window = window_diagnostics.get("best_window") or {}
    gap = candidate.get("runtime_gap_analysis") or {}
    if runtime.get("status") == "runtime-proven":
        lessons.append("runtime probe proves target throughput, clean right boundary, and no invalid output inserters")
    elif runtime:
        lessons.append(f"runtime proof is not sufficient: {runtime.get('status')}")
    if runtime and best_window.get("target_per_minute") is not None:
        lessons.append(
            f"best throughput window reached {best_window.get('target_per_minute')}/min with deficit {best_window.get('target_rate_deficit_per_minute')}/min"
        )
    elif not runtime:
        lessons.append("runtime proof is missing; offline audits are not enough for final acceptance")
    if contract.get("status") == "over-provisioned":
        lessons.append(
            f"output contract is over-provisioned: expected {contract.get('expected_belt_count')} routes but generated {contract.get('route_count')}"
        )
    if contract.get("status") == "exact" and capacity.get("status") == "unresolved":
        lessons.append("exact external contract exists, but output capacity remains unresolved")
    if lane_summary.get("line_count"):
        lessons.append(
            f"runtime throughput is distributed across {lane_summary.get('line_count')} output lines with spread {lane_summary.get('spread_target_items')}"
        )
    if gap.get("near_miss"):
        lessons.append(
            f"strict near-miss: exact boundary is clean, invalid output inserters are zero, and best window is short by {gap.get('best_window_deficit_per_minute')}/min"
        )
    mixed_exposure = (candidate.get("output_preseparation_exposure_status_counts") or {}).get("mixed-before-separation", 0)
    if mixed_exposure:
        lessons.append(
            f"{mixed_exposure} output route(s) merge multiple production instances before target/byproduct separation"
        )
    return lessons


def build_comparison(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(candidates, key=lambda item: item["score"])
    recommended = ordered[0] if ordered else None
    strict_candidates = [
        item
        for item in ordered
        if (item.get("output_contract") or {}).get("status") == "exact"
    ]
    runtime_proven = [
        item
        for item in ordered
        if (item.get("runtime_proof") or {}).get("status") == "runtime-proven"
    ]
    strict_near_misses = [
        item
        for item in ordered
        if (item.get("runtime_gap_analysis") or {}).get("near_miss")
    ]
    return {
        "candidate_count": len(candidates),
        "recommended_label": recommended.get("label") if recommended else None,
        "recommended_reason": "runtime proof outranks visual/exact boundary contract until strict compression is runtime-proven"
        if recommended else None,
        "candidates": ordered,
        "strict_boundary_candidates": [item["label"] for item in strict_candidates],
        "runtime_proven_candidates": [item["label"] for item in runtime_proven],
        "strict_near_miss_candidates": [item["label"] for item in strict_near_misses],
        "next_constraints": [
            "strict two-belt candidate must keep output contract exact",
            "strict two-belt candidate must provide runtime-proven throughput at or above target",
            "runtime lane summary must collapse external output to the expected final transport lines without falling below target",
            "right boundary must remain clean and invalid_output_inserters must stay zero",
            "strict near-miss candidates should tune final two-belt compression geometry before changing machine count",
        ],
    }


def render_markdown_report(comparison: dict[str, Any]) -> str:
    lines = [
        "# Blueprint Stage 4 Candidate Comparison",
        "",
        f"- Candidate count: {comparison['candidate_count']}",
        f"- Recommended: {comparison.get('recommended_label') or 'none'}",
        f"- Reason: {comparison.get('recommended_reason') or 'none'}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in comparison["candidates"]:
        contract = candidate.get("output_contract") or {}
        capacity = candidate.get("output_capacity") or {}
        runtime = candidate.get("runtime_proof") or {}
        lane_summary = runtime.get("throughput_lane_summary") or {}
        throughput = runtime.get("throughput_summary") or {}
        window_diagnostics = runtime.get("throughput_window_diagnostics") or {}
        best_window = window_diagnostics.get("best_window") or {}
        last_window = window_diagnostics.get("last_window") or {}
        gap = candidate.get("runtime_gap_analysis") or {}
        exposure_counts = candidate.get("output_preseparation_exposure_status_counts") or {}
        lines.extend(
            [
                f"### {candidate['label']}",
                "",
                f"- Score: {candidate['score']}",
                f"- Contract: {contract.get('status', 'unknown')} routes={contract.get('route_count', 'unknown')} expected={contract.get('expected_belt_count', 'unknown')}",
                f"- Capacity: {capacity.get('status', 'unknown')} proven={capacity.get('proven_capacity_per_minute', 'unknown')}/min required={capacity.get('required_rate_per_minute', 'unknown')}/min",
                f"- Runtime: {runtime.get('status', 'missing')}",
                f"- Runtime throughput: {throughput.get('target_per_minute', 'unknown')}/min",
                f"- Runtime best window: {best_window.get('target_per_minute', 'unknown')}/min deficit={best_window.get('target_rate_deficit_per_minute', 'unknown')}/min",
                f"- Runtime last window: {last_window.get('target_per_minute', 'unknown')}/min deficit={last_window.get('target_rate_deficit_per_minute', 'unknown')}/min",
                f"- Runtime windows at target: {window_diagnostics.get('windows_at_or_above_target', 'unknown')}/{window_diagnostics.get('window_count', 'unknown')}",
                f"- Runtime output lines: {lane_summary.get('line_count', 'unknown')} spread={lane_summary.get('spread_target_items', 'unknown')}",
                f"- Runtime gap category: {gap.get('category', 'unknown')} next={gap.get('next_action', 'unknown')}",
                f"- Output pre-separation exposure: {exposure_counts}",
                f"- Bounds: {candidate.get('width'):g} x {candidate.get('height'):g}",
            ]
        )
        for lesson in candidate.get("lessons") or []:
            lines.append(f"- Lesson: {lesson}")
        lines.append("")
    lines.extend(["## Next Constraints", ""])
    for item in comparison["next_constraints"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def parse_candidate_arg(value: str) -> tuple[str, Path, Path | None]:
    parts = value.split("=", 1)
    if len(parts) != 2 or not parts[0]:
        raise argparse.ArgumentTypeError("candidate must be label=summary.json or label=summary.json,runtime-proof.json")
    label, paths = parts
    path_parts = [Path(part) for part in paths.split(",") if part]
    if not path_parts:
        raise argparse.ArgumentTypeError("candidate summary path is required")
    return label, path_parts[0], path_parts[1] if len(path_parts) > 1 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare stage-4 generated blueprint candidates using offline audits and runtime proof.")
    parser.add_argument("--candidate", action="append", type=parse_candidate_arg, required=True)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    candidates = [
        summarize_candidate(label=label, summary_path=summary_path, runtime_proof_path=runtime_path)
        for label, summary_path, runtime_path in args.candidate
    ]
    comparison = build_comparison(candidates)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(comparison), encoding="utf-8")
    print(render_markdown_report(comparison))
    return 0 if comparison.get("recommended_label") else 2


if __name__ == "__main__":
    raise SystemExit(main())
