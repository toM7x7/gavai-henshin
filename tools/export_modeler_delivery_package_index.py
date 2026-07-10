"""Export a modeler delivery package index.

The index is the top-level sharing checklist for modeler handoff. It points to
the P1 order packet, 30variant tri-view fix request, handoff summary, and the
validators that must be run before sharing. It only reads local docs/manifests
through existing packet exporters; it does not render images, run Blender, or
inspect GLB geometry.
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


CONTRACT_VERSION = "modeler-delivery-package-index.v1"
DEFAULT_OUT = Path("docs/modeler-delivery-package-index-latest.md")
P1_ORDER_PACKET_OUT = Path("docs/modeler-deliveries/p1-limb-order-packet-latest.json")
TRIVIEW_AUDIT_PACKET_OUT = Path("qa/modeler-triview-audit-latest.json")
FIX_REQUEST_OUT = Path("docs/modeler-fix-request-latest.md")
HANDOFF_SUMMARY_OUT = Path("docs/modeler-handoff-summary-latest.md")
REQUIRED_INDEX_KEYS = (
    "pre_github_reading_order",
    "documents_to_share",
    "generated_packets",
    "validators_to_run",
    "github_submission_preflight",
    "blocked_items",
    "runtime_release_note",
    "do_not_share_local_artifacts",
)


def export_delivery_package_index(
    *,
    p1_manifest: str | Path = p1_order_exporter.order_validator.DEFAULT_MANIFEST,
    audit_doc: str | Path = fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    p1_packet = p1_order_exporter.export_order_packet(p1_manifest)
    fix_request = fix_request_exporter.export_fix_request(audit_doc=audit_doc, worklist_doc=worklist_doc)
    index = build_delivery_package_index(
        p1_packet=p1_packet,
        fix_request=fix_request,
        p1_manifest=p1_manifest,
        audit_doc=audit_doc,
        worklist_doc=worklist_doc,
    )
    _assert_index_contract(index)
    return index


def build_delivery_package_index(
    *,
    p1_packet: dict[str, Any],
    fix_request: dict[str, Any],
    p1_manifest: str | Path,
    audit_doc: str | Path,
    worklist_doc: str | Path,
) -> dict[str, Any]:
    p1_summary = p1_packet.get("summary", {})
    review = fix_request.get("review_status", {})
    runtime = _runtime_release_note(p1_packet, fix_request)
    blocked = _blocked_items(p1_packet, fix_request, runtime)
    return {
        "contract_version": CONTRACT_VERSION,
        "source": {
            "p1_manifest": _rel(p1_manifest),
            "audit_doc": _rel(audit_doc),
            "worklist_doc": _rel(worklist_doc),
            "rendering_or_blender_required": False,
            "glb_geometry_inspection_required": False,
        },
        "current_state_snapshot": _current_state_snapshot(p1_packet, fix_request, runtime),
        "pre_github_reading_order": _pre_github_reading_order(),
        "documents_to_share": _documents_to_share(),
        "generated_packets": _generated_packets(
            p1_manifest=p1_manifest,
            audit_doc=audit_doc,
            worklist_doc=worklist_doc,
            p1_order_item_count=int(p1_summary.get("order_item_count", 0) or 0),
            p1_blocked_asset_count=int(p1_summary.get("p1_blocked_asset_count", 0) or 0),
            fidelity_hold_count=int(review.get("file_pass_but_fidelity_hold_count", 0) or 0),
            per_part_fix_request_count=len(fix_request.get("per_part_fix_requests", [])),
        ),
        "validators_to_run": _validators_to_run(p1_manifest),
        "github_submission_preflight": _github_submission_preflight(p1_manifest),
        "blocked_items": blocked,
        "runtime_release_note": runtime,
        "do_not_share_local_artifacts": _do_not_share_local_artifacts(),
    }


def format_index(index: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return _json_payload(index)
    if output_format == "markdown":
        return _markdown_payload(index)
    raise ValueError(f"unsupported format: {output_format}")


def _documents_to_share() -> list[dict[str, Any]]:
    return [
        {
            "path": "docs/modeler-delivery-package-index-latest.md",
            "purpose": "Top-level index for the modeler handoff package.",
            "share": True,
            "generated": True,
        },
        {
            "path": "docs/modeler-handoff-summary-latest.md",
            "purpose": "Integrated P1 order and 30variant fidelity handoff summary.",
            "share": True,
            "generated": True,
        },
        {
            "path": "docs/modeler-fix-request-latest.md",
            "purpose": "30variant fidelity_hold fix request and acceptance recheck table.",
            "share": True,
            "generated": True,
        },
        {
            "path": "docs/p1-limb-variant-order-acceptance-2026-05-04.md",
            "purpose": "P1 limb order, delivery, catalog registration, and runtime activation contract.",
            "share": True,
            "generated": False,
        },
        {
            "path": "docs/modeler-30variant-triview-review-worklist-2026-05-04.md",
            "purpose": "Human review worklist for tri-view fidelity fixes.",
            "share": True,
            "generated": False,
        },
        {
            "path": "docs/modeler-triview-30variant-audit-table-2026-05-03.md",
            "purpose": "Source audit table behind the tri-view audit packet.",
            "share": True,
            "generated": False,
        },
        {
            "path": "docs/modeler-delivery-coordinate-review-2026-05-03.md",
            "purpose": "Coordinator note explaining file pass, fidelity_hold, and release-gate separation.",
            "share": True,
            "generated": False,
        },
    ]


def _pre_github_reading_order() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "path": "docs/modeler-delivery-package-index-latest.md",
            "read_for": "Top-level package scope, blocked state, QA commands, and local artifacts that must not be shared.",
            "must_confirm": [
                "P1 order and 30variant fidelity fixes are separate workstreams.",
                "runtime_release_note keeps public Web/Quest activation false.",
            ],
        },
        {
            "step": 2,
            "path": "docs/p1-limb-variant-order-acceptance-2026-05-04.md",
            "read_for": "P1 upperarm/forearm/hand/thigh order units, fileset contract, reject conditions, and runtime activation policy.",
            "must_confirm": [
                "There are 24 missing P1 assets: 3 lines x 4 limb families x left/right.",
                "runtime_activation_allowed=false is intentional until a separate runtime change.",
            ],
        },
        {
            "step": 3,
            "path": P1_ORDER_PACKET_OUT.as_posix(),
            "read_for": "Machine-readable modeler checklist generated from missing_matrix.",
            "must_confirm": [
                "order_items has 24 rows.",
                "blocked_by_stage.delivery has 24 rows before modeler delivery.",
            ],
        },
        {
            "step": 4,
            "path": "docs/modeler-30variant-triview-review-worklist-2026-05-04.md",
            "read_for": "30 delivered variants that are file-valid but still need tri-view fidelity rework.",
            "must_confirm": [
                "fidelity_hold means not public runtime-ready.",
                "missing_p1 rows are not part of the 30variant fix pass.",
            ],
        },
        {
            "step": 5,
            "path": FIX_REQUEST_OUT.as_posix(),
            "read_for": "Modeler-facing 30variant fix request and acceptance recheck table.",
            "must_confirm": [
                "per_part_fix_requests is the 30variant correction queue.",
                "modeler_delivery_blockers are listed before share.",
            ],
        },
        {
            "step": 6,
            "path": HANDOFF_SUMMARY_OUT.as_posix(),
            "read_for": "Single handoff summary after P1 packet and 30variant fix request are generated.",
            "must_confirm": [
                "P1 shortage=24 and fidelity_hold=30 are both visible.",
                "handoff validator passes in strict mode before GitHub submission.",
            ],
        },
    ]


def _generated_packets(
    *,
    p1_manifest: str | Path,
    audit_doc: str | Path,
    worklist_doc: str | Path,
    p1_order_item_count: int,
    p1_blocked_asset_count: int,
    fidelity_hold_count: int,
    per_part_fix_request_count: int,
) -> list[dict[str, Any]]:
    return [
        {
            "artifact": "p1_order_packet",
            "path": P1_ORDER_PACKET_OUT.as_posix(),
            "command": (
                "python tools\\export_p1_modeler_order_packet.py "
                f"--manifest {_cmd_path(p1_manifest)} --out {_cmd_path(P1_ORDER_PACKET_OUT)} "
                "--format json --report-json"
            ),
            "required_keys": list(p1_order_exporter.REQUIRED_TOP_LEVEL_KEYS),
            "current_summary": {
                "order_item_count": p1_order_item_count,
                "blocked_asset_count": p1_blocked_asset_count,
                "acceptance_label": "warn_now_block_p1",
            },
        },
        {
            "artifact": "triview_audit_packet",
            "path": TRIVIEW_AUDIT_PACKET_OUT.as_posix(),
            "command": (
                "python tools\\export_modeler_triview_audit_packet.py "
                f"--audit-doc {_cmd_path(audit_doc)} --worklist-doc {_cmd_path(worklist_doc)} "
                f"--out {_cmd_path(TRIVIEW_AUDIT_PACKET_OUT)} --report-json"
            ),
            "required_keys": list(fix_request_exporter.triview_packet.REQUIRED_PACKET_KEYS),
            "current_summary": {
                "fidelity_hold_count": fidelity_hold_count,
                "runtime_public_activation_allowed": False,
            },
        },
        {
            "artifact": "modeler_fix_request",
            "path": FIX_REQUEST_OUT.as_posix(),
            "command": (
                "python tools\\export_modeler_fix_request.py "
                f"--audit-doc {_cmd_path(audit_doc)} --worklist-doc {_cmd_path(worklist_doc)} "
                f"--out {_cmd_path(FIX_REQUEST_OUT)} --report-json"
            ),
            "required_keys": list(fix_request_exporter.REQUIRED_SUMMARY_KEYS),
            "current_summary": {
                "fidelity_hold_count": fidelity_hold_count,
                "per_part_fix_request_count": per_part_fix_request_count,
            },
        },
        {
            "artifact": "modeler_handoff_summary",
            "path": HANDOFF_SUMMARY_OUT.as_posix(),
            "command": (
                "python tools\\export_modeler_handoff_summary.py "
                f"--p1-manifest {_cmd_path(p1_manifest)} "
                f"--audit-doc {_cmd_path(audit_doc)} --worklist-doc {_cmd_path(worklist_doc)} "
                f"--out {_cmd_path(HANDOFF_SUMMARY_OUT)} --report-json"
            ),
            "required_keys": [
                "p1_order_status",
                "triview_fidelity_status",
                "modeler_action_queue",
                "acceptance_gate",
                "runtime_release_note",
                "handoff_message_japanese",
            ],
            "current_summary": {
                "p1_blocked_asset_count": p1_blocked_asset_count,
                "fidelity_hold_count": fidelity_hold_count,
                "must_pass_validator_before_share": True,
            },
        },
        {
            "artifact": "modeler_delivery_package_index",
            "path": DEFAULT_OUT.as_posix(),
            "command": (
                "python tools\\export_modeler_delivery_package_index.py "
                f"--p1-manifest {_cmd_path(p1_manifest)} "
                f"--audit-doc {_cmd_path(audit_doc)} --worklist-doc {_cmd_path(worklist_doc)} "
                f"--out {_cmd_path(DEFAULT_OUT)} --report-json"
            ),
            "required_keys": list(REQUIRED_INDEX_KEYS),
            "current_summary": {
                "documents_to_share_count": len(_documents_to_share()),
                "validators_to_run_count": 3,
            },
        },
    ]


def _validators_to_run(p1_manifest: str | Path) -> list[dict[str, Any]]:
    return [
        {
            "name": "P1 limb order manifest acceptance",
            "command": (
                "python tools\\validate_modeler_variant_order_manifest.py "
                f"--manifest {_cmd_path(p1_manifest)} --require-delivered --report-json"
            ),
            "purpose": "Prove the 24 P1 upperarm/forearm/hand/thigh line variants are delivered and catalog-ready.",
            "current_expected": "fail_or_warn_until_modeler_delivery; do not treat runtime_activation_allowed=false as acceptance failure.",
            "blocks": "P1 model delivery acceptance",
        },
        {
            "name": "Modeler handoff share gate",
            "command": (
                "python tools\\validate_modeler_handoff_summary.py "
                f"--handoff {_cmd_path(HANDOFF_SUMMARY_OUT)} --strict --report-json"
            ),
            "purpose": "Prevent sharing a handoff that omits P1=24, fidelity_hold=30, runtime/model-delivery distinction, gates, or Japanese message.",
            "current_expected": "pass before external modeler share",
            "blocks": "handoff sharing",
        },
        {
            "name": "Variant catalog routing guard",
            "command": "python tools\\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json",
            "purpose": "Keep Web/Quest runtime routing from silently using fallback or proxy variant keys.",
            "current_expected": "pass before public runtime activation of accepted variants",
            "blocks": "public runtime activation",
        },
    ]


def _github_submission_preflight(p1_manifest: str | Path) -> list[dict[str, Any]]:
    return [
        {
            "gate": "generate_package_index",
            "command": (
                "python tools\\export_modeler_delivery_package_index.py "
                f"--p1-manifest {_cmd_path(p1_manifest)} --out {_cmd_path(DEFAULT_OUT)} --report-json"
            ),
            "pass_before_github": True,
            "expected_current": "index JSON includes pre_github_reading_order, validators_to_run, blocked_items, and runtime_release_note.",
            "failure_action": "Regenerate the index or fix the exporter before using the package as a PR/issue reference.",
        },
        {
            "gate": "generate_p1_order_packet",
            "command": (
                "python tools\\export_p1_modeler_order_packet.py "
                f"--manifest {_cmd_path(p1_manifest)} --out {_cmd_path(P1_ORDER_PACKET_OUT)} "
                "--format json --report-json"
            ),
            "pass_before_github": True,
            "expected_current": "order_items=24, blocked_by_stage.delivery=24, acceptance_label=warn_now_block_p1.",
            "failure_action": "Do not summarize P1 shortage by hand; fix the manifest/report path until packet generation is deterministic.",
        },
        {
            "gate": "generate_triview_fix_request",
            "command": f"python tools\\export_modeler_fix_request.py --out {_cmd_path(FIX_REQUEST_OUT)} --report-json",
            "pass_before_github": True,
            "expected_current": "fidelity_hold_items=30 and runtime_release_impact.public_runtime_allowed=false.",
            "failure_action": "Keep the 30variant repair conversation out of GitHub until the audit packet is reproducible.",
        },
        {
            "gate": "handoff_share_validator",
            "command": (
                "python tools\\validate_modeler_handoff_summary.py "
                f"--handoff {_cmd_path(HANDOFF_SUMMARY_OUT)} --strict --report-json"
            ),
            "pass_before_github": True,
            "expected_current": "status=pass after handoff Markdown is generated.",
            "failure_action": "Regenerate or tighten the handoff summary; missing P1/fidelity/runtime wording must block sharing.",
        },
        {
            "gate": "p1_strict_delivery_acceptance",
            "command": (
                "python tools\\validate_modeler_variant_order_manifest.py "
                f"--manifest {_cmd_path(p1_manifest)} --require-delivered --report-json"
            ),
            "pass_before_github": False,
            "expected_current": "not pass until modeler delivery fills the 24 P1 filesets.",
            "failure_action": "Use the failure as the modeler order backlog; do not treat it as a release-package failure yet.",
        },
    ]


def _blocked_items(
    p1_packet: dict[str, Any],
    fix_request: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    p1_summary = p1_packet.get("summary", {})
    review = fix_request.get("review_status", {})
    blocked_by_stage = p1_packet.get("blocked_by_stage", {})
    return {
        "p1_order": {
            "blocked_asset_count": int(p1_summary.get("p1_blocked_asset_count", 0) or 0),
            "order_item_count": int(p1_summary.get("order_item_count", 0) or 0),
            "current_stop_stage_counts": {
                stage: int(blocked_by_stage.get(stage, {}).get("count", 0) or 0)
                for stage in p1_order_exporter.STAGE_ORDER
            },
            "acceptance_label": "warn_now_block_p1",
            "next_packet": P1_ORDER_PACKET_OUT.as_posix(),
        },
        "triview_fidelity": {
            "fidelity_hold_count": int(review.get("file_pass_but_fidelity_hold_count", 0) or 0),
            "missing_p1_rows_in_audit": int(review.get("missing_p1_count", 0) or 0),
            "per_part_fix_request_count": len(fix_request.get("per_part_fix_requests", [])),
            "acceptance_label": "fidelity_hold",
            "next_packet": FIX_REQUEST_OUT.as_posix(),
        },
        "runtime_activation": {
            "public_runtime_allowed": bool(runtime.get("public_runtime_allowed")),
            "reviewer_only_allowed": bool(runtime.get("reviewer_only_allowed")),
            "canonical_base_runtime_release_can_proceed": bool(
                runtime.get("canonical_base_runtime_release_can_proceed")
            ),
            "model_delivery_blocked": bool(runtime.get("model_delivery_blocked")),
            "runtime_block_label": runtime.get("runtime_block_label"),
        },
    }


def _current_state_snapshot(
    p1_packet: dict[str, Any],
    fix_request: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    p1_summary = p1_packet.get("summary", {})
    blocked_by_stage = p1_packet.get("blocked_by_stage", {})
    review = fix_request.get("review_status", {})
    return {
        "p1_missing_limb_scope": "upperarm/forearm/hand/thigh across 3 lines and left/right sides",
        "p1_order_item_count": int(p1_summary.get("order_item_count", 0) or 0),
        "p1_blocked_asset_count": int(p1_summary.get("p1_blocked_asset_count", 0) or 0),
        "p1_current_stop_stage": "delivery"
        if int(blocked_by_stage.get("delivery", {}).get("count", 0) or 0)
        else "unknown",
        "triview_review_decision": review.get("decision"),
        "triview_fidelity_hold_count": int(review.get("file_pass_but_fidelity_hold_count", 0) or 0),
        "triview_missing_p1_rows_are_separate": int(review.get("missing_p1_count", 0) or 0),
        "canonical_base_runtime_release_can_proceed": bool(
            runtime.get("canonical_base_runtime_release_can_proceed")
        ),
        "model_delivery_blocked": bool(runtime.get("model_delivery_blocked")),
        "public_runtime_allowed": bool(runtime.get("public_runtime_allowed")),
    }


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
            "Canonical/base exhibition runtime may proceed if package gates pass; "
            "P1 limb delivery and 30variant fidelity acceptance remain blocked, "
            "and public Web/Quest activation stays false until a separate approval."
        ),
    }


def _do_not_share_local_artifacts() -> list[dict[str, str]]:
    return [
        {
            "path": ".claude/worktrees/**",
            "reason": "Local review worktree and scratch state; share only the summarized docs/packets.",
        },
        {
            "path": "tests/.tmp/**",
            "reason": "Local pytest/audit scratch output; regenerate if engineering needs evidence.",
        },
        {
            "path": ".pytest_cache/** and __pycache__/**",
            "reason": "Local execution cache.",
        },
        {
            "path": "qa/local-* and unreferenced screenshots/renders",
            "reason": "Local QA captures are not authoritative unless listed in documents_to_share.",
        },
        {
            "path": "terminal logs or validator stdout copied outside generated packets",
            "reason": "Use --report-json outputs and Markdown packets instead of ad-hoc logs.",
        },
    ]


def _markdown_payload(index: dict[str, Any]) -> str:
    runtime = index.get("runtime_release_note", {})
    blocked = index.get("blocked_items", {})
    snapshot = index.get("current_state_snapshot", {})
    lines = [
        "# Modeler Delivery Package Index",
        "",
        f"- Contract: `{index.get('contract_version')}`",
        f"- Rendering/Blender required: `{index.get('source', {}).get('rendering_or_blender_required')}`",
        f"- P1 blocked assets: `{snapshot.get('p1_blocked_asset_count')}`",
        f"- 30variant fidelity_hold items: `{snapshot.get('triview_fidelity_hold_count')}`",
        f"- Public runtime allowed: `{snapshot.get('public_runtime_allowed')}`",
        "",
        "## Pre-GitHub Reading Order",
        "",
        "| Step | Path | Read for | Must confirm |",
        "|---:|---|---|---|",
    ]
    for item in index.get("pre_github_reading_order", []):
        confirms = "<br>".join(str(value) for value in item.get("must_confirm", []))
        lines.append(
            "| "
            f"{item.get('step')} | "
            f"`{item.get('path')}` | "
            f"{item.get('read_for')} | "
            f"{confirms} |"
        )
    lines.extend(
        [
        "",
        "## Documents To Share",
        "",
        "| Path | Purpose | Generated |",
        "|---|---|---:|",
        ]
    )
    for item in index.get("documents_to_share", []):
        lines.append(f"| `{item.get('path')}` | {item.get('purpose')} | `{item.get('generated')}` |")

    lines.extend(
        [
            "",
            "## Generated Packets",
            "",
            "| Artifact | Path | Command | Current summary |",
            "|---|---|---|---|",
        ]
    )
    for item in index.get("generated_packets", []):
        summary = ", ".join(f"{key}={value}" for key, value in item.get("current_summary", {}).items())
        lines.append(f"| `{item.get('artifact')}` | `{item.get('path')}` | `{item.get('command')}` | {summary} |")

    lines.extend(
        [
            "",
            "## Validators To Run",
            "",
            "| Name | Command | Blocks | Expected now |",
            "|---|---|---|---|",
        ]
    )
    for item in index.get("validators_to_run", []):
        lines.append(
            "| "
            f"{item.get('name')} | "
            f"`{item.get('command')}` | "
            f"{item.get('blocks')} | "
            f"{item.get('current_expected')} |"
        )

    lines.extend(
        [
            "",
            "## GitHub Submission Preflight",
            "",
            "| Gate | Command | Required before GitHub | Expected current result | Failure action |",
            "|---|---|---:|---|---|",
        ]
    )
    for item in index.get("github_submission_preflight", []):
        lines.append(
            "| "
            f"`{item.get('gate')}` | "
            f"`{item.get('command')}` | "
            f"`{item.get('pass_before_github')}` | "
            f"{item.get('expected_current')} | "
            f"{item.get('failure_action')} |"
        )

    lines.extend(
        [
            "",
            "## Blocked Items",
            "",
            f"- P1 blocked assets: `{blocked.get('p1_order', {}).get('blocked_asset_count')}`",
            f"- P1 current stop counts: `{blocked.get('p1_order', {}).get('current_stop_stage_counts')}`",
            f"- 30variant fidelity_hold items: `{blocked.get('triview_fidelity', {}).get('fidelity_hold_count')}`",
            f"- Separate missing P1 rows in audit: `{blocked.get('triview_fidelity', {}).get('missing_p1_rows_in_audit')}`",
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
            "## Do Not Share Local Artifacts",
            "",
            "| Path | Reason |",
            "|---|---|",
        ]
    )
    for item in index.get("do_not_share_local_artifacts", []):
        lines.append(f"| `{item.get('path')}` | {item.get('reason')} |")
    return "\n".join(lines) + "\n"


def _json_payload(index: dict[str, Any]) -> str:
    return json.dumps(index, ensure_ascii=False, indent=2) + "\n"


def _assert_index_contract(index: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_INDEX_KEYS if key not in index]
    if missing:
        raise ValueError(f"delivery package index missing required key(s): {missing}")


def _write_output(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="")


def _rel(path: str | Path) -> str:
    resolved = Path(path)
    if not resolved.is_absolute():
        return resolved.as_posix()
    repo_root = Path(__file__).resolve().parents[1]
    try:
        return resolved.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _cmd_path(path: str | Path) -> str:
    return str(Path(_rel(path))).replace("/", "\\")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p1-manifest", default=p1_order_exporter.order_validator.DEFAULT_MANIFEST, type=Path)
    parser.add_argument("--audit-doc", default=fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC, type=Path)
    parser.add_argument("--worklist-doc", default=fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path, help="Write the package index to this path")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--report-json", action="store_true", help="Print the JSON index to stdout")
    args = parser.parse_args(argv)

    index = export_delivery_package_index(
        p1_manifest=args.p1_manifest,
        audit_doc=args.audit_doc,
        worklist_doc=args.worklist_doc,
    )
    formatted = format_index(index, args.format)
    if args.out:
        _write_output(args.out, formatted)
    if args.report_json:
        sys.stdout.write(_json_payload(index))
    elif not args.out:
        sys.stdout.write(formatted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
