"""Wave-based part generation pipeline for exhibition workflows."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .archive import ensure_session_dir, write_json
from .emotion_compiler import compile_emotion_request
from .gemini_image import extension_for_mime, save_image, write_generation_meta
from .ids import generate_session_id
from .image_providers import GeneratedImage, ImageReference, ImageProviderError, generate_image, resolve_provider_api_key
from .mesh_assets import resolve_mesh_asset_ref
from .part_prompts import _base_style_text, build_uv_refine_prompt, list_enabled_parts, resolve_part_prompts
from .suit_dna import resolve_suit_design_dna, serialize_suit_design_dna
from .user_profile_compiler import compile_operator_profile
from .uv_guides import ensure_uv_guide_image, serialize_uv_guide
from .uv_contracts import resolve_uv_contract, serialize_uv_contract
from .validators import load_json


ProgressCallback = Callable[[dict[str, Any]], None]

WAVE_PRIORITY = [
    ["helmet", "chest", "left_shoulder", "right_shoulder"],
    ["back", "waist", "left_forearm", "right_forearm"],
]

DEFAULT_PROVIDER_PROFILE = "nano_banana"
DEFAULT_FAL_FAST_MODEL = "fal-ai/flux/schnell"
DEFAULT_FAL_REFINE_MODEL = "fal-ai/flux/dev"
DEFAULT_OPENAI_HERO_MODEL = "gpt-image-1"
DEFAULT_GEMINI_FAST_MODEL = "gemini-2.5-flash-image"
DEFAULT_GEMINI_REFINE_MODEL = DEFAULT_GEMINI_FAST_MODEL
DEFAULT_GEMINI_HERO_MODEL = "gemini-3-pro-image-preview"
DEFAULT_GEMINI_FALLBACK_MODEL = "gemini-3.1-flash-image-preview"


@dataclass(slots=True)
class ProviderSpec:
    provider: str
    model_id: str


@dataclass(slots=True)
class GenerationRequest:
    suitspec: str
    root: str = "sessions"
    session_id: str | None = None
    parts: list[str] | None = None
    model_id: str | None = None
    api_key: str | None = None
    generation_brief: str | None = None
    emotion_profile: dict[str, Any] | None = None
    operator_profile_override: dict[str, Any] | None = None
    timeout: int = 90
    texture_mode: str = "mesh_uv"
    uv_refine: bool = False
    fallback_dir: str | None = None
    prefer_fallback: bool = False
    update_suitspec: bool = False
    dry_run: bool = False
    provider_profile: str = DEFAULT_PROVIDER_PROFILE
    priority_mode: str = "exhibition"
    use_cache: bool = True
    hero_render: bool = False
    tracking_source: str = "webcam"
    max_parallel: int = 4
    retry_count: int = 1


def _load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}

    values: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def _setting(*keys: str, default: str) -> str:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value

    dotenv = _load_dotenv()
    for key in keys:
        value = dotenv.get(key)
        if value:
            return value

    return default


def resolve_provider_profile(name: str) -> dict[str, ProviderSpec]:
    profile = name.strip().lower().replace("-", "_")

    if profile == "nano_banana":
        fast_model = _setting("GEMINI_FAST_MODEL", default=DEFAULT_GEMINI_FAST_MODEL)
        refine_model = _setting(
            "GEMINI_REFINE_MODEL",
            "GEMINI_QUALITY_MODEL",
            default=DEFAULT_GEMINI_REFINE_MODEL,
        )
        hero_model = _setting("GEMINI_HERO_MODEL", default=DEFAULT_GEMINI_HERO_MODEL)
        fallback_model = _setting(
            "GEMINI_FALLBACK_MODEL",
            "GEMINI_SECONDARY_MODEL",
            default=DEFAULT_GEMINI_FALLBACK_MODEL,
        )
        return {
            "fast_draft": ProviderSpec("gemini", fast_model),
            "quality_refine": ProviderSpec("gemini", refine_model),
            "hero_render": ProviderSpec("gemini", hero_model),
            "fallback_fast": ProviderSpec("gemini", fallback_model),
        }

    if profile == "exhibition":
        return {
            "fast_draft": ProviderSpec(
                "fal",
                _setting("FAL_FAST_DRAFT_MODEL", default=DEFAULT_FAL_FAST_MODEL),
            ),
            "quality_refine": ProviderSpec(
                "fal",
                _setting("FAL_QUALITY_REFINE_MODEL", default=DEFAULT_FAL_REFINE_MODEL),
            ),
            "hero_render": ProviderSpec(
                "openai",
                _setting("OPENAI_HERO_MODEL", default=DEFAULT_OPENAI_HERO_MODEL),
            ),
            "fallback_fast": ProviderSpec(
                "gemini",
                _setting(
                    "GEMINI_FALLBACK_MODEL",
                    "GEMINI_FAST_MODEL",
                    default=DEFAULT_GEMINI_FAST_MODEL,
                ),
            ),
        }

    raise ValueError(f"Unsupported provider profile: {name}")


def build_generation_waves(requested: list[str]) -> list[list[str]]:
    remaining = list(dict.fromkeys(requested))
    waves: list[list[str]] = []
    for wave in WAVE_PRIORITY:
        current = [part for part in wave if part in remaining]
        if current:
            waves.append(current)
            remaining = [part for part in remaining if part not in current]
    if remaining:
        waves.append(remaining)
    return waves


def build_generation_cache_key(
    *,
    provider: str,
    model_id: str,
    part: str,
    texture_mode: str,
    prompt: str,
    reference_hash: str,
    suitspec_generation_version: str,
) -> str:
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    return "__".join(
        [
            provider,
            model_id.replace("/", "_"),
            part,
            texture_mode,
            prompt_hash,
            reference_hash,
            suitspec_generation_version,
        ]
    )


GENERATION_RUNTIME_KEYS = frozenset(
    {
        "last_generation_brief",
        "last_generation_brief_raw",
        "last_operator_profile_raw",
        "last_operator_profile_resolved",
        "last_user_armor_profile",
        "last_emotion_profile_raw",
        "last_emotion_profile_resolved",
        "last_style_variation",
        "last_resolved_defaults",
        "part_prompts",
        "provider_profile",
        "texture_mode",
        "tracking_source",
        "uv_refine",
    }
)


def _summary_generation_version(spec: dict[str, Any]) -> str:
    generation = spec.get("generation", {})
    if isinstance(generation, dict):
        if generation.get("version"):
            return str(generation["version"])
        semantic_generation = {
            key: value
            for key, value in generation.items()
            if key not in GENERATION_RUNTIME_KEYS and not key.startswith("last_")
        }
        serialized = json.dumps(semantic_generation, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
    return "nogeneration"


def _resolve_fallback_image(part: str, fallback_dir: Path) -> Path | None:
    candidates = [
        f"{part}.generated.png",
        f"{part}.generated.jpg",
        f"{part}.generated.jpeg",
        f"{part}.generated.webp",
        f"{part}.png",
        f"{part}.jpg",
        f"{part}.jpeg",
        f"{part}.webp",
    ]
    for name in candidates:
        path = fallback_dir / name
        if path.exists() and path.is_file():
            return path
    return None


def _use_fallback_asset(part: str, fallback_dir: Path, parts_dir: Path, *, source_label: str = "fallback") -> dict[str, str] | None:
    source = _resolve_fallback_image(part, fallback_dir)
    if source is None:
        return None

    ext = source.suffix.lower() or ".png"
    image_path = parts_dir / f"{part}.generated{ext}"
    if source.resolve() != image_path.resolve():
        shutil.copy2(source, image_path)

    meta_path = parts_dir / f"{part}.generation.json"
    meta_payload = {
        "kind": f"part:{part}",
        "source": source_label,
        "fallback_image_path": str(source),
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"image_path": str(image_path), "meta_path": str(meta_path), "source": source_label}


def _ensure_cache_dirs(root: str | Path) -> Path:
    cache_dir = Path(root) / "_cache" / "parts"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_meta_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{key}.json"


def _cache_load(cache_dir: Path, key: str) -> dict[str, Any] | None:
    meta_path = _cache_meta_path(cache_dir, key)
    if not meta_path.exists():
        return None
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    image_path = meta_path.parent / payload["filename"]
    if not image_path.exists():
        return None
    payload["image_path"] = str(image_path)
    return payload


def _reference_hash(*tokens: str | None) -> str:
    meaningful = [token for token in tokens if token]
    if not meaningful:
        return "none"
    payload = "||".join(meaningful).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _load_image_reference(path: str | Path | None) -> ImageReference | None:
    if not path:
        return None
    ref_path = Path(path)
    if not ref_path.exists():
        return None
    suffix = ref_path.suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")
    return ImageReference(mime_type=mime_type, image_bytes=ref_path.read_bytes())


def _cache_store(cache_dir: Path, key: str, result: GeneratedImage) -> dict[str, Any]:
    ext = extension_for_mime(result.mime_type)
    image_path = cache_dir / f"{key}{ext}"
    image_path.write_bytes(result.image_bytes)
    payload = {
        "provider": result.provider,
        "model_id": result.model_id,
        "mime_type": result.mime_type,
        "filename": image_path.name,
        "image_path": str(image_path),
    }
    _cache_meta_path(cache_dir, key).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _copy_cached_asset(part: str, cached: dict[str, Any], parts_dir: Path) -> dict[str, str]:
    source = Path(cached["image_path"])
    image_path = parts_dir / f"{part}.generated{source.suffix.lower() or '.png'}"
    if source.resolve() != image_path.resolve():
        shutil.copy2(source, image_path)

    meta_path = parts_dir / f"{part}.generation.json"
    meta_payload = {
        "kind": f"part:{part}",
        "source": "cache",
        "cached_image_path": str(source),
        "provider": cached.get("provider"),
        "model_id": cached.get("model_id"),
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"image_path": str(image_path), "meta_path": str(meta_path), "source": "cache"}


def _hero_prompt(
    spec: dict[str, Any],
    generated_parts: list[str],
    tracking_source: str,
    generation_brief: str | None = None,
    user_armor_profile: dict[str, Any] | None = None,
    style_variation: dict[str, Any] | None = None,
) -> str:
    style_text = _base_style_text(spec)
    user_profile_text = ""
    if user_armor_profile:
        user_profile_text = (
            "User-specific armor DNA:\n"
            f"- Identity seed: {user_armor_profile.get('identity_seed', 'unknown')}\n"
            f"- Palette family: {user_armor_profile.get('palette_family', '')}\n"
            f"- Palette guidance: {user_armor_profile.get('palette_guidance', '')}\n"
            f"- Motif guidance: {user_armor_profile.get('motif_guidance', '')}\n"
            f"- Silhouette guidance: {user_armor_profile.get('silhouette_guidance', '')}\n"
            f"- Emissive guidance: {user_armor_profile.get('emissive_guidance', '')}\n"
            f"- Continuity rule: {user_armor_profile.get('continuity_rule', '')}\n"
        )
    variation_text = ""
    if style_variation:
        variation_text = (
            "Current emotional modulation:\n"
            f"- Palette guidance: {style_variation.get('palette_guidance', '')}\n"
            f"- Finish guidance: {style_variation.get('finish_guidance', '')}\n"
            f"- Emissive guidance: {style_variation.get('emissive_guidance', '')}\n"
            f"- Tri-view guidance: {style_variation.get('tri_view_guidance', '')}\n"
        )
    brief_text = ""
    if generation_brief and generation_brief.strip():
        brief_text = f"Creative direction from the current request: {generation_brief.strip()}.\n"
    return (
        "Create a clean exhibition-ready hero poster of a human silhouette wearing the generated modular armor.\n"
        f"{style_text}\n"
        f"{user_profile_text}"
        f"{variation_text}"
        f"{brief_text}"
        f"Visible generated parts: {', '.join(generated_parts) if generated_parts else 'none'}.\n"
        f"Tracking source in the installation: {tracking_source}.\n"
        "Composition: full body, front-facing, white exhibition background, luminous visor, readable silhouette.\n"
        "No text, no watermark, no frame graphics."
    )


def _emit(progress: ProgressCallback | None, payload: dict[str, Any]) -> None:
    if progress is not None:
        progress(payload)


def _display_path(path: str | Path, repo_root: Path | None) -> str:
    raw = Path(path)
    try:
        if repo_root is not None:
            return str(raw.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        pass
    return str(raw).replace("\\", "/")


def _resolve_paths(request: GenerationRequest, *, repo_root: Path | None = None) -> tuple[Path, Path, Path | None]:
    if repo_root is not None:
        session_root = (repo_root / request.root).resolve()
        suitspec_path = (repo_root / request.suitspec).resolve()
        fallback_dir = (repo_root / request.fallback_dir).resolve() if request.fallback_dir else None
    else:
        session_root = Path(request.root).resolve()
        suitspec_path = Path(request.suitspec).resolve()
        fallback_dir = Path(request.fallback_dir).resolve() if request.fallback_dir else None
    return session_root, suitspec_path, fallback_dir


def _provider_attempt(
    spec: ProviderSpec,
    *,
    prompt: str,
    api_key_override: str | None,
    references: list[ImageReference] | None,
    aspect_ratio: str | None,
    image_size: str | None,
    timeout_seconds: int,
    progress: ProgressCallback | None,
) -> GeneratedImage:
    api_key = resolve_provider_api_key(spec.provider, api_key_override)
    return generate_image(
        provider=spec.provider,
        prompt=prompt,
        model_id=spec.model_id,
        api_key=api_key,
        references=references,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        timeout_seconds=timeout_seconds,
        progress=progress,
    )


def run_generate_parts(
    request: GenerationRequest,
    *,
    repo_root: Path | None = None,
    progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    session_root, suitspec_path, fallback_dir = _resolve_paths(request, repo_root=repo_root)
    spec = load_json(suitspec_path)
    requested = request.parts or list_enabled_parts(spec)
    if not requested:
        raise ValueError("No enabled parts found in suitspec.")
    operator_context = compile_operator_profile(spec.get("operator_profile"), request.operator_profile_override)
    user_armor_profile = operator_context["user_armor_profile"]
    emotion_context = compile_emotion_request(
        request.emotion_profile,
        request.generation_brief,
        user_armor_profile=user_armor_profile,
    )
    effective_generation_brief = emotion_context["compiled_brief"]
    style_variation = emotion_context["style_variation"]
    design_dna = serialize_suit_design_dna(resolve_suit_design_dna(spec))
    uv_contracts = {part: serialize_uv_contract(resolve_uv_contract(spec, part)) for part in requested}
    uv_guides = {
        part: ensure_uv_guide_image(
            part=part,
            module=spec.get("modules", {}).get(part),
            contract=uv_contracts[part],
            session_root=session_root,
            repo_root=repo_root,
            write_image=not request.dry_run,
        )
        for part in requested
    }

    prompts = resolve_part_prompts(
        spec,
        requested,
        texture_mode=request.texture_mode,
        generation_brief=effective_generation_brief,
        style_variation=style_variation,
        user_armor_profile=user_armor_profile,
    )
    concept_prompts: dict[str, str] = {}
    refine_prompts: dict[str, str] = {}
    if request.uv_refine and request.texture_mode == "mesh_uv":
        concept_prompts = resolve_part_prompts(
            spec,
            requested,
            texture_mode="concept",
            generation_brief=effective_generation_brief,
            style_variation=style_variation,
            user_armor_profile=user_armor_profile,
        )
        refine_prompts = {
            part: build_uv_refine_prompt(
                part,
                spec,
                generation_brief=effective_generation_brief,
                style_variation=style_variation,
                user_armor_profile=user_armor_profile,
            )
            for part in requested
        }

    if request.dry_run:
        payload: dict[str, Any] = {
            "ok": True,
            "dry_run": True,
            "parts": requested,
            "operator_profile_raw": operator_context["operator_profile_raw"],
            "operator_profile_resolved": operator_context["operator_profile_resolved"],
            "user_armor_profile": user_armor_profile,
            "operator_resolved_defaults": operator_context["resolved_defaults"],
            "emotion_profile": emotion_context["emotion_profile_resolved"],
            "emotion_profile_raw": emotion_context["emotion_profile_raw"],
            "emotion_profile_resolved": emotion_context["emotion_profile_resolved"],
            "emotion_directives": emotion_context["emotion_directives"],
            "style_variation": style_variation,
            "resolved_defaults": emotion_context["resolved_defaults"],
            "generation_brief_raw": request.generation_brief,
            "generation_brief_compiled": effective_generation_brief,
            "prompts": prompts,
            "design_dna": design_dna,
            "uv_contracts": uv_contracts,
            "uv_guides": {part: serialize_uv_guide(info) for part, info in uv_guides.items()},
        }
        if refine_prompts:
            payload["refine_prompts"] = refine_prompts
        return payload

    if fallback_dir is not None and (not fallback_dir.exists() or not fallback_dir.is_dir()):
        raise ValueError(f"Fallback dir not found or not a directory: {fallback_dir}")

    session_id = request.session_id or generate_session_id()
    session_dir = ensure_session_dir(session_id, root=session_root)
    parts_dir = session_dir / "artifacts" / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = _ensure_cache_dirs(session_root)
    image_aspect_ratio = "1:1" if request.texture_mode == "mesh_uv" else None
    image_size = "2K" if request.texture_mode == "mesh_uv" else None
    provider_profile = resolve_provider_profile(request.provider_profile)
    if request.model_id:
        provider_profile["fast_draft"] = ProviderSpec(provider_profile["fast_draft"].provider, request.model_id)
        provider_profile["quality_refine"] = ProviderSpec(provider_profile["quality_refine"].provider, request.model_id)
    generation_version = _summary_generation_version(spec)

    generated: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    fallback_used: list[str] = []
    cache_hits: list[str] = []
    cancelled_parts: list[str] = []
    part_metrics: dict[str, dict[str, Any]] = {}
    waves = build_generation_waves(requested)

    _emit(
        progress,
        {
            "type": "job_started",
            "stage": "scan",
            "status": "started",
            "session_id": session_id,
            "requested_count": len(requested),
            "requested_parts": requested,
        },
    )

    def generate_part(part: str, wave_index: int) -> tuple[str, dict[str, Any] | None, str | None]:
        part_started = time.perf_counter()
        metric = {
            "queue_wait_ms": 0,
            "inference_ms": 0,
            "total_ms": 0,
            "cache_hit": False,
            "retry_count": 0,
            "fallback_used": False,
        }
        if cancel_event and cancel_event.is_set():
            cancelled_parts.append(part)
            return part, None, "cancelled"

        guide_info = uv_guides.get(part)
        guide_path = Path(guide_info["path"]) if guide_info else None
        guide_reference = _load_image_reference(guide_path) if request.texture_mode == "mesh_uv" else None
        concept_prompt_hash = hashlib.sha256(concept_prompts.get(part, "").encode("utf-8")).hexdigest()[:12] if concept_prompts else None
        reference_hash = _reference_hash(guide_info["guide_hash"] if guide_info else None, concept_prompt_hash)
        output_spec = provider_profile["quality_refine" if request.uv_refine and request.texture_mode == "mesh_uv" else "fast_draft"]
        key = build_generation_cache_key(
            provider=output_spec.provider,
            model_id=output_spec.model_id,
            part=part,
            texture_mode=request.texture_mode,
            prompt=refine_prompts.get(part) or prompts[part],
            reference_hash=reference_hash,
            suitspec_generation_version=generation_version,
        )
        guide_display_path = _display_path(guide_path, repo_root) if guide_path else None
        info_common = {
            "uv_guide_path": guide_display_path,
            "uv_guide_hash": guide_info["guide_hash"] if guide_info else None,
            "mesh_asset_ref": resolve_mesh_asset_ref(part, spec.get("modules", {}).get(part)),
        }
        if request.texture_mode == "mesh_uv" and guide_reference is None:
            return part, None, f"UV guide image is unavailable for part={part}."

        _emit(
            progress,
            {
                "type": "part_started",
                "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                "part": part,
                "wave_index": wave_index,
                "status": "running",
            },
        )

        if request.use_cache:
            cached = _cache_load(cache_dir, key)
            if cached is not None:
                metric["cache_hit"] = True
                metric["total_ms"] = int((time.perf_counter() - part_started) * 1000)
                cache_hits.append(part)
                info = _copy_cached_asset(part, cached, parts_dir)
                info["image_path"] = _display_path(info["image_path"], repo_root)
                info["meta_path"] = _display_path(info["meta_path"], repo_root)
                info["preview_url"] = "/" + info["image_path"].lstrip("/")
                info["timing_ms"] = dict(metric)
                info["reference_stack"] = [{"role": "uv_engineering_guide", "path": guide_display_path}] if guide_display_path else []
                info.update(info_common)
                part_metrics[part] = dict(metric)
                return part, info, None

        if request.prefer_fallback and fallback_dir is not None:
            info = _use_fallback_asset(part, fallback_dir, parts_dir)
            if info is not None:
                metric["fallback_used"] = True
                metric["total_ms"] = int((time.perf_counter() - part_started) * 1000)
                fallback_used.append(part)
                info["image_path"] = _display_path(info["image_path"], repo_root)
                info["meta_path"] = _display_path(info["meta_path"], repo_root)
                info["preview_url"] = "/" + info["image_path"].lstrip("/")
                info["timing_ms"] = dict(metric)
                info["reference_stack"] = [{"role": "uv_engineering_guide", "path": guide_display_path}] if guide_display_path else []
                info.update(info_common)
                part_metrics[part] = dict(metric)
                return part, info, None

        last_error: str | None = None
        attempts = request.retry_count + 1
        for attempt in range(1, attempts + 1):
            if cancel_event and cancel_event.is_set():
                cancelled_parts.append(part)
                return part, None, "cancelled"
            try:
                if request.uv_refine and request.texture_mode == "mesh_uv":
                    concept = _provider_attempt(
                        provider_profile["fast_draft"],
                        prompt=concept_prompts[part],
                        api_key_override=request.api_key,
                        references=None,
                        aspect_ratio=image_aspect_ratio,
                        image_size=image_size,
                        timeout_seconds=request.timeout,
                        progress=lambda payload: _emit(
                            progress,
                            {
                                "type": "provider_progress",
                                "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                                "part": part,
                                "status": payload.get("status", "running"),
                                "queue_position": payload.get("queue_position"),
                                "log": "\n".join(payload.get("logs") or []),
                            },
                        ),
                    )
                    concept_ext = extension_for_mime(concept.mime_type)
                    concept_path = save_image(concept, output_path=parts_dir / f"{part}.concept{concept_ext}")
                    write_generation_meta(parts_dir / f"{part}.concept.generation.json", result=concept, kind=f"part:{part}:concept")

                    result = _provider_attempt(
                        provider_profile["quality_refine"],
                        prompt=refine_prompts[part],
                        api_key_override=request.api_key,
                        references=[
                            guide_reference,
                            ImageReference(mime_type=concept.mime_type, image_bytes=concept.image_bytes),
                        ],
                        aspect_ratio=image_aspect_ratio,
                        image_size=image_size,
                        timeout_seconds=request.timeout,
                        progress=lambda payload: _emit(
                            progress,
                            {
                                "type": "provider_progress",
                                "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                                "part": part,
                                "status": payload.get("status", "running"),
                                "queue_position": payload.get("queue_position"),
                                "log": "\n".join(payload.get("logs") or []),
                            },
                        ),
                    )
                    source = f"{result.provider}_refine"
                    info_extra = {
                        "concept_path": _display_path(concept_path, repo_root),
                        "reference_stack": [
                            {"role": "uv_engineering_guide", "path": guide_display_path},
                            {"role": "style_concept", "path": _display_path(concept_path, repo_root)},
                        ],
                    }
                else:
                    result = _provider_attempt(
                        provider_profile["fast_draft"],
                        prompt=prompts[part],
                        api_key_override=request.api_key,
                        references=[guide_reference] if request.texture_mode == "mesh_uv" else None,
                        aspect_ratio=image_aspect_ratio,
                        image_size=image_size,
                        timeout_seconds=request.timeout,
                        progress=lambda payload: _emit(
                            progress,
                            {
                                "type": "provider_progress",
                                "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                                "part": part,
                                "status": payload.get("status", "running"),
                                "queue_position": payload.get("queue_position"),
                                "log": "\n".join(payload.get("logs") or []),
                            },
                        ),
                    )
                    source = result.provider
                    info_extra = {
                        "reference_stack": [{"role": "uv_engineering_guide", "path": guide_display_path}] if guide_display_path else []
                    }

                ext = extension_for_mime(result.mime_type)
                image_path = save_image(result, output_path=parts_dir / f"{part}.generated{ext}")
                meta_path = write_generation_meta(parts_dir / f"{part}.generation.json", result=result, kind=f"part:{part}")
                if request.use_cache:
                    _cache_store(cache_dir, key, result)

                metric.update(
                    {
                        "queue_wait_ms": result.queue_wait_ms,
                        "inference_ms": result.inference_ms,
                        "total_ms": result.total_ms or int((time.perf_counter() - part_started) * 1000),
                        "retry_count": attempt - 1,
                        "fallback_used": False,
                    }
                )
                info = {
                    "image_path": _display_path(image_path, repo_root),
                    "meta_path": _display_path(meta_path, repo_root),
                    "source": source,
                    "provider": result.provider,
                    "model_id": result.model_id,
                    "preview_url": "/" + _display_path(image_path, repo_root).lstrip("/"),
                    "timing_ms": dict(metric),
                    **info_common,
                    **info_extra,
                }
                part_metrics[part] = dict(metric)
                return part, info, None
            except ImageProviderError as exc:
                metric["retry_count"] = attempt
                last_error = str(exc)

        try:
            result = _provider_attempt(
                provider_profile["fallback_fast"],
                prompt=prompts[part],
                api_key_override=request.api_key,
                references=[guide_reference] if request.texture_mode == "mesh_uv" else None,
                aspect_ratio=image_aspect_ratio,
                image_size=image_size,
                timeout_seconds=request.timeout,
                progress=None,
            )
            ext = extension_for_mime(result.mime_type)
            image_path = save_image(result, output_path=parts_dir / f"{part}.generated{ext}")
            meta_path = write_generation_meta(parts_dir / f"{part}.generation.json", result=result, kind=f"part:{part}")
            metric.update(
                {
                    "queue_wait_ms": result.queue_wait_ms,
                    "inference_ms": result.inference_ms,
                    "total_ms": result.total_ms or int((time.perf_counter() - part_started) * 1000),
                    "retry_count": max(metric["retry_count"], attempts),
                    "fallback_used": False,
                }
            )
            info = {
                "image_path": _display_path(image_path, repo_root),
                "meta_path": _display_path(meta_path, repo_root),
                "source": "fallback_fast",
                "provider": result.provider,
                "model_id": result.model_id,
                "preview_url": "/" + _display_path(image_path, repo_root).lstrip("/"),
                "timing_ms": dict(metric),
                "reference_stack": [{"role": "uv_engineering_guide", "path": guide_display_path}] if guide_display_path else [],
                **info_common,
            }
            part_metrics[part] = dict(metric)
            return part, info, None
        except ImageProviderError as exc:
            last_error = str(exc)

        if fallback_dir is not None:
            info = _use_fallback_asset(part, fallback_dir, parts_dir)
            if info is not None:
                metric["fallback_used"] = True
                metric["total_ms"] = int((time.perf_counter() - part_started) * 1000)
                fallback_used.append(part)
                info["image_path"] = _display_path(info["image_path"], repo_root)
                info["meta_path"] = _display_path(info["meta_path"], repo_root)
                info["preview_url"] = "/" + info["image_path"].lstrip("/")
                info["timing_ms"] = dict(metric)
                info["reference_stack"] = [{"role": "uv_engineering_guide", "path": guide_display_path}] if guide_display_path else []
                info.update(info_common)
                part_metrics[part] = dict(metric)
                return part, info, None

        part_metrics[part] = dict(metric)
        return part, None, last_error or "Image generation failed."

    completed_count = 0
    for wave_index, wave in enumerate(waves, start=1):
        if cancel_event and cancel_event.is_set():
            break
        _emit(
            progress,
            {
                "type": "wave_started",
                "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                "status": "running",
                "wave_index": wave_index,
                "wave_parts": wave,
            },
        )
        max_workers = max(1, min(int(request.max_parallel or 1), len(wave)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(generate_part, part, wave_index): part for part in wave}
            for future in as_completed(futures):
                part, info, error = future.result()
                if error == "cancelled":
                    continue
                if info is not None:
                    generated[part] = info
                    completed_count += 1
                    _emit(
                        progress,
                        {
                            "type": "part_completed",
                            "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                            "part": part,
                            "wave_index": wave_index,
                            "status": info.get("source") or "completed",
                            "preview_url": info.get("preview_url"),
                            "timing_ms": info.get("timing_ms"),
                            "completed_count": completed_count,
                            "requested_count": len(requested),
                            "log": info.get("source"),
                        },
                    )
                else:
                    errors[part] = error or "Image generation failed."
                    _emit(
                        progress,
                        {
                            "type": "part_failed",
                            "stage": "core_materialization" if wave_index == 1 else "full_assembly",
                            "part": part,
                            "wave_index": wave_index,
                            "status": "failed",
                            "log": errors[part],
                        },
                    )

    hero_result: dict[str, Any] | None = None
    if request.hero_render and not (cancel_event and cancel_event.is_set()):
        try:
            _emit(progress, {"type": "hero_started", "stage": "hero_finish", "status": "running"})
            hero_spec = provider_profile["hero_render"]
            result = _provider_attempt(
                hero_spec,
                prompt=_hero_prompt(
                    spec,
                    list(generated.keys()),
                    request.tracking_source,
                    effective_generation_brief,
                    user_armor_profile=user_armor_profile,
                    style_variation=style_variation,
                ),
                api_key_override=request.api_key,
                references=None,
                aspect_ratio="1:1",
                image_size="2K",
                timeout_seconds=request.timeout,
                progress=None,
            )
            hero_dir = session_dir / "artifacts" / "hero"
            hero_dir.mkdir(parents=True, exist_ok=True)
            ext = extension_for_mime(result.mime_type)
            hero_path = save_image(result, output_path=hero_dir / f"hero-poster{ext}")
            hero_meta_path = write_generation_meta(hero_dir / "hero-poster.generation.json", result=result, kind="hero_poster")
            hero_result = {
                "image_path": _display_path(hero_path, repo_root),
                "meta_path": _display_path(hero_meta_path, repo_root),
                "preview_url": "/" + _display_path(hero_path, repo_root).lstrip("/"),
                "provider": result.provider,
                "model_id": result.model_id,
                "timing_ms": {
                    "queue_wait_ms": result.queue_wait_ms,
                    "inference_ms": result.inference_ms,
                    "total_ms": result.total_ms,
                },
            }
            _emit(
                progress,
                {
                    "type": "hero_completed",
                    "stage": "hero_finish",
                    "status": "completed",
                    "preview_url": hero_result["preview_url"],
                    "timing_ms": hero_result["timing_ms"],
                },
            )
        except Exception as exc:  # noqa: BLE001
            _emit(progress, {"type": "hero_failed", "stage": "hero_finish", "status": "failed", "log": str(exc)})

    if request.update_suitspec:
        modules = spec.setdefault("modules", {})
        generation = spec.setdefault("generation", {})
        generation["texture_mode"] = request.texture_mode
        generation["uv_refine"] = bool(request.uv_refine)
        generation["provider_profile"] = request.provider_profile
        generation["tracking_source"] = request.tracking_source
        generation["last_generation_brief"] = effective_generation_brief or ""
        generation["last_generation_brief_raw"] = request.generation_brief or ""
        generation["last_operator_profile_raw"] = operator_context["operator_profile_raw"] or {}
        generation["last_operator_profile_resolved"] = operator_context["operator_profile_resolved"] or {}
        generation["last_user_armor_profile"] = user_armor_profile or {}
        generation["last_emotion_profile_raw"] = emotion_context["emotion_profile_raw"] or {}
        generation["last_emotion_profile_resolved"] = emotion_context["emotion_profile_resolved"] or {}
        generation["last_style_variation"] = style_variation or {}
        generation["last_resolved_defaults"] = emotion_context["resolved_defaults"] or {}
        generation["part_prompts"] = prompts
        for part, info in generated.items():
            module = modules.setdefault(part, {"enabled": True, "asset_ref": f"modules/{part}/base.prefab"})
            module["texture_path"] = info["image_path"]
        write_json(suitspec_path, spec)

    summary_path = parts_dir / "parts.generation.summary.json"
    summary = {
        "session_id": session_id,
        "provider_profile": request.provider_profile,
        "priority_mode": request.priority_mode,
        "tracking_source": request.tracking_source,
        "operator_profile_raw": operator_context["operator_profile_raw"],
        "operator_profile_resolved": operator_context["operator_profile_resolved"],
        "operator_resolved_defaults": operator_context["resolved_defaults"],
        "user_armor_profile": user_armor_profile,
        "emotion_profile": emotion_context["emotion_profile_resolved"],
        "emotion_profile_raw": emotion_context["emotion_profile_raw"],
        "emotion_profile_resolved": emotion_context["emotion_profile_resolved"],
        "emotion_directives": emotion_context["emotion_directives"],
        "style_variation": style_variation,
        "resolved_defaults": emotion_context["resolved_defaults"],
        "generation_brief_raw": request.generation_brief,
        "generation_brief": effective_generation_brief,
        "texture_mode": request.texture_mode,
        "uv_refine": bool(request.uv_refine),
        "requested_parts": requested,
        "waves": waves,
        "design_dna": design_dna,
        "uv_contracts": uv_contracts,
        "uv_guides": {
            part: {
                **serialize_uv_guide(info),
                "path": _display_path(info["path"], repo_root),
                "mesh_asset_ref": resolve_mesh_asset_ref(part, spec.get("modules", {}).get(part)),
            }
            for part, info in uv_guides.items()
        },
        "prompts": prompts,
        "refine_prompts": refine_prompts,
        "fallback_dir": _display_path(fallback_dir, repo_root) if fallback_dir else None,
        "fallback_used": fallback_used,
        "cache_hits": cache_hits,
        "generated": generated,
        "hero_result": hero_result,
        "errors": errors,
        "part_metrics": part_metrics,
        "cancelled_parts": cancelled_parts,
        "total_elapsed_sec": round(time.perf_counter() - started_at, 3),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = len(errors) == 0 and not cancelled_parts
    _emit(
        progress,
        {
            "type": "job_completed" if ok else ("job_cancelled" if cancelled_parts else "job_failed"),
            "stage": "complete" if ok else "error",
            "status": "completed" if ok else ("cancelled" if cancelled_parts else "failed"),
            "session_id": session_id,
            "summary_path": "/" + _display_path(summary_path, repo_root).lstrip("/"),
            "generated_count": len(generated),
            "error_count": len(errors),
            "fallback_used_count": len(fallback_used),
            "cache_hit_count": len(cache_hits),
            "hero_preview_url": hero_result["preview_url"] if hero_result else None,
        },
    )

    return {
        "ok": ok,
        "session_id": session_id,
        "generated_count": len(generated),
        "error_count": len(errors),
        "fallback_used_count": len(fallback_used),
        "cache_hit_count": len(cache_hits),
        "summary_path": _display_path(summary_path, repo_root),
        "hero_preview_url": hero_result["preview_url"] if hero_result else None,
        "total_elapsed_sec": summary["total_elapsed_sec"],
    }


__all__ = [
    "DEFAULT_PROVIDER_PROFILE",
    "GenerationRequest",
    "ProviderSpec",
    "_resolve_fallback_image",
    "_use_fallback_asset",
    "build_generation_cache_key",
    "build_generation_waves",
    "resolve_provider_profile",
    "run_generate_parts",
]
