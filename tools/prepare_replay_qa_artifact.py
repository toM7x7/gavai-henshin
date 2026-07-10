"""Prepare a ReplayRecord QA artifact for Web replay checking.

This tool is intentionally browser-free. It normalizes a ReplayRecord JSON file
into a stable QA directory, runs the variant alignment validator against that
copied artifact, and writes a small summary JSON that operators can keep beside
screenshots or manual Web replay notes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


CONTRACT_VERSION = "replay-qa-artifact-summary.v1"
DEFAULT_QA_DIR = Path("qa/replay")
PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION = "replay-public-artifact-policy.v1"
QUEST_REPLAY_VIEWER_PATH = "viewer/quest-iw-demo/index.html"
QUEST_REPLAY_RECORD_QUERY_PARAM = "replay"
QUEST_RECALL_CODE_QUERY_PARAM = "code"
QUEST_QA_CODE_QUERY_PARAM = "qa"


def prepare_replay_qa_artifact(
    replay_record: str | Path | dict[str, Any],
    *,
    code: str | None = None,
    qa_dir: str | Path = DEFAULT_QA_DIR,
    out_summary: str | Path | None = None,
) -> dict[str, Any]:
    record, source_path = _load_record(replay_record)
    qa_root = Path(qa_dir)
    qa_root.mkdir(parents=True, exist_ok=True)
    artifact_code = _artifact_code(code, record)
    artifact_path = qa_root / f"{artifact_code}.replay-record.json"
    summary_path = Path(out_summary) if out_summary else qa_root / f"{artifact_code}.summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    normalized_record = _normalize_replay_record(record, artifact_code=artifact_code, source_path=source_path)
    artifact_path.write_text(json.dumps(normalized_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    alignment_report = _validate_alignment(artifact_path)
    summary = _summary(
        normalized_record,
        source_path=source_path,
        artifact_path=artifact_path,
        summary_path=summary_path,
        artifact_code=artifact_code,
        alignment_report=alignment_report,
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _summary(
    record: dict[str, Any],
    *,
    source_path: str | None,
    artifact_path: Path,
    summary_path: Path,
    artifact_code: str,
    alignment_report: dict[str, Any],
) -> dict[str, Any]:
    alignment_status = str(alignment_report.get("status") or "fail")
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": bool(alignment_report.get("ok")),
        "status": "pass" if alignment_report.get("ok") else "fail",
        "source_path": source_path,
        "artifact_code": artifact_code,
        "artifact_path": artifact_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "replay_id": record.get("replay_id"),
        "recall_code": record.get("recall_code"),
        "experience_label": _dict(record.get("experience")).get("label"),
        "alignment_status": alignment_status,
        "alignment_report": alignment_report,
        "web_replay_check_url_hint": _web_replay_check_url_hint(
            artifact_path,
            artifact_code=artifact_code,
            recall_code=record.get("recall_code"),
        ),
        "recommended_operator_check": _recommended_operator_check(alignment_status),
    }


def _normalize_replay_record(
    record: dict[str, Any],
    *,
    artifact_code: str,
    source_path: str | None,
) -> dict[str, Any]:
    normalized = _clone(record)
    normalized.setdefault("metadata", {})
    if isinstance(normalized["metadata"], dict):
        normalized["metadata"].setdefault("qa_artifact_code", artifact_code)
        normalized["metadata"].setdefault("qa_source_path", _portable_source_ref(source_path))
        normalized["metadata"].setdefault("qa_prepared_by", "tools/prepare_replay_qa_artifact.py")
    normalized["public_artifact_policy"] = _public_artifact_policy(normalized.get("public_artifact_policy"))
    return normalized


def _web_replay_check_url_hint(artifact_path: Path, *, artifact_code: str, recall_code: Any = None) -> str:
    query = {
        QUEST_REPLAY_RECORD_QUERY_PARAM: artifact_path.as_posix(),
        QUEST_QA_CODE_QUERY_PARAM: artifact_code,
    }
    viewer_recall_code = _viewer_recall_code(recall_code)
    if viewer_recall_code:
        query[QUEST_RECALL_CODE_QUERY_PARAM] = viewer_recall_code
    return f"{QUEST_REPLAY_VIEWER_PATH}?{urlencode(query)}"


def _recommended_operator_check(alignment_status: str) -> dict[str, Any]:
    return {
        "mode": "manual_web_replay_static_qa",
        "requires_browser_launch": False,
        "pass_alignment_before_visual_review": alignment_status == "pass",
        "steps": [
            "Open the Web replay/check view using web_replay_check_url_hint.",
            "Confirm the displayed recall code and experience label match the summary.",
            "Confirm selected armor variants match the saved ReplayRecord.",
            "Capture screenshots or notes beside artifact_path and summary_path.",
        ],
        "fail_policy": (
            "Do not accept Web replay screenshots as exhibition QA evidence until "
            "alignment_status is pass."
        ),
    }


def _load_record(replay_record: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(replay_record, dict):
        return replay_record, None
    path = Path(replay_record)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("ReplayRecord JSON must be an object")
    return data, path.as_posix()


def _validate_alignment(artifact_path: Path) -> dict[str, Any]:
    validator = _load_alignment_validator()
    return validator.validate_replay_variant_alignment(artifact_path)


def _load_alignment_validator():
    module_name = "validate_replay_variant_alignment"
    if module_name in sys.modules:
        return sys.modules[module_name]
    tool_path = Path(__file__).with_name("validate_replay_variant_alignment.py")
    spec = importlib.util.spec_from_file_location(module_name, tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_replay_variant_alignment.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _artifact_code(code: str | None, record: dict[str, Any]) -> str:
    raw = (
        str(code or "").strip()
        or str(record.get("recall_code") or "").strip()
        or str(record.get("replay_id") or "").strip()
        or "latest"
    )
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    return slug or "latest"


def _viewer_recall_code(value: Any) -> str:
    code = re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())[:4]
    return code if len(code) == 4 else ""


def _portable_source_ref(path: str | None) -> str:
    if not path:
        return ""
    source = Path(path)
    try:
        return source.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (OSError, ValueError):
        return source.name or ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _public_artifact_policy(existing: Any = None) -> dict[str, Any]:
    policy = _clone(existing) if isinstance(existing, dict) else {}
    policy.setdefault("contract_version", PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION)
    policy.setdefault("role", "snapshot_consumer")
    policy["playcanvas_writeback_allowed"] = False
    policy["local_path_allowed"] = False
    policy["external_publication_requires_preflight"] = True
    policy.setdefault("external_preflight_tool", "tools/validate_replay_public_artifact.py --mode external")
    return policy


def _clone(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _print_text_report(summary: dict[str, Any]) -> None:
    print(f"[{summary['status'].upper()}] {summary['artifact_path']}")
    print(f"alignment: {summary['alignment_status']}")
    print(f"web hint: {summary['web_replay_check_url_hint']}")
    for reason in summary.get("alignment_report", {}).get("reasons", []):
        print(f"  fail  {reason}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay_record", type=Path, help="ReplayRecord JSON path")
    parser.add_argument("--code", help="Stable QA artifact code; defaults to replay recall_code")
    parser.add_argument("--qa-dir", type=Path, default=DEFAULT_QA_DIR, help="QA artifact directory")
    parser.add_argument("--out-summary", type=Path, help="Summary JSON output path")
    parser.add_argument("--report-json", action="store_true", help="Emit summary JSON to stdout")
    args = parser.parse_args(argv)

    summary = prepare_replay_qa_artifact(
        args.replay_record,
        code=args.code,
        qa_dir=args.qa_dir,
        out_summary=args.out_summary,
    )
    if args.report_json:
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
