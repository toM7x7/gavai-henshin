from __future__ import annotations

import copy
import importlib.util
import json
import struct
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_modeler_variant_order_manifest.py"
MANIFEST_PATH = (
    REPO_ROOT
    / "docs"
    / "modeler-deliveries"
    / "p1-limb-three-line-variants-2026-05-03.order-manifest.json"
)


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_modeler_variant_order_manifest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_modeler_variant_order_manifest"] = module
    spec.loader.exec_module(module)
    return module


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _write_manifest(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "order-manifest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_glb(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk = b"{}  "
    payload = struct.pack("<4sII", b"glTF", 2, 20 + len(chunk))
    payload += struct.pack("<II", len(chunk), 0x4E4F534A)
    payload += chunk
    path.write_bytes(payload)


def _materialize_order_asset(
    root: Path,
    order: dict,
    *,
    with_fidelity: bool = True,
    sidecar_extra: dict | None = None,
) -> None:
    for field in (
        "expected_source_blend_path",
        "expected_preview_mesh_path",
    ):
        path = root / order[field]
        path.parent.mkdir(parents=True, exist_ok=True)
        if field.endswith("preview_mesh_path"):
            path.write_text(json.dumps({"format": "mesh.v1"}), encoding="utf-8")
        else:
            path.write_bytes(b"BLENDER")
    _write_glb(root / order["expected_glb_path"])
    sidecar = {
        "contract_version": "modeler-part-variant-sidecar.v1",
        "module": order["module"],
        "variant_key": order["variant_key"],
        "line_id": order["line_id"],
        "source_concept_ids": ["c02"],
        "design_intent": order["design_intent"],
    }
    if with_fidelity:
        sidecar["fidelity_notes"] = "Reviewed against front/side/back/3q and Quest controller clearance."
    if sidecar_extra:
        sidecar.update(sidecar_extra)
    sidecar_path = root / order["expected_sidecar_path"]
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")


def test_committed_p1_limb_order_manifest_is_valid_open_order() -> None:
    validator = _load_validator()

    result = validator.validate_order_manifest(MANIFEST_PATH)

    assert result["ok"], result["reasons"]
    assert result["status"] in {"warn", "pass"}
    assert result["asset_count"] == 24
    assert sorted(result["module_reports"]) == sorted(validator.P1_TARGET_MODULES)
    assert all(report["ordered_count"] == 3 for report in result["module_reports"].values())
    assert result["p1_acceptance"]["package_gate_status"] == "warn_now_block_p1"
    assert result["p1_acceptance"]["acceptance_complete"] is False
    assert result["p1_acceptance"]["runtime_activation_allowed"] is False
    assert set(result["line_system_reports"]) == {
        "line_rescue_knight",
        "line_royal_insect",
        "line_final_oath",
    }
    assert all(
        report["package_gate_status"] == "warn_now_block_p1"
        for report in result["line_system_reports"].values()
    )
    assert {asset["limb_family"] for asset in result["assets"]} == {
        "upperarm",
        "forearm",
        "hand",
        "thigh",
    }
    assert all(asset["p1_acceptance"]["runtime_activation_allowed"] is False for asset in result["assets"])
    matrix = result["missing_matrix"]
    assert matrix["contract_version"] == "p1-limb-missing-matrix.v1"
    assert matrix["axis"] == ["line_id", "limb_family", "side"]
    assert matrix["entry_count"] == 24
    assert matrix["p1_blocked_asset_count"] == 24
    assert matrix["runtime_activation_blocked_count"] == 24
    assert matrix["stage_counts"]["order"]["blocked_count"] == 0
    assert matrix["stage_counts"]["delivery"]["missing_count"] == 24
    assert matrix["stage_counts"]["catalog_registration"]["missing_count"] == 24
    assert matrix["stage_counts"]["runtime_activation"]["blocked_count"] == 24
    assert matrix["stage_counts"]["current_stop"]["delivery"] == 24
    assert {
        (entry["line_id"], entry["limb_family"], entry["side"])
        for entry in matrix["entries"]
    } == {
        (line_id, family, side)
        for line_id in {"line_rescue_knight", "line_royal_insect", "line_final_oath"}
        for family in {"upperarm", "forearm", "hand", "thigh"}
        for side in {"left", "right"}
    }
    assert (
        matrix["by_line"]["line_rescue_knight"]["families"]["upperarm"]["left"]["variant_key"]
        == "left_upperarm:rescue_upperarm_stream"
    )


def test_right_side_order_must_reference_left_side_mirror(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    right_order = next(order for order in manifest["variants"] if order["module"] == "right_upperarm")
    right_order["mirror_of"] = "left_forearm:wrong"
    path = _write_manifest(tmp_path, manifest)

    result = validator.validate_order_manifest(path)

    assert not result["ok"]
    assert any("mirror_of: expected left_upperarm" in reason for reason in result["reasons"])


def test_missing_matrix_marks_missing_order_rows(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    first = copy.deepcopy(manifest["variants"][0])
    manifest["target_modules"] = [first["module"]]
    manifest["required_lines"] = [
        line for line in manifest["required_lines"] if line["line_id"] == first["line_id"]
    ]
    manifest["acceptance_policy"]["required_variants_per_module"] = 1
    manifest["source_concept_catalog"] = None
    manifest["variants"] = []
    path = _write_manifest(tmp_path, manifest)

    result = validator.validate_order_manifest(path)

    assert not result["ok"]
    entry = result["missing_matrix"]["entries"][0]
    assert entry["line_id"] == first["line_id"]
    assert entry["limb_family"] == "upperarm"
    assert entry["side"] == "left"
    assert entry["order_status"] == "missing_order"
    assert entry["current_stop_stage"] == "order"
    assert entry["blocked_stages"] == ["order", "delivery", "catalog_registration", "runtime_activation"]
    assert result["missing_matrix"]["stage_counts"]["current_stop"]["order"] == 1


def test_require_delivered_promotes_open_order_gaps_to_failures(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    manifest["source_concept_catalog"] = None
    path = _write_manifest(tmp_path, manifest)
    catalog = tmp_path / "variant_catalog.json"
    catalog.write_text(json.dumps({"modules": {}}), encoding="utf-8")

    result = validator.validate_order_manifest(path, catalog_path=catalog, require_delivered=True)

    assert not result["ok"]
    assert any("not declared in variant_catalog.json" in reason for reason in result["reasons"])
    assert any("required GLB/source/sidecar/preview files are missing" in reason for reason in result["reasons"])


def test_delivered_sidecar_requires_fidelity_notes_in_strict_mode(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    first = copy.deepcopy(manifest["variants"][0])
    manifest["target_modules"] = [first["module"]]
    manifest["required_lines"] = [
        line for line in manifest["required_lines"] if line["line_id"] == first["line_id"]
    ]
    manifest["acceptance_policy"]["required_variants_per_module"] = 1
    manifest["source_concept_catalog"] = None
    manifest["variants"] = [first]
    path = _write_manifest(tmp_path, manifest)
    catalog = tmp_path / "variant_catalog.json"
    catalog.write_text(
        json.dumps({"modules": {first["module"]: {"variants": [{"variant_key": first["variant_key"]}]}}}),
        encoding="utf-8",
    )
    validator.REPO_ROOT = tmp_path
    _materialize_order_asset(tmp_path, first, with_fidelity=False)
    result = validator.validate_order_manifest(path, catalog_path=catalog, require_delivered=True)

    assert not result["ok"]
    assert any("sidecar.fidelity_notes" in reason for reason in result["reasons"])


def test_strict_acceptance_passes_without_runtime_activation(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    first = copy.deepcopy(manifest["variants"][0])
    manifest["target_modules"] = [first["module"]]
    manifest["required_lines"] = [
        line for line in manifest["required_lines"] if line["line_id"] == first["line_id"]
    ]
    manifest["acceptance_policy"]["required_variants_per_module"] = 1
    manifest["source_concept_catalog"] = None
    manifest["variants"] = [first]
    path = _write_manifest(tmp_path, manifest)
    catalog = tmp_path / "variant_catalog.json"
    catalog.write_text(
        json.dumps({"modules": {first["module"]: {"variants": [{"variant_key": first["variant_key"]}]}}}),
        encoding="utf-8",
    )
    validator.REPO_ROOT = tmp_path
    _materialize_order_asset(tmp_path, first)

    result = validator.validate_order_manifest(path, catalog_path=catalog, require_delivered=True)

    assert result["ok"], result["reasons"]
    assert result["p1_acceptance"]["package_gate_status"] == "pass_p1"
    assert result["p1_acceptance"]["acceptance_complete"] is True
    assert result["p1_acceptance"]["runtime_activation_allowed"] is False
    assert result["line_system_reports"][first["line_id"]]["package_gate_status"] == "pass_p1"
    assert result["assets"][0]["p1_acceptance"]["package_gate_status"] == "pass_p1"
    assert result["assets"][0]["p1_acceptance"]["runtime_activation_label"] == (
        "runtime_activation_blocked_by_order_manifest"
    )
    matrix_entry = result["missing_matrix"]["entries"][0]
    assert matrix_entry["p1_acceptance_complete"] is True
    assert matrix_entry["delivery_status"] == "present"
    assert matrix_entry["catalog_registration_status"] == "present"
    assert matrix_entry["blocked_stages"] == ["runtime_activation"]
    assert matrix_entry["current_stop_stage"] == "runtime_activation"
    assert result["missing_matrix"]["stage_counts"]["runtime_activation"]["blocked_count"] == 1


def test_missing_matrix_marks_catalog_registration_after_delivery(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    first = copy.deepcopy(manifest["variants"][0])
    manifest["target_modules"] = [first["module"]]
    manifest["required_lines"] = [
        line for line in manifest["required_lines"] if line["line_id"] == first["line_id"]
    ]
    manifest["acceptance_policy"]["required_variants_per_module"] = 1
    manifest["source_concept_catalog"] = None
    manifest["variants"] = [first]
    path = _write_manifest(tmp_path, manifest)
    catalog = tmp_path / "variant_catalog.json"
    catalog.write_text(json.dumps({"modules": {}}), encoding="utf-8")
    validator.REPO_ROOT = tmp_path
    _materialize_order_asset(tmp_path, first)

    result = validator.validate_order_manifest(path, catalog_path=catalog, require_delivered=True)

    assert not result["ok"]
    entry = result["missing_matrix"]["entries"][0]
    assert entry["order_status"] == "ordered"
    assert entry["delivery_status"] == "present"
    assert entry["catalog_registration_status"] == "missing"
    assert entry["blocked_stages"] == ["catalog_registration", "runtime_activation"]
    assert entry["current_stop_stage"] == "catalog_registration"
    assert entry["stage_reasons"]["catalog_registration"]


def test_sidecar_runtime_activation_claim_is_rejected_in_p1_acceptance(tmp_path: Path) -> None:
    validator = _load_validator()
    manifest = _manifest()
    first = copy.deepcopy(manifest["variants"][0])
    manifest["target_modules"] = [first["module"]]
    manifest["required_lines"] = [
        line for line in manifest["required_lines"] if line["line_id"] == first["line_id"]
    ]
    manifest["acceptance_policy"]["required_variants_per_module"] = 1
    manifest["source_concept_catalog"] = None
    manifest["variants"] = [first]
    path = _write_manifest(tmp_path, manifest)
    catalog = tmp_path / "variant_catalog.json"
    catalog.write_text(
        json.dumps({"modules": {first["module"]: {"variants": [{"variant_key": first["variant_key"]}]}}}),
        encoding="utf-8",
    )
    validator.REPO_ROOT = tmp_path
    _materialize_order_asset(tmp_path, first, sidecar_extra={"runtime_activation_allowed": True})

    result = validator.validate_order_manifest(path, catalog_path=catalog, require_delivered=True)

    assert not result["ok"]
    assert result["p1_acceptance"]["package_gate_status"] == "warn_now_block_p1"
    assert result["p1_acceptance"]["runtime_activation_allowed"] is False
    assert any("P1 acceptance is not runtime activation" in reason for reason in result["reasons"])
