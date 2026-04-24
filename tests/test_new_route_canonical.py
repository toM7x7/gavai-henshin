import json
import unittest
from pathlib import Path

from henshin.validators import validate_against_schema, validate_suitspec


class TestNewRouteCanonical(unittest.TestCase):
    def test_canonical_suitspec_points_to_valid_seed(self) -> None:
        config = json.loads(Path("config/new-route.canonical.json").read_text(encoding="utf-8"))
        suitspec = json.loads(Path(config["suitspec_path"]).read_text(encoding="utf-8"))
        partcatalog = json.loads(Path(config["partcatalog_path"]).read_text(encoding="utf-8"))

        validate_suitspec(suitspec)
        validate_against_schema(suitspec, "suitspec")
        validate_against_schema(partcatalog, "partcatalog")

        self.assertEqual(config["canonical_suit_id"], suitspec["suit_id"])
        self.assertIn("quest", config["runtime_targets"])
        self.assertIn("replay", config["runtime_targets"])


if __name__ == "__main__":
    unittest.main()
