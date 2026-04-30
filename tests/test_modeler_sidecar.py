"""Tests for ``henshin.modeler_sidecar.load_modeler_sidecar``."""

from __future__ import annotations

import json
from pathlib import Path

from henshin.modeler_sidecar import SIDECAR_KEYS, load_modeler_sidecar


def _write_sidecar(repo_root: Path, module: str, payload: dict) -> Path:
    target_dir = repo_root / "viewer" / "assets" / "armor-parts" / module
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{module}.modeler.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_modeler_sidecar_returns_normalized_dict_when_present(tmp_path: Path) -> None:
    module = "chest"
    payload = {
        "bbox_m": {"x": 0.64, "y": 0.5, "z": 0.16},
        "triangles": 1450,
        "material_zones": ["base", "emissive"],
        "vrm_attachment": {
            "primary_bone": "upperChest",
            "offset_m": [0.0, 0.0, 0.02],
            "rotation_deg": [0.0, 0.0, 0.0],
            "fallback_bones": ["chest", "spine"],
        },
        "external_glb_target": f"viewer/assets/armor-parts/{module}/{module}.glb",
    }
    _write_sidecar(tmp_path, module, payload)

    result = load_modeler_sidecar(module, repo_root=tmp_path)

    assert isinstance(result, dict)
    assert result["module"] == module
    for key in SIDECAR_KEYS:
        assert key in result, f"missing required key {key!r}"
    assert result["bbox_m"] == payload["bbox_m"]
    assert result["triangles"] == 1450
    assert result["material_zones"] == ["base", "emissive"]
    assert result["vrm_attachment"]["primary_bone"] == "upperChest"
    # Pass-through key preserved.
    assert result["external_glb_target"] == payload["external_glb_target"]


def test_load_modeler_sidecar_returns_none_when_missing(tmp_path: Path) -> None:
    # No file written under tmp_path/viewer/assets/armor-parts/back/back.modeler.json
    assert load_modeler_sidecar("back", repo_root=tmp_path) is None
    # Empty / whitespace module ids are also rejected without raising.
    assert load_modeler_sidecar("", repo_root=tmp_path) is None
    assert load_modeler_sidecar("   ", repo_root=tmp_path) is None
