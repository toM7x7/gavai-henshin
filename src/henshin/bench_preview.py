"""Build dashboard-readable SuitSpec previews from prompt bench outputs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _repo_relative(path: str | Path, repo_root: str | Path) -> str:
    root = Path(repo_root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path must be inside repo root: {resolved}") from exc


def resolve_bench_output_image(
    summary: dict[str, Any],
    *,
    variant_key: str | None = None,
) -> tuple[str, Path]:
    """Return the selected live output variant and image path from a bench summary."""

    live_outputs = summary.get("live_outputs")
    if not isinstance(live_outputs, dict) or not live_outputs:
        raise ValueError("Bench summary does not contain live_outputs. Run the bench with --live or pass --image.")

    selected_key = variant_key
    if selected_key is None:
        if len(live_outputs) != 1:
            keys = ", ".join(sorted(live_outputs))
            raise ValueError(f"Multiple live outputs found; pass --variant. Available: {keys}")
        selected_key = next(iter(live_outputs))

    selected = live_outputs.get(selected_key)
    if not isinstance(selected, dict):
        keys = ", ".join(sorted(live_outputs))
        raise ValueError(f"Unknown live output variant: {selected_key}. Available: {keys}")

    image_path = selected.get("image_path")
    if not image_path:
        raise ValueError(f"Live output variant has no image_path: {selected_key}")
    return selected_key, Path(str(image_path))


def resolve_batch_output_images(
    summary: dict[str, Any],
    *,
    variant_key: str | None = None,
) -> tuple[str | None, dict[str, Path]]:
    """Return {part: image_path} from a multi-part bench summary."""

    results = summary.get("results")
    if not isinstance(results, dict) or not results:
        raise ValueError("Batch summary does not contain results.")

    images: dict[str, Path] = {}
    selected_variant: str | None = variant_key
    for part, result in results.items():
        if not isinstance(result, dict):
            continue
        live_outputs = result.get("live_outputs")
        if not isinstance(live_outputs, dict) or not live_outputs:
            continue
        part_variant = selected_variant
        if part_variant is None:
            if len(live_outputs) != 1:
                keys = ", ".join(sorted(live_outputs))
                raise ValueError(f"Multiple live outputs found for {part}; pass --variant. Available: {keys}")
            part_variant = next(iter(live_outputs))
            selected_variant = part_variant
        selected = live_outputs.get(part_variant)
        if not isinstance(selected, dict):
            keys = ", ".join(sorted(live_outputs))
            raise ValueError(f"Unknown live output variant for {part}: {part_variant}. Available: {keys}")
        image_path = selected.get("image_path")
        if image_path:
            images[str(part)] = Path(str(image_path))

    if not images:
        raise ValueError("No live output images found in batch summary.")
    return selected_variant, images


def build_preview_suitspec(
    base_suitspec: dict[str, Any],
    *,
    part: str,
    texture_path: str | Path,
    repo_root: str | Path,
    only_part: bool = True,
    variant_key: str | None = None,
    source_summary_path: str | Path | None = None,
    fit_summary: dict[str, Any] | None = None,
    fit_summary_path: str | Path | None = None,
    preview_label: str | None = None,
) -> dict[str, Any]:
    """Overlay a generated texture onto one module for dashboard/body-fit preview."""

    spec = copy.deepcopy(base_suitspec)
    modules = spec.get("modules")
    if not isinstance(modules, dict) or part not in modules:
        raise ValueError(f"SuitSpec has no module named {part!r}")

    texture_rel = _repo_relative(texture_path, repo_root)
    if only_part:
        for name, module in modules.items():
            if isinstance(module, dict):
                module["enabled"] = name == part

    target = modules[part]
    if not isinstance(target, dict):
        raise ValueError(f"SuitSpec module must be an object: {part}")
    target["enabled"] = True
    target["texture_path"] = texture_rel
    fit_applied = False
    if fit_summary:
        fit_by_part = fit_summary.get("fitByPart")
        anchor_by_part = fit_summary.get("anchorByPart")
        if isinstance(fit_by_part, dict) and isinstance(fit_by_part.get(part), dict):
            target["fit"] = copy.deepcopy(fit_by_part[part])
            fit_applied = True
        if isinstance(anchor_by_part, dict) and isinstance(anchor_by_part.get(part), dict):
            target["vrm_anchor"] = copy.deepcopy(anchor_by_part[part])
            fit_applied = True

    generation = spec.setdefault("generation", {})
    if not isinstance(generation, dict):
        generation = {}
        spec["generation"] = generation

    preview_source: dict[str, Any] = {
        "type": "bench_texture_preview",
        "part": part,
        "texture_path": texture_rel,
        "variant": variant_key,
        "only_part": only_part,
        "fit_applied": fit_applied,
    }
    if source_summary_path is not None:
        preview_source["source_summary"] = _repo_relative(source_summary_path, repo_root)
    if fit_summary_path is not None:
        preview_source["fit_summary"] = _repo_relative(fit_summary_path, repo_root)
    if preview_label:
        preview_source["label"] = preview_label
    generation["preview_source"] = preview_source

    text = spec.setdefault("text", {})
    if isinstance(text, dict):
        text["callout"] = preview_label or f"Body-fit preview: {part} bench texture"

    return spec


def build_batch_preview_suitspec(
    base_suitspec: dict[str, Any],
    *,
    part_textures: dict[str, str | Path],
    repo_root: str | Path,
    only_parts: bool = True,
    variant_key: str | None = None,
    source_summary_path: str | Path | None = None,
    fit_summary: dict[str, Any] | None = None,
    fit_summary_path: str | Path | None = None,
    preview_label: str | None = None,
) -> dict[str, Any]:
    """Overlay generated textures onto multiple modules for full-body preview."""

    spec = copy.deepcopy(base_suitspec)
    modules = spec.get("modules")
    if not isinstance(modules, dict):
        raise ValueError("SuitSpec.modules must be an object.")

    normalized: dict[str, str] = {}
    for part, image_path in part_textures.items():
        if part not in modules:
            raise ValueError(f"SuitSpec has no module named {part!r}")
        normalized[part] = _repo_relative(image_path, repo_root)

    if only_parts:
        for name, module in modules.items():
            if isinstance(module, dict):
                module["enabled"] = name in normalized

    fit_by_part = fit_summary.get("fitByPart") if isinstance(fit_summary, dict) else None
    anchor_by_part = fit_summary.get("anchorByPart") if isinstance(fit_summary, dict) else None
    fit_applied_parts: list[str] = []

    for part, texture_rel in normalized.items():
        module = modules[part]
        if not isinstance(module, dict):
            raise ValueError(f"SuitSpec module must be an object: {part}")
        module["enabled"] = True
        module["texture_path"] = texture_rel
        fit_applied = False
        if isinstance(fit_by_part, dict) and isinstance(fit_by_part.get(part), dict):
            module["fit"] = copy.deepcopy(fit_by_part[part])
            fit_applied = True
        if isinstance(anchor_by_part, dict) and isinstance(anchor_by_part.get(part), dict):
            module["vrm_anchor"] = copy.deepcopy(anchor_by_part[part])
            fit_applied = True
        if fit_applied:
            fit_applied_parts.append(part)

    generation = spec.setdefault("generation", {})
    if not isinstance(generation, dict):
        generation = {}
        spec["generation"] = generation
    preview_source: dict[str, Any] = {
        "type": "bench_batch_texture_preview",
        "parts": sorted(normalized),
        "textures": normalized,
        "variant": variant_key,
        "only_parts": only_parts,
        "fit_applied_parts": fit_applied_parts,
    }
    if source_summary_path is not None:
        preview_source["source_summary"] = _repo_relative(source_summary_path, repo_root)
    if fit_summary_path is not None:
        preview_source["fit_summary"] = _repo_relative(fit_summary_path, repo_root)
    if preview_label:
        preview_source["label"] = preview_label
    generation["preview_source"] = preview_source

    text = spec.setdefault("text", {})
    if isinstance(text, dict):
        text["callout"] = preview_label or f"Body-fit preview: {len(normalized)} bench textures"

    return spec


def write_preview_suitspec(
    *,
    base_suitspec_path: str | Path,
    output_path: str | Path,
    repo_root: str | Path,
    part: str = "helmet",
    image_path: str | Path | None = None,
    bench_summary_path: str | Path | None = None,
    variant_key: str | None = None,
    only_part: bool = True,
    fit_summary_path: str | Path | None = None,
    preview_label: str | None = None,
) -> dict[str, Any]:
    """Write a preview SuitSpec and return UI-friendly metadata."""

    repo_root = Path(repo_root).resolve()
    base_suitspec_path = Path(base_suitspec_path)
    if not base_suitspec_path.is_absolute():
        base_suitspec_path = repo_root / base_suitspec_path

    selected_variant = variant_key
    selected_image = Path(image_path) if image_path else None
    summary_path = Path(bench_summary_path) if bench_summary_path else None
    if summary_path is not None and not summary_path.is_absolute():
        summary_path = repo_root / summary_path

    if selected_image is None:
        if summary_path is None:
            raise ValueError("Pass either image_path or bench_summary_path.")
        selected_variant, selected_image = resolve_bench_output_image(
            _load_json(summary_path),
            variant_key=variant_key,
        )

    if selected_image is None:
        raise ValueError("No preview image resolved.")
    if not selected_image.is_absolute():
        selected_image = repo_root / selected_image
    if not selected_image.exists():
        raise FileNotFoundError(selected_image)

    resolved_fit_summary_path = Path(fit_summary_path) if fit_summary_path else None
    if resolved_fit_summary_path is not None and not resolved_fit_summary_path.is_absolute():
        resolved_fit_summary_path = repo_root / resolved_fit_summary_path
    fit_summary = _load_json(resolved_fit_summary_path) if resolved_fit_summary_path is not None else None

    spec = build_preview_suitspec(
        _load_json(base_suitspec_path),
        part=part,
        texture_path=selected_image,
        repo_root=repo_root,
        only_part=only_part,
        variant_key=selected_variant,
        source_summary_path=summary_path,
        fit_summary=fit_summary,
        fit_summary_path=resolved_fit_summary_path,
        preview_label=preview_label,
    )

    output = Path(output_path)
    if not output.is_absolute():
        output = repo_root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "path": _repo_relative(output, repo_root),
        "absolute_path": str(output.resolve()),
        "part": part,
        "texture_path": _repo_relative(selected_image, repo_root),
        "variant": selected_variant,
        "only_part": only_part,
        "fit_applied": bool(fit_summary),
    }


def write_batch_preview_suitspec(
    *,
    base_suitspec_path: str | Path,
    output_path: str | Path,
    repo_root: str | Path,
    batch_summary_path: str | Path,
    variant_key: str | None = None,
    only_parts: bool = True,
    fit_summary_path: str | Path | None = None,
    preview_label: str | None = None,
) -> dict[str, Any]:
    """Write a preview SuitSpec from a multi-part prompt bench summary."""

    repo_root = Path(repo_root).resolve()
    base_suitspec_path = Path(base_suitspec_path)
    if not base_suitspec_path.is_absolute():
        base_suitspec_path = repo_root / base_suitspec_path
    summary_path = Path(batch_summary_path)
    if not summary_path.is_absolute():
        summary_path = repo_root / summary_path

    selected_variant, part_images = resolve_batch_output_images(
        _load_json(summary_path),
        variant_key=variant_key,
    )
    resolved_images: dict[str, Path] = {}
    for part, image_path in part_images.items():
        resolved = image_path if image_path.is_absolute() else repo_root / image_path
        if not resolved.exists():
            raise FileNotFoundError(resolved)
        resolved_images[part] = resolved

    resolved_fit_summary_path = Path(fit_summary_path) if fit_summary_path else None
    if resolved_fit_summary_path is not None and not resolved_fit_summary_path.is_absolute():
        resolved_fit_summary_path = repo_root / resolved_fit_summary_path
    fit_summary = _load_json(resolved_fit_summary_path) if resolved_fit_summary_path is not None else None

    spec = build_batch_preview_suitspec(
        _load_json(base_suitspec_path),
        part_textures=resolved_images,
        repo_root=repo_root,
        only_parts=only_parts,
        variant_key=selected_variant,
        source_summary_path=summary_path,
        fit_summary=fit_summary,
        fit_summary_path=resolved_fit_summary_path,
        preview_label=preview_label,
    )

    output = Path(output_path)
    if not output.is_absolute():
        output = repo_root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "path": _repo_relative(output, repo_root),
        "absolute_path": str(output.resolve()),
        "parts": sorted(resolved_images),
        "texture_count": len(resolved_images),
        "variant": selected_variant,
        "only_parts": only_parts,
        "fit_applied": bool(fit_summary),
    }
