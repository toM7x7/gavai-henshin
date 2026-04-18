"""Sakura AI Engine audio integration.

This module keeps the Sakura REST calls isolated from the rest of the
henshin pipeline so API keys and endpoint changes do not leak into the
viewer or generation code.
"""

from __future__ import annotations

import json
import mimetypes
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .gemini_image import _load_dotenv


DEFAULT_BASE_URL = "https://api.ai.sakura.ad.jp/v1"
DEFAULT_WHISPER_MODEL = "whisper-large-v3-turbo"
DEFAULT_TTS_MODEL = "zundamon"
DEFAULT_TTS_VOICE = "normal"
DEFAULT_TTS_FORMAT = "wav"
DEFAULT_TIMEOUT_SECONDS = 90


class SakuraAIEngineError(RuntimeError):
    """Raised when Sakura AI Engine audio calls fail."""


@dataclass(slots=True)
class SakuraAIEngineConfig:
    token: str | None = None
    base_url: str = DEFAULT_BASE_URL
    whisper_model: str = DEFAULT_WHISPER_MODEL
    tts_model: str = DEFAULT_TTS_MODEL
    tts_voice: str = DEFAULT_TTS_VOICE
    tts_format: str = DEFAULT_TTS_FORMAT
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    model: str
    raw: dict[str, Any]


@dataclass(slots=True)
class SpeechResult:
    audio_bytes: bytes
    model: str
    voice: str
    response_format: str
    input_text: str


def _first_env(keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def resolve_sakura_config(
    *,
    token: str | None = None,
    base_url: str | None = None,
    whisper_model: str | None = None,
    tts_model: str | None = None,
    tts_voice: str | None = None,
    tts_format: str | None = None,
    timeout_seconds: int | None = None,
    dotenv_path: str | Path = ".env",
) -> SakuraAIEngineConfig:
    dotenv = _load_dotenv(dotenv_path)

    resolved_token = (
        token
        or _first_env(("SAKURA_AI_ENGINE_TOKEN", "SAKURA_AI_ENGINE_API_KEY"))
        or dotenv.get("SAKURA_AI_ENGINE_TOKEN")
        or dotenv.get("SAKURA_AI_ENGINE_API_KEY")
    )
    resolved_base_url = (
        base_url
        or os.getenv("SAKURA_AI_ENGINE_BASE_URL")
        or dotenv.get("SAKURA_AI_ENGINE_BASE_URL")
        or DEFAULT_BASE_URL
    )
    resolved_whisper_model = (
        whisper_model
        or os.getenv("SAKURA_WHISPER_MODEL")
        or dotenv.get("SAKURA_WHISPER_MODEL")
        or DEFAULT_WHISPER_MODEL
    )
    resolved_tts_model = (
        tts_model
        or os.getenv("SAKURA_TTS_MODEL")
        or dotenv.get("SAKURA_TTS_MODEL")
        or DEFAULT_TTS_MODEL
    )
    resolved_tts_voice = (
        tts_voice
        or os.getenv("SAKURA_TTS_VOICE")
        or dotenv.get("SAKURA_TTS_VOICE")
        or DEFAULT_TTS_VOICE
    )
    resolved_tts_format = (
        tts_format
        or os.getenv("SAKURA_TTS_FORMAT")
        or dotenv.get("SAKURA_TTS_FORMAT")
        or DEFAULT_TTS_FORMAT
    )
    timeout_raw = (
        timeout_seconds
        or os.getenv("SAKURA_AI_ENGINE_TIMEOUT")
        or dotenv.get("SAKURA_AI_ENGINE_TIMEOUT")
        or DEFAULT_TIMEOUT_SECONDS
    )

    return SakuraAIEngineConfig(
        token=resolved_token,
        base_url=resolved_base_url.rstrip("/"),
        whisper_model=resolved_whisper_model,
        tts_model=resolved_tts_model,
        tts_voice=resolved_tts_voice,
        tts_format=resolved_tts_format,
        timeout_seconds=int(timeout_raw),
    )


def _require_token(config: SakuraAIEngineConfig) -> str:
    if not config.token:
        raise SakuraAIEngineError(
            "Sakura AI Engine token is missing. Set SAKURA_AI_ENGINE_TOKEN "
            "or pass --sakura-token."
        )
    return config.token


def _multipart_form_data(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = f"henshin-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    for name, path in files.items():
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("ascii"),
                data,
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), boundary


class SakuraAIEngineClient:
    def __init__(self, config: SakuraAIEngineConfig) -> None:
        self.config = config

    def transcribe_file(self, audio_path: str | Path) -> TranscriptionResult:
        token = _require_token(self.config)
        path = Path(audio_path)
        if not path.is_file():
            raise SakuraAIEngineError(f"Audio file not found: {path}")

        body, boundary = _multipart_form_data(
            fields={"model": self.config.whisper_model},
            files={"file": path},
        )
        request = Request(
            url=f"{self.config.base_url}/audio/transcriptions",
            data=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        parsed = self._json_request(request)
        text = str(parsed.get("text") or "")
        model = str(parsed.get("model") or self.config.whisper_model)
        return TranscriptionResult(text=text, model=model, raw=parsed)

    def synthesize_speech(self, input_text: str) -> SpeechResult:
        token = _require_token(self.config)
        payload = {
            "model": self.config.tts_model,
            "input": input_text,
            "voice": self.config.tts_voice,
            "response_format": self.config.tts_format,
        }
        request = Request(
            url=f"{self.config.base_url}/audio/speech",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": f"audio/{self.config.tts_format}",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        audio_bytes = self._bytes_request(request)
        return SpeechResult(
            audio_bytes=audio_bytes,
            model=self.config.tts_model,
            voice=self.config.tts_voice,
            response_format=self.config.tts_format,
            input_text=input_text,
        )

    def _json_request(self, request: Request) -> dict[str, Any]:
        body = self._bytes_request(request)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SakuraAIEngineError("Sakura AI Engine returned invalid JSON.") from exc

    def _bytes_request(self, request: Request) -> bytes:
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SakuraAIEngineError(f"Sakura AI Engine HTTP error: status={exc.code} body={detail}") from exc
        except URLError as exc:
            raise SakuraAIEngineError(f"Sakura AI Engine connection error: {exc}") from exc


def save_speech(result: SpeechResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result.audio_bytes)
    return path
