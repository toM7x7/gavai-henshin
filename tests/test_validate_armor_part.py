"""Tests for tools/validate_armor_part.py.

Builds tiny synthetic GLB files in a tmp dir so we don't need real Blender
output or a third-party glTF library. Covers pass, bbox-too-big, missing
sidecar, and mirror-mismatch scenarios.
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
_TOOL_PATH = _REPO_ROOT / "tools" / "validate_armor_part.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_armor_part", _TOOL_PATH)
    assert spec and spec.loader, "could not load validator module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_armor_part"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_module()


# ---------------------------------------------------------------------------
# Synthetic GLB builder
# ---------------------------------------------------------------------------


def _pack_glb(json_obj: dict[str, Any], bin_blob: bytes = b"") -> bytes:
    json_bytes = json.dumps(json_obj, separators=(",", ":")).encode("utf-8")
    # Pad JSON chunk to 4 bytes with spaces.
    pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * pad
    bin_pad = (4 - (len(bin_blob) % 4)) % 4 if bin_blob else 0
    bin_bytes = bin_blob + (b"\x00" * bin_pad) if bin_blob else b""

    chunks = bytearray()
    chunks += struct.pack("<II", len(json_bytes), 0x4E4F534A)  # 'JSON'
    chunks += json_bytes
    if bin_bytes:
        chunks += struct.pack("<II", len(bin_bytes), 0x004E4942)  # 'BIN\0'
        chunks += bin_bytes

    total_length = 12 + len(chunks)
    header = struct.pack("<III", 0x46546C67, 2, total_length)  # 'glTF', version, total
    return bytes(header + chunks)


def _build_glb_payload(
    module: str,
    *,
    bbox_size: tuple[float, float, float],
    triangle_count: int = 6,
    materials: list[str] | None = None,
    mesh_name: str | None = None,
    inset: float | None = None,
) -> bytes:
    """Build a minimal valid GLB with one mesh and one or more materials.

    `bbox_size` controls the position accessor min/max (centered at origin).
    `inset` overrides the lateral inner inset (closest |x| or |z| to body axis).
    When `inset` is provided, bbox_min[0] = inset and bbox_max[0] = inset + size_x.
    """

    sx, sy, sz = bbox_size
    if inset is None:
        bmin = [-sx / 2, -sy / 2, -sz / 2]
        bmax = [sx / 2, sy / 2, sz / 2]
    else:
        bmin = [inset, -sy / 2, inset]
        bmax = [inset + sx, sy / 2, inset + sz]

    mesh_label = mesh_name or f"armor_{module}_v001"
    materials = materials or ["base_surface"]

    # We'll embed a tiny BIN chunk with two UV samples just to have something
    # to scan for the UV gate. Bytes are 4 vec2 floats = 32 bytes.
    uv_floats: list[float] = []
    for u, v in [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]:
        uv_floats.extend([u, v])
    bin_blob = struct.pack(f"<{len(uv_floats)}f", *uv_floats)

    gltf = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "name": mesh_label,
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "TEXCOORD_0": 1},
                        "indices": 2,
                        "material": 0,
                    }
                ],
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 4,
                "type": "VEC3",
                "min": bmin,
                "max": bmax,
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": 4,
                "type": "VEC2",
                "min": [0.0, 0.0],
                "max": [1.0, 1.0],
            },
            {
                "bufferView": 2,
                "componentType": 5123,  # UNSIGNED_SHORT
                "count": triangle_count * 3,
                "type": "SCALAR",
            },
        ],
        # The TEXCOORD_0 buffer view is the only one we actually need to point
        # at the BIN chunk for the UV scan; the others are referenced for
        # completeness but the validator only inspects accessor min/max.
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 0},
            {"buffer": 0, "byteOffset": 0, "byteLength": len(bin_blob)},
            {"buffer": 0, "byteOffset": 0, "byteLength": 0},
        ],
        "buffers": [{"byteLength": len(bin_blob)}],
        "materials": [{"name": name} for name in materials],
    }
    return _pack_glb(gltf, bin_blob=bin_blob)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _module_dir(repo_root: Path, module: str) -> Path:
    base = repo_root / "viewer" / "assets" / "armor-parts" / module
    base.mkdir(parents=True, exist_ok=True)
    (base / "preview").mkdir(parents=True, exist_ok=True)
    return base


def _write_glb(repo_root: Path, module: str, glb_bytes: bytes) -> Path:
    base = _module_dir(repo_root, module)
    glb_path = base / f"{module}.glb"
    glb_path.write_bytes(glb_bytes)
    return glb_path


def _write_sidecar(
    repo_root: Path,
    module: str,
    *,
    bbox_size: tuple[float, float, float],
    triangle_count: int,
    attachment_offset: tuple[float, float, float] | None = None,
) -> Path:
    base = _module_dir(repo_root, module)
    sidecar_path = base / f"{module}.modeler.json"
    payload: dict[str, Any] = {
        "module": module,
        "bbox_m": {"x": bbox_size[0], "y": bbox_size[1], "z": bbox_size[2]},
        "triangle_count": triangle_count,
    }
    if attachment_offset is not None:
        payload["vrm_attachment"] = {
            "offset_m": list(attachment_offset),
        }
    sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sidecar_path


def _write_preview(repo_root: Path, module: str) -> Path:
    base = _module_dir(repo_root, module)
    preview_path = base / "preview" / f"{module}.mesh.json"
    preview_path.write_text(
        json.dumps({"format": "mesh.v1", "name": module, "positions": [], "indices": []}),
        encoding="utf-8",
    )
    return preview_path


def _gate_status(report, name: str) -> str:
    for gate in report.gates:
        if gate.name == name:
            return gate.status
    raise AssertionError(f"gate '{name}' not present in report; gates={[g.name for g in report.gates]}")


def _setup_passing_module(
    repo_root: Path,
    module: str,
    *,
    bbox_size: tuple[float, float, float] | None = None,
    triangle_count: int = 6,
    inset: float | None = None,
    attachment_offset: tuple[float, float, float] | None = None,
) -> None:
    target = validator._reference_target_dimensions(module)
    bbox = bbox_size or (
        float(target["x"]) * 0.95,
        float(target["y"]) * 0.95,
        float(target["z"]) * 0.95,
    )
    # For body-clearance pass, push the bbox laterally so its inner inset
    # exceeds body_radius + clearance. Helmet/torso modules are centered on
    # the body axis; we use the sidecar offset compensation instead.
    glb_bytes = _build_glb_payload(
        module,
        bbox_size=bbox,
        triangle_count=triangle_count,
        materials=["base_surface"],
        inset=inset,
    )
    _write_glb(repo_root, module, glb_bytes)
    _write_sidecar(
        repo_root,
        module,
        bbox_size=bbox,
        triangle_count=triangle_count,
        attachment_offset=attachment_offset,
    )
    _write_preview(repo_root, module)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pass_case_for_left_shoulder(tmp_path: Path) -> None:
    module = "left_shoulder"
    partner = validator._MIRROR_PAIRS[module]
    target = validator._reference_target_dimensions(module)
    bbox = (float(target["x"]) * 0.95, float(target["y"]) * 0.95, float(target["z"]) * 0.95)
    # Push the GLB outward so it clears the shoulder body radius.
    inset = 0.20
    # Provide a sidecar offset large enough to compensate any inner inset.
    offset = (0.20, 0.0, 0.0)

    _setup_passing_module(
        tmp_path,
        module,
        bbox_size=bbox,
        triangle_count=8,
        inset=inset,
        attachment_offset=offset,
    )
    _setup_passing_module(
        tmp_path,
        partner,
        bbox_size=bbox,
        triangle_count=8,
        inset=inset,
        attachment_offset=offset,
    )

    report = validator.validate_module(tmp_path, module)

    assert report.ok, [g.to_dict() for g in report.gates if g.status == "fail"]
    assert _gate_status(report, "stable_part_name") == "pass"
    assert _gate_status(report, "bbox_within_target_envelope") == "pass"
    assert _gate_status(report, "single_surface_base_material_or_declared_slots") == "pass"
    assert _gate_status(report, "mirror_pair_dimension_delta_below_3_percent") == "pass"
    assert _gate_status(report, "sidecar_present_and_consistent") == "pass"
    assert _gate_status(report, "preview_mesh_present") == "pass"
    # Body-intersection gate may be pass or warn depending on inset/offset
    # arithmetic; both are acceptable here.
    body_gate = _gate_status(report, "no_body_intersection_at_reference_pose")
    assert body_gate in {"pass", "warn"}, body_gate


def test_bbox_too_big_fails(tmp_path: Path) -> None:
    module = "helmet"
    target = validator._reference_target_dimensions(module)
    # Make the bbox way larger than +5% slack on every axis.
    huge = (
        float(target["x"]) * 1.5,
        float(target["y"]) * 1.5,
        float(target["z"]) * 1.5,
    )
    glb_bytes = _build_glb_payload(module, bbox_size=huge, triangle_count=10)
    _write_glb(tmp_path, module, glb_bytes)
    _write_sidecar(tmp_path, module, bbox_size=huge, triangle_count=10)
    _write_preview(tmp_path, module)

    report = validator.validate_module(tmp_path, module)

    assert not report.ok
    assert _gate_status(report, "bbox_within_target_envelope") == "fail"


def test_missing_sidecar_fails(tmp_path: Path) -> None:
    module = "chest"
    target = validator._reference_target_dimensions(module)
    bbox = (float(target["x"]) * 0.95, float(target["y"]) * 0.95, float(target["z"]) * 0.95)
    glb_bytes = _build_glb_payload(module, bbox_size=bbox, triangle_count=12)
    _write_glb(tmp_path, module, glb_bytes)
    _write_preview(tmp_path, module)
    # Deliberately do NOT write the sidecar.

    report = validator.validate_module(tmp_path, module)

    assert _gate_status(report, "sidecar_present_and_consistent") == "fail"
    assert not report.ok


def test_mirror_pair_mismatch_fails(tmp_path: Path) -> None:
    module = "left_shoulder"
    partner = validator._MIRROR_PAIRS[module]
    target = validator._reference_target_dimensions(module)
    bbox = (float(target["x"]) * 0.95, float(target["y"]) * 0.95, float(target["z"]) * 0.95)
    big_partner_bbox = (
        bbox[0] * 1.20,  # 20% larger on x
        bbox[1],
        bbox[2],
    )
    inset = 0.20
    offset = (0.20, 0.0, 0.0)

    _setup_passing_module(
        tmp_path,
        module,
        bbox_size=bbox,
        triangle_count=8,
        inset=inset,
        attachment_offset=offset,
    )
    # Partner has a deliberately mismatched x dimension.
    _setup_passing_module(
        tmp_path,
        partner,
        bbox_size=big_partner_bbox,
        triangle_count=8,
        inset=inset,
        attachment_offset=offset,
    )

    report = validator.validate_module(tmp_path, module)

    assert _gate_status(report, "mirror_pair_dimension_delta_below_3_percent") == "fail"
    assert not report.ok


def test_glb_parser_extracts_root_mesh_and_bbox(tmp_path: Path) -> None:
    glb_bytes = _build_glb_payload(
        "helmet",
        bbox_size=(0.3, 0.4, 0.3),
        triangle_count=4,
        materials=["base_surface", "emissive"],
    )
    glb_path = tmp_path / "helmet.glb"
    glb_path.write_bytes(glb_bytes)

    data = validator._read_glb(glb_path)

    assert data.root_mesh_name == "armor_helmet_v001"
    assert data.material_names == ["base_surface", "emissive"]
    assert data.bbox_min is not None and data.bbox_max is not None
    size = data.bbox_size()
    assert size is not None
    assert pytest.approx(size[0], rel=1e-6) == 0.3
    assert pytest.approx(size[1], rel=1e-6) == 0.4
    assert pytest.approx(size[2], rel=1e-6) == 0.3
    # Triangle count is derived from indices accessor count // 3 = 4*3/3 = 4.
    assert data.triangle_count == 4


def test_main_cli_returns_nonzero_on_missing_glb(tmp_path: Path, capsys) -> None:
    # No assets at all: --all should fail because every module's GLB is missing.
    rc = validator.main(["--all", "--repo-root", str(tmp_path), "--no-color"])
    captured = capsys.readouterr()
    assert rc != 0
    assert "validated" in captured.out


def test_wrap_around_torso_passes_body_intersection(tmp_path: Path) -> None:
    """A torso module whose shell encloses the body diameter on x and z passes
    the body-intersection gate via the new wrap-around branch, even though it
    sits centered on the body axis."""

    module = "chest"
    # Pick a bbox whose x and z extents both exceed 2*(body_radius+clearance)-tol
    # for the torso category (body_radius=0.18, clearance=0.024 -> required~=0.398m).
    bbox = (0.50, 0.40, 0.50)
    glb_bytes = _build_glb_payload(
        module,
        bbox_size=bbox,
        triangle_count=8,
        materials=["base_surface"],
    )
    _write_glb(tmp_path, module, glb_bytes)
    _write_sidecar(
        tmp_path,
        module,
        bbox_size=bbox,
        triangle_count=8,
        attachment_offset=(0.0, 0.03, 0.0),
    )
    _write_preview(tmp_path, module)

    report = validator.validate_module(tmp_path, module)

    assert _gate_status(report, "no_body_intersection_at_reference_pose") == "pass"


def test_main_cli_json_report(tmp_path: Path, capsys) -> None:
    module = "helmet"
    target = validator._reference_target_dimensions(module)
    bbox = (float(target["x"]) * 0.95, float(target["y"]) * 0.95, float(target["z"]) * 0.95)
    glb_bytes = _build_glb_payload(module, bbox_size=bbox)
    _write_glb(tmp_path, module, glb_bytes)
    _write_sidecar(tmp_path, module, bbox_size=bbox, triangle_count=6)
    _write_preview(tmp_path, module)

    rc = validator.main(
        [module, "--repo-root", str(tmp_path), "--report-json"]
    )
    captured = capsys.readouterr()
    assert isinstance(rc, int)
    payload = json.loads(captured.out)
    assert payload["modules"][0]["module"] == module
    assert isinstance(payload["modules"][0]["gates"], list)
