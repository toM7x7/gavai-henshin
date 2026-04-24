"""PC-side mocopi UDP bridge.

This bridge intentionally keeps the browser-facing contract simple:
receive a local UDP packet, normalize it into the mocopi-live frame JSON, then
POST it to the local dashboard API. Native mocopi binary packets can be adapted
later by replacing only the packet decoder.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from .iw_henshin import JOINT_ALIASES


DEFAULT_LISTEN_HOST = "0.0.0.0"
DEFAULT_LISTEN_PORT = 12351
DEFAULT_DASHBOARD_ENDPOINT = "http://127.0.0.1:8010/api/iw-henshin/mocopi-live/frame"


@dataclass(slots=True)
class MocopiBridgeConfig:
    listen_host: str = DEFAULT_LISTEN_HOST
    listen_port: int = DEFAULT_LISTEN_PORT
    dashboard_endpoint: str = DEFAULT_DASHBOARD_ENDPOINT
    status_endpoint: str | None = None
    input_format: str = "auto"
    timeout_sec: float = 2.0
    quiet: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class OscMessage:
    address: str
    args: list[Any]


class MocopiBridgeError(RuntimeError):
    pass


def _norm_token(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _joint_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in JOINT_ALIASES.items():
        lookup[_norm_token(canonical)] = canonical
        for alias in aliases:
            lookup[_norm_token(alias)] = canonical
    return lookup


JOINT_LOOKUP = _joint_lookup()


def _decode_json_payload(data: bytes) -> dict[str, Any] | None:
    try:
        decoded = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        return None
    if not decoded:
        return None
    if not (decoded.startswith("{") or decoded.startswith("[")):
        return None
    value = json.loads(decoded)
    if isinstance(value, list):
        return {"frames": value}
    if not isinstance(value, dict):
        return None
    if "frames" in value or "mocopi_frames" in value or "bones" in value or "joints" in value:
        return value
    if "address" in value and "args" in value:
        return _payload_from_osc_messages([OscMessage(str(value["address"]), list(value.get("args") or []))])
    return {"frames": [value]}


def _read_osc_string(data: bytes, offset: int) -> tuple[str, int]:
    end = data.find(b"\0", offset)
    if end < 0:
        raise MocopiBridgeError("Invalid OSC string.")
    raw = data[offset:end]
    next_offset = (end + 4) & ~0x03
    return raw.decode("utf-8", errors="replace"), next_offset


def _read_osc_blob(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(data):
        raise MocopiBridgeError("Invalid OSC blob length.")
    size = struct.unpack(">i", data[offset : offset + 4])[0]
    start = offset + 4
    end = start + size
    if size < 0 or end > len(data):
        raise MocopiBridgeError("Invalid OSC blob payload.")
    next_offset = (end + 3) & ~0x03
    return data[start:end], next_offset


def _parse_osc_message(data: bytes, offset: int = 0, limit: int | None = None) -> tuple[list[OscMessage], int]:
    end_limit = len(data) if limit is None else limit
    address, offset = _read_osc_string(data, offset)
    if address == "#bundle":
        if offset + 8 > end_limit:
            raise MocopiBridgeError("Invalid OSC bundle timestamp.")
        offset += 8
        messages: list[OscMessage] = []
        while offset < end_limit:
            if offset + 4 > end_limit:
                raise MocopiBridgeError("Invalid OSC bundle element size.")
            size = struct.unpack(">i", data[offset : offset + 4])[0]
            offset += 4
            if size <= 0 or offset + size > end_limit:
                raise MocopiBridgeError("Invalid OSC bundle element payload.")
            nested, _ = _parse_osc_message(data, offset, offset + size)
            messages.extend(nested)
            offset += size
        return messages, offset

    typetags, offset = _read_osc_string(data, offset)
    if not typetags.startswith(","):
        raise MocopiBridgeError("Invalid OSC typetag string.")
    args: list[Any] = []
    for tag in typetags[1:]:
        if tag == "f":
            if offset + 4 > end_limit:
                raise MocopiBridgeError("Invalid OSC float.")
            args.append(struct.unpack(">f", data[offset : offset + 4])[0])
            offset += 4
        elif tag == "i":
            if offset + 4 > end_limit:
                raise MocopiBridgeError("Invalid OSC int.")
            args.append(struct.unpack(">i", data[offset : offset + 4])[0])
            offset += 4
        elif tag == "s":
            value, offset = _read_osc_string(data, offset)
            args.append(value)
        elif tag == "b":
            value, offset = _read_osc_blob(data, offset)
            args.append(value)
        elif tag == "T":
            args.append(True)
        elif tag == "F":
            args.append(False)
        elif tag == "N":
            args.append(None)
        else:
            raise MocopiBridgeError(f"Unsupported OSC type tag: {tag}")
    return [OscMessage(address=address, args=args)], offset


def decode_osc_messages(data: bytes) -> list[OscMessage]:
    messages, _ = _parse_osc_message(data)
    return messages


def _joint_from_address(address: str) -> str | None:
    tokens = [_norm_token(token) for token in address.replace("\\", "/").split("/") if token]
    joined = _norm_token(address)
    for token in reversed(tokens):
        if token in JOINT_LOOKUP:
            return JOINT_LOOKUP[token]
    for token, canonical in JOINT_LOOKUP.items():
        if token and token in joined:
            return canonical
    return None


def _float_args(args: Iterable[Any]) -> list[float]:
    floats: list[float] = []
    for value in args:
        if isinstance(value, (int, float)):
            floats.append(float(value))
    return floats


def _payload_from_osc_messages(messages: list[OscMessage]) -> dict[str, Any] | None:
    bones: dict[str, list[float]] = {}
    dt_sec: float | None = None
    for message in messages:
        if message.address.endswith("/dt") or message.address.endswith("/dt_sec"):
            values = _float_args(message.args)
            if values:
                dt_sec = max(0.001, min(values[0], 1.0))
            continue
        if message.args and isinstance(message.args[0], str):
            nested = _decode_json_payload(str(message.args[0]).encode("utf-8"))
            if nested:
                return nested
        joint = _joint_from_address(message.address)
        values = _float_args(message.args)
        if joint and len(values) >= 2:
            bones[joint] = values[:3] if len(values) >= 3 else values[:2]
    if not bones:
        return None
    return {"frames": [{"dt_sec": dt_sec or 0.033, "bones": bones}]}


def decode_bridge_payload(data: bytes, *, input_format: str = "auto") -> dict[str, Any] | None:
    mode = input_format.lower().strip()
    if mode not in {"auto", "json", "osc"}:
        raise ValueError("input_format must be auto, json, or osc.")
    if mode in {"auto", "json"}:
        payload = _decode_json_payload(data)
        if payload is not None or mode == "json":
            return payload
    if mode in {"auto", "osc"}:
        try:
            return _payload_from_osc_messages(decode_osc_messages(data))
        except MocopiBridgeError:
            if mode == "osc":
                raise
    return None


def _default_status_endpoint(endpoint: str) -> str:
    if endpoint.endswith("/frame"):
        return f"{endpoint[:-len('/frame')]}/bridge-status"
    return endpoint.rstrip("/") + "/bridge-status"


def post_json(endpoint: str, payload: dict[str, Any], *, timeout_sec: float = 2.0) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {"ok": response.status < 400}
    except urllib.error.URLError as exc:
        raise MocopiBridgeError(f"Failed to POST JSON: {exc}") from exc


def post_frame(endpoint: str, payload: dict[str, Any], *, timeout_sec: float = 2.0) -> dict[str, Any]:
    try:
        return post_json(endpoint, payload, timeout_sec=timeout_sec)
    except MocopiBridgeError as exc:
        raise MocopiBridgeError(f"Failed to POST mocopi frame: {exc}") from exc


def post_bridge_status(endpoint: str, payload: dict[str, Any], *, timeout_sec: float = 2.0) -> None:
    try:
        post_json(endpoint, payload, timeout_sec=timeout_sec)
    except MocopiBridgeError:
        return


def run_udp_bridge(config: MocopiBridgeConfig, *, stop_event: threading.Event | None = None) -> int:
    stop = stop_event or threading.Event()
    status_endpoint = config.status_endpoint or _default_status_endpoint(config.dashboard_endpoint)
    received = 0
    forwarded = 0
    unsupported = 0
    last_log = 0.0
    last_status = 0.0
    last_source: str | None = None
    last_error: str | None = None
    last_packet_bytes: int | None = None

    def emit_status(event: str, *, packet_seen: bool = False) -> None:
        post_bridge_status(
            status_endpoint,
            {
                "ok": last_error is None or event != "unsupported",
                "event": event,
                "listening": f"{config.listen_host}:{config.listen_port}",
                "received": received,
                "forwarded_frames": forwarded,
                "unsupported": unsupported,
                "last_source": last_source,
                "last_error": last_error,
                "last_packet_bytes": last_packet_bytes,
                "input_format": config.input_format,
                "dry_run": config.dry_run,
                "packet_seen": packet_seen,
            },
            timeout_sec=min(config.timeout_sec, 0.5),
        )

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((config.listen_host, int(config.listen_port)))
        sock.settimeout(0.3)
        if not config.quiet:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "message": "mocopi UDP bridge listening",
                        "listen": f"{config.listen_host}:{config.listen_port}",
                        "endpoint": config.dashboard_endpoint,
                        "status_endpoint": status_endpoint,
                        "input_format": config.input_format,
                        "dry_run": config.dry_run,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        emit_status("listening")
        while not stop.is_set():
            try:
                data, address = sock.recvfrom(65535)
            except TimeoutError:
                now = time.time()
                if now - last_status > 2:
                    last_status = now
                    emit_status("heartbeat")
                continue
            except socket.timeout:
                now = time.time()
                if now - last_status > 2:
                    last_status = now
                    emit_status("heartbeat")
                continue
            received += 1
            last_source = f"{address[0]}:{address[1]}"
            last_packet_bytes = len(data)
            try:
                payload = decode_bridge_payload(data, input_format=config.input_format)
            except (ValueError, MocopiBridgeError, json.JSONDecodeError) as exc:
                unsupported += 1
                last_error = str(exc)
                emit_status("unsupported", packet_seen=True)
                if not config.quiet:
                    print(json.dumps({"ok": False, "source": address[0], "error": str(exc)}, ensure_ascii=False), flush=True)
                continue
            if payload is None:
                unsupported += 1
                last_error = "Unsupported mocopi packet. Use JSON/OSC or add a Motion Serializer adapter."
                emit_status("unsupported", packet_seen=True)
                now = time.time()
                if not config.quiet and now - last_log > 2:
                    last_log = now
                    print(
                        json.dumps(
                            {
                                "ok": False,
                                "source": address[0],
                                "error": "Unsupported mocopi packet. Use JSON/OSC or add a Motion Serializer adapter.",
                                "received": received,
                                "unsupported": unsupported,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                continue
            if config.dry_run:
                result = {"ok": True, "dry_run": True, "accepted_frames": len(payload.get("frames") or [payload])}
            else:
                result = post_frame(config.dashboard_endpoint, payload, timeout_sec=config.timeout_sec)
            forwarded += int(result.get("accepted_frames") or 0)
            last_error = None
            emit_status("accepted", packet_seen=True)
            if not config.quiet:
                print(
                    json.dumps(
                        {
                            "ok": bool(result.get("ok", True)),
                            "source": f"{address[0]}:{address[1]}",
                            "accepted_frames": result.get("accepted_frames"),
                            "connected": result.get("connected"),
                            "axis": result.get("axis"),
                            "received": received,
                            "forwarded_frames": forwarded,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    return 0
