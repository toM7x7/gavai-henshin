import base64
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from henshin.gemini_image import GeminiImageError, generate_image, resolve_api_key


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestGeminiImage(unittest.TestCase):
    def test_resolve_api_key_from_env(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "abc"}, clear=True):
            self.assertEqual(resolve_api_key(None), "abc")

    def test_resolve_api_key_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GeminiImageError):
                resolve_api_key(None, dotenv_path="tests/.env.none")

    def test_resolve_api_key_from_dotenv(self) -> None:
        env_path = Path("tests/.env.test")
        try:
            env_path.write_text("GEMINI_API_KEY=from_dotenv\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(resolve_api_key(None, dotenv_path=env_path), "from_dotenv")
        finally:
            if env_path.exists():
                env_path.unlink()

    def test_generate_image_success(self) -> None:
        raw = b"fakepngbytes"
        encoded = base64.b64encode(raw).decode("ascii")
        payload = {
            "responseId": "resp-1",
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": encoded,
                                }
                            }
                        ]
                    }
                }
            ],
        }

        with patch("henshin.gemini_image.urlopen", return_value=_FakeHttpResponse(payload)):
            result = generate_image(prompt="x", model_id="gemini-3-pro-image-preview", api_key="k")
        self.assertEqual(result.mime_type, "image/png")
        self.assertEqual(result.image_bytes, raw)
        self.assertEqual(result.response_id, "resp-1")


if __name__ == "__main__":
    unittest.main()
