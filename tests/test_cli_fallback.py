import json
import shutil
import unittest
from pathlib import Path

from henshin.cli import _resolve_fallback_image, _use_fallback_asset


class TestCliFallback(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_cli_fallback") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.fallback_dir = self.root / "fallback"
        self.parts_dir = self.root / "parts"
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        self.parts_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_resolve_fallback_image_prefers_generated_png(self) -> None:
        (self.fallback_dir / "helmet.generated.jpg").write_bytes(b"jpg")
        (self.fallback_dir / "helmet.generated.png").write_bytes(b"png")

        resolved = _resolve_fallback_image("helmet", self.fallback_dir)
        self.assertEqual(resolved, self.fallback_dir / "helmet.generated.png")

    def test_use_fallback_asset_copies_image_and_writes_meta(self) -> None:
        source = self.fallback_dir / "chest.generated.jpg"
        source.write_bytes(b"fakejpgbytes")

        info = _use_fallback_asset("chest", self.fallback_dir, self.parts_dir)
        self.assertIsNotNone(info)
        assert info is not None

        image_path = Path(info["image_path"])
        meta_path = Path(info["meta_path"])
        self.assertTrue(image_path.exists())
        self.assertEqual(image_path.read_bytes(), b"fakejpgbytes")
        self.assertTrue(meta_path.exists())

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.assertEqual(meta["source"], "fallback")
        self.assertEqual(meta["kind"], "part:chest")
        self.assertEqual(meta["fallback_image_path"], str(source))

    def test_use_fallback_asset_returns_none_when_missing(self) -> None:
        info = _use_fallback_asset("right_hand", self.fallback_dir, self.parts_dir)
        self.assertIsNone(info)


if __name__ == "__main__":
    unittest.main()
