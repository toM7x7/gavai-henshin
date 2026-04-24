import json
import shutil
import unittest
from pathlib import Path

from henshin.prompt_bench import build_helmet_prompt_bench, write_prompt_bench


class TestPromptBench(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_prompt_bench") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        mesh_dir = self.root / "viewer" / "assets" / "meshes"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        (mesh_dir / "helmet.mesh.json").write_text(
            json.dumps(
                {
                    "format": "mesh.v1",
                    "positions": [0, 0, -1, 1, 0, -1, 1, 1, -1, 0, 1, -1],
                    "normals": [0, 0, -1] * 4,
                    "uv": [0.1, 0.1, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9],
                    "indices": [0, 1, 2, 0, 2, 3],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (mesh_dir / "chest.mesh.json").write_text(
            json.dumps(
                {
                    "format": "mesh.v1",
                    "positions": [0, 0, -1, 1, 0, -1, 1, 1, -1, 0, 1, -1],
                    "normals": [0, 0, -1] * 4,
                    "uv": [0.1, 0.1, 0.9, 0.1, 0.9, 0.9, 0.1, 0.9],
                    "indices": [0, 1, 2, 0, 2, 3],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.spec_path = self.root / "spec.json"
        self.spec_path.write_text(
            json.dumps(
                {
                    "style_tags": ["metal", "visor", "audit"],
                    "operator_profile": {
                        "protect_archetype": "citizens",
                        "temperament_bias": "calm",
                        "color_mood": "industrial_gray",
                    },
                    "palette": {"primary": "#112233", "secondary": "#ccddee", "emissive": "#22ccff"},
                    "generation": {},
                    "modules": {
                        "helmet": {"enabled": True, "asset_ref": "viewer/assets/meshes/helmet.mesh.json"},
                        "chest": {"enabled": True, "asset_ref": "viewer/assets/meshes/chest.mesh.json"},
                    },
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

    def test_build_helmet_prompt_bench_returns_four_variants(self) -> None:
        bench = build_helmet_prompt_bench(
            suitspec="spec.json",
            root="sessions",
            repo_root=self.root,
        )

        variants = {variant["key"]: variant for variant in bench["variants"]}
        self.assertEqual(
            set(variants),
            {"a_current_full", "b_compressed_uv_first", "c_normal_fold_first", "d_two_pass_strict"},
        )
        self.assertLess(len(variants["b_compressed_uv_first"]["prompt"]), len(variants["a_current_full"]["prompt"]))
        self.assertIn("Reference A is authoritative", variants["b_compressed_uv_first"]["prompt"])
        self.assertIn("mask-like UV topology field", variants["b_compressed_uv_first"]["prompt"])
        self.assertIn("UV occupancy only", variants["c_normal_fold_first"]["prompt"])
        self.assertIn("Do not draw the assembled armor module", variants["c_normal_fold_first"]["prompt"])
        self.assertIn("Cover the entire square with continuous armor material", variants["c_normal_fold_first"]["prompt"])
        self.assertIn("Do not add readable letters", variants["c_normal_fold_first"]["prompt"])
        self.assertEqual(variants["d_two_pass_strict"]["mode"], "two_pass")
        self.assertIn("Reference A controls layout", variants["d_two_pass_strict"]["refine_prompt"])
        self.assertIn("evaluation_rubric", bench)

    def test_part_prompt_bench_avoids_helmet_specific_language_for_chest(self) -> None:
        bench = build_helmet_prompt_bench(
            suitspec="spec.json",
            root="sessions",
            repo_root=self.root,
            part="chest",
        )
        variants = {variant["key"]: variant for variant in bench["variants"]}
        prompt = variants["c_normal_fold_first"]["prompt"]
        refine = variants["d_two_pass_strict"]["refine_prompt"]

        self.assertEqual(bench["part"], "chest")
        self.assertIn("sternum", prompt)
        self.assertNotIn("visor and brow rhythm", prompt)
        self.assertNotIn("sensor rails", prompt)
        self.assertNotIn("especially around visor", prompt)
        self.assertNotIn("No standalone helmet", prompt)
        self.assertNotIn("helmet concept", refine)

    def test_write_prompt_bench_writes_summary_and_prompt_files(self) -> None:
        bench = build_helmet_prompt_bench(
            suitspec="spec.json",
            root="sessions",
            repo_root=self.root,
        )
        out = self.root / "out"
        summary_path = write_prompt_bench(bench, out)

        self.assertTrue(summary_path.exists())
        self.assertTrue((out / "a_current_full.prompt.txt").exists())
        self.assertTrue((out / "d_two_pass_strict.refine.txt").exists())


if __name__ == "__main__":
    unittest.main()
