from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_replay_public_artifact.py"
PREPARE_TOOL_PATH = REPO_ROOT / "tools" / "prepare_replay_qa_artifact.py"


def _load_tool(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool(TOOL_PATH, "validate_replay_public_artifact")
prepare_tool = _load_tool(PREPARE_TOOL_PATH, "prepare_replay_qa_artifact_for_public_validation")


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


def _replay_record() -> dict:
    asset_ref = "viewer/assets/armor-parts/chest/variants/split_rib/chest__split_rib.glb"
    selected = _placement("chest", "split_rib", asset_ref)
    runtime_package = {
        "contract_version": "base-suit-overlay.v1",
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
    return {
        "schema_version": "0.2",
        "contract_version": "replay-record.v0.2",
        "replay_id": "RPL-20260504-P7C1-TEST",
        "recall_code": "P7C1",
        "selected_variants": {"chest": "chest:split_rib"},
        "runtime_package": runtime_package,
        "playback": {"view_mode": "observer"},
        "experience": {"label": "Replay QA"},
        "metadata": {"created_at": "2026-05-04T12:00:00+00:00"},
        "operation": {
            "mode": "web_service",
            "runtime_resolver": {
                "artifact_uri_schemes": ["relative", "gs", "https"],
                "requires_runtime_package_snapshot": True,
            },
        },
        "public_artifact_policy": {
            "contract_version": "replay-public-artifact-policy.v1",
            "role": "snapshot_consumer",
            "playcanvas_writeback_allowed": False,
            "local_path_allowed": False,
            "external_publication_requires_preflight": True,
        },
        "playcanvas": {"role": "snapshot_consumer", "write_authority": False},
    }


def _clone(value: dict) -> dict:
    return json.loads(json.dumps(value))


def test_replay_record_passes_external_public_preflight() -> None:
    result = tool.validate_replay_public_artifact(_replay_record(), mode="external")

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["source_type"] == "replay_record"
    assert result["selected_variant_count"] == 1
    assert result["local_path_leak_count"] == 0
    assert result["localhost_url_count"] == 0
    assert result["playcanvas"]["writeback_forbidden_explicit"] is True


def test_summary_input_loads_relative_artifact(tmp_path: Path) -> None:
    replay_path = tmp_path / "P7C1.replay-record.json"
    summary_path = tmp_path / "P7C1.summary.json"
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "contract_version": "replay-qa-artifact-summary.v1",
                "artifact_path": "P7C1.replay-record.json",
                "artifact_code": "P7C1",
                "alignment_status": "pass",
                "web_replay_check_url_hint": (
                    "viewer/quest-iw-demo/index.html?replay=P7C1.replay-record.json&code=P7C1&qa=P7C1"
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = tool.validate_replay_public_artifact(summary_path, mode="external")

    assert result["ok"] is True
    assert result["source_type"] == "qa_summary"
    assert result["artifact_path"] == replay_path.as_posix()
    assert result["recall_code"] == "P7C1"
    assert result["web_replay_url_contract"]["status"] == "pass"


def test_summary_legacy_web_replay_query_warns_local_and_fails_external(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    replay_path = Path("P7C1.replay-record.json")
    summary_path = Path("P7C1.summary.json")
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "contract_version": "replay-qa-artifact-summary.v1",
                "artifact_path": replay_path.as_posix(),
                "artifact_code": "P7C1",
                "alignment_status": "pass",
                "web_replay_check_url_hint": (
                    "viewer/quest-iw-demo/index.html?replayRecord=P7C1.replay-record.json&qaCode=P7C1"
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    local_result = tool.validate_replay_public_artifact(summary_path, mode="local")
    external_result = tool.validate_replay_public_artifact(summary_path, mode="external")

    assert local_result["ok"] is True
    assert local_result["web_replay_url_contract"]["status"] == "warn"
    assert local_result["web_replay_url_contract"]["legacy_query_keys"] == ["qaCode", "replayRecord"]
    assert any("legacy query params" in warning for warning in local_result["warnings"])
    assert external_result["ok"] is False
    assert external_result["web_replay_url_contract"]["status"] == "warn"
    assert any("legacy query params" in reason for reason in external_result["reasons"])


def test_summary_current_web_replay_query_rejects_wrong_replay_and_code(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    replay_path = Path("P7C1.replay-record.json")
    summary_path = Path("P7C1.summary.json")
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "contract_version": "replay-qa-artifact-summary.v1",
                "artifact_path": replay_path.as_posix(),
                "artifact_code": "P7C1",
                "alignment_status": "pass",
                "web_replay_check_url_hint": (
                    "viewer/quest-iw-demo/index.html?replay=qa/replay/stale.json&code=ZZZZ&qa=P7C1"
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = tool.validate_replay_public_artifact(summary_path, mode="external")

    assert result["ok"] is False
    assert result["web_replay_url_contract"]["status"] == "fail"
    assert any("replay query must match summary artifact_path" in reason for reason in result["reasons"])
    assert any("code query must match ReplayRecord recall_code" in reason for reason in result["reasons"])


def test_prepare_rewrites_summary_with_current_web_replay_query_contract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    replay_path = Path("input-replay-record.json")
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")

    summary = prepare_tool.prepare_replay_qa_artifact(replay_path, qa_dir=Path("qa/replay"))
    result = tool.validate_replay_public_artifact(Path(summary["summary_path"]), mode="local")

    assert result["ok"] is True
    assert result["source_type"] == "qa_summary"
    assert result["web_replay_url_contract"]["status"] == "pass"
    assert result["web_replay_url_contract"]["query_keys"] == ["code", "qa", "replay"]
    assert result["web_replay_url_contract"]["legacy_query_keys"] == []


def test_external_mode_rejects_localhost_url_and_local_path() -> None:
    record = _clone(_replay_record())
    record["web_replay_check_url_hint"] = "http://localhost:3000/viewer/quest-iw-demo/index.html"
    record["artifacts"] = {"runtime_package": {"uri": "C:\\dev\\replay\\runtime-package.json"}}

    result = tool.validate_replay_public_artifact(record, mode="external")

    assert result["ok"] is False
    assert result["localhost_url_count"] == 1
    assert result["local_path_leak_count"] == 1
    assert any("localhost/loopback URL is not allowed" in reason for reason in result["reasons"])
    assert any("local filesystem path is not public-portable" in reason for reason in result["reasons"])


def test_local_mode_warns_on_localhost_url() -> None:
    record = _clone(_replay_record())
    record["web_replay_check_url_hint"] = "http://127.0.0.1:5173/viewer/quest-iw-demo/index.html"

    result = tool.validate_replay_public_artifact(record, mode="local")

    assert result["ok"] is True
    assert result["localhost_url_count"] == 1
    assert result["warnings"] == ["localhost/loopback URLs are tolerated only in local mode"]


def test_rejects_missing_runtime_snapshot_selected_variants_and_playcanvas_policy() -> None:
    record = _clone(_replay_record())
    record.pop("selected_variants")
    record.pop("public_artifact_policy")
    record.pop("playcanvas")
    record["runtime_package"].pop("variant_placement_snapshot")
    record["runtime_package"].pop("selected_variant_keys")
    record["runtime_package"]["visual_layers"]["armor_overlay"].pop("selected_variant_keys")
    record["runtime_package"]["render_placements"]["chest"].pop("selected_variant_key")
    record["runtime_package"]["selected_variant_render_placements"]["chest"].pop("selected_variant_key")

    result = tool.validate_replay_public_artifact(record, mode="external")

    assert result["ok"] is False
    assert result["variant_placement_snapshot_present"] is False
    assert result["selected_variant_count"] == 0
    assert any("variant_placement_snapshot is required" in reason for reason in result["reasons"])
    assert any("selected variants are required" in reason for reason in result["reasons"])
    assert any("PlayCanvas write-back prohibition" in reason for reason in result["reasons"])
    assert any("public_artifact_policy is required" in reason for reason in result["reasons"])


def test_rejects_playcanvas_writeback_allowed() -> None:
    record = _clone(_replay_record())
    record["playcanvas"]["write_authority"] = True

    result = tool.validate_replay_public_artifact(record, mode="external")

    assert result["ok"] is False
    assert result["playcanvas"]["writeback_forbidden_explicit"] is True
    assert result["playcanvas"]["writeback_violation_count"] == 1
    assert any("PlayCanvas write-back appears enabled" in reason for reason in result["reasons"])


def test_rejects_public_artifact_policy_that_allows_local_paths_or_skips_preflight() -> None:
    record = _clone(_replay_record())
    record["public_artifact_policy"]["local_path_allowed"] = True
    record["public_artifact_policy"]["external_publication_requires_preflight"] = False

    result = tool.validate_replay_public_artifact(record, mode="external")

    assert result["ok"] is False
    assert result["public_artifact_policy"]["ok"] is False
    assert any("local_path_allowed must be false" in reason for reason in result["reasons"])
    assert any("external_publication_requires_preflight must be true" in reason for reason in result["reasons"])


def test_rejects_playcanvas_source_of_truth_role_and_write_endpoints() -> None:
    record = _clone(_replay_record())
    record["playcanvas"] = {
        "role": "source_of_truth",
        "write_authority": False,
        "mutation_endpoint": "/api/playcanvas/write-back",
    }
    record["playcanvas_write_endpoint"] = "/api/playcanvas/save"

    result = tool.validate_replay_public_artifact(record, mode="external")

    assert result["ok"] is False
    assert result["playcanvas"]["writeback_violation_count"] >= 3
    assert any("PlayCanvas write-back appears enabled" in reason for reason in result["reasons"])


def test_cli_report_json_passes(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay-record.json"
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(replay_path), "--mode", "external", "--report-json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["ok"] is True
    assert result["contract_version"] == "replay-public-artifact-preflight.v1"
    assert result["mode"] == "external"
