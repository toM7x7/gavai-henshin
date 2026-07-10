"""Audit local armor-part modeler delivery assets one part at a time.

The audit is intentionally read-only. It inventories canonical and variant
GLB/modeler/source/preview companions, extracts sidecar placement and bbox
metadata, and joins each asset to variant_catalog.json metadata for hand review.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS_ROOT = Path("viewer/assets/armor-parts")
DEFAULT_CATALOG = DEFAULT_ASSETS_ROOT / "variant_catalog.json"
CANONICAL_PARTS = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
)
LINEAGE_METADATA_FIELDS = (
    "source_concept_ids",
    "line_id",
    "design_intent",
)
FIDELITY_METADATA_FIELDS = (
    "fidelity_notes",
)
TOP_LEVEL_METADATA_FIELDS = LINEAGE_METADATA_FIELDS + FIDELITY_METADATA_FIELDS
GLB_MAGIC = b"glTF"
GLB_JSON_CHUNK_TYPE = 0x4E4F534A


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - audit should report malformed files.
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "JSON root is not an object"
    return payload, None


def _file_record(path: Path, *, parse_json: bool = False) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": _rel(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else None,
    }
    if parse_json and path.is_file():
        payload, error = _read_json(path)
        record["json_ok"] = error is None
        if error:
            record["json_error"] = error
        else:
            record["json_keys"] = sorted(payload or {})
    return record


def _glb_header(path: Path) -> dict[str, Any]:
    record = _file_record(path)
    if not path.is_file():
        return record
    try:
        data = path.read_bytes()
        record["actual_length"] = len(data)
        if len(data) < 20:
            record["valid_header"] = False
            record["header_error"] = "GLB too small for header"
            return record
        magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
        chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
        record.update(
            {
                "magic": magic.decode("ascii", errors="replace"),
                "version": version,
                "declared_length": declared_length,
                "declared_length_matches": declared_length == len(data),
                "first_chunk_length": chunk_length,
                "first_chunk_type": f"0x{chunk_type:08X}",
                "first_chunk_is_json": chunk_type == GLB_JSON_CHUNK_TYPE,
                "valid_header": magic == GLB_MAGIC
                and version == 2
                and declared_length == len(data)
                and chunk_type == GLB_JSON_CHUNK_TYPE
                and chunk_length > 0
                and 20 + chunk_length <= len(data),
            }
        )
    except Exception as exc:  # noqa: BLE001
        record["valid_header"] = False
        record["header_error"] = str(exc)
    return record


def _bbox_size_from_bounds(bounds: Any) -> dict[str, float] | None:
    if not isinstance(bounds, dict):
        return None
    mins = bounds.get("min")
    maxs = bounds.get("max")
    if (
        isinstance(mins, list)
        and isinstance(maxs, list)
        and len(mins) == 3
        and len(maxs) == 3
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in mins + maxs)
    ):
        return {
            "x": float(maxs[0]) - float(mins[0]),
            "y": float(maxs[1]) - float(mins[1]),
            "z": float(maxs[2]) - float(mins[2]),
        }
    return None


def _mesh_summary(path: Path) -> dict[str, Any]:
    record = _file_record(path, parse_json=True)
    if not path.is_file() or not record.get("json_ok"):
        return record
    payload, _ = _read_json(path)
    if payload is None:
        return record
    positions = payload.get("positions")
    indices = payload.get("indices")
    record.update(
        {
            "format": payload.get("format"),
            "part": payload.get("part"),
            "category": payload.get("category"),
            "vertex_count": len(positions) // 3 if isinstance(positions, list) else None,
            "index_count": len(indices) if isinstance(indices, list) else None,
            "triangle_count": len(indices) // 3 if isinstance(indices, list) else None,
            "bounds": payload.get("bounds") if isinstance(payload.get("bounds"), dict) else None,
            "bounds_size_m": _bbox_size_from_bounds(payload.get("bounds")),
        }
    )
    return record


def _bbox3(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        result = {axis: value.get(axis) for axis in ("x", "y", "z") if axis in value}
        return result or None
    return None


def _bbox_within(actual: Any, target: Any) -> dict[str, Any]:
    actual_bbox = _bbox3(actual)
    target_bbox = _bbox3(target)
    if actual_bbox is None or target_bbox is None:
        return {"ok": None, "reason": "bbox_m or target bbox missing"}
    deltas: dict[str, Any] = {}
    ok = True
    for axis in ("x", "y", "z"):
        a = actual_bbox.get(axis)
        t = target_bbox.get(axis)
        axis_ok = isinstance(a, (int, float)) and isinstance(t, (int, float)) and float(a) <= float(t)
        ok = ok and axis_ok
        deltas[axis] = {"actual": a, "target": t, "within": axis_ok}
    return {"ok": ok, "axes": deltas}


def _metadata_presence(sidecar: dict[str, Any] | None) -> dict[str, Any]:
    sidecar = sidecar or {}
    return {
        field: {
            "present": field in sidecar,
            "value": sidecar.get(field),
        }
        for field in TOP_LEVEL_METADATA_FIELDS
    }


def _attachment_info(sidecar: dict[str, Any] | None) -> dict[str, Any]:
    sidecar = sidecar or {}
    vrm = sidecar.get("vrm_attachment") if isinstance(sidecar.get("vrm_attachment"), dict) else {}
    return {
        "attachment_offset_target_m": sidecar.get("attachment_offset_target_m"),
        "vrm_offset_m": vrm.get("offset_m"),
        "primary_bone": vrm.get("primary_bone"),
        "rotation_deg": vrm.get("rotation_deg"),
        "fallback_bones": vrm.get("fallback_bones"),
    }


def _selected_line_info(
    sidecar: dict[str, Any] | None,
    catalog_variant: dict[str, Any] | None,
    module_catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    sidecar = sidecar or {}
    catalog_variant = catalog_variant or {}
    module_catalog = module_catalog or {}
    source_concept_ids = (
        sidecar.get("source_concept_ids")
        or catalog_variant.get("source_concept_ids")
        or catalog_variant.get("source_concepts")
    )
    if not source_concept_ids and catalog_variant.get("source_concept"):
        source_concept_ids = [catalog_variant.get("source_concept")]
    return {
        "line_id": sidecar.get("line_id") or catalog_variant.get("line_id"),
        "source_concept_ids": source_concept_ids,
        "design_intent": sidecar.get("design_intent") or catalog_variant.get("design_intent"),
        "fidelity_notes": sidecar.get("fidelity_notes") or catalog_variant.get("fidelity_notes"),
        "variant_key": sidecar.get("variant_key") or catalog_variant.get("variant_key"),
        "display_name": catalog_variant.get("display_name") or catalog_variant.get("label"),
        "detail_features": catalog_variant.get("detail_features"),
        "base_motif_link": catalog_variant.get("base_motif_link") or module_catalog.get("base_motif_link"),
        "mirror_of": sidecar.get("mirror_of") or catalog_variant.get("mirror_of") or module_catalog.get("mirror_of"),
    }


def _sidecar_summary(path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    record = _file_record(path, parse_json=True)
    payload: dict[str, Any] | None = None
    if path.is_file() and record.get("json_ok"):
        payload, _ = _read_json(path)
        payload = payload or {}
        target_bbox = payload.get("target_envelope_m") or payload.get("target_bbox_m") or payload.get("max_bbox_m")
        record.update(
            {
                "contract_version": payload.get("contract_version"),
                "module": payload.get("module"),
                "parent_module": payload.get("parent_module"),
                "variant_key": payload.get("variant_key"),
                "part_id": payload.get("part_id"),
                "category": payload.get("category"),
                "bbox_m": payload.get("bbox_m"),
                "target_bbox_m": target_bbox,
                "bbox_within_target": _bbox_within(payload.get("bbox_m"), target_bbox),
                "triangle_count": payload.get("triangle_count", payload.get("triangles")),
                "material_zones": payload.get("material_zones"),
                "metadata_presence": _metadata_presence(payload),
                "attachment": _attachment_info(payload),
            }
        )
    return record, payload


def _catalog_variant_by_key(module_catalog: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    variants = module_catalog.get("variants") if isinstance(module_catalog, dict) else None
    if not isinstance(variants, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in variants:
        if not isinstance(item, dict):
            continue
        variant_key = item.get("variant_key")
        if isinstance(variant_key, str) and ":" in variant_key:
            result[variant_key.split(":", 1)[1]] = item
    return result


def _asset_status(
    files: dict[str, dict[str, Any]],
    sidecar: dict[str, Any],
    *,
    selected_line_info: dict[str, Any] | None = None,
) -> str:
    required_missing = [
        label
        for label, record in files.items()
        if label in {"glb", "modeler_sidecar", "source_blend", "preview_mesh"} and not record.get("exists")
    ]
    if required_missing:
        return "missing"
    if files["glb"].get("valid_header") is False or sidecar.get("json_ok") is False:
        return "invalid"
    selected_line_info = selected_line_info or {}
    missing_metadata = []
    for field, item in sidecar.get("metadata_presence", {}).items():
        if isinstance(item, dict) and item.get("present"):
            continue
        if selected_line_info.get(field):
            continue
        missing_metadata.append(field)
    if any(field in missing_metadata for field in LINEAGE_METADATA_FIELDS):
        return "metadata_hold"
    if any(field in missing_metadata for field in FIDELITY_METADATA_FIELDS):
        return "fidelity_hold"
    return "pass"


def _audit_asset(
    *,
    kind: str,
    module: str,
    asset_key: str,
    root: Path,
    module_catalog: dict[str, Any] | None,
    catalog_variant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if kind == "canonical":
        asset_dir = root / module
        stem = module
    else:
        asset_dir = root / module / "variants" / asset_key
        stem = f"{module}__{asset_key}"
    glb = asset_dir / f"{stem}.glb"
    sidecar_path = asset_dir / f"{stem}.modeler.json"
    source = asset_dir / "source" / f"{stem}.blend"
    preview = asset_dir / "preview" / f"{stem}.mesh.json"
    sidecar_record, sidecar_payload = _sidecar_summary(sidecar_path)
    selected_line_info = _selected_line_info(sidecar_payload, catalog_variant, module_catalog)
    files = {
        "glb": _glb_header(glb),
        "modeler_sidecar": sidecar_record,
        "source_blend": _file_record(source),
        "preview_mesh": _mesh_summary(preview),
    }
    return {
        "kind": kind,
        "module": module,
        "asset_key": asset_key,
        "asset_dir": _rel(asset_dir),
        "status": _asset_status(files, sidecar_record, selected_line_info=selected_line_info),
        "files": files,
        "variant_metadata": catalog_variant,
        "selected_line_info": selected_line_info,
    }


def _variant_asset_keys(module_root: Path, catalog_by_key: dict[str, dict[str, Any]]) -> list[str]:
    keys = set(catalog_by_key)
    variants_root = module_root / "variants"
    if variants_root.is_dir():
        keys.update(path.name for path in variants_root.iterdir() if path.is_dir())
    return sorted(keys)


def _load_catalog(path: Path) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if not path.is_file():
        warnings.append(f"catalog missing: {_rel(path)}")
        return {}, warnings
    payload, error = _read_json(path)
    if error:
        warnings.append(f"catalog unreadable: {_rel(path)}: {error}")
        return {}, warnings
    return payload or {}, warnings


def audit_parts(
    parts: list[str] | None = None,
    *,
    assets_root: str | Path = DEFAULT_ASSETS_ROOT,
    catalog_path: str | Path = DEFAULT_CATALOG,
) -> dict[str, Any]:
    root = _repo_path(assets_root)
    catalog_file = _repo_path(catalog_path)
    catalog, warnings = _load_catalog(catalog_file)
    modules = catalog.get("modules", catalog.get("parts")) if isinstance(catalog, dict) else {}
    if not isinstance(modules, dict):
        modules = {}
        warnings.append("catalog modules object missing")

    selected_parts = parts or list(CANONICAL_PARTS)
    unknown_parts = [part for part in selected_parts if part not in CANONICAL_PARTS]
    part_reports = []
    for module in selected_parts:
        if module in unknown_parts:
            continue
        module_root = root / module
        module_catalog = modules.get(module) if isinstance(modules.get(module), dict) else {}
        catalog_by_key = _catalog_variant_by_key(module_catalog)
        assets = [
            _audit_asset(
                kind="canonical",
                module=module,
                asset_key="canonical",
                root=root,
                module_catalog=module_catalog,
            )
        ]
        for asset_key in _variant_asset_keys(module_root, catalog_by_key):
            assets.append(
                _audit_asset(
                    kind="variant",
                    module=module,
                    asset_key=asset_key,
                    root=root,
                    module_catalog=module_catalog,
                    catalog_variant=catalog_by_key.get(asset_key),
                )
            )
        part_reports.append(
            {
                "part": module,
                "part_family": module_catalog.get("part_family"),
                "base_motif_link": module_catalog.get("base_motif_link"),
                "mirror_of": module_catalog.get("mirror_of"),
                "topping_slots": module_catalog.get("topping_slots", []),
                "asset_count": len(assets),
                "assets": assets,
                "status_counts": _status_counts(assets),
            }
        )

    status_counts: dict[str, int] = {}
    for part in part_reports:
        for status, count in part["status_counts"].items():
            status_counts[status] = status_counts.get(status, 0) + count
    return {
        "contract_version": "modeler-part-delivery-audit.v1",
        "audit_date": date.today().isoformat(),
        "assets_root": _rel(root),
        "catalog_path": _rel(catalog_file),
        "parts_requested": selected_parts,
        "unknown_parts": unknown_parts,
        "warnings": warnings,
        "part_count": len(part_reports),
        "asset_count": sum(part["asset_count"] for part in part_reports),
        "status_counts": status_counts,
        "parts": part_reports,
    }


def _status_counts(assets: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for asset in assets:
        status = str(asset.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _fmt_bbox(value: Any) -> str:
    bbox = _bbox3(value)
    if bbox is None:
        return "-"
    return "/".join(str(bbox.get(axis, "-")) for axis in ("x", "y", "z"))


def _present_list(sidecar: dict[str, Any]) -> str:
    presence = sidecar.get("metadata_presence")
    if not isinstance(presence, dict):
        return "-"
    present = [field for field, item in presence.items() if isinstance(item, dict) and item.get("present")]
    missing = [field for field, item in presence.items() if isinstance(item, dict) and not item.get("present")]
    return f"present: {', '.join(present) or '-'}; missing: {', '.join(missing) or '-'}"


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Modeler Part Delivery Audit - 2026-05-03",
        "",
        f"- Audit date: {result['audit_date']}",
        f"- Assets root: `{result['assets_root']}`",
        f"- Catalog: `{result['catalog_path']}`",
        f"- Parts audited: {result['part_count']}",
        f"- Canonical/variant assets audited: {result['asset_count']}",
        f"- Status counts: `{json.dumps(result['status_counts'], sort_keys=True)}`",
        "",
        "## Method",
        "",
        "Generated by `python tools/audit_modeler_part_delivery.py --format markdown --output docs/modeler-part-delivery-audit-2026-05-03.md`.",
        "The script is read-only and joins local filesystem companions with `variant_catalog.json` metadata.",
        "",
    ]
    if result.get("warnings"):
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"])
        lines.append("")
    if result.get("unknown_parts"):
        lines.extend(["## Unknown Parts", ""])
        lines.extend(f"- {part}" for part in result["unknown_parts"])
        lines.append("")

    lines.extend(["## Summary By Part", ""])
    lines.append("| Part | Assets | Pass | Fidelity hold | Metadata hold | Missing | Invalid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for part in result["parts"]:
        counts = part["status_counts"]
        lines.append(
            f"| `{part['part']}` | {part['asset_count']} | {counts.get('pass', 0)} | "
            f"{counts.get('fidelity_hold', 0)} | {counts.get('metadata_hold', 0)} | "
            f"{counts.get('missing', 0)} | {counts.get('invalid', 0)} |"
        )
    lines.append("")

    lines.extend(["## Part Detail", ""])
    for part in result["parts"]:
        lines.append(f"### {part['part']}")
        lines.append("")
        lines.append(f"- Part family: `{part.get('part_family') or '-'}`")
        lines.append(f"- Base motif link: `{json.dumps(part.get('base_motif_link'), ensure_ascii=False)}`")
        lines.append(f"- Mirror of: `{part.get('mirror_of') or '-'}`")
        lines.append(f"- Catalog topping slots: {len(part.get('topping_slots') or [])}")
        lines.append("")
        lines.append(
            "| Kind | Asset key | Status | GLB | Sidecar | Blend | Preview | bbox x/y/z | target x/y/z | attachment offset | selected line info |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for asset in part["assets"]:
            files = asset["files"]
            sidecar = files["modeler_sidecar"]
            attachment = sidecar.get("attachment", {}) if isinstance(sidecar.get("attachment"), dict) else {}
            selected = asset.get("selected_line_info") or {}
            selected_summary = (
                f"line={selected.get('line_id') or '-'}; "
                f"concepts={selected.get('source_concept_ids') or '-'}; "
                f"display={selected.get('display_name') or '-'}"
            )
            lines.append(
                f"| {asset['kind']} | `{asset['asset_key']}` | `{asset['status']}` | "
                f"{'ok' if files['glb'].get('exists') and files['glb'].get('valid_header') else 'no'} | "
                f"{'ok' if sidecar.get('exists') and sidecar.get('json_ok') else 'no'} | "
                f"{'ok' if files['source_blend'].get('exists') else 'no'} | "
                f"{'ok' if files['preview_mesh'].get('exists') and files['preview_mesh'].get('json_ok') else 'no'} | "
                f"`{_fmt_bbox(sidecar.get('bbox_m'))}` | `{_fmt_bbox(sidecar.get('target_bbox_m'))}` | "
                f"`{attachment.get('attachment_offset_target_m') or attachment.get('vrm_offset_m') or '-'}` | "
                f"{selected_summary} |"
            )
        lines.append("")
        lines.append("Metadata gate notes:")
        for asset in part["assets"]:
            sidecar = asset["files"]["modeler_sidecar"]
            if asset["status"] == "metadata_hold":
                lines.append(f"- `{asset['kind']}:{asset['asset_key']}`: {_present_list(sidecar)}")
        if not any(asset["status"] == "metadata_hold" for asset in part["assets"]):
            lines.append("- No top-level metadata gaps detected.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", action="append", choices=CANONICAL_PARTS, help="Part to audit; repeatable")
    parser.add_argument("--assets-root", default=DEFAULT_ASSETS_ROOT, type=Path, help="Armor parts root")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, type=Path, help="variant_catalog.json path")
    parser.add_argument("--format", choices=("json", "markdown"), default="json", help="Output format")
    parser.add_argument("--output", type=Path, help="Write output to this path instead of stdout")
    args = parser.parse_args(argv)

    result = audit_parts(args.part, assets_root=args.assets_root, catalog_path=args.catalog)
    text = (
        render_markdown(result)
        if args.format == "markdown"
        else json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    if args.output:
        output_path = _repo_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
    return 1 if result.get("unknown_parts") else 0


if __name__ == "__main__":
    raise SystemExit(main())
