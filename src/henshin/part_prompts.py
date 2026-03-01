"""Per-part prompt strategy for modular armor generation."""

from __future__ import annotations

from typing import Any, Literal


TextureMode = Literal["concept", "mesh_uv"]


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


def _uv_layout_hint(part: str) -> str:
    hints: dict[str, str] = {
        "helmet": (
            "Visor band and frontal silhouette should occupy center U range (0.30-0.70). "
            "Top crown detail should concentrate in upper V range (0.58-0.92). "
            "Back-seam area near U<0.06 and U>0.94 must stay low-frequency."
        ),
        "chest": (
            "Main sternum line should stay around U=0.50 (approximately 0.42-0.58). "
            "Pectoral panel rhythm should be left-right symmetric in U. "
            "Outer edge zones U<0.05 and U>0.95 must remain seam-safe and low-density."
        ),
        "back": "Spine-line details should run vertically through UV center.",
        "left_shoulder": "Keep shoulder cap highlight in upper UV half and seam-safe at the back edge.",
        "right_shoulder": "Keep shoulder cap highlight in upper UV half and seam-safe at the back edge.",
        "left_upperarm": "Longitudinal striping should run along V direction for sleeve wrapping.",
        "right_upperarm": "Longitudinal striping should run along V direction for sleeve wrapping.",
        "left_forearm": "Primary panel lines should follow forearm axis; avoid dense detail at seam edges.",
        "right_forearm": "Primary panel lines should follow forearm axis; avoid dense detail at seam edges.",
        "waist": "Belt-like horizontal banding with seam-safe transitions on left/right edges.",
        "left_thigh": "Vertical armor grooves aligned to limb axis, sparse detail near UV border.",
        "right_thigh": "Vertical armor grooves aligned to limb axis, sparse detail near UV border.",
        "left_shin": "Front shin highlight should be centered and taper towards lower V.",
        "right_shin": "Front shin highlight should be centered and taper towards lower V.",
        "left_boot": "Toe-cap emphasis in lower UV region, side seams kept simple.",
        "right_boot": "Toe-cap emphasis in lower UV region, side seams kept simple.",
        "left_hand": "Back-of-hand plating should occupy UV center, fingers implied with clean lanes.",
        "right_hand": "Back-of-hand plating should occupy UV center, fingers implied with clean lanes.",
    }
    return hints.get(part, "Keep principal details centered and seam-safe for UV wrapping.")


def build_part_prompt(part: str, suitspec: dict[str, Any], *, texture_mode: TextureMode = "concept") -> str:
    modules = suitspec.get("modules", {})
    module = modules.get(part, {})
    if isinstance(module, dict):
        override = module.get("generation_prompt")
        if isinstance(override, str) and override.strip():
            return override.strip()

    hint = PART_PROMPT_HINTS.get(part, f"{part} armor part")
    style_text = _base_style_text(suitspec)
    if texture_mode == "mesh_uv":
        uv_hint = _uv_layout_hint(part)
        return (
            "Generate a UV-ready texture atlas for one armor module.\n"
            f"Target module: {part} ({hint}).\n"
            f"{style_text}\n"
            "Output format requirements:\n"
            "- 1:1 square texture map (base-color/albedo style), no perspective view.\n"
            "- Resolution target: 2048x2048 equivalent detail density.\n"
            "- Flat texture sheet only. Do NOT draw standalone objects, mannequins, or scene background.\n"
            "- Texture fill ratio target: 82-96% of the canvas should contain intended material/panel information.\n"
            "- Border seam-safe margin: outer 3-5% edges should be low-frequency detail only.\n"
            "- Do not leave large blank white regions (>10% contiguous area).\n"
            "- Maintain consistent material language across the whole sheet.\n"
            f"- UV layout intent: {uv_hint}\n"
            "- Keep directional panel lines continuous across UV seams (U wrap continuity).\n"
            "- No text, watermark, logos, or frame graphics."
        )

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


def resolve_part_prompts(
    suitspec: dict[str, Any], parts: list[str], *, texture_mode: TextureMode = "concept"
) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for part in parts:
        prompts[part] = build_part_prompt(part, suitspec, texture_mode=texture_mode)
    return prompts
