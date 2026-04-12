import contextlib
import io
import json
import shutil
import unittest
from pathlib import Path
from unittest import mock

from henshin import cli
from henshin.vrm_authoring_audit import build_authoring_audit, write_authoring_audit


class TestVrmAuthoringAudit(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_vrm_authoring_audit") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_build_authoring_audit_marks_rebuild_and_tune_parts(self) -> None:
        regression = {
            "ok": False,
            "mode": "auto_fit",
            "root": "repo",
            "suitspec": "examples/suitspec.sample.json",
            "sim": "sessions/body-sim.json",
            "baselines": [
                {
                    "id": "default",
                    "label": "Default VRM",
                    "vrm_path": "viewer/assets/vrm/default.vrm",
                    "ok": False,
                    "summary": {
                        "fitScore": 72.0,
                        "canSave": False,
                        "reasons": ["Critical surface violations"],
                        "weakParts": [
                            {"part": "left_upperarm", "score": 54.0, "critical": True},
                            {"part": "left_boot", "score": 81.0, "critical": True},
                        ],
                        "weakPairs": [
                            {"pair": "left_upperarm-left_forearm", "score": 71.0, "gap": 0.0, "penetration": 0.12},
                        ],
                        "surfaceViolations": [
                            {"part": "left_upperarm", "critical": True, "metric": "radial", "kind": "above_max"},
                        ],
                        "heroOverflow": [
                            {"part": "left_boot", "metric": "y"},
                        ],
                        "symmetryDelta": [
                            {"group": "upperarm", "delta": 0.2, "tolerance": 0.065, "ok": False},
                            {"group": "boot", "delta": 0.0, "tolerance": 0.075, "ok": True},
                        ],
                    },
                }
            ],
        }

        audit = build_authoring_audit(regression)
        self.assertEqual(audit["decision_totals"]["rebuild"], 2)
        baseline = audit["baselines"][0]
        actions = {entry["part"]: entry for entry in baseline["part_actions"]}
        self.assertEqual(actions["left_upperarm"]["decision"], "rebuild")
        self.assertEqual(actions["right_upperarm"]["decision"], "rebuild")
        self.assertEqual(actions["left_boot"]["decision"], "tune")
        self.assertEqual(actions["helmet"]["decision"], "keep")
        self.assertEqual(actions["left_upperarm"]["weak_pairs"][0]["pair"], "left_upperarm-left_forearm")

    def test_write_authoring_audit_writes_json_and_markdown(self) -> None:
        audit = {
            "ok": True,
            "mode": "auto_fit",
            "root": "repo",
            "suitspec": "examples/suitspec.sample.json",
            "sim": "sessions/body-sim.json",
            "decision_totals": {"rebuild": 1, "tune": 1, "keep": 16},
            "waves": [],
            "baselines": [],
        }
        outputs = write_authoring_audit(
            audit,
            json_path=self.root / "audit.json",
            markdown_path=self.root / "audit.md",
        )
        self.assertTrue(Path(outputs["json"]).exists())
        self.assertTrue(Path(outputs["markdown"]).exists())

    def test_cli_authoring_audit_prints_payload(self) -> None:
        fake_audit = {
            "ok": True,
            "mode": "auto_fit",
            "root": "repo",
            "suitspec": "examples/suitspec.sample.json",
            "sim": "sessions/body-sim.json",
            "decision_totals": {"rebuild": 0, "tune": 0, "keep": 18},
            "waves": [],
            "baselines": [],
        }
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), mock.patch("henshin.cli.run_authoring_audit", return_value=fake_audit):
            exit_code = cli.main(["authoring-audit", "--root", "."])
        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
