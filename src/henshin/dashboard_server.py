"""Local dashboard server for suit generation + preview workflows."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer, ThreadingMixIn
from typing import Any
from urllib.parse import parse_qs, urlparse

from .part_generation import DEFAULT_PROVIDER_PROFILE, GenerationRequest, run_generate_parts


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_repo_path(root: Path, raw: str) -> Path:
    if not raw:
        raise ValueError("Path is required.")
    candidate = (root / raw).resolve()
    if not _is_within_root(candidate, root):
        raise ValueError(f"Path is outside repository root: {raw}")
    return candidate


def discover_suitspec_paths(root: Path) -> list[str]:
    candidates: set[str] = set()
    default = root / "examples" / "suitspec.sample.json"
    if default.exists():
        candidates.add(str(default.relative_to(root)).replace("\\", "/"))
    for path in (root / "sessions").glob("*/suitspec.json"):
        if path.is_file():
            candidates.add(str(path.relative_to(root)).replace("\\", "/"))
    for path in (root / "examples").glob("**/*suitspec*.json"):
        if path.is_file():
            candidates.add(str(path.relative_to(root)).replace("\\", "/"))
    return sorted(candidates)


@dataclass(slots=True)
class GeneratePartsPayload:
    suitspec: str
    session_id: str | None = None
    parts: list[str] | None = None
    root: str = "sessions"
    model_id: str | None = None
    api_key: str | None = None
    generation_brief: str | None = None
    emotion_profile: dict[str, Any] | None = None
    operator_profile_override: dict[str, Any] | None = None
    timeout: int = 90
    texture_mode: str = "mesh_uv"
    uv_refine: bool = False
    fallback_dir: str | None = None
    prefer_fallback: bool = False
    update_suitspec: bool = False
    dry_run: bool = False
    provider_profile: str = DEFAULT_PROVIDER_PROFILE
    priority_mode: str = "exhibition"
    use_cache: bool = True
    hero_render: bool = False
    tracking_source: str = "webcam"
    max_parallel: int = 4
    retry_count: int = 1


@dataclass(slots=True)
class SaveSuitspecPayload:
    path: str
    suitspec: dict[str, Any]


class GenerationJob:
    def __init__(self, job_id: str, payload: GeneratePartsPayload) -> None:
        self.job_id = job_id
        self.payload = payload
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.status = "queued"
        self.stage = "scan"
        self.events: list[dict[str, Any]] = []
        self.lock = threading.Condition()
        self.cancel_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.completed_count = 0
        self.requested_count = 0
        self.latest_preview_url: str | None = None
        self.summary_path: str | None = None
        self.hero_preview_url: str | None = None

    @property
    def is_done(self) -> bool:
        return self.status in {"completed", "failed", "cancelled"}

    def emit(self, event: dict[str, Any]) -> None:
        with self.lock:
            enriched = {
                "job_id": self.job_id,
                "event_id": len(self.events) + 1,
                "created_at": time.time(),
                **event,
            }
            self.updated_at = time.time()
            self.stage = str(enriched.get("stage") or self.stage)
            if enriched.get("preview_url"):
                self.latest_preview_url = str(enriched["preview_url"])
            if enriched.get("summary_path"):
                self.summary_path = str(enriched["summary_path"])
            if enriched.get("hero_preview_url"):
                self.hero_preview_url = str(enriched["hero_preview_url"])
            if enriched.get("requested_count") is not None:
                self.requested_count = int(enriched["requested_count"])
            if enriched.get("completed_count") is not None:
                self.completed_count = int(enriched["completed_count"])

            event_type = enriched.get("type")
            if event_type == "job_started":
                self.status = "running"
            elif event_type == "job_completed":
                self.status = "completed"
            elif event_type == "job_failed":
                self.status = "failed"
            elif event_type == "job_cancelled":
                self.status = "cancelled"

            self.events.append(enriched)
            self.lock.notify_all()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "ok": self.error is None,
                "job_id": self.job_id,
                "status": self.status,
                "stage": self.stage,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "completed_count": self.completed_count,
                "requested_count": self.requested_count,
                "latest_preview_url": self.latest_preview_url,
                "summary_path": self.summary_path,
                "hero_preview_url": self.hero_preview_url,
                "result": self.result,
                "error": self.error,
                "events": len(self.events),
            }


class GenerationJobManager:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.lock = threading.Lock()
        self.jobs: dict[str, GenerationJob] = {}

    def _validate_payload(self, payload: GeneratePartsPayload) -> None:
        _resolve_repo_path(self.repo_root, payload.suitspec)
        if payload.fallback_dir:
            _resolve_repo_path(self.repo_root, payload.fallback_dir)

    def create_job(self, payload: GeneratePartsPayload) -> GenerationJob:
        self._validate_payload(payload)
        job_id = f"job-{int(time.time() * 1000):x}"
        job = GenerationJob(job_id=job_id, payload=payload)
        with self.lock:
            self.jobs[job_id] = job
        thread = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        job.thread = thread
        thread.start()
        return job

    def get(self, job_id: str) -> GenerationJob:
        with self.lock:
            job = self.jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def cancel(self, job_id: str) -> GenerationJob:
        job = self.get(job_id)
        job.cancel_event.set()
        job.emit({"type": "job_cancel_requested", "stage": job.stage, "status": "cancelling"})
        return job

    def _run_job(self, job: GenerationJob) -> None:
        req = GenerationRequest(**asdict(job.payload))
        try:
            result = run_generate_parts(
                req,
                repo_root=self.repo_root,
                progress=job.emit,
                cancel_event=job.cancel_event,
            )
            job.result = result
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc)
            job.emit({"type": "job_failed", "stage": "error", "status": "failed", "log": job.error})


def run_generate_parts_sync(root: Path, payload: GeneratePartsPayload) -> dict[str, Any]:
    try:
        result = run_generate_parts(GenerationRequest(**asdict(payload)), repo_root=root)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    return {"ok": bool(result.get("ok")), "parsed": result}


def run_save_suitspec(root: Path, payload: SaveSuitspecPayload) -> dict[str, Any]:
    target = _resolve_repo_path(root, payload.path)
    if target.suffix.lower() != ".json":
        raise ValueError("Only JSON files can be saved.")
    if not isinstance(payload.suitspec, dict):
        raise ValueError("suitspec must be a JSON object.")
    text = json.dumps(payload.suitspec, ensure_ascii=False, indent=2) + "\n"
    target.write_text(text, encoding="utf-8")
    return {"ok": True, "path": str(target.relative_to(root)).replace("\\", "/")}


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str, root: Path, jobs: GenerationJobManager, **kwargs: Any) -> None:
        self.repo_root = root
        self.jobs = jobs
        super().__init__(*args, directory=directory, **kwargs)

    def _write_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _job_route(self, path: str) -> tuple[str, str | None]:
        suffix = path[len("/api/generation-jobs/") :]
        if not suffix:
            return "", None
        parts = suffix.split("/")
        job_id = parts[0]
        action = "/".join(parts[1:]) if len(parts) > 1 else None
        return job_id, action

    def _stream_sse(self, job: GenerationJob, cursor: int) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                with job.lock:
                    while cursor >= len(job.events) and not job.is_done:
                        job.lock.wait(timeout=10)
                        if cursor >= len(job.events):
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                    while cursor < len(job.events):
                        event = job.events[cursor]
                        cursor += 1
                        self.wfile.write(f"id: {event['event_id']}\n".encode("utf-8"))
                        self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    if job.is_done and cursor >= len(job.events):
                        break
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._write_json({"ok": True})
            return
        if parsed.path == "/api/suitspecs":
            self._write_json({"ok": True, "items": discover_suitspec_paths(self.repo_root)})
            return
        if parsed.path == "/api/suitspec":
            query = parse_qs(parsed.query)
            raw_path = (query.get("path") or [""])[0]
            try:
                target = _resolve_repo_path(self.repo_root, raw_path)
                payload = json.loads(target.read_text(encoding="utf-8"))
            except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json({"ok": True, "path": raw_path, "suitspec": payload})
            return
        if parsed.path.startswith("/api/generation-jobs/"):
            job_id, action = self._job_route(parsed.path)
            try:
                job = self.jobs.get(job_id)
            except KeyError:
                self._write_json({"ok": False, "error": f"Unknown job: {job_id}"}, status=HTTPStatus.NOT_FOUND)
                return
            if action == "events":
                query = parse_qs(parsed.query)
                cursor_raw = (query.get("cursor") or [self.headers.get("Last-Event-ID", "0")])[0] or "0"
                cursor = int(cursor_raw)
                self._stream_sse(job, cursor=max(0, cursor))
                return
            if action in (None, ""):
                self._write_json({"ok": True, **job.snapshot()})
                return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/generation-jobs/") and parsed.path.endswith("/cancel"):
            job_id, _ = self._job_route(parsed.path)
            try:
                job = self.jobs.cancel(job_id)
            except KeyError:
                self._write_json({"ok": False, "error": f"Unknown job: {job_id}"}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json({"ok": True, **job.snapshot()})
            return

        if parsed.path not in ("/api/generation-jobs", "/api/generate-parts", "/api/suitspec-save"):
            self._write_json({"ok": False, "error": "Unknown API endpoint."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            payload_dict = json.loads(raw)
            if parsed.path in ("/api/generation-jobs", "/api/generate-parts"):
                payload = GeneratePartsPayload(**payload_dict)
                if parsed.path == "/api/generation-jobs":
                    result = self.jobs.create_job(payload)
                    self._write_json({"ok": True, **result.snapshot()})
                    return
                result = run_generate_parts_sync(self.repo_root, payload)
            else:
                payload = SaveSuitspecPayload(**payload_dict)
                result = run_save_suitspec(self.repo_root, payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
        self._write_json(result, status=status)


def serve_dashboard(*, root: Path, port: int) -> None:
    class ReusableThreadingTCPServer(ThreadingMixIn, TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    directory = str(root)
    jobs = GenerationJobManager(root)

    def factory(*args: Any, **kwargs: Any) -> DashboardHandler:
        return DashboardHandler(*args, directory=directory, root=root, jobs=jobs, **kwargs)

    with ReusableThreadingTCPServer(("", port), factory) as httpd:
        print(
            json.dumps(
                {
                    "ok": True,
                    "message": "Serving suit dashboard",
                    "root": str(root),
                    "pid": os.getpid(),
                    "url": f"http://localhost:{port}/viewer/suit-dashboard/",
                },
                ensure_ascii=False,
            )
        )
        httpd.serve_forever()
