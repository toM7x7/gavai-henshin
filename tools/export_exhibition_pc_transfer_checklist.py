"""Export an exhibition-PC transfer checklist.

This is a static pre-transfer helper. It checks that the operator-facing
README/runbook/env/scripts/QA artifacts needed by a separate exhibition PC are
present, then writes a JSON or Markdown checklist for the release owner.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


CONTRACT_VERSION = "exhibition-pc-transfer-checklist.v1"
DEFAULT_JSON_OUT = Path("qa/exhibition-pc-transfer-checklist-latest.json")
DEFAULT_MARKDOWN_OUT = Path("qa/exhibition-pc-transfer-checklist-latest.md")
OutputFormat = Literal["json", "markdown"]


@dataclass(frozen=True)
class RequiredItem:
    key: str
    label: str
    category: str
    description: str
    path: str | None = None
    patterns: tuple[str, ...] = ()


REQUIRED_ITEMS: tuple[RequiredItem, ...] = (
    RequiredItem(
        key="readme",
        label="README",
        category="operator_docs",
        path="README.md",
        description="Top-level project orientation for a fresh exhibition PC checkout or zip.",
    ),
    RequiredItem(
        key="demo_env_template",
        label="Demo env template",
        category="env",
        path=".env.demo.example",
        description="Local exhibition fallback env template with no real secrets.",
    ),
    RequiredItem(
        key="local_stack_helper",
        label="Local stack helper",
        category="script",
        path="tools/start_exhibition_local_stack.ps1",
        description="One-command API/Web Forge/Quest Vite/ADB reverse/smoke setup helper.",
    ),
    RequiredItem(
        key="adb_reverse_helper",
        label="Quest ADB reverse helper",
        category="script",
        path="tools/start_quest_adb_reverse.ps1",
        description="USB Quest reverse-port helper for 5173 and 8010.",
    ),
    RequiredItem(
        key="runbook",
        label="Exhibition PC runbook",
        category="operator_docs",
        path="docs/exhibition-pc-runbook-2026-05-04.md",
        description="Operator runbook for local stack, Quest USB, smoke checks, and recovery.",
    ),
    RequiredItem(
        key="service_contract_tool",
        label="Service deployment contract tool",
        category="qa_tool",
        path="tools/validate_service_deployment_contract.py",
        description="Local/external URL and env contract validator.",
    ),
    RequiredItem(
        key="release_package_validator",
        label="Release package validator",
        category="qa_tool",
        path="tools/validate_exhibition_release_package.py",
        description="Release package completeness validator.",
    ),
    RequiredItem(
        key="qa_release_manifest",
        label="Release package QA manifest",
        category="qa_artifact",
        path="qa/exhibition_release_package_latest.json",
        description="Latest release package QA JSON to carry beside the transferred package.",
    ),
    RequiredItem(
        key="replay_qa_artifact",
        label="Replay QA artifact",
        category="qa_artifact",
        patterns=(
            "qa/replay/*.replay-record.json",
            "qa/replay/*.summary.json",
            "qa/replay-record-*.demo.json",
        ),
        description="Replay proof or prepared ReplayRecord QA artifact for Web/Replay validation.",
    ),
)


def build_transfer_checklist(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    ready_items: list[dict[str, Any]] = []
    missing_items: list[dict[str, Any]] = []

    for item in REQUIRED_ITEMS:
        report = _item_report(root, item)
        if report["status"] == "ready":
            ready_items.append(report)
        else:
            missing_items.append(report)

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not missing_items,
        "status": "pass" if not missing_items else "fail",
        "generated_at": _now_iso(),
        "repo_root": root.as_posix(),
        "ready_count": len(ready_items),
        "missing_count": len(missing_items),
        "ready_items": ready_items,
        "missing_items": missing_items,
        "manual_steps": _manual_steps(),
        "urls": _operator_urls(),
        "usb_quest_steps": _usb_quest_steps(),
        "do_not_copy_items": _do_not_copy_items(),
        "recommended_commands": _recommended_commands(),
    }


def export_transfer_checklist(
    repo_root: str | Path = ".",
    *,
    out: str | Path | None = None,
    output_format: OutputFormat = "json",
) -> dict[str, Any]:
    if output_format not in {"json", "markdown"}:
        raise ValueError("output_format must be 'json' or 'markdown'")

    result = build_transfer_checklist(repo_root)
    out_path = Path(out) if out is not None else _default_out(output_format)
    if not out_path.is_absolute():
        out_path = Path(repo_root) / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result["out"] = out_path.resolve().as_posix()
    result["format"] = output_format

    if output_format == "json":
        _write_utf8_no_bom(out_path, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        _write_utf8_no_bom(out_path, render_markdown_checklist(result))

    return result


def render_markdown_checklist(result: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Exhibition PC Transfer Checklist",
        "",
        f"- contract_version: `{result['contract_version']}`",
        f"- status: `{result['status']}`",
        f"- ready_items: `{result['ready_count']}`",
        f"- missing_items: `{result['missing_count']}`",
        "",
        "## Ready Items",
    ]
    lines.extend(_markdown_item_lines(result["ready_items"], checked=True))
    lines.extend(["", "## Missing Items"])
    lines.extend(_markdown_item_lines(result["missing_items"], checked=False))
    lines.extend(["", "## Manual Steps"])
    lines.extend(f"{index}. {step}" for index, step in enumerate(result["manual_steps"], start=1))
    lines.extend(["", "## URLs"])
    for key, value in result["urls"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## USB Quest Steps"])
    lines.extend(f"{index}. {step}" for index, step in enumerate(result["usb_quest_steps"], start=1))
    lines.extend(["", "## Do Not Copy"])
    lines.extend(f"- {item}" for item in result["do_not_copy_items"])
    lines.extend(["", "## Recommended Commands"])
    lines.extend(f"- `{command}`" for command in result["recommended_commands"])
    return "\n".join(lines).rstrip() + "\n"


def _item_report(root: Path, item: RequiredItem) -> dict[str, Any]:
    base = {
        "key": item.key,
        "label": item.label,
        "category": item.category,
        "description": item.description,
        "required": True,
    }
    if item.path is not None:
        path = root / item.path
        return {
            **base,
            "status": "ready" if path.is_file() else "missing",
            "path": item.path,
            "present": path.is_file(),
        }

    matched = sorted(
        {
            match.as_posix()
            for pattern in item.patterns
            for match in root.glob(pattern)
            if match.is_file()
        }
    )
    return {
        **base,
        "status": "ready" if matched else "missing",
        "patterns": list(item.patterns),
        "matched_count": len(matched),
        "matched_paths": [_rel(root, Path(path)) for path in matched],
        "present": bool(matched),
    }


def _manual_steps() -> list[str]:
    return [
        r"Copy or unzip the package to C:\henshin-demo\gavai-henshin on the exhibition PC.",
        "Run npm install and python -m pip install -e \".[dev]\" on the exhibition PC.",
        "Copy .env.demo.example to .env only on the exhibition PC, then fill venue-local placeholders if needed.",
        "Run the release package validator and keep its JSON under qa/ before doors open.",
        "Start the local stack helper with a fresh Web Forge code for the public visitor path.",
        "Record local-pass/local-fail before evaluating service, PlayCanvas, or mocopi optional lanes.",
    ]


def _operator_urls() -> dict[str, str]:
    return {
        "web_forge": "http://127.0.0.1:8010/viewer/armor-forge/",
        "api_health": "http://127.0.0.1:8010/api/health",
        "quest_usb_template": "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>",
        "quest_manual_entry_usb_adb": "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1",
        "quest_lan_fallback_template": "http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>",
    }


def _usb_quest_steps() -> list[str]:
    return [
        "Connect the Quest to the exhibition PC with a USB-C data cable.",
        "Put on the headset and accept the USB debugging prompt.",
        "Run adb devices -l and confirm the state is device, not unauthorized or offline.",
        r"Run .\tools\start_quest_adb_reverse.ps1 -RecallCode <CODE> -CacheBust -LaunchBrowser.",
        "Confirm adb reverse --list includes tcp:5173 tcp:5173 and tcp:8010 tcp:8010.",
        "Open the Quest USB URL with the same fresh code that Web Forge generated.",
    ]


def _do_not_copy_items() -> list[str]:
    return [
        ".env files containing real provider secrets or venue-only credentials.",
        "node_modules/, .venv/, venv/, __pycache__/, or .pytest_cache/ dependency caches.",
        r"Machine-local absolute paths such as C:\dev\codex\gavai-henshin.",
        "Old Quest Browser tabs, browser cache, or stale recall codes as QA evidence.",
        "Downloaded cloud credential files or service account keys.",
    ]


def _recommended_commands() -> list[str]:
    return [
        "python tools/export_exhibition_pc_transfer_checklist.py --report-json",
        "python tools/validate_exhibition_release_package.py --report-json > qa\\exhibition_release_package_external_pc.json",
        ".\\tools\\start_exhibition_local_stack.ps1 -RecallCode <CODE> -LaunchQuest -RequireAdbReverseSmoke",
    ]


def _markdown_item_lines(items: list[dict[str, Any]], *, checked: bool) -> list[str]:
    if not items:
        return ["- None"]
    marker = "x" if checked else " "
    lines = []
    for item in items:
        path = item.get("path") or ", ".join(item.get("patterns", []))
        lines.append(f"- [{marker}] `{item['key']}` - {item['label']} (`{path}`)")
    return lines


def _default_out(output_format: OutputFormat) -> Path:
    return DEFAULT_MARKDOWN_OUT if output_format == "markdown" else DEFAULT_JSON_OUT


def _write_utf8_no_bom(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result['out']}")
    print(f"ready_items={result['ready_count']} missing_items={result['missing_count']}")
    for item in result["missing_items"]:
        path = item.get("path") or ", ".join(item.get("patterns", []))
        print(f"  missing  {item['key']} ({path})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository/package root to inspect")
    parser.add_argument("--out", type=Path, help="Checklist output path")
    parser.add_argument("--format", choices=("json", "markdown"), default="json", help="Checklist file format")
    parser.add_argument("--report-json", action="store_true", help="Emit the checklist report JSON to stdout")
    args = parser.parse_args(argv)

    result = export_transfer_checklist(args.repo_root, out=args.out, output_format=args.format)
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
