import importlib.util
import json
import struct
from pathlib import Path


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_armor_parts_intake.py"
SPEC = importlib.util.spec_from_file_location("validate_armor_parts_intake_acceptance", TOOL_PATH)
armor_intake = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(armor_intake)


def _write_glb(path: Path) -> None:
    json_chunk = b'{"asset":{"version":"2.0"}}  '
    while len(json_chunk) % 4:
        json_chunk += b" "
    total_length = 12 + 8 + len(json_chunk)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<II", len(json_chunk), 0x4E4F534A)
        + json_chunk
    )


def _sidecar(module: str, *, bbox: dict[str, float] | None = None, offset_m=None) -> dict:
    bbox = bbox or armor_intake._reference_target_dimensions(module)
    return {
        "contract_version": "modeler-part-sidecar.v1",
        "module": module,
        "part_id": f"viewer.mesh.{module}.v1",
        "bbox_m": {"x": bbox["x"], "y": bbox["y"], "z": bbox["z"], "size": [bbox["x"], bbox["y"], bbox["z"]]},
        "triangle_count": 12,
        "material_zones": ["base_surface", "accent", "trim"],
        "texture_provider_profile": "nano_banana",
        "vrm_attachment": {
            "primary_bone": armor_intake.ARMOR_SLOT_SPECS[armor_intake.normalize_slot_id(module)].body_anchor,
            "offset_m": list(offset_m or [0, 0, 0]),
            "rotation_deg": [0, 0, 0],
        },
    }


def _p0_metadata(module: str, slots: list[str]) -> dict:
    return {
        "variant_key": f"{module}:base",
        "base_motif_link": {"name": f"{module}_motif", "surface_zone": "accent"},
        "topping_slots": [
            {
                "topping_slot": slot,
                "slot_transform": {"anchor": [0, 0, 0], "rotation_deg": [0, 0, 0]},
                "max_bbox_m": {"x": 0.05, "y": 0.05, "z": 0.05},
                "conflicts_with": [],
                "parent_module": module,
            }
            for slot in slots
        ],
    }


def _write_part(root: Path, module: str, payload: dict) -> None:
    module_dir = root / module
    module_dir.mkdir(parents=True)
    _write_glb(module_dir / f"{module}.glb")
    (module_dir / f"{module}.modeler.json").write_text(json.dumps(payload), encoding="utf-8")


def test_p0_metadata_gate_requires_variant_motif_and_required_topping_slots(tmp_path: Path) -> None:
    sidecar_path = tmp_path / "helmet.modeler.json"
    sidecar_path.write_text(json.dumps(_sidecar("helmet")), encoding="utf-8")

    result = armor_intake.validate_modeler_sidecar(
        sidecar_path,
        expected_module="helmet",
        enforce_p0_metadata=True,
    )

    assert result["ok"] is False
    assert result["metrics"]["p0_metadata_gate"]["status"] == "fail"
    assert any("variant_key" in reason for reason in result["reasons"])
    assert any("required topping slots" in reason for reason in result["reasons"])


def test_p0_metadata_gate_rejects_legacy_string_motif_and_string_slot_list(tmp_path: Path) -> None:
    sidecar = _sidecar("left_shin")
    sidecar.update(
        {
            "variant_key": "sleek",
            "base_motif_link": "shin_line",
            "topping_slots": ["shin_spike", "ankle_cuff_trim"],
        }
    )
    sidecar_path = tmp_path / "left_shin.modeler.json"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")

    result = armor_intake.validate_modeler_sidecar(
        sidecar_path,
        expected_module="left_shin",
        enforce_p0_metadata=True,
    )

    assert result["ok"] is False
    assert result["metrics"]["p0_metadata_gate"]["status"] == "fail"
    assert any("base_motif_link` must be an object" in reason for reason in result["reasons"])
    assert any("topping_slots[0]` must be an object" in reason for reason in result["reasons"])


def test_p0_metadata_gate_accepts_structured_topping_slot_contract(tmp_path: Path) -> None:
    sidecar = _sidecar("left_shin")
    sidecar.update(_p0_metadata("left_shin", ["shin_spike", "ankle_cuff_trim"]))
    sidecar_path = tmp_path / "left_shin.modeler.json"
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")

    result = armor_intake.validate_modeler_sidecar(
        sidecar_path,
        expected_module="left_shin",
        enforce_p0_metadata=True,
    )

    assert result["ok"] is True, result["reasons"]
    gate = result["metrics"]["p0_metadata_gate"]
    assert gate["status"] == "pass"
    assert gate["base_motif_link"]["name"] == "left_shin_motif"
    assert gate["declared_topping_slots"] == ["ankle_cuff_trim", "shin_spike"]


def test_bbox_acceptance_tiers_warn_at_12_percent_and_fail_above_15(tmp_path: Path) -> None:
    target = armor_intake._reference_target_dimensions("helmet")
    warn_payload = _sidecar("helmet", bbox={axis: target[axis] * 1.12 for axis in ("x", "y", "z")})
    warn_path = tmp_path / "warn.modeler.json"
    warn_path.write_text(json.dumps(warn_payload), encoding="utf-8")

    warn = armor_intake.validate_modeler_sidecar(warn_path, expected_module="helmet")

    assert warn["ok"] is True
    assert warn["metrics"]["bbox_target_gate"]["status"] == "warn"
    assert any("bbox_m exceeds pass target" in item for item in warn["warnings"])

    fail_payload = _sidecar("helmet", bbox={axis: target[axis] * 1.20 for axis in ("x", "y", "z")})
    fail_path = tmp_path / "fail.modeler.json"
    fail_path.write_text(json.dumps(fail_payload), encoding="utf-8")

    fail = armor_intake.validate_modeler_sidecar(fail_path, expected_module="helmet")

    assert fail["ok"] is False
    assert fail["metrics"]["bbox_target_gate"]["status"] == "fail"
    assert any("bbox_m exceeds target envelope" in item for item in fail["reasons"])


def test_attachment_offset_warns_above_target_and_fails_above_hard_limit(tmp_path: Path) -> None:
    warn_path = tmp_path / "warn.modeler.json"
    warn_path.write_text(json.dumps(_sidecar("left_shoulder", offset_m=[0.041, 0, 0])), encoding="utf-8")

    warn = armor_intake.validate_modeler_sidecar(warn_path, expected_module="left_shoulder")

    assert warn["ok"] is True
    assert warn["metrics"]["attachment_offset_gate"]["status"] == "warn"

    fail_path = tmp_path / "fail.modeler.json"
    fail_path.write_text(json.dumps(_sidecar("left_shoulder", offset_m=[0.31, 0, 0])), encoding="utf-8")

    fail = armor_intake.validate_modeler_sidecar(fail_path, expected_module="left_shoulder")

    assert fail["ok"] is False
    assert fail["metrics"]["attachment_offset_gate"]["status"] == "fail"


def test_intake_aggregate_fails_mirror_pair_above_five_percent(tmp_path: Path) -> None:
    previous_expected = armor_intake.EXPECTED_PARTS
    armor_intake.EXPECTED_PARTS = ("left_forearm", "right_forearm")
    try:
        target = armor_intake._reference_target_dimensions("left_forearm")
        _write_part(tmp_path, "left_forearm", _sidecar("left_forearm", bbox=target))
        _write_part(tmp_path, "right_forearm", _sidecar("right_forearm", bbox={**target, "x": target["x"] * 1.06}))

        result = armor_intake.validate_armor_parts(tmp_path)
    finally:
        armor_intake.EXPECTED_PARTS = previous_expected

    assert result["status"] == "fail"
    assert result["mirror_pair_checks"][0]["status"] == "fail"
    assert any("mirror pair dimensions exceed" in reason for reason in result["reasons"])
