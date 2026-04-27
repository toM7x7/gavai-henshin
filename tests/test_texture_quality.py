import shutil
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from henshin.texture_quality import analyze_texture_quality


class TestTextureQuality(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_texture_quality") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_patterned_square_texture_is_ok(self) -> None:
        path = self.root / "pattern.png"
        image = Image.new("RGBA", (128, 128), (32, 48, 72, 255))
        draw = ImageDraw.Draw(image)
        for x in range(0, 128, 16):
            draw.line((x, 0, x, 127), fill=(220, 235, 255, 255), width=2)
        for y in range(0, 128, 20):
            draw.line((0, y, 127, y), fill=(255, 180, 80, 255), width=2)
        image.save(path)

        quality = analyze_texture_quality(path)

        self.assertEqual(quality["status"], "ok")
        self.assertEqual(quality["width"], 128)
        self.assertEqual(quality["height"], 128)
        self.assertGreater(quality["color_bin_count"], 2)
        self.assertLess(quality["blank_ratio"], 0.25)

    def test_blank_texture_warns_without_failing(self) -> None:
        path = self.root / "blank.png"
        Image.new("RGBA", (128, 128), (255, 255, 255, 255)).save(path)

        quality = analyze_texture_quality(path)

        self.assertEqual(quality["mode"], "warning_only")
        self.assertEqual(quality["status"], "warn")
        self.assertIn("blank_area_high", quality["warnings"])
        self.assertIn("low_color_variety", quality["warnings"])


if __name__ == "__main__":
    unittest.main()
