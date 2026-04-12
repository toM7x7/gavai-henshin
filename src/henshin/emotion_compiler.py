"""Compile transient emotion input into run-specific armor modulation."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EmotionProfile:
    drive: str = "protect"
    protect_target: str = ""
    scene: str = "urban_night"
    vow: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class EmotionDirectiveSet:
    drive_label: str
    mission_profile: str
    design_translation: str
    restraint_policy: str
    hero_signal: str
    default_vow: str
    finish_shift: str
    emissive_shift: str
    accent_shift: str


@dataclass(frozen=True, slots=True)
class StyleVariationProfile:
    variation_seed: str
    palette_family: str
    palette_guidance: str
    finish_guidance: str
    emissive_guidance: str
    motif_guidance: str
    panel_guidance: str
    silhouette_guidance: str
    tri_view_guidance: str


DRIVE_RULES: dict[str, EmotionDirectiveSet] = {
    "protect": EmotionDirectiveSet(
        drive_label="Protect",
        mission_profile="Interception, shielding, and civilian-first protection under visible threat.",
        design_translation=(
            "Bias the run toward sternum certainty, shield-like chest confidence, calm visor geometry, and dependable forearm protection."
        ),
        restraint_policy="Avoid cruelty, berserk spikes, and villain-coded aggression. The force is protective, not sadistic.",
        hero_signal="A lawful metal-hero ignition driven by the need to stand between danger and the people behind the wearer.",
        default_vow="No one gets through.",
        finish_shift="Keep surfaces stable and dependable. Stress can appear, but the suit must still look like protective equipment.",
        emissive_shift="Lift reassurance and target-legibility cues slightly, especially around visor, sternum, and shield-adjacent diagnostics.",
        accent_shift="Allow hazard accents only where they improve public readability and defensive intent.",
    ),
    "duty": EmotionDirectiveSet(
        drive_label="Duty",
        mission_profile="Lawful patrol, repeatable deployment, and accountable response under command pressure.",
        design_translation=(
            "Bias the run toward inspection hatches, ordered panel rhythm, and institutionally disciplined centerline control."
        ),
        restraint_policy="Avoid vanity styling, aristocratic decoration, and chaotic asymmetry.",
        hero_signal="A metal-hero transformation powered by oath, repeatability, and refusal to abandon assigned duty.",
        default_vow="I hold the line.",
        finish_shift="Keep finishing crisp, audited, and inspection-ready instead of expressive.",
        emissive_shift="Reduce theatrical glow and push diagnostic clarity, alignment lights, and audit-like readouts.",
        accent_shift="Use warning or authority accents only where regulation logic would justify them.",
    ),
    "rage": EmotionDirectiveSet(
        drive_label="Rage",
        mission_profile="Pursuit, breach, and hard interception against a superior threat while preserving command judgment.",
        design_translation=(
            "Bias the run toward reinforced gauntlets, compressed tension in the shoulders, harder strike faces, and heat-relief logic."
        ),
        restraint_policy="The anger must remain governed. Avoid monster coding, gore cues, feral teeth shapes, and demonic ornament.",
        hero_signal="A burning but disciplined metal-hero ignition: wrath converted into lawful force instead of loss of control.",
        default_vow="This anger answers to me.",
        finish_shift="Increase strike-face wear and thermal stress slightly, but keep the rest of the shell controlled.",
        emissive_shift="Concentrate pressure in narrow heat-relief or overload channels, never broad neon wash.",
        accent_shift="Allow warning-red or heat accents only on strike zones, vents, and emergency release logic.",
    ),
    "hope": EmotionDirectiveSet(
        drive_label="Hope",
        mission_profile="Recovery, rally support, navigation through darkness, and morale restoration under pressure.",
        design_translation=(
            "Bias the run toward clearer chest readability, cleaner visor confidence, and rescue-friendly module clarity."
        ),
        restraint_policy="Avoid toy-like color chaos, mystical softness, or decorative glow without operational purpose.",
        hero_signal="A luminous metal-hero activation that turns fear into forward motion for everyone nearby.",
        default_vow="I will light the way.",
        finish_shift="Keep surfaces bright enough to read in crisis, but still industrial and service-grade.",
        emissive_shift="Open guidance lines and morale-lighting slightly while keeping routing precise and useful.",
        accent_shift="Permit a little more rescue-readability in accents, but keep the manufacturing family intact.",
    ),
    "bond": EmotionDirectiveSet(
        drive_label="Bond",
        mission_profile="Coordinated team action, relay support, and survivability for the whole unit rather than solo dominance.",
        design_translation=(
            "Bias the run toward relay seams, anchor points, interoperable modules, and visibly shared unit logic."
        ),
        restraint_policy="Avoid lone-wolf vanity, isolated-ace styling, and ceremonial excess detached from the team.",
        hero_signal="A transformation charged by shared resolve: the armor carries comrades, signals trust, and never reads as solitary ego.",
        default_vow="No one stands alone.",
        finish_shift="Keep maintenance and service continuity especially clear across neighboring modules.",
        emissive_shift="Favor repeatable relay rhythms, formation cues, and cooperative diagnostics over singular hero glow.",
        accent_shift="Use unit-like markings and paired accent placement, not a singular signature flourish.",
    ),
    "resolve": EmotionDirectiveSet(
        drive_label="Resolve",
        mission_profile="Last-line commitment, decisive forward action, and unbroken posture under terminal pressure.",
        design_translation=(
            "Bias the run toward locked centerline geometry, stripped-down purpose, and a severe but precise posture."
        ),
        restraint_policy="Avoid melodramatic chaos, ornamental tragedy, and random damage everywhere. Resolve is precision, not collapse.",
        hero_signal="A hard, silent metal-hero ignition: the instant a human decision crystallizes into irreversible action.",
        default_vow="I go forward.",
        finish_shift="Reduce ornamental nuance and leave only the essential load-bearing and mission-critical emphasis.",
        emissive_shift="Compress emissives toward life-systems, visor certainty, and core-state declaration.",
        accent_shift="Keep accents sparse and severe. A little goes a long way.",
    ),
}


SCENE_RULES: dict[str, dict[str, str]] = {
    "urban_night": {
        "label": "Urban night",
        "environment": "Rain-slick patrol lanes, reflective hazard light, and public-facing readability in dense city space.",
        "material": "Use controlled grime, edge wear, and reflective cues appropriate for dense city deployment without cluttering the texture.",
    },
    "orbit_patrol": {
        "label": "Orbital patrol",
        "environment": "Vacuum-rated sealing, thermal cycling, and hard serviceability in dock-maintenance conditions.",
        "material": "Favor seal lines, pressure-stable panel logic, tether-ready hardpoints, and crisp high-contrast material breaks.",
    },
    "disaster_zone": {
        "label": "Disaster zone",
        "environment": "Smoke, debris, emergency extraction, and rapid triage in unstable civic infrastructure.",
        "material": "Favor rescue-grade visibility, ruggedized edges, and impact wear concentrated around access and extraction surfaces.",
    },
    "deep_sea": {
        "label": "Deep sea",
        "environment": "High-pressure operations with corrosion control, low visibility, and sealed maintenance logic.",
        "material": "Favor gasket lines, corrosion-resistant surfacing, pressure-clamp logic, and subdued emissive guidance.",
    },
    "wasteland": {
        "label": "Wasteland",
        "environment": "Abrasive particulate exposure, heat differential, long-range patrol, and field-repair necessity.",
        "material": "Favor dust-polished edges, robust seals, modular replacement logic, and minimal fragile detailing.",
    },
    "dark_void": {
        "label": "Dark void",
        "environment": "Low-visibility hostile space where silhouette clarity and orientation cues matter more than spectacle.",
        "material": "Favor disciplined luminous routing, strong centerline legibility, and calm surface hierarchy under darkness.",
    },
}


PALETTE_FAMILIES: tuple[dict[str, str], ...] = (
    {
        "palette_family": "Midnight shield",
        "palette_guidance": "Use graphite or midnight blue as the main shell, a colder pale secondary on access covers, and reserve cyan or white-blue accents for diagnostics only.",
    },
    {
        "palette_family": "Rescue signal",
        "palette_guidance": "Use pale ceramic or off-white shell plates, slate substructure, and restrained rescue red-orange accents on alert surfaces and latch zones.",
    },
    {
        "palette_family": "Orbital audit",
        "palette_guidance": "Use gunmetal and maintenance-white as the core family, then add amber inspection marks and slim blue diagnostics for institutional clarity.",
    },
    {
        "palette_family": "Abyssal patrol",
        "palette_guidance": "Use blue-black or sea-dark shell plates, muted sea-glass secondary tones, and low-saturation teal guidance lights instead of loud hero colors.",
    },
    {
        "palette_family": "Heat breach",
        "palette_guidance": "Use charred graphite and heat-treated steel with controlled ember or warning-red accents placed only on strike faces, vents, or emergency release zones.",
    },
    {
        "palette_family": "Relay unit",
        "palette_guidance": "Use titanium gray and disciplined unit-color strips, with emissive routing kept thin and regular so the parts still read as issue-standard equipment.",
    },
)


FINISH_GUIDANCES: tuple[str, ...] = (
    "Favor matte ceramic shell breaks over mirror gloss; let readability come from plane changes and service cuts.",
    "Favor brushed titanium and slightly burnished edges where maintenance contact would naturally polish the surface.",
    "Favor seal-coated composite plates with occasional satin clearcoat on high-value front faces.",
    "Favor rugged field-replacement modules with subtle finish mismatch between removable covers and main armor shell.",
)


MOTIF_GUIDANCES: tuple[str, ...] = (
    "Use split chevrons, sternum arrows, and wedge cuts to suggest forward commitment without becoming ornamental.",
    "Use stacked rib lanes and service-band segmentation so the armor feels dock-built and modular.",
    "Use arc-broken visor or chest motifs that read as sensor framing and load transfer rather than decoration.",
    "Use offset inspection bands and hardpoint rails to create identity through manufacturing logic, not decals.",
)


PANEL_GUIDANCES: tuple[str, ...] = (
    "Keep panel density medium and deliberate: major masses first, secondary seams second, micro-detail only where service access demands it.",
    "Bias toward sparse broad plates with a few assertive service cuts, so silhouette and paint blocking do most of the work.",
    "Bias toward dense but disciplined paneling around high-function zones only, with calm surrounds and wide low-frequency borders.",
)


SILHOUETTE_GUIDANCES: dict[str, tuple[str, ...]] = {
    "protect": (
        "Emphasize frontal shield faces, dependable collar lines, and a stable center of mass.",
        "Keep the profile broad and trustworthy rather than sleek or predatory.",
    ),
    "duty": (
        "Emphasize formal centerline symmetry, institutional restraint, and repeatable production geometry.",
        "Keep the profile disciplined and regulatory, not flamboyant.",
    ),
    "rage": (
        "Emphasize compressed forward angles, strike-ready gauntlet faces, and controlled aggressive taper.",
        "Keep the profile forceful without becoming feral or monstrous.",
    ),
    "hope": (
        "Emphasize open chest readability, clear visor confidence, and a silhouette that feels like a visible beacon in crisis.",
        "Keep the profile uplifting and legible, not delicate.",
    ),
    "bond": (
        "Emphasize relay mounts, unit-family shapes, and a silhouette that reads as interoperable with allied equipment.",
        "Keep the profile cooperative and modular rather than lone-ace exotic.",
    ),
    "resolve": (
        "Emphasize locked centerline geometry, stern face planes, and stripped-down commitment.",
        "Keep the profile severe and precise rather than bulky or baroque.",
    ),
}


EMISSIVE_GUIDANCES: dict[str, tuple[str, ...]] = {
    "protect": (
        "Keep emissives thin and trustworthy: visor edge, sternum guide, and shield-adjacent diagnostics only.",
        "Use light as reassurance and targeting clarity, not spectacle.",
    ),
    "duty": (
        "Keep emissives audit-like and sparse, closer to institutional diagnostics than dramatic glow.",
        "Let service status and alignment marks read before hero lighting does.",
    ),
    "rage": (
        "Keep emissives tight and pressurized near heat relief paths, strike faces, or overload channels.",
        "Avoid turning the whole suit into a neon weapon.",
    ),
    "hope": (
        "Let emissives form clean guidance lines that read through smoke and darkness without overwhelming the shell.",
        "Use light as navigation and morale, not ornament.",
    ),
    "bond": (
        "Use emissives as relay and coordination marks that would make sense in a unit formation.",
        "Favor repeated rhythm over singular hero glow.",
    ),
    "resolve": (
        "Keep emissives minimal, hard, and centered on critical life systems.",
        "Use light as a statement of irreversible commitment, not decoration.",
    ),
}


TRI_VIEW_GUIDANCES: dict[str, tuple[str, ...]] = {
    "protect": (
        "Front view should read as defense-first identity, side view should show impact routing and joint protection, rear view should show maintenance and support continuity.",
        "Do not spend all visual identity on the front face only.",
    ),
    "duty": (
        "Front, side, and rear views must look like the same issued machine, with markings and color blocking surviving orthographic inspection.",
        "Rear surfaces should never become anonymous filler.",
    ),
    "rage": (
        "Front view can carry controlled aggression, but side and rear views must still explain actuator logic, cooling, and service breaks.",
        "Do not rely on hero-shot perspective cues to sell force.",
    ),
    "hope": (
        "Front view should carry the beacon-like identity, while side and rear views preserve rescue logic, visibility control, and modular continuity.",
        "Keep all three views readable under emergency conditions.",
    ),
    "bond": (
        "Each orthographic view should reinforce squad-family commonality, relay hardpoints, and interoperable service access.",
        "Side and rear views must look like intentional unit hardware, not leftovers.",
    ),
    "resolve": (
        "All three views should reinforce a single decisive centerline and stripped-down mission logic.",
        "Avoid adding detail that only works from one dramatic angle.",
    ),
}


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _sanitize_raw_profile(payload: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    raw: dict[str, str] = {}
    for key in ("drive", "protect_target", "scene", "vow", "note"):
        value = _normalized_text(payload.get(key))
        if value:
            raw[key] = value
    return raw or None


def _seed_digest(*values: str) -> str:
    seed = "|".join(value.strip() for value in values if value and value.strip())
    return hashlib.sha256((seed or "default").encode("utf-8")).hexdigest()


def _pick(items: tuple[Any, ...], digest: str, offset: int = 0) -> Any:
    if not items:
        raise ValueError("No items available for selection.")
    start = (offset * 8) % len(digest)
    chunk = digest[start : start + 8] or digest[:8]
    return items[int(chunk, 16) % len(items)]


def _with_shift(base: str, shift: str | None) -> str:
    if not shift:
        return base
    return f"{base} {shift}".strip()


def build_style_variation(
    profile: EmotionProfile,
    *,
    extra_brief: str | None = None,
    user_armor_profile: dict[str, Any] | None = None,
) -> StyleVariationProfile:
    digest = _seed_digest(
        user_armor_profile.get("identity_seed", "") if isinstance(user_armor_profile, dict) else "",
        profile.drive,
        profile.protect_target,
        profile.scene,
        profile.vow,
        profile.note,
        extra_brief or "",
    )
    drive = DRIVE_RULES.get(profile.drive, DRIVE_RULES["protect"])

    if user_armor_profile:
        palette_family = str(user_armor_profile.get("palette_family") or "Lore-safe personal palette")
        palette_guidance = _with_shift(
            str(user_armor_profile.get("palette_guidance") or "Keep the user's production-line palette intact."),
            drive.accent_shift,
        )
        finish_guidance = _with_shift(
            str(user_armor_profile.get("finish_guidance") or "Preserve the user's surface finish family."),
            drive.finish_shift,
        )
        emissive_guidance = _with_shift(
            str(user_armor_profile.get("emissive_guidance") or "Preserve the user's emissive family."),
            drive.emissive_shift,
        )
        motif_guidance = str(user_armor_profile.get("motif_guidance") or "Preserve the user's motif family.")
        panel_guidance = str(
            user_armor_profile.get("panel_density_guidance") or "Preserve the user's panel-density family."
        )
        silhouette_guidance = str(
            user_armor_profile.get("silhouette_guidance") or "Preserve the user's silhouette family."
        )
        tri_view_guidance = _with_shift(
            str(user_armor_profile.get("tri_view_guidance") or "Preserve the user's three-view family."),
            _pick(TRI_VIEW_GUIDANCES.get(profile.drive, TRI_VIEW_GUIDANCES["protect"]), digest, 6),
        )
        return StyleVariationProfile(
            variation_seed=digest[:12],
            palette_family=palette_family,
            palette_guidance=palette_guidance,
            finish_guidance=finish_guidance,
            emissive_guidance=emissive_guidance,
            motif_guidance=motif_guidance,
            panel_guidance=panel_guidance,
            silhouette_guidance=silhouette_guidance,
            tri_view_guidance=tri_view_guidance,
        )

    palette = _pick(PALETTE_FAMILIES, digest, 0)
    finish = _pick(FINISH_GUIDANCES, digest, 1)
    motif = _pick(MOTIF_GUIDANCES, digest, 2)
    panel = _pick(PANEL_GUIDANCES, digest, 3)
    silhouette = _pick(SILHOUETTE_GUIDANCES.get(profile.drive, SILHOUETTE_GUIDANCES["protect"]), digest, 4)
    emissive = _pick(EMISSIVE_GUIDANCES.get(profile.drive, EMISSIVE_GUIDANCES["protect"]), digest, 5)
    tri_view = _pick(TRI_VIEW_GUIDANCES.get(profile.drive, TRI_VIEW_GUIDANCES["protect"]), digest, 6)
    return StyleVariationProfile(
        variation_seed=digest[:12],
        palette_family=palette["palette_family"],
        palette_guidance=_with_shift(palette["palette_guidance"], drive.accent_shift),
        finish_guidance=_with_shift(finish, drive.finish_shift),
        emissive_guidance=_with_shift(emissive, drive.emissive_shift),
        motif_guidance=motif,
        panel_guidance=panel,
        silhouette_guidance=silhouette,
        tri_view_guidance=tri_view,
    )


def resolve_emotion_profile(payload: dict[str, Any] | None) -> tuple[EmotionProfile | None, dict[str, str]]:
    raw = _sanitize_raw_profile(payload)
    if raw is None:
        return None, {}

    drive_key = raw.get("drive", "protect")
    if drive_key not in DRIVE_RULES:
        drive_key = "protect"

    scene_key = raw.get("scene", "urban_night")
    if scene_key not in SCENE_RULES:
        scene_key = "urban_night"

    resolved_defaults: dict[str, str] = {}
    if "scene" not in raw:
        resolved_defaults["scene"] = scene_key

    drive = DRIVE_RULES[drive_key]
    vow = raw.get("vow") or drive.default_vow
    if "vow" not in raw:
        resolved_defaults["vow"] = vow

    profile = EmotionProfile(
        drive=drive_key,
        protect_target=raw.get("protect_target", ""),
        scene=scene_key,
        vow=vow,
        note=raw.get("note", ""),
    )
    return profile, resolved_defaults


def serialize_emotion_profile(profile: EmotionProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    data = asdict(profile)
    data["drive_label"] = DRIVE_RULES.get(profile.drive, DRIVE_RULES["protect"]).drive_label
    data["scene_label"] = SCENE_RULES.get(profile.scene, SCENE_RULES["urban_night"])["label"]
    return data


def serialize_emotion_directives(directives: EmotionDirectiveSet, scene_key: str) -> dict[str, Any]:
    scene = SCENE_RULES.get(scene_key, SCENE_RULES["urban_night"])
    return {
        "drive_label": directives.drive_label,
        "scene_label": scene["label"],
        "mission_profile": directives.mission_profile,
        "environment_profile": scene["environment"],
        "material_translation": scene["material"],
        "design_translation": directives.design_translation,
        "restraint_policy": directives.restraint_policy,
        "hero_signal": directives.hero_signal,
        "finish_shift": directives.finish_shift,
        "emissive_shift": directives.emissive_shift,
        "accent_shift": directives.accent_shift,
    }


def serialize_style_variation(variation: StyleVariationProfile | None) -> dict[str, Any] | None:
    if variation is None:
        return None
    return asdict(variation)


def compile_emotion_request(
    emotion_profile_payload: dict[str, Any] | None,
    generation_brief: str | None = None,
    user_armor_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_profile = _sanitize_raw_profile(emotion_profile_payload)
    profile, resolved_defaults = resolve_emotion_profile(emotion_profile_payload)
    extra_brief = _normalized_text(generation_brief)

    if profile is None:
        return {
            "emotion_profile": None,
            "emotion_profile_raw": None,
            "emotion_profile_resolved": None,
            "emotion_directives": None,
            "style_variation": None,
            "resolved_defaults": {},
            "compiled_brief": extra_brief or None,
        }

    directives = DRIVE_RULES.get(profile.drive, DRIVE_RULES["protect"])
    scene = SCENE_RULES.get(profile.scene, SCENE_RULES["urban_night"])
    protect_target = profile.protect_target or "someone the wearer refuses to lose"
    variation = build_style_variation(
        profile,
        extra_brief=extra_brief,
        user_armor_profile=user_armor_profile,
    )

    compiled_lines = [
        "Current emotional modulation:",
        f"- Core emotional trigger: {directives.drive_label}",
        f"- Protect target: {protect_target}",
        f"- Operating scene: {scene['label']}",
        f"- Vow phrase: {profile.vow}",
        f"- Mission translation: {directives.mission_profile}",
        f"- Environment translation: {scene['environment']}",
        f"- Material translation: {scene['material']}",
        f"- Design translation: {directives.design_translation}",
        f"- Restraint policy: {directives.restraint_policy}",
        f"- Hero signal: {directives.hero_signal}",
        "Run-specific modulation:",
        f"- Variation seed: {variation.variation_seed}",
        f"- Palette family: {variation.palette_family}",
        f"- Palette guidance: {variation.palette_guidance}",
        f"- Finish guidance: {variation.finish_guidance}",
        f"- Emissive guidance: {variation.emissive_guidance}",
        f"- Motif guidance: {variation.motif_guidance}",
        f"- Panel guidance: {variation.panel_guidance}",
        f"- Silhouette guidance: {variation.silhouette_guidance}",
        f"- Tri-view guidance: {variation.tri_view_guidance}",
        "- Keep the result inside disciplined sci-fi canon: engineered, wearable, and modular.",
    ]
    if profile.note:
        compiled_lines.append(f"- Supplemental note: {profile.note}")
    if extra_brief:
        compiled_lines.append(f"- Additional operator note: {extra_brief}")

    resolved_profile = serialize_emotion_profile(profile)
    return {
        "emotion_profile": resolved_profile,
        "emotion_profile_raw": raw_profile,
        "emotion_profile_resolved": resolved_profile,
        "emotion_directives": serialize_emotion_directives(directives, profile.scene),
        "style_variation": serialize_style_variation(variation),
        "resolved_defaults": resolved_defaults,
        "compiled_brief": "\n".join(compiled_lines),
    }
