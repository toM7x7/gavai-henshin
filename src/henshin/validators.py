"""Lightweight validators for provisional schemas.

No third-party dependency is required in this phase.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .constants import CORE_MODULE_SLOTS, REQUIRED_MORPHOTYPE_FIELDS, REQUIRED_SUITSPEC_FIELDS

_SUIT_ID_RE = re.compile(r"^VDA-[A-Z0-9]+-[A-Z0-9]+-[0-9]{2}-[0-9]{4}$")
_APPROVAL_ID_RE = re.compile(r"^APV-[0-9]{8}$")
_MORPHOTYPE_ID_RE = re.compile(r"^MTP-[0-9]{8}$")
_HEX_RE = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _require_fields(payload: dict[str, Any], required: list[str], label: str) -> None:
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")


def validate_suitspec(payload: dict[str, Any]) -> None:
    _require_fields(payload, REQUIRED_SUITSPEC_FIELDS, label="SuitSpec")
    if payload.get("schema_version") != "0.2":
        raise ValueError("SuitSpec.schema_version must be '0.2'")
    if not _SUIT_ID_RE.fullmatch(payload["suit_id"]):
        raise ValueError("SuitSpec.suit_id format is invalid")

    approval_id = payload.get("approval_id")
    if approval_id and not _APPROVAL_ID_RE.fullmatch(approval_id):
        raise ValueError("SuitSpec.approval_id format is invalid")

    morphotype_id = payload.get("morphotype_id")
    if morphotype_id and not _MORPHOTYPE_ID_RE.fullmatch(morphotype_id):
        raise ValueError("SuitSpec.morphotype_id format is invalid")

    style_tags = payload.get("style_tags", [])
    if not isinstance(style_tags, list) or not style_tags:
        raise ValueError("SuitSpec.style_tags must be a non-empty list")

    modules = payload.get("modules", {})
    if not isinstance(modules, dict) or not modules:
        raise ValueError("SuitSpec.modules must be a non-empty object")

    for slot in CORE_MODULE_SLOTS:
        if slot not in modules:
            raise ValueError(f"SuitSpec.modules.{slot} is required")

    for name, module in modules.items():
        if not isinstance(module, dict):
            raise ValueError(f"SuitSpec.modules.{name} must be an object")
        if "enabled" not in module:
            raise ValueError(f"SuitSpec.modules.{name}.enabled is required")
        if "asset_ref" not in module:
            raise ValueError(f"SuitSpec.modules.{name}.asset_ref is required")

    palette = payload.get("palette", {})
    for color in ("primary", "secondary", "emissive"):
        value = palette.get(color, "")
        if not _HEX_RE.fullmatch(value):
            raise ValueError(f"SuitSpec.palette.{color} must be hex color")


def validate_morphotype(payload: dict[str, Any]) -> None:
    _require_fields(payload, REQUIRED_MORPHOTYPE_FIELDS, label="Morphotype")
    if payload.get("schema_version") != "0.2":
        raise ValueError("Morphotype.schema_version must be '0.2'")
    if not _MORPHOTYPE_ID_RE.fullmatch(payload["morphotype_id"]):
        raise ValueError("Morphotype.morphotype_id format is invalid")

    source = payload.get("source")
    if source not in {"manual", "mocopi", "webcam"}:
        raise ValueError("Morphotype.source must be manual/mocopi/webcam")

    conf = payload.get("confidence")
    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
        raise ValueError("Morphotype.confidence must be in 0..1")


def validate_file(path: str | Path, kind: str) -> None:
    payload = load_json(path)
    if kind == "suitspec":
        validate_suitspec(payload)
        return
    if kind == "morphotype":
        validate_morphotype(payload)
        return
    raise ValueError(f"Unsupported kind: {kind}")
