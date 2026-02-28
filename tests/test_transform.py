import unittest

from henshin.transform import ProtocolStateMachine


class TestTransform(unittest.TestCase):
    def test_happy_path_reaches_archived(self) -> None:
        machine = ProtocolStateMachine()
        machine.run_happy_path()
        self.assertEqual(machine.state, "ARCHIVED")
        self.assertGreater(len(machine.events), 0)

    def test_illegal_transition_raises(self) -> None:
        machine = ProtocolStateMachine()
        with self.assertRaises(ValueError):
            machine.transition("APPROVED")

    def test_refusal(self) -> None:
        machine = ProtocolStateMachine()
        machine.transition("POSTED")
        machine.refuse("AUDIT_MISMATCH")
        self.assertEqual(machine.state, "REFUSED")


if __name__ == "__main__":
    unittest.main()
