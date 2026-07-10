from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "audit_repo_readiness.py"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("audit_repo_readiness", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_repo_readiness"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _classified(path: str, category: str, status: str = "??") -> dict:
    return {
        "category": category,
        "path": path,
        "status": status,
        "tracked": status not in {"??", "!!"},
        "ignored": status == "!!",
        "reason": f"{category} reason",
        "recommended_action": "fallback-action",
        "old_path": "",
    }


def _fake_report(items: list[dict]) -> dict:
    return {
        "contract_version": "release-stage-candidates.v7",
        "repo_root": "C:/repo",
        "read_only": True,
        "git_status": {
            "include_ignored": True,
            "command": ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored"],
        },
        "items": items,
    }


def test_audit_blocks_raw_generated_and_local_paths(monkeypatch, tmp_path: Path) -> None:
    items = [
        _classified(".env", "local-only-root", "!!"),
        _classified("node_modules/.package-lock.json", "local-only-root", "!!"),
        _classified("sessions/.gitkeep", "local-only-root", " D"),
        _classified(".playwright-cli/page.png", "deleted-tracked-artifact", " D"),
        _classified("tests/.tmp/quest-api-live.err.log", "generated-artifact", " M"),
        _classified(".tmp-quest.err", "generated-artifact"),
        _classified("docs/archive/evidence-2026-05/root-runtime/.tmp-quest.out", "generated-artifact"),
        _classified("qa/exhibition_release_package_latest.json", "local-qa-artifact"),
        _classified("qa/exhibition-pc-transfer-checklist-latest.md", "local-qa-artifact"),
        _classified("qa/shareable-qa-evidence-latest.json", "qa-evidence"),
        _classified("examples/feedback.jpg", "user-feedback-media"),
        _classified(".claude/worktrees/demo/file.txt", "local-workspace"),
        _classified("src/henshin/new_route_api.py", "release-critical", " M"),
        _classified("docs/exhibition-pc-runbook-2026-05-04.md", "operator-docs"),
        _classified("viewer/assets/armor-parts/helmet/helmet.glb", "armor-assets"),
    ]

    monkeypatch.setattr(tool.stage_candidates, "build_report", lambda repo_root, include_ignored: _fake_report(items))

    payload = tool.build_audit(tmp_path, sample_limit=20)
    by_path = {item["path"]: item for group in payload["samples_by_stage_group"].values() for item in group}

    assert payload["contract_version"] == "repo-readiness-audit.v1"
    assert payload["read_only"] is True
    assert payload["ok"] is False
    assert payload["counts"]["blocked"] == 10
    assert payload["counts"]["tracked_blocked"] == 2
    assert payload["counts"]["by_recommended_stage_group"]["do-not-stage"] == 10
    assert payload["counts"]["by_recommended_stage_group"]["manual-review"] == 2
    assert payload["counts"]["by_recommended_stage_group"]["stage-candidate"] == 3
    assert by_path[".env"]["rule_id"] == "local-env-secret"
    assert by_path[".env"]["matched_glob"] == ".env"
    assert by_path["node_modules/.package-lock.json"]["category"] == "local-only-root"
    assert by_path["node_modules/.package-lock.json"]["rule_id"] == "dependency-cache"
    assert by_path["sessions/.gitkeep"]["category"] == "local-only-root"
    assert by_path["sessions/.gitkeep"]["rule_id"] == "session-generated-output"
    assert by_path[".playwright-cli/page.png"]["blocked"] is False
    assert by_path[".playwright-cli/page.png"]["rule_id"] == "category:deleted-tracked-artifact"
    assert by_path[".playwright-cli/page.png"]["recommended_stage_group"] == "manual-review"
    assert by_path["tests/.tmp/quest-api-live.err.log"]["rule_id"] == "test-temp-output"
    assert by_path["tests/.tmp/quest-api-live.err.log"]["tracked"] is True
    assert by_path[".tmp-quest.err"]["rule_id"] == "root-transient-output"
    assert by_path["docs/archive/evidence-2026-05/root-runtime/.tmp-quest.out"]["rule_id"] == "local-evidence-archive"
    assert by_path["qa/exhibition_release_package_latest.json"]["rule_id"] == "raw-qa-json"
    assert by_path["qa/exhibition-pc-transfer-checklist-latest.md"]["rule_id"] == "raw-qa-json"
    assert by_path["qa/shareable-qa-evidence-latest.json"]["blocked"] is False
    assert by_path["qa/shareable-qa-evidence-latest.json"]["recommended_stage_group"] == "manual-review"
    assert by_path["src/henshin/new_route_api.py"]["recommended_stage_group"] == "stage-candidate"
    blocker_codes = {item["code"] for item in payload["push_readiness"]["blockers"]}
    assert blocker_codes == {"blocked-paths-present", "tracked-blocked-paths-present"}


def test_audit_full_json_includes_items_and_cli_can_fail(monkeypatch, tmp_path: Path, capsys) -> None:
    items = [
        _classified("qa/replay/3601.replay-record.json", "local-qa-artifact"),
        _classified("README.md", "release-critical", " M"),
    ]

    monkeypatch.setattr(tool.stage_candidates, "build_report", lambda repo_root, include_ignored: _fake_report(items))

    rc = tool.main(["--repo-root", str(tmp_path), "--full-json", "--fail-on-blocked"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 1
    assert payload["ok"] is False
    assert len(payload["items"]) == 2
    assert payload["items"][0]["path"] == "qa/replay/3601.replay-record.json"
    assert payload["items"][0]["blocked"] is True
    assert payload["items"][0]["matched_glob"] == "qa/replay/*.json"
    assert payload["items"][1]["recommended_stage_group"] == "stage-candidate"


def test_audit_summary_suppresses_large_groups(monkeypatch, tmp_path: Path) -> None:
    items = [
        _classified(".playwright-cli/one.png", "generated-artifact", "!!"),
        _classified(".playwright-cli/two.png", "generated-artifact", "!!"),
        _classified(".playwright-cli/three.png", "generated-artifact", "!!"),
    ]

    monkeypatch.setattr(tool.stage_candidates, "build_report", lambda repo_root, include_ignored: _fake_report(items))

    payload = tool.build_audit(tmp_path, sample_limit=1)

    assert payload["counts"]["blocked"] == 3
    assert len(payload["blocked"]) == 1
    assert payload["blocked_suppressed"] == 2
    assert len(payload["samples_by_rule"]["browser-smoke-output"]) == 1
    assert payload["suppressed_by_rule"]["browser-smoke-output"] == 2


def test_safe_env_templates_are_not_caught_by_local_env_secret(monkeypatch, tmp_path: Path) -> None:
    items = [
        _classified(".env.example", "release-critical", " M"),
        _classified(".env.demo.example", "release-critical"),
        _classified("examples/foo/.env.example", "reference-artifact"),
    ]

    monkeypatch.setattr(tool.stage_candidates, "build_report", lambda repo_root, include_ignored: _fake_report(items))

    payload = tool.build_audit(tmp_path, sample_limit=10)
    all_samples = [item for group in payload["samples_by_stage_group"].values() for item in group]

    assert payload["ok"] is True
    assert payload["counts"]["blocked"] == 0
    assert {item["path"] for item in all_samples} == {
        ".env.example",
        ".env.demo.example",
        "examples/foo/.env.example",
    }
    assert all(item["rule_id"] != "local-env-secret" for item in all_samples)


def test_root_qa_globs_do_not_catch_docs_qa_paths(monkeypatch, tmp_path: Path) -> None:
    items = [
        _classified("docs/qa/mocopi-vr-exhibition-evidence-gate-2026-05-04.md", "reference-docs"),
        _classified("qa/raw-evidence.md", "local-qa-artifact"),
    ]

    monkeypatch.setattr(tool.stage_candidates, "build_report", lambda repo_root, include_ignored: _fake_report(items))

    payload = tool.build_audit(tmp_path, sample_limit=10)
    by_path = {item["path"]: item for group in payload["samples_by_rule"].values() for item in group}

    assert by_path["docs/qa/mocopi-vr-exhibition-evidence-gate-2026-05-04.md"]["rule_id"] == "category:reference-docs"
    assert by_path["docs/qa/mocopi-vr-exhibition-evidence-gate-2026-05-04.md"]["blocked"] is False
    assert by_path["qa/raw-evidence.md"]["rule_id"] == "raw-qa-json"
    assert by_path["qa/raw-evidence.md"]["blocked"] is True
