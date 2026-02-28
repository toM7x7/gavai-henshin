import re
import unittest
from datetime import datetime, timezone

from henshin.ids import (
    generate_approval_id,
    generate_morphotype_id,
    generate_session_id,
    generate_suit_id,
)


class TestIDs(unittest.TestCase):
    def test_session_id_format(self) -> None:
        fixed = datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc)
        session_id = generate_session_id(now=fixed)
        self.assertTrue(re.fullmatch(r"S-20260228-[A-Z0-9]{4}", session_id))

    def test_suit_id_format(self) -> None:
        suit_id = generate_suit_id(series="axis", role="op", rev=1, seq=42)
        self.assertEqual(suit_id, "VDA-AXIS-OP-01-0042")

    def test_approval_id_format(self) -> None:
        approval_id = generate_approval_id()
        self.assertTrue(re.fullmatch(r"APV-[0-9]{8}", approval_id))

    def test_morphotype_id_format(self) -> None:
        morphotype_id = generate_morphotype_id()
        self.assertTrue(re.fullmatch(r"MTP-[0-9]{8}", morphotype_id))


if __name__ == "__main__":
    unittest.main()
