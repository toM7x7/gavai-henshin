from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_TOOL_PATH = REPO_ROOT / "tools" / "export_replay_demo_record.py"
VALIDATOR_TOOL_PATH = REPO_ROOT / "tools" / "validate_replay_variant_alignment.py"


def _load_tool(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exporter = _load_tool(EXPORT_TOOL_PATH, "export_replay_demo_record")
validator = _load_tool(VALIDATOR_TOOL_PATH, "validate_replay_variant_alignment")


def _placement(part: str, variant: str, asset_ref: str) -> dict:
    return {
        "contract_version": "runtime-render-placement.v1",
        "part": part,
        "asset_ref": asset_ref,
        "selected_variant_key": f"{part}:{variant}",
        "target_size_array_m": [0.64, 0.5, 0.16],
        "offset_m": [0.0, 0.02, 0.06],
        "surface_offset_clamped_m": [0.0, 0.02, 0.06],
        "quest_rig_offset_m": [0.0, 0.02, -0.06],
        "quest_surface_offset_clamped_m": [0.0, 0.02, -0.06],
        "rotation_deg": [0.0, 0.0, 0.0],
    }


def _runtime_package() -> dict:
    asset_ref = "viewer/assets/armor-parts/chest/variants/split_rib/chest__split_rib.glb"
    selected = _placement("chest", "split_rib", asset_ref)
    return {
        "contract_version": "base-suit-overlay.v1",
        "manifest_id": "MNF-20260504-TEST",
        "suitspec": {
            "suit_id": "VDA-DEMO-REPLAY-00-0001",
            "body_profile": {"height_cm": 171.5, "source": "web_forge_declared"},
        },
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
                "variant_render_placements": {"chest": {"chest:split_rib": selected}},
            }
        },
        "variant_placement_snapshot": {
            "contract_version": "runtime-variant-placement-snapshot.v1",
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


def test_export_replay_demo_record_wraps_runtime_package_and_passes_validator(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime-package.json"
    out_path = tmp_path / "replay-record.json"
    runtime_path.write_text(json.dumps(_runtime_package(), ensure_ascii=False), encoding="utf-8")

    result = exporter.export_replay_demo_record(
        runtime_path,
        out=out_path,
        code="P7C1",
        height_cm=180.0,
        experience_label="Stage QA",
        created_at="2026-05-04T12:00:00+00:00",
    )
    record = json.loads(out_path.read_text(encoding="utf-8"))
    alignment = validator.validate_replay_variant_alignment(record)

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["variant_alignment_report"]["ok"] is True
    assert alignment["ok"] is True
    assert record["schema_version"] == "0.2"
    assert record["contract_version"] == "replay-record.v0.2"
    assert record["recall_code"] == "P7C1"
    assert record["experience"]["label"] == "Stage QA"
    assert record["wearer"]["height_cm"] == 180.0
    assert record["wearer"]["source"] == "cli_arg.height_cm"
    assert record["metadata"]["created_at"] == "2026-05-04T12:00:00+00:00"
    assert record["selected_variants"] == {"chest": "chest:split_rib"}
    assert record["placement_snapshot"]["contract_version"] == "runtime-variant-placement-snapshot.v1"
    assert record["runtime_package"]["render_placements"]["chest"]["asset_ref"].endswith("chest__split_rib.glb")
    assert record["public_artifact_policy"]["contract_version"] == "replay-public-artifact-policy.v1"
    assert record["public_artifact_policy"]["playcanvas_writeback_allowed"] is False
    assert record["public_artifact_policy"]["local_path_allowed"] is False
    assert record["public_artifact_policy"]["external_publication_requires_preflight"] is True


def test_cli_exports_report_json_and_uses_runtime_height(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime-package.json"
    out_path = tmp_path / "replay-record.json"
    runtime_path.write_text(json.dumps({"runtime_package": _runtime_package()}, ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(EXPORT_TOOL_PATH),
            str(runtime_path),
            "--out",
            str(out_path),
            "--code",
            "R8D2",
            "--experience-label",
            "Replay preserved",
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    record = json.loads(out_path.read_text(encoding="utf-8"))
    alignment = validator.validate_replay_variant_alignment(out_path)

    assert result["ok"] is True
    assert result["out"] == out_path.as_posix()
    assert result["variant_alignment_report"]["source_type"] == "replay_record"
    assert alignment["ok"] is True
    assert record["recall_code"] == "R8D2"
    assert record["experience"]["label"] == "Replay preserved"
    assert record["wearer"]["height_cm"] == 171.5
    assert record["wearer"]["source"] == "runtime_package.suitspec.body_profile.height_cm"


def test_export_reports_alignment_failure_for_missing_snapshot(tmp_path: Path) -> None:
    runtime_package = _runtime_package()
    runtime_package.pop("variant_placement_snapshot")
    out_path = tmp_path / "replay-record.json"

    result = exporter.export_replay_demo_record(
        runtime_package,
        out=out_path,
        code="FAIL",
        created_at="2026-05-04T12:00:00+00:00",
    )

    assert result["ok"] is False
    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8"))["public_artifact_policy"]["playcanvas_writeback_allowed"] is False
    assert any("variant_placement_snapshot is required" in reason for reason in result["variant_alignment_report"]["reasons"])
