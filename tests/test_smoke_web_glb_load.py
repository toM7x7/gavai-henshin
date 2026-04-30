"""Tests for ``tools/smoke_web_glb_load.py``.

Covers three scenarios:

1. Pass case against the real checkout: every module resolves to a GLB and
   ``previewFallbackParts == 0``.
2. Tmp-dir case with no GLBs anywhere: every module falls back, so
   ``previewFallbackParts == 18``.
3. Tmp-dir case where one sidecar is malformed (missing ``vrm_attachment``):
   the smoke check must report failure for that module gracefully without
   crashing.
"""

from __future__ import annotations

import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TOOL_PATH = _REPO_ROOT / "tools" / "smoke_web_glb_load.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("smoke_web_glb_load", _TOOL_PATH)
    assert spec and spec.loader, "could not load smoke verifier module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["smoke_web_glb_load"] = module
    spec.loader.exec_module(module)
    return module


smoke = _load_smoke_module()

_P0_REQUIRED_TOPPING_SLOTS = {
    "helmet": ["crest", "visor_trim"],
    "chest": ["chest_core", "rib_trim"],
    "back": ["spine_ridge", "rear_core"],
    "waist": ["belt_buckle", "side_clip"],
    "left_shoulder": ["shoulder_fin", "edge_trim"],
    "right_shoulder": ["shoulder_fin", "edge_trim"],
    "left_shin": ["shin_spike", "ankle_cuff_trim"],
    "right_shin": ["shin_spike", "ankle_cuff_trim"],
}


# ---------------------------------------------------------------------------
# Synthetic GLB builder (mirrors tests/test_validate_armor_part.py)
# ---------------------------------------------------------------------------


def _pack_glb(json_obj: dict[str, Any]) -> bytes:
    json_bytes = json.dumps(json_obj, separators=(",", ":")).encode("utf-8")
    pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * pad
    chunks = bytearray()
    chunks += struct.pack("<II", len(json_bytes), 0x4E4F534A)  # JSON
    chunks += json_bytes
    total_length = 12 + len(chunks)
    header = struct.pack("<III", 0x46546C67, 2, total_length)
    return bytes(header + chunks)


def _build_minimal_glb(
    *,
    bbox_m: dict[str, float] | None = None,
) -> bytes:
    bbox = bbox_m or {"x": 0.20, "y": 0.20, "z": 0.20}
    half = [float(bbox[axis]) / 2.0 for axis in ("x", "y", "z")]
    return _pack_glb(
        {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": "synthetic_armor_part"}],
            "meshes": [
                {
                    "name": "synthetic_armor_mesh",
                    "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}],
                }
            ],
            "accessors": [
                {
                    "componentType": 5126,
                    "count": 8,
                    "max": [half[0], half[1], half[2]],
                    "min": [-half[0], -half[1], -half[2]],
                    "type": "VEC3",
                },
                {"componentType": 5123, "count": 12, "type": "SCALAR"},
            ],
            "bufferViews": [],
            "buffers": [{"byteLength": 0}],
        }
    )


def _write_glb_for_module(
    repo_root: Path,
    module: str,
    *,
    bbox_m: dict[str, float] | None = None,
) -> Path:
    base = repo_root / "viewer" / "assets" / "armor-parts" / module
    base.mkdir(parents=True, exist_ok=True)
    glb_path = base / f"{module}.glb"
    glb_path.write_bytes(_build_minimal_glb(bbox_m=bbox_m))
    return glb_path


def _write_sidecar_for_module(
    repo_root: Path,
    module: str,
    *,
    primary_bone: str,
    bbox_m: dict[str, float] | None = None,
    offset_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
    drop_attachment: bool = False,
) -> Path:
    base = repo_root / "viewer" / "assets" / "armor-parts" / module
    base.mkdir(parents=True, exist_ok=True)
    bbox = bbox_m or {"x": 0.20, "y": 0.20, "z": 0.20}
    payload: dict[str, Any] = {
        "contract_version": "modeler-part-sidecar.v1",
        "module": module,
        "part_id": f"viewer.mesh.{module}.v1",
        "category": "armor",
        "bbox_m": {
            "x": bbox["x"],
            "y": bbox["y"],
            "z": bbox["z"],
            "size": [bbox["x"], bbox["y"], bbox["z"]],
        },
        "triangle_count": 8,
        "material_zones": ["base_surface"],
        "texture_provider_profile": "nano_banana",
        "vrm_attachment": {
            "primary_bone": primary_bone,
            "offset_m": list(offset_m),
            "rotation_deg": [0, 0, 0],
            "fallback_bones": [primary_bone],
        },
    }
    if module in _P0_REQUIRED_TOPPING_SLOTS:
        payload.update(
            {
                "variant_key": "sleek",
                "base_motif_link": {"name": f"{module}_motif", "surface_zone": "accent"},
                "topping_slots": [
                    {
                        "topping_slot": slot,
                        "slot_transform": {"anchor": [0, 0, 0], "rotation_deg": [0, 0, 0]},
                        "max_bbox_m": {"x": 0.05, "y": 0.05, "z": 0.05},
                        "conflicts_with": [],
                        "parent_module": module,
                    }
                    for slot in _P0_REQUIRED_TOPPING_SLOTS[module]
                ],
            }
        )
    if drop_attachment:
        payload.pop("vrm_attachment")
    sidecar_path = base / f"{module}.modeler.json"
    sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sidecar_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_actual_repo_resolves_eighteen_glbs_and_passes_acceptance_metadata() -> None:
    report = smoke.smoke_check_web_glb_load(repo_root=_REPO_ROOT)
    assert report["preview_fallback_parts"] == 0, report["failures"]
    assert report["preview_glb_parts"] == 18, report["modules"]
    assert report["ok"] is True, report["failures"]
    assert not any("P0 metadata" in failure for failure in report["failures"])


def test_tmp_dir_with_no_glbs_falls_back_for_every_module(tmp_path: Path) -> None:
    # Only create the armor-parts root so the helper has somewhere to look,
    # but write zero GLBs. Every module should be counted as a fallback.
    (tmp_path / "viewer" / "assets" / "armor-parts").mkdir(parents=True)

    report = smoke.smoke_check_web_glb_load(repo_root=tmp_path)

    assert report["preview_glb_parts"] == 0
    assert report["preview_fallback_parts"] == 18
    assert report["ok"] is False
    assert len(report["failures"]) >= 18
    assert all(entry.get("would_fallback") is True for entry in report["modules"])

    # The CLI surface should also exit non-zero.
    rc = smoke.main(["--repo-root", str(tmp_path)])
    assert rc != 0


def test_malformed_sidecar_fails_gracefully_without_crash(tmp_path: Path, capsys) -> None:
    modules = list(smoke.expected_modules())
    target = "helmet"
    primary_bone = "head"

    # Stand up a fully-valid set for every module first.
    from henshin.armor_fit_contract import ARMOR_SLOT_SPECS, normalize_slot_id

    for module in modules:
        target_bbox = smoke._reference_target_dimensions(module)
        _write_glb_for_module(tmp_path, module, bbox_m=target_bbox)
        spec = ARMOR_SLOT_SPECS[normalize_slot_id(module)]
        _write_sidecar_for_module(
            tmp_path,
            module,
            primary_bone=spec.body_anchor,
            bbox_m=target_bbox,
        )

    # Now corrupt one sidecar by dropping vrm_attachment entirely.
    _write_sidecar_for_module(
        tmp_path,
        target,
        primary_bone=primary_bone,
        bbox_m=smoke._reference_target_dimensions(target),
        drop_attachment=True,
    )

    # The smoke check must run end-to-end, not raise.
    report = smoke.smoke_check_web_glb_load(repo_root=tmp_path)

    # The corrupted module should fail gracefully and not propagate as a
    # fallback; the GLB still resolves, but the sidecar is rejected.
    assert report["preview_glb_parts"] == 18
    assert report["preview_fallback_parts"] == 0
    assert report["ok"] is False
    target_entry = next(entry for entry in report["modules"] if entry["module"] == target)
    assert target_entry["ok"] is False
    assert any("vrm_attachment" in failure for failure in report["failures"])

    # CLI form: must return non-zero and emit the summary line without raising.
    rc = smoke.main(["--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc != 0
    assert "previewGlbParts=" in captured.out
    assert "previewFallbackParts=" in captured.out


def test_back_glb_too_thin_fails_even_when_sidecar_matches(tmp_path: Path) -> None:
    from henshin.armor_fit_contract import ARMOR_SLOT_SPECS, normalize_slot_id

    module = "back"
    target_bbox = smoke._reference_target_dimensions(module)
    thin_bbox = {**target_bbox, "z": target_bbox["z"] * 0.40}
    _write_glb_for_module(tmp_path, module, bbox_m=thin_bbox)
    _write_sidecar_for_module(
        tmp_path,
        module,
        primary_bone=ARMOR_SLOT_SPECS[normalize_slot_id(module)].body_anchor,
        bbox_m=thin_bbox,
    )

    report = smoke.smoke_check_web_glb_load(repo_root=tmp_path, modules=[module])

    assert report["preview_glb_parts"] == 1
    assert report["preview_fallback_parts"] == 0
    assert report["ok"] is False
    assert any(
        "back GLB z thickness too thin" in failure or "bbox_m exceeds target envelope" in failure
        for failure in report["failures"]
    )


def test_sidecar_glb_bbox_mismatch_is_reported_before_preview_can_drift(tmp_path: Path) -> None:
    from henshin.armor_fit_contract import ARMOR_SLOT_SPECS, normalize_slot_id

    module = "chest"
    target_bbox = smoke._reference_target_dimensions(module)
    stale_sidecar_bbox = {**target_bbox, "z": target_bbox["z"] * 0.95}
    _write_glb_for_module(tmp_path, module, bbox_m=target_bbox)
    _write_sidecar_for_module(
        tmp_path,
        module,
        primary_bone=ARMOR_SLOT_SPECS[normalize_slot_id(module)].body_anchor,
        bbox_m=stale_sidecar_bbox,
    )

    report = smoke.smoke_check_web_glb_load(repo_root=tmp_path, modules=[module])

    assert report["preview_glb_parts"] == 1
    assert report["preview_fallback_parts"] == 0
    assert report["ok"] is False
    assert any("sidecar bbox_m differs from GLB bounds" in failure for failure in report["failures"])
    chest = report["modules"][0]
    assert chest["sidecar_glb_bbox_outside_tolerance_axes"] == ["z"]


def test_web_preview_parts_contract_detects_missing_module(tmp_path: Path) -> None:
    forge_dir = tmp_path / "viewer" / "armor-forge"
    forge_dir.mkdir(parents=True)
    (forge_dir / "forge.js").write_text(
        'const PARTS = [["helmet", "Helmet", true], ["chest", "Chest", true]];\n',
        encoding="utf-8",
    )

    report = smoke.smoke_check_web_glb_load(repo_root=tmp_path, modules=[])

    assert report["web_preview_contract"]["ok"] is False
    assert "back" in report["web_preview_contract"]["missing_parts"]
    assert any("Web Forge PARTS missing expected modules" in failure for failure in report["failures"])
