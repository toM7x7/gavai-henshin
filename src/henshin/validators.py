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

_FIT_SOURCES = {
    "chest_core",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
}


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _require_fields(payload: dict[str, Any], required: list[str], label: str) -> None:
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"{label} missing required fields: {missing}")


def _validate_vec3(value: Any, label: str) -> None:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must be a 3-item array")
    for n in value:
        if not isinstance(n, (int, float)):
            raise ValueError(f"{label} items must be numbers")


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
        attachment_slot = module.get("attachment_slot")
        if attachment_slot is not None:
            if not isinstance(attachment_slot, str) or not attachment_slot.strip():
                raise ValueError(f"SuitSpec.modules.{name}.attachment_slot must be a non-empty string")

        fit = module.get("fit")
        if fit is not None:
            if not isinstance(fit, dict):
                raise ValueError(f"SuitSpec.modules.{name}.fit must be an object")
            source = fit.get("source")
            if source is not None and source not in _FIT_SOURCES:
                raise ValueError(
                    f"SuitSpec.modules.{name}.fit.source must be one of {sorted(_FIT_SOURCES)}"
                )
            attach = fit.get("attach")
            if attach is not None and attach not in {"start", "center", "end"}:
                raise ValueError(f"SuitSpec.modules.{name}.fit.attach must be start/center/end")
            for key in ("scale", "follow", "minScale"):
                vec = fit.get(key)
                if vec is not None:
                    _validate_vec3(vec, f"SuitSpec.modules.{name}.fit.{key}")

        vrm_anchor = module.get("vrm_anchor")
        if vrm_anchor is not None:
            if not isinstance(vrm_anchor, dict):
                raise ValueError(f"SuitSpec.modules.{name}.vrm_anchor must be an object")
            bone = vrm_anchor.get("bone")
            if bone is not None and (not isinstance(bone, str) or not bone.strip()):
                raise ValueError(f"SuitSpec.modules.{name}.vrm_anchor.bone must be a non-empty string")
            for key in ("offset", "rotation", "scale"):
                vec = vrm_anchor.get(key)
                if vec is not None:
                    _validate_vec3(vec, f"SuitSpec.modules.{name}.vrm_anchor.{key}")
                    if key == "scale" and any(float(v) <= 0 for v in vec):
                        raise ValueError(f"SuitSpec.modules.{name}.vrm_anchor.scale must be > 0")

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
