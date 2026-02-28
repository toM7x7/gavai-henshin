"""Session workspace and artifact writers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .transform import ProtocolStateMachine


def ensure_session_dir(session_id: str, root: str | Path = "sessions") -> Path:
    base = Path(root)
    session_dir = base / session_id
    (session_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    return session_dir


def write_protocol_log(path: Path, machine: ProtocolStateMachine) -> Path:
    lines = []
    for e in machine.events:
        refusal = f" code={e.refusal_code}" if e.refusal_code else ""
        lines.append(
            f"{e.timestamp} {e.from_state}->{e.to_state} status={e.status}{refusal} note={e.note}"
        )
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def write_audit_summary(path: Path, session_id: str, machine: ProtocolStateMachine) -> Path:
    status = machine.state
    lines = [
        f"SESSION: {session_id}",
        f"FINAL_STATUS: {status}",
        f"EVENT_COUNT: {len(machine.events)}",
        "AUDIT: READY" if status in {"ARCHIVED", "REFUSED"} else "AUDIT: INCOMPLETE",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def touch_binary(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def save_session_bundle(
    session_id: str,
    suit_spec: dict[str, Any],
    morphotype: dict[str, Any],
    machine: ProtocolStateMachine,
    root: str | Path = "sessions",
) -> dict[str, Path]:
    session_dir = ensure_session_dir(session_id=session_id, root=root)
    artifacts = session_dir / "artifacts"

    paths = {
        "suitspec_json": write_json(session_dir / "suitspec.json", suit_spec),
        "morphotype_json": write_json(session_dir / "morphotype.json", morphotype),
        "deposition_log": write_protocol_log(artifacts / "DepositionLog.txt", machine),
        "audit_summary": write_audit_summary(artifacts / "AuditSummary.txt", session_id, machine),
        "blueprint_png": touch_binary(artifacts / "Blueprint.png"),
        "emblem_png": touch_binary(artifacts / "Emblem.png"),
        "archive_clip": touch_binary(artifacts / "ArchiveClip.mp4"),
    }
    return paths
