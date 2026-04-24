"""Local dashboard server for suit generation + preview workflows."""

from __future__ import annotations

import json
import os
import threading
import time
import base64
import binascii
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer, ThreadingMixIn
from typing import Any
from urllib.parse import parse_qs, urlparse

from .iw_henshin import (
    DEFAULT_EXPLANATION,
    DEFAULT_TRIGGER_PHRASE,
    IWSDKHenshinConfig,
    IWSDKHenshinRequest,
    run_iwsdk_henshin,
)
from .new_route_api import NewRouteApi
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


@dataclass(slots=True)
class IWHenshinVoicePayload:
    audio_base64: str
    mime_type: str = "audio/webm"
    audio_stats: dict[str, Any] | None = None
    session_id: str | None = None
    mocopi: str | None = "examples/mocopi_sequence.sample.json"
    trigger_phrase: str | None = None
    explanation: str | None = None
    dry_run: bool = False
    tts_enabled: bool = True


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


def _extension_for_mime(mime_type: str) -> str:
    lowered = (mime_type or "").split(";")[0].strip().lower()
    return {
        "audio/webm": "webm",
        "video/webm": "webm",
        "audio/ogg": "ogg",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/mp4": "mp4",
        "audio/aac": "aac",
    }.get(lowered, "webm")


def _decode_audio_base64(raw: str) -> bytes:
    if not raw:
        raise ValueError("audio_base64 is required.")
    encoded = raw.split(",", 1)[1] if raw.startswith("data:") and "," in raw else raw
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("audio_base64 is not valid base64.") from exc


def _normalize_audio_stats(stats: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(stats, dict):
        return None
    allowed = {
        "mode",
        "mime_type",
        "sample_rate",
        "channels",
        "samples",
        "duration_sec",
        "requested_sec",
        "peak",
        "rms",
        "dbfs",
        "zero_crossings",
        "quiet",
        "bytes",
    }
    normalized: dict[str, Any] = {}
    for key, value in stats.items():
        if key in allowed and isinstance(value, (str, int, float, bool)) and value is not None:
            normalized[key] = value
    return normalized or None


def _web_path(root: Path, raw_path: str | Path | None) -> str | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    candidate = path if path.is_absolute() else (root / path).resolve()
    try:
        rel = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return str(raw_path).replace("\\", "/")
    return "/" + rel.as_posix()


def _load_json_if_present(root: Path, raw_path: str | None) -> dict[str, Any] | None:
    if not raw_path:
        return None
    target = _resolve_repo_path(root, raw_path)
    return json.loads(target.read_text(encoding="utf-8"))


def _normalize_replay_paths(root: Path, replay: dict[str, Any]) -> dict[str, Any]:
    deposition = replay.get("deposition")
    if isinstance(deposition, dict):
        deposition["body_sim_path"] = _web_path(root, deposition.get("body_sim_path"))
    tts = replay.get("tts")
    if isinstance(tts, dict):
        tts["audio_path"] = _web_path(root, tts.get("audio_path"))
    return replay


def run_iw_henshin_voice(root: Path, payload: IWHenshinVoicePayload) -> dict[str, Any]:
    session_id = payload.session_id or f"S-IW-QUEST-{int(time.time() * 1000):x}"
    if not session_id.replace("-", "").isalnum():
        raise ValueError("session_id may only contain letters, numbers, and hyphens.")

    audio_bytes = _decode_audio_base64(payload.audio_base64)
    extension = _extension_for_mime(payload.mime_type)
    session_root = root / "sessions"
    audio_path = session_root / session_id / "artifacts" / f"voice-command.{extension}"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_bytes(audio_bytes)
    audio_stats = _normalize_audio_stats(payload.audio_stats)
    if audio_stats is not None:
        audio_stats["bytes"] = len(audio_bytes)
    voice_audio = {
        "url": _web_path(root, audio_path),
        "bytes": len(audio_bytes),
        "mime_type": payload.mime_type,
        "stats": audio_stats,
    }

    mocopi_payload = _load_json_if_present(root, payload.mocopi)
    config = IWSDKHenshinConfig(
        trigger_phrase=payload.trigger_phrase or os.getenv("VOICE_TRIGGER_PHRASE") or DEFAULT_TRIGGER_PHRASE,
        explanation_text=payload.explanation or DEFAULT_EXPLANATION,
        tts_enabled=payload.tts_enabled,
    )
    result = run_iwsdk_henshin(
        IWSDKHenshinRequest(
            audio_path=audio_path,
            mocopi_payload=mocopi_payload,
            session_id=session_id,
            root=session_root,
            dry_run=payload.dry_run,
            config=config,
        )
    )

    replay_path = result.get("replay_path")
    replay: dict[str, Any] | None = None
    if replay_path:
        replay_file = Path(str(replay_path))
        if replay_file.is_file():
            replay = _normalize_replay_paths(root, json.loads(replay_file.read_text(encoding="utf-8")))
            replay["voice_audio"] = voice_audio

    normalized_result = dict(result)
    for key in ("body_sim_path", "replay_path", "events_path"):
        normalized_result[key] = _web_path(root, normalized_result.get(key))
    tts = normalized_result.get("tts")
    if isinstance(tts, dict):
        tts["audio_path"] = _web_path(root, tts.get("audio_path"))
    normalized_result["voice_audio"] = voice_audio
    normalized_result["audio_stats"] = audio_stats

    return {
        "ok": bool(result.get("ok")),
        "result": normalized_result,
        "replay": replay,
        "replay_url": normalized_result.get("replay_path"),
        "body_sim_url": normalized_result.get("body_sim_path"),
        "voice_audio_url": voice_audio["url"],
        "voice_audio": voice_audio,
        "audio_url": tts.get("audio_path") if isinstance(tts, dict) else None,
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str, root: Path, jobs: GenerationJobManager, **kwargs: Any) -> None:
        self.repo_root = root
        self.jobs = jobs
        super().__init__(*args, directory=directory, **kwargs)

    @staticmethod
    def _new_route_response_for_test(root: Path, path: str):
        return NewRouteApi(root).get(path)

    @staticmethod
    def _new_route_post_response_for_test(
        root: Path,
        path: str,
        payload: dict[str, Any],
        *,
        suit_store_root: Path | None = None,
    ):
        return NewRouteApi(root, suit_store_root=suit_store_root).post(path, payload)

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
        new_route_response = NewRouteApi(self.repo_root).get(parsed.path)
        if new_route_response is not None:
            self._write_json(new_route_response.body, status=new_route_response.status)
            return
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

        if parsed.path.startswith("/v1/"):
            try:
                content_len = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                payload_dict = json.loads(raw)
                response = NewRouteApi(self.repo_root).post(parsed.path, payload_dict)
            except (ValueError, json.JSONDecodeError) as exc:
                self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if response is None:
                self._write_json({"ok": False, "error": "Unknown API endpoint."}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(response.body, status=response.status)
            return

        if parsed.path not in (
            "/api/generation-jobs",
            "/api/generate-parts",
            "/api/suitspec-save",
            "/api/iw-henshin/voice",
        ):
            self._write_json({"ok": False, "error": "Unknown API endpoint."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            payload_dict = json.loads(raw)
            if parsed.path == "/api/iw-henshin/voice":
                payload = IWHenshinVoicePayload(**payload_dict)
                result = run_iw_henshin_voice(self.repo_root, payload)
            elif parsed.path in ("/api/generation-jobs", "/api/generate-parts"):
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

        status = HTTPStatus.OK if parsed.path == "/api/iw-henshin/voice" or result.get("ok") else HTTPStatus.BAD_REQUEST
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
