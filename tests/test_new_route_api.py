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

            self.assertIsNotNone(response)
            self.assertIsNotNone(fetched)
            assert response is not None and fetched is not None
            self.assertEqual(response.status, 201)
            self.assertEqual(response.body["manifest_id"], "MNF-20260424-ABCD")
            self.assertEqual(response.body["manifest"]["status"], "READY")
            self.assertEqual(response.body["manifest"]["parts"]["helmet"]["catalog_part_id"], "viewer.mesh.helmet.v1")
            self.assertEqual(fetched.status, 200)
            self.assertEqual(fetched.body["manifest"]["manifest_id"], "MNF-20260424-ABCD")

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

    def _sample_suitspec(self) -> dict:
        return json.loads(Path("examples/suitspec.sample.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
