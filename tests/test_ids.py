import re
import unittest
from datetime import datetime, timezone

from henshin.ids import (
    generate_approval_id,
    generate_morphotype_id,
    generate_recall_code,
    generate_session_id,
    generate_suit_id,
    next_suit_id,
    normalize_recall_code,
    next_recall_code,
    parse_suit_id,
)


class TestIDs(unittest.TestCase):
    def test_session_id_format(self) -> None:
        fixed = datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc)
        session_id = generate_session_id(now=fixed)
        self.assertTrue(re.fullmatch(r"S-20260228-[A-Z0-9]{4}", session_id))

    def test_suit_id_format(self) -> None:
        suit_id = generate_suit_id(series="axis", role="op", rev=1, seq=42)
        self.assertEqual(suit_id, "VDA-AXIS-OP-01-0042")

    def test_parse_suit_id(self) -> None:
        parsed = parse_suit_id("VDA-AXIS-OP-01-0042")
        self.assertEqual(parsed, {"series": "AXIS", "role": "OP", "rev": 1, "seq": 42})

    def test_next_suit_id_uses_existing_series_role_rev(self) -> None:
        suit_id = next_suit_id(
            ["VDA-AXIS-OP-00-0001", "VDA-AXIS-OP-00-0002", "VDA-AXIS-GUEST-00-0009"],
            series="axis",
            role="op",
            rev=0,
        )
        self.assertEqual(suit_id, "VDA-AXIS-OP-00-0003")

    def test_recall_code_is_four_alphanumeric_characters(self) -> None:
        code = generate_recall_code()
        self.assertTrue(re.fullmatch(r"[A-Z0-9]{4}", code))
        self.assertEqual(normalize_recall_code("a1-b2"), "A1B2")

    def test_next_recall_code_skips_existing_code(self) -> None:
        class FixedRng:
            def __init__(self) -> None:
                self.values = iter([0, 0, 0, 0, 0, 0, 0, 1])

            def choice(self, alphabet: str) -> str:
                return alphabet[next(self.values)]

        code = next_recall_code(["AAAA"], rng=FixedRng())
        self.assertEqual(code, "AAAB")

    def test_approval_id_format(self) -> None:
        approval_id = generate_approval_id()
        self.assertTrue(re.fullmatch(r"APV-[0-9]{8}", approval_id))

    def test_morphotype_id_format(self) -> None:
        morphotype_id = generate_morphotype_id()
        self.assertTrue(re.fullmatch(r"MTP-[0-9]{8}", morphotype_id))


if __name__ == "__main__":
    unittest.main()
