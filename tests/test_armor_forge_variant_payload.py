import tempfile
import unittest
from pathlib import Path

from henshin.dashboard_server import DashboardHandler


class TestArmorForgeVariantPayload(unittest.TestCase):
    def test_forge_js_posts_selected_variant_keys_from_part_variant_selects(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        render_block = js[js.index("function renderPartGrid()") : js.index("\n\nfunction syncPreviewLegendPalette")]
        self.assertIn('querySelectorAll("select[data-part-variant]")', render_block)
        self.assertIn('const variantSelect = document.createElement("select");', render_block)
        self.assertIn("variantSelect.dataset.partVariant = id;", render_block)
        self.assertIn("autoOption.value = AUTO_VARIANT_VALUE;", render_block)
        self.assertIn("variantSelect.value = variants.includes(preferred) ? preferred : AUTO_VARIANT_VALUE;", render_block)
        self.assertIn("manualVariantOverrides.add(id);", render_block)
        self.assertIn("applyVariantOverrideToPreview(id, variantSelect.value)", render_block)

        payload_block = js[js.index("function formPayload()") : js.index("\n\nfunction questViewerUrl")]
        self.assertIn("const selected_variant_keys = selectedVariantMap({ explicitOnly: true });", payload_block)
        self.assertIn("parts: selectedParts(),", payload_block)
        self.assertIn('variant_selection_mode: "auto"', payload_block)
        self.assertIn("selected_variant_keys,", payload_block)
        self.assertIn("selected_variants: selectedVariantRecords({ explicitOnly: true }),", payload_block)

        submit_block = js[js.index("async function submitForge(event)") : js.index("\n\napplyExhibitionModePreference();")]
        self.assertIn('fetchJson("/v1/suits/forge"', submit_block)
        self.assertIn("body: JSON.stringify(formPayload()),", submit_block)

    def test_manual_variant_preview_disables_stale_quest_link(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        preview_block = js[js.index("async function applyVariantOverrideToPreview") : js.index("\n\nfunction syncVariantSelectsFromForgeData")]
        stale_block = js[js.index("function markQuestLinkStaleForPreview") : js.index("\n\nfunction assertForgeReadiness")]

        self.assertIn("markQuestLinkStaleForPreview", preview_block)
        self.assertIn('UI.questLink.classList.add("disabled");', stale_block)
        self.assertIn('UI.questLink.textContent = "再生成してQuestへ";', stale_block)
        self.assertIn('UI.questLink.dataset.stalePreview = "true";', stale_block)
        self.assertIn('UI.questLink.setAttribute("aria-disabled", "true");', stale_block)
        self.assertIn('UI.questUrl.value = "再生成後に表示";', stale_block)

    def test_forge_preview_prefers_runtime_render_placements(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        self.assertIn("function runtimePlacementForPreviewPart(part, module = {})", js)
        self.assertIn("latestForgeData?.preview?.render_placements?.[part]", js)
        self.assertIn("latestForgeData?.asset_pipeline?.render_placements?.[part]", js)
        self.assertIn("function variantRuntimePlacementForPreviewPart(part, variantKey, assetRef = \"\", module = {})", js)
        self.assertIn("latestForgeData?.preview?.variant_render_placements", js)
        self.assertIn("latestForgeData?.asset_pipeline?.variant_render_placements", js)
        self.assertIn("function runtimePlacementMatchesPreviewVariant(part, placement, variantKey = \"\", assetRef = \"\")", js)
        self.assertIn("function runtimeTargetSizeForPreviewPart(part, module = {})", js)
        # Clamped surface offsets are resolved by the shared runtime placement
        # resolver in web-preview-parity mode; pin the delegation plus the
        # shared implementation that reads the clamped fields.
        self.assertIn("resolveRuntimeOffset,", js)
        resolver = Path("viewer/shared/runtime-placement-resolver.js").read_text(encoding="utf-8")
        self.assertIn("vectorArrayFromRuntimeRecord(placement?.surface_offset_clamped_m)", resolver)
        self.assertIn("vectorArrayFromRuntimeRecord(placement?.surface_anchor?.offset_clamped_m)", resolver)
        self.assertIn("function runtimeOffsetForPreviewPart(part, module = {})", js)
        self.assertIn("function runtimeRotationForPreviewPart(part, module = {})", js)

        target_size_block = js[js.index("targetSizeForPart(part, module, metrics)") : js.index("\n  targetCenterForPart")]
        self.assertIn("const runtimeTarget = runtimeTargetSizeForPreviewPart(part, module);", target_size_block)
        self.assertIn("if (runtimeTarget) return runtimeTarget;", target_size_block)

        pose_block = js[js.index("targetCenterForPart(part, module, metrics)") : js.index("\n  enforceWornCenterForPart")]
        self.assertIn("const placementOffset = runtimeOffsetForPreviewPart(part, module)", pose_block)

        vrm_pose_block = js[js.index("vrmPoseFor(part, module, mesh)") : js.index("\n  applyPreviewPose")]
        self.assertIn("const runtimeRotation = runtimeRotationForPreviewPart(part, module);", vrm_pose_block)
        self.assertIn("runtimePlacementSource", vrm_pose_block)

    def test_manual_variant_preview_replaces_or_clears_runtime_placement(self) -> None:
        js = Path("viewer/armor-forge/forge.js").read_text(encoding="utf-8")

        runtime_block = js[js.index("function runtimePlacementForPreviewPart") : js.index("\n\nfunction vector3FromRuntimeVector")]
        self.assertIn("const variantPlacement = variantRuntimePlacementForPreviewPart(part, selectedKey, selectedAssetRef, module);", runtime_block)
        self.assertIn("if (variantPlacement) return variantPlacement;", runtime_block)
        self.assertIn("runtimePlacementMatchesPreviewVariant(part, placement, selectedKey, selectedAssetRef)", runtime_block)

        setter_block = js[js.index("function setRuntimePlacementForPreviewPart") : js.index("\n\nfunction vector3FromRuntimeVector")]
        self.assertIn("module.runtime_placement = { ...placement };", setter_block)
        self.assertIn("delete module.runtime_placement;", setter_block)
        self.assertIn("writeRuntimePlacementForPart(latestForgeData?.preview?.render_placements, part, placement);", setter_block)
        self.assertIn("writeRuntimePlacementForPart(latestForgeData?.asset_pipeline?.render_placements, part, placement);", setter_block)

        switch_block = js[js.index("function setPreviewModuleVariant") : js.index("\n\nasync function applyVariantOverrideToPreview")]
        self.assertIn("const placement = variantRuntimePlacementForPreviewPart(part, key, assetRef, module);", switch_block)
        self.assertIn("setRuntimePlacementForPreviewPart(part, placement);", switch_block)

    def test_forge_api_returns_selected_variant_key_and_asset_ref_for_requested_variants(self) -> None:
        root = Path(".").resolve()
        selected_variant_keys = {
            "helmet": "helmet:crest_guardian",
            "chest": "chest:split_rib",
            "back": "back:rear_core",
        }
        expected_asset_refs = {
            "helmet": "viewer/assets/armor-parts/helmet/variants/crest_guardian/helmet__crest_guardian.glb",
            "chest": "viewer/assets/armor-parts/chest/variants/split_rib/chest__split_rib.glb",
            "back": "viewer/assets/armor-parts/back/variants/rear_core/back__rear_core.glb",
        }

        tmp_dir = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(tmp_dir.cleanup)
        tmp = tmp_dir.name
        response = DashboardHandler._new_route_post_response_for_test(
            root,
            "/v1/suits/forge",
            {
                "display_name": "Variant Smoke",
                "parts": sorted(selected_variant_keys),
                "selected_variant_keys": selected_variant_keys,
            },
            suit_store_root=Path(tmp) / "suits",
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 201, response.body)
        body = response.body
        armor_overlay = body["visual_layers"]["armor_overlay"]
        preview_overlay = body["preview"]["visual_layers"]["armor_overlay"]
        preview_modules = body["preview"]["modules"]
        preview_placements = body["preview"]["render_placements"]
        preview_variant_placements = body["preview"]["variant_render_placements"]
        asset_pipeline_placements = body["asset_pipeline"]["render_placements"]
        asset_pipeline_variant_placements = body["asset_pipeline"]["variant_render_placements"]
        variant_catalog_modules = body["asset_pipeline"]["variant_catalog"]["selected_modules"]

        self.assertEqual(armor_overlay["selected_variant_keys"], selected_variant_keys)
        self.assertEqual(armor_overlay["asset_refs"], expected_asset_refs)
        self.assertEqual(body["asset_pipeline"]["render_contract"]["render_placement_contract"], "runtime-render-placement.v1")
        self.assertEqual(body["asset_pipeline"]["render_contract"]["variant_render_placement_contract"], "runtime-render-placement.v1")
        self.assertIn("helmet:heroic_face", preview_variant_placements["helmet"])
        for part, selected_key in selected_variant_keys.items():
            with self.subTest(part=part):
                expected_ref = expected_asset_refs[part]
                self.assertEqual(preview_modules[part]["selected_variant_key"], selected_key)
                self.assertEqual(preview_modules[part]["asset_ref"], expected_ref)
                self.assertEqual(preview_modules[part]["runtime_placement"]["selected_variant_key"], selected_key)
                self.assertEqual(preview_modules[part]["runtime_placement"]["asset_ref"], expected_ref)
                self.assertEqual(preview_modules[part]["runtime_placement"]["contract_version"], "runtime-render-placement.v1")
                self.assertIn("target_size_array_m", preview_modules[part]["runtime_placement"])
                self.assertIn("offset_m", preview_modules[part]["runtime_placement"])
                self.assertIn("rotation_deg", preview_modules[part]["runtime_placement"])
                self.assertEqual(preview_placements[part]["selected_variant_key"], selected_key)
                self.assertEqual(asset_pipeline_placements[part]["selected_variant_key"], selected_key)
                self.assertEqual(preview_overlay["render_placements"][part]["selected_variant_key"], selected_key)
                self.assertEqual(preview_modules[part]["variant_render_placements"][selected_key]["selected_variant_key"], selected_key)
                self.assertEqual(preview_modules[part]["variant_render_placements"][selected_key]["asset_ref"], expected_ref)
                self.assertEqual(preview_variant_placements[part][selected_key]["asset_ref"], expected_ref)
                self.assertEqual(asset_pipeline_variant_placements[part][selected_key]["asset_ref"], expected_ref)
                self.assertEqual(preview_overlay["variant_render_placements"][part][selected_key]["asset_ref"], expected_ref)
                self.assertEqual(armor_overlay["assets"][part]["selected_variant_key"], selected_key)
                self.assertEqual(armor_overlay["assets"][part]["asset_ref"], expected_ref)
                self.assertEqual(armor_overlay["assets"][part]["asset_kind"], "variant_glb")
                self.assertEqual(variant_catalog_modules[part]["selected_variant_key"], selected_key)
                self.assertEqual(variant_catalog_modules[part]["asset_ref"], expected_ref)

        recall = DashboardHandler._new_route_response_for_test(
            root,
            f"/v1/quest/recall/{body['recall_code']}",
            suit_store_root=Path(tmp) / "suits",
        )
        self.assertIsNotNone(recall)
        assert recall is not None
        runtime_assets = recall.body["runtime_package"]["visual_layers"]["armor_overlay"]["assets"]
        runtime_placements = recall.body["runtime_package"]["render_placements"]
        recall_assets = recall.body["visual_layers"]["armor_overlay"]["assets"]
        for part, selected_key in selected_variant_keys.items():
            with self.subTest(recall_part=part):
                self.assertEqual(runtime_assets[part]["selected_variant_key"], selected_key)
                self.assertEqual(runtime_assets[part]["asset_ref"], expected_asset_refs[part])
                self.assertEqual(runtime_placements[part]["selected_variant_key"], selected_key)
                self.assertEqual(runtime_placements[part]["asset_ref"], expected_asset_refs[part])
                self.assertEqual(recall_assets[part]["selected_variant_key"], selected_key)
                self.assertEqual(recall_assets[part]["asset_ref"], expected_asset_refs[part])

    def test_forge_api_auto_selects_variants_and_passes_them_to_texture_payload(self) -> None:
        root = Path(".").resolve()

        with tempfile.TemporaryDirectory(dir=root) as tmp:
            response = DashboardHandler._new_route_post_response_for_test(
                root,
                "/v1/suits/forge",
                {
                    "display_name": "Sky Guard",
                    "parts": ["helmet", "chest", "left_shoulder"],
                    "archetype": "市民",
                    "temperament": "大胆",
                    "brief": "wing flight sky guardian hero suit",
                    "variant_selection_mode": "auto",
                },
                suit_store_root=Path(tmp) / "suits",
            )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 201, response.body)
        body = response.body
        preview_modules = body["preview"]["modules"]
        texture_payload = body["asset_pipeline"]["texture_probe_job"]["payload"]
        variant_selection = body["asset_pipeline"]["job_defaults"]["variant_selection"]

        self.assertEqual(variant_selection["llm_provider"], "local_rule")
        self.assertEqual(variant_selection["provider_status"], "local_rule_active")
        self.assertEqual(preview_modules["chest"]["selected_variant_key"], "chest:broad_guard")
        self.assertTrue(preview_modules["left_shoulder"]["selected_variant_key"].startswith("left_shoulder:"))
        self.assertNotEqual(preview_modules["left_shoulder"]["selected_variant_key"], "left_shoulder:base")
        self.assertIn("/variants/broad_guard/", preview_modules["chest"]["asset_ref"])
        self.assertIn("/variants/", preview_modules["left_shoulder"]["asset_ref"])
        self.assertEqual(texture_payload["selected_variant_keys"]["chest"], "chest:broad_guard")
        self.assertEqual(
            texture_payload["selected_variant_keys"]["left_shoulder"],
            preview_modules["left_shoulder"]["selected_variant_key"],
        )
        self.assertEqual(texture_payload["variant_selection"]["llm_provider"], "local_rule")


if __name__ == "__main__":
    unittest.main()
