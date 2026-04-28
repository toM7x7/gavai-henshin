import unittest

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
                "vrm_anchor": {"bone": "chest"},
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


if __name__ == "__main__":
    unittest.main()
