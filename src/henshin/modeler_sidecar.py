"""Reader for ``<module>.modeler.json`` armor sidecars.

The sidecar is delivered alongside each external GLB at
``viewer/assets/armor-parts/<module>/<module>.modeler.json``. It mirrors the
``runtime_bindings`` and ``vrm_attachment`` fields documented in
``src/henshin/modeler_blueprints.py`` and gives the runtime a stable place to
look up bbox / triangle / material / attachment metadata once the GLB has
been authored.

This module deliberately does not require the sidecar — when missing or
malformed it simply returns ``None`` and the caller is expected to fall back
to the seed proxy contract (``viewer/assets/meshes/<module>.mesh.json``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SIDECAR_KEYS: tuple[str, ...] = ("bbox_m", "triangles", "material_zones", "vrm_attachment")


def _sidecar_path(module: str, repo_root: str | Path) -> Path:
    name = str(module or "").strip()
    if not name:
        return Path(repo_root) / ""
    return Path(repo_root) / "viewer" / "assets" / "armor-parts" / name / f"{name}.modeler.json"


def load_modeler_sidecar(module: str, repo_root: str | Path = ".") -> dict[str, Any] | None:
    """Load the armor modeler sidecar for ``module`` if present.

    Returns a normalized dict with at least the keys listed in
    :data:`SIDECAR_KEYS` (``bbox_m``, ``triangles``, ``material_zones``,
    ``vrm_attachment``). Missing top-level keys are filled with ``None`` so
    the caller can use plain ``dict.get`` access without further guards.

    Returns ``None`` when the file is missing, unreadable, or not valid JSON.
    No exceptions are propagated for those cases — they are recoverable
    fallbacks (the proxy ``mesh.json`` path remains the runtime's safety
    net).
    """

    name = str(module or "").strip()
    if not name:
        return None

    path = _sidecar_path(name, repo_root)
    if not path.is_file():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    normalized: dict[str, Any] = dict(payload)
    for key in SIDECAR_KEYS:
        normalized.setdefault(key, None)
    normalized["module"] = name
    return normalized
