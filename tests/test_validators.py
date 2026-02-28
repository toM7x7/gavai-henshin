import unittest

from henshin.forge import create_draft_morphotype, create_draft_suitspec
from henshin.validators import validate_morphotype, validate_suitspec


class TestValidators(unittest.TestCase):
    def test_valid_suitspec(self) -> None:
        payload = create_draft_suitspec()
        validate_suitspec(payload)

    def test_invalid_suitspec_missing_field(self) -> None:
        payload = create_draft_suitspec()
        payload.pop("modules")
        with self.assertRaises(ValueError):
            validate_suitspec(payload)

    def test_valid_morphotype(self) -> None:
        payload = create_draft_morphotype()
        validate_morphotype(payload)

    def test_invalid_morphotype_confidence(self) -> None:
        payload = create_draft_morphotype()
        payload["confidence"] = 1.2
        with self.assertRaises(ValueError):
            validate_morphotype(payload)


if __name__ == "__main__":
    unittest.main()
