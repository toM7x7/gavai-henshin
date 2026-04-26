import json
import unittest
from pathlib import Path


class TestSampleSuitspec(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(".").resolve()
        self.sample_path = self.repo_root / "examples" / "suitspec.sample.json"
        self.sample = json.loads(self.sample_path.read_text(encoding="utf-8"))

    def test_boot_modules_use_shin_segments_and_foot_anchors(self) -> None:
        for part_name, source_name in (("left_boot", "left_shin"), ("right_boot", "right_shin")):
            module = self.sample["modules"][part_name]
            self.assertEqual(module["fit"]["source"], source_name)
            self.assertEqual(module["fit"]["attach"], "end")
            self.assertIn(module["vrm_anchor"]["bone"], ("leftFoot", "rightFoot"))
            self.assertLess(abs(float(module["vrm_anchor"]["offset"][1])), 0.1)

    def test_hand_modules_use_hand_segments_and_compact_anchors(self) -> None:
        for part_name, source_name in (("left_hand", "left_hand"), ("right_hand", "right_hand")):
            module = self.sample["modules"][part_name]
            self.assertEqual(module["fit"]["source"], source_name)
            self.assertEqual(module["fit"]["attach"], "center")
            self.assertLess(abs(float(module["vrm_anchor"]["offset"][0])), 0.1)

    def test_sample_declares_fit_and_texture_fallback_contracts(self) -> None:
        self.assertEqual(self.sample["fit_contract"]["module_fit_stage"], "calibrated_body_fit")
        self.assertEqual(self.sample["fit_contract"]["module_fit_space"], "body_sim_segment")
        self.assertEqual(self.sample["texture_fallback"]["mode"], "palette_material")
        self.assertEqual(self.sample["texture_fallback"]["source"], "palette")


if __name__ == "__main__":
    unittest.main()
