from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "prepare_replay_qa_artifact.py"
EXPORT_TOOL_PATH = REPO_ROOT / "tools" / "export_replay_demo_record.py"
PUBLIC_VALIDATOR_TOOL_PATH = REPO_ROOT / "tools" / "validate_replay_public_artifact.py"


def _load_tool(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool(TOOL_PATH, "prepare_replay_qa_artifact")
exporter = _load_tool(EXPORT_TOOL_PATH, "export_replay_demo_record")


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
        "experience": {"label": "Replay QA"},
        "runtime_package": runtime_package,
        "playback": {"view_mode": "observer"},
        "source_events": [],
        "metadata": {"created_at": "2026-05-04T12:00:00+00:00"},
    }


def test_prepare_replay_qa_artifact_copies_record_and_writes_summary(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay-record.json"
    qa_dir = tmp_path / "qa" / "replay"
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")

    summary = tool.prepare_replay_qa_artifact(replay_path, qa_dir=qa_dir)
    artifact_path = Path(summary["artifact_path"])
    summary_path = Path(summary["summary_path"])
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    persisted_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["ok"] is True
    assert summary["contract_version"] == "replay-qa-artifact-summary.v1"
    assert summary["artifact_code"] == "P7C1"
    assert artifact_path == qa_dir / "P7C1.replay-record.json"
    assert summary_path == qa_dir / "P7C1.summary.json"
    assert artifact["recall_code"] == "P7C1"
    assert artifact["metadata"]["qa_artifact_code"] == "P7C1"
    assert artifact["public_artifact_policy"]["contract_version"] == "replay-public-artifact-policy.v1"
    assert artifact["public_artifact_policy"]["playcanvas_writeback_allowed"] is False
    assert artifact["public_artifact_policy"]["local_path_allowed"] is False
    assert artifact["public_artifact_policy"]["external_publication_requires_preflight"] is True
    assert summary["alignment_status"] == "pass"
    hint = urlsplit(summary["web_replay_check_url_hint"])
    hint_query = parse_qs(hint.query)
    assert hint.path == "viewer/quest-iw-demo/index.html"
    assert hint_query["replay"] == [summary["artifact_path"]]
    assert hint_query["code"] == ["P7C1"]
    assert hint_query["qa"] == ["P7C1"]
    assert summary["recommended_operator_check"]["requires_browser_launch"] is False
    assert persisted_summary["artifact_path"] == summary["artifact_path"]


def test_cli_supports_explicit_code_out_summary_and_report_json(tmp_path: Path) -> None:
    replay_path = tmp_path / "input.json"
    qa_dir = tmp_path / "qa"
    out_summary = tmp_path / "summary.json"
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            str(replay_path),
            "--code",
            "DAY1",
            "--qa-dir",
            str(qa_dir),
            "--out-summary",
            str(out_summary),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)

    assert summary["ok"] is True
    assert summary["artifact_code"] == "DAY1"
    assert summary["artifact_path"] == (qa_dir / "DAY1.replay-record.json").as_posix()
    assert summary["summary_path"] == out_summary.as_posix()
    hint_query = parse_qs(urlsplit(summary["web_replay_check_url_hint"]).query)
    assert hint_query["code"] == ["P7C1"]
    assert hint_query["qa"] == ["DAY1"]
    assert out_summary.exists()
    assert json.loads(out_summary.read_text(encoding="utf-8"))["alignment_status"] == "pass"


def test_prepare_replay_qa_artifact_preserves_failed_alignment_summary(tmp_path: Path) -> None:
    record = _replay_record()
    record["runtime_package"].pop("variant_placement_snapshot")
    replay_path = tmp_path / "bad-record.json"
    qa_dir = tmp_path / "qa"
    replay_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    summary = tool.prepare_replay_qa_artifact(replay_path, qa_dir=qa_dir)

    assert summary["ok"] is False
    assert summary["alignment_status"] == "fail"
    assert Path(summary["artifact_path"]).exists()
    assert Path(summary["summary_path"]).exists()
    assert summary["recommended_operator_check"]["pass_alignment_before_visual_review"] is False
    assert any("variant_placement_snapshot is required" in reason for reason in summary["alignment_report"]["reasons"])


def test_export_prepare_artifact_passes_public_local_preflight(tmp_path: Path) -> None:
    runtime_path = tmp_path / "runtime-package.json"
    exported_path = tmp_path / "exported-replay-record.json"
    qa_dir = tmp_path / "qa" / "replay"
    runtime_path.write_text(json.dumps(_replay_record()["runtime_package"], ensure_ascii=False), encoding="utf-8")

    export_report = exporter.export_replay_demo_record(
        runtime_path,
        out=exported_path,
        code="3601",
        experience_label="Replay public preflight",
        created_at="2026-05-04T12:00:00+00:00",
    )
    summary = tool.prepare_replay_qa_artifact(exported_path, qa_dir=qa_dir)

    completed = subprocess.run(
        [
            sys.executable,
            str(PUBLIC_VALIDATOR_TOOL_PATH),
            summary["artifact_path"],
            "--mode",
            "local",
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    public_report = json.loads(completed.stdout)
    artifact = json.loads(Path(summary["artifact_path"]).read_text(encoding="utf-8"))

    assert export_report["ok"] is True
    assert summary["ok"] is True
    assert public_report["ok"] is True
    assert public_report["status"] == "pass"
    assert public_report["playcanvas"]["writeback_forbidden_explicit"] is True
    assert artifact["recall_code"] == "3601"
    assert artifact["public_artifact_policy"]["playcanvas_writeback_allowed"] is False
    assert artifact["public_artifact_policy"]["local_path_allowed"] is False
    assert artifact["public_artifact_policy"]["external_publication_requires_preflight"] is True
