import unittest
from pathlib import Path

from henshin.runtime_package import (
    build_runtime_suit_package,
    merge_suitspec_surface_into_manifest,
)


def _suitspec() -> dict:
    return {
        "schema_version": "0.2",
        "suit_id": "VDA-AXIS-WEB-00-0001",
        "body_profile": {"height_cm": 176.0, "vrm_baseline_ref": "viewer/assets/vrm/default.vrm"},
        "modules": {
            "helmet": {
                "enabled": True,
                "asset_ref": "viewer/assets/meshes/helmet.mesh.json",
                "texture_path": "sessions/S-FORGE-0076/artifacts/parts/helmet.generated.png",
                "attachment_slot": "head",
                "fit": {"source": "head", "attach": "head", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
                "vrm_anchor": {"bone": "head"},
            },
            "chest": {
                "enabled": True,
                "asset_ref": "viewer/assets/meshes/chest.mesh.json",
                "attachment_slot": "chest",
                "fit": {"source": "chest", "attach": "chest", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
                "vrm_anchor": {"bone": "chest", "offset": [0.0, 0.02, 0.04], "rotation": [0, 5, 0]},
                "modeler_sidecar": {
                    "variant_key": "chest:rescue_wrap",
                    "coordinate_frame": "vrm_humanoid_local_y_up_z_front",
                    "bbox_m": {"x": 0.42, "y": 0.36, "z": 0.11},
                    "target_envelope_m": {"x": 0.5, "y": 0.4, "z": 0.14},
                    "clearance_m": 0.024,
                    "shell_thickness_target_m": 0.045,
                    "body_follow_profile": {
                        "target_contact": "front shell follows the wearer ribcage surface",
                    },
                    "vrm_attachment": {
                        "primary_bone": "upperChest",
                        "offset_m": [0.0, 0.01, 0.03],
                        "rotation_deg": [0, 0, 0],
                    },
                },
            },
            "back": {
                "enabled": True,
                "asset_ref": "viewer/assets/meshes/back.mesh.json",
                "attachment_slot": "back",
                "fit": {"source": "chest", "attach": "back", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
                "vrm_anchor": {"bone": "chest"},
            },
            "left_forearm": {
                "enabled": False,
                "asset_ref": "viewer/assets/meshes/left_forearm.mesh.json",
            },
        },
    }


class TestRuntimePackage(unittest.TestCase):
    def test_manifest_surface_fields_are_projected_from_suitspec(self) -> None:
        manifest = {"manifest_id": "MNF-20260428-TEST", "parts": {"helmet": {"enabled": True}}}

        package_manifest = merge_suitspec_surface_into_manifest(manifest, _suitspec())

        self.assertEqual(
            package_manifest["parts"]["helmet"]["texture_path"],
            "sessions/S-FORGE-0076/artifacts/parts/helmet.generated.png",
        )
        self.assertEqual(
            package_manifest["parts"]["helmet"]["asset_ref"],
            "viewer/assets/meshes/helmet.mesh.json",
        )
        self.assertEqual(package_manifest["parts"]["left_forearm"]["enabled"], False)

    def test_runtime_package_makes_vrm_only_invalid(self) -> None:
        package = build_runtime_suit_package(
            suitspec=_suitspec(),
            manifest={"manifest_id": "MNF-20260428-TEST", "parts": {}},
        )

        checks = package["runtime_checks"]
        self.assertFalse(checks["vrm_only_is_valid"])
        self.assertTrue(checks["can_render_runtime_suit"])
        self.assertEqual(checks["required_layers"], ["base_suit_surface", "armor_overlay_parts"])
        self.assertEqual(checks["minimum_visible_overlay_parts"], 3)
        self.assertEqual(checks["missing_required_overlay_parts"], [])
        self.assertEqual(
            checks["visible_overlay_parts"],
            ["back", "chest", "helmet"],
        )
        self.assertEqual(checks["body_fit_contract_version"], "armor-body-fit.v1")
        self.assertTrue(checks["body_fit_core_ready"])
        self.assertEqual(package["body_fit_contract"]["height_cm"], 176.0)
        self.assertEqual(
            [item["slot_id"] for item in package["visual_layers"]["armor_overlay"]["body_fit_slots"]],
            ["helmet", "chest", "back"],
        )
        self.assertEqual(package["visual_layers"]["base_suit"]["asset_ref"], "viewer/assets/vrm/default.vrm")
        self.assertEqual(package["render_contract"]["render_placement_contract"], "runtime-render-placement.v1")
        self.assertEqual(package["render_contract"]["render_placement_parts"], ["back", "chest", "helmet"])
        chest = package["render_placements"]["chest"]
        self.assertEqual(chest["body_fit_slot_id"], "chest")
        self.assertEqual(chest["body_anchor"], "upperChest")
        self.assertEqual(chest["selected_variant_key"], "chest:rescue_wrap")
        self.assertEqual(chest["modeler_sidecar_variant_key"], "chest:rescue_wrap")
        self.assertEqual(chest["offset_m"], [0.0, 0.02, 0.04])
        self.assertEqual(chest["quest_rig_offset_m"], [0.0, 0.02, -0.04])
        self.assertEqual(chest["surface_offset_clamped_m"], [0.0, 0.02, 0.04])
        self.assertEqual(chest["quest_surface_offset_clamped_m"], [0.0, 0.02, -0.04])
        self.assertEqual(chest["body_surface_clearance_m"], 0.024)
        self.assertEqual(chest["body_surface_clearance_source"], "modeler_sidecar.clearance_m")
        self.assertEqual(chest["shell_thickness_target_m"], 0.045)
        surface_anchor = chest["surface_anchor"]
        self.assertEqual(surface_anchor["contract_version"], "runtime-body-surface-anchor.v1")
        self.assertEqual(surface_anchor["surface_policy"], "body-surface-fit-policy.v1")
        self.assertEqual(surface_anchor["surface_role"], "front_ribcage_shell")
        self.assertEqual(surface_anchor["body_anchor"], "upperChest")
        self.assertEqual(surface_anchor["offset_clamped_m"], [0.0, 0.02, 0.04])
        self.assertEqual(surface_anchor["quest_rig_offset_clamped_m"], [0.0, 0.02, -0.04])
        self.assertEqual(surface_anchor["vrm_offset_clamp_m"]["z"], [0.04, 0.105])
        self.assertEqual(surface_anchor["quest_offset_clamp_m"]["z"], [-0.105, -0.04])
        self.assertEqual(surface_anchor["clearance_m"], 0.024)
        self.assertEqual(surface_anchor["shell_thickness_target_m"], 0.045)
        self.assertEqual(
            surface_anchor["target_contact"],
            "front shell follows the wearer ribcage surface",
        )
        self.assertEqual(
            surface_anchor["target_contact_source"],
            "modeler_sidecar.body_follow_profile.target_contact",
        )
        self.assertEqual(chest["rotation_deg"], [0.0, 5.0, 0.0])
        self.assertEqual(chest["target_size_array_m"], [0.5, 0.4, 0.14])
        self.assertEqual(
            package["visual_layers"]["armor_overlay"]["render_placements"]["chest"],
            chest,
        )

    def test_runtime_render_placement_public_fields_cover_web_and_quest_offsets(self) -> None:
        package = build_runtime_suit_package(
            suitspec=_suitspec(),
            manifest={"manifest_id": "MNF-20260428-TEST", "parts": {}},
        )

        for part, placement in package["render_placements"].items():
            with self.subTest(part=part):
                self.assertEqual(placement["contract_version"], "runtime-render-placement.v1")
                self.assertEqual(placement["coordinate_space"], "vrm_humanoid_local_y_up_z_front")
                self.assertEqual(placement["quest_coordinate_space"], "quest_rig_local_y_up_z_back")
                self.assertIsInstance(placement["surface_offset_clamped_m"], list)
                self.assertIsInstance(placement["quest_surface_offset_clamped_m"], list)
                self.assertEqual(len(placement["surface_offset_clamped_m"]), 3)
                self.assertEqual(len(placement["quest_surface_offset_clamped_m"]), 3)
                self.assertEqual(
                    placement["surface_anchor"]["offset_clamped_m"],
                    placement["surface_offset_clamped_m"],
                )
                self.assertEqual(
                    placement["surface_anchor"]["quest_rig_offset_clamped_m"],
                    placement["quest_surface_offset_clamped_m"],
                )

    def test_runtime_package_snapshots_variant_render_placements_for_replay_diff(self) -> None:
        selected_chest_placement = {
            "contract_version": "runtime-render-placement.v1",
            "part": "chest",
            "asset_ref": "viewer/assets/meshes/chest.mesh.json",
            "selected_variant_key": "chest:rescue_wrap",
            "coordinate_space": "vrm_humanoid_local_y_up_z_front",
            "quest_coordinate_space": "quest_rig_local_y_up_z_back",
            "target_size_array_m": [0.5, 0.4, 0.14],
            "offset_m": [0.0, 0.02, 0.04],
            "quest_rig_offset_m": [0.0, 0.02, -0.04],
            "rotation_deg": [0.0, 5.0, 0.0],
        }
        alternate_chest_placement = {
            **selected_chest_placement,
            "asset_ref": "viewer/assets/armor-parts/chest/variants/split_rib/chest__split_rib.glb",
            "selected_variant_key": "chest:split_rib",
            "target_size_array_m": [0.62, 0.42, 0.18],
        }
        visual_layers = {
            "armor_overlay": {
                "variant_render_placements": {
                    "chest": {
                        "chest:rescue_wrap": selected_chest_placement,
                        "chest:split_rib": alternate_chest_placement,
                    }
                }
            }
        }

        package = build_runtime_suit_package(
            suitspec=_suitspec(),
            manifest={"manifest_id": "MNF-20260428-TEST", "parts": {}},
            visual_layers=visual_layers,
        )

        self.assertEqual(package["selected_variant_keys"]["chest"], "chest:rescue_wrap")
        self.assertEqual(
            package["visual_layers"]["armor_overlay"]["variant_render_placements"]["chest"]["chest:split_rib"]["target_size_array_m"],
            [0.62, 0.42, 0.18],
        )
        self.assertEqual(
            package["selected_variant_render_placements"]["chest"]["selected_variant_key"],
            "chest:rescue_wrap",
        )
        self.assertEqual(
            package["visual_layers"]["armor_overlay"]["selected_variant_render_placements"]["chest"],
            package["selected_variant_render_placements"]["chest"],
        )
        self.assertEqual(
            package["render_contract"]["variant_render_placement_contract"],
            "runtime-render-placement.v1",
        )
        self.assertEqual(package["render_contract"]["variant_render_placement_parts"], ["chest"])
        snapshot = package["variant_placement_snapshot"]
        self.assertEqual(snapshot["contract_version"], "runtime-variant-placement-snapshot.v1")
        self.assertEqual(
            snapshot["parts"]["chest"]["variant_render_placement_path"],
            "visual_layers.armor_overlay.variant_render_placements.chest.chest:rescue_wrap",
        )
        self.assertTrue(snapshot["parts"]["chest"]["matches_current_render_placement"])
        self.assertEqual(snapshot["parts"]["helmet"]["status"], "not_variant_selected")
        self.assertEqual(snapshot["missing_selected_variant_render_placements"], [])
        self.assertEqual(snapshot["mismatched_selected_variant_render_placements"], [])
        self.assertEqual(package["runtime_checks"]["selected_variant_render_placement_parts"], ["chest"])
        self.assertEqual(package["runtime_checks"]["missing_selected_variant_render_placements"], [])

    def test_runtime_package_keeps_raw_offset_and_adds_surface_clamped_offset(self) -> None:
        suitspec = _suitspec()
        suitspec["modules"]["chest"]["vrm_anchor"]["offset"] = [0.2, -0.2, 0.2]

        package = build_runtime_suit_package(suitspec=suitspec, manifest={})

        chest = package["render_placements"]["chest"]
        self.assertEqual(chest["offset_m"], [0.2, -0.2, 0.2])
        self.assertEqual(chest["quest_rig_offset_m"], [0.2, -0.2, -0.2])
        self.assertEqual(chest["surface_offset_clamped_m"], [0.015, -0.03, 0.105])
        self.assertEqual(chest["quest_surface_offset_clamped_m"], [0.015, -0.03, -0.105])
        self.assertEqual(chest["surface_anchor"]["offset_m"], [0.2, -0.2, 0.2])
        self.assertEqual(chest["surface_anchor"]["quest_rig_offset_m"], [0.2, -0.2, -0.2])

    def test_missing_required_overlay_part_blocks_runtime_render(self) -> None:
        suitspec = _suitspec()
        suitspec["modules"]["back"]["enabled"] = False

        package = build_runtime_suit_package(suitspec=suitspec, manifest={})

        checks = package["runtime_checks"]
        self.assertFalse(checks["can_render_runtime_suit"])
        self.assertEqual(checks["missing_required_overlay_parts"], ["back"])
        self.assertEqual(checks["missing_required_body_fit_slots"], ["back"])
        self.assertEqual(checks["visible_overlay_count"], 2)

    def test_runtime_package_carries_model_quality_gate_without_blocking_trial_render(self) -> None:
        gate = {
            "contract_version": "model-quality-gate.v1",
            "status": "fail",
            "texture_lock_allowed": False,
            "reasons": ["helmet: bounds missing or invalid"],
        }

        package = build_runtime_suit_package(suitspec=_suitspec(), manifest={}, model_quality_gate=gate)

        self.assertEqual(package["model_quality_gate"], gate)
        self.assertEqual(package["runtime_checks"]["model_quality_gate_status"], "fail")
        self.assertFalse(package["runtime_checks"]["model_quality_ready"])
        self.assertFalse(package["runtime_checks"]["texture_lock_allowed"])
        self.assertTrue(package["runtime_checks"]["can_render_runtime_suit"])
        self.assertEqual(package["render_contract"]["render_placement_contract"], "runtime-render-placement.v1")
        self.assertEqual(package["render_contract"]["render_placement_parts"], ["back", "chest", "helmet"])
        self.assertEqual(sorted(package["render_placements"]), ["back", "chest", "helmet"])

    def test_runtime_surface_failures_do_not_expose_machine_local_paths(self) -> None:
        suitspec = _suitspec()
        suitspec["modules"]["helmet"]["asset_ref"] = "viewer/assets/armor-parts/missing/helmet.glb"

        package = build_runtime_suit_package(suitspec=suitspec, manifest={})

        failure = package["runtime_checks"]["runtime_surface_failures"]["helmet"]
        serialized = repr(failure).replace("\\", "/")
        self.assertFalse(failure["ok"])
        self.assertEqual(failure["asset_ref"], "viewer/assets/armor-parts/missing/helmet.glb")
        self.assertNotIn("local_path", failure)
        self.assertNotIn(Path.cwd().as_posix(), serialized)
        self.assertIn("viewer/assets/armor-parts/missing/helmet.glb", failure["reasons"][0])

    def test_runtime_package_uses_local_glb_modeler_sidecar_for_target_size(self) -> None:
        suitspec = {
            "schema_version": "0.2",
            "suit_id": "VDA-AXIS-WEB-00-0002",
            "body_profile": {"height_cm": 176.0, "vrm_baseline_ref": "viewer/assets/vrm/default.vrm"},
            "modules": {
                "helmet": {
                    "enabled": True,
                    "asset_ref": "viewer/assets/armor-parts/helmet/helmet.glb",
                    "attachment_slot": "helmet",
                    "fit": {"scale": [0.05, 0.05, 0.05]},
                    "vrm_anchor": {"bone": "head"},
                },
                "chest": _suitspec()["modules"]["chest"],
                "back": _suitspec()["modules"]["back"],
            },
        }

        package = build_runtime_suit_package(suitspec=suitspec, manifest={})

        helmet = package["render_placements"]["helmet"]
        self.assertEqual(helmet["modeler_sidecar_variant_key"], "helmet:base")
        self.assertGreater(helmet["target_size_array_m"][0], 0.2)
        self.assertGreater(helmet["target_size_array_m"][1], 0.3)
        self.assertGreater(helmet["target_size_array_m"][2], 0.2)
        self.assertNotEqual(helmet["target_size_array_m"], [0.05, 0.05, 0.05])

    def test_runtime_package_uses_blueprint_target_for_variant_sidecar_without_target_envelope(self) -> None:
        suitspec = _suitspec()
        suitspec["modules"]["chest"] = {
            "enabled": True,
            "asset_ref": "viewer/assets/armor-parts/chest/variants/sleek/chest__sleek.glb",
            "attachment_slot": "chest",
            "fit": {"source": "chest", "attach": "chest", "scale": [1, 1, 1], "minScale": [0.1, 0.1, 0.1]},
            "vrm_anchor": {"bone": "chest", "offset": [0.0, 0.02, 0.04], "rotation": [0, 5, 0]},
        }

        package = build_runtime_suit_package(suitspec=suitspec, manifest={})

        chest = package["render_placements"]["chest"]
        self.assertEqual(chest["modeler_sidecar_variant_key"], "chest:sleek")
        self.assertEqual(chest["target_size_source"], "blueprint_canonical_envelope")
        self.assertEqual(chest["target_size_array_m"], [0.6392, 0.4992, 0.1632])
        self.assertNotEqual(chest["target_size_array_m"], [0.589, 0.162046, 0.46])

    def test_runtime_package_ignores_unrecognized_inline_modeler_sidecar(self) -> None:
        for field, value in {
            "contract_version": "unknown-sidecar.v9",
            "coordinate_frame": "quest_rig_local_y_up_z_back",
        }.items():
            with self.subTest(field=field):
                suitspec = _suitspec()
                bad_sidecar = {
                    "contract_version": "modeler-part-sidecar.v1",
                    "variant_key": "chest:bad_inline",
                    "coordinate_frame": "vrm_humanoid_local_y_up_z_front",
                    "target_envelope_m": {"x": 9.0, "y": 9.0, "z": 9.0},
                }
                bad_sidecar[field] = value
                suitspec["modules"]["chest"]["modeler_sidecar"] = bad_sidecar

                package = build_runtime_suit_package(suitspec=suitspec, manifest={})

                chest = package["render_placements"]["chest"]
                self.assertIsNone(chest["modeler_sidecar_variant_key"])
                self.assertNotEqual(chest["target_size_array_m"], [9.0, 9.0, 9.0])


if __name__ == "__main__":
    unittest.main()
