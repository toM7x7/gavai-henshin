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

        blueprint_response = DashboardHandler._new_route_response_for_test(root, "/v1/catalog/part-blueprints")
        self.assertIsNotNone(blueprint_response)
        assert blueprint_response is not None
        self.assertEqual(blueprint_response.status, 200)
        self.assertEqual(blueprint_response.body["contract_version"], "modeler-part-blueprint.v1")
        self.assertEqual(blueprint_response.body["part_count"], 18)

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
            "proxyWarning",
            "modelerHandoff",
            "modelerHandoffTitle",
            "modelerHandoffDetail",
            "modelerBlueprintUrl",
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
        self.assertIn("getGLTFLoaderClass", js)
        self.assertIn("loadGlbArmorObject", js)
        self.assertIn("glb_asset", js)
        self.assertIn('"three/addons/": "../body-fit/vendor/three/examples/jsm/"', html)
        self.assertTrue(Path("viewer/body-fit/vendor/three/examples/jsm/loaders/GLTFLoader.js").is_file())
        self.assertTrue(Path("viewer/body-fit/vendor/three/examples/jsm/utils/BufferGeometryUtils.js").is_file())
        self.assertIn("loadTextureMap", js)
        self.assertIn("texture_path", js)
        self.assertIn("createFallbackArmorGeometry", js)
        self.assertIn("createArmorAttachmentShellMesh", js)
        self.assertIn("attachment_preview_shell", js)
        self.assertIn("seed_proxy_fallback", js)
        self.assertIn("previewFallbackParts", js)
        self.assertIn("previewGlbParts", js)
        self.assertIn("delivered_glb_primary", js)
        self.assertIn('previewLayer = "armor_model"', js)
        self.assertIn('previewLayer = "surface_lines"', js)
        self.assertIn('previewLayer = "dimension_guide"', js)
        self.assertIn("previewMockTexturedParts", js)
        self.assertIn("previewTextureFailedParts", js)
        self.assertIn("mockTexturedParts", js)
        self.assertIn("textureLoaded", js)
        self.assertIn("textureFailedParts", js)
        self.assertIn("surfacePlanFromData", js)
        self.assertIn("data?.generation?.surface_plan", js)
        self.assertIn('const TEXTURE_PROVIDER_PROFILE = "nano_banana"', js)
        self.assertIn("provider_profile: TEXTURE_PROVIDER_PROFILE", js)
        self.assertIn("proxy_envelope_only", js)
        self.assertIn("仮プロキシ", html)
        self.assertIn("半透明の箱/筒は発注対象外", html)
        self.assertIn("modelerBlueprintUrl", js)
        self.assertIn("asset_pipeline.modeler_blueprints", html)
        self.assertIn("current_forge_response", js)
        self.assertIn("selected parts", js)
        self.assertIn("modeler-handoff", css)
        self.assertIn("proxy-warning", css)
        self.assertIn("createArmorMockSurfaceTexture", js)
        self.assertIn("textureMockPreview", js)
        self.assertIn("!module?.texture_path && surfacePlan?.contract_version", js)
        self.assertIn("textureLoadFailed", js)
        self.assertIn("baseSuitMaterialKey", js)
        self.assertIn("getBaseSuitMaterial", js)
        self.assertIn("originalMaterials.forEach", js)
        self.assertIn("プレビュー表面", js)
        self.assertIn("仮表面を表示中。", js)
        self.assertIn("納品GLB主表示", js)
        self.assertIn("/v1/catalog/part-blueprints", Path("src/henshin/new_route_api.py").read_text(encoding="utf-8"))
        modeler_brief = Path("docs/modeler-armor-brief.md").read_text(encoding="utf-8")
        self.assertIn("viewer/assets/armor-parts/<module>/", modeler_brief)
        self.assertIn("<module>.glb", modeler_brief)
        self.assertIn("<module>.modeler.json", modeler_brief)
        self.assertIn("GET /v1/catalog/part-blueprints", modeler_brief)
        self.assertIn("Nanobanana", modeler_brief)
        armor_parts_readme = Path("viewer/assets/armor-parts/README.md").read_text(encoding="utf-8")
        self.assertIn("Armor Parts Intake", armor_parts_readme)
        self.assertIn("source/<module>.blend", armor_parts_readme)
        self.assertIn("textures/", armor_parts_readme)
        blueprint_source = Path("src/henshin/modeler_blueprints.py").read_text(encoding="utf-8")
        self.assertIn("modeler-part-blueprint.v1", blueprint_source)
        self.assertIn("authoring_target_m", blueprint_source)
        self.assertIn("source_bbox_role", blueprint_source)
        self.assertIn("PREVIEW_CONTRACT", blueprint_source)
        self.assertIn("proxy_envelope_only", blueprint_source)
        self.assertIn("do_not_model", blueprint_source)
        self.assertIn("texture_provider_profile", blueprint_source)
        self.assertIn("source/<module>.blend", blueprint_source)
        self.assertIn("textures/", blueprint_source)
        self.assertIn("Nanobanana", modeler_brief)
        self.assertIn("source/<module>.blend", modeler_brief)
        self.assertIn("textures/", modeler_brief)
        self.assertIn("base-suit-surface", js)
        self.assertIn("disposeMaterial", js)
        self.assertIn("parts_per_min", js)
        self.assertIn("last_timing_ms", js)
        self.assertIn("textureGenerationSummaryFromSnapshot", js)
        self.assertIn("snapshotWithTextureGenerationSummary", js)
        self.assertIn("texture_generation_summary", js)
        self.assertIn("generated_by_provider_profile", js)
        self.assertIn("fallback_asset_reused", js)
        self.assertIn("final_texture_writeable_count", js)
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
        self.assertIn("不足: ${missing}", js)
        self.assertIn("本番化に必要な外装が不足。", js)
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
            "dataset.previewGlbParts",
            '"base",',
            "VRMの体表テクスチャを特撮ボディスーツとして扱います。",
        }:
            self.assertIn(token, js)
        self.assertRegex(js, r'this\.ghostGroup\.name = "base-suit-[^"]*surface[^"]*"')

        for token in {
            '_FORGE_ASSET_CONTRACT = "vrm-base-suit+modeler-glb-overlay+mesh-v1-fallback"',
            '_FORGE_VISUAL_LAYER_CONTRACT = "base-suit-overlay.v1"',
            '_FORGE_BASE_SURFACE_LAYER_ID = "base_suit_surface"',
            '_FORGE_SURFACE_LAYER_ID = "surface_materials"',
            '_FORGE_SURFACE_PLAN_CONTRACT = "surface-plan.v1"',
            '"kind": "vrm_body_surface"',
            '"role": "body_conforming_substrate"',
            '"surface_target": "VRM humanoid mesh or future body surface shell"',
            '"generation_target": "continuous low-frequency suit material on the human body"',
            '"not_a_part_catalog_entry": True',
            "def _forge_surface_layer(",
            '"surface_layer": self._forge_surface_layer(),',
            'visual_layers.setdefault("surface_layer", self._forge_surface_layer())',
            '"kind": "texture_and_emissive_maps"',
            '"source_layers": [_FORGE_BASE_SURFACE_LAYER_ID, _FORGE_ARMOR_OVERLAY_LAYER_ID]',
            '"contract_version": _FORGE_SURFACE_PLAN_CONTRACT',
            '"style_intent": "bright_tokusatsu_hero"',
            '"texture_role": "hero_body_suit_surface"',
            '"base_suit_surface.present == true"',
        }:
            self.assertIn(token, api)

    def test_armor_forge_limb_pose_uses_3d_segment_frame_static_contract(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        for token in {
            "const FORGE_DISPLAY_ARM_POSE_CHAINS = Object.freeze([",
            '{ bone: "leftUpperArm", childBone: "leftLowerArm", outward: 0.62, down: -0.78, forward: 0.06, strength: 0.96 }',
            '{ bone: "rightUpperArm", childBone: "rightLowerArm", outward: 0.62, down: -0.78, forward: 0.06, strength: 0.96 }',
            "displayPoseCenterWorldX()",
            "displayArmTargetForChain(chain, bonePos)",
            "this.applyForgeDisplayPose();",
            "this.canvas.dataset.previewDisplayPoseChains = String(this.previewStats.displayPoseChains || 0);",
            'this.canvas.dataset.previewDisplayPoseMode = this.previewStats.displayPoseMode || "pending";',
        }:
            self.assertIn(token, js)

        display_pose_block = js[js.index("  rotateBoneChainTowardWorldDir(") : js.index("\n\n  boneLocalPosition")]
        for token in {
            "const deltaWorld = new THREE.Quaternion().setFromUnitVectors(currentDir, targetDir);",
            "const desiredLocalQuat = parentWorldQuat.clone().invert().multiply(desiredWorldQuat).normalize();",
            "bone.quaternion.slerp(desiredLocalQuat, clamp(strength, 0, 1));",
            "for (const chain of FORGE_DISPLAY_ARM_POSE_CHAINS)",
            "const target = this.displayArmTargetForChain(chain, bonePos);",
            "this.previewStats.displayPoseChains = applied;",
            'this.previewStats.displayPoseMode = "center_outward_a_pose";',
        }:
            self.assertIn(token, display_pose_block)

        frame_block = js[
            js.index("function segmentFrameQuaternion") : js.index("\n\nfunction rotationZFromSegment")
        ]
        for token in {
            "const yAxis = end.clone().sub(start);",
            "const zAxis = new THREE.Vector3(0, 0, 1);",
            "zAxis.sub(yAxis.clone().multiplyScalar(zAxis.dot(yAxis)));",
            "const xAxis = new THREE.Vector3().crossVectors(yAxis, zAxis).normalize();",
            "zAxis.crossVectors(xAxis, yAxis).normalize();",
            "matrix.makeBasis(xAxis, yAxis, zAxis);",
            "return new THREE.Quaternion().setFromRotationMatrix(matrix).normalize();",
        }:
            self.assertIn(token, frame_block)

        offset_block = js[js.index("function addOrientedOffset") : js.index("\n\nfunction rotationZFromSegment")]
        for token in {
            "if (!quaternion) return addOffset(vector, offset);",
            ").applyQuaternion(quaternion);",
            "return vector.clone().add(localOffset);",
        }:
            self.assertIn(token, offset_block)

        metrics_block = js[js.index("  measureVrmMetrics() {") : js.index("\n\n  segmentForPart")]
        for token in {
            'leftUpperArm: p("leftUpperArm"),',
            'rightUpperArm: p("rightUpperArm"),',
            'leftLowerArm: p("leftLowerArm"),',
            'rightLowerArm: p("rightLowerArm"),',
            'leftHand: p("leftHand"),',
            'rightHand: p("rightHand"),',
        }:
            self.assertIn(token, metrics_block)

        segment_block = js[js.index("  segmentForPart(part, metrics) {") : js.index("\n\n  targetSizeForPart")]
        for token in {
            'const side = part.startsWith("left_") ? "left" : part.startsWith("right_") ? "right" : "";',
            'const sideKey = (name) => (side ? `${side}${name}` : name);',
            'if (part.endsWith("upperarm")) return [metrics[sideKey("UpperArm")], metrics[sideKey("LowerArm")]];',
            'if (part.endsWith("forearm")) return [metrics[sideKey("LowerArm")], metrics[sideKey("Hand")]];',
            'if (part.endsWith("hand")) return [metrics[sideKey("LowerArm")], metrics[sideKey("Hand")]];',
        }:
            self.assertIn(token, segment_block)

        center_block = js[js.index("  targetCenterForPart(part, module, metrics) {") : js.index("\n\n  vrmPoseFor")]
        for token in {
            "const [segmentStart, segmentEnd] = this.segmentForPart(part, metrics);",
            "const segmentQuat = segmentFrameQuaternion(segmentStart, segmentEnd);",
            "center = addOrientedOffset(center, anchor.offset, segmentQuat);",
        }:
            self.assertIn(token, center_block)

        pose_block = js[js.index("  vrmPoseFor(part, module, mesh) {") : js.index("\n\n  applyPreviewPose")]
        for token in {
            "const [segmentStart, segmentEnd] = this.segmentForPart(part, metrics);",
            "const segmentQuat = segmentFrameQuaternion(segmentStart, segmentEnd);",
            'const anchorQuat = new THREE.Quaternion().setFromEuler(new THREE.Euler(rotation[0], rotation[1], rotation[2], "XYZ"));',
            "const quaternion = segmentQuat ? segmentQuat.clone().multiply(anchorQuat).normalize() : null;",
            "q: quaternion ? quaternion.toArray() : null,",
            'source: "vrm_bone_metrics",',
        }:
            self.assertIn(token, pose_block)

        apply_block = js[js.index("  applyPreviewPose(mesh, part, module) {") : js.index("\n\n  refreshBaseSuitSurface")]
        for token in {
            "if (pose.q) mesh.quaternion.set(...pose.q);",
            "else mesh.rotation.set(...pose.r);",
        }:
            self.assertIn(token, apply_block)

        self.assertNotIn("applyForgeArmPreviewPose();", js)

    def test_armor_forge_arm_parts_keep_minimum_size_floor_static_contract(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        metrics_block = js[js.index("  measureVrmMetrics() {") : js.index("\n\n  segmentForPart")]
        for token in {
            "metrics.shoulderWidth = Math.max(distanceOr(metrics.leftShoulder, metrics.rightShoulder, 0.68), 0.58);",
            "metrics.upperArmLength = Math.max(distanceOr(metrics.leftUpperArm, metrics.leftLowerArm, 0.34), 0.3);",
            "metrics.forearmLength = Math.max(distanceOr(metrics.leftLowerArm, metrics.leftHand, 0.34), 0.3);",
        }:
            self.assertIn(token, metrics_block)

        target_block = js[js.index("  targetSizeForPart(part, module, metrics) {") : js.index("\n\n  targetCenterForPart")]
        for token in {
            "const arm = Math.max(metrics.upperArmLength, 0.24);",
            "const forearm = Math.max(metrics.forearmLength, 0.24);",
            'case "left_upperarm":',
            'case "right_upperarm":',
            "size = new THREE.Vector3(shoulder * 0.16, arm * 0.86, shoulder * 0.16);",
            'case "left_forearm":',
            'case "right_forearm":',
            "size = new THREE.Vector3(shoulder * 0.15, forearm * 0.82, shoulder * 0.15);",
            "return softFitSize(part, module, size);",
        }:
            self.assertIn(token, target_block)

        scale_block = js[js.index("function scaleForTarget") : js.index("\n\nfunction armorStandPoseFor")]
        for axis in ("x", "y", "z"):
            self.assertRegex(
                scale_block,
                rf"clamp\(targetSize\.{axis} / Math\.max\(sourceSize\.{axis}, 0\.001\), 0\.04, 2\.4\)",
            )

    def test_armor_forge_base_suit_surface_and_preview_shells_coexist_static_contract(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")
        api = Path("src/henshin/new_route_api.py").read_text(encoding="utf-8")

        shell_block = js[
            js.index("function createArmorAttachmentShellMesh") : js.index("\n\nasync function createArmorMesh")
        ]
        for token in {
            "const geometry = createFallbackArmorGeometry(part);",
            "mesh.renderOrder = 5;",
            "mesh.userData.armorPart = true;",
            "mesh.userData.attachmentPreviewShell = true;",
            'mesh.userData.meshSource = "attachment_preview_shell";',
            'mesh.userData.previewPriority = "auxiliary_proxy";',
        }:
            self.assertIn(token, shell_block)
        self.assertRegex(shell_block, r"glowDepthTest:\s*true")
        self.assertRegex(shell_block, r"glowRenderOrder:\s*4\.7")
        demote_block = js[
            js.index("function demoteAttachmentPreviewShell") : js.index("\n\nasync function createArmorMesh")
        ]
        for token in {
            'shell.userData.previewPriority = "post_load_hidden_guide";',
            "shell.visible = false;",
            "material.opacity = 0.018;",
            "material.wireframe = true;",
            "object.material.opacity = Math.min(numberOr(object.material.opacity, 0.08), 0.08);",
        }:
            self.assertIn(token, demote_block)

        base_surface_block = js[js.index("  refreshBaseSuitSurface(") : js.index("\n\n  prepareVrmMannequin")]
        for token in {
            "obj.renderOrder = 2;",
            'obj.userData.baseSuitSurface = "vrm_surface_texture";',
        }:
            self.assertIn(token, base_surface_block)

        clear_block = js[js.index("  clearArmor() {") : js.index("\n\n  async renderSuit")]
        self.assertIn("const removable = this.group.children.filter((child) => child.userData?.armorPart);", clear_block)
        self.assertNotIn("baseSuitSurface", clear_block)

        render_block = js[js.index("  async renderSuit(suitspec) {") : js.index("\n\n  resize()")]
        ordered_tokens = [
            "const surfacePlan = surfacePlanFromData(suitspec) || surfacePlanFromData(latestForgeData);",
            "this.refreshBaseSuitSurface(palette);",
            "const shells = records.map(([part, module]) => createArmorAttachmentShellMesh(part, module, palette));",
            "this.group.add(shell);",
            "let meshes = [];",
            "try {",
            "meshes = await mapWithConcurrency(",
            "([part, module]) => createArmorMesh(part, module, palette, surfacePlan),",
            "this.group.add(mesh);",
            "} finally {",
            "shells.forEach((shell) => demoteAttachmentPreviewShell(shell));",
            "this.previewStats.armorParts = meshes.length;",
            "this.publishPreviewStats();",
        ]
        previous = -1
        for token in ordered_tokens:
            current = render_block.index(token, previous + 1)
            self.assertGreater(current, previous)
            previous = current

        for token in {
            '"required_layers": [_FORGE_BASE_SURFACE_LAYER_ID, _FORGE_ARMOR_OVERLAY_LAYER_ID]',
            '"base_suit_surface_required": True',
            '"armor_overlay_required": True',
            '"base_suit_surface.present == true"',
            '"armor_overlay_parts.visible_count >= minimum_visible_overlay_parts"',
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
        self.assertIn("touch-action: none;", canvas_css)

        dragging_css = self._css_block(css, "#armorCanvas.dragging")
        self.assertIn("cursor: grabbing;", dragging_css)

        controls_block = js[js.index("  installPreviewControls() {") : js.index("\n\n  updateSpinToggle")]
        for token in {
            'canvas.classList.add("dragging");',
            "this.autoSpin = false;",
            "this.updateSpinToggle();",
            "this.viewYaw += dx * 0.008;",
            "this.viewPitch = clamp(this.viewPitch + dy * 0.004, -0.34, 0.22);",
            'canvas.classList.remove("dragging");',
            'canvas.addEventListener("pointercancel", stopDrag);',
            "event.preventDefault();",
            "this.zoomBy(event.deltaY > 0 ? 1.08 : 0.92);",
            "{ passive: false }",
        }:
            self.assertIn(token, controls_block)

        for token in {
            'UI.resetViewButton?.addEventListener("click", () => armorStand?.resetView());',
            'UI.zoomOutButton?.addEventListener("click", () => armorStand?.zoomBy(1.1));',
            'UI.zoomInButton?.addEventListener("click", () => armorStand?.zoomBy(0.9));',
            'UI.spinToggle?.addEventListener("click", () => armorStand?.toggleSpin());',
            'UI.spinToggle) UI.spinToggle.setAttribute("aria-pressed", this.autoSpin ? "true" : "false");',
        }:
            self.assertIn(token, js)

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
            "grid-template-rows: minmax(0, 1fr) auto;",
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
        self.assertIn("height: clamp(440px, 64svh, 640px);", mobile_stand_stage)
        mobile_layer_panel = self._css_block(mobile_css, ".preview-layer-panel")
        self.assertIn("position: absolute;", mobile_layer_panel)
        self.assertIn("margin: 0;", mobile_layer_panel)
        self.assertNotIn("position: static;", mobile_layer_panel)

        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")
        self.assertIn("lastCanvasSize", js)
        self.assertIn("this.lastCanvasSize.width === width", js)

    def test_suit_dashboard_generation_profile_is_nano_banana_only(self) -> None:
        html = Path("viewer/suit-dashboard/index.html").read_text(encoding="utf-8")
        js = Path("viewer/suit-dashboard/dashboard.js").read_text(encoding="utf-8")

        self.assertIn('<option value="nano_banana" selected>', html)
        self.assertNotIn('option value="exhibition"', html)
        self.assertIn('provider_profile: "nano_banana"', js)
        self.assertNotIn("provider_profile: UI.providerProfile.value", js)

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
