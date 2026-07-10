from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
PREPARE_TOOL_PATH = REPO_ROOT / "tools" / "prepare_replay_qa_artifact.py"
QUEST_INDEX_PATH = REPO_ROOT / "viewer" / "quest-iw-demo" / "index.html"
QUEST_JS_PATH = REPO_ROOT / "viewer" / "quest-iw-demo" / "quest-demo.js"


def _load_prepare_tool():
    spec = importlib.util.spec_from_file_location("prepare_replay_qa_artifact", PREPARE_TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["prepare_replay_qa_artifact"] = module
    spec.loader.exec_module(module)
    return module


prepare_tool = _load_prepare_tool()


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


def test_web_replay_url_hint_matches_quest_viewer_query_contract(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay-record.json"
    qa_dir = tmp_path / "qa" / "replay"
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")

    summary = prepare_tool.prepare_replay_qa_artifact(replay_path, qa_dir=qa_dir)
    hint = urlsplit(summary["web_replay_check_url_hint"])
    query = parse_qs(hint.query)
    quest_index = QUEST_INDEX_PATH.read_text(encoding="utf-8")
    quest_js = QUEST_JS_PATH.read_text(encoding="utf-8")
    viewer_query_keys = set(re.findall(r'params\(\)\.get\("([^"]+)"\)', quest_js))

    assert hint.path == "viewer/quest-iw-demo/index.html"
    assert query["replay"] == [summary["artifact_path"]]
    assert query["code"] == ["P7C1"]
    assert query["qa"] == [summary["artifact_code"]]
    assert "replayRecord" not in query
    assert "qaCode" not in query
    assert './quest-demo.js' in quest_index
    assert {"replay", "code", "qa"}.issubset(viewer_query_keys)
    assert "function getReplayPath()" in quest_js
    assert 'params().get("replay")' in quest_js
    assert "function getRecallCode()" in quest_js
    assert 'params().get("code")' in quest_js


def test_web_replay_url_hint_uses_recall_code_not_qa_artifact_slug(tmp_path: Path) -> None:
    replay_path = tmp_path / "replay-record.json"
    qa_dir = tmp_path / "qa" / "replay"
    replay_path.write_text(json.dumps(_replay_record(), ensure_ascii=False), encoding="utf-8")

    summary = prepare_tool.prepare_replay_qa_artifact(replay_path, code="DAY1", qa_dir=qa_dir)
    query = parse_qs(urlsplit(summary["web_replay_check_url_hint"]).query)

    assert summary["artifact_code"] == "DAY1"
    assert query["code"] == ["P7C1"]
    assert query["qa"] == ["DAY1"]
