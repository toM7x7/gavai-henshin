"""Export one modeler handoff summary from P1 order and tri-view fix packets.

The summary combines two already machine-readable streams:

- tools/export_p1_modeler_order_packet.py for the 24 missing P1 limb variants.
- tools/export_modeler_fix_request.py for the 30 delivered-but-fidelity-held tri-view variants.

It writes Markdown for modeler handoff and can also print a JSON summary with
--report-json. It does not render images, run Blender, or inspect GLBs.
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

import export_modeler_fix_request as fix_request_exporter  # noqa: E402
import export_p1_modeler_order_packet as p1_order_exporter  # noqa: E402


CONTRACT_VERSION = "modeler-handoff-summary.v1"
DEFAULT_OUT = Path("docs/modeler-handoff-summary-latest.md")
REQUIRED_SUMMARY_KEYS = (
    "p1_order_status",
    "triview_fidelity_status",
    "modeler_action_queue",
    "acceptance_gate",
    "runtime_release_note",
    "handoff_message_japanese",
)
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def load_p1_order_packet(
    *,
    p1_packet_path: str | Path | None = None,
    p1_manifest: str | Path = p1_order_exporter.order_validator.DEFAULT_MANIFEST,
) -> dict[str, Any]:
    if p1_packet_path is None:
        return p1_order_exporter.export_order_packet(p1_manifest)
    packet = _read_json_file(p1_packet_path, label="p1 packet")
    _assert_p1_packet(packet)
    return packet


def load_fix_request_summary(
    *,
    fix_request_path: str | Path | None = None,
    triview_packet_path: str | Path | None = None,
    audit_doc: str | Path = fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    if fix_request_path is not None:
        summary = _read_json_file(fix_request_path, label="fix request")
        _assert_fix_request(summary)
        return summary
    return fix_request_exporter.export_fix_request(
        packet_path=triview_packet_path,
        audit_doc=audit_doc,
        worklist_doc=worklist_doc,
    )


def build_handoff_summary(
    *,
    p1_packet: dict[str, Any],
    fix_request: dict[str, Any],
) -> dict[str, Any]:
    _assert_p1_packet(p1_packet)
    _assert_fix_request(fix_request)
    p1_status = _p1_order_status(p1_packet)
    triview_status = _triview_fidelity_status(fix_request)
    action_queue = _modeler_action_queue(p1_packet, fix_request)
    summary = {
        "contract_version": CONTRACT_VERSION,
        "source": {
            "p1_packet_contract_version": p1_packet.get("contract_version"),
            "fix_request_contract_version": fix_request.get("contract_version"),
            "p1_manifest": p1_packet.get("source", {}).get("manifest"),
            "triview_audit_doc": fix_request.get("source", {}).get("audit_doc"),
            "triview_worklist_doc": fix_request.get("source", {}).get("worklist_doc"),
            "rendering_or_blender_required": False,
        },
        "p1_order_status": p1_status,
        "triview_fidelity_status": triview_status,
        "modeler_action_queue": action_queue,
        "acceptance_gate": _acceptance_gate(p1_packet, fix_request),
        "runtime_release_note": _runtime_release_note(p1_packet, fix_request),
        "handoff_message_japanese": _handoff_message_japanese(p1_status, triview_status, action_queue),
    }
    _assert_summary_contract(summary)
    return summary


def export_handoff_summary(
    *,
    p1_packet_path: str | Path | None = None,
    p1_manifest: str | Path = p1_order_exporter.order_validator.DEFAULT_MANIFEST,
    triview_packet_path: str | Path | None = None,
    fix_request_path: str | Path | None = None,
    audit_doc: str | Path = fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    return build_handoff_summary(
        p1_packet=load_p1_order_packet(p1_packet_path=p1_packet_path, p1_manifest=p1_manifest),
        fix_request=load_fix_request_summary(
            fix_request_path=fix_request_path,
            triview_packet_path=triview_packet_path,
            audit_doc=audit_doc,
            worklist_doc=worklist_doc,
        ),
    )


def format_markdown(summary: dict[str, Any]) -> str:
    p1 = summary.get("p1_order_status", {})
    tri = summary.get("triview_fidelity_status", {})
    runtime = summary.get("runtime_release_note", {})
    lines = [
        "# Modeler Handoff Summary",
        "",
        f"Contract: `{summary.get('contract_version')}`",
        "",
        "## Handoff Message",
        "",
        summary.get("handoff_message_japanese", ""),
        "",
        "## P1 Order Status",
        "",
        f"- Order items: `{p1.get('order_item_count')}`",
        f"- Blocked assets: `{p1.get('blocked_asset_count')}`",
        f"- Current stop: `{p1.get('primary_stop_stage')}`",
        f"- Runtime activation allowed: `{p1.get('runtime_activation_allowed')}`",
        "",
        "## Triview Fidelity Status",
        "",
        f"- Fidelity hold items: `{tri.get('fidelity_hold_count')}`",
        f"- Per-part fix request groups: `{tri.get('per_part_fix_request_count')}`",
        f"- Separate missing P1 rows referenced by audit: `{tri.get('missing_p1_count')}`",
        f"- Runtime public activation allowed: `{tri.get('runtime_public_activation_allowed')}`",
        "",
        "## Modeler Action Queue",
        "",
        "| Priority | Source | Scope | Count | Action | Acceptance target |",
        "|---|---|---|---:|---|---|",
    ]
    for item in summary.get("modeler_action_queue", []):
        lines.append(
            "| "
            f"`{item.get('priority')}` | "
            f"`{item.get('source')}` | "
            f"`{item.get('scope')}` | "
            f"{item.get('item_count')} | "
            f"{item.get('action')} | "
            f"{item.get('acceptance_target')} |"
        )
    lines.extend(
        [
            "",
            "## Acceptance Gate",
            "",
            "| Gate | Owner | Required result |",
            "|---|---|---|",
        ]
    )
    for gate in summary.get("acceptance_gate", []):
        lines.append(
            f"| `{gate.get('gate')}` | {gate.get('owner')} | {gate.get('required_result')} |"
        )
    lines.extend(
        [
            "",
            "## Runtime Release Note",
            "",
            f"- Public runtime allowed: `{runtime.get('public_runtime_allowed')}`",
            f"- Canonical/base runtime release can proceed: `{runtime.get('canonical_base_runtime_release_can_proceed')}`",
            f"- Model delivery blocked: `{runtime.get('model_delivery_blocked')}`",
            f"- Reviewer-only allowed: `{runtime.get('reviewer_only_allowed')}`",
            f"- Block label: `{runtime.get('runtime_block_label')}`",
            f"- Distinction: {runtime.get('distinction_note')}",
            "",
        ]
    )
    for reason in runtime.get("block_reasons", []):
        lines.append(f"- {reason}")
    return "\n".join(lines) + "\n"


def _p1_order_status(packet: dict[str, Any]) -> dict[str, Any]:
    summary = packet.get("summary", {})
    blocked_by_stage = packet.get("blocked_by_stage", {})
    stage_counts = {
        stage: int(blocked_by_stage.get(stage, {}).get("count", 0) or 0)
        for stage in p1_order_exporter.STAGE_ORDER
    }
    primary_stop = max(stage_counts, key=lambda stage: stage_counts[stage]) if stage_counts else "unknown"
    return {
        "contract_version": packet.get("contract_version"),
        "order_item_count": int(summary.get("order_item_count", 0) or 0),
        "blocked_asset_count": int(summary.get("p1_blocked_asset_count", 0) or 0),
        "runtime_activation_blocked_count": int(summary.get("runtime_activation_blocked_count", 0) or 0),
        "blocked_by_stage_counts": stage_counts,
        "primary_stop_stage": primary_stop,
        "next_action": blocked_by_stage.get(primary_stop, {}).get("next_action"),
        "runtime_activation_allowed": bool(
            packet.get("runtime_activation_policy", {}).get("runtime_activation_allowed", False)
        ),
    }


def _triview_fidelity_status(fix_request: dict[str, Any]) -> dict[str, Any]:
    review = fix_request.get("review_status", {})
    runtime = fix_request.get("runtime_release_impact", {})
    blockers = fix_request.get("modeler_delivery_blockers", [])
    return {
        "contract_version": fix_request.get("contract_version"),
        "decision": review.get("decision"),
        "fidelity_hold_count": int(review.get("file_pass_but_fidelity_hold_count", 0) or 0),
        "missing_p1_count": int(review.get("missing_p1_count", 0) or 0),
        "per_part_fix_request_count": len(fix_request.get("per_part_fix_requests", [])),
        "blocker_count": sum(1 for item in blockers if item.get("severity") == "blocker"),
        "runtime_public_activation_allowed": bool(runtime.get("public_runtime_allowed", False)),
        "runtime_block_label": runtime.get("runtime_block_label"),
    }


def _modeler_action_queue(p1_packet: dict[str, Any], fix_request: dict[str, Any]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for request in fix_request.get("per_part_fix_requests", []):
        queue.append(
            {
                "priority": request.get("priority", "P2"),
                "source": "triview_fidelity_fix",
                "scope": request.get("part"),
                "item_count": request.get("variant_count", 0),
                "variant_keys": request.get("variant_keys", []),
                "action": _fix_request_action(request),
                "acceptance_target": "review_candidate after sidecar provenance and front/side/back/3Q evidence",
                "runtime_visibility": "reviewer_only_until_fidelity_pass",
            }
        )

    p1_order_count = int(p1_packet.get("summary", {}).get("order_item_count", 0) or 0)
    p1_delivery_count = int(p1_packet.get("blocked_by_stage", {}).get("delivery", {}).get("count", 0) or 0)
    queue.append(
        {
            "priority": "P1",
            "source": "p1_limb_order",
            "scope": "upperarm/forearm/hand/thigh left-right 3-line variants",
            "item_count": p1_order_count,
            "variant_keys": [item.get("variant_key") for item in p1_packet.get("order_items", [])],
            "action": (
                f"Deliver {p1_delivery_count} missing P1 limb filesets with GLB, sidecar, source blend, "
                "preview mesh, and review evidence."
            ),
            "acceptance_target": "P1 order validator strict pass with catalog gaps=0 and delivery gaps=0",
            "runtime_visibility": "not_public_until_separate_runtime_activation",
        }
    )
    return sorted(queue, key=_queue_sort_key)


def _fix_request_action(request: dict[str, Any]) -> str:
    lines = request.get("line_requests", [])
    first = lines[0] if lines else {}
    return str(first.get("requested_fix") or "Apply tri-view fidelity rework and evidence updates.")


def _acceptance_gate(p1_packet: dict[str, Any], fix_request: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "triview_fix_delivery",
            "owner": "modeler",
            "required_result": "30 delivered variants keep existing keys and include stronger line identity, sidecar provenance, and full tri-view evidence.",
            "source_count": len(fix_request.get("fidelity_hold_items", [])),
        },
        {
            "gate": "p1_limb_order_delivery",
            "owner": "modeler",
            "required_result": "24 P1 limb order items are delivered and catalog-registered without runtime activation.",
            "source_count": p1_packet.get("summary", {}).get("order_item_count", 0),
        },
        {
            "gate": "engineering_validation",
            "owner": "engineering",
            "required_result": "Run order/fix acceptance commands; no missing delivery, catalog, sidecar, tri-view, or fallback blocker remains.",
            "source_count": 0,
        },
        {
            "gate": "runtime_release",
            "owner": "release reviewer",
            "required_result": "Public Web/Quest runtime mapping remains blocked until fidelity_pass and separate activation approval.",
            "source_count": 0,
        },
    ]


def _runtime_release_note(p1_packet: dict[str, Any], fix_request: dict[str, Any]) -> dict[str, Any]:
    p1_runtime = p1_packet.get("runtime_activation_policy", {})
    tri_runtime = fix_request.get("runtime_release_impact", {})
    return {
        "public_runtime_allowed": False,
        "canonical_base_runtime_release_can_proceed": True,
        "model_delivery_blocked": True,
        "reviewer_only_allowed": True,
        "runtime_block_label": "blocked_by_p1_order_and_triview_fidelity_hold",
        "p1_runtime_activation_allowed": bool(p1_runtime.get("runtime_activation_allowed", False)),
        "triview_public_runtime_allowed": bool(tri_runtime.get("public_runtime_allowed", False)),
        "distinction_note": (
            "Canonical/base runtime release can proceed if package gates pass; "
            "modeler P1 delivery and 30variant fidelity acceptance remain blocked."
        ),
        "block_reasons": [
            "P1 limb variants are still stopped at order/delivery/catalog/runtime activation gates.",
            "30 delivered variants are file-valid but remain fidelity_hold until visual identity, evidence, and sidecar provenance pass.",
            "Any public Web/Quest selector mapping requires a separate runtime activation change after acceptance.",
        ],
    }


def _handoff_message_japanese(
    p1_status: dict[str, Any],
    triview_status: dict[str, Any],
    action_queue: list[dict[str, Any]],
) -> str:
    p0_count = sum(1 for item in action_queue if item.get("priority") == "P0")
    p1_count = sum(1 for item in action_queue if item.get("priority") == "P1")
    return (
        "今回のモデラー依頼は2系統です。"
        f"既存30variantはファイル受領済みですが、三面図再現性が未達のため"
        f"{triview_status.get('fidelity_hold_count')}件をfidelity_holdの修正対象にします。"
        f"別枠でP1 limbは{p1_status.get('blocked_asset_count')}件が未受け入れで、"
        "upperarm/forearm/hand/thighの左右3ライン納品が必要です。"
        f"作業順はP0の三面図修正{p0_count}グループを先に処理し、続いてP1の"
        f"{p1_count}グループを納品/受入に流してください。"
        "canonical/base runtime releaseはpackage gateが通れば進められますが、"
        "model deliveryはP1不足と30variant fidelity_holdが解消するまでblockedです。"
        "どちらもWeb/Questのpublic runtime activationではなく、受け入れ後に別途runtime activation判断を行います。"
    )


def _queue_sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
    return (
        PRIORITY_ORDER.get(str(item.get("priority")), 99),
        str(item.get("source")),
        str(item.get("scope")),
    )


def _assert_p1_packet(packet: dict[str, Any]) -> None:
    missing = [key for key in p1_order_exporter.REQUIRED_TOP_LEVEL_KEYS if key not in packet]
    if missing:
        raise ValueError(f"P1 order packet missing required key(s): {missing}")


def _assert_fix_request(summary: dict[str, Any]) -> None:
    missing = [key for key in fix_request_exporter.REQUIRED_SUMMARY_KEYS if key not in summary]
    if missing:
        raise ValueError(f"fix request missing required key(s): {missing}")


def _assert_summary_contract(summary: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_SUMMARY_KEYS if key not in summary]
    if missing:
        raise ValueError(f"handoff summary missing required key(s): {missing}")


def _read_json_file(path: str | Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label}: JSON root must be an object")
    return payload


def _json_payload(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n"


def _write_output(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p1-packet", type=Path, help="Saved JSON from export_p1_modeler_order_packet.py")
    parser.add_argument("--p1-manifest", default=p1_order_exporter.order_validator.DEFAULT_MANIFEST, type=Path)
    parser.add_argument("--triview-packet", type=Path, help="Saved JSON from export_modeler_triview_audit_packet.py")
    parser.add_argument("--fix-request", type=Path, help="Saved JSON summary from export_modeler_fix_request.py")
    parser.add_argument("--audit-doc", default=fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC, type=Path)
    parser.add_argument("--worklist-doc", default=fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path, help="Write Markdown handoff summary to this path")
    parser.add_argument("--report-json", action="store_true", help="Print machine-readable JSON summary to stdout")
    args = parser.parse_args(argv)

    summary = export_handoff_summary(
        p1_packet_path=args.p1_packet,
        p1_manifest=args.p1_manifest,
        triview_packet_path=args.triview_packet,
        fix_request_path=args.fix_request,
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
