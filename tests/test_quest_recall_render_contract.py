import json
import re
import struct
import tempfile
import unittest
from pathlib import Path

from henshin.new_route_api import NewRouteApi


RECALL_CODE_0076 = "0076"
FORGE_PARTS = ["helmet", "chest", "back", "waist", "left_forearm", "right_forearm"]
REQUIRED_MODULE_KEYS = {"asset_ref", "fit", "vrm_anchor", "attachment_slot"}
REQUIRED_FIT_KEYS = {"source", "attach", "scale", "minScale"}
REQUIRED_RENDER_PLACEMENT_KEYS = {
    "asset_ref",
    "attachment_slot",
    "body_anchor",
    "body_fit_slot_id",
    "coordinate_space",
    "offset_m",
    "part",
    "quest_coordinate_space",
    "quest_rig_offset_m",
    "rotation_deg",
    "scale_policy",
    "selected_variant_key",
    "target_size_array_m",
    "target_size_m",
}


class TestQuestRecallRenderContract(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(".").resolve()

    def test_web_forge_keeps_renderable_module_contract_after_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(self.repo_root, suit_store_root=Path(tmp) / "suits")
            response = api.post(
                "/v1/suits/forge",
                {
                    "display_name": "0076 regression guard",
                    "recall_code": RECALL_CODE_0076,
                    "parts": FORGE_PARTS,
                },
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["recall_code"], RECALL_CODE_0076)

            preview_modules = response.body["preview"]["modules"]
            self.assertGreaterEqual(len(preview_modules), 18)
            for part, module in preview_modules.items():
                with self.subTest(part=part):
                    self._assert_renderable_module(part, module)

            quest = api.get(f"/v1/quest/recall/{RECALL_CODE_0076}")
            self.assertIsNotNone(quest)
            assert quest is not None
            self.assertEqual(quest.status, 200)
            saved_modules = quest.body["suitspec"]["modules"]
            self.assertEqual(set(saved_modules), set(preview_modules))
            for part, module in saved_modules.items():
                with self.subTest(saved_part=part):
                    self._assert_renderable_module(part, module)

    def test_quest_recall_contains_enough_data_to_draw_armor_over_vrm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(self.repo_root, suit_store_root=Path(tmp) / "suits")
            forged = api.post(
                "/v1/suits/forge",
                {
                    "display_name": "0076 render recall",
                    "recall_code": RECALL_CODE_0076,
                    "parts": FORGE_PARTS,
                    "height_cm": 176,
                },
            )
            self.assertIsNotNone(forged)

            recall = api.get(f"/v1/quest/recall/{RECALL_CODE_0076}")

            self.assertIsNotNone(recall)
            assert recall is not None
            self.assertEqual(recall.status, 200)
            self.assertTrue(recall.body["suitspec_ready"])
            self.assertTrue(recall.body["manifest_ready"])
            self.assertEqual(recall.body["recall_code"], RECALL_CODE_0076)
            self.assertEqual(recall.body["suitspec"]["body_profile"]["height_cm"], 176.0)
            self.assertEqual(
                recall.body["suitspec"]["body_profile"]["vrm_baseline_ref"],
                "viewer/assets/vrm/default.vrm",
            )
            self.assertEqual(recall.body["suitspec"]["texture_fallback"]["mode"], "palette_material")

            modules = recall.body["suitspec"]["modules"]
            manifest_parts = recall.body["manifest"]["parts"]
            enabled = {part for part, module in modules.items() if module.get("enabled") is True}
            self.assertEqual(enabled, set(FORGE_PARTS))
            self.assertEqual(
                {part for part, module in manifest_parts.items() if module.get("enabled") is True},
                enabled,
            )

            for part in sorted(enabled):
                with self.subTest(enabled_part=part):
                    module = modules[part]
                    manifest_part = manifest_parts[part]
                    self._assert_renderable_module(part, module)
                    self.assertEqual(manifest_part["asset_ref"], module["asset_ref"])
                    self.assertEqual(manifest_part["fit"], module["fit"])
                    self.assertIn("catalog_part_id", manifest_part)
                    self._assert_mesh_asset_can_load(module["asset_ref"])

            runtime_package = recall.body["runtime_package"]
            runtime_assets = runtime_package["visual_layers"]["armor_overlay"]["assets"]
            render_placements = runtime_package["render_placements"]
            self.assertEqual(set(render_placements), enabled)
            self.assertEqual(runtime_package["render_contract"]["render_placement_contract"], "runtime-render-placement.v1")
            self.assertEqual(set(runtime_package["render_contract"]["render_placement_parts"]), enabled)
            for part in sorted(enabled):
                with self.subTest(render_placement=part):
                    placement = render_placements[part]
                    self.assertLessEqual(REQUIRED_RENDER_PLACEMENT_KEYS, set(placement))
                    self.assertEqual(placement["part"], part)
                    self.assertEqual(placement["asset_ref"], modules[part]["asset_ref"])
                    self.assertEqual(
                        placement["selected_variant_key"],
                        runtime_assets[part]["selected_variant_key"],
                    )
                    self.assertEqual(placement["coordinate_space"], "vrm_humanoid_local_y_up_z_front")
                    self.assertEqual(placement["quest_coordinate_space"], "quest_rig_local_y_up_z_back")
                    self.assertEqual(len(placement["offset_m"]), 3)
                    self.assertEqual(len(placement["quest_rig_offset_m"]), 3)
                    self.assertEqual(placement["quest_rig_offset_m"][0], placement["offset_m"][0])
                    self.assertEqual(placement["quest_rig_offset_m"][1], placement["offset_m"][1])
                    self.assertEqual(placement["quest_rig_offset_m"][2], -placement["offset_m"][2])
                    self.assertEqual(len(placement["target_size_array_m"]), 3)
                    self.assertTrue(all(value > 0 for value in placement["target_size_array_m"]))

    def test_quest_recall_projects_suitspec_texture_paths_into_runtime_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            suit_store_root = Path(tmp) / "suits"
            api = NewRouteApi(self.repo_root, suit_store_root=suit_store_root)
            forged = api.post(
                "/v1/suits/forge",
                {
                    "display_name": "0076 texture projection",
                    "recall_code": RECALL_CODE_0076,
                    "parts": FORGE_PARTS,
                },
            )
            self.assertIsNotNone(forged)

            first_recall = api.get(f"/v1/quest/recall/{RECALL_CODE_0076}")
            self.assertIsNotNone(first_recall)
            assert first_recall is not None
            suit_id = first_recall.body["suit_id"]
            manifest_id = first_recall.body["manifest_id"]
            suitspec_path = suit_store_root / suit_id / "suitspec.json"
            manifest_path = suit_store_root / suit_id / "manifests" / f"{manifest_id}.json"
            texture_path = "sessions/S-FORGE-0076/artifacts/parts/helmet.generated.png"

            stored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertNotIn("texture_path", stored_manifest["parts"]["helmet"])
            suitspec = json.loads(suitspec_path.read_text(encoding="utf-8"))
            suitspec["modules"]["helmet"]["texture_path"] = texture_path
            suitspec_path.write_text(json.dumps(suitspec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            recalled = api.get(f"/v1/quest/recall/{RECALL_CODE_0076}")

            self.assertIsNotNone(recalled)
            assert recalled is not None
            self.assertEqual(recalled.status, 200)
            self.assertEqual(recalled.body["suitspec"]["modules"]["helmet"]["texture_path"], texture_path)
            self.assertEqual(recalled.body["manifest"]["parts"]["helmet"]["texture_path"], texture_path)
            self.assertEqual(
                recalled.body["runtime_package"]["manifest"]["parts"]["helmet"]["texture_path"],
                texture_path,
            )
            self.assertTrue(recalled.body["runtime_package"]["runtime_checks"]["can_render_runtime_suit"])
            self.assertEqual(
                recalled.body["manifest"]["parts"]["helmet"]["asset_ref"],
                recalled.body["suitspec"]["modules"]["helmet"]["asset_ref"],
            )

    def test_quest_viewer_static_smoke_keeps_recall_input_and_glb_fallback(self) -> None:
        html = (self.repo_root / "viewer" / "quest-iw-demo" / "index.html").read_text(encoding="utf-8")
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")

        for token in {
            'id="recallCodeInput"',
            'inputmode="text"',
            'maxlength="4"',
            'enterkeyhint="go"',
            'aria-describedby="recallCodeState"',
            'id="btnLoadRecallCode"',
            'id="recallCodeState"',
        }:
            self.assertIn(token, html)

        for token in {
            'const XR_RECALL_CHARS = "0123456789";',
            'return String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);',
            "if (draft.length >= 4) break;",
            'if (draft.length !== 4 || draft.includes("-")) return "";',
            "UI.recallCodeInput.onkeydown = (event) =>",
            'if (event.key !== "Enter") return;',
            "UI.btnLoadRecallCode.onclick = () =>",
            "await this.loadSuitByRecallCode(code, { reloadMeshes: true, pushUrl: true });",
        }:
            self.assertIn(token, js)

        for token in {
            'import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";',
            "const gltfLoader = new GLTFLoader();",
            "function isGlbAssetPath(assetPath)",
            'return /\\.glb(?:$|[?#])/i.test(assetPath || "");',
            "async function loadGlbGeometry(assetPath)",
            "gltfLoader.load(",
            'geometry.userData.meshSource = "glb_asset";',
            "geometry = await loadMeshGeometry(module?.asset_ref, part);",
            "const fallbackPath = normalizePath(`viewer/assets/meshes/${part}.mesh.json`);",
            "const assetPath = normalizePath(assetRef || fallbackPath);",
            "if (!isGlbAssetPath(assetPath))",
            "const geometry = await loadGlbGeometry(assetPath);",
            "console.warn(`GLB mesh fallback for ${part}: ${fallbackPath}`",
            "const geometry = await loadJsonMeshGeometry(fallbackPath);",
            'geometry.userData.meshSource = "mesh_json_fallback";',
            "geometry = fallbackGeometry(part);",
            'geometry.userData.meshSource = "generated_fallback";',
        }:
            self.assertIn(token, js)

    def test_visible_quest_and_forge_copy_keeps_exhibition_ui_japanese(self) -> None:
        quest_js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        forge_js = (self.repo_root / "viewer" / "armor-forge" / "forge.js").read_text(encoding="utf-8")

        for token in {
            "EQUIP: waiting for code",
            "Quest recall standby.",
            "Enter a 4-character code before transform.",
            "No armor loaded. Enter a 4-character code.",
            "VOICE DEBUG",
            "Whisper heard:",
            "Whisper returned an empty transcript.",
            "Whisper: empty.",
            "Transcript:",
            "confirmed.",
            "result: waiting",
            "trigger:",
            "transcript:",
        }:
            with self.subTest(quest_forbidden=token):
                self.assertNotIn(token, quest_js)

        for token in {
            "変身: コード待ち",
            "Quest呼び出し待機",
            "変身前に4桁コードを入力してください。",
            "鎧未読込。4桁コードを入力してください。",
            "音声デバッグ",
            "結果:",
            "合図:",
            "文字起こし:",
            "Whisper結果:",
        }:
            with self.subTest(quest_required=token):
                self.assertIn(token, quest_js)

        for token in {
            "The current 4-character code belongs",
            "生成して番号発行",
            'setPreviewLayerRow(panel, "readability", "Layers"',
            'setPreviewLayerRow(panel, "sidecar", "Sidecar"',
            'setPreviewLayerRow(panel, "offset", "Offset"',
            'setPreviewLayerRow(panel, "topping", "Topping"',
            'setPreviewLayerRow(panel, "variant", "Variant"',
            'setPreviewLayerRow(panel, "density", "Design QA"',
            'setPreviewLayerRow(panel, "structure", "Structure QA"',
            "attachment_offset_target_m pending",
            "back/boots offset target pending",
            "variant_key pending",
            "micro part contract pending",
        }:
            with self.subTest(forge_forbidden=token):
                self.assertNotIn(token, forge_js)

        for token in {
            "生成してコード発行",
            'setPreviewLayerRow(panel, "readability", "表示層"',
            'setPreviewLayerRow(panel, "sidecar", "設計メタ"',
            'setPreviewLayerRow(panel, "offset", "装着位置"',
            'setPreviewLayerRow(panel, "topping", "追加意匠"',
            'setPreviewLayerRow(panel, "variant", "型選択"',
            'setPreviewLayerRow(panel, "density", "意匠QA"',
            'setPreviewLayerRow(panel, "structure", "構造QA"',
            "装着位置基準は未設定",
            "背中/ブーツの位置基準は未設定",
        }:
            with self.subTest(forge_required=token):
                self.assertIn(token, forge_js)

    def test_replay_alignment_tool_reports_visible_and_settled_metrics(self) -> None:
        tool = (self.repo_root / "tools" / "verify_replay_armor_alignment.mjs").read_text(encoding="utf-8")

        for token in {
            "const measuredParts = parts.filter((part) => part.visible && Number(part.opacity || 0) > 0.01);",
            "alignmentAllowanceM: allowanceM",
            "excessDistanceM",
            "maxExcessDistanceM",
            "settledSummary",
            "settledMaxExcessDistanceM",
            "const settledSamples = samples.filter((sample) => sample.progress >= 0.5);",
            "function aggregateSampleSummary(samples) {",
            "const objectDebugSnapshot = (object) => {",
            "debugTimeline: samples.map((sample) => ({",
            "const response = await fetch(replayPath);",
            "await demo.applyReplay(await response.json(), {",
            "armorStandPreview: Boolean(demo.armorStandPreview)",
            "microphone: debugSnapshot?.microphone || null",
            "baseShell: debugSnapshot?.baseShell || {",
            "depositionEffects: debugSnapshot?.depositionEffects || {",
            "mirrorFrame: objectDebugSnapshot(demo.mirrorFrame)",
            "liveMirror: {",
            "const fallbackExperience = fallbackExperienceSnapshot();",
            "const experience = debugSnapshot?.experience || fallbackExperience;",
            "const uxState = debugSnapshot?.uxState || experience?.uxState || fallbackExperience.uxState;",
            "uxState: sample.debug?.uxState || sample.debug?.experience?.uxState || null",
            "experience: sample.debug?.experience || null",
        }:
            with self.subTest(token=token):
                self.assertIn(token, tool)

    def test_quest_viewer_glb_runtime_scale_uses_part_targets_not_legacy_shrink_only(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")

        for token in {
            "const QUEST_GLB_TARGET_SIZES = {",
            "geometry.userData.sourceSize = [size.x, size.y, size.z];",
            "geometry.userData.normalizedSize = boxSizeArray(geometry);",
            "mesh.userData.normalizedSize = geometry.userData?.normalizedSize || null;",
            "function runtimeRenderPlacement(runtimePackage, part)",
            "if (runtimePlacement) module.runtime_placement = webPreviewParityPlacement(runtimePackage, runtimePlacement);",
            "mesh.userData.runtimePlacement = module?.runtime_placement || null;",
            "function runtimePlacementForMesh(mesh)",
            "function applyRuntimePlacementOffset(mesh, part, reveal = 1, yaw = 0)",
            "function questGlbScaleForPart(mesh, part, reveal = 1)",
            "function questBaseRotationXForMesh(mesh)",
            "const target = targetSizeArrayFromPlacement(runtimePlacementForMesh(mesh), fallbackTarget);",
            "if (isGlbArmorMesh(mesh)) {",
            "applyRuntimePlacementOffset(mesh, part, reveal,",
            "mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));",
            "mesh.scale.set(...questGlbScaleForPart(mesh, part, this.armorStandScale));",
        }:
            self.assertIn(token, js)

        apply_segment = self._extract_js_function(js, "function applySegmentPose")
        self.assertIn("if (isGlbArmorMesh(mesh)) {", apply_segment)
        self.assertNotIn("if (options.centered && isGlbArmorMesh(mesh)) {", apply_segment)
        apply_live = self._extract_js_class_method(js, "applyLiveSuitPose(mesh, part, reveal)")
        self._assert_tokens_in_order(
            apply_live,
            [
                "const emerge = lerp(0.08, 1, reveal);",
                "if (isGlbArmorMesh(mesh)) {",
                "mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));",
                "return;",
                "const vrScale = VR_PART_SCALE[part] || 0.28;",
            ],
        )
        apply_live_mirror = self._extract_js_class_method(js, "applyLiveMirrorSuitPose(mesh, part, reveal)")
        self._assert_tokens_in_order(
            apply_live_mirror,
            [
                "const pose = questAssemblyPoseForPart(part);",
                "mesh.position.fromArray(pose);",
                "applyRuntimePlacementOffset(mesh, part, reveal, 0);",
                "applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, 0);",
                "mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));",
            ],
        )

    def test_quest_viewer_runtime_rotation_uses_render_placement_in_pose_paths(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        rotation_helper = self._extract_js_function(js, "function questRotationArrayFromPlacement")
        apply_helper = self._extract_js_function(js, "function applyRuntimePlacementRotation")
        base_helper = self._extract_js_function(js, "function questBaseRotationXForMesh")

        for token in {
            "function questRotationArrayFromPlacement(placement)",
            "function webPreviewRotationArrayFromPlacement(placement)",
            "function runtimePlacementRotationArray(placement)",
            "if (!Array.isArray(placement?.rotation_deg)) return null;",
            "THREE.MathUtils.degToRad(-rotation[0])",
            "THREE.MathUtils.degToRad(-rotation[1])",
            "THREE.MathUtils.degToRad(rotation[2])",
            "function questBaseRotationXForMesh(mesh)",
            "function applyRuntimePlacementRotation(mesh, baseX, baseY, baseZ)",
            "QUEST_PLACEMENT_BASE_QUATERNION.multiply(QUEST_PLACEMENT_ROTATION_QUATERNION).normalize()",
        }:
            self.assertIn(token, js)

        self.assertIn("return isGlbArmorMesh(mesh) && runtimePlacementForMesh(mesh) ? 0 : Math.PI / 2;", base_helper)
        self._assert_tokens_in_order(
            rotation_helper,
            [
                "const rotation = placement.rotation_deg.map((value) => Number(value));",
                "THREE.MathUtils.degToRad(-rotation[0])",
                "THREE.MathUtils.degToRad(-rotation[1])",
                "THREE.MathUtils.degToRad(rotation[2])",
            ],
        )
        self._assert_tokens_in_order(
            apply_helper,
            [
                "const rotation = runtimePlacementRotationArray(runtimePlacementForMesh(mesh));",
                "mesh.rotation.set(baseX, baseY, baseZ);",
                "QUEST_PLACEMENT_BASE_EULER.set(baseX, baseY, baseZ, \"XYZ\");",
                "QUEST_PLACEMENT_ROTATION_EULER.set(rotation[0], rotation[1], rotation[2], \"XYZ\");",
                "mesh.quaternion.copy(",
            ],
        )

        pose_methods = {
            "applySegmentPose": self._extract_js_function(js, "function applySegmentPose"),
            "applyLiveSuitPose": self._extract_js_class_method(js, "applyLiveSuitPose(mesh, part, reveal)"),
            "applyStandbySuitPose": self._extract_js_class_method(js, "applyStandbySuitPose(mesh, part)"),
            "applyMotionSuitPose": self._extract_js_class_method(js, "applyMotionSuitPose(mesh, part, frame, reveal, options = {})"),
        }
        for name, method in pose_methods.items():
            with self.subTest(pose_method=name):
                self.assertIn("applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0,", method)
                self.assertNotIn("mesh.rotation.set(Math.PI / 2, 0,", method)

    def test_quest_viewer_runtime_offset_rotates_with_body_yaw(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        offset_helper = self._extract_js_function(js, "function applyRuntimePlacementOffset")
        segment_pose = self._extract_js_function(js, "function applySegmentPose")
        live_pose = self._extract_js_class_method(js, "applyLiveSuitPose(mesh, part, reveal)")
        standby_pose = self._extract_js_class_method(js, "applyStandbySuitPose(mesh, part)")
        motion_pose = self._extract_js_class_method(js, "applyMotionSuitPose(mesh, part, frame, reveal, options = {})")

        for token in {
            "function applyRuntimePlacementOffset(mesh, part, reveal = 1, yaw = 0)",
            "const offset = runtimePlacementOffsetArrayForPart(part, runtimePlacementForMesh(mesh));",
            "const angle = Number(yaw) || 0;",
            "const sin = Math.sin(angle);",
            "const cos = Math.cos(angle);",
            "const rotatedX = offset[0] * cos - offset[2] * sin;",
            "const rotatedZ = offset[0] * sin + offset[2] * cos;",
            "mesh.position.x += rotatedX * amount;",
            "mesh.position.z += rotatedZ * amount;",
        }:
            self.assertIn(token, offset_helper)

        self.assertIn("const poseYaw = options.centered ? 0 : liveProfile ? (liveProfile.yawOffsetRad || 0) : (pose.rotation_z || 0);", segment_pose)
        self.assertIn("applyRuntimePlacementOffset(mesh, part, reveal, poseYaw);", segment_pose)
        self.assertIn("applyRuntimePlacementOffset(mesh, part, reveal, this.liveTorsoYaw);", live_pose)
        self.assertIn("armorStandRigPoseForPart(part, mesh, standTransform)", standby_pose)
        self.assertNotIn("applyRuntimePlacementOffset(mesh, 1,", standby_pose)
        self.assertIn("const torsoYaw = options.centered ? 0 : Number(frame.torso_yaw || 0);", motion_pose)
        self.assertIn("applyRuntimePlacementOffset(mesh, part, reveal, torsoYaw);", motion_pose)

    def test_quest_viewer_web_preview_parity_can_prefer_web_runtime_placement_fields(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        resolver = (self.repo_root / "viewer" / "shared" / "runtime-placement-resolver.js").read_text(encoding="utf-8")
        query_helper = self._extract_js_function(js, "function useWebPreviewPlacementParityQuery")
        contract_helper = self._extract_js_function(js, "function runtimePlacementContractUsesWebPreviewParity")
        parity_helper = self._extract_js_function(js, "function webPreviewParityPlacement")
        target_helper = self._extract_js_function(js, "function targetSizeArrayFromPlacement")
        mode_helper = self._extract_js_function(js, "function useWebPreviewRuntimePlacement")
        offset_helper = self._extract_js_function(js, "function runtimePlacementOffsetArrayForPart")
        web_rotation = self._extract_js_function(js, "function webPreviewRotationArrayFromPlacement")
        runtime_rotation = self._extract_js_function(js, "function runtimePlacementRotationArray")
        module_helper = self._extract_js_function(js, "function moduleForRuntimePart")
        snapshot_method = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        for token in {
            'params().get("webPreviewParity")',
            'params().get("webPreviewPlacement")',
            '"web_preview_parity"',
            '"quest_rig"',
            "contract?.quest_runtime_placement_mode",
            "placement?.quest_runtime_placement_mode",
            "module.runtime_placement = webPreviewParityPlacement(runtimePackage, runtimePlacement);",
            "runtimePlacementMode: useWebPreviewRuntimePlacement(placement) ? \"web_preview_parity\" : \"quest_rig\",",
        }:
            self.assertIn(token, js)

        self.assertIn('["1", "true", "yes", "web", "web_preview", "parity"].includes(value)', query_helper)
        self.assertIn('["1", "true", "web_preview_parity", "web_preview", "web-preview", "web", "parity"].includes(value)', contract_helper)
        self.assertIn("useWebPreviewPlacementParityQuery()", parity_helper)
        self.assertIn("runtimePlacementContractUsesWebPreviewParity(runtimePackage, placement)", parity_helper)
        self.assertIn("resolveRuntimeTargetSize({", target_helper)
        self.assertIn("mode: useWebPreviewRuntimePlacement(placement) ? \"web_preview_parity\" : \"quest_rig\",", target_helper)
        self.assertIn("resolveRuntimePlacementMode({", mode_helper)
        self.assertIn("webPreviewParity: useWebPreviewPlacementParityQuery(),", mode_helper)
        self.assertIn("resolveRuntimeOffset({", offset_helper)
        self.assertIn("mode: useWebPreviewRuntimePlacement(placement) ? \"web_preview_parity\" : \"quest_rig\",", offset_helper)
        self.assertIn("THREE.MathUtils.degToRad(rotation[0])", web_rotation)
        self.assertIn("THREE.MathUtils.degToRad(rotation[1])", web_rotation)
        self.assertIn("resolveRuntimeRotation({", runtime_rotation)
        self.assertIn("radiansFromDegrees(rotation[0])", resolver)
        self.assertIn("radiansFromDegrees(-rotation[0])", resolver)
        self.assertIn("webPreviewParityPlacement(runtimePackage, runtimePlacement)", module_helper)
        self.assertIn("runtimeOffset: useWebPreviewRuntimePlacement(placement)", snapshot_method)
        self.assertIn("runtimeOffsetClamped: runtimePlacementOffsetArrayForPart(part, placement)", snapshot_method)

    def test_web_and_quest_share_body_surface_anchor_clamps(self) -> None:
        shared = (self.repo_root / "viewer" / "shared" / "armor-canon.js").read_text(encoding="utf-8")
        resolver = (self.repo_root / "viewer" / "shared" / "runtime-placement-resolver.js").read_text(encoding="utf-8")
        quest = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        forge = (self.repo_root / "viewer" / "armor-forge" / "forge.js").read_text(encoding="utf-8")

        for token in {
            "export const BODY_SURFACE_FIT_POLICIES = Object.freeze({",
            "role: \"pelvis_belt_loop\"",
            "targetContact: \"front, side, and rear plates read as one close loop around the pelvis\"",
            "export function wearableSurfaceFitPolicyForPart(partName)",
            "export function clampSurfaceOffsetForPart(partName, offset, space = \"vrm\")",
            "const policySpace = space === \"quest\" ? \"questOffsetClamp\" : \"vrmOffsetClamp\";",
        }:
            self.assertIn(token, shared)

        for token in {
            "clampSurfaceOffsetForPart,",
            "wearableSurfaceFitPolicyForPart,",
            "function questSurfaceOffsetArrayFromPlacement(placement)",
            "placement?.quest_surface_offset_clamped_m",
            "placement?.surface_anchor?.quest_rig_offset_clamped_m",
            "function clampedQuestOffsetArrayFromPlacement(part, placement)",
            "runtimeOffsetClamped: runtimePlacementOffsetArrayForPart(part, placement),",
            "surfaceFitRole: surfacePolicy?.role || \"\",",
        }:
            self.assertIn(token, quest)

        for token in {
            "const runtimeClampedOffset = questSurfaceOffsetArrayFromPlacement(placement);",
            "if (runtimeClampedOffset) return runtimeClampedOffset;",
            "return offset ? clampSurfaceOffsetForPart(part, offset, \"quest\") : null;",
            "return offset ? clampSurfaceOffsetForPart(part, offset, \"vrm\") : null;",
        }:
            self.assertIn(token, resolver)

        self.assertIn("clampSurfaceOffsetForPart,", forge)
        self.assertIn("resolveRuntimeOffset({", forge)
        self.assertIn("mode: \"web_preview_parity\",", forge)

    def test_quest_armor_stand_workshop_controls_do_not_conflict_with_voice(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        init_controllers = self._extract_js_class_method(js, "initControllers()")
        stand_pose = self._extract_js_function(js, "function armorStandPoseForPart")
        inspection_rotation = self._extract_js_function(js, "function applyArmorStandInspectionRotation")
        standby_pose = self._extract_js_class_method(js, "applyStandbySuitPose(mesh, part)")
        shortcut_method = self._extract_js_class_method(js, "canUseRightTriggerShortcut()")
        activate_method = self._extract_js_class_method(js, "activateController(controller)")
        get_controller_by_hand = self._extract_js_class_method(js, "getControllerByHand(hand, { allowIndexFallback = false } = {})")
        controller_input = self._extract_js_class_method(js, "controllerInputSnapshot(controller, index)")
        workshop_input = self._extract_js_class_method(js, "armorStandWorkshopInputSnapshot()")
        workshop_update = self._extract_js_class_method(js, "updateArmorStandWorkshopControls(dt)")
        workshop_move = self._extract_js_class_method_by_name(js, "applyArmorStandWorkshopMove")
        workshop_drag = self._extract_js_class_method_by_name(js, "applyArmorStandWorkshopDrag")
        workshop_scale = self._extract_js_class_method_by_name(js, "setArmorStandWorkshopScale")
        workshop_finish = self._extract_js_class_method_by_name(js, "finishArmorStandWorkshopManipulation")
        snapshot_method = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        for token in {
            "const ARMOR_STAND_FLOOR_LIFT_M = 0.24;",
            "const ARMOR_STAND_CENTER_Z = -0.28;",
            "const ARMOR_STAND_CENTER_Y =",
            "const ARMOR_STAND_EXPLODE_DISTANCE_M =",
            "const ARMOR_STAND_SCALE_MIN =",
            "const ARMOR_STAND_SCALE_MAX =",
            "const ARMOR_STAND_PITCH_LIMIT_RAD =",
            "const ARMOR_STAND_GRAB_YAW_PER_M =",
            "const ARMOR_STAND_GRAB_PITCH_PER_M =",
            "const ARMOR_STAND_GRAB_DEADZONE_M =",
            "const ARMOR_STAND_GRAB_MAX_DELTA_M =",
            "const ARMOR_STAND_MOVE_DEADZONE_M =",
            "const ARMOR_STAND_MOVE_MAX_DELTA_M =",
            "const ARMOR_STAND_EXIT_ACTIONS =",
            "const QUEST_HUMAN_ANCHOR_CONTRACT =",
            "function questAssemblyPoseForPart(part)",
            "function armorStandExplodeVectorForPart(part)",
            "function armorStandPoseForPart(part, transform = {})",
            "function armorStandRigPoseForPart(part, mesh, transform = {})",
            "function applyArmorStandInspectionRotation",
            "updateArmorStandWorkshopControls(dt)",
            "applyArmorStandWorkshopMove",
            "applyArmorStandWorkshopDrag",
            "setArmorStandWorkshopScale",
            "finishArmorStandWorkshopManipulation",
            "this.armorStandInteractCount = 0;",
        }:
            self.assertIn(token, js)
        self.assertNotIn("const ARMOR_STAND_YAW_STEP_DEG", js)
        self.assertNotIn("cycleArmorStandInspection", js)
        self.assertNotIn('"inspect_rotate"', js)

        self.assertIn("controller.userData.inputSource = event.data", init_controllers)
        for token in {
            'controller.addEventListener("squeezestart"',
            'controller.addEventListener("squeezeend"',
            "controller.userData.squeezePressed = false;",
        }:
            self.assertIn(token, init_controllers)
        for token in {
            "getControllerByHand(hand, { allowIndexFallback = false } = {})",
            "controller?.userData?.inputSource && this.controllerHandedness(controller) === hand",
            "if (!allowIndexFallback) return null;",
            'this.getControllerByHand("left", { allowIndexFallback: true })',
        }:
            self.assertIn(token, js)
        self.assertIn("controllerButtonPressed", js)
        for token in {
            "const inputSource = controller?.userData?.inputSource || null;",
            "const squeezeEventPressed = index === 1 && controller?.userData?.squeezePressed === true;",
            "squeezeEventPressed,",
            "pressed: Boolean(button?.pressed || value > 0.65 || squeezeEventPressed)",
            "buttonCount: Number(buttons.length || 0)",
            "axesCount: Number(gamepad?.axes?.length || 0)",
            "profiles: Array.isArray(inputSource?.profiles) ? inputSource.profiles.slice(0, 4) : []",
        }:
            self.assertIn(token, controller_input)
        self.assertIn("if (!controller?.userData?.inputSource) return false;", js)
        for token in {
            'mode: this.workshopPinchActive ? "two_grip_scale_rotate_move" : this.workshopGrabActive ? "right_grip_rig_move" : "idle"',
            'triggerMapping: "gamepad.buttons[0]"',
            'gripMapping: "gamepad.buttons[1]"',
            "rightGrip: this.controllerInputSnapshot(right, 1)",
            "leftGrip: this.controllerInputSnapshot(left, 1)",
            "controllerCount: this.controllers.length",
        }:
            self.assertIn(token, workshop_input)

        for token in {
            "const anchorCenter = QUEST_HUMAN_ANCHOR_CONTRACT[part]?.center_m;",
            "return anchorCenter.slice(0, 3);",
        }:
            self.assertIn(token, js)

        for token in {
            "const pitch = clamp(Number(options.pitch) || 0, -ARMOR_STAND_PITCH_LIMIT_RAD, ARMOR_STAND_PITCH_LIMIT_RAD);",
            "const scale = clamp(Number(options.scale) || 1, ARMOR_STAND_SCALE_MIN, ARMOR_STAND_SCALE_MAX);",
            "const explode = clamp(Number(options.explode) || 0, 0, 1);",
            "const pose = questAssemblyPoseForPart(part);",
            "const explodeVector = armorStandExplodeVectorForPart(part);",
            "ARMOR_STAND_EXPLODE_DISTANCE_M",
            "ARMOR_STAND_CENTER_Y + pitchedY",
        }:
            self.assertIn(token, stand_pose)
        for token in {
            "const safePitch = clamp(Number(pitch) || 0, -ARMOR_STAND_PITCH_LIMIT_RAD, ARMOR_STAND_PITCH_LIMIT_RAD);",
            'ARMOR_STAND_INSPECTION_EULER.set(safePitch, safeYaw, 0, "YXZ");',
            "mesh.quaternion.premultiply(ARMOR_STAND_INSPECTION_QUATERNION);",
        }:
            self.assertIn(token, inspection_rotation)

        self.assertIn("const pose = armorStandRigPoseForPart(part, mesh, standTransform);", standby_pose)
        self.assertNotIn("applyRuntimePlacementOffset(mesh, 1,", standby_pose)
        self.assertIn("applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, 0);", standby_pose)
        self.assertIn("applyArmorStandInspectionRotation(mesh,", standby_pose)
        self.assertIn(
            "return this.menuMode !== XR_MENU_MODE_OPEN && !this.demo.isArmorStandPreviewMode();",
            shortcut_method,
        )
        self._assert_tokens_in_order(
            activate_method,
            [
                'if (this.controllerHandedness(controller) === "right" && this.demo.isArmorStandPreviewMode()) {',
                "this.controllerButtonPressed(controller, 1)",
                'this.demo.exitArmorStandToMirror({ source: "rightGripTriggerEscape" });',
                "return;",
                "this.canActivateHoveredInArmorStand(this.hovered.userData.action)",
                "this.activateHovered();",
                "return;",
                'this.demo.toggleArmorStandPartExplosion({ source: "rightTrigger", handedness: "right" });',
                "return;",
                "if (this.group.visible && this.hovered && this.hoveredController === controller) {",
                'if (this.demo.voiceState === "rejected" && this.demo.canRunVoiceCommand()) {',
            ],
        )
        for token in {
            "this.controllerButtonPressed(right, 1)",
            "this.demo.applyArmorStandWorkshopMove",
            "this.demo.applyArmorStandWorkshopDrag",
            "this.demo.finishArmorStandWorkshopManipulation",
        }:
            self.assertIn(token, workshop_update)
        for token in {
            "ARMOR_STAND_MOVE_DEADZONE_M",
            "ARMOR_STAND_MOVE_MAX_DELTA_M",
            "ARMOR_STAND_TWO_HAND_YAW_DEADZONE_RAD",
            "const previousYaw = Math.atan2(this.workshopLastPinchVector.x, this.workshopLastPinchVector.z);",
            'this.demo.applyArmorStandWorkshopDrag({ yawDelta, pitchDelta: 0, source: "twoGripRigYaw" });',
        }:
            self.assertIn(token, workshop_update)
        for token in {
            "ARMOR_STAND_PITCH_LIMIT_RAD",
        }:
            self.assertIn(token, workshop_drag)
        for token in {
            'coordinateSpace = "world"',
            "ARMOR_STAND_MOVE_LOCAL_VECTOR.set(dx, dy, dz);",
            "this.rig.getWorldQuaternion(ARMOR_STAND_MOVE_WORLD_QUATERNION).invert();",
            "ARMOR_STAND_MOVE_LOCAL_VECTOR.applyQuaternion(ARMOR_STAND_MOVE_WORLD_QUATERNION);",
            "this.armorStandOffset.x + ARMOR_STAND_MOVE_LOCAL_VECTOR.x",
        }:
            self.assertIn(token, workshop_move)
        for token in {
            "ARMOR_STAND_SCALE_MIN",
            "ARMOR_STAND_SCALE_MAX",
            "clamp(",
        }:
            self.assertIn(token, workshop_scale)
        for token in {
            "this.armorStandInteractCount += 1;",
            'this.sendQuestDebugTelemetry("armor-stand-interact", { force: true });',
        }:
            self.assertIn(token, workshop_finish)
        self.assertIn("armorStand:", snapshot_method)
        self.assertIn("input: this.spatialPanel?.armorStandWorkshopInputSnapshot?.() || null", snapshot_method)
        self.assertIn('rightTriggerMode: this.armorStandPreview ? "ui_exit_or_grip_escape_or_explode_toggle" : "voice_shortcut"', snapshot_method)

    def test_quest_human_body_mock_is_the_runtime_anchor_source(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        anchor_helper = self._extract_js_function(js, "function questHumanAnchorCenterForPart")
        relative_helper = self._extract_js_function(js, "function questBodyRelativeOffsetForPart")
        base_pose = self._extract_js_class_method_by_name(js, "applyBaseSuitGuidePose")
        telemetry = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        for token in {
            "const QUEST_HUMAN_BODY_MOCK = {",
            'version: "quest-human-body-mock.v1"',
            "spine_z_m: -0.28",
            "points_m:",
            "upper_torso: [0, -0.52, -0.28]",
            "left_shoulder_joint: [-0.31, -0.46, -0.28]",
            "bodyPoint: \"upper_torso\"",
            "offset_m: [0, 0, -0.14]",
            "center_m: [0, -0.52, -0.42]",
        }:
            self.assertIn(token, js)
        for token in {
            "const anchorCenter = QUEST_HUMAN_ANCHOR_CONTRACT[part]?.center_m;",
            "const bodyPoint = questHumanBodyPoint(contract?.bodyPoint);",
            "return [",
            "bodyPoint[0] + Number(offset[0] || 0)",
        }:
            self.assertIn(token, anchor_helper)
        self.assertIn("pose[2] - QUEST_HUMAN_BODY_MOCK.spine_z_m - 0.06", relative_helper)
        self.assertIn("armorStandRigPoseForPoint(position, standTransform)", base_pose)
        self.assertIn("humanBodyMock:", telemetry)
        self.assertIn("armorCenterCount: Object.keys(QUEST_HUMAN_ANCHOR_CONTRACT || {}).length", telemetry)
        self.assertIn("centerlineWorld:", telemetry)
        self.assertIn('head: rigLocalPointWorldDebugSnapshot(this.rig, questHumanBodyPoint("head"))', telemetry)
        self.assertIn('pelvis: rigLocalPointWorldDebugSnapshot(this.rig, questHumanBodyPoint("pelvis"))', telemetry)

    def test_quest_armor_stand_observer_anchor_faces_user_and_snaps(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        capture_anchor = self._extract_js_class_method(js, "captureWorldAnchor(viewMode = this.xrViewMode)")
        snap_method = self._extract_js_class_method_by_name(js, "snapRigToWorldAnchor")
        session_scene = self._extract_js_class_method(js, "initScene()")

        for token in {
            "const XR_ARMOR_STAND_DISTANCE = 2.0;",
            "const XR_ARMOR_STAND_SCALE = 0.84;",
            "const XR_ARMOR_STAND_YAW_OFFSET_RAD = 0;",
            "const XR_REPLAY_OBSERVER_YAW_OFFSET_RAD = 0;",
            'const XR_ANCHOR_PROFILE_ARMOR_STAND = "armor_stand";',
            'const XR_ANCHOR_PROFILE_REPLAY_OBSERVER = "replay_observer";',
        }:
            self.assertIn(token, js)
        for token in {
            "const anchorProfile = this.worldAnchorProfileForViewMode(viewMode);",
            "const armorStandObserver = anchorProfile === XR_ANCHOR_PROFILE_ARMOR_STAND;",
            "const observerDistance = armorStandObserver ? XR_ARMOR_STAND_DISTANCE : VR_REPLAY_OBSERVER_DISTANCE;",
            "this.xrWorldAnchorScale.setScalar(observerScale);",
            "rigYaw = yaw + Math.PI + observerYawOffset;",
            "this.xrWorldAnchorProfile = anchorProfile;",
        }:
            self.assertIn(token, capture_anchor)
        self.assertNotIn("Math.PI * 0.82", capture_anchor)
        self.assertIn("this.rig.position.copy(this.xrWorldAnchorPosition);", snap_method)
        self.assertIn('this.snapRigToWorldAnchor({ source: "armorStandPreview" });', js)
        self.assertIn('this.snapRigToWorldAnchor({ source: "armorStandExit" });', js)
        self.assertIn('this.snapRigToWorldAnchor({ source: "sessionstart" });', session_scene)
        self.assertIn("this.xrWorldAnchorProfile !== expectedAnchorProfile", js)
        self.assertIn("expectedAnchorProfile: this.worldAnchorProfileForViewMode(this.xrViewMode)", js)

    def test_quest_viewer_surfaces_runtime_diagnostic_in_debug_output_only(self) -> None:
        html = (self.repo_root / "viewer" / "quest-iw-demo" / "index.html").read_text(encoding="utf-8")
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        helper = self._extract_js_function(js, "function runtimePlacementDiagnostic")
        load_method = self._extract_js_class_method(js, "async loadArmorMeshes()")

        for token in {
            "RUNTIME DIAGNOSTIC",
            'const gate = checks?.can_render_runtime_suit === false ? "FAIL" : "OK";',
            "`gate: ${gate} visible ${visible}/${minimum}`",
            "`placement: ${placementCount} records, ${offsetCount} offsets, ${rotationCount} rotations, ${targetCount} targets`",
            "`meshes: ${meshRecords.length} loaded, ${glbCount} GLB, ${fallbackCount} fallback, ${placedMeshCount} placed, ${rotatedMeshCount} rotated`",
            'missing.length ? `missing: ${missing.join(",")}` : "missing: none"',
            "runtimePlacementForMesh(mesh)",
        }:
            self.assertIn(token, helper)

        self.assertIn("const runtimeDiagnostic = runtimePlacementDiagnostic(this.runtimePackage, this.meshes);", load_method)
        self.assertIn('console.info("[Quest runtime diagnostic]", runtimeDiagnostic);', load_method)
        self.assertIn("this.appendVoiceDebug(runtimeDiagnostic);", load_method)
        self.assertIn('id="debugPanel"', html)
        self.assertIn('id="voiceDebug"', html)
        self.assertNotIn('id="runtimePlacementDiagnostic"', html)

    def test_quest_viewer_debug_telemetry_reports_live_runtime_state_only_when_debugged(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        snapshot_method = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')
        telemetry_method = self._extract_js_class_method(js, 'sendQuestDebugTelemetry(event = "scene", { force = false } = {})')

        for token in {
            "const QUEST_DEBUG_TELEMETRY_INTERVAL_MS = 1000;",
            "function useQuestDebugTelemetry()",
            'return params().get("debug") === "1" || params().has("qa");',
            "function voiceDeviceColorForState(state)",
            "function questDebugMicrophoneSnapshot()",
            "function questDebugUxStateSnapshot(demo)",
            "userAgent: navigator.userAgent",
            "async function postQuestDebugTelemetry(payload)",
            'fetch(`${getApiBase()}/api/quest-debug`, {',
            "this.lastQuestDebugTelemetryAt = -Infinity;",
            'demo.sendQuestDebugTelemetry("started", { force: true });',
        }:
            self.assertIn(token, js)

        for token in {
            "query: questDebugQuerySnapshot()",
            "microphone: questDebugMicrophoneSnapshot()",
            "const experienceState = questDebugUxStateSnapshot(this);",
            "const replayMotionDiagnostic = this.replayMotionDiagnostic || makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);",
            "const payload = {",
            "uxState: experienceState.uxState",
            "experience: experienceState",
            "liveBodyPose: useQuestLiveBodyPose()",
            "playbackSource: this.playbackSource",
            "trialReplayPath: this.trialReplayPath",
            "replayMotionDiagnostic,",
            "replayMotion:",
            "cameraForwardWorld: forwardVectorDebugSnapshot(this.cameraQuaternion)",
            "cameraLocalInRig: localVectorInObjectDebugSnapshot(this.rig, this.cameraPosition)",
            "cameraToAnchorWorldM: vectorDeltaDebugSnapshot(this.xrWorldAnchorPosition, this.cameraPosition)",
            "anchorToRigDeltaM: vectorDeltaDebugSnapshot(this.rig?.position, this.xrWorldAnchorPosition)",
            "baseShell:",
            "armorStand:",
            "visible: Boolean(this.baseSuitGroup?.visible)",
            "visibleCount: meshRecords.filter((record) => record.visible).length",
            "runtimeDiagnostic: runtimePlacementDiagnostic(this.runtimePackage, this.meshes)",
            "payload.centerlineQa = questCenterlineQaSnapshot(payload);",
            "return payload;",
        }:
            self.assertIn(token, snapshot_method)

        self.assertIn("if (!useQuestDebugTelemetry()) return;", telemetry_method)
        self.assertIn("QUEST_DEBUG_TELEMETRY_INTERVAL_MS", telemetry_method)
        self.assertIn('this.sendQuestDebugTelemetry("scene");', update_scene)
        self.assertIn('this.sendQuestDebugTelemetry("armor-loaded", { force: true });', js)

    def test_centerline_qa_skips_xr_anchor_distance_outside_immersive_session(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        qa_helper = self._extract_js_function(js, "function questCenterlineQaSnapshot")

        self.assertIn("const xrAnchorQaActive = Boolean(xr.session);", qa_helper)
        self.assertIn("if (xrAnchorQaActive && !xr.xrWorldAnchorReady) anchorFailures.push(\"anchor_not_ready\");", qa_helper)
        self.assertIn("if (xrAnchorQaActive && Number(xr.anchorToRigDistanceM) > thresholds.anchorToRigDistanceMaxM)", qa_helper)
        self.assertIn("if (xrAnchorQaActive && Math.abs(Number(xr.anchorToRigYawDeltaDeg)) > thresholds.anchorToRigYawMaxDeg)", qa_helper)
        self.assertIn("const cameraLocalX = xrAnchorQaActive ? questVectorArrayAxis(xr.cameraLocalInRig, 0) : null;", qa_helper)
        self.assertIn('state: !xrAnchorQaActive ? "skipped" : anchorFailures.length ? "fail" : "pass"', qa_helper)
        self.assertIn('active: xrAnchorQaActive', qa_helper)
        self.assertIn('anchor=${!xrAnchorQaActive ? "SKIP" : anchorFailures.length ? "NG" : "OK"}', qa_helper)

    def test_centerline_qa_uses_armor_stand_transformed_body_anchor_when_previewing(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        transform_helper = self._extract_js_function(js, "function armorStandDebugTransform")
        anchor_helper = self._extract_js_function(js, "function questDebugAnchorLocalForPart")
        center_snapshot = self._extract_js_function(js, "function questPartCenterDebugSnapshot")

        for token in {
            "yaw: demo?.armorStandYaw || 0",
            "pitch: demo?.armorStandPitch || 0",
            "scale: demo?.armorStandScale || 1",
            "explode: demo?.armorStandExploded ? 1 : 0",
            "offset: demo?.armorStandOffset || null",
        }:
            self.assertIn(token, transform_helper)
        self._assert_tokens_in_order(
            anchor_helper,
            [
                "const assemblyPose = questAssemblyPoseForPart(part);",
                "if (!demo?.armorStandPreview) return assemblyPose;",
                "return armorStandRigPoseForPoint(",
                "assemblyPose,",
                "armorStandDebugTransform(demo),",
                "[0, 0, 0],",
                "armorStandExplodeVectorForPart(part),",
            ],
        )
        self.assertIn("const canonicalAnchorLocal = questDebugAnchorLocalForPart(demo, part);", center_snapshot)
        self.assertIn('anchorPoseMode: demo?.armorStandPreview ? "armor_stand" : "worn_body"', center_snapshot)

    def test_quest_centerline_debug_payload_distinguishes_web_parity_from_quest_rig_offsets(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        per_part_helper = self._extract_js_function(js, "function questRuntimePlacementAnchorDiagnosticsForPart")
        aggregate_helper = self._extract_js_function(js, "function questAnchorDiagnosticsSnapshot")
        centerline_helper = self._extract_js_function(js, "function questCenterlineQaSnapshot")
        query_helper = self._extract_js_function(js, "function questDebugQuerySnapshot")
        snapshot_method = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        for token in {
            "function questVectorDeltaArrayDebugSnapshot(toVector, fromVector)",
            "function questVectorArrayDistanceDebugSnapshot(toVector, fromVector)",
            "function questVectorArraysNearlyEqual(left, right, epsilon = 0.0005)",
            "function questCountBy(records, mapper)",
            "function questDominantCountKey(counts)",
        }:
            self.assertIn(token, js)

        for token in {
            'version: "quest-runtime-anchor-diagnostics.v1"',
            "activeMode",
            "activeOffsetSource",
            "activeOffsetClamped: vectorArrayDebugSnapshot(activeOffsetClamped)",
            "questRigOffsetClamped: vectorArrayDebugSnapshot(questOffsetClamped)",
            "webPreviewOffsetClamped: vectorArrayDebugSnapshot(webOffsetClamped)",
            "questVsWebOffsetDeltaM: questVectorDeltaArrayDebugSnapshot(webOffsetClamped, questOffsetClamped)",
            "questVsWebOffsetDistanceM: questVectorArrayDistanceDebugSnapshot(webOffsetClamped, questOffsetClamped)",
        }:
            self.assertIn(token, per_part_helper)

        self._assert_tokens_in_order(
            per_part_helper,
            [
                'const activeMode = useWebPreviewRuntimePlacement(placement) ? "web_preview_parity" : "quest_rig";',
                "const questOffsetClamped = clampedQuestOffsetArrayFromPlacement(part, placement);",
                "const webOffsetClamped = webPreviewSurfaceOffsetArrayFromPlacement(placement)",
                "const activeOffsetClamped = runtimePlacementOffsetArrayForPart(part, placement);",
                'questVectorArraysNearlyEqual(activeOffsetClamped, webOffsetClamped) ? "web_preview_parity"',
                'questVectorArraysNearlyEqual(activeOffsetClamped, questOffsetClamped) ? "quest_rig"',
            ],
        )
        for token in {
            'version: "quest-anchor-diagnostics.v1"',
            "runtimePlacementModeCounts",
            "activeOffsetSourceCounts",
            "dominantRuntimePlacementMode",
            "dominantActiveOffsetSource",
            "runtimeOffsetImplicated",
            "likelySource",
            '"runtime_anchor_not_runtime_offset"',
            "triageHint: `${likelySource}; activeOffset=${dominantActiveOffsetSource}; mode=${dominantRuntimePlacementMode}`",
        }:
            self.assertIn(token, aggregate_helper)

        self.assertIn("anchorDiagnostics: questRuntimePlacementAnchorDiagnosticsForPart(part, placement),", snapshot_method)
        self.assertIn('webPreviewParity: query.get("webPreviewParity") || "",', query_helper)
        self.assertIn('webPreviewPlacement: query.get("webPreviewPlacement") || "",', query_helper)
        self.assertIn("const anchorDiagnostics = questAnchorDiagnosticsSnapshot({", centerline_helper)
        self.assertIn("anchorDiagnostics,", centerline_helper)
        self.assertIn("mode=${anchorDiagnostics.dominantRuntimePlacementMode}", centerline_helper)
        self.assertIn("offset=${anchorDiagnostics.dominantActiveOffsetSource}", centerline_helper)

    def test_quest_ux_state_prioritizes_current_mode_over_historical_voice_state(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        helper = self._extract_js_function(js, "function questDebugUxStateSnapshot")
        snapshot_method = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        for token in {
            'const voiceStateIsHistorical =',
            '!playing && progress === 0 && ["complete", "detected", "deposition"].includes(voiceState);',
            'uxState = xrSession ? "armor_stand_observer_idle" : "browser_armor_stand_observer_idle";',
            'uxState = xrSession ? "archive_replay_mirror_active" : "browser_archive_replay_mirror_active";',
            'uxState = xrSession ? "archive_replay_observer_active" : "browser_archive_replay_observer_active";',
            'uxState = xrSession ? "transform_active_self" : "browser_transform_active_self";',
            'uxState = xrSession ? "mirror_idle" : "browser_mirror_idle";',
            'uxState = xrSession ? "loaded_idle_self" : "browser_loaded_idle_self";',
            '"browser_archive_replay_mirror_active"',
            '"browser_mirror_idle"',
            '"browser_armor_stand_observer_idle"',
            "realMicrophoneExpected: useMicrophoneCapture() && !useMockTrigger(),",
        }:
            self.assertIn(token, helper)

        self.assertIn("const experienceState = questDebugUxStateSnapshot(this);", snapshot_method)
        self.assertIn("uxState: experienceState.uxState", snapshot_method)
        self.assertIn("experience: experienceState", snapshot_method)

    def test_quest_voice_device_colors_separate_ready_recording_and_recognition(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        color_helper = self._extract_js_function(js, "function voiceDeviceColorForState")
        spatial_voice = self._extract_js_class_method(js, 'setVoiceState(state, detail = "")')
        device_update = self._extract_js_class_method(js, "updateTransformDevice(device, dt)")

        for token in {
            'if (state === "ready" || state === "arming") return 0x36f28f;',
            'if (state === "recording") return 0xffcf5a;',
            'if (state === "analyzing") return 0x8a7cff;',
            'if (state === "detected" || state === "complete") return 0x43d8ff;',
            'if (state === "rejected") return 0xff6b6b;',
        }:
            self.assertIn(token, color_helper)

        self.assertIn("const stateColor = voiceDeviceColorForState(state);", spatial_voice)
        self.assertIn("const color = voiceDeviceColorForState(this.demo.voiceState);", device_update)
        self.assertNotIn("const color = active ? 0xffcf5a", device_update)

    def test_quest_viewer_contract_detects_vrm_only_render_regressions(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")

        for token in {
            "async loadSuitByRecallCode(code, { reloadMeshes = false, pushUrl = false } = {})",
            "this.clearArmorMeshes();",
            "await this.loadArmorMeshes();",
            "async loadArmorMeshes()",
            "const modules = this.suitspec?.modules || {};",
            "if (!module || module.enabled !== true) return null;",
            "const mesh = await createArmorMesh(part, module, this.suitspec);",
            "this.meshes.set(record.part, record.mesh);",
            "this.liveMirrorMeshes.set(record.part, mirrorMesh);",
            "const BASE_SUIT_SURFACE_PARTS = [",
            "function createBaseSuitTexture(suitspec)",
            "function createBaseSuitMaterial(suitspec)",
            "function useQuestLiveBodyPose()",
            "GLTFLoader",
            "function isGlbAssetPath(assetPath)",
            "function loadGlbGeometry(assetPath)",
            "GLB mesh fallback",
            "this.baseSuitGroup = new THREE.Group();",
            "this.refreshBaseSuitSurface();",
            "updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView = false, reveal, bodyShellAligned = true })",
            "const liveBodyPose = useQuestLiveBodyPose();",
            "const fixedBodyPose = inXr && !liveBodyPose && !mocopiSegmentPose;",
            "const useLiveSuit = liveBodyPose && selfView && this.xrWorldAnchorReady;",
            "const hasSegmentPose = Object.keys(segments).length > 0;",
            "const hasRuntimePose = useLiveSuit || hasSegmentPose || Boolean(replayMotionFrame);",
            "const standbyPreview = this.meshes.size > 0 && this.isArmorStandPreviewMode();",
            "const canRenderTransformSuit = this.playing && hasRuntimePose;",
            "const shouldShowSuit = standbyPreview || canRenderTransformSuit;",
            "const bodyShellAligned = fixedBodyPose || (selfView && !mocopiSegmentPose) || (!inXr && !mocopiSegmentPose);",
            "this.updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView, reveal, bodyShellAligned });",
            "const useReplayMotion = !hasSegmentPose && replayMotionFrame;",
            "this.applyStandbySuitPose(mesh, part);",
            "this.applyMotionSuitPose(mesh, part, replayMotionFrame, reveal, { centered: bodyShellAligned });",
            "this.applyLiveSuitPose(mesh, part, reveal);",
            "this.updateLiveMirrorAvatar(progress, reveal, { liveBodyPose });",
            "} else if (!canRenderTransformSuit || (!useLiveSuit && !pose && !useReplayMotion)) {",
            "mesh.material.opacity = standbyPreview ? 0.82",
            "mesh.visible = shouldShowSuit && mesh.material.opacity > 0.09;",
        }:
            self.assertIn(token, js)

        self.assertIn('const SELF_VIEW_HIDDEN_PARTS = new Set(["helmet", "left_hand", "right_hand"]);', js)
        self.assertIn('const SELF_VIEW_STANDBY_HIDDEN_PARTS = new Set(["helmet"]);', js)
        self.assertNotIn('SELF_VIEW_HIDDEN_PARTS = new Set(["helmet", "chest", "back", "waist"', js)

    def test_quest_first_person_hides_base_suit_upper_shell_and_generated_fallback_capsules(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        visibility_method = self._extract_js_class_method(
            js,
            "updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView = false, reveal, bodyShellAligned = true })",
        )
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        fallback_helper = self._extract_js_function(js, "function isGeneratedFallbackArmorMesh")

        for token in {
            'const SELF_VIEW_HIDDEN_BASE_SUIT_PARTS = new Set(["head", "neck", "spine", "shoulder_line", "torso"]);',
            '["neck", "capsule", [0, -0.25, -0.28], [0.055, 0.13, 0.055], [0, 0, 0]],',
        }:
            self.assertIn(token, js)

        self.assertIn('return mesh?.userData?.meshSource === "generated_fallback";', fallback_helper)
        self.assertIn('const baseSuitPart = mesh.userData?.baseSuitPart || "";', visibility_method)
        self.assertIn("SELF_VIEW_HIDDEN_BASE_SUIT_PARTS.has(baseSuitPart)", visibility_method)
        self.assertIn("mesh.visible = this.baseSuitGroup.visible && !hiddenForSelfView;", visibility_method)
        self.assertNotIn("mesh.position.y > -0.22", visibility_method)

        self.assertIn("|| (!standbyPreview && isGeneratedFallbackArmorMesh(mesh))", update_scene)
        self.assertIn("this.applyStandbySuitPose(mesh, part);", update_scene)

    def test_quest_first_person_base_suit_mask_keeps_mirror_and_armor_stand_guides(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        visibility_method = self._extract_js_class_method(
            js,
            "updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView = false, reveal, bodyShellAligned = true })",
        )
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")

        self.assertIn(
            "xrCapsuleGuide && this.world.session && this.playing && !standbyPreview && bodyShellAligned && (selfView || mirrorView);",
            visibility_method,
        )
        self.assertIn("const armorStandBodyGuide = standbyPreview;", visibility_method)
        self.assertIn("const canShowBodyShell = armorStandBodyGuide || (!this.world.session && bodyShellAligned) || xrTransformGuide;", visibility_method)
        self._assert_tokens_in_order(
            visibility_method,
            [
                "const hiddenForSelfView =",
                "selfView",
                "&& !standbyPreview",
                "&& SELF_VIEW_HIDDEN_BASE_SUIT_PARTS.has(baseSuitPart);",
                "mesh.visible = this.baseSuitGroup.visible && !hiddenForSelfView;",
            ],
        )
        self.assertIn("const mirrorView = inXr && this.xrViewMode === XR_VIEW_MODE_MIRROR;", update_scene)
        self.assertIn("this.updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView, reveal, bodyShellAligned });", update_scene)
        self.assertNotIn("mirrorView && SELF_VIEW_HIDDEN_BASE_SUIT_PARTS", visibility_method)

    def test_quest_vrm_base_suit_spike_documents_no_raw_first_person_vrm_cutover(self) -> None:
        doc = (self.repo_root / "docs" / "quest-vrm-base-suit-spike-2026-05-05.md").read_text(encoding="utf-8")

        for token in {
            "Quest VRM Base Suit Spike - 2026-05-05",
            "Decision: do not wire VRM into quest-demo.js in this spike.",
            "`viewer/assets/vrm/default.vrm` exists",
            "`@pixiv/three-vrm is not in package.json`",
            "`Face` and `Body` are SkinnedMesh nodes",
            "first-person rule: never render VRM head/neck.",
            "Hide base-suit `head`, `neck`, `spine`, `shoulder_line`, and `torso` in self view.",
            "A contract test prevents loading raw VRM as first-person body shell without a head/neck mask.",
        }:
            with self.subTest(token=token):
                self.assertIn(token, doc)

    def test_quest_viewer_does_not_raw_load_vrm_until_head_neck_mask_adapter_exists(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        package_json = (self.repo_root / "package.json").read_text(encoding="utf-8")

        self.assertNotIn("@pixiv/three-vrm", package_json)
        self.assertNotIn("@pixiv/three-vrm", js)
        self.assertNotIn("VRMLoader", js)
        self.assertNotIn("default.vrm", js)
        self.assertNotIn("loadGlbGeometry(normalizePath(suitspec?.body_profile?.vrm_baseline_ref", js)
        for token in {
            "function resolveBaseSuitVrmAssetRef(suitspec, suitRecord = null)",
            "this.refreshBaseSuitVrmContractStatus();",
            "this.baseSuitVrmStatus = VRM_BASE_SUIT_STATUS_DISABLED;",
            'this.baseSuitVrmFallbackReason = "raw_vrm_disabled_until_head_neck_mask_adapter";',
            "vrm: {",
            "status: this.baseSuitVrmStatus",
            "assetRef: this.baseSuitVrmAssetRef",
            "fallbackReason: this.baseSuitVrmFallbackReason",
        }:
            self.assertIn(token, js)

    def test_quest_vrm_base_suit_adapter_acceptance_contract_is_documented(self) -> None:
        doc = (self.repo_root / "docs" / "quest-vrm-base-suit-adapter-plan-2026-05-05.md").read_text(encoding="utf-8")

        for token in {
            "Quest VRM Base Suit Adapter Plan - 2026-05-05",
            "Self view must never render VRM head, neck, face, hair, eyes, or helmet-equivalent geometry.",
            "Mirror view must show a readable human guide, including head and neck",
            "Armor stand view must show a full human guide, including head and neck",
            'setBaseSuitAvatarMode("self" | "mirror" | "armor_stand")',
            "firstPersonHeadNeckVisible: false",
            'coordinateSpace: "quest_rig_local_y_up_z_back"',
            "Bone visibility alone is not an accepted mask.",
            "Armor GLB parts continue to use `runtime_placement`.",
            "Runtime placement offsets still pass through `runtimePlacementOffsetArrayForPart`.",
            "Runtime placement rotations still pass through `applyRuntimePlacementRotation`.",
            "Do not raw-load `viewer/assets/vrm/default.vrm` into first-person Quest rendering.",
        }:
            with self.subTest(token=token):
                self.assertIn(token, doc)

    def test_quest_vrm_base_suit_implementation_review_covers_load_mask_and_fallback_traps(self) -> None:
        doc = (self.repo_root / "docs" / "quest-vrm-base-suit-adapter-plan-2026-05-05.md").read_text(encoding="utf-8")

        for token in {
            "## Implementation Review Findings",
            "Current `package.json` does not include a VRM semantic loader.",
            "Resolve the asset ref from `suitspec.body_profile.vrm_baseline_ref` first",
            "Add the adapter root under the same rig space used by the procedural `baseSuitGroup`.",
            "Drive visibility only through `updateBaseSuitVisibility()`.",
            "A hidden head bone is not enough when the face/body surface is one SkinnedMesh.",
            "A clipped head that still writes depth can block armor and particles even if visually transparent.",
            "Do not treat VRM load failure as \"no base suit\"; fall back to the procedural guide.",
            "Do not let adapter errors leave stale visible VRM nodes after `hideLoadedArmorMeshes()`.",
            "Do not let fallback state change GLB armor `mesh.userData.runtimePlacement`.",
            "Browser/Quest QA includes self, mirror, and armor-stand captures.",
        }:
            with self.subTest(token=token):
                self.assertIn(token, doc)

    def test_quest_viewer_recall_success_idle_does_not_force_standby_armor(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        standby_expr = self._extract_js_const_expression(update_scene, "standbyPreview")

        self.assertIn("const standbyPreview =", update_scene)
        self.assertNotIn("!this.playing", standby_expr)
        self.assertNotIn("|| !hasRuntimePose", standby_expr)
        self.assertNotIn("mesh.visible = standbyPreview || mesh.material.opacity > 0.09;", update_scene)
        self.assertIn("mesh.visible = false;", update_scene)

    def test_quest_viewer_hides_loaded_armor_until_preview_or_transform(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        load_method = self._extract_js_class_method(js, "async loadArmorMeshes()")
        recall_method = self._extract_js_class_method(js, "async loadSuitByRecallCode(code, { reloadMeshes = false, pushUrl = false } = {})")
        hide_method = self._extract_js_class_method(js, "hideLoadedArmorMeshes()")

        self.assertIn("this.hideLoadedArmorMeshes();", load_method)
        self.assertIn("this.hideLoadedArmorMeshes();", recall_method)
        self.assertIn("for (const mesh of this.meshes.values()) mesh.visible = false;", hide_method)
        self.assertIn("this.baseSuitGroup.visible = false;", hide_method)

    def test_quest_viewer_standby_armor_is_limited_to_stand_or_preview_mode(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        standby_expr = self._extract_js_const_expression(update_scene, "standbyPreview")

        allowed_preview_gates = (
            "this.armorStandMode",
            "this.previewMode",
            "this.xrStandbyPreviewEnabled",
            "this.isArmorStandPreviewMode()",
            "this.isStandbyPreviewMode()",
        )
        self.assertTrue(
            any(token in standby_expr for token in allowed_preview_gates),
            standby_expr,
        )
        self.assertIn("this.applyStandbySuitPose(mesh, part);", update_scene)
        self.assertNotIn("this.meshes.size > 0 && (!this.playing", standby_expr)

    def test_quest_viewer_audio_or_active_henshin_may_show_armor(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        run_voice = self._extract_js_class_method(js, "async runVoiceCommand()")
        replay_method = self._extract_js_class_method(js, "replayFromStart({ speak, audio = speak, viewMode = XR_VIEW_MODE_SELF, source = \"voice\" })")

        self.assertIn("this.playing = true;", replay_method)
        self.assertIn("source: \"voice\"", run_voice)
        self._assert_tokens_in_order(
            update_scene,
            [
                "const liveBodyPose = useQuestLiveBodyPose();",
                "const fixedBodyPose = inXr && !liveBodyPose && !mocopiSegmentPose;",
                "const useLiveSuit = liveBodyPose && selfView && this.xrWorldAnchorReady;",
                "const useReplayMotion = !hasSegmentPose && replayMotionFrame;",
                "this.applyLiveSuitPose(mesh, part, reveal);",
                "this.applyMotionSuitPose(mesh, part, replayMotionFrame, reveal, { centered: bodyShellAligned });",
                "mesh.visible =",
            ],
        )
        self.assertIn("this.playing", update_scene)
        self.assertIn("this.playbackSource", update_scene)

    def test_quest_viewer_does_not_mix_segment_and_replay_motion_sources_per_part(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")

        self._assert_tokens_in_order(
            update_scene,
            [
                "const segments = frame?.segments || {};",
                "const hasSegmentPose = Object.keys(segments).length > 0;",
                "const replayMotionFrame = this.currentReplayMotionFrame(this.elapsed);",
                "const hasRuntimePose = useLiveSuit || hasSegmentPose || Boolean(replayMotionFrame);",
                "const pose = segments[segmentName];",
                "const useReplayMotion = !hasSegmentPose && replayMotionFrame;",
            ],
        )
        self.assertNotIn("const useReplayMotion = !pose && replayMotionFrame;", update_scene)

    def test_quest_spatial_view_button_recovers_from_stand_to_mirror_replay(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        activate_hovered = self._extract_js_class_method(js, "activateHovered()")
        mirror_method = self._extract_js_class_method(js, "activateMirrorOrToggleArchiveView()")

        self.assertIn('if (action === "view") this.demo.activateMirrorOrToggleArchiveView();', activate_hovered)
        for token in {
            "const leavingStandOrObserver =",
            "this.armorStandPreview || (this.world.session && this.xrViewMode === XR_VIEW_MODE_OBSERVER && !this.playing);",
            "this.archiveViewMode = XR_VIEW_MODE_MIRROR;",
            'this.replayFromStart({ speak: true, viewMode: XR_VIEW_MODE_MIRROR, source: "archive" });',
            "this.setArmorStandPreview(false);",
            "this.captureWorldAnchor(this.xrViewMode);",
        }:
            self.assertIn(token, mirror_method)

    def test_xr_observer_replay_hides_static_base_shell_unless_shell_aligned(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        visibility_method = self._extract_js_class_method(
            js,
            "updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView = false, reveal, bodyShellAligned = true })",
        )

        self.assertIn("const bodyShellAligned = fixedBodyPose || (selfView && !mocopiSegmentPose) || (!inXr && !mocopiSegmentPose);", update_scene)
        self.assertIn("this.updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView, reveal, bodyShellAligned });", update_scene)
        self.assertIn(
            "xrCapsuleGuide && this.world.session && this.playing && !standbyPreview && bodyShellAligned && (selfView || mirrorView);",
            visibility_method,
        )
        self.assertIn("const xrCapsuleGuide = useQuestBaseSuitGuide();", visibility_method)
        self.assertIn(
            "const armorStandBodyGuide = standbyPreview;",
            visibility_method,
        )
        self.assertIn(
            "const canShowBodyShell = armorStandBodyGuide || (!this.world.session && bodyShellAligned) || xrTransformGuide;",
            visibility_method,
        )
        self.assertIn("this.applyBaseSuitGuidePose({ standbyPreview });", visibility_method)
        self.assertNotIn("const canShowBodyShell = standbyPreview || bodyShellAligned;", visibility_method)
        self.assertIn("this.baseSuitGroup.visible = hasSuit && canShowBodyShell && (standbyPreview || this.playing);", visibility_method)

    def test_quest_live_mirror_does_not_apply_rig_local_live_pose_to_scene_mirror_meshes(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        live_mirror = self._extract_js_class_method(
            js,
            "updateLiveMirrorAvatar(progress, reveal, { liveBodyPose = useQuestLiveBodyPose() } = {})",
        )

        self.assertIn("&& liveBodyPose", live_mirror)
        self.assertIn("this.applyLiveMirrorSuitPose(mesh, part, reveal);", live_mirror)
        self.assertNotIn("this.applyLiveSuitPose(mesh, part, reveal);", live_mirror)

    def test_web_replay_body_sim_armor_aligns_to_body_shell(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        segment_pose = self._extract_js_function(js, "function applySegmentPose")
        motion_pose = self._extract_js_class_method(js, "applyMotionSuitPose(mesh, part, frame, reveal, options = {})")

        self._assert_tokens_in_order(
            update_scene,
            [
                "const inXr = Boolean(this.world.session);",
                "const selfView = inXr && this.xrViewMode === XR_VIEW_MODE_SELF;",
                "const liveBodyPose = useQuestLiveBodyPose();",
                "const fixedBodyPose = inXr && !liveBodyPose && !mocopiSegmentPose;",
                "const bodyShellAligned = fixedBodyPose || (selfView && !mocopiSegmentPose) || (!inXr && !mocopiSegmentPose);",
                "applySegmentPose(mesh, pose, part, reveal, {",
                "centered: bodyShellAligned && !mocopiSegmentPose,",
            ],
        )
        self.assertIn("const bodyPose = questAssemblyPoseForPart(part);", segment_pose)
        self.assertIn("mesh.position.lerpVectors(options.stagePosition, options.finalPosition, fitProgress);", segment_pose)
        self.assertIn("const bodyPose = options.centered ? questAssemblyPoseForPart(part) : null;", motion_pose)
        self.assertIn("mesh.position.fromArray(bodyPose);", motion_pose)
        self.assertIn("const torsoYaw = options.centered ? 0 : Number(frame.torso_yaw || 0);", motion_pose)
        self.assertIn("applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, torsoYaw);", motion_pose)

    def test_web_replay_pose_constants_stay_near_base_suit_shell(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        base_positions = self._extract_js_base_suit_positions(js)
        body_positions = self._extract_js_vector_object(js, "VR_BODY_PART_POSES")
        part_to_base = {
            "helmet": "head",
            "chest": "torso",
            "waist": "pelvis",
            "left_upperarm": "left_upperarm",
            "right_upperarm": "right_upperarm",
            "left_forearm": "left_forearm",
            "right_forearm": "right_forearm",
            "left_thigh": "left_thigh",
            "right_thigh": "right_thigh",
            "left_shin": "left_shin",
            "right_shin": "right_shin",
        }

        for part, base_part in part_to_base.items():
            with self.subTest(part=part, base_part=base_part):
                armor = body_positions[part]
                shell = base_positions[base_part]
                delta = [armor[index] - shell[index] for index in range(3)]
                self.assertLessEqual(abs(delta[0]), 0.12, delta)
                self.assertLessEqual(abs(delta[1]), 0.18, delta)
                self.assertLessEqual(abs(delta[2]), 0.12, delta)
                self.assertLessEqual(sum(value * value for value in delta) ** 0.5, 0.22, delta)

    def test_trial_replay_generation_retries_transient_proxy_failures(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        get_json = self._extract_js_function(js, "async function getJson")
        generate_replay = self._extract_js_class_method(js, "async generateTrialReplay()")

        self.assertIn("const attempts = Math.max(1, Number(options.attempts || 1));", get_json)
        self.assertIn("const retriable = status >= 500 || error instanceof TypeError;", get_json)
        self.assertIn("await sleep(180 * attempt);", get_json)
        self.assertIn('const replay = await getJson(`/v1/trials/${this.trialId}/replay`, { attempts: 3 });', generate_replay)

    def test_quest_viewer_has_lore_deposition_particle_effects(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        update_effects = self._extract_js_class_method(js, "updateDepositionEffects(dt, progress, { active = false, selfView = false, mirrorView = false } = {})")

        for token in {
            "const DEPOSITION_PARTICLE_COUNT =",
            "const DEPOSITION_SPARK_COUNT =",
            "const MIRROR_DEPOSITION_DIMMING = 0.42;",
            "const MIRROR_DEPOSITION_Z = -0.46;",
            "function createDepositionParticleField()",
            "group.name = \"IWSDK-蒸着粒子フィールド\";",
            "points.name = \"蒸着粒子\";",
            "sparks.name = \"蒸着光跡\";",
            "new THREE.Points",
            "new THREE.LineSegments",
            "THREE.AdditiveBlending",
            "this.depositionEffects = createDepositionParticleField();",
        }:
            self.assertIn(token, js)

        self._assert_tokens_in_order(
            update_scene,
            [
                "const canRenderTransformSuit = this.playing && hasRuntimePose;",
                "this.updateLiveMirrorAvatar(progress, reveal, { liveBodyPose });",
                "this.updateDepositionEffects(dt, progress, {",
            ],
        )
        for token in {
            "effects.points.material.opacity",
            "effects.sparks.material.opacity",
            "depositionBodyRadiusAtY(y)",
            "effects.points.geometry.attributes.position.needsUpdate = true;",
            "effects.sparks.geometry.attributes.position.needsUpdate = true;",
        }:
            self.assertIn(token, update_effects)

    def test_quest_xr_mirror_dims_deposition_field_so_mirror_stays_readable(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        update_effects = self._extract_js_class_method(js, "updateDepositionEffects(dt, progress, { active = false, selfView = false, mirrorView = false } = {})")
        telemetry = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        self.assertIn("const mirrorView = inXr && this.xrViewMode === XR_VIEW_MODE_MIRROR;", update_scene)
        self.assertIn("mirrorView,", update_scene)
        self.assertIn("const fieldActive = active && progress > 0.015 && progress < 0.995;", update_effects)
        self.assertIn("const zCenter = mirrorView ? MIRROR_DEPOSITION_Z : selfView ? -0.18 : DEPOSITION_BODY_Z;", update_effects)
        self.assertIn("const mirrorParticleDimming = mirrorView ? MIRROR_DEPOSITION_DIMMING : 1;", update_effects)
        self.assertIn("effects.points.material.opacity = (0.2 + glow * 0.7) * mirrorParticleDimming;", update_effects)
        self.assertIn("effects.sparks.material.opacity = (0.12 + glow * 0.58) * mirrorParticleDimming;", update_effects)
        self.assertIn("depositionEffects:", telemetry)
        self.assertIn("visible: Boolean(this.depositionEffects?.group?.visible)", telemetry)
        self.assertIn("pointsOpacity: roundDebugNumber(this.depositionEffects?.points?.material?.opacity)", telemetry)
        self.assertIn("pointsSize: roundDebugNumber(this.depositionEffects?.points?.material?.size)", telemetry)

    def test_quest_viewer_initial_render_does_not_load_armor_before_recall(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        start_method = self._extract_js_class_method(js, "async start()")
        initial_method = self._extract_js_class_method(js, "async loadInitialSuitSpec()")

        self.assertIn("const loadedRecalledSuit = await this.loadInitialSuitSpec();", start_method)
        self.assertIn("if (loadedRecalledSuit) {", start_method)
        self.assertIn("await this.loadArmorMeshes();", start_method)
        self.assertNotIn("\n    await this.loadArmorMeshes();", start_method)

        self.assertIn("if (useNewRouteApi() && this.recallCode) {", initial_method)
        self.assertIn(
            "return await this.loadSuitByRecallCode(this.recallCode, { reloadMeshes: false, pushUrl: false });",
            initial_method,
        )
        self.assertIn("this.suitspec = null;", initial_method)
        self.assertIn("this.clearArmorMeshes();", initial_method)
        self.assertIn("return false;", initial_method)
        self.assertNotIn("this.suitspec = await loadSuitSpec();", initial_method)
        self.assertNotIn("return this.suitspec;", initial_method)

    def test_quest_viewer_loads_armor_meshes_only_after_successful_recall(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        recall_method = self._extract_js_class_method(js, "async loadSuitByRecallCode(code, { reloadMeshes = false, pushUrl = false } = {})")

        ordered_tokens = [
            "const data = await getJson(`/v1/quest/recall/${encodeURIComponent(recallCode)}`);",
            "if (!data.suitspec) {",
            "if (!data.manifest_id || data.manifest_ready === false) {",
            "this.suitRecord = data.suit || null;",
            "this.suitspec = data.suitspec;",
            "this.recallCode = data.recall_code || recallCode;",
            "if (reloadMeshes) {",
            "this.clearArmorMeshes();",
            "await this.loadArmorMeshes();",
            "this.setRecallCodeState(`",
            "return this.suitspec;",
        ]
        self._assert_tokens_in_order(recall_method, ordered_tokens)

        self.assertNotIn("this.clearArmorMeshes();\n    const data = await getJson", recall_method)
        self.assertEqual(recall_method.count("await this.loadArmorMeshes();"), 1)

    def test_quest_viewer_clear_armor_meshes_is_safe_before_or_after_failed_recall(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        submit_method = self._extract_js_class_method(js, "async submitRecallCodeFromInput()")
        clear_method = self._extract_js_class_method(js, "clearArmorMeshes()")

        self._assert_tokens_in_order(
            submit_method,
            [
                "} catch (error) {",
                "this.clearArmorMeshes();",
                'this.setRecallCodeState(message, "error");',
                'this.setRouteApi("CODE ERROR", "error");',
            ],
        )

        for token in {
            "const disposedGeometries = new Set();",
            "const disposedMaterials = new Set();",
            "for (const mesh of this.meshes.values()) {",
            "disposeObjectResources(mesh, disposedGeometries, disposedMaterials);",
            "mesh.removeFromParent();",
            "this.meshes.clear();",
            "for (const mesh of this.liveMirrorMeshes.values()) {",
            "this.liveMirrorMeshes.clear();",
            "this.refreshEquipmentStatus();",
        }:
            self.assertIn(token, clear_method)

        self.assertNotIn("this.suitspec.modules", clear_method)
        self.assertNotIn("throw new Error", clear_method)

    def test_quest_viewer_uses_runtime_armor_asset_ref_when_available(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        helper = self._extract_js_function(js, "function moduleForRuntimePart")
        load_method = self._extract_js_class_method(js, "async loadArmorMeshes()")

        self._assert_tokens_in_order(
            helper,
            [
                "const source = suitspec?.modules?.[part];",
                "const runtimeAsset = runtimeArmorAsset(runtimePackage, part);",
                "if (runtimeAsset?.asset_ref) module.asset_ref = runtimeAsset.asset_ref;",
                "if (runtimeAsset?.selected_variant_key) module.selected_variant_key = runtimeAsset.selected_variant_key;",
                "return module;",
            ],
        )
        self.assertIn("const modules = this.suitspec?.modules || {};", load_method)
        self.assertIn("const module = moduleForRuntimePart(this.suitspec, this.runtimePackage, part);", load_method)
        self.assertIn("const mesh = await createArmorMesh(part, module, this.suitspec);", load_method)

    def test_physical_quest_runbook_covers_external_exhibition_pc_setup(self) -> None:
        runbook = (self.repo_root / "docs" / "web-quest-runtime-placement-check-2026-05-03.md").read_text(encoding="utf-8")

        for token in {
            "Physical Quest Checklist - External Exhibition PC",
            "same Wi-Fi",
            "USB adb reverse",
            "LAN IP discovery",
            "Windows Firewall prompt",
            "HTTPS/cert",
            "Headset Browser URL",
            "http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1",
            "https://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1",
            "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1",
            "Wrong Port / Wrong URL Recovery",
            "5173",
            "8010",
            "RUNTIME DIAGNOSTIC",
            "[Quest runtime diagnostic]",
        }:
            self.assertIn(token, runbook)

    def _assert_renderable_module(self, part: str, module: dict) -> None:
        self.assertTrue(REQUIRED_MODULE_KEYS.issubset(module.keys()), part)
        self.assertIsInstance(module["asset_ref"], str)
        self.assertTrue(
            module["asset_ref"].endswith(f"{part}.mesh.json")
            or module["asset_ref"].endswith(f"{part}.glb")
            or (
                f"viewer/assets/armor-parts/{part}/variants/" in module["asset_ref"]
                and module["asset_ref"].endswith(".glb")
            ),
            module["asset_ref"],
        )
        self.assertIsInstance(module["fit"], dict)
        self.assertTrue(REQUIRED_FIT_KEYS.issubset(module["fit"].keys()), module["fit"])
        self.assertIsInstance(module["vrm_anchor"], dict)
        self.assertIsInstance(module["vrm_anchor"].get("bone"), str)
        self.assertTrue(module["vrm_anchor"]["bone"])

    def _assert_mesh_asset_can_load(self, asset_ref: str) -> None:
        path = (self.repo_root / asset_ref).resolve()
        self.assertTrue(path.is_file(), asset_ref)
        if asset_ref.endswith(".glb"):
            data = path.read_bytes()
            self.assertGreaterEqual(len(data), 20, asset_ref)
            magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
            self.assertEqual(magic, b"glTF", asset_ref)
            self.assertEqual(version, 2, asset_ref)
            self.assertEqual(declared_length, len(data), asset_ref)
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["format"], "mesh.v1")
        self.assertGreaterEqual(len(payload.get("positions") or []), 9)

    def _extract_js_class_method(self, js: str, signature: str) -> str:
        start = js.find(f"  {signature}")
        self.assertNotEqual(start, -1, signature)
        next_method = re.search(r"\n  (?:async\s+)?[A-Za-z_$][\w$]*\(", js[start + 1 :])
        if next_method:
            return js[start : start + 1 + next_method.start()]
        return js[start:]

    def _extract_js_class_method_by_name(self, js: str, name: str) -> str:
        match = re.search(rf"\n  (?:async\s+)?{re.escape(name)}\(", js)
        self.assertIsNotNone(match, name)
        assert match is not None
        start = match.start() + 1
        next_method = re.search(r"\n  (?:async\s+)?[A-Za-z_$][\w$]*\(", js[start + 1 :])
        if next_method:
            return js[start : start + 1 + next_method.start()]
        return js[start:]

    def _extract_js_function(self, js: str, signature: str) -> str:
        start = js.find(signature)
        self.assertNotEqual(start, -1, signature)
        next_function = re.search(r"\nfunction\s+[A-Za-z_$][\w$]*\(", js[start + 1 :])
        if next_function:
            return js[start : start + 1 + next_function.start()]
        return js[start:]

    def _extract_js_const_expression(self, text: str, name: str) -> str:
        match = re.search(rf"\bconst\s+{re.escape(name)}\s*=\s*(.*?);", text, re.DOTALL)
        self.assertIsNotNone(match, name)
        assert match is not None
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _extract_js_vector_object(self, js: str, name: str) -> dict[str, list[float]]:
        match = re.search(rf"\bconst\s+{re.escape(name)}\s*=\s*\{{(.*?)\n\}};", js, re.DOTALL)
        self.assertIsNotNone(match, name)
        assert match is not None
        return {
            key: [float(value.strip()) for value in raw_values.split(",")]
            for key, raw_values in re.findall(r"\b([A-Za-z0-9_]+):\s*\[([^\]]+)\]", match.group(1))
        }

    def _extract_js_base_suit_positions(self, js: str) -> dict[str, list[float]]:
        match = re.search(r"\bconst\s+BASE_SUIT_SURFACE_PARTS\s*=\s*\[(.*?)\n\];", js, re.DOTALL)
        self.assertIsNotNone(match, "BASE_SUIT_SURFACE_PARTS")
        assert match is not None
        return {
            key: [float(value.strip()) for value in raw_values.split(",")]
            for key, raw_values in re.findall(r'\["([^"]+)",\s*"[^"]+",\s*\[([^\]]+)\]', match.group(1))
        }

    def _assert_tokens_in_order(self, text: str, tokens: list[str]) -> None:
        offset = 0
        for token in tokens:
            index = text.find(token, offset)
            self.assertNotEqual(index, -1, token)
            offset = index + len(token)


if __name__ == "__main__":
    unittest.main()
