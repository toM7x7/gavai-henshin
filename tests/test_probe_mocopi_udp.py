from __future__ import annotations

import importlib.util
import socket
import sys
import threading
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "probe_mocopi_udp.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("probe_mocopi_udp", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["probe_mocopi_udp"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_udp_probe_counts_packets_without_payload_retention() -> None:
    port = _free_udp_port()
    holder: dict[str, dict] = {}

    def listen() -> None:
        holder["report"] = tool.probe_mocopi_udp(
            bind_host="127.0.0.1",
            port=port,
            seconds=0.8,
            timeout_sec=0.05,
        )

    thread = threading.Thread(target=listen)
    thread.start()
    time.sleep(0.15)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.sendto(b"mocopi packet one", ("127.0.0.1", port))
        sender.sendto(b"mocopi packet two", ("127.0.0.1", port))
    thread.join(timeout=2.0)

    report = holder["report"]
    assert report["contract_version"] == "mocopi-udp-probe.v1"
    assert report["ok"] is True
    assert report["label"] == "udp-received"
    assert report["packet_count"] >= 2
    assert report["total_bytes"] > 0
    assert report["raw_payload_retained"] is False
    assert report["sample"] is None


def test_udp_probe_no_packets_reports_no_go_transport() -> None:
    report = tool.summarize_probe_events(
        [],
        bind_host="0.0.0.0",
        port=12351,
        seconds=1.0,
        elapsed_sec=1.0,
        min_packets=1,
        raw_payload_retained=False,
    )

    assert report["ok"] is False
    assert report["label"] == "udp-no-packets"
    assert any("IPv4" in action for action in report["next_actions"])
