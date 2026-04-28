import unittest

from henshin.armor_fit_contract import (
    ARMOR_SLOT_SPECS,
    MAJOR_ARMOR_SLOTS,
    audit_armor_fit_slots,
    normalize_slot_id,
    recommend_scale_for_height_cm,
    recommend_slot_scales,
    to_runtime_visual_layers,
)
from henshin.runtime_package import build_runtime_suit_package


class TestArmorFitContract(unittest.TestCase):
    def test_major_slots_expose_body_fit_fields(self) -> None:
        self.assertEqual(
            MAJOR_ARMOR_SLOTS,
            (
                "helmet",
                "chest",
                "back",
                "shoulder_l",
                "shoulder_r",
                "upperarm_l",
                "upperarm_r",
                "forearm_l",
                "forearm_r",
                "hand_l",
                "hand_r",
                "thigh_l",
                "thigh_r",
                "shin_l",
                "shin_r",
                "boot_l",
                "boot_r",
                "belt",
            ),
        )
        for slot_id, spec in ARMOR_SLOT_SPECS.items():
            payload = spec.to_dict()
            self.assertEqual(payload["slot_id"], slot_id)
            self.assertIsInstance(payload["body_anchor"], str)
            self.assertIsInstance(payload["coverage"], list)
            self.assertLess(payload["min_scale"], payload["max_scale"])
            self.assertIsInstance(payload["display_label"], str)

        self.assertEqual(ARMOR_SLOT_SPECS["shoulder_l"].mirror_pair, "shoulder_r")
        self.assertEqual(ARMOR_SLOT_SPECS["upperarm_l"].runtime_part_id, "left_upperarm")
        self.assertEqual(ARMOR_SLOT_SPECS["belt"].body_anchor, "hips")

    def test_height_recommendation_is_slot_clamped(self) -> None:
        self.assertEqual(recommend_scale_for_height_cm(170, "helmet"), 1.0)
        self.assertEqual(recommend_scale_for_height_cm(230, "helmet"), 1.18)

        scales = recommend_slot_scales(182, ["helmet", "chest", "left_shoulder"])

        self.assertEqual(scales["helmet"], 1.0706)
        self.assertEqual(scales["shoulder_l"], 1.0706)
        self.assertEqual(recommend_slot_scales(170, "helmet"), {"helmet": 1.0})

    def test_slot_audit_detects_required_and_mirror_gaps(self) -> None:
        audit = audit_armor_fit_slots(["helmet", "chest", "shoulder_l"])

        self.assertFalse(audit["ok"])
        self.assertEqual(audit["missing_required_slots"], ["back"])
        self.assertEqual(
            audit["missing_mirror_pairs"],
            [{"slot": "shoulder_l", "missing": "shoulder_r", "pair": ["shoulder_l", "shoulder_r"]}],
        )

    def test_existing_suitspec_part_aliases_normalize_to_contract_slots(self) -> None:
        self.assertEqual(normalize_slot_id("left_shoulder"), "shoulder_l")
        self.assertEqual(normalize_slot_id("left_upperarm"), "upperarm_l")
        self.assertEqual(normalize_slot_id("right_upperarm"), "upperarm_r")
        self.assertEqual(normalize_slot_id("waist"), "belt")

        audit = audit_armor_fit_slots(["left_shoulder", "right_shoulder", "left_upperarm", "right_upperarm", "waist"])

        self.assertEqual(audit["selected_slots"], ["shoulder_l", "shoulder_r", "upperarm_l", "upperarm_r", "belt"])
        self.assertEqual(audit["missing_mirror_pairs"], [])

    def test_runtime_visual_layers_match_runtime_package_shape(self) -> None:
        visual_layers = to_runtime_visual_layers(
            182,
            ["helmet", "chest", "back", "shoulder_l", "shoulder_r", "belt"],
            vrm_baseline_ref="viewer/assets/vrm/custom.vrm",
        )

        self.assertEqual(visual_layers["contract_version"], "base-suit-overlay.v1")
        self.assertEqual(visual_layers["base_suit"]["layer_id"], "base_suit_surface")
        self.assertEqual(visual_layers["base_suit"]["kind"], "vrm_body_surface")
        self.assertEqual(visual_layers["base_suit"]["asset_ref"], "viewer/assets/vrm/custom.vrm")
        self.assertEqual(visual_layers["armor_overlay"]["layer_id"], "armor_overlay_parts")
        self.assertEqual(
            visual_layers["armor_overlay"]["selected_parts"],
            ["helmet", "chest", "back", "left_shoulder", "right_shoulder", "waist"],
        )
        self.assertEqual(visual_layers["armor_overlay"]["slot_ids"][-1], "belt")
        self.assertEqual(visual_layers["body_fit_contract"]["recommended_scales"]["chest"], 1.0706)

        suitspec = {
            "schema_version": "0.2",
            "body_profile": {"height_cm": 182, "vrm_baseline_ref": "viewer/assets/vrm/custom.vrm"},
            "modules": {
                part: {"enabled": True, "asset_ref": f"viewer/assets/meshes/{part}.mesh.json"}
                for part in visual_layers["armor_overlay"]["selected_parts"]
            },
        }
        package = build_runtime_suit_package(suitspec=suitspec, visual_layers=visual_layers)

        self.assertEqual(package["visual_layers"]["armor_overlay"]["selected_parts"], visual_layers["armor_overlay"]["selected_parts"])
        self.assertEqual(package["visual_layers"]["armor_overlay"]["part_count"], 6)
        self.assertEqual(package["body_fit_contract"]["height_scale"], 1.0706)
        self.assertEqual(
            [slot["slot_id"] for slot in package["visual_layers"]["armor_overlay"]["body_fit_slots"]],
            ["helmet", "chest", "back", "left_shoulder", "right_shoulder", "waist"],
        )
        self.assertEqual(
            [slot["body_fit_slot_id"] for slot in package["visual_layers"]["armor_overlay"]["body_fit_slots"]],
            ["helmet", "chest", "back", "shoulder_l", "shoulder_r", "belt"],
        )
        self.assertTrue(package["runtime_checks"]["can_render_runtime_suit"])


if __name__ == "__main__":
    unittest.main()
