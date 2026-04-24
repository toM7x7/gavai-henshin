"""Prompt bench utilities for focused armor part generation experiments."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .gemini_image import extension_for_mime, save_image, write_generation_meta
from .image_providers import ImageReference, generate_image, resolve_provider_api_key
from .part_generation import GenerationRequest, resolve_provider_profile, run_generate_parts
from .part_prompts import PART_PROMPT_HINTS, uv_safe_module_descriptor, uv_safe_part_function, uv_subject_guard
from .texture_quality import evaluate_texture_output
from .uv_guides import ensure_uv_guide_image, serialize_uv_guide
from .validators import load_json


BENCH_VERSION = "armor-part-prompt-bench-v5"

DEFAULT_EMOTION_PROFILE = {
    "drive": "protect",
    "protect_target": "someone behind me",
}

DEFAULT_OPERATOR_PROFILE = {
    "protect_archetype": "one_person",
    "temperament_bias": "stoic",
    "color_mood": "midnight_blue",
}

UV_ATLAS_FAILURE_GUARD = (
    "UV atlas failure guards:\n"
    "- Cover the entire square with continuous armor material. No unpainted white or gray negative space around armor-shaped silhouettes.\n"
    "- Do not draw floating left/right plates, detachable side pods, a front-view shell, or a product-shot part on a blank canvas.\n"
    "- Do not add readable letters, numbers, QR codes, labels, maker marks, serial tags, UI text, or calibration text.\n"
    "- Do not use bevel shadows, cast shadows, or perspective shading to make the texture look like a rendered object.\n"
    "- Seam-safe margins can be low frequency, but they must still be painted as armor material.\n"
)


@dataclass(frozen=True, slots=True)
class PromptBenchVariant:
    key: str
    title: str
    intent: str
    prompt: str
    refine_prompt: str | None = None
    mode: str = "single_pass"


def _block(title: str, value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    return f"{title}:\n{text}\n"


def _profile_line(profile: dict[str, Any] | None, key: str, fallback: str = "") -> str:
    return str((profile or {}).get(key) or fallback).strip()


def _compact_user_dna(user_profile: dict[str, Any] | None) -> str:
    return "\n".join(
        [
            f"identity_seed={_profile_line(user_profile, 'identity_seed', 'unknown')}",
            f"palette={_profile_line(user_profile, 'palette_family', 'canon-safe issued palette')}: {_profile_line(user_profile, 'palette_guidance')}",
            f"motif={_profile_line(user_profile, 'motif_family', 'manufacturing motif')}: {_profile_line(user_profile, 'motif_guidance')}",
            f"finish={_profile_line(user_profile, 'finish_family', 'service finish')}: {_profile_line(user_profile, 'finish_guidance')}",
            f"emissive={_profile_line(user_profile, 'emissive_family', 'diagnostic emissive')}: {_profile_line(user_profile, 'emissive_guidance')}",
            f"tri_view={_profile_line(user_profile, 'tri_view_family', 'three-view continuity')}: {_profile_line(user_profile, 'tri_view_guidance')}",
        ]
    )


def _compact_current_state(style_variation: dict[str, Any] | None) -> str:
    return "\n".join(
        [
            f"variation_seed={_profile_line(style_variation, 'variation_seed', 'current-run')}",
            f"finish_modulation={_profile_line(style_variation, 'finish_guidance')}",
            f"emissive_modulation={_profile_line(style_variation, 'emissive_guidance')}",
            f"panel_modulation={_profile_line(style_variation, 'panel_guidance')}",
        ]
    )


def _compact_team(team: dict[str, Any] | None) -> str:
    roles = []
    operating_rule = str((team or {}).get("operating_rule") or "").strip()
    if operating_rule:
        roles.append(f"Operating rule: {operating_rule}")
    hard_rejects = (team or {}).get("hard_rejects") or []
    if hard_rejects:
        reject_text = "; ".join(str(item) for item in hard_rejects if str(item).strip())
        if reject_text:
            roles.append(f"Hard rejects: {reject_text}")
    for role in (team or {}).get("roles") or []:
        if isinstance(role, dict):
            directive = str(role.get("directive", ""))
            directive = directive.replace(
                "especially around visor, sternum, and shield-adjacent diagnostics",
                "especially around this module's primary functional face and safe diagnostic channels",
            )
            roles.append(f"{role.get('title', role.get('key', 'role'))}: {directive}")
    return "\n".join(roles)


def _uv_semantics(uv_guide: dict[str, Any] | None) -> str:
    summary = (uv_guide or {}).get("semantic_summary") or {}
    counts = summary.get("normal_semantic_counts") or {}
    if (uv_guide or {}).get("guide_profile") == "topology_mask":
        return "\n".join(
            [
                "Reference A is a mask-like UV topology field, not an art reference and not a visible blueprint.",
                "Its soft grayscale field encodes UV occupancy only; surface-facing and fold constraints are provided as text metadata below.",
                "Do not copy Reference A tones, diagonals, gradients, center traces, or any mask artifacts into the final texture.",
                "Use Reference A as invisible topology pressure: cover the full square with armor material without drawing guide geometry.",
                f"normal_semantic_counts={counts}",
                f"crease_edges={summary.get('crease_edge_count', 0)} boundary_edges={summary.get('boundary_edge_count', 0)}",
            ]
        )
    if (uv_guide or {}).get("guide_profile") == "ai_reference":
        return "\n".join(
            [
                "Reference A is the AI-safe grayscale UV engineering map, not an art reference.",
                "Its gray fills indicate UV island surface groups only; dark lines indicate hard fold, crease, or boundary authority.",
                "Do not copy Reference A grayscale values, outlines, centerline, motif box, or construction marks into the final texture.",
                "Use Reference A as invisible UV topology: paint final armor material inside the island layout instead of rendering a 3D object.",
                f"normal_semantic_counts={counts}",
                f"crease_edges={summary.get('crease_edge_count', 0)} boundary_edges={summary.get('boundary_edge_count', 0)}",
            ]
        )
    return "\n".join(
        [
            "Reference A is the UV engineering map, not an art reference.",
            "Color semantics: cyan/blue=front identity, green=rear service, purple/pink=side wrap, orange=fold/crease/hard normal break, blue-gray=UV boundary/open seam, amber=primary motif zone.",
            "Do not copy Reference A colors, wireframe strokes, grid lines, or annotation marks into the final texture. Use them as invisible construction instructions.",
            f"normal_semantic_counts={counts}",
            f"crease_edges={summary.get('crease_edge_count', 0)} boundary_edges={summary.get('boundary_edge_count', 0)}",
        ]
    )


def _part_direction_text(part: str) -> str:
    groups: dict[str, str] = {
        "helmet": (
            "Part surface task: front zones carry visor/brow identity; side zones carry sensor and comms wrap logic; rear zones carry occipital shell and service seams."
        ),
        "chest": (
            "Part surface task: front zones carry sternum core and identity plates; side zones carry rib wrap and load-transfer seams; rear-adjacent zones stay quiet for backplate continuity."
        ),
        "back": (
            "Part surface task: rear zones carry spine channel, dorsal rails, and service access; side zones carry shoulder/waist transfer logic; front-adjacent zones stay seam-safe."
        ),
        "waist": (
            "Part surface task: front zones carry abdomen guard and belt identity; side zones carry hip articulation and load transfer; rear zones carry closure and service segmentation."
        ),
        "shoulder": (
            "Part surface task: outer/front zones carry the deflection crest and identification face; side zones carry cap depth and hinge clearance; rear zones carry service seams and deflection returns."
        ),
        "arm": (
            "Part surface task: front/dorsal zones carry strike or tool identity; side zones carry cuff transitions and actuator clearance; inner/rear zones carry calm seam returns and maintenance breaks."
        ),
        "leg": (
            "Part surface task: front zones carry gait crest or strike face; side zones carry hinge and mobility logic; rear/inner zones carry quiet service seams and wrap continuity."
        ),
        "hand": (
            "Part surface task: dorsal zones carry back-of-hand shield and knuckle lanes; side zones carry finger segmentation and wrist docking; palm/inner zones stay lower frequency."
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
    return groups.get(
        part,
        "Part surface task: front, side, rear, and seam-adjacent zones must all read as one engineered armor component.",
    )


def _part_identity_rubric(part: str) -> str:
    hint = PART_PROMPT_HINTS.get(part, f"{part} modular armor component")
    return (
        f"Does the {part} texture express its mechanical role ({hint}) while staying UV-bound and not turning into a standalone object render?"
    )


def _materialize_uv_guide(
    context: dict[str, Any],
    *,
    suitspec: str,
    root: str,
    part: str,
    repo_root: Path | None,
) -> None:
    """Ensure live bench has a real Reference A image, not dry-run metadata only."""

    base = (repo_root or Path.cwd()).resolve()
    suitspec_path = Path(suitspec)
    if not suitspec_path.is_absolute():
        suitspec_path = base / suitspec_path
    session_root = Path(root)
    if not session_root.is_absolute():
        session_root = base / session_root
    spec = load_json(suitspec_path)
    guide = ensure_uv_guide_image(
        part=part,
        module=spec.get("modules", {}).get(part),
        contract=context["uv_contracts"][part],
        session_root=session_root,
        repo_root=base,
        write_image=True,
        guide_profile="topology_mask",
    )
    context["uv_guides"][part] = serialize_uv_guide(guide)


def _compressed_uv_first_prompt(context: dict[str, Any], part: str) -> str:
    return (
        f"Primary task: create a flat UV texture atlas for mesh routing key {part}; UV subject descriptor: {uv_safe_module_descriptor(part)}.\n"
        f"{uv_subject_guard(part)}"
        "Reference A is authoritative. Obey the UV islands, normal color zones, fold/crease lines, seam-safe border, centerline, and motif box over all style impulses.\n"
        "Important: Reference A is a marked-up engineering overlay. Do not reproduce its cyan/green/purple/orange annotation colors or wireframe lines in the final texture.\n"
        f"{_block('UV map semantics', _uv_semantics(context['uv_guides'][part]))}"
        f"{_block('User armor DNA', _compact_user_dna(context.get('user_armor_profile')))}"
        f"{_block('Current activation modulation', _compact_current_state(context.get('style_variation')))}"
        "Lore rule: every line must be explainable as armor manufacturing, service access, actuator clearance, power routing, identification, rescue, inspection, or survivability.\n"
        f"Mechanical role in UV-safe wording: {uv_safe_part_function(part)}\n"
        f"{_part_direction_text(part)}\n"
        f"{UV_ATLAS_FAILURE_GUARD}"
        "Output: 1:1 square base-color texture sheet only. No standalone armor object, no mannequin, no scene, no cast shadows, no text, no labels, no watermark.\n"
    )


def _normal_fold_first_prompt(context: dict[str, Any], part: str) -> str:
    return (
        f"Make a UV-painted armor material sheet for mesh routing key {part}; UV subject descriptor: {uv_safe_module_descriptor(part)}. Start from Reference A's normal and fold map.\n"
        f"{uv_subject_guard(part)}"
        f"{_block('Reference A decoding', _uv_semantics(context['uv_guides'][part]))}"
        "Paint by surface direction: front identity surfaces receive the part's primary functional face; side wrap surfaces receive construction, articulation, or load-transfer logic; rear and inner surfaces receive service-latch logic; crease lines become believable plate bends or material breaks.\n"
        f"Mechanical role in UV-safe wording: {uv_safe_part_function(part)}\n"
        f"{_part_direction_text(part)}\n"
        "Do not draw the assembled armor module. Do not draw a helmet, chest plate, boot, glove, limb sleeve, or any part as an object in space.\n"
        "The full square must read as a UV material texture canvas: flat paint, decal, panel, seam, emissive, and wear information laid inside UV-island topology.\n"
        "No studio background, no cast shadow, no perspective, no object silhouette, no character, no display stand.\n"
        f"{UV_ATLAS_FAILURE_GUARD}"
        "Do not ignore orange fold/crease lines. Use them as hard-surface bend boundaries, panel breaks, or formed metal transitions.\n"
        "Do not reproduce the guide's visible annotation system. Translate it into the user's armor palette and material language.\n"
        f"{_block('Permanent user-specific armor DNA', _compact_user_dna(context.get('user_armor_profile')))}"
        f"{_block('Design team constraints', _compact_team(context.get('armor_design_team')))}"
        "Keep the image flat, albedo-like, orthographic, and UV-island bound. No standalone armor render, no perspective object, no background.\n"
    )


def _two_pass_concept_prompt(context: dict[str, Any], part: str) -> str:
    return (
        f"Design the surface language for mesh routing key {part}; UV subject descriptor: {uv_safe_module_descriptor(part)}.\n"
        f"{uv_subject_guard(part)}"
        "This is a concept pass, not the final UV atlas. Create the part's material logic, mechanical identity, side/rear construction language, service logic, and user-specific palette/motif.\n"
        f"Mechanical role in UV-safe wording: {uv_safe_part_function(part)}\n"
        f"{_part_direction_text(part)}\n"
        f"{_block('User armor DNA', _compact_user_dna(context.get('user_armor_profile')))}"
        f"{_block('Current activation modulation', _compact_current_state(context.get('style_variation')))}"
        "Output an isolated armor-module concept on a clean background. No person, no full body, no text, no logos.\n"
    )


def _two_pass_refine_prompt(context: dict[str, Any], part: str) -> str:
    return (
        f"Convert Reference B's armor-module concept into a flat UV texture atlas for mesh routing key {part}; UV subject descriptor: {uv_safe_module_descriptor(part)}.\n"
        f"{uv_subject_guard(part)}"
        f"{_block('Reference A UV engineering map', _uv_semantics(context['uv_guides'][part]))}"
        "Reference A controls layout, normal-facing surface zones, fold/crease lines, seam-safe borders, and motif zone. Reference B controls material rhythm and identity only.\n"
        "Do not reproduce Reference A annotation colors, wireframe strokes, or grid lines. Convert those annotations into clean armor material, panels, seams, emissives, and wear.\n"
        "Transfer the concept into UV islands. Do not draw a standalone armor object. Do not invent a new layout. Do not place dense detail on boundaries or seam-safe margins.\n"
        f"{UV_ATLAS_FAILURE_GUARD}"
        f"Mechanical role in UV-safe wording: {uv_safe_part_function(part)}\n"
        f"{_part_direction_text(part)} Orange folds become plate bends or material breaks.\n"
        f"{_block('User armor DNA', _compact_user_dna(context.get('user_armor_profile')))}"
        "Output a 1:1 square base-color texture sheet only.\n"
    )


def build_part_prompt_variants(context: dict[str, Any], *, part: str = "helmet") -> list[PromptBenchVariant]:
    current_prompt = context["prompts"][part]
    current_refine = (context.get("refine_prompts") or {}).get(part)
    return [
        PromptBenchVariant(
            key="a_current_full",
            title="A Current Full",
            intent="Current production prompt with all lore, DNA, team, UV, and emotion sections.",
            prompt=current_prompt,
            refine_prompt=current_refine,
            mode="current_pipeline",
        ),
        PromptBenchVariant(
            key="b_compressed_uv_first",
            title="B Compressed UV First",
            intent="Short prompt that makes Reference A authoritative and reduces lore to a hard rule.",
            prompt=_compressed_uv_first_prompt(context, part),
        ),
        PromptBenchVariant(
            key="c_normal_fold_first",
            title="C Normal/Fold Map First",
            intent="Prompt that treats normal zones and crease lines as the main construction grammar.",
            prompt=_normal_fold_first_prompt(context, part),
        ),
        PromptBenchVariant(
            key="d_two_pass_strict",
            title="D Two Pass Strict",
            intent="Concept prompt plus strict UV refine prompt to test separation of style and layout.",
            prompt=_two_pass_concept_prompt(context, part),
            refine_prompt=_two_pass_refine_prompt(context, part),
            mode="two_pass",
        ),
    ]


def build_part_prompt_bench(
    *,
    suitspec: str = "examples/suitspec.sample.json",
    root: str = "sessions",
    part: str = "helmet",
    repo_root: Path | None = None,
    emotion_profile: dict[str, Any] | None = None,
    operator_profile_override: dict[str, Any] | None = None,
    generation_brief: str | None = None,
) -> dict[str, Any]:
    context = run_generate_parts(
        GenerationRequest(
            suitspec=suitspec,
            root=root,
            parts=[part],
            dry_run=True,
            texture_mode="mesh_uv",
            uv_refine=True,
            provider_profile="nano_banana",
            use_cache=False,
            fallback_dir=None,
            generation_brief=generation_brief,
            emotion_profile=emotion_profile or dict(DEFAULT_EMOTION_PROFILE),
            operator_profile_override=operator_profile_override or dict(DEFAULT_OPERATOR_PROFILE),
        ),
        repo_root=repo_root,
    )
    _materialize_uv_guide(context, suitspec=suitspec, root=root, part=part, repo_root=repo_root)
    variants = build_part_prompt_variants(context, part=part)
    return {
        "bench_version": BENCH_VERSION,
        "part": part,
        "suitspec": suitspec,
        "generation_brief": generation_brief,
        "context": context,
        "variants": [asdict(variant) for variant in variants],
        "comparison": [
            {
                "key": variant.key,
                "title": variant.title,
                "mode": variant.mode,
                "prompt_chars": len(variant.prompt),
                "refine_prompt_chars": len(variant.refine_prompt or ""),
                "intent": variant.intent,
            }
            for variant in variants
        ],
        "evaluation_rubric": {
            "uv_layout_obedience": "Does the image stay a flat UV atlas bound to Reference A?",
            "normal_fold_obedience": "Do orange crease lines and normal-facing color zones influence panel breaks?",
            "part_identity": _part_identity_rubric(part),
            "side_rear_logic": "Do side and rear zones carry comms/service logic instead of filler?",
            "user_identity": "Does the stable user palette/motif remain visible without overriding UV correctness?",
            "artifact_rejection": "Reject character renders, scene backgrounds, labels, text, logos, and cast-shadow object views.",
        },
    }


def build_helmet_prompt_variants(context: dict[str, Any], *, part: str = "helmet") -> list[PromptBenchVariant]:
    return build_part_prompt_variants(context, part=part)


def build_helmet_prompt_bench(**kwargs: Any) -> dict[str, Any]:
    return build_part_prompt_bench(**kwargs)


def write_prompt_bench(bench: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for variant in bench["variants"]:
        (output_dir / f"{variant['key']}.prompt.txt").write_text(variant["prompt"], encoding="utf-8")
        if variant.get("refine_prompt"):
            (output_dir / f"{variant['key']}.refine.txt").write_text(variant["refine_prompt"], encoding="utf-8")
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary_path


def _load_reference(path: str | Path) -> ImageReference:
    p = Path(path)
    mime_type = "image/png" if p.suffix.lower() != ".jpg" else "image/jpeg"
    return ImageReference(mime_type=mime_type, image_bytes=p.read_bytes())


def run_live_prompt_bench(
    bench: dict[str, Any],
    output_dir: Path,
    *,
    timeout_seconds: int = 90,
    api_key: str | None = None,
) -> dict[str, Any]:
    provider_spec = resolve_provider_profile("nano_banana")
    fast = provider_spec["fast_draft"]
    refine = provider_spec["quality_refine"]
    key = resolve_provider_api_key(fast.provider, api_key)
    guide_path = bench["context"]["uv_guides"][bench["part"]]["path"]
    guide_reference = _load_reference(guide_path)

    outputs: dict[str, Any] = {}
    output_dir.mkdir(parents=True, exist_ok=True)
    for variant in bench["variants"]:
        started = time.perf_counter()
        if variant["mode"] == "two_pass" and variant.get("refine_prompt"):
            concept = generate_image(
                provider=fast.provider,
                model_id=fast.model_id,
                api_key=key,
                prompt=variant["prompt"],
                references=None,
                aspect_ratio="1:1",
                image_size="2K",
                timeout_seconds=timeout_seconds,
            )
            concept_path = save_image(concept, output_dir / f"{variant['key']}.concept{extension_for_mime(concept.mime_type)}")
            write_generation_meta(output_dir / f"{variant['key']}.concept.generation.json", concept, f"bench:{variant['key']}:concept")
            result = generate_image(
                provider=refine.provider,
                model_id=refine.model_id,
                api_key=key,
                prompt=variant["refine_prompt"],
                references=[
                    guide_reference,
                    ImageReference(mime_type=concept.mime_type, image_bytes=concept.image_bytes),
                ],
                aspect_ratio="1:1",
                image_size="2K",
                timeout_seconds=timeout_seconds,
            )
            references = [
                {"role": "uv_engineering_guide", "path": guide_path},
                {"role": "style_concept", "path": str(concept_path)},
            ]
        else:
            result = generate_image(
                provider=fast.provider,
                model_id=fast.model_id,
                api_key=key,
                prompt=variant["prompt"],
                references=[guide_reference],
                aspect_ratio="1:1",
                image_size="2K",
                timeout_seconds=timeout_seconds,
            )
            references = [{"role": "uv_engineering_guide", "path": guide_path}]

        image_path = save_image(result, output_dir / f"{variant['key']}.generated{extension_for_mime(result.mime_type)}")
        meta_path = write_generation_meta(output_dir / f"{variant['key']}.generation.json", result, f"bench:{variant['key']}")
        quality_gate = evaluate_texture_output(image_path, guide_path=guide_path)
        outputs[variant["key"]] = {
            "image_path": str(image_path),
            "meta_path": str(meta_path),
            "provider": result.provider,
            "model_id": result.model_id,
            "prompt_chars": len(result.prompt),
            "references": references,
            "quality_gate": quality_gate,
            "elapsed_sec": round(time.perf_counter() - started, 3),
        }
    bench["live_outputs"] = outputs
    bench["quality_rejected_variants"] = [
        key for key, output in outputs.items() if (output.get("quality_gate") or {}).get("reject")
    ]
    (output_dir / "summary.json").write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return outputs


__all__ = [
    "BENCH_VERSION",
    "DEFAULT_EMOTION_PROFILE",
    "DEFAULT_OPERATOR_PROFILE",
    "PromptBenchVariant",
    "build_part_prompt_bench",
    "build_part_prompt_variants",
    "build_helmet_prompt_bench",
    "build_helmet_prompt_variants",
    "run_live_prompt_bench",
    "write_prompt_bench",
]
