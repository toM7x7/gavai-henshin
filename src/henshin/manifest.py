"""SuitManifest projection utilities.

SuitSpec remains the authoring contract. SuitManifest is the runtime package
contract consumed by cloud, Quest, and replay surfaces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _yyyymmdd_from_iso(value: str | None) -> str:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y%m%d")
        except ValueError:
            pass
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def build_manifest_id(suit_id: str, *, date_yyyymmdd: str | None = None, version: int = 1) -> str:
    """Build a stable-looking manifest id from suit id and version."""

    yyyymmdd = date_yyyymmdd or datetime.now(timezone.utc).strftime("%Y%m%d")
    digest = sha1(f"{suit_id}:{version}".encode("utf-8")).hexdigest().upper()[:4]
    return f"MNF-{yyyymmdd}-{digest}"


def _catalog_lookup(part_catalog: dict[str, Any] | None) -> dict[str, str]:
    if not part_catalog:
        return {}
    lookup: dict[str, str] = {}
    for part in part_catalog.get("parts", []):
        asset = part.get("asset", {})
        uri = asset.get("uri")
        part_id = part.get("part_id")
        module = part.get("module")
        if isinstance(uri, str) and isinstance(part_id, str):
            lookup[uri] = part_id
        if isinstance(module, str) and isinstance(part_id, str):
            lookup[module] = part_id
    return lookup


def project_suitspec_to_manifest(
    suitspec: dict[str, Any],
    *,
    part_catalog: dict[str, Any] | None = None,
    manifest_id: str | None = None,
    status: str = "DRAFT",
    projection_version: str = "0.1",
) -> dict[str, Any]:
    """Project a SuitSpec v0.2 payload into SuitManifest v0.1."""

    if suitspec.get("schema_version") != "0.2":
        raise ValueError("SuitSpec.schema_version must be '0.2'")
    suit_id = suitspec.get("suit_id")
    if not isinstance(suit_id, str) or not suit_id:
        raise ValueError("SuitSpec.suit_id is required")

    created_at = suitspec.get("metadata", {}).get("created_at")
    mid = manifest_id or build_manifest_id(suit_id, date_yyyymmdd=_yyyymmdd_from_iso(created_at))
    catalog_lookup = _catalog_lookup(part_catalog)

    parts: dict[str, Any] = {}
    for module_name, module in suitspec.get("modules", {}).items():
        if not isinstance(module, dict):
            continue
        part = {
            "enabled": bool(module.get("enabled", False)),
            "asset_ref": module.get("asset_ref", ""),
        }
        for key in ("material_ref", "texture_path", "attachment_slot", "fit", "vrm_anchor"):
            if key in module:
                part[key] = module[key]
        catalog_part_id = catalog_lookup.get(str(module.get("asset_ref", ""))) or catalog_lookup.get(module_name)
        if catalog_part_id:
            part["catalog_part_id"] = catalog_part_id
        parts[module_name] = part

    manifest: dict[str, Any] = {
        "schema_version": "0.1",
        "manifest_id": mid,
        "suit_id": suit_id,
        "source": {
            "type": "suitspec_projection",
            "suitspec_schema_version": "0.2",
            "suitspec_id": suit_id,
            "projection_version": projection_version,
        },
        "status": status,
        "runtime_targets": ["web_preview", "quest", "replay"],
        "parts": parts,
        "palette": suitspec.get("palette", {}),
        "effects": suitspec.get("effects", {}),
        "metadata": {
            "created_at": created_at or _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        },
    }

    for key in ("approval_id", "morphotype_id", "blueprint", "emblem", "text"):
        if key in suitspec:
            manifest[key] = suitspec[key]

    return manifest
