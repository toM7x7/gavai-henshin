from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_shareable_qa_evidence_manifest.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("validate_shareable_qa_evidence_manifest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_shareable_qa_evidence_manifest"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _write_shareable_files(qa: Path) -> None:
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "mocopi-evidence-package-latest.json").write_text(
        json.dumps({"contract_version": "mocopi-evidence-share-package.v1"}),
        encoding="utf-8",
    )
    (qa / "shareable-qa-evidence-latest.json").write_text("{}", encoding="utf-8")


def _manifest(*, blocked: bool = False, raw_recommended: bool = False) -> dict:
    recommended = [
        "qa/mocopi-evidence-package-latest.json",
        "qa/shareable-qa-evidence-latest.json",
    ]
    if raw_recommended:
        recommended.append("qa/logs/quest-3601-demo/screencap.png")
    payload = {
        "contract_version": "shareable-qa-evidence-manifest.v1",
        "qa_root": "qa",
        "privacy_gate_status": {"status": "pass", "ready_for_curated_share": True},
        "shareable_files": [
            {
                "path": "mocopi-evidence-package-latest.json",
                "git_stage_path": "qa/mocopi-evidence-package-latest.json",
                "kind": "curated_json_manifest",
            },
            {
                "path": "shareable-qa-evidence-latest.json",
                "git_stage_path": "qa/shareable-qa-evidence-latest.json",
                "kind": "shareable_qa_manifest",
            },
        ],
        "local_only_files": [
            {
                "path": "logs/quest-3601-demo/screencap.png",
                "kind": "media_or_screenshot",
                "reason": "local only",
            }
        ],
        "blocked_files": [],
        "recommended_git_stage_paths": recommended,
    }
    if blocked:
        payload["blocked_files"] = [
            {
                "path": "leaky.json",
                "kind": "blocked_privacy_finding",
                "reason": "secret-like key",
                "recommended_action": "redact before sharing",
            }
        ]
    return payload


def _release_manifest(paths: list[str], *, local_paths: list[str] | None = None) -> dict:
    return {
        "contract_version": "release-stage-manifest.v3",
        "categories": {
            "qa-evidence": {
                "samples": [{"path": path} for path in paths],
            },
            "local-qa-artifact": {
                "samples": [{"path": path} for path in (local_paths or [])],
            },
        },
    }


def test_valid_manifest_aligns_with_release_stage_manifest(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    _write_shareable_files(qa)
    manifest = _manifest()
    manifest["qa_root"] = qa.as_posix()

    result = tool.validate_shareable_qa_evidence_manifest(
        manifest,
        release_stage_manifest=_release_manifest(manifest["recommended_git_stage_paths"]),
    )

    assert result["status"] == "pass"
    assert result["ok"] is True
    assert result["counts"]["shareable_files"] == 2
    assert result["release_alignment"]["unsafe_qa_evidence_paths"] == []


def test_missing_shareable_file_is_blocker(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    qa.mkdir()
    manifest = _manifest()
    manifest["qa_root"] = qa.as_posix()

    result = tool.validate_shareable_qa_evidence_manifest(manifest)

    assert result["status"] == "fail"
    assert any(item["code"] == "shareable-file-missing" for item in result["blockers"])


def test_blocked_files_warn_by_default_and_fail_in_strict(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    _write_shareable_files(qa)
    manifest = _manifest(blocked=True)
    manifest["qa_root"] = qa.as_posix()

    relaxed = tool.validate_shareable_qa_evidence_manifest(manifest)
    strict = tool.validate_shareable_qa_evidence_manifest(manifest, strict=True)

    assert relaxed["status"] == "warn"
    assert any(item["code"] == "blocked-files-present" for item in relaxed["warnings"])
    assert strict["status"] == "fail"
    assert any(item["code"] == "blocked-files-present" for item in strict["blockers"])


def test_recommended_raw_or_local_only_path_is_blocker(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    _write_shareable_files(qa)
    logs = qa / "logs" / "quest-3601-demo"
    logs.mkdir(parents=True)
    (logs / "screencap.png").write_bytes(b"\x89PNG\r\n")
    manifest = _manifest(raw_recommended=True)
    manifest["qa_root"] = qa.as_posix()

    result = tool.validate_shareable_qa_evidence_manifest(manifest)

    codes = {item["code"] for item in result["blockers"]}
    assert "recommended-stage-path-raw" in codes
    assert "recommended-stage-path-local-only" in codes


def test_release_manifest_raw_qa_evidence_is_blocker(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    _write_shareable_files(qa)
    manifest = _manifest()
    manifest["qa_root"] = qa.as_posix()
    release = _release_manifest(["qa/logs/quest-3601-demo/adb-devices.txt"])

    result = tool.validate_shareable_qa_evidence_manifest(manifest, release_stage_manifest=release)

    assert result["status"] == "fail"
    assert any(item["code"] == "release-qa-evidence-unsafe" for item in result["blockers"])


def test_release_manifest_unknown_qa_evidence_warns_or_blocks_in_strict(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    _write_shareable_files(qa)
    manifest = _manifest()
    manifest["qa_root"] = qa.as_posix()
    release = _release_manifest(["qa/other-clean-clone-summary.json"])

    relaxed = tool.validate_shareable_qa_evidence_manifest(manifest, release_stage_manifest=release)
    strict = tool.validate_shareable_qa_evidence_manifest(manifest, release_stage_manifest=release, strict=True)

    assert relaxed["status"] == "warn"
    assert any(item["code"] == "release-qa-evidence-not-recommended" for item in relaxed["warnings"])
    assert strict["status"] == "fail"
    assert any(item["code"] == "release-qa-evidence-not-recommended" for item in strict["blockers"])


def test_cli_reports_json_and_uses_default_manifest_path(tmp_path: Path) -> None:
    qa = tmp_path / "qa"
    _write_shareable_files(qa)
    manifest = _manifest()
    manifest["qa_root"] = qa.as_posix()
    manifest_path = qa / "shareable-qa-evidence-latest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    release_path = qa / "release-stage-manifest-latest.json"
    release_path.write_text(json.dumps(_release_manifest(manifest["recommended_git_stage_paths"])), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--manifest",
            str(manifest_path),
            "--release-stage-manifest",
            str(release_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["contract_version"] == "shareable-qa-evidence-manifest-validation.v1"
    assert result["status"] == "pass"
    assert result["release_alignment"]["provided"] is True
