import unittest

from henshin.rightarm import CoverScale, DockCharger, RightArmFrame, Vec2, norm_to_world, run_rightarm_sequence


class TestRightArm(unittest.TestCase):
    def test_norm_to_world_with_mirror(self) -> None:
        p = norm_to_world(0.25, 0.5, mirror=True, cover_scale=CoverScale(1.0, 1.0))
        self.assertAlmostEqual(p.x, 0.5)
        self.assertAlmostEqual(p.y, 0.0)

    def test_dock_charger_equip(self) -> None:
        dock = DockCharger(center=Vec2(0.0, 0.0), radius=1.0, hold_to_equip_sec=0.3)
        equipped = False
        for _ in range(3):
            if dock.tick(dt_sec=0.1, wrist=Vec2(0.0, 0.0), already_equipped=equipped):
                equipped = True
        self.assertTrue(equipped)

    def test_sequence_equips(self) -> None:
        frames = [
            RightArmFrame(0.1, (0.32, 0.56), (0.225, 0.625)),
            RightArmFrame(0.1, (0.32, 0.56), (0.225, 0.625)),
            RightArmFrame(0.1, (0.32, 0.56), (0.225, 0.625)),
            RightArmFrame(0.1, (0.31, 0.56), (0.21, 0.61)),
        ]
        out = run_rightarm_sequence(frames, hold_to_equip_sec=0.25)
        self.assertTrue(out["equipped"])
        self.assertGreaterEqual(out["equip_frame"], 0)


if __name__ == "__main__":
    unittest.main()
