"""Deterministic armor design team directives.

This is not a runtime multi-agent orchestration layer. It compiles the same
operator and emotion state into stable role-specific critiques that are then
inserted into image prompts and summaries.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any


TEAM_VERSION = "armor-design-team-v2"


@dataclass(frozen=True, slots=True)
class ArmorDesignRole:
    key: str
    title: str
    responsibility: str
    directive: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _team_seed(user_armor_profile: dict[str, Any] | None, style_variation: dict[str, Any] | None) -> str:
    identity = _text((user_armor_profile or {}).get("identity_seed"))
    variation = _text((style_variation or {}).get("variation_seed"))
    material = f"{TEAM_VERSION}|{identity}|{variation}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _user(value: dict[str, Any] | None, key: str, fallback: str = "") -> str:
    return _text((value or {}).get(key)) or fallback


def compile_armor_design_team(
    *,
    user_armor_profile: dict[str, Any] | None = None,
    style_variation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile deterministic role directives for the armor generation prompt."""

    protect = _user(user_armor_profile, "protect_signature", "operator protection oath")
    temperament = _user(user_armor_profile, "temperament_signature", "disciplined operator temperament")
    palette = _user(user_armor_profile, "palette_family", "canon-safe issued palette")
    finish = _user(user_armor_profile, "finish_family", "serviceable armor finish")
    motif = _user(user_armor_profile, "motif_family", "manufacturing-derived motif")
    silhouette = _user(user_armor_profile, "silhouette_family", "serviceable armor silhouette")
    emissive = _user(user_armor_profile, "emissive_family", "disciplined diagnostic emissive")
    tri_view = _user(user_armor_profile, "tri_view_family", "front-side-rear continuity")
    panel_density = _user(user_armor_profile, "panel_density_family", "controlled service panel density")
    current_emissive = _user(style_variation, "emissive_guidance", "only modulate current-run intensity")
    current_finish = _user(style_variation, "finish_guidance", "keep the permanent surface language intact")

    roles = [
        ArmorDesignRole(
            key="lore_architect",
            title="Lore architect",
            responsibility="Canon continuity, operating doctrine, and why this armor exists.",
            directive=(
                "Reject decorative noise. Every visible choice must be explainable as doctrine, oath, maintenance, "
                "power routing, identification, rescue, inspection, or survivability."
            ),
        ),
        ArmorDesignRole(
            key="operator_oath_keeper",
            title="Operator oath keeper",
            responsibility="Permanent user identity, protected target, temperament, and current emotional override limits.",
            directive=(
                f"Preserve {protect} and {temperament}. Current emotion may raise urgency, glow, wear, or alert state, "
                "but it must not overwrite the operator's permanent production lineage."
            ),
        ),
        ArmorDesignRole(
            key="armor_smith",
            title="Armor smith",
            responsibility="Plate engineering, load paths, actuator clearance, and dock-build realism.",
            directive=(
                f"Build with {silhouette}, {panel_density}, and load-bearing panel breaks. "
                "Fold lines should read as formed metal or composite bends, not random graphic stripes."
            ),
        ),
        ArmorDesignRole(
            key="dock_chief",
            title="Dock chief",
            responsibility="Assembly sequence, service hatches, fasteners, replacement paths, and hangar-ready realism.",
            directive=(
                "Design every module as something a dock arm could lift, align, lock, release, inspect, and replace. "
                "Add calm fastening logic before adding visual flourish."
            ),
        ),
        ArmorDesignRole(
            key="atlas_compositor",
            title="Atlas compositor",
            responsibility="Flat UV atlas composition, topology occupancy, edge quieting, and non-object output discipline.",
            directive=(
                "Compose paint as a continuous material atlas, not a concept object. No blank studio field, no floating part, "
                "no product shot; topology occupancy decides where detail can live."
            ),
        ),
        ArmorDesignRole(
            key="uv_engineer",
            title="UV engineer",
            responsibility="UV island authority, normal-map cues, fold marks, seam safety, and wrap continuity.",
            directive=(
                "Obey the UV guide as the engineering source of truth. Treat topology mask, normal direction, crease logic, "
                "boundary seams, and motif zones as constraints rather than optional decoration."
            ),
        ),
        ArmorDesignRole(
            key="material_director",
            title="Material director",
            responsibility="Palette, finish, emissive routing, and material hierarchy.",
            directive=(
                f"Preserve {palette}, {finish}, {motif}, and {emissive}. Current-run finish modulation: {current_finish}. "
                f"Current-run emissive modulation: {current_emissive}."
            ),
        ),
        ArmorDesignRole(
            key="transformation_choreographer",
            title="Transformation choreographer",
            responsibility="Module-cascade readability, attachment direction, and live assembly silhouette.",
            directive=(
                "Make each part read as a weaponized module that can arrive in sequence and lock onto the body. "
                "The transformation can feel heroic, but every motion implication must still be mechanically dockable."
            ),
        ),
        ArmorDesignRole(
            key="model_inspector",
            title="Model inspector",
            responsibility="Front, side, rear, and seam-adjacent readability after texture application.",
            directive=(
                f"Enforce {tri_view}. The texture must still make sense after being wrapped onto the part: "
                "front identity, side construction, rear service logic, and calm seam returns."
            ),
        ),
        ArmorDesignRole(
            key="reject_gatekeeper",
            title="Reject gatekeeper",
            responsibility="Hard failure detection before an image is accepted as usable armor texture.",
            directive=(
                "Reject object concept sheets, visible guide artifacts, unreadable text blocks, blank backgrounds, "
                "perspective renders, and any design that cannot wrap as the same engineered module."
            ),
        ),
    ]

    return {
        "team_version": TEAM_VERSION,
        "team_seed": _team_seed(user_armor_profile, style_variation),
        "operating_rule": (
            "The team reviews one armor lineage through many disciplines. Lore rules outrank user taste, user armor DNA "
            "outranks current emotion, UV topology outranks composition instinct, and current emotion may only modulate "
            "intensity, wear, and activation state."
        ),
        "review_sequence": [role.key for role in roles],
        "hard_rejects": [
            "standalone armor object, product shot, or concept sheet on plain background",
            "visible UV guide, mask, wire, centerline, calibration mark, label, letter, number, or QR-like block",
            "large unpainted canvas region instead of continuous armor material",
            "perspective lighting, cast shadow, mannequin framing, or camera-view render",
            "front-only decoration with no side, rear, seam, maintenance, or load-path logic",
            "current emotion overriding permanent user armor DNA or lore doctrine",
        ],
        "roles": [asdict(role) for role in roles],
    }


__all__ = ["TEAM_VERSION", "compile_armor_design_team"]
