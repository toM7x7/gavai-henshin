import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "audit_quest_armor_whole_suit.py"
SPEC = importlib.util.spec_from_file_location("audit_quest_armor_whole_suit", TOOL_PATH)
whole_suit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = whole_suit
SPEC.loader.exec_module(whole_suit)


def _write_runtime(
    path: Path,
    parts: list[str],
    poses: dict,
    adjustments: dict,
    sizes: dict,
    human_anchors: dict | None = None,
) -> None:
    lines = [
        f"const ARMOR_PARTS = {json.dumps(parts)};",
        f"const VR_BODY_PART_POSES = {_js_object(poses)};",
        f"const QUEST_ASSEMBLY_ADJUSTMENTS = {_js_object(adjustments)};",
    ]
    if human_anchors is not None:
        lines.append(f"const QUEST_HUMAN_ANCHOR_CONTRACT = {_js_object(human_anchors)};")
    lines.append(f"const QUEST_GLB_TARGET_SIZES = {_js_object(sizes)};")
    path.write_text("\n".join(lines), encoding="utf-8")


def _js_object(payload: dict) -> str:
    items = []
    for key, value in payload.items():
        items.append(f"{key}: {json.dumps(value)}")
    return "{ " + ", ".join(items) + " }"


def _write_asset_pair(root: Path, part: str) -> None:
    part_dir = root / part
    part_dir.mkdir(parents=True, exist_ok=True)
    (part_dir / f"{part}.glb").write_bytes(b"placeholder")
    (part_dir / f"{part}.modeler.json").write_text("{}", encoding="utf-8")


class TestQuestArmorWholeSuitAudit(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_current_quest_contract_reports_all_parts_without_obvious_interpenetration(self) -> None:
        audit = whole_suit.collect_whole_suit_audit(
            self.repo_root / "viewer/quest-iw-demo/quest-demo.js",
            self.repo_root / "viewer/assets/armor-parts",
        )

        self.assertEqual(audit["contract_version"], "quest-armor-whole-suit-audit.v1")
        self.assertEqual(audit["expected_part_count"], 18)
        self.assertEqual(audit["part_count"], 18)
        self.assertEqual(audit["missing_pose_parts"], [])
        self.assertEqual(audit["missing_target_size_parts"], [])
        self.assertEqual(audit["missing_asset_parts"], [])
        self.assertEqual(audit["obvious_interpenetrations"], [])
        self.assertEqual(audit["status"], "pass", audit["failure_reasons"])
        self.assertEqual(audit["audit_scope"]["geometry_basis"], "target-contract-only")
        self.assertEqual(audit["audit_scope"]["asset_validation"], "existence-only")
        self.assertIn("actual GLB mesh dimensions or bounds", audit["audit_scope"]["pass_does_not_guarantee"])
        self.assertFalse(audit["asset_check_summary"]["glb_dimensions_verified"])
        self.assertEqual(audit["asset_check_summary"]["validation_scope"], "existence-only")
        self.assertTrue(all(item["validation_scope"] == "existence-only" for item in audit["asset_checks"]))
        self.assertTrue(all(item["glb_dimensions_verified"] is False for item in audit["asset_checks"]))
        self.assertTrue(all(item["status"] == "pass" for item in audit["symmetry_checks"]))
        self.assertTrue(all(item["status"] == "pass" for item in audit["human_fit_distances_m"]))
        self.assertTrue(all(item["validation_scope"] == "primary-axis-only" for item in audit["human_fit_distances_m"]))
        helmet_link = next(item for item in audit["human_fit_distances_m"] if item["name"] == "helmet_to_chest")
        self.assertEqual(helmet_link["unchecked_secondary_axes"], ["x", "z"])
        self.assertIn("secondary axes", helmet_link["secondary_axis_note"])
        anchor_contract = audit["human_anchor_contract"]
        self.assertEqual(anchor_contract["contract_version"], "quest-human-anchor-contract.v1")
        self.assertEqual(anchor_contract["status"], "pass")
        self.assertEqual(anchor_contract["inference_basis"], "runtime-contract+part-name-derived")
        self.assertEqual(anchor_contract["coverage_summary"]["runtime_anchor_center_count"], 18)
        self.assertEqual(anchor_contract["semantic_failures"], [])
        self.assertEqual(anchor_contract["coverage_summary"]["missing_required_parts"], [])
        self.assertEqual(anchor_contract["coverage_summary"]["unknown_anchor_parts"], [])
        self.assertTrue(all(item["status"] == "pass" for item in anchor_contract["chain_checks"]))
        helmet_anchor = next(item for item in anchor_contract["anchors"] if item["part"] == "helmet")
        self.assertEqual(helmet_anchor["human_anchor"], "head")
        self.assertEqual(helmet_anchor["body_chain"], "head_torso")
        chest_anchor = next(item for item in anchor_contract["anchors"] if item["part"] == "chest")
        self.assertEqual(chest_anchor["human_anchor"], "front_upper_torso")
        self.assertEqual(chest_anchor["runtime_anchor"], "upper_torso_front")
        self.assertEqual(chest_anchor["center_source"], "QUEST_HUMAN_ANCHOR_CONTRACT.center_m")
        self.assertEqual(chest_anchor["center_m"], [0.0, -0.52, -0.42])
        left_upperarm_anchor = next(item for item in anchor_contract["anchors"] if item["part"] == "left_upperarm")
        self.assertEqual(left_upperarm_anchor["human_anchor"], "left_upper_arm")
        self.assertEqual(left_upperarm_anchor["mirror_part"], "right_upperarm")
        self.assertLess(left_upperarm_anchor["center_m"][0], 0)

    def test_runtime_human_anchor_contract_center_overrides_fallback_pose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "quest-demo.js"
            _write_runtime(
                runtime,
                ["helmet", "chest"],
                {
                    "helmet": [9, 9, 9],
                    "chest": [8, 8, 8],
                },
                {},
                {
                    "helmet": [0.25, 0.34, 0.25],
                    "chest": [0.48, 0.38, 0.13],
                },
                {
                    "helmet": {
                        "anchor": "head",
                        "side": "center",
                        "wearIntent": "helmet surrounds the skull",
                        "center_m": [0, -0.04, -0.22],
                    },
                    "chest": {
                        "anchor": "upper_torso_front",
                        "side": "center",
                        "wearIntent": "front armor over ribs",
                        "center_m": [0, -0.49, -0.36],
                    },
                },
            )

            audit = whole_suit.collect_whole_suit_audit(runtime, armor_root=None)

        chest = next(item for item in audit["parts"] if item["part"] == "chest")
        self.assertEqual(chest["center_source"], "QUEST_HUMAN_ANCHOR_CONTRACT.center_m")
        self.assertEqual(chest["center_m"], [0.0, -0.49, -0.36])
        contract = audit["human_anchor_contract"]
        self.assertEqual(contract["inference_basis"], "runtime-contract+part-name-derived")
        chest_anchor = next(item for item in contract["anchors"] if item["part"] == "chest")
        self.assertEqual(chest_anchor["runtime_wear_intent"], "front armor over ribs")

    def test_human_anchor_semantic_errors_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "quest-demo.js"
            _write_runtime(
                runtime,
                ["chest", "back", "left_hand", "right_hand"],
                {
                    "chest": [0, -0.52, 0.2],
                    "back": [0, -0.52, -0.2],
                    "left_hand": [0.35, -1.1, -0.36],
                    "right_hand": [-0.35, -1.1, -0.36],
                },
                {},
                {
                    "chest": [0.48, 0.38, 0.13],
                    "back": [0.46, 0.4, 0.14],
                    "left_hand": [0.095, 0.07, 0.11],
                    "right_hand": [0.095, 0.07, 0.11],
                },
            )

            audit = whole_suit.collect_whole_suit_audit(runtime, armor_root=None)

        self.assertEqual(audit["status"], "fail")
        semantic = "\n".join(audit["human_anchor_contract"]["semantic_failures"])
        self.assertIn("left_hand x should be negative", semantic)
        self.assertIn("right_hand x should be positive", semantic)
        self.assertIn("chest should sit in front of back", semantic)

    def test_missing_pose_size_and_assets_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runtime = tmp_path / "quest-demo.js"
            armor_root = tmp_path / "armor-parts"
            _write_runtime(
                runtime,
                ["helmet", "chest", "left_hand", "right_hand"],
                {
                    "helmet": [0, -0.04, -0.2],
                    "chest": [0, -0.52, -0.32],
                    "left_hand": [-0.5, -1.1, -0.36],
                },
                {},
                {
                    "helmet": [0.25, 0.34, 0.25],
                    "chest": [0.48, 0.38, 0.13],
                    "right_hand": [0.095, 0.07, 0.11],
                },
            )
            _write_asset_pair(armor_root, "helmet")

            audit = whole_suit.collect_whole_suit_audit(runtime, armor_root)

        self.assertEqual(audit["status"], "fail")
        self.assertEqual(audit["missing_pose_parts"], ["right_hand"])
        self.assertEqual(audit["missing_target_size_parts"], ["left_hand"])
        self.assertIn("chest", audit["missing_asset_parts"])
        self.assertIn("left_hand", audit["missing_asset_parts"])

    def test_non_seam_overlap_is_obvious_interpenetration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "quest-demo.js"
            _write_runtime(
                runtime,
                ["chest", "left_shin"],
                {
                    "chest": [0, -0.52, -0.32],
                    "left_shin": [0, -0.52, -0.32],
                },
                {},
                {
                    "chest": [0.48, 0.38, 0.13],
                    "left_shin": [0.48, 0.38, 0.13],
                },
            )

            audit = whole_suit.collect_whole_suit_audit(runtime, armor_root=None)

        self.assertEqual(audit["status"], "fail")
        self.assertEqual(len(audit["obvious_interpenetrations"]), 1)
        self.assertEqual(
            audit["obvious_interpenetrations"][0]["pair"],
            ["chest", "left_shin"],
        )

    def test_symmetry_error_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "quest-demo.js"
            _write_runtime(
                runtime,
                ["left_hand", "right_hand"],
                {
                    "left_hand": [-0.5, -1.1, -0.36],
                    "right_hand": [0.62, -1.1, -0.36],
                },
                {},
                {
                    "left_hand": [0.095, 0.07, 0.11],
                    "right_hand": [0.095, 0.07, 0.11],
                },
            )

            audit = whole_suit.collect_whole_suit_audit(runtime, armor_root=None)

        hand_check = next(item for item in audit["symmetry_checks"] if item["pair"] == ["left_hand", "right_hand"])
        self.assertEqual(audit["status"], "fail")
        self.assertEqual(hand_check["status"], "fail")
        self.assertAlmostEqual(hand_check["center_delta_m"]["mirror_x_error"], 0.12)

    def test_unknown_part_name_is_reported_in_human_anchor_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "quest-demo.js"
            _write_runtime(
                runtime,
                ["helmet", "mystery_plate"],
                {
                    "helmet": [0, -0.04, -0.2],
                    "mystery_plate": [0, -0.55, -0.3],
                },
                {},
                {
                    "helmet": [0.25, 0.34, 0.25],
                    "mystery_plate": [0.2, 0.2, 0.2],
                },
            )

            audit = whole_suit.collect_whole_suit_audit(runtime, armor_root=None)

        self.assertEqual(audit["status"], "fail")
        contract = audit["human_anchor_contract"]
        self.assertEqual(contract["status"], "fail")
        self.assertIn("mystery_plate", contract["coverage_summary"]["unknown_anchor_parts"])
        unknown_anchor = next(item for item in contract["anchors"] if item["part"] == "mystery_plate")
        self.assertEqual(unknown_anchor["inference_status"], "unknown")
        self.assertIsNone(unknown_anchor["human_anchor"])

    def test_cli_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audit.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL_PATH),
                    "--output",
                    str(output),
                ],
                cwd=self.repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["contract_version"], "quest-armor-whole-suit-audit.v1")
        self.assertEqual(payload["audit_scope"]["geometry_basis"], "target-contract-only")
        self.assertFalse(payload["asset_check_summary"]["glb_dimensions_verified"])
        self.assertEqual(payload["human_anchor_contract"]["status"], "pass")
        self.assertEqual(payload["human_anchor_contract"]["inference_basis"], "runtime-contract+part-name-derived")
        self.assertIn("human_fit_distances_m", payload)
        self.assertIn("symmetry_checks", payload)

    def test_cli_writes_markdown_report_with_scope_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "audit.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(TOOL_PATH),
                    "--format",
                    "markdown",
                    "--output",
                    str(output),
                ],
                cwd=self.repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")

        self.assertIn("# Quest Whole-Suit Armor Audit", markdown)
        self.assertIn("target-contract-only", markdown)
        self.assertIn("GLB dimensions verified: `false`", markdown)
        self.assertIn("primary-axis checks", markdown)
        self.assertIn("## Human anchor contract", markdown)
        self.assertIn("runtime-contract+part-name-derived", markdown)
        self.assertIn("left_shoulder_girdle", markdown)


if __name__ == "__main__":
    unittest.main()
