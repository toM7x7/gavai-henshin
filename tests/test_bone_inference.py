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


class TestBoneInference(unittest.TestCase):
    def test_named_bones_support_mocopi_style_aliases(self) -> None:
        script = textwrap.dedent(
            """
            import {
              createBoneInferenceSnapshot,
              inferCanonicalJointsFromNamedBones,
            } from "./viewer/shared/bone-inference.js";

            const namedBones = {
              Head: { x: 0.0, y: 1.72, z: 0.28 },
              Neck: { x: 0.0, y: 1.56, z: 0.25 },
              LeftShoulder: { x: -0.22, y: 1.48, z: 0.22 },
              RightShoulder: { x: 0.22, y: 1.48, z: 0.22 },
              LeftLowerArm: { x: -0.56, y: 1.18, z: 0.2 },
              RightLowerArm: { x: 0.56, y: 1.18, z: 0.2 },
              LeftHand: { x: -0.74, y: 0.96, z: 0.22 },
              RightHand: { x: 0.74, y: 0.96, z: 0.22 },
              Pelvis: { x: 0.0, y: 0.96, z: 0.2 },
              LeftUpperLeg: { x: -0.14, y: 0.92, z: 0.2 },
              RightUpperLeg: { x: 0.14, y: 0.92, z: 0.2 },
              LeftLowerLeg: { x: -0.14, y: 0.48, z: 0.2 },
              RightLowerLeg: { x: 0.14, y: 0.48, z: 0.2 },
              LeftFoot: { x: -0.14, y: 0.08, z: 0.24 },
              RightFoot: { x: 0.14, y: 0.08, z: 0.24 },
              LeftToeBase: { x: -0.14, y: -0.02, z: 0.38 },
              RightToeBase: { x: 0.14, y: -0.02, z: 0.38 },
            };

            const joints = inferCanonicalJointsFromNamedBones(namedBones);
            const snapshot = createBoneInferenceSnapshot({ joints, source: "mocopi-like" });
            console.log(JSON.stringify({
              reliableJointCount: snapshot.reliableJointCount,
              shoulderWidth: snapshot.metrics.shoulderWidth,
              torsoLen: snapshot.metrics.torsoLen,
              footLen: snapshot.metrics.footLen,
              hasSolvedTorsoAnchors: snapshot.hasSolvedTorsoAnchors,
              fitReadiness: snapshot.fitReadiness,
              qualityLabel: snapshot.qualityLabel,
              shapeProfileLabel: snapshot.shapeProfile.label,
              leftHip: snapshot.joints.left_hip,
              rightHip: snapshot.joints.right_hip,
            }));
            """
        )
        output = run_node_module(script)
        self.assertEqual(output["reliableJointCount"], 12)
        self.assertTrue(output["hasSolvedTorsoAnchors"])
        self.assertAlmostEqual(output["shoulderWidth"], 0.44, places=3)
        self.assertGreater(output["torsoLen"], 0.45)
        self.assertGreater(output["footLen"], 0.12)
        self.assertEqual(output["fitReadiness"], "fit-ready")
        self.assertEqual(output["qualityLabel"], "good")
        self.assertIn(output["shapeProfileLabel"], {"broad", "balanced", "lean"})
        self.assertAlmostEqual(output["leftHip"]["x"], -0.14, places=3)
        self.assertAlmostEqual(output["rightHip"]["x"], 0.14, places=3)

    def test_pose_landmarks_map_to_canonical_joints(self) -> None:
        script = textwrap.dedent(
            """
            import {
              POSE_LANDMARK_IDX,
              createBoneInferenceSnapshot,
              inferCanonicalJointsFromPoseLandmarks,
            } from "./viewer/shared/bone-inference.js";

            const landmarks = Array.from({ length: 33 }, () => null);
            const put = (idx, x, y, z = 0.0) => {
              landmarks[idx] = { x, y, z, visibility: 0.99, presence: 0.99 };
            };
            put(POSE_LANDMARK_IDX.NOSE, 0.50, 0.18, -0.08);
            put(POSE_LANDMARK_IDX.LEFT_SHOULDER, 0.64, 0.34, -0.04);
            put(POSE_LANDMARK_IDX.RIGHT_SHOULDER, 0.36, 0.34, -0.04);
            put(POSE_LANDMARK_IDX.LEFT_ELBOW, 0.72, 0.48, -0.02);
            put(POSE_LANDMARK_IDX.RIGHT_ELBOW, 0.28, 0.48, -0.02);
            put(POSE_LANDMARK_IDX.LEFT_WRIST, 0.78, 0.62, 0.02);
            put(POSE_LANDMARK_IDX.RIGHT_WRIST, 0.22, 0.62, 0.02);
            put(POSE_LANDMARK_IDX.LEFT_HIP, 0.58, 0.58, 0.0);
            put(POSE_LANDMARK_IDX.RIGHT_HIP, 0.42, 0.58, 0.0);
            put(POSE_LANDMARK_IDX.LEFT_KNEE, 0.58, 0.78, 0.02);
            put(POSE_LANDMARK_IDX.RIGHT_KNEE, 0.42, 0.78, 0.02);
            put(POSE_LANDMARK_IDX.LEFT_ANKLE, 0.58, 0.94, 0.08);
            put(POSE_LANDMARK_IDX.RIGHT_ANKLE, 0.42, 0.94, 0.08);

            const joints = inferCanonicalJointsFromPoseLandmarks(landmarks, { mirror: true });
            const snapshot = createBoneInferenceSnapshot({
              joints,
              source: "webcam",
              options: {
                syntheticTorsoDropRatio: 1.35,
                syntheticHipWidthRatio: 0.72,
              },
            });
            console.log(JSON.stringify({
              reliableJointCount: snapshot.reliableJointCount,
              hasMeasuredTorsoAnchors: snapshot.hasMeasuredTorsoAnchors,
              shoulderWidth: snapshot.metrics.shoulderWidth,
              upperArmLen: snapshot.metrics.upperArmLen,
              fitReadiness: snapshot.fitReadiness,
              fitReadinessScore: snapshot.fitReadinessScore,
              leftShoulder: snapshot.joints.left_shoulder,
              shouldersCenter: snapshot.joints.shoulders_center,
            }));
            """
        )
        output = run_node_module(script)
        self.assertEqual(output["reliableJointCount"], 13)
        self.assertTrue(output["hasMeasuredTorsoAnchors"])
        self.assertGreater(output["shoulderWidth"], 0.5)
        self.assertGreater(output["upperArmLen"], 0.2)
        self.assertEqual(output["fitReadiness"], "fit-ready")
        self.assertGreater(output["fitReadinessScore"], 0.7)
        self.assertLess(output["leftShoulder"]["x"], output["shouldersCenter"]["x"])

    def test_upper_body_only_readiness_when_hips_are_missing(self) -> None:
        script = textwrap.dedent(
            """
            import { createBoneInferenceSnapshot } from "./viewer/shared/bone-inference.js";

            const snapshot = createBoneInferenceSnapshot({
              source: "upper-only",
              joints: {
                left_shoulder: { x: -0.26, y: 1.2, z: 0.2 },
                right_shoulder: { x: 0.26, y: 1.2, z: 0.2 },
                left_elbow: { x: -0.48, y: 0.96, z: 0.22 },
                right_elbow: { x: 0.48, y: 0.96, z: 0.22 },
                left_wrist: { x: -0.64, y: 0.76, z: 0.24 },
                right_wrist: { x: 0.64, y: 0.76, z: 0.24 },
                nose: { x: 0.0, y: 1.44, z: 0.24 },
              },
            });
            console.log(JSON.stringify({
              fitReadiness: snapshot.fitReadiness,
              fitReadinessReasons: snapshot.fitReadinessReasons,
              hasSolvedTorsoAnchors: snapshot.hasSolvedTorsoAnchors,
              hasUpperBodyAnchors: snapshot.hasUpperBodyAnchors,
            }));
            """
        )
        output = run_node_module(script)
        self.assertEqual(output["fitReadiness"], "upper-body-only")
        self.assertIn("synthetic_torso", output["fitReadinessReasons"])
        self.assertTrue(output["hasSolvedTorsoAnchors"])
        self.assertTrue(output["hasUpperBodyAnchors"])


if __name__ == "__main__":
    unittest.main()
