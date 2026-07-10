"""Validate a modeler handoff summary before sharing it.

The gate accepts either:

- JSON from tools/export_modeler_handoff_summary.py --report-json
- Markdown from tools/export_modeler_handoff_summary.py --out ...
- no input, in which case it generates the summary from local source docs/packets

It is intentionally read-only and does not render images, run Blender, or touch
GLB assets.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import export_modeler_handoff_summary as handoff_exporter  # noqa: E402


CONTRACT_VERSION = "modeler-handoff-summary-validation.v1"
JAPANESE_TEXT_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
REQUIRED_ACCEPTANCE_GATES = {
    "triview_fix_delivery",
    "p1_limb_order_delivery",
    "engineering_validation",
    "runtime_release",
}
REQUIRED_MARKDOWN_SECTIONS = (
    "## Handoff Message",
    "## P1 Order Status",
    "## Triview Fidelity Status",
    "## Modeler Action Queue",
    "## Acceptance Gate",
    "## Runtime Release Note",
)


def validate_modeler_handoff_summary(
    handoff: str | Path | dict[str, Any] | None = None,
    *,
    strict: bool = False,
    p1_packet_path: str | Path | None = None,
    p1_manifest: str | Path = handoff_exporter.p1_order_exporter.order_validator.DEFAULT_MANIFEST,
    triview_packet_path: str | Path | None = None,
    fix_request_path: str | Path | None = None,
    audit_doc: str | Path = handoff_exporter.fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = handoff_exporter.fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    source = _load_source(
        handoff,
        p1_packet_path=p1_packet_path,
        p1_manifest=p1_manifest,
        triview_packet_path=triview_packet_path,
        fix_request_path=fix_request_path,
        audit_doc=audit_doc,
        worklist_doc=worklist_doc,
    )
    if source["kind"] == "json":
        checks = _validate_json_summary(source["payload"])
    else:
        checks = _validate_markdown_summary(source["payload"])

    reasons = [
        check["message"]
        for check in checks
        if check["status"] == "fail" or strict and check["status"] == "warn"
    ]
    warnings = [check["message"] for check in checks if check["status"] == "warn" and check["message"] not in reasons]
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not reasons,
        "status": "fail" if reasons else "warn" if warnings else "pass",
        "strict": strict,
        "source": {
            "kind": source["kind"],
            "path": source.get("path"),
            "generated_from_sources": source.get("generated_from_sources", False),
        },
        "check_count": len(checks),
        "reasons": reasons,
        "warnings": warnings,
        "checks": checks,
    }


def _load_source(
    handoff: str | Path | dict[str, Any] | None,
    *,
    p1_packet_path: str | Path | None,
    p1_manifest: str | Path,
    triview_packet_path: str | Path | None,
    fix_request_path: str | Path | None,
    audit_doc: str | Path,
    worklist_doc: str | Path,
) -> dict[str, Any]:
    if handoff is None:
        summary = handoff_exporter.export_handoff_summary(
            p1_packet_path=p1_packet_path,
            p1_manifest=p1_manifest,
            triview_packet_path=triview_packet_path,
            fix_request_path=fix_request_path,
            audit_doc=audit_doc,
            worklist_doc=worklist_doc,
        )
        return {"kind": "json", "payload": summary, "generated_from_sources": True}
    if isinstance(handoff, dict):
        return {"kind": "json", "payload": handoff}

    path = Path(handoff)
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: JSON root must be an object")
        return {"kind": "json", "payload": payload, "path": path.as_posix()}
    return {"kind": "markdown", "payload": text, "path": path.as_posix()}


def _validate_json_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    _add_check(
        checks,
        "required_top_level_keys",
        all(key in summary for key in handoff_exporter.REQUIRED_SUMMARY_KEYS),
        "handoff JSON contains all required top-level keys",
        f"handoff JSON missing required key(s): {[key for key in handoff_exporter.REQUIRED_SUMMARY_KEYS if key not in summary]}",
    )

    p1 = summary.get("p1_order_status") if isinstance(summary.get("p1_order_status"), dict) else {}
    tri = (
        summary.get("triview_fidelity_status")
        if isinstance(summary.get("triview_fidelity_status"), dict)
        else {}
    )
    runtime = (
        summary.get("runtime_release_note")
        if isinstance(summary.get("runtime_release_note"), dict)
        else {}
    )
    action_queue = summary.get("modeler_action_queue") if isinstance(summary.get("modeler_action_queue"), list) else []
    acceptance_gate = summary.get("acceptance_gate") if isinstance(summary.get("acceptance_gate"), list) else []
    message = str(summary.get("handoff_message_japanese") or "")

    _add_check(
        checks,
        "p1_shortage_24_explicit",
        p1.get("order_item_count") == 24 and p1.get("blocked_asset_count") == 24,
        "P1 shortage explicitly states 24 order items and 24 blocked assets",
        f"P1 shortage must state 24 order items and 24 blocked assets; got order={p1.get('order_item_count')!r}, blocked={p1.get('blocked_asset_count')!r}",
    )
    _add_check(
        checks,
        "p1_action_queue_present",
        any(item.get("source") == "p1_limb_order" and item.get("item_count") == 24 for item in action_queue),
        "modeler action queue includes the 24-item P1 limb order",
        "modeler action queue must include source=p1_limb_order with item_count=24",
    )
    _add_check(
        checks,
        "fidelity_hold_explicit",
        tri.get("fidelity_hold_count") == 30 and "fidelity_hold" in str(tri.get("decision", "")),
        "30variant fidelity_hold is explicit",
        f"triview status must state fidelity_hold_count=30 and decision containing fidelity_hold; got count={tri.get('fidelity_hold_count')!r}, decision={tri.get('decision')!r}",
    )
    _add_check(
        checks,
        "triview_action_queue_present",
        any(item.get("source") == "triview_fidelity_fix" for item in action_queue),
        "modeler action queue includes tri-view fidelity fixes",
        "modeler action queue must include at least one source=triview_fidelity_fix item",
    )
    _add_check(
        checks,
        "runtime_model_delivery_distinction",
        runtime.get("canonical_base_runtime_release_can_proceed") is True
        and runtime.get("model_delivery_blocked") is True
        and runtime.get("public_runtime_allowed") is False,
        "runtime release/model delivery distinction is explicit",
        "runtime note must distinguish canonical/base runtime can proceed from blocked model delivery, while public runtime activation remains false",
    )
    _add_check(
        checks,
        "acceptance_gate_complete",
        REQUIRED_ACCEPTANCE_GATES.issubset(
            {str(item.get("gate")) for item in acceptance_gate if isinstance(item, dict)}
        ),
        "acceptance recheck gates are present",
        f"acceptance_gate must include {sorted(REQUIRED_ACCEPTANCE_GATES)}",
    )
    _add_check(
        checks,
        "japanese_handoff_message_present",
        bool(message.strip()) and bool(JAPANESE_TEXT_RE.search(message)),
        "Japanese handoff message is present",
        "handoff_message_japanese must contain non-empty Japanese text",
    )
    _add_check(
        checks,
        "japanese_handoff_message_mentions_core_counts",
        "P1" in message and "30variant" in message and "fidelity_hold" in message,
        "Japanese handoff message names P1, 30variant, and fidelity_hold",
        "handoff_message_japanese must mention P1, 30variant, and fidelity_hold",
    )
    return checks


def _validate_markdown_summary(text: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    _add_check(
        checks,
        "required_markdown_sections",
        all(section in text for section in REQUIRED_MARKDOWN_SECTIONS),
        "handoff Markdown contains all required sections",
        f"handoff Markdown missing required section(s): {[section for section in REQUIRED_MARKDOWN_SECTIONS if section not in text]}",
    )
    _add_check(
        checks,
        "p1_shortage_24_explicit",
        "Order items: `24`" in text and "Blocked assets: `24`" in text,
        "P1 shortage explicitly states 24 order items and 24 blocked assets",
        "handoff Markdown must contain Order items: `24` and Blocked assets: `24`",
    )
    _add_check(
        checks,
        "fidelity_hold_explicit",
        "Fidelity hold items: `30`" in text and "fidelity_hold" in text,
        "30variant fidelity_hold is explicit",
        "handoff Markdown must contain Fidelity hold items: `30` and fidelity_hold",
    )
    _add_check(
        checks,
        "runtime_model_delivery_distinction",
        "Canonical/base runtime release can proceed: `True`" in text
        and "Model delivery blocked: `True`" in text
        and "Public runtime allowed: `False`" in text,
        "runtime release/model delivery distinction is explicit",
        "handoff Markdown must distinguish canonical/base runtime can proceed, model delivery blocked, and public runtime false",
    )
    _add_check(
        checks,
        "acceptance_gate_complete",
        all(gate in text for gate in REQUIRED_ACCEPTANCE_GATES),
        "acceptance recheck gates are present",
        f"handoff Markdown must include gates {sorted(REQUIRED_ACCEPTANCE_GATES)}",
    )
    _add_check(
        checks,
        "japanese_handoff_message_present",
        bool(JAPANESE_TEXT_RE.search(text)) and "今回のモデラー依頼" in text,
        "Japanese handoff message is present",
        "handoff Markdown must include the Japanese handoff message",
    )
    return checks


def _add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    pass_message: str,
    fail_message: str,
    *,
    severity: str = "fail",
) -> None:
    checks.append(
        {
            "check": name,
            "status": "pass" if passed else severity,
            "message": pass_message if passed else fail_message,
        }
    )


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] modeler handoff summary validation")
    print(f"source={result['source']['kind']} strict={str(result['strict']).lower()} checks={result['check_count']}")
    for check in result["checks"]:
        if check["status"] != "pass":
            print(f"  {check['status']}  {check['check']}: {check['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, help="Handoff Markdown or JSON to validate")
    parser.add_argument("--p1-packet", type=Path, help="Saved JSON from export_p1_modeler_order_packet.py")
    parser.add_argument("--p1-manifest", default=handoff_exporter.p1_order_exporter.order_validator.DEFAULT_MANIFEST, type=Path)
    parser.add_argument("--triview-packet", type=Path, help="Saved JSON from export_modeler_triview_audit_packet.py")
    parser.add_argument("--fix-request", type=Path, help="Saved JSON summary from export_modeler_fix_request.py")
    parser.add_argument("--audit-doc", default=handoff_exporter.fix_request_exporter.triview_packet.DEFAULT_AUDIT_DOC, type=Path)
    parser.add_argument("--worklist-doc", default=handoff_exporter.fix_request_exporter.triview_packet.DEFAULT_WORKLIST_DOC, type=Path)
    parser.add_argument("--strict", action="store_true", help="Promote warnings to failures")
    parser.add_argument("--report-json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args(argv)

    result = validate_modeler_handoff_summary(
        args.handoff,
        strict=args.strict,
        p1_packet_path=args.p1_packet,
        p1_manifest=args.p1_manifest,
        triview_packet_path=args.triview_packet,
        fix_request_path=args.fix_request,
        audit_doc=args.audit_doc,
        worklist_doc=args.worklist_doc,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
