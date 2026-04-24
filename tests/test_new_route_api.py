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


if __name__ == "__main__":
    unittest.main()
