import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


class TestPromptBenchTool(unittest.TestCase):
    def setUp(self) -> None:
        self.out = Path("tests/.tmp/test_prompt_bench_tool") / self._testMethodName
        if self.out.exists():
            shutil.rmtree(self.out)

    def tearDown(self) -> None:
        if self.out.exists():
            shutil.rmtree(self.out, ignore_errors=True)

    def test_prompt_bench_helmet_dry_run_cli_writes_files(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "tools/prompt_bench_helmet.py",
                "--output-dir",
                str(self.out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)

        self.assertTrue(payload["ok"])
        self.assertTrue((self.out / "summary.json").exists())
        self.assertTrue((self.out / "a_current_full.prompt.txt").exists())
        self.assertTrue((self.out / "b_compressed_uv_first.prompt.txt").exists())
        summary = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["part"], "helmet")
        self.assertEqual(len(summary["variants"]), 4)

    def test_prompt_bench_helmet_cli_can_filter_variant(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "tools/prompt_bench_helmet.py",
                "--output-dir",
                str(self.out),
                "--variant",
                "c_normal_fold_first",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))

        self.assertEqual([variant["key"] for variant in summary["variants"]], ["c_normal_fold_first"])
        self.assertTrue((self.out / "c_normal_fold_first.prompt.txt").exists())
        self.assertFalse((self.out / "a_current_full.prompt.txt").exists())

    def test_prompt_bench_parts_cli_writes_selected_variant_for_all_parts(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "tools/prompt_bench_parts.py",
                "--output-dir",
                str(self.out),
                "--parts",
                "helmet,chest",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        summary = json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))

        self.assertTrue(payload["ok"])
        self.assertEqual(summary["parts"], ["helmet", "chest"])
        self.assertTrue((self.out / "helmet" / "c_normal_fold_first.prompt.txt").exists())
        self.assertTrue((self.out / "chest" / "c_normal_fold_first.prompt.txt").exists())
        self.assertFalse((self.out / "helmet" / "a_current_full.prompt.txt").exists())


if __name__ == "__main__":
    unittest.main()
