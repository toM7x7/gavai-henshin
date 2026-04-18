import contextlib
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from henshin import cli
from henshin.fit_regression import load_baseline_manifest, run_fit_regression, select_baselines


class TestFitRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(".").resolve()
        self.manifest_path = self.repo_root / "viewer" / "assets" / "vrm" / "baselines.json"

    def test_load_baseline_manifest_and_select_enabled_entries(self) -> None:
        manifest = load_baseline_manifest(self.manifest_path)
        self.assertEqual(manifest["schema_version"], "0.1")
        selected = select_baselines(manifest)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["id"], "default")

    def test_run_fit_regression_collects_browser_result(self) -> None:
        def fake_runner(command, **kwargs):
            output_path = Path(kwargs["env"]["HENSHIN_FIT_REGRESSION_OUTPUT"])
            output_path.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "summary": {"canSave": True, "fitScore": 88.2, "missingAnchors": []},
                        "wearableSummary": {"canSave": True, "seamContinuity": [], "renderDeviation": []},
                        "metrics": {"torsoLen": 0.61},
                        "fitByPart": {"waist": {"scale": [1, 1, 1]}},
                        "anchorByPart": {"waist": {"bone": "hips"}},
                        "surfaceModel": {"sampleCount": 128, "buckets": {"torso": 32}},
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        result = run_fit_regression(
            root=self.repo_root,
            baselines_manifest=self.manifest_path,
            runner=fake_runner,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["baselines"][0]["summary"]["fitScore"], 88.2)
        self.assertTrue(result["baselines"][0]["wearable_summary"]["canSave"])
        self.assertEqual(result["baselines"][0]["fit_by_part"]["waist"]["scale"], [1, 1, 1])
        self.assertEqual(result["baselines"][0]["anchor_by_part"]["waist"]["bone"], "hips")
        self.assertEqual(result["baselines"][0]["surface_model"]["sampleCount"], 128)

    def test_run_fit_regression_marks_failure_from_browser_harness(self) -> None:
        def fake_runner(command, **kwargs):
            output_path = Path(kwargs["env"]["HENSHIN_FIT_REGRESSION_OUTPUT"])
            output_path.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "summary": {
                            "canSave": False,
                            "fitScore": 54.0,
                            "missingAnchors": ["left_shoulder"],
                            "reasons": ["Missing anchors: left_shoulder"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        result = run_fit_regression(
            root=self.repo_root,
            baselines_manifest=self.manifest_path,
            runner=fake_runner,
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["baselines"][0]["ok"])
        self.assertEqual(result["baselines"][0]["summary"]["fitScore"], 54.0)

    def test_cli_fit_regression_returns_nonzero_on_failure(self) -> None:
        fake_result = {
            "ok": False,
            "baselines": [{"id": "default", "ok": False}],
        }
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), mock.patch("henshin.cli.run_fit_regression", return_value=fake_result):
            exit_code = cli.main(["fit-regression", "--root", str(self.repo_root)])
        self.assertEqual(exit_code, 1)
        payload = json.loads(buffer.getvalue())
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
