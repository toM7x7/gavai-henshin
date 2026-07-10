import json
import re
import unittest
from pathlib import Path


class TestQuestMocopiMotionSource(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(".").resolve()

    def test_fixture_distinguishes_simulated_body_from_mocopi_source(self) -> None:
        fixture = json.loads(
            (self.repo_root / "examples" / "quest-mocopi-motion-source.fixture.json").read_text(
                encoding="utf-8"
            )
        )

        cases = {case["name"]: case for case in fixture["cases"]}
        self.assertEqual(set(cases), {"simulated_body", "mocopi_body"})

        simulated = cases["simulated_body"]
        mocopi = cases["mocopi_body"]
        self.assertEqual(self._case_motion_source(simulated), "body_sim")
        self.assertEqual(self._case_motion_source(mocopi), "mocopi")
        self.assertEqual(simulated["expected"]["diagnostic_token"], "BODY 1f")
        self.assertEqual(mocopi["expected"]["diagnostic_token"], "MOCOPI 1f")
        self.assertEqual(simulated["mode"], mocopi["mode"])

        acceptance = fixture["show_floor_acceptance"]
        self.assertEqual(
            acceptance["pairing_required_sensors"],
            ["head", "hip", "left_wrist", "right_wrist", "left_ankle", "right_ankle"],
        )
        self.assertEqual(
            acceptance["calibration_pose"],
            "stand_upright_face_quest_origin_arms_relaxed_or_app_prompt",
        )
        self.assertLessEqual(acceptance["latency_thresholds_ms"]["pass_median_max"], 120)
        self.assertLessEqual(acceptance["latency_thresholds_ms"]["pass_p95_max"], 250)
        self.assertEqual(acceptance["fallback_order"], ["MOCOPI", "BODY", "STATIC"])
        self.assertIn("identifying motion data", acceptance["privacy_operator_note"])

        for case in cases.values():
            with self.subTest(case=case["name"]):
                self.assertFalse(case["replay"]["deposition"]["body_sim_path"].startswith("/"))
                self.assertNotIn("\\", case["replay"]["deposition"]["body_sim_path"])
                self.assertEqual(len(case["body_sim"]["frames"]), 1)

    def test_quest_viewer_labels_mocopi_as_diagnostic_source_only(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        helper = self._extract_js_function(js, "function replayMotionSourceFromRecord")
        diagnostic = self._extract_js_function(js, "function makeReplayMotionDiagnostic")
        apply_replay = self._extract_js_class_method(
            js,
            "async applyReplay(replay, { speak, autoplay = true, viewMode = XR_VIEW_MODE_SELF, source = \"voice\" })",
        )

        for token in {
            'const DEFAULT_REPLAY = "/sessions/S-IW-DEMO/artifacts/iwsdk-deposition-replay.json";',
            'const DEFAULT_MOCOPI = "examples/mocopi_sequence.sample.json";',
            'const REPLAY_MOTION_SOURCE_MOCOPI = "mocopi";',
            "function normalizeReplayMotionSource(value)",
            "function replayMotionSourceFromRecord(replay, bodySim = null)",
            "motionFramesFromReplayScript(replayScript)",
            "this.setArchiveMotionFrames(replayMotionFrames);",
            "function normalizeServedAssetPath(path)",
            "const match = raw.match(/(?:^|\\/)sessions\\/.+/);",
            "normalizePath(normalizeServedAssetPath(path))",
            "function useAutoplayReplay()",
            'params().get("autoplayReplay") === "1"',
            'params().get("qaReplay") === "1"',
            'const DEFAULT_BODY_SIM_LATEST = "http://localhost:8021/body-sim/latest";',
            "function useMocopiLiveBodySim()",
            "function getBodySimLatestPath()",
            'search.has("bodySimLatest")',
            'search.has("mocopiLatest")',
        }:
            self.assertIn(token, js)

        for token in {
            "replay?.playback?.motion_source",
            "replay?.source?.tracking",
            "replay?.motion_provenance?.primary_source",
            "replay?.motion_provenance?.capture_system?.provider",
            "bodySim?.motion_source",
            "bodySim?.source",
            "bodySim?.metadata?.motion_source",
            "bodySim?.metadata?.source",
        }:
            self.assertIn(token, helper)

        self.assertIn("token: `MOCOPI ${body}f`", diagnostic)
        self.assertIn("label: `mocopi-derived body-sim ${body} frames`", diagnostic)
        self.assertIn("source: REPLAY_MOTION_SOURCE_MOCOPI", diagnostic)
        self.assertIn("motion_source: REPLAY_MOTION_SOURCE_MOCOPI", diagnostic)

        self._assert_tokens_in_order(
            apply_replay,
            [
                "const replayMotionFrames = motionFramesFromReplayScript(replayScript);",
                "this.setArchiveMotionFrames(replayMotionFrames);",
                "let bodySim = null;",
                "const bodySimPath = this.liveBodySimEnabled ? this.liveBodySimLatestPath : replay?.deposition?.body_sim_path;",
                "bodySim = await this.loadBodySimRecord(bodySimPath);",
                "this.frames = bodySim?.frames || [];",
                "this.replayMotionSource = replayMotionSourceFromRecord(replay, bodySim);",
                "this.refreshReplayMotionDiagnostic({",
            ],
        )

    def test_quest_viewer_can_autoplay_loaded_mocopi_replay_for_qa(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        start_method = self._extract_js_class_method(js, "async start()")
        snapshot_method = self._extract_js_class_method(js, 'collectQuestDebugSnapshot(event = "scene")')

        self._assert_tokens_in_order(
            start_method,
            [
                "const replay = await loadReplay();",
                "const autoplayReplay = useAutoplayReplay();",
                "await this.applyReplay(replay, {",
                "autoplay: autoplayReplay,",
                "viewMode: this.archiveViewMode,",
                'source: "archive",',
            ],
        )

        for token in {
            "const replayMotionDiagnostic = this.replayMotionDiagnostic || makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);",
            "replayMotionDiagnostic,",
            "replayMotion:",
            "archiveMotionFrames: this.archiveMotionFrames.length",
            "bodySimFrames: this.frames.length",
            "replayMotionSource: this.replayMotionSource",
            "liveBodySim:",
            "latestPath: this.liveBodySimLatestPath",
            "adapterPacketAgeMs:",
            "renderCalibratedAt: this.liveBodySimRenderCalibratedAt",
            "renderCalibrationSource: this.liveBodySimRenderCalibrationSource",
            "sourceStale: this.liveBodySimSourceStale",
            "stale: liveBodySimStale",
            'renderMode: this.liveBodySimEnabled ? "latest_segment_pose" : "replay_or_static"',
        }:
            self.assertIn(token, snapshot_method)

    def test_quest_viewer_falls_back_when_mocopi_body_sim_is_unavailable(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        diagnostic = self._extract_js_function(js, "function makeReplayMotionDiagnostic")
        compute = self._extract_js_class_method(
            js,
            "computeReplayMotionDiagnostic({ viewMode = this.xrViewMode, playbackSource = this.playbackSource } = {})",
        )
        apply_replay = self._extract_js_class_method(
            js,
            "async applyReplay(replay, { speak, autoplay = true, viewMode = XR_VIEW_MODE_SELF, source = \"voice\" })",
        )

        self.assertIn(
            'const normalizedReplayMotionSource = (live || body) ? normalizeReplayMotionSource(replayMotionSource) : "";',
            diagnostic,
        )
        self.assertIn(
            "return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC, livePoseFrames, bodySimFrames, replayMotionSource);",
            compute,
        )

        for token in {
            "let bodySim = null;",
            "const bodySimPath = this.liveBodySimEnabled ? this.liveBodySimLatestPath : replay?.deposition?.body_sim_path;",
            "try {",
            "bodySim = await this.loadBodySimRecord(bodySimPath);",
            "} catch (error) {",
            'console.warn("body-sim replay unavailable; falling back to replay motion/static", error);',
            'this.appendVoiceDebug("motion fallback: body-sim unavailable; using replay/static");',
            "this.frames = bodySim?.frames || [];",
            "this.replayMotionSource = replayMotionSourceFromRecord(replay, bodySim);",
        }:
            self.assertIn(token, apply_replay)

        self._assert_tokens_in_order(
            apply_replay,
            [
                "let bodySim = null;",
                "const bodySimPath = this.liveBodySimEnabled ? this.liveBodySimLatestPath : replay?.deposition?.body_sim_path;",
                "try {",
                "} catch (error) {",
                "this.frames = bodySim?.frames || [];",
                "this.replayMotionSource = replayMotionSourceFromRecord(replay, bodySim);",
                "this.refreshReplayMotionDiagnostic({",
            ],
        )

    def test_quest_viewer_polls_mocopi_body_sim_latest_when_enabled(self) -> None:
        js = (self.repo_root / "viewer" / "quest-iw-demo" / "quest-demo.js").read_text(encoding="utf-8")
        constructor = self._extract_js_class_method(js, "constructor(world)")
        start_method = self._extract_js_class_method(js, "async start()")
        refresh_latest = self._extract_js_class_method(
            js,
            "async refreshLiveBodySimLatest({ force = false } = {})",
        )
        update_scene = self._extract_js_class_method(js, "updateScene(dt)")
        current_frame = self._extract_js_class_method(js, "currentFrame(progress)")
        calibrate_live = self._extract_js_class_method(
            js,
            'calibrateLiveBodySimArmorToBody({ source = "manual" } = {})',
        )

        for token in {
            "this.liveBodySimEnabled = useMocopiLiveBodySim();",
            "this.liveBodySimLatestPath = getBodySimLatestPath();",
            "this.liveBodySimPollIntervalMs = getLiveBodySimPollIntervalMs();",
            "this.liveBodySimRenderProfile = getLiveBodySimRenderProfile();",
            'this.liveBodySimRenderCalibratedAt = "";',
            'this.liveBodySimRenderCalibrationSource = "";',
            "this.liveBodySimLastPollAt = -Infinity;",
            "this.liveBodySimLastOkAt = -Infinity;",
            "this.liveBodySimInFlight = false;",
            "this.liveBodySimFrameCount = 0;",
            "this.liveBodySimAdapterAgeMs = null;",
            "this.liveBodySimSourceStale = false;",
            "this.liveBodySimPollCount = 0;",
        }:
            self.assertIn(token, constructor)

        self._assert_tokens_in_order(
            start_method,
            [
                "await this.applyReplay(replay, {",
                "if (this.liveBodySimEnabled) {",
                "void this.refreshLiveBodySimLatest({ force: true });",
            ],
        )

        for token in {
            "if (!this.liveBodySimEnabled || this.liveBodySimInFlight) return false;",
            "now - this.liveBodySimLastPollAt < this.liveBodySimPollIntervalMs",
            "const bodySim = await this.loadBodySimRecord(this.liveBodySimLatestPath);",
            'throw new Error("body-sim/latest has no frames");',
            "this.frames = frames;",
            "this.replayMotionSource = replayMotionSourceFromRecord(this.replay, bodySim) || REPLAY_MOTION_SOURCE_MOCOPI;",
            "this.liveBodySimAdapterAgeMs = Number.isFinite(adapterAgeMs) ? adapterAgeMs : null;",
            "this.liveBodySimSourceStale = Boolean(bodySim.adapter_stale || bodySim.metadata?.adapter_stale);",
            "this.liveBodySimLastError = String(error?.message || error);",
        }:
            self.assertIn(token, refresh_latest)

        self._assert_tokens_in_order(
            update_scene,
            [
                "this.updateRigAnchor();",
                "if (this.liveBodySimEnabled) {",
                "void this.refreshLiveBodySimLatest();",
            ],
        )

        self.assertIn("if (this.liveBodySimEnabled) return this.frames.at(-1);", current_frame)
        for token in {
            "const mocopiSegmentPose = this.liveBodySimEnabled && hasSegmentPose && !this.liveBodySimSourceStale;",
            "const fixedBodyPose = inXr && !liveBodyPose && !mocopiSegmentPose;",
            "const bodyShellAligned = fixedBodyPose || (selfView && !mocopiSegmentPose) || (!inXr && !mocopiSegmentPose);",
            "centered: bodyShellAligned && !mocopiSegmentPose,",
            "liveMocopi: mocopiSegmentPose,",
            "liveMocopiProfile: this.liveBodySimRenderProfile,",
        }:
            self.assertIn(token, update_scene)

        for token in {
            '"mocopiCalibrate"',
            'if (action === "mocopiCalibrate") this.demo.calibrateLiveBodySimArmorToBody({ source: "xrPanel" });',
            "const poseYaw = options.centered ? 0 : liveProfile ? (liveProfile.yawOffsetRad || 0) : (pose.rotation_z || 0);",
        }:
            self.assertIn(token, js)

        for token in {
            "const segmentPose = frame?.segments?.chest_core;",
            'const target = questAssemblyPoseForPart("chest");',
            "const offset = PART_OFFSETS.chest || [0, 0, 0];",
            "xOffset: roundDebugNumber(target[0] - offset[0] - sourceX * scale * xSign, 4),",
            "yOffset: roundDebugNumber(target[1] - offset[1] - sourceY * scale * ySign, 4),",
            "zOffset: roundDebugNumber(target[2] - offset[2] - sourceZ * scale * zSign, 4),",
            "yawOffsetRad: 0,",
            'this.sendQuestDebugTelemetry("mocopi-calibrated", { force: true });',
        }:
            self.assertIn(token, calibrate_live)

    def test_mocopi_spike_runbook_covers_external_pc_and_hardware_risks(self) -> None:
        runbook = (
            self.repo_root / "docs" / "quest-mocopi-exhibition-spike-2026-05-04.md"
        ).read_text(encoding="utf-8")

        for token in {
            "Bounded mocopi-to-Quest Exhibition Spike",
            "Existing support inspected",
            "Non-goals",
            "External Exhibition PC Plan",
            "same Wi-Fi",
            "USB adb reverse",
            "LAN IP discovery",
            "Windows Firewall prompt",
            "HTTPS/cert",
            "Headset Browser URL",
            "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601",
            "http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=3601",
            "capture_quest_debug_snapshot.ps1",
            "Wrong 5173/8010 Recovery",
            "MOCOPI",
            "BODY",
            "Smoke checklist",
            "Show-floor mocopi acceptance checklist",
            "Pairing",
            "head",
            "hip",
            "left_wrist",
            "right_wrist",
            "left_ankle",
            "right_ankle",
            "Calibration pose",
            "feet hip-width",
            "T-pose",
            "Quest URL and transport path",
            "Latency thresholds",
            "<= 120 ms",
            "<= 250 ms",
            "> 350 ms",
            "1000 ms",
            "Fallback to BODY/static",
            "Phase 0/1/2",
            "Acceptance gates",
            "BODY fallback",
            "static fallback",
            "Privacy and operator notes",
            "identifying motion data",
            "operator/participant consent",
            "Residual hardware risks",
        }:
            self.assertIn(token, runbook)

    def _case_motion_source(self, case: dict) -> str:
        candidates = [
            case["replay"].get("playback", {}).get("motion_source"),
            case["replay"].get("source", {}).get("tracking"),
            case["replay"].get("tracking", {}).get("source"),
            case["replay"].get("motion_provenance", {}).get("primary_source"),
            case["body_sim"].get("motion_source"),
            case["body_sim"].get("source"),
        ]
        for candidate in candidates:
            normalized = self._normalize_source(candidate)
            if normalized:
                return normalized
        return ""

    def _normalize_source(self, value: object) -> str:
        token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        if "mocopi" in token:
            return "mocopi"
        if "body_sim" in token or "simulated_body" in token or "simulation" in token:
            return "body_sim"
        return ""

    def _extract_js_function(self, js: str, signature: str) -> str:
        start = js.find(signature)
        self.assertNotEqual(start, -1, signature)
        next_function = re.search(r"\nfunction\s+[A-Za-z_$][\w$]*\(", js[start + 1 :])
        if next_function:
            return js[start : start + 1 + next_function.start()]
        return js[start:]

    def _extract_js_class_method(self, js: str, signature: str) -> str:
        start = js.find(f"  {signature}")
        self.assertNotEqual(start, -1, signature)
        next_method = re.search(r"\n  (?:async\s+)?[A-Za-z_$][\w$]*\(", js[start + 1 :])
        if next_method:
            return js[start : start + 1 + next_method.start()]
        return js[start:]

    def _assert_tokens_in_order(self, text: str, tokens: list[str]) -> None:
        offset = 0
        for token in tokens:
            index = text.find(token, offset)
            self.assertNotEqual(index, -1, token)
            offset = index + len(token)


if __name__ == "__main__":
    unittest.main()
