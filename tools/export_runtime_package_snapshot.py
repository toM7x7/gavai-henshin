"""Export a runtime package snapshot from a Quest recall code.

This is a read-only helper for PlayCanvas adapter rehearsals. It fetches
`/v1/quest/recall/{code}`, extracts `runtime_package`, and writes a portable
snapshot JSON that can be passed directly to `validate_playcanvas_snapshot.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote


CONTRACT_VERSION = "runtime-package-snapshot-export.v1"
USER_AGENT = "gavai-henshin-runtime-snapshot-export/1"


class SnapshotExportError(RuntimeError):
    """Raised when a runtime package snapshot cannot be exported."""


def export_runtime_package_snapshot(
    *,
    api_base: str,
    code: str,
    out: str | Path,
    timeout: float = 10.0,
) -> dict[str, Any]:
    recall_code = _normalize_code(code)
    endpoint = _quest_recall_url(api_base, recall_code)
    payload = fetch_quest_recall_payload(endpoint, timeout=timeout)
    runtime_package = payload.get("runtime_package") if isinstance(payload, dict) else None
    if not isinstance(runtime_package, dict):
        raise SnapshotExportError("Quest recall payload must contain a runtime_package object")

    out_path = Path(out)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(runtime_package, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise SnapshotExportError(f"Failed to write snapshot {out_path}: {exc}") from exc

    placements = runtime_package.get("render_placements") if isinstance(runtime_package.get("render_placements"), dict) else {}
    render_contract = runtime_package.get("render_contract") if isinstance(runtime_package.get("render_contract"), dict) else {}
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "status": "pass",
        "api_base": _normalize_api_base(api_base),
        "recall_code": recall_code,
        "endpoint": endpoint,
        "out": out_path.as_posix(),
        "runtime_package_contract": runtime_package.get("contract_version"),
        "render_placement_contract": render_contract.get("render_placement_contract"),
        "render_placement_count": len(placements),
        "render_placement_parts": sorted(str(part) for part in placements),
    }


def fetch_quest_recall_payload(endpoint: str, *, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        detail = f": {error_body[:500]}" if error_body else ""
        raise SnapshotExportError(f"GET {endpoint} failed with HTTP {exc.code}{detail}") from exc
    except urllib.error.URLError as exc:
        raise SnapshotExportError(f"GET {endpoint} failed: {exc.reason}") from exc

    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotExportError(f"GET {endpoint} did not return valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SnapshotExportError(f"GET {endpoint} must return a JSON object")
    return payload


def _quest_recall_url(api_base: str, code: str) -> str:
    base = _normalize_api_base(api_base)
    return f"{base}/v1/quest/recall/{quote(code, safe='')}"


def _normalize_api_base(api_base: str) -> str:
    base = str(api_base or "").strip().rstrip("/")
    if not base:
        raise SnapshotExportError("--api-base is required")
    return base


def _normalize_code(code: str) -> str:
    value = str(code or "").strip()
    if not value:
        raise SnapshotExportError("--code is required")
    return value


def _error_result(error: Exception) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": False,
        "status": "fail",
        "error": str(error),
    }


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result.get('out') or '<no output>'}")
    if result.get("ok"):
        print(f"endpoint: {result['endpoint']}")
        print(f"recall_code: {result['recall_code']}")
        print(f"render placements: {result['render_placement_count']}")
    else:
        print(f"error: {result.get('error')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", required=True, help="Base URL, e.g. http://127.0.0.1:8010")
    parser.add_argument("--code", required=True, help="Quest recall code")
    parser.add_argument("--out", required=True, type=Path, help="Output snapshot JSON path")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    args = parser.parse_args(argv)

    try:
        result = export_runtime_package_snapshot(
            api_base=args.api_base,
            code=args.code,
            out=args.out,
            timeout=args.timeout,
        )
    except SnapshotExportError as exc:
        result = _error_result(exc)

    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
