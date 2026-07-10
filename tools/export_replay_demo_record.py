"""Export a minimal ReplayRecord from a runtime package snapshot.

This is a local exhibition-QA bridge for the "Replay preserves the experience"
line. It wraps an existing runtime package snapshot in the draft
ReplayRecord v0.2 envelope, writes it to disk, then immediately validates the
variant placement identity with validate_replay_variant_alignment.py.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPLAY_RECORD_SCHEMA_VERSION = "0.2"
REPLAY_RECORD_CONTRACT_VERSION = "replay-record.v0.2"
EXPORT_REPORT_CONTRACT_VERSION = "replay-demo-record-export.v1"
PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION = "replay-public-artifact-policy.v1"


def export_replay_demo_record(
    runtime_snapshot: str | Path | dict[str, Any],
    *,
    out: str | Path,
    code: str | None = None,
    height_cm: float | None = None,
    experience_label: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    payload, source_path = _load_payload(runtime_snapshot)
    runtime_package = _runtime_package_from_payload(payload)
    if not isinstance(runtime_package, dict):
        record = _error_record(
            source_path=source_path,
            code=code,
            experience_label=experience_label,
            created_at=created_at,
            reason="input must be a runtime package object or contain runtime_package",
        )
    else:
        record = build_replay_demo_record(
            runtime_package,
            source_payload=payload,
            source_path=source_path,
            code=code,
            height_cm=height_cm,
            experience_label=experience_label,
            created_at=created_at,
        )

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    alignment_report = _validate_alignment(record)
    return {
        "contract_version": EXPORT_REPORT_CONTRACT_VERSION,
        "ok": bool(alignment_report.get("ok")),
        "status": "pass" if alignment_report.get("ok") else "fail",
        "out": out_path.as_posix(),
        "runtime_snapshot_path": source_path,
        "replay_id": record.get("replay_id"),
        "recall_code": record.get("recall_code"),
        "created_at": record.get("metadata", {}).get("created_at"),
        "selected_variant_count": len(record.get("selected_variants", {})),
        "variant_alignment_report": alignment_report,
    }


def build_replay_demo_record(
    runtime_package: dict[str, Any],
    *,
    source_payload: dict[str, Any] | None = None,
    source_path: str | None = None,
    code: str | None = None,
    height_cm: float | None = None,
    experience_label: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    created = created_at or _now_iso()
    selected_variants = _selected_variant_keys(runtime_package)
    placement_snapshot = _dict(runtime_package.get("variant_placement_snapshot"))
    height = _height_metadata(runtime_package, override_cm=height_cm)
    recall_code = _first_string(code, _dict(source_payload or {}).get("recall_code"), runtime_package.get("recall_code"), "DEMO")
    suit_id = _first_string(
        runtime_package.get("suit_id"),
        _dict(runtime_package.get("suitspec")).get("suit_id"),
        _dict(source_payload or {}).get("suit_id"),
        "VDA-DEMO-REPLAY-00-0000",
    )
    manifest_id = _first_string(runtime_package.get("manifest_id"), _dict(source_payload or {}).get("manifest_id"), "MNF-DEMO-REPLAY")
    label = _first_string(experience_label, _dict(source_payload or {}).get("display_name"), "Replay demo export")
    replay_id = _replay_id(created, recall_code, runtime_package)
    runtime_source_ref = _portable_source_ref(source_path)

    return {
        "schema_version": REPLAY_RECORD_SCHEMA_VERSION,
        "contract_version": REPLAY_RECORD_CONTRACT_VERSION,
        "replay_id": replay_id,
        "suit_id": suit_id,
        "recall_code": recall_code,
        "manifest_id": manifest_id,
        "created_at": created,
        "experience": {
            "label": label,
            "source": "runtime_package_snapshot",
            "exporter": "tools/export_replay_demo_record.py",
        },
        "wearer": height,
        "selected_variants": selected_variants,
        "placement_snapshot": placement_snapshot,
        "runtime_package": runtime_package,
        "transform_trial": {
            "session_id": f"S-REPLAY-DEMO-{_short_hash(replay_id)}",
            "state": "SNAPSHOT_EXPORTED",
            "started_at": created,
            "completed_at": created,
            "event_count": 1,
            "tracking_source": "runtime_package_snapshot",
        },
        "playback": {
            "view_mode": "observer",
            "source": "runtime_package_snapshot",
            "motion_source": "static_diagnostic",
            "duration_sec": 0.0,
        },
        "source_events": [
            {
                "event_id": f"EVT-REPLAY-DEMO-{_short_hash(replay_id + created)}",
                "sequence": 0,
                "event_type": "RUNTIME_PACKAGE_SNAPSHOT_EXPORTED",
                "occurred_at": created,
                "state_after": "SNAPSHOT_EXPORTED",
                "payload_summary": {
                    "selected_variant_count": len(selected_variants),
                    "variant_placement_snapshot_contract": placement_snapshot.get("contract_version"),
                    "runtime_snapshot_ref": runtime_source_ref,
                },
            }
        ],
        "presentation": {
            "default_locale": "ja-JP",
            "supported_locales": ["ja-JP"],
            "event_labels": [
                {
                    "event_type": "RUNTIME_PACKAGE_SNAPSHOT_EXPORTED",
                    "locale": "ja-JP",
                    "label": "Replay saved",
                    "short_label": "Replay",
                }
            ],
            "view_mode_labels": [
                {"view_mode": "observer", "locale": "ja-JP", "label": "Replay QA", "short_label": "Replay"}
            ],
            "display_policy": {
                "ui_uses_labels_not_raw_event_types": True,
                "hide_private_ids_on_public_display": True,
                "fallback_locale": "ja-JP",
            },
        },
        "operation": {
            "mode": "local_demo",
            "storage_backend": "local_json",
            "write_path": "runtime_snapshot_to_minimal_replay_record",
            "runtime_resolver": {
                "artifact_uri_schemes": ["relative"],
                "requires_runtime_package_snapshot": True,
                "fallback_allowed": False,
            },
        },
        "portability": {
            "uri_policy": "bundle_relative_or_local_demo_file",
            "required_artifact_keys": ["runtime_package"],
            "move_validation": {
                "portable_between_pcs": False,
                "absolute_local_paths_allowed": False,
                "validation_strategy": "validate_replay_variant_alignment_report",
            },
        },
        "validity": {
            "validation_status": "pending_variant_alignment",
            "integrity_policy": {
                "runtime_package_snapshot_required": True,
                "variant_alignment_validation_required": True,
            },
        },
        "public_artifact_policy": _public_artifact_policy(),
        "artifacts": {
            "runtime_package": {
                "uri": runtime_source_ref,
                "media_type": "application/json",
                "schema_version": str(runtime_package.get("contract_version") or ""),
                "storage_backend": "local_demo",
                "portable": not _looks_absolute_or_drive_path(runtime_source_ref),
                "retention_role": "required_runtime",
            }
        },
        "metadata": {
            "created_at": created,
            "generator": "tools/export_replay_demo_record.py",
            "runtime_snapshot_path": runtime_source_ref,
            "height_source": height["source"],
            "notes": "Minimal local ReplayRecord for exhibition QA; generated from a runtime package snapshot.",
        },
    }


def _error_record(
    *,
    source_path: str | None,
    code: str | None,
    experience_label: str | None,
    created_at: str | None,
    reason: str,
) -> dict[str, Any]:
    created = created_at or _now_iso()
    return {
        "schema_version": REPLAY_RECORD_SCHEMA_VERSION,
        "contract_version": REPLAY_RECORD_CONTRACT_VERSION,
        "replay_id": _replay_id(created, code or "ERROR", {"error": reason}),
        "recall_code": code or "DEMO",
        "created_at": created,
        "experience": {
            "label": experience_label or "Replay demo export",
            "source": "runtime_package_snapshot",
            "exporter": "tools/export_replay_demo_record.py",
        },
        "runtime_package": {},
        "selected_variants": {},
        "placement_snapshot": {},
        "public_artifact_policy": _public_artifact_policy(),
        "source_events": [],
        "metadata": {
            "created_at": created,
            "generator": "tools/export_replay_demo_record.py",
            "runtime_snapshot_path": _portable_source_ref(source_path),
            "error": reason,
        },
    }


def _load_payload(snapshot: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(snapshot, dict):
        return snapshot, None
    path = Path(snapshot)
    return json.loads(path.read_text(encoding="utf-8-sig")), path.as_posix()


def _runtime_package_from_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    runtime_package = payload.get("runtime_package")
    if isinstance(runtime_package, dict):
        return runtime_package
    if isinstance(payload.get("render_placements"), dict) or isinstance(payload.get("variant_placement_snapshot"), dict):
        return payload
    return None


def _selected_variant_keys(runtime_package: dict[str, Any]) -> dict[str, str]:
    selected: dict[str, str] = {}
    selected.update({str(part): str(key) for part, key in _dict(runtime_package.get("selected_variant_keys")).items() if key})
    overlay = _dict(_dict(runtime_package.get("visual_layers")).get("armor_overlay"))
    selected.update({str(part): str(key) for part, key in _dict(overlay.get("selected_variant_keys")).items() if key})
    snapshot = _dict(runtime_package.get("variant_placement_snapshot"))
    selected.update({str(part): str(key) for part, key in _dict(snapshot.get("selected_variant_keys")).items() if key})
    for part, placement in _dict(runtime_package.get("render_placements")).items():
        if isinstance(placement, dict) and placement.get("selected_variant_key"):
            selected.setdefault(str(part), str(placement["selected_variant_key"]))
    return dict(sorted(selected.items()))


def _height_metadata(runtime_package: dict[str, Any], *, override_cm: float | None) -> dict[str, Any]:
    if override_cm is not None:
        return {"height_cm": float(override_cm), "source": "cli_arg.height_cm"}
    body_profile = _dict(_dict(runtime_package.get("suitspec")).get("body_profile"))
    for key, source in (
        ("height_cm", "runtime_package.suitspec.body_profile.height_cm"),
        ("declared_height_cm", "runtime_package.suitspec.body_profile.declared_height_cm"),
    ):
        if _is_number(body_profile.get(key)):
            return {"height_cm": float(body_profile[key]), "source": source}
    body_fit = _dict(runtime_package.get("body_fit_contract"))
    if _is_number(body_fit.get("height_cm")):
        return {"height_cm": float(body_fit["height_cm"]), "source": "runtime_package.body_fit_contract.height_cm"}
    return {"height_cm": None, "source": "missing"}


def _validate_alignment(record: dict[str, Any]) -> dict[str, Any]:
    validator = _load_alignment_validator()
    return validator.validate_replay_variant_alignment(record)


def _public_artifact_policy() -> dict[str, Any]:
    return {
        "contract_version": PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION,
        "role": "snapshot_consumer",
        "playcanvas_writeback_allowed": False,
        "local_path_allowed": False,
        "external_publication_requires_preflight": True,
        "external_preflight_tool": "tools/validate_replay_public_artifact.py --mode external",
    }


def _load_alignment_validator():
    module_name = "validate_replay_variant_alignment"
    if module_name in sys.modules:
        return sys.modules[module_name]
    tool_path = Path(__file__).with_name("validate_replay_variant_alignment.py")
    spec = importlib.util.spec_from_file_location(module_name, tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_replay_variant_alignment.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_string(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _replay_id(created_at: str, code: str, runtime_package: dict[str, Any]) -> str:
    stamp = created_at[:10].replace("-", "")
    suffix = _short_hash(json.dumps(runtime_package, sort_keys=True, ensure_ascii=False) + code)
    clean_code = "".join(char for char in str(code or "DEMO").upper() if char.isalnum())[:8] or "DEMO"
    return f"RPL-{stamp}-{clean_code}-{suffix}"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8].upper()


def _portable_source_ref(path: str | None) -> str:
    if not path:
        return "runtime-package.json"
    source = Path(path)
    try:
        return source.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (OSError, ValueError):
        return source.name or "runtime-package.json"


def _looks_absolute_or_drive_path(value: str) -> bool:
    text = str(value or "").replace("\\", "/")
    return text.startswith("/") or (len(text) >= 3 and text[1] == ":" and text[2] == "/")


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result['out']}")
    print(f"replay_id: {result.get('replay_id')}")
    print(f"recall_code: {result.get('recall_code')}")
    print(f"selected variants: {result.get('selected_variant_count')}")
    alignment = result.get("variant_alignment_report", {})
    print(f"variant alignment: {alignment.get('status', 'unknown')}")
    for reason in alignment.get("reasons", []):
        print(f"  fail  {reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_snapshot", type=Path, help="Runtime package snapshot JSON, or a JSON object containing runtime_package")
    parser.add_argument("--out", type=Path, required=True, help="Output ReplayRecord JSON path")
    parser.add_argument("--code", help="Four-character Quest recall code or demo code to store")
    parser.add_argument("--height-cm", type=float, help="Wearer height to store in the ReplayRecord")
    parser.add_argument("--experience-label", help="Human-readable label for this preserved experience")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured export report")
    args = parser.parse_args(argv)

    result = export_replay_demo_record(
        args.runtime_snapshot,
        out=args.out,
        code=args.code,
        height_cm=args.height_cm,
        experience_label=args.experience_label,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
