"""Image generation provider adapters with timing and progress hooks."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .gemini_image import (
    GeminiImageError,
    GeminiReferenceImage,
    generate_image as generate_gemini_image,
    resolve_api_key as resolve_gemini_api_key,
)


ProgressCallback = Callable[[dict[str, Any]], None]


class ImageProviderError(RuntimeError):
    """Raised when an image provider request fails."""


@dataclass(slots=True)
class ImageReference:
    mime_type: str
    image_bytes: bytes


@dataclass(slots=True)
class GeneratedImage:
    provider: str
    model_id: str
    mime_type: str
    image_bytes: bytes
    prompt: str
    response_id: str | None
    timestamp: str
    queue_wait_ms: int = 0
    inference_ms: int = 0
    total_ms: int = 0
    logs: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] | None = None


def _load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}

    values: dict[str, str] = {}
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def resolve_provider_api_key(provider: str, explicit: str | None = None, dotenv_path: str | Path = ".env") -> str:
    if provider == "gemini":
        return resolve_gemini_api_key(explicit, dotenv_path=dotenv_path)

    if explicit:
        return explicit

    env_keys = {
        "fal": ("FAL_KEY", "FAL_API_KEY"),
        "openai": ("OPENAI_API_KEY",),
    }
    keys = env_keys.get(provider)
    if not keys:
        raise ImageProviderError(f"Unsupported provider: {provider}")

    for key in keys:
        value = os.getenv(key)
        if value:
            return value

    dotenv = _load_dotenv(dotenv_path)
    for key in keys:
        value = dotenv.get(key)
        if value:
            return value

    raise ImageProviderError(f"API key is missing for provider={provider}.")


def _json_request(
    url: str,
    *,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        url=url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urlopen(req, timeout=timeout_seconds) as res:
            body = res.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageProviderError(f"HTTP error from {url}: status={exc.code} body={detail}") from exc
    except URLError as exc:
        raise ImageProviderError(f"Connection error for {url}: {exc}") from exc

    if not body.strip():
        return {}
    return json.loads(body)


def _binary_request(url: str, *, headers: dict[str, str] | None = None, timeout_seconds: int = 90) -> tuple[bytes, str]:
    req = Request(url=url, method="GET", headers=headers or {})
    try:
        with urlopen(req, timeout=timeout_seconds) as res:
            mime_type = res.headers.get_content_type() or "image/png"
            return res.read(), mime_type
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageProviderError(f"HTTP error while downloading {url}: status={exc.code} body={detail}") from exc
    except URLError as exc:
        raise ImageProviderError(f"Download error for {url}: {exc}") from exc


def _sized_dimensions(aspect_ratio: str | None, image_size: str | None) -> tuple[int, int]:
    edge = 1024
    if image_size == "2K":
        edge = 1536
    if aspect_ratio == "16:9":
        return edge, int(edge * 9 / 16)
    if aspect_ratio == "9:16":
        return int(edge * 9 / 16), edge
    return edge, edge


def _extract_fal_logs(payload: dict[str, Any]) -> list[str]:
    logs = payload.get("logs") or []
    items: list[str] = []
    for entry in logs:
        if isinstance(entry, str):
            items.append(entry)
        elif isinstance(entry, dict):
            message = entry.get("message") or entry.get("msg") or entry.get("log")
            if message:
                items.append(str(message))
    return items


def _extract_fal_image_url(payload: dict[str, Any]) -> str:
    candidates: list[Any] = []
    for key in ("images", "output", "result", "data"):
        value = payload.get(key)
        if value is not None:
            candidates.append(value)
    if "url" in payload:
        candidates.append(payload["url"])

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.startswith("http"):
            return candidate
        if isinstance(candidate, dict):
            url = candidate.get("url")
            if isinstance(url, str) and url.startswith("http"):
                return url
            nested = candidate.get("images") or candidate.get("data")
            if isinstance(nested, list):
                candidates.extend(nested)
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, str) and item.startswith("http"):
                    return item
                if isinstance(item, dict):
                    url = item.get("url")
                    if isinstance(url, str) and url.startswith("http"):
                        return url
    raise ImageProviderError("No image URL found in fal response.")


def generate_image_with_fal(
    *,
    prompt: str,
    model_id: str,
    api_key: str,
    references: list[ImageReference] | None = None,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    timeout_seconds: int = 90,
    progress: ProgressCallback | None = None,
) -> GeneratedImage:
    started_at = time.perf_counter()
    width, height = _sized_dimensions(aspect_ratio, image_size)
    body: dict[str, Any] = {
        "prompt": prompt,
        "num_images": 1,
        "image_size": {"width": width, "height": height},
    }
    if references:
        body["prompt"] = f"{prompt}\nPreserve silhouette and motif continuity from the previous draft."

    headers = {"Authorization": f"Key {api_key}"}
    queue_url = f"https://queue.fal.run/{model_id}"
    submit = _json_request(queue_url, headers=headers, payload=body, timeout_seconds=timeout_seconds)
    request_id = submit.get("request_id") or submit.get("requestId")
    if not request_id:
        raise ImageProviderError(f"fal queue submit did not return request_id: {submit}")

    status_url = submit.get("status_url") or submit.get("statusUrl") or f"{queue_url}/requests/{request_id}/status"
    response_url = submit.get("response_url") or submit.get("responseUrl") or f"{queue_url}/requests/{request_id}"
    logs: list[str] = []
    queue_wait_ms = 0
    deadline = started_at + timeout_seconds
    while time.perf_counter() < deadline:
        state = _json_request(status_url, method="GET", headers=headers, timeout_seconds=timeout_seconds)
        status = str(state.get("status") or state.get("state") or "RUNNING").upper()
        logs = _extract_fal_logs(state) or logs
        queue_position = state.get("queue_position") or state.get("queuePosition")
        if progress:
            progress(
                {
                    "provider": "fal",
                    "status": status,
                    "queue_position": queue_position,
                    "logs": logs[-1:] if logs else [],
                }
            )
        if status in {"COMPLETED", "SUCCESS", "OK"}:
            queue_wait_ms = int((time.perf_counter() - started_at) * 1000)
            result_payload = _json_request(response_url, method="GET", headers=headers, timeout_seconds=timeout_seconds)
            image_url = _extract_fal_image_url(result_payload)
            image_bytes, mime_type = _binary_request(image_url, timeout_seconds=timeout_seconds)
            total_ms = int((time.perf_counter() - started_at) * 1000)
            return GeneratedImage(
                provider="fal",
                model_id=model_id,
                mime_type=mime_type or (mimetypes.guess_type(image_url)[0] or "image/png"),
                image_bytes=image_bytes,
                prompt=prompt,
                response_id=request_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                queue_wait_ms=queue_wait_ms,
                inference_ms=max(0, total_ms - queue_wait_ms),
                total_ms=total_ms,
                logs=logs,
                raw_response=result_payload,
            )
        if status in {"FAILED", "ERROR", "CANCELLED"}:
            raise ImageProviderError(f"fal generation failed: request_id={request_id} state={state}")
        time.sleep(0.8)

    raise ImageProviderError(f"fal generation timed out after {timeout_seconds}s: request_id={request_id}")


def generate_image_with_openai(
    *,
    prompt: str,
    model_id: str,
    api_key: str,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    timeout_seconds: int = 90,
) -> GeneratedImage:
    started_at = time.perf_counter()
    width, height = _sized_dimensions(aspect_ratio, image_size)
    body = {
        "model": model_id,
        "prompt": prompt,
        "size": f"{width}x{height}",
        "response_format": "b64_json",
    }
    response = _json_request(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}"},
        payload=body,
        timeout_seconds=timeout_seconds,
    )
    items = response.get("data") or []
    if not items:
        raise ImageProviderError(f"OpenAI response did not include image data: {response}")
    first = items[0]
    mime_type = "image/png"
    if isinstance(first, dict) and first.get("b64_json"):
        image_bytes = base64.b64decode(first["b64_json"])
    elif isinstance(first, dict) and first.get("url"):
        image_bytes, mime_type = _binary_request(first["url"], timeout_seconds=timeout_seconds)
    else:
        raise ImageProviderError(f"OpenAI response did not include a supported image payload: {response}")

    total_ms = int((time.perf_counter() - started_at) * 1000)
    return GeneratedImage(
        provider="openai",
        model_id=model_id,
        mime_type=mime_type,
        image_bytes=image_bytes,
        prompt=prompt,
        response_id=str(response.get("created")) if response.get("created") is not None else None,
        timestamp=datetime.now(timezone.utc).isoformat(),
        queue_wait_ms=0,
        inference_ms=total_ms,
        total_ms=total_ms,
        raw_response=response,
    )


def generate_image_with_gemini(
    *,
    prompt: str,
    model_id: str,
    api_key: str,
    references: list[ImageReference] | None = None,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    timeout_seconds: int = 90,
) -> GeneratedImage:
    started_at = time.perf_counter()
    try:
        result = generate_gemini_image(
            prompt=prompt,
            model_id=model_id,
            api_key=api_key,
            references=[
                GeminiReferenceImage(mime_type=ref.mime_type, image_bytes=ref.image_bytes) for ref in (references or [])
            ],
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            timeout_seconds=timeout_seconds,
        )
    except GeminiImageError as exc:
        raise ImageProviderError(str(exc)) from exc

    total_ms = int((time.perf_counter() - started_at) * 1000)
    return GeneratedImage(
        provider="gemini",
        model_id=result.model_id,
        mime_type=result.mime_type,
        image_bytes=result.image_bytes,
        prompt=result.prompt,
        response_id=result.response_id,
        timestamp=result.timestamp,
        queue_wait_ms=0,
        inference_ms=total_ms,
        total_ms=total_ms,
    )


def generate_image(
    *,
    provider: str,
    prompt: str,
    model_id: str,
    api_key: str,
    references: list[ImageReference] | None = None,
    aspect_ratio: str | None = None,
    image_size: str | None = None,
    timeout_seconds: int = 90,
    progress: ProgressCallback | None = None,
) -> GeneratedImage:
    if provider == "fal":
        return generate_image_with_fal(
            prompt=prompt,
            model_id=model_id,
            api_key=api_key,
            references=references,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            timeout_seconds=timeout_seconds,
            progress=progress,
        )
    if provider == "openai":
        return generate_image_with_openai(
            prompt=prompt,
            model_id=model_id,
            api_key=api_key,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            timeout_seconds=timeout_seconds,
        )
    if provider == "gemini":
        return generate_image_with_gemini(
            prompt=prompt,
            model_id=model_id,
            api_key=api_key,
            references=references,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            timeout_seconds=timeout_seconds,
        )
    raise ImageProviderError(f"Unsupported provider: {provider}")
