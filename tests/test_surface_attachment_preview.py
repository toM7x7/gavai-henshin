import json
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_node_module(source: str) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", source],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class TestSurfaceAttachmentPreview(unittest.TestCase):
    def test_preview_reports_mount_and_proxy_status_without_geometry(self) -> None:
        script = textwrap.dedent(
            """
            import { buildSurfaceAttachmentPreview } from "./viewer/shared/surface-attachment-preview.js";
            import {
              effectiveVrmAnchorFor,
              normalizeAttachmentSlot,
            } from "./viewer/shared/armor-canon.js";

            const suitspec = {
              modules: {
                helmet: {},
                chest: {},
                left_upperarm: {},
                left_hand: { attachment_slot: "hand_l" },
                mystery_plate: { attachment_slot: "mystery_plate" },
                right_shin: { enabled: false },
              },
            };
            const snapshot = {
              regionCounts: {
                head: 6,
                torso: 12,
                left_upperarm: 5,
                left_forearm: 4,
              },
              nodes: [],
              mounts: [
                { name: "head_crown", region: "head" },
                { name: "chest_front", region: "torso" },
              ],
            };
            const preview = buildSurfaceAttachmentPreview({
              suitspec,
              snapshot,
              trackingSource: "vrm",
              normalizeAttachmentSlot,
              effectiveVrmAnchorFor,
            });
            console.log(JSON.stringify(preview));
            """
        )
        preview = run_node_module(script)

        self.assertEqual(preview["schema_version"], "surface_attachment_preview.v0")
        self.assertEqual(preview["mode"], "telemetry_only")
        self.assertFalse(preview["applies_to_quest"])
        self.assertEqual(preview["part_count"], 6)
        self.assertEqual(sum(preview["status_counts"].values()), preview["part_count"])

        by_part = {binding["part"]: binding for binding in preview["bindings"]}
        self.assertEqual(by_part["helmet"]["status"], "matched_mount")
        self.assertEqual(by_part["helmet"]["anchor_bone"], "head")
        self.assertEqual(by_part["helmet"]["expected_region"], "head")
        self.assertEqual(by_part["chest"]["status"], "matched_mount")
        self.assertEqual(by_part["left_upperarm"]["status"], "proxy_region_only")
        self.assertEqual(by_part["left_hand"]["attachment_slot"], "left_hand")
        self.assertEqual(by_part["left_hand"]["expected_region"], "left_forearm")
        self.assertEqual(by_part["left_hand"]["status"], "proxy_region_only")
        self.assertEqual(by_part["mystery_plate"]["status"], "missing_surface_region")
        self.assertIn("mystery_plate", preview["missing_parts"])
        self.assertEqual(by_part["right_shin"]["status"], "not_enabled")

        forbidden_geometry_keys = {"position", "normal", "offset", "scale", "fit"}
        for binding in preview["bindings"]:
            self.assertFalse(forbidden_geometry_keys.intersection(binding.keys()))


if __name__ == "__main__":
    unittest.main()
