from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_qa_evidence_privacy.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("validate_qa_evidence_privacy", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_qa_evidence_privacy"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _write_share_safe_manifest(qa_root: Path) -> Path:
    path = qa_root / "mocopi-evidence-package-latest.json"
    path.write_text(
        json.dumps(
            {
                "contract_version": "mocopi-evidence-share-package.v1",
                "current_gate_label": "mocopi-DEMO-ONLY",
                "included_evidence": {
                    "evaluation_report": {
                        "pack_summaries": {
                            "mocopi_candidate": {
                                "motion": {"token": "MOCOPI 12f", "category": "mocopi"}
                            }
                        }
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_share_mode_warns_for_media_raw_debug_localhost_and_blocks_secret(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    log_dir = qa / "logs" / "quest-3601-demo"
    log_dir.mkdir(parents=True)
    _write_share_safe_manifest(qa)
    (log_dir / "screencap.png").write_bytes(b"\x89PNG\r\n")
    (log_dir / "adb-devices.txt").write_text("1WMHH000000000\tdevice\n", encoding="utf-8")
    (log_dir / "quest-debug-latest.json").write_text(
        json.dumps(
            {
                "query": {"href": "http://localhost:5173/viewer/quest-iw-demo/?code=3601"},
                "api_key": "sk-testvalue1234567890",
            }
        ),
        encoding="utf-8",
    )
    (qa / "server.log").write_text("raw server log\n", encoding="utf-8")

    result = tool.validate_qa_evidence_privacy(qa, mode="share")

    codes = {finding["code"] for finding in result["findings"]}
    assert result["status"] == "fail"
    assert "share-exclude-quest-screenshot" in codes
    assert "share-exclude-raw-debug" in codes
    assert "share-exclude-raw-log" in codes
    assert "localhost-url-share-warning" in codes
    assert "secret-like-json-key" in codes
    assert result["counts"]["blocker_count"] >= 1


def test_local_mode_allows_localhost_as_local_evidence(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "local-run.json").write_text(
        json.dumps(
            {
                "contract_version": "local-quest-debug.v1",
                "href": "http://127.0.0.1:8010/api/quest-debug/latest",
            }
        ),
        encoding="utf-8",
    )

    result = tool.validate_qa_evidence_privacy(qa, mode="local")

    codes = {finding["code"] for finding in result["findings"]}
    assert result["status"] == "pass"
    assert result["ok"] is True
    assert "localhost-url-local-evidence" in codes
    assert result["counts"]["warning_count"] == 0
    assert result["counts"]["local_evidence_count"] == 1


def test_release_stage_manifest_qa_evidence_samples_are_checked(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    manifest_path = tmp_path / "release-stage-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "contract_version": "release-stage-manifest.v1",
                "categories": {
                    "qa-evidence": {
                        "samples": [
                            {"path": "qa/logs/quest-3601-demo/screencap.png"},
                            {"path": "qa/mocopi-evidence-package-latest.json"},
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = tool.validate_qa_evidence_privacy(
        qa,
        mode="share",
        release_stage_manifest=manifest_path,
    )

    assert result["status"] == "warn"
    assert result["release_stage_manifest"]["qa_evidence_sample_count"] == 2
    assert any(finding["code"] == "release-manifest-qa-evidence-unsafe" for finding in result["findings"])


def test_share_safe_manifest_has_no_findings(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    _write_share_safe_manifest(qa)

    result = tool.validate_qa_evidence_privacy(qa, mode="share")

    assert result["status"] == "pass"
    assert result["json_manifest_safety"][0]["safe_manifest"] is True
    assert result["findings"] == []


def test_current_share_and_release_manifests_are_share_safe_contracts(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    for name, contract in (
        ("release-stage-manifest-latest.json", "release-stage-manifest.v5"),
        ("release-stage-validation-latest.json", "release-stage-manifest-validation.v6"),
        ("shareable-qa-evidence-latest.json", "shareable-qa-evidence-manifest.v1"),
    ):
        (qa / name).write_text(json.dumps({"contract_version": contract}), encoding="utf-8")

    result = tool.validate_qa_evidence_privacy(qa, mode="share")

    assert result["status"] == "pass"
    assert result["findings"] == []
    assert {item["contract_version"] for item in result["json_manifest_safety"]} == {
        "release-stage-manifest.v5",
        "release-stage-manifest-validation.v6",
        "shareable-qa-evidence-manifest.v1",
    }
    assert all(item["safe_manifest"] for item in result["json_manifest_safety"])


def test_utf16_json_evidence_is_parseable(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "exhibition_smoke_check_3601_adb_latest.json").write_text(
        json.dumps({"contract_version": "local-smoke-report.v1", "ok": True}),
        encoding="utf-16",
    )

    result = tool.validate_qa_evidence_privacy(qa, mode="share")

    assert result["json_manifest_safety"][0]["parseable"] is True
    assert result["json_manifest_safety"][0]["contract_version"] == "local-smoke-report.v1"


def test_cli_reports_json_and_exits_nonzero_on_secret_blocker(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "leaky.json").write_text(
        json.dumps({"client_secret": "sk-testvalue1234567890"}),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--qa-root",
            str(qa),
            "--mode",
            "share",
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["status"] == "fail"
    assert result["share_readiness"]["blockers"][0]["code"] == "secret-like-json-key"
