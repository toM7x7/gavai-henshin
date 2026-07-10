import json
import subprocess
import textwrap
import unittest
from pathlib import Path

from henshin.armor_fit_contract import (
    BODY_SURFACE_FIT_POLICIES,
    clamp_surface_offset_for_part,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _python_surface_policies():
    return {
        part: {
            "role": policy["role"],
            "vrm_offset_clamp_m": policy.get("vrm_offset_clamp_m", {}),
            "quest_offset_clamp_m": policy.get("quest_offset_clamp_m", {}),
            "target_contact": policy["target_contact"],
        }
        for part, policy in BODY_SURFACE_FIT_POLICIES.items()
    }


def _javascript_surface_contract():
    script = textwrap.dedent(
        """
        import {
          BODY_SURFACE_FIT_POLICIES,
          clampSurfaceOffsetForPart,
        } from './viewer/shared/armor-canon.js';

        const normalizeClamp = (clamp) => {
          if (!clamp) return {};
          return {
            x: clamp.x,
            y: clamp.y,
            z: clamp.z,
          };
        };

        const policies = Object.fromEntries(
          Object.entries(BODY_SURFACE_FIT_POLICIES).map(([part, policy]) => [
            part,
            {
              role: policy.role,
              vrm_offset_clamp_m: normalizeClamp(policy.vrmOffsetClamp),
              quest_offset_clamp_m: normalizeClamp(policy.questOffsetClamp),
              target_contact: policy.targetContact,
            },
          ])
        );

        const samples = {
          chest_vrm: clampSurfaceOffsetForPart('chest', [0.2, -0.2, 0.2], 'vrm'),
          chest_quest: clampSurfaceOffsetForPart('chest', [0.2, -0.2, 0.2], 'quest'),
          helmet_vrm: clampSurfaceOffsetForPart('helmet', [0, 0, 0], 'vrm'),
          helmet_quest: clampSurfaceOffsetForPart('helmet', [0, 0, 0], 'quest'),
          left_hand_vrm: clampSurfaceOffsetForPart('left_hand', [0.02, -0.05, 0.05], 'vrm'),
          left_hand_quest: clampSurfaceOffsetForPart('left_hand', [0.02, -0.05, 0.05], 'quest'),
          unknown_vrm: clampSurfaceOffsetForPart('unknown_part', [0.1, -0.2, 0.3], 'vrm'),
        };

        console.log(JSON.stringify({ policies, samples }));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


class BodySurfacePolicyParityTest(unittest.TestCase):
    def test_python_and_javascript_surface_policy_keys_and_values_match(self):
        js_contract = _javascript_surface_contract()
        python_policies = _python_surface_policies()

        self.assertEqual(set(js_contract["policies"]), set(python_policies))
        self.assertEqual(js_contract["policies"], python_policies)

    def test_python_and_javascript_surface_offset_clamps_match(self):
        js_contract = _javascript_surface_contract()
        expected_samples = {
            "chest_vrm": clamp_surface_offset_for_part("chest", [0.2, -0.2, 0.2], space="vrm"),
            "chest_quest": clamp_surface_offset_for_part("chest", [0.2, -0.2, 0.2], space="quest"),
            "helmet_vrm": clamp_surface_offset_for_part("helmet", [0, 0, 0], space="vrm"),
            "helmet_quest": clamp_surface_offset_for_part("helmet", [0, 0, 0], space="quest"),
            "left_hand_vrm": clamp_surface_offset_for_part("left_hand", [0.02, -0.05, 0.05], space="vrm"),
            "left_hand_quest": clamp_surface_offset_for_part("left_hand", [0.02, -0.05, 0.05], space="quest"),
            "unknown_vrm": clamp_surface_offset_for_part(
                "unknown_part",
                [0.1, -0.2, 0.3],
                space="vrm",
            ),
        }

        self.assertEqual(js_contract["samples"], expected_samples)


if __name__ == "__main__":
    unittest.main()
