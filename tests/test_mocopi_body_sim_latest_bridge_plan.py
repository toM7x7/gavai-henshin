from __future__ import annotations

import unittest
from pathlib import Path


class TestMocopiBodySimLatestBridgePlan(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(".").resolve()

    def test_adapter_endpoint_contract_supports_quest_fetch(self) -> None:
        adapter = (self.repo_root / "tools" / "serve_mocopi_body_sim_latest.py").read_text(encoding="utf-8")

        for token in {
            'BODY_SIM_PATHS = {"/body-sim/latest", "/api/mocopi/body-sim/latest"}',
            '"Cache-Control"',
            '"no-store"',
            '"Access-Control-Allow-Origin"',
            '"motion_source"',
            '"raw_payload_retained": False',
        }:
            self.assertIn(token, adapter)

    def test_quest_loader_can_read_absolute_live_body_sim_path(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")

        for token in {
            "function normalizePath(path)",
            "if (/^(https?:|data:|blob:)/i.test(raw) || raw.startsWith(\"/\")) return raw;",
            "const response = await fetch(normalized, { cache: \"no-store\" });",
            "const bodySimPath = this.liveBodySimEnabled ? this.liveBodySimLatestPath : replay?.deposition?.body_sim_path;",
            "bodySim = await this.loadBodySimRecord(bodySimPath);",
            "this.frames = bodySim?.frames || [];",
            "this.replayMotionSource = replayMotionSourceFromRecord(replay, bodySim);",
            "bodySim?.motion_source",
            "bodySim?.metadata?.motion_source",
            "replayMotion:",
            "replayMotionDiagnostic,",
        }:
            self.assertIn(token, js)

    def test_dashboard_api_gap_and_target_bridge_are_documented(self) -> None:
        dashboard = (self.repo_root / "src" / "henshin" / "dashboard_server.py").read_text(encoding="utf-8")
        plan = (
            self.repo_root / "docs" / "quest-mocopi-body-sim-latest-bridge-plan-2026-05-05.md"
        ).read_text(encoding="utf-8")

        self.assertIn('if parsed.path == "/api/quest-debug/latest":', dashboard)
        self.assertIn("/api/quest-debug/latest", plan)

        for token in {
            "GET /api/mocopi/body-sim/latest",
            "http://127.0.0.1:8021/body-sim/latest",
            "http://127.0.0.1:8010/api/mocopi/body-sim/latest",
            "adb reverse tcp:8021 tcp:8021",
            "deposition.body_sim_path",
            "bodySimLatest=http://127.0.0.1:8010/api/mocopi/body-sim/latest",
            "GO",
            "DEMO",
            "NO-GO",
        }:
            self.assertIn(token, plan)


if __name__ == "__main__":
    unittest.main()
