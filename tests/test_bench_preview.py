import json
import tempfile
import unittest
from pathlib import Path

from henshin.bench_preview import resolve_bench_output_image, write_batch_preview_suitspec, write_preview_suitspec


class TestBenchPreview(unittest.TestCase):
    def test_resolve_bench_output_image_requires_variant_when_ambiguous(self) -> None:
        summary = {
            "live_outputs": {
                "a": {"image_path": "a.png"},
                "b": {"image_path": "b.png"},
            }
        }

        with self.assertRaisesRegex(ValueError, "pass --variant"):
            resolve_bench_output_image(summary)

        key, image_path = resolve_bench_output_image(summary, variant_key="b")
        self.assertEqual(key, "b")
        self.assertEqual(image_path, Path("b.png"))

    def test_write_preview_suitspec_overlays_one_part_texture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "examples" / "suitspec.sample.json"
            image_path = root / "sessions" / "_bench" / "helmet" / "out.png"
            output_path = root / "sessions" / "S-BENCH-HELMET" / "suitspec.json"
            base_path.parent.mkdir(parents=True)
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"png")
            base_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.2",
                        "suit_id": "VDA-AXIS-OP-00-0001",
                        "approval_id": "APV-12345678",
                        "morphotype_id": "MTP-12345678",
                        "oath": "INTEGRITY_FIRST",
                        "style_tags": ["metal"],
                        "modules": {
                            "helmet": {"enabled": True, "asset_ref": "viewer/assets/meshes/helmet.mesh.json"},
                            "chest": {
                                "enabled": True,
                                "asset_ref": "viewer/assets/meshes/chest.mesh.json",
                                "texture_path": "old.png",
                            },
                        },
                        "generation": {},
                    }
                ),
                encoding="utf-8",
            )

            result = write_preview_suitspec(
                base_suitspec_path=base_path,
                output_path=output_path,
                repo_root=root,
                part="helmet",
                image_path=image_path,
                variant_key="c_normal_fold_first",
                preview_label="Helmet body-fit check",
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["path"], "sessions/S-BENCH-HELMET/suitspec.json")
            self.assertEqual(result["texture_path"], "sessions/_bench/helmet/out.png")
            spec = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(spec["modules"]["helmet"]["enabled"])
            self.assertFalse(spec["modules"]["chest"]["enabled"])
            self.assertEqual(spec["modules"]["helmet"]["texture_path"], "sessions/_bench/helmet/out.png")
            self.assertEqual(spec["generation"]["preview_source"]["variant"], "c_normal_fold_first")
            self.assertEqual(spec["generation"]["preview_source"]["label"], "Helmet body-fit check")

    def test_write_preview_suitspec_can_apply_fit_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "examples" / "suitspec.sample.json"
            image_path = root / "sessions" / "_bench" / "helmet" / "out.png"
            fit_summary_path = root / "tests" / ".tmp" / "fit-summary.json"
            output_path = root / "sessions" / "S-BENCH-HELMET" / "suitspec.json"
            base_path.parent.mkdir(parents=True)
            image_path.parent.mkdir(parents=True)
            fit_summary_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"png")
            base_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.2",
                        "suit_id": "VDA-AXIS-OP-00-0001",
                        "approval_id": "APV-12345678",
                        "morphotype_id": "MTP-12345678",
                        "oath": "INTEGRITY_FIRST",
                        "style_tags": ["metal"],
                        "modules": {
                            "helmet": {
                                "enabled": True,
                                "asset_ref": "viewer/assets/meshes/helmet.mesh.json",
                                "fit": {"shape": "sphere", "scale": [0.05, 0.05, 0.05]},
                            }
                        },
                        "generation": {},
                    }
                ),
                encoding="utf-8",
            )
            fit_summary_path.write_text(
                json.dumps(
                    {
                        "fitByPart": {
                            "helmet": {
                                "shape": "sphere",
                                "source": "chest_core",
                                "attach": "start",
                                "offsetY": 0.2,
                                "zOffset": 0.02,
                                "scale": [0.35, 0.326, 0.343],
                                "follow": [0.34, 0.42, 0.34],
                                "minScale": [0.14, 0.16, 0.14],
                            }
                        },
                        "anchorByPart": {
                            "helmet": {
                                "bone": "head",
                                "offset": [0, -0.097, 0.007],
                                "rotation": [0, 0, 0],
                                "scale": [1, 1, 1],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = write_preview_suitspec(
                base_suitspec_path=base_path,
                output_path=output_path,
                repo_root=root,
                part="helmet",
                image_path=image_path,
                fit_summary_path=fit_summary_path,
            )

            self.assertTrue(result["fit_applied"])
            spec = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(spec["modules"]["helmet"]["fit"]["scale"], [0.35, 0.326, 0.343])
            self.assertEqual(spec["modules"]["helmet"]["vrm_anchor"]["offset"], [0, -0.097, 0.007])
            self.assertEqual(spec["generation"]["preview_source"]["fit_summary"], "tests/.tmp/fit-summary.json")
            self.assertTrue(spec["generation"]["preview_source"]["fit_applied"])

    def test_write_batch_preview_suitspec_overlays_multiple_textures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "examples" / "suitspec.sample.json"
            helmet_image = root / "sessions" / "_bench" / "all" / "helmet.png"
            chest_image = root / "sessions" / "_bench" / "all" / "chest.png"
            batch_summary_path = root / "sessions" / "_bench" / "all" / "summary.json"
            output_path = root / "sessions" / "S-BENCH-ALL" / "suitspec.json"
            base_path.parent.mkdir(parents=True)
            helmet_image.parent.mkdir(parents=True)
            helmet_image.write_bytes(b"helmet")
            chest_image.write_bytes(b"chest")
            base_path.write_text(
                json.dumps(
                    {
                        "schema_version": "0.2",
                        "suit_id": "VDA-AXIS-OP-00-0001",
                        "approval_id": "APV-12345678",
                        "morphotype_id": "MTP-12345678",
                        "oath": "INTEGRITY_FIRST",
                        "style_tags": ["metal"],
                        "modules": {
                            "helmet": {"enabled": False, "asset_ref": "viewer/assets/meshes/helmet.mesh.json"},
                            "chest": {"enabled": False, "asset_ref": "viewer/assets/meshes/chest.mesh.json"},
                            "back": {"enabled": True, "asset_ref": "viewer/assets/meshes/back.mesh.json"},
                        },
                        "generation": {},
                    }
                ),
                encoding="utf-8",
            )
            batch_summary_path.write_text(
                json.dumps(
                    {
                        "results": {
                            "helmet": {
                                "live_outputs": {
                                    "c_normal_fold_first": {"image_path": str(helmet_image)}
                                }
                            },
                            "chest": {
                                "live_outputs": {
                                    "c_normal_fold_first": {"image_path": str(chest_image)}
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = write_batch_preview_suitspec(
                base_suitspec_path=base_path,
                output_path=output_path,
                repo_root=root,
                batch_summary_path=batch_summary_path,
                variant_key="c_normal_fold_first",
                preview_label="All part preview",
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["texture_count"], 2)
            spec = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(spec["modules"]["helmet"]["enabled"])
            self.assertTrue(spec["modules"]["chest"]["enabled"])
            self.assertFalse(spec["modules"]["back"]["enabled"])
            self.assertEqual(spec["modules"]["helmet"]["texture_path"], "sessions/_bench/all/helmet.png")
            self.assertEqual(spec["modules"]["chest"]["texture_path"], "sessions/_bench/all/chest.png")
            self.assertEqual(spec["generation"]["preview_source"]["type"], "bench_batch_texture_preview")


if __name__ == "__main__":
    unittest.main()
