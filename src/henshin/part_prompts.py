"""Per-part prompt strategy for modular armor generation."""

from __future__ import annotations

from typing import Any, Literal

from .suit_dna import describe_part_function, resolve_suit_design_dna
from .uv_contracts import resolve_uv_contract


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


def _base_style_text(suitspec: dict[str, Any], style_variation: dict[str, Any] | None = None) -> str:
    tags = suitspec.get("style_tags") or []
    palette = suitspec.get("palette") or {}
    primary = palette.get("primary", "#1E2A3A")
    secondary = palette.get("secondary", "#A8B3C6")
    emissive = palette.get("emissive", "#3AC7FF")
    tag_text = ", ".join(tags) if tags else "metal, audit, visor"
    base = (
        f"Style tags: {tag_text}. Palette primary={primary}, secondary={secondary}, emissive={emissive}. "
        "Treat the SuitSpec palette as the baseline manufacturing family, not as a rigid color lock. "
        "Hard-surface industrial hero armor, clean panel lines, production-ready concept sheet."
    )
    return base


def _base_suit_surface_text(suitspec: dict[str, Any]) -> str:
    palette = suitspec.get("palette") or {}
    primary = palette.get("primary", "#1E2A3A")
    secondary = palette.get("secondary", "#A8B3C6")
    emissive = palette.get("emissive", "#3AC7FF")
    return (
        "Base suit substrate continuity:\n"
        f"- Treat primary={primary} and secondary={secondary} as outer armor colors; the fitted body suit beneath them should be a darker harmonized substrate, not a flat single-color fill.\n"
        "- The base suit language is tokusatsu-style technical fabric: restrained symmetric panel lines, controlled diagonal motifs, flexible joint zones, and narrow emissive piping.\n"
        f"- Emissive routing uses {emissive} sparingly as thin line masks that visually connect the base suit to the armor overlay.\n"
        "- Generate armor surfaces as part of this full suit system: hard plates sit above the patterned body suit, while color blocking stays compatible instead of fighting the substrate.\n"
    )


def _lore_design_text() -> str:
    return (
        "Treat this armor as belonging to an established sci-fi canon. "
        "Preserve lore continuity, manufacturing logic, maintenance access, actuator clearance, power routing, "
        "and readable mechanical purpose. Every seam, panel split, vent, fastener, and emissive element must feel "
        "engineered rather than decorative."
    )


def _module_override_text(module: dict[str, Any]) -> str:
    override = module.get("generation_prompt")
    if not isinstance(override, str) or not override.strip():
        return ""
    return (
        "Module-specific art direction from SuitSpec:\n"
        f"{override.strip()}\n"
        "Honor that direction, but do not violate the UV engineering contract, the suit-wide manufacturing language, or the part's mechanical role.\n"
    )


def _generation_brief_text(generation_brief: str | None) -> str:
    if not generation_brief or not generation_brief.strip():
        return ""
    return (
        "Creative direction from the current request: "
        f"{generation_brief.strip()}\n"
        "Keep the result practical for wearable modular armor and preserve clean silhouette readability.\n"
    )


def _user_armor_profile_text(user_armor_profile: dict[str, Any] | None) -> str:
    if not user_armor_profile:
        return ""
    return (
        "User-specific armor DNA:\n"
        f"- Identity seed: {user_armor_profile.get('identity_seed', 'unknown')}\n"
        f"- Protect signature: {user_armor_profile.get('protect_signature', '')}\n"
        f"- Temperament signature: {user_armor_profile.get('temperament_signature', '')}\n"
        f"- Palette family: {user_armor_profile.get('palette_family', '')}\n"
        f"- Palette guidance: {user_armor_profile.get('palette_guidance', '')}\n"
        f"- Finish family: {user_armor_profile.get('finish_family', '')}\n"
        f"- Finish guidance: {user_armor_profile.get('finish_guidance', '')}\n"
        f"- Motif family: {user_armor_profile.get('motif_family', '')}\n"
        f"- Motif guidance: {user_armor_profile.get('motif_guidance', '')}\n"
        f"- Panel density family: {user_armor_profile.get('panel_density_family', '')}\n"
        f"- Panel guidance: {user_armor_profile.get('panel_density_guidance', '')}\n"
        f"- Silhouette family: {user_armor_profile.get('silhouette_family', '')}\n"
        f"- Silhouette guidance: {user_armor_profile.get('silhouette_guidance', '')}\n"
        f"- Emissive family: {user_armor_profile.get('emissive_family', '')}\n"
        f"- Emissive guidance: {user_armor_profile.get('emissive_guidance', '')}\n"
        f"- Tri-view family: {user_armor_profile.get('tri_view_family', '')}\n"
        f"- Tri-view guidance: {user_armor_profile.get('tri_view_guidance', '')}\n"
        f"- Continuity rule: {user_armor_profile.get('continuity_rule', '')}\n"
    )


def _style_variation_text(style_variation: dict[str, Any] | None) -> str:
    if not style_variation:
        return ""
    return (
        "Current emotional modulation:\n"
        f"- Variation seed: {style_variation.get('variation_seed', 'current-run')}\n"
        f"- Palette family: {style_variation.get('palette_family', 'canon-safe variation')}\n"
        f"- Palette guidance: {style_variation.get('palette_guidance', '')}\n"
        f"- Finish guidance: {style_variation.get('finish_guidance', '')}\n"
        f"- Emissive guidance: {style_variation.get('emissive_guidance', '')}\n"
        f"- Motif guidance: {style_variation.get('motif_guidance', '')}\n"
        f"- Panel guidance: {style_variation.get('panel_guidance', '')}\n"
        f"- Silhouette guidance: {style_variation.get('silhouette_guidance', '')}\n"
        f"- Tri-view guidance: {style_variation.get('tri_view_guidance', '')}\n"
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


def _design_dna_text(suitspec: dict[str, Any]) -> str:
    dna = resolve_suit_design_dna(suitspec)
    silhouette = ", ".join(dna.silhouette_keywords)
    return (
        "Whole-suit design DNA:\n"
        f"- Manufacturer family: {dna.manufacturer_family}\n"
        f"- Armor generation: {dna.armor_generation}\n"
        f"- Silhouette keywords: {silhouette}\n"
        f"- Panel language: {dna.panel_language}\n"
        f"- Fastener family: {dna.fastener_family}\n"
        f"- Emissive routing: {dna.emissive_routing}\n"
        f"- Maintenance philosophy: {dna.maintenance_philosophy}\n"
        f"- Damage policy: {dna.damage_policy}\n"
        f"- Material stack: {dna.material_stack}\n"
        f"- Dock continuity rule: {dna.dock_readiness}\n"
    )


def _part_role_text(part: str) -> str:
    return f"Mechanical role:\n- {describe_part_function(part)}\n"


def _three_view_text(part: str) -> str:
    groups: dict[str, str] = {
        "helmet": (
            "Three-view discipline:\n"
            "- Front view: visor band, brow line, and frontal crown carry identity.\n"
            "- Side view: sensor housings, ear or comms shells, and neck transition explain function.\n"
            "- Rear view: occipital shell, rear seam, and service latch logic must remain intentional.\n"
            "- No front-only decoration that collapses from the side or rear.\n"
        ),
        "chest": (
            "Three-view discipline:\n"
            "- Front view: sternum core, pectoral plates, and service hatches define identity.\n"
            "- Side view: rib wraps, under-arm cut lines, and harness transfer logic must read cleanly.\n"
            "- Rear-adjacent wrap zones: edge transitions must already imply how the part joins the dorsal assembly.\n"
            "- Color blocking and panel rhythm must survive orthographic inspection.\n"
        ),
        "back": (
            "Three-view discipline:\n"
            "- Rear view: spine channel, dorsal rails, and exhaust or service access define identity.\n"
            "- Side view: shoulder and waist transfer logic must remain readable.\n"
            "- Front-adjacent wrap zones: edges should imply how the assembly meets the chest without painted perspective tricks.\n"
        ),
        "shoulder": (
            "Three-view discipline:\n"
            "- Front/outer view: identification face and deflection crest carry identity.\n"
            "- Side view: cap depth, hinge clearance, and collar transition explain the module.\n"
            "- Rear view: deflection return and service seam remain intentional, not blank filler.\n"
        ),
        "arm": (
            "Three-view discipline:\n"
            "- Front view: strike face or dorsal lane carries primary identity.\n"
            "- Side view: cuff transitions, tool lanes, and actuator clearances explain the wrap.\n"
            "- Rear or inner view: seam returns and maintenance breaks must remain purposeful and calm.\n"
        ),
        "waist": (
            "Three-view discipline:\n"
            "- Front view: abdomen guard and belt transfer define identity.\n"
            "- Side view: articulation breaks and load transfer into the hips must read cleanly.\n"
            "- Rear view: closure logic and service segmentation must still look designed.\n"
        ),
        "leg": (
            "Three-view discipline:\n"
            "- Front view: crest or strike face carries identity.\n"
            "- Side view: gait mechanics, hinge approach, and ankle or knee transitions explain structure.\n"
            "- Rear or inner view: seam returns and maintenance zones remain coherent and controlled.\n"
        ),
        "hand": (
            "Three-view discipline:\n"
            "- Front or dorsal view: back-of-hand shield and knuckle lanes carry identity.\n"
            "- Side view: finger segmentation and wrist docking must stay readable.\n"
            "- Palm or inner wrap zones should remain low-frequency and mechanically plausible.\n"
        ),
    }
    if part in {"left_shoulder", "right_shoulder"}:
        return groups["shoulder"]
    if part in {"left_upperarm", "right_upperarm", "left_forearm", "right_forearm"}:
        return groups["arm"]
    if part in {"left_thigh", "right_thigh", "left_shin", "right_shin", "left_boot", "right_boot"}:
        return groups["leg"]
    if part in {"left_hand", "right_hand"}:
        return groups["hand"]
    return groups.get(part, (
        "Three-view discipline:\n"
        "- Front, side, and rear surfaces must all read as the same engineered object.\n"
        "- No identity logic that depends on a single hero angle.\n"
    ))


def _uv_contract_text(suitspec: dict[str, Any], part: str) -> str:
    contract = resolve_uv_contract(suitspec, part)
    fill_min, fill_max = contract.fill_ratio_target
    seam_min, seam_max = contract.seam_safe_margin_percent
    return (
        "UV engineering contract:\n"
        f"- Texture fill ratio target: {fill_min}-{fill_max}% of the canvas contains intentional material and panel information.\n"
        f"- Blank contiguous area max: {contract.blank_area_max_percent}%.\n"
        f"- Seam-safe margin: outer {seam_min}-{seam_max}% stays low-frequency.\n"
        f"- Symmetry rule: {contract.symmetry_rule}\n"
        f"- Primary motif zone: {contract.primary_motif_zone}\n"
        f"- Low-frequency zone: {contract.low_frequency_zone}\n"
        f"- Panel flow direction: {contract.panel_flow_direction}\n"
        f"- Forbidden detail zone: {contract.forbidden_detail_zone}\n"
        f"- UV island rule: {contract.island_layout_rule}\n"
    )


def build_part_prompt(
    part: str,
    suitspec: dict[str, Any],
    *,
    texture_mode: TextureMode = "concept",
    generation_brief: str | None = None,
    style_variation: dict[str, Any] | None = None,
    user_armor_profile: dict[str, Any] | None = None,
) -> str:
    modules = suitspec.get("modules", {})
    module = modules.get(part, {})
    if not isinstance(module, dict):
        module = {}

    hint = PART_PROMPT_HINTS.get(part, f"{part} armor part")
    style_text = _base_style_text(suitspec, style_variation=style_variation)
    base_suit_surface_text = _base_suit_surface_text(suitspec)
    design_dna_text = _design_dna_text(suitspec)
    lore_text = _lore_design_text()
    user_profile_text = _user_armor_profile_text(user_armor_profile)
    module_override_text = _module_override_text(module)
    part_role_text = _part_role_text(part)
    three_view_text = _three_view_text(part)
    variation_text = _style_variation_text(style_variation)
    brief_text = _generation_brief_text(generation_brief)
    if texture_mode == "mesh_uv":
        uv_hint = _uv_layout_hint(part)
        uv_contract_text = _uv_contract_text(suitspec, part)
        return (
            "Generate a UV-ready texture atlas for one armor module.\n"
            f"Target module: {part} ({hint}).\n"
            f"{style_text}\n"
            f"{base_suit_surface_text}"
            f"{design_dna_text}"
            f"{lore_text}\n"
            f"{user_profile_text}"
            f"{part_role_text}"
            f"{three_view_text}"
            f"{module_override_text}"
            f"{variation_text}"
            f"{brief_text}"
            f"{uv_contract_text}"
            "Output format requirements:\n"
            "- When a reference image is provided, treat it as the UV engineering guide and obey its island layout authority.\n"
            "- Think like an orthographic three-view sheet translated into UV islands, not like a hero render painted onto a square.\n"
            "- Front-facing identity surfaces belong to primary motif zones; lateral surfaces carry wrap logic and service cuts; rear or seam-adjacent surfaces carry maintenance logic.\n"
            "- Preserve same user, same production lineage continuity across every module.\n"
            "- 1:1 square texture map (base-color/albedo style), no perspective view.\n"
            "- Resolution target: 2048x2048 equivalent detail density.\n"
            "- Flat texture sheet only. Do NOT draw standalone objects, mannequins, or scene background.\n"
            "- Maintain consistent material language across the whole sheet.\n"
            f"- UV layout intent: {uv_hint}\n"
            "- Keep directional panel lines continuous across UV seams (U wrap continuity).\n"
            "- Preserve the user-specific palette, motif, panel-density, and tri-view family; emotional input only modulates the current run.\n"
            "- No text, watermark, logos, or frame graphics."
        )

    return (
        "Generate a single isolated armor part image.\n"
        f"Part: {part} ({hint}).\n"
        f"{style_text}\n"
        f"{base_suit_surface_text}"
        f"{design_dna_text}"
        f"{lore_text}\n"
        f"{user_profile_text}"
        f"{part_role_text}"
        f"{three_view_text}"
        f"{module_override_text}"
        f"{variation_text}"
        f"{brief_text}"
        "Requirements:\n"
        "- White or transparent-like clean background.\n"
        "- Centered object, orthographic three-view feel, no perspective distortion.\n"
        "- Make the design survive front, side, and rear orthographic inspection; avoid front-only gimmicks.\n"
        "- Preserve same user, same production lineage continuity across every module.\n"
        "- Preserve the user-specific palette, motif, panel-density, and tri-view family; emotional input only modulates the current run.\n"
        "- No human body, no full character, no text, no watermark.\n"
        "- Crisp edge definition for texture/decal extraction."
    )


def build_uv_refine_prompt(
    part: str,
    suitspec: dict[str, Any],
    generation_brief: str | None = None,
    *,
    style_variation: dict[str, Any] | None = None,
    user_armor_profile: dict[str, Any] | None = None,
) -> str:
    hint = PART_PROMPT_HINTS.get(part, f"{part} armor part")
    style_text = _base_style_text(suitspec, style_variation=style_variation)
    base_suit_surface_text = _base_suit_surface_text(suitspec)
    design_dna_text = _design_dna_text(suitspec)
    lore_text = _lore_design_text()
    uv_hint = _uv_layout_hint(part)
    uv_contract_text = _uv_contract_text(suitspec, part)
    module_override_text = _module_override_text(suitspec.get("modules", {}).get(part, {}))
    part_role_text = _part_role_text(part)
    three_view_text = _three_view_text(part)
    user_profile_text = _user_armor_profile_text(user_armor_profile)
    variation_text = _style_variation_text(style_variation)
    brief_text = _generation_brief_text(generation_brief)
    return (
        "You are given a reference concept image for one armor module.\n"
        f"Target module: {part} ({hint}).\n"
        f"{style_text}\n"
        f"{base_suit_surface_text}"
        f"{design_dna_text}"
        f"{lore_text}\n"
        f"{user_profile_text}"
        f"{part_role_text}"
        f"{three_view_text}"
        f"{module_override_text}"
        f"{variation_text}"
        f"{brief_text}"
        f"{uv_contract_text}"
        "Task:\n"
        "- Reference A = UV engineering guide. It controls island placement, seam-safe borders, centerline, and motif zones.\n"
        "- Reference B = style concept. It controls surface language, material rhythm, and motif character.\n"
        "- Convert the reference visual language into a UV-ready flat texture sheet.\n"
        "- Preserve front, side, and rear logic while translating it into UV space. Side and rear surfaces must not collapse into blank filler.\n"
        "- Preserve same user, same production lineage continuity across every module.\n"
        "- Keep motifs, panel rhythm, and material logic from the reference while re-laying to UV space.\n"
        "Output format requirements:\n"
        "- 1:1 square base-color texture map.\n"
        "- Resolution target: 2048x2048 equivalent detail density.\n"
        f"- UV layout intent: {uv_hint}\n"
        "- No object render, no mannequin, no perspective camera.\n"
        "- No text, watermark, logos, or frame graphics."
    )


def resolve_part_prompts(
    suitspec: dict[str, Any],
    parts: list[str],
    *,
    texture_mode: TextureMode = "concept",
    generation_brief: str | None = None,
    style_variation: dict[str, Any] | None = None,
    user_armor_profile: dict[str, Any] | None = None,
) -> dict[str, str]:
    prompts: dict[str, str] = {}
    for part in parts:
        prompts[part] = build_part_prompt(
            part,
            suitspec,
            texture_mode=texture_mode,
            generation_brief=generation_brief,
            style_variation=style_variation,
            user_armor_profile=user_armor_profile,
        )
    return prompts
