"""Probe mocopi UDP reachability without storing raw motion payloads.

This is a transport-level rehearsal tool, not a live Quest retargeter. It lets
an operator confirm that the mocopi phone app can send UDP packets to the
exhibition PC before debugging body fitting, IK, or Quest rendering.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "mocopi-udp-probe.v1"
DEFAULT_PORT = 12351
DEFAULT_OUT = Path("qa/mocopi-udp-probe-latest.json")


def probe_mocopi_udp(
    *,
    bind_host: str = "0.0.0.0",
    port: int = DEFAULT_PORT,
    seconds: float = 20.0,
    min_packets: int = 1,
    timeout_sec: float = 0.25,
    include_sample_hex: bool = False,
    max_sample_bytes: int = 32,
) -> dict[str, Any]:
    """Listen for UDP packets and summarize transport health.

    Raw packet payloads are intentionally not retained by default because
    motion streams can identify a participant. Use include_sample_hex only when
    debugging protocol-level parsing in a private engineering session.
    """

    if seconds <= 0:
        raise ValueError("seconds must be greater than 0.")
    if port <= 0 or port > 65535:
        raise ValueError("port must be between 1 and 65535.")
    if min_packets < 0:
        raise ValueError("min_packets must be 0 or greater.")

    events: list[dict[str, Any]] = []
    started = time.time()
    deadline = started + seconds
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind_host, port))
        sock.settimeout(timeout_sec)
        while time.time() < deadline:
            try:
                payload, sender = sock.recvfrom(65535)
            except socket.timeout:
                continue
            now = time.time()
            event: dict[str, Any] = {
                "t_ms": round((now - started) * 1000.0, 3),
                "bytes": len(payload),
                "sender": f"{sender[0]}:{sender[1]}",
            }
            if include_sample_hex and not any("sample_hex" in item for item in events):
                event["sample_hex"] = payload[:max_sample_bytes].hex()
                event["sample_bytes"] = min(len(payload), max_sample_bytes)
            events.append(event)

    elapsed = max(time.time() - started, 0.001)
    return summarize_probe_events(
        events,
        bind_host=bind_host,
        port=port,
        seconds=seconds,
        elapsed_sec=elapsed,
        min_packets=min_packets,
        raw_payload_retained=include_sample_hex,
    )


def summarize_probe_events(
    events: list[dict[str, Any]],
    *,
    bind_host: str,
    port: int,
    seconds: float,
    elapsed_sec: float,
    min_packets: int,
    raw_payload_retained: bool,
) -> dict[str, Any]:
    packet_count = len(events)
    total_bytes = sum(int(event.get("bytes") or 0) for event in events)
    senders: dict[str, dict[str, Any]] = {}
    for event in events:
        sender = str(event.get("sender") or "unknown")
        bucket = senders.setdefault(sender, {"packets": 0, "bytes": 0})
        bucket["packets"] += 1
        bucket["bytes"] += int(event.get("bytes") or 0)

    received = packet_count >= min_packets
    return {
        "contract_version": CONTRACT_VERSION,
        "label": "udp-received" if received else "udp-no-packets",
        "ok": received,
        "bind_host": bind_host,
        "port": port,
        "requested_seconds": seconds,
        "elapsed_sec": round(elapsed_sec, 3),
        "packet_count": packet_count,
        "total_bytes": total_bytes,
        "packets_per_sec": round(packet_count / max(elapsed_sec, 0.001), 3),
        "senders": senders,
        "first_packet_ms": events[0]["t_ms"] if events else None,
        "last_packet_ms": events[-1]["t_ms"] if events else None,
        "raw_payload_retained": raw_payload_retained,
        "sample": next((event for event in events if "sample_hex" in event), None),
        "privacy_note": "Raw mocopi motion payloads are not retained unless include_sample_hex is set.",
        "interpretation": _interpretation(received),
        "next_actions": _next_actions(received),
    }


def _interpretation(received: bool) -> str:
    if received:
        return (
            "The phone/app can reach this PC over UDP. Quest live retargeting is still a separate "
            "adapter step; this only proves transport reachability."
        )
    return (
        "No UDP packets were received. Check phone and PC are on the same LAN, Windows Firewall, "
        "the PC IPv4 address, and that the mocopi app is in Motion Send mode."
    )


def _next_actions(received: bool) -> list[str]:
    if received:
        return [
            "Capture this JSON as mocopi transport evidence.",
            "Run the Quest BODY baseline and MOCOPI-derived replay evidence packs.",
            "Do not claim live Quest mocopi until a parser/retargeter feeds Quest motion diagnostics.",
        ]
    return [
        "Use the PC IPv4 address, not localhost or IPv6, in the mocopi app destination.",
        "Open/allow UDP port 12351 in Windows Firewall or retry on the selected port.",
        "Confirm the mocopi app is switched from Motion Save to Motion Send before Capture.",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--min-packets", type=int, default=1)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report-json", action="store_true")
    parser.add_argument("--include-sample-hex", action="store_true")
    args = parser.parse_args(argv)

    report = probe_mocopi_udp(
        bind_host=args.bind_host,
        port=args.port,
        seconds=args.seconds,
        min_packets=args.min_packets,
        include_sample_hex=args.include_sample_hex,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['label']}: packets={report['packet_count']} port={report['port']}")
        for action in report["next_actions"]:
            print(f"- {action}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
