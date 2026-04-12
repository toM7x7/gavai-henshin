"""Mesh asset helpers shared between backend generation flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .validators import load_json


def resolve_mesh_asset_ref(part: str, module: dict[str, Any] | None) -> str:
    ref = str((module or {}).get("asset_ref") or "").replace("\\", "/").strip()
    if ref.lower().endswith(".mesh.json"):
        return ref
    return f"viewer/assets/meshes/{part}.mesh.json"


def resolve_mesh_asset_path(
    part: str,
    module: dict[str, Any] | None,
    *,
    repo_root: Path | None = None,
) -> Path:
    ref = resolve_mesh_asset_ref(part, module)
    path = Path(ref)
    if not path.is_absolute():
        base = repo_root or Path.cwd()
        path = (base / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Mesh asset not found for part={part}: {path}")
    return path


def load_mesh_payload(mesh_path: Path) -> dict[str, Any]:
    payload = load_json(mesh_path)
    if payload.get("format") != "mesh.v1":
        raise ValueError(f"Unsupported mesh format: {mesh_path}")
    uv = payload.get("uv") or payload.get("uvs")
    if not isinstance(uv, list) or len(uv) < 6 or len(uv) % 2 != 0:
        raise ValueError(f"Mesh UV data is missing or invalid: {mesh_path}")
    positions = payload.get("positions")
    if not isinstance(positions, list) or len(positions) < 9 or len(positions) % 3 != 0:
        raise ValueError(f"Mesh positions are missing or invalid: {mesh_path}")
    payload["uv"] = uv
    return payload

