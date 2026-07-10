import copy
import json
import unittest
from pathlib import Path

from henshin.validators import validate_against_schema


class TestReplayRecordContract(unittest.TestCase):
    def setUp(self) -> None:
        self.sample = json.loads(Path("examples/replay-record.sample.json").read_text(encoding="utf-8"))

    def test_sample_replay_record_matches_schema(self) -> None:
        validate_against_schema(self.sample, "replay-record")

    def test_replay_record_preserves_experience_identity_and_runtime_contract(self) -> None:
        self.assertEqual(self.sample["schema_version"], "0.2")
        self.assertRegex(self.sample["suit_id"], r"^VDA-")
        self.assertRegex(self.sample["recall_code"], r"^[A-Z0-9]{4}$")
        self.assertEqual(self.sample["runtime_package"]["contract_version"], "base-suit-overlay.v1")
        self.assertEqual(
            self.sample["runtime_package"]["render_placement_contract"],
            "runtime-render-placement.v1",
        )
        self.assertEqual(self.sample["transform_trial"]["tracking_source"], "mocopi")
        self.assertIn(self.sample["playback"]["view_mode"], {"self", "mirror", "observer"})
        self.assertEqual(self.sample["playback"]["motion_source"], "mocopi")
        self.assertGreaterEqual(self.sample["transform_trial"]["event_count"], len(self.sample["source_events"]))

    def test_replay_record_keeps_voice_audio_and_artifact_refs(self) -> None:
        audio = self.sample["audio"]
        self.assertIn(audio["voice_capture"]["status"], {"captured", "mock", "not_captured", "unavailable"})
        self.assertTrue(audio["trigger"]["detected"])
        self.assertEqual(audio["trigger"]["phrase"], "generate")
        self.assertIn("artifact_ref", audio["voice_capture"])
        self.assertIn("audio_ref", audio["tts"])

        artifacts = self.sample["artifacts"]
        for key in ("replay_script", "transform_session", "runtime_package"):
            with self.subTest(artifact=key):
                self.assertIn("uri", artifacts[key])
                self.assertTrue(artifacts[key]["uri"])
                self.assertTrue(artifacts[key]["portable"])

    def test_replay_record_stores_japanese_ui_event_labels(self) -> None:
        presentation = self.sample["presentation"]
        self.assertEqual(presentation["default_locale"], "ja-JP")
        self.assertTrue(presentation["display_policy"]["ui_uses_labels_not_raw_event_types"])
        self.assertTrue(presentation["display_policy"]["hide_private_ids_on_public_display"])

        ja_labels = {
            item["event_type"]: item["label"]
            for item in presentation["event_labels"]
            if item["locale"] == "ja-JP"
        }
        for event in self.sample["source_events"]:
            with self.subTest(event_type=event["event_type"]):
                self.assertIn(event["event_type"], ja_labels)
                self.assertNotEqual(ja_labels[event["event_type"]], event["event_type"])

        view_labels = {
            item["view_mode"]: item["label"]
            for item in presentation["view_mode_labels"]
            if item["locale"] == "ja-JP"
        }
        self.assertEqual(view_labels["mirror"], "鏡")

    def test_replay_record_declares_mocopi_motion_provenance(self) -> None:
        motion = self.sample["motion_provenance"]

        self.assertEqual(motion["primary_source"], "mocopi")
        self.assertEqual(motion["capture_system"]["provider"], "mocopi")
        self.assertEqual(motion["capture_system"]["format"], "mocopi-joint-stream.v1")
        self.assertEqual(motion["frame_rate_hz"], 30)
        self.assertEqual(motion["frame_count"], self.sample["playback"]["motion_frame_count"])
        self.assertEqual(motion["timebase"], "deposition_elapsed_sec")
        self.assertEqual(motion["coordinate_space"], "mocopi_world_y_up")
        self.assertEqual(motion["privacy_classification"], "identifying_motion")
        self.assertIn("session_id", motion["session_ref"])
        self.assertIn("source_session_id", motion["session_ref"])
        self.assertEqual(motion["source_artifact_ref"]["retention_role"], "private_raw_capture")
        self.assertEqual(self.sample["artifacts"]["mocopi_motion"]["schema_version"], "mocopi-joint-stream.v1")

    def test_replay_record_declares_web_service_operation(self) -> None:
        operation = self.sample["operation"]

        self.assertEqual(operation["mode"], "web_service")
        self.assertEqual(operation["storage_backend"], "cloud_sql_gcs")
        self.assertEqual(operation["write_path"], "cloud_sql_metadata_gcs_artifacts")
        self.assertEqual(operation["api_surface"]["replay_record_endpoint"], "/v1/trials/{trialId}/replay-record")
        self.assertIn("gs", operation["runtime_resolver"]["artifact_uri_schemes"])
        self.assertTrue(operation["runtime_resolver"]["requires_runtime_package_snapshot"])
        self.assertFalse(operation["runtime_resolver"]["fallback_allowed"])
        self.assertTrue(operation["external_pc_runtime"]["offline_supported"])
        self.assertFalse(operation["external_pc_runtime"]["network_required"])
        self.assertTrue(operation["external_pc_runtime"]["preflight_required"])

    def test_replay_record_declares_portability_retention_and_privacy_policy(self) -> None:
        portability = self.sample["portability"]
        self.assertEqual(portability["uri_policy"], "bundle_relative_or_cloud_uri")
        self.assertIn("external_exhibition_pc", portability["deployment_targets"])
        self.assertIn("gcp_cloud_run", portability["deployment_targets"])
        self.assertFalse(portability["move_validation"]["absolute_local_paths_allowed"])
        self.assertEqual(
            portability["move_validation"]["validation_strategy"],
            "validate_schema_then_resolve_required_artifacts",
        )
        self.assertEqual(portability["cloud_artifact_root"]["storage_backend"], "gcs")
        self.assertTrue(portability["cloud_artifact_root"]["uri"].startswith("gs://"))

        retention = self.sample["media_retention"]
        self.assertIn("portable_bundle_zip", retention["export_formats"])
        self.assertTrue(retention["contains_voice_audio"])
        self.assertTrue(retention["contains_motion_capture"])
        self.assertEqual(retention["mocopi_raw_retention"], "retain_with_consent")
        self.assertTrue(retention["export_review_required"])

        privacy = self.sample["privacy"]
        self.assertEqual(privacy["operator_consent"]["status"], "assumed_for_operator_demo")
        self.assertFalse(privacy["cloud_export_allowed"])
        self.assertIn("voice_audio", privacy["pii_classes"])
        self.assertIn("mocopi_motion", privacy["pii_classes"])
        self.assertEqual(privacy["motion_storage"], "raw_frames_retained")
        self.assertTrue(privacy["exhibition_pc_policy"]["operator_unlock_required"])
        self.assertEqual(privacy["exhibition_pc_policy"]["public_display_redaction"], "hide_raw_audio_and_ids")
        self.assertTrue(privacy["exhibition_pc_policy"]["raw_media_export_requires_granted_consent"])

        validity = self.sample["validity"]
        self.assertTrue(validity["valid_when_moved"]["portable_bundle_required"])
        self.assertEqual(validity["valid_when_moved"]["missing_required_artifact_behavior"], "invalid")
        self.assertIn("gs", validity["valid_in_cloud"]["uri_schemes"])
        self.assertTrue(validity["integrity_policy"]["runtime_package_snapshot_required"])

    def test_replay_record_rejects_absolute_local_artifact_paths(self) -> None:
        absolute = copy.deepcopy(self.sample)
        absolute["artifacts"]["replay_script"]["uri"] = "C:\\demo\\replay-script.json"

        with self.assertRaises(ValueError):
            validate_against_schema(absolute, "replay-record")

    def test_replay_record_rejects_missing_mocopi_frame_rate(self) -> None:
        missing = copy.deepcopy(self.sample)
        missing["motion_provenance"].pop("frame_rate_hz")

        with self.assertRaises(ValueError):
            validate_against_schema(missing, "replay-record")

    def test_replay_record_rejects_missing_presentation_labels(self) -> None:
        missing = copy.deepcopy(self.sample)
        missing.pop("presentation")

        with self.assertRaises(ValueError):
            validate_against_schema(missing, "replay-record")

    def test_replay_record_allows_cloud_portable_gcs_artifact_refs(self) -> None:
        cloud = copy.deepcopy(self.sample)
        cloud["artifacts"]["runtime_package"]["uri"] = (
            "gs://gavai-henshin-replay-demo/replay-bundles/RPB-20260504-0076/runtime-package.json"
        )
        cloud["artifacts"]["runtime_package"]["storage_backend"] = "gcs"

        validate_against_schema(cloud, "replay-record")

    def test_replay_record_requires_recall_code(self) -> None:
        missing = copy.deepcopy(self.sample)
        missing.pop("recall_code")

        with self.assertRaises(ValueError):
            validate_against_schema(missing, "replay-record")


if __name__ == "__main__":
    unittest.main()
