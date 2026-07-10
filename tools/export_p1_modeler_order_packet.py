"""Export a P1 limb modeler order and acceptance packet.

The packet is a modeler-facing view over
tools/validate_modeler_variant_order_manifest.py --report-json. It can read a
validator JSON report, stdin JSON, or an order manifest path and generate the
same report internally.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import validate_modeler_variant_order_manifest as order_validator  # noqa: E402


CONTRACT_VERSION = "p1-modeler-order-packet.v1"
REQUIRED_TOP_LEVEL_KEYS = (
    "order_items",
    "acceptance_checks",
    "blocked_by_stage",
    "runtime_activation_policy",
    "modeler_message_outline",
)
STAGE_ORDER = ("order", "delivery", "catalog_registration", "runtime_activation")
SIDECAR_FIELDS = (
    "line_id",
    "source_concept_ids",
    "design_intent",
    "fidelity_notes",
    "bbox_m",
    "target_envelope_m",
    "vrm_attachment",
)
REVIEW_VIEWS = ("front", "side", "back", "3q", "closeup")
PATH_FIELDS = {
    "glb": "{root}/{module}/variants/{asset_key}/{module}__{asset_key}.glb",
    "sidecar": "{root}/{module}/variants/{asset_key}/{module}__{asset_key}.modeler.json",
    "source_blend": "{root}/{module}/variants/{asset_key}/source/{module}__{asset_key}.blend",
    "preview_mesh": "{root}/{module}/variants/{asset_key}/preview/{module}__{asset_key}.mesh.json",
}

LINE_ORDER_PREFIX = {
    "line_rescue_knight": "RK",
    "line_royal_insect": "RI",
    "line_final_oath": "FO",
}

FAMILY_CHECKS = {
    "upperarm": {
        "primary_review": "shoulder-to-elbow read, shoulder lift, elbow clearance",
        "reject_if": "shoulder lift or elbow bend is blocked, or the part reads as a flat stripe",
        "evidence": ["paired_front", "side_elbow_clearance", "3q_line_identity"],
    },
    "forearm": {
        "primary_review": "worn vambrace/gauntlet fit, elbow bend, wrist rotation, controller sightline",
        "reject_if": "the asset floats as a wrist prop or hides controller grip/readability",
        "evidence": ["paired_front", "side_wrist_rotation", "controller_clearance"],
    },
    "hand": {
        "primary_review": "palm, knuckle, cuff/core read, gesture and controller clearance",
        "reject_if": "hand depth exceeds the accepted envelope without reviewer-only waiver",
        "evidence": ["palm_closeup", "side_depth", "controller_grip"],
    },
    "thigh": {
        "primary_review": "waist-to-shin continuity, hip flex, knee bend, walking stance",
        "reject_if": "the plate bridges hip/knee as a rigid bar or intersects the body",
        "evidence": ["paired_front", "side_hip_knee", "3q_walk_stance"],
    },
}


def load_validator_report(source: str | Path = order_validator.DEFAULT_MANIFEST) -> dict[str, Any]:
    """Load a validator JSON report or generate one from an order manifest."""

    if str(source) == "-":
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("stdin JSON root must be an object")
        return _report_from_payload(payload, source_label="stdin")

    path = Path(source)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return _report_from_payload(payload, source_label=path.as_posix(), source_path=path)


def _report_from_payload(
    payload: dict[str, Any],
    *,
    source_label: str,
    source_path: Path | None = None,
) -> dict[str, Any]:
    if isinstance(payload.get("missing_matrix"), dict):
        return payload
    if source_path is None:
        raise ValueError(f"{source_label}: expected validator report JSON with missing_matrix")
    return order_validator.validate_order_manifest(source_path)


def build_order_packet(validator_report: dict[str, Any]) -> dict[str, Any]:
    matrix = validator_report.get("missing_matrix")
    if not isinstance(matrix, dict):
        raise ValueError("validator report missing missing_matrix")
    entries = matrix.get("entries")
    if not isinstance(entries, list):
        raise ValueError("missing_matrix.entries must be a list")

    order_items = [_order_item(entry) for entry in entries if isinstance(entry, dict)]
    blocked_by_stage = _blocked_by_stage(order_items)
    acceptance_checks = _acceptance_checks()
    runtime_activation_policy = _runtime_activation_policy(validator_report, matrix)

    packet = {
        "contract_version": CONTRACT_VERSION,
        "source": {
            "tool": "tools/validate_modeler_variant_order_manifest.py",
            "manifest": validator_report.get("manifest"),
            "validator_status": validator_report.get("status"),
            "validator_ok": validator_report.get("ok"),
            "missing_matrix_contract": matrix.get("contract_version"),
            "axis": matrix.get("axis", []),
        },
        "summary": {
            "order_item_count": len(order_items),
            "p1_blocked_asset_count": matrix.get("p1_blocked_asset_count", 0),
            "runtime_activation_blocked_count": matrix.get("runtime_activation_blocked_count", 0),
            "current_stop_counts": matrix.get("stage_counts", {}).get("current_stop", {}),
        },
        "order_items": order_items,
        "acceptance_checks": acceptance_checks,
        "blocked_by_stage": blocked_by_stage,
        "runtime_activation_policy": runtime_activation_policy,
        "modeler_message_outline": _modeler_message_outline(order_items, blocked_by_stage),
    }
    _assert_packet_contract(packet)
    return packet


def export_order_packet(source: str | Path = order_validator.DEFAULT_MANIFEST) -> dict[str, Any]:
    return build_order_packet(load_validator_report(source))


def _order_item(entry: dict[str, Any]) -> dict[str, Any]:
    family = str(entry.get("limb_family") or "unknown")
    line_id = str(entry.get("line_id") or "")
    side = str(entry.get("side") or "unknown")
    module = entry.get("module")
    asset_key = entry.get("asset_key")
    variant_key = entry.get("variant_key")
    checks = FAMILY_CHECKS.get(family, {})
    return {
        "order_item_id": _order_item_id(line_id=line_id, family=family, side=side),
        "line_id": line_id,
        "line_label": entry.get("line_label"),
        "source_concept_ids": entry.get("source_concept_ids", []),
        "limb_family": family,
        "side": side,
        "module": module,
        "asset_key": asset_key,
        "variant_key": variant_key,
        "current_stop_stage": entry.get("current_stop_stage"),
        "blocked_stages": entry.get("blocked_stages", []),
        "statuses": {
            "order": entry.get("order_status"),
            "delivery": entry.get("delivery_status"),
            "catalog_registration": entry.get("catalog_registration_status"),
            "runtime_activation": entry.get("runtime_activation_status"),
        },
        "required_files": _required_files(module=module, asset_key=asset_key),
        "acceptance_focus": checks.get("primary_review", "tri-view identity, fit, and metadata proof"),
        "reject_if": checks.get("reject_if", "manifest, metadata, tri-view, or runtime identity contract is broken"),
        "evidence_required": checks.get("evidence", list(REVIEW_VIEWS)),
        "stage_reasons": entry.get("stage_reasons", {}),
    }


def _order_item_id(*, line_id: str, family: str, side: str) -> str:
    line = LINE_ORDER_PREFIX.get(line_id, line_id.replace("line_", "").upper() or "UNKNOWN")
    return f"P1-LIMB-{line}-{family.upper()}-{side.upper()}"


def _required_files(*, module: Any, asset_key: Any) -> dict[str, str] | dict[str, None]:
    if not isinstance(module, str) or not isinstance(asset_key, str):
        return {name: None for name in PATH_FIELDS}
    values = {
        "root": order_validator.ARMOR_ROOT,
        "module": module,
        "asset_key": asset_key,
    }
    return {name: template.format(**values) for name, template in PATH_FIELDS.items()}


def _acceptance_checks() -> dict[str, Any]:
    return {
        "delivery_fileset": {
            "required": ["GLB", "modeler sidecar JSON", "source .blend", "preview .mesh.json"],
            "reject_if_missing": True,
        },
        "sidecar_fields": {
            "required": list(SIDECAR_FIELDS),
            "reject_if_missing": True,
        },
        "review_packet": {
            "required_views": list(REVIEW_VIEWS),
            "left_right_pair_review_required": True,
        },
        "numeric_fit": {
            "axis_target_pass_pct": 10,
            "axis_target_fail_pct": 15,
            "left_right_pair_delta_max_pct": 3,
            "glb_sidecar_preview_bbox_delta_max_m": 0.002,
        },
        "family_checks": FAMILY_CHECKS,
        "catalog_registration": {
            "required_before_p1_acceptance": True,
            "variant_key_must_match_manifest": True,
            "fallback_or_proxy_does_not_satisfy_order": True,
        },
    }


def _blocked_by_stage(order_items: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for stage in STAGE_ORDER:
        items = [
            _blocked_item_summary(item)
            for item in order_items
            if item.get("current_stop_stage") == stage
        ]
        result[stage] = {
            "count": len(items),
            "items": items,
            "next_action": _stage_next_action(stage),
        }
    return result


def _blocked_item_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_item_id": item.get("order_item_id"),
        "variant_key": item.get("variant_key"),
        "line_id": item.get("line_id"),
        "limb_family": item.get("limb_family"),
        "side": item.get("side"),
        "status": item.get("statuses", {}).get(item.get("current_stop_stage")),
    }


def _stage_next_action(stage: str) -> str:
    return {
        "order": "Fix manifest order rows before sending work to modelers.",
        "delivery": "Ask modelers to deliver GLB, sidecar, source blend, preview mesh, and review views.",
        "catalog_registration": "Register the delivered variant_key in variant_catalog.json without changing the manifest key.",
        "runtime_activation": "Keep P1 accepted assets reviewer-only until a separate Web/Quest runtime activation change.",
    }[stage]


def _runtime_activation_policy(validator_report: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    p1 = validator_report.get("p1_acceptance", {})
    return {
        "runtime_activation_allowed": False,
        "runtime_activation_label": order_validator.RUNTIME_ACTIVATION_BLOCKED,
        "source_runtime_activation_allowed": p1.get("runtime_activation_allowed", False),
        "requires_separate_change": True,
        "public_activation_blocked_while": [
            "p1_blocked_asset_count > 0",
            "package_gate_status == warn_now_block_p1",
            "Web/Quest/Replay exact variant_key proof is missing",
        ],
        "current_counts": {
            "p1_blocked_asset_count": matrix.get("p1_blocked_asset_count", 0),
            "runtime_activation_blocked_count": matrix.get("runtime_activation_blocked_count", 0),
        },
    }


def _modeler_message_outline(
    order_items: list[dict[str, Any]],
    blocked_by_stage: dict[str, Any],
) -> dict[str, Any]:
    delivery_items = blocked_by_stage.get("delivery", {}).get("items", [])
    catalog_items = blocked_by_stage.get("catalog_registration", {}).get("items", [])
    return {
        "title": "P1 limb three-line variant order packet",
        "audience": "modeler delivery and intake reviewers",
        "opening": (
            f"Deliver {len(order_items)} P1 limb assets across three suit lines, "
            "four limb families, and left/right sides."
        ),
        "send_to_modeler": [
            "Use the order_items table as the authoritative line/family/side checklist.",
            "Each item needs GLB, modeler sidecar JSON, source .blend, preview .mesh.json, and review views.",
            "Do not submit base assets, toppings, proxies, or color-only swaps as P1 line variants.",
        ],
        "intake_reviewer_notes": [
            f"{len(delivery_items)} item(s) currently stop at delivery.",
            f"{len(catalog_items)} item(s) currently stop at catalog registration.",
            "Runtime activation is intentionally blocked even after P1 acceptance.",
        ],
    }


def _assert_packet_contract(packet: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_TOP_LEVEL_KEYS if key not in packet]
    if missing:
        raise ValueError(f"packet missing required top-level key(s): {missing}")


def format_packet(packet: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return _json_payload(packet)
    if output_format == "markdown":
        return _markdown_payload(packet)
    if output_format == "csv":
        return _csv_payload(packet)
    raise ValueError(f"unsupported format: {output_format}")


def _json_payload(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2) + "\n"


def _markdown_payload(packet: dict[str, Any]) -> str:
    summary = packet.get("summary", {})
    lines = [
        "# P1 Modeler Order Packet",
        "",
        f"- Contract: `{packet.get('contract_version')}`",
        f"- Source manifest: `{packet.get('source', {}).get('manifest')}`",
        f"- Order items: `{summary.get('order_item_count')}`",
        f"- P1 blocked assets: `{summary.get('p1_blocked_asset_count')}`",
        "",
        "## Blocked By Stage",
        "",
        "| Stage | Count | Next action |",
        "|---|---:|---|",
    ]
    for stage in STAGE_ORDER:
        stage_payload = packet.get("blocked_by_stage", {}).get(stage, {})
        lines.append(f"| `{stage}` | {stage_payload.get('count', 0)} | {stage_payload.get('next_action', '')} |")
    lines.extend(
        [
            "",
            "## Order Items",
            "",
            "| Item | Variant | Line | Family | Side | Current stop | Acceptance focus |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in packet.get("order_items", []):
        lines.append(
            "| "
            f"`{item.get('order_item_id')}` | "
            f"`{item.get('variant_key')}` | "
            f"`{item.get('line_id')}` | "
            f"`{item.get('limb_family')}` | "
            f"`{item.get('side')}` | "
            f"`{item.get('current_stop_stage')}` | "
            f"{item.get('acceptance_focus')} |"
        )
    return "\n".join(lines) + "\n"


def _csv_payload(packet: dict[str, Any]) -> str:
    output = io.StringIO()
    fieldnames = [
        "order_item_id",
        "variant_key",
        "line_id",
        "limb_family",
        "side",
        "module",
        "asset_key",
        "current_stop_stage",
        "order_status",
        "delivery_status",
        "catalog_registration_status",
        "runtime_activation_status",
        "acceptance_focus",
        "reject_if",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for item in packet.get("order_items", []):
        statuses = item.get("statuses", {})
        writer.writerow(
            {
                "order_item_id": item.get("order_item_id"),
                "variant_key": item.get("variant_key"),
                "line_id": item.get("line_id"),
                "limb_family": item.get("limb_family"),
                "side": item.get("side"),
                "module": item.get("module"),
                "asset_key": item.get("asset_key"),
                "current_stop_stage": item.get("current_stop_stage"),
                "order_status": statuses.get("order"),
                "delivery_status": statuses.get("delivery"),
                "catalog_registration_status": statuses.get("catalog_registration"),
                "runtime_activation_status": statuses.get("runtime_activation"),
                "acceptance_focus": item.get("acceptance_focus"),
                "reject_if": item.get("reject_if"),
            }
        )
    return output.getvalue()


def _write_output(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=order_validator.DEFAULT_MANIFEST,
        help="Order manifest path, validator report JSON path, or '-' for validator report JSON on stdin",
    )
    parser.add_argument("--out", type=Path, help="Write the requested format to this path")
    parser.add_argument("--format", choices=("json", "markdown", "csv"), default="json")
    parser.add_argument("--report-json", action="store_true", help="Print the JSON packet to stdout")
    args = parser.parse_args(argv)

    packet = export_order_packet(args.manifest)
    formatted = format_packet(packet, args.format)

    if args.out:
        _write_output(args.out, formatted)
    if args.report_json or not args.out:
        sys.stdout.write(_json_payload(packet) if args.report_json else formatted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
