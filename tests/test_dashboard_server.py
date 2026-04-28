import base64
import json
import re
import threading
import tempfile
import unittest
from socketserver import TCPServer, ThreadingMixIn
from pathlib import Path
from unittest.mock import patch
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
        self.assertIn("createFallbackArmorGeometry", js)
        self.assertIn("createArmorAttachmentShellMesh", js)
        self.assertIn("attachment_preview_shell", js)
        self.assertIn("seed_proxy_fallback", js)
        self.assertIn("previewFallbackParts", js)
        self.assertIn("base-suit-surface", js)
        self.assertIn("disposeMaterial", js)
        self.assertIn("parts_per_min", js)
        self.assertIn("last_timing_ms", js)
        self.assertIn("generation_job", js)
        self.assertIn("texture_probe_job", js)
        self.assertIn("model_rebuild_job", js)
        self.assertIn("model_quality_gate", js)
        self.assertIn("modelGateStateForPipeline", js)
        self.assertIn("job_payload_template", js)
        self.assertIn("model ${modelStatus}", js)
        self.assertIn("seed/proxy", js)
        self.assertIn("planned", js)
        self.assertIn('title: "部分生成"', js)
        self.assertIn("本番スーツ化には ${missing} が必要です。現在は部分プレビューです。", js)
        self.assertIn("本番スーツ化に必要な外装パーツ数が足りません。現在は部分プレビューです。", js)
        self.assertIn("color-scheme: light", css)
        self.assertIn("--body-reference", css)
        self.assertIn("--base-suit", css)
        self.assertIn(".preview-legend", css)
        self.assertIn(".texture-job", css)
        self.assertIn("Quest入力コード", html)
        self.assertIn("Quest VR入力ページ", html)
        self.assertIn("表面生成", html)
        self.assertIn("本番表面生成", js)
        self.assertIn("モデル品質Gate通過後", html)
        self.assertIn("モデル品質Gate前", js)
        self.assertIn("VRM骨格", html)
        self.assertIn("VRM表面ボディスーツ", html)
        self.assertIn("外装パーツ", html)
        self.assertNotIn('id="suitId"', html)
        self.assertNotIn('id="manifestId"', html)

    def test_armor_forge_base_suit_is_vrm_surface_layer_static_contract(self) -> None:
        html = Path("viewer/armor-forge/index.html").read_text(encoding="utf-8")
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")
        api = Path("src/henshin/new_route_api.py").read_text(encoding="utf-8")

        for token in {
            "VRM骨格",
            "VRM表面ボディスーツ",
            "基礎スーツ",
            "外装パーツ",
            "VRM基礎スーツと外装パーツの3Dプレビュー",
            "VRM表面の基礎スーツに外装パーツを重ねて表示",
        }:
            self.assertIn(token, html)

        for token in {
            "const BASE_SUIT_COLOR",
            "const BASE_SUIT_EMISSIVE",
            "createBaseSuitTexture",
            "createBaseSuitMaterial",
            "vrm-body-suit-surface-texture",
            "vrm-body-suit-surface-material",
            "base-suit-surface-torso",
            "base-suit-surface-head",
            "base-suit-surface-limb",
            'userData.baseSuitSurface = "vrm_surface_texture"',
            "refreshBaseSuitSurface",
            "baseSuitVisible",
            "dataset.previewBaseSuit",
            '"base",',
            "VRMの体表テクスチャを特撮ボディスーツとして扱います。",
        }:
            self.assertIn(token, js)
        self.assertRegex(js, r'this\.ghostGroup\.name = "base-suit-[^"]*surface[^"]*"')

        for token in {
            '_FORGE_ASSET_CONTRACT = "vrm-base-suit+mesh-v1-overlay"',
            '_FORGE_VISUAL_LAYER_CONTRACT = "base-suit-overlay.v1"',
            '_FORGE_BASE_SURFACE_LAYER_ID = "base_suit_surface"',
            '"kind": "vrm_body_surface"',
            '"role": "body_conforming_substrate"',
            '"surface_target": "VRM humanoid mesh or future body surface shell"',
            '"generation_target": "continuous low-frequency suit material on the human body"',
            '"not_a_part_catalog_entry": True',
            '"base_suit_surface.present == true"',
        }:
            self.assertIn(token, api)

    def test_armor_forge_canvas_exposes_direct_manipulation_static_contract(self) -> None:
        html = Path("viewer/armor-forge/index.html").read_text(encoding="utf-8")
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")
        css = Path("viewer/armor-forge/styles.css").read_text(encoding="utf-8")

        canvas_match = re.search(r'<canvas[^>]+id="armorCanvas"[^>]+aria-label="(?P<label>[^"]+)"', html)
        self.assertIsNotNone(canvas_match)
        assert canvas_match is not None
        self.assertIn("3Dプレビュー", canvas_match.group("label"))

        for dom_id in {"standControls", "resetViewButton", "zoomOutButton", "zoomInButton", "spinToggle"}:
            self.assertIn(f'id="{dom_id}"', html)
            self.assertIn(f'getElementById("{dom_id}")', js)
        for token in {
            'aria-label="鎧プレビュー操作"',
            'aria-label="正面へ戻す"',
            'aria-label="縮小"',
            'aria-label="拡大"',
            'aria-label="自動回転を切り替え"',
        }:
            self.assertIn(token, html)

        interaction_contracts = [
            ("OrbitControls", ("OrbitControls", "new OrbitControls(", ".controls.update(")),
            ("pointer drag rotation", ("pointerdown", "pointermove", "pointerup", "setPointerCapture")),
            ("mouse drag rotation", ("mousedown", "mousemove", "mouseup")),
        ]
        self.assertTrue(
            any(all(token in js for token in tokens) for _, tokens in interaction_contracts),
            "Armor Forge canvas must expose an orbit/drag interaction contract for rotating the armor preview.",
        )

        canvas_css = self._css_block(css, "#armorCanvas")
        self.assertTrue(
            "cursor: grab;" in canvas_css or "cursor: move;" in canvas_css or "canvas.style.cursor" in js,
            "Interactive armor preview should advertise draggable affordance on the canvas.",
        )

    def test_forge_partial_selection_cannot_be_final_complete_static_contract(self) -> None:
        api = Path("src/henshin/new_route_api.py").read_text(encoding="utf-8")
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        required_match = re.search(r"_FORGE_REQUIRED_PARTS\s*=\s*\{(?P<body>[^}]+)\}", api)
        self.assertIsNotNone(required_match)
        assert required_match is not None
        required_body = required_match.group("body")
        for part in {"helmet", "chest", "back"}:
            self.assertIn(f'"{part}"', required_body)

        for token in {
            '"vrm_only_is_valid": False',
            '"failure_mode_prevented": "vrm_only_render_after_generation"',
            '"minimum_visible_overlay_parts": len(required_parts)',
            '"missing_required_overlay_parts": missing_required',
            "selection_complete = not missing_required and overlay_count >= minimum_count",
            'gate["selection_complete_for_final_texture"] = selection_complete',
            'gate["texture_lock_allowed"] = mesh_texture_lock_allowed and selection_complete',
            'gate["status"] = "fail"',
            'job_payload_template["writes_final_texture"] = texture_lock_allowed',
            '"final_texture_ready": False',
        }:
            self.assertIn(token, api)

        partial_branch = js[
            js.index("if (gate.selection_complete_for_final_texture === false)") : js.index('if (status === "pass")')
        ]
        self.assertIn('state: "planned"', partial_branch)
        self.assertIn("gate.missing_required_overlay_parts", partial_branch)
        self.assertNotIn('state: "ready"', partial_branch)

    def test_armor_forge_layout_css_keeps_stand_panel_bounded(self) -> None:
        css = Path("viewer/armor-forge/styles.css").read_text(encoding="utf-8")

        app_shell = self._css_block(css, ".app-shell")
        self.assertIn("display: grid;", app_shell)
        self.assertIn("align-items: start;", app_shell)

        stand_panel = self._css_block_containing(css, ".stand-panel", "position: sticky;")
        for token in {
            "position: sticky;",
            "top: 0;",
            "height: 100vh;",
            "grid-template-rows: minmax(360px, 1fr) auto;",
            "overflow: hidden;",
        }:
            self.assertIn(token, stand_panel)

        stand_stage = self._css_block(css, ".stand-stage")
        self.assertIn("min-height: 0;", stand_stage)
        self.assertIn("overflow: hidden;", stand_stage)

        mobile_css = css[css.index("@media (max-width: 1080px)") :]
        mobile_stand_panel = self._css_block(mobile_css, ".stand-panel")
        for token in {
            "position: relative;",
            "height: auto;",
            "overflow: visible;",
        }:
            self.assertIn(token, mobile_stand_panel)
        mobile_stand_stage = self._css_block(mobile_css, ".stand-stage")
        self.assertIn("height: clamp(420px, 62vh, 620px);", mobile_stand_stage)
        mobile_layer_panel = self._css_block(mobile_css, ".preview-layer-panel")
        self.assertIn("position: absolute;", mobile_layer_panel)
        self.assertIn("margin: 0;", mobile_layer_panel)
        self.assertNotIn("position: static;", mobile_layer_panel)

        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")
        self.assertIn("lastCanvasSize", js)
        self.assertIn("this.lastCanvasSize.width === width", js)

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
            self.assertNotIn("must_render_layers", payload)
            self.assertNotIn("minimum_visible_overlay_parts", payload)
            job_payload = GeneratePartsPayload(**payload)

            GenerationJobManager(root)._validate_payload(job_payload)

        self.assertTrue(response.body["asset_pipeline"]["texture_probe_job"]["writes_final_texture"])
        self.assertTrue(response.body["asset_pipeline"]["texture_probe_job"]["final_texture_lock_allowed"])
        self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["blocked_by_model_quality"])
        self.assertTrue(response.body["asset_pipeline"]["model_rebuild_job"]["blocking"])
        self.assertEqual(job_payload.provider_profile, "nano_banana")
        self.assertEqual(job_payload.texture_mode, "mesh_uv")
        self.assertTrue(job_payload.uv_refine)
        self.assertTrue(job_payload.update_suitspec)
        self.assertTrue(job_payload.writes_final_texture)
        self.assertTrue(job_payload.suitspec.endswith("/suitspec.json"))

    def test_forge_generation_job_payload_keeps_helmet_only_selection(self) -> None:
        root = Path(".").resolve()
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            with patch(
                "henshin.new_route_api.audit_viewer_mesh_assets",
                side_effect=self._selected_p0_gate,
            ) as mesh_audit:
                response = DashboardHandler._new_route_post_response_for_test(
                    root,
                    "/v1/suits/forge",
                    {"display_name": "Visitor", "parts": ["helmet"]},
                    suit_store_root=Path(tmp) / "suits",
                )
            assert response is not None
            self.assertEqual(response.status, 201, response.body)
            payload = response.body["asset_pipeline"]["texture_probe_job"]["payload"]
            job_payload = GeneratePartsPayload(**payload)

            GenerationJobManager(root)._validate_payload(job_payload)

        self.assertEqual(mesh_audit.call_args.kwargs.get("required_parts"), ["helmet"])
        self.assertEqual(response.body["visual_layers"]["armor_overlay"]["selected_parts"], ["helmet"])
        self.assertEqual(response.body["visual_layers"]["armor_overlay"]["part_count"], 1)
        self.assertEqual(response.body["render_contract"]["required_overlay_parts"], ["back", "chest", "helmet"])
        self.assertEqual(response.body["render_contract"]["minimum_visible_overlay_parts"], 3)
        self.assertEqual(response.body["render_contract"]["missing_required_overlay_parts"], ["back", "chest"])
        self.assertEqual(response.body["model_quality_gate"]["required_parts"], ["helmet"])
        self.assertEqual(response.body["model_quality_gate"]["mesh_quality_status"], "pass")
        self.assertEqual(response.body["model_quality_gate"]["status"], "fail")
        self.assertFalse(response.body["model_quality_gate"]["selection_complete_for_final_texture"])
        self.assertFalse(response.body["readiness"]["final_texture_ready"])
        self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["final_texture_lock_allowed"])
        self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["writes_final_texture"])
        self.assertEqual(payload["parts"], ["helmet"])
        self.assertFalse(job_payload.writes_final_texture)

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
            "BASE_SUIT_SURFACE_PARTS",
            "createBaseSuitTexture",
            "createBaseSuitMaterial",
            "this.baseSuitGroup = new THREE.Group();",
            "this.refreshBaseSuitSurface();",
            "updateBaseSuitVisibility({ standbyPreview, selfView, reveal })",
            "this.updateBaseSuitVisibility({ standbyPreview, selfView, reveal });",
            "SELF_VIEW_STANDBY_HIDDEN_PARTS",
            "mesh.material.opacity = standbyPreview ? 0.82",
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

    def _selected_p0_gate(self, *, required_parts: list[str] | None = None, **_: object) -> dict:
        required = list(required_parts or ["helmet", "chest", "back", "left_shoulder", "right_shoulder"])
        status = "pass" if required == ["helmet"] else "fail"
        return {
            "contract_version": "model-quality-gate.v1",
            "schema_version": "model-quality-gate.v1",
            "blocking_gate": "mesh_fit_before_texture_final",
            "gate": "mesh.v1.p0",
            "status": status,
            "ok": status == "pass",
            "mesh_assets_ready": status == "pass",
            "texture_lock_allowed": status == "pass",
            "mesh_dir": "viewer/assets/meshes",
            "bounds_contract_version": "mesh-bounds.v1",
            "p0_parts": required,
            "required_parts": required,
            "present_parts": ["helmet"] if "helmet" in required else [],
            "missing_required_parts": [] if status == "pass" else [part for part in required if part != "helmet"],
            "reasons": ["selected P0 quality gate passed"] if status == "pass" else ["unselected global P0 was requested"],
            "summary": {"required_count": len(required)},
            "parts": {
                part: {
                    "part": part,
                    "path": f"viewer/assets/meshes/{part}.mesh.json",
                    "status": "pass" if part == "helmet" else "fail",
                    "ok": part == "helmet",
                    "required": True,
                    "reasons": [f"{part}: selected P0 test gate"],
                    "metrics": {},
                }
                for part in required
            },
        }

    def _css_block(self, css: str, selector: str) -> str:
        block = self._css_block_containing(css, selector, "")
        self.assertTrue(block, f"{selector} block should exist")
        return block

    def _css_block_containing(self, css: str, selector: str, token: str) -> str:
        pattern = rf"(^|\n)\s*{re.escape(selector)}\s*\{{(?P<body>.*?)\n\s*\}}"
        for match in re.finditer(pattern, css, re.DOTALL):
            body = match.group("body")
            if token in body:
                return body
        self.fail(f"{selector} block containing {token!r} should exist")


if __name__ == "__main__":
    unittest.main()
