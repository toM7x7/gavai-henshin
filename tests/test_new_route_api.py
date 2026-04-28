import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from henshin.new_route_api import NewRouteApi


class TestNewRouteApi(unittest.TestCase):
    def setUp(self) -> None:
        self.api = NewRouteApi(Path("."))

    def test_health_exposes_phase_contracts(self) -> None:
        response = self.api.get("/health")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["service"], "new-route-api")
        self.assertIn("SuitManifest", response.body["contracts"])

    def test_catalog_parts_returns_seed_catalog(self) -> None:
        response = self.api.get("/v1/catalog/parts")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertTrue(response.body["ok"])
        self.assertEqual(response.body["catalog_id"], "PCAT-VIEWER-SEED-0001")
        self.assertEqual(len(response.body["parts"]), 18)

    def test_get_manifest_returns_sample_manifest(self) -> None:
        response = self.api.get("/v1/manifests/MNF-20260424-SAMP")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["manifest"]["manifest_id"], "MNF-20260424-SAMP")
        self.assertEqual(response.body["manifest"]["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")

    def test_get_manifest_returns_404_for_unknown_manifest(self) -> None:
        response = self.api.get("/v1/manifests/MNF-20260424-NONE")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 404)
        self.assertFalse(response.body["ok"])

    def test_create_suit_saves_suitspec(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            response = api.post("/v1/suits", {"suitspec": suitspec})

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["suit_id"], "VDA-AXIS-OP-00-0001")
            self.assertEqual(response.body["schema_version"], "0.2")
            self.assertTrue((Path(tmp) / "suits" / "VDA-AXIS-OP-00-0001" / "suitspec.json").is_file())
            self.assertEqual(response.body["links"]["manifest"], "/v1/suits/VDA-AXIS-OP-00-0001/manifest")

    def test_issue_suit_id_reserves_named_registry_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits/issue-id", {"series": "axis", "role": "guest", "display_name": "試作鎧A"})
            second = api.post("/v1/suits/issue-id", {"series": "axis", "role": "guest"})
            assert first is not None
            fetched = api.get(f"/v1/suits/code/{first.body['recall_code']}")
            quest = api.get(f"/v1/quest/recall/{first.body['recall_code']}")

            self.assertIsNotNone(second)
            self.assertIsNotNone(fetched)
            self.assertIsNotNone(quest)
            assert second is not None and fetched is not None and quest is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(first.body["suit_id"], "VDA-AXIS-GUEST-00-0001")
            self.assertRegex(first.body["recall_code"], r"^[A-Z0-9]{4}$")
            self.assertEqual(first.body["display_name"], "試作鎧A")
            self.assertEqual(first.body["issue"]["seq"], 1)
            self.assertEqual(first.body["issue"]["recall_code"], first.body["recall_code"])
            self.assertEqual(second.body["suit_id"], "VDA-AXIS-GUEST-00-0002")
            self.assertRegex(second.body["recall_code"], r"^[A-Z0-9]{4}$")
            self.assertEqual(fetched.status, 200)
            self.assertIsNone(fetched.body["suitspec"])
            self.assertEqual(fetched.body["suit"]["metadata"]["display_name"], "試作鎧A")
            self.assertEqual(fetched.body["recall_code"], first.body["recall_code"])
            self.assertEqual(quest.status, 200)
            self.assertFalse(quest.body["suitspec_ready"])
            self.assertFalse(quest.body["manifest_ready"])
            self.assertEqual(quest.body["display_name"], "試作鎧A")
            self.assertNotIn("metadata", quest.body["suit"])

    def test_create_suit_preserves_issue_metadata_and_display_name(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            issued = api.post("/v1/suits/issue-id", {"series": "axis", "role": "op", "display_name": "生成前"})
            assert issued is not None
            response = api.post("/v1/suits", {"suitspec": suitspec, "display_name": "完成鎧"})
            fetched = api.get("/v1/suits/VDA-AXIS-OP-00-0001")
            by_code = api.get(f"/v1/suits/code/{issued.body['recall_code']}")

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            self.assertIsNotNone(by_code)
            assert response is not None and fetched is not None and by_code is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["recall_code"], issued.body["recall_code"])
            self.assertEqual(response.body["suit"]["metadata"]["display_name"], "完成鎧")
            self.assertEqual(response.body["suit"]["metadata"]["issue"]["seq"], 1)
            self.assertEqual(response.body["suit"]["metadata"]["issue"]["recall_code"], issued.body["recall_code"])
            self.assertEqual(fetched.body["suitspec"]["suit_id"], "VDA-AXIS-OP-00-0001")
            self.assertEqual(fetched.body["suit"]["metadata"]["display_name"], "完成鎧")
            self.assertEqual(by_code.body["suit"]["suit_id"], "VDA-AXIS-OP-00-0001")

    def test_create_suit_rejects_duplicate_recall_code_for_other_suit(self) -> None:
        suitspec = self._sample_suitspec()
        other = json.loads(json.dumps(suitspec))
        other["suit_id"] = "VDA-AXIS-OP-00-0002"
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits", {"suitspec": suitspec, "recall_code": "A1B2"})
            second = api.post("/v1/suits", {"suitspec": other, "recall_code": "A1B2"})

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(second.status, 400)

    def test_issue_suit_id_rejects_duplicate_recall_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits/issue-id", {"recall_code": "A1B2"})
            second = api.post("/v1/suits/issue-id", {"recall_code": "A1B2"})

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(second.status, 400)
            self.assertIn("recall_code", second.body["error"])

    def test_recall_code_lookup_tolerates_common_visual_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            issued = api.post("/v1/suits/forge", {"display_name": "Visitor", "recall_code": "535O"})
            quest = api.get("/v1/quest/recall/5350")
            by_code = api.get("/v1/suits/code/5350")
            duplicate = api.post("/v1/suits/issue-id", {"recall_code": "5350"})

            self.assertIsNotNone(issued)
            self.assertIsNotNone(quest)
            self.assertIsNotNone(by_code)
            self.assertIsNotNone(duplicate)
            assert issued is not None and quest is not None and by_code is not None and duplicate is not None
            self.assertEqual(issued.status, 201)
            self.assertEqual(quest.status, 200)
            self.assertEqual(quest.body["recall_code"], "535O")
            self.assertEqual(by_code.status, 200)
            self.assertEqual(by_code.body["recall_code"], "535O")
            self.assertEqual(duplicate.status, 400)

    def test_forge_suit_creates_ready_manifest_and_recall_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            response = api.post(
                "/v1/suits/forge",
                {
                    "display_name": "来場者A",
                    "recall_code": "F9A1",
                    "palette": {"primary": "#112233", "secondary": "#445566", "emissive": "#77CCFF"},
                    "archetype": "city",
                    "temperament": "swift",
                    "height_cm": 182,
                    "brief": "街を守る軽量外装",
                    "parts": ["helmet", "chest", "back", "left_forearm", "right_forearm"],
                },
            )
            quest = api.get("/v1/quest/recall/F9A1")

            self.assertIsNotNone(response)
            self.assertIsNotNone(quest)
            assert response is not None and quest is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["recall_code"], "F9A1")
            self.assertEqual(response.body["status"], "READY")
            self.assertTrue(response.body["readiness"]["suitspec_ready"])
            self.assertTrue(response.body["readiness"]["manifest_ready"])
            self.assertTrue(response.body["readiness"]["model_quality_ready"])
            self.assertFalse(response.body["readiness"]["final_texture_ready"])
            self.assertFalse(response.body["readiness"]["exhibition_ready"])
            self.assertNotIn("suit_id", response.body)
            self.assertNotIn("manifest_id", response.body)
            self.assertNotIn("suitspec", response.body)
            self.assertNotIn("manifest", response.body)
            self.assertEqual(response.body["body_profile"]["height_cm"], 182.0)
            self.assertEqual(response.body["preview"]["body_profile"]["height_cm"], 182.0)
            self.assertEqual(response.body["preview"]["body_profile"]["vrm_baseline_ref"], "viewer/assets/vrm/default.vrm")
            self.assertEqual(response.body["preview"]["palette"]["primary"], "#112233")
            self.assertEqual(response.body["visual_layers"]["contract_version"], "base-suit-overlay.v1")
            self.assertEqual(response.body["visual_layers"]["base_suit"]["kind"], "vrm_body_surface")
            self.assertEqual(response.body["visual_layers"]["base_suit"]["asset_ref"], "viewer/assets/vrm/default.vrm")
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["kind"], "multi_part_mesh_overlay")
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["part_count"], 5)
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["minimum_visible_parts"], 3)
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["body_fit_contract_version"], "armor-body-fit.v1")
            self.assertEqual(response.body["visual_layers"]["surface_layer"]["layer_id"], "surface_materials")
            self.assertEqual(response.body["visual_layers"]["surface_layer"]["kind"], "texture_and_emissive_maps")
            self.assertEqual(
                response.body["visual_layers"]["surface_layer"]["source_layers"],
                ["base_suit_surface", "armor_overlay_parts"],
            )
            self.assertEqual(response.body["visual_layers"]["surface_layer"]["status"], "planned_not_generated")
            self.assertEqual(
                [slot["slot_id"] for slot in response.body["visual_layers"]["armor_overlay"]["body_fit_slots"]],
                ["helmet", "chest", "back", "left_forearm", "right_forearm"],
            )
            self.assertFalse(response.body["render_contract"]["vrm_only_is_valid"])
            self.assertEqual(response.body["render_contract"]["body_fit_contract_version"], "armor-body-fit.v1")
            self.assertTrue(response.body["render_contract"]["body_fit_core_ready"])
            self.assertTrue(response.body["render_contract"]["body_fit_pairs_balanced"])
            self.assertEqual(
                response.body["render_contract"]["required_layers"],
                ["base_suit_surface", "armor_overlay_parts"],
            )
            self.assertEqual(response.body["render_contract"]["minimum_visible_overlay_parts"], 3)
            self.assertEqual(response.body["render_contract"]["overlay_part_count"], 5)
            self.assertEqual(response.body["render_contract"]["missing_required_overlay_parts"], [])
            self.assertIn("chest", response.body["render_contract"]["required_overlay_parts"])
            self.assertEqual(response.body["asset_pipeline"]["texture_plan"]["provider_profile"], "nano_banana")
            self.assertEqual(response.body["asset_pipeline"]["texture_plan"]["texture_mode"], "mesh_uv")
            self.assertEqual(response.body["asset_pipeline"]["fit_status"], "preview_vrm_bone_metrics")
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["fit_solver"], "web_forge_vrm_bone_metrics_preview")
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["status"], "requires_rebuild")
            self.assertTrue(response.body["asset_pipeline"]["model_plan"]["model_rebuild_required"])
            self.assertFalse(response.body["asset_pipeline"]["model_plan"]["vrm_only_is_valid"])
            self.assertEqual(
                response.body["asset_pipeline"]["model_plan"]["visual_layer_contract"],
                "base-suit-overlay.v1",
            )
            self.assertEqual(
                response.body["asset_pipeline"]["model_plan"]["mesh_source_status"],
                "seed_proxy_requires_vrm_first_rebuild",
            )
            self.assertEqual(
                response.body["asset_pipeline"]["model_plan"]["preview_mesh_role"],
                "fit-check proxy, not final texture target",
            )
            self.assertIn("VRM-first Wave 1", response.body["asset_pipeline"]["model_plan"]["next_model_quality_gate"])
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["model_quality_gate"], "mesh_fit_before_texture_final")
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["model_rebuild_wave"], "Wave 1")
            self.assertIn("waist", response.body["asset_pipeline"]["model_plan"]["model_rebuild_focus_parts"])
            self.assertEqual(response.body["asset_pipeline"]["texture_plan"]["status"], "planned_not_generated")
            self.assertEqual(response.body["asset_pipeline"]["surface_generation_status"], "planned_not_generated")
            self.assertEqual(response.body["asset_pipeline"]["surface_plan"]["contract_version"], "surface-plan.v1")
            self.assertEqual(response.body["asset_pipeline"]["surface_plan"]["layer_id"], "surface_materials")
            self.assertEqual(response.body["asset_pipeline"]["surface_plan"]["style_intent"], "bright_tokusatsu_hero")
            self.assertEqual(
                response.body["asset_pipeline"]["surface_plan"]["source_layers"],
                ["base_suit_surface", "armor_overlay_parts"],
            )
            self.assertEqual(
                response.body["asset_pipeline"]["surface_plan"]["base_suit"]["texture_role"],
                "hero_body_suit_surface",
            )
            self.assertEqual(
                response.body["asset_pipeline"]["surface_plan"]["emissive"]["texture_role"],
                "emissive_line_mask",
            )
            self.assertTrue(response.body["asset_pipeline"]["texture_plan"]["uv_refine"])
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["asset_contract"], "vrm-base-suit+mesh-v1-overlay")
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["body_fit_contract_version"], "armor-body-fit.v1")
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["body_fit_slot_count"], 5)
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["body_fit_contract"]["height_cm"], 182.0)
            self.assertEqual(response.body["asset_pipeline"]["model_quality_gate"], response.body["model_quality_gate"])
            self.assertEqual(response.body["model_quality_gate"]["contract_version"], "model-quality-gate.v1")
            self.assertEqual(response.body["model_quality_gate"]["blocking_gate"], "mesh_fit_before_texture_final")
            self.assertEqual(response.body["model_quality_gate"]["status"], "pass")
            self.assertTrue(response.body["model_quality_gate"]["mesh_assets_ready"])
            self.assertTrue(response.body["model_quality_gate"]["texture_lock_allowed"])
            self.assertEqual(response.body["model_quality_gate"]["bounds_contract_version"], "mesh-bounds.v1")
            self.assertEqual(
                response.body["model_quality_gate"]["required_parts"],
                ["back", "chest", "helmet", "left_forearm", "right_forearm"],
            )
            self.assertEqual(response.body["model_quality_gate"]["reasons"], ["mesh.v1 P0 quality gate passed"])
            self.assertIn("computed_bounds", response.body["model_quality_gate"]["parts"]["helmet"]["metrics"])
            self.assertEqual(response.body["model_quality_gate"]["parts"]["helmet"]["metrics"]["bounds_source"], "sidecar")
            self.assertIn("left_forearm", response.body["asset_pipeline"]["model_plan"]["overlay_parts"])
            self.assertIn("left_forearm", response.body["asset_pipeline"]["job_defaults"]["parts"])
            self.assertEqual(
                response.body["asset_pipeline"]["job_defaults"]["must_render_layers"],
                ["base_suit_surface", "armor_overlay_parts"],
            )
            self.assertEqual(response.body["asset_pipeline"]["job_defaults"]["minimum_visible_overlay_parts"], 3)
            self.assertIn("server_resolved_suitspec_path", response.body["asset_pipeline"]["job_defaults"]["requires"])
            self.assertEqual(response.body["asset_pipeline"]["job_payload_template"]["suitspec"], response.body["preview"]["asset_pipeline"]["job_payload_template"]["suitspec"])
            self.assertTrue(response.body["asset_pipeline"]["job_payload_template"]["suitspec"].endswith("/suitspec.json"))
            self.assertEqual(response.body["asset_pipeline"]["job_payload_template"]["provider_profile"], "nano_banana")
            self.assertEqual(response.body["asset_pipeline"]["job_payload_template"]["texture_mode"], "mesh_uv")
            self.assertTrue(response.body["asset_pipeline"]["job_payload_template"]["update_suitspec"])
            self.assertTrue(response.body["asset_pipeline"]["job_payload_template"]["writes_final_texture"])
            self.assertFalse(response.body["asset_pipeline"]["job_payload_template"]["dry_run"])
            self.assertNotIn("surface_plan", response.body["asset_pipeline"]["job_payload_template"])
            self.assertNotIn("must_render_layers", response.body["asset_pipeline"]["job_payload_template"])
            self.assertNotIn("minimum_visible_overlay_parts", response.body["asset_pipeline"]["job_payload_template"])
            self.assertEqual(response.body["asset_pipeline"]["links"]["create_generation_job"], "/api/generation-jobs")
            self.assertEqual(response.body["asset_pipeline"]["links"]["job_status_template"], "/api/generation-jobs/{job_id}")
            self.assertEqual(response.body["asset_pipeline"]["links"]["job_events_template"], "/api/generation-jobs/{job_id}/events")
            self.assertEqual(response.body["asset_pipeline"]["links"]["job_cancel_template"], "/api/generation-jobs/{job_id}/cancel")
            self.assertEqual(response.body["asset_pipeline"]["expected_status_flow"][0]["status"], "queued")
            self.assertEqual(response.body["asset_pipeline"]["expected_status_flow"][-1]["status"], "cancelled")
            self.assertEqual(response.body["asset_pipeline"]["model_rebuild_job"]["contract_version"], "model-rebuild.v1")
            self.assertEqual(response.body["asset_pipeline"]["model_rebuild_job"]["status"], "required")
            self.assertTrue(response.body["asset_pipeline"]["model_rebuild_job"]["blocking"])
            self.assertEqual(response.body["asset_pipeline"]["model_rebuild_job"]["blocking_gate"], "mesh_fit_before_texture_final")
            self.assertEqual(response.body["asset_pipeline"]["model_rebuild_job"]["quality_gate_status"], "pass")
            self.assertEqual(response.body["asset_pipeline"]["model_rebuild_job"]["wave"], "Wave 1")
            self.assertIn("chest", response.body["asset_pipeline"]["model_rebuild_job"]["parts"])
            self.assertIn("back", response.body["asset_pipeline"]["model_rebuild_job"]["parts"])
            self.assertIn("waist", response.body["asset_pipeline"]["model_rebuild_job"]["parts"])
            self.assertIn("fit-regression", response.body["asset_pipeline"]["model_rebuild_job"]["entrypoint"])
            self.assertIn("fit_regression.canSave == true", response.body["asset_pipeline"]["model_rebuild_job"]["pass_gates"])
            self.assertEqual(response.body["asset_pipeline"]["texture_probe_job"]["contract_version"], "texture-probe.v1")
            self.assertEqual(response.body["asset_pipeline"]["texture_probe_job"]["status"], "ready_for_final_texture_lock")
            self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["blocking"])
            self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["blocked_by_model_quality"])
            self.assertTrue(response.body["asset_pipeline"]["texture_probe_job"]["final_texture_lock_allowed"])
            self.assertTrue(response.body["asset_pipeline"]["texture_probe_job"]["writes_final_texture"])
            self.assertTrue(response.body["asset_pipeline"]["texture_probe_job"]["payload"]["writes_final_texture"])
            self.assertEqual(response.body["asset_pipeline"]["texture_probe_job"]["method"], "POST")
            self.assertEqual(response.body["asset_pipeline"]["texture_probe_job"]["endpoint"], "/api/generation-jobs")
            self.assertEqual(
                response.body["asset_pipeline"]["texture_probe_job"]["render_contract"],
                response.body["render_contract"],
            )
            self.assertEqual(
                response.body["asset_pipeline"]["texture_probe_job"]["payload"],
                response.body["asset_pipeline"]["job_payload_template"],
            )
            self.assertEqual(response.body["asset_pipeline"]["generation_job"]["method"], "POST")
            self.assertEqual(response.body["asset_pipeline"]["generation_job"]["alias_of"], "texture_probe_job")
            self.assertTrue(response.body["asset_pipeline"]["generation_job"]["deprecated_for_public_ui"])
            self.assertEqual(response.body["asset_pipeline"]["generation_job"]["endpoint"], "/api/generation-jobs")
            self.assertEqual(
                response.body["asset_pipeline"]["generation_job"]["payload"],
                response.body["asset_pipeline"]["job_payload_template"],
            )
            self.assertEqual(
                response.body["asset_pipeline"]["generation_job"]["expected_status_flow"],
                response.body["asset_pipeline"]["expected_status_flow"],
            )
            self.assertEqual(response.body["asset_pipeline"]["quality_policy"]["texture_quality"], "warning_only_until_generation_completes")
            self.assertEqual(response.body["asset_pipeline"]["quality_policy"]["model_quality"], "blocking_before_final_texture")
            self.assertEqual(response.body["asset_pipeline"]["quality_policy"]["blocking_gate"], "mesh_fit_before_texture_final")
            self.assertEqual(response.body["asset_pipeline"]["quality_policy"]["speed_check_texture_generation"], "allowed_on_seed_proxy")
            self.assertEqual(response.body["asset_pipeline"]["quality_policy"]["vrm_only_render"], "invalid_after_generation")
            self.assertIn("base_suit_surface_present", response.body["asset_pipeline"]["planned_quality_gates"])
            self.assertIn("visible_overlay_parts_minimum", response.body["asset_pipeline"]["planned_quality_gates"])
            self.assertIn("uv_contract", response.body["asset_pipeline"]["planned_quality_gates"])
            self.assertEqual(response.body["preview"]["visual_layers"], response.body["visual_layers"])
            self.assertEqual(response.body["preview"]["render_contract"], response.body["render_contract"])
            self.assertEqual(response.body["preview"]["asset_pipeline"]["texture_plan"]["provider_profile"], "nano_banana")
            self.assertEqual(response.body["preview"]["asset_pipeline"]["fit_status"], "preview_vrm_bone_metrics")
            self.assertEqual(response.body["preview"]["asset_pipeline"]["surface_generation_status"], "planned_not_generated")
            self.assertTrue(response.body["preview"]["modules"]["helmet"]["enabled"])
            self.assertIn("fit", response.body["preview"]["modules"]["helmet"])
            self.assertIn("vrm_anchor", response.body["preview"]["modules"]["helmet"])
            self.assertIn("attachment_slot", response.body["preview"]["modules"]["helmet"])
            self.assertTrue(response.body["preview"]["modules"]["left_forearm"]["enabled"])
            self.assertFalse(response.body["preview"]["modules"]["left_shin"]["enabled"])
            self.assertNotIn("texture_path", response.body["preview"]["modules"]["helmet"])
            self.assertEqual(quest.status, 200)
            self.assertTrue(quest.body["manifest_ready"])
            self.assertRegex(quest.body["manifest_id"], r"^MNF-[0-9]{8}-[A-Z0-9]{4}$")
            self.assertEqual(quest.body["suitspec"]["body_profile"]["height_cm"], 182.0)
            self.assertFalse(quest.body["render_contract"]["vrm_only_is_valid"])
            self.assertEqual(quest.body["render_contract"]["overlay_part_count"], 5)
            self.assertEqual(quest.body["visual_layers"]["armor_overlay"]["part_count"], 5)
            self.assertEqual(quest.body["visual_layers"]["surface_layer"]["layer_id"], "surface_materials")
            self.assertEqual(quest.body["visual_layers"]["surface_layer"]["kind"], "texture_and_emissive_maps")
            self.assertEqual(quest.body["asset_pipeline"]["surface_plan"]["contract_version"], "surface-plan.v1")
            self.assertEqual(quest.body["asset_pipeline"]["surface_plan"]["style_intent"], "bright_tokusatsu_hero")
            self.assertEqual(quest.body["asset_pipeline"]["render_contract"], quest.body["render_contract"])
            self.assertEqual(quest.body["model_quality_gate"], quest.body["asset_pipeline"]["model_quality_gate"])
            self.assertEqual(quest.body["runtime_package"]["manifest"], quest.body["manifest"])
            self.assertEqual(quest.body["runtime_package"]["visual_layers"], quest.body["visual_layers"])
            self.assertEqual(quest.body["runtime_package"]["render_contract"], quest.body["render_contract"])
            self.assertEqual(quest.body["runtime_package"]["body_fit_contract"]["contract_version"], "armor-body-fit.v1")
            self.assertEqual(quest.body["runtime_package"]["body_fit_contract"]["height_cm"], 182.0)
            self.assertEqual(quest.body["runtime_package"]["model_quality_gate"], quest.body["model_quality_gate"])
            self.assertEqual(quest.body["runtime_package"]["runtime_checks"]["model_quality_gate_status"], "pass")
            self.assertTrue(quest.body["runtime_package"]["runtime_checks"]["model_quality_ready"])
            self.assertTrue(quest.body["runtime_package"]["runtime_checks"]["texture_lock_allowed"])
            self.assertTrue(quest.body["runtime_package"]["runtime_checks"]["can_render_runtime_suit"])
            self.assertEqual(
                quest.body["runtime_package"]["runtime_checks"]["required_layers"],
                ["base_suit_surface", "armor_overlay_parts"],
            )

    def test_quest_recall_backfills_surface_layer_for_legacy_forge_suitspec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            suit_store = Path(tmp) / "suits"
            api = NewRouteApi(Path("."), suit_store_root=suit_store)
            response = api.post(
                "/v1/suits/forge",
                {"display_name": "Legacy surface", "recall_code": "L9G4", "parts": ["helmet", "chest", "back"]},
            )
            assert response is not None
            self.assertEqual(response.status, 201, response.body)

            suit_dir = next(path for path in suit_store.iterdir() if path.is_dir())
            suitspec_path = suit_dir / "suitspec.json"
            suitspec = json.loads(suitspec_path.read_text(encoding="utf-8"))
            generation = suitspec.get("generation")
            assert isinstance(generation, dict)
            visual_layers = generation.get("visual_layers")
            assert isinstance(visual_layers, dict)
            visual_layers.pop("surface_layer", None)
            generation.pop("surface_plan", None)
            suitspec_path.write_text(json.dumps(suitspec, ensure_ascii=False, indent=2), encoding="utf-8")

            quest = api.get("/v1/quest/recall/L9G4")

            self.assertIsNotNone(quest)
            assert quest is not None
            self.assertEqual(quest.status, 200)
            self.assertEqual(quest.body["visual_layers"]["surface_layer"]["layer_id"], "surface_materials")
            self.assertEqual(quest.body["asset_pipeline"]["surface_plan"]["contract_version"], "surface-plan.v1")
            self.assertEqual(
                quest.body["runtime_package"]["visual_layers"]["surface_layer"],
                quest.body["visual_layers"]["surface_layer"],
            )

    def test_forge_suit_helmet_only_keeps_selected_overlay_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            with patch(
                "henshin.new_route_api.audit_viewer_mesh_assets",
                side_effect=self._selected_p0_gate,
            ) as mesh_audit:
                response = api.post(
                    "/v1/suits/forge",
                    {"display_name": "Helmet only", "recall_code": "H1A1", "parts": ["helmet"]},
                )
            quest = api.get("/v1/quest/recall/H1A1")

            self.assertIsNotNone(response)
            self.assertIsNotNone(quest)
            assert response is not None and quest is not None
            self.assertEqual(response.status, 201, response.body)
            self.assertEqual(mesh_audit.call_args.kwargs.get("required_parts"), ["helmet"])
            self.assertFalse(response.body["readiness"]["model_quality_ready"])
            self.assertFalse(response.body["readiness"]["final_texture_ready"])
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["selected_parts"], ["helmet"])
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["required_parts"], ["back", "chest", "helmet"])
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["part_count"], 1)
            self.assertEqual(response.body["visual_layers"]["armor_overlay"]["minimum_visible_parts"], 3)
            self.assertEqual(response.body["render_contract"]["selected_overlay_parts"], ["helmet"])
            self.assertEqual(response.body["render_contract"]["required_overlay_parts"], ["back", "chest", "helmet"])
            self.assertEqual(response.body["render_contract"]["overlay_part_count"], 1)
            self.assertEqual(response.body["render_contract"]["minimum_visible_overlay_parts"], 3)
            self.assertEqual(response.body["render_contract"]["missing_required_overlay_parts"], ["back", "chest"])
            self.assertEqual(response.body["model_quality_gate"]["required_parts"], ["helmet"])
            self.assertEqual(response.body["model_quality_gate"]["mesh_quality_status"], "pass")
            self.assertEqual(response.body["model_quality_gate"]["status"], "fail")
            self.assertFalse(response.body["model_quality_gate"]["selection_complete_for_final_texture"])
            self.assertEqual(response.body["model_quality_gate"]["missing_required_overlay_parts"], ["back", "chest"])
            self.assertFalse(response.body["model_quality_gate"]["texture_lock_allowed"])
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["overlay_parts"], ["helmet"])
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["body_fit_slot_count"], 1)
            self.assertEqual(response.body["asset_pipeline"]["job_defaults"]["parts"], ["helmet"])
            self.assertEqual(response.body["asset_pipeline"]["job_payload_template"]["parts"], ["helmet"])
            self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["final_texture_lock_allowed"])
            self.assertFalse(response.body["asset_pipeline"]["texture_probe_job"]["payload"]["writes_final_texture"])
            self.assertEqual(quest.body["visual_layers"]["armor_overlay"]["part_count"], 1)
            self.assertEqual(quest.body["render_contract"]["minimum_visible_overlay_parts"], 3)
            self.assertEqual(quest.body["runtime_package"]["runtime_checks"]["enabled_overlay_parts"], ["helmet"])
            self.assertEqual(quest.body["runtime_package"]["runtime_checks"]["minimum_visible_overlay_parts"], 3)
            self.assertEqual(quest.body["runtime_package"]["runtime_checks"]["missing_required_overlay_parts"], ["back", "chest"])
            self.assertFalse(quest.body["runtime_package"]["runtime_checks"]["texture_lock_allowed"])
            self.assertFalse(quest.body["runtime_package"]["runtime_checks"]["can_render_runtime_suit"])

    def test_forge_suit_all_parts_keeps_upperarm_model_gate_pass(self) -> None:
        parts = [
            "helmet",
            "chest",
            "back",
            "waist",
            "left_shoulder",
            "right_shoulder",
            "left_upperarm",
            "right_upperarm",
            "left_forearm",
            "right_forearm",
            "left_hand",
            "right_hand",
            "left_thigh",
            "right_thigh",
            "left_shin",
            "right_shin",
            "left_boot",
            "right_boot",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            response = api.post(
                "/v1/suits/forge",
                {
                    "display_name": "All parts",
                    "recall_code": "A18B",
                    "parts": parts,
                },
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201, response.body)
            self.assertEqual(response.body["asset_pipeline"]["model_plan"]["body_fit_slot_count"], 18)
            self.assertEqual(response.body["model_quality_gate"]["status"], "pass")
            self.assertTrue(response.body["model_quality_gate"]["texture_lock_allowed"])
            self.assertEqual(response.body["model_quality_gate"]["parts"]["left_upperarm"]["body_fit_slot_id"], "upperarm_l")
            self.assertEqual(response.body["model_quality_gate"]["parts"]["right_upperarm"]["body_fit_slot_id"], "upperarm_r")
            self.assertEqual(response.body["model_quality_gate"]["parts"]["left_upperarm"]["runtime_part_id"], "left_upperarm")
            self.assertEqual(response.body["model_quality_gate"]["parts"]["right_upperarm"]["runtime_part_id"], "right_upperarm")
            self.assertIn("left_upperarm", response.body["model_quality_gate"]["required_parts"])
            self.assertIn("right_upperarm", response.body["model_quality_gate"]["required_parts"])
            self.assertEqual(response.body["render_contract"]["overlay_part_count"], 18)

    def test_forge_suit_issues_default_code_and_rejects_duplicate_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits/forge", {"display_name": "Visitor"})
            self.assertIsNotNone(first)
            assert first is not None
            duplicate = api.post("/v1/suits/forge", {"display_name": "Other", "recall_code": first.body["recall_code"]})
            quest = api.get(f"/v1/quest/recall/{first.body['recall_code']}")

            self.assertIsNotNone(duplicate)
            self.assertIsNotNone(quest)
            assert duplicate is not None and quest is not None
            self.assertEqual(first.status, 201)
            self.assertRegex(first.body["recall_code"], r"^[A-Z0-9]{4}$")
            self.assertRegex(first.body["recall_code"], r"^[0-9]{4}$")
            self.assertEqual(duplicate.status, 400)
            self.assertIn("recall_code", duplicate.body["error"])
            self.assertEqual(quest.status, 200)
            self.assertTrue(quest.body["manifest_ready"])

    def test_forge_suit_rejects_invalid_height_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            suit_store_root = Path(tmp) / "suits"
            api = NewRouteApi(Path("."), suit_store_root=suit_store_root)
            response = api.post("/v1/suits/forge", {"height_cm": 400})

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 400)
            self.assertIn("height_cm", response.body["error"])
            self.assertFalse(suit_store_root.exists())

    def test_forge_suit_rejects_invalid_public_parameters_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            suit_store_root = Path(tmp) / "suits"
            api = NewRouteApi(Path("."), suit_store_root=suit_store_root)
            response = api.post(
                "/v1/suits/forge",
                {"palette": {"primary": "blue"}, "parts": ["helmet"]},
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 400)
            self.assertFalse(suit_store_root.exists())

    def test_recall_code_lookup_rejects_invalid_or_unknown_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            invalid = api.get("/v1/suits/code/ABC")
            unknown = api.get("/v1/quest/recall/ZZZZ")

            self.assertIsNotNone(invalid)
            self.assertIsNotNone(unknown)
            assert invalid is not None and unknown is not None
            self.assertEqual(invalid.status, 400)
            self.assertEqual(unknown.status, 404)

    def test_create_suit_rejects_duplicate_without_overwrite(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits", {"suitspec": suitspec})
            second = api.post("/v1/suits", {"suitspec": suitspec})

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(second.status, 409)

    def test_manifest_post_projects_saved_suitspec(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            api.post("/v1/suits", {"suitspec": suitspec})

            response = api.post(
                "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
                {"manifest_id": "MNF-20260424-ABCD", "status": "READY"},
            )
            fetched = api.get("/v1/manifests/MNF-20260424-ABCD")
            assert response is not None
            quest = api.get(f"/v1/quest/recall/{response.body['suit']['recall_code']}")

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            self.assertIsNotNone(quest)
            assert fetched is not None and quest is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(response.body["manifest"]["status"], "READY")
            self.assertEqual(response.body["manifest"]["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")
            self.assertEqual(fetched.status, 200)
            self.assertEqual(fetched.body["manifest"]["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(quest.status, 200)
            self.assertTrue(quest.body["suitspec_ready"])
            self.assertTrue(quest.body["manifest_ready"])
            self.assertEqual(quest.body["suit_id"], "VDA-AXIS-OP-00-0001")
            self.assertEqual(quest.body["manifest"]["manifest_id"], "MNF-20260424-ABCD")

    def test_manifest_post_returns_404_for_unknown_suit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            response = api.post(
                "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
                {"manifest_id": "MNF-20260424-ABCD"},
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 404)

    def test_create_trial_uses_latest_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            response = api.post(
                "/v1/trials",
                {
                    "suit_id": "VDA-AXIS-OP-00-0001",
                    "session_id": "S-TRIAL-UNIT-0001",
                    "operator_id": "operator-local",
                    "device_id": "quest-local",
                    "tracking_source": "iw_sdk",
                },
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["session_id"], "S-TRIAL-UNIT-0001")
            self.assertEqual(response.body["trial"]["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(response.body["trial"]["events"][0]["event_type"], "SESSION_CREATED")

    def test_append_trial_event_updates_state_and_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})

            response = api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {
                    "event_type": "DEPOSITION_STARTED",
                    "state_after": "DEPOSITION",
                    "actor": {"type": "device", "id": "quest-local"},
                    "payload": {"source": "quest-browser"},
                    "idempotency_key": "deposition-start",
                },
            )
            fetched = api.get("/v1/trials/S-TRIAL-UNIT-0001")

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            assert response is not None and fetched is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["event"]["sequence"], 1)
            self.assertEqual(response.body["trial"]["state"], "DEPOSITION")
            self.assertEqual(fetched.body["trial"]["events"][1]["idempotency_key"], "deposition-start")

    def test_append_trial_event_does_not_regress_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_COMPLETED", "state_after": "ACTIVE"},
            )

            response = api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "VOICE_CAPTURED", "state_after": "POSTED"},
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["trial"]["state"], "ACTIVE")
            self.assertEqual(response.body["event"]["state_before"], "ACTIVE")
            self.assertEqual(response.body["event"]["state_after"], "ACTIVE")
            self.assertEqual(response.body["event"]["payload"]["requested_state_after"], "POSTED")

    def test_create_trial_returns_conflict_without_manifest(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            api.post("/v1/suits", {"suitspec": suitspec})

            response = api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001"})

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 409)

    def test_get_trial_replay_generates_replay_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_STARTED", "state_after": "DEPOSITION"},
            )

            response = api.get("/v1/trials/S-TRIAL-UNIT-0001/replay")

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 200)
            self.assertRegex(response.body["replay_id"], r"^RPL-[0-9]{8}-[A-Z0-9]{4}$")
            self.assertEqual(response.body["replay"]["session_id"], "S-TRIAL-UNIT-0001")
            self.assertEqual(response.body["replay"]["source_events"]["event_ids"][0], response.body["session"]["events"][0]["event_id"])
            self.assertTrue(response.body["replay_path"].endswith("replay-script.json"))

    def test_get_trial_replay_expands_motion_capture_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_STARTED", "state_after": "DEPOSITION"},
            )
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {
                    "event_type": "DEPOSITION_COMPLETED",
                    "state_after": "ACTIVE",
                    "payload": {
                        "motion_capture": {
                            "format": "quest-live-pose.v0",
                            "tracking": "hmd_plus_controllers",
                            "timebase": "deposition_elapsed_sec",
                            "coordinate_space": {"head": "rig_local", "right_hand": "rig_local"},
                            "frames": [
                                {"t": 0.2, "head": [0, 1.6, 0], "right_hand": [0.5, 1.2, -0.2]},
                                {"t": 0.0, "head": [0, 1.6, 0], "right_hand": [0.3, 1.2, -0.2]},
                            ],
                        }
                    },
                },
            )

            response = api.get("/v1/trials/S-TRIAL-UNIT-0001/replay")

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 200)
            motion_segments = [
                segment for segment in response.body["replay"]["timeline"]
                if str(segment["segment_id"]).startswith("SEG-MOTION-")
            ]
            self.assertEqual(len(motion_segments), 1)
            self.assertEqual(motion_segments[0]["duration_sec"], 0.2)
            self.assertEqual(len(motion_segments[0]["actions"]), 2)
            action_times = [action["at_time_sec"] for action in motion_segments[0]["actions"]]
            self.assertEqual(action_times, sorted(action_times))
            self.assertAlmostEqual(action_times[0], motion_segments[0]["start_time_sec"], places=3)
            self.assertEqual(round(action_times[1] - action_times[0], 3), 0.2)
            self.assertEqual(motion_segments[0]["actions"][1]["action_type"], "deposition_progress")
            self.assertEqual(motion_segments[0]["actions"][1]["params"]["motion_capture_format"], "quest-live-pose.v0")
            self.assertEqual(motion_segments[0]["actions"][1]["params"]["timebase"], "deposition_elapsed_sec")
            self.assertEqual(motion_segments[0]["actions"][1]["params"]["motion_frame"]["right_hand"], [0.5, 1.2, -0.2])
            event_segment = next(
                segment for segment in response.body["replay"]["timeline"]
                if segment["segment_id"] == "SEG-0002"
            )
            compact_motion = event_segment["actions"][0]["params"]["payload"]["motion_capture"]
            self.assertEqual(compact_motion["frame_count"], 2)
            self.assertNotIn("frames", compact_motion)

    def test_get_latest_trial_returns_replay_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0002"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_COMPLETED", "state_after": "ACTIVE"},
            )
            api.get("/v1/trials/S-TRIAL-UNIT-0001/replay")

            latest = api.get("/v1/trials/latest")
            listed = api.get("/v1/trials")

            self.assertIsNotNone(latest)
            self.assertIsNotNone(listed)
            assert latest is not None and listed is not None
            self.assertEqual(latest.status, 200)
            self.assertEqual(latest.body["trial_id"], "S-TRIAL-UNIT-0001")
            self.assertEqual(latest.body["summary"]["state"], "ACTIVE")
            self.assertEqual(latest.body["summary"]["event_count"], 2)
            self.assertTrue(latest.body["summary"]["replay_script_path"].endswith("replay-script.json"))
            self.assertEqual(listed.body["count"], 2)
            self.assertEqual(listed.body["latest"]["session_id"], "S-TRIAL-UNIT-0001")

    def _sample_suitspec(self) -> dict:
        return json.loads(Path("examples/suitspec.sample.json").read_text(encoding="utf-8"))

    def _api_with_manifest(self, suit_store_root: Path) -> NewRouteApi:
        api = NewRouteApi(Path("."), suit_store_root=suit_store_root)
        api.post("/v1/suits", {"suitspec": self._sample_suitspec()})
        api.post(
            "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
            {"manifest_id": "MNF-20260424-ABCD", "status": "READY"},
        )
        return api

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


if __name__ == "__main__":
    unittest.main()
