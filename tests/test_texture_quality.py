import shutil
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from henshin.texture_quality import evaluate_texture_output


class TestTextureQuality(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_texture_quality") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_full_painted_texture_passes(self) -> None:
        path = self.root / "painted.png"
        image = Image.new("RGB", (256, 256), (28, 45, 62))
        draw = ImageDraw.Draw(image)
        for x in range(0, 256, 16):
            shade = 34 + (x % 48)
            draw.rectangle((x, 0, x + 8, 255), fill=(shade, 48, 66))
        for y in range(24, 256, 48):
            draw.line((0, y, 255, y), fill=(72, 98, 118), width=2)
        for i in range(0, 256, 24):
            draw.rectangle((i, 0, min(i + 12, 255), 28), fill=(82, 106, 126))
            draw.rectangle((i, 228, min(i + 12, 255), 255), fill=(18, 32, 48))
            draw.rectangle((0, i, 28, min(i + 12, 255)), fill=(68, 88, 108))
            draw.rectangle((228, i, 255, min(i + 12, 255)), fill=(22, 36, 52))
        image.save(path)

        result = evaluate_texture_output(path)

        self.assertFalse(result["reject"])
        self.assertIn(result["status"], {"pass", "warn"})
        self.assertLess(result["metrics"]["blank_ratio"], 0.01)

    def test_object_on_blank_background_rejects(self) -> None:
        path = self.root / "object.png"
        image = Image.new("RGB", (256, 256), (245, 245, 245))
        draw = ImageDraw.Draw(image)
        draw.rectangle((98, 98, 158, 158), fill=(20, 35, 50))
        image.save(path)

        result = evaluate_texture_output(path)

        self.assertTrue(result["reject"])
        self.assertIn("large_unpainted_background", result["reasons"])
        self.assertIn("object_silhouette_on_background", result["reasons"])

    def test_orange_construction_line_rejects(self) -> None:
        path = self.root / "orange.png"
        image = Image.new("RGB", (256, 256), (28, 45, 62))
        draw = ImageDraw.Draw(image)
        draw.line((0, 0, 255, 255), fill=(208, 112, 42), width=6)
        image.save(path)

        result = evaluate_texture_output(path)

        self.assertTrue(result["reject"])
        self.assertIn("construction_orange_guide_leak", result["reasons"])

    def test_invalid_image_is_not_evaluated_without_rejecting(self) -> None:
        path = self.root / "bad.png"
        path.write_bytes(b"not an image")

        result = evaluate_texture_output(path)

        self.assertEqual(result["status"], "not_evaluated")
        self.assertFalse(result["reject"])


if __name__ == "__main__":
    unittest.main()
