import unittest

from henshin.bodyfit import BodyFrame, CoverScale, Vec2, norm_to_world, run_body_sequence


class TestBodyFit(unittest.TestCase):
    def test_norm_to_world(self) -> None:
        p = norm_to_world(0.25, 0.5, mirror=True, cover_scale=CoverScale(1.0, 1.0))
        self.assertAlmostEqual(p.x, 0.5)
        self.assertAlmostEqual(p.y, 0.0)

    def test_run_body_sequence_equips(self) -> None:
        frames = []
        for _ in range(8):
            frames.append(
                BodyFrame(
                    dt_sec=0.1,
                    joints_xy01={
                        "left_shoulder": (0.62, 0.38),
                        "right_shoulder": (0.38, 0.38),
                        "left_elbow": (0.67, 0.48),
                        "right_elbow": (0.33, 0.48),
                        "left_wrist": (0.70, 0.61),
                        "right_wrist": (0.225, 0.625),
                        "left_hip": (0.57, 0.58),
                        "right_hip": (0.43, 0.58),
                        "left_knee": (0.57, 0.76),
                        "right_knee": (0.43, 0.76),
                        "left_ankle": (0.57, 0.92),
                        "right_ankle": (0.43, 0.92),
                    },
                )
            )

        out = run_body_sequence(
            frames,
            mirror=True,
            cover_scale=CoverScale(1.0, 1.0),
            dock_center=Vec2(0.55, -0.25),
            hold_to_equip_sec=0.6,
            trigger_joint="right_wrist",
        )
        self.assertTrue(out["equipped"])
        self.assertGreaterEqual(out["equip_frame"], 0)
        self.assertIn("right_forearm", out["segments"])


if __name__ == "__main__":
    unittest.main()
