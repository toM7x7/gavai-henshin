"""Gemini image generation integration (REST, no external dependencies)."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiImageError(RuntimeError):
    """Raised when image generation fails."""


@dataclass(slots=True)
class GeminiImageResult:
    model_id: str
    mime_type: str
    image_bytes: bytes
    prompt: str
    response_id: str | None
    timestamp: str


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
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        values[key] = value
    return values


def resolve_api_key(explicit: str | None = None, dotenv_path: str | Path = ".env") -> str:
    if explicit:
        return explicit
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(key)
        if value:
            return value

    dotenv = _load_dotenv(dotenv_path)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = dotenv.get(key)
        if value:
            return value

    raise GeminiImageError("API key is missing. Set GEMINI_API_KEY or pass --api-key.")


def build_image_request(prompt: str) -> dict[str, Any]:
    return {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
        },
    }


def _extract_image_part(response: dict[str, Any]) -> tuple[bytes, str]:
    candidates = response.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            data = inline.get("data")
            mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            if data:
                return base64.b64decode(data), mime

    texts: list[str] = []
    for candidate in candidates:
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                texts.append(text)
    suffix = f" text={texts[:1]}" if texts else ""
    raise GeminiImageError(f"No image part found in Gemini response.{suffix}")


def generate_image(
    *,
    prompt: str,
    model_id: str,
    api_key: str,
    timeout_seconds: int = 60,
    endpoint_base: str = "https://generativelanguage.googleapis.com/v1beta",
) -> GeminiImageResult:
    url = f"{endpoint_base}/models/{model_id}:generateContent?key={api_key}"
    payload = build_image_request(prompt=prompt)
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GeminiImageError(f"Gemini HTTP error: status={exc.code} body={detail}") from exc
    except URLError as exc:
        raise GeminiImageError(f"Gemini connection error: {exc}") from exc

    parsed = json.loads(body)
    image_bytes, mime_type = _extract_image_part(parsed)

    return GeminiImageResult(
        model_id=model_id,
        mime_type=mime_type,
        image_bytes=image_bytes,
        prompt=prompt,
        response_id=parsed.get("responseId") or parsed.get("response_id"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def extension_for_mime(mime_type: str) -> str:
    if mime_type == "image/png":
        return ".png"
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".bin"


def save_image(result: GeminiImageResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result.image_bytes)
    return path


def write_generation_meta(path: str | Path, result: GeminiImageResult, kind: str) -> Path:
    payload = {
        "kind": kind,
        "model_id": result.model_id,
        "mime_type": result.mime_type,
        "prompt": result.prompt,
        "response_id": result.response_id,
        "generated_at": result.timestamp,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p
