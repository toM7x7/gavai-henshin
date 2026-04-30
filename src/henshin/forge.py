"""Draft asset generation for SuitSpec and Morphotype."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import OATHS
from .ids import generate_morphotype_id, generate_suit_id


RUNTIME_ARMOR_MODULES: tuple[str, ...] = (
    "helmet",
    "chest",
    "back",
    "left_shoulder",
    "right_shoulder",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "waist",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
    "left_hand",
    "right_hand",
)


def armor_glb_asset_ref(module: str, repo_root: str | Path = ".") -> str | None:
    """Return the canonical GLB asset_ref for a delivered armor module."""

    name = str(module or "").strip()
    if not name:
        return None
    rel = f"viewer/assets/armor-parts/{name}/{name}.glb"
    return rel if (Path(repo_root) / rel).is_file() else None


def create_draft_suitspec(
    suit_id: str | None = None,
    *,
    style_tags: list[str] | None = None,
    oath: str = "INTEGRITY_FIRST",
    model_id: str = "gemini-3-pro-image-preview",
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    if oath not in OATHS:
        raise ValueError(f"Unsupported oath: {oath}")

    sid = suit_id or generate_suit_id()
    tags = style_tags or ["metal", "visor", "audit"]

    modules: dict[str, dict[str, Any]] = {}
    for module_name in RUNTIME_ARMOR_MODULES:
        asset_ref = armor_glb_asset_ref(module_name, repo_root=repo_root) or (
            f"viewer/assets/meshes/{module_name}.mesh.json"
        )
        modules[module_name] = {"enabled": True, "asset_ref": asset_ref}

    return {
        "schema_version": "0.2",
        "suit_id": sid,
        "oath": oath,
        "style_tags": tags,
        "operator_profile": {
            "protect_archetype": "citizens",
            "temperament_bias": "calm",
            "color_mood": "industrial_gray",
            "note": "",
        },
        "modules": modules,
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
            "part_prompts": {},
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
