import unittest

from tools.export_modeler_fit_adjustments import fit_adjustments_from_report


class TestExportModelerFitAdjustments(unittest.TestCase):
    def test_bbox_warning_becomes_micro_adjustment(self) -> None:
        report = {
            "bbox_warning_summary": [
                {
                    "module": "chest",
                    "status": "warn",
                    "axes": ["z"],
                    "max_abs_delta_pct": 12.7,
                    "actual_bbox_m": {"z": 0.142398},
                    "target_bbox_m": {"z": 0.1632},
                    "axis_acceptance": {
                        "z": {
                            "actual_m": 0.142398,
                            "target_m": 0.1632,
                            "minimum_change_to_pass_m": 0.004482,
                        }
                    },
                }
            ]
        }

        adjustments = fit_adjustments_from_report(report)

        self.assertEqual(len(adjustments), 1)
        self.assertEqual(adjustments[0]["module"], "chest")
        self.assertIn("胸部装甲", adjustments[0]["display_name"])
        self.assertIn("側面/3Q", adjustments[0]["triview_proof"])
        self.assertEqual(adjustments[0]["priority"], "P0")
        self.assertEqual(adjustments[0]["adjustment_contract"], "modeler-fit-adjustments.v0.2")
        self.assertEqual(
            adjustments[0]["affected_fidelity_hold_variants"],
            ["chest:rescue_wrap", "chest:emerald_v_core", "chest:oath_core_shell"],
        )
        self.assertEqual(adjustments[0]["fidelity_hold_relation"], "direct_variant_scope")
        self.assertEqual(adjustments[0]["placement_nudges"][0]["axis"], "z")
        self.assertEqual(adjustments[0]["placement_nudges"][0]["max_mm"], 2.0)
        self.assertIn("Suit Forge", adjustments[0]["route_gate"]["web"])
        self.assertIn("Henshin Trial", adjustments[0]["route_gate"]["quest"])
        self.assertIn("Replay Archive", adjustments[0]["route_gate"]["replay"])
        self.assertEqual(adjustments[0]["acceptance"]["bbox_warning_count_target"], 0)
        self.assertEqual(adjustments[0]["acceptance"]["sidecar_glb_bbox_match_max_m"], 0.002)
        task = adjustments[0]["size_tasks"][0]
        self.assertEqual(task["axis"], "z")
        self.assertEqual(task["axis_label"], "奥行き")
        self.assertEqual(task["minimum_to_pass_mm"], 4.5)
        self.assertEqual(task["pass_min_mm"], 0.0)
        self.assertEqual(task["pass_max_mm"], 0.0)
        self.assertEqual(task["recommended_demo_delta_mm"], 6.1)
        self.assertEqual(task["recommended_demo_target_mm"], 148.4)
        self.assertEqual(task["target_delta_mm"], 20.8)
        self.assertGreater(task["axis_scale_factor"], 1.0)

    def test_pair_module_gets_pair_gate_and_future_variant_relation(self) -> None:
        report = {
            "bbox_warning_summary": [
                {
                    "module": "left_upperarm",
                    "status": "warn",
                    "axes": ["x"],
                    "actual_bbox_m": {"x": 0.096304},
                    "target_bbox_m": {"x": 0.1088},
                    "axis_acceptance": {
                        "x": {
                            "actual_m": 0.096304,
                            "target_m": 0.1088,
                            "pass_min_m": 0.09792,
                            "pass_max_m": 0.11968,
                            "minimum_change_to_pass_m": 0.001616,
                        }
                    },
                }
            ]
        }

        adjustments = fit_adjustments_from_report(report)

        self.assertEqual(adjustments[0]["pair_group"], "upperarm_pair")
        self.assertEqual(adjustments[0]["affected_fidelity_hold_variants"], [])
        self.assertEqual(
            adjustments[0]["fidelity_hold_relation"],
            "base_fit_rule_for_missing_or_future_line_variants",
        )
        self.assertEqual(adjustments[0]["acceptance"]["mirror_pair_max_delta_pct"], 3.0)
        task = adjustments[0]["size_tasks"][0]
        self.assertEqual(task["pass_min_mm"], 97.9)
        self.assertEqual(task["pass_max_mm"], 119.7)
        self.assertEqual(task["recommended_demo_target_mm"], 99.4)

    def test_empty_report_has_no_tasks(self) -> None:
        self.assertEqual(fit_adjustments_from_report({"bbox_warning_summary": []}), [])


if __name__ == "__main__":
    unittest.main()
