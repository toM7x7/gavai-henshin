import json
import struct
import tempfile
import unittest
from pathlib import Path

from henshin.new_route_api import NewRouteApi


RECALL_CODE_0076 = "0076"
FORGE_PARTS = ["helmet", "chest", "back", "waist", "left_forearm", "right_forearm"]
REQUIRED_MODULE_KEYS = {"asset_ref", "fit", "vrm_anchor", "attachment_slot"}
REQUIRED_FIT_KEYS = {"source", "attach", "scale", "minScale"}


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
            "GLTFLoader",
            "function isGlbAssetPath(assetPath)",
            "function loadGlbGeometry(assetPath)",
            "GLB mesh fallback",
            "this.baseSuitGroup = new THREE.Group();",
            "this.refreshBaseSuitSurface();",
            "updateBaseSuitVisibility({ standbyPreview, selfView, reveal })",
            "const useLiveSuit = selfView && this.xrWorldAnchorReady;",
            "const hasRuntimePose = useLiveSuit || Object.keys(segments).length > 0 || Boolean(replayMotionFrame);",
            "const standbyPreview = this.meshes.size > 0 && (!this.playing || !hasRuntimePose);",
            "this.updateBaseSuitVisibility({ standbyPreview, selfView, reveal });",
            "const useReplayMotion = !pose && replayMotionFrame;",
            "this.applyStandbySuitPose(mesh, part);",
            "this.applyMotionSuitPose(mesh, part, replayMotionFrame, reveal);",
            "this.applyLiveSuitPose(mesh, part, reveal);",
            "} else if (!useLiveSuit && !pose && !useReplayMotion) {",
            "mesh.material.opacity = standbyPreview ? 0.82",
            "mesh.visible = standbyPreview || mesh.material.opacity > 0.09;",
        }:
            self.assertIn(token, js)

        self.assertIn('const SELF_VIEW_HIDDEN_PARTS = new Set(["helmet", "left_hand", "right_hand"]);', js)
        self.assertIn('const SELF_VIEW_STANDBY_HIDDEN_PARTS = new Set(["helmet"]);', js)
        self.assertNotIn('SELF_VIEW_HIDDEN_PARTS = new Set(["helmet", "chest", "back", "waist"', js)

    def _assert_renderable_module(self, part: str, module: dict) -> None:
        self.assertTrue(REQUIRED_MODULE_KEYS.issubset(module.keys()), part)
        self.assertIsInstance(module["asset_ref"], str)
        self.assertTrue(
            module["asset_ref"].endswith(f"{part}.mesh.json")
            or module["asset_ref"].endswith(f"{part}.glb"),
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


if __name__ == "__main__":
    unittest.main()
