import json
import shutil
import unittest
from pathlib import Path

from henshin.uv_guides import ensure_uv_guide_image


class TestUvGuides(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_uv_guides") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        mesh_dir = self.root / "viewer" / "assets" / "meshes"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        (mesh_dir / "helmet.mesh.json").write_text(
            json.dumps(
                {
                    "format": "mesh.v1",
                    "positions": [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0],
                    "normals": [0, 0, 1] * 4,
                    "uv": [0.1, 0.1, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9],
                    "indices": [0, 1, 2, 0, 2, 3],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_ensure_uv_guide_image_generates_and_reuses_cache(self) -> None:
        contract = {
            "fill_ratio_target": [88, 96],
            "blank_area_max_percent": 10,
            "seam_safe_margin_percent": [4, 5],
        }
        first = ensure_uv_guide_image(
            part="helmet",
            module={"asset_ref": "viewer/assets/meshes/helmet.mesh.json"},
            contract=contract,
            session_root=self.root / "sessions",
            repo_root=self.root,
            write_image=True,
        )
        second = ensure_uv_guide_image(
            part="helmet",
            module={"asset_ref": "viewer/assets/meshes/helmet.mesh.json"},
            contract=contract,
            session_root=self.root / "sessions",
            repo_root=self.root,
            write_image=True,
        )

        self.assertTrue(Path(first["path"]).exists())
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["guide_hash"], second["guide_hash"])


if __name__ == "__main__":
    unittest.main()
