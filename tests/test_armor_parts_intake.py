import importlib.util
import json
import struct
import unittest
from pathlib import Path


TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_armor_parts_intake.py"
SPEC = importlib.util.spec_from_file_location("validate_armor_parts_intake", TOOL_PATH)
armor_intake = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(armor_intake)


def _write_glb(path: Path, *, declared_length_delta: int = 0) -> None:
    json_chunk = b'{"asset":{"version":"2.0"}}  '
    while len(json_chunk) % 4:
        json_chunk += b" "
    total_length = 12 + 8 + len(json_chunk)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total_length + declared_length_delta)
        + struct.pack("<II", len(json_chunk), 0x4E4F534A)
        + json_chunk
    )


def _sidecar(module: str) -> dict:
    return {
        "contract_version": "modeler-part-sidecar.v1",
        "module": module,
        "part_id": f"viewer.mesh.{module}.v1",
        "bbox_m": {"x": 0.1, "y": 0.2, "z": 0.3, "size": [0.1, 0.2, 0.3]},
        "triangle_count": 12,
        "material_zones": ["base_surface", "accent", "trim"],
        "texture_provider_profile": "nano_banana",
        "vrm_attachment": {
            "primary_bone": "upperChest",
            "offset_m": [0, 0, 0],
            "rotation_deg": [0, 0, 0],
        },
    }


def _write_part(root: Path, module: str, *, sidecar_module: str | None = None, bad_glb: bool = False) -> None:
    module_dir = root / module
    module_dir.mkdir(parents=True)
    _write_glb(module_dir / f"{module}.glb", declared_length_delta=1 if bad_glb else 0)
    (module_dir / f"{module}.modeler.json").write_text(
        json.dumps(_sidecar(sidecar_module or module), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class TestArmorPartsIntake(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_armor_parts_intake") / self._testMethodName
        self.root.mkdir(parents=True, exist_ok=True)
        self.previous_expected = armor_intake.EXPECTED_PARTS
        armor_intake.EXPECTED_PARTS = ("helmet", "chest")

    def tearDown(self) -> None:
        armor_intake.EXPECTED_PARTS = self.previous_expected
        if self.root.exists():
            for path in sorted(self.root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                else:
                    path.rmdir()

    def test_intake_passes_for_valid_glb_headers_and_sidecars(self) -> None:
        _write_part(self.root, "helmet")
        _write_part(self.root, "chest")

        result = armor_intake.validate_armor_parts(self.root)

        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["ok"])
        self.assertEqual(result["missing_parts"], [])
        self.assertEqual(result["parts"]["helmet"]["glb"]["metrics"]["magic"], "glTF")
        self.assertEqual(result["parts"]["helmet"]["glb"]["metrics"]["first_chunk_type"], "JSON")
        self.assertEqual(result["parts"]["helmet"]["glb"]["metrics"]["asset_version"], "2.0")
        self.assertEqual(result["parts"]["chest"]["sidecar"]["metrics"]["bbox_size_m"], [0.1, 0.2, 0.3])

    def test_intake_fails_on_glb_length_mismatch_sidecar_module_mismatch_and_blend1(self) -> None:
        _write_part(self.root, "helmet", sidecar_module="wrong_module", bad_glb=True)
        _write_part(self.root, "chest")
        (self.root / "helmet" / "source").mkdir()
        (self.root / "helmet" / "source" / "helmet.blend1").write_bytes(b"backup")

        result = armor_intake.validate_armor_parts(self.root)

        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["ok"])
        self.assertIn("helmet: sidecar module must match folder name", result["reasons"])
        self.assertTrue(any("declared length must match file size" in reason for reason in result["reasons"]))
        self.assertTrue(any("backup file must not be committed" in reason for reason in result["reasons"]))

    def test_committed_armor_parts_tree_keeps_all_18_glb_deliveries_renderable(self) -> None:
        armor_intake.EXPECTED_PARTS = self.previous_expected

        result = armor_intake.validate_armor_parts(armor_intake.DEFAULT_ARMOR_PARTS_DIR)

        self.assertEqual(len(armor_intake.EXPECTED_PARTS), 18)
        self.assertEqual(result["status"], "pass", result["reasons"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["part_count"], 18)
        self.assertEqual(result["missing_parts"], [])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(set(result["present_parts"]), set(armor_intake.EXPECTED_PARTS))
        for part in armor_intake.EXPECTED_PARTS:
            with self.subTest(part=part):
                self.assertEqual(result["parts"][part]["status"], "pass")
                self.assertEqual(result["parts"][part]["glb"]["metrics"]["magic"], "glTF")
                self.assertEqual(result["parts"][part]["glb"]["metrics"]["version"], 2)
                self.assertEqual(result["parts"][part]["glb"]["metrics"]["asset_version"], "2.0")
                self.assertIn("base_surface", result["parts"][part]["sidecar"]["metrics"]["material_zones"])
                self.assertGreater(result["parts"][part]["sidecar"]["metrics"]["triangle_count"], 0)


if __name__ == "__main__":
    unittest.main()
