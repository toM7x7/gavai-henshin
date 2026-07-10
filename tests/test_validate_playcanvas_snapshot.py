from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_playcanvas_snapshot.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_playcanvas_snapshot", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_playcanvas_snapshot"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _snapshot() -> dict:
    return {
        "contract_version": "base-suit-overlay.v1",
        "render_contract": {
            "render_placement_contract": "runtime-render-placement.v1",
            "render_placement_parts": ["helmet"],
        },
        "visual_layers": {
            "armor_overlay": {
                "selected_variant_keys": {"helmet": "helmet:base"},
                "assets": {
                    "helmet": {
                        "selected_variant_key": "helmet:base",
                        "asset_ref": "viewer/assets/armor-parts/helmet/variants/base/helmet__base.glb",
                    }
                },
            }
        },
        "render_placements": {
            "helmet": {
                "contract_version": "runtime-render-placement.v1",
                "part": "helmet",
                "asset_ref": "viewer/assets/armor-parts/helmet/variants/base/helmet__base.glb",
                "selected_variant_key": "helmet:base",
                "coordinate_space": "vrm_humanoid_local_y_up_z_front",
                "quest_coordinate_space": "quest_rig_local_y_up_z_back",
                "offset_m": [0.0, 0.0, 0.0],
                "quest_rig_offset_m": [0.0, 0.0, -0.0],
                "surface_offset_clamped_m": [0.0, 0.02, 0.0],
                "quest_surface_offset_clamped_m": [0.0, 0.02, -0.0],
                "surface_anchor": {
                    "contract_version": "runtime-body-surface-anchor.v1",
                    "offset_clamped_m": [0.0, 0.02, 0.0],
                    "quest_rig_offset_clamped_m": [0.0, 0.02, -0.0],
                },
            }
        },
        "playcanvas": {
            "role": "snapshot_consumer",
            "write_authority": False,
        },
    }


def _clone(value: dict) -> dict:
    return json.loads(json.dumps(value))


def test_valid_runtime_package_snapshot_passes() -> None:
    result = validator.validate_playcanvas_snapshot(_snapshot())

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["render_placement_count"] == 1
    assert result["selected_parts"] == ["helmet"]
    assert result["artifact_ref_count"] == 1
    assert result["playcanvas"]["write_authority"] is False


def test_valid_quest_payload_snapshot_passes_cli(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "quest-runtime-snapshot.json"
    snapshot_path.write_text(
        json.dumps({"ok": True, "runtime_package": _snapshot()}, ensure_ascii=False),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(snapshot_path), "--report-json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["snapshot_path"] == snapshot_path.as_posix()
    assert result["render_placement_count"] == 1


def test_cli_accepts_powershell_bom_json(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "quest-runtime-snapshot-bom.json"
    snapshot_path.write_text(
        json.dumps({"ok": True, "runtime_package": _snapshot()}, ensure_ascii=False),
        encoding="utf-8-sig",
    )

    completed = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(snapshot_path), "--report-json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["snapshot_path"] == snapshot_path.as_posix()


def test_rejects_missing_render_placements() -> None:
    snapshot = _clone(_snapshot())
    snapshot.pop("render_placements")

    result = validator.validate_playcanvas_snapshot(snapshot)

    assert result["ok"] is False
    assert any("render_placements must be a non-empty object" in reason for reason in result["reasons"])


def test_rejects_variant_identity_drift_and_missing_artifact_ref() -> None:
    snapshot = _clone(_snapshot())
    placement = snapshot["render_placements"]["helmet"]
    placement["selected_variant_key"] = "chest:base"
    placement.pop("asset_ref")

    result = validator.validate_playcanvas_snapshot(snapshot)

    assert result["ok"] is False
    assert any("selected_variant_key must use '<part>:<variant>' identity" in reason for reason in result["reasons"])
    assert any("selected_variant_key must match visual_layers selected_variant_keys" in reason for reason in result["reasons"])
    assert any("asset_ref is required" in reason for reason in result["reasons"])


def test_rejects_machine_local_paths_and_local_path_keys() -> None:
    snapshot = _clone(_snapshot())
    snapshot["render_placements"]["helmet"]["asset_ref"] = "C:\\dev\\private\\helmet.glb"
    snapshot["runtime_checks"] = {"runtime_surface_failures": {"helmet": {"local_path": "C:/dev/private/helmet.glb"}}}

    result = validator.validate_playcanvas_snapshot(snapshot)

    assert result["ok"] is False
    assert result["local_path_leak_count"] >= 2
    assert any("machine-local path leak" in reason for reason in result["reasons"])
    assert any("must be a portable artifact ref" in reason for reason in result["reasons"])


def test_accepts_explicit_read_only_playcanvas_write_policy_strings() -> None:
    snapshot = _clone(_snapshot())
    snapshot["playcanvas"] = {
        "role": "read_only_snapshot_consumer",
        "write_authority": "read-only",
        "writeback": "disabled",
        "can_write": "false",
    }

    result = validator.validate_playcanvas_snapshot(snapshot)

    assert result["ok"] is True
    assert result["playcanvas"]["write_authority_violation_count"] == 0


def test_rejects_playcanvas_writeback_authority() -> None:
    snapshot = _clone(_snapshot())
    snapshot["playcanvas"] = {
        "role": "source_of_truth",
        "write_authority": True,
        "mutation_endpoint": "/api/playcanvas/write-back",
    }
    snapshot["playcanvas_write_endpoint"] = "/api/playcanvas/save"

    result = validator.validate_playcanvas_snapshot(snapshot)

    assert result["ok"] is False
    assert result["playcanvas"]["write_authority_violation_count"] >= 3
    assert any("snapshot-consumer/read-only adapter mode" in reason for reason in result["reasons"])
    assert any("write-back authority" in reason for reason in result["reasons"])
    assert any("write or authority semantics" in reason for reason in result["reasons"])
