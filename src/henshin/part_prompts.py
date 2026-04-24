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

UV_ATLAS_FAILURE_GUARD = (
    "UV atlas failure guards:\n"
    "- Cover the entire square with continuous armor material. No unpainted white or gray negative space around armor-shaped silhouettes.\n"
    "- Do not draw floating left/right plates, detachable side pods, a front-view shell, or a product-shot part on a blank canvas.\n"
    "- Do not add readable letters, numbers, QR codes, labels, maker marks, serial tags, UI text, or calibration text.\n"
    "- Do not use bevel shadows, cast shadows, or perspective shading to make the texture look like a rendered object.\n"
    "- Seam-safe margins can be low frequency, but they must still be painted as armor material.\n"
)

UV_SAFE_MODULE_DESCRIPTORS: dict[str, str] = {
    "helmet": "H-01 cranial sensor-shell UV surface group",
    "chest": "C-01 torso core-shell UV surface group",
    "back": "B-01 dorsal service-shell UV surface group",
    "left_shoulder": "LS-01 left upper-mount UV surface group",
    "right_shoulder": "RS-01 right upper-mount UV surface group",
    "left_upperarm": "LUA-01 left proximal limb-shell UV surface group",
    "right_upperarm": "RUA-01 right proximal limb-shell UV surface group",
    "left_forearm": "LFA-01 left distal tool-shell UV surface group",
    "right_forearm": "RFA-01 right distal tool-shell UV surface group",
    "waist": "W-01 abdominal transfer-shell UV surface group",
    "left_thigh": "LT-01 left upper-leg load-shell UV surface group",
    "right_thigh": "RT-01 right upper-leg load-shell UV surface group",
    "left_shin": "LSH-01 left lower-leg gait-shell UV surface group",
    "right_shin": "RSH-01 right lower-leg gait-shell UV surface group",
    "left_boot": "LFT-01 left lower terminal contact-shell UV surface group",
    "right_boot": "RFT-01 right lower terminal contact-shell UV surface group",
    "left_hand": "LH-01 left manipulator guard-shell UV surface group",
    "right_hand": "RH-01 right manipulator guard-shell UV surface group",
}

UV_OBJECT_SUBJECT_TERMS: dict[str, str] = {
    "helmet": "helmet, mask, head, or face object",
    "chest": "chestplate or torso object",
    "back": "backpack or backplate object",
    "left_shoulder": "pauldron or shoulder object",
    "right_shoulder": "pauldron or shoulder object",
    "left_upperarm": "arm sleeve object",
    "right_upperarm": "arm sleeve object",
    "left_forearm": "gauntlet or forearm object",
    "right_forearm": "gauntlet or forearm object",
    "waist": "belt or waist object",
    "left_thigh": "thigh guard object",
    "right_thigh": "thigh guard object",
    "left_shin": "shin guard object",
    "right_shin": "shin guard object",
    "left_boot": "boot, shoe, sole, or footwear object",
    "right_boot": "boot, shoe, sole, or footwear object",
    "left_hand": "glove, hand, or finger object",
    "right_hand": "glove, hand, or finger object",
}

UV_SAFE_PART_FUNCTIONS: dict[str, str] = {
    "helmet": "Cranial sensor-shell zones need visor-cassette material lanes, comms enclosure surfaces, and maintenance-latch returns without drawing a headgear silhouette.",
    "chest": "Torso core-shell zones need sternum access, load-transfer lanes, and core-protection hierarchy without drawing a torso plate object.",
    "back": "Dorsal service-shell zones need spine channeling, thermal management, and mount hardware continuity without drawing a backpack object.",
    "left_shoulder": "Upper-mount zones need deflection crest, rotation clearance, and identification surface logic without drawing a pauldron object.",
    "right_shoulder": "Upper-mount zones need deflection crest, rotation clearance, and identification surface logic without drawing a pauldron object.",
    "left_upperarm": "Proximal limb-shell zones need actuator clearance, removable service cover logic, and strike-face hierarchy without drawing an arm sleeve object.",
    "right_upperarm": "Proximal limb-shell zones need actuator clearance, removable service cover logic, and strike-face hierarchy without drawing an arm sleeve object.",
    "left_forearm": "Distal tool-shell zones need wrist-cuff logic, hardpoint lanes, cable routing, and tool-robust surfaces without drawing a gauntlet object.",
    "right_forearm": "Distal tool-shell zones need wrist-cuff logic, hardpoint lanes, cable routing, and tool-robust surfaces without drawing a gauntlet object.",
    "waist": "Transfer-shell zones need abdomen guard rhythm, hip articulation edges, and service segmentation without drawing a belt object.",
    "left_thigh": "Upper-leg load-shell zones need forward load face, mount rail continuity, and replacement-friendly segmentation without drawing a leg object.",
    "right_thigh": "Upper-leg load-shell zones need forward load face, mount rail continuity, and replacement-friendly segmentation without drawing a leg object.",
    "left_shin": "Lower-leg gait-shell zones need front crest hierarchy, ankle-transfer seams, and grounded mobility logic without drawing a greave object.",
    "right_shin": "Lower-leg gait-shell zones need front crest hierarchy, ankle-transfer seams, and grounded mobility logic without drawing a greave object.",
    "left_boot": "Lower terminal contact-shell zones need toe-roll material bands, heel-stabilizer logic, and sole-transition service seams without drawing footwear.",
    "right_boot": "Lower terminal contact-shell zones need toe-roll material bands, heel-stabilizer logic, and sole-transition service seams without drawing footwear.",
    "left_hand": "Manipulator guard-shell zones need dorsal shield material, knuckle lane hints, and wrist docking continuity without drawing a glove or fingers.",
    "right_hand": "Manipulator guard-shell zones need dorsal shield material, knuckle lane hints, and wrist docking continuity without drawing a glove or fingers.",
}


def uv_safe_module_descriptor(part: str) -> str:
    return UV_SAFE_MODULE_DESCRIPTORS.get(part, f"{part} UV surface group")


def uv_safe_part_function(part: str) -> str:
    return UV_SAFE_PART_FUNCTIONS.get(part, describe_part_function(part))


def uv_subject_guard(part: str) -> str:
    subject = UV_OBJECT_SUBJECT_TERMS.get(part, "armor object")
    return (
        f"The mesh key '{part}' is a routing key and UV address only, not the subject of an illustration. "
        f"Do not render a recognizable {subject}; produce only its flat material atlas.\n"
    )


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


def _armor_design_team_text(armor_design_team: dict[str, Any] | None) -> str:
    if not armor_design_team:
        return ""
    review_sequence = armor_design_team.get("review_sequence") or []
    hard_rejects = armor_design_team.get("hard_rejects") or []
    lines = [
        "Armor design team review:",
        f"- Team seed: {armor_design_team.get('team_seed', 'unknown')}",
        f"- Operating rule: {armor_design_team.get('operating_rule', '')}",
    ]
    if review_sequence:
        sequence_text = ", ".join(str(role) for role in review_sequence if str(role).strip())
        if sequence_text:
            lines.append(f"- Review sequence: {sequence_text}")
    if hard_rejects:
        reject_text = "; ".join(str(item) for item in hard_rejects if str(item).strip())
        if reject_text:
            lines.append(f"- Team hard rejects: {reject_text}")
    for role in armor_design_team.get("roles") or []:
        if not isinstance(role, dict):
            continue
        title = role.get("title") or role.get("key") or "Role"
        responsibility = role.get("responsibility") or ""
        directive = role.get("directive") or ""
        lines.append(f"- {title}: {responsibility} Directive: {directive}")
    return "\n".join(lines) + "\n"


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
    armor_design_team: dict[str, Any] | None = None,
) -> str:
    modules = suitspec.get("modules", {})
    module = modules.get(part, {})
    if not isinstance(module, dict):
        module = {}

    hint = PART_PROMPT_HINTS.get(part, f"{part} armor part")
    style_text = _base_style_text(suitspec, style_variation=style_variation)
    design_dna_text = _design_dna_text(suitspec)
    lore_text = _lore_design_text()
    user_profile_text = _user_armor_profile_text(user_armor_profile)
    team_text = _armor_design_team_text(armor_design_team)
    module_override_text = _module_override_text(module)
    part_role_text = _part_role_text(part)
    three_view_text = _three_view_text(part)
    variation_text = _style_variation_text(style_variation)
    brief_text = _generation_brief_text(generation_brief)
    if texture_mode == "mesh_uv":
        uv_hint = _uv_layout_hint(part)
        uv_contract_text = _uv_contract_text(suitspec, part)
        safe_descriptor = uv_safe_module_descriptor(part)
        safe_function = uv_safe_part_function(part)
        subject_guard = uv_subject_guard(part)
        return (
            "Generate a UV-ready texture atlas for one armor module.\n"
            f"Mesh routing key: {part}. UV subject descriptor: {safe_descriptor}.\n"
            f"{subject_guard}"
            f"{style_text}\n"
            f"{design_dna_text}"
            f"{lore_text}\n"
            f"{user_profile_text}"
            f"{team_text}"
            f"Mechanical role in UV-safe wording:\n- {safe_function}\n"
            f"{three_view_text}"
            f"{module_override_text}"
            f"{variation_text}"
            f"{brief_text}"
            f"{uv_contract_text}"
            "Output format requirements:\n"
            "- When a reference image is provided, treat it as the UV engineering guide and obey its island layout authority.\n"
            "- Reference A may be grayscale or color-coded, but its tones, fills, wire lines, centerline, motif box, and seam borders are construction annotations only.\n"
            "- Do NOT copy Reference A tones, guide colors, wireframe strokes, grid lines, centerline, motif box, labels, or annotation marks into the final texture.\n"
            "- Do NOT draw the assembled armor module as a 3D object. Paint material only inside the UV island topology.\n"
            "- The entire square is a texture canvas. No studio background, no object silhouette, no cast shadow, no perspective camera.\n"
            f"{UV_ATLAS_FAILURE_GUARD}"
            "- Think like an orthographic three-view sheet translated into UV islands, not like a hero render painted onto a square.\n"
            "- Place paint breaks, emissives, and panel seams according to normal-facing zones and fold cues. Do not fight the indicated surface direction.\n"
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
        f"{design_dna_text}"
        f"{lore_text}\n"
        f"{user_profile_text}"
        f"{team_text}"
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
    armor_design_team: dict[str, Any] | None = None,
) -> str:
    hint = PART_PROMPT_HINTS.get(part, f"{part} armor part")
    style_text = _base_style_text(suitspec, style_variation=style_variation)
    design_dna_text = _design_dna_text(suitspec)
    lore_text = _lore_design_text()
    uv_hint = _uv_layout_hint(part)
    uv_contract_text = _uv_contract_text(suitspec, part)
    module_override_text = _module_override_text(suitspec.get("modules", {}).get(part, {}))
    part_role_text = _part_role_text(part)
    three_view_text = _three_view_text(part)
    user_profile_text = _user_armor_profile_text(user_armor_profile)
    team_text = _armor_design_team_text(armor_design_team)
    variation_text = _style_variation_text(style_variation)
    brief_text = _generation_brief_text(generation_brief)
    safe_descriptor = uv_safe_module_descriptor(part)
    safe_function = uv_safe_part_function(part)
    subject_guard = uv_subject_guard(part)
    return (
        "You are given a reference concept image for one armor module.\n"
        f"Mesh routing key: {part}. UV subject descriptor: {safe_descriptor}.\n"
        f"{subject_guard}"
        f"{style_text}\n"
        f"{design_dna_text}"
        f"{lore_text}\n"
        f"{user_profile_text}"
        f"{team_text}"
        f"Mechanical role in UV-safe wording:\n- {safe_function}\n"
        f"{three_view_text}"
        f"{module_override_text}"
        f"{variation_text}"
        f"{brief_text}"
        f"{uv_contract_text}"
        "Task:\n"
        "- Reference A = UV engineering guide. It controls island placement, seam-safe borders, centerline, and motif zones.\n"
        "- Reference A tones, fills, wire lines, centerline, motif box, and seam borders are construction annotations only. Do NOT copy them into the final texture.\n"
        "- Reference B = style concept. It controls surface language, material rhythm, and motif character.\n"
        "- Convert the reference visual language into a UV-ready flat texture sheet.\n"
        "- Do NOT draw the assembled armor module as a 3D object. Paint material only inside the UV island topology.\n"
        "- The entire square is a texture canvas. No studio background, no object silhouette, no cast shadow, no perspective camera.\n"
        f"{UV_ATLAS_FAILURE_GUARD}"
        "- Use fold/crease cues as places for believable plate bends, material breaks, or controlled hard-surface transitions.\n"
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
    armor_design_team: dict[str, Any] | None = None,
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
            armor_design_team=armor_design_team,
        )
    return prompts
