from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "export_shareable_qa_evidence_manifest.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("export_shareable_qa_evidence_manifest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_shareable_qa_evidence_manifest"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _write_safe_manifest(qa: Path) -> Path:
    path = qa / "mocopi-evidence-package-latest.json"
    path.write_text(
        json.dumps(
            {
                "contract_version": "mocopi-evidence-share-package.v1",
                "current_gate_label": "mocopi-DEMO-ONLY",
                "files_to_share": [{"path": "qa/mocopi-evidence-package-latest.json"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_release_manifests(qa: Path) -> None:
    (qa / "release-stage-manifest-latest.json").write_text(
        json.dumps({"contract_version": "release-stage-manifest.v5"}),
        encoding="utf-8",
    )
    (qa / "release-stage-validation-latest.json").write_text(
        json.dumps({"contract_version": "release-stage-manifest-validation.v6"}),
        encoding="utf-8",
    )


def _write_qa_tree(root: Path) -> Path:
    qa = root / "qa"
    logs = qa / "logs" / "quest-3601-demo"
    logs.mkdir(parents=True)
    _write_safe_manifest(qa)
    _write_release_manifests(qa)
    (logs / "screencap.png").write_bytes(b"\x89PNG\r\n")
    (logs / "adb-devices.txt").write_text("1WMHH000000000\tdevice\n", encoding="utf-8")
    (logs / "quest-debug-latest.json").write_text(
        json.dumps({"query": {"href": "http://localhost:5173/?code=3601"}}),
        encoding="utf-8",
    )
    (qa / "leaky.json").write_text(json.dumps({"client_secret": "sk-testvalue1234567890"}), encoding="utf-8")
    return qa


def test_exporter_extracts_only_curated_json_and_generated_manifest(tmp_path: Path) -> None:
    qa = _write_qa_tree(tmp_path)

    manifest = tool.export_shareable_qa_evidence_manifest(
        qa_root=qa,
        output_path=qa / "shareable-qa-evidence-latest.json",
    )

    share_paths = {item["path"] for item in manifest["shareable_files"]}
    local_paths = {item["path"] for item in manifest["local_only_files"]}
    blocked_paths = {item["path"] for item in manifest["blocked_files"]}

    assert manifest["contract_version"] == "shareable-qa-evidence-manifest.v1"
    assert "mocopi-evidence-package-latest.json" in share_paths
    assert "release-stage-manifest-latest.json" in share_paths
    assert "release-stage-validation-latest.json" in share_paths
    assert "shareable-qa-evidence-latest.json" in share_paths
    assert "logs/quest-3601-demo/screencap.png" in local_paths
    assert "logs/quest-3601-demo/adb-devices.txt" in local_paths
    assert "logs/quest-3601-demo/quest-debug-latest.json" in local_paths
    assert "leaky.json" in blocked_paths
    assert "qa/mocopi-evidence-package-latest.json" in manifest["recommended_git_stage_paths"]
    assert "qa/release-stage-manifest-latest.json" in manifest["recommended_git_stage_paths"]
    assert "qa/release-stage-validation-latest.json" in manifest["recommended_git_stage_paths"]
    assert "qa/shareable-qa-evidence-latest.json" in manifest["recommended_git_stage_paths"]
    assert all("screencap" not in path for path in manifest["recommended_git_stage_paths"])


def test_exporter_can_use_existing_privacy_report_json(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    _write_safe_manifest(qa)
    privacy_report = {
        "contract_version": "qa-evidence-privacy-validation.v1",
        "mode": "share",
        "qa_root": qa.as_posix(),
        "ok": True,
        "status": "pass",
        "json_manifest_safety": [
            {
                "path": "mocopi-evidence-package-latest.json",
                "parseable": True,
                "contract_version": "mocopi-evidence-share-package.v1",
                "safe_manifest": True,
            }
        ],
        "share_readiness": {"ready": True, "blockers": [], "warnings": [], "local_evidence": []},
        "findings": [],
    }

    manifest = tool.export_shareable_qa_evidence_manifest(
        qa_root=qa,
        privacy_report=privacy_report,
        privacy_report_path=qa / "privacy.json",
        output_path=qa / "shareable-qa-evidence-latest.json",
    )

    assert manifest["privacy_gate_status"]["source"].endswith("privacy.json")
    assert manifest["privacy_gate_status"]["ready_for_curated_share"] is True
    assert len(manifest["shareable_files"]) == 2
    assert manifest["local_only_files"] == []
    assert manifest["blocked_files"] == []


def test_warning_only_files_are_local_only_not_blocked(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    _write_safe_manifest(qa)
    (qa / "operator-summary.txt").write_text("href: http://localhost:5173/?code=3601\n", encoding="utf-8")

    manifest = tool.export_shareable_qa_evidence_manifest(
        qa_root=qa,
        output_path=qa / "shareable-qa-evidence-latest.json",
    )

    assert any(item["path"] == "operator-summary.txt" for item in manifest["local_only_files"])
    assert manifest["blocked_files"] == []
    assert manifest["privacy_gate_status"]["ready_for_curated_share"] is True


def test_cli_writes_manifest_and_reports_json(tmp_path: Path) -> None:
    qa = _write_qa_tree(tmp_path)
    out = qa / "shareable-qa-evidence-latest.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--qa-root",
            str(qa),
            "--out",
            str(out),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_manifest = json.loads(completed.stdout)
    file_manifest = json.loads(out.read_text(encoding="utf-8"))

    assert stdout_manifest["contract_version"] == "shareable-qa-evidence-manifest.v1"
    assert file_manifest["recommended_git_stage_paths"] == stdout_manifest["recommended_git_stage_paths"]
    assert out.exists()
