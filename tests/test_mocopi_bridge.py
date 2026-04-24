import json
import struct
import unittest

from henshin.mocopi_bridge import decode_bridge_payload, decode_osc_messages


def _osc_string(value: str) -> bytes:
    raw = value.encode("utf-8") + b"\0"
    return raw + (b"\0" * ((4 - len(raw) % 4) % 4))


def _osc_message(address: str, tags: str, *values: object) -> bytes:
    data = _osc_string(address) + _osc_string("," + tags)
    for tag, value in zip(tags, values):
        if tag == "f":
            data += struct.pack(">f", float(value))
        elif tag == "i":
            data += struct.pack(">i", int(value))
        elif tag == "s":
            data += _osc_string(str(value))
        else:
            raise ValueError(tag)
    return data


def _osc_bundle(*messages: bytes) -> bytes:
    data = _osc_string("#bundle") + b"\0" * 8
    for message in messages:
        data += struct.pack(">i", len(message)) + message
    return data


class TestMocopiBridge(unittest.TestCase):
    def test_decode_json_frame_payload(self) -> None:
        packet = json.dumps(
            {
                "frames": [
                    {
                        "dt_sec": 0.033,
                        "bones": {
                            "LeftShoulder": [0.62, 0.38],
                            "RightShoulder": [0.38, 0.38],
                        },
                    }
                ]
            }
        ).encode("utf-8")

        payload = decode_bridge_payload(packet)

        self.assertEqual(payload["frames"][0]["bones"]["LeftShoulder"], [0.62, 0.38])

    def test_decode_osc_bundle_to_frame_payload(self) -> None:
        packet = _osc_bundle(
            _osc_message("/mocopi/LeftShoulder/position", "fff", 0.24, 0.36, 0.0),
            _osc_message("/mocopi/RightShoulder/position", "fff", -0.24, 0.36, 0.0),
            _osc_message("/mocopi/RightHand/position", "fff", -0.55, -0.25, 0.0),
            _osc_message("/mocopi/dt_sec", "f", 0.05),
        )

        messages = decode_osc_messages(packet)
        payload = decode_bridge_payload(packet, input_format="osc")

        self.assertEqual(len(messages), 4)
        self.assertAlmostEqual(payload["frames"][0]["dt_sec"], 0.05, places=5)
        self.assertIn("left_shoulder", payload["frames"][0]["bones"])
        self.assertIn("right_wrist", payload["frames"][0]["bones"])

    def test_unsupported_binary_returns_none_in_auto_mode(self) -> None:
        self.assertIsNone(decode_bridge_payload(b"\x00\x01\x02\x03", input_format="auto"))


if __name__ == "__main__":
    unittest.main()
