"""Draft asset generation for SuitSpec and Morphotype."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import OATHS
from .ids import generate_morphotype_id, generate_suit_id


def create_draft_suitspec(
    suit_id: str | None = None,
    *,
    style_tags: list[str] | None = None,
    oath: str = "INTEGRITY_FIRST",
    model_id: str = "gemini-3-pro-image-preview",
) -> dict[str, Any]:
    if oath not in OATHS:
        raise ValueError(f"Unsupported oath: {oath}")

    sid = suit_id or generate_suit_id()
    tags = style_tags or ["metal", "visor", "audit"]

    return {
        "schema_version": "0.2",
        "suit_id": sid,
        "oath": oath,
        "style_tags": tags,
        "modules": {
            "helmet": {"enabled": True, "asset_ref": "modules/helmet/base.prefab"},
            "chest": {"enabled": True, "asset_ref": "modules/chest/base.prefab"},
            "shoulder": {"enabled": True, "asset_ref": "modules/shoulder/base.prefab"},
            "back": {"enabled": True, "asset_ref": "modules/back/base.prefab"},
        },
        "palette": {"primary": "#1E2A3A", "secondary": "#A8B3C6", "emissive": "#3AC7FF"},
        "blueprint": {"image_path": "artifacts/Blueprint.png", "projection_mode": "triplanar"},
        "emblem": {"image_path": "artifacts/Emblem.png", "placement": "chest"},
        "effects": {
            "deposition_seconds": 7.5,
            "particle_density": 0.8,
            "wire_to_metal_curve": "ease_in_out",
        },
        "text": {
            "deposition_log_lines": [
                "STATUS: POSTED",
                "FIT AUDIT: PASS",
                "MORPHOTYPE: LOCKED",
                "BLUEPRINT: ISSUED",
                "APPROVAL: GRANTED",
                "DEPOSITION: START",
                "SEAL: VERIFIED",
            ],
            "callout": "Protocol complete. Integrity first.",
        },
        "generation": {
            "model_id": model_id,
            "prompt": "Industrial armored suit blueprint, strict panel lines, no character face.",
            "seed": 1001,
        },
    }


def create_draft_morphotype(
    morphotype_id: str | None = None,
    *,
    source: str = "manual",
) -> dict[str, Any]:
    if source not in {"manual", "mocopi", "webcam"}:
        raise ValueError(f"Unsupported source: {source}")

    mid = morphotype_id or generate_morphotype_id()
    return {
        "schema_version": "0.2",
        "morphotype_id": mid,
        "height_cm": 175.0,
        "shoulder_width_cm": 44.0,
        "hip_width_cm": 36.0,
        "arm_length_cm": 62.0,
        "leg_length_cm": 92.0,
        "torso_length_cm": 56.0,
        "scale": 1.0,
        "source": source,
        "confidence": 0.72,
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p
