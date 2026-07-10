from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_replay_variant_alignment.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_replay_variant_alignment", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_replay_variant_alignment"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _placement(part: str, variant: str, asset_ref: str) -> dict:
    return {
        "contract_version": "runtime-render-placement.v1",
        "part": part,
        "asset_ref": asset_ref,
        "selected_variant_key": f"{part}:{variant}",
        "target_size_array_m": [0.3, 0.4, 0.2],
        "offset_m": [0.0, 0.02, 0.06],
        "surface_offset_clamped_m": [0.0, 0.02, 0.06],
        "quest_rig_offset_m": [0.0, 0.02, -0.06],
        "quest_surface_offset_clamped_m": [0.0, 0.02, -0.06],
        "rotation_deg": [0.0, 0.0, 0.0],
    }


def _runtime_package() -> dict:
    asset_ref = "viewer/assets/armor-parts/chest/variants/split_rib/chest__split_rib.glb"
    selected = _placement("chest", "split_rib", asset_ref)
    alternate = _placement(
        "chest",
        "base",
        "viewer/assets/armor-parts/chest/variants/base/chest__base.glb",
    )
    return {
        "contract_version": "base-suit-overlay.v1",
        "render_contract": {
            "render_placement_contract": "runtime-render-placement.v1",
            "variant_render_placement_contract": "runtime-render-placement.v1",
        },
        "selected_variant_keys": {"chest": "chest:split_rib"},
        "render_placements": {"chest": selected},
        "selected_variant_render_placements": {"chest": selected},
        "visual_layers": {
            "armor_overlay": {
                "selected_variant_keys": {"chest": "chest:split_rib"},
                "variant_render_placements": {
                    "chest": {
                        "chest:split_rib": selected,
                        "chest:base": alternate,
                    }
                },
            }
        },
        "variant_placement_snapshot": {
            "contract_version": "runtime-variant-placement-snapshot.v1",
            "selection_source": "render_placements.selected_variant_key",
            "selected_variant_keys": {"chest": "chest:split_rib"},
            "parts": {
                "chest": {
                    "part": "chest",
                    "selected_variant_key": "chest:split_rib",
                    "render_placement_path": "render_placements.chest",
                    "variant_render_placement_path": (
                        "visual_layers.armor_overlay.variant_render_placements.chest.chest:split_rib"
                    ),
                    "render_asset_ref": asset_ref,
                    "variant_asset_ref": asset_ref,
                    "matches_current_render_placement": True,
                    "status": "matched",
                }
            },
        },
    }


def _clone(value: dict) -> dict:
    return json.loads(json.dumps(value))


def test_runtime_package_snapshot_passes_with_web_quest_replay_identity() -> None:
    result = validator.validate_replay_variant_alignment(_runtime_package())

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["source_type"] == "runtime_package"
    assert result["selected_variant_count"] == 1
    assert result["matched_parts"] == ["chest"]
    assert result["parts"]["chest"]["web_quest_replay_identity"] == "matched"
    assert result["parts"]["chest"]["variant_table_entry_present"] is True
    assert result["parts"]["chest"]["checks"]["selected_key_consistent"] is True
    assert result["parts"]["chest"]["checks"]["asset_ref_consistent"] is True


def test_replay_record_container_passes_cli_report_json(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay-record.json"
    replay_path.write_text(
        json.dumps(
            {
                "replay_id": "RPL-TEST",
                "playback": {"view_mode": "mirror"},
                "source_events": [],
                "runtime_package": _runtime_package(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(replay_path), "--report-json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["source_type"] == "replay_record"
    assert result["snapshot_path"] == replay_path.as_posix()
    assert result["parts"]["chest"]["selected_variant_key"] == "chest:split_rib"


def test_missing_variant_snapshot_fails() -> None:
    runtime_package = _runtime_package()
    runtime_package.pop("variant_placement_snapshot")

    result = validator.validate_replay_variant_alignment(runtime_package)

    assert result["ok"] is False
    assert any("variant_placement_snapshot is required" in reason for reason in result["reasons"])


def test_rejects_selected_key_drift_between_render_and_snapshot() -> None:
    runtime_package = _clone(_runtime_package())
    runtime_package["variant_placement_snapshot"]["parts"]["chest"]["selected_variant_key"] = "chest:base"

    result = validator.validate_replay_variant_alignment(runtime_package)

    assert result["ok"] is False
    assert result["mismatch_parts"] == ["chest"]
    assert any("selected variant key drift" in reason for reason in result["reasons"])
    assert result["parts"]["chest"]["checks"]["selected_key_consistent"] is False


def test_rejects_asset_ref_mismatch_and_snapshot_status_warning() -> None:
    runtime_package = _clone(_runtime_package())
    snapshot_part = runtime_package["variant_placement_snapshot"]["parts"]["chest"]
    snapshot_part["variant_asset_ref"] = "viewer/assets/armor-parts/chest/variants/base/chest__base.glb"
    snapshot_part["status"] = "asset_ref_mismatch"
    snapshot_part["matches_current_render_placement"] = False

    result = validator.validate_replay_variant_alignment(runtime_package)

    assert result["ok"] is False
    assert result["parts"]["chest"]["web_quest_replay_identity"] == "mismatch"
    assert any("asset_ref does not match variant table identity" in reason for reason in result["reasons"])
    assert any("snapshot status must be matched" in reason for reason in result["reasons"])
    assert any("matches_current_render_placement=true" in reason for reason in result["reasons"])


def test_rejects_missing_variant_table_entry_for_selected_key() -> None:
    runtime_package = _clone(_runtime_package())
    del runtime_package["visual_layers"]["armor_overlay"]["variant_render_placements"]["chest"]["chest:split_rib"]

    result = validator.validate_replay_variant_alignment(runtime_package)

    assert result["ok"] is False
    assert result["parts"]["chest"]["variant_table_entry_present"] is False
    assert any("variant_render_placements entry is missing" in reason for reason in result["reasons"])
