"""Validate Replay/Web/Quest variant placement identity.

The validator accepts either a ReplayRecord-like JSON object containing
``runtime_package`` or a runtime package snapshot directly. It checks the
``variant_placement_snapshot`` relation that binds:

- the selected variant key,
- the active render placement asset_ref used by Quest recall, and
- the Web Forge variant placement table entry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "replay-variant-alignment-report.v1"
SNAPSHOT_CONTRACT_VERSION = "runtime-variant-placement-snapshot.v1"
RUNTIME_PLACEMENT_CONTRACT = "runtime-render-placement.v1"
MATCHED_STATUS = "matched"
NO_VARIANT_STATUS = "not_variant_selected"


def validate_replay_variant_alignment(snapshot: str | Path | dict[str, Any]) -> dict[str, Any]:
    payload, snapshot_path = _load_payload(snapshot)
    runtime_package, source_type = _runtime_package_from_payload(payload)
    reasons: list[str] = []
    warnings: list[str] = []

    if not isinstance(runtime_package, dict):
        reasons.append("payload must be a runtime package object or contain runtime_package")
        runtime_package = {}

    render_placements = _dict(runtime_package.get("render_placements"))
    selected_keys = _selected_variant_keys(runtime_package)
    variant_table = _variant_render_placements(runtime_package)
    selected_variant_records = _dict(runtime_package.get("selected_variant_render_placements"))
    snapshot_record = _dict(runtime_package.get("variant_placement_snapshot"))
    snapshot_parts = _dict(snapshot_record.get("parts"))

    if not snapshot_record:
        reasons.append("runtime_package.variant_placement_snapshot is required")
    elif snapshot_record.get("contract_version") != SNAPSHOT_CONTRACT_VERSION:
        reasons.append(
            f"runtime_package.variant_placement_snapshot.contract_version must be {SNAPSHOT_CONTRACT_VERSION}"
        )

    parts: dict[str, dict[str, Any]] = {}
    part_names = sorted(
        set(render_placements)
        | set(selected_keys)
        | set(snapshot_parts)
        | set(variant_table)
        | set(selected_variant_records)
    )
    for part in part_names:
        part_report = _validate_part(
            part,
            render_placement=_dict(render_placements.get(part)),
            selected_key=selected_keys.get(part, ""),
            variant_records=_dict(variant_table.get(part)),
            selected_variant_record=_dict(selected_variant_records.get(part)),
            snapshot_part=_dict(snapshot_parts.get(part)),
        )
        parts[part] = part_report
        reasons.extend(part_report["reasons"])
        warnings.extend(part_report["warnings"])

    matched_parts = [
        part for part, report in parts.items()
        if report["web_quest_replay_identity"] == MATCHED_STATUS
    ]
    mismatch_parts = [
        part for part, report in parts.items()
        if report["web_quest_replay_identity"] == "mismatch"
    ]
    skipped_parts = [
        part for part, report in parts.items()
        if report["web_quest_replay_identity"] == NO_VARIANT_STATUS
    ]

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not reasons,
        "status": "fail" if reasons else "pass",
        "snapshot_path": snapshot_path,
        "source_type": source_type,
        "runtime_package_present": bool(runtime_package),
        "variant_placement_snapshot_present": bool(snapshot_record),
        "render_placement_count": len(render_placements),
        "selected_variant_count": len(selected_keys),
        "variant_table_part_count": len(variant_table),
        "matched_part_count": len(matched_parts),
        "mismatch_part_count": len(mismatch_parts),
        "not_variant_selected_part_count": len(skipped_parts),
        "matched_parts": matched_parts,
        "mismatch_parts": mismatch_parts,
        "not_variant_selected_parts": skipped_parts,
        "parts": parts,
        "reasons": reasons,
        "warnings": warnings,
    }


def _validate_part(
    part: str,
    *,
    render_placement: dict[str, Any],
    selected_key: str,
    variant_records: dict[str, Any],
    selected_variant_record: dict[str, Any],
    snapshot_part: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    key_candidates = {
        "runtime_package.selected_variant_keys": selected_key,
        "render_placements.selected_variant_key": str(render_placement.get("selected_variant_key") or ""),
        "variant_placement_snapshot.selected_variant_key": str(snapshot_part.get("selected_variant_key") or ""),
        "selected_variant_render_placements.selected_variant_key": str(
            selected_variant_record.get("selected_variant_key") or ""
        ),
    }
    selected_key = _first_string(*key_candidates.values())
    variant_record = _dict(variant_records.get(selected_key)) if selected_key else {}
    if variant_record:
        key_candidates["variant_render_placements.selected_variant_key"] = str(
            variant_record.get("selected_variant_key") or ""
        )

    nonempty_keys = {source: key for source, key in key_candidates.items() if key}
    normalized_keys = set(nonempty_keys.values())
    if len(normalized_keys) > 1:
        reasons.append(f"{part}: selected variant key drift: {nonempty_keys}")
    if selected_key and not _variant_key_matches_part(part, selected_key):
        reasons.append(f"{part}: selected variant key must use '<part>:<variant>' identity")

    render_asset_ref = str(render_placement.get("asset_ref") or "")
    snapshot_render_asset_ref = str(snapshot_part.get("render_asset_ref") or "")
    variant_asset_ref = str(variant_record.get("asset_ref") or "")
    snapshot_variant_asset_ref = str(snapshot_part.get("variant_asset_ref") or "")
    selected_variant_asset_ref = str(selected_variant_record.get("asset_ref") or "")
    asset_candidates = {
        "render_placements.asset_ref": render_asset_ref,
        "variant_placement_snapshot.render_asset_ref": snapshot_render_asset_ref,
        "variant_render_placements.asset_ref": variant_asset_ref,
        "variant_placement_snapshot.variant_asset_ref": snapshot_variant_asset_ref,
        "selected_variant_render_placements.asset_ref": selected_variant_asset_ref,
    }
    nonempty_assets = {source: _portable_ref(value) for source, value in asset_candidates.items() if value}
    if selected_key and not render_asset_ref:
        reasons.append(f"{part}: render placement asset_ref is required for selected variant")
    if selected_key and len(set(nonempty_assets.values())) > 1:
        reasons.append(f"{part}: render placement asset_ref does not match variant table identity: {nonempty_assets}")

    snapshot_status = str(snapshot_part.get("status") or "")
    snapshot_matches = bool(snapshot_part.get("matches_current_render_placement"))
    if selected_key:
        if not variant_record:
            reasons.append(f"{part}: variant_render_placements entry is missing for {selected_key}")
        if snapshot_status != MATCHED_STATUS:
            reasons.append(f"{part}: variant placement snapshot status must be matched for selected variant")
        if not snapshot_matches:
            reasons.append(f"{part}: variant placement snapshot must mark matches_current_render_placement=true")
    else:
        if snapshot_status and snapshot_status != NO_VARIANT_STATUS:
            warnings.append(f"{part}: snapshot status is {snapshot_status} but no selected variant key is present")

    if render_placement and render_placement.get("contract_version") != RUNTIME_PLACEMENT_CONTRACT:
        reasons.append(f"{part}: render placement contract_version must be {RUNTIME_PLACEMENT_CONTRACT}")
    if variant_record and variant_record.get("contract_version") != RUNTIME_PLACEMENT_CONTRACT:
        reasons.append(f"{part}: variant render placement contract_version must be {RUNTIME_PLACEMENT_CONTRACT}")

    identity = MATCHED_STATUS
    if not selected_key:
        identity = NO_VARIANT_STATUS
    elif reasons:
        identity = "mismatch"

    return {
        "part": part,
        "selected_variant_key": selected_key,
        "render_asset_ref": render_asset_ref,
        "variant_asset_ref": variant_asset_ref or snapshot_variant_asset_ref,
        "snapshot_status": snapshot_status,
        "snapshot_matches_current_render_placement": snapshot_matches,
        "render_placement_path": str(snapshot_part.get("render_placement_path") or f"render_placements.{part}"),
        "variant_render_placement_path": str(
            snapshot_part.get("variant_render_placement_path")
            or (f"visual_layers.armor_overlay.variant_render_placements.{part}.{selected_key}" if selected_key else "")
        ),
        "render_placement_present": bool(render_placement),
        "variant_table_entry_present": bool(variant_record),
        "selected_variant_render_placement_present": bool(selected_variant_record),
        "web_quest_replay_identity": identity,
        "checks": {
            "selected_key_consistent": len(normalized_keys) <= 1,
            "asset_ref_consistent": len(set(nonempty_assets.values())) <= 1,
            "snapshot_status_matched": snapshot_status == MATCHED_STATUS if selected_key else snapshot_status == NO_VARIANT_STATUS,
            "snapshot_matches_current_render_placement": snapshot_matches,
        },
        "reasons": reasons,
        "warnings": warnings,
    }


def _load_payload(snapshot: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(snapshot, dict):
        return snapshot, None
    path = Path(snapshot)
    return json.loads(path.read_text(encoding="utf-8-sig")), path.as_posix()


def _runtime_package_from_payload(payload: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(payload, dict):
        return None, "unknown"
    runtime_package = payload.get("runtime_package")
    if isinstance(runtime_package, dict):
        source_type = "replay_record" if any(key in payload for key in ("replay_id", "playback", "source_events")) else "container"
        return runtime_package, source_type
    if (
        isinstance(payload.get("render_placements"), dict)
        or isinstance(payload.get("variant_placement_snapshot"), dict)
        or isinstance(payload.get("visual_layers"), dict)
    ):
        return payload, "runtime_package"
    return None, "unknown"


def _selected_variant_keys(runtime_package: dict[str, Any]) -> dict[str, str]:
    selected: dict[str, str] = {}
    snapshot = _dict(runtime_package.get("variant_placement_snapshot"))
    selected.update({str(part): str(key) for part, key in _dict(snapshot.get("selected_variant_keys")).items() if key})
    selected.update({str(part): str(key) for part, key in _dict(runtime_package.get("selected_variant_keys")).items() if key})

    overlay = _armor_overlay(runtime_package)
    selected.update({str(part): str(key) for part, key in _dict(overlay.get("selected_variant_keys")).items() if key})

    for part, placement in _dict(runtime_package.get("render_placements")).items():
        if isinstance(placement, dict) and placement.get("selected_variant_key"):
            selected.setdefault(str(part), str(placement["selected_variant_key"]))
    return dict(sorted(selected.items()))


def _variant_render_placements(runtime_package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for source in (
        _dict(_armor_overlay(runtime_package).get("variant_render_placements")),
        _dict(runtime_package.get("variant_render_placements")),
    ):
        for part, records in source.items():
            if isinstance(records, dict):
                result.setdefault(str(part), {}).update(records)
    return dict(sorted(result.items()))


def _armor_overlay(runtime_package: dict[str, Any]) -> dict[str, Any]:
    visual_layers = _dict(runtime_package.get("visual_layers"))
    return _dict(visual_layers.get("armor_overlay"))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_string(*values: str) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _variant_key_matches_part(part: str, key: str) -> bool:
    return ":" in key and key.split(":", 1)[0] == part


def _portable_ref(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    return text.split("?", 1)[0].split("#", 1)[0].lstrip("/")


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result.get('snapshot_path') or '<payload>'}")
    print(f"source: {result['source_type']}")
    print(f"selected variants: {result['selected_variant_count']}")
    print(f"matched parts: {result['matched_part_count']}")
    print(f"mismatch parts: {result['mismatch_part_count']}")
    for part, report in result["parts"].items():
        print(
            f"  {part}: {report['web_quest_replay_identity']} "
            f"{report['selected_variant_key'] or '<no variant>'} "
            f"{report['render_asset_ref'] or '<no asset>'}"
        )
    for reason in result["reasons"]:
        print(f"  fail  {reason}")
    for warning in result["warnings"]:
        print(f"  warn  {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Path to ReplayRecord or runtime package snapshot JSON")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    args = parser.parse_args(argv)

    result = validate_replay_variant_alignment(args.snapshot)
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
