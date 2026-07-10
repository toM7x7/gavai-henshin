"""Export a machine-readable modeler tri-view audit packet.

This helper reads the existing 30-variant tri-view audit docs and turns the
Markdown review table into a JSON packet for modeler fix requests. It does not
run Blender, render images, or inspect GLB geometry.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DOC = Path("docs/modeler-triview-30variant-audit-table-2026-05-03.md")
DEFAULT_WORKLIST_DOC = Path("docs/modeler-30variant-triview-review-worklist-2026-05-04.md")
CONTRACT_VERSION = "modeler-triview-audit-packet.v1"
REQUIRED_PACKET_KEYS = (
    "review_status",
    "fidelity_hold_items",
    "per_part_findings",
    "modeler_fix_message_outline",
    "acceptance_recheck_steps",
    "runtime_release_impact",
)

PART_ORDER = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
)
P0_PARTS = {"helmet", "chest", "back", "left_shin", "right_shin", "left_boot", "right_boot"}
P1_PARTS = {"waist", "left_shoulder", "right_shoulder"}
P1_MISSING_PARTS = {
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
}
REQUIRED_EVIDENCE = ("front", "side", "back", "3q", "source_overlay_front", "closeup", "boot_closeup_side")
SIDECAR_FIELDS = ("source_concept_ids", "line_id", "design_intent", "fidelity_notes")
RUNTIME_BLOCK_LABEL = "runtime_release_blocked_by_fidelity_hold"


def export_triview_audit_packet(
    *,
    audit_doc: str | Path = DEFAULT_AUDIT_DOC,
    worklist_doc: str | Path = DEFAULT_WORKLIST_DOC,
) -> dict[str, Any]:
    audit_path = _repo_path(audit_doc)
    worklist_path = _repo_path(worklist_doc)
    audit_text = audit_path.read_text(encoding="utf-8")
    worklist_text = worklist_path.read_text(encoding="utf-8") if worklist_path.is_file() else ""

    priorities = _parse_worklist_priorities(worklist_text)
    line_holds = _parse_line_hold_reasons(audit_text)
    defects = _parse_numbered_section(audit_text, "Defect List")
    reorder_memo = _parse_numbered_section(audit_text, "Reorder Memo")
    findings = _parse_per_part_findings(audit_text, priorities=priorities)
    hold_items = [finding for finding in findings if finding["finding_type"] == "fidelity_hold"]
    missing_p1_items = [finding for finding in findings if finding["finding_type"] == "missing_p1"]

    packet = {
        "contract_version": CONTRACT_VERSION,
        "source": {
            "audit_doc": _rel(audit_path),
            "worklist_doc": _rel(worklist_path),
            "parser": "markdown_tables",
            "rendering_or_blender_required": False,
        },
        "review_status": _review_status(findings, hold_items, missing_p1_items),
        "fidelity_hold_items": hold_items,
        "per_part_findings": findings,
        "modeler_fix_message_outline": _modeler_fix_message_outline(
            hold_items=hold_items,
            missing_p1_items=missing_p1_items,
            line_holds=line_holds,
            defects=defects,
            reorder_memo=reorder_memo,
        ),
        "acceptance_recheck_steps": _acceptance_recheck_steps(),
        "runtime_release_impact": _runtime_release_impact(hold_items, missing_p1_items),
    }
    _assert_packet_contract(packet)
    return packet


def _parse_per_part_findings(text: str, *, priorities: dict[str, str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    current_part: str | None = None
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        if raw.startswith("### "):
            candidate = _normalize_part_name(raw.removeprefix("### ").strip())
            current_part = candidate if candidate in PART_ORDER else None
            index += 1
            continue
        if current_part and _is_per_part_table_header(raw):
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = _table_cells(lines[index])
                if len(cells) >= 6:
                    findings.append(_finding_from_cells(current_part, cells, priorities=priorities))
                index += 1
            continue
        index += 1
    return sorted(findings, key=_finding_sort_key)


def _finding_from_cells(
    part: str,
    cells: list[str],
    *,
    priorities: dict[str, str],
) -> dict[str, Any]:
    line_id, delivered_key, file_gate, triview_check, auditor_status, reorder_memo = cells[:6]
    line_id = _strip_code(line_id)
    variant_key = None if delivered_key == "-" else _strip_code(delivered_key)
    finding_type = "missing_p1" if "missing" in auditor_status.lower() else "fidelity_hold"
    priority = priorities.get(part) or _default_priority(part)
    return {
        "part": part,
        "priority": priority,
        "line_id": line_id,
        "variant_key": variant_key,
        "file_gate": _normalize_status(file_gate),
        "triview_check": triview_check,
        "auditor_status": auditor_status,
        "finding_type": finding_type,
        "runtime_visibility": "reviewer_only_until_fidelity_pass"
        if finding_type == "fidelity_hold"
        else "not_available_until_p1_delivery",
        "modeler_action": reorder_memo,
        "required_evidence": _required_evidence_for_part(part),
        "sidecar_fields_required": list(SIDECAR_FIELDS) if finding_type == "fidelity_hold" else [],
        "acceptance_label": "fidelity_hold" if finding_type == "fidelity_hold" else "missing_p1_order_gap",
        "runtime_release_allowed": False,
    }


def _parse_line_hold_reasons(text: str) -> list[dict[str, Any]]:
    rows = _parse_table_after_header(
        text,
        "| Line | Source | Must read from triview | Current hold reason |",
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 4:
            continue
        result.append(
            {
                "line_id": _strip_code(row[0]),
                "source": _strip_code(row[1]),
                "must_read": row[2],
                "current_hold_reason": row[3],
            }
        )
    return result


def _parse_worklist_priorities(text: str) -> dict[str, str]:
    priorities: dict[str, str] = {}
    current_part: str | None = None
    for raw in text.splitlines():
        if raw.startswith("### "):
            part = _normalize_part_name(raw.removeprefix("### ").strip())
            current_part = part if part in PART_ORDER else None
            continue
        if current_part:
            match = re.match(r"Priority:\s*(P\d)", raw.strip())
            if match:
                priorities[current_part] = match.group(1)
    return priorities


def _parse_numbered_section(text: str, section_title: str) -> list[str]:
    lines = text.splitlines()
    capture = False
    items: list[str] = []
    for raw in lines:
        if raw.strip() == f"## {section_title}":
            capture = True
            continue
        if capture and raw.startswith("## "):
            break
        if capture:
            match = re.match(r"\s*\d+\.\s+(.*)", raw)
            if match:
                items.append(match.group(1).strip())
    return items


def _parse_table_after_header(text: str, header: str) -> list[list[str]]:
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        if raw.strip() == header:
            rows: list[list[str]] = []
            cursor = index + 2
            while cursor < len(lines) and lines[cursor].strip().startswith("|"):
                rows.append(_table_cells(lines[cursor]))
                cursor += 1
            return rows
    return []


def _is_per_part_table_header(line: str) -> bool:
    return line.strip() == "| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |"


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _strip_code(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def _normalize_part_name(value: str) -> str:
    return _strip_code(value).strip().lower().replace(" ", "_")


def _normalize_status(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _default_priority(part: str) -> str:
    if part in P0_PARTS:
        return "P0"
    if part in P1_PARTS or part in P1_MISSING_PARTS:
        return "P1"
    return "P2"


def _required_evidence_for_part(part: str) -> list[str]:
    evidence = ["front", "side", "back", "3q", "source_overlay_front"]
    if part == "helmet":
        evidence.extend(["helmet_closeup_front", "helmet_closeup_side"])
    elif part in {"chest", "back", "waist"}:
        evidence.extend(["torso_closeup_front", "torso_closeup_back"])
    elif part.endswith("_boot"):
        evidence.append("boot_closeup_side")
    elif part.endswith("_shin"):
        evidence.append("boot_closeup_side")
    return evidence


def _review_status(
    findings: list[dict[str, Any]],
    hold_items: list[dict[str, Any]],
    missing_p1_items: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for finding in findings:
        status_counts[finding["finding_type"]] = status_counts.get(finding["finding_type"], 0) + 1
        priority_counts[finding["priority"]] = priority_counts.get(finding["priority"], 0) + 1
    return {
        "decision": "technical_file_pass_fidelity_hold",
        "file_pass_but_fidelity_hold_count": len(hold_items),
        "missing_p1_count": len(missing_p1_items),
        "per_part_finding_count": len(findings),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "runtime_public_activation_allowed": False,
        "hold_label": "fidelity_hold",
    }


def _modeler_fix_message_outline(
    *,
    hold_items: list[dict[str, Any]],
    missing_p1_items: list[dict[str, Any]],
    line_holds: list[dict[str, Any]],
    defects: list[str],
    reorder_memo: list[str],
) -> dict[str, Any]:
    return {
        "title": "30variant tri-view fidelity rework request",
        "opening": (
            f"{len(hold_items)} delivered variants are file-valid but stay fidelity_hold. "
            f"{len(missing_p1_items)} P1 limb rows are separate missing-order work."
        ),
        "line_focus": line_holds,
        "must_fix": defects,
        "send_back_to_modeler": reorder_memo,
        "top_priority_order": [
            "helmet",
            "chest",
            "back",
            "boots",
            "shins",
            "waist",
            "shoulders",
            "P1 limbs in separate order flow",
        ],
        "do_not_claim": [
            "Do not mark these variants as public runtime-ready while fidelity_hold remains.",
            "Do not use catalog fallback as a substitute for per-asset sidecar provenance.",
            "Do not mix the 24 missing P1 limb filesets into the 30variant fidelity pass.",
        ],
    }


def _acceptance_recheck_steps() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "gate": "delivery_manifest",
            "command": (
                "python tools\\validate_modeler_delivery_manifest.py --manifest "
                "docs\\modeler-deliveries\\first-three-lines-2026-05-02.delivery-manifest.json"
            ),
            "pass_condition": "status=pass, asset_count=30, reasons=[]",
        },
        {
            "step": 2,
            "gate": "variant_catalog",
            "command": "python tools\\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots",
            "pass_condition": "catalog validates without warnings or missing variant keys",
        },
        {
            "step": 3,
            "gate": "sidecar_provenance",
            "command": "inspect delivered *.modeler.json sidecars",
            "pass_condition": f"each held variant has top-level {', '.join(SIDECAR_FIELDS)}",
        },
        {
            "step": 4,
            "gate": "tri_view_evidence",
            "command": "review front/side/back/3q and required closeups per line",
            "pass_condition": f"evidence includes {', '.join(REQUIRED_EVIDENCE)} where applicable",
        },
        {
            "step": 5,
            "gate": "runtime_route_proof",
            "command": "run Web smoke, then capture Quest/Replay notes for promoted candidates",
            "pass_condition": "fallback count is 0 and no fidelity_hold item is public runtime selectable",
        },
    ]


def _runtime_release_impact(
    hold_items: list[dict[str, Any]],
    missing_p1_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "public_runtime_allowed": False,
        "runtime_block_label": RUNTIME_BLOCK_LABEL,
        "held_variant_count": len(hold_items),
        "missing_p1_count": len(missing_p1_items),
        "reviewer_only_allowed": True,
        "release_rules": [
            "Canonical/base exhibition runtime may proceed independently if package smoke passes.",
            "The 30 delivered line variants stay reviewer-only until fidelity_pass.",
            "A line-complete claim is blocked until the separate 24-item P1 limb order is accepted.",
            "Quest and Replay proof are required before any public runtime selector mapping.",
        ],
    }


def _finding_sort_key(finding: dict[str, Any]) -> tuple[int, str, str]:
    try:
        part_index = PART_ORDER.index(str(finding.get("part")))
    except ValueError:
        part_index = len(PART_ORDER)
    return part_index, str(finding.get("line_id")), str(finding.get("variant_key"))


def _assert_packet_contract(packet: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_PACKET_KEYS if key not in packet]
    if missing:
        raise ValueError(f"packet missing required top-level key(s): {missing}")


def _json_payload(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2) + "\n"


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _rel(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _write_output(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-doc", default=DEFAULT_AUDIT_DOC, type=Path, help="30variant audit Markdown")
    parser.add_argument("--worklist-doc", default=DEFAULT_WORKLIST_DOC, type=Path, help="review worklist Markdown")
    parser.add_argument("--out", type=Path, help="Write JSON packet to this path")
    parser.add_argument("--report-json", action="store_true", help="Print the JSON packet to stdout")
    args = parser.parse_args(argv)

    packet = export_triview_audit_packet(audit_doc=args.audit_doc, worklist_doc=args.worklist_doc)
    payload = _json_payload(packet)
    if args.out:
        _write_output(args.out, payload)
    if args.report_json or not args.out:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
