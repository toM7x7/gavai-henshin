import json
import tempfile
import unittest
from pathlib import Path

from henshin.new_route_api import NewRouteApi


class TestNewRouteApi(unittest.TestCase):
    def setUp(self) -> None:
        self.api = NewRouteApi(Path("."))

    def test_health_exposes_phase_contracts(self) -> None:
        response = self.api.get("/health")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["service"], "new-route-api")
        self.assertIn("SuitManifest", response.body["contracts"])

    def test_catalog_parts_returns_seed_catalog(self) -> None:
        response = self.api.get("/v1/catalog/parts")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertTrue(response.body["ok"])
        self.assertEqual(response.body["catalog_id"], "PCAT-VIEWER-SEED-0001")
        self.assertEqual(len(response.body["parts"]), 18)

    def test_get_manifest_returns_sample_manifest(self) -> None:
        response = self.api.get("/v1/manifests/MNF-20260424-SAMP")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["manifest"]["manifest_id"], "MNF-20260424-SAMP")
        self.assertEqual(response.body["manifest"]["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")

    def test_get_manifest_returns_404_for_unknown_manifest(self) -> None:
        response = self.api.get("/v1/manifests/MNF-20260424-NONE")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.status, 404)
        self.assertFalse(response.body["ok"])

    def test_create_suit_saves_suitspec(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            response = api.post("/v1/suits", {"suitspec": suitspec})

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["suit_id"], "VDA-AXIS-OP-00-0001")
            self.assertEqual(response.body["schema_version"], "0.2")
            self.assertTrue((Path(tmp) / "suits" / "VDA-AXIS-OP-00-0001" / "suitspec.json").is_file())
            self.assertEqual(response.body["links"]["manifest"], "/v1/suits/VDA-AXIS-OP-00-0001/manifest")

    def test_issue_suit_id_reserves_named_registry_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits/issue-id", {"series": "axis", "role": "guest", "display_name": "試作鎧A"})
            second = api.post("/v1/suits/issue-id", {"series": "axis", "role": "guest"})
            assert first is not None
            fetched = api.get(f"/v1/suits/code/{first.body['recall_code']}")
            quest = api.get(f"/v1/quest/recall/{first.body['recall_code']}")

            self.assertIsNotNone(second)
            self.assertIsNotNone(fetched)
            self.assertIsNotNone(quest)
            assert second is not None and fetched is not None and quest is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(first.body["suit_id"], "VDA-AXIS-GUEST-00-0001")
            self.assertRegex(first.body["recall_code"], r"^[A-Z0-9]{4}$")
            self.assertEqual(first.body["display_name"], "試作鎧A")
            self.assertEqual(first.body["issue"]["seq"], 1)
            self.assertEqual(first.body["issue"]["recall_code"], first.body["recall_code"])
            self.assertEqual(second.body["suit_id"], "VDA-AXIS-GUEST-00-0002")
            self.assertRegex(second.body["recall_code"], r"^[A-Z0-9]{4}$")
            self.assertEqual(fetched.status, 200)
            self.assertIsNone(fetched.body["suitspec"])
            self.assertEqual(fetched.body["suit"]["metadata"]["display_name"], "試作鎧A")
            self.assertEqual(fetched.body["recall_code"], first.body["recall_code"])
            self.assertEqual(quest.status, 200)
            self.assertFalse(quest.body["suitspec_ready"])
            self.assertFalse(quest.body["manifest_ready"])
            self.assertEqual(quest.body["display_name"], "試作鎧A")
            self.assertNotIn("metadata", quest.body["suit"])

    def test_create_suit_preserves_issue_metadata_and_display_name(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            issued = api.post("/v1/suits/issue-id", {"series": "axis", "role": "op", "display_name": "生成前"})
            assert issued is not None
            response = api.post("/v1/suits", {"suitspec": suitspec, "display_name": "完成鎧"})
            fetched = api.get("/v1/suits/VDA-AXIS-OP-00-0001")
            by_code = api.get(f"/v1/suits/code/{issued.body['recall_code']}")

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            self.assertIsNotNone(by_code)
            assert response is not None and fetched is not None and by_code is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["recall_code"], issued.body["recall_code"])
            self.assertEqual(response.body["suit"]["metadata"]["display_name"], "完成鎧")
            self.assertEqual(response.body["suit"]["metadata"]["issue"]["seq"], 1)
            self.assertEqual(response.body["suit"]["metadata"]["issue"]["recall_code"], issued.body["recall_code"])
            self.assertEqual(fetched.body["suitspec"]["suit_id"], "VDA-AXIS-OP-00-0001")
            self.assertEqual(fetched.body["suit"]["metadata"]["display_name"], "完成鎧")
            self.assertEqual(by_code.body["suit"]["suit_id"], "VDA-AXIS-OP-00-0001")

    def test_create_suit_rejects_duplicate_recall_code_for_other_suit(self) -> None:
        suitspec = self._sample_suitspec()
        other = json.loads(json.dumps(suitspec))
        other["suit_id"] = "VDA-AXIS-OP-00-0002"
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits", {"suitspec": suitspec, "recall_code": "A1B2"})
            second = api.post("/v1/suits", {"suitspec": other, "recall_code": "A1B2"})

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(second.status, 400)

    def test_issue_suit_id_rejects_duplicate_recall_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits/issue-id", {"recall_code": "A1B2"})
            second = api.post("/v1/suits/issue-id", {"recall_code": "A1B2"})

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(second.status, 400)
            self.assertIn("recall_code", second.body["error"])

    def test_recall_code_lookup_rejects_invalid_or_unknown_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            invalid = api.get("/v1/suits/code/ABC")
            unknown = api.get("/v1/quest/recall/ZZZZ")

            self.assertIsNotNone(invalid)
            self.assertIsNotNone(unknown)
            assert invalid is not None and unknown is not None
            self.assertEqual(invalid.status, 400)
            self.assertEqual(unknown.status, 404)

    def test_create_suit_rejects_duplicate_without_overwrite(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            first = api.post("/v1/suits", {"suitspec": suitspec})
            second = api.post("/v1/suits", {"suitspec": suitspec})

            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertEqual(first.status, 201)
            self.assertEqual(second.status, 409)

    def test_manifest_post_projects_saved_suitspec(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            api.post("/v1/suits", {"suitspec": suitspec})

            response = api.post(
                "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
                {"manifest_id": "MNF-20260424-ABCD", "status": "READY"},
            )
            fetched = api.get("/v1/manifests/MNF-20260424-ABCD")
            assert response is not None
            quest = api.get(f"/v1/quest/recall/{response.body['suit']['recall_code']}")

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            self.assertIsNotNone(quest)
            assert fetched is not None and quest is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(response.body["manifest"]["status"], "READY")
            self.assertEqual(response.body["manifest"]["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")
            self.assertEqual(fetched.status, 200)
            self.assertEqual(fetched.body["manifest"]["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(quest.status, 200)
            self.assertTrue(quest.body["suitspec_ready"])
            self.assertTrue(quest.body["manifest_ready"])
            self.assertEqual(quest.body["suit_id"], "VDA-AXIS-OP-00-0001")
            self.assertEqual(quest.body["manifest"]["manifest_id"], "MNF-20260424-ABCD")

    def test_manifest_post_returns_404_for_unknown_suit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            response = api.post(
                "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
                {"manifest_id": "MNF-20260424-ABCD"},
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 404)

    def test_create_trial_uses_latest_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            response = api.post(
                "/v1/trials",
                {
                    "suit_id": "VDA-AXIS-OP-00-0001",
                    "session_id": "S-TRIAL-UNIT-0001",
                    "operator_id": "operator-local",
                    "device_id": "quest-local",
                    "tracking_source": "iw_sdk",
                },
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["session_id"], "S-TRIAL-UNIT-0001")
            self.assertEqual(response.body["trial"]["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(response.body["trial"]["events"][0]["event_type"], "SESSION_CREATED")

    def test_append_trial_event_updates_state_and_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})

            response = api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {
                    "event_type": "DEPOSITION_STARTED",
                    "state_after": "DEPOSITION",
                    "actor": {"type": "device", "id": "quest-local"},
                    "payload": {"source": "quest-browser"},
                    "idempotency_key": "deposition-start",
                },
            )
            fetched = api.get("/v1/trials/S-TRIAL-UNIT-0001")

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            assert response is not None and fetched is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["event"]["sequence"], 1)
            self.assertEqual(response.body["trial"]["state"], "DEPOSITION")
            self.assertEqual(fetched.body["trial"]["events"][1]["idempotency_key"], "deposition-start")

    def test_append_trial_event_does_not_regress_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_COMPLETED", "state_after": "ACTIVE"},
            )

            response = api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "VOICE_CAPTURED", "state_after": "POSTED"},
            )

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["trial"]["state"], "ACTIVE")
            self.assertEqual(response.body["event"]["state_before"], "ACTIVE")
            self.assertEqual(response.body["event"]["state_after"], "ACTIVE")
            self.assertEqual(response.body["event"]["payload"]["requested_state_after"], "POSTED")

    def test_create_trial_returns_conflict_without_manifest(self) -> None:
        suitspec = self._sample_suitspec()
        with tempfile.TemporaryDirectory() as tmp:
            api = NewRouteApi(Path("."), suit_store_root=Path(tmp) / "suits")
            api.post("/v1/suits", {"suitspec": suitspec})

            response = api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001"})

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 409)

    def test_get_trial_replay_generates_replay_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_STARTED", "state_after": "DEPOSITION"},
            )

            response = api.get("/v1/trials/S-TRIAL-UNIT-0001/replay")

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 200)
            self.assertRegex(response.body["replay_id"], r"^RPL-[0-9]{8}-[A-Z0-9]{4}$")
            self.assertEqual(response.body["replay"]["session_id"], "S-TRIAL-UNIT-0001")
            self.assertEqual(response.body["replay"]["source_events"]["event_ids"][0], response.body["session"]["events"][0]["event_id"])
            self.assertTrue(response.body["replay_path"].endswith("replay-script.json"))

    def test_get_trial_replay_expands_motion_capture_samples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_STARTED", "state_after": "DEPOSITION"},
            )
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {
                    "event_type": "DEPOSITION_COMPLETED",
                    "state_after": "ACTIVE",
                    "payload": {
                        "motion_capture": {
                            "format": "quest-live-pose.v0",
                            "tracking": "hmd_plus_controllers",
                            "timebase": "deposition_elapsed_sec",
                            "coordinate_space": {"head": "rig_local", "right_hand": "rig_local"},
                            "frames": [
                                {"t": 0.2, "head": [0, 1.6, 0], "right_hand": [0.5, 1.2, -0.2]},
                                {"t": 0.0, "head": [0, 1.6, 0], "right_hand": [0.3, 1.2, -0.2]},
                            ],
                        }
                    },
                },
            )

            response = api.get("/v1/trials/S-TRIAL-UNIT-0001/replay")

            self.assertIsNotNone(response)
            assert response is not None
            self.assertEqual(response.status, 200)
            motion_segments = [
                segment for segment in response.body["replay"]["timeline"]
                if str(segment["segment_id"]).startswith("SEG-MOTION-")
            ]
            self.assertEqual(len(motion_segments), 1)
            self.assertEqual(motion_segments[0]["duration_sec"], 0.2)
            self.assertEqual(len(motion_segments[0]["actions"]), 2)
            action_times = [action["at_time_sec"] for action in motion_segments[0]["actions"]]
            self.assertEqual(action_times, sorted(action_times))
            self.assertAlmostEqual(action_times[0], motion_segments[0]["start_time_sec"], places=3)
            self.assertEqual(round(action_times[1] - action_times[0], 3), 0.2)
            self.assertEqual(motion_segments[0]["actions"][1]["action_type"], "deposition_progress")
            self.assertEqual(motion_segments[0]["actions"][1]["params"]["motion_capture_format"], "quest-live-pose.v0")
            self.assertEqual(motion_segments[0]["actions"][1]["params"]["timebase"], "deposition_elapsed_sec")
            self.assertEqual(motion_segments[0]["actions"][1]["params"]["motion_frame"]["right_hand"], [0.5, 1.2, -0.2])
            event_segment = next(
                segment for segment in response.body["replay"]["timeline"]
                if segment["segment_id"] == "SEG-0002"
            )
            compact_motion = event_segment["actions"][0]["params"]["payload"]["motion_capture"]
            self.assertEqual(compact_motion["frame_count"], 2)
            self.assertNotIn("frames", compact_motion)

    def test_get_latest_trial_returns_replay_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            api = self._api_with_manifest(Path(tmp) / "suits")
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0001"})
            api.post("/v1/trials", {"suit_id": "VDA-AXIS-OP-00-0001", "session_id": "S-TRIAL-UNIT-0002"})
            api.post(
                "/v1/trials/S-TRIAL-UNIT-0001/events",
                {"event_type": "DEPOSITION_COMPLETED", "state_after": "ACTIVE"},
            )
            api.get("/v1/trials/S-TRIAL-UNIT-0001/replay")

            latest = api.get("/v1/trials/latest")
            listed = api.get("/v1/trials")

            self.assertIsNotNone(latest)
            self.assertIsNotNone(listed)
            assert latest is not None and listed is not None
            self.assertEqual(latest.status, 200)
            self.assertEqual(latest.body["trial_id"], "S-TRIAL-UNIT-0001")
            self.assertEqual(latest.body["summary"]["state"], "ACTIVE")
            self.assertEqual(latest.body["summary"]["event_count"], 2)
            self.assertTrue(latest.body["summary"]["replay_script_path"].endswith("replay-script.json"))
            self.assertEqual(listed.body["count"], 2)
            self.assertEqual(listed.body["latest"]["session_id"], "S-TRIAL-UNIT-0001")

    def _sample_suitspec(self) -> dict:
        return json.loads(Path("examples/suitspec.sample.json").read_text(encoding="utf-8"))

    def _api_with_manifest(self, suit_store_root: Path) -> NewRouteApi:
        api = NewRouteApi(Path("."), suit_store_root=suit_store_root)
        api.post("/v1/suits", {"suitspec": self._sample_suitspec()})
        api.post(
            "/v1/suits/VDA-AXIS-OP-00-0001/manifest",
            {"manifest_id": "MNF-20260424-ABCD", "status": "READY"},
        )
        return api


if __name__ == "__main__":
    unittest.main()
