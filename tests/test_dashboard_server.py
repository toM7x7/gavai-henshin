import base64
import json
import tempfile
import unittest
from pathlib import Path

from henshin.dashboard_server import (
    DashboardHandler,
    GeneratePartsPayload,
    GenerationJob,
    IWHenshinVoicePayload,
    run_iw_henshin_voice,
)
from henshin.new_route_api import NewRouteApi


class TestDashboardServer(unittest.TestCase):
    def test_new_route_api_paths_are_served_by_dashboard_handler(self) -> None:
        root = Path(".").resolve()
        response = DashboardHandler._new_route_response_for_test(root, "/v1/catalog/parts")
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["catalog_id"], "PCAT-VIEWER-SEED-0001")

    def test_new_route_post_paths_are_served_by_dashboard_handler(self) -> None:
        suitspec = json.loads(Path("examples/suitspec.sample.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            response = DashboardHandler._new_route_post_response_for_test(
                Path(".").resolve(),
                "/v1/suits",
                {"suitspec": suitspec},
                suit_store_root=Path(tmp) / "suits",
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 201)

    def test_new_route_latest_trial_is_served_by_dashboard_handler(self) -> None:
        root = Path(".").resolve()
        suitspec = json.loads(Path("examples/suitspec.sample.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            suit_store_root = Path(tmp) / "suits"
            api = NewRouteApi(root, suit_store_root=suit_store_root)
            api.post("/v1/suits", {"suitspec": suitspec})
            api.post(
                "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
                {"manifest_id": "MNF-20260424-ABCD", "status": "READY"},
            )
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-DASH-0001"})

            response = DashboardHandler._new_route_response_for_test(
                root,
                "/v1/trials/latest",
                suit_store_root=suit_store_root,
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["trial_id"], "S-TRIAL-DASH-0001")

    def test_new_route_quest_recall_is_served_by_dashboard_handler(self) -> None:
        root = Path(".").resolve()
        suitspec = json.loads(Path("examples/suitspec.sample.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            suit_store_root = Path(tmp) / "suits"
            api = NewRouteApi(root, suit_store_root=suit_store_root)
            created = api.post("/v1/suits", {"suitspec": suitspec, "recall_code": "A1B2"})
            api.post(
                "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
                {"manifest_id": "MNF-20260424-ABCD", "status": "READY"},
            )
            assert created is not None

            response = DashboardHandler._new_route_response_for_test(
                root,
                f"/v1/quest/recall/{created.body['recall_code']}",
                suit_store_root=suit_store_root,
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["recall_code"], "A1B2")
        self.assertTrue(response.body["suitspec_ready"])
        self.assertTrue(response.body["manifest_ready"])

    def test_armor_forge_page_exposes_public_workflow_contract(self) -> None:
        html = Path("viewer/armor-forge/index.html").read_text(encoding="utf-8")
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        for dom_id in {
            "forgeForm",
            "partGrid",
            "armorCanvas",
            "recallCode",
            "heightCm",
            "heightRange",
            "questLink",
        }:
            self.assertIn(f'id="{dom_id}"', html)
            self.assertIn(f'getElementById("{dom_id}")', js)
        self.assertIn("/v1/suits/forge", js)
        self.assertIn("Quest入力コード", html)
        self.assertNotIn('id="suitId"', html)
        self.assertNotIn('id="manifestId"', html)

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


if __name__ == "__main__":
    unittest.main()
