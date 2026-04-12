"""Compile operator-facing profile choices into a stable armor identity."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OperatorProfile:
    protect_archetype: str = "citizens"
    temperament_bias: str = "calm"
    color_mood: str = "industrial_gray"
    note: str = ""


@dataclass(frozen=True, slots=True)
class UserArmorProfile:
    identity_seed: str
    protect_signature: str
    temperament_signature: str
    palette_family: str
    finish_family: str
    motif_family: str
    panel_density_family: str
    silhouette_family: str
    emissive_family: str
    tri_view_family: str
    palette_guidance: str
    finish_guidance: str
    motif_guidance: str
    panel_density_guidance: str
    silhouette_guidance: str
    emissive_guidance: str
    tri_view_guidance: str
    continuity_rule: str


PROTECT_RULES: dict[str, dict[str, str]] = {
    "one_person": {
        "label": "One person",
        "signature": "The armor protects one irreplaceable life with intimate precision and close-range certainty.",
        "motif_family": "Personal guard crest",
        "motif_guidance": "Use intimate guard motifs, close-protection framing, and front surfaces that read like a vow made specific.",
        "tri_view_family": "Close-guard orthographic logic",
        "tri_view_guidance": "Front view should carry the intimate promise, side view should show close-body protection logic, and rear view should keep private service seams deliberate and quiet.",
        "silhouette_family": "Close guard silhouette",
        "silhouette_guidance": "Keep the silhouette compact, protective, and close to the body rather than parade-broad.",
    },
    "companions": {
        "label": "Companions",
        "signature": "The armor reads as interoperable equipment built to survive with a squad instead of above one.",
        "motif_family": "Relay unit geometry",
        "motif_guidance": "Use relay motifs, repeated hardpoint rhythms, and paired surfaces that imply cooperation and mutual support.",
        "tri_view_family": "Squad-readable three-view logic",
        "tri_view_guidance": "All views should reinforce unit-family continuity, shared service logic, and hardware that would look correct alongside allied suits.",
        "silhouette_family": "Unit-cohesive silhouette",
        "silhouette_guidance": "Keep the silhouette cooperative and modular rather than singularly exotic.",
    },
    "citizens": {
        "label": "Citizens",
        "signature": "The armor reads as a public-facing shield platform built to stand visibly between danger and civilians.",
        "motif_family": "Civic shield geometry",
        "motif_guidance": "Use civic guard motifs, sternum certainty, and forward faces that read as reassuring, lawful, and impact-ready.",
        "tri_view_family": "Public-defense three-view logic",
        "tri_view_guidance": "Front view must establish protection-first identity, side view must explain impact routing, and rear view must still look like maintained civic hardware.",
        "silhouette_family": "Public shield silhouette",
        "silhouette_guidance": "Keep the silhouette broad, trustworthy, and legible from a distance in public space.",
    },
    "truth": {
        "label": "Truth",
        "signature": "The armor reads as an investigator's machine: disciplined, evidentiary, and impossible to mistake for chaos.",
        "motif_family": "Audit spine geometry",
        "motif_guidance": "Use audit-strip motifs, inspection bands, and precise centerline marks that read like traceable institutional hardware.",
        "tri_view_family": "Inspection-led three-view logic",
        "tri_view_guidance": "Each view must preserve evidentiary clarity, inspection access, and institutional discipline instead of raw heroics.",
        "silhouette_family": "Investigative silhouette",
        "silhouette_guidance": "Keep the silhouette clean, inspecting, and regulator-stable rather than theatrical.",
    },
    "future": {
        "label": "Future",
        "signature": "The armor reads as a rescue-capable system built to preserve continuity, evacuation, and the next generation.",
        "motif_family": "Beacon rescue geometry",
        "motif_guidance": "Use rescue-beacon motifs, clear chest readability, and guidance surfaces that imply navigation through crisis.",
        "tri_view_family": "Rescue-forward three-view logic",
        "tri_view_guidance": "Front view should beacon, side view should explain recovery hardware, and rear view should preserve continuity and evacuation utility.",
        "silhouette_family": "Rescue-forward silhouette",
        "silhouette_guidance": "Keep the silhouette open, encouraging, and visibly capable under crisis conditions.",
    },
    "legacy": {
        "label": "Legacy",
        "signature": "The armor reads as a lineage machine carrying inherited duty, with ceremony stripped down into function.",
        "motif_family": "Lineage hardpoint geometry",
        "motif_guidance": "Use inheritance motifs sparingly: repeated heirloom lines, disciplined insignia zones, and hard surfaces that feel passed down but field-usable.",
        "tri_view_family": "Lineage-maintained three-view logic",
        "tri_view_guidance": "All views must preserve continuity of lineage hardware while remaining serviceable and present-day believable.",
        "silhouette_family": "Lineage silhouette",
        "silhouette_guidance": "Keep the silhouette dignified, centered, and historically grounded without slipping into ceremonial excess.",
    },
}


TEMPERAMENT_RULES: dict[str, dict[str, str]] = {
    "calm": {
        "label": "Calm",
        "signature": "The armor stays measured, clean, and pressure-stable even under extreme load.",
        "finish_family": "Calm ceramic matte",
        "finish_guidance": "Favor matte ceramic shell breaks, disciplined sheen, and stable surface separation over dramatic gloss.",
        "panel_density_family": "Measured service spacing",
        "panel_density_guidance": "Keep panel density medium and rational, with wide breathing space between major seams.",
        "silhouette_family": "Measured massing",
        "silhouette_guidance": "Keep transitions settled and deliberate, avoiding fidgety or twitch-like protrusions.",
    },
    "straight": {
        "label": "Straight",
        "signature": "The armor commits forward with blunt clarity and minimal hesitation in its forms.",
        "finish_family": "Direct strike finish",
        "finish_guidance": "Favor straight-edged, purposeful finishes with clear wear on impact-leading surfaces.",
        "panel_density_family": "Forward-biased panel spacing",
        "panel_density_guidance": "Bias density toward strike faces and forward planes while keeping the rest clean.",
        "silhouette_family": "Direct force silhouette",
        "silhouette_guidance": "Use strong forward vectors and simple decisive masses rather than intricate layered nuance.",
    },
    "fierce": {
        "label": "Fierce",
        "signature": "The armor compresses power into bold forward faces while remaining governed and usable.",
        "finish_family": "Heat-hardened assault finish",
        "finish_guidance": "Favor heat-treated surfaces, strike-worn edges, and compressed high-tension finishing at combat faces.",
        "panel_density_family": "High-tension density",
        "panel_density_guidance": "Concentrate denser seams and relief around weaponside or strike zones only; keep calm margins elsewhere.",
        "silhouette_family": "Compressed assault silhouette",
        "silhouette_guidance": "Use compressed aggression and hard momentum without turning feral or monster-like.",
    },
    "gentle": {
        "label": "Gentle",
        "signature": "The armor reads as protective and humane without losing industrial authority.",
        "finish_family": "Rescue-stable finish",
        "finish_guidance": "Favor clean, humane material breaks, soft-value contrast, and surfaces that still feel service-grade and durable.",
        "panel_density_family": "Calm rescue spacing",
        "panel_density_guidance": "Keep panel seams broad, readable, and reassuring, with complexity limited to true function zones.",
        "silhouette_family": "Humane shield silhouette",
        "silhouette_guidance": "Let the silhouette feel approachable and protective without becoming soft or toy-like.",
    },
    "stoic": {
        "label": "Stoic",
        "signature": "The armor carries pressure in silence, with minimal flourish and maximum inevitability.",
        "finish_family": "Austere field finish",
        "finish_guidance": "Favor austere, low-gloss field finishes and restrained wear placed only where function justifies it.",
        "panel_density_family": "Sparse austere spacing",
        "panel_density_guidance": "Keep panel density sparse and severe, relying on a few precise seams rather than many decorative cuts.",
        "silhouette_family": "Austere centerline silhouette",
        "silhouette_guidance": "Keep the silhouette hard, quiet, and centerline-driven.",
    },
    "noble": {
        "label": "Noble",
        "signature": "The armor reads as dignified public duty translated into precise industrial function.",
        "finish_family": "Ceremonial-service finish",
        "finish_guidance": "Favor clean, premium service finishes with slightly elevated contrast at authoritative front faces, never ornament for ornament's sake.",
        "panel_density_family": "Dignified service spacing",
        "panel_density_guidance": "Use medium-sparse paneling with immaculate seam order and clear hierarchy between primary and secondary cuts.",
        "silhouette_family": "Dignified guard silhouette",
        "silhouette_guidance": "Keep the silhouette elevated and upright without aristocratic bloat.",
    },
}


COLOR_RULES: dict[str, dict[str, str]] = {
    "clear_white": {
        "label": "Clear white",
        "palette_family": "Rescue ceramic white",
        "palette_guidance": "Use clear ceramic white or off-white shell plates, cool gray substructure, and only restrained hazard accents at latches or emergency controls.",
        "emissive_family": "Clean guidance emissive",
        "emissive_guidance": "Use clean blue-white or ice-cyan guidance light with strict routing discipline.",
    },
    "midnight_blue": {
        "label": "Midnight blue",
        "palette_family": "Midnight shield blue",
        "palette_guidance": "Use midnight blue or graphite-blue shell masses with pale maintenance secondaries and reserve bright accents for diagnostics only.",
        "emissive_family": "Deep patrol emissive",
        "emissive_guidance": "Use cool cyan or pale electric blue diagnostics that stay thin and exact.",
    },
    "industrial_gray": {
        "label": "Industrial gray",
        "palette_family": "Orbital audit gray",
        "palette_guidance": "Use disciplined industrial gray, maintenance white, and sparse warning accents for a dock-authentic issued-machine look.",
        "emissive_family": "Audit diagnostic emissive",
        "emissive_guidance": "Use sparse institutional diagnostics in blue, amber, or white, never broad hero glow.",
    },
    "abyssal_teal": {
        "label": "Abyssal teal",
        "palette_family": "Abyssal teal patrol",
        "palette_guidance": "Use blue-black or sea-dark plates with muted teal and sea-glass secondaries suited for low-visibility high-pressure deployment.",
        "emissive_family": "Submerged guidance emissive",
        "emissive_guidance": "Use low-saturation teal guidance strips and pressure-safe diagnostics instead of bright theatrical light.",
    },
    "burnt_red": {
        "label": "Burnt red",
        "palette_family": "Heat breach red",
        "palette_guidance": "Use charred graphite with controlled burnt-red or warning-red accents on strike faces, heat reliefs, and emergency releases only.",
        "emissive_family": "Overload channel emissive",
        "emissive_guidance": "Use restrained ember or overload-channel light without washing the whole suit in red.",
    },
    "signal_amber": {
        "label": "Signal amber",
        "palette_family": "Signal amber service",
        "palette_guidance": "Use disciplined gray or white hardware with amber signal markings and rescue-service visibility where it aids recognition.",
        "emissive_family": "Signal relay emissive",
        "emissive_guidance": "Use amber relay or status lights with strict placement and repeatable rhythm.",
    },
}


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _sanitize_operator_profile(payload: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    raw: dict[str, str] = {}
    for key in ("protect_archetype", "temperament_bias", "color_mood", "note"):
        value = _normalized_text(payload.get(key))
        if value:
            raw[key] = value
    return raw or None


def _merge_raw_profiles(base: dict[str, str] | None, override: dict[str, str] | None) -> dict[str, str] | None:
    if base is None and override is None:
        return None
    merged: dict[str, str] = {}
    if base:
        merged.update(base)
    if override:
        merged.update(override)
    return merged


def _digest_seed(profile: OperatorProfile) -> str:
    material = "|".join(
        [
            profile.protect_archetype,
            profile.temperament_bias,
            profile.color_mood,
            profile.note,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def resolve_operator_profile(
    stored_payload: dict[str, Any] | None,
    override_payload: dict[str, Any] | None = None,
) -> tuple[OperatorProfile | None, dict[str, str] | None, dict[str, str]]:
    stored_raw = _sanitize_operator_profile(stored_payload)
    override_raw = _sanitize_operator_profile(override_payload)
    raw = _merge_raw_profiles(stored_raw, override_raw)
    if raw is None:
        return None, None, {}

    resolved_defaults: dict[str, str] = {}

    protect = raw.get("protect_archetype", "citizens")
    if protect not in PROTECT_RULES:
        protect = "citizens"
    if "protect_archetype" not in raw:
        resolved_defaults["protect_archetype"] = protect

    temperament = raw.get("temperament_bias", "calm")
    if temperament not in TEMPERAMENT_RULES:
        temperament = "calm"
    if "temperament_bias" not in raw:
        resolved_defaults["temperament_bias"] = temperament

    color_mood = raw.get("color_mood", "industrial_gray")
    if color_mood not in COLOR_RULES:
        color_mood = "industrial_gray"
    if "color_mood" not in raw:
        resolved_defaults["color_mood"] = color_mood

    profile = OperatorProfile(
        protect_archetype=protect,
        temperament_bias=temperament,
        color_mood=color_mood,
        note=raw.get("note", ""),
    )
    return profile, raw, resolved_defaults


def serialize_operator_profile(profile: OperatorProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    payload = asdict(profile)
    payload["protect_archetype_label"] = PROTECT_RULES[profile.protect_archetype]["label"]
    payload["temperament_bias_label"] = TEMPERAMENT_RULES[profile.temperament_bias]["label"]
    payload["color_mood_label"] = COLOR_RULES[profile.color_mood]["label"]
    return payload


def build_user_armor_profile(profile: OperatorProfile) -> UserArmorProfile:
    protect = PROTECT_RULES[profile.protect_archetype]
    temperament = TEMPERAMENT_RULES[profile.temperament_bias]
    color = COLOR_RULES[profile.color_mood]
    digest = _digest_seed(profile)
    return UserArmorProfile(
        identity_seed=digest[:12],
        protect_signature=protect["signature"],
        temperament_signature=temperament["signature"],
        palette_family=color["palette_family"],
        finish_family=temperament["finish_family"],
        motif_family=protect["motif_family"],
        panel_density_family=temperament["panel_density_family"],
        silhouette_family=f"{protect['silhouette_family']} / {temperament['silhouette_family']}",
        emissive_family=color["emissive_family"],
        tri_view_family=protect["tri_view_family"],
        palette_guidance=color["palette_guidance"],
        finish_guidance=temperament["finish_guidance"],
        motif_guidance=protect["motif_guidance"],
        panel_density_guidance=temperament["panel_density_guidance"],
        silhouette_guidance=f"{protect['silhouette_guidance']} {temperament['silhouette_guidance']}",
        emissive_guidance=color["emissive_guidance"],
        tri_view_guidance=protect["tri_view_guidance"],
        continuity_rule=(
            "Same user, same production lineage, same personal armor identity across every module and every run."
        ),
    )


def serialize_user_armor_profile(profile: UserArmorProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return asdict(profile)


def compile_operator_profile(
    stored_payload: dict[str, Any] | None,
    override_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile, raw_profile, resolved_defaults = resolve_operator_profile(stored_payload, override_payload)
    if profile is None:
        return {
            "operator_profile": None,
            "operator_profile_raw": None,
            "operator_profile_resolved": None,
            "resolved_defaults": {},
            "user_armor_profile": None,
        }

    resolved_profile = serialize_operator_profile(profile)
    return {
        "operator_profile": resolved_profile,
        "operator_profile_raw": raw_profile,
        "operator_profile_resolved": resolved_profile,
        "resolved_defaults": resolved_defaults,
        "user_armor_profile": serialize_user_armor_profile(build_user_armor_profile(profile)),
    }
