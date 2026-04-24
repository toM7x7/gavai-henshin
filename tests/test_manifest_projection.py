import json
import unittest
from pathlib import Path

from henshin.manifest import build_manifest_id, project_suitspec_to_manifest


class TestManifestProjection(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(".").resolve()
        self.suitspec = json.loads(
            (self.repo_root / "examples" / "suitspec.sample.json").read_text(encoding="utf-8")
        )
        self.part_catalog = json.loads(
            (self.repo_root / "examples" / "partcatalog.seed.json").read_text(encoding="utf-8")
        )

    def test_build_manifest_id_is_stable_for_suit_version(self) -> None:
        first = build_manifest_id("VDA-AXIS-OP-00-0001", date_yyyymmdd="20260424", version=1)
        second = build_manifest_id("VDA-AXIS-OP-00-0001", date_yyyymmdd="20260424", version=1)
        self.assertEqual(first, second)
        self.assertRegex(first, r"^MNF-20260424-[A-Z0-9]{4}$")

    def test_project_sample_suitspec_to_manifest_with_catalog_refs(self) -> None:
        manifest = project_suitspec_to_manifest(
            self.suitspec,
            part_catalog=self.part_catalog,
            manifest_id="MNF-20260424-ABCD",
        )

        self.assertEqual(manifest["schema_version"], "0.1")
        self.assertEqual(manifest["source"]["type"], "suitspec_projection")
        self.assertEqual(manifest["source"]["suitspec_id"], self.suitspec["suit_id"])
        self.assertEqual(manifest["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")
        self.assertEqual(manifest["parts"]["left_hand"]["catalog_part_id"], "viewer.mesh.left_hand.v1")
        self.assertEqual(manifest["parts"]["right_hand"]["fit"]["source"], "right_hand")
        self.assertEqual(manifest["runtime_targets"], ["web_preview", "quest", "replay"])


if __name__ == "__main__":
    unittest.main()
