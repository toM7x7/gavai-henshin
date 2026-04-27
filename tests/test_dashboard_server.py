import base64
import json
import threading
import tempfile
import unittest
from socketserver import TCPServer, ThreadingMixIn
from pathlib import Path
from urllib.request import Request, urlopen

from henshin.dashboard_server import (
    DashboardHandler,
    GeneratePartsPayload,
    GenerationJob,
    GenerationJobManager,
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

    def test_runtime_info_exposes_quest_dev_url_contract(self) -> None:
        payload = DashboardHandler._runtime_info_for_test(Path(".").resolve(), host="localhost:8010", port=8010)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dashboard_port"], 8010)
        self.assertEqual(payload["quest_dev_port"], 5173)
        self.assertEqual(payload["quest_runtime_scheme"], "http")
        self.assertIn("quest_runtime_origin", payload)
        self.assertIn("/viewer/quest-iw-demo/?newRoute=1", payload["quest_viewer_localhost"])
        self.assertIn("localhost", payload["note"])
        self.assertNotIn("repo_root", payload)
        self.assertNotIn("lan_hosts", payload)

    def test_runtime_info_is_served_over_http(self) -> None:
        root = Path(".").resolve()

        class TestServer(ThreadingMixIn, TCPServer):
            allow_reuse_address = True
            daemon_threads = True

        def factory(*args, **kwargs):
            return DashboardHandler(
                *args,
                directory=str(root),
                root=root,
                jobs=GenerationJobManager(root),
                **kwargs,
            )

        with TestServer(("127.0.0.1", 0), factory) as httpd:
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                port = httpd.server_address[1]
                request = Request(
                    f"http://127.0.0.1:{port}/api/runtime-info",
                    headers={"Host": f"pc.local:{port}"},
                )
                with urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                httpd.shutdown()
                thread.join(timeout=5)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dashboard_host"], f"pc.local:{port}")
        self.assertEqual(payload["dashboard_port"], port)
        self.assertEqual(payload["quest_dev_port"], 5173)
        self.assertIn("/viewer/quest-iw-demo/?newRoute=1", payload["quest_viewer_path"])
        self.assertNotIn("repo_root", payload)

    def test_armor_forge_page_exposes_public_workflow_contract(self) -> None:
        html = Path("viewer/armor-forge/index.html").read_text(encoding="utf-8")
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")
        css = Path("viewer/armor-forge/styles.css").read_text(encoding="utf-8")

        for dom_id in {
            "forgeForm",
            "partGrid",
            "armorCanvas",
            "recallCode",
            "heightCm",
            "heightRange",
            "questLink",
            "questUrl",
            "questUrlHint",
            "assetPipeline",
            "assetPipelineTitle",
            "assetPipelineDetail",
            "textureJobPanel",
            "textureJobButton",
            "textureJobTitle",
            "textureJobDetail",
            "textureJobMeter",
        }:
            self.assertIn(f'id="{dom_id}"', html)
            self.assertIn(f'getElementById("{dom_id}")', js)
        self.assertIn("/v1/suits/forge", js)
        self.assertIn("/api/generation-jobs", js)
        self.assertIn("/api/runtime-info", js)
        self.assertIn("armorStandPoseFor", js)
        self.assertIn("FIT_SHAPE_BASELINES", js)
        self.assertIn("applyApproximateVrmTPose", js)
        self.assertIn("VRM_BONE_ALIAS_INDEX", js)
        self.assertIn("measureVrmMetrics", js)
        self.assertIn("vrmPoseFor", js)
        self.assertIn("vrm_bone_metrics", js)
        self.assertIn("addArmorEdges", js)
        self.assertIn("renderAssetPipeline", js)
        self.assertIn("planned only / surface not generated", html)
        self.assertIn("planned_not_generated", js)
        self.assertIn("fitStatus", js)
        self.assertIn("preview_vrm_bone_metrics", js)
        self.assertIn("nano_banana", js)
        self.assertIn("mesh_uv", js)
        self.assertIn("textureJobPayload", js)
        self.assertIn("startTextureGeneration", js)
        self.assertIn("TextureLoader", js)
        self.assertIn("loadTextureMap", js)
        self.assertIn("texture_path", js)
        self.assertIn("disposeMaterial", js)
        self.assertIn("parts_per_min", js)
        self.assertIn("last_timing_ms", js)
        self.assertIn("generation_job", js)
        self.assertIn("texture_probe_job", js)
        self.assertIn("model_rebuild_job", js)
        self.assertIn("job_payload_template", js)
        self.assertIn("model ${modelStatus}", js)
        self.assertIn("seed/proxy", js)
        self.assertIn("planned", js)
        self.assertIn("color-scheme: light", css)
        self.assertIn("--body-reference", css)
        self.assertIn("--base-suit", css)
        self.assertIn(".preview-legend", css)
        self.assertIn(".texture-job", css)
        self.assertIn("Quest入力コード", html)
        self.assertIn("Quest VR入力ページ", html)
        self.assertIn("表面生成を試す", html)
        self.assertIn("モデル品質Gate前", html)
        self.assertIn("VRM人体", html)
        self.assertIn("基礎スーツ", html)
        self.assertIn("装甲/表面", html)
        self.assertNotIn('id="suitId"', html)
        self.assertNotIn('id="manifestId"', html)

    def test_forge_generation_job_payload_matches_existing_job_api_contract(self) -> None:
        root = Path(".").resolve()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            api = NewRouteApi(root, suit_store_root=Path(tmp) / "suits")
            response = api.post(
                "/v1/suits/forge",
                {"display_name": "Visitor", "parts": ["helmet", "chest", "back"]},
            )
            assert response is not None
            payload = response.body["asset_pipeline"]["texture_probe_job"]["payload"]
            job_payload = GeneratePartsPayload(**payload)

            GenerationJobManager(root)._validate_payload(job_payload)

        self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["writes_final_texture"])
        self.assertTrue(response.body["asset_pipeline"]["model_rebuild_job"]["blocking"])
        self.assertEqual(job_payload.provider_profile, "nano_banana")
        self.assertEqual(job_payload.texture_mode, "mesh_uv")
        self.assertTrue(job_payload.uv_refine)
        self.assertTrue(job_payload.update_suitspec)
        self.assertTrue(job_payload.suitspec.endswith("/suitspec.json"))

    def test_quest_viewer_exposes_vr_recall_input_controls(self) -> None:
        html = Path("viewer/quest-iw-demo/index.html").read_text(encoding="utf-8")
        js = Path("viewer/quest-iw-demo/quest-demo.js").read_text(encoding="utf-8")

        self.assertIn('id="recallCodeInput"', html)
        self.assertIn('inputmode="text"', html)
        self.assertIn('enterkeyhint="go"', html)
        self.assertIn("Quest呼び出し", html)
        for token in {
            "XR_RECALL_CHARS",
            "recallDisplay",
            "submitRecallCodeFromInput",
            "onkeydown",
            "recallDisplayCode",
            "setCodeInputMode",
            "codeMode",
            "コード入力",
            "codeDigit",
            "codeBackspace",
            "codeClear",
            "codeSubmit",
            "appendRecallDigit",
            "VRコード入力 数字4桁",
            "fitText",
            "minFontSize",
            "fontSize: /^[0-9]$/.test(label) ? 76 : 52",
            "height: Math.max(0.086, height * 0.86)",
            "this.codeInputHint.position.set(0, 0.205",
            "&& !this.codeInputMode",
            "右トリガーで再入力",
            "textColor",
            'this.addButton("codeMode", "コード入力", 0.48',
            "this.recallDisplay.position.set(this.codeInputMode ? 0 : -0.39",
            "loadSuitByRecallCode(code, { reloadMeshes: true, pushUrl: true })",
        }:
            self.assertIn(token, js)
        self.assertNotIn('this.normalInputElements.push(this.addButton("codeSubmit"', js)
        self.assertNotIn('this.addButton("codeNext"', js)
        self.assertNotIn('this.addButton("codeInc"', js)
        self.assertNotIn('this.addButton("codeLoad"', js)

    def test_generation_job_snapshot_tracks_progress(self) -> None:
        job = GenerationJob("job-1", GeneratePartsPayload(suitspec="examples/suitspec.sample.json"))
        job.emit({"type": "job_started", "stage": "scan", "status": "started", "requested_count": 2})
        job.emit({
            "type": "part_completed",
            "stage": "core_materialization",
            "part": "helmet",
            "completed_count": 1,
            "timing_ms": {"total_ms": 1234, "inference_ms": 1200},
        })
        job.emit({
            "type": "job_completed",
            "stage": "complete",
            "status": "completed",
            "summary_path": "/x.json",
            "generated_count": 1,
            "cache_hit_count": 0,
        })

        snapshot = job.snapshot()
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["completed_count"], 1)
        self.assertEqual(snapshot["requested_count"], 2)
        self.assertEqual(snapshot["summary_path"], "/x.json")
        self.assertGreaterEqual(snapshot["elapsed_sec"], 0)
        self.assertIn("parts_per_min", snapshot)
        self.assertEqual(snapshot["last_timing_ms"]["total_ms"], 1234)
        self.assertEqual(snapshot["result"]["generated_count"], 1)
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
