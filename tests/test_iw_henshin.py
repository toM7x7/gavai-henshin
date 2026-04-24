import json
import tempfile
import unittest
from pathlib import Path

from henshin.iw_henshin import (
    DEFAULT_EXPLANATION,
    DEFAULT_TRIGGER_PHRASE,
    IWSDKHenshinConfig,
    IWSDKHenshinRequest,
    analyze_generation_trigger,
    detect_generation_trigger,
    normalize_mocopi_frames,
    run_iwsdk_henshin,
)


class TestIWHenshin(unittest.TestCase):
    def test_defaults_are_japanese_and_readable(self) -> None:
        config = IWSDKHenshinConfig()

        self.assertEqual(DEFAULT_TRIGGER_PHRASE, "\u751f\u6210")
        self.assertEqual(config.trigger_phrase, "\u751f\u6210")
        self.assertTrue(DEFAULT_EXPLANATION.startswith("\u751f\u6210\u3068\u306f\u3001"))
        self.assertIn("\u84b8\u7740", DEFAULT_EXPLANATION)
        self.assertEqual(config.explanation_text, DEFAULT_EXPLANATION)

    def test_detect_generation_trigger(self) -> None:
        self.assertTrue(detect_generation_trigger("\u751f\u6210\uff01"))
        self.assertTrue(detect_generation_trigger("\u305b\u3044 \u305b\u3044 \u751f\u6210 \u3057\u307e\u3059"))
        self.assertFalse(detect_generation_trigger("\u5f85\u6a5f\u3057\u307e\u3059"))

    def test_near_miss_generation_trigger(self) -> None:
        for transcript in (
            "\u5148\u751f",
            "\u5148\u751f\u3067\u3059",
            "\u305b\u3044\u305b\u3044",
            "\u305b\u3048\u305b\u3048",
            "\u305b\u30fc\u305b\u30fc",
            "\u305b\u3044\u305c\u3044",
            "\u7cbe\u88fd",
            "\u7cbe\u88fd\u3057\u307e\u3059",
        ):
            with self.subTest(transcript=transcript):
                match = analyze_generation_trigger(transcript)
                self.assertTrue(match["detected"])
                self.assertEqual(match["mode"], "voice_intent")
                self.assertEqual(match["source"], "generation_homophone_lexicon")

        self.assertFalse(detect_generation_trigger("\u5148\u751f\u306b\u76f8\u8ac7\u3057\u307e\u3059"))

    def test_normalize_mocopi_frames_accepts_aliases(self) -> None:
        frames = normalize_mocopi_frames(
            {
                "frames": [
                    {
                        "dt_sec": 0.1,
                        "bones": {
                            "RightShoulder": [0.38, 0.38],
                            "RightLowerArm": [0.33, 0.48],
                            "RightHand": [0.225, 0.625],
                        },
                    }
                ]
            }
        )

        self.assertEqual(len(frames), 1)
        self.assertIn("right_wrist", frames[0].joints_xy01)

    def test_normalize_mocopi_frames_can_disable_demo_fallback(self) -> None:
        self.assertEqual(normalize_mocopi_frames({"frames": [{"bones": {}}]}, fallback=False), [])

    def test_run_iwsdk_henshin_writes_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_iwsdk_henshin(
                IWSDKHenshinRequest(
                    transcript="\u751f\u6210",
                    root=tmp,
                    session_id="S-IWTEST",
                    dry_run=True,
                )
            )

            self.assertTrue(result["ok"])
            self.assertTrue(result["triggered"])
            self.assertTrue(result["equipped"])
            self.assertEqual(result["trigger_match"]["mode"], "exact")
            self.assertEqual(result["final_state"], "ARCHIVED")
            self.assertEqual(result["tts"]["status"], "dry_run")
            self.assertEqual(result["tts"]["text"], DEFAULT_EXPLANATION)

            replay_path = Path(result["replay_path"])
            self.assertTrue(replay_path.exists())
            replay = json.loads(replay_path.read_text(encoding="utf-8"))
            self.assertTrue(replay["deposition"]["completed"])
            self.assertEqual(replay["trigger"]["phrase"], "\u751f\u6210")
            self.assertEqual(replay["trigger"]["match"]["mode"], "exact")

    def test_run_iwsdk_henshin_accepts_near_miss_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_iwsdk_henshin(
                IWSDKHenshinRequest(
                    transcript="\u5148\u751f",
                    root=tmp,
                    session_id="S-IWTEST-NEAR",
                    dry_run=True,
                )
            )

            self.assertTrue(result["ok"])
            self.assertTrue(result["triggered"])
            self.assertEqual(result["trigger_match"]["mode"], "voice_intent")


if __name__ == "__main__":
    unittest.main()
