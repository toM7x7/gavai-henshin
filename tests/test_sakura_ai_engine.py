import tempfile
import unittest
from pathlib import Path

from henshin.sakura_ai_engine import (
    DEFAULT_BASE_URL,
    DEFAULT_TTS_MODEL,
    DEFAULT_WHISPER_MODEL,
    resolve_sakura_config,
)


class TestSakuraAIEngine(unittest.TestCase):
    def test_resolve_sakura_config_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = resolve_sakura_config(dotenv_path=Path(tmp) / ".env")

        self.assertEqual(config.base_url, DEFAULT_BASE_URL)
        self.assertEqual(config.whisper_model, DEFAULT_WHISPER_MODEL)
        self.assertEqual(config.tts_model, DEFAULT_TTS_MODEL)

    def test_resolve_sakura_config_reads_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "SAKURA_AI_ENGINE_TOKEN=test-token",
                        "SAKURA_AI_ENGINE_BASE_URL=https://example.invalid/v1/",
                        "SAKURA_WHISPER_MODEL=whisper-test",
                        "SAKURA_TTS_MODEL=voice-test",
                    ]
                ),
                encoding="utf-8",
            )
            config = resolve_sakura_config(dotenv_path=env_path)

        self.assertEqual(config.token, "test-token")
        self.assertEqual(config.base_url, "https://example.invalid/v1")
        self.assertEqual(config.whisper_model, "whisper-test")
        self.assertEqual(config.tts_model, "voice-test")


if __name__ == "__main__":
    unittest.main()
