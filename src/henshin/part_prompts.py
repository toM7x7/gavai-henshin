"""Per-part prompt strategy for modular armor generation."""

from __future__ import annotations

from typing import Any


PART_PROMPT_HINTS: dict[str, str] = {
    "helmet": "helmet shell with visor aperture, no face, no neck",
    "chest": "chest armor plate, sternum core area, no arms",
    "back": "backplate with spine line and mount points",
    "left_shoulder": "left shoulder pauldron, isolated part",
    "right_shoulder": "right shoulder pauldron, isolated part",
    "left_upperarm": "left upper-arm armor sleeve, isolated",
    "right_upperarm": "right upper-arm armor sleeve, isolated",
    "left_forearm": "left forearm gauntlet, isolated",
    "right_forearm": "right forearm gauntlet, isolated",
    "waist": "waist belt armor and abdomen guard, isolated",
    "left_thigh": "left thigh armor plate, isolated",
    "right_thigh": "right thigh armor plate, isolated",
    "left_shin": "left shin greave, isolated",
    "right_shin": "right shin greave, isolated",
    "left_boot": "left armored boot, isolated",
    "right_boot": "right armored boot, isolated",
    "left_hand": "left hand armored glove, isolated",
    "right_hand": "right hand armored glove, isolated",
}


def list_enabled_parts(suitspec: dict[str, Any]) -> list[str]:
    modules = suitspec.get("modules", {})
    enabled = []
    for name, module in modules.items():
        if isinstance(module, dict) and module.get("enabled", False):
            enabled.append(name)
    return enabled


def _base_style_text(suitspec: dict[str, Any]) -> str:
    tags = suitspec.get("style_tags") or []
    palette = suitspec.get("palette") or {}
    primary = palette.get("primary", "#1E2A3A")
    secondary = palette.get("secondary", "#A8B3C6")
    emissive = palette.get("emissive", "#3AC7FF")
    tag_text = ", ".join(tags) if tags else "metal, audit, visor"
    return (
        f"Style tags: {tag_text}. Palette primary={primary}, secondary={secondary}, emissive={emissive}. "
        "Hard-surface industrial hero armor, clean panel lines, production-ready concept sheet."
    )


def build_part_prompt(part: str, suitspec: dict[str, Any]) -> str:
    modules = suitspec.get("modules", {})
    module = modules.get(part, {})
    if isinstance(module, dict):
        override = module.get("generation_prompt")
        if isinstance(override, str) and override.strip():
            return override.strip()

    hint = PART_PROMPT_HINTS.get(part, f"{part} armor part")
    style_text = _base_style_text(suitspec)
    return (
        "Generate a single isolated armor part image.\n"
        f"Part: {part} ({hint}).\n"
        f"{style_text}\n"
        "Requirements:\n"
        "- White or transparent-like clean background.\n"
        "- Centered object, orthographic feel, no perspective distortion.\n"
        "- No human body, no full character, no text, no watermark.\n"
        "- Crisp edge definition for texture/decal extraction."
    )


def resolve_part_prompts(suitspec: dict[str, Any], parts: list[str]) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for part in parts:
        prompts[part] = build_part_prompt(part, suitspec)
    return prompts
