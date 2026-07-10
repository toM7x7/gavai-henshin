"""Validate a PlayCanvas runtime-package snapshot import contract.

PlayCanvas is an adapter that consumes exported runtime package snapshots. This
validator rejects snapshots that make PlayCanvas a write-back or placement
authority, or that leak machine-local paths into public artifact refs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "playcanvas-snapshot-consumer.v1"
RUNTIME_PLACEMENT_CONTRACT = "runtime-render-placement.v1"
SURFACE_ANCHOR_CONTRACT = "runtime-body-surface-anchor.v1"
LOCAL_POSIX_PREFIXES = (
    "/tmp/",
    "/var/folders/",
    "/private/var/",
    "/users/",
    "/home/",
    "/mnt/",
    "/workspace/",
)
LOCAL_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
PLAYCANVAS_WRITE_KEYS = {
    "playcanvas_writeback",
    "playcanvas_write_authority",
    "playcanvas_write_enabled",
    "playcanvas_can_write",
    "playcanvas_authoritative",
    "playcanvas_source_of_truth",
    "playcanvas_owner",
    "playcanvas_mutation_endpoint",
    "playcanvas_save_endpoint",
    "playcanvas_write_endpoint",
}
PLAYCANVAS_DICT_WRITE_KEYS = {
    "write_authority",
    "writeback",
    "write_enabled",
    "can_write",
    "authoritative",
    "source_of_truth",
    "owns_placement",
    "owner",
    "mutation_endpoint",
    "save_endpoint",
    "write_endpoint",
}
FALSEY_PLAYCANVAS_WRITE_VALUES = {
    "disabled",
    "false",
    "forbidden",
    "no",
    "none",
    "read-only",
    "read_only",
    "readonly",
    "snapshot_consumer",
}


def validate_playcanvas_snapshot(snapshot: str | Path | dict[str, Any]) -> dict[str, Any]:
    payload, snapshot_path = _load_payload(snapshot)
    runtime_package = _runtime_package_from_payload(payload)
    reasons: list[str] = []
    warnings: list[str] = []
    artifact_refs: list[dict[str, str]] = []

    if not isinstance(runtime_package, dict):
        reasons.append("snapshot must be a runtime package object or contain runtime_package")
        runtime_package = {}

    render_contract = runtime_package.get("render_contract") if isinstance(runtime_package.get("render_contract"), dict) else {}
    if render_contract.get("render_placement_contract") != RUNTIME_PLACEMENT_CONTRACT:
        reasons.append("render_contract.render_placement_contract must be runtime-render-placement.v1")

    placements = runtime_package.get("render_placements") if isinstance(runtime_package.get("render_placements"), dict) else {}
    if not placements:
        reasons.append("runtime_package.render_placements must be a non-empty object")
    else:
        _validate_render_placements(
            placements,
            runtime_package=runtime_package,
            reasons=reasons,
            artifact_refs=artifact_refs,
        )

    declared_parts = render_contract.get("render_placement_parts")
    if isinstance(declared_parts, list) and placements:
        actual_parts = sorted(str(part) for part in placements)
        declared = sorted(str(part) for part in declared_parts)
        if declared != actual_parts:
            reasons.append(
                "render_contract.render_placement_parts must match runtime_package.render_placements keys"
            )

    local_path_leaks = _local_path_leaks(payload)
    reasons.extend(f"machine-local path leak at {leak['path']}: {leak['value']}" for leak in local_path_leaks)
    playcanvas_authority = _playcanvas_write_authority(payload)
    reasons.extend(playcanvas_authority["reasons"])

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not reasons,
        "status": "fail" if reasons else "pass",
        "snapshot_path": snapshot_path,
        "runtime_package_present": bool(runtime_package),
        "render_placement_count": len(placements),
        "selected_parts": sorted(str(part) for part in placements),
        "artifact_ref_count": len(artifact_refs),
        "artifact_refs": artifact_refs,
        "local_path_leak_count": len(local_path_leaks),
        "local_path_leaks": local_path_leaks,
        "playcanvas": {
            "mode": "snapshot_consumer",
            "write_authority": False,
            "write_authority_violation_count": len(playcanvas_authority["reasons"]),
        },
        "reasons": reasons,
        "warnings": warnings,
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
    if isinstance(payload.get("render_placements"), dict) or isinstance(payload.get("render_contract"), dict):
        return payload
    return None


def _validate_render_placements(
    placements: dict[str, Any],
    *,
    runtime_package: dict[str, Any],
    reasons: list[str],
    artifact_refs: list[dict[str, str]],
) -> None:
    selected_keys = _selected_variant_keys(runtime_package)
    overlay_assets = _overlay_assets(runtime_package)
    for part, placement in sorted(placements.items()):
        path = f"runtime_package.render_placements.{part}"
        if not isinstance(placement, dict):
            reasons.append(f"{path} must be an object")
            continue
        placement_part = str(placement.get("part") or part)
        if placement_part != str(part):
            reasons.append(f"{path}.part must match its render_placements key")
        if placement.get("contract_version") != RUNTIME_PLACEMENT_CONTRACT:
            reasons.append(f"{path}.contract_version must be {RUNTIME_PLACEMENT_CONTRACT}")

        variant_key = str(placement.get("selected_variant_key") or "").strip()
        if not variant_key:
            reasons.append(f"{path}.selected_variant_key is required")
        elif ":" not in variant_key or variant_key.split(":", 1)[0] != str(part):
            reasons.append(f"{path}.selected_variant_key must use '<part>:<variant>' identity")

        if selected_keys.get(str(part)) and selected_keys[str(part)] != variant_key:
            reasons.append(f"{path}.selected_variant_key must match visual_layers selected_variant_keys")
        asset = overlay_assets.get(str(part))
        if isinstance(asset, dict) and asset.get("selected_variant_key") and asset["selected_variant_key"] != variant_key:
            reasons.append(f"{path}.selected_variant_key must match visual_layers armor_overlay asset identity")

        asset_ref = str(placement.get("asset_ref") or "").strip()
        if not asset_ref:
            reasons.append(f"{path}.asset_ref is required")
        else:
            _record_artifact_ref(path, "asset_ref", asset_ref, reasons, artifact_refs)
            if isinstance(asset, dict) and asset.get("asset_ref") and str(asset["asset_ref"]) != asset_ref:
                reasons.append(f"{path}.asset_ref must match visual_layers armor_overlay asset_ref")

        for key in ("surface_offset_clamped_m", "quest_surface_offset_clamped_m"):
            if not _vector3(placement.get(key)):
                reasons.append(f"{path}.{key} must be a three-number array")

        surface_anchor = placement.get("surface_anchor") if isinstance(placement.get("surface_anchor"), dict) else {}
        if surface_anchor.get("contract_version") != SURFACE_ANCHOR_CONTRACT:
            reasons.append(f"{path}.surface_anchor.contract_version must be {SURFACE_ANCHOR_CONTRACT}")
        if surface_anchor.get("offset_clamped_m") != placement.get("surface_offset_clamped_m"):
            reasons.append(f"{path}.surface_anchor.offset_clamped_m must match surface_offset_clamped_m")
        if surface_anchor.get("quest_rig_offset_clamped_m") != placement.get("quest_surface_offset_clamped_m"):
            reasons.append(
                f"{path}.surface_anchor.quest_rig_offset_clamped_m must match quest_surface_offset_clamped_m"
            )


def _selected_variant_keys(runtime_package: dict[str, Any]) -> dict[str, str]:
    visual_layers = runtime_package.get("visual_layers") if isinstance(runtime_package.get("visual_layers"), dict) else {}
    overlay = visual_layers.get("armor_overlay") if isinstance(visual_layers.get("armor_overlay"), dict) else {}
    selected = overlay.get("selected_variant_keys") if isinstance(overlay.get("selected_variant_keys"), dict) else {}
    return {str(part): str(key) for part, key in selected.items()}


def _overlay_assets(runtime_package: dict[str, Any]) -> dict[str, Any]:
    visual_layers = runtime_package.get("visual_layers") if isinstance(runtime_package.get("visual_layers"), dict) else {}
    overlay = visual_layers.get("armor_overlay") if isinstance(visual_layers.get("armor_overlay"), dict) else {}
    assets = overlay.get("assets") if isinstance(overlay.get("assets"), dict) else {}
    return {str(part): asset for part, asset in assets.items()}


def _record_artifact_ref(
    path: str,
    key: str,
    value: str,
    reasons: list[str],
    artifact_refs: list[dict[str, str]],
) -> None:
    if _is_local_path(value):
        reasons.append(f"{path}.{key} must be a portable artifact ref, not a machine-local path")
    elif value.startswith("../") or "/../" in value.replace("\\", "/"):
        reasons.append(f"{path}.{key} must not traverse outside the snapshot artifact root")
    artifact_refs.append({"path": f"{path}.{key}", "ref": value})


def _local_path_leaks(payload: Any) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if str(key) == "local_path":
                    leaks.append({"path": child_path, "value": str(child)})
                walk(child, child_path)
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(value, str) and _is_local_path(value):
            leaks.append({"path": path, "value": value})

    walk(payload, "$")
    return leaks


def _is_local_path(value: str) -> bool:
    text = str(value or "").strip().replace("\\", "/")
    lower = text.lower()
    if not text:
        return False
    if lower.startswith("file://") or LOCAL_PATH_RE.match(text):
        return True
    if lower.startswith("//"):
        return True
    if URL_RE.match(text) and not lower.startswith("file://"):
        return False
    return any(lower.startswith(prefix) for prefix in LOCAL_POSIX_PREFIXES)


def _playcanvas_write_authority(payload: Any) -> dict[str, list[str]]:
    reasons: list[str] = []

    def truthy(value: Any) -> bool:
        if value in (None, False, "", [], {}):
            return False
        if isinstance(value, str) and value.strip().lower() in FALSEY_PLAYCANVAS_WRITE_VALUES:
            return False
        return True

    def walk(value: Any, path: str, inside_playcanvas: bool = False) -> None:
        if isinstance(value, dict):
            current_inside = inside_playcanvas or path.lower().endswith(".playcanvas")
            role = str(value.get("role") or value.get("mode") or "").strip().lower()
            if current_inside and role and role not in {
                "snapshot_consumer",
                "read_only_snapshot_consumer",
                "consumer",
                "adapter",
                "preview_adapter",
                "visual_qa_adapter",
            }:
                reasons.append(f"{path}.role must keep PlayCanvas in snapshot-consumer/read-only adapter mode")
            for key, child in value.items():
                key_text = str(key)
                key_lower = key_text.lower()
                child_path = f"{path}.{key_text}"
                if key_lower in PLAYCANVAS_WRITE_KEYS and truthy(child):
                    reasons.append(f"{child_path} grants PlayCanvas write or authority semantics")
                if current_inside and key_lower in PLAYCANVAS_DICT_WRITE_KEYS and truthy(child):
                    reasons.append(f"{child_path} grants PlayCanvas write-back authority")
                walk(child, child_path, current_inside or key_lower == "playcanvas")
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", inside_playcanvas)

    walk(payload, "$")
    return {"reasons": reasons}


def _vector3(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result.get('snapshot_path') or '<payload>'}")
    print(f"validated {result['render_placement_count']} render placement(s)")
    print(f"artifact refs: {result['artifact_ref_count']}")
    print(f"local path leaks: {result['local_path_leak_count']}")
    for reason in result["reasons"]:
        print(f"  fail  {reason}")
    for warning in result["warnings"]:
        print(f"  warn  {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Path to runtime package snapshot JSON")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    args = parser.parse_args(argv)

    result = validate_playcanvas_snapshot(args.snapshot)
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
