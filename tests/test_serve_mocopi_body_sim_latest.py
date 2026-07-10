from __future__ import annotations

import importlib.util
import json
import socket
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "serve_mocopi_body_sim_latest.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("serve_mocopi_body_sim_latest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["serve_mocopi_body_sim_latest"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _mocopi_box(type_4cc: str, data: bytes) -> bytes:
    return struct.pack("<I4s", len(data), type_4cc.encode("ascii")) + data


def _minimal_mocopi_mmf_frame_packet(
    *,
    omit_bones: set[int] | None = None,
    rotations_by_bone: dict[int, tuple[float, float, float, float]] | None = None,
) -> bytes:
    """Tiny Sony mocopi Motion Serializer-style MMF packet.

    The official receiver plugin accepts mocopi UDP by passing bytes through
    mocopi_motion_serializer's IsMmfBytes/ConvertBytesToFrameData path. This
    fixture uses the same little-endian 4CC box structure:
    head + sndf + fram/btrs/btdt/bnid/tran.
    """

    joints = [
        (11, 0.62, 0.38),
        (12, 0.62, 0.38),
        (15, 0.38, 0.38),
        (16, 0.38, 0.38),
        (13, 0.67, 0.48),
        (17, 0.33, 0.48),
        (14, 0.70, 0.61),
        (18, 0.225, 0.625),
        (19, 0.57, 0.58),
        (23, 0.43, 0.58),
        (20, 0.57, 0.76),
        (24, 0.43, 0.76),
        (21, 0.57, 0.92),
        (25, 0.43, 0.92),
    ]
    omit_bones = omit_bones or set()
    rotations_by_bone = rotations_by_bone or {}
    head = _mocopi_box(
        "head",
        _mocopi_box("ftyp", b"sony motion format") + _mocopi_box("vrsn", b"\x01"),
    )
    sender_ip_as_decimal_groups = 127 * 1000 * 1000 * 1000 + 1
    sndf = _mocopi_box(
        "sndf",
        _mocopi_box("ipad", struct.pack("<Q", sender_ip_as_decimal_groups))
        + _mocopi_box("rcvp", struct.pack("<H", 12351)),
    )
    btdt_boxes = []
    for bone_id, x_coord, y_coord in joints:
        if bone_id in omit_bones:
            continue
        rotation = rotations_by_bone.get(bone_id, (0.0, 0.0, 0.0, 1.0))
        btdt_boxes.append(
            _mocopi_box(
                "btdt",
                _mocopi_box("bnid", struct.pack("<h", bone_id))
                + _mocopi_box("tran", struct.pack("<7f", *rotation, x_coord, y_coord, 0)),
            )
        )
    fram = _mocopi_box(
        "fram",
        _mocopi_box("fnum", struct.pack("<i", 1))
        + _mocopi_box("time", struct.pack("<f", 0.1))
        + _mocopi_box("uttm", struct.pack("<d", 0.0))
        + _mocopi_box("tmcd", bytes([0, 0, 0, 1, 30, 0]))
        + _mocopi_box("btrs", b"".join(btdt_boxes)),
    )
    return head + sndf + fram


def _final_segment(result: dict, name: str) -> dict:
    return result["body_sim"]["frames"][-1]["segments"][name]


def _segment_pose_signature(segment: dict) -> tuple[float, float, float]:
    return (
        round(float(segment["position_x"]), 6),
        round(float(segment["position_y"]), 6),
        round(float(segment["rotation_z"]), 6),
    )


def test_payload_to_body_sim_accepts_mocopi_fixture() -> None:
    fixture = (REPO_ROOT / "examples" / "mocopi_sequence.sample.json").read_bytes()

    result = tool.payload_to_body_sim(fixture, max_frames=8)

    assert result["ok"] is True
    body_sim = result["body_sim"]
    assert body_sim["contract_version"] == "mocopi-body-sim-latest-adapter.v1"
    assert body_sim["motion_source"] == "mocopi"
    assert body_sim["source"] == "mocopi"
    assert body_sim["frame_count"] == 7
    assert body_sim["metadata"]["raw_payload_retained"] is False
    assert body_sim["frames"][0]["segments"]


def test_payload_to_body_sim_accepts_embedded_body_sim_without_raw_retention() -> None:
    payload = {
        "source": "mocopi",
        "body_sim": {
            "frames": [
                {
                    "index": 0,
                    "dt_sec": 0.1,
                    "segments": {"right_forearm": {"position_x": 0.1}},
                }
            ]
        },
    }

    result = tool.payload_to_body_sim(json.dumps(payload).encode("utf-8"))

    assert result["ok"] is True
    assert result["body_sim"]["motion_source"] == "mocopi"
    assert result["body_sim"]["frame_count"] == 1
    assert result["body_sim"]["frames"][0]["segments"]["right_forearm"]["position_x"] == 0.1


def test_payload_to_body_sim_accepts_minimal_binary_mocopi_packet() -> None:
    result = tool.payload_to_body_sim(_minimal_mocopi_mmf_frame_packet(), max_frames=8)

    assert result["ok"] is True
    body_sim = result["body_sim"]
    assert body_sim["contract_version"] == "mocopi-body-sim-latest-adapter.v1"
    assert body_sim["motion_source"] == "mocopi"
    assert body_sim["frame_count"] >= 1
    assert body_sim["metadata"]["raw_payload_retained"] is False
    assert body_sim["metadata"]["retarget"] == "mocopi-rotation-chain.xy01.v1"
    assert body_sim["frames"][0]["segments"]["right_forearm"]


def test_binary_mocopi_rotations_drive_body_sim_pose_even_when_positions_are_static() -> None:
    baseline = tool.payload_to_body_sim(_minimal_mocopi_mmf_frame_packet(), max_frames=8)
    bent = tool.payload_to_body_sim(
        _minimal_mocopi_mmf_frame_packet(
            rotations_by_bone={
                16: (0.0, 0.0, 0.3826834324, 0.9238795325),
                17: (0.0, 0.0, -0.2588190451, 0.9659258263),
            },
        ),
        max_frames=8,
    )

    assert baseline["ok"] is True
    assert bent["ok"] is True
    assert _segment_pose_signature(_final_segment(bent, "right_upperarm")) != _segment_pose_signature(_final_segment(baseline, "right_upperarm"))
    assert _segment_pose_signature(_final_segment(bent, "right_forearm")) != _segment_pose_signature(_final_segment(baseline, "right_forearm"))


def test_binary_mocopi_zero_quaternion_falls_back_to_identity_pose() -> None:
    baseline = tool.payload_to_body_sim(_minimal_mocopi_mmf_frame_packet(), max_frames=8)
    zero_quaternion = tool.payload_to_body_sim(
        _minimal_mocopi_mmf_frame_packet(
            rotations_by_bone={
                16: (0.0, 0.0, 0.0, 0.0),
                17: (0.0, 0.0, 0.0, 0.0),
            },
        ),
        max_frames=8,
    )

    assert baseline["ok"] is True
    assert zero_quaternion["ok"] is True
    assert _segment_pose_signature(_final_segment(zero_quaternion, "right_upperarm")) == _segment_pose_signature(_final_segment(baseline, "right_upperarm"))
    assert _segment_pose_signature(_final_segment(zero_quaternion, "right_forearm")) == _segment_pose_signature(_final_segment(baseline, "right_forearm"))


def test_binary_mocopi_missing_upper_arm_rotation_keeps_body_sim_available() -> None:
    result = tool.payload_to_body_sim(
        _minimal_mocopi_mmf_frame_packet(
            omit_bones={16},
            rotations_by_bone={17: (0.0, 0.0, 0.3826834324, 0.9238795325)},
        ),
        max_frames=8,
    )

    assert result["ok"] is True
    assert _final_segment(result, "right_upperarm")
    assert _final_segment(result, "right_forearm")
    assert result["body_sim"]["motion_source"] == "mocopi"


def test_binary_mocopi_limb_chain_combines_upper_and_lower_rotations() -> None:
    baseline = tool.payload_to_body_sim(_minimal_mocopi_mmf_frame_packet(), max_frames=8)
    upper_only = tool.payload_to_body_sim(
        _minimal_mocopi_mmf_frame_packet(rotations_by_bone={16: (0.0, 0.0, 0.3826834324, 0.9238795325)}),
        max_frames=8,
    )
    lower_only = tool.payload_to_body_sim(
        _minimal_mocopi_mmf_frame_packet(rotations_by_bone={17: (0.0, 0.0, -0.2588190451, 0.9659258263)}),
        max_frames=8,
    )
    combined = tool.payload_to_body_sim(
        _minimal_mocopi_mmf_frame_packet(
            rotations_by_bone={
                16: (0.0, 0.0, 0.3826834324, 0.9238795325),
                17: (0.0, 0.0, -0.2588190451, 0.9659258263),
            },
        ),
        max_frames=8,
    )

    assert baseline["ok"] is True
    assert upper_only["ok"] is True
    assert lower_only["ok"] is True
    assert combined["ok"] is True
    assert _segment_pose_signature(_final_segment(upper_only, "right_upperarm")) != _segment_pose_signature(_final_segment(baseline, "right_upperarm"))
    assert _segment_pose_signature(_final_segment(lower_only, "right_upperarm")) == _segment_pose_signature(_final_segment(baseline, "right_upperarm"))
    assert _segment_pose_signature(_final_segment(lower_only, "right_forearm")) != _segment_pose_signature(_final_segment(baseline, "right_forearm"))
    assert _segment_pose_signature(_final_segment(combined, "right_forearm")) != _segment_pose_signature(_final_segment(upper_only, "right_forearm"))
    assert _segment_pose_signature(_final_segment(combined, "right_forearm")) != _segment_pose_signature(_final_segment(lower_only, "right_forearm"))


def test_payload_to_body_sim_rejects_unknown_or_malformed_payload() -> None:
    binary = tool.payload_to_body_sim(b"\x00\x01\x02")
    unknown = tool.payload_to_body_sim(json.dumps({"hello": "world"}).encode("utf-8"))

    assert binary["ok"] is False
    assert "unsupported UDP payload" in binary["error"]
    assert unknown["ok"] is False
    assert "body_sim frames or mocopi-like frames" in unknown["error"]


def test_http_latest_serves_debug_and_body_sim_after_ingest() -> None:
    adapter = tool.MocopiBodySimLatestAdapter()
    http_port = _free_tcp_port()
    server = ThreadingHTTPServer(("127.0.0.1", http_port), tool.make_handler(adapter))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{http_port}/api/mocopi/debug/latest", timeout=2) as response:
            debug = json.loads(response.read().decode("utf-8"))
        assert debug["ok"] is False

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{http_port}/body-sim/latest", timeout=2)
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("body-sim/latest should be 404 before first valid ingest")

        adapter.ingest_packet((REPO_ROOT / "examples" / "mocopi_sequence.sample.json").read_bytes(), sender="127.0.0.1:1")
        with urllib.request.urlopen(f"http://127.0.0.1:{http_port}/body-sim/latest", timeout=2) as response:
            latest = json.loads(response.read().decode("utf-8"))
        assert latest["motion_source"] == "mocopi"
        assert latest["adapter_stale"] is False
        assert latest["adapter_packet_age_ms"] is not None
        assert latest["metadata"]["adapter_stale"] is False
        assert latest["frames"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_udp_receiver_updates_http_latest() -> None:
    adapter = tool.MocopiBodySimLatestAdapter()
    stop_event = threading.Event()
    udp_port = _free_udp_port()
    receiver = threading.Thread(
        target=tool.run_udp_receiver,
        args=(adapter,),
        kwargs={"bind_host": "127.0.0.1", "udp_port": udp_port, "stop_event": stop_event, "timeout_sec": 0.05},
        daemon=True,
    )
    receiver.start()
    time.sleep(0.1)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto((REPO_ROOT / "examples" / "mocopi_sequence.sample.json").read_bytes(), ("127.0.0.1", udp_port))
        deadline = time.time() + 2
        while time.time() < deadline and not adapter.latest_body_sim():
            time.sleep(0.05)
        assert adapter.latest_body_sim()["motion_source"] == "mocopi"
        assert adapter.debug_summary()["valid_packet_count"] == 1
        assert adapter.debug_summary()["latest"]["stale"] is False
    finally:
        stop_event.set()
        receiver.join(timeout=2)


def test_latest_body_sim_and_debug_mark_stale_without_erasing_last_pose() -> None:
    adapter = tool.MocopiBodySimLatestAdapter()
    result = adapter.ingest_packet(_minimal_mocopi_mmf_frame_packet(), sender="127.0.0.1:1")
    assert result["ok"] is True

    adapter.last_valid_received_at = time.time() - 2.0

    latest = adapter.latest_body_sim()
    debug = adapter.debug_summary()
    assert latest is not None
    assert latest["frames"]
    assert latest["adapter_stale"] is True
    assert latest["metadata"]["adapter_stale"] is True
    assert debug["latest"]["stale"] is True
