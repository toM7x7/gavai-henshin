import base64
import tempfile
import unittest
from pathlib import Path

from henshin.dashboard_server import (
    GeneratePartsPayload,
    GenerationJob,
    IWHenshinVoicePayload,
    run_iw_henshin_voice,
)
from henshin.mocopi_live import LiveMocopiStore


class TestDashboardServer(unittest.TestCase):
    def test_generation_job_snapshot_tracks_progress(self) -> None:
        job = GenerationJob("job-1", GeneratePartsPayload(suitspec="examples/suitspec.sample.json"))
        job.emit({"type": "job_started", "stage": "scan", "status": "started", "requested_count": 2})
        job.emit({"type": "part_completed", "stage": "core_materialization", "part": "helmet", "completed_count": 1})
        job.emit({"type": "job_completed", "stage": "complete", "status": "completed", "summary_path": "/x.json"})

        snapshot = job.snapshot()
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["completed_count"], 1)
        self.assertEqual(snapshot["requested_count"], 2)
        self.assertEqual(snapshot["summary_path"], "/x.json")
        self.assertEqual(snapshot["events"], 3)

    def test_payload_accepts_emotion_profile(self) -> None:
        payload = GeneratePartsPayload(
            suitspec="examples/suitspec.sample.json",
            emotion_profile={"drive": "protect", "scene": "urban_night", "protect_target": "city"},
        )
        self.assertEqual(payload.emotion_profile["drive"], "protect")

    def test_payload_accepts_operator_profile_override(self) -> None:
        payload = GeneratePartsPayload(
            suitspec="examples/suitspec.sample.json",
            operator_profile_override={"protect_archetype": "future", "color_mood": "clear_white"},
        )
        self.assertEqual(payload.operator_profile_override["protect_archetype"], "future")

    def test_iw_voice_payload_dry_run_generates_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = IWHenshinVoicePayload(
                audio_base64=base64.b64encode(b"dry-run").decode("ascii"),
                mime_type="audio/wav",
                audio_stats={"mode": "wav", "sample_rate": 48000, "duration_sec": 4.5, "peak": 0.25, "rms": 0.04},
                session_id="S-IW-QUEST-TEST",
                mocopi=None,
                trigger_phrase="\u751f\u6210",
                dry_run=True,
            )
            result = run_iw_henshin_voice(root, payload)

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["session_id"], "S-IW-QUEST-TEST")
        self.assertEqual(result["replay_url"], "/sessions/S-IW-QUEST-TEST/artifacts/iwsdk-deposition-replay.json")
        self.assertEqual(result["body_sim_url"], "/sessions/S-IW-QUEST-TEST/body-sim.json")
        self.assertEqual(result["voice_audio_url"], "/sessions/S-IW-QUEST-TEST/artifacts/voice-command.wav")
        self.assertEqual(result["voice_audio"]["stats"]["mode"], "wav")
        self.assertEqual(result["voice_audio"]["stats"]["bytes"], len(b"dry-run"))
        self.assertEqual(result["result"]["voice_audio"]["mime_type"], "audio/wav")

    def test_iw_voice_payload_can_use_live_mocopi_buffer(self) -> None:
        live = LiveMocopiStore()
        live.push_payload(
            {
                "frames": [
                    {
                        "dt_sec": 0.1,
                        "bones": {
                            "LeftShoulder": [0.62, 0.38],
                            "RightShoulder": [0.38, 0.38],
                            "LeftHip": [0.57, 0.58],
                            "RightHip": [0.43, 0.58],
                            "RightHand": [0.225, 0.625],
                        },
                    }
                    for _ in range(8)
                ]
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = IWHenshinVoicePayload(
                audio_base64=base64.b64encode(b"dry-run").decode("ascii"),
                mime_type="audio/wav",
                session_id="S-IW-QUEST-LIVE",
                mocopi=None,
                mocopi_live=True,
                trigger_phrase="\u751f\u6210",
                dry_run=True,
            )
            result = run_iw_henshin_voice(root, payload, mocopi_live=live)

        self.assertTrue(result["ok"])
        self.assertTrue(result["mocopi_live"]["connected"])
        self.assertTrue(result["mocopi_live"]["axis"]["locked"])
        self.assertEqual(result["replay"]["tracking"]["frame_count"], 8)

    def test_mocopi_live_status_includes_bridge_diagnostics(self) -> None:
        live = LiveMocopiStore()
        live.bridge.update(
            {
                "event": "unsupported",
                "listening": "0.0.0.0:12351",
                "received": 3,
                "forwarded_frames": 0,
                "unsupported": 3,
                "last_source": "192.168.1.12:50000",
                "last_error": "Unsupported mocopi packet.",
                "packet_seen": True,
            }
        )

        status = live.status()

        self.assertIn("bridge", status)
        self.assertEqual(status["bridge"]["received"], 3)
        self.assertEqual(status["bridge"]["unsupported"], 3)
        self.assertTrue(status["bridge"]["receiving"])
        self.assertEqual(status["bridge"]["last_source"], "192.168.1.12:50000")


if __name__ == "__main__":
    unittest.main()
