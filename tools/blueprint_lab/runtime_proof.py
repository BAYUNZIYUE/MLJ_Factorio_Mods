from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MARKER = "BLUEPRINT_LAB_VALIDATION "


def coerce_value(value: str) -> Any:
    if value == "nil":
        return None
    if value in {"true", "false"}:
        return value == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_marker_payload(payload: str) -> dict[str, Any]:
    parts = payload.strip().split()
    if not parts:
        return {"event": ""}
    first = parts[0]
    if "=" in first:
        event, first_value = first.split("=", 1)
        values: dict[str, Any] = {"event": event, event: coerce_value(first_value)}
        parts = parts[1:]
    else:
        values = {"event": first}
        parts = parts[1:]
    for part in parts:
        if "=" not in part:
            values.setdefault("message_parts", []).append(part)
            continue
        key, value = part.split("=", 1)
        values[key] = coerce_value(value)
    return values


def parse_count_map(value: Any) -> dict[str, int]:
    if not isinstance(value, str) or not value:
        return {}
    counts: dict[str, int] = {}
    for part in value.split(","):
        if not part or ":" not in part:
            continue
        key, raw_count = part.rsplit(":", 1)
        try:
            counts[key] = int(raw_count)
        except ValueError:
            continue
    return counts


def iter_runtime_markers(log_path: Path) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for line_number, line in enumerate(log_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if MARKER not in line:
            continue
        payload = line.split(MARKER, 1)[1]
        marker = parse_marker_payload(payload)
        marker["line_number"] = line_number
        markers.append(marker)
    return markers


def latest_marker(markers: list[dict[str, Any]], event: str) -> dict[str, Any] | None:
    for marker in reversed(markers):
        if marker.get("event") == event:
            return marker
    return None


def runtime_proof_status(
    *,
    throughput: dict[str, Any] | None,
    cleanliness: dict[str, Any] | None,
    invalid_output_inserters: dict[str, Any] | None,
    target_rate_per_minute: float | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if throughput is None:
        reasons.append("missing-throughput-summary")
    elif target_rate_per_minute is not None:
        actual = throughput.get("target_per_minute")
        if not isinstance(actual, (int, float)):
            reasons.append("missing-throughput-rate")
        elif float(actual) < float(target_rate_per_minute):
            reasons.append("throughput-below-target")

    if cleanliness is None:
        reasons.append("missing-right-boundary-cleanliness")
    elif cleanliness.get("status") not in {"clean", "empty"}:
        reasons.append(f"right-boundary-{cleanliness.get('status')}")

    if invalid_output_inserters is None:
        reasons.append("missing-invalid-output-inserter-audit")
    elif int(invalid_output_inserters.get("count") or 0) != 0:
        reasons.append("invalid-output-inserters")

    if not reasons:
        return "runtime-proven", []
    if "throughput-below-target" in reasons:
        return "below-target", reasons
    if "invalid-output-inserters" in reasons or any(reason.startswith("right-boundary-") for reason in reasons):
        return "runtime-failed", reasons
    return "runtime-incomplete", reasons


def line_distribution_summary(
    lane_marker: dict[str, Any] | None,
    *,
    observed_ticks: int | float | None,
) -> dict[str, Any] | None:
    if lane_marker is None:
        return None
    counts = parse_count_map(lane_marker.get("target_by_line"))
    if not counts:
        return {
            "line_count": 0,
            "target_by_line": {},
            "reason": "missing-target-by-line",
        }
    values = list(counts.values())
    per_minute_by_line: dict[str, float] = {}
    if isinstance(observed_ticks, (int, float)) and float(observed_ticks) > 0:
        multiplier = 3600.0 / float(observed_ticks)
        per_minute_by_line = {line: round(count * multiplier, 3) for line, count in counts.items()}
    return {
        "line_count": len(counts),
        "target_by_line": counts,
        "total_target_items": sum(values),
        "min_target_items": min(values),
        "max_target_items": max(values),
        "spread_target_items": max(values) - min(values),
        "per_minute_by_line": per_minute_by_line,
        "line_marker": lane_marker,
    }


def build_runtime_proof(
    log_path: Path,
    *,
    target_item: str | None = None,
    target_rate_per_minute: float | None = None,
) -> dict[str, Any]:
    markers = iter_runtime_markers(log_path)
    throughput = latest_marker(markers, "right_boundary_throughput_summary")
    lane_summary_marker = latest_marker(markers, "right_boundary_throughput_lane_summary")
    cleanliness = latest_marker(markers, "right_boundary_cleanliness")
    invalid_output_marker = latest_marker(markers, "invalid_output_inserters")
    invalid_output_inserters = None
    if invalid_output_marker is not None:
        invalid_count = invalid_output_marker.get("count", invalid_output_marker.get("invalid_output_inserters", 0))
        invalid_output_inserters = {
            "count": int(invalid_output_marker.get("message_parts", [invalid_count])[0])
            if invalid_output_marker.get("message_parts")
            else int(invalid_count or 0),
            "samples": invalid_output_marker.get("samples", ""),
            "line_number": invalid_output_marker.get("line_number"),
        }
    success = latest_marker(markers, "success") is not None
    status, reasons = runtime_proof_status(
        throughput=throughput,
        cleanliness=cleanliness,
        invalid_output_inserters=invalid_output_inserters,
        target_rate_per_minute=target_rate_per_minute,
    )
    if not success and status == "runtime-proven":
        status = "runtime-incomplete"
        reasons = ["missing-success-marker"]
    return {
        "log_path": str(log_path),
        "marker_count": len(markers),
        "target_item": target_item,
        "target_rate_per_minute": target_rate_per_minute,
        "status": status,
        "reasons": reasons,
        "success_marker": success,
        "import_result": latest_marker(markers, "import_result"),
        "blueprint_entities": latest_marker(markers, "blueprint_entities"),
        "manual_placement": latest_marker(markers, "manual_entities"),
        "throughput_summary": throughput,
        "throughput_lane_summary": line_distribution_summary(
            lane_summary_marker,
            observed_ticks=throughput.get("observed_ticks") if throughput else None,
        ),
        "right_boundary_cleanliness": cleanliness,
        "invalid_output_inserters": invalid_output_inserters,
        "recipe_machine_audit": latest_marker(markers, "recipe_machine_audit"),
        "recipe_machine_runtime": latest_marker(markers, "recipe_machine_runtime"),
        "output_unload_audit": latest_marker(markers, "output_unload_audit"),
    }


def render_markdown_report(proof: dict[str, Any]) -> str:
    throughput = proof.get("throughput_summary") or {}
    lane_summary = proof.get("throughput_lane_summary") or {}
    cleanliness = proof.get("right_boundary_cleanliness") or {}
    invalid_output = proof.get("invalid_output_inserters") or {}
    lines = [
        "# Blueprint Runtime Proof Report",
        "",
        f"- Log: {proof['log_path']}",
        f"- Status: {proof['status']}",
        f"- Target item: {proof.get('target_item') or 'unknown'}",
        f"- Target rate: {proof.get('target_rate_per_minute') or 'unknown'}/min",
        f"- Marker count: {proof['marker_count']}",
        f"- Success marker: {proof['success_marker']}",
        f"- Throughput: {throughput.get('target_per_minute', 'unknown')}/min",
        f"- Throughput windows: {throughput.get('windows', 'unknown')}",
        f"- Throughput lane count: {lane_summary.get('line_count', 'unknown')}",
        f"- Throughput lane item spread: {lane_summary.get('spread_target_items', 'unknown')}",
        f"- Right boundary cleanliness: {cleanliness.get('status', 'unknown')}",
        f"- Invalid output inserters: {invalid_output.get('count', 'unknown')}",
    ]
    if proof.get("reasons"):
        lines.append(f"- Reasons: {', '.join(proof['reasons'])}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse Factorio BLUEPRINT_LAB_VALIDATION markers into a runtime proof report.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--target-item")
    parser.add_argument("--target-rate-per-minute", type=float)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args(argv)

    proof = build_runtime_proof(
        args.log,
        target_item=args.target_item,
        target_rate_per_minute=args.target_rate_per_minute,
    )
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_report(proof), encoding="utf-8")
    print(render_markdown_report(proof))
    return 0 if proof["status"] == "runtime-proven" else 2


if __name__ == "__main__":
    raise SystemExit(main())
