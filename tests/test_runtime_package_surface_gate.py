import json
import tempfile
import unittest
from pathlib import Path

from henshin.part_generation import GenerationRequest, run_generate_parts
from henshin.runtime_package import build_runtime_suit_package


def _suitspec(*, helmet_asset_ref: str, generation: dict | None = None) -> dict:
    payload = {
        "schema_version": "0.2",
        "suit_id": "VDA-AXIS-WEB-00-0001",
        "body_profile": {"height_cm": 176.0, "vrm_baseline_ref": "viewer/assets/vrm/default.vrm"},
        "modules": {
            "helmet": {
                "enabled": True,
                "asset_ref": helmet_asset_ref,
                "attachment_slot": "head",
                "fit": {"source": "head", "attach": "head", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
                "vrm_anchor": {"bone": "head"},
            },
            "chest": {
                "enabled": True,
                "asset_ref": "viewer/assets/meshes/chest.mesh.json",
                "attachment_slot": "chest",
                "fit": {"source": "chest", "attach": "chest", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
                "vrm_anchor": {"bone": "chest"},
            },
            "back": {
                "enabled": True,
                "asset_ref": "viewer/assets/meshes/back.mesh.json",
                "attachment_slot": "back",
                "fit": {"source": "chest", "attach": "back", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
                "vrm_anchor": {"bone": "chest"},
            },
        },
    }
    if generation is not None:
        payload["generation"] = generation
    return payload


class TestRuntimePackageSurfaceGate(unittest.TestCase):
    def test_missing_local_glb_blocks_runtime_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_glb = Path(tmp) / "helmet.glb"

            package = build_runtime_suit_package(
                suitspec=_suitspec(helmet_asset_ref=str(missing_glb)),
                manifest={},
            )

        checks = package["runtime_checks"]
        self.assertFalse(checks["can_render_runtime_suit"])
        self.assertEqual(checks["visible_overlay_parts"], ["back", "chest"])
        self.assertEqual(checks["missing_required_overlay_parts"], ["helmet"])
        self.assertEqual(checks["invalid_overlay_parts"], ["helmet"])
        self.assertIn(
            "local GLB asset missing",
            " ".join(checks["runtime_surface_failures"]["helmet"]["reasons"]),
        )
        contract = package["per_part_texture_contracts"]["helmet"]
        self.assertEqual(
            contract["uv_availability"]["asset_surface_case"],
            "glb_fallback_unavailable_for_final_texture",
        )
        self.assertFalse(contract["uv_availability"]["can_generate_mesh_uv_texture"])
        self.assertIn("Asset surface case: glb_fallback_unavailable_for_final_texture", contract["texture_prompt"])

    def test_corrupt_local_glb_blocks_runtime_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corrupt_glb = Path(tmp) / "helmet.glb"
            corrupt_glb.write_bytes(b"not a glb")

            package = build_runtime_suit_package(
                suitspec=_suitspec(helmet_asset_ref=str(corrupt_glb)),
                manifest={},
            )

        checks = package["runtime_checks"]
        self.assertFalse(checks["can_render_runtime_suit"])
        self.assertEqual(checks["missing_required_overlay_parts"], ["helmet"])
        self.assertIn(
            "GLB too small",
            " ".join(checks["runtime_surface_failures"]["helmet"]["reasons"]),
        )

    def test_remote_glb_url_is_not_rejected_by_local_asset_gate(self) -> None:
        package = build_runtime_suit_package(
            suitspec=_suitspec(helmet_asset_ref="https://cdn.example.test/assets/helmet.glb"),
            manifest={},
        )

        checks = package["runtime_checks"]
        self.assertTrue(checks["can_render_runtime_suit"])
        self.assertEqual(checks["visible_overlay_parts"], ["back", "chest", "helmet"])
        self.assertEqual(checks["runtime_surface_failures"], {})
        self.assertEqual(checks["invalid_overlay_parts"], [])

    def test_per_part_texture_contracts_are_exposed_to_runtime_package(self) -> None:
        generation = {
            "selected_variant_keys": {"helmet": "helmet:sleek"},
            "surface_design_hints": {
                "per_part_texture_contracts": {
                    "helmet": {
                        "contract_version": "web-forge-per-part-texture.v1",
                        "part": "helmet",
                        "provider_profile": "nano_banana",
                        "texture_prompt_contract": "nanobanana-texture-prompt.v1",
                        "texture_mode": "mesh_uv",
                        "selected_variant_key": "helmet:sleek",
                        "uv_availability": {"uv0_status": "pass", "can_generate_mesh_uv_texture": True},
                        "uv_policy": {"contract_version": "part-uv-policy.v1", "primary_motif_zone": "visor band"},
                        "material_hints": {"contract_version": "part-material-hints.v1", "material_zones": ["emissive"]},
                        "texture_prompt": "Per-part texture target: helmet with selected variant helmet:sleek.",
                    }
                }
            },
        }
        package = build_runtime_suit_package(
            suitspec=_suitspec(
                helmet_asset_ref="https://cdn.example.test/assets/helmet.glb",
                generation=generation,
            ),
            manifest={},
        )

        contracts = package["per_part_texture_contracts"]
        self.assertIn("helmet", contracts)
        self.assertIn("chest", contracts)
        self.assertEqual(contracts["helmet"]["selected_variant_key"], "helmet:sleek")
        self.assertEqual(contracts["helmet"]["provider_profile"], "nano_banana")
        self.assertIn("Per-part texture target: helmet", contracts["helmet"]["texture_prompt"])
        self.assertEqual(
            package["visual_layers"]["armor_overlay"]["per_part_texture_contracts"]["helmet"]["uv_availability"]["uv0_status"],
            "pass",
        )
        self.assertEqual(package["render_contract"]["per_part_texture_contract"], "web-forge-per-part-texture.v1")
        self.assertIn("helmet", package["runtime_checks"]["per_part_texture_contract_parts"])

    def test_mesh_json_seed_proxy_contract_blocks_final_mesh_uv_texture(self) -> None:
        package = build_runtime_suit_package(
            suitspec=_suitspec(helmet_asset_ref="https://cdn.example.test/assets/helmet.glb"),
            manifest={},
        )

        contract = package["per_part_texture_contracts"]["chest"]
        uv = contract["uv_availability"]
        self.assertEqual(uv["asset_format"], "mesh_json")
        self.assertEqual(uv["asset_surface_case"], "mesh_json_seed_proxy_no_authoritative_uv")
        self.assertEqual(uv["uv0_status"], "not_applicable")
        self.assertFalse(uv["can_generate_mesh_uv_texture"])
        self.assertIn("Asset surface case: mesh_json_seed_proxy_no_authoritative_uv", contract["texture_prompt"])
        self.assertIn("mesh_uv_allowed=False", contract["texture_prompt"])

    def test_surface_gate_failure_keeps_render_placement_evidence_but_blocks_runtime_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_glb = Path(tmp) / "helmet.glb"

            package = build_runtime_suit_package(
                suitspec=_suitspec(helmet_asset_ref=str(missing_glb)),
                manifest={},
            )

        checks = package["runtime_checks"]
        self.assertFalse(checks["can_render_runtime_suit"])
        self.assertEqual(checks["invalid_overlay_parts"], ["helmet"])
        self.assertEqual(package["render_contract"]["render_placement_parts"], ["back", "chest", "helmet"])
        self.assertIn("helmet", package["render_placements"])
        self.assertEqual(
            package["visual_layers"]["armor_overlay"]["render_placements"]["helmet"],
            package["render_placements"]["helmet"],
        )

        placement = package["render_placements"]["helmet"]
        self.assertEqual(placement["contract_version"], "runtime-render-placement.v1")
        self.assertEqual(placement["coordinate_space"], "vrm_humanoid_local_y_up_z_front")
        self.assertEqual(placement["quest_coordinate_space"], "quest_rig_local_y_up_z_back")
        self.assertEqual(placement["surface_anchor"]["offset_clamped_m"], placement["surface_offset_clamped_m"])
        self.assertEqual(
            placement["surface_anchor"]["quest_rig_offset_clamped_m"],
            placement["quest_surface_offset_clamped_m"],
        )

        contract = package["per_part_texture_contracts"]["helmet"]
        self.assertEqual(contract["asset_ref"], placement["asset_ref"])
        uv = contract["uv_availability"]
        self.assertFalse(uv["surface_check_ok"])
        self.assertFalse(uv["can_generate_mesh_uv_texture"])
        self.assertEqual(uv["asset_surface_case"], "glb_fallback_unavailable_for_final_texture")

    def test_mesh_json_preview_surface_gate_does_not_create_final_texture_lock(self) -> None:
        package = build_runtime_suit_package(
            suitspec=_suitspec(helmet_asset_ref="https://cdn.example.test/assets/helmet.glb"),
            manifest={},
        )

        checks = package["runtime_checks"]
        self.assertTrue(checks["can_render_runtime_suit"])
        self.assertNotIn("chest", checks["invalid_overlay_parts"])
        self.assertIn("chest", package["render_placements"])

        placement = package["render_placements"]["chest"]
        contract = package["per_part_texture_contracts"]["chest"]
        uv = contract["uv_availability"]
        self.assertEqual(contract["asset_ref"], placement["asset_ref"])
        self.assertTrue(uv["surface_check_ok"])
        self.assertEqual(uv["asset_surface_case"], "mesh_json_seed_proxy_no_authoritative_uv")
        self.assertFalse(uv["can_generate_mesh_uv_texture"])

    def test_remote_glb_keeps_web_quest_placement_and_remains_uv_unknown(self) -> None:
        package = build_runtime_suit_package(
            suitspec=_suitspec(helmet_asset_ref="https://cdn.example.test/assets/helmet.glb"),
            manifest={},
        )

        checks = package["runtime_checks"]
        self.assertTrue(checks["can_render_runtime_suit"])
        self.assertNotIn("helmet", checks["invalid_overlay_parts"])

        placement = package["render_placements"]["helmet"]
        self.assertEqual(placement["coordinate_space"], "vrm_humanoid_local_y_up_z_front")
        self.assertEqual(placement["quest_coordinate_space"], "quest_rig_local_y_up_z_back")
        self.assertEqual(placement["surface_anchor"]["offset_clamped_m"], placement["surface_offset_clamped_m"])
        self.assertEqual(
            placement["surface_anchor"]["quest_rig_offset_clamped_m"],
            placement["quest_surface_offset_clamped_m"],
        )

        contract = package["per_part_texture_contracts"]["helmet"]
        uv = contract["uv_availability"]
        self.assertEqual(contract["asset_ref"], placement["asset_ref"])
        self.assertTrue(uv["surface_check_ok"])
        self.assertEqual(uv["asset_surface_case"], "glb_without_local_sidecar_uv_unknown")
        self.assertEqual(uv["uv0_status"], "unknown")

    def test_dry_run_prompt_includes_uv_unavailable_contract_case(self) -> None:
        generation = {
            "surface_design_hints": {
                "per_part_texture_contracts": {
                    "helmet": {
                        "contract_version": "web-forge-per-part-texture.v1",
                        "part": "helmet",
                        "provider_profile": "nano_banana",
                        "texture_prompt_contract": "nanobanana-texture-prompt.v1",
                        "texture_mode": "mesh_uv",
                        "selected_variant_key": "helmet:base",
                        "uv_availability": {
                            "asset_format": "missing",
                            "asset_surface_case": "uv_unavailable_no_asset_ref",
                            "uv0_status": "missing",
                            "can_generate_mesh_uv_texture": False,
                        },
                        "uv_policy": {
                            "contract_version": "part-uv-policy.v1",
                            "primary_motif_zone": "visor band",
                            "low_frequency_zone": "rear seam",
                            "panel_flow_direction": "brow to crown",
                        },
                        "material_hints": {
                            "contract_version": "part-material-hints.v1",
                            "material_zones": ["base_surface", "emissive"],
                        },
                        "texture_prompt": "Per-part texture target: helmet without authoritative UV0.",
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            suitspec_path = root / "suitspec.json"
            suitspec_path.write_text(
                json.dumps(
                    _suitspec(helmet_asset_ref="viewer/assets/meshes/helmet.mesh.json", generation=generation),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = run_generate_parts(
                GenerationRequest(
                    suitspec=str(suitspec_path),
                    root=str(root / "sessions"),
                    parts=["helmet"],
                    dry_run=True,
                    texture_mode="mesh_uv",
                    uv_refine=True,
                    surface_design_hints=generation["surface_design_hints"],
                    provider_profile="nano_banana",
                ),
                repo_root=Path(".").resolve(),
            )

        prompt = result["prompts"]["helmet"]
        refine_prompt = result["refine_prompts"]["helmet"]
        self.assertIn("Web Forge per-part texture contract:", prompt)
        self.assertIn("Asset surface case: uv_unavailable_no_asset_ref (missing).", prompt)
        self.assertIn("uv0_status=missing", prompt)
        self.assertIn("mesh_uv_allowed=False", prompt)
        self.assertIn("Asset surface case: uv_unavailable_no_asset_ref (missing).", refine_prompt)

    def test_texture_uv_plan_documents_acceptance_contract_and_operator_copy(self) -> None:
        plan = Path("docs/web-forge-texture-uv-plan-2026-05-05.md").read_text(encoding="utf-8")

        for heading in [
            "## Current capability split",
            "## Acceptance criteria",
            "## Prompt granularity",
            "## UV lock unavailable display copy",
            "## UI acceptance notes",
            "## Surface gate and render placement parity",
        ]:
            self.assertIn(heading, plan)

        for required_copy in [
            "UVロック不可",
            "仮メッシュのため最終UVが未確定です",
            "GLBを検査できないためUVロック不可です",
            "リモートGLBのUVは未検査です",
            "UV0未確認のため本番テクスチャ固定はできません",
            "表面: コンセプト可 / UV固定不可",
        ]:
            self.assertIn(required_copy, plan)

    def test_texture_uv_plan_keeps_mesh_json_glb_fallback_and_remote_glb_distinct(self) -> None:
        plan = Path("docs/web-forge-texture-uv-plan-2026-05-05.md").read_text(encoding="utf-8")

        for asset_case in [
            "mesh_json_seed_proxy_no_authoritative_uv",
            "glb_fallback_unavailable_for_final_texture",
            "glb_without_local_sidecar_uv_unknown",
            "uv_unavailable_no_asset_ref",
        ]:
            self.assertIn(asset_case, plan)

        self.assertIn("can_generate_mesh_uv_texture: false", plan)
        self.assertIn("Prompt text alone cannot visually prove", plan)
        self.assertIn("Remote GLB with `uv0_status: unknown`", plan)

    def test_texture_uv_plan_documents_surface_gate_render_placement_boundaries(self) -> None:
        plan = Path("docs/web-forge-texture-uv-plan-2026-05-05.md").read_text(encoding="utf-8")

        for required in [
            "Surface gate answers whether the selected overlay asset can participate",
            "`render_placements.<part>` must be emitted for every enabled overlay part",
            "`render_contract.render_placement_parts` must describe placement coverage",
            "`per_part_texture_contracts.<part>.asset_ref` and `render_placements.<part>.asset_ref`",
            "Web preview must use `coordinate_space: vrm_humanoid_local_y_up_z_front`",
            "Quest recall must use `quest_coordinate_space: quest_rig_local_y_up_z_back`",
            "Web/Quest parity must not use final texture lock as a renderability signal",
            "モデル表面Gate不可 / 配置契約あり / Quest表示不可",
            "表示可 / UVロック不可 / 本番テクスチャ未固定",
            "表示可 / UV未検査 / 固定前に検査",
        ]:
            self.assertIn(required, plan)


if __name__ == "__main__":
    unittest.main()
