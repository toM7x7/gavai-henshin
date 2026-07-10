"""Export a modeler-facing fix request from the tri-view audit packet.

Default input is the local tri-view audit docs via
tools/export_modeler_triview_audit_packet.py. Pass --packet to reuse a saved
audit packet JSON. The primary artifact is Markdown for modeler handoff; use
--report-json for the machine-readable summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import export_modeler_triview_audit_packet as triview_packet  # noqa: E402


CONTRACT_VERSION = "modeler-fix-request.v1"
DEFAULT_OUT = Path("docs/modeler-fix-request-latest.md")
REQUIRED_SUMMARY_KEYS = (
    "fidelity_hold_items",
    "per_part_fix_requests",
    "acceptance_recheck_steps",
    "runtime_release_impact",
    "modeler_delivery_blockers",
)
PART_ORDER = triview_packet.PART_ORDER
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def load_audit_packet(
    *,
    packet_path: str | Path | None = None,
    audit_doc: str | Path = triview_packet.DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = triview_packet.DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    if packet_path is None:
        return triview_packet.export_triview_audit_packet(audit_doc=audit_doc, worklist_doc=worklist_doc)
    if str(packet_path) == "-":
        payload = json.loads(sys.stdin.read())
    else:
        payload = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("audit packet JSON root must be an object")
    _assert_audit_packet(payload)
    return payload


def build_fix_request_summary(packet: dict[str, Any]) -> dict[str, Any]:
    _assert_audit_packet(packet)
    hold_items = list(packet.get("fidelity_hold_items", []))
    fix_requests = _per_part_fix_requests(hold_items)
    blockers = _modeler_delivery_blockers(packet, hold_items)
    summary = {
        "contract_version": CONTRACT_VERSION,
        "source": {
            "packet_contract_version": packet.get("contract_version"),
            "audit_doc": packet.get("source", {}).get("audit_doc"),
            "worklist_doc": packet.get("source", {}).get("worklist_doc"),
            "rendering_or_blender_required": False,
        },
        "review_status": packet.get("review_status", {}),
        "fidelity_hold_items": hold_items,
        "per_part_fix_requests": fix_requests,
        "acceptance_recheck_steps": packet.get("acceptance_recheck_steps", []),
        "runtime_release_impact": packet.get("runtime_release_impact", {}),
        "modeler_delivery_blockers": blockers,
        "modeler_message": _modeler_message(packet, fix_requests, blockers),
    }
    _assert_summary_contract(summary)
    return summary


def export_fix_request(
    *,
    packet_path: str | Path | None = None,
    audit_doc: str | Path = triview_packet.DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = triview_packet.DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    return build_fix_request_summary(
        load_audit_packet(packet_path=packet_path, audit_doc=audit_doc, worklist_doc=worklist_doc)
    )


def _per_part_fix_requests(hold_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_part: dict[str, list[dict[str, Any]]] = {}
    for item in hold_items:
        by_part.setdefault(str(item.get("part", "unknown")), []).append(item)

    requests: list[dict[str, Any]] = []
    for part, items in by_part.items():
        priority = _highest_priority(items)
        requests.append(
            {
                "part": part,
                "priority": priority,
                "variant_count": len(items),
                "variant_keys": [item.get("variant_key") for item in items],
                "line_requests": [
                    {
                        "line_id": item.get("line_id"),
                        "variant_key": item.get("variant_key"),
                        "triview_check": item.get("triview_check"),
                        "requested_fix": item.get("modeler_action"),
                        "required_evidence": item.get("required_evidence", []),
                        "sidecar_fields_required": item.get("sidecar_fields_required", []),
                    }
                    for item in sorted(items, key=lambda value: str(value.get("line_id")))
                ],
                "acceptance": {
                    "next_state": "review_candidate",
                    "requires_front_side_back_3q": True,
                    "requires_sidecar_provenance": True,
                    "runtime_visibility": "reviewer_only_until_fidelity_pass",
                    "public_runtime_allowed": False,
                },
            }
        )
    return sorted(requests, key=_part_request_sort_key)


def _modeler_delivery_blockers(packet: dict[str, Any], hold_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review_status = packet.get("review_status", {})
    missing_p1_count = int(review_status.get("missing_p1_count", 0) or 0)
    outline = packet.get("modeler_fix_message_outline", {})
    blockers = [
        {
            "code": "fidelity-hold-visual-identity",
            "severity": "blocker",
            "count": len(hold_items),
            "message": "Delivered 30 variants are file-valid but tri-view fidelity is not accepted.",
            "required_resolution": "Strengthen line identity in front, side, back, and 3Q before promotion.",
        },
        {
            "code": "sidecar-provenance-incomplete",
            "severity": "blocker",
            "count": len(hold_items),
            "message": "Per-asset sidecars still need top-level provenance and fidelity notes.",
            "required_resolution": "Add source_concept_ids, line_id, design_intent, and fidelity_notes to each held sidecar.",
        },
        {
            "code": "review-evidence-incomplete",
            "severity": "blocker",
            "count": len(hold_items),
            "message": "Review packet must include full tri-view evidence, source overlay, and required closeups.",
            "required_resolution": "Attach front/side/back/3Q, source_overlay_front.png, helmet/torso closeups, and boot_closeup_side.png where applicable.",
        },
        {
            "code": "runtime-release-blocked",
            "severity": "blocker",
            "count": len(hold_items),
            "message": "Held variants must not be public Web/Quest runtime selections.",
            "required_resolution": "Keep reviewer-only visibility until fidelity_pass and route proof are complete.",
        },
    ]
    if missing_p1_count:
        blockers.append(
            {
                "code": "p1-limb-order-separate",
                "severity": "warn",
                "count": missing_p1_count,
                "message": "P1 upperarm/forearm/hand/thigh variants are separate missing-order work.",
                "required_resolution": "Do not claim line-complete limbs from this 30variant fix request.",
            }
        )
    for index, item in enumerate(outline.get("do_not_claim", []) or [], start=1):
        blockers.append(
            {
                "code": f"do-not-claim-{index}",
                "severity": "guardrail",
                "count": 0,
                "message": str(item),
                "required_resolution": "Keep this as a review note in the modeler handoff.",
            }
        )
    return blockers


def _modeler_message(
    packet: dict[str, Any],
    fix_requests: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    review_status = packet.get("review_status", {})
    return {
        "title": "30variant tri-view fidelity fix request",
        "opening": (
            f"{review_status.get('file_pass_but_fidelity_hold_count', 0)} delivered variants passed file checks "
            "but remain fidelity_hold. Please treat this as a visual/metadata/evidence rework request, not a new runtime activation request."
        ),
        "part_count": len(fix_requests),
        "blocker_count": len([item for item in blockers if item["severity"] == "blocker"]),
        "send_back_format": [
            "One updated fileset per variant key; keep the existing variant keys.",
            "One review evidence packet per line with full tri-view, overlay, and closeups.",
            "One sidecar provenance update per held variant.",
            "One notes file summarizing line identity changes and remaining deviations.",
        ],
    }


def format_markdown(summary: dict[str, Any]) -> str:
    review = summary.get("review_status", {})
    message = summary.get("modeler_message", {})
    lines = [
        "# Modeler 30variant Fix Request",
        "",
        f"Contract: `{summary.get('contract_version')}`",
        "",
        message.get("opening", ""),
        "",
        "## Status",
        "",
        f"- Decision: `{review.get('decision')}`",
        f"- Fidelity hold items: `{review.get('file_pass_but_fidelity_hold_count')}`",
        f"- Separate P1 missing rows: `{review.get('missing_p1_count')}`",
        f"- Public runtime activation: `{summary.get('runtime_release_impact', {}).get('public_runtime_allowed')}`",
        "",
        "## Modeler Delivery Blockers",
        "",
        "| Code | Severity | Count | Required resolution |",
        "|---|---|---:|---|",
    ]
    for blocker in summary.get("modeler_delivery_blockers", []):
        lines.append(
            f"| `{blocker.get('code')}` | `{blocker.get('severity')}` | {blocker.get('count')} | {blocker.get('required_resolution')} |"
        )
    lines.extend(
        [
            "",
            "## Per-Part Fix Requests",
            "",
        ]
    )
    for request in summary.get("per_part_fix_requests", []):
        lines.extend(
            [
                f"### {request.get('part')}",
                "",
                f"- Priority: `{request.get('priority')}`",
                f"- Variants: {', '.join(f'`{key}`' for key in request.get('variant_keys', []))}",
                "- Runtime visibility: `reviewer_only_until_fidelity_pass`",
                "",
                "| Line | Variant | Requested fix | Evidence |",
                "|---|---|---|---|",
            ]
        )
        for line_request in request.get("line_requests", []):
            evidence = ", ".join(f"`{item}`" for item in line_request.get("required_evidence", []))
            lines.append(
                "| "
                f"`{line_request.get('line_id')}` | "
                f"`{line_request.get('variant_key')}` | "
                f"{line_request.get('requested_fix')} | "
                f"{evidence} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Acceptance Recheck Steps",
            "",
            "| Step | Gate | Command | Pass condition |",
            "|---:|---|---|---|",
        ]
    )
    for step in summary.get("acceptance_recheck_steps", []):
        lines.append(
            f"| {step.get('step')} | `{step.get('gate')}` | `{step.get('command')}` | {step.get('pass_condition')} |"
        )
    lines.extend(
        [
            "",
            "## Runtime Release Impact",
            "",
        ]
    )
    runtime = summary.get("runtime_release_impact", {})
    lines.append(f"- Public runtime allowed: `{runtime.get('public_runtime_allowed')}`")
    lines.append(f"- Runtime block label: `{runtime.get('runtime_block_label')}`")
    lines.append(f"- Held variant count: `{runtime.get('held_variant_count')}`")
    lines.append(f"- Missing P1 count: `{runtime.get('missing_p1_count')}`")
    lines.append("")
    for rule in runtime.get("release_rules", []):
        lines.append(f"- {rule}")
    return "\n".join(lines) + "\n"


def _highest_priority(items: list[dict[str, Any]]) -> str:
    priorities = [str(item.get("priority", "P2")) for item in items]
    return min(priorities, key=lambda priority: PRIORITY_ORDER.get(priority, 99))


def _part_request_sort_key(request: dict[str, Any]) -> tuple[int, int, str]:
    part = str(request.get("part"))
    try:
        part_index = PART_ORDER.index(part)
    except ValueError:
        part_index = len(PART_ORDER)
    priority = PRIORITY_ORDER.get(str(request.get("priority")), 99)
    return priority, part_index, part


def _assert_audit_packet(packet: dict[str, Any]) -> None:
    missing = [key for key in triview_packet.REQUIRED_PACKET_KEYS if key not in packet]
    if missing:
        raise ValueError(f"audit packet missing required key(s): {missing}")


def _assert_summary_contract(summary: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_SUMMARY_KEYS if key not in summary]
    if missing:
        raise ValueError(f"fix request summary missing required key(s): {missing}")


def _json_payload(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n"


def _write_output(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, help="Saved JSON from export_modeler_triview_audit_packet.py, or '-'")
    parser.add_argument("--audit-doc", default=triview_packet.DEFAULT_AUDIT_DOC, type=Path)
    parser.add_argument("--worklist-doc", default=triview_packet.DEFAULT_WORKLIST_DOC, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path, help="Write Markdown fix request to this path")
    parser.add_argument("--report-json", action="store_true", help="Print machine-readable JSON summary to stdout")
    args = parser.parse_args(argv)

    summary = export_fix_request(
        packet_path=args.packet,
        audit_doc=args.audit_doc,
        worklist_doc=args.worklist_doc,
    )
    markdown = format_markdown(summary)
    if args.out:
        _write_output(args.out, markdown)
    if args.report_json:
        sys.stdout.write(_json_payload(summary))
    elif not args.out:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
