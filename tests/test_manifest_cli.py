import json
import shutil
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from henshin.cli import main


class TestManifestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_manifest_cli") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_project_manifest_writes_valid_manifest(self) -> None:
        output = self.root / "manifest.json"
        stdout = StringIO()

        with redirect_stdout(stdout):
            code = main(
                [
                    "project-manifest",
                    "--suitspec",
                    "examples/suitspec.sample.json",
                    "--partcatalog",
                    "examples/partcatalog.seed.json",
                    "--manifest-id",
                    "MNF-20260424-CLIT",
                    "--output",
                    str(output),
                ]
            )

        self.assertEqual(code, 0)
        self.assertTrue(output.exists())
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["manifest_id"], "MNF-20260424-CLIT")
        self.assertEqual(result["parts"], 18)

        manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(manifest["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")
        self.assertEqual(manifest["parts"]["left_hand"]["catalog_part_id"], "viewer.mesh.left_hand.v1")

    def test_validate_accepts_partcatalog_seed(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = main(
                [
                    "validate",
                    "--kind",
                    "partcatalog",
                    "--path",
                    "examples/partcatalog.seed.json",
                ]
            )

        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
