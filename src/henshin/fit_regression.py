from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable


DEFAULT_BASELINE_MANIFEST = Path("viewer/assets/vrm/baselines.json")
DEFAULT_ATTACH_MODE = "vrm"


def _root_relative_posix(root: Path, candidate: str | Path) -> str:
    root = root.resolve()
    path = Path(candidate)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Path must stay within repository root: {candidate}") from exc


def load_baseline_manifest(path: str | Path) -> dict:
    manifest_path = Path(path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    defaults = data.get("defaults") or {}
    baselines = data.get("baselines")
    if not isinstance(baselines, list) or not baselines:
        raise ValueError(f"Invalid baseline manifest: {manifest_path}")
    return {
        "path": str(manifest_path),
        "schema_version": data.get("schema_version", "0"),
        "defaults": defaults,
        "baselines": baselines,
    }


def select_baselines(manifest: dict, baseline_ids: Iterable[str] | None = None) -> list[dict]:
    requested = {str(item) for item in baseline_ids or [] if str(item).strip()}
    baselines = []
    for entry in manifest.get("baselines") or []:
        if not entry.get("enabled", True):
            continue
        if requested and str(entry.get("id")) not in requested:
            continue
        baselines.append(entry)
    if requested and not baselines:
        raise ValueError(f"No enabled baselines matched ids: {', '.join(sorted(requested))}")
    if not baselines:
        raise ValueError("No enabled VRM baselines available.")
    return baselines


class _ThreadingHttpServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


@contextlib.contextmanager
def serve_static_root(root: Path):
    directory = root.resolve()
    class QuietStaticHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003 - stdlib signature
            return

    handler = functools.partial(QuietStaticHandler, directory=str(directory))
    server = _ThreadingHttpServer(("127.0.0.1", 0), handler)
    try:
        import threading

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _find_node() -> str:
    for candidate in ("node.exe", "node"):
        found = shutil.which(candidate)
        if found:
            return found
    raise RuntimeError("node is required to run fit regression browser harness.")


def run_browser_harness(
    *,
    root: Path,
    base_url: str,
    suitspec_path: str,
    sim_path: str,
    vrm_path: str,
    mode: str,
    force_tpose: bool,
    timeout_seconds: int,
    browser_channel: str | None = None,
    runner=subprocess.run,
) -> dict:
    node = _find_node()
    script_path = root / "tools" / "fit_regression_browser.mjs"
    if not script_path.exists():
        raise FileNotFoundError(f"Missing browser harness script: {script_path}")
    if not (root / "node_modules" / "playwright").exists():
        raise RuntimeError("Missing local 'playwright' dependency. Run 'npm install' in the repository root.")

    with tempfile.NamedTemporaryFile(prefix="fit-regression-", suffix=".json", delete=False) as tmp:
        output_path = Path(tmp.name)

    env = os.environ.copy()
    env.update(
        {
            "HENSHIN_FIT_REGRESSION_URL": base_url,
            "HENSHIN_FIT_REGRESSION_SUITSPEC": suitspec_path,
            "HENSHIN_FIT_REGRESSION_SIM": sim_path,
            "HENSHIN_FIT_REGRESSION_VRM": vrm_path,
            "HENSHIN_FIT_REGRESSION_MODE": mode,
            "HENSHIN_FIT_REGRESSION_FORCE_TPOSE": "1" if force_tpose else "0",
            "HENSHIN_FIT_REGRESSION_ATTACH_MODE": DEFAULT_ATTACH_MODE,
            "HENSHIN_FIT_REGRESSION_OUTPUT": str(output_path),
            "HENSHIN_FIT_REGRESSION_TIMEOUT_MS": str(int(timeout_seconds) * 1000),
        }
    )
    if browser_channel:
        env["HENSHIN_PLAYWRIGHT_CHANNEL"] = browser_channel

    command = [node, str(script_path)]
    completed = runner(
        command,
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=max(int(timeout_seconds) + 30, 60),
    )

    try:
        result = {}
        if output_path.exists():
            raw_output = output_path.read_text(encoding="utf-8").strip()
            if raw_output:
                result = json.loads(raw_output)
        if completed.returncode != 0:
            raise RuntimeError(
                (result.get("error") if isinstance(result, dict) else None)
                or completed.stderr.strip()
                or completed.stdout.strip()
                or f"Browser harness failed with exit code {completed.returncode}"
            )
        return result
    finally:
        with contextlib.suppress(FileNotFoundError):
            output_path.unlink()


def run_fit_regression(
    *,
    root: str | Path = ".",
    baselines_manifest: str | Path = DEFAULT_BASELINE_MANIFEST,
    suitspec: str | Path | None = None,
    sim: str | Path | None = None,
    baseline_ids: Iterable[str] | None = None,
    mode: str = "auto_fit",
    force_tpose: bool = True,
    timeout_seconds: int = 90,
    browser_channel: str | None = None,
    runner=subprocess.run,
) -> dict:
    repo_root = Path(root).resolve()
    manifest_path = (repo_root / baselines_manifest).resolve() if not Path(baselines_manifest).is_absolute() else Path(baselines_manifest).resolve()
    manifest = load_baseline_manifest(manifest_path)
    defaults = manifest.get("defaults") or {}
    suitspec_url = _root_relative_posix(repo_root, suitspec or defaults.get("suitspec_path") or "examples/suitspec.sample.json")
    sim_url = _root_relative_posix(repo_root, sim or defaults.get("sim_path") or "sessions/body-sim.json")
    force_tpose_value = bool(force_tpose if force_tpose is not None else defaults.get("force_tpose", True))

    baselines = select_baselines(manifest, baseline_ids)
    results = []
    with serve_static_root(repo_root) as server:
        base_url = f"http://127.0.0.1:{server.server_port}/viewer/body-fit/"
        for baseline in baselines:
            vrm_url = _root_relative_posix(repo_root, baseline["vrm_path"])
            entry = {
                "id": str(baseline.get("id") or vrm_url),
                "label": str(baseline.get("label") or baseline.get("id") or vrm_url),
                "vrm_path": vrm_url,
            }
            try:
                payload = run_browser_harness(
                    root=repo_root,
                    base_url=base_url,
                    suitspec_path=suitspec_url,
                    sim_path=sim_url,
                    vrm_path=vrm_url,
                    mode=mode,
                    force_tpose=force_tpose_value,
                    timeout_seconds=timeout_seconds,
                    browser_channel=browser_channel,
                    runner=runner,
                )
                entry.update(
                    {
                        "ok": bool(payload.get("ok")),
                        "summary": payload.get("summary"),
                        "wearable_summary": payload.get("wearableSummary") or payload.get("summary"),
                        "metrics": payload.get("metrics"),
                        "fit_by_part": payload.get("fitByPart"),
                        "anchor_by_part": payload.get("anchorByPart"),
                        "surface_model": payload.get("surfaceModel"),
                    }
                )
            except Exception as exc:  # pragma: no cover - exercised via tests through mocked runner
                entry.update({"ok": False, "error": str(exc)})
            results.append(entry)

    all_passed = all(bool(item.get("ok")) for item in results)
    return {
        "ok": all_passed,
        "root": str(repo_root),
        "baselines_manifest": str(manifest_path),
        "mode": mode,
        "force_tpose": force_tpose_value,
        "suitspec": suitspec_url,
        "sim": sim_url,
        "baselines": results,
    }


def write_fit_regression_output(result: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
